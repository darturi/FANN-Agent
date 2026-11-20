"""Explicit static-asset packaging and trusted compile/container execution."""

import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from . import EXPERIMENT, PROJECT
from .core import digest, prepare, read, seal_initial, sha, write
from .engine import bindings, empty

NEUTRAL_STUDY = (
    "static bool CompiledStudyRule(int arm,int filter,int cp,int count,"
    "double gap,double tenth,int turnover) { return false; }\n"
)
NEUTRAL_V2 = """static bool V2ArmDeclared(int arm) { return false; }
static int V2Mask(int arm,int filter,int cp) { return 0; }
static bool V2ForceContinue(int arm) { return false; }
static bool V2Decision(int arm,int filter,int cp,int count,double tenth,double gap,
 int turnover,bool full,bool hasgap,bool hasturn) { return false; }
"""


def software_tree(source, target):
    """Copy software, replacing every fitted policy header with data-free stubs."""
    source, target = Path(source), Path(target)
    if any(p.is_symlink() for p in source.rglob("*")):
        raise ValueError("engine software must not contain links")
    allowed = {".c", ".h", ".inc", ".sql", ".control", ".mk"}
    for p in source.rglob("*"):
        if not p.is_file() or not (p.suffix in allowed or p.name in ("Makefile", "LICENSE")):
            continue
        if p.name.startswith("compiled_"):
            continue
        dest = target / p.relative_to(source)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, dest)
    if (
        not (target / "src/hnswutils.c").exists()
        or "broad_runtime.inc" not in (target / "src/hnswutils.c").read_text()
    ):
        raise ValueError("a qualified v3 software engine template is required")
    (target / "src/compiled_study_policies.inc").write_text(NEUTRAL_STUDY)
    (target / "src/compiled_v2.inc").write_text(NEUTRAL_V2)
    from fannproto3.compiler import compile_programs

    code, _ = compile_programs([{"arm": 89, "policy": empty(), "force_continue": False}])
    (target / "src/compiled_v3.inc").write_text(code)
    # Disable every legacy policy arm. Arm 10 remains a private forced-prefix primitive.
    p = target / "src/fannbench.c"
    text = p.read_text()
    pattern = (
        r"arm < 0 \|\| \(arm > 11 && !FannbenchV2ArmDeclared\(arm\)"
        r" && !FannbenchV3ArmDeclared\(arm\)\)"
    )
    text, n = re.subn(pattern, "(arm != 10 && !FannbenchV3ArmDeclared(arm))", text)
    if n != 1 and text.count("(arm != 10 && !FannbenchV3ArmDeclared(arm))") != 1:
        raise ValueError("legacy-arm isolation patch did not match exactly")
    p.write_text(text)


