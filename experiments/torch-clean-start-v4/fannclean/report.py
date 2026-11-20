"""Private post-freeze reporting; never available as an agent tool."""

from pathlib import Path

from .core import Limits, digest, read, write
from .timing import summarize


def analyze(root):
    root = Path(root)
    config = read(root / "config.json")
    limits = Limits(**config["limits"])
    identity = read(root / "private/final-started.json")["request_id"]
    directory = root / "private/requests" / identity
    response = read(directory / "response.json")
    if not response.get("final_complete") or not response.get("private_cleanup_verified"):
        raise ValueError("partial final returns cannot yield a comparison")
    quality, timing = read(directory / "quality.json"), read(directory / "timing.json")
    cases = read(root / "private/cases.json")
    primary = [r for r in timing if r["phase"] == "sample"]
    expected_families = {"candidate:0", "matched:0", "clone", "empty", "oracle_full", "oracle_test"}
    if {r["family"] for r in primary} != expected_families:
        raise ValueError("incomplete final timing families")
    for family in expected_families:
        expected_handles = {
            c["handle"] for c in cases if family != "oracle_test" or c["role"] == "test"
        }
        rows = [r for r in primary if r["family"] == family]
        expected_hash = digest(sorted(expected_handles))
        if (
            len(rows) != len(expected_handles) * 2
            or {(r["handle"], r["block"]) for r in rows}
            != {(h, b) for h in expected_handles for b in (0, 1)}
            or any(r["declared_handles_sha256"] != expected_hash for r in rows)
        ):
            raise ValueError("incomplete declared final timing panel")
    result = {
        "run_id": config["run_id"],
        "agent_freeze_sha256": digest(read(root / "private/final-freeze.json")),
        "agent_disposition": read(root / "private/final-freeze.json")["disposition"],
        "test_feedback_returned_to_agent": False,
        "cohorts": {},
        "limitations": [
            "Single allocation; intervals condition on the selected policy and "
            "omit adaptive selection and allocation variability.",
            "Hindsight oracle references were fitted on their reported cohorts; "
            "the agent acquired development evidence only.",
            "Full workload includes development cases. Recall and result-count "
            "preservation are assessed separately.",
            "Every quality case receives a compiled/reference VM decision audit. "
            "Independent forced-prefix output checks use predeclared 16-vector "
            "panels per policy/cohort; raw quality and timing still cover every case.",
        ],
    }
    ledger = read(root / "private/query-ledger.json")
    result["accounting"] = {
        "queries_charged": ledger["charged"],
        "ann_queries": sum(r["operations"].get("ann", 0) for r in ledger["requests"].values()),
        "exact_queries": sum(r["operations"].get("exact", 0) for r in ledger["requests"].values()),
        "unsettled_requests": sum(r["status"] != "settled" for r in ledger["requests"].values()),
    }
    for scope in ("held_out", "full"):
        selected = [r for r in cases if scope == "full" or r["role"] == "test"]
        handles = {r["handle"] for r in selected}
        oracle = "oracle_test" if scope == "held_out" else "oracle_full"
        families = {"candidate:0", "matched:0", "clone", "empty", oracle}
        scope_hash = digest(sorted(handles))
        samples = [
            {**r, "declared_handles_sha256": scope_hash}
            for r in timing
            if r.get("phase") == "sample" and r["handle"] in handles and r["family"] in families
        ]
        estimates = summarize(
            samples, limits.bootstrap_draws, limits.control_tolerance, int(identity[:8], 16)
        )
        outcomes = {}
        for family in ("candidate:0", oracle):
            rows = [r for r in quality if r["handle"] in handles and r["family"] == family]
            if len(rows) != len(handles) or {r["handle"] for r in rows} != handles:
                raise ValueError("incomplete/duplicate final quality cohort")
            recall_losses = sum(r["recall"] + 1e-12 < r["native_recall"] for r in rows)
            count_losses = sum(r["count"] < r["native_count"] for r in rows)
            faults = sum(bool(r["fault"] or r["exhausted"]) for r in rows)
            outcomes[family] = {
                "recall_loss_cases": recall_losses,
                "count_loss_cases": count_losses,
                "resource_fault_cases": faults,
                "stopped_cases": sum(r["checkpoint"] > 0 for r in rows),
                "independent_forced_prefix_audits": sum(
                    r.get("independent_forced_prefix_audit", False) for r in rows
                ),
                "strict_quality_pass": not (recall_losses or count_losses or faults),
            }
        agent = estimates["families"]["candidate:0"]["all"]
        reference = estimates["families"][oracle]["all"]
        qualified = (
            estimates["controls_pass"]
            and outcomes["candidate:0"]["strict_quality_pass"]
            and outcomes["candidate:0"]["stopped_cases"] > 0
            and agent.get("ci95", [0, 2])[1] < 1
            and estimates["families"]["candidate:0"]["matched"].get("ci95", [0, 2])[1] < 1
            and result["agent_disposition"]["status"] == "policy_frozen"
        )
        result["cohorts"][scope] = {
            "cases": len(handles),
            "quality": outcomes,
            "timing": estimates,
            "qualified_agent_win": bool(qualified),
            "gap_percentage_points": (
                reference["savings_percent"] - agent["savings_percent"]
                if "savings_percent" in reference and "savings_percent" in agent
                else None
            ),
            "oracle_is_strict_quality_comparator": outcomes[oracle]["strict_quality_pass"],
            "latency_descriptive_if_controls_fail": True,
        }
    write(root / "private/final-report.json", result)
    return result
