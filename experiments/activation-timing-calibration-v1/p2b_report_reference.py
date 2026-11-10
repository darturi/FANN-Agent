"""Trusted raw-data replay; profiling is kept separate from primary statistics."""

import argparse
import math
import random
from pathlib import Path

from pp_common import (
    ARMS,
    COUNTS,
    CRITERIA,
    SEMANTIC_ARMS,
    bootstrap,
    digest,
    lines,
    read,
    save,
    sha,
    verify,
)


def contrast_rows(rows, arm, treatment=("owned",), baseline="original"):
    keyed = unique(
        rows, lambda r: (r["block"], r["query_id"], r["arm"], r["regime"], r["repetition"])
    )
    result = []
    for row in rows:
        if row["arm"] not in {v + "/" + arm for v in treatment}:
            continue
        old = keyed[
            (row["block"], row["query_id"], baseline + "/" + arm, row["regime"], row["repetition"])
        ]
        if (row["policy_ids"], row["policy_distances"], row["policy_recall"]) != (
            old["policy_ids"],
            old["policy_distances"],
            old["policy_recall"],
        ):
            raise ValueError("Original/owned results differ")
        # Direct new-policy versus old-policy contrast, without subtracting the
        # two arms' independently summarized native gaps.
        result.append(
            {
                **row,
                "native_ms": old["policy_ms"],
                "native_outer_ms": old["policy_outer_ms"],
                "native_recall": old["policy_recall"],
                "recall_delta": 0.0,
            }
        )
    return result


def mechanism_checks(profiles):
    checked = 0
    for block, data in profiles.items():
        for key, group in data["groups"].items():
            arm, stratum, phase = key.rsplit("/", 2)
            variant, semantic = arm.split("/")
            eligible = semantic != "routed-native" and stratum != "votes108"
            expected = (
                group["calls"]
                if eligible
                and phase != "prepare"
                and (variant == "original" or phase == "activation")
                else 0
            )
            calls = sum(
                r["total_calls"]
                for r in group["functions"]
                if "/fannagent_pgvector/prepared.py:" in r["function"]
                and r["function"].endswith(":prepare")
            )
            if calls != expected:
                raise ValueError(f"Prepared-call mechanism differs: block {block}/{key}")
            fingerprint_calls = sum(
                r["total_calls"]
                for r in group["functions"]
                if "/fannagent/api/profiles.py:" in r["function"]
                and r["function"].endswith(":fingerprint")
            )
            if phase == "prepare":
                expected_fingerprints = group["calls"] * (
                    1 if variant.startswith("admission-") else 4
                )
                if fingerprint_calls != expected_fingerprints:
                    raise ValueError(
                        f"Admission fingerprint mechanism differs: block {block}/{key}"
                    )
                if variant.startswith("admission-"):
                    snapshots = sum(
                        r["total_calls"]
                        for r in group["functions"]
                        if "/pb_session.py:" in r["function"] and r["function"].endswith(":capture")
                    )
                    if snapshots != group["calls"]:
                        raise ValueError("Admission snapshot count differs")
            checked += 1
    return {
        "status": "passed",
        "profile_groups_checked": checked,
        "owned_reuse_cache_prepare_calls": 0,
        "first_prepare_charged_to_activation_backend_timer": True,
        "admission_fingerprints_per_constructor": 1,
        "original_and_p2a_fingerprints_per_constructor": 4,
        "snapshot_and_fingerprint_charged_to_preparation": True,
    }


