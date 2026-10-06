# ruff: noqa: E501
"""Installed-wheel acceptance in three clean environments, outside the checkout."""

import hashlib
import json
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UV = str(Path.home() / ".local/bin/uv")
CORE = ROOT / "agent/dist/fannagent-0.2.0-py3-none-any.whl"
PG = ROOT / "agent-pgvector/dist/fannagent_pgvector-0.1.0-py3-none-any.whl"
TEST = (
    ROOT / "agent/tests/extensions/independent/dist/fannagent_test_extension-0.1.0-py3-none-any.whl"
)
WORK = Path(tempfile.mkdtemp(prefix="fannagent-wheel-acceptance-"))
ENV = {
    **os.environ,
    "UV_CACHE_DIR": os.environ.get("UV_CACHE_DIR", str(Path.home() / ".cache/uv")),
    "MSWEA_SILENT_STARTUP": "1",
    "LITELLM_LOCAL_MODEL_COST_MAP": "True",
    "MSWEA_GLOBAL_CONFIG_DIR": str(WORK / "mini"),
}
ENV.pop("PYTHONPATH", None)


def invoke(args):
    if os.environ.get("FANNAGENT_VERIFY_OFFLINE") == "1":
        args = [*args[:1], "--offline", *args[1:]] if args[0] == UV else args
    subprocess.run(args, check=True, cwd=WORK, env=ENV)


def code(python, body):
    invoke([str(python), "-c", body])


constraints = WORK / "core-constraints.txt"
subprocess.run(
    [
        UV,
        "export",
        "--offline",
        "--project",
        str(ROOT / "agent"),
        "--no-dev",
        "--no-emit-project",
        "--no-hashes",
        "--output-file",
        str(constraints),
    ],
    check=True,
    stdout=subprocess.DEVNULL,
    env=ENV,
)
before = hashlib.sha256(CORE.read_bytes()).hexdigest()
with zipfile.ZipFile(CORE) as z:
    assert not any("pgvector" in n or "http_backends" in n for n in z.namelist())
with zipfile.ZipFile(PG) as z:
    for suffix in (
        "engine/postgresql-17.11-executor.patch",
        "engine/patches/0004-existing-target-binding.patch",
        "engine/build.sh",
        "native/registry.json",
    ):
        assert any(n.endswith(suffix) for n in z.namelist()), suffix

for kind, wheels in (("core", [CORE]), ("pgvector", [CORE, PG]), ("independent", [CORE, TEST])):
    envdir = WORK / kind
    invoke([UV, "venv", "--python", "3.12", str(envdir)])
    python = envdir / "bin/python"
    invoke(
        [
            UV,
            "pip",
            "install",
            "--python",
            str(python),
            "-c",
            str(constraints),
            *map(str, wheels),
        ]
    )
    code(
        python,
        'import importlib.util; assert importlib.util.find_spec("fannbench") is None; assert importlib.util.find_spec("elasticsearch") is None; from fannagent.backends import discover; print("discovered", sorted(discover()))',
    )
    if kind == "core":
        code(
            python,
            'import importlib.util; assert importlib.util.find_spec("psycopg") is None; from fannagent.backends import discover; assert set(discover()) == {"fake"}',
        )
    if kind == "pgvector":
        code(
            python,
            'from fannagent.backends import extension; from importlib.resources import files; import sys; m=extension("pgvector").manifest(); assert "psycopg" not in sys.modules; assert m.name=="pgvector"; assert files("fannagent_pgvector").joinpath("engine/build.sh").is_file()',
        )
    if kind in {"core", "independent"}:
        name = "fake" if kind == "core" else "independent"
        code(
            python,
            f"""
from pathlib import Path
from fannagent.config import RunConfig
from fannagent.controller import open_run, explore
from fannagent.study import Study
from fannagent.client import open_session
from fannagent.cli import status, report, clean
from fannagent.api.conformance import check_descriptor, check_observation
from fannagent.backends import extension
config=RunConfig(backend={{"name": {name!r}}}, model={{"ceiling_usd":"1"}}, workload={{"count":1000,"seed":1,"warmups":0,"passes":1}})
root=Path({str(WORK / (kind + "-run"))!r})
config,store,backend=open_run(root,config)
check_descriptor(extension({name!r}).manifest(),backend)
store.set("prepared",backend.prepare_copy().serialize())
assert explore(config,store,backend,step_limit=2)["status"]=="interrupted"
assert explore(config,store,backend,resume=True,step_limit=10)["status"]=="frozen"
study=Study(config,store,backend)
assert study.final()["status"]=="accepted"
session=open_session(root)
q=backend.snapshot().query({{"id":"app","k":10,"vector":backend.snapshot().rows[0]["vector"]}})
result=session.query(q)
assert type(result.ids[0]) is {"int" if kind == "core" else "str"}
session.close()
policy=study.frozen_policy()
(root/"saved-hash").write_text(policy.policy_hash)
assert backend.runtime_profile.checkpoint_interval=={8 if kind == "core" else 5}
status(root); report(root)
""",
        )
    if kind == "core":
        # Installing an unrelated separately distributed extension must preserve the saved policy.
        invoke([UV, "pip", "install", "--python", str(python), str(TEST)])
        code(
            python,
            f'from pathlib import Path; from fannagent.controller import open_run; from fannagent.study import Study; p=Path({str(WORK / "core-run")!r}); c,s,b=open_run(p); assert Study(c,s,b).frozen_policy().policy_hash==(p/"saved-hash").read_text()',
        )
    if kind in {"core", "independent"}:
        code(
            python,
            f"from pathlib import Path; from fannagent.cli import clean; clean(Path({str(WORK / (kind + '-run'))!r}))",
        )
assert hashlib.sha256(CORE.read_bytes()).hexdigest() == before
(WORK / "result.json").write_text(
    json.dumps(
        {
            "status": "passed",
            "core_wheel_sha256": before,
            "environments": ["core", "pgvector", "independent"],
        }
    )
)
print("wheel_acceptance", WORK)
