"""Verify the sealed 60-query timing rerun and compare the three allocations."""

import argparse
import hashlib
import io
import json
import re
import tarfile
from pathlib import Path
from statistics import fmean, stdev
from tempfile import TemporaryDirectory

from analyze import FAMILIES, equivalent, matches
from rb_plan import file_sha, require
from rb_stats import aa_equivalent
from shared_report import RAW, reconstruct

ALLOCATIONS = 3
T95_DF2 = 4.302652729696142
QUALITY_SHA = "4be2898ad8da3aa3a89c22f418cf66f5a860aa451d8d5a5c6d72b91e6ff65c1c"
PINS = {
    "freeze_sha256": "97356451b79ee0fbfec82018efb8e39fca38d4bf384741a03d63d0938e212c31",
    "fresh_queries_sha256": "e02218ae29e9ddac0e68049a5b96720b3345789cf6ed615f1f936a8979d3597f",
    "qualification_sha256": "5c0a93b5924ee41d618dab686d04f84309cf5133cb5009205e04b3d8da891b6b",
    "module_sha256": "9c1f0e4fabab9390507fa388f6a46edbb2a096aa8a11f1603d0ba592175915b1",
    "package_manifest_sha256": "b596c69bbab0bb49d720df02b820e5a9f2c1652a47e67b6b327f16f8769663bc",
    "runtime_sha256": "7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a",
}
HOST_KEYS = ("kernel", "vendor_id", "cpu family", "model", "model name", "stepping", "microcode")


def members(tar):
    files = {}
    for entry in tar:
        require(
            entry.isfile() and entry.size <= 16 * 1024**2 and entry.name not in files,
            "Invalid calibration return member",
        )
        files[entry.name] = tar.extractfile(entry).read()
    return files


def checksum(raw, name, record):
    require(
        record.decode("ascii").split() == [hashlib.sha256(raw).hexdigest(), name],
        f"Checksum mismatch for {name}",
    )


def one_return(payload, job, path, prior_quality):
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
        raw = members(tar)
    files = RAW | {"shared-receipt.json"}
    require(set(raw) == {f"results/{name}" for name in files}, "Unexpected job return inventory")
    path.mkdir()
    for name in files:
        (path / name).write_bytes(raw[f"results/{name}"])
    receipt = json.loads((path / "shared-receipt.json").read_bytes())
    require(
        receipt["job_id"] == job and all(receipt[k] == v for k, v in PINS.items()),
        "Frozen run identity differs",
    )
    require(
        receipt["data_and_index_verified_before_and_after"] is True
        and receipt["development_parity"]
        == {f: {"queries": 200, "stops": n} for f, n in zip(FAMILIES, (0, 21, 56), strict=True)},
        "Graph or recall parity differs",
    )
    result = reconstruct(path, receipt["raw_sha256"])
    actual = [json.loads(line) for line in (path / "quality.jsonl").read_bytes().splitlines()]
    for row, prior in zip(actual, prior_quality, strict=True):
        require(
            row["id"] == prior["id"]
            and matches(row["exact"], prior["exact"])
            and all(
                row[f]["checkpoint"] == prior[f]["checkpoint"]
                and matches(row[f]["output"], prior[f]["output"])
                for f in FAMILIES
            ),
            "Original recall output or stop decision differs",
        )
    require(
        equivalent(json.loads(json.dumps(result)), receipt["analysis"]),
        "Remote job analysis differs",
    )
    return result


