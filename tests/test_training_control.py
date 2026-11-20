import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TrainingControlSecurityContractTests(unittest.TestCase):
    def test_edge_function_is_owner_gated_and_origin_restricted(self):
        source = (ROOT / "supabase/functions/training-control/index.ts").read_text()
        self.assertIn('const ALLOWED_ORIGIN = "https://shayaanfarsheed-cmd.github.io"', source)
        self.assertIn('user.id !== ownerId', source)
        self.assertIn('Deno.env.get("ULTRON_GITHUB_TOKEN")', source)
        self.assertNotIn("device-control", source)

    def test_github_actions_is_the_only_remote_launch_target(self):
        source = (ROOT / "supabase/functions/training-control/index.ts").read_text()
        self.assertIn('const CPU_SERVER_ID = "github_actions_cpu"', source)
        self.assertIn('id === CPU_SERVER_ID', source)
        self.assertIn('"ultron-cpu-diagnostic"', source)
        self.assertNotIn("lightning", source.lower())

    def test_dashboard_has_explicit_owner_confirmed_controls(self):
        html = (ROOT / "dashboard/index.html").read_text()
        script = (ROOT / "dashboard/training-control.js").read_text()
        self.assertIn('id="trainingStartButton"', html)
        self.assertIn('id="trainingStopButton"', html)
        self.assertIn("window.confirm(", script)
        self.assertIn('session.user.id === config.ownerUserId', script)
        self.assertNotIn("ULTRON_GITHUB_TOKEN", script)


    def test_stop_confirmation_describes_diagnostic_without_checkpoint_claims(self):
        script = (ROOT / "dashboard/training-control.js").read_text()
        self.assertIn("Cancel the currently queued or running ULTRON CPU diagnostic?", script)
        self.assertIn("does not train the model or create, modify, or delete checkpoints", script)
        self.assertNotIn("latest durable checkpoint will be retained", script)

    def test_registry_exposes_only_github_actions_remote_and_manual_colab(self):
        import json
        servers = json.loads((ROOT / "servers.json").read_text())
        self.assertEqual([item["id"] for item in servers["servers"]], ["github_actions_cpu", "google_colab"])
        self.assertEqual(servers["servers"][0]["role"], "primary_cpu_runtime")
        self.assertFalse(servers["servers"][1]["remote_control_allowed"])


if __name__ == "__main__":
    unittest.main()
