from __future__ import annotations

import hashlib
import json
import os
import random
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

import torch
from safetensors.torch import load_file, save_file


class CheckpointError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError:
        pass


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    with path.open("w", encoding="utf-8") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def _encode_value(value: Any, tensors: dict[str, torch.Tensor], prefix: str) -> Any:
    if isinstance(value, torch.Tensor):
        key = f"tensor_{len(tensors):06d}"
        tensors[key] = value.detach().cpu().contiguous()
        return {"__tensor__": key}
    if isinstance(value, dict):
        return {
            "__dict__": [
                [_encode_value(key, tensors, prefix), _encode_value(item, tensors, prefix)]
                for key, item in value.items()
            ]
        }
    if isinstance(value, tuple):
        return {"__tuple__": [_encode_value(item, tensors, prefix) for item in value]}
    if isinstance(value, list):
        return {"__list__": [_encode_value(item, tensors, prefix) for item in value]}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported checkpoint metadata type: {type(value).__name__}")


def _decode_value(value: Any, tensors: Mapping[str, torch.Tensor]) -> Any:
    if isinstance(value, dict) and set(value) == {"__tensor__"}:
        return tensors[value["__tensor__"]]
    if isinstance(value, dict) and set(value) == {"__dict__"}:
        return {
            _decode_value(key, tensors): _decode_value(item, tensors)
            for key, item in value["__dict__"]
        }
    if isinstance(value, dict) and set(value) == {"__tuple__"}:
        return tuple(_decode_value(item, tensors) for item in value["__tuple__"])
    if isinstance(value, dict) and set(value) == {"__list__"}:
        return [_decode_value(item, tensors) for item in value["__list__"]]
    return value


def _to_tuple(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_to_tuple(item) for item in value)
    return value


def _numpy_rng_state() -> dict[str, Any] | None:
    try:
        import numpy as np
        state = np.random.get_state()
        return {
            "algorithm": state[0],
            "keys": state[1].tolist(),
            "position": int(state[2]),
            "has_gauss": int(state[3]),
            "cached_gaussian": float(state[4]),
        }
    except Exception:
        return None


def _restore_numpy_rng(state: Mapping[str, Any] | None) -> None:
    if state is None:
        return
    try:
        import numpy as np
        np.random.set_state((
            state["algorithm"],
            np.asarray(state["keys"], dtype=np.uint32),
            int(state["position"]),
            int(state["has_gauss"]),
            float(state["cached_gaussian"]),
        ))
    except Exception as error:
        raise CheckpointError("Could not restore NumPy random state") from error


