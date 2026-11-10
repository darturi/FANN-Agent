"""Data-only independent replay and prespecified B1b frontier gates."""

import argparse
import math
import random
from collections import defaultdict
from pathlib import Path

from ef_common import (
    CELLS,
    COUNTS,
    CRITERIA,
    FILTERS,
    OPERATIONS,
    REGIMES,
    SEED,
    digest,
    lines,
    read,
    safe_file,
    save,
    sha,
    verify,
)
from ef_interface import context
from ef_measure import schedule


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value, positive=False):
    require(
        type(value) in (float, int)
        and math.isfinite(value)
        and (value > 0 if positive else value >= 0),
        "Invalid duration/value",
    )


def near(a, b):
    require(abs(a - b) <= 1e-9, "Raw timer arithmetic differs")


def unique(rows, key):
    result = {}
    for row in rows:
        k = key(row)
        require(k not in result, "Duplicate raw identity")
        result[k] = row
    return result


def score_result(value, truth, query, eligibility):
    ids, distances = value["ids"], value["distances"]
    require(len(ids) == len(distances) and len(ids) <= 10, "Malformed ANN output")
    require(
        all(type(i) is int and 0 <= i < len(eligibility["votes"]) for i in ids),
        "Unknown analysis ID",
    )
    require(
        all(
            type(d) in (float, int) and math.isfinite(d) and -1e-6 <= d <= 2.000001
            for d in distances
        ),
        "Invalid cosine distance",
    )
    require(distances == sorted(distances), "ANN output is not distance ordered")
    predicate = query.get("filter")
    votes = eligibility["votes"]
    violations = sum(
        predicate is not None and (votes[i] is None or votes[i] < predicate["value"])
        for i in set(ids)
    )
    strict, ties, k = set(truth["truth_strict"]), set(truth["truth_ties"]), truth["truth_k"]
    require(k == 10 and len(strict) <= k and not strict & ties, "Malformed exact truth")
    recall = (len(set(ids) & strict) + min(k - len(strict), len(set(ids) & ties))) / k
    duplicates = len(ids) - len(set(ids))
    expected = {
        "ids": ids,
        "distances": distances,
        "recall": recall,
        "valid": not duplicates and not violations and len(ids) == 10,
        "returned_count": len(ids),
        "duplicate_count": duplicates,
        "predicate_violation_count": violations,
    }
    require(value == expected, "Output membership/recall/validity differs from independent score")


def audit_settings(audit, cell, origin, source_settings):
    roles = (
        {"320": 320, "640": 640}
        if cell.startswith("wrapped")
        else {"plain": 640 if cell == "original640" else int(source_settings["hnsw.ef_search"])}
    )
    require(set(audit) == set(roles), "Reader audit coverage differs")
    for role, effort in roles.items():
        row = audit[role]
        require(row["origin"] == origin, "Origin manifest was mutated")
        expected = {**origin, "settings": {**source_settings, "hnsw.ef_search": str(effort)}}
        require(row["effective"] == expected, "Effective binding changed more than effort")
        if cell.startswith("wrapped"):
            require(
                row["origin_sha256"] == digest(origin)
                and row["effective_sha256"] == digest(expected),
                "Binding fingerprint differs",
            )
        expected_values = {**expected["settings"], "statement_timeout": "30000"}
        require(
            {k: v["value"] for k, v in row["settings"].items()} == expected_values,
            "Actual setting isolation failed",
        )
        require(
            all(v["source"] == "session" for v in row["settings"].values()),
            "Settings were not session bound",
        )


