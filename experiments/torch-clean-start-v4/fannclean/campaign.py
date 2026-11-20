"""One allocated job: qualify the real static graph, then start one fresh worker.

Qualification files never enter the experiment's agent workspace. This module
cannot submit jobs or make model requests; a controller must connect separately.
"""

import argparse
import json
import os
import subprocess
import sys
import tarfile
import time
import uuid
from pathlib import Path

from .core import Limits, read, sha, write
from .deploy import ContainerExecutor, package
from .engine import empty

REQUEST = (
    "Qualify the native/container workflow, then run one clean-start Opus 5.5 "
    "experiment and compare its latency savings with oracle_feasible on both "
    "the held-out and full workloads."
)


def run(parent, snapshot, image, research_image, local_queries, prior_seconds=0):
    parent = Path(parent).resolve()
    job = os.environ["SLURM_JOB_ID"]
    started = time.time()
    status_file = parent / "campaign-status.json"
    if status_file.exists():
        raise ValueError("campaign already attempted; inspect existing records without redispatch")
    write(status_file, {"status": "qualifying", "job_id": job, "started_epoch": started})
    cases = read(parent / "static-cases.json")
    development = [c for c in cases if c["role"] == "development"]
    groups = sorted({c["group"] for c in development})[:32]
    qc = [c for c in development if c["group"] in groups]
    qroot = parent / "qualification-stage"
    qlimits = Limits(
        query_cap=57000 - local_queries,
        final_reserve=7000,
        wall_seconds=21600,
        discovery_seconds=14400,
    )
    engine = parent / "engine"
    try:
        package(
            qroot, qc, engine, snapshot, image, research_image, qlimits, database_user="torch_owner"
        )
        executor = ContainerExecutor(qroot)
        qcases = read(qroot / "private/cases.json")
        capture_groups = sorted({c["group"] for c in qcases})[:2]
        from fannagent.api.broad_policy import FEATURES

        profile = {
            "kind": "profile",
            "handles": [c["handle"] for c in qcases if c["group"] in capture_groups],
            "checkpoints": [1, 3],
            "features": list(FEATURES),
        }
        captured = executor(uuid.uuid4().hex, profile, 1800)
        if (
            not captured.get("private_cleanup_verified")
            or not captured["evidence"]
            or any(r["fault"] or r["exhausted"] for r in captured["acquisition_diagnostics"])
        ):
            raise ValueError("real-graph acquisition/audit/cleanup qualification failed")
        controls = {
            "kind": "screen",
            "handles": [c["handle"] for c in qcases],
            "policies": [empty()],
            "blocks": 6,
        }
        measured = executor(uuid.uuid4().hex, controls, 1800)
        if any(
            r["checkpoint"]
            or r["fault"]
            or r["exhausted"]
            or r["recall"] != r["native_recall"]
            or r["count"] != r["native_count"]
            for r in measured["quality"]
        ):
            raise ValueError("no-op changed native output/quality")
        estimate = measured["timing"]
        requests = [measured["request_id"]]
        # One predeclared additional batch is allowed. Retain and combine all
        # blocks; never select a passing subset or drop an earlier observation.
        if not estimate["controls_pass"]:
            measured2 = executor(uuid.uuid4().hex, {**controls, "blocks": 2}, 1800)
            requests.append(measured2["request_id"])
            joined = []
            for offset, response in ((0, measured), (6, measured2)):
                for row in response["samples"]:
                    if row["phase"] == "sample":
                        joined.append({**row, "block": row["block"] + offset, "declared_blocks": 8})
            command = [
                "/share/apps/apptainer/bin/apptainer",
                "exec",
                "--cleanenv",
                "--containall",
                "--no-home",
                "--bind",
                f"{qroot / 'code'}:/code:ro",
                "--env",
                "PYTHONPATH=/code/experiments/torch-clean-start-v4:/code/src:/opt/torch-reviews/vendor",
                str(image),
                "python",
                "-B",
                "-c",
                "import json,sys; from fannclean.timing import summarize; "
                "print(json.dumps(summarize(json.load(sys.stdin),10000,.02)))",
            ]
            combined = subprocess.run(
                command,
                input=json.dumps(joined),
                capture_output=True,
                text=True,
                check=True,
                timeout=300,
            )
            estimate = json.loads(combined.stdout)
        qcharged = read(qroot / "private/query-ledger.json")["charged"] + local_queries
        qualification = {
            "status": "passed" if estimate["controls_pass"] else "timing_inconclusive",
            "job_id": job,
            "queries_charged_including_local": qcharged,
            "all_timing_blocks_retained": True,
            "timing_requests": requests,
            "timing": estimate,
            "agent_received_qualification_evidence": False,
        }
        write(parent / "native-qualification.json", qualification)
        if not estimate["controls_pass"]:
            raise ValueError(
                "real-graph negative controls did not qualify; no model experiment started"
            )
        if qcharged > 50000:
            raise ValueError("qualification exceeded its total query envelope")
        remaining = int(21600 - prior_seconds - (time.time() - started) - 120)
        if remaining <= 10800:
            raise ValueError(
                "qualification left too little time for a useful independent experiment"
            )
        limits = Limits(
            query_cap=300000 - qcharged,
            final_reserve=211000,
            wall_seconds=remaining,
            discovery_seconds=min(14400, remaining - 7200),
        )
        stage = parent / "experiment-stage"
        task = package(
            stage,
            cases,
            engine,
            snapshot,
            image,
            research_image,
            limits,
            database_user="torch_owner",
        )
        write(
            stage / "authorization.json",
            {
                "status": "authorized",
                "run_id": task["run_id"],
                "package_sha256": sha(stage / "package-seal.json"),
                "purpose": "clean_start_discovery",
                "user_instruction": REQUEST,
                "job_id": job,
                "allocation_limit": 1,
                "queries_including_qualification_limit": 300000,
                "qualification_queries": qcharged,
                "provider_usd_limit": "15",
                "wall_seconds_including_qualification_limit": 21600,
                "prior_bootstrap_allocation_seconds": prior_seconds,
            },
        )
        initial = parent / "initial-package.tar.gz"
        with tarfile.open(initial, "w:gz") as archive:
            archive.add(stage, arcname="experiment-stage")
        write(
            parent / "initial-package.json",
            {
                "sha256": sha(initial),
                "run_id": task["run_id"],
                "initial_empirical_records": 0,
                "limits": task["limits"],
            },
        )
        env = {
            **os.environ,
            "PYTHONPATH": str(stage / "code/experiments/torch-clean-start-v4"),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        with (parent / "worker.log").open("wb") as out:
            worker = subprocess.Popen(
                [sys.executable, "-B", "-m", "fannclean.worker", "serve", "--root", str(stage)],
                env=env,
                stdout=out,
                stderr=subprocess.STDOUT,
            )
            for _ in range(30):
                if (stage / "private/worker.json").exists() or worker.poll() is not None:
                    break
                time.sleep(1)
            if worker.poll() is not None:
                raise ValueError("fresh worker failed startup; no model started")
            write(
                status_file,
                {
                    "status": "ready_for_one_model_experiment",
                    "job_id": job,
                    "run_id": task["run_id"],
                    "qualification_queries": qcharged,
                    "started_epoch": started,
                    "stage": str(stage),
                    "initial_package_sha256": sha(initial),
                },
            )
            rc = worker.wait(timeout=limits.wall_seconds + 60)
        state = read(stage / "private/worker.json")
        write(
            status_file,
            {
                "status": state["status"],
                "job_id": job,
                "run_id": task["run_id"],
                "worker_exit_code": rc,
                "qualification_queries": qcharged,
            },
        )
        with tarfile.open(parent / "final-returns.tar.gz", "w:gz") as archive:
            for p in (stage / "private").iterdir():
                if p.name not in ("engine", "builds"):
                    archive.add(p, arcname="private/" + p.name)
        return state
    except BaseException as error:
        write(
            status_file,
            {
                "status": "stopped_campaign_failure",
                "job_id": job,
                "error": str(error),
                "automatic_retry": False,
                "model_start_not_automatic": True,
            },
        )
        raise


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--parent", type=Path, required=True)
    p.add_argument("--snapshot", type=Path, required=True)
    p.add_argument("--image", type=Path, required=True)
    p.add_argument("--research-image", required=True)
    p.add_argument("--local-qualification-queries", type=int, required=True)
    p.add_argument("--prior-allocation-seconds", type=int, default=0)
    a = p.parse_args()
    run(
        a.parent,
        a.snapshot,
        a.image,
        a.research_image,
        a.local_qualification_queries,
        a.prior_allocation_seconds,
    )


if __name__ == "__main__":
    main()
