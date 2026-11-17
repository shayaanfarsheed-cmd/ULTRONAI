from __future__ import annotations

import json
import os
import random
import signal
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping

import torch

from ultron_checkpoint import LocalCheckpointStore
from ultron_data import generate_dataset
from ultron_model import CharTokenizer, ULTRONTransformer
from ultron_storage import RemoteCheckpointStore, SupabaseStorageClient
from ultron_supabase import (
    LeaseLostError,
    SupabaseAPIError,
    TrainingControlAPI,
    from_environment,
    iso_utc,
)
from ultron_training import (
    CurriculumController,
    MathBatchStream,
    evaluate_by_topic,
    make_grad_scaler,
    train_one_batch,
)


class TrainingSessionError(RuntimeError):
    pass


def get_session_limit_seconds(server: Mapping[str, Any] | None, fallback_seconds: int = 7200) -> int:
    if server is None:
        return fallback_seconds
    limits = server.get("limits", {})
    hours = (
        limits.get("session_limit_hours")
        or limits.get("free_studio_restart_hours")
        or limits.get("job_execution_limit_hours")
    )
    if hours is None:
        return fallback_seconds
    return max(60, int(float(hours) * 3600))


def _build_model(config: Mapping[str, Any], tokenizer: CharTokenizer) -> ULTRONTransformer:
    settings = config.get("model", {})
    model = ULTRONTransformer(
        vocab_size=tokenizer.vocab_size,
        context_length=int(settings.get("context_length", 192)),
        dimension=int(settings.get("embedding_dimension", 256)),
        layers=int(settings.get("transformer_layers", 5)),
        heads=int(settings.get("attention_heads", 8)),
        feedforward_multiplier=int(settings.get("feedforward_multiplier", 4)),
        dropout=float(settings.get("dropout", 0.1)),
    )
    expected = settings.get("expected_parameter_count")
    if expected is not None and model.parameter_count() != int(expected):
        raise TrainingSessionError(
            f"Model parameter count {model.parameter_count()} does not match configured count {expected}"
        )
    return model


def _make_curriculum(config: Mapping[str, Any]) -> CurriculumController:
    settings = config.get("training", {}).get("curriculum", {})
    return CurriculumController(
        settings.get("stages", []),
        mastery_accuracy=float(settings.get("unlock_mastery_accuracy", 0.9)),
        consecutive_evaluations=int(settings.get("consecutive_evaluations_required", 3)),
        require_held_out=bool(settings.get("held_out_evaluation_required", True)),
    )


def _make_training_stream(
    config: Mapping[str, Any],
    tokenizer: CharTokenizer,
    curriculum: CurriculumController,
    seed: int,
    batch_size: int,
) -> MathBatchStream:
    if curriculum.is_finished:
        raise TrainingSessionError("Curriculum has already reached its final stage")
    stage_index = curriculum.stage_index
    stage_seed = seed + stage_index * 100_003
    examples_per_stage = int(config.get("training", {}).get("examples_per_stage", 3000))
    examples = generate_dataset(
        examples_per_stage,
        seed=stage_seed,
        split="train",
        topics=curriculum.current_topics,
    )
    return MathBatchStream(
        examples,
        tokenizer,
        context_length=int(config.get("model", {}).get("context_length", 192)),
        batch_size=batch_size,
        seed=stage_seed,
    )


def _evaluate_current_stage(
    model: torch.nn.Module,
    tokenizer: CharTokenizer,
    config: Mapping[str, Any],
    curriculum: CurriculumController,
    seed: int,
    device: str,
) -> dict[str, dict[str, float | int]]:
    if curriculum.is_finished:
        return {}
    topics = curriculum.current_topics
    stage_index = curriculum.stage_index
    examples_per_topic = int(config.get("training", {}).get("evaluation_examples_per_topic", 10))
    total_examples = max(len(topics), examples_per_topic * len(topics) * 10)
    evaluation_seed = seed + 999_983 + stage_index * 100_003
    held_out = generate_dataset(
        total_examples,
        seed=evaluation_seed,
        split="test",
        topics=topics,
    )
    return evaluate_by_topic(
        model,
        held_out,
        tokenizer,
        context_length=int(config.get("model", {}).get("context_length", 192)),
        device=device,
        maximum_examples_per_topic=examples_per_topic,
    )


