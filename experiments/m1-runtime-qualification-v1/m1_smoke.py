"""Exercise production M1 loops on a reproducible synthetic graph. Never study evidence."""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

from common import publish, require, sha, write
from m1_design import FILTERS, ledger
from m1_experiment import load_programs, offline, quality, timing, work
from psycopg import connect
from startup import start

HERE = Path("/qual")


class Backend:
    def __init__(self, bundle, work):
        self.state = {"source_manifest": {"settings": {}}}
        self.conn = None

    def _connect(self):
        self.conn = connect("host=/tmp/socket dbname=postgres user=nobody", autocommit=True)
        self.conn.execute("SELECT fannagent.bind_target('reviews','id','embedding','reviews_hnsw')")
        return self.conn

    def close(self):
        if self.conn:
            self.conn.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=("timing", "work"), required=True)
    p.add_argument("--population", choices=(0, 7), type=int, default=7)
    p.add_argument("--quality-only", action="store_true")
    a = p.parse_args()
    os.sched_setaffinity(0, set(sorted(os.sched_getaffinity(0))[:4]))
    shared = HERE / "checks/smoke-shared"
    backup = shared / ("backup" + str(a.population))
    Path("/tmp/socket").mkdir(mode=0o700)
    Path("/tmp/pg_hba.conf").write_text("local all all trust\n")
    require(
        sha("/opt/postgresql/lib/vector.so") == sha(HERE / (a.phase + "-module.so")),
        "wrong smoke module",
    )
    if a.phase == "timing":
        require(not backup.exists(), "preserve existing synthetic graph backup")
        subprocess.run(
            ["/opt/postgresql/bin/initdb", "-D", "/tmp/pgdata", "-A", "trust", "-U", "nobody"],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        start(Path("/tmp"))
        fixture = (
            (HERE / "fixture.sql")
            .read_text()
            .replace("i<=10000 THEN 1000", f"i<={a.population} THEN 1000")
            .replace("reviews_fixture_graph", "reviews_hnsw")
        )
        with connect("host=/tmp/socket dbname=postgres user=nobody", autocommit=True) as c:
            c.execute(fixture + (HERE / "functions.sql").read_text())
        subprocess.run(
            ["/opt/postgresql/bin/pg_ctl", "-D", "/tmp/pgdata", "-m", "fast", "-w", "stop"],
            check=True,
        )
        shutil.copytree("/tmp/pgdata", backup)
    else:
        shutil.copytree(backup, "/tmp/pgdata")
    start(Path("/tmp"))
    output = shared / (a.phase + str(a.population))
    output.mkdir(mode=0o700)
    args = SimpleNamespace(
        bundle=Path("/tmp"),
        work=Path("/tmp"),
        output=output,
        ef=8192,
        fixture=True,
        phase=a.phase,
        previous_attempts=0,
    )
    queries = []
    for t in FILTERS:
        for i in range(4):
            q = {
                "id": f"synthetic-v{i}-" + ("unfiltered" if t < 0 else "votes" + str(t)),
                "k": 10,
                "vector": [0.3 + i * 0.03, 0.1, 0.8, 0.4, 0.9, 0.2, 0.6, 0.5],
            }
            if t >= 0:
                q["filter"] = {"field": "totalvotes", "op": "gte", "value": t}
            queries.append(q)
    try:
        with connect("host=/tmp/socket dbname=postgres user=nobody", autocommit=True) as keeper:
            if a.phase == "work":
                # The copied graph already has base/v2 functions; add observer-only exports.
                sql = (
                    (HERE / "work-functions.sql")
                    .read_text()
                    .split("CREATE FUNCTION fannagent.diagnostic_reset", 1)[1]
                )
                keeper.execute("CREATE FUNCTION fannagent.diagnostic_reset" + sql)
            keeper.execute("BEGIN ISOLATION LEVEL REPEATABLE READ")
            keeper.execute("LOCK TABLE reviews IN SHARE MODE")
            args.snapshot = keeper.execute("SELECT pg_export_snapshot()").fetchone()[0]
            heap, index = keeper.execute(
                "SELECT 'reviews'::regclass::oid,'reviews_hnsw'::regclass::oid"
            ).fetchone()
            rows = keeper.execute("SELECT ctid::text,total_votes FROM reviews").fetchall()
            sources = keeper.execute("SELECT id,total_votes FROM reviews").fetchall()
            eligible = {
                t: {i for i, v in sources if t < 0 or v is not None and v >= t} for t in FILTERS
            }
            for t in FILTERS:
                publish(Path(f"/tmp/membership-{t}.bin"), heap, index, rows, t)
            write(output / "eligibility.json", {str(t): sorted(ids) for t, ids in eligible.items()})
            counter = {"total": 0}
            truths = offline(Backend, args, queries, eligible, None, counter)
            if a.phase == "timing":
                cache, summary = quality(
                    Backend, args, queries, eligible, truths, None, counter, load_programs(HERE)
                )
                reached = summary["prefixes"]["reached"]
                if not a.quality_only:
                    timing(Backend, args, queries, eligible, cache, counter)
                expected = ledger(len(queries), reached, 4)["timing"]
                if a.quality_only:
                    expected = {
                        k: v
                        for k, v in expected.items()
                        if k not in ("timed_ann", "warmup_ann", "total")
                    }
                    expected["total"] = sum(expected.values())
                require(counter == expected, "smoke timing ledger differs")
                write(shared / ("quality-summary" + str(a.population) + ".json"), summary)
                if a.population == 0:
                    rows_ = [
                        json.loads(line)
                        for line in (output / "quality.jsonl").read_text().splitlines()
                    ]
                    require(
                        any(
                            v["checkpoint"] and v["returned_count"] == 0
                            for r in rows_
                            for v in r["results"].values()
                        ),
                        "zero-result stop not exercised",
                    )
            else:
                rows_ = [
                    json.loads(line)
                    for line in (shared / ("timing" + str(a.population)) / "quality.jsonl")
                    .read_text()
                    .splitlines()
                ]
                cache = {(r["id"], n): v for r in rows_ for n, v in r["results"].items()}
                summary = work(Backend, args, queries, eligible, truths, cache, counter)
                require(counter == ledger(len(queries), 0, 4)["work"], "smoke work ledger differs")
            print(
                "SMOKE_RECEIPT "
                + json.dumps(
                    {
                        "status": "passed",
                        "phase": a.phase,
                        "population": a.population,
                        "conditions": list(FILTERS),
                        "queries": len(queries),
                        "programs": 21,
                        "searches": counter,
                        "fixture": "synthetic8d same graph under both modules; not original graph "
                        "or performance qualification",
                        "zero_output_stops_verified": a.population == 0,
                        "production_loops_exercised": True,
                        "exact_serving_calls": 0,
                        "provider_calls": 0,
                        "validation_test_outcomes_opened": False,
                    }
                ),
                flush=True,
            )
    finally:
        subprocess.run(
            ["/opt/postgresql/bin/pg_ctl", "-D", "/tmp/pgdata", "-m", "fast", "-w", "stop"],
            check=True,
        )


if __name__ == "__main__":
    main()
