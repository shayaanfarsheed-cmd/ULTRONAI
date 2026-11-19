import tempfile
import unittest
from datetime import timedelta

import torch

from ultron_checkpoint import LocalCheckpointStore
from ultron_model import ULTRONTransformer
from ultron_session import run_training_session
from ultron_storage import RemoteCheckpointStore, SupabaseStorageError
from ultron_supabase import LeaseResult, SupabaseAPIError, iso_utc, utc_now


class FakeStorage:
    def __init__(self):
        self.objects = {}

    def upload(self, bucket, path, content, content_type):
        key = (bucket, path)
        if key in self.objects:
            if self.objects[key] != content:
                raise SupabaseStorageError(409, "Different object content")
            return True
        self.objects[key] = bytes(content)
        return False

    def download(self, bucket, path):
        try:
            return self.objects[(bucket, path)]
        except KeyError:
            raise SupabaseStorageError(404, "Object not found")

    def list_objects(self, bucket, prefix, limit=1000, offset=0):
        start = prefix.strip("/") + "/"
        names = sorted(path[len(start):] for (bucket_id, path) in self.objects if bucket_id == bucket and path.startswith(start))
        return [{"name": name} for name in names[offset:offset + limit]]

    def remove(self, bucket, paths):
        for path in paths:
            self.objects.pop((bucket, path), None)
        return []


class FakeAPI:
    def __init__(self, acquired=True, pause=False, renew=True, handoff=False):
        self.owner_id = "owner-1"
        self.client = type("Client", (), {"project_url": "https://example.supabase.co", "_api_key": "not-a-real-key"})()
        self.status = None
        self.acquired = acquired
        self.pause = pause
        self.handoff = handoff
        self.renew = renew
        self.released = []
        self.sessions = []
        self.switches = []
        self.selected_resume = []

    def create_run_id(self):
        return "run-1"

    def acquire_lease(self, run_id, server_name, lease_holder, ttl_seconds, device="cpu", session_limit_seconds=None):
        if not self.acquired:
            return LeaseResult(False, run_id, "other-worker", 1, iso_utc(utc_now() + timedelta(minutes=5)), "busy")
        now = iso_utc()
        if self.status and self.status.get("run_id") == run_id:
            token = int(self.status.get("fencing_token", 0)) + 1
            self.status.update({
                "current_server": server_name,
                "state": "starting",
                "lease_holder": lease_holder,
                "lease_expires_at": iso_utc(utc_now() + timedelta(seconds=ttl_seconds)),
                "fencing_token": token,
                "updated_at": now,
            })
            return LeaseResult(True, run_id, lease_holder, token, self.status["lease_expires_at"], "reacquired")
        self.status = {
            "run_id": run_id,
            "owner_id": self.owner_id,
            "current_server": server_name,
            "state": "starting",
            "lease_holder": lease_holder,
            "lease_expires_at": iso_utc(utc_now() + timedelta(seconds=ttl_seconds)),
            "fencing_token": 1,
            "last_checkpoint_step": None,
            "last_checkpoint_id": None,
            "pause_requested": False,
            "updated_at": now,
        }
        return LeaseResult(True, run_id, lease_holder, 1, self.status["lease_expires_at"], "acquired")

    def start_session(self, run_id, server_name, session_id=None, details=None):
        self.sessions.append({"run_id": run_id, "server": server_name, "details": details or {}, "ended": False})
        return "session-1"

    def get_status(self, run_id):
        return dict(self.status) if self.status else None

    def renew_lease(self, run_id, lease_holder, fencing_token, ttl_seconds, status_values=None):
        if not self.renew:
            return False
        if self.status.get("lease_holder") is None:
            return False
        if self.status.get("fencing_token") != fencing_token or self.status.get("lease_holder") != lease_holder:
            return False
        self.status.update(status_values or {})
        self.status["lease_expires_at"] = iso_utc(utc_now() + timedelta(seconds=ttl_seconds))
        self.status["last_heartbeat_at"] = iso_utc()
        return True


    def select_resume_checkpoint(self, run_id, lease_holder, fencing_token, checkpoint, training_state):
        self.selected_resume.append(checkpoint["checkpoint_id"])
        self.status.update({
            "last_checkpoint_id": checkpoint["checkpoint_id"],
            "last_checkpoint_step": checkpoint["step"],
            "last_checkpoint_size_bytes": checkpoint["total_size_bytes"],
            "last_checkpoint_manifest_sha256": checkpoint["manifest_sha256"],
            "current_step": checkpoint["step"],
            "requested_resume_checkpoint_id": None,
        })
        return True

    def clear_requested_resume_checkpoint(self, run_id, lease_holder, fencing_token, requested_checkpoint_id, reason):
        self.status["requested_resume_checkpoint_id"] = None
        self.status["last_error"] = reason
        return True

    def controls(self, run_id):
        return {"pause_requested": self.pause, "handoff_requested": self.handoff}

    def commit_checkpoint(self, run_id, lease_holder, fencing_token, checkpoint_id, checkpoint_size_bytes, training_state, manifest_sha256=None):
        if self.status["lease_holder"] != lease_holder or self.status["fencing_token"] != fencing_token:
            raise RuntimeError("stale lease")
        self.status.update({
            "last_checkpoint_id": checkpoint_id,
            "last_checkpoint_step": training_state["step"],
            "last_checkpoint_verified": True,
            "last_checkpoint_manifest_sha256": manifest_sha256,
            "current_step": training_state["step"],
        })
        return dict(self.status)

    def release_lease(self, run_id, lease_holder, fencing_token, final_state, end_reason=None):
        self.status["lease_holder"] = None
        self.status["lease_expires_at"] = None
        self.status["state"] = final_state
        self.released.append(final_state)
        if self.sessions:
            self.sessions[-1]["ended"] = True
            self.sessions[-1]["end_reason"] = end_reason or {
                "finished": "finished",
                "handoff_needed": "handoff",
                "paused": "user_stop",
                "dead": "crashed",
            }[final_state]
        return True

    def end_session(self, session_id, gpu_seconds, end_reason, details=None):
        self.sessions[-1]["ended"] = True
        self.sessions[-1]["end_reason"] = end_reason
        return True

    def create_switch_request(self, run_id, from_server, to_server, reason, automatic=False, metadata=None):
        self.switches.append({"reason": reason, "from": from_server, "to": to_server})
        return "switch-1"


