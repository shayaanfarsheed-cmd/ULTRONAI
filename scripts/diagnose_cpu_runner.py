#!/usr/bin/env python3
"""Read-only GitHub Actions runner diagnostics; never imports the training loop."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import shutil
from pathlib import Path
from typing import Any


def _read_meminfo() -> dict[str, int]:
    values: dict[str, int] = {}
    path = Path("/proc/meminfo")
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].isdigit():
            values[parts[0].rstrip(":")] = int(parts[1]) * 1024
    return values


def _read_cgroup_memory() -> dict[str, int | None]:
    result: dict[str, int | None] = {}
    for key, path in (
        ("limit_bytes", Path("/sys/fs/cgroup/memory.max")),
        ("current_bytes", Path("/sys/fs/cgroup/memory.current")),
    ):
        try:
            raw = path.read_text(encoding="utf-8").strip()
            result[key] = None if raw == "max" else int(raw)
        except (OSError, ValueError):
            result[key] = None
    return result


def _cpu_model() -> str | None:
    path = Path("/proc/cpuinfo")
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.lower().startswith(("model name", "hardware")) and ":" in line:
            return line.split(":", 1)[1].strip()
    return None


def collect_report(torch_module: Any = None) -> dict[str, Any]:
    if torch_module is None:
        import torch as torch_module  # type: ignore[no-redef]

    memory = _read_meminfo()
    disk = shutil.disk_usage("/")
    package_versions: dict[str, str | None] = {}
    for package in ("numpy", "safetensors", "huggingface-hub"):
        try:
            package_versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            package_versions[package] = None

    cpu_count = os.cpu_count() or 0
    memory_total = memory.get("MemTotal", 0)
    torch_cpu_threads = int(torch_module.get_num_threads())
    cuda_available = bool(torch_module.cuda.is_available())
    checks = {
        "cpu_visible": cpu_count >= 1,
        "memory_visible": memory_total > 0,
        "disk_available": disk.free > 0,
        "pytorch_imported": bool(getattr(torch_module, "__version__", "")),
        "pytorch_cpu_threads": torch_cpu_threads >= 1,
        "cuda_not_required": True,
    }
    return {
        "schema_version": 1,
        "diagnostic": "ultron-github-actions-cpu",
        "status": "passed" if all(checks.values()) else "failed",
        "training_started": False,
        "model_weights_modified": False,
        "persistent_checkpoints_touched": False,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "runner": {
            "github_actions": os.environ.get("GITHUB_ACTIONS") == "true",
            "runner_os": os.environ.get("RUNNER_OS"),
            "runner_arch": os.environ.get("RUNNER_ARCH"),
        },
        "cpu": {"logical_count": cpu_count, "model": _cpu_model()},
        "memory": {
            "total_bytes": memory_total,
            "available_bytes": memory.get("MemAvailable"),
            "cgroup": _read_cgroup_memory(),
        },
        "disk_root": {
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
        },
        "pytorch": {
            "version": str(torch_module.__version__),
            "cpu_threads": torch_cpu_threads,
            "cuda_available": cuda_available,
            "device": "cpu",
        },
        "packages": package_versions,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("compute-diagnostic.json"))
    args = parser.parse_args()
    report = collect_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
