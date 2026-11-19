import copy
import unittest

from ultron_evaluation import (
    DATASET_ID,
    EvaluationInputError,
    evaluate_predictions,
    load_heldout_dataset,
)


class ReadOnlyEvaluationRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = load_heldout_dataset()

    def test_perfect_explicit_predictions_score_one(self):
        predictions = {item["sample_id"]: item["answer"] for item in self.dataset["examples"]}
        report = evaluate_predictions(self.dataset, predictions, model_label="test-checkpoint")
        self.assertEqual(report["overall"], {"correct": 14, "total": 14, "accuracy": 1.0})
        self.assertEqual(report["model_label"], "test-checkpoint")
        self.assertEqual(sum(item["total"] for item in report["by_topic"].values()), 14)
        self.assertEqual(sum(item["total"] for item in report["by_difficulty"].values()), 14)
        self.assertEqual(report["failures"], [])

    def test_missing_and_incorrect_predictions_are_distinguished(self):
        first, second = self.dataset["examples"][:2]
        report = evaluate_predictions(
            self.dataset,
            {first["sample_id"]: "definitely-wrong", second["sample_id"]: second["answer"]},
        )
        self.assertEqual(report["overall"]["correct"], 1)
        self.assertEqual(report["failures"][0]["category"], "incorrect_answer")
        self.assertEqual(report["failures"][1]["category"], "missing_prediction")
        self.assertEqual(report["failures"][1]["predicted_answer"], None)

    def test_whitespace_is_normalized_but_math_content_is_not(self):
        item = self.dataset["examples"][0]
        report = evaluate_predictions(
            self.dataset,
            {item["sample_id"]: "  " + item["answer"] + "  "},
        )
        self.assertTrue(report["failures"][0]["category"] == "missing_prediction" or report["overall"]["correct"] == 1)

    def test_unknown_prediction_ids_are_rejected(self):
        with self.assertRaises(EvaluationInputError):
            evaluate_predictions(self.dataset, {"not-a-test-case": "42"})

    def test_non_string_prediction_is_rejected(self):
        item = self.dataset["examples"][0]
        with self.assertRaises(EvaluationInputError):
            evaluate_predictions(self.dataset, {item["sample_id"]: 42})

    def test_dataset_mutation_is_not_performed_and_report_is_deterministic(self):
        before = copy.deepcopy(self.dataset)
        predictions = {item["sample_id"]: item["answer"] for item in self.dataset["examples"]}
        first = evaluate_predictions(self.dataset, predictions)
        second = evaluate_predictions(self.dataset, predictions)
        self.assertEqual(self.dataset, before)
        self.assertEqual(first, second)

    def test_dataset_identity_must_match(self):
        altered = dict(self.dataset, dataset_id="different-dataset")
        with self.assertRaises(EvaluationInputError):
            evaluate_predictions(altered, {})

    def test_dataset_loader_enforces_frozen_test_split(self):
        self.assertEqual(self.dataset["dataset_id"], DATASET_ID)
        self.assertTrue(self.dataset["frozen"])
        self.assertTrue(all(item["split"] == "test" for item in self.dataset["examples"]))


if __name__ == "__main__":
    unittest.main()
