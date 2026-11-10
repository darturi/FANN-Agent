"""Held single-job Torch controller for the persistent Reviews development batch."""

import argparse
import datetime
import json
import os
import re
import shlex
import signal
import stat
import subprocess
import tempfile
import time
from pathlib import Path

import rb_site as site
from rb_seal import (
    inventory,
    json_bytes,
    need,
    sha_bytes,
    sha_file,
    verify_archive,
    verify_directory,
    write_once,
)

NAME = "reviews-persistent-batch-native-v1"
RESERVATION = NAME + "-startup-memory-gate-v1-reservation"
MANIFEST = "f31ff3fc13cb2443c1a60565c30d856d15a98f3cd6e14f5b1ff71924b443464d"
ARCHIVE = "9a5b6d88c515d9fdddd554e29952de863de787637936c71bb05e89f9b06f2b00"
CANDIDATE = "e7f1ae0465bfe05aaf7d7768adf93ef6c99fe2be1eaa7be3fa73509bea75882b"
JOB_NAME = "fann-reviews-batch-v1"
COMMENT = "rb4-" + MANIFEST[:24]
SCHEMA = "reviews-persistent-batch.torch-release.v1"
LOCK = "host-return-lock.json"
PACKAGE = "package"
KIT = ("rb_host.py", "rb_site.py", "rb_seal.py")


def read_pinned(path, digest):
    raw = Path(path).read_bytes()
    need(sha_bytes(raw) == digest, f"Digest differs: {path}")
    return json.loads(raw)


def private(path):
    st = path.lstat()
    need(
        stat.S_ISDIR(st.st_mode) and st.st_uid == os.getuid() and not st.st_mode & 0o077,
        f"Expected private owned directory: {path}",
    )
    return path


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def publish(path, data):
    """Atomically publish an immutable record, including across Slurm's start race."""
    with tempfile.NamedTemporaryFile(dir=path.parent) as tmp:
        tmp.write(json_bytes(data))
        tmp.flush()
        os.fsync(tmp.fileno())
        os.link(tmp.name, path)
        sync_dir(path.parent)


def kit_digest(root):
    return sha_bytes(json_bytes({name: sha_file(root / name) for name in KIT}))


def stage(root, archive):
    import tarfile

    private(root)
    need(sha_file(archive) == ARCHIVE, "Archive digest differs")
    expected = verify_archive(archive, MANIFEST)
    with tempfile.TemporaryDirectory(dir=root, prefix=".extract-") as work:
        destination = Path(work) / PACKAGE
        destination.mkdir(mode=0o700)
        with tarfile.open(archive, "r:gz") as tar:
            for member in tar:
                name = member.name.removeprefix(NAME + "/")
                limit = (
                    4 * 1024**2 if name == "manifest.json" else expected.get(name, {}).get("bytes")
                )
                need(
                    member.isfile()
                    and not member.issparse()
                    and limit is not None
                    and 0 <= member.size <= limit,
                    "Unexpected extracted member",
                )
                out = destination / name
                out.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                write_once(out, tar.extractfile(member).read())
        verify_directory(destination, MANIFEST)
        target = root / PACKAGE
        need(not target.exists() and not target.is_symlink(), "Stage already exists")
        # A complete verified tree appears at once. A second nonempty tree cannot replace it.
        destination.rename(target)
    return {
        "status": "staged_held",
        "package_manifest_sha256": MANIFEST,
        "host_kit_sha256": kit_digest(root),
    }