def run_training_session(
    config: Mapping[str, Any],
    servers: Mapping[str, Any],
    checkpoint_root: str | Path = "/tmp/ultron-checkpoints",
    api: TrainingControlAPI | None = None,
    remote_store: RemoteCheckpointStore | None = None,
    platform_id: str | None = None,
    runtime_override: Mapping[str, Any] | None = None,
    max_steps_override: int | None = None,
    stop_checker: Callable[[], bool] | None = None,
    model_factory: Callable[[CharTokenizer], torch.nn.Module] | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    from train import detect_platform, resolve_runtime_settings

    platform = platform_id or detect_platform()
    server = next((item for item in servers.get("servers", []) if item.get("id") == platform), None)
    if server is None:
        server = next((item for item in servers.get("servers", []) if item.get("provider") == platform), None)
    server_name = str(server.get("name")) if server else platform
    server_id = str(server.get("id")) if server else platform
    session_limit = get_session_limit_seconds(server)
    safety_margin = int(config.get("session_management", {}).get("session_safety_margin_minutes", 10) * 60)
    coordination = config.get("coordination", {})
    lease_ttl = int(coordination.get("lease_ttl_seconds", 780))
    heartbeat_interval = int(config.get("monitoring", {}).get("heartbeat_interval_seconds", 60))
    checkpoint_interval = int(config.get("persistence", {}).get("checkpoint_interval_seconds", 300))
    retention = int(config.get("persistence", {}).get("keep_last_valid_checkpoints", 3))
    maximum_steps = int(config.get("training", {}).get("maximum_training_steps", 100000))
    if max_steps_override is not None:
        maximum_steps = min(maximum_steps, int(max_steps_override))
    if maximum_steps < 1:
        raise ValueError("Maximum training steps must be positive")

    if api is None:
        configured_url = config.get("database", {}).get("project_url")
        if configured_url and not os.environ.get("SUPABASE_URL"):
            os.environ["SUPABASE_URL"] = str(configured_url)
        api = from_environment()
    if remote_store is None:
        project_url = api.client.project_url
        secret_key = api.client._api_key
        remote_store = RemoteCheckpointStore(
            SupabaseStorageClient(project_url, secret_key),
            bucket=str(config.get("storage", {}).get("supabase_bucket", "checkpoints")),
            keep_last=retention,
            maximum_file_bytes=int(float(config.get("persistence", {}).get("max_single_storage_object_mb", 45)) * 1_000_000),
        )

    if runtime_override is None:
        runtime = resolve_runtime_settings(config, platform, torch_module=torch)
    else:
        runtime = dict(runtime_override)
    device = str(runtime["device"])
    gpu_name = torch.cuda.get_device_name(0) if device == "cuda" and torch.cuda.is_available() else None

    run_id = api.create_run_id()
    lease_holder = f"{platform}:{uuid.uuid4().hex}"
    lease_result = api.acquire_lease(
        run_id,
        server_name,
        lease_holder,
        lease_ttl,
        device=device,
        session_limit_seconds=session_limit,
    )
    if not lease_result.acquired:
        return {
            "state": "waiting_for_lease",
            "run_id": lease_result.run_id,
            "lease_holder": lease_result.lease_holder,
            "lease_expires_at": lease_result.lease_expires_at,
            "message": "Waiting for the other server to stop and release its training lease.",
        }
    fencing_token = int(lease_result.fencing_token or 0)
    lease_deadline = monotonic() + lease_ttl
    session_start = monotonic()
    session_start_iso = iso_utc()
    gpu_seconds = 0.0
    session_id = lease_result.session_id or api.start_session(
        run_id,
        server_name,
        details={"server_id": server_id, "compute_device": device, "gpu_name": gpu_name},
    )
    try:
        api.update_server_status(
            run_id,
            server_id,
            "running",
            extra={"compute_device": device, "gpu_name": gpu_name, "last_started_at": session_start_iso},
        )
    except Exception:
        pass
    batch_size = int(runtime["batch_size"])
    cpu_threads = int(runtime.get("cpu_threads", 1))
    torch.set_num_threads(max(1, cpu_threads))

    seed = int(config.get("training", {}).get("seed", 20261117))
    random.seed(seed)
    torch.manual_seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except Exception:
        pass

    tokenizer = CharTokenizer()
    model = (model_factory or (lambda item: _build_model(config, item)))(tokenizer)
    model.to(device)
    training_settings = config.get("training", {})
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(training_settings.get("learning_rate", 0.0003)),
        weight_decay=float(training_settings.get("weight_decay", 0.1)),
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=max(1, int(training_settings.get("maximum_training_steps", 100000))),
    )
    precision = str(runtime.get("mixed_precision", "none")) if device == "cuda" else "none"
    scaler = make_grad_scaler(device, precision)
    curriculum = _make_curriculum(config)
    local_store = LocalCheckpointStore(
        checkpoint_root,
        keep_last=retention,
        maximum_file_bytes=int(float(config.get("persistence", {}).get("max_single_storage_object_mb", 45)) * 1_000_000),
    )

    initial_status = api.get_status(run_id) or {}
    committed_step = initial_status.get("last_checkpoint_step")
    requested_resume_id = initial_status.get("requested_resume_checkpoint_id")
    selected_remote_candidate = None
    if committed_step is not None:
        try:
            candidates = remote_store.list_remote_candidates(
                api.owner_id,
                run_id,
                maximum_step=int(committed_step),
            )
        except Exception:
            candidates = []
        pointer_id = initial_status.get("last_checkpoint_id")
        candidates.sort(
            key=lambda item: (
                item.get("checkpoint_id") != requested_resume_id,
                item.get("checkpoint_id") != pointer_id,
                -int(item.get("step", 0)),
            )
        )
        for candidate in candidates:
            try:
                remote_store.download_checkpoint(
                    api.owner_id,
                    run_id,
                    str(candidate["checkpoint_id"]),
                    local_store,
                )
                selected_remote_candidate = candidate
                break
            except Exception:
                continue

    loaded = local_store.load_latest(model, optimizer, scheduler, restore_rng=True, map_location=device)
    if loaded is not None:
        state = dict(loaded["state"])
        if requested_resume_id:
            if selected_remote_candidate is None or selected_remote_candidate.get("checkpoint_id") != requested_resume_id:
                raise TrainingSessionError(
                    "The requested resume checkpoint could not be verified. Training was stopped without starting from a different checkpoint."
                )
            api.select_resume_checkpoint(
                run_id,
                lease_holder,
                fencing_token,
                selected_remote_candidate,
                state,
            )
        step = int(state["step"])
        if state.get("curriculum_state"):
            curriculum.load_state_dict(state["curriculum_state"])
        if scaler is not None and state.get("grad_scaler_state"):
            scaler.load_state_dict(state["grad_scaler_state"])
        accuracy_by_topic = dict(state.get("accuracy_by_topic") or {})
        last_loss = state.get("loss")
        if "seed" in state:
            seed = int(state["seed"])
        resume_stream_state = state.get("batch_stream")
        last_saved_step = step
    else:
        if committed_step is not None:
            raise TrainingSessionError(
                "A committed checkpoint exists, but no valid local or remote copy could be restored. Refusing to start fresh."
            )
        state = {}
        step = 0
        accuracy_by_topic = {}
        last_loss = None
        resume_stream_state = None
        last_saved_step = -1

    if curriculum.is_finished:
        api.release_lease(run_id, lease_holder, fencing_token, "finished")
        return {"state": "finished", "run_id": run_id, "step": step, "reason": "curriculum already mastered"}

    stream = _make_training_stream(config, tokenizer, curriculum, seed, batch_size)
    if resume_stream_state is not None:
        stream.load_state_dict(resume_stream_state)

    stop_requested = False
    previous_handlers: dict[int, Any] = {}

    def request_stop(signum: int, frame: Any) -> None:
        nonlocal stop_requested
        stop_requested = True

    for signal_name in ("SIGTERM", "SIGINT"):
        signal_value = getattr(signal, signal_name, None)
        if signal_value is not None:
            try:
                previous_handlers[signal_value] = signal.getsignal(signal_value)
                signal.signal(signal_value, request_stop)
            except (ValueError, OSError):
                pass

    last_heartbeat = monotonic() - heartbeat_interval
    last_checkpoint = monotonic()
    pending_checkpoint_id: str | None = None
    pending_state: dict[str, Any] | None = None
    last_error: str | None = None
    switch_completion_marked = False
    final_state = "finished"
    force_handoff_reason = "no_gpu" if server and server.get("role") in {"primary_gpu", "backup_gpu"} and device != "cuda" else None
    lease_lost = False

    def build_training_state() -> dict[str, Any]:
        current_topic = curriculum.select_topic(step) or "completed"
        difficulty = max(1, curriculum.stage_index + 1)
        return {
            "step": step,
            "current_topic": current_topic,
            "difficulty": difficulty,
            "data_position": stream.position,
            "data_epoch": stream.epoch,
            "seed": seed,
            "lease_holder": lease_holder,
            "fencing_token": fencing_token,
            "loss": last_loss,
            "accuracy_by_topic": accuracy_by_topic,
            "curriculum_state": curriculum.state_dict(),
            "batch_stream": stream.state_dict(),
            "learning_rate": float(optimizer.param_groups[0]["lr"]),
            "grad_scaler_state": scaler.state_dict() if scaler is not None else None,
            "run_id": run_id,
            "platform": platform,
            "session_started_at": session_start_iso,
        }

    def save_checkpoint() -> bool:
        nonlocal pending_checkpoint_id, pending_state, last_checkpoint, last_error, last_saved_step
        if step == last_saved_step and pending_checkpoint_id is None:
            return True
        training_state = build_training_state()
        manifest = local_store.save(model, optimizer, training_state, scheduler)
        pending_checkpoint_id = str(manifest["checkpoint_id"])
        pending_state = training_state
        last_checkpoint = monotonic()
        last_saved_step = step
        try:
            remote_store.upload_and_commit(
                local_store,
                pending_checkpoint_id,
                api.owner_id,
                run_id,
                api,
                lease_holder,
                fencing_token,
                pending_state,
            )
            pending_checkpoint_id = None
            pending_state = None
            last_error = None
            return True
        except LeaseLostError:
            raise
        except Exception as error:
            last_error = type(error).__name__
            return False

    def update_heartbeat() -> bool:
        nonlocal last_heartbeat, lease_deadline, switch_completion_marked
        elapsed = monotonic() - session_start
        remaining = max(0, int(session_limit - elapsed))
        values = {
            "current_server": server_name,
            "current_step": step,
            "current_topic": curriculum.select_topic(step),
            "difficulty": max(1, curriculum.stage_index + 1),
            "data_position": stream.position,
            "data_epoch": stream.epoch,
            "loss": last_loss,
            "accuracy_by_topic": accuracy_by_topic,
            "curriculum_state": curriculum.state_dict(),
            "learning_rate": float(optimizer.param_groups[0]["lr"]),
            "session_limit_seconds": session_limit,
            "session_time_left_seconds": remaining,
            "state": "running",
            "last_error": last_error,
        }
        renewed = api.renew_lease(run_id, lease_holder, fencing_token, lease_ttl, status_values=values)
        if renewed:
            last_heartbeat = monotonic()
            lease_deadline = last_heartbeat + lease_ttl
            if not switch_completion_marked:
                try:
                    api.mark_switch_requests_done(run_id, server_id)
                    switch_completion_marked = True
                except Exception:
                    pass
        return renewed

    def finish(
        final_status: str,
        reason: str,
        create_switch: bool = False,
        switch_reason: str | None = None,
    ) -> dict[str, Any]:
        nonlocal final_state
        final_state = final_status
        if not lease_lost:
            try:
                api.release_lease(run_id, lease_holder, fencing_token, final_status)
            except Exception:
                pass
        if create_switch:
            try:
                api.create_switch_request(
                    run_id,
                    server_name,
                    None,
                    switch_reason or "handoff_needed",
                    automatic=False,
                    metadata={"step": step, "reason": reason},
                )
            except Exception:
                pass
        try:
            latest_status = api.get_status(run_id) or {}
        except Exception:
            latest_status = {}
        return {
            "state": final_state,
            "run_id": run_id,
            "server": server_name,
            "step": step,
            "loss": last_loss,
            "accuracy_by_topic": accuracy_by_topic,
            "reason": reason,
            "last_checkpoint_id": pending_checkpoint_id or latest_status.get("last_checkpoint_id"),
            "last_error": last_error,
        }

    try:
        while step < maximum_steps:
            now = monotonic()
            elapsed = now - session_start
            remaining = session_limit - elapsed

            if force_handoff_reason is not None:
                try:
                    save_checkpoint()
                except LeaseLostError:
                    lease_lost = True
                    return finish("dead", "lease_lost_during_no_gpu_handoff")
                return finish("handoff_needed", "no_gpu", create_switch=True, switch_reason="no_gpu")

            if remaining <= safety_margin:
                try:
                    save_checkpoint()
                except LeaseLostError:
                    lease_lost = True
                    return finish("dead", "lease_lost_before_handoff")
                if pending_checkpoint_id is None:
                    return finish("handoff_needed", "session_limit", create_switch=True)
                return finish("handoff_needed", "session_limit_checkpoint_not_committed", create_switch=True)

            if stop_requested or (stop_checker is not None and stop_checker()):
                try:
                    save_checkpoint()
                except LeaseLostError:
                    lease_lost = True
                    return finish("dead", "lease_lost_during_stop")
                return finish("paused", "user_stop")

            if now - last_heartbeat >= heartbeat_interval:
                try:
                    if not update_heartbeat():
                        lease_lost = True
                        return finish("dead", "lease_lost")
                    controls = api.controls(run_id)
                    if controls.get("pause_requested"):
                        try:
                            save_checkpoint()
                        except LeaseLostError:
                            lease_lost = True
                            return finish("dead", "lease_lost_during_pause")
                        return finish("paused", "pause_requested")
                    if controls.get("handoff_requested"):
                        try:
                            save_checkpoint()
                        except LeaseLostError:
                            lease_lost = True
                            return finish("dead", "lease_lost_during_handoff")
                        return finish("handoff_needed", "handoff_requested")
                    if pending_checkpoint_id is not None and pending_state is not None:
                        try:
                            remote_store.upload_and_commit(
                                local_store,
                                pending_checkpoint_id,
                                api.owner_id,
                                run_id,
                                api,
                                lease_holder,
                                fencing_token,
                                pending_state,
                            )
                            pending_checkpoint_id = None
                            pending_state = None
                            last_error = None
                        except LeaseLostError:
                            lease_lost = True
                            return finish("dead", "lease_lost_during_checkpoint_retry")
                        except Exception as error:
                            last_error = type(error).__name__
                except SupabaseAPIError:
                    last_heartbeat = monotonic()
                    if monotonic() >= lease_deadline - 30:
                        try:
                            save_checkpoint()
                        except LeaseLostError:
                            lease_lost = True
                        return finish("dead", "database_unreachable_lease_expiring")
                except Exception as error:
                    last_error = type(error).__name__

            batch = stream.next_batch(tokenizer.stoi[" "])
            try:
                last_loss = train_one_batch(
                    model,
                    optimizer,
                    batch,
                    device,
                    precision=precision,
                    gradient_clip_norm=float(training_settings.get("gradient_clip_norm", 1.0)),
                    scaler=scaler,
                )
            except FloatingPointError:
                try:
                    save_checkpoint()
                except Exception:
                    pass
                return finish("dead", "non_finite_training_loss")
            scheduler.step()
            step += 1
            if device == "cuda":
                gpu_seconds = monotonic() - session_start

            evaluation_interval = int(training_settings.get("evaluation_interval_steps", 500))
            if evaluation_interval > 0 and step % evaluation_interval == 0:
                metrics = _evaluate_current_stage(model, tokenizer, config, curriculum, seed, device)
                accuracy_by_topic.update(metrics)
                advanced = curriculum.record_evaluation(metrics, held_out=True)
                if advanced:
                    if curriculum.is_finished:
                        try:
                            save_checkpoint()
                        except LeaseLostError:
                            lease_lost = True
                            return finish("dead", "lease_lost_at_curriculum_completion")
                        return finish("finished", "curriculum_mastery")
                    stream = _make_training_stream(config, tokenizer, curriculum, seed, batch_size)

            if checkpoint_interval <= 0 or monotonic() - last_checkpoint >= checkpoint_interval:
                try:
                    save_checkpoint()
                except LeaseLostError:
                    lease_lost = True
                    return finish("dead", "lease_lost_during_checkpoint")

        try:
            save_checkpoint()
        except LeaseLostError:
            lease_lost = True
            return finish("dead", "lease_lost_at_maximum_steps")
        if max_steps_override is not None:
            return finish("paused", "test_step_limit")
        return finish("finished", "maximum_training_steps")
    except KeyboardInterrupt:
        try:
            save_checkpoint()
        except Exception:
            pass
        return finish("paused", "keyboard_interrupt")
    except Exception as error:
        if not lease_lost:
            try:
                save_checkpoint()
            except Exception:
                pass
        result = finish("dead", f"training_error:{type(error).__name__}")
        raise TrainingSessionError(json.dumps(result)) from error
    finally:
        for signal_value, handler in previous_handlers.items():
            try:
                signal.signal(signal_value, handler)
            except (ValueError, OSError):
                pass
