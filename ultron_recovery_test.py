from __future__ import annotations

import copy
import math
import uuid
from tempfile import TemporaryDirectory
from typing import Any, Mapping

import torch

from ultron_checkpoint import LocalCheckpointStore
from ultron_model import CharTokenizer, ULTRONTransformer
from ultron_storage import RemoteCheckpointStore
from ultron_training import CurriculumController, MathBatchStream, make_grad_scaler, train_steps


def _make_objects(tokenizer: CharTokenizer, device: str, architecture: Mapping[str, int] | None = None):
    settings = dict(architecture or {
        "dimension": 32,
        "layers": 1,
        "heads": 4,
        "feedforward_multiplier": 2,
    })
    model = ULTRONTransformer(
        vocab_size=tokenizer.vocab_size,
        context_length=192,
        dimension=int(settings["dimension"]),
        layers=int(settings["layers"]),
        heads=int(settings["heads"]),
        feedforward_multiplier=int(settings["feedforward_multiplier"]),
        dropout=0.1,
    ).to(device)
    # Move the model before creating the optimizer so its parameter references
    # and optimizer state are bound to the final device from the outset.
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=8)
    return model, optimizer, scheduler


def _equal_nested(left: Any, right: Any) -> bool:
    if isinstance(left, torch.Tensor) or isinstance(right, torch.Tensor):
        return isinstance(left, torch.Tensor) and isinstance(right, torch.Tensor) and torch.equal(left, right)
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return left.keys() == right.keys() and all(_equal_nested(left[key], right[key]) for key in left)
    if isinstance(left, (tuple, list)) and isinstance(right, (tuple, list)):
        return len(left) == len(right) and all(_equal_nested(a, b) for a, b in zip(left, right))
    if isinstance(left, float) and isinstance(right, float):
        return math.isclose(left, right, rel_tol=0.0, abs_tol=0.0)
    return left == right


