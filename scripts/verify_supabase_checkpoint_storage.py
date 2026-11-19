from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Running a file inside scripts/ puts that directory, not the repository root,
# at sys.path[0]. Add the project root so top-level ULTRON modules are importable
# both in GitHub Actions and when this script is launched directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch
from torch import nn

from ultron_checkpoint import LocalCheckpointStore
from ultron_storage import RemoteCheckpointStore, SupabaseStorageClient


def _cleanup_prefix(storage: SupabaseStorageClient, bucket: str, prefix: str) -> None:
    paths: list[str] = []
    offset = 0
    while True:
        page = storage.list_objects(bucket, prefix, limit=500, offset=offset)
        if not page:
            break
        for item in page:
            name = str(item.get("name", "")).strip("/")
            if not name:
                continue
            if name.startswith(prefix + "/"):
                object_path = name
            else:
                object_path = f"{prefix}/{name}"
            if object_path.startswith(prefix + "/"):
                paths.append(object_path)
        offset += len(page)
        if len(page) < 500:
            break
    for start in range(0, len(paths), 100):
        storage.remove(bucket, paths[start:start + 100])
    remaining = storage.list_objects(bucket, prefix, limit=500, offset=0)
    if remaining:
        raise RuntimeError("Temporary checkpoint objects remain after cleanup")


def main() -> None:
    project_url = os.environ.get("SUPABASE_URL", "")
    secret_key = os.environ.get("SUPABASE_SECRET_KEY", "")
    owner_id = os.environ.get("SUPABASE_OWNER_ID", "")
    run_id = f"storage-smoke-{os.environ.get('GITHUB_RUN_ID', 'manual')}-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}"
    if not project_url or not secret_key or not owner_id:
        raise SystemExit("Missing SUPABASE_URL, SUPABASE_SECRET_KEY, or SUPABASE_OWNER_ID.")

    bucket = "checkpoints"
    prefix = f"{owner_id}/{run_id}"
    storage = SupabaseStorageClient(project_url, secret_key)
    remote = RemoteCheckpointStore(storage, bucket=bucket)
    torch.manual_seed(20261119)

    try:
        with tempfile.TemporaryDirectory(prefix="ultron-storage-smoke-") as source_dir, tempfile.TemporaryDirectory(prefix="ultron-storage-restore-") as target_dir:
            model = nn.Sequential(nn.Linear(16, 32), nn.GELU(), nn.Linear(32, 8))
            optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
            sample = torch.randn(4, 16)
            model(sample).square().mean().backward()
            optimizer.step()

            local = LocalCheckpointStore(source_dir)
            state = {
                "step": 1,
                "current_topic": "storage_round_trip_smoke",
                "difficulty": 1,
                "data_position": 4,
                "seed": 20261119,
                "lease_holder": "github-actions-storage-smoke",
                "fencing_token": 1,
            }
            manifest = local.save(model, optimizer, state)
            checkpoint_id = manifest["checkpoint_id"]

            uploaded = remote.upload_checkpoint(local, checkpoint_id, owner_id, run_id)
            if not uploaded.get("verified"):
                raise RuntimeError("Remote upload did not return a verified receipt")
            remote_manifest = remote.verify_remote_checkpoint(owner_id, run_id, checkpoint_id)
            if int(remote_manifest["step"]) != 1:
                raise RuntimeError("Remote checkpoint step did not match")

            restored_store = LocalCheckpointStore(target_dir)
            downloaded = remote.download_checkpoint(owner_id, run_id, checkpoint_id, restored_store)
            restored_model = nn.Sequential(nn.Linear(16, 32), nn.GELU(), nn.Linear(32, 8))
            restored_optimizer = torch.optim.AdamW(restored_model.parameters(), lr=1e-3)
            restored = restored_store.load_latest(restored_model, restored_optimizer, restore_rng=False)
            if downloaded["checkpoint_id"] != checkpoint_id or restored is None or restored["step"] != 1:
                raise RuntimeError("Downloaded checkpoint could not be restored")
            for name, tensor in model.state_dict().items():
                if not torch.equal(tensor, restored_model.state_dict()[name]):
                    raise RuntimeError(f"Restored model tensor mismatch: {name}")
            for original_parameter, restored_parameter in zip(model.parameters(), restored_model.parameters()):
                original_state = optimizer.state[original_parameter]
                restored_state = restored_optimizer.state[restored_parameter]
                for state_name in ("exp_avg", "exp_avg_sq"):
                    if not torch.equal(original_state[state_name], restored_state[state_name]):
                        raise RuntimeError(f"Restored optimizer tensor mismatch: {state_name}")
            print(f"PASS: upload, remote hash verification, download, model and optimizer restore ({uploaded['total_size_bytes']} bytes).")
    finally:
        _cleanup_prefix(storage, bucket, prefix)
        print(f"PASS: temporary objects deleted from {bucket}/{prefix}.")


if __name__ == "__main__":
    main()
