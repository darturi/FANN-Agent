"""Replay eight compiled families on the same synthetic graph, then audit timing."""

import json
import os
import subprocess
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import oracle_experiment
import variants_benchmark
from common import sha, write
from oracle_design import FILTERS
from psycopg import connect
from smoke_capture import Backend
from startup import start
from variants_analyse import report


def main():
    os.sched_setaffinity(0, set(sorted(os.sched_getaffinity(0))[:4]))
    here = Path("/qual")
    output = here / "checks/benchmark-smoke"
    output.mkdir(mode=0o700)
    queries = [json.loads(line) for line in (here / "queries.jsonl").open()]
    roles = json.loads((here / "query-roles.json").read_text())
    args = SimpleNamespace(
        bundle=Path("/tmp"), work=Path("/tmp"), output=output, ef=640, fixture=True, roles=roles
    )
    start(Path("/tmp"))
    try:
        with connect("host=/tmp/socket dbname=postgres user=nobody", autocommit=True) as keeper:
            keeper.execute("BEGIN ISOLATION LEVEL REPEATABLE READ")
            keeper.execute("LOCK TABLE reviews IN SHARE MODE")
            args.snapshot = keeper.execute("SELECT pg_export_snapshot()").fetchone()[0]
            source = keeper.execute("SELECT id,total_votes FROM reviews").fetchall()
            eligible = {t: {i for i, v in source if t < 0 or v >= t} for t in FILTERS}
            write(output / "eligibility.json", {str(t): sorted(ids) for t, ids in eligible.items()})
            counter = Counter(total=0)
            oracle_experiment.reserve = variants_benchmark.reserve
            truths = variants_benchmark.offline(Backend, args, queries, eligible, counter)
            choices = variants_benchmark.acquire(Backend, args, queries, eligible, truths, counter)
            variants_benchmark.timing(Backend, args, queries, eligible, choices, counter)
            write(
                output / "receipt.json",
                {
                    "status": "synthetic_only",
                    "searches": dict(counter),
                    "raw_sha256": {p.name: sha(p) for p in output.iterdir() if p.is_file()},
                },
            )
            result = report(output, here, fixture=True)
            assert result["cohorts"]["full_workload"]["cases"] == 14
            print("VARIANT_BENCHMARK_SMOKE_PASSED " + json.dumps(dict(counter)), flush=True)
    finally:
        subprocess.run(
            ["/opt/postgresql/bin/pg_ctl", "-D", "/tmp/pgdata", "-m", "fast", "-w", "stop"],
            check=True,
        )


if __name__ == "__main__":
    main()
