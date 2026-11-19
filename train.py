from __future__ import annotations

import argparse
import importlib
import json
import os
import platform as host_platform
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


PLATFORM_IDS = ("kaggle", "google_colab", "lightning_ai", "github_actions", "other")
SECRET_ENV_NAMES = ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "SUPABASE_OWNER_ID", "HF_TOKEN", "HF_REPO_ID")


def load_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{file_path.name} must contain a JSON object")
    return value


def detect_platform(
    environ: Mapping[str, str] | None = None,
    module_names: Sequence[str] | None = None,
    existing_paths: Sequence[str] | None = None,
) -> str:
    env = dict(os.environ if environ is None else environ)
    modules = set(sys.modules if module_names is None else module_names)
    paths = list(existing_paths) if existing_paths is not None else ["/kaggle", "/content", "/teamspace"]
    path_exists = {str(Path(item)): Path(item).exists() for item in paths}

    if env.get("GITHUB_ACTIONS", "").lower() == "true":
        return "github_actions"

    if any(env.get(key) for key in ("KAGGLE_KERNEL_RUN_TYPE", "KAGGLE_URL_BASE", "KAGGLE_KERNEL_INTEGRATION")):
        return "kaggle"
    if path_exists.get("/kaggle", False):
        return "kaggle"

    if any(env.get(key) for key in ("COLAB_RELEASE_TAG", "COLAB_GPU")) or "google.colab" in modules:
        return "google_colab"

    if any(env.get(key) for key in ("LIGHTNING_CLOUD_SPACE_ID", "LIGHTNING_TEAMSPACE", "LIGHTNING_USERNAME")):
        return "lightning_ai"
    if path_exists.get("/teamspace", False):
        return "lightning_ai"

    return "other"


def _load_torch() -> Any | None:
    try:
        return importlib.import_module("torch")
    except Exception:
        return None


def _device_details(torch_module: Any | None) -> dict[str, Any]:
    if torch_module is None or torch_module is False:
        return {"device": "cpu", "accelerator_name": None, "torch_available": False, "bf16_supported": False}

    try:
        cuda = getattr(torch_module, "cuda", None)
        if cuda is not None and callable(getattr(cuda, "is_available", None)) and cuda.is_available():
            try:
                name = cuda.get_device_name(0)
            except Exception:
                name = "CUDA GPU"
            try:
                bf16 = bool(cuda.is_bf16_supported())
            except Exception:
                bf16 = False
            return {"device": "cuda", "accelerator_name": name, "torch_available": True, "bf16_supported": bf16}
    except Exception:
        pass

    try:
        backends = getattr(torch_module, "backends", None)
        mps = getattr(backends, "mps", None) if backends is not None else None
        if mps is not None and callable(getattr(mps, "is_available", None)) and mps.is_available():
            return {"device": "mps", "accelerator_name": "Apple Metal", "torch_available": True, "bf16_supported": False}
    except Exception:
        pass

    return {"device": "cpu", "accelerator_name": None, "torch_available": True, "bf16_supported": False}


def resolve_runtime_settings(
    config: Mapping[str, Any],
    platform_id: str,
    torch_module: Any | None = None,
) -> dict[str, Any]:
    if platform_id not in PLATFORM_IDS:
        platform_id = "other"

    profiles = {
        "kaggle": {"gpu_batch_size": 32, "cpu_batch_size": 8, "workers": 2, "cpu_threads": 4},
        "google_colab": {"gpu_batch_size": 32, "cpu_batch_size": 8, "workers": 2, "cpu_threads": 4},
        "lightning_ai": {"gpu_batch_size": 32, "cpu_batch_size": 8, "workers": 2, "cpu_threads": 4},
        "github_actions": {"gpu_batch_size": 8, "cpu_batch_size": 8, "workers": 0, "cpu_threads": 4},
        "other": {"gpu_batch_size": 8, "cpu_batch_size": 4, "workers": 0, "cpu_threads": 2},
    }
    profile = profiles[platform_id]
    torch_probe = _load_torch() if torch_module is None else torch_module
    hardware = _device_details(torch_probe)
    device = hardware["device"]

    runtime_config = config.get("runtime", {})
    batch_size_setting = runtime_config.get("batch_size", "auto")
    worker_setting = runtime_config.get("dataloader_workers", "auto")
    precision_setting = runtime_config.get("mixed_precision", "auto")

    if device == "cuda":
        batch_size = profile["gpu_batch_size"]
        precision = "bf16" if hardware["bf16_supported"] else "fp16"
    elif device == "mps":
        batch_size = profile["cpu_batch_size"]
        precision = "none"
    else:
        batch_size = profile["cpu_batch_size"]
        precision = "none"

    if isinstance(batch_size_setting, int) and not isinstance(batch_size_setting, bool) and batch_size_setting > 0:
        batch_size = batch_size_setting

    workers = profile["workers"]
    if isinstance(worker_setting, int) and not isinstance(worker_setting, bool) and worker_setting >= 0:
        workers = worker_setting

    if precision_setting != "auto":
        precision = str(precision_setting)

    return {
        "platform": platform_id,
        "device": device,
        "accelerator_name": hardware["accelerator_name"],
        "torch_available": hardware["torch_available"],
        "batch_size": batch_size,
        "dataloader_workers": workers,
        "mixed_precision": precision,
        "cpu_threads": profile["cpu_threads"],
        "sequence_length": config.get("training", {}).get("sequence_length", 128),
    }


