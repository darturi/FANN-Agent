"""Independent raw replay, quality-first decision and warm-only B2b gates."""

import argparse
import math
from pathlib import Path

from xt_common import (
    CELLS,
    COUNTS,
    CRITERIA,
    FILTERS,
    OPERATIONS,
    PROFILE_SHA,
    QUALITY_OPERATIONS,
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
from xt_measure import order_manifest
from xt_metadata import validate_catalog, validate_charge, validate_packet
from xt_quality import quality_report
from xt_stats import contrasts, equivalent, finite, near, require, score_result, summary, unique


def audit_settings(row, level, role, origin):
    require(
        row["reader"] == role and row["mode"] == level and row["origin"] == origin,
        "Reader/origin audit identity differs",
    )
    expected = effective(origin, level)
    require(row["effective"] == expected, "Binding changed more than effort")
    values = {**expected["settings"], "statement_timeout": "30000"}
    require(
        {k: v["value"] for k, v in row["settings"].items()} == values,
        "Actual session setting differs",
    )
    require(
        all(v["source"] == "session" for v in row["settings"].values()), "Unbound session setting"
    )
    require(
        row["settings"]["hnsw.ef_search"]["boot_val"] == "40",
        "Boot metadata/source/reference conflated",
    )


def interval(start, end):
    require(
        type(start) is int and type(end) is int and 0 <= start < end, "Invalid timestamp interval"
    )


def charge(row):
    interval(row["start_ns"], row["end_ns"])
    near(row["outer_ms"], (row["end_ns"] - row["start_ns"]) / 1e6)
    finite(row["outer_ms"], positive=True)


def validate_qualification(folder, items, pins, eligibility, origin):
    q = read(folder / "qualification.json")
    require(
        q["status"] == "passed" and q["backend_searches"] == 30 and len(q["cases"]) == 3,
        "Native conformance incomplete",
    )
    finite(q["outer_ms"], positive=True)
    require(
        q["non_search_sql"]
        == {
            "plan_packets": 12,
            "setting_queries": 12,
            "injected_failed_statements": 3,
            "rollback_recovery_selects": 3,
            "exact_internal_non_search_execute_calls": 120,
        },
        "Qualification non-search accounting differs",
    )
    lower = {}
    for filter_, row in zip(FILTERS, q["cases"]):
        query = next(i["query"] for i in items if i["query"]["id"].endswith("-" + filter_))
        qid = query["id"]
        require(
            row["query_id"] == qid
            and row["filter"] == filter_
            and row["status"] == "passed"
            and row["searches"] == 10,
            "Conformance fixture/search count differs",
        )
        require(
            all(
                row[k] is True
                for k in (
                    "sql_abort_rolled_back",
                    "closed_session_rejected_without_search",
                    "explicit_new_session_recovered",
                )
            ),
            "Error/new-session proof failed",
        )
        require(
            row["truth"] == {k: pins[qid][k] for k in row["truth"]},
            "Qualification exact truth differs",
        )
        outputs = row["outputs"]
        require(
            [o["mode"] for o in outputs]
            == [
                "native640",
                "exact10",
                "native640",
                "exact10",
                "exact10",
                "native640",
                "native640",
                "exact10",
            ],
            "Native effort order differs",
        )
        roles = [
            "initial-reference640",
            f"qualification-{filter_}-exact10-old",
            "initial-reference640",
            f"qualification-{filter_}-exact10-old",
            f"qualification-{filter_}-exact10-new",
            "initial-reference640",
            f"qualification-{filter_}-native640-new",
            f"qualification-{filter_}-exact10-new",
        ]
        for index, (o, role) in enumerate(zip(outputs, roles)):
            charge(o)
            require(
                o["reader"] == role and o["step"] == index + 1,
                "Qualification reader identity differs",
            )
            score_result(o["result"], row["truth"], query, eligibility)
            require(o["result"]["valid"], "Invalid conformance result")
            equivalent(
                o["result"],
                pins[qid]["original640"] if o["mode"] == "native640" else outputs[1]["result"],
                row["truth"],
                o["mode"],
            )
            if index:
                require(
                    outputs[index - 1]["end_ns"] <= o["start_ns"], "Qualification searches overlap"
                )
        for field in ("exact_before", "exact_after"):
            charge(row[field])
            require(
                row[field]["inherited_non_search_execute_calls"] == 20,
                "Exact non-search accounting differs",
            )
        require(
            row["exact_before"]["end_ns"] <= outputs[0]["start_ns"]
            and outputs[4]["end_ns"]
            <= row["exact_after"]["start_ns"]
            < row["exact_after"]["end_ns"]
            <= outputs[5]["start_ns"],
            "Exact/native temporal isolation differs",
        )
        require(set(row["plans"]) == {"before", "after"}, "Qualification plans incomplete")
        for phase in ("before", "after"):
            require(set(row["plans"][phase]) == set(CELLS), "Qualification plan cells incomplete")
            for cell, packet in row["plans"][phase].items():
                validate_packet(packet, query, cell)
        for phase in ("before", "after"):
            audit_settings(
                row["settings"][phase]["reference"], "native640", "initial-reference640", origin
            )
            suffix = "old" if phase == "before" else "new"
            audit_settings(
                row["settings"][phase]["candidate"],
                "exact10",
                f"qualification-{filter_}-exact10-{suffix}",
                origin,
            )
        lower[qid] = outputs[1]["result"]
    return lower


def validate_run(campaign, package, cfg):
    folder = campaign / "run"
    items = lines(package / "frozen/inputs/queries.jsonl")
    pins, eligibility = read(package / "baseline-results.json"), read(package / "eligibility.json")
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
        "quality.json",
        "quality-settings.json",
        "admissions.json",
        "cleanup.json",
        "charges.json",
        "metadata.json",
        "plan-audits.jsonl",
    }
    require(
        lock["package_manifest_sha256"] == sha(package / "manifest.json")
        and required <= set(lock["files_sha256"]),
        "Raw lock incomplete",
    )
    for name, expected in lock["files_sha256"].items():
        require(sha(safe_file(folder, name)) == expected, "Raw hash differs: " + name)
    record = read(campaign / "submission.json")
    for name in ("job-exit.json", "host-exit.json"):
        require(read(folder / name)["exit_code"] == 0, "Native runtime/host/cleanup incomplete")
    host = read(folder / "host-exit.json")
    require(
        host["protected_sources_unchanged"] is True
        and host["array_job_id"] == record["jobs"]["block-0"]
        and host["array_task_id"] == "0",
        "Submission/job/host proof differs",
    )
    require(
        read(campaign / "protected-source-before.json")
        == read(folder / "protected-source-before.json")
        == read(folder / "protected-source-after.json"),
        "Protected evidence changed",
    )
    source_cfg = read(package / "frozen/experiment.json")
    require(
        read(folder / "runtime-identity.json")
        == {
            "module_sha256": source_cfg["module_sha256"],
            "image_sha256": source_cfg["image_sha256"],
            "runtime_profile_hash": PROFILE_SHA,
            "registry_hash": "fc42b1fb1441518b15123ed30ba2a0d0c96e9c74d4f0727ab9eb391597cdbf37",
            "package_manifest_sha256": sha(package / "manifest.json"),
        },
        "Runtime identity differs",
    )
    require(
        read(folder / "database-identity.json") == read(package / "frozen/source-index.json"),
        "Physical index changed",
    )
    init = read(folder / "shared-initialization.json")
    origin = read(package / "origin-source.json")
    require(
        init["origin_manifest"] == origin
        and init["source_effort"] == 320
        and init["study_reference_effort"] == 640
        and init["eligibility_sha256"] == sha(package / "eligibility.json"),
        "Shared snapshot/origin/reference identity differs",
    )
    require(init["snapshot_identity"] == cfg["snapshot_identity"], "Snapshot changed")
    charge(init)
    lower = validate_qualification(folder, items, pins, eligibility, origin)
    raw_refs = lines(folder / "references.jsonl")
    refs = unique(raw_refs, lambda r: r["query_id"])
    orders = order_manifest(items)
    require(
        [r["query_id"] for r in raw_refs] == orders["quality_order"],
        "Quality acquisition order/coverage differs",
    )
    queries = {i["query"]["id"]: i for i in items}
    for qid, ref in refs.items():
        item = queries[qid]
        require(
            ref["group"] == item["group"] and set(ref["outcomes"]) == set(CELLS),
            "Reference/group identity differs",
        )
        require(
            {k: ref[k] for k in ("truth_strict", "truth_ties", "truth_k")}
            == {k: pins[qid][k] for k in ("truth_strict", "truth_ties", "truth_k")}
            and ref["outcomes"]["native640"] == pins[qid]["original640"],
            "Pinned640/exact reference changed",
        )
        for cell in CELLS:
            score_result(ref["outcomes"][cell], ref, item["query"], eligibility)
            require(ref["outcomes"][cell]["valid"], "Invalid native result, not quality-negative")
            if cell == "exact10":
                equivalent(ref["outcomes"][cell], ref["outcomes"][cell], ref, cell)
            charge(ref["charge"][cell])
        charge(ref["charge"])
        require(
            ref["charge"]["inherited_non_search_execute_calls"] == 20
            and ref["charge"]["end_ns"]
            <= ref["charge"]["native640"]["start_ns"]
            < ref["charge"]["native640"]["end_ns"]
            <= ref["charge"]["exact10"]["start_ns"],
            "Quality reference phases overlap",
        )
        if qid in lower:
            require(ref["outcomes"]["exact10"]["recall"] == 1.0, "Exact10 semantic failure")
    quality = quality_report(raw_refs)
    saved_quality = read(folder / "quality.json")
    finite(saved_quality["analysis_outer_ms"], positive=True)
    parity(quality, {k: v for k, v in saved_quality.items() if k != "analysis_outer_ms"}, "quality")
    audits = read(folder / "quality-settings.json")
    audit_settings(audits["reference"], "native640", "initial-reference640", origin)
    audit_settings(audits["candidate"], "exact10", "qualification-votes108-exact10-new", origin)
    status = read(folder / "status.json")
    passed = quality["pass"]
    wanted = {
        "status": "complete",
        "provider_calls": 0,
        "confirmation_queries": 0,
        "new_fits": 0,
        "cases": 600,
        "vectors": 200,
        "backend_searches": 40230 if passed else 1830,
        "operations": OPERATIONS if passed else QUALITY_OPERATIONS,
        "control_installations": 0,
        "index_and_module_after_verified": True,
        "quality_pass": passed,
        "retained_executions": 19200 if passed else 0,
        "discarded_warmups": 9600 if passed else 0,
        "slots": 9600 if passed else 0,
        "conditioning_searches": 9600 if passed else 0,
        "reader_connections": 14 if passed else 10,
        "completed_temporal_blocks": 2 if passed else 0,
    }
    require(
        all(status.get(k) == v for k, v in wanted.items()),
        "Status/resource/early-stop accounting differs",
    )
    finite(status["elapsed_seconds"], positive=True)
    require(status["elapsed_seconds"] <= 6600, "Work deadline exceeded")
    admissions = read(folder / "admissions.json")
    roles = [("initial-reference640", "native640")]
    for f in FILTERS:
        roles += [
            (f"qualification-{f}-exact10-old", "exact10"),
            (f"qualification-{f}-exact10-new", "exact10"),
            (f"qualification-{f}-native640-new", "native640"),
        ]
    if passed:
        roles += [(cell + "-" + label, cell) for cell in CELLS for label in ("a", "b")]
    require(
        [(r["reader"], r["mode"]) for r in admissions["readers"]] == roles
        and admissions["maximum_live_readers"] <= 5,
        "Reader admission budget/order differs",
    )
    for row in admissions["readers"]:
        charge(row)
        expected = effective(origin, row["mode"])
        require(
            row["origin"] == origin
            and row["effective"] == expected
            and row["origin_sha256"] == digest(origin)
            and row["effective_sha256"] == digest(expected)
            and row["inherited_explicit_startup_execute_calls"] == 17,
            "Reader startup binding/accounting differs",
        )
    cleanup = read(folder / "cleanup.json")
    charge(cleanup)
    require(
        cleanup["all_readers_closed"] is True and cleanup["database_stopped"] is True,
        "Reader/database cleanup incomplete",
    )
    charges = read(folder / "charges.json")
    require(
        charges["searches"] == status["backend_searches"]
        and charges["operations"] == status["operations"]
        and charges["explicit_reader_startup_execute_calls"] == 17 * len(roles)
        and charges["exact_internal_non_search_execute_calls"] == 20 * 606,
        "Phase/SQL charge accounting differs",
    )
    charge(charges["restore_import"])
    require(charges["overlapping_categories_must_not_be_summed"] is True, "Charge scope omitted")
    timing_names = {
        "slots.jsonl",
        "executions.jsonl",
        "conditioning.jsonl",
        "warm-boundaries-before.json",
        "warm-boundary-0.json",
        "warm-boundary-1.json",
    }
    validate_metadata(folder, items, origin, passed)
    if not passed:
        require(
            not any((folder / name).exists() for name in timing_names),
            "Timing ran after failed quality gate",
        )
        return [], quality, lock, status, charges
    require(timing_names <= set(lock["files_sha256"]), "Warm raw lock incomplete")
    for role, row in read(folder / "warm-boundaries-before.json").items():
        audit_settings(row, role.rsplit("-", 1)[0], role, origin)
    expected_slots = [
        {"query_id": qid, "group": queries[qid]["group"], "block": b, "slot_index": j, **meta}
        for b in (0, 1)
        for qid in orders["timing_order"][str(b)]
        for j, meta in enumerate(orders["slots"][str(b)][qid])
    ]
    slots, executions, conditioning = (
        lines(folder / n) for n in ("slots.jsonl", "executions.jsonl", "conditioning.jsonl")
    )
    require(
        (len(slots), len(executions), len(conditioning)) == (9600, 28800, 9600),
        "Warm raw counts differ",
    )
    retained, previous_end = [], -1
    for index, (slot, expected) in enumerate(zip(slots, expected_slots)):
        require(all(slot.get(k) == v for k, v in expected.items()), "Slot identity/order differs")
        role = expected["cell"] + "-" + expected["label"]
        require(slot["reader"] == role, "Wrong persistent reader")
        interval(slot["conditioning_start_ns"], slot["conditioning_end_ns"])
        require(
            previous_end
            <= slot["conditioning_start_ns"]
            < slot["conditioning_end_ns"]
            < slot["end_ns"],
            "Slot ordering/phase timing differs",
        )
        previous_end = slot["end_ns"]
        last = slot["conditioning_start_ns"]
        ref = refs[expected["query_id"]]
        for rep, row in enumerate(conditioning[index : index + 1]):
            require(
                all(row.get(k) == v for k, v in expected.items())
                and row["repetition"] == rep
                and row["reader"] == "initial-reference640",
                "Conditioning identity/order differs",
            )
            charge(row)
            require(
                last <= row["start_ns"] < row["end_ns"] <= slot["conditioning_end_ns"],
                "Conditioning overlaps primary query",
            )
            last = row["end_ns"]
            finite(row["sql_ms"], positive=True)
            require(
                row["sql_ms"] <= row["outer_ms"] + 1e-6
                and row["result"] == ref["outcomes"]["native640"],
                "Conditioning output/timer differs",
            )
        last = slot["conditioning_end_ns"]
        for rep, row in enumerate(executions[index * 3 : index * 3 + 3]):
            require(
                all(row.get(k) == v for k, v in expected.items())
                and row["repetition"] == rep
                and row["retained"] == (rep != 0)
                and row["regime"] == "reuse"
                and row["reader"] == role,
                "Execution identity/retention differs",
            )
            charge(row)
            require(
                last <= row["start_ns"] < row["end_ns"] <= slot["end_ns"],
                "Primary queries overlap/reverse",
            )
            last = row["end_ns"]
            finite(row["sql_ms"], positive=True)
            require(row["sql_ms"] <= row["outer_ms"] + 1e-6, "SQL timer exceeds primary")
            score_result(row["result"], ref, queries[expected["query_id"]]["query"], eligibility)
            equivalent(row["result"], ref["outcomes"][expected["cell"]], ref, expected["cell"])
            if rep:
                retained.append(row)
    for block in (0, 1):
        boundary = read(folder / f"warm-boundary-{block}.json")
        interval(boundary["start_ns"], boundary["before_end_ns"])
        interval(boundary["after_start_ns"], boundary["end_ns"])
        block_slots = slots[block * 4800 : (block + 1) * 4800]
        require(
            boundary["block"] == block
            and boundary["before_end_ns"]
            <= block_slots[0]["conditioning_start_ns"]
            < block_slots[-1]["end_ns"]
            <= boundary["after_start_ns"],
            "Warm block charge/phase bounds differ",
        )
        for phase in ("before", "after"):
            rows = boundary[phase]
            require(
                set(rows)
                == {
                    "initial-reference640",
                    *[cell + "-" + label for cell in CELLS for label in ("a", "b")],
                },
                "Boundary reader audit incomplete",
            )
            for role, row in rows.items():
                audit_settings(
                    row,
                    "native640" if role == "initial-reference640" else role.rsplit("-", 1)[0],
                    role,
                    origin,
                )
    return retained, quality, lock, status, charges


