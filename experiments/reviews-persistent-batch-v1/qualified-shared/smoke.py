"""Use independent PostgreSQL connections to check shared activation and stop parity."""

from pathlib import Path

from lookup import FILENAME, publish
from psycopg import connect, errors

DSN = "host=/tmp/socket dbname=postgres user=nobody"
QUERY = """
SELECT id, embedding <=> '[0.3,0.1,0.8,0.4,0.9,0.2,0.6,0.5]' AS distance
FROM reviews WHERE id <= 16000 AND total_votes >= 108 ORDER BY distance LIMIT 10
"""


def arm(conn, kind, value):
    with conn.transaction():
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        conn.execute("SET LOCAL enable_seqscan = off")
        conn.execute("SET LOCAL hnsw.ef_search = 1000")
        assert conn.execute(
            "SELECT fannagent.confirm_attach('reviews','reviews_fixture_graph',%s)"
            if kind == "shared"
            else "SELECT fannagent.confirm_bind('reviews','reviews_fixture_graph',%s)",
            (value,),
        ).fetchone() == (247286,)
        results = []
        for _ in range(2):
            out = conn.execute(QUERY).fetchall()
            cp = conn.execute("SELECT fannagent.confirm_last()").fetchone()[0]
            results.append((out, cp))
        return results


with connect(DSN, autocommit=True) as keeper, keeper.transaction():
    keeper.execute("LOCK TABLE reviews IN SHARE MODE NOWAIT")
    heap, index = keeper.execute(
        "SELECT 'reviews'::regclass::oid, 'reviews_fixture_graph'::regclass::oid"
    ).fetchone()
    rows = keeper.execute(
        "SELECT ctid::text,coalesce(total_votes >= 108,false) FROM ONLY reviews"
    ).fetchall()
    path = Path("/tmp") / FILENAME
    publish(path, heap, index, rows)
    with connect(DSN, autocommit=True) as first, connect(DSN, autocommit=True) as second:
        first.execute("SET lock_timeout = '50ms'")
        try:
            first.execute("UPDATE reviews SET total_votes = 0 WHERE id = 1")
        except errors.LockNotAvailable:
            pass
        else:
            raise AssertionError("Keeper lock allowed a concurrent writer")
        for value, cp in ((1, 32), (2, 16)):
            reference = arm(first, "local", value)
            assert all(len(out) == 10 and stop == cp for out, stop in reference)
            assert arm(first, "shared", value) == reference
            assert arm(second, "shared", value) == reference
            assert arm(first, "shared", value) == reference
        path.unlink()
print("SHARED_LOOKUP_TWO_CONNECTIONS_STOP_AND_OUTPUT_PARITY_PASSED")
