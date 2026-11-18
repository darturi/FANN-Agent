"""Real partial handoff with an unexecuted reserved stop, then complete resumed timing."""

import json
import os
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import oracle_experiment
import timing_followup
from common import capture, publish, sha, threshold, write
from followup_analyse import report
from oracle_design import FILTERS, prefix_chain, prefix_signature
from oracle_experiment import acquire, offline, timing
from psycopg import connect
from sessions import bind, session
from startup import start


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
    output = here / "checks/followup-smoke-r2/source"
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
            ordered = [q for t in FILTERS for q in queries if threshold(q) == t]
            acquire(Backend, args, ordered[:3], eligible, truths, counter)
            (output / "oracle-freeze.json").rename(output / "subcall-freeze.json")
            pending = ordered[3]
            t = threshold(pending)
            with session(Backend, args) as c:
                with bind(c, args, t, len(eligible[t]), None):
                    oracle_experiment.perform(c, pending, counter, "native_quality", args)
                with bind(c, args, t, len(eligible[t]), 0):
                    oracle_experiment.reserve(counter, "canonical_capture", args)
                    cap = capture(c, pending, "pending-source", budget=(1 << 63) - 1, fixture=True)
                    signature = prefix_signature(cap["states"])
                    with (output / "trajectories.jsonl").open("a") as handle:
                        oracle_experiment.emit(
                            handle,
                            {
                                "id": pending["id"],
                                "count": len(signature),
                                "targets": [r["target"] for r in signature],
                                "prefix_sha256": prefix_chain(signature),
                                "output": cap["output"],
                            },
                        )
                    # Deliberately reserve, but do not dispatch, this query.
                    (output / "attempts.pending").write_text('{"total":')
            keeper.execute("ROLLBACK")
            prior_output = output
            manifest = {
                "job_id": "synthetic-source",
                "partial_acquisition": True,
                "unpublished_reservation_charged": True,
                "files": {
                    r.name: sha(r)
                    for r in prior_output.iterdir()
                    if r.name in timing_followup.SOURCE_FILES or r.name == "attempts.pending"
                },
            }
            manifest_path = prior_output.parent / "source-acquisition.json"
            write(manifest_path, manifest)
            output = prior_output.parent / "results"
            output.mkdir(mode=0o700)
            args.output = output
            args.acquisition_path = prior_output
            args.acquisition_manifest = manifest_path
            for name in ("queries.jsonl", "query-roles.json", "eligibility.json"):
                shutil.copyfile(prior_output / name, output / name)
            keeper.execute("BEGIN ISOLATION LEVEL REPEATABLE READ")
            keeper.execute("LOCK TABLE reviews IN SHARE MODE")
            args.snapshot = keeper.execute("SELECT pg_export_snapshot()").fetchone()[0]
            counter = Counter(total=0)
            oracle_experiment.reserve = timing_followup.reserve
            truths = timing_followup.load_acquisition(Backend, args, queries, eligible, counter)
            choices = timing_followup.resume_and_qualify(
                Backend, args, queries, eligible, truths, counter
            )
            timing(Backend, args, queries, eligible, choices, counter)
            args.window_ledger.finish(counter)
            write(
                output / "receipt.json",
                {
                    "status": "synthetic_only",
                    "searches": dict(counter),
                    "raw_sha256": {
                        str(r.relative_to(output)): sha(r) for r in output.rglob("*") if r.is_file()
                    },
                },
            )
            report(output, output, fixture=True)
            assert counter["source_incomplete_forced_prefix"] == 0
            assert counter["source_unpublished_reserved"] == 1
            print(
                "FOLLOWUP_SMOKE_PASSED "
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
