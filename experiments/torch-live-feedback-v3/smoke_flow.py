"""Synthetic PostgreSQL check of compiled v3 audits, forced prefixes and timing."""

import json
import os
import subprocess
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import support
from analysis import summarize
from broad_contract import compile_graph
from broad_support import replay_graph, verify_audit
from common import matches, publish, search, threshold
from limits import read, write
from measurement import Ledger, quality, timing
from oracle_design import FILTERS, validate_output
from psycopg import connect
from serving import request
from sessions import bind, session
from smoke_capture import Backend
from startup import start

# The synthetic index is partial; retain the real plan gate with that fixture predicate.
_statement = support.statement
support.statement = lambda q, exact=False: _statement(q, exact=exact, fixture=True)


def main():
    here = Path("/qual")
    batch = Path("/batch")
    output = here / "checks/live-v3-flow"
    output.mkdir(mode=0o777, parents=True)
    args = SimpleNamespace(
        bundle=Path("/tmp"),
        work=Path("/tmp"),
        output=output,
        fixture=True,
        ef=640,
        counter=Counter(total=0),
        arms=read(batch / "batch-binding.json")["arms"],
    )
    args.ledger = Ledger(output, 0, 5000)
    entries = {e["arm"]: e for e in read(batch / "compiled-programs.json")["bindings"]}
    os.sched_setaffinity(0, set(sorted(os.sched_getaffinity(0))[:4]))
    Path("/tmp/socket").mkdir(mode=0o700)
    Path("/tmp/pg_hba.conf").write_text("local all all trust\n")
    subprocess.run(
        ["/opt/postgresql/bin/initdb", "-D", "/tmp/pgdata", "-A", "trust", "-U", "nobody"],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    start(Path("/tmp"))
    try:
        with connect("host=/tmp/socket dbname=postgres user=nobody", autocommit=True) as keeper:
            fixture = (
                (here / "fixture.sql").read_text().replace("reviews_fixture_graph", "reviews_hnsw")
            )
            fixture = (
                fixture.replace("i<=10000 THEN 1000", "i<=0 THEN 1000")
                .replace("i<=20000 THEN 600", "i<=7 THEN 600")
                .replace("i<=30000 THEN 400", "i<=300 THEN 400")
            )
            fixture = fixture.replace("WHERE id<=16000", "WHERE id<=32000").replace(
                "WITH(m=32)", "WITH(m=64,ef_construction=128)"
            )
            keeper.execute(fixture + (here / "functions.sql").read_text())
            keeper.execute("BEGIN ISOLATION LEVEL REPEATABLE READ")
            keeper.execute("LOCK TABLE reviews IN SHARE MODE")
            args.snapshot = keeper.execute("SELECT pg_export_snapshot()").fetchone()[0]
            heap, index = keeper.execute(
                "SELECT 'reviews'::regclass::oid,'reviews_hnsw'::regclass::oid"
            ).fetchone()
            corpus = keeper.execute("SELECT ctid::text,total_votes FROM reviews").fetchall()
            ids = keeper.execute("SELECT id,total_votes FROM reviews").fetchall()
            eligible = {t: {i for i, v in ids if t < 0 or v >= t} for t in FILTERS}
            for t in FILTERS:
                publish(Path(f"/tmp/membership-{t}.bin"), heap, index, corpus, t)
            queries = []
            for i in range(2):
                for t in FILTERS:
                    q = {
                        "id": f"fixture-v{i}-" + ("unfiltered" if t < 0 else f"votes{t}"),
                        "k": 10,
                        "vector": [0.3 + i * 0.03, 0.1, 0.8, 0.4, 0.9, 0.2, 0.6, 0.5],
                    }
                    if t >= 0:
                        q["filter"] = {"field": "totalvotes", "op": "gte", "value": t}
                    queries.append(q)
            cases, truths = {}, {}
            for q in queries:
                t = threshold(q)
                with session(Backend, args) as c, bind(c, args, t, len(eligible[t]), None):
                    native = request(
                        c,
                        q,
                        lambda op: args.ledger.reserve(args.counter, "native_capture"),
                        fixture=True,
                    )["output"]
                with session(Backend, args) as c, bind(c, args, t, len(eligible[t]), None):
                    c.execute("SET LOCAL enable_indexscan=off")
                    c.execute("SET LOCAL enable_bitmapscan=off")
                    c.execute("SET LOCAL enable_seqscan=on")
                    args.ledger.reserve(args.counter, "fixture_exact")
                    truth, _ = search(c, q, exact=True, fixture=True)
                    truths[q["id"]] = truth
                with session(Backend, args) as c, bind(c, args, t, len(eligible[t]), 80):
                    c.execute("SELECT fannagent.v3_audit_enable(true)")
                    out = request(
                        c,
                        q,
                        lambda op: args.ledger.reserve(args.counter, "capture_probe"),
                        fixture=True,
                    )["output"]
                    audit = json.loads(c.execute("SELECT fannagent.v3_audit_read()").fetchone()[0])
                assert matches(out, native) and not audit["fault"] and not audit["exhausted"]
                row = {
                    "id": q["id"],
                    "filter": t,
                    "role": "development",
                    "native": native,
                    "native_recall": validate_output(native, eligible[t], truth),
                    "frames": audit["frames"],
                }
                _, trace = replay_graph(
                    compile_graph(entries[80]["policy"]), row, force_continue=True, trace=True
                )
                verify_audit(trace, audit)
                cases[q["id"]] = row
            expected, records, losses = quality(
                Backend, args, queries, eligible, truths, cases, entries, {}
            )
            timing(Backend, args, queries, eligible, expected)
            times = [json.loads(s) for s in (output / "timing.jsonl").open()]
            report = summarize(records, times, tuple(args.arms), draws=100)
            args.ledger.finish(args.counter)
            assert len(times) == len(queries) * len(args.arms) * 4
            assert len(records) == len(queries) * len(args.arms)
            assert all(
                not losses[f]
                for f in args.arms
                if f == "native640" or f == "empty" or f.startswith("matched")
            )
            assert any(r["checkpoint"] in (2, 3) for r in records)
            assert any(r["audit"] and r["audit"]["fault"] for r in records)
            write(
                output / "receipt.json",
                {
                    "status": "synthetic_v3_live_flow_passed",
                    "fixture_only": True,
                    "cases": len(queries),
                    "families": len(args.arms),
                    "quality_records": len(records),
                    "timing_records": len(times),
                    "searches": dict(args.counter),
                    "quality_losses": losses,
                    "control_equivalence": report["all_condition_controls_pass"],
                    "module_sha256": read(batch / "batch-binding.json")["module_sha256"],
                },
            )
            print((output / "receipt.json").read_text(), flush=True)
    finally:
        subprocess.run(
            ["/opt/postgresql/bin/pg_ctl", "-D", "/tmp/pgdata", "-m", "fast", "-w", "stop"],
            check=True,
        )


if __name__ == "__main__":
    main()
