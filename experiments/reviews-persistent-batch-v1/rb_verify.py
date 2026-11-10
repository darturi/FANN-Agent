"""Data-only verification and independent gate reconstruction for local returns."""

from __future__ import annotations

import json
from pathlib import Path

from rb_evidence import Evidence
from rb_measure import (
    MAX_RAW_FILE_BYTES,
    READER_SQL_LIMIT,
    STREAMS,
    check_timed,
    proof_outcome,
)
from rb_plan import INSTALLATIONS, PROFILES, READER_OPENS, SEARCHES, digest, pinned, require
from rb_stats import quality_reports, timing


def locked_raw(directory, *, streams=STREAMS, optional=("getters.json", "failure.json")):
    directory = Path(directory)
    lock = directory / "LOCK.json"
    require(
        lock.is_file() and not lock.is_symlink() and lock.stat().st_size <= 4096,
        "Invalid local return lock",
    )
    pins = json.loads(lock.read_bytes())["files_sha256"]
    mandatory = {"status.json", *(f"{name}.jsonl" for name in streams)}
    allowed = mandatory.union(optional)
    require(
        mandatory <= set(pins) <= allowed
        and {p.name for p in directory.iterdir()} == {*pins, lock.name},
        "Local return inventory changed",
    )
    data = {}
    for name, expected in pins.items():
        path = directory / name
        require(path.stat().st_size <= MAX_RAW_FILE_BYTES, "Raw file exceeds cap")
        contents = pinned(path, expected)
        data[name] = (
            [json.loads(line) for line in contents.splitlines()]
            if name.endswith(".jsonl")
            else json.loads(contents)
        )
    return data


def check_identity(row, seen):
    identity = row["reader"]
    require(
        type(identity) is list
        and len(identity) == 2
        and type(identity[0]) is int
        and identity[0] > 0
        and type(identity[1]) is str
        and identity[1]
        and tuple(identity) not in seen,
        "Reader freshness evidence changed",
    )
    seen.add(tuple(identity))


def check_requests(session, family, evidence, row):
    installed = False
    count = 0
    for case, record in zip(session.cases, row["requests"], strict=True):
        require(record["query_id"] == case.id, "Session request order changed")
        policy = evidence.policies.get(family)
        eligible = policy is not None and case.stratum in policy["eligible"]
        expected = int(eligible and not installed)
        require(
            type(record["installations"]) is int
            and record["installations"] == expected
            and record["composite"] == evidence.identities.get(family)
            and record["ordinary_default"] is (not eligible)
            and record["policy_applied"] is eligible
            and record["bypass"] is (policy is not None and not eligible),
            "Installation, route or acknowledgement evidence changed",
        )
        count += record["installations"]
        installed |= eligible
    return count


def verify_local(directory, plan, frozen, evidence):
    return _reconstruct(directory, plan, frozen, evidence, synthetic_only=True)


def _reconstruct(directory, plan, frozen, evidence, *, synthetic_only):
    raw = locked_raw(directory)
    status = raw["status.json"]
    require(
        status["synthetic_only"] is synthetic_only and status["candidate"] == evidence.identities,
        "Return identity changed",
    )
    disposition = status["disposition"]
    if disposition == "invalid_incomplete":
        require("failure.json" in raw, "Missing failure record")
        return {
            "disposition": disposition,
            "development_qualifier": False,
            "failure": raw["failure.json"],
        }
    require(
        disposition in ("closed_negative_quality", "complete") and "failure.json" not in raw,
        "Inconsistent return disposition",
    )
    getters = raw["getters.json"]
    seen = set()
    check_identity(getters, seen)
    for mode, profile, report in zip(
        ("base", "static", "progress"), PROFILES, getters["reports"], strict=True
    ):
        names = frozen.policy.names(plan.config, profile)
        require(
            report
            == {
                "profile": mode,
                "features": names,
                "status": "passed",
                "backend_calls": 3 * (1 + 4 * len(names)),
            },
            "Getter proof changed",
        )
    refs = {}
    for case, ref in zip(plan.cases.values(), raw["references.jsonl"], strict=True):
        require(
            ref["query_id"] == case.id and digest(ref) == digest(evidence.references[case.id]),
            "Fresh reference coverage or identity changed",
        )
        refs[case.id] = ref

    proof = {"seed": {}, "candidate": {}}
    proof_installs = 0
    scheduled = ((family, session) for family in proof for session in plan.sessions)
    for (family, session), row in zip(scheduled, raw["proofs.jsonl"], strict=True):
        require((row["arm"], row["session_id"]) == (family, session.id), "Proof schedule changed")
        check_identity(row, seen)
        proof_installs += check_requests(session, family, evidence, row)
        for record in row["requests"]:
            proof[family][record["query_id"]] = proof_outcome(evidence, family, record)

    actual = Evidence(refs, evidence.eligible, evidence.policies, evidence.identities, proof)
    report = quality_reports(plan, frozen, actual)
    complete = disposition == "complete"
    require(complete == report["passes"], "Quality did not gate timing")
    installed = 0
    last_close = 0
    timed_rows = raw["timings.jsonl"]
    slots = plan.timed() if complete else ()
    for (epoch, session, arm), row in zip(slots, timed_rows, strict=True):
        require(
            (row["epoch"], row["session_id"], row["arm"]) == (epoch, session.id, arm),
            "Timing slot order changed",
        )
        check_identity(row, seen)
        start, _, _, _, end = row["boundary_ns"]
        require(
            type(start) is int and start >= last_close and type(end) is int,
            "Timed sessions overlap or run out of order",
        )
        last_close = end
        family = arm.split("-")[0]
        installed += check_requests(session, family, evidence, row)
        for record in row["requests"]:
            check_timed(evidence, proof, family, record)

    accounting = status["accounting"]
    searches = {name: count for name, count in SEARCHES.items() if complete or name != "timing"}
    readers = {name: count for name, count in READER_OPENS.items() if complete or name != "timing"}
    install_counts = accounting["installations"]
    require(
        accounting["searches"] == searches
        and accounting["reader_opens"] == readers
        and accounting["reader_closes"] == readers
        and len(seen) == sum(readers.values())
        and accounting["reader_startup_sql_reserved"] == sum(readers.values()) * READER_SQL_LIMIT
        and set(install_counts) <= set(INSTALLATIONS)
        and all(type(n) is int and 0 <= n <= INSTALLATIONS[k] for k, n in install_counts.items())
        and install_counts.get("proof", 0) == proof_installs == 120
        and install_counts.get("timing", 0) == installed == (480 if complete else 0),
        "Reconstructed operation accounting changed",
    )

    latency = timing(plan, timed_rows) if complete else None
    verdict = "closed_negative_quality"
    if latency is not None:
        if not latency["aa_pass"]:
            verdict = "measurement_inconclusive"
        else:
            verdict = "would_pass" if latency["latency_pass"] else "closed_negative_latency"
    return {
        "synthetic_only": synthetic_only,
        "development_qualifier": False,
        "fixture_verdict" if synthetic_only else "provisional_verdict": verdict,
        "quality": report,
        "timing": latency,
        "accounting": accounting,
    }
