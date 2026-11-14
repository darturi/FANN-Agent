"""Rescore verified full prefixes against raw native; no new search/provider/holdout access."""

import hashlib
import json
import re
from pathlib import Path

from fannproto.evidence import Evidence
from fannproto.policy import FEATURES, PROFILE

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_jsonl(p):
    with p.open() as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def build(output):
    old = STUDY / "returns/job-22684501/results"
    raw = STUDY / "returns/job-23045686/results"
    for directory in (old, raw):
        receipt = json.loads((directory / "receipt.json").read_text())
        for name, h in receipt["raw_sha256"].items():
            if sha(directory / name) != h:
                raise ValueError("source checksum differs: " + name)
    split_freeze = json.loads((STUDY / "freeze/split-freeze.json").read_text())
    split_sha = "d48d341f3252e24c7eadf5b13e81b66063b25a0dff2d6b6ddd72cb4af418eec0"
    if sha(STUDY / "splits/split-manifest.json") != split_sha:
        raise ValueError("frozen split manifest changed")
    dev = STUDY / "splits/development.jsonl"
    if sha(dev) != split_freeze["role_file_hashes"]["development.jsonl"]:
        raise ValueError("frozen development membership changed")
    membership = list(load_jsonl(dev))
    allowed = {r["source_index"] for r in membership}
    assert len(allowed) == 450
    fold = {
        int(i): int(f)
        for f, indices in json.loads((STUDY / "protocol/development-folds.json").read_text())[
            "folds"
        ].items()
        for i in indices
    }
    assert set(fold) == allowed
    if any(not re.fullmatch("reviews-small-sha256:[a-f0-9]{64}", r["group"]) for r in membership):
        raise ValueError("unexpected development vector-group identity")
    ranked = sorted(
        membership,
        key=lambda r: hashlib.sha256(
            ("reviews-clean-development-folds-v1:" + r["group"][-64:]).encode()
        ).hexdigest(),
    )
    if fold != {r["source_index"]: rank % 5 for rank, r in enumerate(ranked)}:
        raise ValueError("development fold map differs from frozen algorithm")
    ordinal = {i: k for k, i in enumerate(sorted(allowed))}
    source = {}
    for r in load_jsonl(raw / "quality.jsonl"):
        i = int(re.fullmatch(r"reviews-clean-v(\d+)-(?:unfiltered|votes\d+)", r["id"])[1])
        assert i in allowed
        source[r["id"]] = {
            "group": ordinal[i],
            "fold": fold[i],
            "filter": r["id"].rsplit("-", 1)[1],
            "native_recall": r["results"]["native640"]["recall"],
            "native_count": r["results"]["native640"]["returned_count"],
            "observations": {},
            "proofs": {},
        }
    for t in (-1, 743, 527, 310, 192, 108, 32):
        for r in load_jsonl(old / f"policy-qualification-{t}.jsonl"):
            row = source[r["id"]]
            row["observations"] = {
                str(o["checkpoint"]): {n: o[n] for n in FEATURES} for o in r["checkpoints"]
            }
            row["proofs"] = {
                cp: {"recall": p["recall"], "returned_count": len(p["output"])}
                for cp, p in r["forced"].items()
            }
    rows = [source[qid] for qid in sorted(source)]
    bundle = {
        "schema": "filtered-ann-evidence.v2",
        "scope": "development",
        "runtime_profile": PROFILE.fingerprint,
        "cost_status": "unqualified_pending_M0_and_original_graph_v2_costs",
        "rows": rows,
        "source_receipt_sha256": {
            "raw": sha(raw / "receipt.json"),
            "full_prefixes": sha(old / "receipt.json"),
        },
        "limits": "Full-result prefixes from qualified old runtime are rescored"
        ", not relabeled as v2 qualification. Missing partial prefixe"
        "s require new original-graph measurements.",
    }
    evidence = Evidence(bundle)
    summary = evidence.summary()
    safe = 0
    available = 0
    missing = 0
    for r in rows:
        available += len(r["proofs"])
        missing += len(r["observations"]) - len(r["proofs"])
        safe += any(p["recall"] >= r["native_recall"] - 1e-12 for p in r["proofs"].values())
    summary.update(
        full_prefix_labels=available,
        missing_reached_prefix_labels=missing,
        cases_with_some_known_raw_recall_preserving_full_prefix=safe,
        opportunity_limit="Oracle diagnostic count, not a causal rule or latency result"
        ". Partial-prefix opportunity remains unknown.",
    )
    output.mkdir(parents=True, exist_ok=False)
    (output / "evidence.json").write_text(
        json.dumps(bundle, sort_keys=True, separators=(",", ":")) + "\n"
    )
    (output / "summary.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    s = build(a.output)
    print(
        json.dumps(
            {
                k: s[k]
                for k in (
                    "groups",
                    "full_prefix_labels",
                    "missing_reached_prefix_labels",
                    "cases_with_some_known_raw_recall_preserving_full_prefix",
                    "cost_status",
                )
            },
            indent=2,
        )
    )
