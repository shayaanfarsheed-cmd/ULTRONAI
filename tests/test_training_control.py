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

    def test_only_github_actions_cpu_is_remote_launchable(self):
        source = (ROOT / "supabase/functions/training-control/index.ts").read_text()
        self.assertIn('const LAUNCHABLE_SERVER = "github_actions_cpu"', source)
        self.assertIn('body.server_id !== LAUNCHABLE_SERVER', source)
        self.assertIn('event_type: "ultron-cpu-start"', source)

    def test_dashboard_has_explicit_owner_confirmed_controls(self):
        html = (ROOT / "dashboard/index.html").read_text()
        script = (ROOT / "dashboard/training-control.js").read_text()
        self.assertIn('id="trainingStartButton"', html)
        self.assertIn('id="trainingStopButton"', html)
        self.assertIn("window.confirm(", script)
        self.assertIn('session.user.id === config.ownerUserId', script)
        self.assertNotIn("ULTRON_GITHUB_TOKEN", script)


if __name__ == "__main__":
    unittest.main()
