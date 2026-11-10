import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pc_common as C
from sa_observe import CATALOG, Observation, Probe
from sa_session import Session


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.obs = Observation(self.root, "runtime", lambda obs: {"fixture": True})
        self.addCleanup(lambda: self.obs.finish(False) if not self.obs.closed else None)

    def test_unknown_checkpoint(self):
        with self.assertRaises(RuntimeError):
            self.obs.checkpoint("unknown")

    def test_duplicate_checkpoint(self):
        self.obs.checkpoint("S00.producer_entry")
        with self.assertRaises(RuntimeError):
            self.obs.checkpoint("S00.producer_entry")

    def test_host_checkpoint_in_runtime(self):
        with self.assertRaises(RuntimeError):
            self.obs.checkpoint("H00.sampler_ready")

    def test_incomplete_success_rejected(self):
        with self.assertRaises(RuntimeError):
            self.obs.finish(True)
        self.assertTrue(self.obs.closed)

    def test_pending_buffer_bounded(self):
        for n in range(4000):
            self.obs.record("command", dict(id=n, sample="x" * 100))
            self.assertLessEqual(len(self.obs.pending), 262144)
        self.assertGreater(self.obs.path.stat().st_size, 0)

    def test_record_cap(self):
        with self.assertRaises(RuntimeError):
            self.obs.record("command", dict(text="x" * 768))

    def test_raw_reserve(self):
        self.obs.bytes = self.obs.caps["raw"] - 131072
        with self.assertRaises(RuntimeError):
            self.obs.record("command", dict(id=1))
        self.obs.record("summary", dict(failure="bounded"), emergency=True)

    def test_file_cap(self):
        path = self.root / "oversize"
        path.write_bytes(b"x" * 65537)
        with self.assertRaises(RuntimeError):
            self.obs.read_file(path)

    def test_read_count_cap(self):
        self.obs.reads = 8192
        with self.assertRaises(RuntimeError):
            self.obs.read_file(self.root / "absent")

    def test_optional_missing_is_none(self):
        self.assertIsNone(self.obs.read_file(self.root / "absent", optional=True))
        self.assertEqual(self.obs.reads, 1)

    def test_roles_cap(self):
        self.obs.roles = 256
        with self.assertRaises(RuntimeError):
            self.obs.role("x", 1, 2)

    def test_metadata_cap(self):
        with self.assertRaises(RuntimeError):
            self.obs.role("x", 1, 2, entries=50001)

    def test_line_callback_cap(self):
        self.obs.lines = 512
        with self.assertRaises(RuntimeError):
            self.obs.callback(line=True)

    def test_hook_callback_cap(self):
        self.obs.callbacks = 65536
        with self.assertRaises(RuntimeError):
            self.obs.callback()

    def test_cpu_cap(self):
        self.obs.cpu = 16
        with self.assertRaises(RuntimeError), self.obs.charge():
            pass

    def test_wall_cap(self):
        self.obs.wall = 31
        with self.assertRaises(RuntimeError), self.obs.charge():
            pass

    def test_slow_checkpoint_rejected(self):
        with patch("sa_observe.time.monotonic_ns", side_effect=[1, 10**9 + 2]):
            with self.assertRaises(RuntimeError):
                self.obs.checkpoint("S00.producer_entry")

    def test_nested_charge_once(self):
        with patch("sa_observe.time.process_time", side_effect=[0, 1]):
            with patch("sa_observe.time.monotonic", side_effect=[0, 2]):
                with self.obs.charge():
                    with self.obs.charge():
                        pass
        self.assertEqual((self.obs.cpu, self.obs.wall), (1, 2))

    def test_cleanup_runs_if_probe_fails(self):
        session = object.__new__(Session)
        session.checkpoint = lambda *args: (_ for _ in ()).throw(KeyboardInterrupt())
        completed = []
        with self.assertRaises(BaseExceptionGroup):
            session.cleanup_call("R11.server_stop.native640", lambda: completed.append(1))
        self.assertEqual(completed, [1])

    def test_global_runtime_deadline_is_clamped(self):
        with patch.dict(os.environ, SA_RUNTIME_DEADLINE="800"):
            budget = C.Budget(clock=lambda: 100)
        self.assertEqual(budget.deadline, 800)
        budget.enter("restore_identity")
        self.assertEqual(budget.stage_end, 200)
        budget.enter("final_cleanup")
        self.assertEqual(budget.stage_end, 700)

    def test_catalog102_with_two_scopes(self):
        self.assertEqual(len(CATALOG), 102)
        self.assertEqual(sum(v == "host" for v in CATALOG.values()), 12)

    def test_required_pool_capability_actual_arrow22(self):
        import pyarrow as pa

        self.assertEqual(pa.__version__, "22.0.0")
        pool = pa.default_memory_pool()
        self.assertIsInstance(pool.bytes_allocated(), int)
        self.assertIsInstance(pool.backend_name, str)
        self.assertIsInstance(pool.max_memory(), int)

    def test_real_probe_synthetic_proc_and_cgroups(self):
        from sa_fixtures import stat

        proc, cg = self.root / "proc", self.root / "cg"
        leaf = cg / "job_42/step_0/user/task_0"
        leaf.mkdir(parents=True)
        (proc / "self").mkdir(parents=True)
        (proc / "self/cgroup").write_text("0::/job_42/step_0/user/task_0\n")
        (proc / "self/mountinfo").write_text(f"1 0 0:1 / {cg} rw - cgroup2 cgroup rw\n")
        (proc / "self/stat").write_text(stat(os.getpid(), 123))
        (proc / "self/status").write_text("VmRSS: 100 kB\nVmHWM: 200 kB\n")
        (proc / "self/io").write_text("read_bytes: 0\nwrite_bytes: 0\n")
        for path in (leaf, leaf.parent, cg / "job_42"):
            for name, text in {
                "memory.current": "100",
                "memory.peak": "200",
                "memory.max": str(32 * 1024**3),
                "memory.stat": "anon 40\nfile 50\nkernel 10\n",
                "memory.events": "max 0\noom 0\noom_kill 0\n",
            }.items():
                (path / name).write_text(text)
        import pyarrow

        probe = Probe(pyarrow, proc=proc)
        with patch.dict(os.environ, SLURM_JOB_ID="42"):
            sample = probe(self.obs)
        self.assertEqual(set(sample["scopes"]), {"job", "step_user", "task"})
        self.assertEqual(sample["starttime"], 123)
        self.assertIsNone(sample["smaps_rollup"])
        self.assertIsNotNone(sample["smaps_unavailable_reason"])
        self.assertIsNotNone(sample["arrow"])
