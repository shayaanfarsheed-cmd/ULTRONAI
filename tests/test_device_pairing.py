import re
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
            self.assertIn(f'id="{element_id}"', html)
            self.assertIn(f'\$("{element_id}")', app)
        self.assertIn("assertOwnerAccess(session)", app)
        self.assertIn('if (view === "devices" && hasVerifiedOwnerSession())', app)
        self.assertIn("data-revoke-device", app)

    def test_pairing_backend_keeps_registry_private(self):
        migration = (ROOT / "supabase" / "migrations" / "20261118080000_device_pairing.sql").read_text(encoding="utf-8")
        self.assertIn("ENABLE ROW LEVEL SECURITY", migration)
        self.assertIn("REVOKE ALL ON public.ultron_devices, public.ultron_pairing_challenges FROM anon, authenticated", migration)
        self.assertIn("GRANT ALL ON public.ultron_devices, public.ultron_pairing_challenges TO service_role", migration)
        self.assertIn("FOR UPDATE", migration)
        self.assertIn("attempts >= 5", migration)
        self.assertIn("consumed_at", migration)
        self.assertIn("SECURITY DEFINER", migration)
        self.assertIn("GRANT EXECUTE ON FUNCTION", migration)

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
        self.assertIn("Device authentication required", function)

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
