"""Local-only dummy worker lifecycle for ULTRON.

This module deliberately does not import the model/training engine, contact a
network, or expose an HTTP/API control surface. It is a lifecycle prototype,
not a training launcher.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any


ACTIVE_STATES = {"STARTING", "RUNNING", "STOP_REQUESTED", "CHECKPOINTING"}
TERMINAL_STATES = {"STOPPED", "FAILED", "COMPLETED"}


class RuntimeErrorState(RuntimeError):
    pass


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeErrorState("Runtime state must be a JSON object.")
    return value


def _write_status(root: Path, run_id: str, state: str, **details: Any) -> None:
    _atomic_json(root / "status.json", {
        "schema": 1, "run_id": run_id, "state": state,
        "updated_at": time.time(), **details,
    })


def _checkpoint(root: Path, run_id: str, completed_batches: int) -> dict[str, Any]:
    payload = {
        "schema": 1, "run_id": run_id,
        "completed_batches": completed_batches,
        "worker": "dummy-only",
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    record = {**payload, "sha256": hashlib.sha256(encoded).hexdigest()}
    _atomic_json(root / "checkpoint.json", record)
    verified = _read_json(root / "checkpoint.json")
    digest_payload = {k: v for k, v in verified.items() if k != "sha256"}
    digest = hashlib.sha256(json.dumps(digest_payload, sort_keys=True).encode("utf-8")).hexdigest()
    if digest != verified.get("sha256") or verified.get("run_id") != run_id:
        raise RuntimeErrorState("Checkpoint verification failed.")
    return verified


def verify_checkpoint(root: Path) -> dict[str, Any]:
    record = _read_json(root / "checkpoint.json")
    digest_payload = {k: v for k, v in record.items() if k != "sha256"}
    digest = hashlib.sha256(json.dumps(digest_payload, sort_keys=True).encode("utf-8")).hexdigest()
    if record.get("schema") != 1 or digest != record.get("sha256"):
        raise RuntimeErrorState("Checkpoint is corrupt or has an unsupported schema.")
    if record.get("worker") != "dummy-only" or not isinstance(record.get("completed_batches"), int):
        raise RuntimeErrorState("Checkpoint contents are invalid.")
    return record


def _worker(root: Path, run_id: str, batches: int, delay: float) -> int:
    completed = 0
    try:
        _write_status(root, run_id, "RUNNING", completed_batches=completed, total_batches=batches)
        while completed < batches:
            stop_file = root / "stop.request"
            if stop_file.exists():
                try:
                    request = _read_json(stop_file)
                except Exception:
                    request = {}
                if request.get("run_id") != run_id:
                    raise RuntimeErrorState("Stop request does not match the active run.")
                _write_status(root, run_id, "STOP_REQUESTED", completed_batches=completed)
                _write_status(root, run_id, "CHECKPOINTING", completed_batches=completed)
                _checkpoint(root, run_id, completed)
                _write_status(root, run_id, "STOPPED", completed_batches=completed,
                              checkpoint="checkpoint.json", stop_reason="local_request")
                return 0
            time.sleep(delay)
            completed += 1
            _write_status(root, run_id, "RUNNING", completed_batches=completed, total_batches=batches)
        _write_status(root, run_id, "CHECKPOINTING", completed_batches=completed)
        _checkpoint(root, run_id, completed)
        _write_status(root, run_id, "COMPLETED", completed_batches=completed,
                      checkpoint="checkpoint.json")
        return 0
    except Exception as exc:
        _write_status(root, run_id, "FAILED", completed_batches=completed,
                      error_type=type(exc).__name__)
        return 1


class LocalDummyRuntime:
    """Explicit local process manager. No remote-control or training methods."""

    def __init__(self, directory: str | Path):
        self.root = Path(directory).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = self.root / "runtime.lock"
        self.status_file = self.root / "status.json"
        self.process_file = self.root / "process.json"

    def start(self, *, batches: int = 20, delay: float = 0.1,
              require_hard_ram_cap: bool = False) -> str:
        if require_hard_ram_cap:
            raise RuntimeErrorState(
                "Start refused: this prototype has no verified OS-level RAM enforcement."
            )
        if not isinstance(batches, int) or batches < 1 or batches > 10000:
            raise ValueError("batches must be an integer from 1 to 10000")
        if not isinstance(delay, (int, float)) or delay < 0 or delay > 5:
            raise ValueError("delay must be between 0 and 5 seconds")
        if self.lock.exists():
            try:
                existing = _read_json(self.status_file)
            except Exception:
                raise RuntimeErrorState("A runtime lock exists; inspect it before recovery.")
            if existing.get("state") in ACTIVE_STATES:
                raise RuntimeErrorState("A worker is already active.")
            raise RuntimeErrorState("A stale runtime lock exists; manual recovery is required.")
        run_id = uuid.uuid4().hex
        fd = os.open(self.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"run_id": run_id, "pid": os.getpid()}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        (self.root / "stop.request").unlink(missing_ok=True)
        _write_status(self.root, run_id, "STARTING", completed_batches=0, total_batches=batches)
        command = [sys.executable, str(Path(__file__).resolve()), "--worker",
                   str(self.root), run_id, str(batches), str(float(delay))]
        try:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       close_fds=True)
            process_identity = {"run_id": run_id, "pid": process.pid}
            start_ticks = _proc_start_ticks(process.pid)
            if start_ticks is not None:
                process_identity["start_ticks"] = start_ticks
            _atomic_json(self.process_file, process_identity)
            return run_id
        except Exception:
            _write_status(self.root, run_id, "FAILED", error_type="ProcessStartError")
            self.lock.unlink(missing_ok=True)
            raise

    def request_stop(self) -> str:
        status = _read_json(self.status_file)
        if status.get("state") in TERMINAL_STATES:
            return str(status["state"])
        if status.get("state") not in ACTIVE_STATES:
            raise RuntimeErrorState("No active local worker is available to stop.")
        _atomic_json(self.root / "stop.request", {
            "run_id": status.get("run_id"), "requested_at": time.time(),
            "source": "local_cli",
        })
        # The worker owns lifecycle status writes. This prevents a race in
        # which the worker finishes checkpointing before this process updates status.
        return "STOP_REQUESTED"

    def status(self) -> dict[str, Any]:
        status = _read_json(self.status_file)
        process_info = {}
        try:
            process_info = _read_json(self.process_file)
        except (FileNotFoundError, json.JSONDecodeError, RuntimeErrorState):
            pass
        pid = process_info.get("pid")
        identity_matches = (
            process_info.get("run_id") == status.get("run_id")
            and isinstance(pid, int) and pid > 0
        )
        if status.get("state") in TERMINAL_STATES:
            # Missing/mismatched identity is unknown, not proof of process exit.
            if not identity_matches:
                status["process_exited"] = False
            elif _pid_exists(pid, process_info.get("start_ticks")):
                status["process_exited"] = False
            else:
                status["process_exited"] = True
                self.lock.unlink(missing_ok=True)
        else:
            status["process_exited"] = False
        return status


def _proc_start_ticks(pid: int) -> int | None:
    """Read Linux process start-time ticks to distinguish PID reuse."""
    try:
        stat_text = (Path("/proc") / str(pid) / "stat").read_text(encoding="utf-8")
        fields_after_comm = stat_text.rsplit(")", 1)[1].split()
        # Field 22 (starttime); fields_after_comm begins at field 3 (state).
        return int(fields_after_comm[19])
    except (OSError, ValueError, IndexError):
        return None


def _pid_exists(pid: int, expected_start_ticks: int | None = None) -> bool:
    """Return whether this process identity is executing; Linux zombies have exited."""
    if pid <= 0:
        return False
    proc_stat = Path("/proc") / str(pid) / "stat"
    try:
        stat_text = proc_stat.read_text(encoding="utf-8")
    except OSError:
        stat_text = None
    if stat_text is not None:
        try:
            fields_after_comm = stat_text.rsplit(")", 1)[1].split()
            process_state = fields_after_comm[0]
            actual_start_ticks = int(fields_after_comm[19])
            if expected_start_ticks is not None and actual_start_ticks != expected_start_ticks:
                return False
            return process_state not in {"Z", "X"}
        except (ValueError, IndexError):
            return True
    # Without procfs there is no portable PID-reuse check. Signal-zero is
    # conservative: unknown/permission-denied means still potentially alive.
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def main() -> int:
    parser = argparse.ArgumentParser(description="ULTRON local dummy-worker prototype")
    parser.add_argument("--worker", nargs=4, metavar=("ROOT", "RUN_ID", "BATCHES", "DELAY"))
    parser.add_argument("--directory", default=".ultron-local")
    parser.add_argument("command", nargs="?", choices=("start", "stop", "status", "verify"))
    args = parser.parse_args()
    if args.worker:
        root, run_id, batches, delay = args.worker
        return _worker(Path(root), run_id, int(batches), float(delay))
    runtime = LocalDummyRuntime(args.directory)
    if args.command == "start":
        print(json.dumps({"run_id": runtime.start()}, sort_keys=True))
    elif args.command == "stop":
        print(runtime.request_stop())
    elif args.command == "status":
        print(json.dumps(runtime.status(), sort_keys=True))
    elif args.command == "verify":
        print(json.dumps(verify_checkpoint(runtime.root), sort_keys=True))
    else:
        parser.print_help()
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
