#!/usr/bin/env python3
"""Inventory saved experiment evidence without executing experiment code.

Only writes this documentation directory. Does not import trial modules, access
credentials, contact services, or rerun model/database work. See README.md for scope.
"""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ROOTS = ["trials", "agent/runs", "agent-pgvector/verification", "harness/results",
         "harness/docs/qualification", "mini-bench/qualification", "research/verification",
         "research/agent-audit-2026-10-06", "release"]
SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache",
        ".ruff_cache", ".pytest_cache", "site-packages", "lib", "lib64", "bin", "include",
        "cache", "offline-cache", "wheelhouse", "wheels", "wheels-v2", "wheels-final",
        "sources", "source", "source-before", "engine-source", "core", "adapter", "engine",
        "images", "releases", "sandbox-build", "sandbox-build-v2", "private", "artifacts",
        "inputs", "evidence", "reference", "packages", "measurement"}
MARKERS = {"state.sqlite3", "status.json", "failure.json", "host-failure.json", "error.json",
           "result.json", "results.json", "run.json", "summary.json", "report.txt", "study.json",
           "study-report.txt", "selection.json", "agent-status.json", "verification.json",
           "native-summary.json", "smoke-result.json", "audit.json", "progress.json"}
FIELDS = {"status", "outcome", "stage", "accepted", "candidate_accepted", "termination_reason",
          "reason", "error", "type", "message", "censored", "failure", "canonical_acceptance_established",
          "confirmation_queries", "selected_policy", "provider_calls", "model_calls"}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(2 ** 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def link(path, label=None):
    target = os.path.relpath(ROOT / path, HERE)
    return f"[{label or Path(path).name}]({quote(target, safe='/#')})"


def recipe(path):
    p = ROOT / path
    if p.is_file():
        p = p.parent
    parts = p.relative_to(ROOT).parts
    family = parts[1] if len(parts) > 1 else parts[0]
    if path.startswith("trials/torch-reviews-results/"):
        name = parts[2]
        mapping = [("frozen-proposals-timing-v1-runtime-fix", "torch-reviews-frozen-proposals-timing-v1-runtime-fix"),
                   ("frozen-proposals-timing-v1", "torch-reviews-frozen-proposals-timing-v1"),
                   ("aggressive-policy-proposals-v2", "torch-reviews-aggressive-proposals-v2"),
                   ("aggressive-policy-proposals-v1", "torch-reviews-aggressive-proposals-v1"),
                   ("dispatch-overhead", "torch-reviews-dispatch-overhead-v1"),
                   ("insertion-bypass", "torch-reviews-insertion-bypass-v1"),
                   ("predicate-ablation", "torch-reviews-predicate-ablation-v1"),
                   ("training-stops-v2", "torch-reviews-training-stops-v2"),
                   ("policy-feedback", "torch-reviews-policy-feedback"),
                   ("policy-learning", "torch-reviews-policy-learning"),
                   ("collector-ab", "torch-reviews-collector-ab"), ("size-sweep", "torch-reviews-size-sweep"),
                   ("ef-sweep", "torch-reviews-ef-sweep"), ("reference-", "torch-reviews-reference-fix")]
        family = next((package for term, package in mapping if term in name), family)
    candidates = [ROOT / "trials" / family / "README.md"]
    if family == "morevec-movies-small":
        candidates += [ROOT / "trials" / family / "latency-diagnosis-README.txt",
                       ROOT / "trials" / family / "research-instructions.txt"]
    fallbacks = {"morevec-reviews-qualification": "qualify_workload.py",
                 "morevec-reviews-durable-workflow": "analyze_saved.py",
                 "morevec-reviews-workflow-review": "package_fix.py",
                 "torch-reviews-queue-optimization": "report.txt"}
    if family in fallbacks:
        candidates.append(ROOT / "trials" / family / fallbacks[family])
    if path.startswith("agent/runs/"):
        candidates += [ROOT / "agent/docs/OFFLINE_LEARNING.md"]
    if path.startswith("harness/"):
        candidates += [ROOT / "harness/docs/methodology.md", ROOT / "harness/README.md"]
    if path.startswith("mini-bench/"):
        candidates += [ROOT / "mini-bench/qualification/REPORT.md"]
    for ancestor in [p, *p.parents]:
        if ancestor == ROOT:
            break
        candidates += [ancestor / name for name in ["README.md", "study.sh", "study_entry.py",
                       "run_authorized_study.py", "report_results.py", "report.py", "report_investigation.py"]]
    if path.startswith("release/"):
        candidates += [ROOT / "agent/README.md"]
    found = next((q for q in candidates if q.is_file()), None)
    return rel(found) if found else None


def evidence_record(path, files, kind="saved evidence directory"):
    evidence = []
    observations = []
    for name in sorted(files):
        q = path / name
        if q.is_symlink() or not q.is_file():
            continue
        if (name in MARKERS or name.endswith("failure.json") or name.endswith("-journal.json")
                or ("authentication-check" in name and name.endswith(".json"))):
            item = {"path": rel(q)}
            if name != "state.sqlite3":
                item["sha256"] = sha(q)
            if q.suffix == ".json" and q.stat().st_size < 8_000_000:
                try:
                    data = json.loads(q.read_text())
                    if isinstance(data, dict):
                        selected = {k: v for k, v in data.items() if k in FIELDS and
                                    (v is None or isinstance(v, (str, int, float, bool)))}
                        item["observed_fields"] = selected
                        observations += [f"{k}={str(v)[:200]}" for k, v in selected.items()
                                         if v is not None and k in {"status", "outcome", "stage", "error", "failure"}]
                except (ValueError, UnicodeError):
                    item["parse_status"] = "unreadable JSON"
            if name in {"report.txt", "study-report.txt"}:
                lines = q.read_text(errors="replace").splitlines()
                item["headline"] = next((x.strip() for x in lines if x.strip()), "")[:400]
            evidence.append(item)
    record = {"path": rel(path), "kind": kind, "evidence": evidence,
              "recorded_outcome": "; ".join(dict.fromkeys(observations)) or "No terminal status inferred; inspect linked evidence",
              "reproduction_reference": recipe(rel(path))}
    db = path / "state.sqlite3"
    if db.is_file():
        try:
            with sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True) as con:
                has_state = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='state'").fetchone()
                if has_state:
                    status = con.execute("SELECT value FROM state WHERE key='status'").fetchone()
                    if status:
                        record["database_status"] = json.loads(status[0])
                    record["journaled_experiments"] = []
                    for key, value in con.execute("SELECT key,value FROM state WHERE key LIKE 'research_experiment:%'"):
                        data = json.loads(value)
                        record["journaled_experiments"].append({"experiment_id": data.get("experiment_id", key.split(":", 1)[1]),
                                                               "state": data.get("state"), "created_at": data.get("created_at"),
                                                               "finished_at": data.get("finished_at")})
        except (sqlite3.Error, ValueError) as error:
            record["database_read_error"] = type(error).__name__
    return record


