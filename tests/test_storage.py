import tempfile
import unittest

import torch
from torch import nn

from ultron_checkpoint import LocalCheckpointStore
from ultron_storage import RemoteCheckpointStore, SupabaseStorageError


class FakeStorage:
    def __init__(self):
        self.objects = {}

    def upload(self, bucket, path, content, content_type):
        key = (bucket, path)
        if key in self.objects:
            if self.objects[key] != content:
                raise SupabaseStorageError(409, "Different content already exists")
            return True
        self.objects[key] = bytes(content)
        return False

    def download(self, bucket, path):
        try:
            return self.objects[(bucket, path)]
        except KeyError:
            raise SupabaseStorageError(404, "Object not found")

    def list_objects(self, bucket, prefix, limit=1000, offset=0):
        start = prefix.strip("/") + "/"
        names = sorted(path[len(start):] for (bucket_id, path) in self.objects if bucket_id == bucket and path.startswith(start))
        return [{"name": name} for name in names[offset:offset + limit]]

    def remove(self, bucket, paths):
        for path in paths:
            self.objects.pop((bucket, path), None)
        return []


class RemoteCheckpointTests(unittest.TestCase):
    def _save(self, store, model, optimizer, step):
        return store.save(
            model,
            optimizer,
            {
                "step": step,
                "current_topic": "fractions",
                "difficulty": 1,
                "data_position": step * 4,
                "seed": 20261117,
                "lease_holder": "worker-a",
                "fencing_token": 1,
            },
        )

    def test_upload_and_download_checkpoint_round_trip(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as target_dir:
            model = nn.Linear(4, 2)
            optimizer = torch.optim.AdamW(model.parameters())
            x = torch.randn(2, 4)
            model(x).sum().backward()
            optimizer.step()
            source = LocalCheckpointStore(source_dir)
            manifest = self._save(source, model, optimizer, 1)
            storage = FakeStorage()
            remote = RemoteCheckpointStore(storage)
            uploaded = remote.upload_checkpoint(source, manifest["checkpoint_id"], "owner-1", "run-1")
            self.assertTrue(uploaded["verified"])
            self.assertEqual(len(storage.objects), 6)
            target = LocalCheckpointStore(target_dir)
            downloaded = remote.download_checkpoint("owner-1", "run-1", manifest["checkpoint_id"], target)
            self.assertEqual(downloaded["step"], 1)
            self.assertTrue(target.verify_checkpoint(manifest["checkpoint_id"])[0])

    def test_remote_verification_detects_corrupt_object(self):
        with tempfile.TemporaryDirectory() as source_dir:
            model = nn.Linear(4, 2)
            optimizer = torch.optim.AdamW(model.parameters())
            x = torch.randn(2, 4)
            model(x).sum().backward()
            optimizer.step()
            source = LocalCheckpointStore(source_dir)
            manifest = self._save(source, model, optimizer, 1)
            storage = FakeStorage()
            remote = RemoteCheckpointStore(storage)
            remote.upload_checkpoint(source, manifest["checkpoint_id"], "owner-1", "run-1")
            path = f"owner-1/run-1/{manifest['checkpoint_id']}/model.safetensors"
            storage.objects[("checkpoints", path)] = b"corrupt"
            with self.assertRaises(Exception):
                remote.verify_remote_checkpoint("owner-1", "run-1", manifest["checkpoint_id"])

    def test_remote_prune_keeps_last_three_valid_checkpoints(self):
        with tempfile.TemporaryDirectory() as source_dir:
            model = nn.Linear(4, 2)
            optimizer = torch.optim.AdamW(model.parameters())
            x = torch.randn(2, 4)
            model(x).sum().backward()
            optimizer.step()
            source = LocalCheckpointStore(source_dir, keep_last=10)
            storage = FakeStorage()
            remote = RemoteCheckpointStore(storage, keep_last=3)
            ids = []
            for step in range(1, 6):
                manifest = self._save(source, model, optimizer, step)
                ids.append(manifest["checkpoint_id"])
                remote.upload_checkpoint(source, manifest["checkpoint_id"], "owner-1", "run-1")
            removed = remote.prune_remote("owner-1", "run-1")
            self.assertEqual(len(removed), 2)
            self.assertFalse(any(path.startswith(f"owner-1/run-1/{ids[0]}/") for _, path in storage.objects))
            self.assertTrue(any(path.startswith(f"owner-1/run-1/{ids[-1]}/") for _, path in storage.objects))

    def test_remote_prune_does_not_delete_corrupt_checkpoint(self):
        with tempfile.TemporaryDirectory() as source_dir:
            model = nn.Linear(4, 2)
            optimizer = torch.optim.AdamW(model.parameters())
            x = torch.randn(2, 4)
            model(x).sum().backward()
            optimizer.step()
            source = LocalCheckpointStore(source_dir, keep_last=10)
            storage = FakeStorage()
            remote = RemoteCheckpointStore(storage, keep_last=2)
            manifests = []
            for step in range(1, 4):
                manifest = self._save(source, model, optimizer, step)
                manifests.append(manifest)
                remote.upload_checkpoint(source, manifest["checkpoint_id"], "owner-1", "run-1")
            corrupt_id = manifests[0]["checkpoint_id"]
            corrupt_path = f"owner-1/run-1/{corrupt_id}/manifest.json"
            storage.objects[("checkpoints", corrupt_path)] = b"corrupt"
            remote.prune_remote("owner-1", "run-1")
            self.assertIn(("checkpoints", corrupt_path), storage.objects)

    def test_remote_candidate_order_is_newest_first(self):
        with tempfile.TemporaryDirectory() as source_dir:
            model = nn.Linear(4, 2)
            optimizer = torch.optim.AdamW(model.parameters())
            model(torch.randn(2, 4)).sum().backward()
            optimizer.step()
            source = LocalCheckpointStore(source_dir, keep_last=10)
            storage = FakeStorage()
            remote = RemoteCheckpointStore(storage, keep_last=3)
            manifests = []
            for step in range(1, 4):
                manifest = self._save(source, model, optimizer, step)
                manifests.append(manifest)
                remote.upload_checkpoint(source, manifest["checkpoint_id"], "owner-1", "run-1")
            candidates = remote.list_remote_candidates("owner-1", "run-1")
            self.assertEqual([item["step"] for item in candidates], [3, 2, 1])


if __name__ == "__main__":
    unittest.main()
