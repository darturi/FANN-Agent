"""Check all fixture checkpoints through the independent raw canonical path."""

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

from canonical_features import cosine_projection
from common import capture, matches
from psycopg import connect
from sessions import bind, session
from smoke_capture import Backend
from startup import start


def main():
    os.sched_setaffinity(0, set(sorted(os.sched_getaffinity(0))[:4]))
    here = Path("/qual")
    queries = [json.loads(line) for line in (here / "queries.jsonl").open()]
    cases = {r["id"]: r for r in map(json.loads, (here / "checks/v3-smoke/cases.jsonl").open())}
    args = SimpleNamespace(bundle=Path("/tmp"), work=Path("/tmp"), ef=640, fixture=True)
    output = here / "checks/frontier-projection-v1.json"
    assert not output.exists()
    checked = 0
    differences = []
    start(Path("/tmp"))
    try:
        with connect("host=/tmp/socket dbname=postgres user=nobody", autocommit=True) as keeper:
            keeper.execute("BEGIN ISOLATION LEVEL REPEATABLE READ")
            keeper.execute("LOCK TABLE reviews IN SHARE MODE")
            args.snapshot = keeper.execute("SELECT pg_export_snapshot()").fetchone()[0]
            for i, q in enumerate(queries):
                t = -1 if q.get("filter") is None else q["filter"]["value"]
                passing = keeper.execute(
                    "SELECT count(*) FROM reviews WHERE %s<0 OR total_votes >= %s", (t, t)
                ).fetchone()[0]
                with session(Backend, args) as c, bind(c, args, t, passing, 0):
                    result = capture(
                        c, q, "projection-" + str(i), budget=(1 << 63) - 1, fixture=True
                    )
                row = cases[q["id"]]
                assert matches(row["native"], result["output"])
                assert len(row["frames"]) == len(result["states"])
                for frame in row["frames"]:
                    raw = result["states"][frame["checkpoint"]]["features"].get(
                        "frontier_distance_min"
                    )
                    a, b = frame["values"][8], cosine_projection(raw)
                    assert a == b or a is not None and b is not None and abs(a - b) < 1e-12, (
                        q["id"],
                        frame["checkpoint"],
                        a,
                        raw,
                        b,
                    )
                    if raw != b:
                        differences.append(
                            {
                                "id": q["id"],
                                "checkpoint": frame["checkpoint"],
                                "raw": raw,
                                "projected": b,
                            }
                        )
                    checked += 1
            receipt = {
                "status": "independent_frontier_projection_fixture_passed",
                "cases": len(queries),
                "frames": checked,
                "ann_queries": len(queries),
                "raw_boundary_differences": differences,
                "fixture_only": True,
            }
            output.write_text(json.dumps(receipt, indent=2) + "\n")
            print(json.dumps(receipt), flush=True)
    finally:
        subprocess.run(
            ["/opt/postgresql/bin/pg_ctl", "-D", "/tmp/pgdata", "-m", "fast", "-w", "stop"],
            check=True,
        )


if __name__ == "__main__":
    main()
