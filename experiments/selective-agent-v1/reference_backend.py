"""Exact ground truth may scan the table; timed ANN code is inherited unchanged."""
from fannagent.api import AgentError, ExactTruth
from fannagent_pgvector.backend import uses_index
from psycopg import sql


class ExactReferenceMixin:
    def _exact_reference(self, query):
        conn = self._connect()
        statement, params = self._statement(query, exact=True)
        with conn.transaction():
            self._settings(conn)
            conn.execute("SELECT set_config('enable_seqscan','on',true)")
            for name in ("enable_indexscan", "enable_indexonlyscan", "enable_bitmapscan"):
                conn.execute("SELECT set_config(%s,'off',true)", (name,))
            plan = conn.execute(sql.SQL("EXPLAIN (FORMAT JSON) ") + statement, params).fetchone()[0]
            if uses_index(plan):
                raise AgentError("authoritative reference did not bypass index scans")
            rows = conn.execute(statement, params).fetchall()
        ids = [self.snapshot().source_to_id[str(r[0])] for r in rows]
        k = min(query["k"], len(rows))
        boundary = float(rows[k - 1][1]) if k else None
        strict = frozenset(
            i for i, r in zip(ids, rows) if boundary is not None and float(r[1]) < boundary
        )
        ties = frozenset(
            i for i, r in zip(ids, rows) if boundary is not None and float(r[1]) == boundary
        )
        return ExactTruth(len(ids), k, strict, ties, frozenset(ids))
