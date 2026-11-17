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
SECRET_ENV_NAMES = ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY")


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
    if constraints.get("ai_apis_allowed") is not False:
        errors.append("AI APIs must remain disabled")
    if constraints.get("pretrained_models_allowed") is not False:
        errors.append("Pretrained models must remain disabled")
    if constraints.get("pretrained_weights_allowed") is not False:
        errors.append("Pretrained weights must remain disabled")
    if constraints.get("initialize_model_from_random_weights") is not True:
        errors.append("Model must initialize from random weights")
    if constraints.get("paid_compute_allowed") is not False:
        errors.append("Paid compute must remain disabled")

    server_items = servers.get("servers", [])
    server_ids = [item.get("id") for item in server_items]
    if len(server_ids) != len(set(server_ids)):
        errors.append("Server IDs must be unique")
    if server_items and any(item.get("order") != index for index, item in enumerate(server_items, 1)):
        errors.append("Server order must be sequential")

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
            "automatic_start": server.get("automatic_start", {}).get("capability") if server else "no",
            "session_limit_hours": (
                server.get("limits", {}).get("session_limit_hours")
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
        context_length=settings.get("context_length", 128),
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
    topics = curriculum.get("initial_topics", [])
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ultron-train", description="ULTRON portable training preflight")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--servers", default="servers.json")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--model-summary", action="store_true")
    parser.add_argument("--data-smoke-test", action="store_true")
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

    if not report["configuration_valid"]:
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