def release(approval_path, approval_digest, preflight_path, preflight_digest, root):
    readiness = read_pinned(preflight_path, preflight_digest)
    receipt = readiness["site"]
    need(
        readiness["status"] == "scheduler_test_passed_held"
        and readiness["stage"] == str(root)
        and readiness["package_manifest_sha256"] == MANIFEST
        and readiness["host_kit_sha256"] == kit_digest(root),
        "Release requires the exact staged scheduler dry-run receipt",
    )
    approval = read_pinned(approval_path, approval_digest)
    expires = datetime.datetime.fromisoformat(approval["valid_until_utc"])
    need(
        expires.utcoffset() == datetime.timedelta(0)
        and datetime.timedelta(0) < expires - site.now() <= datetime.timedelta(hours=24),
        "Release expiry must be explicit UTC within the next 24 hours",
    )
    need(
        approval
        == {
            "schema": SCHEMA,
            "preflight_sha256": preflight_digest,
            "host_kit_sha256": kit_digest(root),
            "package_manifest_sha256": MANIFEST,
            "candidate": CANDIDATE,
            "uid": os.getuid(),
            "account": site.ACCOUNT,
            "partition": site.PARTITION,
            "allocations": 1,
            "no_retry": True,
            "valid_until_utc": approval["valid_until_utc"],
        }
        and type(approval["allocations"]) is int
        and type(approval["uid"]) is int,
        "Approval does not authorize this exact single job",
    )
    checked = site.site_check()
    keys = (
        "schema",
        "host",
        "uid",
        "cluster",
        "partition",
        "account",
        "tools",
        "inputs",
        "allocations",
        "searches",
    )
    need(all(receipt[key] == checked[key] for key in keys), "Live Torch preflight identity changed")
    issued = datetime.datetime.fromisoformat(receipt["checked_utc"])
    need(
        datetime.timedelta(0) <= site.now() - issued <= datetime.timedelta(hours=24),
        "Read-only preflight receipt is stale",
    )
    return checked, expires


def scheduler(checked, name):
    saved = checked["tools"][name]
    need(site.binary(saved["path"]) == saved, f"Site binary changed: {name}")
    return saved["path"]


def make_submission(root, state, run, checked):
    python = scheduler(checked, "python")
    launch = [
        scheduler(checked, "srun"),
        "--export=ALL",
        "--ntasks=1",
        "--cpus-per-task=4",
        "--hint=nomultithread",
        "--cpu-bind=verbose",
        "--kill-on-bad-exit=1",
        python,
        "-B",
        str(root / "rb_host.py"),
        "compute",
        str(state),
    ]
    checks = "".join(f"{sha_file(root / name)}  {root / name}\n" for name in KIT)
    script = (
        "#!/bin/bash\nset -euo pipefail\numask 077\n"
        + "printf %s "
        + shlex.quote(checks)
        + " | /usr/bin/sha256sum -c --status\n"
        + "exec "
        + shlex.join(launch)
        + "\n"
    )
    argv = [
        scheduler(checked, "sbatch"),
        "--parsable",
        "--export=NIL",
        "--account=" + site.ACCOUNT,
        "--partition=" + site.PARTITION,
        "--job-name=" + JOB_NAME,
        "--comment=" + COMMENT,
        "--nodes=1",
        "--ntasks=1",
        "--cpus-per-task=4",
        "--mem=32G",
        "--time=02:00:00",
        "--hint=nomultithread",
        "--no-requeue",
        "--open-mode=append",
        "--chdir=" + str(run),
        "--output=" + str(run / "slurm-%j.out"),
        "--error=" + str(run / "slurm-%j.err"),
    ]
    return argv, script


def scheduler_test(root):
    private(root)
    verify_directory(root / PACKAGE, MANIFEST)
    checked = site.site_check()
    state = site.RESULTS / RESERVATION
    need(not state.exists() and not state.is_symlink(), "Attempt is already reserved")
    argv, script = make_submission(root, state, root, checked)
    # The actual dispatch uses a new scratch directory for these three paths.
    argv = [arg for arg in argv if not arg.startswith(("--output=", "--error="))]
    argv.extend(("--output=/dev/null", "--error=/dev/null", "--test-only"))
    proc = subprocess.run(
        argv, input=script, text=True, capture_output=True, timeout=30, env=site.ENV
    )
    need(len(proc.stdout) + len(proc.stderr) < 8192, "Unexpected scheduler test response size")
    if proc.returncode:
        raise RuntimeError(f"Scheduler test rejected: {proc.stderr.strip()}")
    return {
        "status": "scheduler_test_passed_held",
        "stage": str(root),
        "site": checked,
        "package_manifest_sha256": MANIFEST,
        "host_kit_sha256": kit_digest(root),
        "scheduler_test": {"argv": argv, "stdout": proc.stdout, "stderr": proc.stderr},
    }


