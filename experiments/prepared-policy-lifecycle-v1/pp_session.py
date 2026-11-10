"""One experimental change: session-owned prepared policy, unchanged query path."""

import time

from execution import Session


class OwnedPolicy:
    """Private per-session handle; admission work stays inside the backend timer."""

    def __init__(self, owner, tree):
        self.owner = owner
        self.tree = tree
        self.cache = owner._policies
        self.identity = self.cache.identity
        self.connection = owner.conn
        self.prepared = None

    def resolve(self, backend):
        if (
            backend is not self.owner
            or backend.conn is not self.connection
            or backend._policies is not self.cache
            or self.cache.identity != self.identity
        ):
            raise RuntimeError("Prepared handle binding changed")
        if self.prepared is None:
            prepared = backend._prepare_policy(self.tree)
            if prepared.artifact.runtime_profile_hash != self.identity:
                raise RuntimeError("Prepared cache/runtime profile binding differs")
            self.prepared = prepared
        return self.prepared


class OwnedSession(Session):
    def __init__(self, backend, raw, cfg):
        started = time.perf_counter_ns()
        # Preserve the original complete composite validation and ownership copy.
        with backend._operation_lock:
            super().__init__(backend, raw, cfg)
            self._owner = backend
            self._connection = backend.conn
            self._cache = backend._policies
            self._profile_identity = self._cache.identity
            self._runtime_profile = backend.runtime_profile
            # Resolve lazily at the original preparation line inside the backend
            # timer, so a native bypass never pays tree preparation/compilation.
            self._handle = OwnedPolicy(backend, self.raw["tree"])
            self.preparation_ms = (time.perf_counter_ns() - started) / 1e6

    def query(self, q, budget, *, trace=False):
        # Same routing/query body with a private owned handle for policy execution.
        # All additional binding checks are inside the routing timer.
        started = time.perf_counter_ns()
        from policy import route
        from pp_backend import execute_owned

        b = self.backend
        with b._operation_lock:
            if (
                b is not self._owner
                or b.conn is not self._connection
                or b.conn is not self.connection
                or b.conn is None
                or b.conn.closed
                or b._policies is not self._cache
                or b._policies.identity != self._profile_identity
                or b.runtime_profile is not self._runtime_profile
            ):
                raise RuntimeError("Owned session binding changed; create a new session")
            q = b.snapshot().query(q)
            bypass = q.get("k") != self.k or route(q) not in self.raw["eligible"]
            routing_ms = (time.perf_counter_ns() - started) / 1e6
            budget.reserve("native_bypass" if bypass else "policy_trace" if trace else "policy")
            result = (
                b.execute_probe(q, mode="native", policy=None, trace=False)
                if bypass
                else execute_owned(b, q, self._handle, trace=trace)
            )
            if not bypass and (
                not result.metadata.get("policy_applied")
                or result.metadata.get("policy_fallback")
                or result.metadata.get("policy_runtime_error")
            ):
                raise RuntimeError("Policy not cleanly acknowledged")
            result.metadata.update(
                native_bypass=bypass,
                requested_composite_hash=self.identity,
                policy_ann_ms=result.latency_ms,
                routing_ms=routing_ms,
            )
            result.latency_ms += routing_ms
            return result


def session(backend, raw, cfg):
    """Host empty-mask control gets the same original envelope validation."""
    from contract import FILTERS, digest

    if raw["eligible"]:
        return OwnedSession(backend, raw, cfg)
    # Skip backend preparation for a host-only empty mask, as original execution
    # never passes a policy on this path. Charge all original envelope validation.
    validating = {**raw, "eligible": FILTERS.copy()}
    result = OwnedSession.__new__(OwnedSession)
    started = time.perf_counter_ns()
    with backend._operation_lock:
        Session.__init__(result, backend, validating, cfg)
        result.raw["eligible"] = []
        result.identity = digest(["host-native-only", result.identity])
        result._owner = backend
        result._connection = backend.conn
        result._cache = backend._policies
        result._profile_identity = result._cache.identity
        result._runtime_profile = backend.runtime_profile
        result._handle = None
        result.preparation_ms = (time.perf_counter_ns() - started) / 1e6
    return result
