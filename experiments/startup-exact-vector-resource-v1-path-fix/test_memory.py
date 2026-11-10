import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pc_common as C
import sr_memory as M
import sr_sampler as sampler
from sr_report import memory_result
from test_fixtures import memory_fixture, rewrite, stat


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def fixture(self, version=2):
        proc, leaf = memory_fixture(self.root, version)
        return M.Memory(100, proc=proc), leaf, proc

    def test_v2_root_interfaces_not_required(self):
        memory, leaf, proc = self.fixture()
        row = memory.sample("snapshot_load")
        self.assertEqual(row["scopes"][-1]["availability"], "system_root_no_memory_interface")
        self.assertEqual(row["scopes"][0]["stat"]["anon"], 1024**3)

    def test_v1_infinite_root_limit(self):
        memory, leaf, proc = self.fixture(1)
        row = memory.sample("startup")
        self.assertIsNone(row["scopes"][-1]["limit"])
        self.assertEqual(row["scopes"][0]["events"]["failcnt"], 0)

    def test_v2_membership(self):
        self.assertEqual(M.membership("0::/job/task\n"), (2, M.path_value("/job/task")))

    def test_v1_membership(self):
        self.assertEqual(M.membership("7:cpu:/x\n4:memory:/job\n")[0], 1)

    def test_ambiguous_membership_rejected(self):
        with self.assertRaises(ValueError):
            M.membership("0::/x\n4:memory:/x\n")

    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            M.membership("0::/job/../other\n")

    def test_mount_root_mapping(self):
        r = M.resolve_scope("0::/slurm/job/task\n", "1 0 0:1 /slurm /cg rw - cgroup2 cgroup rw\n")
        self.assertEqual(r["leaf"], "/cg/job/task")
        self.assertEqual(r["ancestors"], ["/cg/job/task", "/cg/job", "/cg"])

    def test_uncovered_mount_rejected(self):
        with self.assertRaises(ValueError):
            M.resolve_scope("0::/different\n", "1 0 0:1 /slurm /cg rw - cgroup2 cg rw\n")

    def test_duplicate_mount_rejected(self):
        with self.assertRaises(ValueError):
            M.resolve_scope("0::/x\n", ("1 0 0:1 / /cg rw - cgroup2 cg rw\n") * 2)

    def test_no_finite_limit_rejected(self):
        memory, leaf, proc = self.fixture()
        (leaf / "memory.max").write_text("max")
        (leaf.parent / "memory.max").write_text("max")
        with self.assertRaises(RuntimeError):
            memory.sample("startup")

    def test_changed_limit_rejected(self):
        memory, leaf, proc = self.fixture()
        memory.sample("startup")
        (leaf / "memory.max").write_text(str(31 * 1024**3))
        with self.assertRaises(RuntimeError):
            memory.sample("startup")

    def test_peak_reset_rejected(self):
        memory, leaf, proc = self.fixture()
        memory.sample("startup")
        (leaf / "memory.peak").write_text(str(3 * 1024**3))
        with self.assertRaises(RuntimeError):
            memory.sample("startup")

    def test_event_counter_reset_rejected(self):
        memory, leaf, proc = self.fixture()
        (leaf / "memory.events").write_text("oom 1\noom_kill 1\nmax 1\n")
        memory.sample("startup")
        (leaf / "memory.events").write_text("oom 0\noom_kill 0\nmax 0\n")
        with self.assertRaises(RuntimeError):
            memory.sample("startup")

    def test_missing_peak_recorded_not_invented(self):
        memory, leaf, proc = self.fixture()
        (leaf / "memory.peak").unlink()
        self.assertIsNone(memory.sample("startup")["scopes"][0]["peak"])

    def test_missing_core_counter_fails(self):
        memory, leaf, proc = self.fixture()
        (leaf / "memory.current").unlink()
        with self.assertRaises(FileNotFoundError):
            memory.sample("startup")

    def test_negative_counter_rejected(self):
        with self.assertRaises(ValueError):
            M.integers("anon -1\n")

    def test_duplicate_counter_rejected(self):
        with self.assertRaises(ValueError):
            M.integers("anon 1\nanon 2\n")

    def test_host_pid_replaced_rejected(self):
        memory, leaf, proc = self.fixture()
        (proc / "100/stat").write_text(stat(100, 9999))
        with self.assertRaises(RuntimeError):
            memory.sample("startup")

    def test_host_membership_change_rejected(self):
        memory, leaf, proc = self.fixture()
        (proc / "100/cgroup").write_text("0::/elsewhere\n")
        with self.assertRaises(RuntimeError):
            memory.sample("startup")

    def test_pid_reuse_is_explicit(self):
        memory, leaf, proc = self.fixture()
        memory.sample("startup")
        (proc / "200/stat").write_text(stat(200, 9999))
        row = memory.sample("startup")
        self.assertTrue(next(p for p in row["processes"] if p["pid"] == 200)["pid_reused"])

    def test_exited_process_recorded(self):
        memory, leaf, proc = self.fixture()
        (proc / "200/stat").unlink()
        r = memory.sample("startup")
        self.assertEqual(r["processes"][1]["availability"], "exited_during_sample")

    def test_process_ceiling(self):
        memory, leaf, proc = self.fixture()
        (leaf / "cgroup.procs").write_text(" ".join(map(str, range(33))))
        with self.assertRaises(RuntimeError):
            memory.sample("startup")

    def test_read_size_cap(self):
        p = self.root / "huge"
        p.write_bytes(b"x" * 65537)
        with self.assertRaises(ValueError):
            M.Reader().read(p)

    def test_read_count_cap(self):
        r = M.Reader()
        r.files = 500000
        with self.assertRaises(RuntimeError):
            r.read(self.root / "x")

    def test_optional_absence_not_zero(self):
        self.assertIsNone(M.Reader().read(self.root / "missing", True))


