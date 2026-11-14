"""Synthetic runtime parity for masks, dependency frames and partial/zero stops."""

import json
import os
import subprocess
from pathlib import Path

from common import THRESHOLDS, capture, matches, publish, require, search
from psycopg import connect, sql
from startup import start

HERE = Path("/qual")
PROGRAMS = json.loads((HERE / "compiled-programs.json").read_text())["bindings"]
HIGH_COUNT = int(os.environ.get("SYNTHETIC_HIGH_VOTE_COUNT", "7"))
assert HIGH_COUNT in (0, 7)
SQL = (
    (HERE / "fixture.sql")
    .read_text()
    .replace("i<=10000 THEN 1000", f"i<={HIGH_COUNT} THEN 1000")
    .replace("reviews_fixture_graph", "reviews_hnsw")
)


def conn():
    c = connect("host=/tmp/socket dbname=postgres user=nobody", autocommit=True)
    c.execute("SELECT fannagent.bind_target('reviews','id','embedding','reviews_hnsw')")
    return c


def begin(c, snapshot, t, passing, arm=None):
    c.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
    c.execute(sql.SQL("SET TRANSACTION SNAPSHOT {}").format(sql.Literal(snapshot)))
    c.execute("SET LOCAL enable_seqscan=off")
    c.execute("SET LOCAL hnsw.ef_search=8192")
    c.execute("SET LOCAL hnsw.iterative_scan=off")
    if arm is not None:
        c.execute(
            "SELECT fannagent.study_attach('reviews','reviews_hnsw',%s,%s,%s)", (t, arm, passing)
        )


def decision(p, f, cp, o):
    for c in p["rules"].get(f, []):
        if c["cp"] == cp and all(
            o.get(n) is not None and (o[n] >= v if op == ">=" else o[n] <= v)
            for n, op, v in c["conditions"]
        ):
            return True
    return False