def validate_block(folder, package, cfg, block, items, eligibility, pins):
    status = read(folder / "status.json")
    wanted = {
        "status": "complete",
        "block": block,
        "provider_calls": 0,
        "confirmation_queries": 0,
        "new_fits": 0,
        "cases": 600,
        "vectors": 200,
        "backend_searches": COUNTS["searches_per_block"],
        "operations": OPERATIONS,
        "control_installations": 0,
        "index_and_module_after_verified": True,
        "retained_executions": 38400,
        "discarded_warmups": 9600,
        "slots": 9600,
        "conditioning_searches": 19200,
        "reader_connections": 14416,
    }
    require(all(status.get(k) == v for k, v in wanted.items()), "Status/accounting differs")
    finite(status["elapsed_seconds"], positive=True)
    require(status["elapsed_seconds"] <= cfg["maximum_seconds"], "Work deadline exceeded")
    for name in ("job-exit.json", "host-exit.json"):
        require(read(folder / name)["exit_code"] == 0, "Host/runtime/cleanup failure")
    require(
        read(folder / "host-exit.json")["protected_sources_unchanged"] is True,
        "Protected source changed",
    )
    before = read(folder / "protected-source-before.json")
    require(
        before
        == read(folder / "protected-source-after.json")
        == read(folder.parents[1] / "protected-source-before.json"),
        "Source preservation differs",
    )
    source_cfg = read(package / "frozen/experiment.json")
    expected_runtime = {
        "module_sha256": source_cfg["module_sha256"],
        "runtime_profile_hash": "b2974c2c65d40780d207109d9bbd298b2628ea58abde673c0dd479c1a0e52ed3",
        "registry_hash": "fc42b1fb1441518b15123ed30ba2a0d0c96e9c74d4f0727ab9eb391597cdbf37",
        "package_manifest_sha256": sha(package / "manifest.json"),
        "image_sha256": source_cfg["image_sha256"],
    }
    require(
        read(folder / "runtime-identity.json") == expected_runtime,
        "Runtime/module/image identity differs",
    )
    require(
        read(folder / "database-identity.json") == read(package / "frozen/source-index.json"),
        "Physical index identity differs",
    )
    lock = read(folder / "LOCK.json")
    required = {
        "status.json",
        "job-exit.json",
        "runtime-identity.json",
        "database-identity.json",
        "qualification.json",
        "shared-initialization.json",
        "host.json",
        "references.jsonl",
        "executions.jsonl",
        "slots.jsonl",
        "conditioning.jsonl",
    }
    require(
        lock["package_manifest_sha256"] == sha(package / "manifest.json")
        and required <= set(lock["files_sha256"]),
        "Raw lock incomplete",
    )
    for name, expected in lock["files_sha256"].items():
        require(sha(safe_file(folder, name)) == expected, "Raw hash differs: " + name)
    init = read(folder / "shared-initialization.json")
    origin = init["origin_manifest"]
    require(origin == read(package / "origin-source.json"), "Origin metadata/index binding differs")
    require(
        origin["settings"] == cfg["source_settings"]
        and init["eligibility_sha256"] == sha(package / "eligibility.json"),
        "Snapshot/source identity differs",
    )
    require(
        init["study_reference_effort"] == 640
        and init["source_effort"] == int(cfg["source_settings"]["hnsw.ef_search"]),
        "Study/source baseline conflated",
    )
    qualification = read(folder / "qualification.json")
    require(
        qualification["status"] == "passed"
        and qualification["backend_searches"] == 36
        and len(qualification["cases"]) == 3,
        "Native qualification incomplete",
    )
    fixture_ids = [
        next(i["query"]["id"] for i in items if i["query"]["id"].endswith("-" + f)) for f in FILTERS
    ]
    for row, qid in zip(qualification["cases"], fixture_ids):
        require(
            row["query_id"] == qid and row["searches"] == 12 and row["status"] == "passed",
            "Qualification fixture differs",
        )
        require(
            row["sql_abort_rolled_back"]
            and row["closed_session_rejected_without_search"]
            and row["explicit_new_session_recovered"],
            "Error/recovery qualification failed",
        )
        require(
            row["original640"] == pins[qid]["original640"]
            and row["truth"] == {k: pins[qid][k] for k in row["truth"]},
            "Qualification original640/truth changed",
        )
        require(
            [o["level"] for o in row["outputs"]] == [640, 320, 640, 320, 640, 640],
            "Effort alternation differs",
        )
        expected_lower = row["outputs"][1]["result"]
        require(
            all(
                o["result"] == (row["original640"] if o["level"] == 640 else expected_lower)
                for o in row["outputs"]
            ),
            "Alternating output isolation failed",
        )
        require(
            row["source"]
            == (expected_lower if init["source_effort"] == 320 else row["original640"]),
            "Source comparator differs",
        )
        require(
            set(row["plans"]) == {"original640", "source", "320", "640"},
            "Native plan coverage differs",
        )
        for plan in row["plans"].values():
            encoded_plan = __import__("json").dumps(plan)
            require(
                '"Index Name": "reviews_hnsw"' in encoded_plan
                and '"Node Type": "Index Scan"' in encoded_plan,
                "Native HNSW plan missing",
            )
        for phase in ("before", "after"):
            audit = row["settings"][phase]
            audit_settings(audit["pool"], "wrapped640", origin, cfg["source_settings"])
            for role in ("source", "original640"):
                effective = {
                    **origin,
                    "settings": {
                        **origin["settings"],
                        "hnsw.ef_search": str(init["source_effort"] if role == "source" else 640),
                    },
                }
                audit_settings(
                    {"plain": {"origin": origin, "effective": effective, "settings": audit[role]}},
                    role,
                    origin,
                    cfg["source_settings"],
                )
    refs = unique(lines(folder / "references.jsonl"), lambda r: r["query_id"])
    require(set(refs) == {i["query"]["id"] for i in items}, "Reference coverage differs")
    for item in items:
        q = item["query"]
        ref, pin = refs[q["id"]], pins[q["id"]]
        require(
            ref["group"] == item["group"] and ref["outcomes"]["original640"] == pin["original640"],
            "Pinned original640 output changed",
        )
        require(
            {k: ref[k] for k in ("truth_strict", "truth_ties", "truth_k")}
            == {k: pin[k] for k in ("truth_strict", "truth_ties", "truth_k")},
            "Exact truth changed",
        )
        require(
            set(ref["outcomes"]) == set(CELLS)
            and ref["outcomes"]["wrapped640"] == ref["outcomes"]["original640"],
            "640 output identity differs",
        )
        require(
            ref["outcomes"]["source"]
            == ref["outcomes"]["wrapped320" if init["source_effort"] == 320 else "original640"],
            "Source path output differs",
        )
        for value in ref["outcomes"].values():
            score_result(value, ref, q, eligibility)
    for row in qualification["cases"]:
        require(
            row["outputs"][1]["result"] == refs[row["query_id"]]["outcomes"]["wrapped320"],
            "Qualification320 differs from acquired frontier reference",
        )
    ordered = items.copy()
    random.Random(SEED + block).shuffle(ordered)
    expected_slots = [
        {"query_id": i["query"]["id"], "group": i["group"], "block": block, "slot_index": j, **m}
        for i in ordered
        for j, m in enumerate(schedule(i["query"]["id"], block))
    ]
    slots, executions, conditioning = (
        lines(folder / "slots.jsonl"),
        lines(folder / "executions.jsonl"),
        lines(folder / "conditioning.jsonl"),
    )
    require(
        (len(slots), len(executions), len(conditioning)) == (9600, 48000, 19200),
        "Raw schedule count differs",
    )
    retained = []
    previous_end = -1
    queries = {i["query"]["id"]: i["query"] for i in items}
    for index, (slot, expected) in enumerate(zip(slots, expected_slots)):
        require(all(slot.get(k) == v for k, v in expected.items()), "Slot order/identity differs")
        boundaries = [
            slot[k]
            for k in (
                "conditioning_start_ns",
                "conditioning_end_ns",
                "preparation_start_ns",
                "preparation_end_ns",
                "audit_start_ns",
                "audit_end_ns",
                "cleanup_start_ns",
                "cleanup_end_ns",
            )
        ]
        require(
            all(type(t) is int and t >= 0 for t in boundaries)
            and boundaries == sorted(boundaries)
            and boundaries[0] >= previous_end,
            "Slot phases overlap or run backwards",
        )
        previous_end = boundaries[-1]
        near(slot["preparation_ms"], (boundaries[3] - boundaries[2]) / 1e6)
        audit_settings(slot["audit"], expected["cell"], origin, cfg["source_settings"])
        ref = refs[expected["query_id"]]
        last = boundaries[0]
        for rep, row in enumerate(conditioning[index * 2 : index * 2 + 2]):
            require(
                all(row.get(k) == v for k, v in expected.items()) and row["repetition"] == rep,
                "Conditioning schedule differs",
            )
            require(
                last <= row["start_ns"] < row["end_ns"] <= boundaries[1],
                "Conditioning overlaps activation",
            )
            last = row["end_ns"]
            near(row["outer_ms"], (row["end_ns"] - row["start_ns"]) / 1e6)
            finite(row["sql_ms"], positive=True)
            require(row["result"] == ref["outcomes"]["original640"], "Conditioning output differs")
        last = boundaries[3]
        for rep, row in enumerate(executions[index * 5 : index * 5 + 5]):
            require(
                all(row.get(k) == v for k, v in expected.items()) and row["repetition"] == rep,
                "Execution schedule differs",
            )
            require(
                row["retained"] == (rep != 1)
                and row["regime"] == ("activation" if rep == 0 else "reuse"),
                "Retention/regime differs",
            )
            require(
                last <= row["start_ns"] < row["end_ns"] <= boundaries[4],
                "Execution timing overlaps other phases",
            )
            last = row["end_ns"]
            finite(row["sql_ms"], positive=True)
            near(row["query_outer_ms"], (row["end_ns"] - row["start_ns"]) / 1e6)
            near(row["preparation_ms"], slot["preparation_ms"] if rep == 0 else 0.0)
            near(row["outer_ms"], row["query_outer_ms"] + row["preparation_ms"])
            finite(row["outer_ms"], positive=True)
            require(
                row["sql_ms"] <= row["query_outer_ms"] + 1e-6,
                "Backend timer exceeds containing query timer",
            )
            require(
                row["result"] == ref["outcomes"][expected["cell"]],
                "Timed output differs from actual reference",
            )
            wrapped = expected["cell"].startswith("wrapped")
            level = (
                320
                if expected["cell"] == "wrapped320"
                else 640
                if expected["cell"] != "source"
                else init["source_effort"]
            )
            route = {
                "requested_effort": level if wrapped else None,
                "effective_effort": level,
                "context": context(queries[expected["query_id"]]) if wrapped else None,
                "fallback_to640": False,
            }
            require(row["route"] == route, "Effort request/actual predicate route differs")
            if row["retained"]:
                retained.append(row)
    ref_identity = {q: {k: v for k, v in ref.items() if k != "outer_ms"} for q, ref in refs.items()}
    return (
        retained,
        ref_identity,
        lock["files_sha256"],
        {"status": status, "shared_initialization": init, "host": read(folder / "host.json")},
    )


