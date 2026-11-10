"""Offline synthetic correctness checks only; no native database or Torch execution."""

import copy
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from collections import Counter, defaultdict
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import experiment as E
import pc_common as C
import pc_control as control
import pc_interface as I
import pc_job as job
import pc_measure as M
import pc_metadata as metadata
import pc_proc as P
import pc_report as report
import pc_resources as resources
import pc_restore as restore
import pc_settings as settings
import pc_stats as stats
from pc_runtime import Journal
from pc_trace import Trace
from test_support import CLOCK, VECTOR, FakeBase, FakeConnection, snapshot


def rewrite(p, value):
    p.write_text(json.dumps(value, sort_keys=True) + "\n")


def retained(bias=0, half=False, gradient=False):
    rows = []
    for e in (0, 1):
        for c in C.CELLS:
            for q in range(200):
                for slot in ("r0", "r1"):
                    for rep in (1, 2, 3):
                        ms = (
                            5
                            + (bias * (1 if q < 100 or not half else -1) if slot == "r1" else 0)
                            + (rep * 0.2 if gradient else 0)
                        )
                        rows.append(
                            dict(
                                epoch=e,
                                cell=c,
                                group=str(q),
                                query_id=str(q) + "-votes108",
                                physical_slot=slot,
                                repetition=rep,
                                outer_ms=ms,
                                query_position=q,
                            )
                        )
    return rows


class FakeProc:
    def __init__(self, journal):
        self.j = journal
        self.i = 0
        self.records = []

    def bind(self, r, work, epoch=0):
        self.i += 1
        r.physical = dict(
            reader=r.identity,
            cell=r.mode,
            pid=100 + self.i,
            starttime=1000 + self.i,
            postmaster=10 + C.CELLS.index(r.mode),
            server="/run/" + r.mode,
            socket="/run/" + r.mode + "/socket",
            epoch=epoch,
            cpu=1 + C.CELLS.index(r.mode) if epoch == 0 else 2 - C.CELLS.index(r.mode),
            schedstat_available=False,
        )
        self.j.emit("identities", r.physical.copy())

    def repin(self, r, e):
        r.physical.update(
            epoch=e, cpu=1 + C.CELLS.index(r.mode) if e == 0 else 2 - C.CELLS.index(r.mode)
        )

    def sample(self, r, boundary, **meta):
        if self.j.hold:
            raise AssertionError("Proc read inside primary buffer")
        a = CLOCK.now()
        b = CLOCK.now()
        ident = r.physical.copy()

        def process(pid, start, cpu, ppid):
            return dict(
                affinity=[cpu],
                allowed_cpus=str(cpu),
                status_pid=pid,
                status_ppid=ppid,
                threads=1,
                stat=dict(
                    pid=pid,
                    starttime=start,
                    processor=cpu,
                    ppid=ppid,
                    state="S",
                    minflt=0,
                    majflt=0,
                    utime=0,
                    stime=0,
                ),
                io=dict(read_bytes=0, write_bytes=0),
                context_switches=dict(voluntary_ctxt_switches=0, nonvoluntary_ctxt_switches=0),
            )

        row = dict(
            boundary=boundary,
            identity=ident,
            backend=process(ident["pid"], ident["starttime"], ident["cpu"], ident["postmaster"]),
            client=process(999, 999, 0, 0),
            start_ns=a,
            end_ns=b,
            outer_ms=(b - a) / 1e6,
            **meta,
        )
        self.records.append(row)
        self.j.emit("telemetry", row)


def mock_acquisition(root, quality_negative=False, real_backend=False):
    p = root / "inputs"
    p.mkdir()
    out = root / "run"
    out.mkdir()
    s = C.read(E.HERE / "SCHEDULE.json")
    shutil.copyfile(E.HERE / "SCHEDULE.json", p / "SCHEDULE.json")
    actual = C.lines(E.SOURCE / "queries.jsonl")
    items = [dict(group=i["group"], query={**i["query"], "vector": VECTOR}) for i in actual]
    items = copy.deepcopy(actual)
    for i in items:
        i["query"]["vector"] = VECTOR
    truth = dict(truth_strict=list(range(9)), truth_ties=[9], truth_k=10)

    def value(c):
        ids = list(range(10))
        ids[-1] = 10 if quality_negative and c == "partial640" else 9
        return dict(
            ids=ids,
            distances=[i / 20 for i in ids],
            recall=0.9 if quality_negative and c == "partial640" else 1.0,
            valid=True,
            returned_count=10,
            duplicate_count=0,
            predicate_violation_count=0,
        )

    rewrite(p / "baseline-results.json", {i["query"]["id"]: truth for i in items})
    (p / "eligibility.json").write_bytes(
        C.encoded(dict(source_ids=list(range(40)), votes=[108] * 40))
    )
    (p / "b2d-references.jsonl").write_text(
        "".join(
            json.dumps(dict(query_id=i["query"]["id"], outcomes={c: value(c) for c in C.CELLS}))
            + "\n"
            for i in items
        )
    )
    budget = C.Budget(clock=lambda: 0)
    budget.enter("restore_identity")
    journal = Journal(out, budget)
    trace = Trace(budget, journal.emit)
    observer = metadata.Observer(
        budget, lambda n, r: journal.emit(n, {**r, **getattr(observer, "tags", {})})
    )
    FakeBase.trace = trace
    FakeBase.fail = False
    FakeBase.behavior = "quality" if quality_negative else "good"
    targets = C.CONTRACT["targets"]
    stack = ExitStack()
    base_class = FakeBase
    bundle = Path("/bundle")
    works = {c: Path("/run") / c for c in C.CELLS}
    try:
        if real_backend:
            _, base_class = real_frozen_backend()
            bundle = E.ROOT / "trials/torch-reviews-first"
            works = {c: restore_fixture(root / c, c) for c in C.CELLS}

            def connect(dsn, **kwargs):
                return __import__("pc_trace").Connection(
                    RealConnection("partial640" if "partial640" in dsn else "native640"), trace
                )

            stack.enter_context(patch("psycopg.connect", side_effect=connect))
        factory = I.Factory(
            base_class,
            bundle,
            works,
            targets,
            observer,
            budget,
            journal.emit,
        )
        main = {c: factory.create(c, c.split("640")[0] + "-reference") for c in C.CELLS}
        snap = main["native640"].backend.snapshot() if real_backend else snapshot()
        if real_backend:
            factory.snapshot = snap
            for r in main.values():
                r.backend._snapshot = snap
        if real_backend:
            (p / "eligibility.json").write_bytes(
                C.encoded(
                    dict(
                        source_ids=snap.source_ids,
                        votes=[row["metadata"]["total_votes"] for row in snap.rows],
                    )
                )
            )
            rewrite(p / "experiment.json", dict(snapshot_identity=snap.identity))
            (p / "queries.jsonl").write_text("".join(json.dumps(i) + "\n" for i in items))
            admitted, startup_proof = __import__("pc_snapshot").prepare_requests(main, factory, p)
            self_check = __import__("pc_snapshot").validate_snapshot(snap, p)
            assert startup_proof == self_check
        else:
            admitted = __import__("pc_results").admit(snap, items)
        factory.requests = {i["query"]["id"]: i["query"] for i in admitted}
        proc = FakeProc(journal)
        for c, r in main.items():
            proc.bind(r, factory.works[c])
        budget.enter("conformance_quality")
        result = M.acquire(
            factory,
            main,
            budget,
            p,
            out,
            admitted,
            observer,
            proc,
            journal,
            lambda *a, **k: None,
            budget.enter,
            lambda *a: None,
        )
        factory.close()
        journal.close()
        return dict(
            result=result,
            budget=budget,
            journal=journal,
            observer=observer,
            trace=trace,
            factory=factory,
            proc=proc,
            package=p,
            out=out,
            schedule=s,
        )
    finally:
        stack.close()


