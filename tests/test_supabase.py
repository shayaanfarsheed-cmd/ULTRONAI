import unittest
import uuid
from datetime import timedelta


from ultron_supabase import (
    LeaseLostError,
    SupabaseRESTClient,
    TrainingControlAPI,
    iso_utc,
    parse_timestamp,
    utc_now,
)


class FakeClient:
    def __init__(self):
        self.rows = {}
        self.logs = []
        self.switches = []
        self.requests = []

    def _matches(self, row, filters):
        for key, expression in filters.items():
            if expression.startswith("eq."):
                if str(row.get(key)) != expression[3:]:
                    return False
            elif expression == "is.null":
                if row.get(key) is not None:
                    return False
            elif expression == "not.is.null":
                if row.get(key) is None:
                    return False
            elif expression.startswith("lt."):
                value = row.get(key)
                if value is None or value >= expression[3:]:
                    return False
            elif expression.startswith("gt."):
                value = row.get(key)
                if value is None or value <= expression[3:]:
                    return False
            elif expression.startswith("in.(") and expression.endswith(")"):
                allowed = expression[4:-1].split(",")
                if str(row.get(key)) not in allowed:
                    return False
            else:
                raise AssertionError(expression)
        return True

    def rpc(self, function, params):
        self.requests.append(("rpc", function, dict(params)))
        if function == "get_or_create_active_run":
            owner_id = params["p_owner_id"]
            active = [row for row in self.rows.values() if row.get("owner_id") == owner_id and row.get("state") != "finished"]
            if active:
                active.sort(key=lambda row: row.get("updated_at", ""), reverse=True)
                return {"run_id": active[0]["run_id"], "owner_id": owner_id, "state": active[0]["state"]}
            run_id = str(uuid.uuid4())
            self.rows[run_id] = {
                "run_id": run_id,
                "owner_id": owner_id,
                "state": "paused",
                "current_step": 0,
                "fencing_token": 0,
                "updated_at": iso_utc(),
            }
            return {"run_id": run_id, "owner_id": owner_id, "state": "paused"}

        if function == "acquire_training_lease":
            row = self.rows.get(params["p_run_id"])
            if row is None or row.get("owner_id") != params["p_owner_id"]:
                return {"granted": False, "reason": "run_not_found"}
            now = utc_now()
            for other in self.rows.values():
                if other is row or other.get("owner_id") != params["p_owner_id"] or not other.get("lease_holder"):
                    continue
                expiry = parse_timestamp(other.get("lease_expires_at"))
                if expiry and expiry > now:
                    return {
                        "granted": False,
                        "reason": "another_run_lease_held",
                        "run_id": other["run_id"],
                        "lease_holder": other["lease_holder"],
                        "lease_expires_at": other["lease_expires_at"],
                        "fencing_token": other.get("fencing_token", 0),
                    }
                other["lease_holder"] = None
                other["lease_expires_at"] = None
                other["active_session_id"] = None
                other["state"] = "dead"
            expiry = parse_timestamp(row.get("lease_expires_at"))
            worker_id = params["p_worker_id"]
            if row.get("lease_holder") == worker_id and expiry and expiry > now:
                row["lease_expires_at"] = iso_utc(now + timedelta(seconds=params["p_ttl_seconds"]))
                return {
                    "granted": True,
                    "run_id": row["run_id"],
                    "worker_id": worker_id,
                    "fencing_token": row["fencing_token"],
                    "lease_expires_at": row["lease_expires_at"],
                    "session_id": row.get("active_session_id"),
                    "idempotent_retry": True,
                }
            if row.get("lease_holder") and expiry and expiry > now:
                return {
                    "granted": False,
                    "reason": "lease_held",
                    "lease_holder": row["lease_holder"],
                    "lease_expires_at": row["lease_expires_at"],
                    "fencing_token": row.get("fencing_token", 0),
                }
            token = int(row.get("fencing_token", 0)) + 1
            session_id = str(uuid.uuid4())
            expiry_text = iso_utc(now + timedelta(seconds=params["p_ttl_seconds"]))
            row.update({
                "current_server": params["p_server_id"],
                "lease_holder": worker_id,
                "lease_expires_at": expiry_text,
                "fencing_token": token,
                "active_session_id": session_id,
                "session_started_at": iso_utc(now),
                "session_limit_seconds": params.get("p_session_limit_seconds"),
                "session_time_left_seconds": params.get("p_session_limit_seconds"),
                "last_heartbeat_at": iso_utc(now),
                "state": "running",
                "pause_requested": False,
                "handoff_requested": False,
                "updated_at": iso_utc(now),
            })
            self.logs.append({
                "owner_id": params["p_owner_id"],
                "run_id": params["p_run_id"],
                "session_id": session_id,
                "server_name": params["p_server_id"],
                "started_at": iso_utc(now),
                "ended_at": None,
                "gpu_seconds": 0,
                "end_reason": None,
                "manual": False,
                "details": {"worker_id": worker_id, "device": params.get("p_device", "cpu")},
            })
            return {
                "granted": True,
                "run_id": row["run_id"],
                "worker_id": worker_id,
                "fencing_token": token,
                "lease_expires_at": expiry_text,
                "session_id": session_id,
                "idempotent_retry": False,
            }

        if function == "heartbeat_training_lease":
            row = self.rows.get(params["p_run_id"])
            expiry = parse_timestamp(row.get("lease_expires_at")) if row else None
            if (
                row is None
                or row.get("owner_id") != params["p_owner_id"]
                or row.get("lease_holder") != params["p_worker_id"]
                or int(row.get("fencing_token", 0)) != int(params["p_fencing_token"])
                or expiry is None
                or expiry <= utc_now()
            ):
                return {"ok": False, "reason": "lease_lost"}
            now = utc_now()
            row.update({
                "lease_expires_at": iso_utc(now + timedelta(seconds=params["p_ttl_seconds"])),
                "last_heartbeat_at": iso_utc(now),
                "current_step": max(int(row.get("current_step", 0)), int(params["p_current_step"])),
                "loss": params.get("p_loss"),
                "learning_rate": params.get("p_learning_rate"),
                "current_topic": params.get("p_current_topic"),
                "difficulty": params.get("p_difficulty"),
                "data_position": params.get("p_data_position"),
                "data_epoch": params.get("p_data_epoch"),
                "accuracy_by_topic": params.get("p_accuracy_by_topic") or {},
                "curriculum_state": params.get("p_curriculum_state") or {},
                "session_time_left_seconds": params.get("p_session_time_left_seconds"),
                "updated_at": iso_utc(now),
            })
            return {
                "ok": True,
                "pause_requested": bool(row.get("pause_requested")),
                "handoff_requested": bool(row.get("handoff_requested")),
                "automatic_start_enabled": bool(row.get("automatic_start_enabled")),
                "state": row.get("state"),
                "lease_expires_at": row["lease_expires_at"],
            }

        if function == "commit_training_checkpoint":
            row = self.rows.get(params["p_run_id"])
            expiry = parse_timestamp(row.get("lease_expires_at")) if row else None
            if (
                row is None
                or row.get("owner_id") != params["p_owner_id"]
                or row.get("lease_holder") != params["p_worker_id"]
                or int(row.get("fencing_token", 0)) != int(params["p_fencing_token"])
                or expiry is None
                or expiry <= utc_now()
                or (row.get("last_checkpoint_step") is not None and int(params["p_step"]) < int(row["last_checkpoint_step"]))
            ):
                return {"ok": False, "reason": "lease_lost_or_checkpoint_regression"}
            row.update({
                "last_checkpoint_id": params["p_checkpoint_id"],
                "last_checkpoint_step": params["p_step"],
                "last_checkpoint_size_bytes": params["p_size_bytes"],
                "last_checkpoint_verified": True,
                "last_checkpoint_manifest_sha256": params["p_manifest_sha256"],
                "current_step": max(int(row.get("current_step", 0)), int(params["p_step"])),
                "current_topic": params.get("p_current_topic"),
                "difficulty": params.get("p_difficulty"),
                "data_position": params.get("p_data_position"),
                "data_epoch": params.get("p_data_epoch"),
                "loss": params.get("p_loss"),
                "learning_rate": params.get("p_learning_rate"),
                "accuracy_by_topic": params.get("p_accuracy_by_topic") or {},
                "curriculum_state": params.get("p_curriculum_state") or {},
                "last_heartbeat_at": iso_utc(),
            })
            return {
                "ok": True,
                "checkpoint_id": row["last_checkpoint_id"],
                "step": row["last_checkpoint_step"],
                "verified": True,
                "manifest_sha256": row["last_checkpoint_manifest_sha256"],
            }

        if function == "release_training_lease":
            row = self.rows.get(params["p_run_id"])
            if (
                row is None
                or row.get("owner_id") != params["p_owner_id"]
                or row.get("lease_holder") != params["p_worker_id"]
                or int(row.get("fencing_token", 0)) != int(params["p_fencing_token"])
            ):
                return {"ok": False, "reason": "lease_lost"}
            session_id = row.get("active_session_id")
            for log in self.logs:
                if log.get("session_id") == session_id and log.get("ended_at") is None:
                    log["ended_at"] = iso_utc()
                    log["end_reason"] = params["p_end_reason"]
            row.update({
                "lease_holder": None,
                "lease_expires_at": None,
                "active_session_id": None,
                "state": params["p_final_state"],
                "pause_requested": False,
                "handoff_requested": params["p_final_state"] == "handoff_needed",
                "updated_at": iso_utc(),
            })
            return {"ok": True, "state": row["state"], "current_step": row.get("current_step", 0), "lease_released": True}

        raise AssertionError(f"Unexpected RPC: {function}")

    def select(self, table, filters=None, columns="*", limit=None, order=None):
        self.requests.append(("select", table, dict(filters or {})))
        if table == "training_status":
            values = list(self.rows.values())
        elif table == "server_log":
            values = list(self.logs)
        elif table == "switch_requests":
            values = list(self.switches)
        else:
            values = []
        selected = [dict(row) for row in values if self._matches(row, filters or {})]
        if order == "updated_at.desc":
            selected.sort(key=lambda row: row.get("updated_at") or "", reverse=True)
        if order == "requested_at.asc":
            selected.sort(key=lambda row: row.get("requested_at") or "")
        return selected[:limit] if limit else selected

    def insert(self, table, row):
        self.requests.append(("insert", table, dict(row)))
        if table == "training_status":
            if row["run_id"] in self.rows:
                raise RuntimeError("duplicate run")
            if any(item["owner_id"] == row["owner_id"] and item.get("lease_holder") for item in self.rows.values()):
                raise RuntimeError("unique active owner lease")
            self.rows[row["run_id"]] = dict(row)
            return [dict(row)]
        if table == "server_log":
            self.logs.append(dict(row))
            return [dict(row)]
        if table == "switch_requests":
            self.switches.append(dict(row))
            return [dict(row)]
        return []

    def patch(self, table, filters, values):
        self.requests.append(("patch", table, dict(filters), dict(values)))
        if table == "training_status":
            rows = list(self.rows.values())
        elif table == "server_log":
            rows = self.logs
        elif table == "switch_requests":
            rows = self.switches
        else:
            rows = []
        updated = []
        for row in rows:
            if self._matches(row, filters):
                row.update(values)
                updated.append(dict(row))
        return updated


class SupabaseLeaseTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeClient()
        self.api = TrainingControlAPI(self.client, "owner-123")
        for run_id in ("run-1", "run-2"):
            self.client.rows[run_id] = {
                "run_id": run_id,
                "owner_id": "owner-123",
                "state": "paused",
                "current_step": 0,
                "fencing_token": 0,
                "updated_at": iso_utc(),
                "pause_requested": False,
                "handoff_requested": False,
            }

    def test_first_worker_acquires_new_lease(self):
        result = self.api.acquire_lease("run-1", "Kaggle", "worker-a", ttl_seconds=120)
        self.assertTrue(result.acquired)
        self.assertEqual(result.fencing_token, 1)
        self.assertEqual(self.client.rows["run-1"]["lease_holder"], "worker-a")

    def test_second_worker_waits_while_lease_is_valid(self):
        self.api.acquire_lease("run-1", "Kaggle", "worker-a", ttl_seconds=120)
        result = self.api.acquire_lease("run-1", "Colab", "worker-b", ttl_seconds=120)
        self.assertFalse(result.acquired)
        self.assertEqual(result.lease_holder, "worker-a")

    def test_expired_lease_takeover_increments_fencing_token(self):
        self.api.acquire_lease("run-1", "Kaggle", "worker-a", ttl_seconds=120)
        self.client.rows["run-1"]["lease_expires_at"] = iso_utc(utc_now() - timedelta(seconds=5))
        result = self.api.acquire_lease("run-1", "Colab", "worker-b", ttl_seconds=120)
        self.assertTrue(result.acquired)
        self.assertEqual(result.fencing_token, 2)
        self.assertEqual(self.client.rows["run-1"]["lease_holder"], "worker-b")

    def test_old_worker_cannot_renew_after_takeover(self):
        self.api.acquire_lease("run-1", "Kaggle", "worker-a", ttl_seconds=120)
        self.client.rows["run-1"]["lease_expires_at"] = iso_utc(utc_now() - timedelta(seconds=5))
        self.api.acquire_lease("run-1", "Colab", "worker-b", ttl_seconds=120)
        renewed = self.api.renew_lease("run-1", "worker-a", 1, ttl_seconds=120)
        self.assertFalse(renewed)

    def test_checkpoint_commit_requires_current_lease(self):
        self.api.acquire_lease("run-1", "Kaggle", "worker-a", ttl_seconds=120)
        result = self.api.commit_checkpoint(
            "run-1",
            "worker-a",
            1,
            "ckpt-0001",
            100,
            {
                "step": 1,
                "current_topic": "fractions",
                "difficulty": 1,
                "data_position": 4,
                "data_epoch": 0,
                "loss": 1.2,
                "accuracy_by_topic": {},
                "curriculum_state": {},
                "learning_rate": 0.0003,
            },
            manifest_sha256="a" * 64,
        )
        self.assertEqual(result["last_checkpoint_id"], "ckpt-0001")
        self.assertEqual(result["last_checkpoint_step"], 1)
        with self.assertRaises(LeaseLostError):
            self.api.commit_checkpoint(
                "run-1",
                "worker-b",
                2,
                "ckpt-0002",
                100,
                {"step": 2, "current_topic": "fractions", "difficulty": 1, "data_position": 8},
                manifest_sha256="b" * 64,
            )

    def test_release_clears_lease_and_preserves_run(self):
        self.api.acquire_lease("run-1", "Kaggle", "worker-a", ttl_seconds=120)
        self.assertTrue(self.api.release_lease("run-1", "worker-a", 1, "handoff_needed"))
        row = self.client.rows["run-1"]
        self.assertIsNone(row["lease_holder"])
        self.assertIsNone(row["lease_expires_at"])
        self.assertEqual(row["state"], "handoff_needed")

    def test_new_run_cannot_take_second_lease_for_same_owner(self):
        self.api.acquire_lease("run-1", "Kaggle", "worker-a", ttl_seconds=120)
        result = self.api.acquire_lease("run-2", "Colab", "worker-b", ttl_seconds=120)
        self.assertFalse(result.acquired)
        self.assertEqual(result.run_id, "run-1")

    def test_session_log_start_and_end(self):
        self.api.acquire_lease("run-1", "Kaggle", "worker-a", ttl_seconds=120)
        session_id = self.api.start_session("run-1", "Kaggle")
        self.assertTrue(self.api.end_session(session_id, 120.5, "handoff"))
        self.assertEqual(self.client.logs[0]["gpu_seconds"], 120.5)
        self.assertEqual(self.client.logs[0]["end_reason"], "handoff")

    def test_client_redacts_key_and_uses_custom_schema_headers(self):
        captured = {}

        class Response:
            headers = {"Content-Type": "application/json"}
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return b"[]"

        def opener(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return Response()

        client = SupabaseRESTClient("https://example.supabase.co", "sb_secret_never-print", opener=opener)
        client.request("GET", "training_status", {"select": "*"})
        self.assertNotIn("sb_secret_never-print", repr(client))
        self.assertEqual(captured["request"].get_header("Accept-profile"), "training_api")
        self.assertEqual(captured["request"].get_header("Apikey"), "sb_secret_never-print")
        self.assertIsNone(captured["request"].get_header("Authorization"))
        self.assertIn("/rest/v1/training_status", captured["request"].full_url)

    def test_switch_request_is_completed_on_target_first_heartbeat(self):
        self.api.acquire_lease("run-1", "Kaggle", "worker-a", ttl_seconds=120)
        request_id = self.api.create_switch_request("run-1", "kaggle", "google_colab", "user_requested")
        self.assertEqual(len(self.client.switches), 1)
        self.api.assign_switch_target(request_id, "google_colab", {"manual": True})
        completed = self.api.mark_switch_requests_done("run-1", "google_colab")
        self.assertEqual(completed, 1)
        self.assertEqual(self.client.switches[0]["result"], "done")

    def test_server_status_updates_only_the_requested_server_entry(self):
        self.api.acquire_lease("run-1", "Kaggle", "worker-a", ttl_seconds=120)
        self.assertTrue(self.api.update_server_status(
            "run-1",
            "kaggle",
            "unavailable_until",
            reason="maintenance",
            unavailable_until="2026-11-18T12:00:00Z",
        ))
        status = self.client.rows["run-1"]["server_statuses"]["kaggle"]
        self.assertEqual(status["status"], "unavailable_until")
        self.assertEqual(status["reason"], "maintenance")


if __name__ == "__main__":
    unittest.main()
