import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import torch
from torch import nn

from ultron_checkpoint import LocalCheckpointStore
from ultron_storage import HuggingFaceCheckpointStore, RemoteCheckpointStore, SupabaseStorageClient, SupabaseStorageError


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

    def test_new_secret_key_is_sent_only_as_apikey(self):
        captured = {}

        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return b"{}"

        def opener(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return Response()

        client = SupabaseStorageClient(
            "https://example.supabase.co",
            "sb_secret_storage_test",
            opener=opener,
        )
        client._request(
            "POST",
            "object/checkpoints/owner/run/checkpoint/model.safetensors",
            body=b"weights",
            content_type="application/octet-stream",
            upsert=False,
        )
        self.assertEqual(captured["request"].get_header("Apikey"), "sb_secret_storage_test")
        self.assertIsNone(captured["request"].get_header("Authorization"))
        self.assertNotIn("sb_secret_storage_test", repr(client))

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
            self.assertEqual(len(uploaded["manifest_sha256"]), 64)
            self.assertEqual(len(storage.objects), 6)
            target = LocalCheckpointStore(target_dir)
            downloaded = remote.download_checkpoint("owner-1", "run-1", manifest["checkpoint_id"], target)
            self.assertEqual(downloaded["step"], 1)
            self.assertTrue(target.verify_checkpoint(manifest["checkpoint_id"])[0])


    def test_sharded_remote_checkpoint_round_trip_and_prune(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as target_dir:
            model = nn.Sequential(*[nn.Linear(256, 256) for _ in range(4)])
            optimizer = torch.optim.AdamW(model.parameters())
            model(torch.randn(2, 256)).sum().backward()
            optimizer.step()
            source = LocalCheckpointStore(source_dir, maximum_file_bytes=1_500_000)
            manifest = self._save(source, model, optimizer, 1)
            self.assertGreater(sum(name.startswith("model-") for name in manifest["files"]), 1)
            self.assertGreater(sum(name.startswith("optimizer-") for name in manifest["files"]), 1)
            storage = FakeStorage()
            remote = RemoteCheckpointStore(storage, maximum_file_bytes=1_500_000)
            uploaded = remote.upload_checkpoint(source, manifest["checkpoint_id"], "owner-1", "run-1")
            self.assertTrue(uploaded["verified"])
            self.assertEqual(len(remote.list_remote_candidates("owner-1", "run-1")), 1)
            target = LocalCheckpointStore(target_dir, maximum_file_bytes=1_500_000)
            downloaded = remote.download_checkpoint("owner-1", "run-1", manifest["checkpoint_id"], target)
            self.assertEqual(downloaded["step"], 1)
            self.assertTrue(target.verify_checkpoint(manifest["checkpoint_id"])[0])
            self.assertEqual(remote.prune_remote("owner-1", "run-1"), [])

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
            model_shard = next(name for name in manifest["files"] if name.startswith("model-"))
            path = f"owner-1/run-1/{manifest['checkpoint_id']}/{model_shard}"
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


    def test_private_huggingface_checkpoint_backup_round_trip(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as download_dir:
            model = nn.Linear(4, 2)
            optimizer = torch.optim.AdamW(model.parameters())
            model(torch.randn(2, 4)).sum().backward()
            optimizer.step()
            source = LocalCheckpointStore(source_dir)
            manifest = self._save(source, model, optimizer, 7)

            class FakeHFAPI:
                def __init__(self):
                    self.files = {}
                def repo_info(self, repo_id, repo_type, revision, token):
                    return SimpleNamespace(private=True)
                def upload_folder(self, repo_id, folder_path, repo_type, revision, path_in_repo, commit_message, token):
                    for path in Path(folder_path).iterdir():
                        if path.is_file():
                            self.files[path_in_repo + "/" + path.name] = path.read_bytes()
                def list_repo_tree(self, repo_id, repo_type, revision, path_in_repo, recursive, expand, token):
                    return [SimpleNamespace(path=name) for name in sorted(self.files)]

            api = FakeHFAPI()
            def download_file(repo_id, filename, repo_type, revision, token):
                destination = Path(download_dir) / filename.replace("/", "_")
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(api.files[filename])
                return str(destination)

            backup = HuggingFaceCheckpointStore(
                "owner/ultron-checkpoints",
                "hf_test_token",
                api=api,
                download_file=download_file,
            )
            uploaded = backup.upload_checkpoint(source, manifest["checkpoint_id"], "owner-1", "run-1")
            self.assertTrue(uploaded["verified"])
            self.assertEqual(uploaded["step"], 7)
            candidates = backup.list_candidates("owner-1", "run-1")
            self.assertEqual([item["step"] for item in candidates], [7])
            target = LocalCheckpointStore(target_dir)
            restored = backup.download_checkpoint("owner-1", "run-1", manifest["checkpoint_id"], target)
            self.assertEqual(restored["step"], 7)
            self.assertTrue(target.verify_checkpoint(manifest["checkpoint_id"])[0])
            self.assertNotIn("hf_test_token", repr(backup))

    def test_huggingface_backup_rejects_public_repository(self):
        class PublicHFAPI:
            def repo_info(self, repo_id, repo_type, revision, token):
                return SimpleNamespace(private=False)
        with self.assertRaises(ValueError):
            HuggingFaceCheckpointStore(
                "owner/public-model",
                "hf_test_token",
                api=PublicHFAPI(),
                download_file=lambda **kwargs: "",
            )

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
            committed_candidates = remote.list_remote_candidates("owner-1", "run-1", maximum_step=2)
            self.assertEqual([item["step"] for item in committed_candidates], [2, 1])


if __name__ == "__main__":
    unittest.main()
