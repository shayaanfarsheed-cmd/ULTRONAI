import unittest

import torch

from ultron_data import generate_dataset
from ultron_model import CharTokenizer, ULTRONTransformer
from ultron_training import (
    CurriculumController,
    MathBatchStream,
    encode_example,
    evaluate_by_topic,
    format_example,
    generate_completion,
    train_one_batch,
    train_steps,
)


class TrainingEngineTests(unittest.TestCase):
    def setUp(self):
        self.tokenizer = CharTokenizer()

    def test_prompt_is_context_and_solution_is_target(self):
        example = generate_dataset(1, seed=20261117, split="train", topics=["whole_number_arithmetic"])[0]
        prefix, completion = format_example(example)
        encoded = encode_example(example, self.tokenizer, 192)
        prefix_length = len(self.tokenizer.encode(prefix))
        self.assertTrue(all(value == -100 for value in encoded["labels"][:prefix_length - 1]))
        self.assertTrue(any(value != -100 for value in encoded["labels"][prefix_length - 1:]))
        self.assertIn("Answer:", completion)

    def test_stream_resume_repeats_the_same_next_batch(self):
        examples = generate_dataset(30, seed=20261117, split="train", topics=["whole_number_arithmetic", "fractions"])
        first = MathBatchStream(examples, self.tokenizer, 192, batch_size=4, seed=88)
        first.next_batch(self.tokenizer.stoi[" "])
        saved = first.state_dict()
        expected = first.next_batch(self.tokenizer.stoi[" "])
        resumed = MathBatchStream(examples, self.tokenizer, 192, batch_size=4, seed=88)
        resumed.load_state_dict(saved)
        actual = resumed.next_batch(self.tokenizer.stoi[" "])
        self.assertTrue(torch.equal(expected["input_ids"], actual["input_ids"]))
        self.assertTrue(torch.equal(expected["labels"], actual["labels"]))

    def test_batch_padding_uses_ignored_target_positions(self):
        examples = generate_dataset(8, seed=20261117, split="train", topics=["whole_number_arithmetic"])
        stream = MathBatchStream(examples, self.tokenizer, 192, batch_size=8, seed=2)
        batch = stream.next_batch(self.tokenizer.stoi[" "])
        self.assertEqual(batch["input_ids"].shape, batch["labels"].shape)
        self.assertTrue(bool((batch["labels"] == -100).any()))

    def test_one_training_batch_updates_parameters(self):
        examples = generate_dataset(8, seed=20261117, split="train", topics=["whole_number_arithmetic"])
        stream = MathBatchStream(examples, self.tokenizer, 192, batch_size=4, seed=2)
        model = ULTRONTransformer(vocab_size=self.tokenizer.vocab_size, context_length=192, dimension=32, layers=1, heads=4, dropout=0.0)
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
        before = model.token_embedding.weight.detach().clone()
        loss = train_one_batch(model, optimizer, stream.next_batch(self.tokenizer.stoi[" "]), "cpu")
        self.assertTrue(torch.isfinite(torch.tensor(loss)))
        self.assertFalse(torch.equal(before, model.token_embedding.weight))

    def test_train_steps_updates_scheduler_and_reports_position(self):
        examples = generate_dataset(8, seed=20261117, split="train", topics=["whole_number_arithmetic"])
        stream = MathBatchStream(examples, self.tokenizer, 192, batch_size=4, seed=2)
        model = ULTRONTransformer(vocab_size=self.tokenizer.vocab_size, context_length=192, dimension=32, layers=1, heads=4, dropout=0.0)
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
        scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=1, gamma=0.5)
        result = train_steps(model, optimizer, stream, 2, "cpu", scheduler=scheduler)
        self.assertEqual(result["step"], 2)
        self.assertTrue(torch.isfinite(torch.tensor(result["last_loss"])))
        self.assertAlmostEqual(optimizer.param_groups[0]["lr"], 0.00025)
        self.assertEqual(result["data_position"], 8)

    def test_greedy_generation_returns_text_and_restores_training_mode(self):
        model = ULTRONTransformer(vocab_size=self.tokenizer.vocab_size, context_length=192, dimension=32, layers=1, heads=4, dropout=0.0)
        model.train()
        output = generate_completion(model, self.tokenizer, "2 + 2", 192, "cpu", maximum_new_tokens=8)
        self.assertIsInstance(output, str)
        self.assertTrue(model.training)

    def test_evaluation_reports_exact_accuracy_fields(self):
        examples = generate_dataset(3, seed=20261117, split="test", topics=["whole_number_arithmetic"])
        model = ULTRONTransformer(vocab_size=self.tokenizer.vocab_size, context_length=192, dimension=32, layers=1, heads=4, dropout=0.0)
        metrics = evaluate_by_topic(model, examples, self.tokenizer, 192, "cpu", maximum_examples_per_topic=2)
        self.assertIn("whole_number_arithmetic", metrics)
        self.assertEqual(metrics["whole_number_arithmetic"]["total"], 2)
        self.assertGreaterEqual(metrics["whole_number_arithmetic"]["accuracy"], 0.0)
        self.assertFalse(model.training)

    def test_curriculum_waits_for_three_held_out_mastery_evaluations(self):
        controller = CurriculumController(
            [
                {"name": "elementary", "topics": ["addition", "fractions"]},
                {"name": "middle_school", "topics": ["algebra"]},
            ],
            mastery_accuracy=0.9,
            consecutive_evaluations=3,
            require_held_out=True,
        )
        metrics = {"addition": 0.95, "fractions": 0.91}
        self.assertFalse(controller.record_evaluation(metrics, held_out=False))
        self.assertFalse(controller.record_evaluation(metrics, held_out=True))
        self.assertFalse(controller.record_evaluation(metrics, held_out=True))
        self.assertTrue(controller.record_evaluation(metrics, held_out=True))
        self.assertEqual(controller.current_stage, "middle_school")

    def test_one_topic_below_mastery_resets_its_streak(self):
        controller = CurriculumController(
            [{"name": "elementary", "topics": ["addition", "fractions"]}],
            mastery_accuracy=0.9,
            consecutive_evaluations=2,
        )
        self.assertFalse(controller.record_evaluation({"addition": 1.0, "fractions": 1.0}))
        self.assertFalse(controller.record_evaluation({"addition": 1.0, "fractions": 0.5}))
        self.assertFalse(controller.record_evaluation({"addition": 1.0, "fractions": 1.0}))
        self.assertTrue(controller.record_evaluation({"addition": 1.0, "fractions": 1.0}))
        self.assertTrue(controller.is_finished)

    def test_curriculum_state_can_be_restored(self):
        controller = CurriculumController([{"name": "elementary", "topics": ["addition"]}])
        controller.record_evaluation({"addition": 0.95})
        state = controller.state_dict()
        restored = CurriculumController([{"name": "elementary", "topics": ["addition"]}])
        restored.load_state_dict(state)
        self.assertEqual(restored.state_dict(), state)


if __name__ == "__main__":
    unittest.main()