def validate_project_config(config: Mapping[str, Any], servers: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    constraints = config.get("non_negotiable_constraints", {})
    if not isinstance(constraints, Mapping):
        constraints = {}
        errors.append("non_negotiable_constraints must be an object")
    for key, expected, message in (
        ("ai_apis_allowed", False, "AI APIs must remain disabled"),
        ("pretrained_models_allowed", False, "Pretrained models must remain disabled"),
        ("pretrained_weights_allowed", False, "Pretrained weights must remain disabled"),
        ("initialize_model_from_random_weights", True, "Model must initialize from random weights"),
        ("paid_compute_allowed", False, "Paid compute must remain disabled"),
    ):
        if constraints.get(key) is not expected:
            errors.append(message)

    access = config.get("access", {})
    if not isinstance(access, Mapping):
        access = {}
        errors.append("access must be an object")
    owner_limit = access.get("owner_account_limit")
    if type(owner_limit) is not int or owner_limit != 1:
        errors.append("ULTRON must have exactly one owner account")
    if access.get("public_self_registration_enabled") is not False:
        errors.append("Public self-registration must remain disabled")
    if access.get("owner_authentication_required_for_private_operations") is not True:
        errors.append("Private operations must require verified owner authentication")
    if access.get("guest_mode_enabled") is not True:
        errors.append("Guest Mode must remain enabled")

    guest_permissions = access.get("guest_permissions", [])
    if not isinstance(guest_permissions, list) or any(not isinstance(item, str) for item in guest_permissions):
        errors.append("Guest permissions must be a list of permission names")
    elif set(guest_permissions) != {"public_dashboard", "public_mathematics_information"}:
        errors.append("Guest Mode must expose public information only")

    required_guest_denials = {
        "private_training_history", "private_checkpoints",
        "device_pairing", "remote_training_controls",
    }
    denied_permissions = access.get("guest_denied_permissions", [])
    if not isinstance(denied_permissions, list) or any(not isinstance(item, str) for item in denied_permissions):
        errors.append("Guest denied permissions must be a list of permission names")
    elif not required_guest_denials.issubset(set(denied_permissions)):
        errors.append("Guest Mode must deny all private training and device operations")

    expected_enforcement = {
        "windows": "job_objects",
        "linux": "cgroups_v2",
        "macos": "unverified_disabled",
        "ipados": "monitoring_only",
        "ios": "monitoring_only",
        "android": "monitoring_only",
        "browser": "monitoring_only",
    }
    local_training = config.get("local_training", {})
    if not isinstance(local_training, Mapping):
        local_training = {}
        errors.append("local_training must be an object")
    enforcement = local_training.get("platform_enforcement", {})
    if not isinstance(enforcement, Mapping):
        enforcement = {}
        errors.append("platform_enforcement must be an object")
    for platform_name, expected_policy in expected_enforcement.items():
        if enforcement.get(platform_name) != expected_policy:
            errors.append(
                f"Invalid resource-enforcement policy for {platform_name}: "
                f"expected {expected_policy!r}"
            )

    runtime = config.get("runtime", {})
    if not isinstance(runtime, Mapping):
        runtime = {}
        errors.append("runtime must be an object")
    supported_platforms = runtime.get("supported_platforms", [])
    if not isinstance(supported_platforms, list) or any(not isinstance(item, str) for item in supported_platforms):
        errors.append("runtime.supported_platforms must be a list of platform IDs")
    elif "kaggle" not in supported_platforms:
        errors.append("Kaggle must be listed as a supported manual runtime")

    switching = config.get("switching", {})
    if not isinstance(switching, Mapping):
        switching = {}
        errors.append("switching must be an object")
    allowlist = switching.get("platform_allowlist", [])
    if not isinstance(allowlist, list) or any(not isinstance(item, str) for item in allowlist):
        errors.append("switching.platform_allowlist must be a list of platform IDs")
    elif "kaggle" in allowlist:
        errors.append("Kaggle must remain excluded from automatic provider selection")

    manual_only = switching.get("manual_only_platforms", [])
    if not isinstance(manual_only, list) or any(not isinstance(item, str) for item in manual_only):
        errors.append("switching.manual_only_platforms must be a list of platform IDs")
    elif "kaggle" not in manual_only:
        errors.append("Kaggle must be explicitly marked as manual-only")

    server_items = servers.get("servers", [])
    if not isinstance(server_items, list):
        server_items = []
        errors.append("servers must be a list")
    server_ids = [item.get("id") for item in server_items if isinstance(item, Mapping)]
    if len(server_ids) != len(server_items):
        errors.append("Every server entry must be an object")
    if len(server_ids) != len(set(server_ids)):
        errors.append("Server IDs must be unique")
    if server_items and any(
        not isinstance(item, Mapping) or item.get("order") != index
        for index, item in enumerate(server_items, 1)
    ):
        errors.append("Server order must be sequential")

    kaggle_entries = [
        item for item in server_items
        if isinstance(item, Mapping) and item.get("id") == "kaggle"
    ]
    if len(kaggle_entries) != 1:
        errors.append("Kaggle must exist exactly once in the server registry")
    elif (
        kaggle_entries[0].get("enabled") is not True
        or kaggle_entries[0].get("manual_only") is not True
        or str(kaggle_entries[0].get("automatic_start", "no")).lower() not in {"no", "false", "disabled"}
        or kaggle_entries[0].get("automatic_start_enabled_by_default") is not False
    ):
        errors.append("Kaggle must be enabled for manual use only; automatic starts must remain disabled")

    fallback = config.get("server_rotation", {}).get("fallback_server_id")
    if fallback and fallback not in server_ids:
        errors.append("Configured CPU fallback is missing from servers.json")

    return errors

def build_preflight_report(
    config: Mapping[str, Any],
    servers: Mapping[str, Any],
    environ: Mapping[str, str] | None = None,
    module_names: Sequence[str] | None = None,
    existing_paths: Sequence[str] | None = None,
    torch_module: Any | None = None,
) -> dict[str, Any]:
    env = dict(os.environ if environ is None else environ)
    platform_id = detect_platform(env, module_names, existing_paths)
    runtime = resolve_runtime_settings(config, platform_id, torch_module)
    server = next((item for item in servers.get("servers", []) if item.get("provider") == platform_id or item.get("id") == platform_id), None)
    errors = validate_project_config(config, servers)

    return {
        "project": config.get("project", {}).get("name", "ULTRON"),
        "phase": "stage_2_preflight",
        "platform": platform_id,
        "host_os": host_platform.system(),
        "python_version": sys.version.split()[0],
        "runtime": runtime,
        "server": {
            "id": server.get("id") if server else None,
            "name": server.get("name") if server else "Unrecognized platform",
            "current_status": server.get("current_status") if server else "unknown",
            "automatic_start": (
                server.get("automatic_start", "no").get("capability", "no")
                if isinstance(server.get("automatic_start"), dict)
                else str(server.get("automatic_start", "no"))
            ) if server else "no",
            "session_limit_hours": (
                server.get("limits", {}).get("session_limit_hours")
                or server.get("limits", {}).get("free_studio_restart_hours")
                or server.get("limits", {}).get("job_execution_limit_hours")
            ) if server else None,
        },
        "secret_presence": {name: bool(env.get(name)) for name in SECRET_ENV_NAMES},
        "configuration_valid": not errors,
        "configuration_errors": errors,
        "training_started": False,
        "message": "Preflight only. The training engine is added in the next implementation stage."
    }


def build_model_summary(config: Mapping[str, Any]) -> dict[str, Any]:
    from ultron_model import CharTokenizer, ULTRONTransformer

    settings = config.get("model", {})
    tokenizer = CharTokenizer()
    if settings.get("vocabulary_size", tokenizer.vocab_size) != tokenizer.vocab_size:
        raise ValueError("Configured vocabulary size does not match the project tokenizer")

    model = ULTRONTransformer(
        vocab_size=tokenizer.vocab_size,
        context_length=settings.get("context_length", 192),
        dimension=settings.get("embedding_dimension", 256),
        layers=settings.get("transformer_layers", 5),
        heads=settings.get("attention_heads", 8),
        feedforward_multiplier=settings.get("feedforward_multiplier", 4),
        dropout=settings.get("dropout", 0.1),
    )
    parameters = model.parameter_count()
    target = config.get("project", {}).get("target_parameter_count", {})
    minimum = target.get("minimum", settings.get("parameter_count_minimum", 3000000))
    maximum = target.get("maximum", settings.get("parameter_count_maximum", 5000000))
    expected = settings.get("expected_parameter_count")
    return {
        "architecture": model.architecture(),
        "parameter_count": parameters,
        "within_target_range": minimum <= parameters <= maximum,
        "matches_expected_count": expected is None or expected == parameters,
        "target_minimum": minimum,
        "target_maximum": maximum,
    }


def build_data_smoke_report(config: Mapping[str, Any]) -> dict[str, Any]:
    from ultron_data import generate_dataset
    from ultron_verify import verify_example_detailed

    training = config.get("training", {})
    curriculum = training.get("curriculum", {})
    from ultron_data import SUPPORTED_TOPICS
    topics = list(SUPPORTED_TOPICS)
    seed = int(training.get("seed", 20261117))
    examples = generate_dataset(100, seed=seed, split="train", topics=topics)
    topic_counts: dict[str, int] = {}
    for example in examples:
        valid, reason = verify_example_detailed(example)
        if not valid:
            raise ValueError(f"Independent verification failed: {reason}")
        topic_counts[example["topic"]] = topic_counts.get(example["topic"], 0) + 1

    return {
        "generated_examples": len(examples),
        "independently_verified_examples": len(examples),
        "topics_covered": len(topic_counts),
        "topic_counts": topic_counts,
        "seed": seed,
        "training_started": False,
    }


def build_checkpoint_smoke_report(config: Mapping[str, Any]) -> dict[str, Any]:
    import tempfile
    import torch
    from ultron_checkpoint import LocalCheckpointStore
    from ultron_model import CharTokenizer, ULTRONTransformer

    settings = config.get("model", {})
    tokenizer = CharTokenizer()
    model = ULTRONTransformer(
        vocab_size=tokenizer.vocab_size,
        context_length=settings.get("context_length", 192),
        dimension=settings.get("embedding_dimension", 256),
        layers=settings.get("transformer_layers", 5),
        heads=settings.get("attention_heads", 8),
        feedforward_multiplier=settings.get("feedforward_multiplier", 4),
        dropout=settings.get("dropout", 0.1),
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(config.get("training", {}).get("learning_rate", 0.0003)))
    tokens = torch.randint(0, tokenizer.vocab_size, (1, 8))
    _, loss = model(tokens, tokens)
    loss.backward()
    optimizer.step()
    state = {
        "step": 1,
        "current_topic": "whole_number_arithmetic",
        "difficulty": 1,
        "data_position": 8,
        "seed": int(config.get("training", {}).get("seed", 20261117)),
        "lease_holder": "local-checkpoint-smoke-test",
        "fencing_token": 1,
    }
    maximum_mb = float(config.get("persistence", {}).get("max_single_storage_object_mb", 45))
    with tempfile.TemporaryDirectory() as directory:
        store = LocalCheckpointStore(
            directory,
            keep_last=int(config.get("persistence", {}).get("keep_last_valid_checkpoints", 3)),
            maximum_file_bytes=int(maximum_mb * 1_000_000),
        )
        manifest = store.save(model, optimizer, state)
        expected = {name: tensor.detach().clone() for name, tensor in model.state_dict().items()}
        with torch.no_grad():
            for parameter in model.parameters():
                parameter.add_(1)
        restored = store.load_latest(model, optimizer, restore_rng=False)
        if restored is None:
            raise RuntimeError("Checkpoint could not be restored")
        exact = all(torch.equal(model.state_dict()[name], tensor) for name, tensor in expected.items())
        folder = Path(directory) / manifest["checkpoint_id"]
        sizes = {item.name: item.stat().st_size for item in folder.iterdir() if item.is_file()}
        if not exact:
            raise RuntimeError("Restored model weights do not match the saved weights")
        return {
            "checkpoint_verified": store.verify_checkpoint(manifest["checkpoint_id"])[0],
            "restored_exactly": exact,
            "step": restored["step"],
            "component_sizes_bytes": sizes,
            "largest_component_mb": round(max(sizes.values()) / 1_000_000, 3),
            "total_checkpoint_mb": round(sum(sizes.values()) / 1_000_000, 3),
            "training_started": False,
        }


def build_training_smoke_report(config: Mapping[str, Any]) -> dict[str, Any]:
    import torch
    from ultron_data import generate_dataset
    from ultron_model import CharTokenizer, ULTRONTransformer
    from ultron_training import CurriculumController, MathBatchStream, make_grad_scaler, train_steps

    seed = int(config.get("training", {}).get("seed", 20261117))
    torch.manual_seed(seed)
    platform_id = detect_platform()
    runtime = resolve_runtime_settings(config, platform_id, torch_module=torch)
    device = runtime["device"]
    torch.set_num_threads(int(runtime["cpu_threads"]))

    model_settings = config.get("model", {})
    tokenizer = CharTokenizer()
    model = ULTRONTransformer(
        vocab_size=tokenizer.vocab_size,
        context_length=model_settings.get("context_length", 192),
        dimension=model_settings.get("embedding_dimension", 256),
        layers=model_settings.get("transformer_layers", 5),
        heads=model_settings.get("attention_heads", 8),
        feedforward_multiplier=model_settings.get("feedforward_multiplier", 4),
        dropout=model_settings.get("dropout", 0.1),
    )
    optimizer_settings = config.get("training", {})
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(optimizer_settings.get("learning_rate", 0.0003)),
        weight_decay=float(optimizer_settings.get("weight_decay", 0.1)),
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=max(1, int(optimizer_settings.get("maximum_training_steps", 100000))),
    )
    curriculum_settings = optimizer_settings.get("curriculum", {})
    curriculum = CurriculumController(
        curriculum_settings.get("stages", []),
        mastery_accuracy=float(curriculum_settings.get("unlock_mastery_accuracy", 0.9)),
        consecutive_evaluations=int(curriculum_settings.get("consecutive_evaluations_required", 3)),
        require_held_out=bool(curriculum_settings.get("held_out_evaluation_required", True)),
    )
    topics = curriculum.current_topics
    examples = generate_dataset(32, seed=seed, split="train", topics=topics)
    stream = MathBatchStream(
        examples,
        tokenizer,
        context_length=int(model_settings.get("context_length", 192)),
        batch_size=min(4, int(runtime["batch_size"])),
        seed=seed,
    )
    precision = runtime["mixed_precision"] if device == "cuda" else "none"
    scaler = make_grad_scaler(device, precision)
    result = train_steps(
        model,
        optimizer,
        stream,
        steps=2,
        device=device,
        precision=precision,
        gradient_clip_norm=float(optimizer_settings.get("gradient_clip_norm", 1.0)),
        scheduler=scheduler,
        scaler=scaler,
    )
    return {
        "training_smoke_passed": result["step"] == 2 and result["last_loss"] is not None,
        "training_started": True,
        "step": result["step"],
        "last_loss": result["last_loss"],
        "device": device,
        "platform": platform_id,
        "curriculum_stage": curriculum.current_stage,
        "topics_used": topics,
        "data_position": result["data_position"],
        "data_epoch": result["data_epoch"],
        "parameter_count": model.parameter_count(),
        "learning_rate_after_smoke": optimizer.param_groups[0]["lr"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ultron-train", description="ULTRON portable training preflight")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--servers", default="servers.json")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--model-summary", action="store_true")
    parser.add_argument("--data-smoke-test", action="store_true")
    parser.add_argument("--checkpoint-smoke-test", action="store_true")
    parser.add_argument("--training-smoke-test", action="store_true")
    parser.add_argument("--train", action="store_true")
    args = parser.parse_args(argv)

    config = load_json(args.config)
    servers = load_json(args.servers)
    report = build_preflight_report(config, servers)
    print(json.dumps(report, indent=2))

    if args.model_summary:
        summary = build_model_summary(config)
        print(json.dumps(summary, indent=2))
        if not summary["within_target_range"] or not summary["matches_expected_count"]:
            return 3

    if args.data_smoke_test:
        data_report = build_data_smoke_report(config)
        print(json.dumps(data_report, indent=2))
        if data_report["generated_examples"] != data_report["independently_verified_examples"]:
            return 4

    if args.checkpoint_smoke_test:
        checkpoint_report = build_checkpoint_smoke_report(config)
        print(json.dumps(checkpoint_report, indent=2))
        if not checkpoint_report["checkpoint_verified"] or not checkpoint_report["restored_exactly"]:
            return 5

    if args.training_smoke_test:
        training_report = build_training_smoke_report(config)
        print(json.dumps(training_report, indent=2))
        if not training_report["training_smoke_passed"]:
            return 6

    if not report["configuration_valid"]:
        return 2

    if args.train:
        from ultron_session import run_training_session
        result = run_training_session(config, servers)
        print(json.dumps(result, indent=2))
        if result.get("state") in {"finished", "handoff_needed", "paused", "waiting_for_lease"}:
            return 0
        return 7

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
