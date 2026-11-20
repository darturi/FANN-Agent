"""Explicit phase entrypoints. Preparing/inspecting never starts a worker or model."""

import argparse
import json
from pathlib import Path

from .core import Limits, digest, read, verify_initial, write
from .deploy import package, verify_package, verify_running_code
from .transport import Client, require_authorization


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare", help="Offline only: seal static task and data-free software")
    prep.add_argument("--root", type=Path, required=True)
    prep.add_argument("--cases", type=Path, required=True)
    prep.add_argument("--engine-source", type=Path)
    prep.add_argument("--snapshot", type=Path)
    prep.add_argument("--runtime-image", type=Path)
    prep.add_argument("--research-image")
    prep.add_argument("--static-asset-stage", type=Path, help="Reuse only sealed static asset pins")
    prep.add_argument("--limits", type=Path)
    prep.add_argument("--database-user")
    prep.add_argument("--comparison-plan", type=Path)
    pair = sub.add_parser("compare", help="Compare independently finalized paired run reports")
    pair.add_argument("reports", nargs="+", type=Path)
    for name in ("run-agent", "run-scripted", "finalize", "status"):
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
        q.add_argument("--host-key-alias")
        if name == "finalize":
            q.add_argument("--oracle-full", type=Path)
            q.add_argument("--oracle-test", type=Path)
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
            database_user=a.database_user,
            comparison=read(a.comparison_plan) if a.comparison_plan else None,
            asset_stage=a.static_asset_stage,
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
    if a.command == "compare":
        from .comparison import compare_reports

        print(json.dumps(compare_reports([read(p) for p in a.reports])))
        return
    root = a.root.resolve()
    client = Client(
        a.worker_root,
        root / "transport",
        host=a.ssh_host,
        known_hosts=a.known_hosts,
        control_path=a.control_path,
        host_key_alias=a.host_key_alias,
    )
    if a.command == "status":
        answer = client.status()
    else:
        require_authorization(root)
        config = read(root / "config.json")
        paired = config.get("comparison")
        if a.command in ("run-agent", "run-scripted"):
            from .comparison import run_scripted
            from .model import run

            verify_initial(root)
            verify_package(root)
            verify_running_code(root)
            answer = (run if a.command == "run-agent" else run_scripted)(root, client)
        else:
            closed, freeze = read(root / "host/model-closed.json"), read(root / "host/freeze.json")
            if closed.get("model_closed") is not True:
                raise ValueError("model must be closed before any oracle file is read")
            oracle_paths = (a.oracle_full, a.oracle_test)
            if paired and any(oracle_paths):
                raise ValueError("paired comparison finalization does not take oracle artifacts")
            if not paired and not all(oracle_paths):
                raise ValueError("historic oracle finalization requires both oracle artifacts")
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
                    **(
                        {}
                        if paired
                        else {
                            "oracle_full": read(a.oracle_full),
                            "oracle_test": read(a.oracle_test),
                        }
                    ),
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
            if paired:
                software = read(root / "package-seal.json")
                answer["comparison"] = {
                    **paired,
                    "limits": config["limits"],
                    "initial_handles_sha256": closed.get("initial_handles_sha256"),
                    "assets_sha256": digest(
                        {
                            path: value
                            for path, value in software.items()
                            if path.startswith(("private/engine/", "code/"))
                            or path == "private/snapshot-seal.json"
                        }
                    ),
                    "runtime_image_sha256": read(root / "deployment.json")["image_sha256"],
                    "research_image": read(root / "deployment.json")["research_image"],
                    "model_calls": closed.get("model_calls", 0),
                    "model_charged_usd": closed["model_charged_usd"],
                }
            write(root / "host/final-report.json", answer)
    print(json.dumps(answer))


if __name__ == "__main__":
    main()
