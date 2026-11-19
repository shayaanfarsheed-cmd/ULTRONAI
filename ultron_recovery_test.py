from __future__ import annotations

import copy
import math
import uuid
from tempfile import TemporaryDirectory
from typing import Any, Mapping

import torch

from ultron_checkpoint import LocalCheckpointStore
from ultron_model import CharTokenizer, ULTRONTransformer
from ultron_storage import RemoteCheckpointStore
from ultron_training import CurriculumController, MathBatchStream, train_steps


def _make_objects(tokenizer: CharTokenizer):
    model = ULTRONTransformer(
        vocab_size=tokenizer.vocab_size,
        context_length=192,
        dimension=32,
        layers=1,
        heads=4,
        feedforward_multiplier=2,
        dropout=0.1,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=8)
    return model, optimizer, scheduler


def _equal_nested(left: Any, right: Any) -> bool:
    if isinstance(left, torch.Tensor) or isinstance(right, torch.Tensor):
        return isinstance(left, torch.Tensor) and isinstance(right, torch.Tensor) and torch.equal(left, right)
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return left.keys() == right.keys() and all(_equal_nested(left[key], right[key]) for key in left)
    if isinstance(left, (tuple, list)) and isinstance(right, (tuple, list)):
        return len(left) == len(right) and all(_equal_nested(a, b) for a, b in zip(left, right))
    if isinstance(left, float) and isinstance(right, float):
        return math.isclose(left, right, rel_tol=0.0, abs_tol=0.0)
    return left == right


