"""P2b: one owned semantic fingerprint per admission; unchanged P2a query path."""

import time
from dataclasses import dataclass
from types import MappingProxyType

from pp_session import OwnedPolicy, OwnedSession


@dataclass(frozen=True, slots=True)
class AdmissionProfile:
    """Only immutable validation inputs, privately copied and hashed per session.

    Never caches a caller's mutable RuntimeProfile or shares identities across
    admissions. Snapshot construction and hashing remain in preparation_ms.
    """

    fingerprint: str
    runtime_features: object
    available_collection_groups: frozenset

    @classmethod
    def capture(cls, profile):
        owned = profile.model_copy(deep=True)
        return cls(
            owned.fingerprint,
            MappingProxyType(owned.runtime_features),
            frozenset(owned.available_collection_groups),
        )


class AdmissionSession(OwnedSession):
    # Inherit the byte-identical P2a query body and lazy preparation handle.
    def __init__(self, backend, raw, cfg):
        started = time.perf_counter_ns()
        from contract import FILTERS, digest
        from fannagent_pgvector.profiles import PROFILE
        from pb_policy import validate

        with backend._operation_lock:
            # This experiment is qualified only for the frozen profile binding.
            if backend.runtime_profile is not PROFILE:
                raise RuntimeError("Admission requires the frozen runtime profile binding")
            profile = AdmissionProfile.capture(PROFILE)
            if profile.fingerprint != backend._policies.identity:
                raise RuntimeError("Admission/cache semantic profile identity differs")
            validating = {**raw, "eligible": FILTERS.copy()} if not raw["eligible"] else raw
            self.backend = backend
            self.raw, self.identity = validate(validating, cfg, profile)
            if not raw["eligible"]:
                self.raw["eligible"] = []
                self.identity = digest(["host-native-only", self.identity])
            self.k = cfg["k"]
            self.connection = backend.conn
            self._owner = backend
            self._connection = backend.conn
            self._cache = backend._policies
            self._profile_identity = self._cache.identity
            self._runtime_profile = backend.runtime_profile
            self._admission_profile = profile
            self._handle = OwnedPolicy(backend, self.raw["tree"]) if self.raw["eligible"] else None
            self.preparation_ms = (time.perf_counter_ns() - started) / 1e6


def session(backend, raw, cfg):
    """Both A/A labels use this exact factory with fresh state and cold charges."""
    return AdmissionSession(backend, raw, cfg)