def submit(root, approval_path, approval_digest, preflight_path, preflight_digest):
    private(root)
    verify_directory(root / PACKAGE, MANIFEST)
    state = site.RESULTS / RESERVATION
    need(
        not state.exists() and not state.is_symlink(),
        "Attempt already reserved, including uncertain dispatch",
    )
    checked, expires = release(
        approval_path, approval_digest, preflight_path, preflight_digest, root
    )
    run = Path(tempfile.mkdtemp(prefix=NAME + ".", dir=site.SCRATCH))
    argv, script = make_submission(root, state, run, checked)
    need(site.now() < expires, "Release expired before reservation")
    state.mkdir(mode=0o700)
    sync_dir(state.parent)
    record = {
        "approval_sha256": approval_digest,
        "preflight_sha256": preflight_digest,
        "host_kit_sha256": kit_digest(root),
        "stage": str(root),
        "run": str(run),
        "site": checked,
        "package_manifest_sha256": MANIFEST,
        "candidate": CANDIDATE,
        "argv": argv,
        "script": script,
        "allocations_reserved": 1,
        "no_retry": True,
    }
    publish(state / "reservation.json", record)
    need(site.now() < expires, "Release expired after reservation; attempt remains closed")
    # Only this call can dispatch. The durable reservation remains even on timeout or ambiguity.
    try:
        proc = subprocess.run(
            argv, input=script, capture_output=True, text=True, timeout=30, env=site.ENV
        )
        raw = {
            "status": "response_received",
            "exit_code": proc.returncode,
            "stdout": proc.stdout[:8192],
            "stderr": proc.stderr[:8192],
        }
    except (OSError, subprocess.TimeoutExpired) as error:
        publish(
            state / "dispatch-response.json", {"status": "uncertain", "error": type(error).__name__}
        )
        raise
    publish(state / "dispatch-response.json", raw)
    match = re.fullmatch(r"([1-9][0-9]*)(?:;torch)?", proc.stdout.strip())
    need(
        proc.returncode == 0 and match, "Dispatch rejected or uncertain; reservation remains closed"
    )
    receipt = {"job_id": match[1], "reservation_sha256": sha_file(state / "reservation.json")}
    publish(state / "job.json", receipt)
    return receipt


def expected_job(job, uid):
    return {
        "JobId": job,
        "JobName": JOB_NAME,
        "UserId": f"{site.USER}({uid})",
        "Account": site.ACCOUNT,
        "Partition": site.PARTITION,
        "Comment": COMMENT,
        "JobState": "RUNNING",
        "NumNodes": "1",
        "NumTasks": "1",
        "CPUs/Task": "4",
        "TimeLimit": "02:00:00",
        "BatchFlag": "1",
        "Requeue": "0",
        "Restarts": "0",
    }


def verify_binding(actual, job, uid):
    need(
        all(actual[key] == value for key, value in expected_job(job, uid).items())
        and actual["NumCPUs"] in {"4", "8"}
        and actual["MinMemoryNode"] in {"32G", "32768M"}
        and actual["NodeList"] == actual["BatchHost"]
        and actual["NodeList"] != "torch-login"
        and not actual["NodeList"].startswith("torch-login-"),
        "Live scheduler allocation differs",
    )


def bound_job(job, checked):
    names = (
        *expected_job(job, checked["uid"]),
        "NumCPUs",
        "MinMemoryNode",
        "NodeList",
        "BatchHost",
    )
    client = site.compute_tool("scontrol")
    response = site.command([client["path"], "--local", "--oneliner", "show", "job", job])
    need(
        site.compute_tool("scontrol") == client,
        "Compute scheduler client changed during the job query",
    )
    actual = site.fields(response, names)
    verify_binding(actual, job, checked["uid"])
    need(
        actual["BatchHost"] == os.uname().nodename.split(".")[0],
        "Scheduler did not bind this single compute host",
    )
    return actual, client