def validate_metadata(folder, items, origin, passed):
    metadata = read(folder / "metadata.json")
    catalogs = metadata["catalogs"]
    phases = ["before_qualification", "after_quality"] + (
        ["after_block_0", "after_block_1"] if passed else []
    )
    require([r["phase"] for r in catalogs] == phases, "Catalog phase coverage differs")
    for row in catalogs:
        validate_catalog(row["value"])
        validate_charge(row["charge"])
        require(
            row["sha256"] == digest(row["value"]) and row["value"] == catalogs[0]["value"],
            "Catalog/statistics drift",
        )
    packets = []
    for q in read(folder / "qualification.json")["cases"]:
        query = next(i["query"] for i in items if i["query"]["id"] == q["query_id"])
        for phase in ("before", "after"):
            for cell in CELLS:
                packet = q["plans"][phase][cell]
                validate_packet(packet, query, cell)
                packets.append(packet)
    events = lines(folder / "plan-audits.jsonl")
    order = order_manifest(items)
    by_id = {i["query"]["id"]: i["query"] for i in items}
    wanted = []
    for qid in order["quality_order"]:
        for phase in ("quality_before", "quality_after"):
            for cell, role in [
                ("native640", "initial-reference640"),
                ("exact10", "qualification-votes108-exact10-new"),
            ]:
                wanted.append((phase, qid, None, role, cell))
    if passed:
        for block in (0, 1):
            for qid in order["timing_order"][str(block)]:
                for phase in ("warm_before", "warm_after"):
                    for cell in CELLS:
                        for label in ("a", "b"):
                            wanted.append((phase, qid, block, cell + "-" + label, cell))
    require(len(events) == len(wanted), "Plan audit coverage differs")
    for row, (phase, qid, block, role, cell) in zip(events, wanted):
        require(
            (row["phase"], row["query_id"], row["block"], row["reader"])
            == (phase, qid, block, role),
            "Plan audit order/reader differs",
        )
        require(
            row["packet"]["must_be_cached"] == (phase == "warm_after"),
            "Cached-plan requirement changed",
        )
        validate_packet(row["packet"], by_id[qid], cell)
        packets.append(row["packet"])
    n = 12012 if passed else 2412
    require(metadata["plan_packets"] == len(packets) == n, "Plan packet count differs")
    require(len({digest(p["driver"]) for p in packets}) == 1, "Driver preparation/cache changed")
    operations = {"catalog": len(catalogs), "cache_inventory": n, "fresh_explain": n}
    cached = sum(len(p["cached"]) for p in packets)
    if cached:
        operations["cached_explain"] = cached
    require(
        metadata["operations"] == operations and sum(operations.values()) <= 40000,
        "Observer SQL accounting differs",
    )
    require(read(folder / "charges.json")["observer"] == metadata, "Observer phase charges differ")
    references = {r["query_id"]: r for r in lines(folder / "references.jsonl")}
    slots = lines(folder / "slots.jsonl") if passed else []
    spans = {}
    for slot in slots:
        key = (slot["block"], slot["query_id"])
        before, after = spans.get(key, (slot["conditioning_start_ns"], slot["end_ns"]))
        spans[key] = (min(before, slot["conditioning_start_ns"]), max(after, slot["end_ns"]))
    for row in events:
        charge_ = row["packet"]["charge"]
        qid = row["query_id"]
        if row["phase"].startswith("quality"):
            start = references[qid]["charge"]["start_ns"]
            end = references[qid]["charge"]["exact10"]["end_ns"]
        else:
            start, end = spans[(row["block"], qid)]
        require(
            charge_["end_ns"] <= start
            if row["phase"].endswith("before")
            else charge_["start_ns"] >= end,
            "Plan diagnostic overlaps primary/acquisition work",
        )


