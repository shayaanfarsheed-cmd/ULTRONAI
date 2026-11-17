import unittest
from datetime import datetime, timezone

from ultron_switcher import (
    _auto_start_allowed,
    calculate_quota_usage,
    run_switcher,
    select_next_server,
)


class FakeSwitchAPI:
    def __init__(self, status, logs=None, requests=None):
        self.status = dict(status)
        self.logs = list(logs or [])
        self.requests = list(requests or [])
        self.created = []
        self.updated = []
        self.server_updates = []
        self.handoff = False

    def find_active_status(self):
        return dict(self.status)

    def get_status(self, run_id):
        return dict(self.status)

    def mark_dead_if_stale(self, run_id, stale_after_seconds):
        return False

    def server_logs_since(self, since_iso):
        return list(self.logs)

    def switch_requests_since(self, since_iso):
        return list(self.requests)

    def waiting_switch_requests(self, limit=20):
        return [dict(row) for row in self.requests if row.get("result") == "waiting"][:limit]

    def create_switch_request(self, run_id, from_server, to_server, reason, automatic=False, metadata=None):
        row = {
            "id": f"switch-{len(self.created)+1}",
            "run_id": run_id,
            "from_server": from_server,
            "to_server": to_server,
            "reason": reason,
            "result": "waiting",
            "automatic": automatic,
            "metadata": metadata or {},
        }
        self.created.append(row)
        self.requests.append(row)
        return row["id"]

    def assign_switch_target(self, request_id, server_id, metadata=None):
        row = next(item for item in self.requests if item["id"] == request_id)
        row["to_server"] = server_id
        row["metadata"] = metadata or {}
        return True

    def update_switch_request(self, request_id, result, **kwargs):
        row = next(item for item in self.requests if item["id"] == request_id)
        row["result"] = result
        row.update(kwargs)
        self.updated.append((request_id, result))
        return True

    def update_server_status(self, run_id, server_id, status, **kwargs):
        self.server_updates.append((server_id, status, kwargs))
        return True

    def request_handoff(self, run_id, handoff=True):
        self.handoff = handoff
        return True


def sample_servers():
    return [
        {
            "id": "kaggle",
            "order": 1,
            "name": "Kaggle",
            "role": "primary_gpu",
            "enabled": True,
            "current_status": "unknown",
            "automatic_start": "yes",
            "notebook_open_url": "https://www.kaggle.com/code",
            "limits": {"quota_period": "weekly", "weekly_gpu_hours_baseline": 30},
        },
        {
            "id": "google_colab",
            "order": 2,
            "name": "Google Colab",
            "role": "backup_gpu",
            "enabled": True,
            "current_status": "unknown",
            "automatic_start": "no",
            "notebook_open_url": "https://colab.research.google.com/",
            "limits": {"quota_period": "dynamic", "session_limit_hours": 12},
        },
        {
            "id": "github_actions_cpu",
            "order": 3,
            "name": "GitHub Actions CPU",
            "role": "cpu_fallback",
            "enabled": True,
            "current_status": "unknown",
            "automatic_start": "yes",
            "notebook_open_url": "https://github.com/example/repo/actions",
            "limits": {"quota_period": "public", "job_execution_limit_hours": 6},
        },
    ]