def guest_command(root, run, work, job, apptainer, admission_sha):
    package = root / PACKAGE
    argv = [
        apptainer,
        "exec",
        "--cleanenv",
        "--containall",
        "--no-home",
        "--pwd",
        "/run",
    ]
    for source, dest, mode in (
        (package, "/patch", "ro"),
        (site.BUNDLE, "/bundle", "ro"),
        (site.PREPARED, "/prepared", "ro"),
        (work, "/run", "rw"),
        (run / "result", "/results", "rw"),
        (package / "modules/vector.so", "/opt/postgresql/lib/vector.so", "ro"),
        (run / "admission.json", "/admission.json", "ro"),
    ):
        need(re.fullmatch(r"/[A-Za-z0-9/_.-]+", str(source)), "Unexpected bind path")
        argv.extend(("--bind", f"{source}:{dest}:{mode}"))
    for key, value in (
        ("PYTHONPATH", "/patch:/opt/torch-reviews/vendor"),
        ("PYTHONDONTWRITEBYTECODE", "1"),
        ("TMPDIR", "/run/tmp"),
        ("OPENBLAS_NUM_THREADS", "1"),
        ("OMP_NUM_THREADS", "1"),
        ("SLURM_JOB_ID", job),
        ("TORCH_IMAGE_SHA256", site.IMAGE_SHA),
    ):
        argv.extend(("--env", f"{key}={value}"))
    return argv + [
        str(site.IMAGE),
        "python",
        "-B",
        "/patch/rb_native.py",
        "guest",
        "/patch",
        MANIFEST,
        "--admission",
        "/admission.json",
        "--admission-sha256",
        admission_sha,
    ]


def admission_for(job, uid):
    return {
        "schema": "reviews-persistent-batch.single-approved-allocation.v1",
        "package_manifest_sha256": MANIFEST,
        "candidate": CANDIDATE,
        "job_id": job,
        "uid": uid,
    }


def compute(root, state):
    job = os.environ.get("SLURM_JOB_ID", "")
    need(
        os.uname().sysname == "Linux"
        and os.uname().machine == "x86_64"
        and re.fullmatch(r"[1-9][0-9]*", job)
        and os.environ.get("SLURM_STEP_ID") == "0"
        and not os.environ.get("SLURM_ARRAY_JOB_ID"),
        "Expected the single native job step",
    )
    need(state == site.RESULTS / RESERVATION, "Reservation path differs")
    private(state)
    for _ in range(25):
        if (state / "job.json").is_file():
            break
        time.sleep(1)
    receipt = site.read_json(state / "job.json")
    record = read_pinned(state / "reservation.json", receipt["reservation_sha256"])
    checked = record["site"]
    need(
        receipt["job_id"] == job
        and record["stage"] == str(root)
        and record["host_kit_sha256"] == kit_digest(root)
        and record["package_manifest_sha256"] == MANIFEST
        and record["candidate"] == CANDIDATE
        and checked["uid"] == os.getuid(),
        "Job does not own the reserved attempt",
    )
    run = private(Path(record["run"]))
    need(run.parent == site.SCRATCH, "Attempt scratch path differs")
    private(root)
    verify_directory(root / PACKAGE, MANIFEST)
    actual, scontrol = bound_job(job, checked)
    apptainer = site.compute_tool("apptainer")
    need(
        site.retained_inputs() == checked["inputs"], "Retained inputs changed since login preflight"
    )
    work = run / "work"
    work.mkdir(mode=0o700)
    for name in ("socket", "tmp"):
        (work / name).mkdir(mode=0o700)
    write_once(work / ".torch-owned", f"{job}\n".encode("ascii"))
    result = run / "result"
    result.mkdir(mode=0o700)
    admission = run / "admission.json"
    publish(admission, admission_for(job, os.getuid()))
    argv = guest_command(root, run, work, job, apptainer["path"], sha_file(admission))
    publish(
        result / "host-start.json",
        {
            "job": actual,
            "compute_tools": {"scontrol": scontrol, "apptainer": apptainer},
            "reservation_sha256": receipt["reservation_sha256"],
            "admission_sha256": sha_file(admission),
            "inputs": checked["inputs"],
        },
    )
    code = 1
    failure = None
    failure_message = None
    lock = None
    unchanged = False
    stopped = False
    apptainer_unchanged = False
    proc = None

    def interrupt(number, _frame):
        raise InterruptedError(f"Slurm signal {number}")

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, interrupt)
    try:
        need(site.compute_tool("apptainer") == apptainer, "Compute Apptainer changed before launch")
        proc = subprocess.Popen(
            argv,
            env={
                **site.ENV,
                "APPTAINER_TMPDIR": str(work / "tmp"),
                "APPTAINER_DISABLE_CACHE": "true",
            },
            start_new_session=True,
        )
        code = proc.wait(timeout=6650)
        guest = result / "guest"
        lock_path = guest / "guest-lock.json"
        if lock_path.is_file():
            lock = sha_file(lock_path)
        need(code == 0, f"Guest process exited with status {code}")
        need(lock is not None, "Guest exited without a result lock")
        guest_exit = site.read_json(guest / "guest-exit.json")
        need(code == guest_exit["exit_code"] == 0 and guest_exit["job_id"] == job, "Guest failed")
        apptainer_unchanged = site.compute_tool("apptainer") == apptainer
        need(apptainer_unchanged, "Compute Apptainer changed during the guest run")
        unchanged = site.retained_inputs() == checked["inputs"]
        stopped = not (work / "pgdata/postmaster.pid").exists()
        need(unchanged and stopped, "Retained inputs or private database cleanup failed")
    except Exception as error:
        failure = type(error).__name__
        failure_message = str(error)
        code = 1
    finally:
        if proc is not None and proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
        publish(
            result / "host-exit.json",
            {
                "exit_code": code,
                "job_id": job,
                "guest_lock_sha256": lock,
                "failure": failure,
                "failure_message": failure_message,
                "inputs_unchanged": unchanged,
                "postmaster_stopped": stopped,
                "apptainer_unchanged": apptainer_unchanged,
            },
        )
    return code


