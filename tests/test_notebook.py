import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NotebookTests(unittest.TestCase):
    def test_notebook_is_valid_and_code_cells_compile(self):
        notebook = json.loads((ROOT / "train.ipynb").read_text(encoding="utf-8"))
        self.assertEqual(notebook["nbformat"], 4)
        self.assertEqual(notebook["metadata"]["kernelspec"]["name"], "python3")
        code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
        self.assertEqual(len(code_cells), 4)
        for index, cell in enumerate(code_cells):
            compile("".join(cell["source"]), f"train.ipynb-cell-{index}", "exec")

    def test_notebook_has_no_saved_execution_output(self):
        notebook = json.loads((ROOT / "train.ipynb").read_text(encoding="utf-8"))
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                self.assertIsNone(cell["execution_count"])
                self.assertEqual(cell["outputs"], [])

    def test_notebook_fetches_only_project_files_from_raw_github(self):
        notebook = json.loads((ROOT / "train.ipynb").read_text(encoding="utf-8"))
        source = "\n".join("".join(cell["source"]) for cell in notebook["cells"])
        self.assertIn("raw.githubusercontent.com", source)
        self.assertIn("train.py", source)
        self.assertIn("ultron_model.py", source)
        self.assertIn("ultron_data.py", source)
        self.assertIn("ultron_verify.py", source)
        self.assertIn("ultron_checkpoint.py", source)
        self.assertIn("ultron_training.py", source)
        self.assertIn("ultron_supabase.py", source)
        self.assertIn("ultron_storage.py", source)
        self.assertIn("ultron_session.py", source)
        self.assertIn("config.json", source)
        self.assertIn("servers.json", source)
        self.assertIn("--model-summary", source)
        self.assertIn("--data-smoke-test", source)
        self.assertNotIn("--training-smoke-test", source)
        self.assertNotIn("--checkpoint-smoke-test", source)
        self.assertIn("ENABLE_REAL_TRAINING = False", source)
        self.assertIn("if not ENABLE_REAL_TRAINING:", source)
        self.assertIn("SUPABASE_SECRET_KEY", source)
        self.assertIn("SUPABASE_OWNER_ID", source)
        self.assertNotRegex(source, r"sb_secret_[A-Za-z0-9]{20,}")
        self.assertIn('"--train"', source)


if __name__ == "__main__":
    unittest.main()
