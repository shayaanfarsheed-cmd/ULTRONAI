from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import statistics
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch

from train import resolve_runtime_settings
from ultron_data import generate_dataset
from ultron_model import CharTokenizer, ULTRONTransformer
from ultron_training import MathBatchStream, train_one_batch


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("Project config must be a JSON object")
    return value


def build_model(config: dict[str, Any], tokenizer: CharTokenizer) -> ULTRONTransformer:
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
        raise RuntimeError(
            f"Benchmark model has {model.parameter_count()} parameters; config requires {expected}"
        )
    return model


def run_benchmark(
    config: dict[str, Any],
    examples_count: int = 256,
    steps: int = 3,
    warmup: int = 1,
) -> dict[str, Any]:
    if not 32 <= examples_count <= 1024:
        raise ValueError("examples_count must be between 32 and 1024")
    if not 1 <= steps <= 10 or not 0 <= warmup <= 3:
        raise ValueError("steps must be 1..10 and warmup must be 0..3")

    runtime = resolve_runtime_settings(config, "github_actions", torch_module=torch)
    if runtime["device"] != "cpu":
        raise RuntimeError("This diagnostic is specifically for the GitHub Actions CPU profile")
    cpu_threads = max(1, int(runtime["cpu_threads"]))
    torch.set_num_threads(cpu_threads)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass

    seed = int(config.get("training", {}).get("seed", 20261117))
    model_settings = config.get("model", {})
    context_length = int(model_settings.get("context_length", 192))
    curriculum = config.get("training", {}).get("curriculum", {})
    stages = curriculum.get("stages", [])
    if not stages or not stages[0].get("topics"):
        raise RuntimeError("The first curriculum stage must define at least one topic")
    topics = [str(topic) for topic in stages[0]["topics"]]

    # Uses ULTRON's own deterministic generator and independent per-example verifier.
    data_generation_started = time.perf_counter()
    examples = generate_dataset(
        examples_count,
        seed=seed,
        split="train",
        topics=topics,
    )
    data_generation_seconds = time.perf_counter() - data_generation_started
    tokenizer = CharTokenizer()
    data_encoding_started = time.perf_counter()
    stream = MathBatchStream(
        examples,
        tokenizer,
        context_length=context_length,
        batch_size=int(runtime["batch_size"]),
        seed=seed,
        shuffle=True,
    )
    dataset_encoding_seconds = time.perf_counter() - data_encoding_started
    model = build_model(config, tokenizer)
    parameter_count = model.parameter_count()
    model.to("cpu")

    training = config.get("training", {})
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(training.get("learning_rate", 0.0003)),
        weight_decay=float(training.get("weight_decay", 0.1)),
        foreach=bool(training.get("adamw_foreach", False)),
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=max(1, int(training.get("maximum_training_steps", 100000))),
    )

    durations: list[float] = []
    losses: list[float] = []
    observed_shapes: list[list[int]] = []
    total_target_tokens = 0

    for index in range(warmup + steps):
        # Match a production iteration: include stream selection and batch collation.
        started = time.perf_counter()
        batch = stream.next_batch(tokenizer.stoi[" "])
        observed_shapes.append(list(batch["input_ids"].shape))
        total_target_tokens += int((batch["labels"] != -100).sum().item())
        loss = train_one_batch(
            model,
            optimizer,
            batch,
            "cpu",
            precision="none",
            gradient_clip_norm=float(training.get("gradient_clip_norm", 1.0)),
        )
        if not torch.isfinite(torch.tensor(loss)):
            raise RuntimeError("Benchmark produced a non-finite loss")
        scheduler.step()
        elapsed = time.perf_counter() - started
        if index >= warmup:
            durations.append(elapsed)
            losses.append(loss)

    measured_seconds = sum(durations)
    return {
        "benchmark": "ultron_generated_math_data_cpu",
        "production_training_started": False,
        "production_checkpoint_written": False,
        "remote_services_contacted": False,
        "platform": platform.platform(),
        "torch_version": torch.__version__,
        "logical_cpus": os.cpu_count(),
        "device": "cpu",
        "cpu_threads": cpu_threads,
        "adamw_foreach": bool(training.get("adamw_foreach", False)),
        "model_parameter_count": parameter_count,
        "model_context_length": context_length,
        "batch_size": int(runtime["batch_size"]),
        "generated_examples": len(examples),
        "data_generation_seconds": data_generation_seconds,
        "dataset_encoding_seconds": dataset_encoding_seconds,
        "step_timing_scope": "batch_selection_and_collation_plus_forward_backward_optimizer_scheduler",
        "topics": topics,
        "verified_data_generator": "ultron_data.generate_dataset -> ultron_verify.verify_example",
        "warmup_steps": warmup,
        "measured_steps": steps,
        "batch_shapes_input_ids": observed_shapes,
        "target_tokens_including_warmup": total_target_tokens,
        "steps_per_second": steps / measured_seconds if measured_seconds else 0.0,
        "median_step_seconds": statistics.median(durations),
        "mean_step_seconds": statistics.mean(durations),
        "mean_loss": statistics.mean(losses),
        "losses_finite": all(torch.isfinite(torch.tensor(value)).item() for value in losses),
        "peak_process_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        "note": (
            "Bounded in-memory diagnostic updates only. It uses ULTRON-generated verified examples, "
            "the configured model and CPU runtime profile; it does not create a production run or checkpoint."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bounded benchmark using ULTRON-generated verified math data; never starts a production session."
    )
    parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    parser.add_argument("--examples", type=int, default=256)
    parser.add_argument("--steps", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=1)
    args = parser.parse_args()
    report = run_benchmark(load_config(args.config), args.examples, args.steps, args.warmup)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