def package(
    root, cases, engine_source, snapshot, image, research_image, limits=None, *, database_user=None
):
    """Offline preparation only. No Docker, database, provider or scheduler invocation."""
    root, snapshot, image = Path(root), Path(snapshot).resolve(), Path(image).resolve()
    root = root.resolve()
    if any(
        root.is_relative_to(Path(p).resolve()) or Path(p).resolve().is_relative_to(root)
        for p in (engine_source, snapshot, EXPERIMENT, PROJECT / "src")
    ):
        raise ValueError("output must be separate from static source/input trees")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", research_image):
        raise ValueError("offline research image must be pinned by digest")
    if not (snapshot / "PG_VERSION").is_file() or (snapshot / "postmaster.pid").exists():
        raise ValueError("a stopped static PostgreSQL snapshot directory is required")
    if any(p.is_symlink() for p in snapshot.rglob("*")):
        raise ValueError("snapshot links are not allowed")
    task = prepare(root, cases, limits)
    code = root / "code"
    if (PROJECT / "host-vendor").is_dir():
        shutil.copytree(
            PROJECT / "host-vendor",
            code / "host-vendor",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    shutil.copytree(
        EXPERIMENT,
        code / "experiments/torch-clean-start-v4",
        ignore=shutil.ignore_patterns("__pycache__", "tests", "checks", "*.pyc"),
    )
    shutil.copytree(
        PROJECT / "src/fannagent",
        code / "src/fannagent",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copytree(
        PROJECT / "experiments/filtered-ann-protocol-v3/fannproto3",
        code / "experiments/filtered-ann-protocol-v3/fannproto3",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    software_tree(engine_source, root / "private/engine")
    api = root / "agent/api"
    shutil.copyfile(PROJECT / "src/fannagent/api/broad_policy.py", api / "broad_contract.py")
    shutil.copyfile(EXPERIMENT / "fannclean/fit.py", api / "fit.py")
    backend = {
        "snapshot": "/database-snapshot",
        "rows": 247286,
        "database": "torch_reviews",
        "pg_ctl": "/opt/postgresql/bin/pg_ctl",
    }
    if database_user:
        backend["database_user"] = database_user
    write(root / "private/backend.json", backend)
    write(
        root / "deployment.json",
        {
            "image": str(image),
            "image_sha256": sha(image),
            "snapshot": str(snapshot),
            "research_image": research_image,
        },
    )
    # Snapshot identity covers every byte, not a past measurement-derived summary.
    write(
        root / "private/snapshot-seal.json",
        {str(p.relative_to(snapshot)): sha(p) for p in snapshot.rglob("*") if p.is_file()},
    )
    seal_initial(root)
    inputs = [p for p in root.rglob("*") if p.is_file() and p.name != "package-seal.json"]
    write(root / "package-seal.json", {p.relative_to(root).as_posix(): sha(p) for p in inputs})
    return task


def verify_package(root):
    root = Path(root)
    for rel, expected in read(root / "package-seal.json").items():
        path = root / rel
        if path.is_symlink() or sha(path) != expected:
            raise ValueError("sealed software/static input changed: " + rel)


def verify_running_code(root):
    """Reject a controller/worker checkout that differs from its sealed software."""
    sources = list((EXPERIMENT / "fannclean").glob("*.py"))
    sources += [PROJECT / "src/fannagent/api/broad_policy.py"]
    sources += list((PROJECT / "experiments/filtered-ann-protocol-v3/fannproto3").glob("*.py"))
    for source in sources:
        target = Path(root) / "code" / source.relative_to(PROJECT)
        if not target.is_file() or sha(source) != sha(target):
            raise ValueError("executing software differs from sealed package: " + source.name)


def compile_request(root, directory, payload):
    from fannproto3.compiler import compile_programs

    root, directory = Path(root), Path(directory)
    assigned = bindings(payload)
    if payload["kind"] == "final":
        refs = read(root / "private/comparison.json")
        freeze = read(root / "private/final-freeze.json")
        if refs["agent_freeze_sha256"] != digest(freeze) or payload["policies"] != [
            freeze["policy"]
        ]:
            raise ValueError("final compiler requires the independently frozen policy")
        for name in ("oracle_full", "oracle_test"):
            assigned[name] = (refs[name], False)
    arms = {name: 60 + i for i, name in enumerate(assigned)}
    entries = [
        {"arm": arms[name], "policy": p, "force_continue": f} for name, (p, f) in assigned.items()
    ]
    code, manifest = compile_programs(entries)
    engine = directory / "engine"
    shutil.copytree(root / "private/engine", engine)
    (engine / "src/compiled_v3.inc").write_text(code)
    result = subprocess.run(
        ["make", "-j1", "OPTFLAGS=", "PG_CONFIG=/opt/postgresql/bin/pg_config"],
        cwd=engine,
        capture_output=True,
        timeout=600,
    )
    (directory / "build.log").write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise ValueError("trusted native compiler/build failed")
    shutil.copyfile(engine / "vector.so", directory / "vector.so")
    write(
        directory / "module.json",
        {"sha256": sha(directory / "vector.so"), "arms": arms, "manifest_hash": digest(manifest)},
    )


class ContainerExecutor:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def __call__(self, identity, payload, timeout):
        begun = time.monotonic()
        root = self.root
        config = read(root / "deployment.json")
        if sha(config["image"]) != config["image_sha256"]:
            raise ValueError("runtime image changed")
        for rel, h in read(root / "private/snapshot-seal.json").items():
            if sha(Path(config["snapshot"]) / rel) != h:
                raise ValueError("static snapshot changed")
        directory = root / "private/builds" / identity
        directory.mkdir(parents=True, exist_ok=False)
        write(directory / "payload.json", payload)
        prefix = [
            "/share/apps/apptainer/bin/apptainer",
            "exec",
            "--cleanenv",
            "--containall",
            "--no-home",
            "--bind",
            f"{root}:/stage:rw",
            "--bind",
            f"{root / 'code'}:/code:ro",
            "--env",
            "PYTHONPATH=/code/experiments/torch-clean-start-v4:/code/src:"
            "/code/experiments/filtered-ann-protocol-v3:/opt/torch-reviews/vendor",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            "--env",
            "OPENBLAS_NUM_THREADS=1",
            "--env",
            "OMP_NUM_THREADS=1",
        ]
        relative = directory.relative_to(root).as_posix()
        subprocess.run(
            prefix
            + [
                config["image"],
                "python",
                "-B",
                "-m",
                "fannclean.driver",
                "compile",
                "--root",
                "/stage",
                "--directory",
                "/stage/" + relative,
            ],
            check=True,
            timeout=min(timeout, 900),
        )
        remaining = timeout - (time.monotonic() - begun)
        if remaining <= 0:
            raise TimeoutError("compilation exhausted the action time envelope")
        command = prefix + [
            "--bind",
            f"{directory / 'vector.so'}:/opt/postgresql/lib/vector.so:ro",
            "--bind",
            f"{config['snapshot']}:/database-snapshot:ro",
            config["image"],
            "python",
            "-B",
            "-m",
            "fannclean.driver",
            "execute",
            "--root",
            "/stage",
            "--directory",
            "/stage/" + relative,
            "--identity",
            identity,
        ]
        with (directory / "execute.log").open("wb") as out:
            process = subprocess.Popen(
                command, stdout=out, stderr=subprocess.STDOUT, start_new_session=True
            )
            try:
                rc = process.wait(timeout=remaining)
            except BaseException:
                import signal

                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                raise
        if rc:
            raise ValueError("native action failed; preserve uncertain reservation and logs")
        return read(root / "private/requests" / identity / "response.json")