def scan():
    records, archives, exclusions = [], [], []
    for base in ROOTS:
        start = ROOT / base
        if not start.exists():
            continue
        for dp, ds, fs in os.walk(start, followlinks=False):
            path = Path(dp)
            removed = [d for d in ds if d in SKIP or d.startswith(("runtime-install", "latency-fix-bundle", "latency-fix-release"))]
            ds[:] = sorted(d for d in ds if d not in removed and not (path / d).is_symlink())
            exclusions += [rel(path / d) for d in removed]
            archives += [path / f for f in fs if f.endswith((".tar.gz", ".tgz", ".zip")) and not (path / f).is_symlink()]
            found = set(fs) & MARKERS
            found |= {f for f in fs if f.endswith("failure.json") or f.endswith("-journal.json")}
            top_trial = path.parent == ROOT / "trials"
            result_root = path.parent == ROOT / "trials/torch-reviews-results"
            attempt = bool(re.match(r"(?:run|execution|prepared|qualification|oracle-preflight|quiet|settings-screen|stopping-feasibility|policy-stall|docker-stability|sequential-fix|latency-fix-recheck)-", path.name))
            verification_root = base in {"agent-pgvector/verification", "mini-bench/qualification", "research/agent-audit-2026-10-06"} and path == start
            if found or top_trial or result_root or attempt or verification_root:
                kind = "package or study family" if top_trial else "saved evidence directory"
                if "integration-only" in path.parts or base == "release" or path.name == "validation":
                    kind = "engineering/synthetic verification"
                elif "blocks" in path.parts or path.name.startswith("cohort-"):
                    kind = "measurement block or segment"
                elif "analysis" in path.name or path.name == "analysis":
                    kind = "analysis of existing run"
                elif "conversations" in path.parts:
                    kind = "agent conversation"
                elif "state.sqlite3" in fs:
                    kind = "saved agent/database state"
                records.append(evidence_record(path, fs, kind))
                if verification_root:
                    records[-1]["additional_verification_files"] = [rel(path / f) for f in sorted(fs) if f.endswith((".json", ".log", ".md"))]
            # Flat launch/failure receipts represent runs with no downloaded raw directory.
            if path.name == "torch-reviews-launch-20261015":
                for name in sorted(fs):
                    if name.endswith(".json"):
                        data = json.loads((path / name).read_text())
                        records.append({"path": rel(path / name), "kind": "Torch launch/failure receipt",
                                        "recorded_outcome": data.get("status", data.get("observed_failure", data.get("diagnosis", "See receipt; initial status may be superseded"))),
                                        "evidence": [{"path": rel(path / name), "sha256": sha(path / name)}],
                                        "remote_campaign": data.get("campaign", data.get("failed_campaign")),
                                        "reproduction_reference": "trials/torch-reviews-first/README.md"})
    correction = ROOT / "trials/torch-reviews-frozen-proposals-timing-v1-runtime-fix/runtime-repair.json"
    if correction.exists():
        for failed in json.loads(correction.read_text()).get("reported_failed_cohorts", []):
            records.append({"path": rel(correction), "run_id": failed["campaign"],
                            "kind": "remote failure with local provenance receipt",
                            "recorded_outcome": f"block 0 failed: Backend.runtime_profile absent; {failed['backend_calls']} backend calls; dependent array cancelled; raw failure files not downloaded",
                            "evidence": [{"path": rel(correction), "sha256": sha(correction)}],
                            "job_id": failed["failed_job"], "cancelled_array": failed["cancelled_array"],
                            "reproduction_reference": "trials/torch-reviews-frozen-proposals-timing-v1/README.md"})
    return sorted(records, key=lambda x: x["path"]), sorted(set(archives)), sorted(set(exclusions))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hash-archives", action="store_true", help="Stream archive bytes and compare saved checksum sidecars")
    args = parser.parse_args()
    stamp = datetime.now(ZoneInfo("America/New_York")).isoformat(timespec="seconds")
    records, archive_paths, exclusions = scan()
    data = {"schema_version": 1, "observed_at": stamp, "workspace_root": str(ROOT), "scope_roots": ROOTS,
            "scope_limit": "Saved workspace evidence only; remote-only/missing/deleted runs cannot be exhaustively enumerated. Blocks, analyses and fixtures are identified separately.",
            "excluded_directories": exclusions, "record_count": len(records),
            "journaled_experiment_count": sum(len(r.get("journaled_experiments", [])) for r in records), "records": records}
    (HERE / "run-inventory.json").write_text(json.dumps(data, indent=2) + "\n")
    lines = ["# Saved run and evidence catalog", "", f"Observed {stamp}. {len(records)} evidence records; these are **not** {len(records)} independent experiments.", "",
             "See [master index](README.md) for conclusions, missing remote failures and reproduction procedures. This catalog includes every discovered family, attempt, block, conversation, analysis and engineering fixture under the documented scan roots. No terminal status is inferred from a filename or a report's existence. JSON outcomes are observations, not scientific acceptance decisions.", "",
             "Artifact links require the original sibling workspace directories. Historical reruns need the linked recipe, saved configuration/manifest, original inputs and runtime. A missing recipe means exact invocation recovery is incomplete; inspect the directory's source/status/logs. Reading reports or regenerating this catalog runs no experiment.", ""]
    last_group = None
    for r in records:
        parts = Path(r["path"]).parts
        group = "/".join(parts[:2])
        if group != last_group:
            lines += ["", f"## {group}", "", "| Saved run / evidence | Kind and recorded outcome | Results / evidence | Reproduction reference |", "|---|---|---|---|"]
            last_group = group
        outcome = r["recorded_outcome"].replace("|", "\\|").replace("\n", " ")[:420]
        if "database_status" in r:
            outcome += "; database status=" + str(r["database_status"])
        artifacts = ", ".join(link(e["path"]) for e in r["evidence"] if Path(e["path"]).name != "state.sqlite3") or link(r["path"], "directory / saved state")
        repro = link(r["reproduction_reference"]) if r["reproduction_reference"] else "Exact invocation not recovered; inspect saved files"
        label = r.get("run_id", '/'.join(parts[2:]) or parts[-1])
        lines.append(f"| {link(r['path'], label)} | {r['kind']}; {outcome} | {artifacts} | {repro} |")
        for exp in r.get("journaled_experiments", []):
            lines.append(f"| `{exp['experiment_id']}` | Journaled experiment; state={exp.get('state')} | {link(r['path'], 'parent run database')} | Inspect with `fannagent experiments --run <parent-run>`; rerun needs original plan and runtime |")
    (HERE / "RUN_CATALOG.md").write_text("\n".join(lines) + "\n")
    if args.hash_archives:
        archives = []
        for path in archive_paths:
            digest = sha(path)
            sidecar = Path(str(path) + ".sha256")
            expected = None
            if sidecar.exists():
                matches = re.findall(r"\b[0-9a-fA-F]{64}\b", sidecar.read_text())
                expected = matches[0].lower() if len(matches) == 1 else None
            archives.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": digest,
                             "checksum_sidecar": rel(sidecar) if sidecar.exists() else None,
                             "expected_sha256": expected,
                             "checksum_status": "matches" if expected == digest else "MISMATCH" if expected else "no usable sidecar",
                             "backup_status": "local bytes verified; independent backup not verified"})
        (HERE / "archive-manifest.json").write_text(json.dumps({"schema_version": 1, "observed_at": stamp,
              "scope": "Archives under the same pruned scan roots as run-inventory.json; runtime/dependency caches and private stores excluded",
              "archive_count": len(archives), "total_bytes": sum(a["bytes"] for a in archives),
              "checksum_counts": dict(Counter(a["checksum_status"] for a in archives)), "archives": archives}, indent=2) + "\n")
    print(json.dumps({"evidence_records": len(records), "journaled_experiments": data["journaled_experiment_count"],
                      "archives_discovered": len(archive_paths), "archive_hashes_refreshed": args.hash_archives}))


if __name__ == "__main__":
    main()