def contrasts(rows, treatment, baseline=None):
    grouped = defaultdict(dict)
    for row in rows:
        grouped[(row["block"], row["query_id"], row["round"], row["repetition"])][
            (row["cell"], row["label"])
        ] = row
    result = []
    for members in grouped.values():
        a = (
            [members[(treatment, "b")]]
            if baseline is None
            else [members[(treatment, label)] for label in ("a", "b")]
        )
        b = (
            [members[(treatment, "a")]]
            if baseline is None
            else [members[(baseline, label)] for label in ("a", "b")]
        )
        require(
            all(x["result"] == a[0]["result"] for x in a)
            and all(x["result"] == b[0]["result"] for x in b),
            "Identical labels changed output",
        )

        def mean(values, key):
            return sum(v[key] for v in values) / len(values)

        first = a[0]
        result.append(
            {
                "group": first["group"],
                "query_id": first["query_id"],
                "stratum": first["query_id"].rsplit("-", 1)[1],
                "block": first["block"],
                "regime": first["regime"],
                "treatment_ms": mean(a, "outer_ms"),
                "baseline_ms": mean(b, "outer_ms"),
                "sql_gap_ms": mean(a, "sql_ms") - mean(b, "sql_ms"),
                "recall_delta": a[0]["result"]["recall"] - b[0]["result"]["recall"],
                "reference_recall": b[0]["result"]["recall"],
                "treatment_recall": a[0]["result"]["recall"],
                "all_valid": all(v["result"]["valid"] for v in a + b),
            }
        )
    return result


