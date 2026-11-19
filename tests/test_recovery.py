import unittest

from ultron_recovery_test import run_checkpoint_recovery_test


class FakeStorage:
    def __init__(self):
        self.objects = {}

    def upload(self, bucket, path, content, content_type):
        key = (bucket, path)
        if key in self.objects:
            if self.objects[key] != content:
                raise RuntimeError("immutable test object collision")
            return True
        self.objects[key] = bytes(content)
        return False

    def download(self, bucket, path):
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
        self.assertFalse(result["training_status_database_written"])
        self.assertFalse(result["real_training_started"])
        self.assertEqual(storage.objects, {})

    def test_recovery_test_requires_path_safe_owner_id(self):
        with self.assertRaises(ValueError):
            run_checkpoint_recovery_test(FakeStorage(), "../other-owner")


if __name__ == "__main__":
    unittest.main()
