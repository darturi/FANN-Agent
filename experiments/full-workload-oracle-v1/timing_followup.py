"""Reuse frozen acquisition; reserve query windows before unmodified serving measurements."""

import json
import os
import shutil
from pathlib import Path

from common import matches, sha, threshold, write
from oracle_design import FAMILIES, FILTERS, MAX_ATTEMPTS, qualifies, require, validate_output
from oracle_experiment import acquire as original_acquire
from oracle_experiment import emit, perform, set_target
from sessions import bind, session

SOURCE_FILES = (
    "exact-reference.jsonl",
    "quality.jsonl",
    "prefixes.jsonl",
    "trajectories.jsonl",
    "oracle-freeze.json",
    "eligibility.json",
    "attempts.json",
)
BASE_OPERATIONS = (
    "offline_exact",
    "native_quality",
    "canonical_capture",
    "forced_prefix",
    "oracle_quality",
    "matched_quality",
)


def lines(path):
    with path.open() as handle:
        for line in handle:
            yield json.loads(line)


def source_lines(path, torn_files=()):
    """Only a declared, unterminated final record may be interrupted evidence."""
    with path.open() as handle:
        while True:
            line = handle.readline()
            if not line:
                return
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                require(
                    path.name in torn_files and not line.endswith("\n") and handle.read(1) == "",
                    "corrupt source record before handoff",
                )
                return


def verify_source(
    folder, manifest, roles, *, expected_cases=7000, usage_name="attempts.json", allow_partial=False
):
    """No synthetic receipt or timing is used to promote an acquisition."""
    for name, expected in manifest["files"].items():
        path = folder / (usage_name if name == "attempts.json" else name)
        require(sha(path) == expected, "source acquisition changed: " + name)
    frozen_path = folder / "oracle-freeze.json"
    frozen = json.loads(frozen_path.read_text()) if frozen_path.exists() else None
    require(frozen is not None or allow_partial, "missing complete acquisition freeze")
    if frozen is not None:
        for name in ("quality", "prefixes", "trajectories"):
            require(
                sha(folder / (name + ".jsonl")) == frozen[name + "_sha256"], "source freeze changed"
            )

    def indexed(name):
        rows = list(
            source_lines(
                folder / name, manifest.get("torn_final_record_files", ()) if allow_partial else ()
            )
        )
        values = {r["id"]: r for r in rows}
        require(len(values) == len(rows), "duplicate source rows")
        return values

    quality = indexed("quality.jsonl")
    truth = indexed("exact-reference.jsonl")
    trajectories = indexed("trajectories.jsonl")
    require(
        len(truth) == expected_cases
        and set(truth) == set(roles)
        and set(quality) <= set(truth)
        and set(quality) <= set(trajectories),
        "source acquisition coverage differs",
    )
    if not allow_partial:
        require(
            len(quality) == frozen["cases"] == expected_cases and set(quality) == set(trajectories),
            "incomplete source acquisition",
        )
    eligible = {
        int(t): set(ids) for t, ids in json.loads((folder / "eligibility.json").read_text()).items()
    }
    positions = {qid: 0 for qid in quality}
    found = set()
    labels = 0
    raw_labels = 0
    incomplete_queries = set()
    for row in source_lines(
        folder / "prefixes.jsonl",
        manifest.get("torn_final_record_files", ()) if allow_partial else (),
    ):
        qid = row["id"]
        raw_labels += 1
        if allow_partial and qid not in quality:
            require(qid in roles, "unknown incomplete source query")
            incomplete_queries.add(qid)
            continue
        require(qid in quality and qid not in found, "unknown or post-selection source prefix")
        reference = quality[qid]
        positions[qid] += 1
        cp = positions[qid]
        trajectory = trajectories[qid]
        score = validate_output(row["output"], eligible[row["filter"]], truth[qid]["output"])
        safe = qualifies(row["output"], score, reference["native"], reference["native_recall"])
        require(
            row["checkpoint"] == cp
            and row["prefix_verified"] is True
            and row["prefix_sha256"] == trajectory["prefix_sha256"][cp - 1]
            and row["target"] == trajectory["targets"][cp - 1]
            and abs(score - row["recall"]) < 1e-12
            and row["qualifies"] == safe,
            "source causal prefix or score differs",
        )
        if safe:
            require(
                reference["checkpoint"] == cp and matches(row["output"], reference["output"]),
                "source earliest stop differs",
            )
            found.add(qid)
        labels += 1
    for qid, row in quality.items():
        t = row["filter"]
        native_score = validate_output(row["native"], eligible[t], truth[qid]["output"])
        score = validate_output(row["output"], eligible[t], truth[qid]["output"])
        require(
            row["role"] == roles[qid]
            and abs(native_score - row["native_recall"]) < 1e-12
            and abs(score - row["recall"]) < 1e-12
            and qualifies(row["output"], score, row["native"], native_score),
            "source quality differs",
        )
        require(
            positions[qid]
            == row["tested_count"]
            == (row["checkpoint"] or row["native_checkpoint_count"]),
            "missing earlier source stop",
        )
        require((qid in found) == bool(row["checkpoint"]), "missing source selection")
        if not row["checkpoint"]:
            require(matches(row["output"], row["native"]), "source native fallback differs")
        trajectory = trajectories[qid]
        require(
            trajectory["count"] == row["native_checkpoint_count"]
            and len(trajectory["targets"])
            == len(trajectory["prefix_sha256"])
            == trajectory["count"]
            and matches(trajectory["output"], row["native"]),
            "source trajectory differs",
        )
    usage = json.loads((folder / usage_name).read_text())
    # A derived count of used evidence records is explicitly separate from the
    # cumulative charged ledger, which is checked independently by the adapter.
    if "used_records" in usage:
        usage = usage["used_records"]
    completed = len(quality)
    expected = {
        "offline_exact": expected_cases,
        "native_quality": 2 * completed,
        "canonical_capture": completed,
        "forced_prefix": labels,
        "oracle_quality": completed,
        "matched_quality": completed,
    }
    if allow_partial:
        require(
            len(incomplete_queries) <= 1
            and usage["offline_exact"] == expected_cases
            and usage.get("timed_ann", 0) == usage.get("warmup_ann", 0) == 0,
            "handoff must precede source timing",
        )
        for k, extra in (
            ("native_quality", 2),
            ("canonical_capture", 1),
            ("oracle_quality", 1),
            ("matched_quality", 1),
        ):
            require(
                expected[k] <= usage.get(k, 0) <= expected[k] + extra,
                "source partial-query accounting differs",
            )
        require(
            raw_labels <= usage["forced_prefix"] <= raw_labels + 1,
            "source pending prefix was not charged",
        )
    else:
        require(
            all(usage.get(k) == v for k, v in expected.items()), "source acquisition ledger differs"
        )
    require(
        set(usage) <= {*expected, "warmup_ann", "timed_ann", "total"}
        and usage["total"] == sum(v for k, v in usage.items() if k != "total"),
        "source spending cannot be reset",
    )
    return quality, {qid: r["output"] for qid, r in truth.items()}, eligible, usage