class LocalCheckpointStore:
    def __init__(
        self,
        root: str | Path,
        keep_last: int = 3,
        maximum_file_bytes: int = 45_000_000,
    ) -> None:
        if keep_last < 1 or maximum_file_bytes < 1:
            raise ValueError("Checkpoint retention and file-size limit must be positive")
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.keep_last = keep_last
        self.maximum_file_bytes = maximum_file_bytes
        self.pointer_path = self.root / "latest.json"

    def _checkpoint_path(self, checkpoint_id: str) -> Path:
        if not checkpoint_id.startswith("ckpt-") or Path(checkpoint_id).name != checkpoint_id:
            raise CheckpointError("Invalid checkpoint identifier")
        return self.root / checkpoint_id

    def _capture_rng(self) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
        tensors = {"torch_cpu": torch.get_rng_state().cpu().contiguous()}
        if torch.cuda.is_available():
            for index, state in enumerate(torch.cuda.get_rng_state_all()):
                tensors[f"torch_cuda_{index}"] = state.cpu().contiguous()
        metadata = {
            "python": random.getstate(),
            "numpy": _numpy_rng_state(),
            "cuda_device_count": len([key for key in tensors if key.startswith("torch_cuda_")]),
        }
        return tensors, _encode_value(metadata, {}, "rng")

    def save(
        self,
        model: torch.nn.Module,
        optimizer: torch.optim.Optimizer,
        state: Mapping[str, Any],
        scheduler: Any | None = None,
        fault_hook: Callable[[str, Path], None] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(state.get("step"), int) or state["step"] < 0:
            raise CheckpointError("Checkpoint state requires a non-negative integer step")
        if not isinstance(state.get("lease_holder"), str) or not state["lease_holder"]:
            raise CheckpointError("Checkpoint state requires a lease holder")
        if not isinstance(state.get("fencing_token"), int) or state["fencing_token"] < 1:
            raise CheckpointError("Checkpoint state requires a positive fencing token")

        step = state["step"]
        current_manifest = None
        if self.pointer_path.is_file():
            try:
                current_pointer = json.loads(self.pointer_path.read_text(encoding="utf-8"))
                valid, candidate = self.verify_checkpoint(current_pointer.get("checkpoint_id", ""))
                if valid and candidate is not None and _sha256(self._checkpoint_path(candidate["checkpoint_id"]) / "manifest.json") == current_pointer.get("manifest_sha256"):
                    current_manifest = candidate
            except Exception:
                current_manifest = None
        if current_manifest is None:
            valid_manifests = self.list_valid_checkpoints()
            current_manifest = valid_manifests[0] if valid_manifests else None
        if current_manifest is not None and step < current_manifest["step"]:
            raise CheckpointError("Refusing to move the latest checkpoint step backwards")
        if current_manifest is not None and state["fencing_token"] < current_manifest["fencing_token"]:
            raise CheckpointError("Refusing a checkpoint from an older fencing token")
        if current_manifest is not None and state["lease_holder"] != current_manifest["lease_holder"] and state["fencing_token"] == current_manifest["fencing_token"]:
            raise CheckpointError("A new lease holder must use a newer fencing token")

        checkpoint_id = f"ckpt-{step:012d}-{uuid.uuid4().hex[:8]}"
        temporary = self.root / f"{checkpoint_id}.tmp"
        final = self._checkpoint_path(checkpoint_id)
        temporary.mkdir(parents=False, exist_ok=False)

        model_tensors = {
            name: tensor.detach().cpu().contiguous()
            for name, tensor in model.state_dict().items()
        }
        save_file(model_tensors, temporary / "model.safetensors", metadata={"format": "ULTRON model state"})

        optimizer_tensors: dict[str, torch.Tensor] = {}
        optimizer_encoded = _encode_value(optimizer.state_dict(), optimizer_tensors, "optimizer")
        scheduler_encoded = None
        if scheduler is not None:
            scheduler_encoded = _encode_value(scheduler.state_dict(), optimizer_tensors, "scheduler")
        if optimizer_tensors:
            save_file(optimizer_tensors, temporary / "optimizer.safetensors", metadata={"format": "ULTRON optimizer state"})
        else:
            save_file({"empty": torch.zeros(1, dtype=torch.uint8)}, temporary / "optimizer.safetensors", metadata={"format": "ULTRON optimizer state"})

        rng_tensors, rng_metadata = self._capture_rng()
        save_file(rng_tensors, temporary / "rng.safetensors", metadata={"format": "ULTRON RNG state"})

        metadata = {
            "schema_version": 1,
            "checkpoint_id": checkpoint_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "state": dict(state),
            "model_architecture": getattr(model, "architecture", lambda: {})(),
            "optimizer_state": optimizer_encoded,
            "scheduler_state": scheduler_encoded,
            "rng_state": rng_metadata,
        }
        _write_json(temporary / "state.json", metadata)

        if fault_hook:
            fault_hook("after_artifacts", temporary)

        file_entries: dict[str, dict[str, Any]] = {}
        for name in ("model.safetensors", "optimizer.safetensors", "rng.safetensors", "state.json"):
            path = temporary / name
            _fsync_file(path)
            size = path.stat().st_size
            if size > self.maximum_file_bytes:
                raise CheckpointError(f"Checkpoint component exceeds size limit: {name}")
            file_entries[name] = {"size_bytes": size, "sha256": _sha256(path)}

        manifest = {
            "schema_version": 1,
            "checkpoint_id": checkpoint_id,
            "step": step,
            "lease_holder": state["lease_holder"],
            "fencing_token": state["fencing_token"],
            "files": file_entries,
        }
        _write_json(temporary / "manifest.json", manifest)
        _fsync_file(temporary / "manifest.json")
        manifest_hash = _sha256(temporary / "manifest.json")
        _fsync_directory(temporary)

        if fault_hook:
            fault_hook("after_manifest", temporary)

        os.replace(temporary, final)
        _fsync_directory(self.root)

        if fault_hook:
            fault_hook("after_rename", final)

        pointer = {
            "checkpoint_id": checkpoint_id,
            "step": step,
            "manifest_sha256": manifest_hash,
        }
        pointer_temp = self.root / f"latest-{uuid.uuid4().hex}.tmp"
        _write_json(pointer_temp, pointer)
        os.replace(pointer_temp, self.pointer_path)
        _fsync_directory(self.root)

        if fault_hook:
            fault_hook("after_pointer", final)

        self.prune()
        return manifest

    def verify_checkpoint(self, checkpoint_id: str) -> tuple[bool, dict[str, Any] | None]:
        try:
            folder = self._checkpoint_path(checkpoint_id)
            manifest_path = folder / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("checkpoint_id") != checkpoint_id or not isinstance(manifest.get("files"), dict):
                return False, None
            for name, entry in manifest["files"].items():
                if Path(name).name != name:
                    return False, None
                file_path = folder / name
                if not file_path.is_file() or file_path.stat().st_size != entry.get("size_bytes"):
                    return False, None
                if _sha256(file_path) != entry.get("sha256"):
                    return False, None
            return True, manifest
        except Exception:
            return False, None

    def list_valid_checkpoints(self) -> list[dict[str, Any]]:
        valid = []
        for folder in self.root.glob("ckpt-*"):
            if not folder.is_dir() or folder.name.endswith(".tmp"):
                continue
            ok, manifest = self.verify_checkpoint(folder.name)
            if ok and manifest is not None:
                valid.append(manifest)
        return sorted(valid, key=lambda item: (item["step"], item["checkpoint_id"]), reverse=True)

    def prune(self) -> list[str]:
        valid = self.list_valid_checkpoints()
        removed = []
        for manifest in valid[self.keep_last:]:
            folder = self._checkpoint_path(manifest["checkpoint_id"])
            shutil.rmtree(folder)
            removed.append(manifest["checkpoint_id"])
        return removed

    def _candidate_ids(self) -> list[str]:
        candidates = []
        if self.pointer_path.is_file():
            try:
                pointer = json.loads(self.pointer_path.read_text(encoding="utf-8"))
                checkpoint_id = pointer.get("checkpoint_id")
                ok, _ = self.verify_checkpoint(checkpoint_id)
                if ok and _sha256(self._checkpoint_path(checkpoint_id) / "manifest.json") == pointer.get("manifest_sha256"):
                    candidates.append(checkpoint_id)
            except Exception:
                pass
        for manifest in self.list_valid_checkpoints():
            checkpoint_id = manifest["checkpoint_id"]
            if checkpoint_id not in candidates:
                candidates.append(checkpoint_id)
        return candidates

    def load_latest(
        self,
        model: torch.nn.Module,
        optimizer: torch.optim.Optimizer | None = None,
        scheduler: Any | None = None,
        restore_rng: bool = True,
        map_location: str | torch.device = "cpu",
    ) -> dict[str, Any] | None:
        for checkpoint_id in self._candidate_ids():
            ok, manifest = self.verify_checkpoint(checkpoint_id)
            if not ok or manifest is None:
                continue
            folder = self._checkpoint_path(checkpoint_id)
            try:
                model_state = load_file(folder / "model.safetensors", device=str(map_location))
                model.load_state_dict(model_state, strict=True)

                metadata = json.loads((folder / "state.json").read_text(encoding="utf-8"))
                optimizer_tensors = load_file(folder / "optimizer.safetensors", device="cpu")
                if optimizer is not None:
                    optimizer_state = _decode_value(metadata["optimizer_state"], optimizer_tensors)
                    optimizer.load_state_dict(optimizer_state)
                if scheduler is not None and metadata.get("scheduler_state") is not None:
                    scheduler_state = _decode_value(metadata["scheduler_state"], optimizer_tensors)
                    scheduler.load_state_dict(scheduler_state)

                if restore_rng:
                    rng_tensors = load_file(folder / "rng.safetensors", device="cpu")
                    rng_state = _decode_value(metadata["rng_state"], {})
                    random.setstate(_to_tuple(rng_state["python"]))
                    _restore_numpy_rng(rng_state.get("numpy"))
                    torch.set_rng_state(rng_tensors["torch_cpu"].cpu())
                    cuda_states = [
                        rng_tensors[f"torch_cuda_{index}"]
                        for index in range(int(rng_state.get("cuda_device_count", 0)))
                        if f"torch_cuda_{index}" in rng_tensors
                    ]
                    if cuda_states and torch.cuda.is_available():
                        available_devices = torch.cuda.device_count()
                        for index in range(min(available_devices, len(cuda_states))):
                            torch.cuda.set_rng_state(cuda_states[index], device=index)

                pointer = {
                    "checkpoint_id": checkpoint_id,
                    "step": manifest["step"],
                    "manifest_sha256": _sha256(folder / "manifest.json"),
                }
                pointer_temp = self.root / f"latest-{uuid.uuid4().hex}.tmp"
                _write_json(pointer_temp, pointer)
                os.replace(pointer_temp, self.pointer_path)
                _fsync_directory(self.root)

                return {
                    "checkpoint_id": checkpoint_id,
                    "step": manifest["step"],
                    "state": metadata["state"],
                    "manifest": manifest,
                }
            except Exception:
                continue
        return None