def run_checkpoint_recovery_test(
    storage: Any,
    owner_id: str,
    bucket: str = "checkpoints",
    maximum_file_bytes: int = 45_000_000,
) -> dict[str, Any]:
    """Exercise an isolated Storage-only checkpoint round trip and exact next-step resume."""
    if not owner_id or "/" in owner_id or "\\" in owner_id:
        raise ValueError("A valid owner ID is required for the isolated recovery test")

    from ultron_data import generate_dataset

    torch.set_num_threads(1)
    torch.manual_seed(20261119)
    seed = 20261119
    test_run_id = f"recovery-test-{uuid.uuid4().hex}"
    remote = RemoteCheckpointStore(storage, bucket=bucket, keep_last=1, maximum_file_bytes=maximum_file_bytes)
    checkpoint_id: str | None = None

    try:
        tokenizer = CharTokenizer()
        examples = generate_dataset(
            12,
            seed=seed,
            split="train",
            topics=["whole_number_arithmetic"],
        )
        stages = [{"name": "recovery-test", "topics": ["whole_number_arithmetic"]}]
        curriculum = CurriculumController(stages, require_held_out=False)
        stream = MathBatchStream(
            examples,
            tokenizer,
            context_length=192,
            batch_size=2,
            seed=seed,
            shuffle=True,
        )
        model, optimizer, scheduler = _make_objects(tokenizer)
        train_steps(
            model,
            optimizer,
            stream,
            steps=2,
            device="cpu",
            precision="none",
            scheduler=scheduler,
            start_step=0,
        )
        saved_state = {
            "step": 2,
            "current_topic": "whole_number_arithmetic",
            "difficulty": 1,
            "data_position": stream.position,
            "data_epoch": stream.epoch,
            "seed": seed,
            "lease_holder": test_run_id,
            "fencing_token": 1,
            "curriculum_state": curriculum.state_dict(),
            "data_stream_state": stream.state_dict(),
            "loss": None,
            "learning_rate": float(optimizer.param_groups[0]["lr"]),
            "recovery_test": True,
        }

        with TemporaryDirectory(prefix="ultron-recovery-source-") as source_dir, TemporaryDirectory(
            prefix="ultron-recovery-fresh-"
        ) as fresh_dir:
            source_store = LocalCheckpointStore(source_dir, keep_last=1, maximum_file_bytes=maximum_file_bytes)
            manifest = source_store.save(model, optimizer, saved_state, scheduler=scheduler)
            checkpoint_id = str(manifest["checkpoint_id"])

            uploaded = remote.upload_checkpoint(source_store, checkpoint_id, owner_id, test_run_id)
            remote_manifest = remote.verify_remote_checkpoint(owner_id, test_run_id, checkpoint_id)
            if int(remote_manifest["step"]) != 2 or not uploaded.get("verified"):
                raise RuntimeError("Remote checkpoint verification did not confirm step 2")

            # Continue the original process once to establish the uninterrupted reference.
            train_steps(
                model,
                optimizer,
                stream,
                steps=1,
                device="cpu",
                precision="none",
                scheduler=scheduler,
                start_step=2,
            )
            expected_model = {name: tensor.detach().clone() for name, tensor in model.state_dict().items()}
            expected_optimizer = copy.deepcopy(optimizer.state_dict())
            expected_scheduler = copy.deepcopy(scheduler.state_dict())
            expected_stream = copy.deepcopy(stream.state_dict())
            expected_curriculum = copy.deepcopy(curriculum.state_dict())

            # A fresh local directory and fresh objects represent a new Kaggle runtime.
            fresh_store = LocalCheckpointStore(fresh_dir, keep_last=1, maximum_file_bytes=maximum_file_bytes)
            downloaded = remote.download_checkpoint(owner_id, test_run_id, checkpoint_id, fresh_store)
            fresh_model, fresh_optimizer, fresh_scheduler = _make_objects(tokenizer)
            fresh_curriculum = CurriculumController(stages, require_held_out=False)
            fresh_stream = MathBatchStream(
                examples,
                tokenizer,
                context_length=192,
                batch_size=2,
                seed=seed + 1,
                shuffle=True,
            )
            restored = fresh_store.load_latest(
                fresh_model,
                fresh_optimizer,
                scheduler=fresh_scheduler,
                restore_rng=True,
                map_location="cpu",
            )
            if restored is None or int(restored["step"]) != 2:
                raise RuntimeError("Fresh runtime did not restore the exact saved step")
            fresh_stream.load_state_dict(restored["state"]["data_stream_state"])
            fresh_curriculum.load_state_dict(restored["state"]["curriculum_state"])

            train_steps(
                fresh_model,
                fresh_optimizer,
                fresh_stream,
                steps=1,
                device="cpu",
                precision="none",
                scheduler=fresh_scheduler,
                start_step=int(restored["step"]),
            )

            model_exact = all(
                torch.equal(fresh_model.state_dict()[name], tensor)
                for name, tensor in expected_model.items()
            )
            optimizer_exact = _equal_nested(fresh_optimizer.state_dict(), expected_optimizer)
            scheduler_exact = _equal_nested(fresh_scheduler.state_dict(), expected_scheduler)
            stream_exact = _equal_nested(fresh_stream.state_dict(), expected_stream)
            curriculum_exact = _equal_nested(fresh_curriculum.state_dict(), expected_curriculum)
            if not all((model_exact, optimizer_exact, scheduler_exact, stream_exact, curriculum_exact)):
                raise RuntimeError(
                    "Resume diverged from uninterrupted execution: "
                    f"model={model_exact}, optimizer={optimizer_exact}, scheduler={scheduler_exact}, "
                    f"data_stream={stream_exact}, curriculum={curriculum_exact}"
                )

            return {
                "recovery_test_passed": True,
                "test_run_id": test_run_id,
                "checkpoint_id": checkpoint_id,
                "saved_step": int(downloaded["step"]),
                "resumed_step": int(restored["step"]) + 1,
                "checks": {
                    "remote_upload_and_manifest_verified": True,
                    "fresh_runtime_download_and_integrity_verified": True,
                    "model_weights_match_uninterrupted_run": model_exact,
                    "optimizer_state_matches_uninterrupted_run": optimizer_exact,
                    "scheduler_state_matches_uninterrupted_run": scheduler_exact,
                    "data_stream_position_and_rng_match": stream_exact,
                    "curriculum_state_matches": curriculum_exact,
                },
                "training_status_database_written": False,
                "production_run_id_touched": False,
                "real_training_started": False,
            }
    finally:
        if checkpoint_id is not None:
            paths = [
                f"{owner_id}/{test_run_id}/{checkpoint_id}/{name}"
                for name in (*RemoteCheckpointStore.COMPONENTS, "upload_receipt.json")
            ]
            storage.remove(bucket, paths)
