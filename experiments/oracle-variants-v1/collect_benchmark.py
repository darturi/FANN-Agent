"""Collect one completed return without overwriting or synthesizing raw evidence."""

import hashlib
import json
import shlex
import subprocess
import tarfile

from launch_benchmark import OPTIONS, TARGET, WORK


def run(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=300)
    if result.returncode:
        raise RuntimeError(result.stderr[-2500:])
    return result.stdout


def main():
    submitted = json.loads((WORK / "benchmark-submission.json").read_text())
    job, stage = submitted["job_id"], submitted["stage"]
    assert job.isdigit()
    accounting = run(
        [
            "ssh",
            *OPTIONS,
            TARGET,
            shlex.join(
                [
                    "/opt/slurm/bin/sacct",
                    "--local",
                    "-n",
                    "-P",
                    "-j",
                    job,
                    "--format=JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,ReqMem,NodeList,MaxRSS",
                ]
            ),
        ]
    )
    top = next(line.split("|") for line in accounting.splitlines() if line.startswith(job + "|"))
    assert top[1:3] == ["COMPLETED", "0:0"], top
    assert int(top[3]) + submitted["plan"]["source_elapsed_seconds"] <= 21600
    assert top[4] == "4"
    receipt_path = stage + "/run-" + job + "/results/receipt.json"
    receipt = json.loads(run(["ssh", *OPTIONS, TARGET, shlex.join(["cat", receipt_path])]))
    assert receipt["status"] == "oracle_variants_benchmark_complete" and receipt["job_id"] == job
    output = WORK / ("return-" + job)
    output.mkdir(mode=0o700)
    archive = "oracle-variants-benchmark-" + job + ".tar.gz"
    paths = [
        stage + "/run-" + job + "/" + archive,
        stage + "/run-" + job + "/" + archive + ".sha256",
        stage + "/slurm-" + job + ".out",
        stage + "/slurm-" + job + ".err",
    ]
    run(["scp", *OPTIONS, *(TARGET + ":" + p for p in paths), str(output) + "/"])
    fields = (output / (archive + ".sha256")).read_text().split()
    assert len(fields) == 2 and fields[1] == archive
    with (output / archive).open("rb") as handle:
        actual = hashlib.file_digest(handle, "sha256").hexdigest()
    assert fields[0] == actual
    with tarfile.open(output / archive) as handle:
        for member in handle.getmembers():
            assert member.name == "results" or (
                member.name.startswith("results/")
                and ".." not in member.name.split("/")
                and (member.isfile() or member.isdir())
            )
        handle.extractall(output, filter="data")
    assert json.loads((output / "results/host-exit.json").read_text()) == {
        "job_id": job,
        "exit_code": 0,
    }
    with (WORK / "benchmark-accounting.psv").open("x") as handle:
        handle.write(accounting)
    result = {
        "job_id": job,
        "status": "completed_return_collected",
        "archive_sha256": actual,
        "elapsed_seconds": int(top[3]),
        "results": str((output / "results").resolve()),
    }
    (WORK / "benchmark-collection.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
