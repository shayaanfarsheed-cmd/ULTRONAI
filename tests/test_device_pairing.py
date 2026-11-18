import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DevicePairingStaticTests(unittest.TestCase):
    def test_dashboard_pairing_controls_are_present_and_owner_gated(self):
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        for element_id in (
            "generatePairingCodeButton", "pairingCodePanel", "pairingCode",
            "pairingChallengeId", "copyPairingCodeButton", "pairedDeviceList",
            "refreshDevicesButton", "deviceCountMetric",
        ):
            self.assertIn('id="' + element_id + '"', html)
            self.assertIn('$("' + element_id + '")', app)
        self.assertIn("assertOwnerAccess(session)", app)
        self.assertIn("generation !== state.authGeneration", app)
        self.assertIn("button.disabled = !hasVerifiedOwnerSession()", app)
        self.assertIn('if (view === "devices" && hasVerifiedOwnerSession())', app)
        self.assertIn("data-revoke-device", app)
        self.assertIn("Challenge ID: ", app)
        self.assertIn("Pairing code: ", app)
        self.assertIn("DEVICE_CONTROL_ENABLED = CONFIG.deviceControlEnabled === true", app)

    def test_pairing_backend_keeps_registry_private(self):
        migration = (ROOT / "supabase" / "migrations" / "20261118080000_device_pairing.sql").read_text(encoding="utf-8").lower()
        self.assertIn("enable row level security", migration)
        self.assertIn("revoke all on public.ultron_devices, public.ultron_pairing_challenges from anon, authenticated", migration)
        self.assertIn("grant all on public.ultron_devices, public.ultron_pairing_challenges to service_role", migration)
        self.assertIn("for update", migration)
        self.assertIn("attempts >= 5", migration)
        self.assertIn("consumed_at", migration)
        self.assertIn("security invoker", migration)
        self.assertIn("grant execute on function", migration)
        self.assertIn("ultron_pairing_rate_limits", migration)
        self.assertIn("consume_ultron_pairing_rate_limit", migration)

    def test_edge_function_verifies_owner_and_uses_one_time_device_tokens(self):
        function = (ROOT / "supabase" / "functions" / "device-control" / "index.ts").read_text(encoding="utf-8")
        self.assertIn("client.auth.getUser()", function)
        self.assertIn("crypto.getRandomValues", function)
        self.assertIn("consume_ultron_pairing_challenge", function)
        self.assertIn('route === "heartbeat"', function)
        self.assertIn('route === "devices"', function)
        self.assertIn('status: "revoked"', function)
        self.assertIn("Cache-Control", function)
        self.assertNotIn("console.log", function)

    def test_edge_function_jwt_is_verified_in_handler_not_gateway(self):
        config = (ROOT / "supabase" / "config.toml").read_text(encoding="utf-8")
        function = (ROOT / "supabase" / "functions" / "device-control" / "index.ts").read_text(encoding="utf-8")
        self.assertIn("[functions.device-control]", config)
        self.assertIn("verify_jwt = false", config)
        self.assertIn("ownerFromRequest(request)", function)
        self.assertIn("ULTRON_OWNER_USER_ID", function)
        self.assertIn("data.user.id !== OWNER_USER_ID", function)
        self.assertIn("Array.isArray(capabilities)", function)
        self.assertIn("allowPairingRequest(request, \"redeem\", 10)", function)
        self.assertIn("cf-connecting-ip", function)
        self.assertNotIn('"ios"', function)
        self.assertNotIn('"ipados"', function)
        self.assertNotIn('"android"', function)
        self.assertIn("Device authentication required", function)

    def test_agent_keeps_device_token_in_memory_and_supports_heartbeat_only(self):
        agent = (ROOT / "agents" / "device_agent.py").read_text(encoding="utf-8")
        compile(agent, "agents/device_agent.py", "exec")
        self.assertIn("getpass.getpass", agent)
        self.assertIn("heartbeat", agent)
        self.assertIn("HEARTBEAT_SECONDS = 60", agent)
        self.assertIn("ULTRON_DEVICE_TOKEN", agent)
        self.assertNotIn("write_text(", agent)
        self.assertNotIn("print(token)", agent)
        self.assertNotIn("device_token", agent.replace('data.get("device_token")', ""))

    def test_dashboard_does_not_contain_service_role_or_device_token(self):
        dashboard = ROOT / "dashboard"
        for path in dashboard.iterdir():
            if path.is_file():
                source = path.read_text(encoding="utf-8")
                self.assertNotRegex(source, r"sb_secret_[A-Za-z0-9]{12,}")
                self.assertNotIn("SUPABASE_SERVICE_ROLE_KEY", source)
                self.assertNotIn("device_token", source)


if __name__ == "__main__":
    unittest.main()
