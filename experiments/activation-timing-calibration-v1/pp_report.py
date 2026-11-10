"""Trusted replay of conditioned activation crossovers; no returned code executes."""

import argparse
import math
import random
from pathlib import Path

from pp_common import (
    ARMS,
    CELLS,
    COUNTS,
    CRITERIA,
    FILTERS,
    SEMANTIC_ARMS,
    bootstrap,
    digest,
    lines,
    read,
    safe_file,
    save,
    sha,
    verify,
)


def unique(rows, key):
    result = {}
    for row in rows:
        k = key(row)
        if k in result:
            raise ValueError("Duplicate raw identity: " + str(k))
        result[k] = row
    return result


def finite(value, *, positive=False):
    if (
        type(value) not in (int, float)
        or not math.isfinite(value)
        or value < 0
        or (positive and value <= 0)
    ):
        raise ValueError("Invalid duration")


def comparisons(rows, semantic, treatment, baseline):
    indexed = unique(
        rows,
        lambda r: (r["block"], r["query_id"], r["arm"], r["round"], r["regime"], r["repetition"]),
    )
    result = []
    for r in rows:
        if r["arm"] not in {v + "/" + semantic for v in treatment}:
            continue
        refs = [
            indexed[
                (
                    r["block"],
                    r["query_id"],
                    v + "/" + semantic,
                    r["round"],
                    r["regime"],
                    r["repetition"],
                )
            ]
            for v in baseline
        ]
        if any(
            (r["policy_ids"], r["policy_distances"], r["policy_recall"])
            != (old["policy_ids"], old["policy_distances"], old["policy_recall"])
            for old in refs
        ):
            raise ValueError("Execution versions differ in outputs/quality")
        result.append(
            {
                **r,
                "native_ms": sum(v["policy_ms"] for v in refs) / len(refs),
                "native_outer_ms": sum(v["policy_outer_ms"] for v in refs) / len(refs),
                "native_recall": r["policy_recall"],
                "recall_delta": 0.0,
                "ordinary_native_B_minus_A_ms": r["native_ms"]
                - sum(v["native_ms"] for v in refs) / len(refs),
            }
        )
    return result


def calibration_gate(aa):
    if set(aa) != set(CELLS):
        raise ValueError("Missing/unexpected A/A control cell")
    for regimes in aa.values():
        if set(regimes) != {"activation-cold", "reused-warm"}:
            raise ValueError("Missing A/A regime")
        if any(set(record["per_filter"]) != set(FILTERS) for record in regimes.values()):
            raise ValueError("Missing A/A filter stratum")
    failures = []
    for cell, regimes in aa.items():
        for regime, report in regimes.items():
            for stratum, s in [("overall", report["overall"]), *report["per_filter"].items()]:
                for field, bound in [
                    ("gap_ci95", CRITERIA["aa_equivalence_ms"]),
                    ("outer_gap_ci95", CRITERIA["aa_equivalence_ms"]),
                    ("log_latency_ratio_ci95", math.log(CRITERIA["aa_equivalence_ratio"])),
                ]:
                    if s[field][0] < -bound or s[field][1] > bound:
                        failures.append(
                            f"{cell}/{regime}/{stratum}: {field} outside fixed equivalence band"
                        )
    return {
        "verdict": "pass" if not failures else "measurement_inconclusive",
        "failures": failures,
        "all_native_original_P2a_P2b_cells_required": True,
        "absolute_band_ms": CRITERIA["aa_equivalence_ms"],
        "log_ratio_band": math.log(CRITERIA["aa_equivalence_ratio"]),
        "scope": (
            "Explicitly conditioned index/query, fresh policy/session activation only; "
            "no serving acceptance."
        ),
    }


