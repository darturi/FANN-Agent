"""Strict independent returned-data replay; no native operations, providers or fits."""

import argparse
import math
from collections import Counter
from pathlib import Path

from pa_common import (
    CELLS,
    OPERATIONS,
    PROFILE_SHA,
    SQL_CAPS,
    campaign_identity,
    digest,
    effective,
    lines,
    parity,
    read,
    safe_file,
    save,
    sha,
    verify,
)
from pa_measure import equivalent, preview_decision, quality_report
from pa_metadata import validate_catalog, validate_charge, validate_packet
from pa_settings import memory_proof, validate_build_settings, validate_phase
from pa_stats import contrasts, require, score_result, summary

REGISTRY = "fc42b1fb1441518b15123ed30ba2a0d0c96e9c74d4f0727ab9eb391597cdbf37"


def expected_events(items, order, outcome):
    """Derive exact operation/request/reader/schedule order independently of raw rows."""
    first = items[0]["query"]["id"]
    a = "initial-native-reference"
    b = "qualification-partial-old"
    aa = "native-reference"
    bb = "partial-reference"
    events = [("qualification_exact", first, a, {})]
    for step, c, r in [
        (1, "native640", a),
        (2, "partial640", b),
        (3, "native640", a),
        (4, "partial640", b),
        (5, "partial640", bb),
    ]:
        events.append(("qualification_" + c, first, r, dict(step=step)))
    events.append(("qualification_exact", first, aa, {}))
    for step, c, r in [(6, "native640", aa), (7, "native640", aa), (8, "partial640", bb)]:
        events.append(("qualification_" + c, first, r, dict(step=step)))
    main = {"native640": aa, "partial640": bb}
    for n, qid in enumerate(order["preview_order"]):
        for pos, c in enumerate(CELLS if n % 2 == 0 else CELLS[::-1]):
            events.append(
                ("preview_conditioning", qid, main[c], dict(preview_index=n, part="conditioning"))
            )
        for c in CELLS:
            events.append(("preview_warmup", qid, main[c], dict(preview_index=n, part="warmup")))
        for pos, c in enumerate(
            ["native640", "partial640", "partial640", "native640"]
            if n % 2 == 0
            else ["partial640", "native640", "native640", "partial640"]
        ):
            events.append(
                (
                    "preview_measurement",
                    qid,
                    main[c],
                    dict(preview_index=n, part="retained", preview_position=pos),
                )
            )
    if outcome == "closed_cost_futility":
        return events
    for n, qid in enumerate(order["quality_order"]):
        events.append(("reference_exact", qid, aa, {}))
        for c in CELLS:
            events.append(("reference_" + c, qid, main[c], dict(quality_index=n)))
    if outcome == "closed_negative_quality":
        return events
    for block in (0, 1):
        for n, qid in enumerate(order["timing_order"][str(block)]):
            for slot, meta in enumerate(order["slots"][str(block)][qid]):
                for pos, c in enumerate(CELLS if (n * 8 + slot) % 2 == 0 else CELLS[::-1]):
                    events.append(
                        (
                            "conditioning",
                            qid,
                            main[c],
                            dict(
                                block=block,
                                slot_index=slot,
                                slot_cell=meta["cell"],
                                conditioning_position=pos,
                            ),
                        )
                    )
                for rep in range(3):
                    events.append(
                        (
                            "warmup" if rep == 0 else "measurement",
                            qid,
                            meta["cell"] + "-" + meta["label"],
                            dict(
                                block=block,
                                slot_index=slot,
                                round=meta["round"],
                                label=meta["label"],
                                repetition=rep,
                                regime="reuse",
                                retained=rep != 0,
                            ),
                        )
                    )
    return events


def expected_plans(items, order, outcome):
    first = items[0]["query"]["id"]
    main = ["native-reference", "partial-reference"]
    result = [
        (first, r, False) for r in ["initial-native-reference", "qualification-partial-old", *main]
    ]
    for q in order["preview_order"]:
        for side in range(2):
            result.extend((q, r, False) for r in main)
    if outcome == "closed_cost_futility":
        return result
    for q in order["quality_order"]:
        for side in range(2):
            result.extend((q, r, False) for r in main)
    if outcome == "closed_negative_quality":
        return result
    allreaders = [*main, *[c + "-" + label for c in CELLS for label in ["a", "b"]]]
    for block in (0, 1):
        for q in order["timing_order"][str(block)]:
            for side in range(2):
                result.extend((q, r, bool(side)) for r in allreaders)
    return result


