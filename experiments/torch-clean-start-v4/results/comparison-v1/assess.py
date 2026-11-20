"""Audit saved returns only; never dispatch native queries or provider calls."""

import argparse
import hashlib
import json
import shutil
import tarfile
from collections import Counter
from decimal import Decimal
from pathlib import Path


def read(path):
    return json.loads(path.read_text())


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trial", type=Path, required=True)
    args = parser.parse_args()
    trial, out = args.trial.resolve(), Path(__file__).resolve().parent
    stage, private = trial / "experiment-stage", trial / "final-returns/private"
    report = read(stage / "host/final-report.json")
    freeze = read(stage / "host/freeze.json")
    closed = read(stage / "host/model-closed.json")
    assert closed["model_closed"] and closed["status"] == "abstained"
    assert digest(freeze) == closed["freeze_sha256"] == report["agent_freeze_sha256"]
    assert freeze == read(private / "final-freeze.json")
    assert freeze["policy"]["programs"] == {} and not freeze["test_feedback_seen"]
    assert report["test_feedback_returned_to_agent"] is False
    identity = read(private / "final-started.json")["request_id"]
    request = private / "requests" / identity
    response = read(request / "response.json")
    assert response["final_complete"] and response["private_cleanup_verified"]
    assert read(request / "cleanup.json")["verified"]
    ledger, cases = read(private / "query-ledger.json"), read(private / "cases.json")
    journals = {}
    for key, entry in ledger["requests"].items():
        rows, ordinals = Counter(), []
        with (private / "requests" / key / "queries.jsonl").open() as stream:
            for line in stream:
                row = json.loads(line)
                rows[row["family"]] += 1
                result = row.get("result")
                ordinals.append(
                    row.get("query_ordinal")
                    if "query_ordinal" in row
                    else result.get("query_ordinal")
                    if isinstance(result, dict)
                    else None
                )
        assert entry["status"] == "settled"
        assert sum(rows.values()) == entry["actual"] == sum(entry["operations"].values())
        assert set(ordinals) == set(range(1, entry["actual"] + 1))
        assert rows["exact"] == entry["operations"].get("exact", 0)
        journals[key] = {"rows": sum(rows.values()), "families": dict(rows)}
    assert sum(v["rows"] for v in journals.values()) == ledger["charged"] == 199484
    quality, timing = read(request / "quality.json"), read(request / "timing.json")
    samples = [v for v in timing if v["phase"] == "sample"]
    assert len(quality) == 15925 and len(samples) == 73850
    panels = {}
    for family in ("candidate:0", "matched:0", "clone", "empty", "oracle_full", "oracle_test"):
        expected = {c["handle"] for c in cases if family != "oracle_test" or c["role"] == "test"}
        rows = [v for v in samples if v["family"] == family]
        assert len(rows) == 2 * len(expected)
        assert {(v["handle"], v["block"]) for v in rows} == {
            (h, b) for h in expected for b in (0, 1)
        }
        assert all(v["reader"] == v["block"] for v in rows)
        assert all(v["measurement_design"] == "adjacent_randomized_pair_v1" for v in rows)
        assert all(sorted(v["pair_order"]) == sorted([family, "native"]) for v in rows)
        panels[family] = dict(Counter(str(v["block"]) for v in rows))
    metrics = {}
    for scope, cohort in report["cohorts"].items():
        oracle = "oracle_test" if scope == "held_out" else "oracle_full"
        assert cohort["cases"] == (1925 if scope == "held_out" else 7000)
        assert cohort["timing"]["controls_pass"] and not cohort["qualified_agent_win"]
        handles = {c["handle"] for c in cases if scope == "full" or c["role"] == "test"}
        for family in ("candidate:0", oracle):
            rows = [v for v in quality if v["handle"] in handles and v["family"] == family]
            q = cohort["quality"][family]
            assert len(rows) == len(handles) == len({v["handle"] for v in rows})
            assert q["recall_loss_cases"] == sum(
                v["recall"] + 1e-12 < v["native_recall"] for v in rows
            )
            assert q["count_loss_cases"] == sum(v["count"] < v["native_count"] for v in rows)
            assert q["stopped_cases"] == sum(v["checkpoint"] > 0 for v in rows)
        families = cohort["timing"]["families"]
        values = {}
        for family in families:
            rows = [v for v in samples if v["handle"] in handles and v["family"] == family]
            estimate = families[family]["all"]
            native, arm = sum(v["native_ns"] for v in rows), sum(v["request_ns"] for v in rows)
            assert abs(arm / native - estimate["ratio"]) < 1e-12
            values[family] = {
                **estimate,
                "savings_ci95_percent": [
                    100 * (1 - estimate["ci95"][1]),
                    100 * (1 - estimate["ci95"][0]),
                ],
                "mean_native_ms": native / len(rows) / 1e6,
                "mean_arm_ms": arm / len(rows) / 1e6,
            }
        metrics[scope] = {
            "cases": cohort["cases"],
            "controls_pass": True,
            "agent_operational_savings_percent": 0,
            "oracle_savings_percent": values[oracle]["savings_percent"],
            "operational_gap_percentage_points": values[oracle]["savings_percent"],
            "oracle_is_strict_quality_comparator": cohort["oracle_is_strict_quality_comparator"],
            "quality": cohort["quality"],
            "families": values,
        }
    scheduler = (trial / "scheduler-accounting.txt").read_text()
    row = next(v.split("|") for v in scheduler.splitlines() if v.startswith("23800555|"))
    assert row[1] == "COMPLETED" and row[5] == "0:0"
    model_cost = Decimal(closed["model_charged_usd"])
    accounting = {
        "replacement": {
            "model_usd": str(model_cost),
            "queries": ledger["charged"],
            "discovery_queries": ledger["charged"] - ledger["requests"][identity]["actual"],
            "final_queries": ledger["requests"][identity]["actual"],
            "ann_queries": report["accounting"]["ann_queries"],
            "exact_queries": 7000,
            "allocated_seconds": int(row[2]),
            "job_id": row[0],
            "status": row[1],
        },
        "previous_qualification_and_failed_episode": {
            "model_usd": "1.228968",
            "queries": 55650,
            "allocated_seconds": 4891,
        },
        "total": {
            "model_usd": str(model_cost + Decimal("1.228968")),
            "queries": ledger["charged"] + 55650,
            "allocated_seconds": int(row[2]) + 4891,
        },
        "caps": {"model_usd": "15", "queries": 300000, "allocated_seconds": 21600},
        "unsettled_requests": report["accounting"]["unsettled_requests"],
        "unused_replacement_discovery_queries": 49350
        - (ledger["charged"] - ledger["requests"][identity]["actual"]),
        "unused_shared_model_usd": closed["model_remaining_usd"],
        "stop_was_voluntary": not freeze["disposition"]["resource_exit"],
    }
    assert (
        accounting["total"]["queries"] <= 300000
        and accounting["total"]["allocated_seconds"] <= 21600
    )
    assert Decimal(accounting["total"]["model_usd"]) <= 15 and accounting["unsettled_requests"] == 0
    expected_archives = {
        "final-returns.tar.gz": "f23b55e64732a60179e2836007b0398e7cf76d47e20c9b2a8c011927ef8f11d1",
        "final-compiled-module.tar.gz": (
            "1b38df22efc6a6082623eb081b04cde12d322cf02f67411fb4f3758014d3608b"
        ),
    }
    for name, expected in expected_archives.items():
        assert sha(trial / name) == expected
    module = read(request / "module.json")
    with tarfile.open(trial / "final-compiled-module.tar.gz") as archive:
        assert (
            hashlib.sha256(archive.extractfile("vector.so").read()).hexdigest() == module["sha256"]
        )
        assert archive.getmember("engine/src/compiled_v3.inc").size > 0
    audit = {
        "status": "passed_complete_saved_returns",
        "run_id": report["run_id"],
        "final_request_id": identity,
        "source_commit": "a1fe405",
        "freeze_sha256": digest(freeze),
        "journals": journals,
        "quality_rows": len(quality),
        "primary_timing_rows": len(samples),
        "timing_rows_including_arm_warmups": len(timing),
        "panels": panels,
        "oracle_count_loss_cases": [
            v
            for v in quality
            if v["family"].startswith("oracle_") and v["count"] < v["native_count"]
        ],
        "archives_sha256": expected_archives,
        "compiled_module": module,
        "raw_trial": str(trial),
        "no_native_or_provider_dispatch": True,
    }
    for name, value in (
        ("metrics.json", metrics),
        ("accounting.json", accounting),
        ("audit.json", audit),
    ):
        write(out / name, value)
    for source, target in (
        (stage / "host/final-report.json", "final-report.json"),
        (stage / "host/freeze.json", "agent-freeze.json"),
        (trial / "discovery-audit.json", "discovery-audit.json"),
        (trial / "post-closure-oracle-bindings.json", "oracle-bindings.json"),
        (trial / "approved-clean-start-verification.json", "initial-verification.json"),
        (trial / "authorized-initial-package.json", "initial-package.json"),
        (stage / "host/report-execution.json", "report-execution.json"),
        (trial / "scheduler-accounting.txt", "scheduler-accounting.txt"),
        (stage / "agent/policies/tree_d3_all.json", "unsafe-tree.json"),
        (stage / "agent/policies/gap_margin.json", "unsafe-gap-rule.json"),
    ):
        shutil.copyfile(source, out / target)
    write(
        out / "artifact-hashes.json",
        {
            p.name: sha(p)
            for p in sorted(out.iterdir())
            if p.is_file() and p.name != "artifact-hashes.json"
        },
    )
    print(
        json.dumps(
            {
                "status": audit["status"],
                "total": accounting["total"],
                "metrics": {
                    k: {
                        s: v[s]
                        for s in (
                            "cases",
                            "oracle_savings_percent",
                            "oracle_is_strict_quality_comparator",
                        )
                    }
                    for k, v in metrics.items()
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