class WindowLedger:
    """Reserve a whole window durably. Every unused/uncertain slot stays charged."""

    def __init__(self, output, source_charged, *, window=1024, cap=MAX_ATTEMPTS):
        require(0 <= source_charged <= cap and window > 0, "invalid ledger bounds")
        self.output, self.window, self.cap = output, window, cap
        self.source_charged = source_charged
        self.ceiling = source_charged
        self.reservations = 0

    def reserve(self, counter, operation):
        require(
            counter["total"] >= self.source_charged and counter["total"] < self.cap,
            "cumulative attempt ceiling reached",
        )
        if counter["total"] == self.ceiling:
            self.ceiling = min(self.cap, self.ceiling + self.window)
            self.reservations += 1
            record = {
                "source_charged": self.source_charged,
                "reserved_total": self.ceiling,
                "actual_total_at_reservation": counter["total"],
                "window": self.window,
                "reservations": self.reservations,
                "cap": self.cap,
            }
            pending = self.output / "reservation.pending"
            with pending.open("w") as handle:
                json.dump(record, handle)
                handle.flush()
                os.fsync(handle.fileno())
            pending.replace(self.output / "reservation.json")
        require(counter["total"] < self.ceiling, "unreserved query")
        counter["total"] += 1
        counter[operation] += 1

    def finish(self, counter):
        write(self.output / "attempts.json", dict(counter))
        write(
            self.output / "reservation-final.json",
            {
                "source_charged": self.source_charged,
                "actual_total": counter["total"],
                "charged_total": self.ceiling,
                "unused_charged": self.ceiling - counter["total"],
                "reservations": self.reservations,
                "window": self.window,
                "cap": self.cap,
            },
        )


def reserve(counter, operation, args):
    args.window_ledger.reserve(counter, operation)


