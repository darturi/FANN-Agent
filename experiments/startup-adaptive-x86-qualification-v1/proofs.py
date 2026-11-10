"""Reconcile every preserved case, guard, exact provenance and bounded CPU sample."""

import ast
import math
from pathlib import Path

from common import read, sha
from paths import A3, MAIN


def ids(paths):
    result = set()
    for p in paths:
        for n in ast.parse(p.read_text()).body:
            if isinstance(n, ast.ClassDef):
                result.update(
                    p.stem + "." + n.name + "." + m.name
                    for m in n.body
                    if isinstance(m, ast.FunctionDef) and m.name.startswith("test_")
                )
    return result


def expected(workspace, kind):
    w = Path(workspace)
    if kind == "main":
        return ids((w / MAIN).glob("test_*.py"))
    p = w / A3
    return ids(
        [
            *p.glob("test_*.py"),
            *(p / "a3").glob("test_*.py"),
            w / "trials/torch-reviews-startup-exact-vector-exact-image-review-v1/test_review.py",
        ]
    )


def validate(out, workspace, contract, profile="target"):
    out = Path(out)
    target = contract["target_reference" if profile == "target" else "local_reference"]
    main_ids = expected(workspace, "main")
    a3_ids = expected(workspace, "a3")
    if len(main_ids) != 128 or len(a3_ids) != 276:
        raise ValueError("Frozen case inventory differs")
    for kind, count, case_ids in [("main", 128, main_ids), ("a3", 276, a3_ids)]:
        for phase in ("source", "sealed"):
            root = out / (kind + "-" + phase)
            r = read(root / "receipt.json")
            v = read(root / "tests.json")
            if (
                r["status"] != "pass"
                or r["profile"] != profile
                or type(r["tests_run"]) is not int
                or r["tests_run"] != count
            ):
                raise ValueError("Incomplete " + kind + " " + phase)
            if (
                v["status"] != "pass"
                or (type(v["tests_run"]) is not int or v["tests_run"] != count)
                or v["failures"]
                or v["errors"]
            ):
                raise ValueError("Suite result differs")
            if any(type(v[k]) is not int or v[k] != 0 for k in ("failures", "errors")):
                raise ValueError("Strict zero error counters required")
            if kind == "main":
                if v["actual_provenance"] != target:
                    raise ValueError("Main exact reference differs")
                if r["tests_sha256"] != sha(root / "tests.json") or r["guard_sha256"] != sha(
                    root / "guard.json"
                ):
                    raise ValueError("Main child proof bytes differ")
                g = read(root / "guard.json")
                io = g["fixture_io"]
                if (
                    g["exit_code"]
                    or g["error"] is not None
                    or g["denied_connections"]
                    or g["denied_subprocesses"]
                    or not g["connection_bindings_restored"]
                ):
                    raise ValueError("Main guard failed")
                if io["clones"] < 1 or io["clones"] != io["seeds_verified"] or io["reseals"] != 10:
                    raise ValueError("Original fixture proofs incomplete")
                if g["fixture_builds"] != dict(
                    requests=5, actual_builds=1, reused=4, seed_verifications=6, restored=True
                ):
                    raise ValueError("Actual original seed/build proof differs")
                import json

                events = [
                    json.loads(s) for s in (root / "guard.events.jsonl").read_text().splitlines()
                ]
                passed = [
                    e["test"].rsplit("(", 1)[-1].removesuffix(")")
                    for e in events
                    if e["kind"] == "pass"
                ]
                if set(passed) != case_ids or len(passed) != count:
                    raise ValueError("Main per-case outcomes differ")
            else:
                if (
                    v["skipped"]
                    or set(v["test_ids"]) != case_ids
                    or len(v["test_ids"]) != count
                    or r["actual_provenance"] != target
                    or r["external_attempts"]
                    or r["code_sha256"] != contract["source_inventory"]
                ):
                    raise ValueError("A3 cases/source/guard/reference differ")
                if profile == "target" and (
                    not v["adapter_records"]
                    or any(
                        q["status"] != "pass"
                        or q["actual_python"] != "3.12.15"
                        or q["synthetic_fixture"] is not True
                        for q in v["adapter_records"]
                    )
                ):
                    raise ValueError("Exact target fixture selector not proved")
    r = read(out / "cpu/receipt.json")
    c = read(out / "cpu/cpu.json")
    if (
        r["status"] != "pass"
        or r["profile"] != profile
        or r["actual_provenance"] != target
        or r["external_attempts"]
        or r["code_sha256"] != contract["source_inventory"]
        or c["status"] != "pass"
        or c["total_cpu_seconds"] > 120
        or c["total_wall_seconds"] > 180
    ):
        raise ValueError("Bounded CPU source/reference/caps failed")
    if len(c["measurements"]) != 60:
        raise ValueError("Complete CPU repeats required")
    for name in contract["CPU"]["profiles"]:
        for method in ("original_packed64_producer", "adaptive_producer"):
            for rows in (16, 64):
                group = [
                    m
                    for m in c["measurements"]
                    if (m["profile"], m["method"], m["rows"]) == (name, method, rows)
                ]
                if len(group) != 3 or {m["repeat"] for m in group} != {0, 1, 2}:
                    raise ValueError("CPU sample inventory differs")
                for m in group:
                    if any(
                        type(m[k]) not in (int, float) or not math.isfinite(m[k]) or m[k] <= 0
                        for k in ("cpu_seconds", "wall_seconds")
                    ):
                        raise ValueError("CPU clocks invalid")
    worst = max(
        s["same_machine_linear_wall_projection_seconds"]
        for s in c["summaries"]
        if s["method"] == "adaptive_producer"
    )
    return dict(
        status="complete_target_correctness_and_bounded_CPU"
        if profile == "target"
        else "complete_local_readiness_only",
        main_cases_per_phase=128,
        A3_cases_per_phase=276,
        target_correctness_qualified=profile == "target",
        bounded_native_CPU_measurement_qualified=profile == "target",
        bounded_CPU_screen="observed_projection_below600"
        if worst <= 600
        else "held_projection_over600",
        worst_observed_projection_seconds=worst,
        native_CPU_budget_qualified=False,
        native_memory_qualified=False,
        native_resource_release=False,
        full_B2f_released=False,
        ANN_searches=0,
        exact_searches=0,
        real_SQL=0,
        provider_calls=0,
    )
