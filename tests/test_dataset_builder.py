import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_math_dataset import build_dataset
from ultron_evaluation import load_heldout_dataset


class MathDatasetBuilderTests(unittest.TestCase):
    def test_builds_verified_splits_and_reserves_frozen_evaluation_examples(self):
        with tempfile.TemporaryDirectory(prefix="ultron-dataset-builder-test-") as directory:
            manifest = build_dataset(
                directory,
                seed=20261119,
                counts={"train": 600, "validation": 300, "test": 300},
            )
            self.assertEqual(manifest["total_examples"], 1200)
            self.assertEqual(manifest["split_counts"], {
                "train": 600,
                "validation": 300,
                "test": 300,
            })
            self.assertEqual(
                manifest["frozen_evaluation"]["examples_included"],
                len(load_heldout_dataset()["examples"]),
            )
            self.assertTrue(manifest["frozen_evaluation"]["reserved_from_training"])
            self.assertTrue(manifest["reproducibility"]["verified"])
            self.assertEqual(manifest["quality_report"]["status"], "passed")
            self.assertEqual(manifest["quality_report"]["cross_split_exact_leakage_count"], 0)
            self.assertEqual(manifest["quality_report"]["near_duplicate_leakage_count"], 0)

            root = Path(directory)
            for split, count in manifest["split_counts"].items():
                path = root / f"{split}.jsonl"
                self.assertTrue(path.is_file())
                rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
                self.assertEqual(len(rows), count)
                self.assertTrue(all(row["split"] == split for row in rows))

            frozen_ids = {row["sample_id"] for row in load_heldout_dataset()["examples"]}
            test_rows = [json.loads(line) for line in (root / "test.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertTrue(frozen_ids.issubset({row["sample_id"] for row in test_rows}))
            train_rows = [json.loads(line) for line in (root / "train.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertTrue(frozen_ids.isdisjoint({row["sample_id"] for row in train_rows}))


if __name__ == "__main__":
    unittest.main()
