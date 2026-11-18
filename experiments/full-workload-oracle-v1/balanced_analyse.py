"""Validate cumulative spending and fresh timing before using unchanged r2 statistics."""

import argparse
import json
from pathlib import Path

import analyse
from analyse import equal, lines, sha
from balanced_source import EVIDENCE, source_counts
from oracle_design import FILTERS, require, schedule
from timing_followup import verify_source


def verify(results, kit, *, fixture=False):
    receipt = json.loads((results / "receipt.json").read_text())
    if not fixture:
        require(
            receipt["status"] == "full_workload_oracle_balanced_timing_complete"
            and receipt["binding_sha256"] == sha(kit / "binding.json"),
            "followup binding changed",
        )
        require(
            json.loads((results / "host-exit.json").read_text())
            == {"exit_code": 0, "job_id": receipt["job_id"]},
            "followup did not complete",
        )
        binding = json.loads((kit / "binding.json").read_text())
        for name, expected in binding["files"].items():
            require(sha(kit / name) == expected, "sealed followup input changed")
        require(
            receipt["graph"] == binding["graph"] and receipt["data_index_before_after"] is True,
            "fresh graph qualification failed",
        )
    for name, expected in receipt["raw_sha256"].items():
        require(sha(results / name) == expected, "followup raw hash changed: " + name)
    queries = list(lines(kit / "queries.jsonl"))
    roles = json.loads((kit / "query-roles.json").read_text())
    manifest = json.loads((results / "source-acquisition.json").read_text())
    quality, truth, eligible, _ = verify_source(
        results / "source-acquisition",
        manifest,
        roles,
        expected_cases=len(queries),
        usage_name="acquisition-counts.json",
    )
    for name in EVIDENCE:
        require(
            sha(results / name) == sha(results / "source-acquisition" / name),
            "frozen source copy differs: " + name,
        )
    require(set(roles) == {q["id"] for q in queries}, "query inventory changed")
    cpus = json.loads((results / "allowed-cpus.json").read_text())
    require(len(cpus) == len(set(cpus)) == 4, "invalid CPU pool")
    readers = {}
    for row in lines(results / "reader-setup.jsonl"):
        if "pid" in row:
            key = row["filter"], row["reader"]
            require(key not in readers, "duplicate reader assignment")
            readers[key] = row
    expected = (
        cell
        for ti, t in enumerate(FILTERS)
        for cell in schedule([q for q in queries if quality[q["id"]]["filter"] == t], ti)
    )
    count = 0
    seen = set()
    for row, cell in zip(lines(results / "timing.jsonl"), expected, strict=True):
        cycle, rotation, reader, family, q = cell
        key = q["id"], cycle, reader, family
        require(key not in seen, "duplicate timing")
        seen.add(key)
        assignment = readers[row["filter"], reader]
        require(
            (row["id"], row["cycle"], row["rotation"], row["reader"], row["family"])
            == (q["id"], cycle, rotation, reader, family),
            "timing order changed",
        )
        require(
            row["pid"] == assignment["pid"]
            and row["cpu"]
            == assignment["cpu"]
            == cpus[(reader + FILTERS.index(row["filter"])) % 4],
            "timing CPU/PID changed",
        )
        require(
            row["request_ns"] > 0
            and row["construction_ns"] >= 0
            and row["sql_fetch_decode_ns"] > 0
            and row["request_ns"] == row["construction_ns"] + row["sql_fetch_decode_ns"],
            "invalid timing boundary",
        )
        want = quality[q["id"]]["output" if family == "oracle" else "native"]
        require(
            equal(row["output"], want) and row["returned_count"] == len(want),
            "timed answer changed",
        )
        count += 1
    require(count == len(queries) * 16, "incomplete timing coverage")
    expected_usage = source_counts(manifest, quality, len(queries))
    expected_usage["timed_ann"] = count
    expected_usage["warmup_ann"] = 16 * sum(
        min(10, sum(r["filter"] == t for r in quality.values())) for t in FILTERS
    )
    expected_usage["total"] = sum(v for k, v in expected_usage.items() if k != "total")
    require(receipt["searches"] == expected_usage, "cumulative charge ledger differs")
    budget = json.loads((results / "reservation-final.json").read_text())
    require(
        budget["source_charged"] == manifest["prior_reserved_total"]
        and budget["actual_total"] == expected_usage["total"]
        and budget["charged_total"] >= budget["actual_total"]
        and budget["unused_charged"] == budget["charged_total"] - budget["actual_total"]
        and budget["charged_total"] <= budget["cap"] == 2000000,
        "unknown or unused reservation reset",
    )
    return queries, roles, quality


def report(results, kit, *, fixture=False):
    # The numeric aggregation/bootstrap implementation is unchanged from the
    # original seal. Only evidence accounting has a new verified envelope.
    original_verify = analyse.verify
    analyse.verify = verify
    try:
        output = analyse.report(results, kit, fixture=fixture)
    finally:
        analyse.verify = original_verify
    receipt = json.loads((results / "receipt.json").read_text())
    output["provenance"] = {
        "acquisition_job": receipt.get("acquisition_job_ids", ["synthetic"]),
        "timing_job": receipt.get("job_id", "synthetic"),
        "timing_allocations": 1,
        "reused_choices_changed": False,
        "repetitions_per_case_family": 4,
        "cycles": 1,
        "all_choices_frozen_before_primary_timing": True,
        "discarded_source_timings_used": False,
        "ledger": "durable windows before queries; unused and uncertain slots charged",
    }
    (results / "report.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--fixture", action="store_true")
    args = parser.parse_args()
    out = report(args.results, args.kit, fixture=args.fixture)
    print(
        json.dumps(
            {name: row["latency"]["equal_six_filters"] for name, row in out["cohorts"].items()},
            indent=2,
        )
    )