def summary(rows):
    import numpy as np

    grouped = defaultdict(list)
    for row in rows:
        grouped[row["group"]].append(row)
    require(len(grouped) == 200, "Expected200 independent exposed vectors")

    def columns(r):
        return [
            r["treatment_ms"] - r["baseline_ms"],
            math.log(r["treatment_ms"] / r["baseline_ms"]),
            r["recall_delta"],
            r["sql_gap_ms"],
        ]

    matrix = np.asarray(
        [np.mean([columns(r) for r in grouped[g]], axis=0) for g in sorted(grouped)]
    )
    rng = np.random.default_rng(CRITERIA["bootstrap_seed"])
    boot = np.empty((CRITERIA["bootstrap_samples"], 4))
    for offset in range(0, len(boot), 128):
        count = min(128, len(boot) - offset)
        boot[offset : offset + count] = matrix[
            rng.integers(0, len(matrix), size=(count, len(matrix)))
        ].mean(axis=1)
    ci = np.quantile(boot, [0.025, 0.975], axis=0)

    def mean(key):
        return float(np.mean([r[key] for r in rows]))

    return {
        "observations": len(rows),
        "independent_vectors": len(grouped),
        "gap_ms": float(matrix[:, 0].mean()),
        "gap_ci95": ci[:, 0].tolist(),
        "log_ratio": float(matrix[:, 1].mean()),
        "log_ratio_ci95": ci[:, 1].tolist(),
        "recall_delta": float(matrix[:, 2].mean()),
        "recall_delta_ci95": ci[:, 2].tolist(),
        "sql_gap_ms": float(matrix[:, 3].mean()),
        "sql_gap_ci95": ci[:, 3].tolist(),
        "baseline_ms": mean("baseline_ms"),
        "treatment_ms": mean("treatment_ms"),
        "reference_recall": mean("reference_recall"),
        "treatment_recall": mean("treatment_recall"),
        "all_valid": all(r["all_valid"] for r in rows),
        "block_gap_ms": {
            str(b): float(
                np.mean([r["treatment_ms"] - r["baseline_ms"] for r in rows if r["block"] == b])
            )
            for b in range(2)
        },
    }


