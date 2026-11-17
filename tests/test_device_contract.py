import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "device-command.schema.json"


class DeviceCommandContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_schema_is_strict_and_allowlists_only_safe_actions(self):
        self.assertEqual(self.schema["type"], "object")
        self.assertFalse(self.schema["additionalProperties"])
        self.assertEqual(
            self.schema["properties"]["action"]["enum"],
            ["status", "start", "pause", "resume", "stop"],
        )
        self.assertFalse(self.schema["properties"]["parameters"]["additionalProperties"])

    def test_command_envelope_requires_identity_expiry_and_idempotency(self):
        self.assertEqual(
            set(self.schema["required"]),
            {"id", "device_id", "action", "issued_at", "expires_at", "nonce", "parameters"},
        )
        self.assertEqual(self.schema["properties"]["id"]["format"], "uuid")
        self.assertEqual(self.schema["properties"]["device_id"]["format"], "uuid")
        self.assertGreaterEqual(self.schema["properties"]["nonce"]["minLength"], 32)

    def test_start_requires_memory_budget_and_fencing_token(self):
        rule = self.schema["allOf"][0]["then"]
        self.assertIn("fencing_token", rule["required"])
        self.assertIn("memory_limit_mb", rule["properties"]["parameters"]["required"])
        self.assertEqual(
            self.schema["properties"]["parameters"]["properties"]["memory_limit_mb"]["maximum"],
            10240,
        )

    def test_run_controls_require_run_id_and_fencing_token(self):
        rule = self.schema["allOf"][1]["then"]
        self.assertIn("fencing_token", rule["required"])
        self.assertIn("run_id", rule["properties"]["parameters"]["required"])

    def test_status_command_cannot_carry_parameters(self):
        rule = self.schema["allOf"][2]["then"]
        self.assertEqual(rule["properties"]["parameters"]["maxProperties"], 0)

    def test_contract_never_accepts_arbitrary_command_text(self):
        parameters = self.schema["properties"]["parameters"]["properties"]
        self.assertNotIn("command", parameters)
        self.assertNotIn("shell", parameters)
        self.assertNotIn("script", parameters)
        self.assertNotIn("executable", parameters)


if __name__ == "__main__":
    unittest.main()
