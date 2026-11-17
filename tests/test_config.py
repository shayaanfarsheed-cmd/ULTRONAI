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
