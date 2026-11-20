import json
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


class FakeTorch:
    __version__ = "test-cpu"

    def __init__(self):
        self.cuda = SimpleNamespace(is_available=lambda: False)

    @staticmethod
    def get_num_threads():
        return 2


class ComputeDiagnosticTests(unittest.TestCase):
    def test_diagnostic_reports_resources_without_training(self):
        from scripts.diagnose_cpu_runner import collect_report

        report = collect_report(torch_module=FakeTorch())
        self.assertEqual(report["status"], "passed")
        self.assertFalse(report["training_started"])
        self.assertFalse(report["model_weights_modified"])
        self.assertFalse(report["persistent_checkpoints_touched"])
        self.assertGreaterEqual(report["cpu"]["logical_count"], 1)
        self.assertGreater(report["disk_root"]["free_bytes"], 0)
        self.assertEqual(report["pytorch"]["device"], "cpu")
        self.assertFalse(report["pytorch"]["cuda_available"])

    def test_diagnostic_workflow_never_invokes_training_or_uses_secrets(self):
        workflow = (ROOT / ".github/workflows/cpu-diagnostic.yml").read_text()
        self.assertIn("ultron-cpu-diagnostic", workflow)
        self.assertIn("scripts/diagnose_cpu_runner.py", workflow)
        self.assertNotIn("train.py --train", workflow)
        self.assertNotIn("SUPABASE_SECRET_KEY", workflow)
        self.assertNotIn("ULTRON_GITHUB_TOKEN", workflow)
        self.assertIn("actions/checkout@v5", workflow)
        self.assertIn("actions/setup-python@v6", workflow)

    def test_all_workflows_use_node24_compatible_action_majors(self):
        workflow_dir = ROOT / ".github/workflows"
        for path in workflow_dir.glob("*.yml"):
            content = path.read_text()
            self.assertNotIn("actions/checkout@v4", content, path.name)
            self.assertNotIn("actions/setup-python@v5", content, path.name)
            self.assertNotIn("actions/upload-artifact@v4", content, path.name)

    def test_colab_notebook_is_manual_and_diagnostic_only(self):
        notebook = json.loads((ROOT / "compute_provider_diagnostic.ipynb").read_text())
        code = "\\n".join(
            "".join(cell.get("source", []))
            for cell in notebook["cells"]
            if cell.get("cell_type") == "code"
        )
        self.assertIn("google_colab_manual", code)
        self.assertIn("'training_started': False", code)
        self.assertNotIn("train.py --train", code)
        self.assertNotIn("SUPABASE_SECRET_KEY", code)
        self.assertNotIn("ULTRON_GITHUB_TOKEN", code)

    def test_owner_control_targets_safe_diagnostic_workflow(self):
        source = (ROOT / "supabase/functions/training-control/index.ts").read_text()
        self.assertIn('const CPU_WORKFLOW_PATH = "cpu-diagnostic.yml"', source)
        self.assertIn('const CPU_WORKFLOW_PATH = "cpu-diagnostic.yml"', source)
        self.assertIn('"/actions/workflows/" + workflowPath + "/dispatches"', source)
        self.assertNotIn('const CPU_WORKFLOW_PATH = "cpu-training.yml"', source)

    def test_dashboard_labels_start_as_diagnostic_not_training(self):
        html = (ROOT / "dashboard/index.html").read_text()
        script = (ROOT / "dashboard/training-control.js").read_text()
        self.assertIn("Run compute diagnostic", html)
        self.assertIn("Start a safe CPU compute diagnostic", script)
        self.assertNotIn("Start ULTRON neural training", script)


if __name__ == "__main__":
    unittest.main()
