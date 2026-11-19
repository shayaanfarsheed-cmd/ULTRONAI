import unittest

from ultron_data import generate_example
from ultron_self_learning import run_generation_dry_run


class SelfLearningDryRunTests(unittest.TestCase):
    def test_generates_requested_number_of_independently_verified_examples(self):
        report = run_generation_dry_run(40, seed=20261119)
        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["accepted_count"], 40)
        self.assertEqual(report["rejected_count"], 0)
        self.assertTrue(all(item["split"] == "train" for item in report["examples"]))

    def test_same_seed_produces_same_verified_examples(self):
        first = run_generation_dry_run(30, seed=1234)
        second = run_generation_dry_run(30, seed=1234)
        self.assertEqual(first["examples"], second["examples"])
        self.assertEqual(first["topic_counts"], second["topic_counts"])

    def test_validation_and_test_splits_do_not_overlap_training_questions(self):
        training = run_generation_dry_run(80, seed=4321, split="train")
        validation = run_generation_dry_run(30, seed=4321, split="validation")
        testing = run_generation_dry_run(30, seed=4321, split="test")
        train_questions = {item["question"] for item in training["examples"]}
        validation_questions = {item["question"] for item in validation["examples"]}
        test_questions = {item["question"] for item in testing["examples"]}
        self.assertFalse(train_questions & validation_questions)
        self.assertFalse(train_questions & test_questions)
        self.assertFalse(validation_questions & test_questions)

    def test_corrupted_candidate_is_rejected_and_never_returned(self):
        def corrupting_generator(topic, rng, difficulty=1, sample_index=0):
            item = generate_example(topic, rng, difficulty, sample_index)
            item["answer"] = "not-the-answer"
            return item

        report = run_generation_dry_run(
            1,
            seed=9,
            topics=("whole_number_arithmetic",),
            maximum_attempts=100,
            generator=corrupting_generator,
        )
        self.assertEqual(report["accepted_count"], 0)
        self.assertGreater(report["rejected_count"], 0)
        self.assertEqual(report["examples"], [])
        self.assertEqual(report["status"], "incomplete")

    def test_generator_exceptions_are_counted_as_rejections(self):
        def broken_generator(*args, **kwargs):
            raise ArithmeticError("synthetic generator failure")

        report = run_generation_dry_run(
            1,
            seed=11,
            topics=("whole_number_arithmetic",),
            maximum_attempts=50,
            generator=broken_generator,
        )
        self.assertEqual(report["accepted_count"], 0)
        self.assertGreater(report["rejected_count"], 0)
        self.assertIn("ArithmeticError", report["rejection_reasons"])

    def test_dry_run_never_trains_or_writes_files(self):
        report = run_generation_dry_run(5, seed=7)
        self.assertFalse(report["training_started"])
        self.assertFalse(report["model_weights_changed"])
        self.assertFalse(report["written_to_disk"])
        self.assertEqual(report["mode"], "generation_and_verification_dry_run")

    def test_invalid_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            run_generation_dry_run(0, seed=1)
        with self.assertRaises(ValueError):
            run_generation_dry_run(1, seed=True)
        with self.assertRaises(ValueError):
            run_generation_dry_run(1, seed=1, split="holdout")
        with self.assertRaises(ValueError):
            run_generation_dry_run(1, seed=1, topics=("unsupported_topic",))


if __name__ == "__main__":
    unittest.main()
