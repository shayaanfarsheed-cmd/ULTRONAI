import unittest
from datetime import timedelta

from ultron_supabase import (
    LeaseLostError,
    SupabaseRESTClient,
    TrainingControlAPI,
    iso_utc,
    utc_now,
)


class FakeClient:
    def __init__(self):
        self.rows = {}
        self.logs = []
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
            else:
                raise AssertionError(expression)
        return True

    def select(self, table, filters=None, columns="*", limit=None, order=None):
        self.requests.append(("select", table, dict(filters or {})))
        if table == "training_status":
            values = list(self.rows.values())
        elif table == "server_log":
            values = list(self.logs)
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
        return []

    def patch(self, table, filters, values):
        self.requests.append(("patch", table, dict(filters), dict(values)))
        if table == "training_status":
            rows = list(self.rows.values())
        elif table == "server_log":
            rows = self.logs
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
        self.assertIn("/rest/v1/training_status", captured["request"].full_url)


if __name__ == "__main__":
    unittest.main()