def gates(quality, aa=None, comparison=None):
    result = {
        "activation_qualified": False,
        "B1c_proceed": False,
        "router_selected": False,
        "canonical_acceptance_established": False,
        "M1": False,
        "M2": False,
        "M3": False,
    }
    if not quality["pass"]:
        return {**result, "status": "closed_negative_quality", "aa_assessed": False}
    require(
        set(aa) == set(CELLS) and set(comparison) == {"overall", *FILTERS},
        "Incomplete warm statistics",
    )
    failures = []
    for cell in CELLS:
        require(set(aa[cell]) == {"overall", *FILTERS}, "Incomplete A/A strata")
        for f, stat in aa[cell].items():
            for field, bound in (("gap_ci95", 0.10), ("log_ratio_ci95", math.log(1.02))):
                if stat[field][0] < -bound or stat[field][1] > bound:
                    failures.append(cell + "/" + f + "/" + field)
    benefit = {
        f: {
            "confidence_bound_saving": stat["gap_upper_adjusted"] <= -0.10
            and stat["log_ratio_upper_adjusted"] <= math.log(0.98),
            "saving_both_blocks": all(g < 0 for g in stat["block_gap_ms"].values()),
        }
        for f, stat in comparison.items()
    }
    status = (
        "measurement_inconclusive"
        if failures
        else "promising_warm_context_frontier"
        if any(all(v.values()) for v in benefit.values())
        else "closed_negative_economics"
    )
    return {
        **result,
        "status": status,
        "aa_assessed": True,
        "aa": {
            "interval_checks": 16,
            "failures": failures,
            "status": "pass" if not failures else "measurement_inconclusive",
        },
        "benefit": benefit,
        "qualifying_contexts": []
        if failures
        else [f for f, v in benefit.items() if all(v.values())],
        "benefit_multiplicity": {
            "endpoints": 8,
            "family_alpha": 0.05,
            "one_sided_quantile": 0.99375,
        },
    }


