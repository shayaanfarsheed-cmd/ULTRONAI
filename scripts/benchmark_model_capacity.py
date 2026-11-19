from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark_math_data import load_config, run_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bounded, isolated CPU capacity test for candidate ULTRON model widths/depths."
    )
    parser.add_argument("--dimension", type=int, required=True)
    parser.add_argument("--layers", type=int, required=True)
    parser.add_argument("--heads", type=int, required=True)
    parser.add_argument("--examples", type=int, default=256)
    parser.add_argument("--steps", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if args.dimension % args.heads:
        raise SystemExit("--dimension must be divisible by --heads")
    config: dict[str, Any] = load_config(ROOT / "config.json")
    settings = config["model"]
    settings["embedding_dimension"] = args.dimension
    settings["transformer_layers"] = args.layers
    settings["attention_heads"] = args.heads
    settings.pop("expected_parameter_count", None)

    report = run_benchmark(
        config,
        examples_count=args.examples,
        steps=args.steps,
        warmup=args.warmup,
    )
    parameters = int(report["model_parameter_count"])
    model_bytes = parameters * 4
    adam_moment_bytes = parameters * 8
    object_limit = int(
        float(config.get("persistence", {}).get("max_single_storage_object_mb", 45))
        * 1_000_000
    )
    report.update(
        {
            "candidate_architecture": {
                "dimension": args.dimension,
                "layers": args.layers,
                "heads": args.heads,
                "feedforward_multiplier": int(settings.get("feedforward_multiplier", 4)),
            },
            "estimated_model_weights_bytes_fp32": model_bytes,
            "estimated_adam_moments_bytes_fp32": adam_moment_bytes,
            "estimated_checkpoint_payload_bytes_excluding_metadata": model_bytes + adam_moment_bytes,
            "current_storage_object_limit_bytes": object_limit,
            "model_component_fits_current_object_limit": model_bytes <= object_limit,
            "optimizer_component_fits_current_object_limit": adam_moment_bytes <= object_limit,
            "checkpoint_sharding_required_for_current_storage_limit": (
                model_bytes > object_limit or adam_moment_bytes > object_limit
            ),
        }
    )
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
