import unittest

from scripts.verify_supabase_checkpoint_storage import _cleanup_prefix


class HierarchicalFakeStorage:
    """Model Supabase's immediate-child listing and virtual folders."""

    def __init__(self, objects):
        self.objects = {
            (bucket, path): content
            for bucket, path, content in objects
        }

    def list_objects(self, bucket, prefix, limit=1000, offset=0):
        base = prefix.strip("/") + "/"
        children = {}
        for bucket_id, path in self.objects:
            if bucket_id != bucket or not path.startswith(base):
                continue
            remainder = path[len(base):]
            first, separator, _tail = remainder.partition("/")
            if separator:
                children[first] = {"name": first, "id": None, "metadata": None}
            else:
                children[first] = {"name": first, "id": "object-id", "metadata": {}}
        ordered = [children[name] for name in sorted(children)]
        return ordered[offset:offset + limit]

    def remove(self, bucket, paths):
        for path in paths:
            self.objects.pop((bucket, path), None)
        return []


class SupabaseSmokeCleanupTests(unittest.TestCase):
    def test_cleanup_recurses_into_checkpoint_folders_and_preserves_siblings(self):
        prefix = "owner-1/storage-smoke-123-1"
        storage = HierarchicalFakeStorage([
            ("checkpoints", f"{prefix}/ckpt-abc/manifest.json", b"manifest"),
            ("checkpoints", f"{prefix}/ckpt-abc/model/model-00001.safetensors", b"weights"),
            ("checkpoints", f"{prefix}/ckpt-abc/optimizer/optimizer-00001.safetensors", b"optimizer"),
            ("checkpoints", f"{prefix}/ckpt-abc/upload_receipt.json", b"receipt"),
            ("checkpoints", "owner-1/storage-smoke-other/keep.bin", b"keep"),
        ])

        _cleanup_prefix(storage, "checkpoints", prefix)

        self.assertEqual(
            set(storage.objects),
            {("checkpoints", "owner-1/storage-smoke-other/keep.bin")},
        )

    def test_cleanup_handles_empty_prefix(self):
        storage = HierarchicalFakeStorage([
            ("checkpoints", "owner-1/another-run/keep.bin", b"keep"),
        ])

        _cleanup_prefix(storage, "checkpoints", "owner-1/storage-smoke-empty-1")

        self.assertEqual(len(storage.objects), 1)


if __name__ == "__main__":
    unittest.main()