class TrainingSessionTests(unittest.TestCase):
    def _config(self):
        return {
            "model": {
                "context_length": 192,
                "embedding_dimension": 32,
                "transformer_layers": 1,
                "attention_heads": 4,
                "feedforward_multiplier": 4,
                "dropout": 0.0,
                "expected_parameter_count": None,
            },
            "training": {
                "seed": 20261117,
                "learning_rate": 0.001,
                "weight_decay": 0.0,
                "gradient_clip_norm": 1.0,
                "examples_per_stage": 16,
                "evaluation_examples_per_topic": 1,
                "evaluation_interval_steps": 0,
                "maximum_training_steps": 2,
                "curriculum": {
                    "stages": [{"name": "elementary", "topics": ["whole_number_arithmetic"]}],
                    "unlock_mastery_accuracy": 0.9,
                    "consecutive_evaluations_required": 3,
                    "held_out_evaluation_required": True,
                },
            },
            "session_management": {"session_safety_margin_minutes": 10},
            "coordination": {"lease_ttl_seconds": 780},
            "monitoring": {"heartbeat_interval_seconds": 60},
            "persistence": {
                "checkpoint_interval_seconds": 0,
                "keep_last_valid_checkpoints": 3,
                "max_single_storage_object_mb": 45,
            },
            "storage": {"supabase_bucket": "checkpoints"},
        }

    def _servers(self):
        return {"servers": [{
            "id": "lightning_ai",
            "name": "Lightning AI Free CPU",
            "limits": {"free_studio_restart_hours": 4, "training_session_target_hours": 3.5},
        }]}

    def _model_factory(self, tokenizer):
        return ULTRONTransformer(
            vocab_size=tokenizer.vocab_size,
            context_length=192,
            dimension=32,
            layers=1,
            heads=4,
            dropout=0.0,
        )

    def test_short_training_session_commits_checkpoint_and_finishes(self):
        api = FakeAPI()
        remote = RemoteCheckpointStore(FakeStorage(), keep_last=3)
        with tempfile.TemporaryDirectory() as folder:
            result = run_training_session(
                self._config(),
                self._servers(),
                checkpoint_root=folder,
                api=api,
                remote_store=remote,
                platform_id="lightning_ai",
                runtime_override={"device": "cpu", "batch_size": 2, "cpu_threads": 1, "mixed_precision": "none"},
                model_factory=self._model_factory,
            )
        self.assertEqual(result["state"], "finished")
        self.assertEqual(result["step"], 2)
        self.assertIsNotNone(api.status["last_checkpoint_id"])
        self.assertEqual(api.status["last_checkpoint_step"], 2)
        self.assertEqual(api.released[-1], "finished")
        self.assertTrue(api.sessions[0]["ended"])

    def test_second_worker_waits_without_starting_session(self):
        api = FakeAPI(acquired=False)
        remote = RemoteCheckpointStore(FakeStorage(), keep_last=3)
        with tempfile.TemporaryDirectory() as folder:
            result = run_training_session(
                self._config(),
                self._servers(),
                checkpoint_root=folder,
                api=api,
                remote_store=remote,
                platform_id="lightning_ai",
                runtime_override={"device": "cpu", "batch_size": 2, "cpu_threads": 1, "mixed_precision": "none"},
                model_factory=self._model_factory,
            )
        self.assertEqual(result["state"], "waiting_for_lease")
        self.assertEqual(api.sessions, [])

    def test_pause_request_saves_and_releases_lease(self):
        api = FakeAPI(pause=True)
        remote = RemoteCheckpointStore(FakeStorage(), keep_last=3)
        with tempfile.TemporaryDirectory() as folder:
            result = run_training_session(
                self._config(),
                self._servers(),
                checkpoint_root=folder,
                api=api,
                remote_store=remote,
                platform_id="lightning_ai",
                runtime_override={"device": "cpu", "batch_size": 2, "cpu_threads": 1, "mixed_precision": "none"},
                model_factory=self._model_factory,
            )
        self.assertEqual(result["state"], "paused")
        self.assertEqual(result["reason"], "pause_requested")
        self.assertEqual(api.released[-1], "paused")
        self.assertEqual(api.status["last_checkpoint_step"], 0)

    def test_unexpected_heartbeat_error_saves_local_checkpoint_without_remote_commit(self):
        class Clock:
            value = 0.0
            lease_deadline = 0.0

            def __call__(self):
                return self.value

        clock = Clock()

        class FailingControlsAPI(FakeAPI):
            def renew_lease(self, run_id, lease_holder, fencing_token, ttl_seconds, status_values=None):
                renewed = super().renew_lease(
                    run_id, lease_holder, fencing_token, ttl_seconds, status_values=status_values
                )
                if renewed:
                    clock.lease_deadline = clock.value + ttl_seconds
                return renewed

            def controls(self, run_id):
                clock.value = clock.lease_deadline - 20
                raise RuntimeError("temporary control read failure")

        api = FailingControlsAPI()
        remote_storage = FakeStorage()
        remote = RemoteCheckpointStore(remote_storage, keep_last=3)
        config = self._config()
        config["monitoring"]["heartbeat_interval_seconds"] = 0
        with tempfile.TemporaryDirectory() as folder:
            result = run_training_session(
                config,
                self._servers(),
                checkpoint_root=folder,
                api=api,
                remote_store=remote,
                platform_id="lightning_ai",
                runtime_override={"device": "cpu", "batch_size": 2, "cpu_threads": 1, "mixed_precision": "none"},
                model_factory=self._model_factory,
                monotonic=clock,
            )
            local = LocalCheckpointStore(folder)
            checkpoints = local.list_valid_checkpoints()

        self.assertEqual(result["state"], "dead")
        self.assertEqual(result["reason"], "heartbeat_failed_lease_expiring")
        self.assertTrue(checkpoints, "the latest training state must be preserved locally")
        self.assertEqual(checkpoints[0]["step"], 0)
        self.assertEqual(remote_storage.objects, {}, "uncertain lease must not trigger a remote commit")
        self.assertEqual(api.released, [], "an expired/uncertain lease must not be released by this worker")

    def test_unexpected_heartbeat_error_is_throttled_between_retries(self):
        class FailingControlsAPI(FakeAPI):
            def __init__(self):
                super().__init__()
                self.control_calls = 0

            def controls(self, run_id):
                self.control_calls += 1
                raise RuntimeError("temporary control read failure")

        api = FailingControlsAPI()
        remote = RemoteCheckpointStore(FakeStorage(), keep_last=3)
        with tempfile.TemporaryDirectory() as folder:
            result = run_training_session(
                self._config(),
                self._servers(),
                checkpoint_root=folder,
                api=api,
                remote_store=remote,
                platform_id="lightning_ai",
                runtime_override={"device": "cpu", "batch_size": 2, "cpu_threads": 1, "mixed_precision": "none"},
                model_factory=self._model_factory,
                monotonic=lambda: 0.0,
            )

        self.assertEqual(result["state"], "finished")
        self.assertEqual(api.control_calls, 1, "heartbeat errors must not retry on every training batch")

    def test_database_heartbeat_error_saves_locally_without_remote_commit(self):
        class Clock:
            value = 0.0

            def __call__(self):
                return self.value

        clock = Clock()

        class FailingRenewalAPI(FakeAPI):
            def renew_lease(self, run_id, lease_holder, fencing_token, ttl_seconds, status_values=None):
                clock.value = 751.0
                raise SupabaseAPIError(503, "database unavailable")

        api = FailingRenewalAPI()
        remote_storage = FakeStorage()
        remote = RemoteCheckpointStore(remote_storage, keep_last=3)
        config = self._config()
        config["monitoring"]["heartbeat_interval_seconds"] = 0
        with tempfile.TemporaryDirectory() as folder:
            result = run_training_session(
                config,
                self._servers(),
                checkpoint_root=folder,
                api=api,
                remote_store=remote,
                platform_id="lightning_ai",
                runtime_override={"device": "cpu", "batch_size": 2, "cpu_threads": 1, "mixed_precision": "none"},
                model_factory=self._model_factory,
                monotonic=clock,
            )
            checkpoints = LocalCheckpointStore(folder).list_valid_checkpoints()

        self.assertEqual(result["state"], "dead")
        self.assertEqual(result["reason"], "database_unreachable_lease_expiring")
        self.assertTrue(checkpoints, "the latest training state must be preserved locally")
        self.assertEqual(checkpoints[0]["step"], 0)
        self.assertEqual(remote_storage.objects, {}, "database outage must never trigger a remote checkpoint commit")
        self.assertEqual(api.released, [], "an uncertain lease must not be released by this worker")

    def test_lost_lease_stops_before_training_or_checkpointing(self):
        api = FakeAPI(renew=False)
        remote = RemoteCheckpointStore(FakeStorage(), keep_last=3)
        with tempfile.TemporaryDirectory() as folder:
            result = run_training_session(
                self._config(),
                self._servers(),
                checkpoint_root=folder,
                api=api,
                remote_store=remote,
                platform_id="lightning_ai",
                runtime_override={"device": "cpu", "batch_size": 2, "cpu_threads": 1, "mixed_precision": "none"},
                model_factory=self._model_factory,
            )
        self.assertEqual(result["state"], "dead")
        self.assertEqual(result["reason"], "lease_lost")
        self.assertIsNone(api.status["last_checkpoint_id"])

    def test_corrupt_newest_remote_checkpoint_falls_back_and_resumes(self):
        api = FakeAPI()
        storage = FakeStorage()
        remote = RemoteCheckpointStore(storage, keep_last=3)
        with tempfile.TemporaryDirectory() as first_folder:
            first = run_training_session(
                self._config(),
                self._servers(),
                checkpoint_root=first_folder,
                api=api,
                remote_store=remote,
                platform_id="lightning_ai",
                runtime_override={"device": "cpu", "batch_size": 2, "cpu_threads": 1, "mixed_precision": "none"},
                max_steps_override=2,
                model_factory=self._model_factory,
            )
        self.assertEqual(first["state"], "paused")
        newest_id = api.status["last_checkpoint_id"]
        newest_path = f"owner-1/run-1/{newest_id}/model.safetensors"
        storage.objects[("checkpoints", newest_path)] = b"corrupt"
        with tempfile.TemporaryDirectory() as second_folder:
            second = run_training_session(
                self._config(),
                self._servers(),
                checkpoint_root=second_folder,
                api=api,
                remote_store=remote,
                platform_id="lightning_ai",
                runtime_override={"device": "cpu", "batch_size": 2, "cpu_threads": 1, "mixed_precision": "none"},
                model_factory=self._model_factory,
            )
        self.assertEqual(second["state"], "finished")
        self.assertEqual(second["step"], 2)
        self.assertNotEqual(api.status["last_checkpoint_id"], newest_id)


    def test_requested_resume_checkpoint_is_verified_before_pointer_selection(self):
        api = FakeAPI()
        storage = FakeStorage()
        remote = RemoteCheckpointStore(storage, keep_last=3)
        with tempfile.TemporaryDirectory() as first_folder:
            first = run_training_session(
                self._config(),
                self._servers(),
                checkpoint_root=first_folder,
                api=api,
                remote_store=remote,
                platform_id="lightning_ai",
                runtime_override={"device": "cpu", "batch_size": 2, "cpu_threads": 1, "mixed_precision": "none"},
                max_steps_override=2,
                model_factory=self._model_factory,
            )
        self.assertEqual(first["state"], "paused")
        checkpoint_id = api.status["last_checkpoint_id"]
        api.status["requested_resume_checkpoint_id"] = checkpoint_id

        with tempfile.TemporaryDirectory() as second_folder:
            second = run_training_session(
                self._config(),
                self._servers(),
                checkpoint_root=second_folder,
                api=api,
                remote_store=remote,
                platform_id="lightning_ai",
                runtime_override={"device": "cpu", "batch_size": 2, "cpu_threads": 1, "mixed_precision": "none"},
                max_steps_override=2,
                model_factory=self._model_factory,
            )

        self.assertEqual(second["state"], "paused")
        self.assertEqual(api.selected_resume, [checkpoint_id])
        self.assertIsNone(api.status["requested_resume_checkpoint_id"])
        self.assertEqual(api.status["last_checkpoint_id"], checkpoint_id)

    def test_failed_primary_checkpoint_without_secondary_backup_does_not_release_lease(self):
        class FailingStorage(FakeStorage):
            def upload(self, bucket, path, content, content_type):
                raise SupabaseStorageError(503, "storage unavailable")

        api = FakeAPI()
        remote = RemoteCheckpointStore(FailingStorage(), keep_last=3)
        config = self._config()
        config["persistence"]["checkpoint_interval_seconds"] = 300
        with tempfile.TemporaryDirectory() as folder:
            result = run_training_session(
                config,
                self._servers(),
                checkpoint_root=folder,
                api=api,
                remote_store=remote,
                platform_id="lightning_ai",
                runtime_override={"device": "cpu", "batch_size": 2, "cpu_threads": 1, "mixed_precision": "none"},
                max_steps_override=2,
                model_factory=self._model_factory,
            )
            local = LocalCheckpointStore(folder).list_valid_checkpoints()

        self.assertEqual(result["state"], "dead")
        self.assertEqual(result["reason"], "checkpoint_not_durable_at_maximum_steps")
        self.assertTrue(local, "local checkpoint should remain for manual recovery")
        self.assertEqual(local[0]["step"], 2)
        self.assertEqual(api.released, [], "worker must not release its lease with an uncommitted checkpoint")
        self.assertIsNone(api.status["last_checkpoint_id"], "failed remote upload must not advance the durable pointer")

    def test_handoff_request_saves_and_releases_lease(self):
        api = FakeAPI(handoff=True)
        remote = RemoteCheckpointStore(FakeStorage(), keep_last=3)
        with tempfile.TemporaryDirectory() as folder:
            result = run_training_session(
                self._config(),
                self._servers(),
                checkpoint_root=folder,
                api=api,
                remote_store=remote,
                platform_id="lightning_ai",
                runtime_override={"device": "cpu", "batch_size": 2, "cpu_threads": 1, "mixed_precision": "none"},
                model_factory=self._model_factory,
            )
        self.assertEqual(result["state"], "handoff_needed")
        self.assertEqual(result["reason"], "handoff_requested")
        self.assertEqual(api.released[-1], "handoff_needed")
        self.assertEqual(api.status["last_checkpoint_step"], 0)


if __name__ == "__main__":
    unittest.main()
