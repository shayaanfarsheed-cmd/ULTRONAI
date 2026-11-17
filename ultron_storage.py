from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from ultron_checkpoint import CheckpointError, LocalCheckpointStore
from ultron_supabase import TrainingControlAPI


class SupabaseStorageError(RuntimeError):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class SupabaseStorageClient:
    def __init__(
        self,
        project_url: str,
        api_key: str,
        timeout_seconds: int = 60,
        opener: Any | None = None,
    ) -> None:
        if not project_url.startswith("https://"):
            raise ValueError("Supabase project URL must use HTTPS")
        if not api_key:
            raise ValueError("Supabase API key is required")
        self.project_url = project_url.rstrip("/")
        self._api_key = api_key
        self.timeout_seconds = timeout_seconds
        self._opener = opener or urllib.request.urlopen

    def __repr__(self) -> str:
        return f"SupabaseStorageClient(project_url={self.project_url!r}, api_key=[redacted])"

    def _request(
        self,
        method: str,
        path: str,
        body: bytes | Mapping[str, Any] | None = None,
        content_type: str | None = None,
        upsert: bool | None = None,
    ) -> bytes:
        url = f"{self.project_url}/storage/v1/{path.lstrip('/')}"
        headers = {
            "apikey": self._api_key,
            "Authorization": f"Bearer {self._api_key}",
        }
        payload: bytes | None
        if isinstance(body, Mapping):
            payload = json.dumps(body, separators=(",", ":"), allow_nan=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        else:
            payload = body
            if content_type:
                headers["Content-Type"] = content_type
        if upsert is not None:
            headers["x-upsert"] = "true" if upsert else "false"
        request = urllib.request.Request(url, data=payload, headers=headers, method=method.upper())
        try:
            with self._opener(request, timeout=self.timeout_seconds) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            raw = error.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(raw)
                message = str(detail.get("message") or detail.get("error") or "Storage request failed")
            except Exception:
                message = "Storage request failed"
            raise SupabaseStorageError(error.code, message) from None
        except urllib.error.URLError as error:
            raise SupabaseStorageError(0, f"Storage connection failed: {error.reason}") from None

    @staticmethod
    def _object_path(bucket: str, path: str) -> str:
        return f"object/{urllib.parse.quote(bucket, safe='')}/{urllib.parse.quote(path.lstrip('/'), safe='/')}"

    def upload(self, bucket: str, path: str, content: bytes, content_type: str) -> bool:
        endpoint = self._object_path(bucket, path)
        try:
            self._request("POST", endpoint, body=content, content_type=content_type, upsert=False)
            return False
        except SupabaseStorageError as error:
            if error.status_code != 409:
                raise
            existing = self.download(bucket, path)
            if _sha256_bytes(existing) != _sha256_bytes(content):
                raise SupabaseStorageError(409, "An object already exists at this path with different content")
            return True

    def download(self, bucket: str, path: str) -> bytes:
        endpoint = f"object/authenticated/{urllib.parse.quote(bucket, safe='')}/{urllib.parse.quote(path.lstrip('/'), safe='/')}"
        return self._request("GET", endpoint)

    def list_objects(self, bucket: str, prefix: str, limit: int = 1000, offset: int = 0) -> list[dict[str, Any]]:
        endpoint = f"object/list/{urllib.parse.quote(bucket, safe='')}"
        raw = self._request(
            "POST",
            endpoint,
            body={
                "prefix": prefix.strip("/"),
                "limit": int(limit),
                "offset": int(offset),
                "sortBy": {"column": "name", "order": "asc"},
            },
        )
        return json.loads(raw.decode("utf-8")) if raw else []

    def remove(self, bucket: str, paths: Sequence[str]) -> list[dict[str, Any]]:
        if not paths:
            return []
        endpoint = f"object/{urllib.parse.quote(bucket, safe='')}"
        raw = self._request("DELETE", endpoint, body={"prefixes": list(paths)})
        return json.loads(raw.decode("utf-8")) if raw else []


class RemoteCheckpointStore:
    COMPONENTS = (
        "model.safetensors",
        "optimizer.safetensors",
        "rng.safetensors",
        "state.json",
        "manifest.json",
    )

    def __init__(
        self,
        storage: SupabaseStorageClient,
        bucket: str = "checkpoints",
        keep_last: int = 3,
        maximum_file_bytes: int = 45_000_000,
    ) -> None:
        if keep_last < 1:
            raise ValueError("Remote checkpoint retention must be positive")
        self.storage = storage
        self.bucket = bucket
        self.keep_last = keep_last
        self.maximum_file_bytes = maximum_file_bytes

    @staticmethod
    def _prefix(owner_id: str, run_id: str) -> str:
        if "/" in owner_id or "/" in run_id:
            raise ValueError("Owner and run identifiers must be path-safe")
        return f"{owner_id}/{run_id}"

    def upload_checkpoint(
        self,
        local_store: LocalCheckpointStore,
        checkpoint_id: str,
        owner_id: str,
        run_id: str,
    ) -> dict[str, Any]:
        valid, manifest = local_store.verify_checkpoint(checkpoint_id)
        if not valid or manifest is None:
            raise CheckpointError("Refusing to upload an invalid local checkpoint")
        prefix = self._prefix(owner_id, run_id)
        folder = local_store.root / checkpoint_id
        component_sizes: dict[str, int] = {}
        for name in self.COMPONENTS:
            content = (folder / name).read_bytes()
            if len(content) > self.maximum_file_bytes:
                raise SupabaseStorageError(413, f"Checkpoint component exceeds the configured limit: {name}")
            content_type = "application/json" if name.endswith(".json") else "application/octet-stream"
            object_path = f"{prefix}/{checkpoint_id}/{name}"
            self.storage.upload(self.bucket, object_path, content, content_type)
            component_sizes[name] = len(content)
        remote_manifest = self.storage.download(self.bucket, f"{prefix}/{checkpoint_id}/manifest.json")
        local_manifest = (folder / "manifest.json").read_bytes()
        manifest_hash = _sha256_bytes(local_manifest)
        if _sha256_bytes(remote_manifest) != manifest_hash:
            raise SupabaseStorageError(500, "Remote checkpoint manifest verification failed")
        receipt = {
            "schema_version": 1,
            "checkpoint_id": checkpoint_id,
            "manifest_sha256": manifest_hash,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "files": manifest["files"],
        }
        receipt_bytes = json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        receipt_path = f"{prefix}/{checkpoint_id}/upload_receipt.json"
        self.storage.upload(self.bucket, receipt_path, receipt_bytes, "application/json")
        if _sha256_bytes(self.storage.download(self.bucket, receipt_path)) != _sha256_bytes(receipt_bytes):
            raise SupabaseStorageError(500, "Remote checkpoint upload receipt verification failed")
        return {
            "checkpoint_id": checkpoint_id,
            "object_prefix": f"{prefix}/{checkpoint_id}",
            "verified": True,
            "verification_mode": "local_hashes_and_remote_upload_receipt; component_hashes_rechecked_on_resume",
            "component_sizes_bytes": component_sizes,
            "total_size_bytes": sum(component_sizes.values()),
            "step": int(manifest["step"]),
            "fencing_token": int(manifest["fencing_token"]),
        }

    def download_checkpoint(
        self,
        owner_id: str,
        run_id: str,
        checkpoint_id: str,
        local_store: LocalCheckpointStore,
    ) -> dict[str, Any]:
        prefix = self._prefix(owner_id, run_id)
        files = {}
        for name in self.COMPONENTS:
            object_path = f"{prefix}/{checkpoint_id}/{name}"
            files[name] = self.storage.download(self.bucket, object_path)
        return local_store.import_checkpoint(checkpoint_id, files)

    def verify_remote_checkpoint(self, owner_id: str, run_id: str, checkpoint_id: str) -> dict[str, Any]:
        prefix = self._prefix(owner_id, run_id)
        manifest_data = self.storage.download(self.bucket, f"{prefix}/{checkpoint_id}/manifest.json")
        manifest = json.loads(manifest_data.decode("utf-8"))
        if manifest.get("checkpoint_id") != checkpoint_id:
            raise CheckpointError("Remote manifest checkpoint ID does not match its path")
        receipt_data = self.storage.download(self.bucket, f"{prefix}/{checkpoint_id}/upload_receipt.json")
        receipt = json.loads(receipt_data.decode("utf-8"))
        if receipt.get("checkpoint_id") != checkpoint_id or receipt.get("manifest_sha256") != _sha256_bytes(manifest_data):
            raise CheckpointError("Remote checkpoint upload receipt does not match its manifest")
        state_data = None
        for name, entry in manifest["files"].items():
            content = self.storage.download(self.bucket, f"{prefix}/{checkpoint_id}/{name}")
            if len(content) != int(entry["size_bytes"]) or _sha256_bytes(content) != entry["sha256"]:
                raise CheckpointError(f"Remote checkpoint component failed verification: {name}")
            if name == "state.json":
                state_data = content
        if state_data is None:
            raise CheckpointError("Remote checkpoint state file is missing")
        state = json.loads(state_data.decode("utf-8"))
        saved_state = state.get("state", {})
        if state.get("checkpoint_id") != checkpoint_id:
            raise CheckpointError("Remote checkpoint state ID does not match")
        if saved_state.get("step") != manifest.get("step"):
            raise CheckpointError("Remote checkpoint step does not match its manifest")
        if saved_state.get("lease_holder") != manifest.get("lease_holder"):
            raise CheckpointError("Remote checkpoint lease holder does not match")
        if saved_state.get("fencing_token") != manifest.get("fencing_token"):
            raise CheckpointError("Remote checkpoint fencing token does not match")
        return manifest

    def upload_and_commit(
        self,
        local_store: LocalCheckpointStore,
        checkpoint_id: str,
        owner_id: str,
        run_id: str,
        api: TrainingControlAPI,
        lease_holder: str,
        fencing_token: int,
        training_state: Mapping[str, Any],
    ) -> dict[str, Any]:
        uploaded = self.upload_checkpoint(local_store, checkpoint_id, owner_id, run_id)
        api.commit_checkpoint(
            run_id,
            lease_holder,
            fencing_token,
            checkpoint_id,
            uploaded["total_size_bytes"],
            training_state,
        )
        try:
            self.prune_remote(owner_id, run_id, pinned_ids={checkpoint_id})
        except Exception as error:
            uploaded["prune_warning"] = type(error).__name__
        return uploaded

    def list_remote_candidates(self, owner_id: str, run_id: str, maximum_step: int | None = None) -> list[dict[str, Any]]:
        prefix = self._prefix(owner_id, run_id)
        top_level = self.storage.list_objects(self.bucket, prefix)
        checkpoint_ids = set()
        for item in top_level:
            name = str(item.get("name", "")).strip("/")
            if name:
                first = name.split("/", 1)[0]
                if first.startswith("ckpt-"):
                    checkpoint_ids.add(first)
        candidates = []
        for checkpoint_id in checkpoint_ids:
            checkpoint_prefix = f"{prefix}/{checkpoint_id}"
            try:
                manifest_data = self.storage.download(self.bucket, f"{checkpoint_prefix}/manifest.json")
                manifest = json.loads(manifest_data.decode("utf-8"))
                receipt_data = self.storage.download(self.bucket, f"{checkpoint_prefix}/upload_receipt.json")
                receipt = json.loads(receipt_data.decode("utf-8"))
                if manifest.get("checkpoint_id") != checkpoint_id:
                    continue
                if receipt.get("checkpoint_id") != checkpoint_id or receipt.get("manifest_sha256") != _sha256_bytes(manifest_data):
                    continue
                if receipt.get("files") != manifest.get("files"):
                    continue
                if maximum_step is not None and int(manifest.get("step", -1)) > maximum_step:
                    continue
                candidates.append(manifest)
            except Exception:
                continue
        candidates.sort(key=lambda item: (int(item["step"]), item["checkpoint_id"]), reverse=True)
        return candidates

    def prune_remote(self, owner_id: str, run_id: str, pinned_ids: set[str] | None = None) -> list[str]:
        prefix = self._prefix(owner_id, run_id)
        top_level = self.storage.list_objects(self.bucket, prefix)
        checkpoint_ids: set[str] = set()
        for item in top_level:
            name = str(item.get("name", "")).strip("/")
            if not name:
                continue
            first = name.split("/", 1)[0]
            if first.startswith("ckpt-"):
                checkpoint_ids.add(first)
        valid: list[dict[str, Any]] = []
        object_paths: dict[str, list[str]] = {}
        for checkpoint_id in checkpoint_ids:
            checkpoint_prefix = f"{prefix}/{checkpoint_id}"
            children = self.storage.list_objects(self.bucket, checkpoint_prefix)
            paths = []
            names = set()
            for child in children:
                name = str(child.get("name", "")).strip("/")
                if not name:
                    continue
                relative = name if not name.startswith(checkpoint_id + "/") else name[len(checkpoint_id) + 1:]
                names.add(relative)
                paths.append(f"{checkpoint_prefix}/{relative}")
            object_paths[checkpoint_id] = paths
            required = set(self.COMPONENTS) | {"upload_receipt.json"}
            if not required.issubset(names):
                continue
            try:
                manifest_data = self.storage.download(self.bucket, f"{checkpoint_prefix}/manifest.json")
                manifest = json.loads(manifest_data.decode("utf-8"))
                receipt_data = self.storage.download(self.bucket, f"{checkpoint_prefix}/upload_receipt.json")
                receipt = json.loads(receipt_data.decode("utf-8"))
                if manifest.get("checkpoint_id") != checkpoint_id:
                    continue
                if receipt.get("checkpoint_id") != checkpoint_id or receipt.get("manifest_sha256") != _sha256_bytes(manifest_data):
                    continue
                if receipt.get("files") != manifest.get("files"):
                    continue
                valid.append(manifest)
            except Exception:
                continue
        valid.sort(key=lambda item: (int(item["step"]), item["checkpoint_id"]), reverse=True)
        keep = {item["checkpoint_id"] for item in valid[:self.keep_last]}
        keep.update(pinned_ids or set())
        remove_paths = []
        for checkpoint_id, paths in object_paths.items():
            if checkpoint_id not in keep and any(item["checkpoint_id"] == checkpoint_id for item in valid):
                remove_paths.extend(paths)
        if remove_paths:
            self.storage.remove(self.bucket, remove_paths)
        return sorted({item["checkpoint_id"] for item in valid} - keep)
