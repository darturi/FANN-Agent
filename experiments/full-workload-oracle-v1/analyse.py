"""Independently verify actual labels and timing coverage, then report both cohorts."""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from oracle_design import FAMILIES, FILTERS, group, qualifies, require, schedule, validate_output


def lines(path):
    with path.open() as handle:
        for line in handle:
            yield json.loads(line)


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def equal(a, b):
    return (
        len(a) == len(b)
        and set(dict(a)) == set(dict(b))
        and all(abs(dict(a)[i] - d) <= 1e-6 for i, d in b)
    )


def verify(results, kit, *, fixture=False):
    binding = json.loads((kit / "binding.json").read_text()) if not fixture else None
    queries = list(lines(kit / "queries.jsonl"))
    qmap = {q["id"]: q for q in queries}
    require(len(qmap) == len(queries), "duplicate query inputs")
    roles = json.loads((kit / "query-roles.json").read_text())
    receipt = json.loads((results / "receipt.json").read_text())
    if not fixture:
        require(
            receipt["status"] == "full_workload_oracle_complete"
            and receipt["binding_sha256"] == sha(kit / "binding.json"),
            "receipt binding mismatch",
        )
        host = json.loads((results / "host-exit.json").read_text())
        require(
            host == {"exit_code": 0, "job_id": receipt["job_id"]}, "failed/incomplete host return"
        )
        for name, expected in binding["files"].items():
            require(sha(kit / name) == expected, "changed sealed input: " + name)
    for name, expected in receipt["raw_sha256"].items():
        require(sha(results / name) == expected, "changed raw evidence: " + name)
    frozen = json.loads((results / "oracle-freeze.json").read_text())
    for name in ("quality", "prefixes", "trajectories"):
        require(
            sha(results / (name + ".jsonl")) == frozen[name + "_sha256"],
            "choices changed after freeze",
        )
    eligible = {
        int(t): set(ids)
        for t, ids in json.loads((results / "eligibility.json").read_text()).items()
    }

    def indexed(name):
        rows = list(lines(results / name))
        mapped = {r["id"]: r for r in rows}
        require(len(mapped) == len(rows), "duplicate evidence: " + name)
        return mapped

    truth = {qid: row["output"] for qid, row in indexed("exact-reference.jsonl").items()}
    quality = indexed("quality.jsonl")
    trajectories = indexed("trajectories.jsonl")
    require(
        set(quality) == set(truth) == set(roles) == set(qmap) == set(trajectories),
        "incomplete quality/reference coverage",
    )
    measured = defaultdict(list)
    for row in lines(results / "prefixes.jsonl"):
        require(row["id"] in qmap, "unknown prefix query")
        measured[row["id"]].append(row)
    for qid, row in quality.items():
        t = row["filter"]
        require(row["role"] == roles[qid], "cohort mismatch")
        native = validate_output(row["native"], eligible[t], truth[qid])
        oracle = validate_output(row["output"], eligible[t], truth[qid])
        require(
            abs(native - row["native_recall"]) < 1e-12 and abs(oracle - row["recall"]) < 1e-12,
            "saved recall differs from actual result",
        )
        require(qualifies(row["output"], oracle, row["native"], native), "oracle loses quality")
        stops = measured[qid]
        trajectory = trajectories[qid]
        require(
            trajectory["count"] == row["native_checkpoint_count"]
            and len(trajectory["prefix_sha256"])
            == len(trajectory["targets"])
            == trajectory["count"]
            and equal(trajectory["output"], row["native"]),
            "canonical trajectory mismatch",
        )
        end = row["checkpoint"] or row["native_checkpoint_count"]
        require(
            [p["checkpoint"] for p in stops] == list(range(1, end + 1))
            and len(stops) == row["tested_count"],
            "earlier untested checkpoint or duplicate label",
        )
        for index, p in enumerate(stops):
            score = validate_output(p["output"], eligible[t], truth[qid])
            safe = qualifies(p["output"], score, row["native"], native)
            require(
                abs(score - p["recall"]) < 1e-12
                and p["qualifies"] == safe
                and p["prefix_verified"] is True
                and p["prefix_sha256"] == trajectory["prefix_sha256"][index]
                and p["target"] == trajectory["targets"][index],
                "invalid prefix label/proof",
            )
            require(
                safe == (bool(row["checkpoint"]) and index == len(stops) - 1),
                "not the first safe stop",
            )
        require(
            equal(row["output"], stops[-1]["output"] if row["checkpoint"] else row["native"]),
            "selected answer mismatch",
        )
    expected = (
        cell
        for ti, t in enumerate(FILTERS)
        for cell in schedule([q for q in queries if quality[q["id"]]["filter"] == t], ti)
    )
    count = 0
    coverage = set()
    cpus = json.loads((results / "allowed-cpus.json").read_text())
    require(len(cpus) == len(set(cpus)) == 4, "invalid CPU inventory")
    readers = {}
    for r in lines(results / "reader-setup.jsonl"):
        if "pid" in r:
            key = r["filter"], r["reader"]
            require(key not in readers, "duplicate reader assignment")
            readers[key] = r
    for row, cell in zip(lines(results / "timing.jsonl"), expected, strict=True):
        cycle, rotation, reader, family, q = cell
        key = (q["id"], cycle, reader, family)
        require(key not in coverage, "duplicate timing")
        coverage.add(key)
        assignment = readers[row["filter"], reader]
        require(
            row["pid"] == assignment["pid"]
            and row["cpu"]
            == assignment["cpu"]
            == cpus[(reader + FILTERS.index(row["filter"])) % 4],
            "PID/CPU assignment changed",
        )
        require(
            (row["id"], row["cycle"], row["rotation"], row["reader"], row["family"])
            == (q["id"], cycle, rotation, reader, family),
            "timing schedule changed",
        )
        require(
            row["request_ns"] > 0
            and row["construction_ns"] >= 0
            and row["sql_fetch_decode_ns"] > 0
            and row["request_ns"] == row["construction_ns"] + row["sql_fetch_decode_ns"],
            "invalid timer",
        )
        want = quality[q["id"]]["output" if family == "oracle" else "native"]
        require(
            equal(row["output"], want) and row["returned_count"] == len(want),
            "changed timed answer",
        )
        count += 1
    require(
        count == len(queries) * 32 == receipt["searches"]["timed_ann"], "timing coverage mismatch"
    )
    expected_counts = {
        "offline_exact": len(queries),
        "canonical_capture": len(queries),
        "native_quality": len(queries) * 2,
        "oracle_quality": len(queries),
        "matched_quality": len(queries),
        "forced_prefix": sum(map(len, measured.values())),
        "warmup_ann": 4
        * 8
        * sum(min(10, sum(r["filter"] == t for r in quality.values())) for t in FILTERS),
        "timed_ann": count,
    }
    expected_counts["total"] = sum(expected_counts.values())
    require(receipt["searches"] == expected_counts, "query attempt ledger differs")
    return queries, roles, quality