def terminal_rows(text, job):
    keys = site.ACCOUNT_FIELDS.split(",")
    rows = {}
    for line in text.splitlines():
        values = line.split("|")
        need(len(values) == len(keys) and values[0] not in rows, "Ambiguous scheduler accounting")
        rows[values[0]] = dict(zip(keys, values))
    need(
        set(rows) <= {job, job + ".batch", job + ".extern", job + ".0"}
        and {job, job + ".batch", job + ".0"} <= rows.keys(),
        "Missing or unexpected scheduler steps",
    )
    allocation = rows[job]
    need(
        all(
            allocation[key] == value
            for key, value in {
                "JobName": JOB_NAME,
                "User": site.USER,
                "Account": site.ACCOUNT,
                "Partition": site.PARTITION,
                "DerivedExitCode": "0:0",
                "NNodes": "1",
                "TimelimitRaw": "120",
                "Restarts": "0",
            }.items()
        )
        and allocation["AllocCPUS"] in {"4", "8"}
        and allocation["ReqMem"] in {"32Gn", "32G", "32768Mn", "32768M"}
        and 0 < int(allocation["ElapsedRaw"]) <= 7200
        and all(row["State"] == "COMPLETED" and row["ExitCode"] == "0:0" for row in rows.values()),
        "Scheduler accounting did not verify the bounded completed allocation",
    )
    return rows


