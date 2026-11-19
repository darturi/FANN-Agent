"""Explicit phase entrypoints. Preparing/inspecting never starts a worker or model."""

import argparse
import json
from pathlib import Path

from .core import Limits, read, verify_initial, write
from .deploy import package, verify_package, verify_running_code
from .transport import Client, require_authorization


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare", help="Offline only: seal static task and data-free software")
    prep.add_argument("--root", type=Path, required=True)
    prep.add_argument("--cases", type=Path, required=True)
    prep.add_argument("--engine-source", type=Path, required=True)
    prep.add_argument("--snapshot", type=Path, required=True)
    prep.add_argument("--runtime-image", type=Path, required=True)
    prep.add_argument("--research-image", required=True)
    prep.add_argument("--limits", type=Path)
    for name in ("run-agent", "finalize", "status"):
        q = sub.add_parser(name)
        q.add_argument(
            "--root",
            type=Path,
            required=True,
            help="Local prepared package, with an empty agent workspace",
        )
        q.add_argument("--worker-root", required=True, help="Prepared stage path on worker host")
        q.add_argument("--ssh-host")
        q.add_argument("--known-hosts", type=Path)
        q.add_argument("--control-path", type=Path)
        if name == "finalize":
            q.add_argument("--oracle-full", type=Path, required=True)
            q.add_argument("--oracle-test", type=Path, required=True)
    a = p.parse_args()
    if a.command == "prepare":
        task = package(
            a.root,
            read(a.cases),
            a.engine_source,
            a.snapshot,
            a.runtime_image,
            a.research_image,
            Limits(**read(a.limits)) if a.limits else Limits(),
        )
        print(
            json.dumps(
                {
                    "status": "prepared_only",
                    "run_id": task["run_id"],
                    "native_queries": 0,
                    "paid_calls": 0,
                    "worker_started": False,
                }
            )
        )
        return
    root = a.root.resolve()
    client = Client(
        a.worker_root,
        root / "transport",
        host=a.ssh_host,
        known_hosts=a.known_hosts,
        control_path=a.control_path,
    )
    if a.command == "status":
        answer = client.status()
    else:
        require_authorization(root)
        if a.command == "run-agent":
            from .model import run

            verify_initial(root)
            verify_package(root)
            verify_running_code(root)
            answer = run(root, client)
        else:
            closed, freeze = read(root / "host/model-closed.json"), read(root / "host/freeze.json")
            if closed.get("model_closed") is not True:
                raise ValueError("model must be closed before any oracle file is read")
            if (root / "host/finalization-started.json").exists():
                raise ValueError(
                    "finalization already attempted; retrieve existing identity, never retry"
                )
            write(
                root / "host/finalization-started.json", {"freeze_sha256": closed["freeze_sha256"]}
            )
            client.call(
                "freeze",
                payload={
                    "freeze": freeze,
                    "model_closed": closed,
                    "oracle_full": read(a.oracle_full),
                    "oracle_test": read(a.oracle_test),
                },
            )
            completed = client.action(
                {"kind": "final", "policies": [freeze["policy"]], "handles": [], "blocks": 2}
            )
            if not completed.get("final_complete"):
                raise ValueError("final comparison did not complete; preserve all partial returns")
            # Worker may still be committing its terminal status; don't redispatch native work.
            import time

            for _ in range(20):
                if client.status()["status"] == "completed_frozen_comparison":
                    break
                time.sleep(0.25)
            answer = client.call("report")
            write(root / "host/final-report.json", answer)
    print(json.dumps(answer))


if __name__ == "__main__":
    main()
