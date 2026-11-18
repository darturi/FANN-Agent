"""Exercise semantic corruption rejection after rehashing the synthetic return."""

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from analyse import lines, report, sha, verify
from oracle_design import group


def rewrite(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def rehash(folder, name, frozen_key=None):
    if frozen_key:
        path = folder / "oracle-freeze.json"
        frozen = json.loads(path.read_text())
        frozen[frozen_key] = sha(folder / name)
        path.write_text(json.dumps(frozen))
    path = folder / "receipt.json"
    receipt = json.loads(path.read_text())
    receipt["raw_sha256"][name] = sha(folder / name)
    if frozen_key:
        receipt["raw_sha256"]["oracle-freeze.json"] = sha(folder / "oracle-freeze.json")
    path.write_text(json.dumps(receipt))


def check(folder):
    result = report(folder, folder, fixture=True)
    rows = list(lines(folder / "timing.jsonl"))
    roles = json.loads((folder / "query-roles.json").read_text())
    cpus = json.loads((folder / "allowed-cpus.json").read_text())
    comparisons = 0
    for cohort, stats in result["cohorts"].items():
        included = {
            group(qid) for qid, role in roles.items() if cohort == "full_workload" or role == "test"
        }
        for cpu in cpus:
            cells = {
                family: [
                    r["request_ns"]
                    for r in rows
                    if r["filter"] >= 0
                    and r["cpu"] == cpu
                    and group(r["id"]) in included
                    and r["family"] == family
                ]
                for family in ("native", "oracle")
            }
            ratio = (sum(cells["oracle"]) / len(cells["oracle"])) / (
                sum(cells["native"]) / len(cells["native"])
            )
            expected = stats["latency"]["equal_six_filters"][
                "per_physical_cpu_oracle_native_ratio"
            ][str(cpu)]
            assert abs(ratio - expected) < 1e-12
            comparisons += 1
    rejected = []
    for corruption in (
        "missing_earlier_prefix",
        "causal_prefix_identity",
        "timing_cpu",
        "timing_order",
    ):
        with tempfile.TemporaryDirectory() as temp:
            altered = Path(temp) / "results"
            shutil.copytree(folder, altered)
            if corruption == "missing_earlier_prefix":
                values = list(lines(altered / "prefixes.jsonl"))
                counts = {}
                for row in values:
                    counts[row["id"]] = counts.get(row["id"], 0) + 1
                qid = next(qid for qid, count in counts.items() if count > 1)
                values = [r for r in values if not (r["id"] == qid and r["checkpoint"] == 1)]
                rewrite(altered / "prefixes.jsonl", values)
                rehash(altered, "prefixes.jsonl", "prefixes_sha256")
            elif corruption == "causal_prefix_identity":
                values = list(lines(altered / "prefixes.jsonl"))
                values[0]["prefix_sha256"] = "0" * 64
                rewrite(altered / "prefixes.jsonl", values)
                rehash(altered, "prefixes.jsonl", "prefixes_sha256")
            else:
                values = list(lines(altered / "timing.jsonl"))
                if corruption == "timing_cpu":
                    values[0]["cpu"] = -1
                else:
                    values[0], values[1] = values[1], values[0]
                rewrite(altered / "timing.jsonl", values)
                rehash(altered, "timing.jsonl")
            try:
                verify(altered, folder, fixture=True)
            except ValueError as exc:
                rejected.append({"corruption": corruption, "reason": str(exc)})
            else:
                raise AssertionError("corrupt return accepted: " + corruption)
    output = {
        "status": "passed",
        "fixture_only": True,
        "CPU_summary_comparisons": comparisons,
        "semantic_corruptions_rejected": rejected,
        "new_SQL_searches": 0,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    check(parser.parse_args().fixture)
