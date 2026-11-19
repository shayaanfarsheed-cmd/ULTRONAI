import unittest

import torch

from ultron_evaluation import (
    HELD_OUT_EVALUATION_SET,
    evaluate_model,
    evaluation_set_fingerprint,
    validate_evaluation_set,
)
from ultron_model import CharTokenizer, ULTRONTransformer
from ultron_training import MathBatchStream


class EvaluationFoundationTests(unittest.TestCase):
    def test_fixed_set_covers_every_supported_topic_and_difficulty(self):
        validate_evaluation_set()
        topics = {item["topic"] for item in HELD_OUT_EVALUATION_SET}
        difficulties = {item["difficulty"] for item in HELD_OUT_EVALUATION_SET}
        self.assertEqual(len(topics), 14)
        self.assertEqual(difficulties, {1, 3})
        self.assertEqual(len(HELD_OUT_EVALUATION_SET), 28)
        self.assertTrue(all(item["evaluation_only"] for item in HELD_OUT_EVALUATION_SET))

    def test_evaluation_fingerprint_is_stable(self):
        self.assertEqual(
            evaluation_set_fingerprint(),
            evaluation_set_fingerprint(tuple(dict(item) for item in HELD_OUT_EVALUATION_SET)),
        )

    def test_evaluation_does_not_change_weights_or_training_mode(self):
        tokenizer = CharTokenizer()
        model = ULTRONTransformer(
            vocab_size=tokenizer.vocab_size,
            context_length=192,
            dimension=16,
            layers=1,
            heads=2,
            dropout=0.0,
        )
        model.train()
        before = {key: value.detach().clone() for key, value in model.state_dict().items()}
        report = evaluate_model(
            model,
            tokenizer,
            examples=HELD_OUT_EVALUATION_SET[:2],
            maximum_new_tokens=2,
        )
        self.assertTrue(model.training)
        self.assertFalse(report["training_started"])
        self.assertFalse(report["model_weights_changed"])
        self.assertFalse(report["optimizer_used"])
        self.assertEqual(report["sample_count"], 2)
        for key, value in model.state_dict().items():
            self.assertTrue(torch.equal(before[key], value), key)

    def test_evaluation_reports_topic_and_difficulty_metrics(self):
        tokenizer = CharTokenizer()
        model = ULTRONTransformer(
            vocab_size=tokenizer.vocab_size,
            context_length=192,
            dimension=16,
            layers=1,
            heads=2,
            dropout=0.0,
        )
        report = evaluate_model(
            model,
            tokenizer,
            examples=HELD_OUT_EVALUATION_SET[:4],
            maximum_new_tokens=2,
        )
        self.assertIn("whole_number_arithmetic", report["by_topic"])
        self.assertIn("fractions", report["by_topic"])
        self.assertIn("1", report["by_difficulty"])
        self.assertIn("3", report["by_difficulty"])
        self.assertGreaterEqual(report["accuracy"], 0.0)
        self.assertLessEqual(report["accuracy"], 1.0)

    def test_evaluation_examples_are_rejected_by_training_stream(self):
        with self.assertRaisesRegex(ValueError, "held-out evaluation"):
            MathBatchStream(
                HELD_OUT_EVALUATION_SET,
                CharTokenizer(),
                context_length=192,
                batch_size=2,
                seed=1,
            )


if __name__ == "__main__":
    unittest.main()