class SwitcherTests(unittest.TestCase):
    def test_weekly_quota_usage_uses_gpu_seconds_and_period(self):
        now = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
        logs = [{
            "server_name": "Kaggle",
            "started_at": "2026-11-16T08:00:00Z",
            "ended_at": "2026-11-16T11:00:00Z",
            "gpu_seconds": 27 * 3600,
            "details": {"server_id": "kaggle", "compute_device": "cuda"},
        }]
        usage = calculate_quota_usage(sample_servers(), logs, now)
        self.assertEqual(usage["kaggle"]["used_hours"], 27.0)
        self.assertEqual(usage["kaggle"]["usage_percent"], 90.0)
        self.assertTrue(usage["kaggle"]["warning"])
        self.assertIsNone(usage["google_colab"]["usage_percent"])

    def test_selector_picks_first_ready_server_in_order(self):
        servers = sample_servers()
        statuses = {"google_colab": {"status": "ready"}, "github_actions_cpu": {"status": "ready"}}
        decision = select_next_server(
            servers,
            statuses,
            {},
            exclude_server_id="kaggle",
            fallback_server_id="github_actions_cpu",
        )
        self.assertEqual(decision["server"]["id"], "google_colab")

    def test_selector_uses_cpu_fallback_when_no_gpu_server_is_ready(self):
        servers = sample_servers()
        statuses = {"github_actions_cpu": {"status": "unknown"}}
        decision = select_next_server(
            servers,
            statuses,
            {},
            exclude_server_id="kaggle",
            fallback_server_id="github_actions_cpu",
        )
        self.assertEqual(decision["server"]["id"], "github_actions_cpu")
        self.assertTrue(decision["requires_manual_check"])

    def test_selector_skips_quota_and_kicked_out_servers(self):
        servers = sample_servers()
        statuses = {
            "google_colab": {"status": "kicked_out", "kicked_out_until": "2026-11-18T00:00:00Z"},
            "github_actions_cpu": {"status": "out_of_quota"},
        }
        decision = select_next_server(
            servers,
            statuses,
            {"kaggle": {"usage_percent": 95}},
            threshold_percent=90,
            exclude_server_id=None,
            fallback_server_id="github_actions_cpu",
            now=datetime(2026, 11, 17, tzinfo=timezone.utc),
        )
        self.assertIsNone(decision)

    def test_switcher_produces_guided_instruction_for_ready_colab(self):
        now = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
        status = {
            "run_id": "run-1",
            "state": "handoff_needed",
            "current_server": "Kaggle",
            "lease_expires_at": None,
            "last_heartbeat_at": "2026-11-17T11:00:00Z",
            "automatic_start_enabled": False,
            "server_statuses": {
                "google_colab": {"status": "ready"},
                "github_actions_cpu": {"status": "ready"},
            },
        }
        api = FakeSwitchAPI(status)
        config = {
            "monitoring": {"stale_run_after_seconds": 720},
            "switching": {"quota_switch_threshold_percent": 90, "automatic_switching_enabled": True},
            "server_rotation": {"fallback_server_id": "github_actions_cpu"},
        }
        result = run_switcher(config, {"servers": sample_servers()}, api=api, environment={}, now=now)
        self.assertEqual(result["state"], "guided_switch")
        self.assertEqual(result["target_server"], "google_colab")
        self.assertIn("Runtime > Run all", result["instruction"])
        self.assertEqual(api.requests[0]["to_server"], "google_colab")

    def test_quota_at_ninety_percent_requests_handoff(self):
        now = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
        status = {
            "run_id": "run-1",
            "state": "running",
            "current_server": "Kaggle",
            "lease_expires_at": "2026-11-17T12:05:00Z",
            "last_heartbeat_at": "2026-11-17T11:59:30Z",
            "automatic_start_enabled": False,
            "server_statuses": {},
        }
        logs = [{
            "server_name": "Kaggle",
            "started_at": "2026-11-16T08:00:00Z",
            "ended_at": "2026-11-16T11:00:00Z",
            "gpu_seconds": 27 * 3600,
            "details": {"server_id": "kaggle", "compute_device": "cuda"},
        }]
        api = FakeSwitchAPI(status, logs=logs)
        config = {
            "monitoring": {"stale_run_after_seconds": 720},
            "switching": {"quota_switch_threshold_percent": 90},
        }
        result = run_switcher(config, {"servers": sample_servers()}, api=api, now=now)
        self.assertEqual(result["state"], "handoff_requested")
        self.assertTrue(api.handoff)
        self.assertEqual(api.created[0]["reason"], "quota")

    def test_auto_start_requires_dashboard_toggle_ready_status_and_credentials(self):
        server = sample_servers()[0]
        allowed, _ = _auto_start_allowed(
            server,
            {"status": "ready"},
            {"automatic_start_enabled": True},
            {"switching": {
                "automatic_switching_enabled": True,
                "platform_allowlist": ["kaggle"],
                "maximum_automatic_starts_per_day": 3,
                "automatic_start_cooldown_seconds": 1200,
            }},
            [],
            datetime(2026, 11, 17, tzinfo=timezone.utc),
            {"KAGGLE_USERNAME": "example_user", "KAGGLE_KEY": "example_key"},
        )
        self.assertTrue(allowed)


if __name__ == "__main__":
    unittest.main()