def gate(comparisons, block_contrasts, reports):
    failures = []
    aa_failures = []

    def cells(regimes):
        for regime, record in regimes.items():
            for stratum, stat in [("overall", record["overall"]), *record["per_filter"].items()]:
                yield regime, stratum, stat

    for arm, regimes in reports.items():
        for regime, record in regimes.items():
            stats = record["statistics"]
            for stratum, stat in [("overall", stats["overall"]), *stats["per_filter"].items()]:
                key = f"{arm}/{regime}/{stratum}"
                if not stat["all_valid"] or stat["recall_delta_ci95"][0] < -0.0025:
                    failures.append(key + ": validity/development recall reserve fails")
                if stratum != "overall" and stat["native_recall"] < 0.95:
                    failures.append(key + ": native recall floor fails")
    for arm, regimes in comparisons["aa_b_vs_a"].items():
        for regime, stratum, stat in cells(regimes):
            key = f"A/A/{arm}/{regime}/{stratum}"
            for field in ("gap_ci95", "outer_gap_ci95"):
                lo, hi = stat[field]
                if lo < -CRITERIA["aa_equivalence_ms"] or hi > CRITERIA["aa_equivalence_ms"]:
                    aa_failures.append(key + ": " + field + " not contained in +/-0.10 ms")
            lo, hi = stat["log_latency_ratio_ci95"]
            bound = math.log(CRITERIA["aa_equivalence_ratio"])
            if lo < -bound or hi > bound:
                aa_failures.append(key + ": log ratio not contained in +/-log(1.02)")
    for family in ("p2b_vs_p2a", "p2b_vs_original"):
        for arm, regimes in comparisons[family].items():
            for regime, stratum, stat in cells(regimes):
                key = f"{family}/{arm}/{regime}/{stratum}"
                if stat["gap_ci95"][1] > CRITERIA["maximum_regression_ms"]:
                    failures.append(key + ": primary regression exceeds 0.10 ms")
                if stat["outer_gap_ci95"][1] > CRITERIA["maximum_regression_ms"]:
                    failures.append(key + ": outer regression exceeds 0.10 ms")
                if stat["log_latency_ratio_ci95"][1] > math.log(
                    CRITERIA["maximum_regression_ratio"]
                ):
                    failures.append(key + ": primary regression exceeds 2%")
    # Admission is the incremental target; separately retain the combined reuse gain.
    for family, regime, minimum_key, ratio_key in [
        (
            "p2b_vs_p2a",
            "activation-cold",
            "activation_minimum_saving_ms",
            "activation_maximum_ratio",
        ),
        (
            "p2b_vs_original",
            "reused-warm",
            "candidate_reuse_minimum_saving_ms",
            "candidate_reuse_maximum_ratio",
        ),
    ]:
        stat = comparisons[family]["candidate"][regime]["overall"]
        for field in ("gap_ci95", "outer_gap_ci95"):
            if stat[field][1] > -CRITERIA[minimum_key]:
                failures.append(f"{family}/{regime}: {field} saving lower bound below 0.10 ms")
        if stat["log_latency_ratio_ci95"][1] > math.log(CRITERIA[ratio_key]):
            failures.append(f"{family}/{regime}: relative saving lower bound below 2%")
        if any(
            block[family]["candidate"][regime]["overall"]["gap_ms"] >= 0
            for block in block_contrasts.values()
        ):
            failures.append(f"{family}/{regime}: saving direction not present in every block")
    return {
        "criteria": CRITERIA,
        "verdict": (
            "measurement_inconclusive"
            if aa_failures
            else "revise_or_retain_original"
            if failures
            else "pass"
        ),
        "failures": failures,
        "aa_failures": aa_failures,
        "aa_verdict": "equivalent_within_declared_bounds" if not aa_failures else "not_established",
        "scope": (
            "Engineering only; no confirmation, selection, M1 or acceptance. "
            "A/A never corrects gaps."
        ),
    }


def unique(rows, key):
    result = {}
    for row in rows:
        identity = key(row)
        if identity in result:
            raise ValueError("Duplicate result identity: " + str(identity))
        result[identity] = row
    return result


def validate_profiles(data):
    expected = {
        arm + "/" + stratum + "/" + phase: COUNTS["diagnostic_vectors"]
        * (COUNTS["reuse_repetitions"] if phase == "reuse" else 1)
        for arm in ARMS
        for stratum in ["unfiltered", "votes32", "votes108"]
        for phase in ["prepare", "activation", "warmup", "reuse"]
    }
    if data.get("version") != "cprofile-attribution.v1" or data.get("diagnostic_only") is not True:
        raise ValueError("Profiles lack diagnostic identity")
    if set(data["groups"]) != set(expected):
        raise ValueError("Profile group coverage differs")
    for key, calls in expected.items():
        group = data["groups"][key]
        if group["calls"] != calls or not math.isfinite(group["wall_ms"]) or group["wall_ms"] <= 0:
            raise ValueError("Profile count/time differs: " + key)
        if not group["functions"]:
            raise ValueError("Empty profile: " + key)
        seen = set()
        for row in group["functions"]:
            if row["function"] in seen:
                raise ValueError("Duplicate function profile")
            seen.add(row["function"])
            if type(row["primitive_calls"]) is not int or type(row["total_calls"]) is not int:
                raise ValueError("Noninteger profile count")
            if not 0 <= row["primitive_calls"] <= row["total_calls"]:
                raise ValueError("Invalid profile count")
            for field in ("self_ms", "cumulative_ms"):
                if not math.isfinite(row[field]) or row[field] < 0:
                    raise ValueError("Invalid function duration")
            if row["self_ms"] > row["cumulative_ms"] + 1e-6:
                raise ValueError("Self time exceeds inclusive time")
        if sum(row["self_ms"] for row in group["functions"]) > group["wall_ms"] * 1.05 + 0.01:
            raise ValueError("Exclusive profile times exceed wall time")


