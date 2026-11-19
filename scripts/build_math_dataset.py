from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ultron_data import SUPPORTED_TOPICS, generate_dataset
from ultron_dataset_quality import audit_dataset, require_dataset_pass

DEFAULT_COUNTS = {"train": 12_000, "validation": 1_500, "test": 1_500}
DATASET_SCHEMA_VERSION = 1


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_dataset(output_dir: str | Path, seed: int = 20261119, counts: dict[str, int] | None = None) -> dict[str, Any]:
    selected_counts = dict(DEFAULT_COUNTS if counts is None else counts)
    if set(selected_counts) != {"train", "validation", "test"}:
        raise ValueError("Counts must define train, validation and test")
    if any(type(value) is not int or value < 1 for value in selected_counts.values()):
        raise ValueError("Every split count must be a positive integer")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")

    splits: dict[str, list[dict[str, Any]]] = {}
    for split in ("train", "validation", "test"):
        splits[split] = generate_dataset(
            selected_counts[split],
            seed=seed,
            split=split,
            topics=SUPPORTED_TOPICS,
        )

    combined = [example for split in ("train", "validation", "test") for example in splits[split]]
    quality = audit_dataset(
        combined,
        required_splits=("train", "validation", "test"),
        require_all_topics=SUPPORTED_TOPICS,
        minimum_examples=sum(selected_counts.values()),
    )
    require_dataset_pass(quality)

    # Each split must contain every topic and all three difficulty levels.
    for split, examples in splits.items():
        topic_counts = Counter(item["topic"] for item in examples)
        difficulty_counts = Counter(item["difficulty"] for item in examples)
        missing_topics = sorted(set(SUPPORTED_TOPICS).difference(topic_counts))
        missing_difficulties = sorted({1, 2, 3}.difference(difficulty_counts))
        if missing_topics or missing_difficulties:
            raise RuntimeError(
                f"{split} coverage incomplete: missing_topics={missing_topics}, "
                f"missing_difficulties={missing_difficulties}"
            )
        minimum_difficulty_count = max(1, len(examples) // 30)
        if any(difficulty_counts[level] < minimum_difficulty_count for level in (1, 2, 3)):
            raise RuntimeError(f"{split} difficulty distribution is too imbalanced: {dict(difficulty_counts)}")

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    file_records: dict[str, dict[str, Any]] = {}
    for split, examples in splits.items():
        path = destination / f"{split}.jsonl"
        with path.open("wb") as stream:
            for example in examples:
                stream.write(_canonical_json(example))
        file_records[path.name] = {
            "example_count": len(examples),
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }

    # Rebuild a bounded deterministic slice independently to catch seed drift.
    probe_count = min(256, selected_counts["train"])
    probe_a = generate_dataset(probe_count, seed=seed, split="train", topics=SUPPORTED_TOPICS)
    probe_b = generate_dataset(probe_count, seed=seed, split="train", topics=SUPPORTED_TOPICS)
    reproducibility_verified = probe_a == probe_b
    if not reproducibility_verified:
        raise RuntimeError("Fixed-seed reproducibility check failed")

    manifest = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "dataset_id": "ultron-math-foundation-v1",
        "generator": "ultron_data.generate_dataset",
        "generator_version": "2.0.0",
        "verifier": "ultron_verify.verify_example_detailed",
        "quality_auditor_version": quality["auditor_version"],
        "seed": seed,
        "topics": list(SUPPORTED_TOPICS),
        "split_counts": selected_counts,
        "total_examples": len(combined),
        "files": file_records,
        "quality_report": quality,
        "reproducibility": {
            "fixed_seed_probe_count": probe_count,
            "verified": reproducibility_verified,
            "scope": "two independent builds of the same bounded train slice",
        },
        "training_started": False,
        "model_weights_changed": False,
    }
    manifest_path = destination / "manifest.json"
    manifest_path.write_bytes(_canonical_json(manifest))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and independently audit ULTRON's synthetic mathematics dataset.")
    parser.add_argument("--output-dir", default="build/math-dataset")
    parser.add_argument("--seed", type=int, default=20261119)
    parser.add_argument("--train-count", type=int, default=DEFAULT_COUNTS["train"])
    parser.add_argument("--validation-count", type=int, default=DEFAULT_COUNTS["validation"])
    parser.add_argument("--test-count", type=int, default=DEFAULT_COUNTS["test"])
    args = parser.parse_args()
    counts = {
        "train": args.train_count,
        "validation": args.validation_count,
        "test": args.test_count,
    }
    manifest = build_dataset(args.output_dir, seed=args.seed, counts=counts)
    print(json.dumps({
        "status": "passed",
        "dataset_id": manifest["dataset_id"],
        "total_examples": manifest["total_examples"],
        "split_counts": manifest["split_counts"],
        "topic_count": len(manifest["topics"]),
        "dataset_quality": manifest["quality_report"]["status"],
        "fixed_seed_reproducibility": manifest["reproducibility"]["verified"],
        "training_started": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
