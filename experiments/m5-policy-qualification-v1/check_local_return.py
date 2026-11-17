"""Verify actual synthetic phase outputs and reject deliberately corrupted/re-signed rows."""

import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
RUNTIME = STUDY / "runtime-m5-v1"


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    sys.path.append(str(RUNTIME))
    from m5_analyse import analyse
    from m5_verify import verify

    shared = RUNTIME / "checks/smoke-shared"
    root = RUNTIME / "checks/verifier-fixture"
    root.mkdir(exist_ok=False)
    kit = root / "kit"
    kit.mkdir()
    results = root / "results"
    results.mkdir()
    for name in ("compiled-programs.json", "binding.json", "nominees.json"):
        shutil.copyfile(STUDY / "kits/m5-policy-qualification-v1" / name, kit / name)
    queries = []
    for r in (
        json.loads(line) for line in (shared / "timing7/quality.jsonl").read_text().splitlines()
    ):
        i = int(r["id"].split("-v")[1].split("-")[0])
        q = {"id": r["id"], "k": 10, "vector": [0.3 + i * 0.03, 0.1, 0.8, 0.4, 0.9, 0.2, 0.6, 0.5]}
        if r["filter"] >= 0:
            q["filter"] = {"field": "totalvotes", "op": "gte", "value": r["filter"]}
        queries.append(q)
    (kit / "queries.jsonl").write_text("".join(json.dumps(q) + "\n" for q in queries))
    (kit / "SHA256SUMS").write_text(
        "".join(sha(p) + "  " + p.name + "\n" for p in sorted(kit.iterdir()))
    )
    binding = json.loads((kit / "binding.json").read_text())
    from m5_design import ledger

    for phase in ("timing", "work"):
        shutil.copytree(shared / (phase + "7"), results / phase)
        folder = results / phase
        # Fixture metadata is constructed around real PostgreSQL rows; never study evidence.
        write(folder / "attempts.json", ledger(28, 84, 4)[phase])
        receipt = {
            "status": "M5_fixture_" + phase + "_complete",
            "job_id": "synthetic-only",
            "module_sha256": binding[phase + "_module_sha256"],
            "programs_sha256": binding["programs_sha256"],
            "runtime_profile": binding["runtime_profile"],
            "searches": ledger(28, 84, 4)[phase],
            "exact_serving_calls": 0,
            "provider_calls": 0,
            "validation_test_queries": 0,
            "data_index_before_after": True,
            "cleanup_verified": True,
            "raw_sha256": {p.name: sha(p) for p in folder.iterdir() if p.is_file()},
        }
        write(folder / "receipt.json", receipt)
    write(results / "host-exit.json", {"exit_code": 0, "job_id": "synthetic-only"})
    result = verify(results, kit, fixture=True)
    assert result["timed_requests"] == 1344 and result["attempts"]["total"] == 3220
    report = analyse(results, kit)
    assert report["status"] == "M5_fixture_analysis_only"
    try:
        verify(results, kit)
    except RuntimeError:
        pass
    else:
        raise AssertionError("synthetic return passed production scope")
    tested = []

    def corrupt(phase, name, mutate, expected):
        path = results / phase / name
        original = path.read_text()
        receipt_path = results / phase / "receipt.json"
        receipt = receipt_path.read_text()
        first, rest = original.split("\n", 1)
        row = json.loads(first)
        mutate(row)
        path.write_text(json.dumps(row) + "\n" + rest)
        r = json.loads(receipt)
        r["raw_sha256"][name] = sha(path)
        write(receipt_path, r)
        try:
            verify(results, kit, fixture=True)
        except RuntimeError as error:
            assert expected in str(error), str(error)
            tested.append(expected)
        else:
            raise AssertionError("corrupted " + name + " accepted")
        path.write_text(original)
        receipt_path.write_text(receipt)

    corrupt(
        "timing", "assignments.jsonl", lambda r: r.update(cpu=-1), "role/CPU assignment differs"
    )
    corrupt(
        "timing", "timing.jsonl", lambda r: r.update(position=99), "mirrored Williams order differs"
    )
    corrupt(
        "timing", "quality.jsonl", lambda r: r["prefixes"].pop("16"), "missing actual prefix label"
    )
    corrupt(
        "work",
        "work.jsonl",
        lambda r: r["counts"].update(start_cpu=-1),
        "work CPU/counter schema differs",
    )
    corrupt(
        "timing",
        "timing.jsonl",
        lambda r: r.update(output=[]),
        "timed output differs from qualification",
    )
    corrupt(
        "work",
        "work.jsonl",
        lambda r: r["counts"].update(feature_passes=1),
        "unneeded heap feature work on bypass/decision-only path",
    )
    receipt_path = results / "timing/receipt.json"
    saved = receipt_path.read_text()
    r = json.loads(saved)
    r["module_sha256"] = binding["work_module_sha256"]
    write(receipt_path, r)
    try:
        verify(results, kit, fixture=True)
    except RuntimeError as error:
        assert "phase module/profile binding differs" in str(error)
        tested.append("instrumented timing module rejected")
    else:
        raise AssertionError("instrumented primary timings accepted")
    receipt_path.write_text(saved)
    r = json.loads(saved)
    r["searches"]["total"] += 1
    write(receipt_path, r)
    try:
        verify(results, kit, fixture=True)
    except RuntimeError as error:
        assert "phase attempt ledger differs" in str(error)
        tested.append("extra attempted query rejected")
    else:
        raise AssertionError("wrong attempt ledger accepted")
    receipt_path.write_text(saved)
    outcome = {
        "status": "passed",
        "fixture": "Actual synthetic PostgreSQL outputs, not fabricated study performance",
        "timing_records": result["timed_requests"],
        "attempts": result["attempts"],
        "all_seven_conditions": True,
        "prefix_labels": result["prefix_labels"],
        "partial_prefix_labels": result["partial_prefix_labels"],
        "full_prefix_labels": result["full_prefix_labels"],
        "bad_CPU_order_missing_prefix_work_sample_and_module_rejected": tested,
        "production_scope_rejects_fixture": True,
        "paired_cost_analysis_executed": True,
        "validation_test_outcomes_opened": False,
    }
    write(RUNTIME / "checks/local-verifier-check.json", outcome)
    return outcome


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
