import random
import unittest

from ultron_data import SUPPORTED_TOPICS, generate_example, generate_dataset
from ultron_dataset_quality import (
    DatasetQualityError,
    _near_duplicate_pairs,
    audit_dataset,
    require_dataset_pass,
    structural_fingerprint,
)


class DatasetQualityTests(unittest.TestCase):
    def test_all_expanded_topics_are_present(self):
        self.assertEqual(len(SUPPORTED_TOPICS), 18)
        self.assertTrue({
            "median_and_range",
            "simple_interest",
            "unit_conversion",
            "pythagorean_theorem",
        }.issubset(SUPPORTED_TOPICS))

    def test_fixed_seed_build_is_reproducible(self):
        first = generate_dataset(80, seed=20261119, split="train")
        second = generate_dataset(80, seed=20261119, split="train")
        self.assertEqual(first, second)

    def test_difficulty_progression_expands_simple_interest_values(self):
        maxima = []
        for difficulty in (1, 2, 3):
            values = []
            for index in range(100):
                example = generate_example(
                    "simple_interest",
                    random.Random(4000 + difficulty * 1000 + index),
                    difficulty=difficulty,
                    sample_index=index,
                )
                principal = int(example["question"].split("principal ", 1)[1].split(",", 1)[0])
                values.append(principal)
                self.assertEqual(example["difficulty"], difficulty)
            maxima.append(max(values))
        self.assertLess(maxima[0], maxima[1])
        self.assertLess(maxima[1], maxima[2])

    def test_exact_question_reuse_across_splits_fails_closed(self):
        example = generate_example("whole_number_arithmetic", random.Random(44), sample_index=44)
        training = dict(example, split="train")
        testing = dict(example, split="test")
        report = audit_dataset([training, testing], required_splits=("train", "test"))
        self.assertEqual(report["status"], "failed")
        self.assertGreater(report["exact_duplicate_count"], 0)
        self.assertEqual(report["cross_split_exact_leakage_count"], 1)
        with self.assertRaises(DatasetQualityError):
            require_dataset_pass(report)

    def test_invalid_answer_is_rejected_even_if_last_step_is_changed(self):
        example = generate_example("simple_interest", random.Random(45), sample_index=45)
        corrupted = dict(example, split="train")
        corrupted["answer"] = "999999"
        corrupted["steps"] = list(example["steps"][:-1]) + ["Step 2: I = 999999."]
        report = audit_dataset([corrupted], required_splits=("train",))
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["invalid_example_count"], 1)

    def test_structural_fingerprint_groups_numeric_variants(self):
        first = structural_fingerprint("Calculate: 120 + 34")
        second = structural_fingerprint("Calculate: 981 + 765")
        self.assertEqual(first, second)

    def test_fuzzy_near_duplicate_detector_finds_small_edit(self):
        examples = [
            {
                "sample_id": "a",
                "topic": "linear_equations",
                "question": "Solve the linear equation by isolating x: 3*x + 12 = 48",
                "split": "train",
            },
            {
                "sample_id": "b",
                "topic": "linear_equations",
                "question": "Solve the linear equation by isolating x: 3*x + 13 = 49",
                "split": "test",
            },
        ]
        pairs = _near_duplicate_pairs(examples, threshold=0.8)
        self.assertEqual(len(pairs), 1)
        self.assertGreaterEqual(pairs[0]["similarity"], 0.8)
        self.assertNotEqual(pairs[0]["left_split"], pairs[0]["right_split"])


if __name__ == "__main__":
    unittest.main()
