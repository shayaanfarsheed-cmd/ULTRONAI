import json
import unittest
from pathlib import Path

from train import build_connection_report, build_preflight_report, detect_platform, resolve_runtime_settings, validate_project_config


ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
SERVERS = json.loads((ROOT / "servers.json").read_text(encoding="utf-8"))


class FakeCuda:
    @staticmethod
    def is_available():
        return True

    @staticmethod
    def get_device_name(index):
        return "Test GPU"

    @staticmethod
    def is_bf16_supported():
        return True


class FakeTorch:
    cuda = FakeCuda()


class RuntimeTests(unittest.TestCase):
    def test_detects_github_actions(self):
        self.assertEqual(detect_platform({"GITHUB_ACTIONS": "true"}, [], []), "github_actions")

    def test_detects_kaggle(self):
        self.assertEqual(detect_platform({"KAGGLE_KERNEL_RUN_TYPE": "Interactive"}, [], []), "kaggle")

    def test_detects_colab(self):
        self.assertEqual(detect_platform({"COLAB_RELEASE_TAG": "release"}, [], []), "google_colab")

    def test_detects_lightning(self):
        self.assertEqual(detect_platform({"LIGHTNING_CLOUD_SPACE_ID": "space-id"}, [], []), "lightning_ai")

    def test_unknown_platform_is_other(self):
        self.assertEqual(detect_platform({}, [], []), "other")

    def test_cpu_fallback_when_torch_is_missing(self):
        result = resolve_runtime_settings(CONFIG, "github_actions", False)
        self.assertEqual(result["device"], "cpu")
        self.assertEqual(result["mixed_precision"], "none")
        self.assertEqual(result["dataloader_workers"], 0)

    def test_kaggle_gpu_profile_uses_bfloat16_when_supported(self):
        result = resolve_runtime_settings(CONFIG, "kaggle", FakeTorch())
        self.assertEqual(result["platform"], "kaggle")
        self.assertEqual(result["device"], "cuda")
        self.assertEqual(result["accelerator_name"], "Test GPU")
        self.assertEqual(result["mixed_precision"], "bf16")
        self.assertEqual(result["batch_size"], 32)
        self.assertEqual(result["dataloader_workers"], 2)

    def test_gpu_profile_uses_bfloat16_when_supported(self):
        result = resolve_runtime_settings(CONFIG, "google_colab", FakeTorch())
        self.assertEqual(result["device"], "cuda")
        self.assertEqual(result["accelerator_name"], "Test GPU")
        self.assertEqual(result["mixed_precision"], "bf16")
        self.assertEqual(result["batch_size"], 32)

    def test_config_overrides_are_respected(self):
        config = {
            **CONFIG,
            "runtime": {"batch_size": 12, "dataloader_workers": 1, "mixed_precision": "none"},
        }
        result = resolve_runtime_settings(config, "google_colab", False)
        self.assertEqual(result["batch_size"], 12)
        self.assertEqual(result["dataloader_workers"], 1)
        self.assertEqual(result["mixed_precision"], "none")

    def test_project_config_invariants(self):
        self.assertEqual(validate_project_config(CONFIG, SERVERS), [])


    def test_connection_report_is_read_only_and_checks_database_and_storage(self):
        class FakeClient:
            project_url = "https://example.supabase.co"

            def __init__(self):
                self.calls = []

            def select(self, table, filters, columns="*", limit=None, order=None):
                self.calls.append((table, filters, columns, limit, order))
                return []

        class FakeAPI:
            owner_id = "owner-test"
            client = FakeClient()

        class FakeStorage:
            def __init__(self):
                self.calls = []

            def list_objects(self, bucket, prefix, limit=1000, offset=0):
                self.calls.append((bucket, prefix, limit, offset))
                return []

        api = FakeAPI()
        storage = FakeStorage()
        report = build_connection_report(api=api, storage=storage, bucket="checkpoints")
        self.assertTrue(report["connected"])
        self.assertFalse(report["writes_performed"])
        self.assertFalse(report["training_started"])
        self.assertEqual(api.client.calls[0][0], "training_status")
        self.assertEqual(api.client.calls[0][1], {"owner_id": "eq.owner-test"})
        self.assertEqual(storage.calls, [("checkpoints", "owner-test", 1, 0)])

    def test_preflight_does_not_start_training_or_reveal_secret_values(self):
        report = build_preflight_report(
            CONFIG,
            SERVERS,
            environ={"GITHUB_ACTIONS": "true", "SUPABASE_SECRET_KEY": "do-not-print-this"},
            module_names=[],
            existing_paths=[],
            torch_module=False,
        )
        serialized = str(report)
        self.assertFalse(report["training_started"])
        self.assertTrue(report["secret_presence"]["SUPABASE_SECRET_KEY"])
        self.assertNotIn("do-not-print-this", serialized)


if __name__ == "__main__":
    unittest.main()
