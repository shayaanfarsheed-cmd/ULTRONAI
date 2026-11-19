from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch

from ultron_checkpoint import LocalCheckpointStore
from ultron_model import ALPHABET, ULTRONTransformer
from ultron_storage import RemoteCheckpointStore, SupabaseStorageClient
from scripts.verify_supabase_checkpoint_storage import _cleanup_prefix


CANDIDATE5 = {
    "vocab_size": len(ALPHABET),
    "context_length": 192,
    "dimension": 512,
    "layers": 8,
    "heads": 16,
    "feedforward_multiplier": 4,
    "dropout": 0.1,
}
EXPECTED_PARAMETERS = 25_398_350
MAX_OBJECT_BYTES = 45_000_000


def _equal(left: Any, right: Any) -> bool:
    if isinstance(left, torch.Tensor) and isinstance(right, torch.Tensor):
        return torch.equal(left, right)
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_equal(left[k], right[k]) for k in left)
    if isinstance(left, (list, tuple)) and isinstance(right, type(left)):
        return len(left) == len(right) and all(_equal(a, b) for a, b in zip(left, right))
    return left == right


def main() -> None:
    project_url = os.environ.get("SUPABASE_URL", "").strip()
    secret_key = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
    owner_id = os.environ.get("SUPABASE_OWNER_ID", "").strip()
    run_id = f"candidate5-live-{os.environ.get('GITHUB_RUN_ID', 'manual')}-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}"
    if not project_url or not secret_key or not owner_id:
        raise SystemExit("Missing required Supabase workflow configuration; no storage request was made.")
    if "/" in owner_id:
        raise SystemExit("SUPABASE_OWNER_ID must be a path-safe owner identifier.")

    torch.set_num_threads(2)
    torch.manual_seed(20261119)
    model = ULTRONTransformer(**CANDIDATE5)
    count = model.parameter_count()
    if count != EXPECTED_PARAMETERS:
        raise RuntimeError(f"Candidate 5 parameter-count mismatch: expected {EXPECTED_PARAMETERS}, got {count}")
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, foreach=False)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=1000)

    # One deterministic update populates AdamW moments so the real optimizer
    # checkpoint is representative, not an empty optimizer state.
    tokens = torch.randint(0, len(ALPHABET), (1, CANDIDATE5["context_length"]))
    model.train()
    optimizer.zero_grad(set_to_none=True)
    _, loss = model(tokens, tokens)
    if loss is None or not torch.isfinite(loss):
        raise RuntimeError("Candidate 5 pre-upload diagnostic loss was not finite.")
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    optimizer.step()
    scheduler.step()

    bucket = "checkpoints"
    prefix = f"{owner_id}/{run_id}"
    storage = SupabaseStorageClient(project_url, secret_key, timeout_seconds=180)
    remote = RemoteCheckpointStore(storage, bucket=bucket, maximum_file_bytes=MAX_OBJECT_BYTES)
    print(f"Candidate 5 parameters: {count:,}")
    print(f"Per-object limit: {MAX_OBJECT_BYTES:,} bytes")
    print("Total remaining Supabase bucket quota: UNKNOWN (provider quota is not exposed by this workflow).")
    print("This test writes only beneath its unique run prefix; no existing checkpoint is overwritten.")

    try:
        with tempfile.TemporaryDirectory(prefix="ultron-candidate5-live-") as source_dir, tempfile.TemporaryDirectory(
            prefix="ultron-candidate5-restore-"
        ) as target_dir:
            local = LocalCheckpointStore(source_dir, keep_last=1, maximum_file_bytes=MAX_OBJECT_BYTES)
            state = {
                "step": 1,
                "current_topic": "candidate5_storage_validation",
                "difficulty": 1,
                "data_position": 1,
                "seed": 20261119,
                "lease_holder": "github-actions-candidate5-live-test",
                "fencing_token": 1,
            }
            manifest = local.save(model, optimizer, state, scheduler=scheduler)
            sizes = {name: (local.root / manifest["checkpoint_id"] / name).stat().st_size for name in manifest["files"]}
            if not sizes or max(sizes.values()) > MAX_OBJECT_BYTES:
                raise RuntimeError("At least one local checkpoint component exceeds the configured per-object limit.")
            print(f"Local checkpoint payload: {sum(sizes.values()):,} bytes across {len(sizes)} components.")

            receipt = remote.upload_checkpoint(local, manifest["checkpoint_id"], owner_id, run_id)
            if not receipt.get("verified"):
                raise RuntimeError("Supabase upload did not return a verified receipt.")
            verified_manifest = remote.verify_remote_checkpoint(owner_id, run_id, manifest["checkpoint_id"])
            if verified_manifest["files"] != manifest["files"]:
                raise RuntimeError("Remote manifest differs from the local manifest.")

            restored_store = LocalCheckpointStore(target_dir, keep_last=1, maximum_file_bytes=MAX_OBJECT_BYTES)
            remote.download_checkpoint(owner_id, run_id, manifest["checkpoint_id"], restored_store)
            restored_model = ULTRONTransformer(**CANDIDATE5)
            restored_optimizer = torch.optim.AdamW(restored_model.parameters(), lr=3e-4, foreach=False)
            restored_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(restored_optimizer, T_max=1000)
            restored = restored_store.load_latest(
                restored_model, restored_optimizer, scheduler=restored_scheduler, restore_rng=False
            )
            if restored is None or int(restored["step"]) != 1:
                raise RuntimeError("Fresh restore did not recover checkpoint step 1.")
            model_ok = all(torch.equal(value, restored_model.state_dict()[name]) for name, value in model.state_dict().items())
            optimizer_ok = _equal(optimizer.state_dict(), restored_optimizer.state_dict())
            scheduler_ok = _equal(scheduler.state_dict(), restored_scheduler.state_dict())
            if not (model_ok and optimizer_ok and scheduler_ok):
                raise RuntimeError(
                    f"Candidate 5 restore mismatch: model={model_ok}, optimizer={optimizer_ok}, scheduler={scheduler_ok}"
                )
            print(f"PASS: live Supabase upload and remote component/hash verification ({receipt['total_size_bytes']:,} bytes).")
            print("PASS: download into fresh directory and exact model, AdamW, scheduler restore.")
    finally:
        _cleanup_prefix(storage, bucket, prefix)
        print("PASS: temporary Candidate 5 objects removed; unrelated prefixes were not targeted.")


if __name__ == "__main__":
    main()
