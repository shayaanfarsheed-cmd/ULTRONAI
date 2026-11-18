import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from ultron_device_contract import MAX_COMMAND_TTL, validate_command


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "device-command.schema.json"
NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
DEVICE_ID = "b7e1d52e-20ef-4c73-8f3b-3c3d5e7a9b11"
RUN_ID = "d2a3c1e0-8b7f-4d5a-9c2e-1f6a7b8c9d10"
COMMAND_ID = "a1b2c3d4-e5f6-4789-8abc-def012345678"
NONCE = "0123456789abcdef0123456789abcdef"


def timestamp(value):
    return value.isoformat().replace("+00:00", "Z")


def command_for(action):
    command = {
        "id": COMMAND_ID,
        "device_id": DEVICE_ID,
        "action": action,
        "issued_at": timestamp(NOW - timedelta(seconds=10)),
        "expires_at": timestamp(NOW + timedelta(seconds=30)),
        "nonce": NONCE,
        "parameters": {},
    }
    if action == "start":
        command["fencing_token"] = 7
        command["parameters"] = {"memory_limit_mb": 2048}
    elif action in {"pause", "resume", "stop"}:
        command["fencing_token"] = 7
        command["parameters"] = {"run_id": RUN_ID}
    return command


class DeviceCommandContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.validator = Draft202012Validator(cls.schema, format_checker=FormatChecker())

    def assert_schema_invalid(self, command):
        self.assertTrue(list(self.validator.iter_errors(command)), command)

    def test_schema_is_valid_draft_2020_12(self):
        Draft202012Validator.check_schema(self.schema)

    def test_all_five_allowlisted_actions_validate(self):
        for action in ("status", "start", "pause", "resume", "stop"):
            with self.subTest(action=action):
                self.validator.validate(command_for(action))

    def test_runtime_validator_accepts_each_valid_action(self):
        for action in ("status", "start", "pause", "resume", "stop"):
            with self.subTest(action=action):
                validate_command(command_for(action), now=NOW, current_fencing_token=7)

    def test_unknown_action_is_rejected(self):
        candidate = command_for("status")
        candidate["action"] = "execute"
        self.assert_schema_invalid(candidate)

    def test_unknown_envelope_and_parameter_properties_are_rejected(self):
        candidate = command_for("status")
        candidate["shell"] = "echo unsafe"
        self.assert_schema_invalid(candidate)
        candidate = command_for("status")
        candidate["parameters"]["script"] = "unsafe"
        self.assert_schema_invalid(candidate)

    def test_missing_required_envelope_field_is_rejected(self):
        candidate = command_for("status")
        del candidate["device_id"]
        self.assert_schema_invalid(candidate)

    def test_invalid_uuids_are_rejected(self):
        for field in ("id", "device_id"):
            with self.subTest(field=field):
                candidate = command_for("status")
                candidate[field] = "not-a-uuid"
                self.assert_schema_invalid(candidate)
        candidate = command_for("pause")
        candidate["parameters"]["run_id"] = "not-a-uuid"
        self.assert_schema_invalid(candidate)

    def test_invalid_datetime_and_missing_timezone_are_rejected(self):
        for value in ("yesterday", "2026-01-01T12:00:00", "2026-99-99T12:00:00Z"):
            with self.subTest(value=value):
                candidate = command_for("status")
                candidate["issued_at"] = value
                self.assert_schema_invalid(candidate)

    def test_invalid_nonce_length_and_characters_are_rejected(self):
        for value in ("short", "x" * 129, "!" * 32):
            with self.subTest(value=value):
                candidate = command_for("status")
                candidate["nonce"] = value
                self.assert_schema_invalid(candidate)

    def test_fencing_token_must_be_positive_integer_not_boolean(self):
        for value in (0, -1, True, 1.5):
            with self.subTest(value=value):
                candidate = command_for("start")
                candidate["fencing_token"] = value
                self.assert_schema_invalid(candidate)

    def test_start_requires_fencing_token_and_memory_budget(self):
        candidate = command_for("start")
        del candidate["fencing_token"]
        self.assert_schema_invalid(candidate)
        candidate = command_for("start")
        del candidate["parameters"]["memory_limit_mb"]
        self.assert_schema_invalid(candidate)

    def test_start_rejects_run_id_and_checkpoint_flag(self):
        for key, value in (("run_id", RUN_ID), ("checkpoint_on_stop", True)):
            with self.subTest(key=key):
                candidate = command_for("start")
                candidate["parameters"][key] = value
                self.assert_schema_invalid(candidate)

    def test_run_controls_require_run_id_and_fencing_token(self):
        for action in ("pause", "resume", "stop"):
            with self.subTest(action=action):
                candidate = command_for(action)
                del candidate["parameters"]["run_id"]
                self.assert_schema_invalid(candidate)
                candidate = command_for(action)
                del candidate["fencing_token"]
                self.assert_schema_invalid(candidate)

    def test_pause_and_resume_reject_start_or_stop_only_parameters(self):
        for action in ("pause", "resume"):
            for key, value in (("memory_limit_mb", 2048), ("checkpoint_on_stop", True)):
                with self.subTest(action=action, key=key):
                    candidate = command_for(action)
                    candidate["parameters"][key] = value
                    self.assert_schema_invalid(candidate)

    def test_stop_rejects_memory_budget_but_allows_checkpoint_flag(self):
        candidate = command_for("stop")
        candidate["parameters"]["memory_limit_mb"] = 2048
        self.assert_schema_invalid(candidate)
        candidate = command_for("stop")
        candidate["parameters"]["checkpoint_on_stop"] = True
        self.validator.validate(candidate)

    def test_status_rejects_parameters(self):
        candidate = command_for("status")
        candidate["parameters"] = {"run_id": RUN_ID}
        self.assert_schema_invalid(candidate)

    def test_memory_budget_bounds_and_types_are_enforced(self):
        for value in (1023, 10241, True, 2048.5):
            with self.subTest(value=value):
                candidate = command_for("start")
                candidate["parameters"]["memory_limit_mb"] = value
                self.assert_schema_invalid(candidate)

    def test_expired_command_is_rejected(self):
        candidate = command_for("status")
        candidate["expires_at"] = timestamp(NOW - timedelta(seconds=1))
        with self.assertRaisesRegex(ValueError, "expired"):
            validate_command(candidate, now=NOW)

    def test_future_issued_command_beyond_clock_skew_is_rejected(self):
        candidate = command_for("status")
        candidate["issued_at"] = timestamp(NOW + timedelta(seconds=31))
        candidate["expires_at"] = timestamp(NOW + timedelta(seconds=60))
        with self.assertRaisesRegex(ValueError, "future"):
            validate_command(candidate, now=NOW)

    def test_expiry_must_follow_issue_time(self):
        candidate = command_for("status")
        candidate["issued_at"] = timestamp(NOW + timedelta(seconds=10))
        candidate["expires_at"] = timestamp(NOW + timedelta(seconds=5))
        with self.assertRaisesRegex(ValueError, "later"):
            validate_command(candidate, now=NOW)

    def test_command_lifetime_is_bounded_to_120_seconds(self):
        candidate = command_for("status")
        candidate["issued_at"] = timestamp(NOW - timedelta(seconds=1))
        candidate["expires_at"] = timestamp(NOW + MAX_COMMAND_TTL)
        with self.assertRaisesRegex(ValueError, "120 seconds"):
            validate_command(candidate, now=NOW)

    def test_replayed_nonce_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "already been used"):
            validate_command(command_for("status"), now=NOW, seen_nonces={NONCE})

    def test_run_action_requires_current_fencing_token(self):
        candidate = command_for("start")
        with self.assertRaisesRegex(ValueError, "required"):
            validate_command(candidate, now=NOW)
        with self.assertRaisesRegex(ValueError, "stale"):
            validate_command(candidate, now=NOW, current_fencing_token=6)

    def test_status_does_not_require_fencing_token(self):
        validate_command(command_for("status"), now=NOW)

    def test_naive_runtime_clock_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            validate_command(command_for("status"), now=datetime(2026, 1, 1, 12, 0, 0))


if __name__ == "__main__":
    unittest.main()
