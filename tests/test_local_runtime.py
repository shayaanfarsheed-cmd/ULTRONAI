import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from ultron_local_runtime import (
    LocalDummyRuntime,
    RuntimeErrorState,
    _pid_exists,
    verify_checkpoint,
)


class LocalDummyRuntimeTests(unittest.TestCase):
    def wait_for(self, runtime, expected, timeout=5):
        deadline = time.monotonic() + timeout
        last = None
        while time.monotonic() < deadline:
            try:
                last = runtime.status()
            except FileNotFoundError:
                time.sleep(0.02)
                continue
            if last.get("state") == expected and last.get("process_exited"):
                return last
            time.sleep(0.02)
        self.fail(f"Timed out waiting for {expected}; last status={last!r}")

    # /proc/<pid>/stat fields after comm include starttime at index 19.
    def test_linux_zombie_is_reported_as_exited(self):
        zombie_stat = "4321 (python worker) Z 1 4321 4321 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 12345"
        with patch.object(Path, "read_text", return_value=zombie_stat):
            self.assertFalse(_pid_exists(4321))

    def test_linux_running_process_is_reported_as_running(self):
        running_stat = "4321 (python worker with spaces) R 1 4321 4321 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 12345"
        with patch.object(Path, "read_text", return_value=running_stat):
            self.assertTrue(_pid_exists(4321))

    def test_linux_reused_pid_is_not_mistaken_for_original_worker(self):
        current_stat = "4321 (unrelated process) R 1 4321 4321 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 99999"
        with patch.object(Path, "read_text", return_value=current_stat):
            self.assertFalse(_pid_exists(4321, expected_start_ticks=12345))

    def test_terminal_status_without_matching_process_identity_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = LocalDummyRuntime(temp)
            runtime.status_file.write_text(
                '{"schema":1,"run_id":"current","state":"COMPLETED"}',
                encoding="utf-8",
            )
            runtime.process_file.write_text(
                '{"run_id":"previous","pid":4321}',
                encoding="utf-8",
            )
            status = runtime.status()
            self.assertFalse(status["process_exited"])
            self.assertFalse(runtime.lock.exists())

    def test_hard_ram_cap_is_refused_before_start(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = LocalDummyRuntime(temp)
            with self.assertRaisesRegex(RuntimeErrorState, "no verified OS-level RAM"):
                runtime.start(require_hard_ram_cap=True)
            self.assertFalse(runtime.lock.exists())

    def test_explicit_start_runs_dummy_worker_and_checkpoints(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = LocalDummyRuntime(temp)
            run_id = runtime.start(batches=2, delay=0.01)
            self.assertTrue(run_id)
            result = self.wait_for(runtime, "COMPLETED")
            self.assertEqual(result["run_id"], run_id)
            checkpoint = verify_checkpoint(Path(temp))
            self.assertEqual(checkpoint["completed_batches"], 2)
            self.assertEqual(checkpoint["worker"], "dummy-only")
            self.assertFalse(runtime.lock.exists())

    def test_local_stop_checkpoints_at_batch_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = LocalDummyRuntime(temp)
            run_id = runtime.start(batches=100, delay=0.04)
            self.assertEqual(runtime.request_stop(), "STOP_REQUESTED")
            result = self.wait_for(runtime, "STOPPED")
            self.assertEqual(result["run_id"], run_id)
            self.assertEqual(result["stop_reason"], "local_request")
            self.assertTrue(result["process_exited"])
            self.assertEqual(verify_checkpoint(Path(temp))["run_id"], run_id)

    def test_duplicate_start_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = LocalDummyRuntime(temp)
            runtime.start(batches=100, delay=0.05)
            with self.assertRaisesRegex(RuntimeErrorState, "already active"):
                runtime.start()

    def test_stop_is_idempotent_after_worker_stops(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = LocalDummyRuntime(temp)
            runtime.start(batches=1, delay=0)
            self.wait_for(runtime, "COMPLETED")
            self.assertEqual(runtime.request_stop(), "COMPLETED")

    def test_corrupt_checkpoint_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "checkpoint.json"
            path.write_text('{"schema":1,"sha256":"bad"}', encoding="utf-8")
            with self.assertRaisesRegex(RuntimeErrorState, "corrupt"):
                verify_checkpoint(Path(temp))

    def test_stale_lock_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = LocalDummyRuntime(temp)
            runtime.lock.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeErrorState, "inspect it"):
                runtime.start()


if __name__ == "__main__":
    unittest.main()
