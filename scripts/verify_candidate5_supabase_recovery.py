from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ultron_recovery_test import run_checkpoint_recovery_test
from ultron_storage import SupabaseStorageClient


CANDIDATE5_ARCHITECTURE = {
    "dimension": 512,
    "layers": 8,
    "heads": 16,
    "feedforward_multiplier": 4,
}
EXPECTED_PARAMETERS = 25_400_400
MAXIMUM_FILE_BYTES = 45_000_000
REQUIRED_RECOVERY_CHECKS = {
    "remote_upload_and_manifest_verified",
    "corrupted_checkpoint_rejected",
    "missing_checkpoint_component_rejected",
    "valid_checkpoint_accepted_after_fault_repair",
    "fresh_runtime_download_and_integrity_verified",
    "model_weights_match_uninterrupted_run",
    "optimizer_state_matches_uninterrupted_run",
    "scheduler_state_matches_uninterrupted_run",
    "data_stream_position_and_rng_match",
    "curriculum_state_matches",
    "gradient_scaler_state_matches",
    "source_optimizer_bound_to_model_on_target_device",
    "resumed_optimizer_bound_to_model_on_target_device",
}


def main() -> dict:
    project_url = os.environ.get("SUPABASE_URL", "").strip()
    secret_key = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
    owner_id = os.environ.get("SUPABASE_OWNER_ID", "").strip()
    if not project_url or not secret_key or not owner_id:
        raise SystemExit(
            "Missing required Supabase workflow configuration; no storage request was made."
        )
    if any(char in owner_id for char in ("/", chr(92))) or owner_id in {".", ".."}:
        raise SystemExit("SUPABASE_OWNER_ID must be a path-safe owner identifier.")

    storage = SupabaseStorageClient(project_url, secret_key, timeout_seconds=180)
    result = run_checkpoint_recovery_test(
        storage=storage,
        owner_id=owner_id,
        bucket="checkpoints",
        maximum_file_bytes=MAXIMUM_FILE_BYTES,
        device="cpu",
        precision="none",
        architecture=CANDIDATE5_ARCHITECTURE,
    )

    checks = result.get("checks", {})
    required_checks_passed = (
        REQUIRED_RECOVERY_CHECKS.issubset(checks)
        and all(checks.get(name) is True for name in REQUIRED_RECOVERY_CHECKS)
        and all(value is True for value in checks.values())
    )
    cleanup_passed = result.get("temporary_storage_cleanup_verified") is True
    safe_scope = (
        result.get("training_status_database_written") is False
        and result.get("production_run_id_touched") is False
        and result.get("real_training_started") is False
    )
    if (
        result.get("recovery_test_passed") is not True
        or result.get("model_parameter_count") != EXPECTED_PARAMETERS
        or result.get("saved_step") != 2
        or result.get("resumed_step") != 3
        or not required_checks_passed
        or not cleanup_passed
        or not safe_scope
    ):
        raise RuntimeError(
            "Candidate 5 live recovery did not satisfy every required assertion; "
            "inspect the structured result below."
        )

    report = {
        "project": "ULTRON",
        "test": "candidate5_live_supabase_interrupted_recovery",
        "status": "passed",
        "model_parameter_count": result["model_parameter_count"],
        "architecture": result["architecture"],
        "device": result["device"],
        "precision": result["precision"],
        "saved_step": result["saved_step"],
        "resumed_step": result["resumed_step"],
        "checks": checks,
        "temporary_storage_cleanup_verified": cleanup_passed,
        "training_status_database_written": False,
        "production_run_id_touched": False,
        "real_training_started": False,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


if __name__ == "__main__":
    main()