class ProtocolChecks(unittest.TestCase):
    def test_fixed_contract(self):
        self.assertEqual(C.sha(E.HERE / "CONTRACT.json"), C.CONTRACT_SHA)

    def test_frozen_schedule(self):
        self.assertEqual(C.sha(E.HERE / "SCHEDULE.json"), C.CONTRACT["schedule_sha256"])

    def test_frozen_design(self):
        self.assertEqual(C.sha(E.HERE / "DESIGN.md"), C.CONTRACT["design_sha256"])

    def test_search_inventory(self):
        events = list(M.events(C.read(E.HERE / "SCHEDULE.json")))
        self.assertEqual(len(events), 16242)
        self.assertEqual(dict(Counter(e[0] for e in events)), C.OPERATIONS)

    def test_plan_inventory(self):
        self.assertEqual(len(list(report.plan_events(C.read(E.HERE / "SCHEDULE.json")))), 4200)

    def test_factor_balance(self):
        s = C.read(E.HERE / "SCHEDULE.json")
        g = defaultdict(Counter)
        for r in s["primary_bursts"]:
            g[r["epoch"], r["cell"], r["reader"]][
                r["within_cell_position"], r["conditioning_order"][-1]
            ] += 1
        self.assertEqual(len(g), 8)
        self.assertTrue(all(sorted(v.values()) == [50] * 4 for v in g.values()))

    def test_nonmatching_request(self):
        with self.assertRaises(ValueError):
            C.context(dict(k=11, filter=dict(field="m_000000", op="gte", value=108)))

    def test_unused_560_not_spendable(self):
        b = C.Budget(clock=lambda: 0)
        b.enter("epoch0")
        b.calls = 16242
        with self.assertRaises(RuntimeError):
            b.reserve("priming")

    def test_per_operation_ceiling(self):
        b = C.Budget(clock=lambda: 0)
        b.enter("epoch0")
        b.operations["priming"] = 80
        with self.assertRaises(RuntimeError):
            b.reserve("priming")

    def test_stage_expiry(self):
        clock = [0]
        b = C.Budget(clock=lambda: clock[0])
        b.enter("epoch0")
        clock[0] = 1801
        with self.assertRaises(RuntimeError):
            b.reserve("measurement")

    def test_cleanup_reserve(self):
        clock = [0]
        b = C.Budget(clock=lambda: clock[0])
        b.enter("epoch1")
        clock[0] = 9601
        with self.assertRaises(RuntimeError):
            b.reserve("measurement")

    def test_sql_ceiling(self):
        b = C.Budget(clock=lambda: 0)
        b.enter("epoch0")
        b.sql["observer"] = 13500
        with self.assertRaises(RuntimeError):
            b.sql_reserve("observer")

    def test_primary_buffer(self):
        with tempfile.TemporaryDirectory() as d:
            b = C.Budget(clock=lambda: 0)
            b.enter("epoch0")
            j = Journal(Path(d), b)
            j.hold = True
            j.emit("searches", dict(x=1))
            self.assertFalse(list(Path(d).iterdir()))
            j.hold = False
            j.flush_buffer()
            j.close()
            self.assertEqual(C.lines(Path(d) / "searches.jsonl"), [dict(x=1)])

    def test_evidence_cap(self):
        with tempfile.TemporaryDirectory() as d:
            b = C.Budget(clock=lambda: 0)
            b.enter("epoch0")
            j = Journal(Path(d), b)
            j.bytes = 1024**3
            with self.assertRaises(RuntimeError):
                j.emit("x", dict(a=1))

    def test_whole_copy_independent(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {"SLURM_JOB_ID": "42"}):
            root = Path(d).resolve()
            src = root / "src"
            (src / "pgdata").mkdir(parents=True)
            (src / "pgdata/x").write_bytes(b"wal bytes")
            for n in ("admin.pgpass", "reader.pgpass", "pg_hba.conf"):
                (src / n).write_text("private")
                (src / n).chmod(0o600)
            shutil.copyfile(E.SOURCE / "frozen/source-index.json", src / "database-identity.json")
            (src / "database-identity.json").chmod(0o600)
            before = restore.inventory(src)
            proof = restore.clone(src, root / "copy")
            self.assertTrue(proof["independent_inodes"])
            self.assertEqual(restore.inventory(src), before)
            (root / "copy/pgdata/x").write_text("newwal")
            self.assertEqual((src / "pgdata/x").read_bytes(), b"wal bytes")

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d).resolve()
            (p / "a").write_text("x")
            (p / "link").symlink_to(p / "a")
            with self.assertRaises(ValueError):
                restore.inventory(p)

    def test_hardlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d).resolve()
            (p / "a").write_text("x")
            os.link(p / "a", p / "b")
            with self.assertRaises(ValueError):
                restore.inventory(p)

    def test_special_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d).resolve()
            os.mkfifo(p / "fifo")
            with self.assertRaises(ValueError):
                restore.inventory(p)

    def test_unclean_control_rejected(self):
        with self.assertRaises(ValueError):
            restore.control_state(
                Path("/mock"),
                run=lambda *a, **k: SimpleNamespace(
                    stdout="Database cluster state: in production\nDatabase system identifier: 42\n"
                ),
            )

    def test_clean_control(self):
        self.assertEqual(
            restore.control_state(
                Path("/mock"),
                run=lambda *a, **k: SimpleNamespace(
                    stdout="Database cluster state: shut down\nDatabase system identifier: 42\n"
                ),
            )["fields"]["Database system identifier"],
            "42",
        )

    def test_resource_formula(self):
        self.assertEqual(
            resources.demands(100, 200, 3, 4)["scratch_bytes"], (12 * (300 + 2 * 1024**3) + 9) // 10
        )

    def test_memory_unchanged(self):
        self.assertEqual(
            settings.memory_proof(
                [
                    settings.memory_record(c, (128 * 1024**2, 16, 4 * 1024**2, "64MB", "0"))
                    for c in C.CELLS
                ]
            )["conservative_bound_bytes"],
            15300820992,
        )

    def test_stat_parentheses(self):
        f = ["0"] * 50
        f[0] = "S"
        f[1] = "12"
        f[19] = "500"
        f[36] = "3"
        r = P.parse_stat("99 (name (with) spaces) " + " ".join(f))
        self.assertEqual((r["pid"], r["ppid"], r["starttime"], r["processor"]), (99, 12, 500, 3))

    def test_stat_truncated(self):
        with self.assertRaises(ValueError):
            P.parse_stat("1 (x) S")

    def test_cpu_ranges(self):
        self.assertEqual(P.cpu_list("1-3,7"), {1, 2, 3, 7})

    def test_cpu_negative(self):
        with self.assertRaises(ValueError):
            P.cpu_list("-1")

    def test_distinct_cores_required(self):
        with tempfile.TemporaryDirectory() as d:
            for cpu in range(4):
                p = Path(d) / ("cpu" + str(cpu)) / "topology"
                p.mkdir(parents=True)
                (p / "physical_package_id").write_text("0")
                (p / "core_id").write_text(str(cpu // 2))
            with self.assertRaises(ValueError):
                P.select_cores(range(4), Path(d))

    def test_optional_missing_not_zero(self):
        proc = object.__new__(P.Proc)
        proc.root = Path("/mock")
        proc.read = lambda p: (_ for _ in ()).throw(PermissionError())
        self.assertIsNone(proc.optional_read(Path("/mock")))

    def test_required_missing_fails(self):
        proc = object.__new__(P.Proc)
        proc.root = Path("/mock")
        proc.read = lambda p: (_ for _ in ()).throw(PermissionError())
        with self.assertRaises(PermissionError):
            proc.stat(10)

    def test_immutable_binding(self):
        v = I.freeze(dict(settings=dict(x=1)))
        with self.assertRaises(TypeError):
            v["settings"]["x"] = 2

    def test_read_only_source_mount(self):
        with patch.dict(os.environ, {"SLURM_JOB_ID": "42"}):
            with patch("pc_job.read", return_value=dict(image_sha256="x")):
                cmd = job.container_command(
                    Path("/pkg"),
                    Path("/bundle"),
                    Path("/prepared"),
                    Path("/out"),
                    Path("/work"),
                    "apptainer",
                    0,
                )
            self.assertIn(C.CONTRACT["retained_source_work"] + ":/retained:ro", cmd)
            self.assertNotIn("--writable", cmd)

    def test_one_physical_core_hint(self):
        self.assertIn(
            "--hint=nomultithread",
            control.command(
                Path("/pkg"),
                dict(
                    account="x",
                    bundle="/b",
                    prepared="/p",
                    campaign="/c",
                    workspace="/w",
                    sources="/s",
                    apptainer="/a",
                    host_python="/usr/bin/python3",
                ),
                [],
            ),
        )

    def test_unknown_dispatch_no_retry(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            r = dict(dispatch={"block-0": {"status": "unknown"}})
            with patch("pc_control.subprocess.run") as run:
                with self.assertRaises(ValueError):
                    control.dispatch(p, p, r, 0)
                run.assert_not_called()

    def test_reservation_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "manifest.json").write_text("{}")
            control.reserve(p, p, p / "campaign")
            with self.assertRaises(FileExistsError):
                control.reserve(p, p, p / "another")

    def test_archive_traversal(self):
        self.archive_bad("../escape")

    def test_archive_link(self):
        self.archive_bad("x", link=True)

    def archive_bad(self, name, link=False):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            a = p / (C.PREFIX + "20261027T120000Z.mock.tar.gz")
            root = a.name[:-7]
            with tarfile.open(a, "w:gz") as t:
                m = tarfile.TarInfo(root + "/" + name)
                m.size = 1
                if link:
                    m.type = tarfile.SYMTYPE
                    m.linkname = "/etc/passwd"
                t.addfile(m, io.BytesIO(b"x"))
            with self.assertRaises(ValueError):
                E.extract_data(a, p / "out")

    def test_corrected_campaign_prefix(self):
        self.assertIn("prefix=PREFIX", Path(control.__file__).read_text())
        self.assertNotIn('prefix="reviews-partial-ann', Path(control.__file__).read_text())

    def test_all_56_intervals(self):
        v = stats.timing(retained())
        self.assertEqual(v["passed_intervals"], 56)
        self.assertTrue(v["all_pass"])
        self.assertFalse(v["treatment_speed_verdict"])

    def test_physical_bias_not_hidden_by_labels(self):
        self.assertFalse(stats.timing(retained(0.2))["all_pass"])

    def test_opposing_half_bias_cannot_qualify(self):
        v = stats.timing(retained(0.15, half=True))
        self.assertFalse(v["all_pass"])
        self.assertTrue(
            any(not r["equivalent"] for n, r in v["intervals"].items() if n.startswith("half/"))
        )

    def test_retained_transient_rejected(self):
        v = stats.timing(retained(gradient=True))
        self.assertFalse(v["all_pass"])
        self.assertTrue(
            any(
                not r["equivalent"] for n, r in v["intervals"].items() if n.startswith("stability/")
            )
        )

    def test_missing_retained_row(self):
        with self.assertRaises(ValueError):
            stats.timing(retained()[:-1])

    def test_duplicate_retained_row(self):
        r = retained()
        r[-1] = r[0]
        with self.assertRaises(ValueError):
            stats.timing(r)


class AcquisitionChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.patch = patch("time.perf_counter_ns", CLOCK.now)
        cls.patch.start()
        cls.driver = patch("psycopg.__version__", "3.3.6")
        cls.driver.start()
        cls.result = mock_acquisition(Path(cls.tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls.driver.stop()
        cls.patch.stop()
        cls.tmp.cleanup()

    def test_complete_counts(self):
        self.assertEqual(dict(self.result["budget"].operations), C.OPERATIONS)
        self.assertEqual(self.result["budget"].calls, 16242)

    def test_complete_fresh_epochs(self):
        self.assertEqual(len(self.result["factory"].readers), 10)
        self.assertEqual(self.result["factory"].maximum_live, 6)
        self.assertTrue(all(r.closed for r in self.result["factory"].readers))

    def test_search_order_from_frozen_schedule(self):
        actual = C.lines(self.result["out"] / "searches.jsonl")
        expected = list(M.events(self.result["schedule"]))
        self.assertEqual(
            [(r["operation"], r["query_id"], r["reader"]) for r in actual],
            [(a, b, c) for a, b, c, d in expected],
        )
        for r, (_, _, _, meta) in zip(actual, expected):
            self.assertTrue(all(r.get(k) == v for k, v in meta.items()))

    def test_plan_order_from_frozen_schedule(self):
        plans = C.lines(self.result["out"] / "plans.jsonl")
        expected = list(report.plan_events(self.result["schedule"]))
        self.assertEqual(len(plans), 4200)
        for p, e in zip(plans, expected):
            self.assertTrue(all(p.get(k) == v for k, v in e.items()), (p, e))

    def test_no_observer_between_seven_calls(self):
        searches = C.lines(self.result["out"] / "searches.jsonl")
        sql = C.lines(self.result["out"] / "sql.jsonl")
        bursts = defaultdict(list)
        for r in searches:
            if r["operation"] in ("warmup", "measurement"):
                bursts[r["reader"], r["query_id"]].append(r)
        self.assertEqual(len(bursts), 1600)
        for rr in bursts.values():
            a = min(r["start_ns"] for r in rr)
            b = max(r["end_ns"] for r in rr)
            self.assertFalse(any(a < r.get("start_ns", r.get("time_ns")) < b for r in sql))

    def test_telemetry_complete(self):
        placement = [
            dict(
                kind="allocation",
                selected=[0, 1, 2, 3],
                allowed=[0, 1, 2, 3],
                topology=[dict(cpu=i, socket=0, core=i) for i in range(4)],
                scheduler_wait_accounting_enabled=False,
            )
        ]
        r = report.telemetry(
            C.lines(self.result["out"] / "telemetry.jsonl"),
            C.lines(self.result["out"] / "searches.jsonl"),
            {r["reader"]: r for r in C.lines(self.result["out"] / "identities.jsonl")},
            placement,
            True,
        )
        self.assertEqual(r["bundles"], 4992)
        self.assertEqual(r["primary_bursts"], 1600)

    def test_missing_telemetry_cannot_qualify(self):
        rows = C.lines(self.result["out"] / "telemetry.jsonl")[:-1]
        searches = C.lines(self.result["out"] / "searches.jsonl")
        ids = {r["reader"]: r for r in C.lines(self.result["out"] / "identities.jsonl")}
        placement = [
            dict(
                kind="allocation",
                selected=[0, 1, 2, 3],
                allowed=[0, 1, 2, 3],
                topology=[dict(cpu=i, socket=0, core=i) for i in range(4)],
                scheduler_wait_accounting_enabled=False,
            )
        ]
        with self.assertRaises(ValueError):
            report.telemetry(rows, searches, ids, placement, True)

    def test_pid_identity_drift(self):
        rows = C.lines(self.result["out"] / "telemetry.jsonl")
        rows[0]["identity"]["starttime"] += 1
        ids = {r["reader"]: r for r in C.lines(self.result["out"] / "identities.jsonl")}
        placement = [
            dict(
                kind="allocation",
                selected=[0, 1, 2, 3],
                allowed=[0, 1, 2, 3],
                topology=[dict(cpu=i, socket=0, core=i) for i in range(4)],
                scheduler_wait_accounting_enabled=False,
            )
        ]
        with self.assertRaises(ValueError):
            report.telemetry(rows, [], ids, placement, False)

    def test_closed_reader_not_replayed(self):
        reader = self.result["factory"].readers[0]
        with self.assertRaises(RuntimeError):
            reader.check()

    def test_native_sql_matches_attempts(self):
        self.assertEqual(self.result["trace"].search_sql, 16242)

    def test_observer_cap(self):
        self.assertLessEqual(self.result["budget"].sql["observer"], 13500)

    def test_generic_plan_rejected(self):
        p = copy.deepcopy(C.lines(self.result["out"] / "plans.jsonl")[1000])
        p["packet"]["cached"][0]["generic_plans"] = 1
        # The acquisition wrapper checks zero generic plans before accepting packets.
        observer = SimpleNamespace(tags={}, plan=lambda *a, **k: p["packet"])
        with self.assertRaises(RuntimeError):
            M.plan(observer, None, None)


class QualificationNegativeChecks(unittest.TestCase):
    def test_quality_stops_at_610(self):
        with (
            tempfile.TemporaryDirectory() as d,
            patch("time.perf_counter_ns", CLOCK.now),
            patch("psycopg.__version__", "3.3.6"),
        ):
            r = mock_acquisition(Path(d), True)
            self.assertEqual(r["budget"].calls, 610)
            self.assertEqual(r["observer"].plan_packets, 808)
            self.assertEqual(r["result"]["outcome"], "closed_negative_quality")
            self.assertEqual(len(r["factory"].readers), 2)

    def test_native_error_charged_and_closed(self):
        b = C.Budget(clock=lambda: 0)
        b.enter("epoch0")
        FakeBase.trace = Trace(b, lambda *a: None)
        f = I.Factory(
            FakeBase,
            Path("/b"),
            {c: Path("/w") / c for c in C.CELLS},
            C.CONTRACT["targets"],
            None,
            b,
            lambda *a: None,
        )
        r = f.create("native640", "native-reference")
        q = dict(id="x", k=10, filter=dict(field="m_000000", op="gte", value=108), vector=VECTOR)
        f.requests["x"] = q
        FakeBase.fail = True
        try:
            with self.assertRaises(RuntimeError):
                r.native(q, b, "priming")
            self.assertTrue(r.closed)
            self.assertEqual(b.calls, 1)
            with self.assertRaises(RuntimeError):
                r.native(q, b, "priming")
            self.assertEqual(b.calls, 1)
        finally:
            FakeBase.fail = False
            f.close()

    def test_replaced_connection_fails(self):
        b = C.Budget(clock=lambda: 0)
        b.enter("epoch0")
        FakeBase.trace = Trace(b, lambda *a: None)
        f = I.Factory(
            FakeBase,
            Path("/b"),
            {c: Path("/w") / c for c in C.CELLS},
            C.CONTRACT["targets"],
            None,
            b,
            lambda *a: None,
        )
        r = f.create("native640", "r")
        r.backend.conn = object()
        with self.assertRaises(RuntimeError):
            r.check()
        r.backend.conn = r.connection
        f.close()


def reseal(p):
    manifest = p / "manifest.json"
    if manifest.exists():
        manifest.unlink()
    C.save(
        manifest,
        dict(
            version=C.VERSION,
            files={
                str(f.relative_to(p)): C.sha(f)
                for f in sorted(p.rglob("*"))
                if f.is_file() and f.name != "submission-binding.json"
            },
        ),
    )


def complete_raw_fixture(root, acquisition, package):
    """Make data-only mock evidence for verifier correctness, never native evidence."""
    campaign = root / (C.PREFIX + "20261027T120000Z.mock")
    campaign.mkdir()
    run = campaign / "run"
    shutil.copytree(acquisition["out"], run)
    p = package
    for n in ("baseline-results.json", "eligibility.json", "b2d-references.jsonl"):
        shutil.copyfile(acquisition["package"] / n, p / n)
    items = C.lines(E.SOURCE / "queries.jsonl")
    for i in items:
        i["query"]["vector"] = VECTOR
    (p / "queries.jsonl").write_text("".join(json.dumps(i) + "\n" for i in items))
    cfg = C.read(p / "experiment.json")
    cfg["queries_sha256"] = C.sha(p / "queries.jsonl")
    rewrite(p / "experiment.json", cfg)
    reseal(p)
    source = dict(
        files={c + "/pgdata/x": dict(bytes=1, mode=384, uid=1, sha256="x") for c in C.CELLS},
        bytes=2,
        file_count=2,
    )
    for c in C.CELLS:
        source["files"][c + "/database-identity.json"] = dict(
            bytes=957, mode=384, uid=1, sha256=restore.IDENTITY_SHA
        )
    source["bytes"] = sum(v["bytes"] for v in source["files"].values())
    source["file_count"] = len(source["files"])
    for n in ("source-before.json", "source-after.json"):
        rewrite(run / n, source)
    rewrite(
        run / "source-control.json",
        {
            c: dict(
                fields={"Database cluster state": "shut down", "Database system identifier": "42"}
            )
            for c in C.CELLS
        },
    )
    rewrite(
        run / "copies.json",
        {
            c: dict(
                pgdata_inventory_sha256=C.digest(
                    dict(files={"x": source["files"][c + "/pgdata/x"]}, bytes=1, file_count=1)
                ),
                independent_inodes=True,
                database_identity_sha256=restore.IDENTITY_SHA,
            )
            for c in C.CELLS
        },
    )
    for n in ("protected-source-before.json", "protected-source-after.json"):
        rewrite(run / n, dict(mock_only=True))
    rewrite(campaign / "protected-source-before.json", dict(mock_only=True))
    rewrite(
        run / "host-launch.json",
        dict(host_python="/usr/bin/python3", step_export="ALL", python_no_bytecode="1"),
    )
    rewrite(run / "runtime-identity.json", C.CONTRACT["runtime"])
    rewrite(
        run / "snapshot-qualified.json",
        dict(
            eligibility_sha256=C.sha(p / "eligibility.json"),
            snapshot_identity=C.read(p / "experiment.json")["snapshot_identity"],
            field_map={"m_000000": "total_votes"},
            rows=len(C.read(p / "eligibility.json")["source_ids"]),
        ),
    )
    rewrite(
        run / "final-integrity.json",
        dict(
            module_sha256=C.CONTRACT["runtime"]["module_sha256"],
            copies={
                c: dict(
                    data_bits_verified=True,
                    rows=247286,
                    original_graph_files=C.CONTRACT["graphs"]["native640"],
                    partial_graph_files=C.CONTRACT["graphs"]["partial640"]["partial"]
                    if c == "partial640"
                    else {},
                )
                for c in C.CELLS
            },
        ),
    )
    rewrite(
        run / "stopped-copies.json",
        dict(
            graphs_match=True,
            controls={c: dict(fields={"Database cluster state": "shut down"}) for c in C.CELLS},
        ),
    )
    rewrite(run / "cleanup.json", dict(errors=[], all_readers_closed=True, databases_stopped=True))
    rewrite(
        run / "memory-preflight.json",
        settings.memory_proof(
            [
                settings.memory_record(c, (128 * 1024**2, 16, 4 * 1024**2, "64MB", "0"))
                for c in C.CELLS
            ]
        ),
    )
    resources = dict(
        graph_hashes_match=True,
        source=C.CONTRACT["retained_source_work"],
        quota={
            fs: dict(
                filesystem_free_bytes=10,
                space_available_lower=10,
                required_bytes=1,
                filesystem_free_inodes=10,
                inodes_available_lower=10,
                required_inodes=1,
            )
            for fs in ("/home", "/scratch")
        },
    )
    rewrite(run / "resource-preflight.json", resources)
    rewrite(campaign / "resource-preflight-login.json", resources)
    expected = C.read(p / "b2d-catalogs.json")
    cats = [
        dict(
            copy=c,
            phase=phase,
            session_user="torch_owner",
            value=expected[c],
            sha256=C.digest(expected[c]),
        )
        for phase in ("before_build", "final")
        for c in C.CELLS
    ]
    (run / "catalogs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in cats))
    placement = [
        dict(
            kind="allocation",
            selected=[0, 1, 2, 3],
            allowed=[0, 1, 2, 3],
            topology=[dict(cpu=i, socket=0, core=i) for i in range(4)],
            scheduler_wait_accounting_enabled=False,
        )
    ]
    (run / "placement.jsonl").write_text("".join(json.dumps(r) + "\n" for r in placement))
    rewrite(
        run / "status.json",
        dict(
            status="complete",
            final_integrity_verified=True,
            provider_calls=0,
            new_fits=0,
            confirmation_queries=0,
            operations=dict(acquisition["budget"].operations),
            backend_searches=16242,
            search_sql=16242,
            reader_connections=10,
            maximum_live_readers=6,
            plan_packets=4200,
            sql=dict(acquisition["budget"].sql),
            telemetry=dict(
                bundles=4992, proc_reads=40000, affinity_operations=10000, telemetry_seconds=1
            ),
            elapsed_seconds=100,
            result=acquisition["result"],
        ),
    )
    rewrite(
        campaign / "submission.json",
        dict(
            host_python="/usr/bin/python3",
            campaign="/home/dar579/torch-reviews-results/" + campaign.name,
            counts=C.COUNTS,
            package_manifest_sha256=C.sha(p / "manifest.json"),
            jobs={"block-0": "42"},
            dispatch={"block-0": dict(status="submitted", job_id="42")},
        ),
    )
    rewrite(
        campaign / "scheduler-evidence.json", dict(sacct_stdout="42_0|COMPLETED|0:0|00:20:00\n")
    )
    rewrite(
        run / "host-exit.json",
        dict(
            exit_code=0,
            protected_sources_unchanged=True,
            provider_calls=0,
            array_job_id="42",
            array_task_id="0",
            job_id="42",
        ),
    )
    rewrite(run / "job-exit.json", dict(exit_code=0))
    rewrite(
        run / "LOCK.json",
        dict(
            complete=True,
            files={
                f.name: C.sha(f)
                for f in run.iterdir()
                if f.is_file()
                and f.name
                not in (
                    "LOCK.json",
                    "job-exit.json",
                    "host-exit.json",
                    "protected-source-after.json",
                )
            },
        ),
    )
    return campaign


class SealedVerificationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.package = E.build(cls.root / "seal", testing=True)
        cls.patch = patch("time.perf_counter_ns", CLOCK.now)
        cls.patch.start()
        cls.driver = patch("psycopg.__version__", "3.3.6")
        cls.driver.start()
        mockroot = cls.root / "mock"
        mockroot.mkdir()
        cls.acq = mock_acquisition(mockroot)
        cls.campaign = complete_raw_fixture(cls.root, cls.acq, cls.package)

    @classmethod
    def tearDownClass(cls):
        cls.driver.stop()
        cls.patch.stop()
        cls.tmp.cleanup()

    def test_full_trusted_reconstruction(self):
        value = report.analyze(self.campaign, self.package, self.root / "analysis")
        self.assertEqual(value["outcome"], "calibration_qualified_scoped")
        self.assertEqual(value["timing"]["passed_intervals"], 56)
        self.assertFalse(value["treatment_speed_qualified"])

    def test_wrong_snapshot_proof_cannot_qualify(self):
        original_read = report.read
        for field in ("snapshot_identity", "eligibility_sha256", "field_map", "rows"):
            with self.subTest(field=field):

                def changed(path):
                    row = original_read(path)
                    if Path(path).name == "snapshot-qualified.json":
                        row[field] = "changed"
                    return row

                with patch("pc_report.read", side_effect=changed):
                    with self.assertRaisesRegex(ValueError, "Startup snapshot"):
                        report.analyze(
                            self.campaign, self.package, self.root / ("wrong-proof-" + field)
                        )

    def test_raw_lock_tamper(self):
        with patch("pc_report.sha", return_value="tamper"):
            with self.assertRaises(ValueError):
                report.raw_lock(self.campaign / "run")

    def test_seal_detects_code_tamper(self):
        with patch(
            "pc_common.sha",
            side_effect=lambda p: (
                "tamper" if Path(p).name == "pc_runtime.py" else C.sha_original(p)
            ),
        ):
            with self.assertRaises(ValueError):
                C.verify(self.package)

    def test_synthetic_cannot_submit(self):
        with self.assertRaises(ValueError):
            control.submit(self.package, Path("/bundle"), Path("/results"))

    def test_no_downloaded_execution(self):
        text = Path(E.__file__).read_text()
        self.assertNotIn("exec(", text)
        self.assertNotIn("importlib", text)

    def test_campaign_prefix_binding(self):
        self.assertEqual(C.campaign_identity(self.campaign, self.package), self.campaign.name)

    def test_wrong_campaign_manifest(self):
        with patch(
            "pc_common.read",
            return_value=dict(
                campaign="/home/" + self.campaign.name,
                package_manifest_sha256="wrong",
                counts=C.COUNTS,
                jobs={"block-0": "42"},
                dispatch={"block-0": dict(status="submitted", job_id="42")},
            ),
        ):
            with self.assertRaises(ValueError):
                C.campaign_identity(self.campaign, self.package)


C.sha_original = C.sha


class ProcGuardChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.proc = object.__new__(P.Proc)
        p = self.proc
        p.root = self.root
        p.budget = C.Budget(clock=lambda: 0)
        p.budget.enter("epoch0")
        p.reads = p.affinity = p.bundles = p.elapsed_ns = p.depth = 0
        p.client = 999
        p.client_threads = None
        p.optional = {123: False}
        p.optional_schedstat = False
        p.scheduler_enabled = False
        p.previous = {}
        p.peak_rss_kib = {}
        p.get = lambda pid: {1}
        p.layout = dict(allowed=[0, 1, 2, 3], selected=[0, 1, 2, 3])
        p.set = lambda pid, cpus: None
        self.write()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, **values):
        p = self.root / "123"
        p.mkdir(exist_ok=True)
        f = ["0"] * 50
        f[0] = "S"
        f[1] = "10"
        f[7] = str(values.get("minflt", 5))
        f[19] = str(values.get("start", 50))
        f[36] = str(values.get("cpu", 1))
        (p / "stat").write_text("123 (postgres) " + " ".join(f))
        (p / "status").write_text(
            "Pid: "
            + str(values.get("pid", 123))
            + "\nPPid: 10\nNSpid: 123\nThreads: "
            + str(values.get("threads", 1))
            + "\nCpus_allowed_list: 1\nMems_allowed_list: 0\nVmRSS: 10 kB\nVmHWM: 12 kB"
            + "\nvoluntary_ctxt_switches: 0\nnonvoluntary_ctxt_switches: 0\n"
        )
        (p / "io").write_text(
            "read_bytes: " + str(values.get("read_bytes", 0)) + "\nwrite_bytes: 0\n"
        )

    def test_valid_owned_identity(self):
        self.assertEqual(self.proc.process(123, 50, 1)["affinity"], [1])

    def test_pid_reuse(self):
        self.write(start=51)
        with self.assertRaises(RuntimeError):
            self.proc.process(123, 50, 1)

    def test_namespace_mismatch(self):
        self.write(pid=12)
        with self.assertRaises(RuntimeError):
            self.proc.process(123, 50, 1)

    def test_migration(self):
        self.write(cpu=2)
        with self.assertRaises(RuntimeError):
            self.proc.process(123, 50, 1)

    def test_affinity_drift(self):
        self.proc.get = lambda pid: {1, 2}
        with self.assertRaises(RuntimeError):
            self.proc.process(123, 50, 1)

    def test_unexpected_worker_thread(self):
        self.write(threads=2)
        with self.assertRaises(RuntimeError):
            self.proc.process(123, 50, 1)

    def test_negative_io(self):
        self.write(read_bytes=-1)
        with self.assertRaises(RuntimeError):
            self.proc.process(123, 50, 1)

    def test_decreasing_counter(self):
        self.proc.process(123, 50, 1)
        self.write(minflt=4)
        with self.assertRaises(RuntimeError):
            self.proc.process(123, 50, 1)

    def test_affinity_permission_denied(self):
        self.proc.set = lambda *a: (_ for _ in ()).throw(PermissionError())
        with self.assertRaises(PermissionError):
            self.proc.pin(123, 1)

    def test_cpu_outside_allocation(self):
        with self.assertRaises(RuntimeError):
            self.proc.pin(123, 99)

    def test_owned_source_uid_required(self):
        (self.root / "file").write_text("x")
        with patch("pc_restore.os.getuid", return_value=-1):
            with self.assertRaises(ValueError):
                restore.inventory(self.root.resolve())

    def test_proc_read_ceiling(self):
        self.proc.reads = 44000
        with self.assertRaises(RuntimeError):
            self.proc.read(self.root / "123/stat")

    def test_affinity_ceiling(self):
        self.proc.affinity = 11200
        with self.assertRaises(RuntimeError):
            self.proc.mask(123)


class LauncherChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.package = self.root / "package with spaces"
        self.package.mkdir()
        # A synthetic srun preserves the relevant export/exec boundary; no Slurm call.
        self.srun = self.bin / "srun"
        self.srun.write_text(
            "#!"
            + sys.executable
            + "\n"
            + """import os,sys
args=sys.argv[1:]
while args and args[0].startswith('--'):args.pop(0)
if '--export=ALL' not in sys.argv or not os.path.isabs(args[0]):
    print('synthetic execve(): python3: No such file or directory',file=sys.stderr)
    raise SystemExit(2)
os.execve(args[0],args,dict(os.environ))
"""
        )
        self.srun.chmod(0o700)
        (self.package / "pc_job.py").write_text("""import json,os,sys
from pathlib import Path
Path(sys.argv[1],'observed.json').write_text(json.dumps(dict(args=sys.argv[1:],export=os.environ.get('SLURM_EXPORT_ENV'),no_bytecode=os.environ.get('PYTHONDONTWRITEBYTECODE'),executable=sys.executable)))
""")
        self.args = [
            str(self.package),
            "/bundle",
            "/prepared",
            "/campaign",
            "/workspace",
            "/results",
            "/apptainer",
            str(Path(sys.executable).resolve()),
        ]
        self.env = {
            "PATH": str(self.bin),
            "SLURM_EXPORT_ENV": "NONE",
            "SLURM_JOB_ID": "42",
            "SLURM_CPUS_PER_TASK": "4",
        }

    def tearDown(self):
        self.tmp.cleanup()

    def run_launcher(self, script=None, args=None):
        return subprocess.run(
            [
                "/bin/bash",
                str(script or E.HERE / "LAUNCHER.sh"),
                *(args if args is not None else self.args),
            ],
            env=self.env,
            capture_output=True,
            text=True,
        )

    def test_reproduces_original_bare_interpreter_failure(self):
        original = (
            E.ROOT
            / "trials/torch-reviews-partial-calibration-v1"
            / "torch-partial-calibration-v1/slurm/measure.sbatch"
        )
        r = self.run_launcher(original, self.args[:7])
        self.assertEqual(r.returncode, 2)
        self.assertIn("execve()", r.stderr)
        self.assertFalse((self.package / "observed.json").exists())

    def test_absolute_interpreter_under_restricted_environment(self):
        r = self.run_launcher()
        self.assertEqual(r.returncode, 0, r.stderr)
        row = C.read(self.package / "observed.json")
        self.assertEqual(row["export"], "ALL")
        self.assertEqual(Path(row["executable"]).resolve(), Path(sys.executable).resolve())

    def test_all_arguments_round_trip_including_spaces(self):
        r = self.run_launcher()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(C.read(self.package / "observed.json")["args"], self.args)

    def test_no_bytecode_export_survives_step(self):
        self.assertEqual(self.run_launcher().returncode, 0)
        self.assertEqual(C.read(self.package / "observed.json")["no_bytecode"], "1")

    def test_relative_interpreter_rejected_before_step(self):
        r = self.run_launcher(args=[*self.args[:7], "python3"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("must be absolute", r.stderr)
        self.assertFalse((self.package / "observed.json").exists())

    def test_missing_interpreter_rejected_before_step(self):
        r = self.run_launcher(args=[*self.args[:7], "/missing/python3"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("unavailable on compute node", r.stderr)

    def test_missing_argument_fails_closed(self):
        self.assertEqual(self.run_launcher(args=self.args[:7]).returncode, 2)

    def test_submit_command_carries_absolute_interpreter(self):
        r = dict(
            account="x",
            bundle="/b",
            prepared="/p",
            campaign="/c",
            workspace="/w",
            sources="/s",
            apptainer="/a",
            host_python="/usr/bin/python3.12",
        )
        self.assertEqual(control.command(Path("/pkg"), r, [])[-1], "/usr/bin/python3.12")

    def test_failed_archive_verified_without_runtime(self):
        from launch_repair import verify_failure

        r = verify_failure()
        self.assertEqual(r["archive_files"], 6)
        self.assertEqual(r["native_searches"], 0)
        self.assertTrue(r["allocation_spent"])

    def test_scientific_code_and_schedule_unchanged(self):
        original = E.ROOT / "agent/experiments/partial-calibration-v1"
        for n in (
            "CONTRACT.json",
            "SCHEDULE.json",
            "DESIGN.md",
            "pc_measure.py",
            "pc_interface.py",
            "pc_stats.py",
            "pc_results.py",
            "pc_proc.py",
            "pc_metadata.py",
            "pc_settings.py",
            "pc_trace.py",
            "pc_resources.py",
        ):
            self.assertEqual(C.sha(E.HERE / n), C.sha(original / n), n)


def real_frozen_backend():
    """Load the unmodified frozen class; redirect only its container-local runner path."""
    original_spec = importlib.util.spec_from_file_location
    runner = E.ROOT / "trials/torch-reviews-first/runner.py"
    assert C.sha(runner) == C.read(runner.parent / "manifest.json")["files"]["runner.py"]

    def local_spec(name, path, *args, **kwargs):
        return original_spec(
            name, runner if str(path) == "/opt/torch-reviews/runner.py" else path, *args, **kwargs
        )

    from execution import load_backend

    with patch("importlib.util.spec_from_file_location", side_effect=local_spec):
        return load_backend(E.SOURCE / "frozen")


def source_fixture(root):
    root.mkdir(mode=0o700)
    (root / "pgdata").mkdir(mode=0o700)
    (root / "pgdata/x").write_bytes(b"synthetic cluster bytes")
    for n in ("admin.pgpass", "reader.pgpass", "pg_hba.conf"):
        (root / n).write_text("private")
        (root / n).chmod(0o600)
    shutil.copyfile(E.SOURCE / "frozen/source-index.json", root / "database-identity.json")
    (root / "database-identity.json").chmod(0o600)
    return root


def restore_fixture(root, cell):
    root = root.resolve()
    src = source_fixture(root.with_name(root.name + "-source"))
    with patch.dict(os.environ, {"SLURM_JOB_ID": "42"}):
        restore.clone(src, root)
    return root


class RealCursor:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, *args, **kwargs):
        self.connection.execute(*args, **kwargs)
        return self

    def __iter__(self):
        return iter(self.connection.rows)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class RealConnection(FakeConnection):
    """Only PostgreSQL responses are synthetic; constructor/binding/snapshot/query code is real."""

    def cursor(self, *args, **kwargs):
        return RealCursor(self)

    def execute(self, statement, params=None, prepare=None):
        text = statement.as_string(self) if hasattr(statement, "as_string") else str(statement)
        if text.replace(", ", ",").startswith('SELECT "id","embedding","total_votes" FROM'):
            self.rows = [(n, json.dumps(VECTOR), 108) for n in range(40)]
            return self
        if "bind_target" in text:
            self.rows = [(270339 if self.mode == "partial640" else 264013,)]
            return self
        return super().execute(statement, params, prepare)


class FrozenBootstrapChecks(unittest.TestCase):
    def test_original_omission_reproduces_actual_constructor_failure(self):
        _, Base = real_frozen_backend()
        old = E.ROOT / "agent/experiments/partial-calibration-v1-launch-fix/pc_restore.py"
        spec = importlib.util.spec_from_file_location("old_restore_fixture", old)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {"SLURM_JOB_ID": "42"}):
            root = Path(d).resolve()
            src = source_fixture(root / "source")
            mod.clone(src, root / "work")
            with patch("psycopg.connect") as connect:
                with self.assertRaises(FileNotFoundError):
                    Base(E.ROOT / "trials/torch-reviews-first", root / "work")
                connect.assert_not_called()

    def test_both_bound_constructors_read_exact_copied_sidecar_without_connect(self):
        _, Base = real_frozen_backend()
        with tempfile.TemporaryDirectory() as d, patch("psycopg.connect") as connect:
            for c in C.CELLS:
                work = restore_fixture(Path(d).resolve() / c, c)
                Backend = I.bound_class(Base, c, C.CONTRACT["targets"][c])
                backend = Backend(E.ROOT / "trials/torch-reviews-first", work)
                self.assertEqual(
                    backend.state["source_manifest"]["index"], C.CONTRACT["targets"][c]["index"]
                )
                self.assertEqual(
                    backend.state["prepared"]["index_identity"],
                    C.CONTRACT["targets"][c]["index_identity"],
                )
                self.assertEqual(C.sha(work / "database-identity.json"), restore.IDENTITY_SHA)
                backend.close()
            connect.assert_not_called()

    def test_missing_sidecar_stops_before_copy(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            src = source_fixture(root / "source")
            (src / "database-identity.json").unlink()
            with self.assertRaises(FileNotFoundError):
                restore.clone(src, root / "work")
            self.assertFalse((root / "work").exists())

    def test_tampered_sidecar_stops_before_copy(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            src = source_fixture(root / "source")
            rewrite(src / "database-identity.json", dict(index_oid=270339))
            with self.assertRaises(ValueError):
                restore.clone(src, root / "work")
            self.assertFalse((root / "work").exists())

    def test_sidecar_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            src = source_fixture(root / "source")
            identity = src / "database-identity.json"
            identity.unlink()
            identity.symlink_to(E.SOURCE / "frozen/source-index.json")
            with self.assertRaises(ValueError):
                restore.clone(src, root / "work")

    def test_failed_metadata_archive_verifies_cleanup_and_source(self):
        from metadata_repair import verify_failure

        r = verify_failure()
        self.assertEqual(r["native_searches"], 0)
        self.assertTrue(r["cleanup_verified"])
        self.assertTrue(r["source_inventories_unchanged"])
        self.assertTrue(r["retained_identity_present_both_cells"])


class FrozenAcquisitionChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.clock = patch("time.perf_counter_ns", CLOCK.now)
        cls.clock.start()
        cls.driver = patch("psycopg.__version__", "3.3.6")
        cls.driver.start()
        cls.addClassCleanup(cls.driver.stop)
        cls.addClassCleanup(cls.clock.stop)
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.result = mock_acquisition(Path(cls.tmp.name), real_backend=True)

    @classmethod
    def tearDownClass(cls):
        cls.driver.stop()
        cls.clock.stop()
        cls.tmp.cleanup()

    def test_actual_frozen_methods_used(self):
        r = self.result["factory"].readers[0]
        names = [c.__module__ for c in type(r.backend).__mro__]
        self.assertIn("four_frozen_reviews", names)
        self.assertNotIn(FakeBase, type(r.backend).__mro__)

    def test_full_actual_backend_acquisition(self):
        self.assertEqual(self.result["result"]["completed_epochs"], 2)
        self.assertEqual(self.result["budget"].calls, 16242)
        self.assertEqual(dict(self.result["budget"].operations), C.OPERATIONS)

    def test_actual_backend_bindings_snapshot_and_cleanup(self):
        f = self.result["factory"]
        self.assertEqual(len(f.readers), 10)
        self.assertEqual(f.maximum_live, 6)
        self.assertTrue(all(r.closed for r in f.readers))
        self.assertEqual(len(f.snapshot.source_ids), 40)

    def test_actual_backend_search_and_sql_caps(self):
        self.assertEqual(self.result["trace"].search_sql, 16242)
        for k, v in C.SQL_CAPS.items():
            self.assertLessEqual(self.result["budget"].sql[k], v)

    def test_actual_backend_trusted_complete_reconstruction(self):
        root = Path(self.tmp.name) / "trusted"
        root.mkdir()
        package = E.build(root / "seal", testing=True)
        campaign = complete_raw_fixture(root, self.result, package)
        result = report.analyze(campaign, package, root / "analysis")
        self.assertEqual(result["outcome"], "calibration_qualified_scoped")
        self.assertEqual(result["timing"]["passed_intervals"], 56)
        self.assertFalse(result["treatment_speed_qualified"])

    def test_actual_backend_plan_inventory(self):
        self.assertEqual(self.result["observer"].plan_packets, 4200)

    def test_actual_backend_schedule_parity(self):
        rows = C.lines(self.result["out"] / "searches.jsonl")
        expected = list(M.events(self.result["schedule"]))
        self.assertEqual(
            [(r["operation"], r["query_id"], r["reader"]) for r in rows],
            [(a, b, c) for a, b, c, m in expected],
        )
        for r, (_, _, _, meta) in zip(rows, expected):
            self.assertTrue(all(r.get(k) == v for k, v in meta.items()))


class SnapshotStartupChecks(unittest.TestCase):
    def setUp(self):
        import pc_snapshot

        self.guard = pc_snapshot
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.package = Path(self.tmp.name)
        self.snap = snapshot()
        self.eligibility = dict(
            source_ids=self.snap.source_ids,
            votes=[row["metadata"]["total_votes"] for row in self.snap.rows],
        )
        (self.package / "eligibility.json").write_bytes(C.encoded(self.eligibility))
        rewrite(self.package / "experiment.json", dict(snapshot_identity=self.snap.identity))

    def test_old_three_key_hash_is_guaranteed_wrong(self):
        old = dict(field_map=self.snap.field_map, **self.eligibility)
        self.assertNotEqual(C.digest(old), C.sha(self.package / "eligibility.json"))
        self.assertEqual(C.digest(self.eligibility), C.sha(self.package / "eligibility.json"))

    def test_actual_frozen_snapshot_passes_startup_validation(self):
        proof = self.guard.validate_snapshot(self.snap, self.package)
        self.assertEqual(proof["snapshot_identity"], self.snap.identity)
        self.assertEqual(proof["rows"], 40)

    def test_pinned_full_eligibility_schema_and_values(self):
        pinned = C.read(E.SOURCE / "eligibility.json")

        # IDs/votes only, no dataset vectors or database opened.
        class Rows:
            def __len__(self):
                return len(pinned["votes"])

            def __iter__(self):
                return (dict(metadata=dict(total_votes=v)) for v in pinned["votes"])

        cfg = C.read(E.SOURCE / "experiment.json")
        view = SimpleNamespace(
            source_ids=pinned["source_ids"],
            rows=Rows(),
            field_map={"m_000000": "total_votes"},
            identity=cfg["snapshot_identity"],
        )
        proof = self.guard.validate_snapshot(view, E.SOURCE)
        self.assertEqual(proof["rows"], 247286)
        self.assertEqual(proof["eligibility_sha256"], C.sha(E.SOURCE / "eligibility.json"))

    def test_changed_ids_rejected(self):
        self.snap.source_ids[0] = -1
        with self.assertRaisesRegex(RuntimeError, "eligibility changed"):
            self.guard.validate_snapshot(self.snap, self.package)

    def test_changed_votes_rejected(self):
        self.snap.rows[0]["metadata"]["total_votes"] += 1
        with self.assertRaisesRegex(RuntimeError, "eligibility changed"):
            self.guard.validate_snapshot(self.snap, self.package)

    def test_changed_data_identity_rejected(self):
        self.snap.identity = "different"
        with self.assertRaisesRegex(RuntimeError, "data identity changed"):
            self.guard.validate_snapshot(self.snap, self.package)

    def test_changed_field_map_rejected(self):
        self.snap.field_map["m_000000"] = "different"
        with self.assertRaisesRegex(RuntimeError, "field mapping changed"):
            self.guard.validate_snapshot(self.snap, self.package)

    def test_extra_field_map_rejected(self):
        self.snap.field_map["m_000001"] = "extra"
        with self.assertRaisesRegex(RuntimeError, "field mapping changed"):
            self.guard.validate_snapshot(self.snap, self.package)

    def test_extra_eligibility_key_rejected(self):
        (self.package / "eligibility.json").write_bytes(
            C.encoded(dict(field_map=self.snap.field_map, **self.eligibility))
        )
        with self.assertRaisesRegex(RuntimeError, "eligibility schema differs"):
            self.guard.validate_snapshot(self.snap, self.package)

    def test_current_archive_independently_verified(self):
        from identity_repair import verify_failure

        r = verify_failure()
        self.assertEqual(r["archive_files"], 30)
        self.assertTrue(r["cleanup_verified"])
        self.assertEqual(r["native_searches"], 0)
        self.assertEqual(r["reader_admissions"], 2)

    def test_production_package_build_held(self):
        with self.assertRaisesRegex(ValueError, "Release held"):
            E.build(self.package / "held")
        self.assertFalse((self.package / "held" / C.NAME).exists())


def mock_runtime_entry(root, fault=None):
    """Run pc_runtime.main itself; only its OS/database/resource boundaries are synthetic."""
    import pc_runtime as runtime
    from fannagent_pgvector.profiles import PROFILE

    root = root.resolve()
    FakeBase.behavior = "good"
    package = E.build(root / "seal", testing=True)
    bundle = E.ROOT / "trials/torch-reviews-first"
    work, out, source = root / "work", root / "results", root / "retained"
    for folder in (work, out, source):
        folder.mkdir()
    for cell in C.CELLS:
        source_fixture(source / cell)
    mountinfo = root / "mountinfo"
    mountinfo.write_text("1 0 0:1 / /retained ro - test test ro\n")
    items = copy.deepcopy(C.lines(package / "queries.jsonl"))
    for row in items:
        row["query"]["vector"] = VECTOR
    (package / "queries.jsonl").write_text("".join(json.dumps(i) + "\n" for i in items))
    snap = snapshot()
    (package / "eligibility.json").write_bytes(
        C.encoded(dict(source_ids=snap.source_ids, votes=[108] * 40))
    )
    cfg = C.read(package / "experiment.json")
    cfg.update(snapshot_identity=snap.identity, queries_sha256=C.sha(package / "queries.jsonl"))
    if fault == "snapshot_identity":
        cfg["snapshot_identity"] = "changed"
    if fault == "eligibility":
        (package / "eligibility.json").write_bytes(
            C.encoded(dict(source_ids=snap.source_ids, votes=[109] + [108] * 39))
        )
    rewrite(package / "experiment.json", cfg)
    truth = dict(truth_strict=list(range(9)), truth_ties=[9], truth_k=10)
    value = dict(
        ids=list(range(10)),
        distances=[i / 20 for i in range(10)],
        recall=1.0,
        valid=True,
        returned_count=10,
        duplicate_count=0,
        predicate_violation_count=0,
    )
    rewrite(package / "baseline-results.json", {i["query"]["id"]: truth for i in items})
    (package / "b2d-references.jsonl").write_text(
        "".join(
            json.dumps(dict(query_id=i["query"]["id"], outcomes={c: value for c in C.CELLS})) + "\n"
            for i in items
        )
    )
    reseal(package)
    frozen, Base = real_frozen_backend()
    catalogs = C.read(package / "b2d-catalogs.json")
    opened, stopped, procs = [], [], []

    class RuntimeConnection(RealConnection):
        def __init__(self, cell, admin):
            super().__init__(cell)
            self.admin = admin
            if admin:
                self.info.user = "torch_owner"
            self.pid = 30 + C.CELLS.index(cell)
            opened.append(self)

        def execute(self, statement, params=None, prepare=None):
            text = statement.as_string(self) if hasattr(statement, "as_string") else str(statement)
            if "current_setting('data_directory')" in text:
                self.rows = [(self.pid, str(work / self.mode / "pgdata"))]
            elif text == "SELECT pg_backend_pid()":
                self.rows = [(self.pid,)]
            elif text.startswith("SELECT current_setting('plan_cache_mode')"):
                self.rows = [("auto", "on")]
            elif "FROM pg_stat_database" in text:
                self.rows = [(dict(blks_read=0, blks_hit=0, temp_files=0, temp_bytes=0),)]
            elif text == settings.MEMORY_SQL:
                self.rows = [(128 * 1024**2, 16, 4 * 1024**2, "64MB", "0")]
            elif self.admin and "jsonb_build_object" in text:
                cat = copy.deepcopy(catalogs[self.mode])
                if fault == "catalog":
                    cat["unexpected"] = True
                self.rows = [(cat,)]
            else:
                return super().execute(statement, params, prepare)
            return self

    class RuntimeProc(FakeProc):
        def __init__(self, budget, emit):
            super().__init__(emit.__self__)
            self.client, self.layout = 999, dict(selected=[0, 1, 2, 3])
            self.frozen_threads = False
            procs.append(self)

        def pin(self, *args):
            pass

        def server(self, *args):
            pass

        def freeze_client_threads(self):
            self.frozen_threads = True

        def context(self, *args):
            pass

        def charges(self):
            return dict(synthetic=True)

        def bind(self, reader, path, epoch=0):
            super().bind(reader, path, epoch)
            reader.connection.raw.pid = reader.physical["pid"]

    mapping = {
        "/patch": package,
        "/run": work,
        "/results": out,
        "/retained": source,
        "/bundle": bundle,
        "/proc/self/mountinfo": mountinfo,
    }

    def logical_path(value):
        return mapping.get(str(value), Path(value))

    def checksum(value):
        if str(value) == "/opt/postgresql/lib/vector.so":
            return C.CONTRACT["runtime"]["module_sha256"]
        return C.sha(value)

    def graph(work_cell, relative):
        return (
            C.CONTRACT["graphs"]["native640"]
            if relative.endswith("264013")
            else C.CONTRACT["graphs"]["partial640"]["partial"]
            if Path(work_cell).name == "partial640"
            else {}
        )

    def start(path):
        if fault == "second_server" and path.name == "partial640":
            raise RuntimeError("Injected second server start failure")
        (path / "pgdata/postmaster.pid").write_text("synthetic\n")

    def stop(path):
        stopped.append(path.name)
        pid = path / "pgdata/postmaster.pid"
        if pid.exists():
            pid.unlink()
        (path / "server.log").write_text("database system is shut down\n")
        if fault == "cleanup" and path.name == "partial640":
            raise RuntimeError("Injected cleanup failure")

    def connect(dsn, **kwargs):
        return RuntimeConnection(
            "partial640" if "partial640" in dsn else "native640", "torch_owner" in dsn
        )

    failure = None
    with ExitStack() as stack:
        for target, kwargs in [
            ("pc_runtime.Path", dict(side_effect=logical_path)),
            ("pc_runtime.sha", dict(side_effect=checksum)),
            (
                "pc_runtime.os.uname",
                dict(return_value=SimpleNamespace(sysname="Linux", machine="x86_64")),
            ),
            ("pc_runtime.signal.signal", dict()),
            ("pc_runtime.signal.setitimer", dict()),
            (
                "pc_runtime.control_state",
                dict(return_value=dict(fields={"Database cluster state": "shut down"})),
            ),
            ("pc_runtime.verify_graphs", dict()),
            ("pc_runtime.graph_files", dict(side_effect=graph)),
            (
                "pc_runtime.verify_data",
                dict(return_value=dict(rows=247286, data_bits_verified=True)),
            ),
            ("execution.load_backend", dict(return_value=(frozen, Base))),
            ("database.start", dict(side_effect=start)),
            ("database.stop", dict(side_effect=stop)),
            ("pc_proc.Proc", dict(side_effect=RuntimeProc)),
            ("psycopg.connect", dict(side_effect=connect)),
            ("psycopg.__version__", dict(new="3.3.6")),
            ("time.perf_counter_ns", dict(side_effect=CLOCK.now)),
            ("sys.argv", dict(new=["pc_runtime.py", "--block", "0"])),
            (
                "subprocess.run",
                dict(
                    side_effect=AssertionError("No real subprocess allowed in entry-point fixture")
                ),
            ),
        ]:
            stack.enter_context(patch(target, **kwargs))
        stack.enter_context(
            patch.dict(
                os.environ,
                SLURM_JOB_ID="test",
                SLURM_CPUS_PER_TASK="4",
                TORCH_IMAGE_SHA256=C.CONTRACT["runtime"]["image_sha256"],
            )
        )
        # Assert local profile is the exact pinned runtime, not a mocked profile.
        assert PROFILE.fingerprint == C.CONTRACT["runtime"]["runtime_profile_hash"]
        stack.enter_context(patch("sys.stdout", new=io.StringIO()))
        try:
            runtime.main()
        except RuntimeError as error:
            failure = error
    return dict(
        out=out,
        failure=failure,
        opened=opened,
        stopped=stopped,
        status=C.read(out / "status.json"),
        procs=procs,
    )


class RuntimeEntryChecks(unittest.TestCase):
    def run_fixture(self, fault=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return mock_runtime_entry(Path(tmp.name), fault)

    def test_entry_point_completes_exact_protocol_and_cleanup(self):
        r = self.run_fixture()
        self.assertIsNone(
            r["failure"],
            (r["out"] / "failure.json").read_text() if (r["out"] / "failure.json").exists() else "",
        )
        self.assertEqual(r["status"]["backend_searches"], 16242)
        self.assertEqual(r["status"]["plan_packets"], 4200)
        self.assertEqual(r["status"]["reader_connections"], 10)
        self.assertTrue(r["status"]["final_integrity_verified"])
        self.assertEqual(r["status"]["result"]["completed_epochs"], 2)
        self.assertTrue(r["procs"][0].frozen_threads)
        self.assertTrue(all(c.closed for c in r["opened"]))
        self.assertEqual(set(r["stopped"]), set(C.CELLS))
        self.assertTrue(C.read(r["out"] / "LOCK.json")["complete"])
        self.assertTrue((r["out"] / "stopped-copies.json").exists())

    def check_failure(self, fault, message):
        r = self.run_fixture(fault)
        self.assertIsNotNone(r["failure"])
        self.assertEqual(r["status"]["status"], "failed")
        self.assertIn(message, C.read(r["out"] / "failure.json")["message"])
        self.assertFalse(C.read(r["out"] / "LOCK.json")["complete"])
        self.assertEqual(
            C.read(r["out"] / "source-before.json"), C.read(r["out"] / "source-after.json")
        )
        self.assertTrue(all(c.closed for c in r["opened"]))
        self.assertEqual(set(r["stopped"]), set(C.CELLS))
        return r

    def test_entry_point_eligibility_failure_preserves_sources_and_closes_readers(self):
        r = self.check_failure("eligibility", "Snapshot eligibility changed")
        self.assertEqual(r["status"]["backend_searches"], 0)
        self.assertEqual(r["status"]["reader_connections"], 2)

    def test_entry_point_snapshot_identity_failure_closes_readers(self):
        r = self.check_failure("snapshot_identity", "Snapshot data identity changed")
        self.assertEqual(r["status"]["backend_searches"], 0)

    def test_entry_point_catalog_failure_closes_started_servers(self):
        r = self.check_failure("catalog", "Complete catalog/statistics differ")
        self.assertEqual(r["status"]["backend_searches"], 0)

    def test_entry_point_second_server_start_failure_preserves_source(self):
        self.check_failure("second_server", "Injected second server start failure")

    def test_entry_point_cleanup_error_cannot_qualify(self):
        r = self.check_failure("cleanup", "Cleanup/source preservation failed")
        self.assertIn("Injected cleanup failure", C.read(r["out"] / "cleanup.json")["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
