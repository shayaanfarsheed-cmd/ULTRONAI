import json
import tempfile
import unittest
from pathlib import Path

from ultron_seed_dataset import DatasetScanError, scan_dataset


def make_task(root: Path, folder: str = "sample-task", theorem: str = "Example.demo") -> Path:
    task = root / "tasks" / folder
    (task / "tests").mkdir(parents=True)
    (task / "task.toml").write_text(
        "[task]\nname = \"sample/" + folder + "\"\nversion = \"0.1.0\"\n"
        "[metadata]\ntheorems = [\"" + theorem + "\"]\n"
        "source = \"https://example.invalid/source\"\n"
        "source_commit = \"abc123\"\nsource_license = \"Apache-2.0\"\n"
        "hf_revision = \"rev123\"\nvalidation_status = \"unvalidated\"\n",
        encoding="utf-8",
    )
    (task / "instruction.md").write_text("A sample task.", encoding="utf-8")
    (task / "LICENSE").write_text("License text.", encoding="utf-8")
    (task / "NOTICE").write_text("Notice text.", encoding="utf-8")
    (task / "tests" / "Challenge.lean").write_text("theorem demo : True := by trivial\n", encoding="utf-8")
    (task / "tests" / "task.json").write_text(
        json.dumps({"comparator": {"theorem_names": [theorem]}}), encoding="utf-8"
    )
    return task


class SeedDatasetScannerTests(unittest.TestCase):
    def test_scans_expected_task_and_records_hashes_without_proof_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            task = make_task(root)
            result = scan_dataset(root, expected_count=1)

            self.assertEqual(result["task_count"], 1)
            self.assertEqual(result["scan_status"], "structure_validated")
            self.assertEqual(result["proof_status"], "not_checked")
            self.assertFalse(result["execution_performed"])
            record = result["tasks"][0]
            self.assertEqual(record["theorems"], ["Example.demo"])
            self.assertEqual(record["file_count"], 6)
            self.assertEqual(len(record["files"][0]["sha256"]), 64)
            self.assertEqual(record["folder"], task.name)

    def test_rejects_wrong_task_count(self):
        with tempfile.TemporaryDirectory() as temp:
            make_task(Path(temp))
            with self.assertRaisesRegex(DatasetScanError, "Expected 2 task folders"):
                scan_dataset(temp, expected_count=2)

    def test_rejects_missing_required_file(self):
        with tempfile.TemporaryDirectory() as temp:
            task = make_task(Path(temp))
            (task / "NOTICE").unlink()
            with self.assertRaisesRegex(DatasetScanError, "NOTICE"):
                scan_dataset(temp, expected_count=1)

    def test_rejects_theorem_metadata_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            task = make_task(Path(temp))
            (task / "tests" / "task.json").write_text(
                json.dumps({"comparator": {"theorem_names": ["Example.other"]}}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(DatasetScanError, "does not match"):
                scan_dataset(temp, expected_count=1)

    def test_rejects_duplicate_task_names(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_task(root, "task-a")
            make_task(root, "task-b")
            (root / "tasks" / "task-b" / "task.toml").write_text(
                (root / "tasks" / "task-a" / "task.toml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(DatasetScanError, "Duplicate task name"):
                scan_dataset(root, expected_count=2)

    def test_rejects_duplicate_theorems_within_one_task(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            task = make_task(root, theorem="Example.demo")
            (task / "task.toml").write_text(
                (task / "task.toml").read_text(encoding="utf-8").replace(
                    'theorems = ["Example.demo"]',
                    'theorems = ["Example.demo", "Example.demo"]',
                ),
                encoding="utf-8",
            )
            (task / "tests" / "task.json").write_text(
                json.dumps({"comparator": {"theorem_names": ["Example.demo", "Example.demo"]}}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(DatasetScanError, "repeated theorem identifier"):
                scan_dataset(root, expected_count=1)

    def test_rejects_non_object_task_json(self):
        with tempfile.TemporaryDirectory() as temp:
            task = make_task(Path(temp))
            (task / "tests" / "task.json").write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(DatasetScanError, "must contain an object"):
                scan_dataset(temp, expected_count=1)

    def test_rejects_invalid_expected_count(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(DatasetScanError, "positive integer"):
                scan_dataset(temp, expected_count=0)


if __name__ == "__main__":
    unittest.main()
