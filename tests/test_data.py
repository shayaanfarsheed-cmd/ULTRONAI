import random
import unittest

from ultron_data import SUPPORTED_TOPICS, generate_dataset, generate_example
from ultron_model import CharTokenizer
from ultron_verify import verify_example, verify_example_detailed


class DataPipelineTests(unittest.TestCase):
    def test_all_topics_generate_independently_verified_examples(self):
        tokenizer = CharTokenizer()
        for topic_index, topic in enumerate(SUPPORTED_TOPICS):
            for sample_index in range(100):
                rng = random.Random(91000 + topic_index * 1009 + sample_index)
                example = generate_example(topic, rng, difficulty=(sample_index % 3) + 1, sample_index=sample_index)
                valid, reason = verify_example_detailed(example)
                self.assertTrue(valid, f"{topic}: {reason}")
                training_text = example["question"] + "\n" + "\n".join(example["steps"]) + "\nAnswer: " + example["answer"] + "\n"
                tokenizer.encode(training_text)

    def test_corrupted_answer_is_rejected_by_independent_verifier(self):
        example = generate_example("whole_number_arithmetic", random.Random(77), sample_index=77)
        corrupted = dict(example)
        wrong = str(int(example["answer"]) + 1)
        corrupted["answer"] = wrong
        corrupted["steps"] = list(example["steps"][:-1]) + [f"Step 2: Result = {wrong}."]
        self.assertFalse(verify_example(corrupted))

    def test_modified_question_identifier_is_rejected(self):
        example = generate_example("percentages", random.Random(78), sample_index=78)
        corrupted = dict(example)
        corrupted["question"] = corrupted["question"] + "  "
        self.assertFalse(verify_example(corrupted))

    def test_datasets_are_deterministic(self):
        first = generate_dataset(80, seed=20261117, split="train")
        second = generate_dataset(80, seed=20261117, split="train")
        self.assertEqual(first, second)

    def test_train_validation_and_test_questions_do_not_overlap(self):
        training = generate_dataset(300, seed=20261117, split="train")
        validation = generate_dataset(100, seed=20261117, split="validation")
        testing = generate_dataset(100, seed=20261117, split="test")
        training_questions = {item["question"] for item in training}
        validation_questions = {item["question"] for item in validation}
        testing_questions = {item["question"] for item in testing}
        self.assertFalse(training_questions & validation_questions)
        self.assertFalse(training_questions & testing_questions)
        self.assertFalse(validation_questions & testing_questions)

    def test_invalid_topic_is_rejected(self):
        with self.assertRaises(ValueError):
            generate_example("advanced_calculus", random.Random(1))


if __name__ == "__main__":
    unittest.main()
