from __future__ import annotations

import copy
import json
import random
import tempfile
import unittest
from pathlib import Path
from typing import Any

import torch

from ultron_checkpoint import LocalCheckpointStore
from ultron_data import generate_dataset
from ultron_model import CharTokenizer, ULTRONTransformer
from ultron_training import MathBatchStream, train_one_batch


def _assert_nested_equal(test: unittest.TestCase, left: Any, right: Any) -> None:
    if isinstance(left, torch.Tensor) or isinstance(right, torch.Tensor):
        test.assertIsInstance(left, torch.Tensor)
        test.assertIsInstance(right, torch.Tensor)
        test.assertTrue(torch.equal(left, right))
    elif isinstance(left, dict) and isinstance(right, dict):
        test.assertEqual(left.keys(), right.keys())
        for key in left:
            _assert_nested_equal(test, left[key], right[key])
    elif isinstance(left, (tuple, list)) and isinstance(right, (tuple, list)):
        test.assertEqual(len(left), len(right))
        for first, second in zip(left, right):
            _assert_nested_equal(test, first, second)
    else:
        test.assertEqual(left, right)


class ConfiguredModelCheckpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config_path = Path(__file__).resolve().parents[1] / "config.json"
        with config_path.open("r", encoding="utf-8") as handle:
            cls.config = json.load(handle)

    def _make_model(self, tokenizer: CharTokenizer) -> ULTRONTransformer:
        settings = self.config["model"]
        model = ULTRONTransformer(
            vocab_size=tokenizer.vocab_size,
            context_length=int(settings["context_length"]),
            dimension=int(settings["embedding_dimension"]),
            layers=int(settings["transformer_layers"]),
            heads=int(settings["attention_heads"]),
            feedforward_multiplier=int(settings["feedforward_multiplier"]),
            dropout=float(settings["dropout"]),
        )
        self.assertEqual(model.parameter_count(), int(settings["expected_parameter_count"]))
        return model

    def test_full_configured_model_checkpoint_restores_training_state(self):
        previous_threads = torch.get_num_threads()
        torch.set_num_threads(2)
        seed = int(self.config["training"]["seed"])
        random.seed(seed)
        torch.manual_seed(seed)
        try:
            tokenizer = CharTokenizer()
            training = self.config["training"]
            model_settings = self.config["model"]
            topics = self.config["training"]["curriculum"]["stages"][0]["topics"]
            examples = generate_dataset(24, seed=seed, split="train", topics=topics)
            stream = MathBatchStream(
                examples,
                tokenizer,
                context_length=int(model_settings["context_length"]),
                batch_size=2,
                seed=seed,
                shuffle=True,
            )
            model = self._make_model(tokenizer)
            optimizer = torch.optim.AdamW(
                model.parameters(),
                lr=float(training["learning_rate"]),
                weight_decay=float(training["weight_decay"]),
                foreach=False,
            )
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
                optimizer,
                T_max=int(training["maximum_training_steps"]),
            )

            batch = stream.next_batch(tokenizer.stoi[" "])
            loss = train_one_batch(
                model,
                optimizer,
                batch,
                "cpu",
                precision="none",
                gradient_clip_norm=float(training["gradient_clip_norm"]),
            )
            self.assertTrue(torch.isfinite(torch.tensor(loss)).item())
            scheduler.step()

            saved_state = {
                "step": 1,
                "current_topic": str(topics[0]),
                "difficulty": 1,
                "data_position": stream.position,
                "data_epoch": stream.epoch,
                "seed": seed,
                "lease_holder": "configured-model-checkpoint-test",
                "fencing_token": 1,
                "batch_stream": stream.state_dict(),
                "curriculum_state": {"stage_index": 0, "mastery_streaks": {}, "mastery_scores": {}},
                "loss": loss,
                "learning_rate": float(optimizer.param_groups[0]["lr"]),
            }
            expected_model = {
                name: value.detach().clone()
                for name, value in model.state_dict().items()
            }
            expected_optimizer = copy.deepcopy(optimizer.state_dict())
            expected_scheduler = copy.deepcopy(scheduler.state_dict())
            expected_stream = copy.deepcopy(stream.state_dict())

            with tempfile.TemporaryDirectory(prefix="ultron-configured-checkpoint-") as directory:
                store = LocalCheckpointStore(directory, keep_last=2, maximum_file_bytes=45_000_000)
                manifest = store.save(model, optimizer, saved_state, scheduler=scheduler)
                expected_next_random = torch.rand(3)

                fresh_model = self._make_model(tokenizer)
                fresh_optimizer = torch.optim.AdamW(
                    fresh_model.parameters(),
                    lr=float(training["learning_rate"]),
                    weight_decay=float(training["weight_decay"]),
                    foreach=False,
                )
                fresh_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
                    fresh_optimizer,
                    T_max=int(training["maximum_training_steps"]),
                )
                fresh_stream = MathBatchStream(
                    examples,
                    tokenizer,
                    context_length=int(model_settings["context_length"]),
                    batch_size=2,
                    seed=seed + 1,
                    shuffle=True,
                )

                restored = store.load_latest(
                    fresh_model,
                    fresh_optimizer,
                    scheduler=fresh_scheduler,
                    restore_rng=True,
                    map_location="cpu",
                )

                self.assertIsNotNone(restored)
                self.assertEqual(restored["checkpoint_id"], manifest["checkpoint_id"])
                self.assertEqual(restored["step"], 1)
                for name, expected in expected_model.items():
                    self.assertTrue(torch.equal(fresh_model.state_dict()[name], expected), name)
                _assert_nested_equal(self, fresh_optimizer.state_dict(), expected_optimizer)
                self.assertEqual(fresh_scheduler.state_dict(), expected_scheduler)
                fresh_stream.load_state_dict(restored["state"]["batch_stream"])
                _assert_nested_equal(self, fresh_stream.state_dict(), expected_stream)
                self.assertTrue(torch.equal(torch.rand(3), expected_next_random))

                self.assertEqual(len(fresh_optimizer.state), len(list(fresh_model.parameters())))
                self.assertTrue(
                    all(
                        parameter.device.type == "cpu"
                        for group in fresh_optimizer.param_groups
                        for parameter in group["params"]
                    )
                )
        finally:
            torch.set_num_threads(previous_threads)


if __name__ == "__main__":
    unittest.main()