def gates(retained):
    aa = {}
    for c in CELLS:
        s = summary(contrasts(retained, c))
        s["pass"] = all(-0.10 <= v <= 0.10 for v in s["gap_ci95"]) and all(
            -math.log(1.02) <= v <= math.log(1.02) for v in s["log_ratio_ci95"]
        )
        aa[c] = s
    comparison = summary(contrasts(retained, "partial640", "native640"))
    comparison["pass"] = (
        comparison["gap_upper_adjusted"] <= -0.10
        and comparison["log_ratio_upper_adjusted"] <= math.log(0.98)
        and all(g < 0 for g in comparison["block_gap_ms"].values())
    )
    verdict = (
        "measurement_inconclusive"
        if not all(s["pass"] for s in aa.values())
        else "promising_partial_ann_votes108"
        if comparison["pass"]
        else "closed_negative_economics"
    )
    return dict(aa=aa, comparison=comparison, verdict=verdict)


def analyze(campaign, package, output, allow_synthetic=False):
    campaign, package, output = map(Path, (campaign, package, output))
    cfg = verify(package)
    name = campaign_identity(campaign, package)
    folder = campaign / "run"
    lock = read(folder / "LOCK.json")
    status = read(folder / "status.json")
    host = read(folder / "host-exit.json")
    require(
        lock["package_manifest_sha256"] == sha(package / "manifest.json")
        and lock["complete"] is True,
        "Incomplete raw cannot receive performance verdict",
    )
    expected_files = {p.name for p in folder.iterdir() if p.is_file()} - {
        "LOCK.json",
        "progress.json",
        "host-exit.json",
        "protected-source-before.json",
        "protected-source-after.json",
        "resource-preflight.json",
        "host-failure.json",
    }
    require(set(lock["files_sha256"]) == expected_files, "Raw lock coverage differs")
    for p, h in lock["files_sha256"].items():
        require(sha(safe_file(folder, p)) == h, "Raw digest differs: " + p)
    require(
        status["status"] == "complete"
        and status["final_integrity_verified"] is True
        and read(folder / "job-exit.json")["exit_code"] == 0,
        "Final status/integrity incomplete",
    )
    submission = read(campaign / "submission.json")
    job = submission["jobs"]["block-0"]
    require(
        host["exit_code"] == 0
        and host["protected_sources_unchanged"] is True
        and host["job_id"] == job
        and host["array_job_id"] == job
        and host["array_task_id"] == "0"
        and host["provider_calls"] == 0,
        "Host/job identity differs",
    )
    before = read(campaign / "protected-source-before.json")
    require(
        bool(before)
        and before
        == read(folder / "protected-source-before.json")
        == read(folder / "protected-source-after.json"),
        "Protected-source receipts differ",
    )
    cleanup = read(folder / "cleanup.json")
    require(
        cleanup["all_readers_closed"] and cleanup["databases_stopped"] and cleanup["errors"] == [],
        "Cleanup incomplete",
    )
    scheduler = read(campaign / "scheduler-evidence.json")
    require(scheduler["terminal_verified"] is True, "Terminal scheduler proof missing")
    require(
        any(
            line.split("|")[:3] == [job + "_0", "COMPLETED", "0:0"]
            for line in scheduler["sacct_stdout"].splitlines()
        ),
        "Successful job accounting missing",
    )
    identity = read(folder / "runtime-identity.json")
    frozen = read(package / "frozen/experiment.json")
    require(
        identity["module_sha256"] == frozen["module_sha256"]
        and identity["image_sha256"] == frozen["image_sha256"]
        and identity["runtime_profile_hash"] == PROFILE_SHA
        and identity["registry_hash"] == REGISTRY,
        "Runtime/profile/registry differs",
    )
    require(
        identity["synthetic_mock"] is False or allow_synthetic,
        "Synthetic raw is not native evidence",
    )
    original = read(package / "frozen/source-index.json")
    require(
        read(folder / "database-identity.json") == original, "Preserved database identity differs"
    )
    targets = read(folder / "targets.json")
    build = read(folder / "build.json")
    graph = build["graph"]
    final = read(folder / "final-integrity.json")
    require(
        targets["native640"]
        == dict(
            index=dict(oid=264013, relname="reviews_hnsw"),
            index_identity=original["index_identity"],
        ),
        "Baseline target changed",
    )
    validate_build_settings(build["build_settings"])
    expected_graph = {k: v for k, v in graph.items() if k != "index_identity"}
    require(
        graph["index_identity"] == digest(expected_graph)
        and targets["partial640"]
        == dict(
            index=dict(oid=int(graph["index"]["oid"]), relname=graph["index"]["relname"]),
            index_identity=graph["index_identity"],
        ),
        "New graph target identity differs",
    )
    for c in CELLS:
        require(
            final[c]["original_graph_files"] == original["index_files"]
            and final[c]["data_bits_verified"] is True,
            "Final original graph/data proof differs",
        )
    require(
        final["partial640"]["partial_graph_files"] == graph["files_sha256"]
        and final["module_sha256"] == frozen["module_sha256"],
        "Final partial graph/module proof differs",
    )
    initialized = read(folder / "shared-initialization.json")
    require(
        initialized["snapshot_identity"] == cfg["snapshot_identity"]
        and initialized["eligibility_sha256"] == sha(package / "eligibility.json")
        and initialized["admitted_requests"] == 200
        and initialized["source_effort"] == 320
        and initialized["reference_effort"] == 640
        and initialized["two_private_copies"] is True,
        "Snapshot/source/reference scope differs",
    )
    resources = read(folder / "resource-preflight.json")
    memory = read(folder / "memory-preflight.json")
    require(
        resources["memory_gib"] == 32 and memory["conservative_bound_bytes"] <= 32 * 1024**3,
        "Resource proof differs",
    )
    require(set(resources["quota"]) == {"/home", "/scratch"}, "Both quota proofs required")
    for fs, v in resources["quota"].items():
        require(
            min(v["filesystem_free_bytes"], v["space_available_lower"]) >= v["required_bytes"]
            and min(v["filesystem_free_inodes"], v["inodes_available_lower"])
            >= v["required_inodes"],
            "Resource preflight insufficient",
        )
    require(memory == memory_proof(memory["servers"]), "Memory proof does not replay")
    items = lines(package / "queries.jsonl")
    queries = {i["query"]["id"]: i["query"] for i in items}
    pins = read(package / "baseline-results.json")
    eligibility = read(package / "eligibility.json")
    order = read(package / "order.json")
    outcome = status["result"]["outcome"]
    require(
        outcome in ["closed_cost_futility", "closed_negative_quality", "complete_measurement"],
        "Unknown terminal outcome",
    )
    searches = lines(folder / "searches.jsonl")
    expected = expected_events(items, order, outcome)
    require(len(searches) == len(expected) == status["backend_searches"], "Search coverage differs")
    operations = Counter()
    retained = []
    previous = 0
    qual = []
    reference_rows = (
        {r["query_id"]: r for r in lines(folder / "references.jsonl")}
        if outcome != "closed_cost_futility"
        else {}
    )
    for row, (op, qid, reader, meta) in zip(searches, expected):
        require(
            row["operation"] == op
            and row["query_id"] == qid
            and row["reader"] == reader
            and not row.get("error"),
            "Search identity/order/failure differs",
        )
        for k, v in meta.items():
            require(row[k] == v, "Search schedule metadata differs: " + k)
        validate_charge(row)
        if not op.endswith("_exact"):
            require(
                type(row["sql_ms"]) in (int, float)
                and math.isfinite(row["sql_ms"])
                and 0 <= row["sql_ms"] <= row["outer_ms"] + 1e-9,
                "SQL timer outside full outer interval",
            )
        require(row["start_ns"] >= previous, "Search intervals overlap/out of order")
        previous = row["end_ns"]
        operations[op] += 1
        q = queries[qid]
        truth = {k: pins[qid][k] for k in ["truth_strict", "truth_ties", "truth_k"]}
        if op.endswith("_exact"):
            require(row["truth"] == truth, "Full truth differs")
        else:
            mode = "partial640" if "partial" in reader else "native640"
            require(row["cell"] == mode, "Reader/cell differs")
            value = row["result"]
            score_result(value, truth, q, eligibility)
            if mode == "native640":
                equivalent(value, pins[qid]["original640"])
            elif op in ["conditioning", "warmup", "measurement"]:
                equivalent(value, reference_rows[qid]["outcomes"][mode])
            if op == "measurement":
                retained.append(row)
        if op.startswith("qualification"):
            qual.append(row)
    require(
        dict(operations) == status["operations"]
        and all(v <= OPERATIONS[k] for k, v in operations.items()),
        "Operation counts differ",
    )
    if outcome == "complete_measurement":
        require(dict(operations) == OPERATIONS, "Full operation allowance differs")
    expected_roles = [
        "initial-native-reference",
        "qualification-partial-old",
        "native-reference",
        "partial-reference",
    ] + (
        []
        if outcome != "complete_measurement"
        else [c + "-" + label for c in CELLS for label in ["a", "b"]]
    )
    admissions = lines(folder / "admissions.jsonl")
    require(
        [r["reader"] for r in admissions] == expected_roles
        and status["reader_connections"] == len(expected_roles)
        and status["maximum_live_readers"] == (6 if outcome == "complete_measurement" else 2),
        "Reader coverage differs",
    )
    for a in admissions:
        mode = "partial640" if "partial" in a["reader"] else "native640"
        require(
            a["mode"] == mode
            and a["copy"] == mode
            and a["origin"]["settings"] == cfg["source_settings"]
            and a["origin"]["index"] == targets[mode]["index"]
            and a["effective"] == effective(a["origin"], mode),
            "Admission settings/target differs",
        )
        validate_charge(a)
    packets = lines(folder / "plans.jsonl")
    plans = expected_plans(items, order, outcome)
    require(len(packets) == len(plans), "Plan coverage differs")
    for p, (qid, reader, cached) in zip(packets, plans):
        require(
            p["query_id"] == qid
            and p["reader"] == reader
            and p["packet"]["must_be_cached"] == cached,
            "Plan order/context differs",
        )
        validate_packet(
            p["packet"], queries[qid], "partial640" if "partial" in reader else "native640"
        )
    catalogs = lines(folder / "catalogs.jsonl")
    seen = {}
    for row in catalogs:
        validate_phase(row["session_user"], row["phase"])
        validate_catalog(row["value"], row["candidate"], row["session_user"])
        require(row["sha256"] == digest(row["value"]), "Catalog hash differs")
        validate_charge(row["charge"])
        key = (row["copy"], row["candidate"], row["session_user"])
        if key in seen:
            require(seen[key] == row["value"], "Catalog/statistics/environment drift")
        seen[key] = row["value"]
    require(
        all(
            any(r["copy"] == c and r["phase"] == phase for r in catalogs)
            for c in CELLS
            for phase in ["before_build", "after_build", "final"]
        ),
        "Catalog stage coverage missing",
    )
    qualification = read(folder / "qualification.json")
    require(
        qualification["status"] == "passed"
        and all(
            qualification[k] is True
            for k in ["rollback_both_cells", "closed_handles_rejected", "explicit_recovery"]
        )
        and len(qual) == 10,
        "Native qualification proofs missing",
    )
    for a, b in [(qual[2], qual[4]), (qual[4], qual[5]), (qual[5], qual[9])]:
        equivalent(a["result"], b["result"])
    preview_rows = [r for r in searches if r["operation"] == "preview_measurement"]
    pairs = []
    for qid in order["preview_order"]:
        pairs.append(
            dict(
                query_id=qid,
                **{
                    c + "_ms": sum(
                        r["outer_ms"]
                        for r in preview_rows
                        if r["query_id"] == qid and r["cell"] == c
                    )
                    / 2
                    for c in CELLS
                },
            )
        )
    preview = preview_decision(pairs)
    parity(dict(pairs=pairs, decision=preview), read(folder / "preview.json"))
    require(
        preview["stop"] == (outcome == "closed_cost_futility"), "Preview stop was ignored/changed"
    )
    quality = None
    economics = None
    if outcome != "closed_cost_futility":
        refs = lines(folder / "references.jsonl")
        require(
            [r["query_id"] for r in refs] == order["quality_order"],
            "Quality order/coverage differs",
        )
        for ref in refs:
            q = queries[ref["query_id"]]
            require(
                ref["group"] == ref["query_id"].rsplit("-", 1)[0]
                and {k: ref[k] for k in ["truth_strict", "truth_ties", "truth_k"]}
                == {k: pins[q["id"]][k] for k in ["truth_strict", "truth_ties", "truth_k"]},
                "Quality truth/group differs",
            )
            for c in CELLS:
                score_result(ref["outcomes"][c], ref, q, eligibility)
                rr = next(
                    r
                    for r in searches
                    if r["operation"] == "reference_" + c and r["query_id"] == q["id"]
                )
                require(
                    rr["result"] == ref["outcomes"][c],
                    "Reference journal differs from actual result",
                )
        quality = quality_report(refs)
        parity(quality, read(folder / "quality.json"))
        require(
            quality["pass"] == (outcome == "complete_measurement"),
            "Quality gate was ignored/changed",
        )
    if outcome == "complete_measurement":
        slots = lines(folder / "slots.jsonl")
        require(
            len(slots) == 3200 and len(retained) == 6400, "Formal slot/retained coverage differs"
        )
        for block in (0, 1):
            selected = [s for s in slots if s["block"] == block]
            require(len(selected) == 1600, "Block incomplete")
            expected_slot = [
                (q, n, m)
                for q in order["timing_order"][str(block)]
                for n, m in enumerate(order["slots"][str(block)][q])
            ]
            for row, (qid, n, meta) in zip(selected, expected_slot):
                require(
                    row["query_id"] == qid
                    and row["slot_index"] == n
                    and all(row[k] == v for k, v in meta.items()),
                    "Slot identity differs",
                )
                calls = [
                    r
                    for r in searches
                    if r.get("block") == block and r["query_id"] == qid and r.get("slot_index") == n
                ]
                require(
                    len(calls) == 5
                    and row["start_ns"] <= calls[0]["start_ns"]
                    and calls[1]["end_ns"] <= row["conditioning_end_ns"] <= calls[2]["start_ns"]
                    and row["end_ns"] >= calls[-1]["end_ns"],
                    "Slot nesting differs",
                )
            boundary = read(folder / f"warm-boundary-{block}.json")
            for side in ["before", "after"]:
                require(
                    set(boundary[side]) == set(expected_roles[2:]),
                    "Boundary reader coverage differs",
                )
                for a in boundary[side].values():
                    expected_settings = {
                        **cfg["source_settings"],
                        "hnsw.ef_search": "640",
                        "statement_timeout": "30000",
                    }
                    require(
                        {k: v[0] for k, v in a["values"].items()} == expected_settings
                        and a["values"]["hnsw.ef_search"][1] == "40",
                        "Boundary settings differ",
                    )
        economics = gates(retained)
    checkpoint = read(folder / "charges-checkpoint.json")
    require(
        checkpoint["searches"] == len(searches) and checkpoint["operations"] == dict(operations),
        "Final incremental charges differ",
    )
    sql = lines(folder / "sql.jsonl")
    actual = Counter(r["category"] for r in sql if "category" in r)
    for row in sql:
        if "category" in row:
            require(
                type(row["start_ns"]) is int and row["end_ns"] > row["start_ns"],
                "Invalid SQL interval",
            )
    require(
        dict(actual) == status["sql"] == checkpoint["sql"]
        and all(actual[k] <= SQL_CAPS[k] for k in actual),
        "SQL ledger/count/cap differs",
    )
    require(
        actual["truth_helper"] == 20 * sum(v for k, v in operations.items() if k.endswith("_exact"))
        and status["search_sql"] == len(searches),
        "Truth helpers/search SQL unaccounted",
    )
    result = dict(
        version="partial-ann.v1.result",
        campaign=name,
        context="votes108",
        independent_vectors=200,
        outcome=economics["verdict"] if economics else outcome,
        measurement_complete=outcome == "complete_measurement",
        searches=len(searches),
        operations=dict(operations),
        reader_admissions=len(admissions),
        plan_packets=len(packets),
        preview=preview,
        quality=quality,
        economics=economics,
        final_integrity=True,
        provider_calls=0,
        independent_confirmation=False,
        canonical_acceptance_established=False,
        synthetic_mock=identity["synthetic_mock"],
        raw_files_sha256=lock["files_sha256"],
    )
    output.mkdir(parents=True, exist_ok=False)
    save(output / "performance.json", result)
    (output / "report.txt").write_text(json_text(result) + "\n")
    return result


def json_text(result):
    import json

    return json.dumps(result, indent=2, sort_keys=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("campaign", type=Path)
    p.add_argument("package", type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    analyze(a.campaign, a.package, a.output)
