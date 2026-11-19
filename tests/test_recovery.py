import unittest

import torch

from ultron_recovery_test import run_checkpoint_recovery_test


class FakeStorage:
    def __init__(self, fail_upload_at=None, fail_download_after=None):
        self.objects = {}
        self.fail_upload_at = fail_upload_at
        self.fail_download_after = fail_download_after
        self.upload_count = 0
        self.download_count = 0

    def upload(self, bucket, path, content, content_type):
        self.upload_count += 1
        if self.fail_upload_at == self.upload_count:
            raise RuntimeError("simulated interrupted upload")
        key = (bucket, path)
        if key in self.objects:
            if self.objects[key] != content:
                raise RuntimeError("immutable test object collision")
            return True
        self.objects[key] = bytes(content)
        return False

    def download(self, bucket, path):
        self.download_count += 1
        if self.fail_download_after == self.download_count:
            raise RuntimeError("simulated interrupted download")
        try:
            return self.objects[(bucket, path)]
        except KeyError:
            from ultron_storage import SupabaseStorageError
            raise SupabaseStorageError(404, "Object not found")

    def list_objects(self, bucket, prefix, limit=1000, offset=0):
        start = prefix.strip("/") + "/"
        names = sorted(
            path[len(start):]
            for (bucket_id, path) in self.objects
            if bucket_id == bucket and path.startswith(start)
        )
        return [{"name": name} for name in names[offset:offset + limit]]

    def remove(self, bucket, paths):
        for path in paths:
            self.objects.pop((bucket, path), None)
        return []


class RecoveryTest(unittest.TestCase):
    def test_isolated_remote_restart_restores_exact_next_training_step(self):
        storage = FakeStorage()
        result = run_checkpoint_recovery_test(storage, "owner-test")
        self.assertTrue(result["recovery_test_passed"])
        self.assertEqual(result["saved_step"], 2)
        self.assertEqual(result["resumed_step"], 3)
        self.assertTrue(all(result["checks"].values()))
        self.assertTrue(result["checks"]["source_optimizer_bound_to_model_on_target_device"])
        self.assertTrue(result["checks"]["resumed_optimizer_bound_to_model_on_target_device"])
        self.assertFalse(result["training_status_database_written"])
        self.assertFalse(result["real_training_started"])
        self.assertEqual(storage.objects, {})

    def test_partial_upload_is_cleaned_without_a_completed_receipt(self):
        storage = FakeStorage(fail_upload_at=3)
        with self.assertRaisesRegex(RuntimeError, "simulated interrupted upload"):
            run_checkpoint_recovery_test(storage, "owner-test")
        self.assertEqual(storage.objects, {})

    def test_interrupted_download_does_not_leave_remote_test_objects(self):
        storage = FakeStorage(fail_download_after=9)
        with self.assertRaisesRegex(RuntimeError, "simulated interrupted download"):
            run_checkpoint_recovery_test(storage, "owner-test")
        self.assertEqual(storage.objects, {})

    @unittest.skipUnless(torch.cuda.is_available(), "CUDA is not available in this CI runtime")
    def test_cuda_precision_round_trip_matches_uninterrupted_update(self):
        precision = "bf16" if torch.cuda.is_bf16_supported() else "fp16"
        storage = FakeStorage()
        result = run_checkpoint_recovery_test(storage, "owner-test", device="cuda", precision=precision)
        self.assertTrue(result["recovery_test_passed"])
        self.assertEqual(result["device"], "cuda")
        self.assertEqual(result["precision"], precision)
        self.assertTrue(all(result["checks"].values()))
        self.assertEqual(storage.objects, {})

    def test_recovery_test_requires_path_safe_owner_id(self):
        with self.assertRaises(ValueError):
            run_checkpoint_recovery_test(FakeStorage(), "../other-owner")


if __name__ == "__main__":
    unittest.main()
