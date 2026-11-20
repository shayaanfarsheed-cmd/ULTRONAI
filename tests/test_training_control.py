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

    def test_launch_refreshes_status_after_busy_flag_is_cleared(self):
        script = (ROOT / "dashboard/training-control.js").read_text()
        launch = script.split("async function launch()", 1)[1].split("async function stop()", 1)[0]
        finally_block = launch.index("} finally {")
        refresh_call = launch.rindex("await refreshStatus();")
        self.assertGreater(refresh_call, finally_block)
        self.assertIn("busy = false;", launch[finally_block:refresh_call])

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

    def test_health_diagnostic_is_owner_gated_and_never_returns_secret_values(self):
        source = (ROOT / "supabase/functions/training-control/index.ts").read_text()
        owner_check = source.index("if (user.id !== ownerId)")
        health_route = source.index('if (body.action === "health")')
        health_end = source.index("// Report missing integration configuration", health_route)
        health_block = source[health_route:health_end]
        self.assertLess(owner_check, health_route)
        self.assertIn("github_token_configured: Boolean(Deno.env.get(\"ULTRON_GITHUB_TOKEN\"))", health_block)
        self.assertNotIn("token:", health_block)
        self.assertIn('return safeError("GitHub integration is not configured.', source)
        self.assertIn('return safeError("GitHub integration is not configured. Add the server-side ULTRON_GITHUB_TOKEN secret.", 503, origin);', source)

    def test_upstream_failures_do_not_echo_upstream_details_to_clients(self):
        source = (ROOT / "supabase/functions/training-control/index.ts").read_text()
        self.assertIn('console.error("training-control request failed:", message);', source)
        self.assertIn("The control service could not complete the request.", source)
        self.assertNotIn("safeError(message.slice", source)


if __name__ == "__main__":
    unittest.main()
