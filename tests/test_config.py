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
        self.assertEqual(len(servers["servers"]), 4)
        self.assertEqual(servers["rotation_rules"]["fallback_server_id"], "github_actions_cpu")

    def test_colab_is_manual_until_free_account_eligibility_is_verified(self):
        config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        self.assertIn("google_colab", config["switching"]["manual_only_platforms"])
        self.assertNotIn("google_colab", config["switching"]["platform_allowlist"])


if __name__ == "__main__":
    unittest.main()