def grouped_report(rows):
    return {
        regime: {
            f: summary(
                [r for r in rows if r["regime"] == regime and (f == "overall" or r["stratum"] == f)]
            )
            for f in ["overall", *FILTERS]
        }
        for regime in REGIMES
    }


def gates(aa, comparisons):
    require(set(aa) == set(CELLS), "Missing A/A cells")
    precision, frontier = {}, {}
    for regime in REGIMES:
        failures = []
        for cell in CELLS:
            require(
                set(aa[cell]) == set(REGIMES) and set(aa[cell][regime]) == {"overall", *FILTERS},
                "Missing A/A regime/filter",
            )
            for f, stat in aa[cell][regime].items():
                for field, bound in (
                    ("gap_ci95", CRITERIA["aa_absolute_ms"]),
                    ("log_ratio_ci95", math.log(CRITERIA["aa_ratio"])),
                ):
                    if stat[field][0] < -bound or stat[field][1] > bound:
                        failures.append(cell + "/" + f + "/" + field)
        precision[regime] = {
            "status": "pass" if not failures else "measurement_inconclusive",
            "failures": failures,
            "interval_checks": 32,
        }
        frontier[regime] = {}
        for f in FILTERS:
            overhead = comparisons["wrapped640_vs_original640"][regime][f]
            lower = comparisons["wrapped320_vs_original640"][regime][f]
            checks = {
                "precision": not failures,
                "wrapper_overhead": overhead["gap_ci95"][1]
                <= CRITERIA["wrapper_maximum_overhead_ms"]
                and overhead["log_ratio_ci95"][1] <= math.log(CRITERIA["wrapper_maximum_ratio"]),
                "complete_valid_top10": lower["all_valid"],
                "native_floor": lower["reference_recall"] >= CRITERIA["minimum_reference_recall"],
                "development_recall": lower["recall_delta_ci95"][0]
                >= -CRITERIA["development_recall_reserve"],
                "minimum_net_benefit": lower["gap_ci95"][1] <= -CRITERIA["minimum_saving_ms"]
                and lower["log_ratio_ci95"][1] <= math.log(CRITERIA["maximum_ratio_for_benefit"]),
                "saving_both_blocks": all(g < 0 for g in lower["block_gap_ms"].values()),
            }
            frontier[regime][f] = {
                "supported": all(checks.values()),
                "checks": checks,
                "final_margin_diagnostic_only": lower["recall_delta_ci95"][0]
                >= -CRITERIA["final_recall_margin_diagnostic_only"],
            }
    supported = [
        regime + "/" + f
        for regime in REGIMES
        for f, row in frontier[regime].items()
        if row["supported"]
    ]
    status = (
        "supported_frontier_for_scoped_B1c_design"
        if supported
        else "measurement_inconclusive"
        if any(p["failures"] for p in precision.values())
        else "closed_negative_bounded_frontier"
    )
    return {
        "status": status,
        "aa": precision,
        "frontier": frontier,
        "supported_context_regimes": supported,
        "router_selected": False,
        "activation_qualified": any(x.startswith("activation/") for x in supported),
        "canonical_acceptance_established": False,
        "M1": False,
        "M2": False,
        "M3": False,
    }