def analyze(campaign, package, output):
    campaign, package, output = map(Path, (campaign, package, output))
    cfg = verify(package)
    bootstrap(package)
    from contract import digest as composite_digest
    from fannagent_pgvector.profiles import PROFILE
    from fd_policy_tools import predict
    from p2b_report_reference import gate as frozen_engineering_gate
    from policy import route, validate
    from pp_measure import pair_rng, policies, schedule
    from report import validate_row
    from study_stats import feasible, with_filters

    from fannagent.api import validate_policy

    source_cfg = read(package / "frozen/experiment.json")
    items = lines(package / "frozen/inputs/queries.jsonl")
    inventory = unique(items, lambda i: i["query"]["id"])
    pins = read(package / "reference-pins.json")
    raw_policies = policies(package)
    expected_identity = {}
    tree_hashes = {}
    for cell in CELLS:
        variant, semantic = cell.split("/")
        raw = raw_policies[semantic]
        if variant == "native":
            expected_identity[cell] = digest(["plain-native-calibration-v1"])
        else:
            normalized = {**raw, "eligible": cfg["filters"]} if not raw["eligible"] else raw
            identity = validate(normalized, source_cfg)[1]
            expected_identity[cell] = (
                composite_digest(["host-native-only", identity])
                if not raw["eligible"]
                else identity
            )
            tree_hashes[cell] = validate_policy(raw["tree"], PROFILE).policy_hash
    all_rows = []
    raw_hashes = {}
    block_metadata = {}
    ref_identity = None
    for block in range(COUNTS["allocations"]):
        folder = campaign / "blocks" / f"block-{block}"
        status = read(folder / "status.json")
        expected_status = {
            "block": block,
            "backend_searches": COUNTS["searches_per_block"],
            "retained_pairs": COUNTS["retained_pairs_per_block"],
            "warmup_pairs": COUNTS["warmups_per_block"],
            "conditioning_searches": COUNTS["conditioning_searches_per_block"],
            "slots": COUNTS["slots_per_block"],
            "development_cases": COUNTS["cases"],
            "independent_vectors": COUNTS["development_vectors"],
            "diagnostic_pairs": 0,
            "diagnostic_cases": 0,
            "control_installations": COUNTS["control_evictions_per_block"],
            "provider_calls": 0,
            "confirmation_queries": 0,
            "status": "complete",
        }
        if (
            any(status.get(k) != v for k, v in expected_status.items())
            or sum(status["operations"].values()) != status["backend_searches"]
        ):
            raise ValueError("Incomplete/changed status or search accounting")
        for name in ["job-exit.json", "host-exit.json"]:
            if read(folder / name)["exit_code"] != 0:
                raise ValueError("Runtime/host/cleanup failure")
        if read(folder / "host-exit.json").get("protected_sources_unchanged") is not True:
            raise ValueError("Host protected-source check failed")
        before = read(folder / "protected-source-before.json")
        if before != read(folder / "protected-source-after.json") or before != read(
            campaign / "protected-source-before.json"
        ):
            raise ValueError("Protected source changed")
        if read(folder / "runtime-identity.json") != {
            "module_sha256": source_cfg["module_sha256"],
            "registry_hash": PROFILE.native_registry_hash,
            "runtime_profile_hash": PROFILE.fingerprint,
            "package_manifest_sha256": sha(package / "manifest.json"),
            "image_sha256": source_cfg["image_sha256"],
        }:
            raise ValueError("Runtime/module/profile identity changed")
        if read(folder / "database-identity.json") != read(package / "frozen/source-index.json"):
            raise ValueError("Physical index changed")
        getters = read(folder / "qualified-features.json")
        if sum(g["backend_calls"] for g in getters) != 921 or any(
            g["status"] != "passed" for g in getters
        ):
            raise ValueError("Getter qualification differs")
        lock = read(folder / "LOCK.json")
        required = {
            "status.json",
            "job-exit.json",
            "runtime-identity.json",
            "database-identity.json",
            "qualified-features.json",
            "references.jsonl",
            "proofs.jsonl",
            "pairs.jsonl",
            "warmups.jsonl",
            "conditioning.jsonl",
            "slots.jsonl",
        }
        if lock["package_manifest_sha256"] != sha(package / "manifest.json") or not required <= set(
            lock["files_sha256"]
        ):
            raise ValueError("Incomplete raw lock")
        for name, value in lock["files_sha256"].items():
            if sha(safe_file(folder, name)) != value:
                raise ValueError("Raw hash differs: " + name)
            raw_hashes[f"blocks/block-{block}/" + name] = value
        refs = unique(lines(folder / "references.jsonl"), lambda r: r["query_id"])
        if set(refs) != set(inventory) or any(digest(v) != pins[q] for q, v in refs.items()):
            raise ValueError("Pinned reference/trajectory changed")
        if ref_identity is not None and digest(refs) != ref_identity:
            raise ValueError("References changed across blocks")
        ref_identity = digest(refs)
        proofs = unique(lines(folder / "proofs.jsonl"), lambda r: (r["query_id"], r["cell"]))
        if set(proofs) != {(q, c) for q in inventory for c in CELLS}:
            raise ValueError("Proof coverage differs")
        for (qid, cell), proof in proofs.items():
            variant, semantic = cell.split("/")
            raw = raw_policies[semantic]
            ref = refs[qid]
            bypass = variant == "native" or route(inventory[qid]["query"]) not in raw["eligible"]
            cp = None if bypass else predict(raw["tree"], ref["states"], PROFILE)
            expected_prefix = (
                None if bypass else digest(ref["states"] if cp is None else ref["states"][:cp])
            )
            if (
                proof["native_bypass"],
                proof["checkpoint"],
                proof["prefix_sha256"],
                proof["composite_hash"],
            ) != (bypass, cp, expected_prefix, expected_identity[cell]):
                raise ValueError("Actual route/stop proof differs")
            if (bypass or cp is None) and (proof["policy_ids"], proof["policy_distances"]) != (
                ref["native_ids"],
                ref["native_distances"],
            ):
                raise ValueError("Native/continue proof changed")
        ordered = items.copy()
        random.Random(cfg["seed"] + block).shuffle(ordered)
        expected = [
            (i["query"]["id"], meta) for i in ordered for meta in schedule(i["query"]["id"], block)
        ]
        slots = lines(folder / "slots.jsonl")
        if len(slots) != len(expected):
            raise ValueError("Slot coverage differs")
        slot_map = {}
        expected_pairs = []
        expected_warmups = []
        expected_conditioning = []
        for (qid, meta), slot in zip(expected, slots):
            if (
                slot["query_id"] != qid
                or slot["block"] != block
                or any(slot.get(k) != v for k, v in meta.items())
            ):
                raise ValueError("Physical slot order/identity differs")
            if slot["conditioning_calls"] != COUNTS["conditioning_calls_per_slot"] or any(
                slot.get(k) is not True
                for k in [
                    "cache_empty_after_conditioning",
                    "cache_empty_after_constructor",
                    "installation_unchanged_until_first_pair",
                ]
            ):
                raise ValueError("Conditioning/constructor warmed policy state")
            times = [
                slot[k]
                for k in [
                    "started_ns",
                    "conditioned_ns",
                    "constructor_started_ns",
                    "constructor_finished_ns",
                    "finished_ns",
                ]
            ]
            if any(type(t) is not int for t in times) or times != sorted(times):
                raise ValueError("Invalid phase boundaries")
            finite(slot["preparation_ms"], positive=True)
            if (
                slot["preparation_ms"]
                > (slot["constructor_finished_ns"] - slot["constructor_started_ns"]) / 1e6 + 1e-6
            ):
                raise ValueError("Constructor accounting outside phase")
            key = (qid, meta["cell"], meta["round"], meta["label"])
            slot_map[key] = slot
            for conditioner in range(COUNTS["conditioning_calls_per_slot"]):
                expected_conditioning.append((key, conditioner))
            for rep in range(5):
                identity = (
                    qid,
                    meta["arm"],
                    meta["round"],
                    "activation-cold" if rep == 0 else "reused-warm",
                    0 if rep == 0 else rep - 2,
                )
                (expected_warmups if rep == 1 else expected_pairs).append(identity)
        conditioning = lines(folder / "conditioning.jsonl")
        previous_conditioner_end = {}
        if len(conditioning) != len(expected_conditioning):
            raise ValueError("Conditioning coverage differs")
        for (key, number), r in zip(expected_conditioning, conditioning):
            qid, cell, round_index, label = key
            slot = slot_map[key]
            if (r["query_id"], r["cell"], r["round"], r["label"], r["conditioner"], r["block"]) != (
                qid,
                cell,
                round_index,
                label,
                number,
                block,
            ):
                raise ValueError("Conditioning physical order differs")
            if any(
                r.get(k) != slot[k]
                for k in [
                    "arm",
                    "cell_position",
                    "cell_order_sha256",
                    "slot_position",
                    "label_order",
                ]
            ):
                raise ValueError("Conditioning schedule metadata differs")
            if type(r["started_ns"]) is not int or type(r["finished_ns"]) is not int:
                raise ValueError("Conditioning timestamps must be integer nanoseconds")
            if key in previous_conditioner_end and r["started_ns"] < previous_conditioner_end[key]:
                raise ValueError("Overlapping conditioning calls")
            previous_conditioner_end[key] = r["finished_ns"]
            for k in ["latency_ms", "outer_ms"]:
                finite(r[k], positive=True)
            if (
                not slot["started_ns"]
                <= r["started_ns"]
                < r["finished_ns"]
                <= slot["conditioned_ns"]
            ):
                raise ValueError("Conditioning outside declared boundary")
            if r["output_sha256"] != digest(
                [refs[qid]["native_ids"], refs[qid]["native_distances"]]
            ):
                raise ValueError("Conditioning output differs")
        timing_by_slot = {k: [] for k in slot_map}
        for filename, expected_keys, retained in [
            ("pairs.jsonl", expected_pairs, True),
            ("warmups.jsonl", expected_warmups, False),
        ]:
            rows = lines(folder / filename)
            keys = [
                (r["query_id"], r["arm"], r["round"], r["regime"], r["repetition"]) for r in rows
            ]
            if keys != expected_keys:
                raise ValueError("Physical timing coverage/order differs")
            for r in rows:
                qid = r["query_id"]
                slot = slot_map[(qid, r["cell"], r["round"], r["label"])]
                proof = proofs[(qid, r["cell"])]
                if any(
                    r.get(k) != slot[k]
                    for k in [
                        "arm",
                        "cell",
                        "round",
                        "label",
                        "label_order",
                        "cell_position",
                        "cell_order_sha256",
                        "slot_position",
                    ]
                ):
                    raise ValueError("Timing schedule metadata differs")
                if (
                    r["block"] != block
                    or r["pass"] != "primary"
                    or r["group"] != inventory[qid]["group"]
                    or r["stratum"] != route(inventory[qid]["query"])
                ):
                    raise ValueError("Timing identity differs")
                if (r["composite_hash"], r["native_bypass"]) != (
                    proof["composite_hash"],
                    proof["native_bypass"],
                ):
                    raise ValueError("Timing route/policy differs")
                validate_row(r, refs[qid])
                if (r["policy_ids"], r["policy_distances"]) != (
                    proof["policy_ids"],
                    proof["policy_distances"],
                ):
                    raise ValueError("Timed output differs from proof")
                if not r["native_bypass"]:
                    count = (
                        proof["checkpoint"]
                        if proof["checkpoint"] is not None
                        else len(refs[qid]["states"])
                    )
                    if (
                        r["policy_hash"] != tree_hashes[r["cell"]]
                        or r["checkpoint_count"] != count
                        or (r["stop_reason"] == "policy_stop") != (proof["checkpoint"] is not None)
                    ):
                        raise ValueError("Timed first-stop/installation acknowledgement differs")
                rep = 0 if r["regime"] == "activation-cold" else r["repetition"] + 2
                order = ["native", "policy"]
                pair_rng(qid, r["cell"], block, r["round"], rep).shuffle(order)
                if r["order"] != order:
                    raise ValueError("Native/subject pair order differs")
                if (
                    r["regime"] == "activation-cold"
                    and r["preparation_ms"] != slot["preparation_ms"]
                ):
                    raise ValueError("Admission charge omitted/changed")
                if (
                    not slot["constructor_finished_ns"]
                    <= r["pair_started_ns"]
                    < r["pair_finished_ns"]
                    <= slot["finished_ns"]
                ):
                    raise ValueError("Execution overlaps conditioning or constructor")
                timing_by_slot[(qid, r["cell"], r["round"], r["label"])].append(r)
            if retained:
                all_rows.extend(rows)
        for group in timing_by_slot.values():
            ordered_t = sorted(group, key=lambda r: r["pair_started_ns"])
            if len(ordered_t) != 5 or any(
                a["pair_finished_ns"] > b["pair_started_ns"]
                for a, b in zip(ordered_t, ordered_t[1:])
            ):
                raise ValueError("Overlapping/incomplete pair phases")
        block_metadata[str(block)] = {
            "backend_searches": status["backend_searches"],
            "slots": len(slots),
            "conditioning_searches": len(conditioning),
            "elapsed_seconds": status["elapsed_seconds"],
            "conditioning_ann_ms_total": sum(r["latency_ms"] for r in conditioning),
            "conditioning_outer_ms_total": sum(r["outer_ms"] for r in conditioning),
            "reset_conditioning_bookkeeping_wall_ms_total": sum(
                (r["constructor_started_ns"] - r["started_ns"]) / 1e6 for r in slots
            ),
            "constructor_preparation_ms_total": sum(r["preparation_ms"] for r in slots),
        }
    stats_cfg = {**source_cfg, "seed": source_cfg["bootstrap_seed"]}

    def summary(rows):
        return with_filters(rows, stats_cfg)

    reports = {
        arm: {
            regime: {
                "statistics": summary(
                    [r for r in all_rows if r["arm"] == arm and r["regime"] == regime]
                )
            }
            for regime in ["activation-cold", "reused-warm"]
        }
        for arm in ARMS
    }
    for arm, regimes in reports.items():
        for regime, record in regimes.items():
            selected = [r for r in all_rows if r["arm"] == arm and r["regime"] == regime]
            record.update(
                current_quality_and_latency_checks_pass=bool(
                    feasible(record["statistics"], stats_cfg)
                ),
                mean_preparation_ms=sum(r["preparation_ms"] for r in selected) / len(selected),
            )
    aa = {}
    order_diagnostics = {}
    block_contrasts = {str(b): {} for b in range(COUNTS["allocations"])}
    for cell in CELLS:
        v, semantic = cell.split("/")
        rows = comparisons(all_rows, semantic, (v + "-b",), (v + "-a",))
        aa[cell] = {
            regime: summary([r for r in rows if r["regime"] == regime])
            for regime in ["activation-cold", "reused-warm"]
        }
        order_diagnostics[cell] = {}
        for regime in ["activation-cold", "reused-warm"]:
            order_diagnostics[cell][regime] = {}
            for orientation in [["a", "b"], ["b", "a"]]:
                rs = [r for r in rows if r["regime"] == regime and r["label_order"] == orientation]
                order_diagnostics[cell][regime]["".join(orientation)] = {
                    "pairs": len(rs),
                    "mean_gap_ms": sum(r["policy_ms"] - r["native_ms"] for r in rs) / len(rs),
                    "per_filter": {
                        f: {
                            "pairs": sum(r["stratum"] == f for r in rs),
                            "mean_gap_ms": sum(
                                r["policy_ms"] - r["native_ms"] for r in rs if r["stratum"] == f
                            )
                            / sum(r["stratum"] == f for r in rs),
                        }
                        for f in FILTERS
                    },
                    "by_block": {
                        str(b): {
                            "pairs": sum(r["block"] == b for r in rs),
                            "mean_gap_ms": sum(
                                r["policy_ms"] - r["native_ms"] for r in rs if r["block"] == b
                            )
                            / sum(r["block"] == b for r in rs),
                        }
                        for b in range(COUNTS["allocations"])
                    },
                    "mean_ordinary_native_gap_ms": sum(
                        r["ordinary_native_B_minus_A_ms"] for r in rs
                    )
                    / len(rs),
                }
    families = {
        "p2a_vs_original": (("owned-a", "owned-b"), ("original-a", "original-b")),
        "p2b_vs_p2a": (("admission-a", "admission-b"), ("owned-a", "owned-b")),
        "p2b_vs_original": (("admission-a", "admission-b"), ("original-a", "original-b")),
    }
    direct = {}
    direct["aa_b_vs_a"] = {a: aa["admission/" + a] for a in SEMANTIC_ARMS}
    for family, (treatment, baseline) in families.items():
        direct[family] = {}
        for b in block_contrasts.values():
            b[family] = {}
        for semantic in SEMANTIC_ARMS:
            rows = comparisons(all_rows, semantic, treatment, baseline)
            direct[family][semantic] = {
                regime: summary([r for r in rows if r["regime"] == regime])
                for regime in ["activation-cold", "reused-warm"]
            }
            for block in block_contrasts:
                block_contrasts[block][family][semantic] = {
                    regime: summary(
                        [r for r in rows if r["block"] == int(block) and r["regime"] == regime]
                    )
                    for regime in ["activation-cold", "reused-warm"]
                }
    calibration = calibration_gate(aa)
    engineering = frozen_engineering_gate(direct, block_contrasts, reports)
    engineering["frozen_P2b_gate_logic_used"] = True
    if calibration["verdict"] != "pass":
        engineering["verdict"] = "measurement_inconclusive"
    result = {
        "version": cfg["version"],
        "status": "verified",
        "package_manifest_sha256": sha(package / "manifest.json"),
        "counts": COUNTS,
        "per_block": block_metadata,
        "reports": reports,
        "aa_controls": aa,
        "order_diagnostics": order_diagnostics,
        "direct_comparisons": direct,
        "per_block_contrasts": block_contrasts,
        "calibration_gate": calibration,
        "execution_gate": engineering,
        "raw_files_sha256": raw_hashes,
        "mechanism_checks": {
            "status": "passed",
            "fixed_conditioning_before_each_fresh_session": True,
            "full_admission_and_first_installation_charged": True,
            "all_phase_and_order_coverage_verified": True,
        },
        "provider_calls": 0,
        "confirmation_queries": 0,
        "candidate_selection_performed": False,
        "canonical_acceptance_established": False,
        "retroactive_P2b_qualification": False,
        "scope": (
            "Conditioned-index fresh-session calibration only. No cold-index claim, "
            "causal correction, profiler subtraction or automatic adoption."
        ),
    }
    output.mkdir(parents=True, exist_ok=True)
    save(output / "performance.json", result)
    text = [
        "Activation timing calibration v1 — verified conditioned crossovers",
        result["scope"],
        "Calibration gate: " + calibration["verdict"],
        *calibration["failures"],
        "Execution engineering gate in this new scope: " + engineering["verdict"],
        *engineering["failures"],
        (
            "A/A differences are never subtracted. "
            "Previous P2b verdict stays measurement_inconclusive."
        ),
        "family | arm | regime | reference ms | treatment ms | gap ms | 95% gap interval",
    ]
    for family, arms in direct.items():
        for arm, regimes in arms.items():
            for regime, stats in regimes.items():
                t = stats["overall"]
                text.append(
                    f"{family} | {arm} | {regime} | {t['native_ms']:.6f} | "
                    f"{t['policy_ms']:.6f} | {t['gap_ms']:+.6f} | {t['gap_ci95']}"
                )
    (output / "report.txt").write_text("\n".join(text) + "\n")
    (output / "calibration.md").write_text(
        "# Conditioned activation calibration\n\n"
        + result["scope"]
        + "\n\n"
        + "All conditioning and reset operations are recorded and resource-counted. "
        "No policy work is moved into conditioning. "
        + "All original admission, lazy preparation, compilation, installation "
        "and query costs remain charged. "
        + "Inspect aa_controls per filter and order_diagnostics without using them as corrections. "
        + "If calibration is inconclusive, retain original and redirect; "
        "no automatic additional campaign.\n"
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign", type=Path)
    parser.add_argument("package", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.campaign, args.package, args.output)
