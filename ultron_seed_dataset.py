"""Safely inventory the approved ULTRON seed theorem dataset.

This module reads task metadata and hashes files. It never imports or executes
code from the downloaded dataset.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tomllib
from pathlib import Path
from typing import Any


DATASET_ID = "bkhtmm/openai-math-lemmas"
DATASET_REVISION = "d7056fd31c19fd1a0aed0a0bc3e99026d412b2ca"
EXPECTED_TASK_FILES = (
    "task.toml",
    "instruction.md",
    "LICENSE",
    "NOTICE",
    "tests/task.json",
    "tests/Challenge.lean",
)
EXPECTED_TASK_COUNT = 47


class DatasetScanError(ValueError):
    """Raised when the seed dataset layout or metadata is invalid."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative_files(task_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(task_dir.rglob("*")):
        if path.is_symlink():
            raise DatasetScanError(f"Symbolic links are not allowed: {path}")
        if path.is_file():
            files.append(path)
    return files


def scan_dataset(
    dataset_root: str | Path,
    expected_count: int = EXPECTED_TASK_COUNT,
) -> dict[str, Any]:
    """Return a deterministic metadata and SHA-256 inventory for task folders."""
    root = Path(dataset_root).expanduser().resolve()
    tasks_root = root / "tasks"

    if not root.is_dir():
        raise DatasetScanError(f"Dataset directory does not exist: {root}")
    if not tasks_root.is_dir():
        raise DatasetScanError("Dataset is missing its 'tasks' directory")
    if isinstance(expected_count, bool) or expected_count < 1:
        raise DatasetScanError("expected_count must be a positive integer")

    task_dirs = sorted(path for path in tasks_root.iterdir() if path.is_dir())
    if len(task_dirs) != expected_count:
        raise DatasetScanError(
            f"Expected {expected_count} task folders, found {len(task_dirs)}"
        )

    tasks: list[dict[str, Any]] = []
    seen_task_names: set[str] = set()
    seen_theorems: set[str] = set()

    for task_dir in task_dirs:
        if task_dir.is_symlink():
            raise DatasetScanError(f"Task folder cannot be a symbolic link: {task_dir}")

        files = _safe_relative_files(task_dir)
        relative_names = {path.relative_to(task_dir).as_posix() for path in files}
        missing = sorted(set(EXPECTED_TASK_FILES) - relative_names)
        if missing:
            raise DatasetScanError(
                f"{task_dir.name} is missing required files: {', '.join(missing)}"
            )

        task_toml_path = task_dir / "task.toml"
        task_data = tomllib.loads(task_toml_path.read_text(encoding="utf-8"))
        task_section = task_data.get("task")
        metadata = task_data.get("metadata")
        if not isinstance(task_section, dict) or not isinstance(metadata, dict):
            raise DatasetScanError(f"{task_dir.name}: task/metadata tables are missing")

        task_name = task_section.get("name")
        theorems = task_data.get("metadata", {}).get("theorems")
        if not isinstance(task_name, str) or not task_name.strip():
            raise DatasetScanError(f"{task_dir.name}: task.name is missing")
        if task_name in seen_task_names:
            raise DatasetScanError(f"Duplicate task name: {task_name}")
        if not isinstance(theorems, list) or not theorems or not all(
            isinstance(item, str) and item.strip() for item in theorems
        ):
            raise DatasetScanError(f"{task_dir.name}: metadata.theorems is invalid")

        if len(set(theorems)) != len(theorems):
            raise DatasetScanError(f"{task_dir.name}: repeated theorem identifier within task")
        duplicate_theorems = seen_theorems.intersection(theorems)
        if duplicate_theorems:
            raise DatasetScanError(
                f"{task_dir.name}: duplicate theorem identifiers: "
                + ", ".join(sorted(duplicate_theorems))
            )

        task_json = json.loads((task_dir / "tests/task.json").read_text(encoding="utf-8"))
        if not isinstance(task_json, dict):
            raise DatasetScanError(f"{task_dir.name}: tests/task.json must contain an object")
        comparator = task_json.get("comparator")
        comparator_theorems = comparator.get("theorem_names") if isinstance(comparator, dict) else None
        if comparator_theorems != theorems:
            raise DatasetScanError(
                f"{task_dir.name}: task.toml theorem list does not match tests/task.json"
            )

        seen_task_names.add(task_name)
        seen_theorems.update(theorems)
        file_records = [
            {
                "path": path.relative_to(task_dir).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in files
        ]
        tasks.append(
            {
                "folder": task_dir.name,
                "name": task_name,
                "version": task_section.get("version"),
                "description": task_section.get("description", ""),
                "theorems": theorems,
                "source": metadata.get("source"),
                "source_commit": metadata.get("source_commit"),
                "source_license": metadata.get("source_license"),
                "source_notice": metadata.get("source_notice"),
                "hugging_face_revision": metadata.get("hf_revision"),
                "validation_status": metadata.get("validation_status", "unknown"),
                "file_count": len(file_records),
                "files": file_records,
            }
        )

    return {
        "schema_version": 1,
        "dataset": DATASET_ID,
        "dataset_revision": DATASET_REVISION,
        "expected_task_count": expected_count,
        "task_count": len(tasks),
        "scan_status": "structure_validated",
        "proof_status": "not_checked",
        "execution_performed": False,
        "tasks": tasks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inventory a local ULTRON seed dataset without running its code."
    )
    parser.add_argument("dataset_root", help="Path to the downloaded dataset folder")
    parser.add_argument(
        "--expected-count",
        type=int,
        default=EXPECTED_TASK_COUNT,
        help=f"Expected number of task folders (default: {EXPECTED_TASK_COUNT})",
    )
    parser.add_argument(
        "--output",
        default="dataset/seed/manifest.json",
        help="Where to write the inventory JSON (default: dataset/seed/manifest.json)",
    )
    args = parser.parse_args(argv)

    try:
        manifest = scan_dataset(args.dataset_root, args.expected_count)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(output.name + ".tmp")
        temporary.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, output)
    except (DatasetScanError, OSError, tomllib.TOMLDecodeError, json.JSONDecodeError) as exc:
        print(f"Dataset scan failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Scanned {manifest['task_count']} task folders. "
        f"Inventory: {output}. Proofs were not executed or verified."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