def run_checkpoint_recovery_test(
    storage: Any,
    owner_id: str,
    bucket: str = "checkpoints",
    maximum_file_bytes: int = 45_000_000,
    device: str = "auto",
    precision: str = "auto",
    architecture: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Exercise an isolated Storage-only checkpoint round trip and exact next-step resume."""
    if not owner_id or "/" in owner_id or "\\" in owner_id:
        raise ValueError("A valid owner ID is required for the isolated recovery test")

    from ultron_data import generate_dataset

    torch.set_num_threads(1)
    torch.manual_seed(20261119)
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA recovery was requested but CUDA is unavailable")
    if precision == "auto":
        precision = ("bf16" if torch.cuda.is_bf16_supported() else "fp16") if device.startswith("cuda") else "none"
    if device == "cpu" and precision != "none":
        raise ValueError("CPU recovery test only supports precision='none'")
    if precision == "bf16" and (not device.startswith("cuda") or not torch.cuda.is_bf16_supported()):
        raise RuntimeError("BF16 recovery requires a CUDA device with BF16 support")
    if precision == "fp16" and not device.startswith("cuda"):
        raise ValueError("FP16 recovery requires CUDA")
    seed = 20261119
    test_run_id = f"recovery-test-{uuid.uuid4().hex}"
    remote = RemoteCheckpointStore(storage, bucket=bucket, keep_last=1, maximum_file_bytes=maximum_file_bytes)
    checkpoint_id: str | None = None
    result: dict[str, Any] | None = None

    try:
        tokenizer = CharTokenizer()
        examples = generate_dataset(
            12,
            seed=seed,
            split="train",
            topics=["whole_number_arithmetic"],
        )
        stages = [{"name": "recovery-test", "topics": ["whole_number_arithmetic"]}]
        curriculum = CurriculumController(stages, require_held_out=False)
        stream = MathBatchStream(
            examples,
            tokenizer,
            context_length=192,
            batch_size=2,
            seed=seed,
            shuffle=True,
        )
        model, optimizer, scheduler = _make_objects(tokenizer, device, architecture)
        scaler = make_grad_scaler(device, precision)
        train_steps(
            model,
            optimizer,
            stream,
            steps=2,
            device=device,
            precision=precision,
            scheduler=scheduler,
            scaler=scaler,
            start_step=0,
        )
        saved_state = {
            "step": 2,
            "current_topic": "whole_number_arithmetic",
            "difficulty": 1,
            "data_position": stream.position,
            "data_epoch": stream.epoch,
            "seed": seed,
            "lease_holder": test_run_id,
            "fencing_token": 1,
            "curriculum_state": curriculum.state_dict(),
            "data_stream_state": stream.state_dict(),
            "loss": None,
            "learning_rate": float(optimizer.param_groups[0]["lr"]),
            "recovery_test": True,
            "grad_scaler_state": scaler.state_dict() if scaler is not None else None,
        }

        with TemporaryDirectory(prefix="ultron-recovery-source-") as source_dir, TemporaryDirectory(
            prefix="ultron-recovery-fresh-"
        ) as fresh_dir:
            source_store = LocalCheckpointStore(source_dir, keep_last=1, maximum_file_bytes=maximum_file_bytes)
            manifest = source_store.save(model, optimizer, saved_state, scheduler=scheduler)
            checkpoint_id = str(manifest["checkpoint_id"])

            uploaded = remote.upload_checkpoint(source_store, checkpoint_id, owner_id, test_run_id)
            remote_manifest = remote.verify_remote_checkpoint(owner_id, test_run_id, checkpoint_id)
            if int(remote_manifest["step"]) != 2 or not uploaded.get("verified"):
                raise RuntimeError("Remote checkpoint verification did not confirm step 2")

            # Continue the original process once to establish the uninterrupted reference.
            train_steps(
                model,
                optimizer,
                stream,
                steps=1,
                device=device,
                precision=precision,
                scheduler=scheduler,
                scaler=scaler,
                start_step=2,
            )
            expected_model = {name: tensor.detach().clone() for name, tensor in model.state_dict().items()}
            expected_optimizer = copy.deepcopy(optimizer.state_dict())
            expected_scheduler = copy.deepcopy(scheduler.state_dict())
            expected_stream = copy.deepcopy(stream.state_dict())
            expected_curriculum = copy.deepcopy(curriculum.state_dict())
            expected_scaler = copy.deepcopy(scaler.state_dict()) if scaler is not None else None

            # A fresh local directory and fresh objects represent a new provider runtime.
            fresh_store = LocalCheckpointStore(fresh_dir, keep_last=1, maximum_file_bytes=maximum_file_bytes)
            downloaded = remote.download_checkpoint(owner_id, test_run_id, checkpoint_id, fresh_store)
            fresh_model, fresh_optimizer, fresh_scheduler = _make_objects(tokenizer, device, architecture)
            fresh_curriculum = CurriculumController(stages, require_held_out=False)
            fresh_scaler = make_grad_scaler(device, precision)
            fresh_stream = MathBatchStream(
                examples,
                tokenizer,
                context_length=192,
                batch_size=2,
                seed=seed + 1,
                shuffle=True,
            )
            restored = fresh_store.load_latest(
                fresh_model,
                fresh_optimizer,
                scheduler=fresh_scheduler,
                restore_rng=True,
                map_location=device,
            )
            if restored is None or int(restored["step"]) != 2:
                raise RuntimeError("Fresh runtime did not restore the exact saved step")
            fresh_stream.load_state_dict(restored["state"]["data_stream_state"])
            fresh_curriculum.load_state_dict(restored["state"]["curriculum_state"])
            if fresh_scaler is not None and restored["state"].get("grad_scaler_state"):
                fresh_scaler.load_state_dict(restored["state"]["grad_scaler_state"])

            train_steps(
                fresh_model,
                fresh_optimizer,
                fresh_stream,
                steps=1,
                device=device,
                precision=precision,
                scheduler=fresh_scheduler,
                scaler=fresh_scaler,
                start_step=int(restored["step"]),
            )

            model_exact = all(
                torch.equal(fresh_model.state_dict()[name], tensor)
                for name, tensor in expected_model.items()
            )
            optimizer_exact = _equal_nested(fresh_optimizer.state_dict(), expected_optimizer)
            scheduler_exact = _equal_nested(fresh_scheduler.state_dict(), expected_scheduler)
            stream_exact = _equal_nested(fresh_stream.state_dict(), expected_stream)
            curriculum_exact = _equal_nested(fresh_curriculum.state_dict(), expected_curriculum)
            scaler_exact = (fresh_scaler is None and expected_scaler is None) or (
                fresh_scaler is not None and _equal_nested(fresh_scaler.state_dict(), expected_scaler)
            )
            source_parameter_ids = {id(parameter) for parameter in model.parameters()}
            source_optimizer_ids = {
                id(parameter)
                for group in optimizer.param_groups
                for parameter in group["params"]
            }
            fresh_parameter_ids = {id(parameter) for parameter in fresh_model.parameters()}
            fresh_optimizer_ids = {
                id(parameter)
                for group in fresh_optimizer.param_groups
                for parameter in group["params"]
            }
            target_device = torch.device(device)

            def is_on_target_device(parameter: torch.nn.Parameter) -> bool:
                return (
                    parameter.device.type == target_device.type
                    and (target_device.index is None or parameter.device.index == target_device.index)
                )

            source_optimizer_bound = source_optimizer_ids == source_parameter_ids and all(
                is_on_target_device(parameter)
                for group in optimizer.param_groups for parameter in group["params"]
            )
            fresh_optimizer_bound = fresh_optimizer_ids == fresh_parameter_ids and all(
                is_on_target_device(parameter)
                for group in fresh_optimizer.param_groups for parameter in group["params"]
            )
            if not all((model_exact, optimizer_exact, scheduler_exact, stream_exact, curriculum_exact, scaler_exact,
                        source_optimizer_bound, fresh_optimizer_bound)):
                raise RuntimeError(
                    "Resume diverged from uninterrupted execution: "
                    f"model={model_exact}, optimizer={optimizer_exact}, scheduler={scheduler_exact}, "
                    f"data_stream={stream_exact}, curriculum={curriculum_exact}, scaler={scaler_exact}, "
                    f"source_optimizer_bound={source_optimizer_bound}, "
                    f"fresh_optimizer_bound={fresh_optimizer_bound}"
                )

            result = {
                "recovery_test_passed": True,
                "device": device,
                "precision": precision,
                "architecture": dict(architecture or {"dimension": 32, "layers": 1, "heads": 4, "feedforward_multiplier": 2}),
                "model_parameter_count": sum(parameter.numel() for parameter in fresh_model.parameters()),
                "test_run_id": test_run_id,
                "checkpoint_id": checkpoint_id,
                "saved_step": int(downloaded["step"]),
                "resumed_step": int(restored["step"]) + 1,
                "checks": {
                    "remote_upload_and_manifest_verified": True,
                    "fresh_runtime_download_and_integrity_verified": True,
                    "model_weights_match_uninterrupted_run": model_exact,
                    "optimizer_state_matches_uninterrupted_run": optimizer_exact,
                    "scheduler_state_matches_uninterrupted_run": scheduler_exact,
                    "data_stream_position_and_rng_match": stream_exact,
                    "curriculum_state_matches": curriculum_exact,
                    "gradient_scaler_state_matches": scaler_exact,
                    "source_optimizer_bound_to_model_on_target_device": source_optimizer_bound,
                    "resumed_optimizer_bound_to_model_on_target_device": fresh_optimizer_bound,
                },
                "training_status_database_written": False,
                "production_run_id_touched": False,
                "real_training_started": False,
            }
            return result
    finally:
        if checkpoint_id is not None:
            checkpoint_prefix = f"{owner_id}/{test_run_id}/{checkpoint_id}"
            children = storage.list_objects(bucket, checkpoint_prefix, limit=1000)
            paths = []
            for item in children:
                name = str(item.get("name", "")).strip("/")
                if not name:
                    continue
                object_path = name if name.startswith(checkpoint_prefix + "/") else f"{checkpoint_prefix}/{name}"
                if object_path.startswith(checkpoint_prefix + "/"):
                    paths.append(object_path)
            if paths:
                storage.remove(bucket, paths)
            remaining = storage.list_objects(
                bucket,
                checkpoint_prefix,
                limit=1000,
            )
            if remaining:
                raise RuntimeError("Temporary recovery-test checkpoint cleanup could not be verified")
            if result is not None:
                result["temporary_storage_cleanup_verified"] = True