def main():
    Path("/tmp/socket").mkdir(mode=0o700)
    subprocess.run(
        ["/opt/postgresql/bin/initdb", "-D", "/tmp/pgdata", "-A", "trust", "-U", "nobody"],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    Path("/tmp/pg_hba.conf").write_text("local all all trust\n")
    start(Path("/tmp"))
    results = []
    partial = 0
    zero = 0
    empty_checks = 0
    dependency_checks = 0
    try:
        with connect("host=/tmp/socket dbname=postgres user=nobody", autocommit=True) as c:
            c.execute(SQL + (HERE / "functions.sql").read_text())
        with conn() as keeper:
            keeper.execute("BEGIN ISOLATION LEVEL REPEATABLE READ")
            keeper.execute("LOCK TABLE reviews IN SHARE MODE")
            snapshot = keeper.execute("SELECT pg_export_snapshot()").fetchone()[0]
            heap, index = keeper.execute(
                "SELECT 'reviews'::regclass::oid,'reviews_hnsw'::regclass::oid"
            ).fetchone()
            rows = keeper.execute("SELECT ctid::text,total_votes FROM reviews").fetchall()
            for t in THRESHOLDS:
                meta = publish(Path(f"/tmp/membership-{t}.bin"), heap, index, rows, t)
                f = "unfiltered" if t < 0 else "votes" + str(t)
                q = {"id": f, "k": 10, "vector": [0.3, 0.1, 0.8, 0.4, 0.9, 0.2, 0.6, 0.5]}
                if t >= 0:
                    q["filter"] = {"field": "totalvotes", "op": "gte", "value": t}
                with conn() as c:
                    begin(c, snapshot, t, meta["qualifying"])
                    native, _ = search(c, q, fixture=True)
                    c.execute("COMMIT")
                    begin(c, snapshot, t, meta["qualifying"], 0)
                    cap = capture(c, q, "canonical", fixture=True)
                    require(matches(cap["output"], native), "capture/native parity")
                    proof = {}
                    for o in cap["checkpoints"]:
                        proof[o["checkpoint"]] = capture(
                            c, q, "force" + str(o["checkpoint"]), budget=o["budget"], fixture=True
                        )["output"]
                    c.execute("COMMIT")
                    require(
                        len(cap["checkpoints"]) == 3,
                        "fixture must exercise all scheduled checkpoints",
                    )
                    # Reuse each backend across all roles and native after v2.
                    for entry in PROGRAMS:
                        arm = entry["arm"]
                        p = entry["policy"]
                        begin(c, snapshot, t, meta["qualifying"], arm)
                        c.execute("SELECT fannagent.v2_audit_enable(true)")
                        out, _ = search(c, q, fixture=True)
                        cp = c.execute("SELECT fannagent.confirm_last()").fetchone()[0]
                        audit = json.loads(
                            c.execute("SELECT fannagent.v2_audit_read()").fetchone()[0]
                        )
                        c.execute("COMMIT")
                        wanted = (
                            0
                            if entry["force_continue"]
                            else next(
                                (
                                    o["checkpoint"]
                                    for o in cap["checkpoints"]
                                    if decision(p, f, o["checkpoint"], o)
                                ),
                                0,
                            )
                        )
                        require(
                            cp == wanted and matches(out, proof[wanted] if wanted else native),
                            "compiled partial first-stop/output parity",
                        )
                        expected_masks = entry["observation_plan"][f]
                        observed = [
                            o["checkpoint"]
                            for o in cap["checkpoints"]
                            if expected_masks[str(o["checkpoint"])]
                            and (not wanted or o["checkpoint"] <= wanted)
                        ]
                        require(
                            audit["arm"] == arm
                            and [o["checkpoint"] for o in audit["frames"]] == observed,
                            "extra or missing observation passes",
                        )
                        for frame in audit["frames"]:
                            canonical = next(
                                o
                                for o in cap["checkpoints"]
                                if o["checkpoint"] == frame["checkpoint"]
                            )
                            mask = expected_masks[str(frame["checkpoint"])]
                            require(frame["mask"] == mask, "dependency mask differs")
                            for n in (
                                "qualifying_count",
                                "tenth_distance",
                                "frontier_gap",
                                "top10_new_since_previous",
                            ):
                                needed = (
                                    mask & 1
                                    if n == "qualifying_count"
                                    else mask & 4
                                    if n == "top10_new_since_previous"
                                    else mask & 2
                                )
                                v = frame[n]
                                w = canonical[n]
                                if not needed:
                                    require(v is None, "unrequested feature collected")
                                elif v is None or w is None:
                                    require(v == w, "null feature semantics differ")
                                else:
                                    require(abs(v - w) <= 1e-12, "masked feature differs")
                        if cp and len(out) < 10:
                            partial += 1
                            zero += len(out) == 0
                        if not any(expected_masks.values()):
                            require(
                                not audit["frames"] and matches(out, native),
                                "empty predicate still observes",
                            )
                            empty_checks += 1
                        if arm == 44 and t == 32:
                            require(
                                [o["checkpoint"] for o in audit["frames"]] == [32, 64],
                                "turnover previous-checkpoint dependency missing",
                            )
                            dependency_checks += 1
                        begin(c, snapshot, t, meta["qualifying"])
                        again, _ = search(c, q, fixture=True)
                        c.execute("COMMIT")
                        require(matches(again, native), "legacy/native contaminated by v2 state")
                results.append(
                    {
                        "filter": t,
                        "programs": len(PROGRAMS),
                        "first_stop_and_prefix_output_parity": True,
                        "masked_features_match_canonical": True,
                        "native_after_role_switch_parity": True,
                    }
                )
            require(
                partial > 0 and empty_checks > 0 and dependency_checks > 0,
                "missing partial/empty/dependency coverage",
            )
            if HIGH_COUNT == 0:
                require(zero > 0, "missing zero-output prefix coverage")
            print(
                "SMOKE_RECEIPT "
                + json.dumps(
                    {
                        "status": "passed",
                        "fixture": "synthetic8d partial graph, effort8192 to exercise all "
                        "checkpoints; not original-graph/cost qualification",
                        "conditions": results,
                        "partial_stops_verified": partial,
                        "zero_result_stops_verified": zero,
                        "synthetic_high_vote_population": HIGH_COUNT,
                        "zero_observation_predicates_checked": empty_checks,
                        "turnover_dependency_checks": dependency_checks,
                        "exact_serving_calls": 0,
                        "holdout_access": False,
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
