import json
import unittest
from pathlib import Path

from ultron_data import SUPPORTED_TOPICS, question_split
from ultron_verify import verify_example_detailed


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "evaluation" / "heldout_foundation_v1.json"


class HeldOutFoundationDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.examples = cls.payload["examples"]

    def test_fixture_is_versioned_and_frozen(self):
        self.assertEqual(self.payload["schema_version"], 1)
        self.assertEqual(self.payload["dataset_id"], "ultron-heldout-foundation-v1")
        self.assertIs(self.payload["frozen"], True)

    def test_covers_every_supported_topic(self):
        self.assertEqual({item["topic"] for item in self.examples}, set(SUPPORTED_TOPICS))

    def test_every_case_is_valid_under_independent_verifier(self):
        for example in self.examples:
            with self.subTest(topic=example["topic"], question=example["question"]):
                valid, reason = verify_example_detailed(example)
                self.assertTrue(valid, reason)

    def test_every_case_is_assigned_to_the_test_split(self):
        for example in self.examples:
            with self.subTest(question=example["question"]):
                self.assertEqual(example["split"], "test")
                self.assertEqual(question_split(example["question"]), "test")

    def test_questions_and_sample_ids_are_unique(self):
        questions = [item["question"] for item in self.examples]
        sample_ids = [item["sample_id"] for item in self.examples]
        self.assertEqual(len(questions), len(set(questions)))
        self.assertEqual(len(sample_ids), len(set(sample_ids)))

    def test_fixture_is_not_empty_and_has_explicit_difficulty(self):
        self.assertTrue(self.examples)
        self.assertTrue(all(type(item["difficulty"]) is int for item in self.examples))
        self.assertTrue(all(item["difficulty"] in (1, 2, 3) for item in self.examples))


if __name__ == "__main__":
    unittest.main()