def report(results, kit, *, fixture=False):
    queries, roles, quality = verify(results, kit, fixture=fixture)
    groups = sorted({group(q["id"]) for q in queries})
    gi = {g: i for i, g in enumerate(groups)}
    values = np.full((len(groups), 7, 4, 2, 4), np.nan)
    routing = np.full_like(values, np.nan)
    for row in lines(results / "timing.jsonl"):
        key = (
            gi[group(row["id"])],
            FILTERS.index(row["filter"]),
            row["reader"],
            row["cycle"],
            FAMILIES.index(row["family"]),
        )
        require(np.isnan(values[key]), "duplicate timing tensor cell")
        values[key] = row["request_ns"] / 1e6
        routing[key] = row["oracle_routing_ns_outside_primary"] / 1e6
    require(np.isfinite(values).all(), "incomplete timing tensor")
    output = {
        "schema": "fannagent.full-workload-oracle.report.v1",
        "fixture": fixture,
        "cohorts": {},
        "definition": (
            "earliest actually executed checkpoint preserving native recall and result count"
        ),
        "scope": "optimistic checkpoint headroom; free hindsight selection; one allocation",
        "timings_select_checkpoints": False,
        "exact_serving_calls": 0,
        "limitations": [
            "Not an upper bound over other algorithms or arbitrary instruction boundaries",
            "Earliest safe checkpoint need not minimize noisy wall time",
            "Intervals omit allocation variability; full and test cohorts overlap",
            "Protected outcomes exposed for this evaluator-only diagnostic",
        ],
    }
    for cohort in ("full_workload", "heldout_test"):
        selected_groups = [
            g
            for g in groups
            if cohort == "full_workload"
            or any(group(qid) == g and r == "test" for qid, r in roles.items())
        ]
        if not selected_groups:
            continue
        indices = [gi[g] for g in selected_groups]
        a = values[indices]
        r = routing[indices]
        n = len(indices)
        per_group = a.mean(axis=(2, 3))
        rng = np.random.default_rng(20261117)
        boot = []
        for _ in range(40):
            weights = rng.multinomial(n, np.full(n, 1 / n), size=500)
            boot.append((weights @ per_group.reshape(n, -1) / n).reshape(500, 7, 4))
        boot = np.concatenate(boot)
        means = per_group.mean(axis=0)
        stats = {}
        for label, filters in (
            ("equal_six_filters", list(range(1, 7))),
            ("equal_seven_conditions", list(range(7))),
            *((str(t), [ti]) for ti, t in enumerate(FILTERS)),
        ):
            m = means[filters].mean(axis=0)
            b = boot[:, filters].mean(axis=1)
            ratio = m[1] / m[0]
            ci = np.quantile(b[:, 1] / b[:, 0], [0.025, 0.975])
            control = np.quantile(b[:, 3] / b[:, 0], [0.05, 0.95])
            stats[label] = {
                "native_mean_ms": float(m[0]),
                "oracle_mean_ms": float(m[1]),
                "matched_continue_mean_ms": float(m[2]),
                "empty_mean_ms": float(m[3]),
                "oracle_native_ratio": float(ratio),
                "latency_reduction_percent": float(100 * (1 - ratio)),
                "ratio_conditional95_interval": ci.tolist(),
                "reduction_percent_conditional95_interval": [
                    float(100 * (1 - ci[1])),
                    float(100 * (1 - ci[0])),
                ],
                "oracle_matched_ratio": float(m[1] / m[2]),
                "empty_native_ratio": float(m[3] / m[0]),
                "empty_native_conditional90_interval": control.tolist(),
                "empty_control_within_2pct": bool(control[0] >= 0.98 and control[1] <= 1.02),
                "oracle_routing_ms_outside_primary": float(r[:, filters, :, :, 1].mean()),
                "per_cycle_oracle_native_ratio": [
                    float(a[:, filters, :, c, 1].mean() / a[:, filters, :, c, 0].mean())
                    for c in (0, 1)
                ],
                "per_reader_oracle_native_ratio": [
                    float(a[:, filters, reader, :, 1].mean() / a[:, filters, reader, :, 0].mean())
                    for reader in range(4)
                ],
                "per_physical_cpu_oracle_native_ratio": {
                    str(cpu): float(
                        np.mean([a[:, ti, (ci - ti) % 4, :, 1].mean() for ti in filters])
                        / np.mean([a[:, ti, (ci - ti) % 4, :, 0].mean() for ti in filters])
                    )
                    for ci, cpu in enumerate(
                        json.loads((results / "allowed-cpus.json").read_text())
                    )
                },
            }
        selected = [row for row in quality.values() if group(row["id"]) in set(selected_groups)]
        condition_quality = {}
        for t in FILTERS:
            rows = [row for row in selected if row["filter"] == t]
            condition_quality[str(t)] = {
                "cases": len(rows),
                "stops": sum(row["checkpoint"] > 0 for row in rows),
                "native_mean_recall": float(np.mean([row["native_recall"] for row in rows])),
                "oracle_mean_recall": float(np.mean([row["recall"] for row in rows])),
                "recall_losses": sum(row["recall"] + 1e-12 < row["native_recall"] for row in rows),
                "result_count_losses": sum(len(row["output"]) < len(row["native"]) for row in rows),
                "checkpoint_histogram": dict(Counter(row["checkpoint"] for row in rows)),
            }
        controls_pass = all(stats[str(t)]["empty_control_within_2pct"] for t in FILTERS)
        output["cohorts"][cohort] = {
            "groups": n,
            "cases": len(selected),
            "latency": stats,
            "quality": condition_quality,
            "all_condition_controls_pass": controls_pass,
            "interpretation": "measured optimistic checkpoint headroom"
            if controls_pass
            else "timing controls inconclusive/outside band; retain descriptive estimates",
        }
    (results / "report.json").write_text(json.dumps(output, sort_keys=True, indent=2) + "\n")
    return output


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--results", type=Path, required=True)
    p.add_argument("--kit", type=Path, required=True)
    p.add_argument("--fixture", action="store_true")
    args = p.parse_args()
    result = report(args.results, args.kit, fixture=args.fixture)
    print(
        json.dumps(
            {
                name: {
                    "groups": row["groups"],
                    "cases": row["cases"],
                    **row["latency"]["equal_six_filters"],
                }
                for name, row in result["cohorts"].items()
            },
            indent=2,
        )
    )
