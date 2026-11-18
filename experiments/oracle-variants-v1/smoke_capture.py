"""Actual synthetic PostgreSQL end-to-end oracle; never benchmark performance evidence."""

import json
import os
import subprocess
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import oracle_experiment
import variants_capture
from common import publish, sha, write
from oracle_design import FILTERS
from oracle_experiment import acquire, offline
from psycopg import connect
from startup import start


class Backend:
    def __init__(self, bundle, work):
        self.state = {"source_manifest": {"settings": {}}}
        self.conn = None

    def _connect(self):
        self.conn = connect("host=/tmp/socket dbname=postgres user=nobody", autocommit=True)
        self.conn.execute("SELECT fannagent.bind_target('reviews','id','embedding','reviews_hnsw')")
        self.conn.execute("SET enable_seqscan=off")
        self.conn.execute("SET enable_bitmapscan=off")
        return self.conn

    def close(self):
        if self.conn:
            self.conn.close()


def main():
    os.sched_setaffinity(0, set(sorted(os.sched_getaffinity(0))[:4]))
    Path("/tmp/socket").mkdir(mode=0o700)
    Path("/tmp/pg_hba.conf").write_text("local all all trust\n")
    subprocess.run(
        ["/opt/postgresql/bin/initdb", "-D", "/tmp/pgdata", "-A", "trust", "-U", "nobody"],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    start(Path("/tmp"))
    here = Path("/qual")
    output = here / "checks/capture-smoke/source"
    output.mkdir(mode=0o700, parents=True)
    queries = []
    roles = {}
    for i in range(2):
        for t in FILTERS:
            suffix = "unfiltered" if t < 0 else "votes" + str(t)
            q = {
                "id": f"synthetic-v{i}-{suffix}",
                "k": 10,
                "vector": [0.3 + i * 0.03, 0.1, 0.8, 0.4, 0.9, 0.2, 0.6, 0.5],
            }
            if t >= 0:
                q["filter"] = {"field": "totalvotes", "op": "gte", "value": t}
            queries.append(q)
            roles[q["id"]] = "test" if i else "development"
    write(output / "query-roles.json", roles)
    (output / "queries.jsonl").write_text("".join(json.dumps(q) + "\n" for q in queries))
    args = SimpleNamespace(
        bundle=Path("/tmp"), work=Path("/tmp"), output=output, ef=640, fixture=True, roles=roles
    )
    try:
        with connect("host=/tmp/socket dbname=postgres user=nobody", autocommit=True) as keeper:
            fixture = (
                (here / "fixture.sql").read_text().replace("reviews_fixture_graph", "reviews_hnsw")
            )
            # Some filters have zero eligible rows; others have short populations.
            fixture = fixture.replace("i<=10000 THEN 1000", "i<=0 THEN 1000")
            fixture = fixture.replace("i<=20000 THEN 600", "i<=7 THEN 600")
            fixture = fixture.replace("i<=30000 THEN 400", "i<=300 THEN 400")
            fixture = fixture.replace("WHERE id<=16000", "WHERE id<=32000")
            fixture = fixture.replace("WITH(m=32)", "WITH(m=64, ef_construction=128)")
            keeper.execute(fixture + (here / "functions.sql").read_text())
            keeper.execute("BEGIN ISOLATION LEVEL REPEATABLE READ")
            keeper.execute("LOCK TABLE reviews IN SHARE MODE")
            args.snapshot = keeper.execute("SELECT pg_export_snapshot()").fetchone()[0]
            heap, index = keeper.execute(
                "SELECT 'reviews'::regclass::oid,'reviews_hnsw'::regclass::oid"
            ).fetchone()
            rows = keeper.execute("SELECT ctid::text,total_votes FROM reviews").fetchall()
            source = keeper.execute("SELECT id,total_votes FROM reviews").fetchall()
            eligible = {t: {i for i, v in source if t < 0 or v >= t} for t in FILTERS}
            for t in FILTERS:
                publish(Path(f"/tmp/membership-{t}.bin"), heap, index, rows, t)
            write(output / "eligibility.json", {str(t): sorted(ids) for t, ids in eligible.items()})
            counter = Counter(total=0)
            truths = offline(Backend, args, queries, eligible, counter)
            choices = acquire(Backend, args, queries, eligible, truths, counter)
            for name, source_name in (
                ("source-quality.jsonl", "quality.jsonl"),
                ("source-trajectories.jsonl", "trajectories.jsonl"),
                ("source-exact-reference.jsonl", "exact-reference.jsonl"),
                ("source-eligibility.json", "eligibility.json"),
            ):
                (output / name).write_bytes((output / source_name).read_bytes())
            (output / "ideal-recall-choices.jsonl").write_text(
                "".join(
                    json.dumps(
                        {
                            "id": qid,
                            "checkpoint": r["checkpoint"],
                            "output": r["output"],
                            "recall": r["recall"],
                        }
                    )
                    + "\n"
                    for qid, r in choices.items()
                )
            )
            variants_capture.HERE = output
            new_output = output.parent / "results"
            new_output.mkdir(mode=0o700)
            args.output = new_output
            fresh = Counter(total=0)
            oracle_experiment.reserve = variants_capture.reserve
            new_truths = variants_capture.offline(Backend, args, queries, eligible, fresh)
            measured = variants_capture.acquire(Backend, args, queries, eligible, new_truths, fresh)
            assert len(measured) == 14
            points = set().union(*(set(r["actions"]) for r in measured.values()))
            assert points == {"16", "32", "64"}, points
            assert fresh["native_bridge"] == 28 and fresh["ideal_replay"] == 14
            assert fresh["canonical_capture"] == 14
            assert fresh["forced_prefix"] == sum(len(r["actions"]) for r in measured.values())
            print(
                "VARIANT_CAPTURE_SMOKE_PASSED "
                + json.dumps(
                    {"cases": len(measured), "points": sorted(points), "searches": dict(fresh)}
                ),
                flush=True,
            )
            write(
                output / "receipt.json",
                {
                    "status": "synthetic_only",
                    "searches": dict(counter),
                    "raw_sha256": {p.name: sha(p) for p in output.iterdir() if p.is_file()},
                },
            )
            print(
                "ORACLE_SMOKE_PASSED "
                + json.dumps(
                    {
                        "cases": len(queries),
                        "searches": dict(counter),
                        "zero_population": len(eligible[743]) == 0,
                        "partial_population": len(eligible[527]) == 7,
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