def load_acquisition(Backend, args, queries, eligible, counter):
    del Backend
    source = getattr(args, "acquisition_path", Path("/acquisition"))
    manifest_path = getattr(
        args, "acquisition_manifest", Path(__file__).parent / "source-acquisition.json"
    )
    manifest = json.loads(manifest_path.read_text())
    choices, truths, prior_eligible, usage = verify_source(
        source, manifest, args.roles, expected_cases=len(queries), allow_partial=True
    )
    require(eligible == prior_eligible, "fresh clone eligibility differs")
    archived = args.output / "source-acquisition"
    archived.mkdir(mode=0o700)
    for name in manifest["files"]:
        shutil.copyfile(source / name, archived / name)
    require(
        sha(args.output / "eligibility.json") == sha(source / "eligibility.json"),
        "eligibility bytes differ",
    )
    shutil.copyfile(source / "exact-reference.jsonl", args.output / "exact-reference.jsonl")
    write(args.output / "source-acquisition.json", manifest)
    used = evidence_counts(choices, len(queries))
    counter.update(used)
    for op in BASE_OPERATIONS:
        if op != "offline_exact":
            counter["source_incomplete_" + op] = usage.get(op, 0) - used[op]
    unpublished = int(bool(manifest.get("unpublished_reservation_charged", False)))
    counter["source_unpublished_reserved"] = unpublished
    counter["total"] = usage["total"] + unpublished
    args.window_ledger = WindowLedger(args.output, counter["total"])
    args.frozen_choices = choices
    args.source_acquisition = archived
    args.source_manifest = manifest
    return truths


def evidence_counts(choices, exact_cases):
    count = len(choices)
    counts = {
        "offline_exact": exact_cases,
        "native_quality": 2 * count,
        "canonical_capture": count,
        "forced_prefix": sum(r["tested_count"] for r in choices.values()),
        "oracle_quality": count,
        "matched_quality": count,
    }
    counts["total"] = sum(counts.values())
    return counts


def resume_and_qualify(Backend, args, queries, eligible, truths, counter):
    root = args.output
    old_choices = dict(args.frozen_choices)
    remaining = [q for q in queries if q["id"] not in old_choices]
    added = {}
    if remaining:
        args.output = root / "new-acquisition"
        args.output.mkdir(mode=0o700)
        try:
            added = original_acquire(Backend, args, remaining, eligible, truths, counter)
        finally:
            args.output = root
    choices = {**old_choices, **added}
    require(len(choices) == len(queries), "resume did not complete every case")
    for name in ("quality", "prefixes", "trajectories"):
        with (root / (name + ".jsonl")).open("x") as out:
            for row in source_lines(
                args.source_acquisition / (name + ".jsonl"),
                args.source_manifest.get("torn_final_record_files", ()),
            ):
                if row["id"] in old_choices:
                    emit(out, row)
            if remaining:
                for row in lines(root / "new-acquisition" / (name + ".jsonl")):
                    emit(out, row)
    write(
        root / "oracle-freeze.json",
        {
            **{
                name + "_sha256": sha(root / (name + ".jsonl"))
                for name in ("quality", "prefixes", "trajectories")
            },
            "cases": len(choices),
            "timing_started": False,
            "reused_completed_cases": len(old_choices),
            "fresh_cases": len(added),
            "criterion": "earliest actual checkpoint preserving native recall and result count",
        },
    )
    write(
        root / "acquisition-counts.json",
        {
            "definition": "used evidence records, not a spending ledger",
            "used_records": evidence_counts(choices, len(queries)),
        },
    )
    args.frozen_choices = choices
    return qualify_reused(Backend, args, queries, eligible, truths, counter)


def qualify_reused(Backend, args, queries, eligible, truths, counter):
    choices = args.frozen_choices
    with (args.output / "followup-quality.jsonl").open("x") as output:
        for t in FILTERS:
            cases = [q for q in queries if threshold(q) == t]
            for family in FAMILIES:
                arm = {"native": None, "oracle": 10, "matched": 11, "empty": 43}[family]
                with session(Backend, args) as c, bind(c, args, t, len(eligible[t]), arm):
                    for q in cases:
                        row = choices[q["id"]]
                        if family in ("oracle", "matched"):
                            set_target(c, row["checkpoint"])
                        actual = perform(c, q, counter, "followup_quality_ann", args)
                        wanted = row["output" if family == "oracle" else "native"]
                        require(
                            matches(actual["output"], wanted), "fresh replay changed frozen answer"
                        )
                        score = validate_output(actual["output"], eligible[t], truths[q["id"]])
                        target_score = row["recall" if family == "oracle" else "native_recall"]
                        require(abs(score - target_score) < 1e-12, "fresh replay recall changed")
                        checkpoint = (
                            c.execute("SELECT fannagent.confirm_last()").fetchone()[0] if arm else 0
                        )
                        require(
                            checkpoint == (row["checkpoint"] if family == "oracle" else 0),
                            "fresh replay checkpoint changed",
                        )
                        emit(
                            output,
                            {
                                "id": q["id"],
                                "filter": t,
                                "family": family,
                                "checkpoint": checkpoint,
                                "recall": score,
                                **actual,
                            },
                        )
            output.flush()
            print(
                json.dumps(
                    {"phase": "followup_quality", "filter": t, "attempts": counter["total"]}
                ),
                flush=True,
            )
    return choices