def review_host(folder, expected_lock):
    files = inventory(folder)
    pin = files.pop(LOCK, None)
    need(pin and pin["sha256"] == expected_lock, "Return lock differs")
    lock = site.read_json(folder / LOCK)
    need(files == lock["files"], "Return contents differ")
    job = lock["job_id"]
    need(re.fullmatch(r"[1-9][0-9]*", job), "Invalid return job")
    rows = terminal_rows((folder / "sacct.txt").read_text(), job)
    host = site.read_json(folder / "host-exit.json")
    start = site.read_json(folder / "host-start.json")
    need(
        host["job_id"] == start["job"]["JobId"] == job
        and host["exit_code"] == 0
        and host["inputs_unchanged"] is True
        and host["postmaster_stopped"] is True
        and host["apptainer_unchanged"] is True
        and host["guest_lock_sha256"] == files["guest/guest-lock.json"]["sha256"]
        and start["reservation_sha256"] == files["reservation.json"]["sha256"],
        "Host and guest evidence disagree",
    )
    reservation = site.read_json(folder / "reservation.json")
    job_receipt = site.read_json(folder / "job.json")
    response = site.read_json(folder / "dispatch-response.json")
    verify_binding(start["job"], job, reservation["site"]["uid"])
    tools = start["compute_tools"]
    need(tools.keys() == site.COMPUTE_TOOL_PATHS.keys(), "Compute tool evidence differs")
    for name, record in tools.items():
        site.compute_tool_path(name, record)
    admission = site.read_json(folder / "guest/runtime.json")["job"]
    need(
        admission == admission_for(job, reservation["site"]["uid"])
        and start["admission_sha256"] == sha_bytes(json_bytes(admission))
        and job_receipt == {"job_id": job, "reservation_sha256": start["reservation_sha256"]}
        and response["status"] == "response_received"
        and response["exit_code"] == 0
        and response["stdout"].strip() in {job, job + ";torch"}
        and rows[job]["AllocCPUS"] == start["job"]["NumCPUs"],
        "Job evidence differs",
    )
    need(
        reservation["candidate"] == CANDIDATE
        and reservation["package_manifest_sha256"] == MANIFEST
        and reservation["no_retry"] is True
        and reservation["allocations_reserved"] == 1
        and start["inputs"] == reservation["site"]["inputs"],
        "Return reservation differs",
    )
    return {
        "status": "host_verified_guest_replay_required",
        "job_id": job,
        "guest_lock_sha256": host["guest_lock_sha256"],
    }


def collect():
    state = private(site.RESULTS / RESERVATION)
    job_record = site.read_json(state / "job.json")
    job = job_record["job_id"]
    need(re.fullmatch(r"[1-9][0-9]*", job), "Invalid reserved job ID")
    record = read_pinned(state / "reservation.json", job_record["reservation_sha256"])
    run = private(Path(record["run"]))
    checked = record["site"]
    output = private(run / "result")
    fmt = ",".join(
        f"{key}%64"
        if key in {"JobIDRaw", "JobName", "User", "Account", "Partition", "State"}
        else key
        for key in site.ACCOUNT_FIELDS.split(",")
    )
    raw = site.command(
        [scheduler(checked, "sacct"), "--local", "--duplicates", "-nP", "-j", job, "-o", fmt]
    )
    terminal_rows(raw, job)
    host = site.read_json(output / "host-exit.json")
    need(
        host["job_id"] == job
        and host["exit_code"] == 0
        and host["inputs_unchanged"] is True
        and host["postmaster_stopped"] is True
        and host["apptainer_unchanged"] is True,
        "Clean host exit required",
    )
    for name, data in (
        ("reservation.json", (state / "reservation.json").read_bytes()),
        ("dispatch-response.json", (state / "dispatch-response.json").read_bytes()),
        ("job.json", (state / "job.json").read_bytes()),
        ("sacct.txt", (raw + "\n").encode("ascii")),
    ):
        path = output / name
        if path.exists():
            need(path.read_bytes() == data, f"Return evidence changed: {name}")
        else:
            write_once(path, data)
    lock = output / LOCK
    if not lock.exists():
        publish(lock, {"job_id": job, "files": inventory(output)})
    digest = sha_file(lock)
    return {"path": str(output), "host_lock_sha256": digest, **review_host(output, digest)}


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("stage", "scheduler-test", "submit", "compute", "collect", "review-host")
    )
    parser.add_argument("args", nargs="*")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    values = args.args
    if args.action == "stage":
        need(len(values) == 1, "Provide the frozen guest archive")
        result = stage(root, Path(values[0]))
    elif args.action == "scheduler-test":
        need(not values, "No arguments expected")
        result = scheduler_test(root)
    elif args.action == "submit":
        need(len(values) == 4, "Provide external approval, its digest, preflight, and its digest")
        result = submit(root, Path(values[0]), values[1], Path(values[2]), values[3])
    elif args.action == "compute":
        need(len(values) == 1, "Provide the fixed state directory")
        raise SystemExit(compute(root, Path(values[0])))
    elif args.action == "collect":
        need(not values, "No arguments expected")
        result = collect()
    else:
        need(
            len(values) == 2,
            "Provide the return directory and separately captured host lock digest",
        )
        result = review_host(Path(values[0]), values[1])
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