def analyze(campaign, package, output):
    campaign, package, output = map(Path, (campaign, package, output))
    cfg = verify(package)
    name = campaign_identity(campaign, package)
    rows, quality, lock, status, charges = validate_run(campaign, package, cfg)
    aa, comparison = None, None
    if quality["pass"]:

        def grouped(values):
            return {
                f: summary([r for r in values if f == "overall" or r["stratum"] == f])
                for f in ["overall", *FILTERS]
            }

        aa = {cell: grouped(contrasts(rows, cell)) for cell in CELLS}
        comparison = grouped(contrasts(rows, "exact10", "native640"))
    result = {
        "version": cfg["version"],
        "campaign": name,
        "package_manifest_sha256": sha(package / "manifest.json"),
        "gate": gates(quality, aa, comparison),
        "quality": quality,
        "aa": aa,
        "comparison": comparison,
        "actual": status,
        "counts": COUNTS,
        "criteria": CRITERIA,
        "scope": cfg["measurement_scope"],
        "charges": charges,
        "diagnostic_outer_ms": {
            "qualification_plans": sum(
                packet["charge"]["outer_ms"]
                for case in read(Path(campaign) / "run/qualification.json")["cases"]
                for phase in case["plans"].values()
                for packet in phase.values()
            ),
            "quality_and_warm_plans": sum(
                p["packet"]["charge"]["outer_ms"]
                for p in lines(Path(campaign) / "run/plan-audits.jsonl")
            ),
            "catalogs": sum(
                c["charge"]["outer_ms"]
                for c in read(Path(campaign) / "run/metadata.json")["catalogs"]
            ),
        },
        "raw_files_sha256": {"run/" + n: h for n, h in lock["files_sha256"].items()},
        "provider_calls": 0,
        "confirmation_queries": 0,
        "new_fits": 0,
        "pointwise_quality_and_aa_intervals": True,
        "benefit_bounds_multiplicity_adjusted": True,
        "independent_confirmation": False,
        "original_execution_retained": True,
    }
    output.mkdir(parents=True, exist_ok=True)
    save(output / "performance.json", result)
    text = [
        "B2b exact10 versus native640: " + result["gate"]["status"],
        "Development and warm-only diagnostic. Original execution retained; "
        "no activation, routing or serving acceptance.",
        "Campaign from verified submission: " + name,
        "Searches: " + str(status["backend_searches"]) + "; quality pass: " + str(quality["pass"]),
    ]
    for f, stat in quality["strata"].items():
        text.append(
            f"{f} recall_exact10-native640: {stat['recall_delta']:.8f} "
            f"CI{stat['recall_delta_ci95']}"
        )
    if comparison:
        text.append("Warm A/A: " + result["gate"]["aa"]["status"])
        text.append(
            "Prospective qualifying contexts (no router): "
            + str(result["gate"]["qualifying_contexts"])
        )
        for f, stat in comparison.items():
            text.append(f"{f} outer_exact10-native640: {stat['gap_ms']:.6f}ms CI{stat['gap_ci95']}")
            text.append(
                f"{f} adjusted upper gap={stat['gap_upper_adjusted']:.6f}ms; "
                f"adjusted upper log-ratio={stat['log_ratio_upper_adjusted']:.8f}"
            )
    with (output / "report.txt").open("x") as handle:
        handle.write("\n".join(text) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign", type=Path)
    parser.add_argument("package", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.campaign, args.package, args.output)
