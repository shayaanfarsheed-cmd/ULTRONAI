import unittest

import torch

from ultron_model import ALPHABET, CharTokenizer, ULTRONTransformer


class ModelTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(20261117)
        self.tokenizer = CharTokenizer()
        self.model = ULTRONTransformer(vocab_size=self.tokenizer.vocab_size, dropout=0.0)

    def test_parameter_count_is_in_requested_range_and_matches_config(self):
        count = self.model.parameter_count()
        self.assertGreaterEqual(count, 3000000)
        self.assertLessEqual(count, 5000000)
        self.assertEqual(count, 4022094)

    def test_forward_shape_and_finite_loss(self):
        tokens = torch.randint(0, self.tokenizer.vocab_size, (2, 24))
        logits, loss = self.model(tokens, tokens)
        self.assertEqual(tuple(logits.shape), (2, 24, len(ALPHABET)))
        self.assertIsNotNone(loss)
        self.assertTrue(bool(torch.isfinite(loss)))

    def test_causal_mask_blocks_future_information(self):
        self.model.eval()
        first = torch.randint(0, self.tokenizer.vocab_size, (1, 16))
        second = first.clone()
        second[:, 10] = (second[:, 10] + 1) % self.tokenizer.vocab_size
        with torch.no_grad():
            first_logits, _ = self.model(first)
            second_logits, _ = self.model(second)
        self.assertTrue(torch.allclose(first_logits[:, :10], second_logits[:, :10], atol=1e-6))

    def test_tokenizer_round_trip(self):
        sample = "Question: 12 + 7\nAnswer: 19\n"
        self.assertEqual(self.tokenizer.decode(self.tokenizer.encode(sample)), sample)

    def test_tokenizer_rejects_unknown_characters(self):
        with self.assertRaises(ValueError):
            self.tokenizer.encode("12 × 3")

    def test_context_length_is_enforced(self):
        tokens = torch.zeros((1, 129), dtype=torch.long)
        with self.assertRaises(ValueError):
            self.model(tokens)

    def test_initialization_is_random_and_not_loaded_from_external_weights(self):
        torch.manual_seed(1)
        first = ULTRONTransformer(dropout=0.0)
        torch.manual_seed(2)
        second = ULTRONTransformer(dropout=0.0)
        self.assertFalse(torch.equal(first.token_embedding.weight, second.token_embedding.weight))


if __name__ == "__main__":
    unittest.main()
