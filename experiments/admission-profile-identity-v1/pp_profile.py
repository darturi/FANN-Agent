"""Diagnostic-only deterministic profiling. No profiler enters primary timing."""

import cProfile
import pstats
import time


class Profiles:
    def __init__(self):
        self.groups = {}

    def call(self, key, function, *args, **kwargs):
        profile = cProfile.Profile()
        started = time.perf_counter_ns()
        result = profile.runcall(function, *args, **kwargs)
        elapsed = (time.perf_counter_ns() - started) / 1e6
        group = self.groups.setdefault(key, {"calls": 0, "wall_ms": 0.0, "functions": {}})
        group["calls"] += 1
        group["wall_ms"] += elapsed
        for (filename, line, name), (primitive, total, self_s, cumulative_s, _) in pstats.Stats(
            profile
        ).stats.items():
            identity = f"{filename}:{line}:{name}"
            row = group["functions"].setdefault(
                identity,
                {
                    "function": identity,
                    "primitive_calls": 0,
                    "total_calls": 0,
                    "self_ms": 0.0,
                    "cumulative_ms": 0.0,
                },
            )
            row["primitive_calls"] += primitive
            row["total_calls"] += total
            row["self_ms"] += self_s * 1000
            row["cumulative_ms"] += cumulative_s * 1000
        return result

    def serialize(self):
        return {
            "version": "cprofile-attribution.v1",
            "diagnostic_only": True,
            "interpretation": "Separate profiled pass; wall time includes profiler perturbation. "
            "Self time is exclusive; cumulative time includes descendants and must not be summed.",
            "groups": {
                key: {
                    **value,
                    "functions": sorted(
                        value["functions"].values(),
                        key=lambda row: (-row["self_ms"], row["function"]),
                    ),
                }
                for key, value in sorted(self.groups.items())
            },
        }


class ProfiledSession:
    def __init__(self, session, profiles, arm, stratum):
        self.session = session
        self.profiles = profiles
        self.key = arm + "/" + stratum
        self.phase = "activation"

    def __getattr__(self, name):
        return getattr(self.session, name)

    def query(self, *args, **kwargs):
        return self.profiles.call(self.key + "/" + self.phase, self.session.query, *args, **kwargs)