def read_returns(path, sha_path):
    payload = path.read_bytes()
    checksum(payload, path.name, sha_path.read_bytes())
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
        raw = members(tar)
    reference = raw.pop("confirmation/prior-quality.jsonl")
    require(hashlib.sha256(reference).hexdigest() == QUALITY_SHA, "Reference output pin differs")
    prior_quality = [json.loads(line) for line in reference.splitlines()]
    jobs = [line.split("\t") for line in raw.pop("jobs.tsv").decode("ascii").splitlines()]
    require(
        len(jobs) == ALLOCATIONS and len({job for job, _ in jobs}) == ALLOCATIONS,
        "Expected three separate allocations",
    )
    returns = []
    with TemporaryDirectory(prefix="votes108-calibration-") as tmp:
        for job, node in jobs:
            require(
                re.fullmatch(r"[1-9][0-9]*", job) and re.fullmatch(r"cs[0-9]+", node),
                "Invalid Slurm job or node",
            )
            host_rows = raw.pop(f"host-{job}.tsv").decode("ascii").splitlines()
            host = dict(row.split("\t", 1) for row in host_rows)
            require(
                host.pop("job_id") == job
                and host.pop("node") == node
                and len(host_rows) == len(HOST_KEYS) + 2
                and set(host) == set(HOST_KEYS)
                and all(host.values()),
                "Invalid host metadata",
            )
            name = f"votes108-shared-{job}.tar.gz"
            inner = raw.pop(f"run-{job}/{name}")
            checksum(inner, name, raw.pop(f"run-{job}/{name}.sha256"))
            result = one_return(inner, job, Path(tmp) / job, prior_quality)
            returns.append({"job": job, "node": node, "host": host, "result": result})
    require(not raw, "Unexpected campaign return member")
    return returns


def interval3(samples):
    require(len(samples) == ALLOCATIONS, "Expected three allocation-level estimates")
    mean = fmean(samples)
    half_width = T95_DF2 * stdev(samples) / (ALLOCATIONS**0.5)
    return [mean - half_width, mean + half_width]


def paired(contrasts):
    gaps = [r["gap_ms"] for r in contrasts]
    logs = [r["log_ratio"] for r in contrasts]
    return {
        "gap_ms": fmean(gaps),
        "gap_ci95_ms": interval3(gaps),
        "gap_ms_by_job": gaps,
        "log_ratio": fmean(logs),
        "log_ratio_ci95": interval3(logs),
        "log_ratio_by_job": logs,
    }


def summarize(returns):
    reports = [job["result"] for job in returns]
    hardware_matches = all(job["host"] == returns[0]["host"] for job in returns)
    timing = [r["latency"] for r in reports]
    controls = {
        metric: {f: paired([t[key][f] for t in timing]) for f in FAMILIES}
        for metric, key in (("request", "request_aa"), ("session_per_query", "session_aa"))
    }
    control_pass = {
        metric: {f: aa_equivalent(value) for f, value in values.items()}
        for metric, values in controls.items()
    }
    contrasts = {
        metric: {key: paired([t["comparison"][metric][key] for t in timing]) for key in values}
        for metric, values in timing[0]["comparison"].items()
    }
    candidate = contrasts["request"]["candidate_vs_native"]
    repeated = candidate["log_ratio_ci95"][1] < 0 and all(g < 0 for g in candidate["gap_ms_by_job"])
    return {
        "scope": "Repeatability on the same 60 queries, using one timing estimate per allocation",
        "timing_interval": "Two-sided 95% Student t over three paired allocation means (2 df)",
        "allocations": returns,
        "matching_hardware_and_kernel": hardware_matches,
        "distinct_nodes": len({job["node"] for job in returns}),
        "request_and_session_means_ms": {
            f: {key: fmean(t["means"][f][key] for t in timing) for key in timing[0]["means"][f]}
            for f in FAMILIES
        },
        "mean_build_ms": fmean(r["lookup"]["build"]["total_ns"] / 1e6 for r in reports),
        "mean_attach_ms": {
            f: fmean(r["lookup"]["attach_ms"][f]["mean"] for r in reports)
            for f in ("candidate", "baseline")
        },
        "timed_requests": sum(t["ann_requests"] for t in timing),
        "timed_sessions": sum(t["sessions"] for t in timing),
        "identical_path": controls,
        "identical_path_pass": control_pass,
        "paired_comparison": contrasts,
        "query_calibration_pass": hardware_matches and all(control_pass["request"].values()),
        "candidate_passes_query_latency_and_recall": (
            hardware_matches
            and all(control_pass["request"].values())
            and repeated
            and all(r["recall"]["candidate"]["passes"] for r in reports)
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("checksum", type=Path)
    args = parser.parse_args()
    report = summarize(read_returns(args.archive, args.checksum))
    report["archive_sha256"] = file_sha(args.archive)
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