def analyze(campaign, package, output):
    campaign, package, output = map(Path, (campaign, package, output))
    cfg = verify(package)
    items = lines(package / "frozen/inputs/queries.jsonl")
    pins, eligibility = read(package / "baseline-results.json"), read(package / "eligibility.json")
    rows, hashes, metadata, previous = [], {}, {}, None
    for block in range(2):
        folder = campaign / "blocks" / ("block-" + str(block))
        retained, refs, raw, meta = validate_block(
            folder, package, cfg, block, items, eligibility, pins
        )
        require(
            previous is None or previous == refs, "Native effort references changed across blocks"
        )
        previous = refs
        rows.extend(retained)
        hashes.update({f"blocks/block-{block}/" + n: h for n, h in raw.items()})
        metadata[str(block)] = meta
    aa = {cell: grouped_report(contrasts(rows, cell)) for cell in CELLS}
    comparisons = {
        cell + "_vs_original640": grouped_report(contrasts(rows, cell, "original640"))
        for cell in CELLS
        if cell != "original640"
    }
    result = {
        "version": cfg["version"],
        "campaign": campaign.name,
        "package_manifest_sha256": sha(package / "manifest.json"),
        "gate": gates(aa, comparisons),
        "aa": aa,
        "comparisons": comparisons,
        "blocks": metadata,
        "counts": COUNTS,
        "criteria": CRITERIA,
        "scope": cfg["measurement_scope"],
        "raw_files_sha256": hashes,
        "provider_calls": 0,
        "confirmation_queries": 0,
        "new_fits": 0,
        "pointwise_intervals": True,
        "independent_confirmation": False,
        "original_execution_retained": True,
    }
    output.mkdir(parents=True, exist_ok=True)
    save(output / "performance.json", result)
    report = [
        "B1b native-effort frontier: " + result["gate"]["status"],
        "Development evidence only; original execution retained; no router fitted.",
        "Supported context/regimes: " + repr(result["gate"]["supported_context_regimes"]),
        "Source effort="
        + cfg["source_settings"]["hnsw.ef_search"]
        + "; study reference=640; default metadata in qualification raw data.",
    ]
    for regime in REGIMES:
        report.append(regime + " A/A: " + result["gate"]["aa"][regime]["status"])
        for f in ["overall", *FILTERS]:
            stat = comparisons["wrapped320_vs_original640"][regime][f]
            report.append(
                f"{regime}/{f}: outer gap {stat['gap_ms']:.6f}ms CI{stat['gap_ci95']}; "
                f"recall delta CI{stat['recall_delta_ci95']}; full top10 {stat['all_valid']}"
            )
    with (output / "report.txt").open("x") as handle:
        handle.write("\n".join(report) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign", type=Path)
    parser.add_argument("package", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.campaign, args.package, args.output)
