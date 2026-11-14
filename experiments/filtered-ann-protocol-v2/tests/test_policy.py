import ctypes
import random
import subprocess

import pytest
from fannproto.compiler import compile_programs
from fannproto.policy import (
    COUNT,
    DECIDE,
    DISTANCE,
    FILTERS,
    POINTS,
    TURNOVER,
    PolicyError,
    choose,
    decide,
    observation_plan,
    replay,
    validate,
)


def p(rules=None):
    return {
        "schema": "fannagent.filtered-ann.v2",
        "name": "test",
        "rules": rules or {},
        "rationale": "test",
    }


def clause(cp, *conditions):
    return {"cp": cp, "conditions": list(conditions)}


def test_partial_count_stop_and_missing_distance():
    a = p({"votes743": [clause(16, ["qualifying_count", "<=", 7])]})
    assert decide(a, "votes743", 16, {"qualifying_count": 0})
    b = p({"votes743": [clause(16, ["tenth_distance", "<=", 1.0])]})
    assert not decide(b, "votes743", 16, {"qualifying_count": 7, "tenth_distance": None})


def test_turnover_dependency_is_previous_scheduled_checkpoint():
    masks = observation_plan(p({"votes32": [clause(64, ["top10_new_since_previous", "<=", 0])]}))
    assert masks["votes32"] == {
        "16": 0,
        "32": COUNT | DISTANCE,
        "64": COUNT | DISTANCE | TURNOVER | DECIDE,
    }
    assert all(not any(m.values()) for f, m in masks.items() if f != "votes32")


def test_first_satisfied_clause_and_no_completeness_floor():
    a = p(
        {
            "unfiltered": [
                clause(16, ["qualifying_count", "<=", 7]),
                clause(32, ["qualifying_count", ">=", 10]),
            ]
        }
    )
    assert (
        choose(
            a,
            {
                "filter": "unfiltered",
                "observations": {"16": {"qualifying_count": 7}, "32": {"qualifying_count": 40}},
            },
        )
        == 16
    )


def test_forbidden_features_order_types_and_limits():
    for bad in (
        p({"source_id": [clause(16)]}),
        p({"votes32": [clause(32), clause(16)]}),
        p({"votes32": [clause(16, ["fold", ">=", 0])]}),
        p({"votes32": [clause(16, ["qualifying_count", ">=", True])]}),
        p({"votes32": [clause(16, ["frontier_gap", ">=", float("nan")])]}),
    ):
        with pytest.raises((PolicyError, ValueError)):
            validate(bad)


def test_unknown_partial_label_cannot_pass_quality():
    row = {
        "group": 0,
        "fold": 0,
        "filter": "votes743",
        "native_recall": 0.7,
        "observations": {"16": {"qualifying_count": 7}},
        "proofs": {},
    }
    report = replay(p({"votes743": [clause(16, ["qualifying_count", "<=", 7])]}), [row])
    assert (
        report["status"] == "incomplete_prefix_evidence"
        and not report["quality_preserves_raw_native640"]
    )


def test_generated_c_matches_python_nullable_partial_decisions(tmp_path):
    a = p(
        {
            f: [
                clause(16, ["qualifying_count", "<=", 7]),
                clause(32, ["frontier_gap", ">=", 0.05], ["tenth_distance", "<=", 0.4]),
                clause(64, ["top10_new_since_previous", "<=", 1]),
            ]
            for f in FILTERS
        }
    )
    programs = [
        {"arm": 20, "policy": a, "force_continue": False},
        {"arm": 21, "policy": a, "force_continue": True},
    ]
    source, manifest = compile_programs(programs)
    (tmp_path / "p.c").write_text(
        "#include <stdbool.h>\n"
        + source
        + "\nint mask(int a,int f,int cp){return V2Mask(a,f,cp);}\nint de"
        "cision(int a,int f,int cp,int n,double t,double g,int u,bool"
        " full,bool hg,bool hu){volatile bool v=V2Decision(a,f,cp,n,t"
        ",g,u,full,hg,hu);return v&&!V2ForceContinue(a);}\n"
    )
    subprocess.run(
        ["cc", "-shared", "-fPIC", "-O2", str(tmp_path / "p.c"), "-o", str(tmp_path / "p.so")],
        check=True,
    )
    lib = ctypes.CDLL(str(tmp_path / "p.so"))
    lib.decision.argtypes = (
        [ctypes.c_int] * 4 + [ctypes.c_double] * 2 + [ctypes.c_int] + [ctypes.c_bool] * 3
    )
    lib.decision.restype = ctypes.c_int
    lib.mask.argtypes = [ctypes.c_int] * 3
    rng = random.Random(20261113)
    for _ in range(1000):
        n = rng.randrange(50)
        t = rng.random() if n >= 10 else None
        g = rng.uniform(-1, 1) if t is not None and rng.randrange(3) else None
        u = rng.randrange(11) if t is not None and rng.randrange(2) else None
        o = dict(qualifying_count=n, tenth_distance=t, frontier_gap=g, top10_new_since_previous=u)
        for cp in POINTS:
            assert bool(
                lib.decision(
                    20,
                    32,
                    cp,
                    n,
                    t or 0,
                    g or 0,
                    u or 0,
                    t is not None,
                    g is not None,
                    u is not None,
                )
            ) == decide(a, "votes32", cp, o)
            assert not lib.decision(
                21, 32, cp, n, t or 0, g or 0, u or 0, t is not None, g is not None, u is not None
            )
            assert lib.mask(20, 32, cp) == observation_plan(a)["votes32"][str(cp)]
