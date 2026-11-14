"""Reconstruct shared build, attach, query and complete-session timings."""

import argparse
import json
import math
from pathlib import Path
from statistics import fmean, median

from analyze import equivalent, report, schedule
from rb_plan import file_sha, pinned, pinned_lines, require

RAW = {"quality.jsonl", "timing.jsonl", "eligible.json", "lookup.json"}


def reconstruct(directory, hashes):
    require(set(hashes) == RAW, "Unexpected raw return inventory")
    for name, digest in hashes.items():
        require(file_sha(directory / name) == digest, f"Return hash differs: {name}")
    lookup = json.loads(pinned(directory / "lookup.json", hashes["lookup.json"]))
    timing_rows = pinned_lines(directory / "timing.jsonl", hashes["timing.jsonl"])
    policy_rows = (r for r in timing_rows if not r["arm"].startswith("native-"))
    by_family = {"candidate": [], "baseline": []}
    for row, attach in zip(policy_rows, lookup["timed_attaches"], strict=True):
        family = row["arm"].rsplit("-", 1)[0]
        start, ready, _ = row["session_ns"]
        elapsed = attach["attach_ns"]
        require(
            attach["family"] == family and type(elapsed) is int and 0 < elapsed <= ready - start,
            "Attach timing differs from session schedule",
        )
        by_family[family].append(elapsed / 1e6)
    scheduled = [arm for _, _, arm, _ in schedule()]
    for f, times in by_family.items():
        require(len(times) == sum(a.startswith(f + "-") for a in scheduled), "Missing attach")
    build = lookup["build"]
    parts = [build[k] for k in ("open_and_lock_ns", "fetch_ns", "pack_publish_ns")]
    require(
        all(type(x) is int and x > 0 for x in parts) and sum(parts) == build["total_ns"],
        "Invalid lookup build timer",
    )
    require(build["rows"] == 247286 and build["qualifying"] == 49498, "Invalid lookup cohort")
    result = report(directory, hashes, query_controls=True)
    latency = result["latency"]
    paired = latency["comparison"]["request"]["candidate_vs_native"]
    query_faster = paired["log_ratio_ci95"][1] < 0 and all(g < 0 for g in paired["epoch_gap_ms"])
    result["candidate_passes_recall_and_query_latency"] = (
        result["recall"]["candidate"]["passes"]
        and all(latency["request_aa_pass_by_family"][f] for f in ("native", "candidate"))
        and query_faster
    )
    result["lookup"] = {
        "build": build,
        "prior_job": lookup["prior_job"],
        "prior_quality_sha256": lookup["prior_quality_sha256"],
        "attach_ms": {
            f: {"mean": fmean(times), "median": median(times), "connections": len(times)}
            for f, times in by_family.items()
        },
    }
    native = latency["means"]["native"]
    economics = {}
    for f in by_family:
        arm = latency["means"][f]
        saving = native["request_ms"] - arm["request_ms"]
        startup = arm["startup_ms"] - native["startup_ms"]
        available = 10 * (native["session_per_query_ms"] - arm["session_per_query_ms"])
        economics[f] = {
            "request_saving_ms": saving,
            "extra_startup_per_connection_ms": startup,
            "net_ten_query_session_saving_ms": available,
            "ten_query_connections_to_amortize_build": (
                max(1, math.ceil(build["total_ns"] / 1e6 / available)) if available > 0 else None
            ),
        }
    result["amortization_point_estimates"] = economics
    return result


def write_receipt(directory):
    original = json.loads((directory / "receipt.json").read_text())
    hashes = {**original["raw_sha256"], "lookup.json": file_sha(directory / "lookup.json")}
    result = reconstruct(directory, hashes)
    receipt = {**original, "raw_sha256": hashes, "analysis": result}
    with (directory / "shared-receipt.json").open("x") as f:
        json.dump(receipt, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    receipt = json.loads((args.directory / "shared-receipt.json").read_text())
    result = reconstruct(args.directory, receipt["raw_sha256"])
    require(
        equivalent(json.loads(json.dumps(result)), receipt["analysis"]),
        "Shared analysis did not reproduce",
    )
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
