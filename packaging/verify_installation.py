"""Installed-bundle acceptance outside the checkout. Never contacts user databases."""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path


def invoke(args, *, cwd, expected=0):
    result = subprocess.run(list(map(str, args)), cwd=cwd, text=True, capture_output=True)
    if result.returncode != expected:
        raise RuntimeError(
            f"command failed: {args[0]} {args[1:3]}\n{result.stderr}\n{result.stdout}"
        )
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--container", action="store_true")
    args = parser.parse_args()
    bundle, work = args.bundle.resolve(), args.output.resolve()
    work.mkdir(parents=True, exist_ok=True)
    modes = ["host", "container"] if args.container else ["host"]
    results = []
    launchers = {}
    for mode in modes:
        for backend in ("fake", "pgvector"):
            install = work / f"{mode} {backend} installation"
            command = [
                "bash",
                bundle / "install.sh",
                "--mode",
                mode,
                "--backend",
                backend,
                "--directory",
                install,
                "--python",
                args.python.resolve(),
            ]
            if args.offline:
                command.append("--offline")
            invoke(command, cwd=work)
            invoke(command, cwd=work)  # Repetition must preserve the same installation.
            launcher = install / "fannagent"
            launchers[mode, backend] = launcher
            descriptors = json.loads(invoke([launcher, "backends", "list"], cwd=work))
            assert {x["name"] for x in descriptors} == (
                {"fake"} if backend == "fake" else {"fake", "pgvector"}
            )
            path = work / f"{mode}-{backend}.yaml"
            invoke([launcher, "init", "--backend", backend, "--output", path], cwd=work)
            if backend == "pgvector":
                checks = json.loads(invoke([launcher, "doctor", path], cwd=work, expected=1))
                if args.container:
                    statuses = {check["name"]: check["status"] for check in checks["checks"]}
                    assert statuses["docker"] == statuses["copy_image"] == "ok"
            else:
                invoke([launcher, "doctor", path], cwd=work)
                root = work / f"{mode} simulation run"
                invoke([launcher, "prepare", path, "--run", root], cwd=work)
                interrupted = json.loads(
                    invoke([launcher, "run", path, "--run", root, "--steps", "2"], cwd=work)
                )
                assert interrupted["status"] == "interrupted"
                resumed = json.loads(invoke([launcher, "resume", "--run", root], cwd=work))
                assert resumed["status"] == "frozen"
                report = json.loads(invoke([launcher, "evaluate", "--run", root], cwd=work))
                assert report["status"] == "accepted" and report["simulated"]
                invoke([launcher, "report", "--run", root], cwd=work)
                invoke([launcher, "clean", "--run", root], cwd=work)
                invoke([launcher, "clean", "--run", root], cwd=work)
                status = json.loads(invoke([launcher, "status", "--run", root], cwd=work))
                assert status["test_entitlement"] == "consumed"
            results.append({"mode": mode, "backend": backend, "status": "passed"})
            print(f"passed: {mode} {backend}", flush=True)
    if args.container:
        image = (bundle / "controller-fake.image").read_text().strip()
        host_runtime = Path((launchers["host", "fake"].parent / "runtime").read_text().strip())
        root = work / "lock recovery run"
        script = work / "lease.py"
        script.write_text("""
import sys,time
from pathlib import Path
from fannagent.store import Store
from fannagent.errors import AgentError
try:
    with Store(Path(sys.argv[1]),create=True).lease('run'):
        print('locked',flush=True)
        if sys.argv[2]=='hold': time.sleep(60)
except AgentError:
    print('blocked',flush=True)
""")
        container = [
            "docker",
            "run",
            "--rm",
            "--mount",
            f"type=bind,source={work},target={work}",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--entrypoint",
            "python",
            image,
            str(script),
            str(root),
        ]
        host = [str(host_runtime / "bin/python"), str(script), str(root)]
        held = subprocess.Popen([*host, "hold"], stdout=subprocess.PIPE, text=True)
        try:
            assert held.stdout.readline().strip() == "locked"
            assert invoke([*container, "try"], cwd=work).strip() == "blocked"
        finally:
            held.kill()
            held.wait(timeout=5)
        # A controller cannot prove a foreign host PID is dead; the host reclaims it.
        assert invoke([*host, "try"], cwd=work).strip() == "locked"
        assert invoke([*container, "try"], cwd=work).strip() == "locked"
        name = f"fannagent-lock-acceptance-{os.getpid()}"
        held = subprocess.Popen(
            [
                *container[:3],
                "--name",
                name,
                "-e",
                f"FANNAGENT_CONTROLLER={name}",
                *container[3:],
                "hold",
            ],
            stdout=subprocess.PIPE,
            text=True,
        )
        try:
            assert held.stdout.readline().strip() == "locked"
            assert invoke([*container, "try"], cwd=work).strip() == "blocked"
            assert invoke([*host, "try"], cwd=work).strip() == "blocked"
        finally:
            invoke(["docker", "kill", name], cwd=work)
            held.wait(timeout=10)
        assert invoke([*host, "try"], cwd=work).strip() == "locked"
        results.append({"case": "host_container_locking_and_crash_recovery", "status": "passed"})
        print("passed: cross-container and host locking", flush=True)
        host_launcher = launchers["host", "fake"]
        container_launcher = launchers["container", "fake"]
        config = work / "host-fake.yaml"
        mixed = work / "cross mode study"
        invoke([host_launcher, "prepare", config, "--run", mixed], cwd=work)
        invoke([host_launcher, "run", config, "--run", mixed, "--steps", "2"], cwd=work)
        resumed = json.loads(invoke([container_launcher, "resume", "--run", mixed], cwd=work))
        assert resumed["status"] == "frozen"
        evaluated = json.loads(invoke([container_launcher, "evaluate", "--run", mixed], cwd=work))
        assert evaluated["status"] == "accepted"
        invoke([host_launcher, "report", "--run", mixed], cwd=work)
        invoke([container_launcher, "clean", "--run", mixed], cwd=work)
        results.append({"case": "cross_mode_study_and_entitlement", "status": "passed"})
        print("passed: cross-mode study", flush=True)
        orphan = work / "orphan sandbox run"
        invoke([host_launcher, "prepare", config, "--run", orphan], cwd=work)
        script = work / "sandbox.py"
        script.write_text("""
import sys,shlex,json
from pathlib import Path
from fannagent.config import load_config
from fannagent.controller import open_run
from fannagent.study import Study
from fannagent.broker import FileBroker,Tools
from fannagent.budget import Budget
from fannagent.environment import ContainerEnvironment
c,s,b=open_run(Path(sys.argv[2]),load_config(Path(sys.argv[1])))
with FileBroker(Tools(Study(c,s,b),Budget(s,c.model)),s.root/'workspace'/'.broker') as broker:
    env=ContainerEnvironment(s.root/'workspace',broker)
    response=env.execute({'command':'fannagent-tool queries '+shlex.quote(json.dumps({'limit':1}))})
    assert response['returncode']==0,response
    denied=env.execute({'command':'ls /workspace/../private /var/run/docker.sock'})
    assert denied['returncode']!=0
    print(env.name,flush=True)
# Intentionally leave the journalled sandbox, as after a killed controller.
b.close()
""")
        endpoint = (
            os.environ.get("DOCKER_HOST")
            or subprocess.check_output(
                ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
                text=True,
            ).strip()
        )
        assert endpoint.startswith("unix://")
        socket = endpoint.removeprefix("unix://")
        socket_gid = invoke(
            [
                "docker",
                "run",
                "--rm",
                "--mount",
                f"type=bind,source={socket},target=/var/run/docker.sock,readonly",
                "--entrypoint",
                "stat",
                image,
                "-c",
                "%g",
                "/var/run/docker.sock",
            ],
            cwd=work,
        ).strip()
        controller = f"fannagent-sandbox-acceptance-{os.getpid()}"
        sandbox = invoke(
            [
                "docker",
                "run",
                "--rm",
                "--name",
                controller,
                "--label",
                "io.fannagent.controller=1",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "--group-add",
                socket_gid,
                "--tmpfs",
                "/tmp:rw,size=256m",
                "-e",
                f"FANNAGENT_CONTROLLER={controller}",
                "--mount",
                f"type=bind,source={work},target={work}",
                "--mount",
                f"type=bind,source={socket},target=/var/run/docker.sock",
                "--entrypoint",
                "python",
                image,
                script,
                config,
                orphan,
            ],
            cwd=work,
        ).strip()
        assert sandbox.startswith("fannagent-agent-")
        invoke([container_launcher, "clean", "--run", orphan], cwd=work)
        invoke(["docker", "container", "inspect", sandbox], cwd=work, expected=1)
        results.append({"case": "nested_sandbox_isolation_and_orphan_cleanup", "status": "passed"})
        print("passed: nested sandbox and orphan cleanup", flush=True)
    (work / "results.json").write_text(
        json.dumps({"results": results, "finished": time.time()}, indent=2) + "\n"
    )
    print(work / "results.json")


if __name__ == "__main__":
    main()
