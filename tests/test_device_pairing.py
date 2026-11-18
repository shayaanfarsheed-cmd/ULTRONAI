import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class NoRemoteDevicePairingTests(unittest.TestCase):
    def test_dashboard_has_no_pairing_ui_or_api_client(self):
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        for forbidden in ("generatePairingCodeButton", "pairingCodePanel", "pairedDeviceList", "OWNER DEVICE REGISTRY"):
            self.assertNotIn(forbidden, html)
            self.assertNotIn(forbidden, app)
        for forbidden in ("deviceControlRequest", "createPairingCode", "loadPairedDevices", "/functions/v1/device-control/"):
            self.assertNotIn(forbidden, app)

    def test_dashboard_explains_local_only_controls_and_disabled_training(self):
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8").lower()
        self.assertIn("no device pairing or remote control", html)
        self.assertIn("training controls are not yet implemented", html)
        self.assertIn("locally", html)

    def test_local_training_copy_does_not_promise_a_remote_agent(self):
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8").lower()
        self.assertNotIn("waiting for agent", html)
        self.assertNotIn("compatible device agent must enforce", html)
        self.assertIn("does not enforce a memory cap", html)

    def test_dashboard_cannot_issue_remote_training_commands(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        for forbidden in ("switchNow", "pauseTraining", "resumeTraining", "toggleAutomaticStart",
                          "insertSwitchRequest", "updateStatus", "requestResume", "safeResume",
                          "verifyCheckpointsButton", "autoStartToggle"):
            self.assertNotIn(forbidden, app)
        for forbidden in ("switchNowButton", "pauseButton", "resumeButton", "safeResumeButton",
                          "data-checkpoint-resume", "manualHoursForm", "data-server-ready",
                          "data-server-unavailable", "autoStartToggle"):
            self.assertNotIn(forbidden, html)
        self.assertIn("read-only", html.lower())

    def test_dashboard_data_client_has_no_training_control_writes(self):
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn('apiRequest("training_status", "PATCH"', app)
        self.assertNotIn('apiRequest("switch_requests", "POST"', app)
        self.assertNotIn('apiRequest("server_log", "POST"', app)

    def test_agent_is_removed(self):
        self.assertFalse((ROOT / "agents" / "device_agent.py").exists())

    def test_pairing_backend_is_retired(self):
        function = (ROOT / "supabase" / "functions" / "device-control" / "index.ts").read_text(encoding="utf-8")
        self.assertIn("410", function)
        self.assertIn("retired", function.lower())
        self.assertNotIn("consume_ultron_pairing_challenge", function)


if __name__ == "__main__":
    unittest.main()
