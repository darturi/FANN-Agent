"""Offline synthetic correctness checks only; no native database or Torch execution."""

import copy
import io
import json
import os
import shutil
import tarfile
import tempfile
import unittest
from collections import Counter, defaultdict
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
from test_support import CLOCK, VECTOR, FakeBase, snapshot


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


def mock_acquisition(root, quality_negative=False):
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
    rewrite(p / "eligibility.json", dict(votes=[108] * 40))
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
    factory = I.Factory(
        FakeBase,
        Path("/bundle"),
        {c: Path("/run") / c for c in C.CELLS},
        targets,
        observer,
        budget,
        journal.emit,
    )
    main = {c: factory.create(c, c.split("640")[0] + "-reference") for c in C.CELLS}
    admitted = __import__("pc_results").admit(snapshot(), items)
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
            )
            for c in C.CELLS
        },
    )
    for n in ("protected-source-before.json", "protected-source-after.json"):
        rewrite(run / n, dict(mock_only=True))
    rewrite(campaign / "protected-source-before.json", dict(mock_only=True))
    rewrite(run / "runtime-identity.json", C.CONTRACT["runtime"])
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
