"""Data-only B1b recovery for the proven /results container-name metadata bug.

Never changes the sealed experiment, returned data, scoring rules or verdicts.
"""

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import sys
import tarfile
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTPUT = ROOT / "trials/torch-reviews-native-effort-frontier-v1"
PACKAGE = OUTPUT / "torch-native-effort-frontier-v1"
MANIFEST = "35a09d4e2fd71598a023f6479e418d9e8bc90434d764a53564c60a5436b69c1f"
CAMPAIGN_PATTERN = r"reviews-native-effort-v1-[0-9]{8}T[0-9]{6}Z[.][A-Za-z0-9_-]+"


def sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text())


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_extracted_archive(archive, campaign):
    """Bind every extracted file to the checksum-verified original download."""
    archive, campaign = Path(archive).resolve(), Path(campaign).resolve()
    require(archive.name == campaign.name + ".tar.gz", "Archive/extracted campaign differs")
    checksum = Path(str(archive) + ".sha256").read_text().split()
    require(checksum == [sha(archive), archive.name], "Archive/checksum differs")
    files, total = {}, 0
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        require(len(members) <= 10000, "Too many returned files")
        for member in members:
            parts = PurePosixPath(member.name).parts
            require(
                member.isfile()
                and len(parts) >= 2
                and parts[0] == campaign.name
                and not PurePosixPath(member.name).is_absolute()
                and ".." not in parts,
                "Unsafe/nonregular archive member",
            )
            relative = str(PurePosixPath(*parts[1:]))
            require(relative not in files, "Duplicate archive member")
            require(member.size <= 256 * 1024**2, "Returned file exceeds budget")
            total += member.size
            require(total <= 2 * 1024**3, "Returned archive exceeds budget")
            path = campaign / relative
            require(not path.is_symlink() and path.is_file(), "Missing/linked extracted file")
            for parent in path.parents:
                if parent == campaign:
                    break
                require(not parent.is_symlink(), "Linked extracted parent")
            value = hashlib.sha256()
            with tar.extractfile(member) as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    value.update(chunk)
            require(sha(path) == value.hexdigest(), "Extracted data differs: " + relative)
            files[relative] = value.hexdigest()
    actual = {str(p.relative_to(campaign)) for p in campaign.rglob("*") if p.is_file()}
    require(actual == set(files), "Unexpected/missing extracted campaign files")
    return {
        "archive_sha256": sha(archive),
        "extracted_files_sha256": files,
        "uncompressed_bytes": total,
    }


def identity_proof(canonical, submission, host_exits, package_manifest):
    require(re.fullmatch(CAMPAIGN_PATTERN, canonical) is not None, "Invalid campaign identity")
    expected = "/home/dar579/torch-reviews-results/" + canonical
    require(submission["campaign"] == expected, "Submission/extracted campaign identity differs")
    require(
        submission["package"] == "/home/dar579/torch-native-effort-frontier-v1",
        "Submission package path differs",
    )
    require(package_manifest == MANIFEST, "Recovery targets another sealed package")
    require(set(submission["jobs"]) == {"block-0", "block-1"}, "Missing/unexpected jobs")
    for block in range(2):
        key = "block-" + str(block)
        job = submission["jobs"][key]
        require(re.fullmatch(r"[1-9][0-9]*", job) is not None, "Invalid job ID")
        require(
            submission["dispatch"][key] == {"status": "submitted", "job_id": job},
            "Job dispatch identity differs",
        )
        require(
            host_exits[block]["job_id"] == job and host_exits[block]["exit_code"] == 0,
            "Job completion identity differs",
        )
    return {
        "canonical_campaign": canonical,
        "submission_campaign": expected,
        "remote_container_directory": "/results",
        "permitted_remote_name": "results",
        "package_manifest_sha256": package_manifest,
        "jobs": submission["jobs"],
    }


def reconcile(local, remote, proof, parity):
    """Change exactly one proven mount-alias field in a copy, then strict parity."""
    require(proof["package_manifest_sha256"] == MANIFEST, "Identity proof package differs")
    canonical = proof["canonical_campaign"]
    require(local["campaign"] == canonical, "Local canonical campaign differs")
    require(
        local["package_manifest_sha256"] == MANIFEST
        and remote["package_manifest_sha256"] == MANIFEST,
        "Report package differs",
    )
    require(remote["campaign"] == "results", "Remote name is not the proven container alias")
    normalized = copy.deepcopy(remote)
    normalized["campaign"] = canonical
    parity(local, normalized)
    return {
        "field": "result/campaign",
        "remote_value": "results",
        "canonical_value": canonical,
        "reason": (
            "Sealed collect binds the canonical campaign to /results; reporter uses Path.name"
        ),
        "all_other_discrete_fields_exact": True,
        "absolute_float_tolerance": 1e-12,
    }


def recover(archive, output):
    require(sha(PACKAGE / "manifest.json") == MANIFEST, "Sealed manifest changed")
    sys.path.insert(0, str(PACKAGE))
    common = load_module("b1b_recovery_common", PACKAGE / "ef_common.py")
    cfg = common.verify(PACKAGE)
    common.bootstrap(PACKAGE)
    ingest = load_module("b1b_sealed_ingest", PACKAGE / "experiment.py")
    reporter = load_module("b1b_sealed_replay", PACKAGE / "ef_report.py")
    archive = Path(archive).resolve()
    canonical = archive.name.removesuffix(".tar.gz")
    campaign = OUTPUT / "returned" / canonical
    require(re.fullmatch(CAMPAIGN_PATTERN, canonical) is not None, "Unexpected archive name")
    if not campaign.exists():
        # This uses the original extraction checks; checksum checked before extraction.
        require(
            Path(str(archive) + ".sha256").read_text().split() == [sha(archive), archive.name],
            "Archive/checksum differs",
        )
        campaign = ingest.extract_data(archive, OUTPUT / "returned")
    archive_proof = check_extracted_archive(archive, campaign)
    submission = read(campaign / "submission.json")
    require(submission["counts"] == cfg["counts"], "Submission count contract differs")
    exits = [read(campaign / "blocks" / f"block-{b}" / "host-exit.json") for b in range(2)]
    proof = identity_proof(canonical, submission, exits, sha(PACKAGE / "manifest.json"))
    output = Path(output).resolve()
    require(
        not output.exists() or not any(output.iterdir()),
        "Recovery output exists; preserve it and select a fresh --output",
    )
    # No returned code or altered gate code is executed.
    result = reporter.analyze(campaign, PACKAGE, output)
    reconciliation = reconcile(
        result, read(campaign / "analysis/performance.json"), proof, ingest.parity
    )
    common.save(
        output / "verification.json",
        {
            "status": "passed_with_proven_campaign_metadata_reconciliation",
            "remote_local_statistical_and_gate_parity": True,
            "exact_unmodified_report_parity": False,
            "identity_proof": proof,
            "campaign_metadata_reconciliation": reconciliation,
            **archive_proof,
            "package_manifest_sha256": MANIFEST,
            "recovery_script_sha256": sha(Path(__file__)),
            "fresh_local_performance_sha256": sha(output / "performance.json"),
            "remote_performance_sha256": sha(campaign / "analysis/performance.json"),
            "raw_data_changed": False,
            "sealed_package_changed": False,
            "native_searches": 0,
            "DB_calls": 0,
            "provider_calls": 0,
            "new_fits": 0,
            "canonical_acceptance_established": False,
        },
    )
    print(str(output / "verification.json"))
    print(str(output / "report.txt"))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    recover(args.archive, args.output)
