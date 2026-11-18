"""Reuse frozen full acquisition, conservatively carrying every earlier reservation."""

import json
import shutil
from pathlib import Path

from common import sha, write
from oracle_design import require
from timing_followup import WindowLedger, evidence_counts, verify_source

EVIDENCE = (
    "exact-reference.jsonl",
    "quality.jsonl",
    "prefixes.jsonl",
    "trajectories.jsonl",
    "oracle-freeze.json",
    "acquisition-counts.json",
    "eligibility.json",
)


def source_counts(manifest, choices, cases):
    counts = evidence_counts(choices, cases)
    for op, value in manifest["source_incomplete_charges"].items():
        counts["source_incomplete_" + op] = value
    counts["previous_partial_quality_ann"] = manifest["partial_quality_rows"]
    counts["previous_unobserved_reserved"] = manifest["unobserved_reserved_charges"]
    counts["total"] = sum(v for k, v in counts.items() if k != "total")
    require(counts["total"] == manifest["prior_reserved_total"], "prior budget was reset")
    return counts


def load_source(Backend, args, queries, eligible, counter):
    del Backend
    source = getattr(args, "acquisition_path", Path("/acquisition"))
    manifest_path = getattr(
        args, "acquisition_manifest", Path(__file__).parent / "source-acquisition.json"
    )
    manifest = json.loads(manifest_path.read_text())
    choices, truths, prior_eligible, _ = verify_source(
        source,
        manifest,
        args.roles,
        expected_cases=len(queries),
        usage_name="acquisition-counts.json",
    )
    require(eligible == prior_eligible, "fresh graph eligibility changed")
    archived = args.output / "source-acquisition"
    archived.mkdir(mode=0o700)
    for name in manifest["files"]:
        target = archived / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
    for name in EVIDENCE:
        if name == "eligibility.json":
            require(sha(args.output / name) == sha(source / name), "eligibility bytes changed")
        else:
            shutil.copyfile(source / name, args.output / name)
    write(args.output / "source-acquisition.json", manifest)
    counter.update(source_counts(manifest, choices, len(queries)))
    args.window_ledger = WindowLedger(args.output, counter["total"])
    args.frozen_choices = choices
    return truths


def reuse_choices(Backend, args, queries, eligible, truths, counter):
    del Backend, queries, eligible, truths, counter
    # Every warmup and timed answer is checked against the frozen source. These
    # replay checks cover every case/family on the fresh graph; no extra full pass.
    return args.frozen_choices
