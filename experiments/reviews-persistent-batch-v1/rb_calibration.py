"""Prospective A/A calibration for the frozen ten-query Reviews sessions."""

import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from rb_measure import (
    MAX_RAW_FILE_BYTES,
    READER_SQL_LIMIT,
    check_timed,
    collect_session,
    guarded_backend,
    write_json,
)
from rb_measure import (
    Meter as StudyMeter,
)
from rb_plan import FAMILIES, file_sha, require
from rb_stats import timing
from rb_verify import check_identity, check_requests, locked_raw

STEPS = ("connect", "bind_and_apply_settings", "verify_settings")
VERDICTS = ("timing_controls_pass", "measurement_inconclusive")


class Meter(StudyMeter):
    def select(self, section):
        require(section == "timing", "Calibration permits only timed searches")
        super().select(section)

    def begin_reader(self, section):
        require(section != "proof", "Calibration permits no proof readers")
        super().begin_reader(section)


def make_backend(runner, base, meter, bundle, work):
    class CalibrationReader(guarded_backend(base, meter)):
        marks = None

        def _observe(self, step, operation, *args, **kwargs):
            if self.marks is None:
                return operation(*args, **kwargs)
            require(step not in self.marks, "Repeated reader setup step")
            start = meter.clock()
            result = operation(*args, **kwargs)
            self.marks[step] = [start, meter.clock()]
            return result

        def _bind(self, conn, source):
            return self._observe("bind_and_apply_settings", super()._bind, conn, source)

        def _verify_reader(self, expected):
            return self._observe("verify_settings", super()._verify_reader, expected)

        @contextmanager
        def trace_reader_setup(self):
            require(self.marks is None, "Reader setup recording is already active")
            driver = runner.psycopg

            def connect(*args, **kwargs):
                return self._observe("connect", driver.connect, *args, **kwargs)

            # This is the private, loaded runner's global, not the shared psycopg module.
            runner.psycopg = SimpleNamespace(connect=connect)
            self.marks = {}
            try:
                yield self.marks
            finally:
                self.marks = None
                runner.psycopg = driver

    return CalibrationReader(bundle, work)


def setup_durations(row):
    marks = row["reader_setup_ns"]
    require(set(marks) == set(STEPS), "Missing reader setup intervals")
    started, opened = row["boundary_ns"][:2]
    previous = started
    durations = {}
    for step in STEPS:
        begin, end = marks[step]
        require(
            type(begin) is int and type(end) is int and previous <= begin <= end <= opened,
            "Reader setup intervals escaped the session boundary",
        )
        durations[step] = (end - begin) / 1e6
        previous = end
    measured = sum(marks[step][1] - marks[step][0] for step in STEPS)
    durations["other_reader_setup"] = (opened - started - measured) / 1e6
    return durations


def capture(
    plan,
    frozen,
    evidence,
    backend,
    meter,
    output,
    *,
    synthetic_only,
    after_snapshot,
    schedule=None,
    batch_size=None,
    collector=collect_session,
):
    require(isinstance(meter, Meter), "Calibration requires its restricted meter")
    require(
        getattr(backend, "synthetic_only", False) is synthetic_only,
        "Calibration backend does not match the execution mode",
    )
    output = Path(output)
    output.mkdir(exist_ok=False)
    disposition = "invalid_incomplete"
    try:
        with (output / "timings.jsonl").open("x") as stream:
            with backend.reader("reference"):
                backend.snapshot()
                after_snapshot()
            meter.next_phase("quality")
            meter.next_phase("timing")
            meter.select("timing")
            for epoch, session, arm in plan.timed() if schedule is None else schedule:
                with backend.trace_reader_setup() as marks:
                    row = collector(
                        plan,
                        frozen,
                        evidence,
                        backend,
                        meter,
                        session,
                        arm,
                        epoch,
                        batch_size=batch_size,
                    )
                row["reader_setup_ns"] = marks
                setup_durations(row)
                for record in row["requests"]:
                    check_timed(evidence, evidence.outcomes, arm.split("-")[0], record)
                line = json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n"
                require(stream.tell() + len(line.encode()) <= MAX_RAW_FILE_BYTES, "Raw cap")
                stream.write(line)
                stream.flush()
            meter.check_time()
            disposition = "complete"
    except BaseException as error:
        write_json(output / "failure.json", {"type": type(error).__name__, "message": str(error)})
        raise
    finally:
        meter.next_phase("final")
        write_json(
            output / "status.json",
            {
                "synthetic_only": synthetic_only,
                "disposition": disposition,
                "candidate": evidence.identities,
                "accounting": meter.receipt(),
            },
        )
        hashes = {path.name: file_sha(path) for path in sorted(output.iterdir())}
        write_json(output / "LOCK.json", {"files_sha256": hashes})


def completed_timing(directory, evidence, synthetic_only):
    raw = locked_raw(directory, streams=("timings",), optional=("failure.json",))
    status = raw["status.json"]
    require(
        status["synthetic_only"] is synthetic_only
        and status["candidate"] == evidence.identities
        and status["disposition"] == "complete"
        and "failure.json" not in raw,
        "Calibration did not complete under the expected identity",
    )
    return raw["timings.jsonl"], status["accounting"]


def check_accounting(accounting, meter_type, installations):
    readers = {section: meter_type.reader_limits[section] for section in ("reference", "timing")}
    require(
        installations == meter_type.install_limits.get("timing", 0)
        and accounting
        == {
            "searches": {"timing": meter_type.search_limits["timing"]},
            "installations": {"timing": installations} if installations else {},
            "reader_opens": readers,
            "reader_closes": readers,
            "reader_startup_sql_reserved": READER_SQL_LIMIT * sum(readers.values()),
        },
        "Calibration accounting changed",
    )


def reconstruct(directory, plan, _frozen, evidence, *, synthetic_only):
    rows, accounting = completed_timing(directory, evidence, synthetic_only)
    report = timing(plan, rows, aa_only=True)
    seen = set()
    installations = 0
    durations = {family: [] for family in FAMILIES}
    for row, (_, session, arm) in zip(rows, plan.timed(), strict=True):
        family = arm.split("-")[0]
        check_identity(row, seen)
        installations += check_requests(session, family, evidence, row)
        for record in row["requests"]:
            check_timed(evidence, evidence.outcomes, family, record)
        durations[family].append(setup_durations(row))
    check_accounting(accounting, Meter, installations)
    setup = {
        family: {
            step: np.quantile([row[step] for row in samples], [0.50, 0.95, 1.0]).tolist()
            for step in (*STEPS, "other_reader_setup")
        }
        for family, samples in durations.items()
    }
    return {
        "calibration_only": True,
        "synthetic_only": synthetic_only,
        "development_qualifier": False,
        "provisional_verdict": VERDICTS[0] if report["aa_pass"] else VERDICTS[1],
        "accounting": accounting,
        **report,
        "reader_setup_ms_quantiles_50_95_100": setup,
    }
