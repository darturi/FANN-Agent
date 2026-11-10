"""Reconstruct the zero-search eligibility failure and its cleanup/preservation proof."""

import hashlib
import json
import tarfile
from pathlib import Path

from pc_common import CELLS, CONTRACT, digest, read, safe_file, sha

ROOT = Path("/Users/danielarturi/Developer/JinyangLiWork")
OLD = ROOT / "trials/torch-reviews-partial-calibration-v1-metadata-fix"
OUTPUT = ROOT / "trials/torch-reviews-startup-resource-stream-v1"
CAMPAIGN = "reviews-partial-calibration-v1-metadata-fix-20261028T000153Z.y1p9092a"
MANIFEST = "794db833de9306045caffbfeca43384f6b45171481bcbb1a21fb51213811615d"


COUNTS = dict(CONTRACT["counts"], allocations=1, vectors=200, cases=200)


def verify_failure():
    archive = OLD / (CAMPAIGN + ".tar.gz")
    campaign = OLD / "returned" / CAMPAIGN
    run = campaign / "run"
    if Path(str(archive) + ".sha256").read_text().split() != [sha(archive), archive.name]:
        raise ValueError("Failure archive checksum differs")
    package = OLD / "torch-partial-calibration-v1-metadata-fix"
    if sha(package / "manifest.json") != MANIFEST:
        raise ValueError("Previous seal changed")
    for n, h in read(package / "manifest.json")["files"].items():
        if sha(safe_file(package, n)) != h:
            raise ValueError("Previous package changed: " + n)
    raw = {}
    with tarfile.open(archive, "r:gz") as tar:
        for m in tar.getmembers():
            rel = Path(m.name)
            if not m.isfile() or rel.parts[0] != CAMPAIGN:
                raise ValueError("Unsafe failure member")
            key = str(rel.relative_to(CAMPAIGN))
            if key in raw:
                raise ValueError("Duplicate failure member")
            h = hashlib.sha256(tar.extractfile(m).read()).hexdigest()
            if sha(safe_file(campaign, key)) != h:
                raise ValueError("Failure extraction differs")
            raw[key] = h
    if raw != {str(f.relative_to(campaign)): sha(f) for f in campaign.rglob("*") if f.is_file()}:
        raise ValueError("Failure inventory differs")
    lock = read(run / "LOCK.json")
    if lock["complete"]:
        raise ValueError("Unexpected successful raw lock")
    for n, h in lock["files"].items():
        if sha(safe_file(run, n)) != h:
            raise ValueError("Failed raw lock differs: " + n)
    exempt = {
        "LOCK.json",
        "job-exit.json",
        "host-exit.json",
        "host-failure.json",
        "protected-source-after.json",
    }
    if {p.name for p in run.iterdir() if p.is_file()} - set(lock["files"]) - exempt:
        raise ValueError("Unexpected unlocked raw")
    record = read(campaign / "submission.json")
    status = read(run / "status.json")
    failure = read(run / "failure.json")
    host = read(run / "host-exit.json")
    if (
        record["package_manifest_sha256"] != MANIFEST
        or record["counts"] != COUNTS
        or record["jobs"] != {"block-0": "21159802"}
        or Path(record["campaign"]).name != CAMPAIGN
    ):
        raise ValueError("Submission identity differs")
    if not any(
        line.split("|")[:3] == ["21159802_0", "FAILED", "1:0"]
        for line in read(campaign / "scheduler-evidence.json")["sacct_stdout"].splitlines()
    ):
        raise ValueError("Terminal failure missing")
    if (
        status["status"] != "failed"
        or status["backend_searches"] != 0
        or status["search_sql"] != 0
        or status["operations"]
        or status["reader_connections"] != 2
        or status["plan_packets"] != 0
        or status["final_integrity_verified"]
        or status["result"] is not None
    ):
        raise ValueError("Different acquisition scope")
    if failure["type"] != "RuntimeError" or failure["message"] != "Snapshot eligibility changed":
        raise ValueError("Different failure")
    if any(status[k] != 0 for k in ("provider_calls", "confirmation_queries", "new_fits")):
        raise ValueError("Prohibited activity")
    if (
        host["exit_code"] != 1
        or host["job_id"] != "21159802"
        or not host["protected_sources_unchanged"]
    ):
        raise ValueError("Host identity/protection differs")
    if read(run / "cleanup.json") != dict(
        all_readers_closed=True, databases_stopped=True, errors=[]
    ):
        raise ValueError("Cleanup unverified")
    if not (
        read(run / "protected-source-before.json")
        == read(run / "protected-source-after.json")
        == read(campaign / "protected-source-before.json")
    ):
        raise ValueError("Protected inputs changed")
    before = read(run / "source-before.json")
    if before != read(run / "source-after.json"):
        raise ValueError("Retained clusters changed")
    copies = read(run / "copies.json")
    for c in CELLS:
        files = {
            n[len(c + "/pgdata/") :]: v
            for n, v in before["files"].items()
            if n.startswith(c + "/pgdata/")
        }
        expected_copy = dict(
            files=files, bytes=sum(v["bytes"] for v in files.values()), file_count=len(files)
        )
        if (
            copies[c]["pgdata_inventory_sha256"] != digest(expected_copy)
            or not copies[c]["independent_inodes"]
            or copies[c]["database_identity_sha256"] != sha(package / "frozen/source-index.json")
        ):
            raise ValueError("Whole-copy proof differs")
        if "database system is shut down" not in (run / (c + "-server.log")).read_text():
            raise ValueError("Stopped-server log missing")
    identity_sha = sha(package / "frozen/source-index.json")
    for c in CELLS:
        if before["files"][c + "/database-identity.json"]["sha256"] != identity_sha:
            raise ValueError("Retained identity differs")
        if read(run / "source-control.json")[c]["fields"]["Database cluster state"] != "shut down":
            raise ValueError("Unclean source")
        if (
            before["files"][c + "/pgdata/base/16384/264013"]["sha256"]
            != CONTRACT["graphs"]["native640"]["264013"]
        ):
            raise ValueError("Source full graph changed")
    if (
        before["files"]["partial640/pgdata/base/16384/270339"]["sha256"]
        != CONTRACT["graphs"]["partial640"]["partial"]["270339"]
    ):
        raise ValueError("Source partial graph changed")
    expected = read(package / "b2d-catalogs.json")
    cats = [json.loads(s) for s in (run / "catalogs.jsonl").read_text().splitlines()]
    if (
        len(cats) != 2
        or {r["copy"] for r in cats} != set(CELLS)
        or any(r["value"] != expected[r["copy"]] for r in cats)
    ):
        raise ValueError("Initial catalogs differ")
    result = dict(
        status="verified_zero_search_eligibility_startup_failure",
        campaign=CAMPAIGN,
        job="21159802_0",
        archive_sha256=sha(archive),
        archive_files=len(raw),
        raw_files_sha256=raw,
        previous_manifest_sha256=MANIFEST,
        raw_lock_verified=True,
        native_searches=0,
        reader_admissions=2,
        source_inventories_unchanged=True,
        source_file_count=before["file_count"],
        source_bytes=before["bytes"],
        identity_source_sha256=identity_sha,
        retained_identity_present_both_cells=True,
        initial_catalogs_match=True,
        cleanup_verified=True,
        protected_sources_unchanged=True,
        final_measurement_integrity_qualified=False,
        calibration_verdict=False,
        spent_allocations_total=3,
        automatic_retry=False,
        scheduler_maxrss="33534232K; accounting peak, anonymous RSS/headroom unresolved",
    )
    target = OUTPUT / "failed-archive-verification.json"
    if target.exists():
        if read(target) != result:
            raise ValueError("Existing failure verification differs")
    else:
        target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(verify_failure(), indent=2))
