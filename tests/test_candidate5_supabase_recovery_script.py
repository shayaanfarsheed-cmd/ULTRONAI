import contextlib
import io
import os
import unittest
from unittest.mock import patch

from scripts import verify_candidate5_supabase_recovery as verifier


class Candidate5SupabaseRecoveryScriptTest(unittest.TestCase):
    def test_missing_configuration_fails_before_storage_access(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(verifier, "SupabaseStorageClient") as storage_client:
                with self.assertRaisesRegex(SystemExit, "no storage request was made"):
                    verifier.main()
                storage_client.assert_not_called()

    def test_path_unsafe_owner_is_rejected(self):
        environment = {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SECRET_KEY": "not-a-real-secret",
            "SUPABASE_OWNER_ID": "../other",
        }
        with patch.dict(os.environ, environment, clear=True):
            with patch.object(verifier, "SupabaseStorageClient") as storage_client:
                with self.assertRaisesRegex(SystemExit, "path-safe"):
                    verifier.main()
                storage_client.assert_not_called()

    def test_candidate5_live_recovery_reports_only_after_all_gates_pass(self):
        environment = {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SECRET_KEY": "not-a-real-secret",
            "SUPABASE_OWNER_ID": "owner-test",
        }
        checks = {
            "remote_upload_and_manifest_verified": True,
            "corrupted_checkpoint_rejected": True,
            "missing_checkpoint_component_rejected": True,
            "valid_checkpoint_accepted_after_fault_repair": True,
            "fresh_runtime_download_and_integrity_verified": True,
            "model_weights_match_uninterrupted_run": True,
            "optimizer_state_matches_uninterrupted_run": True,
            "scheduler_state_matches_uninterrupted_run": True,
            "data_stream_position_and_rng_match": True,
            "curriculum_state_matches": True,
            "gradient_scaler_state_matches": True,
            "source_optimizer_bound_to_model_on_target_device": True,
            "resumed_optimizer_bound_to_model_on_target_device": True,
        }
        simulated_result = {
            "recovery_test_passed": True,
            "model_parameter_count": verifier.EXPECTED_PARAMETERS,
            "architecture": dict(verifier.CANDIDATE5_ARCHITECTURE),
            "device": "cpu",
            "precision": "none",
            "saved_step": 2,
            "resumed_step": 3,
            "checks": checks,
            "temporary_storage_cleanup_verified": True,
            "training_status_database_written": False,
            "production_run_id_touched": False,
            "real_training_started": False,
        }
        output = io.StringIO()
        with patch.dict(os.environ, environment, clear=True):
            with patch.object(verifier, "SupabaseStorageClient") as storage_client:
                with patch.object(
                    verifier, "run_checkpoint_recovery_test", return_value=simulated_result
                ) as recovery_test:
                    with contextlib.redirect_stdout(output):
                        report = verifier.main()

        storage_client.assert_called_once_with(
            "https://example.supabase.co", "not-a-real-secret", timeout_seconds=180
        )
        recovery_test.assert_called_once()
        arguments = recovery_test.call_args.kwargs
        self.assertEqual(arguments["owner_id"], "owner-test")
        self.assertEqual(arguments["bucket"], "checkpoints")
        self.assertEqual(arguments["device"], "cpu")
        self.assertEqual(arguments["precision"], "none")
        self.assertEqual(arguments["architecture"], verifier.CANDIDATE5_ARCHITECTURE)
        self.assertEqual(report["status"], "passed")
        self.assertFalse(report["real_training_started"])
        self.assertIn('"temporary_storage_cleanup_verified": true', output.getvalue())

    def test_any_failed_recovery_check_blocks_pass_report(self):
        environment = {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SECRET_KEY": "not-a-real-secret",
            "SUPABASE_OWNER_ID": "owner-test",
        }
        simulated_result = {
            "recovery_test_passed": True,
            "model_parameter_count": verifier.EXPECTED_PARAMETERS,
            "architecture": dict(verifier.CANDIDATE5_ARCHITECTURE),
            "device": "cpu",
            "precision": "none",
            "saved_step": 2,
            "resumed_step": 3,
            "checks": {"model_weights_match_uninterrupted_run": False},
            "temporary_storage_cleanup_verified": True,
            "training_status_database_written": False,
            "production_run_id_touched": False,
            "real_training_started": False,
        }
        with patch.dict(os.environ, environment, clear=True):
            with patch.object(verifier, "SupabaseStorageClient"):
                with patch.object(verifier, "run_checkpoint_recovery_test", return_value=simulated_result):
                    with self.assertRaisesRegex(RuntimeError, "every required assertion"):
                        verifier.main()


if __name__ == "__main__":
    unittest.main()