class SamplerTests(unittest.TestCase):
    def test_actual_sampler_entry_reads_and_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            proc, leaf = memory_fixture(root)
            out = root / "out"
            out.mkdir()
            memory = M.Memory(100, proc=proc)
            aff = {0, 1, 2, 3}
            ticks = [0]

            def get(*args):
                return set(aff)

            def setaff(pid, cpus):
                aff.clear()
                aff.update(cpus)

            def sleep(n):
                ticks[0] += n
                if ticks[0] >= 2:
                    rewrite(out / "memory-stop.json", {"stop": True})

            with (
                patch("sr_sampler.signal.signal"),
                patch("sr_sampler.os.sched_getaffinity", side_effect=get, create=True),
                patch("sr_sampler.os.sched_setaffinity", side_effect=setaff, create=True),
                patch("sr_sampler.select_cores", return_value={"selected": [0, 1, 2, 3]}),
            ):
                result = sampler.run(
                    out, 100, memory_factory=lambda pid: memory, clock=lambda: ticks[0], sleep=sleep
                )
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["samples"], 3)
            self.assertEqual(C.read(out / "memory-context.json")["sampler_cpu"], 3)

    def test_sampler_failure_is_durable(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            aff = [{0, 1, 2, 3}, {3}]
            with (
                patch("sr_sampler.signal.signal"),
                patch("sr_sampler.os.sched_getaffinity", side_effect=aff, create=True),
                patch("sr_sampler.os.sched_setaffinity", create=True),
                patch("sr_sampler.select_cores", return_value={"selected": [0, 1, 2, 3]}),
            ):
                with self.assertRaises(RuntimeError):
                    sampler.run(
                        out,
                        100,
                        memory_factory=lambda p: (_ for _ in []).throw(ValueError("bad cgroup")),
                    )
            self.assertEqual(C.read(out / "memory-summary.json")["status"], "failed")


def memory_case(root, peak=4 * 1024**3):
    proc, leaf = memory_fixture(root)
    memory = M.Memory(100, proc=proc)
    context = {**memory.context, "sampler_cpu": 3, "allocation": {"selected": [0, 1, 2, 3]}}
    rows = []
    for n, phase in enumerate(["startup", "epoch0_hold", "epoch1_hold", "final"]):
        r = memory.sample(phase)
        r.update(start_ns=(n + 1) * 10**9, end_ns=(n + 1) * 10**9 + 1000)
        for scope in r["scopes"]:
            if scope["peak"] is not None:
                scope["peak"] = peak
        rows.append(r)
    summary = dict(
        status="complete",
        error=None,
        samples=4,
        raw_bytes=5000,
        file_reads=500,
        bytes_read=5000,
        cpu_seconds=0.1,
    )
    phases = [{"time_ns": 10**9 + 500}, {"time_ns": 4 * 10**9}]
    return context, rows, summary, phases, dict(pid=100, starttime=1000)


class MemoryDecisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.args = memory_case(Path(self.tmp.name))

    def outcome(self):
        return memory_result(*self.args)

    def test_positive_scoped_only(self):
        r = self.outcome()
        self.assertEqual(r["outcome"], "startup_resource_margin_pass_scoped")
        self.assertFalse(r["calibration_qualified"])
        self.assertFalse(r["workload_memory_qualified"])

    def test_near_cap_cache_cannot_rescue(self):
        for row in self.args[1]:
            for scope in row["scopes"]:
                if scope["peak"] is not None:
                    scope["peak"] = 32 * 1024**3 - 1
                    scope["stat"]["file"] = 30 * 1024**3
        r = self.outcome()
        self.assertIn("conservative_total_charge_margin_not_demonstrated", r["reasons"])
        self.assertEqual(r["cache_subtracted_bytes"], 0)

    def test_missing_peak_inconclusive(self):
        for row in self.args[1]:
            row["scopes"][0]["peak"] = None
        self.assertIn("kernel_peak_unavailable", self.outcome()["reasons"])

    def test_gap_inconclusive(self):
        self.args[1][-1]["start_ns"] += 10**10
        self.args[1][-1]["end_ns"] += 10**10
        self.assertIn("sampling_gap", self.outcome()["reasons"])

    def test_oom_delta_inconclusive(self):
        self.args[1][-1]["scopes"][0]["events"]["oom_kill"] = 1
        self.assertIn("limit_or_oom_event_delta", self.outcome()["reasons"])

    def test_missing_hold_inconclusive(self):
        self.args[1][1]["phase"] = "different"
        self.assertIn("reader_hold_not_observed", self.outcome()["reasons"])

    def test_missing_host_mapping_inconclusive(self):
        self.args[-1]["starttime"] = 999
        self.assertIn("host_container_process_mapping_unobserved", self.outcome()["reasons"])

    def test_stable_limits_required(self):
        self.args[1][-1]["scopes"][0]["limit"] = 31 * 1024**3
        with self.assertRaises(ValueError):
            self.outcome()

    def test_resource_budget_checked(self):
        self.args[2]["cpu_seconds"] = 61
        with self.assertRaises(ValueError):
            self.outcome()

    def test_scope_mapping_cannot_be_relabelled(self):
        self.args[0]["leaf"] = "/other"
        with self.assertRaises(ValueError):
            self.outcome()
