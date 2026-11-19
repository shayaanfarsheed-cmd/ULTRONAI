import random
import unittest

from ultron_data import InvalidGeneratedExampleError, generate_dataset, generate_example, question_split
from ultron_self_learning import run_generation_dry_run


class SelfLearningDryRunTests(unittest.TestCase):
    def test_generates_requested_number_of_verified_examples(self):
        report = run_generation_dry_run(40, seed=20261119)
        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["accepted_count"], 40)
        self.assertEqual(report["rejected_count"], 0)
        self.assertEqual(report["generation_error_count"], 0)
        self.assertTrue(all(item["split"] == "train" for item in report["examples"]))
        self.assertTrue(all(question_split(item["question"]) == "train" for item in report["examples"]))

    def test_same_seed_produces_same_verified_examples_and_metrics(self):
        first = run_generation_dry_run(30, seed=1234)
        second = run_generation_dry_run(30, seed=1234)
        self.assertEqual(first["examples"], second["examples"])
        self.assertEqual(first["topic_counts"], second["topic_counts"])
        self.assertEqual(first["difficulty_counts"], second["difficulty_counts"])

    def test_shared_split_function_matches_existing_dataset_generator(self):
        for split, count in (("train", 80), ("validation", 30), ("test", 30)):
            existing = generate_dataset(count, seed=4321, split=split)
            dry_run = run_generation_dry_run(count, seed=4321, split=split)
            self.assertEqual(
                [item["question"] for item in dry_run["examples"]],
                [item["question"] for item in existing],
            )
            self.assertTrue(all(question_split(item["question"]) == split for item in dry_run["examples"]))

    def test_question_split_is_independent_of_generation_index(self):
        example = generate_example("whole_number_arithmetic", random.Random(9), sample_index=0)
        expected = question_split(example["question"])
        self.assertEqual(question_split(example["question"]), expected)
        self.assertEqual(question_split(example["question"]), expected)

    def test_train_validation_and_test_questions_do_not_overlap(self):
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

    def test_generator_failures_are_reported_separately_from_split_rejections(self):
        def broken_generator(*args, **kwargs):
            raise InvalidGeneratedExampleError("synthetic invalid candidate")

        report = run_generation_dry_run(
            1,
            seed=11,
            topics=("whole_number_arithmetic",),
            maximum_attempts=5,
            generator=broken_generator,
        )
        self.assertEqual(report["accepted_count"], 0)
        self.assertEqual(report["rejected_count"], 0)
        self.assertEqual(report["generation_error_count"], 5)
        self.assertEqual(report["generation_errors"], {"InvalidGeneratedExampleError": 5})
        self.assertEqual(report["status"], "incomplete")

    def test_unexpected_generator_errors_propagate(self):
        def broken_generator(*args, **kwargs):
            raise TypeError("programming defect")

        with self.assertRaisesRegex(TypeError, "programming defect"):
            run_generation_dry_run(
                1,
                seed=1,
                topics=("whole_number_arithmetic",),
                generator=broken_generator,
            )

    def test_unexpected_value_errors_from_generator_propagate(self):
        def broken_generator(*args, **kwargs):
            raise ValueError("programming defect")

        with self.assertRaisesRegex(ValueError, "programming defect"):
            run_generation_dry_run(
                1,
                seed=1,
                topics=("whole_number_arithmetic",),
                generator=broken_generator,
            )

    def test_unexpected_verifier_errors_propagate(self):
        def broken_verifier(candidate):
            raise RuntimeError("verifier programming defect")

        with self.assertRaisesRegex(RuntimeError, "verifier programming defect"):
            run_generation_dry_run(1, seed=7, verifier=broken_verifier)

    def test_candidate_metadata_must_match_requested_generation(self):
        def wrong_metadata_generator(topic, rng, difficulty=1, sample_index=0):
            item = generate_example(topic, rng, difficulty, sample_index)
            item["difficulty"] = 3 if difficulty != 3 else 2
            return item

        report = run_generation_dry_run(
            1,
            seed=22,
            topics=("whole_number_arithmetic",),
            maximum_attempts=100,
            generator=wrong_metadata_generator,
        )
        self.assertEqual(report["accepted_count"], 0)
        self.assertGreater(report["rejected_count"], 0)
        self.assertIn("metadata_mismatch", report["rejection_reasons"])

    def test_missing_question_is_not_assigned_using_sample_index(self):
        def missing_question_generator(topic, rng, difficulty=1, sample_index=0):
            return {"topic": topic, "difficulty": difficulty, "sample_index": sample_index}

        report = run_generation_dry_run(
            1,
            seed=5,
            topics=("whole_number_arithmetic",),
            maximum_attempts=4,
            generator=missing_question_generator,
        )
        self.assertEqual(report["candidates_in_split"], 0)
        self.assertEqual(report["rejected_count"], 0)
        self.assertEqual(report["unassigned_rejections"], {"missing_question": 4})

    def test_dry_run_never_trains_or_writes_files(self):
        report = run_generation_dry_run(5, seed=7)
        self.assertFalse(report["training_started"])
        self.assertFalse(report["model_weights_changed"])
        self.assertFalse(report["written_to_disk"])
        self.assertEqual(report["mode"], "generation_and_verification_dry_run")

    def test_invalid_inputs_are_rejected_cleanly(self):
        invalid_calls = (
            lambda: run_generation_dry_run(0, seed=1),
            lambda: run_generation_dry_run(1, seed=True),
            lambda: run_generation_dry_run(1, seed=1, split="holdout"),
            lambda: run_generation_dry_run(1, seed=1, split=[]),
            lambda: run_generation_dry_run(1, seed=1, topics=("unsupported_topic",)),
            lambda: run_generation_dry_run(1, seed=1, topics="fractions"),
            lambda: run_generation_dry_run(1, seed=1, topics=None),
            lambda: run_generation_dry_run(1, seed=1, maximum_attempts=True),
            lambda: run_generation_dry_run(1, seed=1, generator=3),
            lambda: run_generation_dry_run(1, seed=1, verifier=3),
        )
        for call in invalid_calls:
            with self.subTest(call=call):
                with self.assertRaises(ValueError):
                    call()


if __name__ == "__main__":
    unittest.main()
