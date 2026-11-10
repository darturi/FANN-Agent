"""Review a held candidate package or run its guest only with a separate admission."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import signal
import time
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

from rb_seal import inventory, need, sha_bytes, sha_file, verify_directory

BASE_MANIFEST = "5538cb6a4bd03da6a00fae4913fdfe9237b481f902bcd15d98666f2e99af070a"
RUNNER = "266bf3d65acc33f18cb0a9d3455a5a562d4ec2e65b608afe94e680b309ca1550"
IMAGE = "7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a"
MODULE = "e7dcace1f4dfd4ea233256d6cdfc17b3190f3f07cccb6406b479b5ebe8b85811"
GRAPH = "90f4a709ab3ee7ce40fe7630009b29d5646f6e1e80ceab8c2246cb970d803484"
CANDIDATE = "e7f1ae0465bfe05aaf7d7768adf93ef6c99fe2be1eaa7be3fa73509bea75882b"
PROPOSAL = "0ce789c4315da6e2fb90df92a0e2ae4b41ec6b6082c3eda60b1054a8a6383a1b"
DISPOSITION = "ddd94b4e59fc46f7fde93a6c0efd2bdb70116de559a3bc1a201374521d7e1f64"
MEMORY_BYTES = 32 * 1024**3


def read_json(path):
    return json.loads(Path(path).read_bytes())


def load_stage(package, manifest_sha):
    package = Path(package).resolve()
    verify_directory(package, manifest_sha)
    # These modules and the frozen vendor inputs are loaded only after the outer pin passes.
    from rb_evidence import Evidence, load_frozen
    from rb_plan import PACKAGE, PILOT_MANIFEST, PINS, SEED_ID, load_plan, pinned
    from rb_stats import quality

    root = package / "inputs"
    plan = load_plan(root)
    frozen = load_frozen(root)
    payload = read_json(package / "native-inputs.json")
    source = root / PACKAGE
    source_pins = json.loads(pinned(source / "manifest.json", PILOT_MANIFEST))["files"]
    index = json.loads(pinned(source / "source-index.json", source_pins["source-index.json"]))
    need(sha_file(package / "proposal.json") == PROPOSAL, "Frozen proposal changed")
    freeze = read_json(package / "candidate-freeze.json")
    need(
        freeze
        == {
            "candidate_sha256": PROPOSAL,
            "frozen_design_inputs_sha256": PINS,
            "policy_semantic_sha256": CANDIDATE,
            "proposal_disposition_sha256": DISPOSITION,
            "torch_released": False,
        },
        "Candidate freeze changed",
    )
    candidate, candidate_id = frozen.policy.validate(
        read_json(package / "proposal.json"), plan.config
    )
    seed, seed_id = frozen.policy.validate(plan.seed, plan.config)
    identities = {"seed": seed_id, "candidate": candidate_id}
    need(
        identities == payload["identities"] == {"seed": SEED_ID, "candidate": CANDIDATE},
        "Frozen policy identity changed",
    )
    need(
        index["index_identity"] == GRAPH
        and plan.config["image_sha256"] == IMAGE
        and plan.config["module_sha256"] == MODULE
        and index["row_count"] == 247286,
        "Native reference identity changed",
    )
    need(sha_file(package / "modules/vector.so") == MODULE, "Native module changed")
    expected_cases = set(plan.cases)
    need(
        set(payload["references"]) == expected_cases
        and set(payload["outcomes"]) == set(identities)
        and all(set(cases) == expected_cases for cases in payload["outcomes"].values()),
        "Native development evidence coverage changed",
    )
    expected_counts = index["filter_eligible_rows"]
    need(set(payload["eligible"]) == set(expected_counts), "Unexpected eligibility stratum")
    eligible = {}
    for filt, ids in payload["eligible"].items():
        need(
            all(type(i) is int and 0 <= i < index["row_count"] for i in ids)
            and len(ids) == len(set(ids)) == expected_counts[filt],
            "Eligibility proof changed",
        )
        eligible[filt] = frozenset(ids)
    need(
        eligible["votes108"] <= eligible["votes32"] <= eligible["unfiltered"],
        "Filter eligibility sets are inconsistent",
    )
    evidence = Evidence(
        payload["references"],
        eligible,
        {"seed": seed, "candidate": candidate},
        identities,
        payload["outcomes"],
    )
    saved_recall = quality(plan, frozen, evidence, "candidate")
    need(
        saved_recall == payload["saved_recall"] and saved_recall["passes"],
        "Candidate's offline recall does not reproduce",
    )
    return SimpleNamespace(
        package=package,
        source=root / PACKAGE,
        manifest_sha=manifest_sha,
        frozen=frozen,
        plan=plan,
        evidence=evidence,
        index=index,
    )


def admission(path, expected_sha, manifest_sha, *, identity=CANDIDATE):
    raw = Path(path).read_bytes()
    need(sha_bytes(raw) == expected_sha, "External admission digest differs")
    record = json.loads(raw)
    need(
        set(record) == {"schema", "package_manifest_sha256", "candidate", "job_id", "uid"}
        and record["schema"] == "reviews-persistent-batch.single-approved-allocation.v1"
        and record["package_manifest_sha256"] == manifest_sha
        and record["candidate"] == identity
        and type(record["uid"]) is int
        and record["uid"] > 0
        and type(record["job_id"]) is str
        and re.fullmatch(r"[1-9][0-9]*", record["job_id"]),
        "Invalid single-job admission",
    )
    need(
        os.uname().sysname == "Linux"
        and os.uname().machine == "x86_64"
        and os.getuid() == record["uid"]
        and os.environ.get("SLURM_JOB_ID") == record["job_id"],
        "Admission requires the named native x86_64 allocation",
    )
    return record


def resource_limits():
    cpus = sorted(os.sched_getaffinity(0))
    cores = set()
    for cpu in cpus:
        topology = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        cores.add(
            tuple(int((topology / key).read_text()) for key in ("physical_package_id", "core_id"))
        )
    need(len(cpus) == len(cores) == 4, "Expected four distinct physical CPUs")
    groups = [
        line.removeprefix("0::")
        for line in Path("/proc/self/cgroup").read_text().splitlines()
        if line.startswith("0::")
    ]
    need(
        len(groups) == 1 and groups[0].startswith("/") and ".." not in Path(groups[0]).parts,
        "Cgroup v2 allocation is not visible",
    )
    mount = Path("/sys/fs/cgroup")
    group = mount / groups[0].lstrip("/")
    need(group.is_dir(), "Allocation cgroup cannot be read")
    finite = []
    for parent in (group, *group.parents):
        if not parent.is_relative_to(mount):
            break
        cap = parent / "memory.max"
        if cap.is_file():
            value = cap.read_text().strip()
            if value != "max":
                finite.append((int(value), parent))
    need(
        finite and min(value for value, _ in finite) == MEMORY_BYTES,
        "Expected the effective 32 GiB job memory limit",
    )
    limit_group = next(parent for value, parent in finite if value == MEMORY_BYTES)
    return {"cpus": cpus, "cores": sorted(cores), "memory_limit": MEMORY_BYTES}, limit_group


def memory_events(group):
    values = dict(line.split() for line in (group / "memory.events").read_text().splitlines())
    return {key: int(values[key]) for key in ("max", "oom", "oom_kill")}


def check_native_inputs(stage, bundle, prepared):
    for folder in (stage.package, bundle, prepared):
        need(os.statvfs(folder).f_flag & os.ST_RDONLY, "Expected a read-only input mount")
    need(sha_file(bundle / "manifest.json") == BASE_MANIFEST, "Base bundle manifest changed")
    base = read_json(bundle / "manifest.json")["files"]
    for name in (
        "images/runtime.sif",
        "inputs/reviews.parquet",
        "inputs/local-identity.json",
        "experiment.json",
    ):
        need(sha_file(bundle / name) == base[name], f"Base bundle input differs: {name}")
    ready = read_json(prepared / "READY.json")
    need(
        ready["architecture"] == "x86_64"
        and ready["image_sha256"] == IMAGE
        and read_json(prepared / "database-identity.json") == stage.index
        and (prepared / "base/backup_manifest").is_file(),
        "Prepared backup identity changed",
    )
    need(
        sha_file(Path("/opt/torch-reviews/runner.py")) == RUNNER
        and sha_file(Path("/opt/postgresql/lib/vector.so")) == MODULE,
        "Mounted native runner or module changed",
    )
    return {
        "base_manifest_sha256": BASE_MANIFEST,
        "prepared_ready_sha256": sha_file(prepared / "READY.json"),
        "prepared_index_sha256": sha_file(prepared / "database-identity.json"),
        "backup_manifest_sha256": sha_file(prepared / "base/backup_manifest"),
        "image_sha256": IMAGE,
        "module_sha256": MODULE,
        "index_identity": GRAPH,
    }


@contextmanager
def watchdog(seconds):
    need(seconds > 0, "Guest deadline exhausted")

    def expired(_signum, _frame):
        raise TimeoutError("Guest deadline expired")

    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def run_guest(stage, record, bundle, prepared, work, output, started, *, experiment=None):
    """Restore, execute, verify and stop a single private copy. No scheduler calls."""
    from rb_measure import Meter, _capture, guarded_backend, write_json
    from rb_plan import PHASE_SECONDS
    from rb_verify import _reconstruct

    meter_type = Meter if experiment is None else experiment.Meter
    capture = _capture if experiment is None else experiment.capture
    reconstruct = _reconstruct if experiment is None else experiment.reconstruct
    verdicts = (
        (
            "would_pass",
            "closed_negative_quality",
            "measurement_inconclusive",
            "closed_negative_latency",
        )
        if experiment is None
        else experiment.VERDICTS
    )

    class GuestMeter(meter_type):
        def remaining(self):
            limit = 6600 if self.phase == "final" else 6000
            now = self.clock()
            return min(
                limit - (now - self.started) / 1e9,
                PHASE_SECONDS[self.phase] - (now - self.phase_start) / 1e9,
            )

        def next_phase(self, phase):
            super().next_phase(phase)
            signal.setitimer(signal.ITIMER_REAL, max(0.001, self.remaining()))

    meter = GuestMeter()
    meter.started = meter.phase_start = started
    output.mkdir(mode=0o700, exist_ok=False)
    started_copy = False
    backend = None
    failed = None
    provisional = None
    native_inputs = None
    mem_group = None
    before = None
    after = None

    def check_snapshot_memory():
        observed = memory_events(mem_group)
        write_json(
            output / "startup-memory.json",
            {"memory_events_after_snapshot": observed, "search_attempts": meter.calls},
        )
        need(observed == before, "Job recorded a limit or OOM event before the first search")

    try:
        with watchdog(meter.remaining()):
            limits, mem_group = resource_limits()
            before = memory_events(mem_group)
            native_inputs = check_native_inputs(stage, bundle, prepared)
            need(
                not (work / "pgdata").exists() and (work / "socket").is_dir(),
                "Expected a new, private work directory",
            )
            write_json(
                output / "runtime.json",
                {
                    "package_manifest_sha256": stage.manifest_sha,
                    "job": record,
                    "inputs_before": native_inputs,
                    "resources": limits,
                    "profile_sha256": stage.frozen.profile.fingerprint,
                    "registry_sha256": stage.frozen.profile.native_registry_hash,
                    "memory_events_before": before,
                    "provider_calls": 0,
                    "confirmation_queries": 0,
                },
            )
            runner, base = stage.frozen.execution.load_backend(stage.source)
            started_copy = True
            restored = stage.frozen.restore(stage.source, bundle, prepared, work, runner)
            need(restored == stage.index, "Restored database identity changed")
            backend = (
                guarded_backend(base, meter)(bundle, work)
                if experiment is None
                else experiment.make_backend(runner, base, meter, bundle, work)
            )
            backend.state["source_manifest"]["settings"]["hnsw.ef_search"] = "640"
            meter.check_time()
        with watchdog(meter.remaining()):
            capture(
                stage.plan,
                stage.frozen,
                stage.evidence,
                backend,
                meter,
                output / "capture",
                synthetic_only=False,
                after_snapshot=check_snapshot_memory,
            )
        with watchdog(meter.remaining() - 90):
            need(backend.conn is None and meter.live is None, "Reader leaked at finalization")
            # Drop the acquisition snapshot before the final streaming verification.
            backend = None
            stage.frozen.verify_import(runner, bundle, work)
            provisional = reconstruct(
                output / "capture", stage.plan, stage.frozen, stage.evidence, synthetic_only=False
            )
            need(
                provisional["provisional_verdict"] in verdicts,
                "Unexpected guest result",
            )
    except BaseException as error:
        failed = {"type": type(error).__name__, "message": str(error)}
    finally:
        if started_copy:
            try:
                if backend is not None:
                    backend.close()
                # Always attempt shutdown, even after the work watchdog fires.
                with watchdog(65):
                    stage.frozen.stop(work)
                need(
                    not (work / "pgdata/postmaster.pid").exists(),
                    "Private PostgreSQL still running",
                )
            except BaseException as error:
                write_json(output / "cleanup-failure.json", {"type": type(error).__name__})
                failed = failed or {"type": type(error).__name__, "message": str(error)}
        if failed is None:
            try:
                with watchdog(meter.remaining()):
                    meter.check_time()
                    stage.frozen.verify_index(work, stage.index)
                    need(
                        check_native_inputs(stage, bundle, prepared) == native_inputs,
                        "Read-only native inputs changed",
                    )
                    after = memory_events(mem_group)
                    need(after == before, "Job recorded a limit or OOM event")
                    write_json(output / "analysis.json", provisional)
                    meter.check_time()
            except BaseException as error:
                failed = {"type": type(error).__name__, "message": str(error)}
        if failed is not None:
            write_json(output / "guest-failure.json", failed)
        write_json(
            output / "guest-exit.json",
            {
                "exit_code": int(failed is not None),
                "job_id": record["job_id"],
                "inputs_verified_after": failed is None,
                "memory_events_after": after,
                "elapsed_seconds": (meter.clock() - meter.started) / 1e9,
                "development_qualifier": False,
            },
        )
        write_json(output / "guest-lock.json", {"files": inventory(output)})
    return int(failed is not None)


def same_analysis(local, remote):
    if type(local) is not type(remote):
        return False
    if isinstance(local, dict):
        return local.keys() == remote.keys() and all(
            same_analysis(local[k], remote[k]) for k in local
        )
    if isinstance(local, list):
        return len(local) == len(remote) and all(map(same_analysis, local, remote))
    if isinstance(local, float):
        return math.isclose(local, remote, rel_tol=0.0, abs_tol=1e-12)
    return local == remote


def verify_guest_inventory(folder, expected_lock):
    actual = inventory(folder)
    lock = actual.pop("guest-lock.json", None)
    need(lock and lock["sha256"] == expected_lock, "Guest return lock changed")
    need(actual == read_json(folder / "guest-lock.json")["files"], "Guest raw inventory changed")
    return actual


def review_guest_return(stage, folder, expected_lock, job_id, *, experiment=None):
    from rb_verify import _reconstruct

    files = verify_guest_inventory(folder, expected_lock)
    status = read_json(folder / "guest-exit.json")
    need(
        status["job_id"] == job_id and status["development_qualifier"] is False,
        "Guest result belongs to another job",
    )
    if status["exit_code"] != 0:
        need("guest-failure.json" in files, "Failed guest return is incomplete")
        return {"status": "guest_failure_preserved", "development_qualifier": False}
    runtime = read_json(folder / "runtime.json")
    startup = read_json(folder / "startup-memory.json")
    need(
        runtime["package_manifest_sha256"] == stage.manifest_sha
        and runtime["job"]["job_id"] == job_id
        and runtime["job"]["candidate"] == getattr(stage, "study_identity", CANDIDATE)
        and runtime["profile_sha256"] == stage.frozen.profile.fingerprint
        and runtime["registry_sha256"] == stage.frozen.profile.native_registry_hash
        and runtime["provider_calls"] == runtime["confirmation_queries"] == 0
        and runtime["inputs_before"]["image_sha256"] == IMAGE
        and runtime["inputs_before"]["module_sha256"] == MODULE
        and runtime["inputs_before"]["index_identity"] == GRAPH
        and runtime["resources"]["memory_limit"] == MEMORY_BYTES
        and status["inputs_verified_after"] is True
        and 0 < status["elapsed_seconds"] < 6600
        and startup
        == {
            "memory_events_after_snapshot": runtime["memory_events_before"],
            "search_attempts": 0,
        }
        and status["memory_events_after"] == runtime["memory_events_before"],
        "Guest proof or resource accounting differs",
    )
    reconstruct = _reconstruct if experiment is None else experiment.reconstruct
    result = reconstruct(
        folder / "capture", stage.plan, stage.frozen, stage.evidence, synthetic_only=False
    )
    need(same_analysis(result, read_json(folder / "analysis.json")), "Guest analysis differs")
    return {"status": "guest_replay_verified_host_review_required", **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("verify", "guest", "review-return"))
    parser.add_argument("package", type=Path)
    parser.add_argument("manifest_sha256")
    parser.add_argument("--admission", type=Path)
    parser.add_argument("--admission-sha256")
    parser.add_argument("--return-dir", type=Path)
    parser.add_argument("--return-lock-sha256")
    parser.add_argument("--job-id")
    args = parser.parse_args()
    if args.action == "guest":
        need(
            args.admission is not None and args.admission_sha256 is not None,
            "Held package needs a separate external admission",
        )
        started = time.monotonic_ns()
        with watchdog(1500):
            stage = load_stage(args.package, args.manifest_sha256)
    else:
        stage = load_stage(args.package, args.manifest_sha256)
    experiment = None
    mode = {}
    if (stage.package / "rb_conditioned.py").is_file():
        import rb_conditioned as experiment

        mode = {"conditioned_calibration": True}
    elif (stage.package / "rb_switch.py").is_file():
        import rb_switch as experiment

        mode = {"reader_switch_diagnostic": True}
    elif (stage.package / "rb_interleave.py").is_file():
        import rb_interleave as experiment

        mode = {"interleaved_calibration": True}
    elif (stage.package / "rb_oracle.py").is_file():
        import rb_oracle as experiment

        mode = {"oracle_diagnostic": True}
    elif (stage.package / "rb_request_timing.py").is_file():
        import rb_request_timing as experiment

        mode = {"request_attribution": True}
    elif (stage.package / "rb_persistent.py").is_file():
        import rb_persistent as experiment

        mode = {"persistent_reader": True}
    elif (stage.package / "rb_calibration.py").is_file():
        import rb_calibration as experiment

        mode = {"calibration_only": True}
    if experiment is not None:
        need(
            Path(experiment.__file__).resolve() == stage.package / f"{experiment.__name__}.py",
            "Experiment must load from the sealed package",
        )
    if mode.get("oracle_diagnostic"):
        payload = read_json(stage.package / "oracle-replay.json")
        experiment.attach(stage, payload)
        stage.study_identity = stage.evidence.identities["oracle"]
    elif any(
        mode.get(key)
        for key in (
            "interleaved_calibration",
            "reader_switch_diagnostic",
            "conditioned_calibration",
        )
    ):
        experiment.attach(stage)
    identity = getattr(stage, "study_identity", CANDIDATE)
    if args.action == "guest":
        record = admission(
            args.admission, args.admission_sha256, args.manifest_sha256, identity=identity
        )
    if args.action == "verify":
        print(
            json.dumps(
                {
                    "status": "verified_held",
                    "candidate": identity,
                    "sessions": len(stage.plan.sessions),
                    "cases": len(stage.plan.cases),
                    "dispatch_released": False,
                    **mode,
                },
                sort_keys=True,
            )
        )
    elif args.action == "review-return":
        need(
            args.return_dir is not None and args.return_lock_sha256 is not None and args.job_id,
            "Return review needs a bound job and raw lock pin",
        )
        print(
            json.dumps(
                review_guest_return(
                    stage,
                    args.return_dir,
                    args.return_lock_sha256,
                    args.job_id,
                    experiment=experiment,
                ),
                sort_keys=True,
                allow_nan=False,
            )
        )
    else:
        raise SystemExit(
            run_guest(
                stage,
                record,
                Path("/bundle"),
                Path("/prepared"),
                Path("/run"),
                Path("/results/guest"),
                started,
                experiment=experiment,
            )
        )


if __name__ == "__main__":
    main()
