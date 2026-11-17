"""Reconstruct every M5 label, audit, role/CPU placement, timed row and work counter."""

import argparse
import collections
import json
from pathlib import Path

from common import matches, require, sha, threshold, write
from m5_design import (
    ARMS,
    CONTINUE_FAMILIES,
    COUNT,
    COUNTERS,
    FILTERS,
    GRAPH_COUNTERS,
    GROUPS,
    blocks,
    choose,
    cpu_for,
    ledger,
    ordered,
    reader_order,
    role,
)
from m5_experiment import KEYS, expected_program, filter_name, load_programs, validate


def lines(path):
    with path.open() as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def value(row):
    return {key: row[key] for key in KEYS}


def scan_nodes(node):
    return ([node] if "Scan" in node["Node Type"] else []) + [
        n for child in node.get("Plans", []) for n in scan_nodes(child)
    ]


def phase_receipt(folder, phase, binding, fixture):
    r = json.loads((folder / "receipt.json").read_text())
    require(
        r["status"] == ("M5_fixture_" if fixture else "M5_") + phase + "_complete",
        "phase did not complete in required scope",
    )
    require(
        set(r["raw_sha256"])
        == {p.name for p in folder.iterdir() if p.is_file() and p.name != "receipt.json"},
        "raw file inventory differs",
    )
    for name, h in r["raw_sha256"].items():
        require(
            Path(name).name == name and sha(folder / name) == h,
            "raw file digest differs: " + phase + "/" + name,
        )
    require(
        r["module_sha256"] == binding[phase + "_module_sha256"]
        and r["programs_sha256"] == binding["programs_sha256"]
        and r["runtime_profile"] == binding["runtime_profile"],
        "phase module/profile binding differs",
    )
    require(
        r["exact_serving_calls"] == r["provider_calls"] == r["validation_test_queries"] == 0
        and r["data_index_before_after"]
        and r["cleanup_verified"],
        "scope/integrity gate differs",
    )
    if not fixture:
        require(
            r["split_sha256"] == binding["split_manifest_sha256"]
            and r["graph"] == binding["graph"]
            and r["plan_sha256"] == binding["plan_sha256"]
            and r["serving_source_sha256"] == binding["serving_source_sha256"],
            "study binding differs",
        )
        require(
            r["limits"]["memory_limit"] == 48 * 1024**3
            and len(set(map(tuple, r["limits"]["cores"]))) == 4,
            "resource contract differs",
        )
    cpus = json.loads((folder / "allowed-cpus.json").read_text())
    require(len(cpus) == len(set(cpus)) == 4 and cpus == sorted(cpus), "CPU inventory differs")
    if not fixture:
        require(cpus == r["limits"]["cpus"], "allocation CPU mask differs")
    return r, cpus


def references(folder, qs, prior, fixture):
    truth = {}
    cost = 0
    for r in lines(folder / "exact-reference.jsonl"):
        qid = r["id"]
        require(
            qid in qs
            and qid not in truth
            and r["filter"] == threshold(qs[qid])
            and r["reference_query_ns"] > 0,
            "offline truth inventory/timer differs",
        )
        if prior is not None:
            require(matches(r["output"], prior[qid]["exact"]), "offline reference changed")
        truth[qid] = r["output"]
        cost += r["reference_query_ns"]
    require(set(truth) == set(qs), "missing offline truth")
    c = json.loads((folder / "offline-reference-cost.json").read_text())
    require(
        c
        == {
            "queries": len(qs),
            "query_ns": cost,
            "included_in_serving": False,
            "exact_readers_closed_before_approximate": True,
        },
        "scoring/serving separation differs",
    )
    if not fixture:
        for t in FILTERS:
            scans = scan_nodes(json.loads((folder / f"exact-plan-{t}.json").read_text()))
            require(
                len(scans) == 1
                and scans[0]["Node Type"] == "Seq Scan"
                and scans[0]["Relation Name"] == "reviews",
                "exact path differs",
            )
    return truth


