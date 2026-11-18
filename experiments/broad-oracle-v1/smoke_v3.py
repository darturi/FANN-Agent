"""Actual fixture graph: full causal capture, native parity and VM semantics."""

import json
import os
import subprocess
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from broad_contract import FEATURES, compile_graph
from broad_support import replay_graph, verify_audit
from common import capture, matches, publish, write
from oracle_design import FILTERS
from psycopg import connect
from serving import request
from sessions import bind, session
from smoke_capture import Backend
from startup import start


def main():
    os.sched_setaffinity(0, set(sorted(os.sched_getaffinity(0))[:4]))
    here = Path("/qual")
    output = here / "checks/v3-smoke"
    output.mkdir(mode=0o700)
    queries = [json.loads(s) for s in (here / "queries.jsonl").open()]
    bindings = {b["arm"]: b for b in json.loads((here / "bindings.json").read_text())}
    args = SimpleNamespace(
        bundle=Path("/tmp"), work=Path("/tmp"), ef=640, fixture=True, output=output
    )
    counter = Counter(total=0)

    def reserve(_):
        assert counter["total"] < 5000
        counter["total"] += 1

    start(Path("/tmp"))
    try:
        with connect("host=/tmp/socket dbname=postgres user=nobody", autocommit=True) as keeper:
            keeper.execute(
                (here / "functions.sql")
                .read_text()
                .replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION")
            )
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
                path = Path(f"/tmp/membership-{t}.bin")
                path.unlink(missing_ok=True)
                publish(path, heap, index, rows, t)
            captured = []
            faults = exhausted = early = 0
            for qi, q in enumerate(queries):
                t = -1 if q.get("filter") is None else q["filter"]["value"]
                with session(Backend, args) as c, bind(c, args, t, len(eligible[t]), None):
                    native = request(c, q, reserve, fixture=True)["output"]
                with session(Backend, args) as c, bind(c, args, t, len(eligible[t]), 80):
                    c.execute("SELECT fannagent.v3_audit_enable(true)")
                    actual = request(c, q, reserve, fixture=True)["output"]
                    audit = json.loads(c.execute("SELECT fannagent.v3_audit_read()").fetchone()[0])
                    assert matches(native, actual)
                assert not audit["exhausted"] and not audit["fault"]
                row = {"id": q["id"], "filter": t, "native": native, "frames": audit["frames"]}
                graph = compile_graph(bindings[80]["policy"])
                cp, frames = replay_graph(graph, row, force_continue=True, trace=True)
                assert cp == 0
                verify_audit(frames, audit)
                with session(Backend, args) as c, bind(c, args, t, len(eligible[t]), 0):
                    reserve("canonical")
                    canonical = capture(
                        c, q, "broad-fixture-" + str(qi), budget=(1 << 63) - 1, fixture=True
                    )
                    assert matches(native, canonical["output"])
                    assert len(row["frames"]) == len(canonical["states"])
                    for frame in row["frames"]:
                        assert (
                            frame["values"][1]
                            == canonical["states"][frame["checkpoint"]]["actual_layer0_distances"]
                        )
                    observed = {
                        f["checkpoint"]: dict(zip(FEATURES, f["values"], strict=True))
                        for f in row["frames"]
                    }
                    for old in canonical["checkpoints"]:
                        for name in ("qualifying_count", "tenth_distance", "frontier_gap"):
                            a, b = old[name], observed[old["checkpoint"]][name]
                            assert a == b or a is not None and b is not None and abs(a - b) < 1e-12
                for arm, binding in bindings.items():
                    if arm == 80:
                        continue
                    wanted, expected = replay_graph(
                        compile_graph(binding["policy"]), row, trace=True
                    )
                    with session(Backend, args) as c, bind(c, args, t, len(eligible[t]), arm):
                        c.execute("SELECT fannagent.v3_audit_enable(true)")
                        result = request(c, q, reserve, fixture=True)["output"]
                        got = c.execute("SELECT fannagent.confirm_last()").fetchone()[0]
                        audit = json.loads(
                            c.execute("SELECT fannagent.v3_audit_read()").fetchone()[0]
                        )
                        assert got == wanted, (arm, got, wanted)
                        verify_audit(expected, audit)
                        faults += audit["fault"]
                        exhausted += audit["exhausted"]
                        early += 0 < got < 16
                    with session(Backend, args) as c, bind(c, args, t, len(eligible[t]), 10):
                        c.execute("SELECT fannagent.oracle_set(%s)", (wanted,))
                        reference = request(c, q, reserve, fixture=True)["output"]
                        assert matches(result, reference), (arm, wanted)
                captured.append(row)
            assert faults > 0 and exhausted > 0 and early > 0
            (output / "cases.jsonl").write_text("".join(json.dumps(r) + "\n" for r in captured))
            write(
                output / "receipt.json",
                {
                    "status": "v3_native_fixture_passed",
                    "cases": len(captured),
                    "queries": dict(counter),
                    "fault_fallbacks": faults,
                    "budget_fallbacks": exhausted,
                    "stops_before_16": early,
                    "fixture_only": True,
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
