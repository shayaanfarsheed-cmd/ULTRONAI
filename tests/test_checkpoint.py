import random
import tempfile
import unittest
from pathlib import Path

import torch
from torch import nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import StepLR

from ultron_checkpoint import CheckpointError, LocalCheckpointStore


class CheckpointTests(unittest.TestCase):
    def _make_training_objects(self):
        model = nn.Sequential(nn.Linear(4, 8), nn.GELU(), nn.Linear(8, 2))
        optimizer = AdamW(model.parameters(), lr=0.001)
        scheduler = StepLR(optimizer, step_size=2, gamma=0.5)
        sample = torch.randn(3, 4)
        target = torch.randn(3, 2)
        loss = torch.nn.functional.mse_loss(model(sample), target)
        loss.backward()
        optimizer.step()
        scheduler.step()
        return model, optimizer, scheduler

    def _state(self, step, fencing_token=1, lease_holder="test-worker"):
        return {
            "step": step,
            "current_topic": "fractions",
            "difficulty": 2,
            "data_position": step * 12,
            "seed": 20261117,
            "lease_holder": lease_holder,
            "fencing_token": fencing_token,
        }

    def test_round_trip_restores_model_optimizer_scheduler_and_rng(self):
        with tempfile.TemporaryDirectory() as directory:
            model, optimizer, scheduler = self._make_training_objects()
            expected_weights = {key: value.detach().clone() for key, value in model.state_dict().items()}
            expected_exp_avg = next(iter(optimizer.state.values()))["exp_avg"].clone()
            expected_scheduler = scheduler.state_dict()
            random.seed(1234)
            torch.manual_seed(555)
            store = LocalCheckpointStore(directory)
            store.save(model, optimizer, self._state(1), scheduler)
            expected_python_next = random.random()
            expected_torch_next = torch.rand(1)

            with torch.no_grad():
                for parameter in model.parameters():
                    parameter.add_(10)
            random.seed(999)
            torch.manual_seed(999)

            restored = store.load_latest(model, optimizer, scheduler, restore_rng=True)
            self.assertIsNotNone(restored)
            self.assertEqual(restored["step"], 1)
            self.assertEqual(restored["state"]["current_topic"], "fractions")
            for key, value in model.state_dict().items():
                self.assertTrue(torch.equal(value, expected_weights[key]))
            restored_exp_avg = next(iter(optimizer.state.values()))["exp_avg"]
            self.assertTrue(torch.equal(restored_exp_avg, expected_exp_avg))
            self.assertEqual(scheduler.state_dict(), expected_scheduler)
            self.assertEqual(random.random(), expected_python_next)
            self.assertTrue(torch.equal(torch.rand(1), expected_torch_next))

    def test_corrupt_newest_checkpoint_falls_back_to_previous_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            model, optimizer, scheduler = self._make_training_objects()
            store = LocalCheckpointStore(directory)
            first_weights = {key: value.detach().clone() for key, value in model.state_dict().items()}
            first = store.save(model, optimizer, self._state(1), scheduler)
            with torch.no_grad():
                for parameter in model.parameters():
                    parameter.add_(1)
            second = store.save(model, optimizer, self._state(2), scheduler)
            newest_model = Path(directory) / second["checkpoint_id"] / "model.safetensors"
            newest_model.write_bytes(b"corrupted checkpoint")
            with torch.no_grad():
                for parameter in model.parameters():
                    parameter.zero_()
            restored = store.load_latest(model, optimizer, scheduler, restore_rng=False)
            self.assertEqual(restored["checkpoint_id"], first["checkpoint_id"])
            self.assertEqual(restored["step"], 1)
            for key, value in model.state_dict().items():
                self.assertTrue(torch.equal(value, first_weights[key]))

    def test_interrupted_write_never_replaces_latest_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            model, optimizer, scheduler = self._make_training_objects()
            store = LocalCheckpointStore(directory)
            first = store.save(model, optimizer, self._state(1), scheduler)

            def interrupt(stage, path):
                if stage == "after_artifacts":
                    raise RuntimeError("simulated power loss")

            with self.assertRaises(RuntimeError):
                store.save(model, optimizer, self._state(2), scheduler, fault_hook=interrupt)
            restored = store.load_latest(model, optimizer, scheduler, restore_rng=False)
            self.assertEqual(restored["checkpoint_id"], first["checkpoint_id"])
            self.assertEqual(restored["step"], 1)

    def test_retention_keeps_last_three_verified_checkpoints(self):
        with tempfile.TemporaryDirectory() as directory:
            model, optimizer, scheduler = self._make_training_objects()
            store = LocalCheckpointStore(directory, keep_last=3)
            for step in range(1, 6):
                store.save(model, optimizer, self._state(step), scheduler)
            valid = store.list_valid_checkpoints()
            self.assertEqual([item["step"] for item in valid], [5, 4, 3])
            self.assertEqual(len(list(Path(directory).glob("ckpt-*"))), 3)

    def test_checkpoint_requires_lease_and_fencing_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            model, optimizer, scheduler = self._make_training_objects()
            store = LocalCheckpointStore(directory)
            with self.assertRaises(CheckpointError):
                store.save(model, optimizer, {"step": 1}, scheduler)

    def test_checkpoint_artifacts_are_not_pickle_files(self):
        with tempfile.TemporaryDirectory() as directory:
            model, optimizer, scheduler = self._make_training_objects()
            store = LocalCheckpointStore(directory)
            manifest = store.save(model, optimizer, self._state(1), scheduler)
            folder = Path(directory) / manifest["checkpoint_id"]
            names = {item.name for item in folder.iterdir()}
            self.assertIn("model.safetensors", names)
            self.assertIn("optimizer.safetensors", names)
            self.assertIn("rng.safetensors", names)
            self.assertIn("state.json", names)
            self.assertFalse(any(name.endswith((".pt", ".pth", ".pkl", ".pickle")) for name in names))

    def test_step_cannot_move_backwards(self):
        with tempfile.TemporaryDirectory() as directory:
            model, optimizer, scheduler = self._make_training_objects()
            store = LocalCheckpointStore(directory)
            store.save(model, optimizer, self._state(5), scheduler)
            with self.assertRaises(CheckpointError):
                store.save(model, optimizer, self._state(4), scheduler)

    def test_new_lease_holder_requires_new_fencing_token(self):
        with tempfile.TemporaryDirectory() as directory:
            model, optimizer, scheduler = self._make_training_objects()
            store = LocalCheckpointStore(directory)
            store.save(model, optimizer, self._state(1, fencing_token=3, lease_holder="worker-a"), scheduler)
            with self.assertRaises(CheckpointError):
                store.save(model, optimizer, self._state(2, fencing_token=3, lease_holder="worker-b"), scheduler)


if __name__ == "__main__":
    unittest.main()