def expected_rows(items):
    retained = {
        (i["query"]["id"], arm, regime, repetition)
        for i in items
        for arm in ARMS
        for regime, repetition in [
            ("activation-cold", 0),
            ("reused-warm", 0),
            ("reused-warm", 1),
            ("reused-warm", 2),
        ]
    }
    warmups = {(i["query"]["id"], arm, "reused-warm", -1) for i in items for arm in ARMS}
    return retained, warmups


def analyze(campaign, package, output):
    campaign, package, output = Path(campaign), Path(package), Path(output)
    cfg = verify(package)
    bootstrap(package)
    from contract import digest as original_digest
    from fannagent_pgvector.profiles import PROFILE
    from fd_policy_tools import predict
    from policy import route, validate
    from pp_measure import arms, pair_rng, schedule_metadata
    from report import validate_row
    from study_stats import feasible, with_filters

    source_cfg = read(package / "frozen/experiment.json")
    items = lines(package / "frozen/inputs/queries.jsonl")
    inventory = unique(items, lambda i: i["query"]["id"])
    pins = read(package / "reference-pins.json")
    diagnostic = [i for i in items if i["group"] in cfg["diagnostic_groups"]]
    arm_map = {name: raw for name, raw, _ in arms(package)}
    primary_rows = []
    diagnostic_rows = []
    block_reports = {}
    raw_hashes = {}
    profiles = {}
    expected_proofs = {(qid, arm) for qid in inventory for arm in ARMS}
    all_reference_identity = None
    for block in range(COUNTS["allocations"]):
        folder = campaign / "blocks" / ("block-" + str(block))
        status = read(folder / "status.json")
        if (
            status["status"] != "complete"
            or status["block"] != block
            or status["provider_calls"] != 0
            or status["confirmation_queries"] != 0
        ):
            raise ValueError("Block not complete/provider-free/development-only")
        expected_status = {
            "backend_searches": COUNTS["searches_per_block"],
            "retained_pairs": COUNTS["retained_pairs_per_block"],
            "diagnostic_pairs": COUNTS["diagnostic_pairs_per_block"],
            "development_cases": COUNTS["cases"],
            "independent_vectors": COUNTS["development_vectors"],
            "diagnostic_cases": COUNTS["diagnostic_cases"],
            "control_installations": COUNTS["control_evictions_per_block"],
        }
        if any(status.get(key) != value for key, value in expected_status.items()):
            raise ValueError("Block count differs")
        if sum(status["operations"].values()) != status["backend_searches"]:
            raise ValueError("Search operation receipt differs")
        for name in ("job-exit.json", "host-exit.json"):
            if read(folder / name)["exit_code"] != 0:
                raise ValueError("Failed runtime/host/cleanup")
        before, after = (
            read(folder / "protected-source-before.json"),
            read(folder / "protected-source-after.json"),
        )
        if before != after or before != read(campaign / "protected-source-before.json"):
            raise ValueError("Protected inputs changed")
        runtime = read(folder / "runtime-identity.json")
        expected_runtime = {
            "module_sha256": source_cfg["module_sha256"],
            "registry_hash": PROFILE.native_registry_hash,
            "runtime_profile_hash": PROFILE.fingerprint,
            "package_manifest_sha256": sha(package / "manifest.json"),
            "image_sha256": source_cfg["image_sha256"],
        }
        if runtime != expected_runtime or read(folder / "database-identity.json") != read(
            package / "frozen/source-index.json"
        ):
            raise ValueError("Runtime/index/profile identity differs")
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
            "diagnostic-pairs.jsonl",
            "diagnostic-warmups.jsonl",
            "profiles.json",
        }
        if lock["package_manifest_sha256"] != sha(package / "manifest.json") or not required <= set(
            lock["files_sha256"]
        ):
            raise ValueError("Incomplete raw lock")
        for name, expected in lock["files_sha256"].items():
            from pp_common import safe_file

            if sha(safe_file(folder, name)) != expected:
                raise ValueError("Raw result hash differs: " + name)
            raw_hashes["blocks/block-" + str(block) + "/" + name] = expected
        refs = unique(lines(folder / "references.jsonl"), lambda r: r["query_id"])
        if set(refs) != set(inventory):
            raise ValueError("Reference coverage differs")
        for qid, ref in refs.items():
            if digest(ref) != pins[qid]:
                raise ValueError("Native/exact reference or qualified trajectory changed: " + qid)
        identity = digest(refs)
        if all_reference_identity is not None and all_reference_identity != identity:
            raise ValueError("References differ between blocks")
        all_reference_identity = identity
        proofs = unique(lines(folder / "proofs.jsonl"), lambda p: (p["query_id"], p["arm"]))
        if set(proofs) != expected_proofs:
            raise ValueError("Proof coverage differs")
        expected_identity = {}
        expected_tree_hash = {}
        for name, raw in arm_map.items():
            validating = {**raw, "eligible": cfg["filters"]} if not raw["eligible"] else raw
            identity = validate(validating, source_cfg)[1]
            expected_identity[name] = (
                original_digest(["host-native-only", identity]) if not raw["eligible"] else identity
            )
            from fannagent.api import validate_policy

            expected_tree_hash[name] = validate_policy(raw["tree"], PROFILE).policy_hash
        for (qid, arm), proof in proofs.items():
            raw = arm_map[arm]
            ref = refs[qid]
            bypass = route(inventory[qid]["query"]) not in raw["eligible"]
            cp = None if bypass else predict(raw["tree"], ref["states"], PROFILE)
            expected_prefix = (
                None if bypass else digest(ref["states"] if cp is None else ref["states"][:cp])
            )
            if (
                proof["checkpoint"],
                proof["native_bypass"],
                proof["prefix_sha256"],
                proof["composite_hash"],
            ) != (cp, bypass, expected_prefix, expected_identity[arm]):
                raise ValueError("Actual route/first-stop proof differs")
            if (bypass or cp is None) and (proof["policy_ids"], proof["policy_distances"]) != (
                ref["native_ids"],
                ref["native_distances"],
            ):
                raise ValueError("Native/continue proof differs")
        for pass_name, selected, filenames, destination in [
            ("primary", items, ("pairs.jsonl", "warmups.jsonl"), primary_rows),
            (
                "diagnostic",
                diagnostic,
                ("diagnostic-pairs.jsonl", "diagnostic-warmups.jsonl"),
                diagnostic_rows,
            ),
        ]:
            retained_keys, warmup_keys = expected_rows(selected)
            for filename, expected, retained in [
                (filenames[0], retained_keys, True),
                (filenames[1], warmup_keys, False),
            ]:
                rows = lines(folder / filename)
                keyed = unique(
                    rows, lambda r: (r["query_id"], r["arm"], r["regime"], r["repetition"])
                )
                if set(keyed) != expected:
                    raise ValueError("Missing/unexpected measurement rows: " + filename)
                scheduled = items.copy()
                random.Random(cfg["seed"] + block).shuffle(scheduled)
                selected_ids = {i["query"]["id"] for i in selected}
                schedule_keys = []
                from pp_measure import ordered_arms

                for item in scheduled:
                    qid = item["query"]["id"]
                    if qid not in selected_ids:
                        continue
                    for arm, _, _ in ordered_arms(package, qid, block):
                        for rep in range(5):
                            key = (
                                qid,
                                arm,
                                "activation-cold" if rep == 0 else "reused-warm",
                                0 if rep == 0 else rep - 2,
                            )
                            if (rep != 1) == retained:
                                schedule_keys.append(key)
                actual_keys = [
                    (r["query_id"], r["arm"], r["regime"], r["repetition"]) for r in rows
                ]
                if actual_keys != schedule_keys:
                    raise ValueError("Physical measurement/query order differs")
                for row in rows:
                    qid, arm = row["query_id"], row["arm"]
                    proof = proofs[(qid, arm)]
                    if (
                        row["block"] != block
                        or row["pass"] != pass_name
                        or row["group"] != inventory[qid]["group"]
                        or row["stratum"] != route(inventory[qid]["query"])
                    ):
                        raise ValueError("Measurement identity differs")
                    schedule = schedule_metadata(package, qid, arm, block)
                    if any(row.get(key) != value for key, value in schedule.items()):
                        raise ValueError("Variant position/schedule differs")
                    rep = 0 if row["regime"] == "activation-cold" else row["repetition"] + 2
                    order = ["native", "policy"]
                    pair_rng(qid, arm, block, rep).shuffle(order)
                    if row["order"] != order:
                        raise ValueError("Native/policy paired order differs")
                    if (
                        row["composite_hash"] != expected_identity[arm]
                        or row["native_bypass"] != proof["native_bypass"]
                    ):
                        raise ValueError("Measurement policy/route differs")
                    validate_row(row, refs[qid])
                    if (row["policy_ids"], row["policy_distances"]) != (
                        proof["policy_ids"],
                        proof["policy_distances"],
                    ):
                        raise ValueError("Timed result differs from proof")
                    if not row["native_bypass"]:
                        expected_cp = proof["checkpoint"]
                        count = expected_cp if expected_cp is not None else len(refs[qid]["states"])
                        if row["policy_hash"] != expected_tree_hash[arm]:
                            raise ValueError("Native tree hash differs")
                        if row["checkpoint_count"] != count or (
                            row["stop_reason"] == "policy_stop"
                        ) != (expected_cp is not None):
                            raise ValueError("Timed first stop differs")
                if retained:
                    destination.extend(rows)
        profile = read(folder / "profiles.json")
        validate_profiles(profile)
        profiles[str(block)] = profile
        stats_cfg = {**source_cfg, "seed": source_cfg["bootstrap_seed"]}
        block_primary = [r for r in primary_rows if r["block"] == block]
        block_reports[str(block)] = {
            arm: {
                regime: with_filters(
                    [r for r in block_primary if r["arm"] == arm and r["regime"] == regime],
                    stats_cfg,
                )
                for regime in ["activation-cold", "reused-warm"]
            }
            for arm in ARMS
        }
    stats_cfg = {**source_cfg, "seed": source_cfg["bootstrap_seed"]}
    reports = {}
    for arm in ARMS:
        reports[arm] = {}
        for regime in ["activation-cold", "reused-warm"]:
            rows = [r for r in primary_rows if r["arm"] == arm and r["regime"] == regime]
            stats = with_filters(rows, stats_cfg)
            reports[arm][regime] = {
                "statistics": stats,
                "current_quality_and_latency_checks_pass": bool(feasible(stats, stats_cfg)),
                "mean_preparation_ms": sum(r["preparation_ms"] for r in rows) / len(rows),
                "mean_routing_ms": sum(r["routing_ms"] for r in rows) / len(rows),
                "mean_ann_ms": sum(r["policy_ann_ms"] for r in rows) / len(rows),
            }
    families = {
        "p2a_vs_original": (("owned",), "original"),
        "p2b_vs_p2a": (("admission-a", "admission-b"), "owned"),
        "p2b_vs_original": (("admission-a", "admission-b"), "original"),
        "aa_b_vs_a": (("admission-b",), "admission-a"),
    }
    comparisons = {}
    block_contrasts = {str(b): {} for b in range(COUNTS["allocations"])}
    for family, (treatment, baseline) in families.items():
        comparisons[family] = {}
        for block in block_contrasts.values():
            block[family] = {}
        for arm in SEMANTIC_ARMS:
            contrast = contrast_rows(primary_rows, arm, treatment, baseline)
            comparisons[family][arm] = {
                regime: with_filters([r for r in contrast if r["regime"] == regime], stats_cfg)
                for regime in ["activation-cold", "reused-warm"]
            }
            for b in range(COUNTS["allocations"]):
                block_contrasts[str(b)][family][arm] = {
                    regime: with_filters(
                        [r for r in contrast if r["block"] == b and r["regime"] == regime],
                        stats_cfg,
                    )
                    for regime in ["activation-cold", "reused-warm"]
                }
            # Diagnostic outputs must also preserve all four variant identities.
            contrast_rows(diagnostic_rows, arm, treatment, baseline)
    mechanism = mechanism_checks(profiles)
    result = {
        "version": cfg["version"],
        "status": "verified",
        "package_manifest_sha256": sha(package / "manifest.json"),
        "counts": COUNTS,
        "reports": reports,
        "per_block": block_reports,
        "profiles": profiles,
        "direct_comparisons": comparisons,
        "direct_comparison_reference": (
            "native_ms/native_outer_ms denote the named baseline POLICY execution; "
            "policy_ms denotes treatment. P2b pools two fresh A/A labels within each vector."
        ),
        "per_block_contrasts": block_contrasts,
        "mechanism_checks": mechanism,
        "execution_gate": gate(comparisons, block_contrasts, reports),
        "raw_files_sha256": raw_hashes,
        "provider_calls": 0,
        "confirmation_queries": 0,
        "candidate_selection_performed": False,
        "canonical_acceptance_established": False,
        "scope": (
            "Development attribution; diagnostic profiles never enter primary timing summaries."
        ),
        "original_ab_comparison": {"status": "inconclusive", "complete_pairs": 0},
    }
    text = [
        "Admission profile identity v1 — verified original/P2a/P2b and A/A comparison",
        "Unchanged policies. No candidate selection, confirmation or serving acceptance.",
        "Primary pass is unprofiled. Diagnostic profiles are perturbed and cannot qualify speed.",
        "",
        "arm | regime | native ms | total ms | preparation ms | routing ms | ANN ms"
        " | saved % | recall delta pp",
    ]
    for arm, regimes in reports.items():
        for regime, record in regimes.items():
            overall = record["statistics"]["overall"]
            text.append(
                "{} | {} | {:.6f} | {:.6f} | {:.6f} | {:.6f} | {:.6f} | {:+.3f} | {:+.6f}".format(
                    arm,
                    regime,
                    overall["native_ms"],
                    overall["policy_ms"],
                    record["mean_preparation_ms"],
                    record["mean_routing_ms"],
                    record["mean_ann_ms"],
                    100 * (overall["native_ms"] - overall["policy_ms"]) / overall["native_ms"],
                    100 * overall["recall_delta"],
                )
            )
    text += [
        "",
        "Direct POLICY comparisons; no native-gap subtraction or A/A correction:",
        "family | arm | regime | baseline ms | treatment ms | gap ms | 95% gap interval",
    ]
    for family, comparison in comparisons.items():
        for arm, regimes in comparison.items():
            for regime, record in regimes.items():
                stat = record["overall"]
                text.append(
                    f"{family} | {arm} | {regime} | {stat['native_ms']:.6f} | "
                    f"{stat['policy_ms']:.6f} | {stat['gap_ms']:+.6f} | {stat['gap_ci95']}"
                )
    text += [
        "Execution gate: " + result["execution_gate"]["verdict"],
        *result["execution_gate"]["failures"],
        "A/A equivalence: " + result["execution_gate"]["aa_verdict"],
        *result["execution_gate"]["aa_failures"],
        "",
        "Inspect profiles by block/arm/filter/phase. Do not sum nested cumulative times.",
        "Each arm has a paired native baseline. Do not subtract control gaps to claim savings.",
        "Inspect per_block as well as pooled estimates. Intervals cluster by vector.",
        "A failed gate does not trigger another campaign. Review the finite revision budget.",
    ]
    output.mkdir(parents=True, exist_ok=True)
    save(output / "performance.json", result)
    with (output / "report.txt").open("x") as handle:
        handle.write("\n".join(text) + "\n")
    profile_text = [
        "# Diagnostic function attribution",
        "",
        "This pass includes profiler perturbation. Function names contain no argument values.",
        "Self time is exclusive. Cumulative time includes descendants; never sum nested rows.",
        "",
    ]
    for block, data in profiles.items():
        for group, values in data["groups"].items():
            profile_text += [
                f"## Block {block} / {group}",
                "",
                "{} calls; {:.6f} ms average profiled wall time.".format(
                    values["calls"], values["wall_ms"] / values["calls"]
                ),
                "",
                "| Function | Calls | Self ms/call | Cumulative ms/call |",
                "| --- | ---: | ---: | ---: |",
            ]
            for row in values["functions"][:12]:
                profile_text.append(
                    "| `{}` | {} | {:.6f} | {:.6f} |".format(
                        row["function"].replace("|", "/"),
                        row["total_calls"],
                        row["self_ms"] / values["calls"],
                        row["cumulative_ms"] / values["calls"],
                    )
                )
            profile_text.append("")
    with (output / "attribution.md").open("x") as handle:
        handle.write("\n".join(profile_text) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign", type=Path)
    parser.add_argument("package", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    analyze(args.campaign, args.package, args.output)