def verify(results, kit, *, fixture=False):
    for line in (kit / "SHA256SUMS").read_text().splitlines():
        h, name = line.split("  ", 1)
        require(Path(name).name == name and sha(kit / name) == h, "kit digest differs")
    b = json.loads((kit / "binding.json").read_text())
    require(
        b["timing_module_sha256"] != b["work_module_sha256"], "observer contaminated timing module"
    )
    host = json.loads((results / "host-exit.json").read_text())
    require(host["exit_code"] == 0, "failed host return must be preserved, not promoted")
    queries = list(lines(kit / "queries.jsonl"))
    qs = {q["id"]: q for q in queries}
    if not fixture:
        import re

        require(
            len(qs) == len(queries) == 3150 and all(len(q["vector"]) == 768 for q in queries),
            "development dimensions/count differs",
        )
        ids = {int(re.fullmatch(r"reviews-clean-v(\d+)-(?:unfiltered|votes\d+)", q)[1]) for q in qs}
        require(
            ids == set(b["development_source_indices"]) and len(ids) == 450,
            "non-development query input",
        )
    cases_per_filter = len(queries) // 7
    require(
        all(sum(threshold(q) == t for q in queries) == cases_per_filter for t in FILTERS),
        "seven-condition coverage differs",
    )
    entries = load_programs(kit)
    prior = None if fixture else {r["id"]: r for r in lines(kit / "prior-references.jsonl")}
    expected = None if fixture else {r["id"]: r for r in lines(kit / "expected.jsonl")}
    tr, cpus = phase_receipt(results / "timing", "timing", b, fixture)
    wr, wcpus = phase_receipt(results / "work", "work", b, fixture)
    require(cpus == wcpus and tr["job_id"] == wr["job_id"] == host["job_id"], "job/CPU set changed")
    truth = references(results / "timing", qs, prior, fixture)
    wt = references(results / "work", qs, prior, fixture)
    require(all(matches(truth[q], wt[q]) for q in qs), "phase truths differ")
    eligibility = json.loads((results / "timing/eligibility.json").read_text())
    require(
        eligibility == json.loads((results / "work/eligibility.json").read_text())
        and set(eligibility) == set(map(str, FILTERS)),
        "eligibility scope differs",
    )
    eligible = {int(t): set(ids) for t, ids in eligibility.items()}
    quality = {}
    reached = 0
    partial = 0
    losses = collections.Counter()
    stops = collections.defaultdict(collections.Counter)
    quality_ids = set()
    stream = iter(lines(results / "timing/quality.jsonl"))
    names = tuple(n for n in ARMS if n != "native640")
    for t in FILTERS:
        cases = [q for q in queries if threshold(q) == t]
        if not fixture:
            scans = scan_nodes(json.loads((results / "timing" / f"ann-plan-{t}.json").read_text()))
            require(
                len(scans) == 1 and scans[0].get("Index Name") == "reviews_hnsw",
                "approximate plan differs",
            )
        for j, q in enumerate(cases):
            r = next(stream, None)
            qid = q["id"]
            require(
                r is not None
                and r["id"] == qid
                and r["filter"] == t
                and qid not in quality_ids
                and set(r["results"]) == set(ARMS),
                "quality row inventory/order differs",
            )
            quality_ids.add(qid)
            obs = r["checkpoints"]
            require(
                [o["checkpoint"] for o in obs] == sorted(set(o["checkpoint"] for o in obs))
                and all(o["checkpoint"] in (16, 32, 64) for o in obs),
                "reached prefix inventory differs",
            )
            if expected is not None:

                def strip(rows):
                    return [{k: v for k, v in o.items() if k != "collection_ns"} for o in rows]

                require(
                    strip(obs) == strip(expected[qid]["checkpoints"]),
                    "M0 canonical features differ",
                )
            require(
                set(r["prefixes"]) == {str(o["checkpoint"]) for o in obs},
                "missing actual prefix label",
            )
            native = r["results"]["native640"]
            native_score = validate(value(native), q, eligible[t], truth[qid])
            require(
                native["checkpoint"] == 0
                and native["audit"] is None
                and abs(native["recall"] - native_score) < 1e-12,
                "native label differs",
            )
            if expected is not None:
                require(
                    matches(native["output"], expected[qid]["results"]["native640"]["output"]),
                    "native bridge differs from frozen M0",
                )
            for o in obs:
                proof = r["prefixes"][str(o["checkpoint"])]
                score = __import__("support").valid(proof["output"], q, eligible[t], truth[qid])
                require(
                    proof["returned_count"] == len(proof["output"])
                    and abs(score - proof["recall"]) < 1e-12,
                    "actual prefix recall label differs",
                )
                require(
                    len(proof["output"]) == min(10, o["qualifying_count"]),
                    "forced output does not match retained eligible prefix",
                )
                if expected is not None:
                    old = expected[qid]["prefixes"][str(o["checkpoint"])]
                    require(
                        matches(proof["output"], old["output"])
                        and abs(score - old["recall"]) < 1e-12,
                        "actual prefix differs from verified M1 label",
                    )
                reached += 1
                partial += o["qualifying_count"] < 10
            for name, arm in ARMS.items():
                v = r["results"][name]
                score = validate(value(v), q, eligible[t], truth[qid])
                if arm is not None and arm >= 20:
                    wanted = expected_program(entries[arm], t, obs, v["output"], v["audit"])
                elif arm is not None and arm >= 7:
                    wanted = choose(entries[arm + 13], filter_name(t), obs)
                else:
                    wanted = 0
                require(
                    v["checkpoint"] == wanted
                    and abs(v["recall"] - score) < 1e-12
                    and matches(
                        v["output"],
                        r["prefixes"][str(wanted)]["output"] if wanted else native["output"],
                    ),
                    "compiled first-stop/output/recall differs",
                )
                losses[name] += score < native_score - 1e-12
                stops[name][str(wanted)] += 1
                quality[qid, name] = v
            require(
                matches(r["native_after"]["output"], native["output"]),
                "native after role changes differs",
            )
            validate(r["native_after"], q, eligible[t], truth[qid])
            rotation = j % len(names)
            require(
                r["native_predecessor"] == (names[rotation:] + names[:rotation])[-1],
                "native bridge predecessor differs",
            )
    require(next(stream, None) is None and set(qs) == quality_ids, "extra/missing quality rows")
    if not fixture:
        require(reached == 9436 and partial == 1496, "frozen full/partial prefix coverage differs")
    require(not any(losses.values()), "nominee/control quality regression")
    if not fixture:
        from m5_design import EXPECTED_STOPS

        for name, counts in EXPECTED_STOPS.items():
            for t in FILTERS:
                require(
                    sum(
                        bool(quality[q["id"], name]["checkpoint"])
                        for q in queries
                        if threshold(q) == t
                    )
                    == counts.get(t, 0),
                    "bound nominee stop inventory differs",
                )
    expected_ledger = ledger(len(queries), reached, cases_per_filter)
    require(
        tr["searches"] == expected_ledger["timing"] and wr["searches"] == expected_ledger["work"],
        "phase attempt ledger differs",
    )
    for phase in ("timing", "work"):
        require(
            json.loads((results / phase / "attempts.json").read_text()) == expected_ledger[phase],
            "persisted phase attempt snapshot differs",
        )
    assignments = {}
    backends = {}
    visits = collections.Counter()
    assignment_stream = iter(lines(results / "timing/assignments.jsonl"))
    for ti, t in enumerate(FILTERS):
        for group in range(len(GROUPS)):
            for block, (cycle, rotation) in enumerate(blocks(group)):
                for reader in range(4):
                    a = next(assignment_stream, None)
                    require(a is not None, "missing reader assignment")
                    cpu = cpu_for(reader, ti, group, cpus)
                    name = role(group, reader, rotation)
                    require(
                        (
                            a["filter"],
                            a["group"],
                            a["block"],
                            a["cycle"],
                            a["rotation"],
                            a["reader"],
                            a["family"],
                            a["cpu"],
                        )
                        == (t, group, block, cycle, rotation, reader, name, cpu),
                        "role/CPU assignment differs",
                    )
                    require(
                        a["affinity_after"] == [cpu]
                        and set(a["affinity_before"]) <= set(cpus)
                        and type(a["pid"]) is int
                        and a["pid"] > 0,
                        "invalid PID/affinity",
                    )
                    key = t, group, reader
                    if key in backends:
                        require(backends[key] == a["pid"], "role moved between processes")
                    else:
                        backends[key] = a["pid"]
                    visits[t, group, reader, name] += 1
                    assignments[t, group, block, reader] = a
            require(len({backends[t, group, r] for r in range(4)}) == 4, "backend PID aliasing")
            require(
                all(visits[t, group, r, n] == 2 for r in range(4) for n in GROUPS[group]),
                "missing within-backend role crossover",
            )
    require(
        next(assignment_stream, None) is None
        and len(assignments) == 7 * 4 * 2 * sum(map(len, GROUPS)),
        "assignment inventory differs",
    )
    totals = collections.defaultdict(lambda: [0, 0])
    cpu_counts = collections.Counter()
    for filename, warmup in (("timing.jsonl", False), ("warmup.jsonl", True)):
        s = iter(lines(results / "timing" / filename))
        count = 0
        for ti, t in enumerate(FILTERS):
            cases = [q for q in queries if threshold(q) == t]
            for group in range(len(GROUPS)):
                for block, (cycle, rotation) in enumerate(blocks(group)):
                    rows = ordered(cases, group, rotation, cycle)
                    sequence = (
                        (
                            (q, reader, None)
                            for reader in (range(4) if cycle == 0 else reversed(range(4)))
                            for q in rows[:10]
                        )
                        if warmup
                        else (
                            (q, reader, (position, order))
                            for j, q in enumerate(rows)
                            for order in (
                                reader_order(
                                    j if cycle == 0 else len(rows) - 1 - j,
                                    cycle,
                                    rotation,
                                    ti,
                                    group,
                                ),
                            )
                            for position, reader in enumerate(order)
                        )
                    )
                    for q, reader, schedule in sequence:
                        r = next(s, None)
                        require(r is not None, "missing timed/warmup request")
                        count += 1
                        name = role(group, reader, rotation)
                        a = assignments[t, group, block, reader]
                        require(
                            (
                                r["id"],
                                r["filter"],
                                r["group"],
                                r["block"],
                                r["cycle"],
                                r["rotation"],
                                r["reader"],
                                r["family"],
                                r["pid"],
                                r["cpu"],
                            )
                            == (
                                q["id"],
                                t,
                                group,
                                block,
                                cycle,
                                rotation,
                                reader,
                                name,
                                a["pid"],
                                a["cpu"],
                            ),
                            "request order/reader/CPU differs",
                        )
                        fields = set(KEYS) | {
                            "id",
                            "filter",
                            "group",
                            "block",
                            "cycle",
                            "rotation",
                            "reader",
                            "family",
                            "pid",
                            "cpu",
                        }
                        if not warmup:
                            position, order = schedule
                            fields |= {"order", "position", "predecessor"}
                            require(
                                r["order"] == order
                                and r["position"] == position
                                and r["predecessor"] == (order[position - 1] if position else None),
                                "mirrored Williams order differs",
                            )
                        require(
                            set(r) == fields, "counters/audit/fallback leaked into primary timing"
                        )
                        require(
                            matches(r["output"], quality[q["id"], name]["output"]),
                            "timed output differs from qualification",
                        )
                        validate(value(r), q, eligible[t], truth[q["id"]])
                        if not warmup:
                            totals[group, t, name][0] += r["request_ns"]
                            totals[group, t, name][1] += 1
                            cpu_counts[group, t, name, r["cpu"]] += 1
        require(
            next(s, None) is None
            and count == expected_ledger["timing"]["warmup_ann" if warmup else "timed_ann"],
            "timing/warmup ledger differs",
        )
    require(
        set(cpu_counts.values()) == {cases_per_filter * 2}
        and len(cpu_counts) == sum(map(len, GROUPS)) * 7 * 4,
        "per-family CPU exposure differs",
    )
    work_counts = {}
    native_reference = (
        None
        if fixture
        else {r["id"]: r["counts"] for r in lines(kit / "native-work-reference.jsonl")}
    )
    s = iter(lines(results / "work/work.jsonl"))
    work_pids = {}
    for ti, t in enumerate(FILTERS):
        cases = [q for q in queries if threshold(q) == t]
        cpu = cpus[ti % 4]
        for name in ARMS:
            for q in cases:
                r = next(s, None)
                require(
                    r is not None and (r["id"], r["filter"], r["family"]) == (q["id"], t, name),
                    "work record inventory differs",
                )
                require(
                    set(r)
                    == set(KEYS) | {"id", "filter", "family", "checkpoint", "recall", "counts"},
                    "work record schema differs",
                )
                target = quality[q["id"], name]
                c = r["counts"]
                score = validate(value(r), q, eligible[t], wt[q["id"]])
                require(
                    r["checkpoint"] == target["checkpoint"]
                    and matches(r["output"], target["output"])
                    and abs(score - r["recall"]) < 1e-12
                    and abs(score - target["recall"]) < 1e-12,
                    "observer prefix/output parity differs",
                )
                require(
                    set(c) == set(COUNTERS) | {"pid", "start_cpu", "end_cpu"}
                    and c["start_cpu"] == c["end_cpu"] == cpu
                    and all(type(c[k]) is int and c[k] >= 0 for k in COUNTERS),
                    "work CPU/counter schema differs",
                )
                require(
                    c["vector_calls"] > 0
                    and c["layer0_queue_pops"] > 0
                    and c["feature_passes"] <= 3,
                    "work counter bounds differ",
                )
                if t in work_pids:
                    require(work_pids[t] == c["pid"], "work role moved between processes")
                else:
                    work_pids[t] = c["pid"]
                if name in ("native640", "empty", "decision_continue"):
                    require(
                        c["feature_passes"] == c["membership_probes"] == 0,
                        "unneeded heap feature work on bypass/decision-only path",
                    )
                if ARMS[name] is not None and ARMS[name] >= 20:
                    require(
                        c["feature_passes"]
                        == sum(bool(f["mask"] & COUNT) for f in target["audit"]["frames"]),
                        "feature pass mask differs",
                    )
                    if c["feature_passes"] == 0:
                        require(c["membership_probes"] == 0, "unrequested membership feature work")
                work_counts[q["id"], name] = c
                if name in CONTINUE_FAMILIES:
                    require(
                        all(c[k] == work_counts[q["id"], "native640"][k] for k in GRAPH_COUNTERS),
                        "continue/native graph work differs",
                    )
                if name == "native640" and native_reference is not None:
                    require(
                        all(c[k] == native_reference[q["id"]][k] for k in GRAPH_COUNTERS),
                        "native graph bridge differs from verified M0",
                    )
    require(
        next(s, None) is None and len(work_counts) == expected_ledger["work"]["work_ann"],
        "work attempt inventory differs",
    )
    setup = json.loads((results / "timing/setup.json").read_text())
    require(
        len(setup) == 7 * 2 * sum(map(len, GROUPS))
        and sum(r["warmups"] for r in setup) == expected_ledger["timing"]["warmup_ann"],
        "setup/warmup inventory differs",
    )
    metrics = {
        str(g): {
            name: {
                "equal_scalar_mean_ms": sum(
                    totals[g, t, name][0] / totals[g, t, name][1] for t in FILTERS if t >= 0
                )
                / 6
                / 1e6,
                "per_filter_mean_ms": {
                    str(t): totals[g, t, name][0] / totals[g, t, name][1] / 1e6 for t in FILTERS
                },
            }
            for name in group
        }
        for g, group in enumerate(GROUPS)
    }
    report = {
        "status": "M5_fixture_return_verified_not_study_evidence"
        if fixture
        else "M5_nominee_return_verified",
        "job_id": host["job_id"],
        "runtime_profile": b["runtime_profile"],
        "groups": len(qs) // 7,
        "conditions": 7,
        "program_bindings": 5,
        "quality_family_results": len(quality),
        "prefix_labels": reached,
        "partial_prefix_labels": partial,
        "full_prefix_labels": reached - partial,
        "timed_requests": expected_ledger["timing"]["timed_ann"],
        "warmups": expected_ledger["timing"]["warmup_ann"],
        "assignments": len(assignments),
        "work_queries": len(work_counts),
        "attempts": expected_ledger,
        "exact_serving_calls": 0,
        "offline_exact_queries": 2 * len(qs),
        "quality_loss_cases": dict(losses),
        "first_stop_counts": {n: dict(c) for n, c in stops.items()},
        "timing_block_metrics": metrics,
        "native_and_continue_graph_work_verified": True,
        "native_work_bridge_to_M0_verified": not fixture,
        "feature_pass_masks_verified": True,
        "source_module_output_and_frozen_prefix_parity_verified": True,
        "no_final_policy_promotion": True,
        "cost_interpretation": "Full-request nominee costs, conditional on one development "
        "allocation; no held-out or allocation-level claim.",
        "scheduler_gate": "independent sacct COMPLETED0:0 still required",
        "validation_test_outcomes_opened": False,
        "provider_calls": 0,
    }
    write(results / "local-verification.json", report)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--results", type=Path, required=True)
    p.add_argument("--kit", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(verify(a.results, a.kit), indent=2))
