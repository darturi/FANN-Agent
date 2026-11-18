"""Export the two evaluator-only oracle tables after complete return verification."""

import argparse
import hashlib
import json
from pathlib import Path


def export(results):
    report = json.loads((results / "report.json").read_text())
    if report["fixture"]:
        raise ValueError("Synthetic choices cannot be exported as benchmark policies")
    receipt = json.loads((results / "receipt.json").read_text())
    frozen = json.loads((results / "oracle-freeze.json").read_text())
    quality = results / "quality.jsonl"
    with quality.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    assert digest == frozen["quality_sha256"]
    rows = [json.loads(line) for line in quality.read_text().splitlines()]
    for cohort, filename in (
        ("full_workload", "oracle-full-workload.json"),
        ("heldout_test", "oracle-heldout-test.json"),
    ):
        selected = [r for r in rows if cohort == "full_workload" or r["role"] == "test"]
        assert len(selected) == report["cohorts"][cohort]["cases"]
        choices = {r["id"]: r["checkpoint"] for r in selected}
        assert len(choices) == len(selected)
        policy = {
            "schema": "fannagent.hindsight-checkpoint-policy.v1",
            "cohort": cohort,
            "evaluator_only": True,
            "deployable": False,
            "uses_query_identity_and_future_outcomes": True,
            "definition": (
                "earliest actually measured checkpoint preserving native recall and count"
            ),
            "parent_ef_search": 640,
            "iterative_scan": "off",
            "zero_checkpoint": "continue native",
            "cases": len(selected),
            "choices": choices,
            "source_quality_sha256": digest,
            "module_sha256": receipt["module_sha256"],
            "graph": receipt["graph"],
            "job_id": receipt["job_id"],
        }
        path = results / filename
        content = json.dumps(policy, sort_keys=True, indent=2) + "\n"
        if path.exists():
            assert path.read_text() == content, "refusing to replace different oracle policy"
        else:
            path.write_text(content)
        print(json.dumps({"policy": str(path.resolve()), "cases": len(selected)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    export(parser.parse_args().results)
