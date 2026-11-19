import json
import unittest
from pathlib import Path

from train import validate_project_config


ROOT = Path(__file__).resolve().parents[1]


class ConfigurationTests(unittest.TestCase):
    def test_json_files_parse(self):
        config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        servers = json.loads((ROOT / "servers.json").read_text(encoding="utf-8"))
        self.assertIsInstance(config, dict)
        self.assertIsInstance(servers, dict)

    def test_server_registry_and_invariants(self):
        config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        servers = json.loads((ROOT / "servers.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_project_config(config, servers), [])
        self.assertEqual(len(servers["servers"]), 5)
        self.assertEqual(servers["rotation_rules"]["fallback_server_id"], "github_actions_cpu")

    def test_owner_guest_and_platform_security_policy(self):
        config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        access = config["access"]
        self.assertEqual(access["owner_account_limit"], 1)
        self.assertFalse(access["public_self_registration_enabled"])
        self.assertTrue(access["owner_authentication_required_for_private_operations"])
        self.assertTrue(access["guest_mode_enabled"])
        self.assertEqual(set(access["guest_permissions"]), {"public_dashboard", "public_mathematics_information"})
        self.assertTrue({
            "private_training_history",
            "private_checkpoints",
            "device_pairing",
            "remote_training_controls",
        }.issubset(set(access["guest_denied_permissions"])))
        enforcement = config["local_training"]["platform_enforcement"]
        for platform_name in ("windows", "linux", "macos", "ipados", "ios", "android", "browser"):
            self.assertIn(platform_name, enforcement)
        self.assertEqual(config["local_training"]["enforcement"], "platform_specific_verified")

    def test_kaggle_is_enabled_for_manual_use_only(self):
        config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        servers = json.loads((ROOT / "servers.json").read_text(encoding="utf-8"))
        kaggle = next(item for item in servers["servers"] if item["id"] == "kaggle")
        self.assertTrue(kaggle["enabled"])
        self.assertTrue(kaggle["manual_only"])
        self.assertEqual(kaggle["automatic_start"], "no")
        self.assertFalse(kaggle["automatic_start_enabled_by_default"])
        self.assertIn("kaggle", config["runtime"]["supported_platforms"])
        self.assertIn("kaggle", config["switching"]["manual_only_platforms"])
        self.assertNotIn("kaggle", config["switching"]["platform_allowlist"])
        self.assertEqual(validate_project_config(config, servers), [])

    def test_invalid_owner_guest_and_platform_policies_are_rejected(self):
        config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        servers = json.loads((ROOT / "servers.json").read_text(encoding="utf-8"))

        invalid_cases = [
            ("multiple owners", lambda c: c["access"].update(owner_account_limit=2)),
            ("boolean owner limit", lambda c: c["access"].update(owner_account_limit=True)),
            ("public signup", lambda c: c["access"].update(public_self_registration_enabled=True)),
            ("private guest permission", lambda c: c["access"]["guest_permissions"].append("private_checkpoints")),
            ("missing guest denial", lambda c: c["access"]["guest_denied_permissions"].remove("device_pairing")),
            ("unknown enforcement", lambda c: c["local_training"]["platform_enforcement"].update(windows="anything")),
            ("missing enforcement", lambda c: c["local_training"]["platform_enforcement"].pop("linux")),
            ("Kaggle missing manual runtime", lambda c: c["runtime"]["supported_platforms"].remove("kaggle")),
            ("Kaggle auto selection", lambda c: c["switching"]["platform_allowlist"].append("kaggle")),
            ("Kaggle missing manual-only flag", lambda c: c["switching"]["manual_only_platforms"].remove("kaggle")),
        ]

        for label, mutate in invalid_cases:
            with self.subTest(label=label):
                candidate = json.loads(json.dumps(config))
                mutate(candidate)
                self.assertTrue(validate_project_config(candidate, servers), label)

    def test_kaggle_runtime_resolves_to_cpu_when_cuda_is_unavailable(self):
        from train import resolve_runtime_settings

        config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        result = resolve_runtime_settings(config, "kaggle", torch_module=False)
        self.assertEqual(result["platform"], "kaggle")
        self.assertEqual(result["device"], "cpu")
        self.assertEqual(result["mixed_precision"], "none")

    def test_kaggle_cannot_be_made_automatic(self):
        config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        servers = json.loads((ROOT / "servers.json").read_text(encoding="utf-8"))
        kaggle = next(item for item in servers["servers"] if item["id"] == "kaggle")
        kaggle["automatic_start"] = "yes"
        self.assertTrue(validate_project_config(config, servers))

    def test_colab_is_manual_until_free_account_eligibility_is_verified(self):
        config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        self.assertIn("google_colab", config["switching"]["manual_only_platforms"])
        self.assertNotIn("google_colab", config["switching"]["platform_allowlist"])

    def test_curriculum_starts_elementary_and_unlocks_middle_school_later(self):
        config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        curriculum = config["training"]["curriculum"]
        self.assertEqual(curriculum["initial_topics"], curriculum["elementary_topics"])
        self.assertEqual(curriculum["stages"][0]["name"], "elementary")
        self.assertEqual(curriculum["stages"][1]["name"], "middle_school")
        self.assertTrue(curriculum["held_out_evaluation_required"])
        self.assertEqual(curriculum["unlock_mastery_accuracy"], 0.9)
        self.assertEqual(curriculum["consecutive_evaluations_required"], 3)
        self.assertTrue(curriculum["do_not_train_advanced_topics"])


if __name__ == "__main__":
    unittest.main()
