"""Strict static task inputs, empty initial workspaces and durable query budgets."""

import errno
import hashlib
import json
import math
import os
import secrets
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

FILTERS = (-1, 743, 527, 310, 192, 108, 32)
ROLES = {"development", "validation", "test", "excluded_historical"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1048576), b""):
            h.update(part)
    return h.hexdigest()


def read(path):
    # Atomic replacement on a shared filesystem can invalidate an already-open
    # inode. Reopen only this idempotent read; never retry a native/API operation.
    delays = (0.01, 0.03, 0.1, 0.3, 1.0)
    for attempt in range(len(delays) + 1):
        try:
            return json.loads(Path(path).read_text())
        except OSError as error:
            if error.errno != errno.ESTALE or attempt == len(delays):
                raise
            time.sleep(delays[attempt])


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as stream:
        stream.write(canonical(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


@dataclass(frozen=True)
class Limits:
    query_cap: int = 300000
    final_reserve: int = 195000
    model_usd: str = "15"
    wall_seconds: int = 21600
    discovery_seconds: int = 14400
    output_tokens: int = 16000
    research_seconds: int = 240
    research_memory_mib: int = 2048
    minimum_rounds: int = 2
    minimum_structures: int = 2
    bootstrap_draws: int = 10000
    control_tolerance: float = 0.02

    def __post_init__(self):
        from decimal import Decimal

        if any(
            type(v) is not int or v <= 0
            for k, v in asdict(self).items()
            if k not in ("model_usd", "control_tolerance")
        ):
            raise ValueError("positive integer resource limits required")
        if not Decimal(self.model_usd).is_finite() or Decimal(self.model_usd) <= 0:
            raise ValueError("positive finite dollar budget required")
        if not 0 < self.control_tolerance < 1 or not 2048 <= self.output_tokens <= 16000:
            raise ValueError("invalid equivalence margin or output budget")
        if not 0 < self.final_reserve < self.query_cap:
            raise ValueError("final reservation must leave an acquisition/search budget")
        if not 0 < self.discovery_seconds < self.wall_seconds:
            raise ValueError("discovery must leave independent final evaluation time")
        if self.minimum_rounds < 2 or self.minimum_structures < 2:
            raise ValueError("normal stopping requires multiple rounds and program structures")


def validate_cases(cases):
    seen, groups = set(), {}
    for case in cases:
        if set(case) != {"handle", "group", "role", "filter", "vector"}:
            raise ValueError("task inputs may contain only static query/split fields")
        h, g, role, t, vector = (case[k] for k in ("handle", "group", "role", "filter", "vector"))
        if not isinstance(h, str) or not h or h in seen or not isinstance(g, str) or not g:
            raise ValueError("unique nonempty query handles and groups required")
        if role not in ROLES or type(t) is not int or t not in FILTERS:
            raise ValueError("invalid split or filter")
        if (
            not isinstance(vector, list)
            or not vector
            or not all(type(v) in (int, float) and math.isfinite(v) for v in vector)
        ):
            raise ValueError("finite static vectors required")
        previous = groups.setdefault(g, (role, vector, set()))
        if previous[:2] != (role, vector) or t in previous[2]:
            raise ValueError("one vector/split and one case per condition per group required")
        previous[2].add(t)
        seen.add(h)
    if not groups or any(v[2] != set(FILTERS) for v in groups.values()):
        raise ValueError("each query group must include all seven conditions")


def prepare(root, cases, limits=None):
    """Creates no observations, baseline results, labels, cache, journal or candidate."""
    root = Path(root)
    validate_cases(cases)
    limits = limits or Limits()
    run_id = uuid.uuid4().hex
    # Handles are regenerated so past source IDs cannot be used as empirical side channels.
    groups = sorted({r["group"] for r in cases})
    secrets.SystemRandom().shuffle(groups)
    aliases = {g: f"q{i:04d}" for i, g in enumerate(groups)}
    private = []
    for r in cases:
        group = aliases[r["group"]]
        private.append(
            {
                **r,
                "group": group,
                "handle": group + ("-all" if r["filter"] < 0 else f"-v{r['filter']}"),
            }
        )
    n, nt = len(private), sum(r["role"] == "test" for r in private)
    # Two randomized-pair blocks; test oracle only on test cases.
    # Full-cohort quality and VM audit, with 16-group independent output panels.
    final_worst = 26 * n + 5 * nt + 512
    if final_worst > limits.final_reserve:
        raise ValueError(f"final schedule needs {final_worst} reserved queries")
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    workspace = root / "agent"
    for name in ("api", "evidence", "policies", "scratch"):
        (workspace / name).mkdir(parents=True)
    task = {
        "schema": "fannagent.clean-task.v1",
        "run_id": run_id,
        "conditions": list(FILTERS),
        "limits": asdict(limits),
        "queries": [
            {k: r[k] for k in ("handle", "group", "filter")}
            for r in private
            if r["role"] == "development"
        ],
    }
    write(workspace / "task.json", task)
    (workspace / "evidence/observations.jsonl").write_bytes(b"")
    write(root / "private/cases.json", private)
    write(
        root / "config.json",
        {"run_id": run_id, "limits": asdict(limits), "final_worst": final_worst},
    )
    return task


def seal_initial(root):
    root = Path(root)
    workspace = root / "agent"
    if any((workspace / "policies").iterdir()) or any((workspace / "scratch").iterdir()):
        raise ValueError("initial policy and scratch directories must be empty")
    if (workspace / "evidence/observations.jsonl").read_bytes():
        raise ValueError("initial empirical evidence must be empty")
    allowed = {"task.json", "evidence/observations.jsonl"}
    for p in workspace.rglob("*"):
        if p.is_symlink():
            raise ValueError("initial workspace cannot contain links")
        if (
            p.is_file()
            and p.relative_to(workspace).as_posix() not in allowed
            and p.parent != workspace / "api"
        ):
            raise ValueError("unexpected initial file/history")
    files = {
        p.relative_to(workspace).as_posix(): sha(p) for p in workspace.rglob("*") if p.is_file()
    }
    inputs = {p: sha(root / p) for p in ("config.json", "private/cases.json")}
    manifest = {
        "run_id": read(root / "config.json")["run_id"],
        "initial_empirical_records": 0,
        "files": files,
        "static_inputs": inputs,
    }
    write(root / "initial-seal.json", manifest)
    return manifest


def verify_initial(root):
    root = Path(root)
    seal = read(root / "initial-seal.json")
    if any(p.is_symlink() for p in (root / "agent").rglob("*")):
        raise ValueError("initial workspace links rejected")
    files = {
        p.relative_to(root / "agent").as_posix(): sha(p)
        for p in (root / "agent").rglob("*")
        if p.is_file()
    }
    if (
        seal["run_id"] != read(root / "config.json")["run_id"]
        or seal["initial_empirical_records"] != 0
        or seal["files"] != files
    ):
        raise ValueError("initial workspace changed or inherited evidence/history is present")
    if any(sha(root / p) != h for p, h in seal["static_inputs"].items()):
        raise ValueError("sealed static query inputs changed")


class Ledger:
    """Serialized worker: persist reservation before work and a debit before each query."""

    def __init__(self, path, limits, run_id, checkpoint_every=1):
        self.path, self.limits = Path(path), limits
        if type(checkpoint_every) is not int or checkpoint_every < 1:
            raise ValueError("positive progress checkpoint interval required")
        self.checkpoint_every, self.pending = checkpoint_every, None
        if not self.path.exists():
            write(self.path, {"run_id": run_id, "charged": 0, "requests": {}})
        if read(self.path).get("run_id") != run_id:
            raise ValueError("cross-run query ledger rejected")

    def check_available(self, worst, final=False):
        s = read(self.path)
        if any(r["status"] == "open" for r in s["requests"].values()):
            raise ValueError("uncertain native request; do not redispatch")
        ceiling = (
            self.limits.query_cap if final else self.limits.query_cap - self.limits.final_reserve
        )
        if type(worst) is not int or worst <= 0 or s["charged"] + worst > ceiling:
            raise ValueError("query budget would invade the frozen final reservation")

    def reserve(self, identity, worst, final=False):
        s = read(self.path)
        if identity in s["requests"] or any(r["status"] == "open" for r in s["requests"].values()):
            raise ValueError("duplicate or uncertain native request; recover without redispatch")
        ceiling = (
            self.limits.query_cap if final else self.limits.query_cap - self.limits.final_reserve
        )
        if type(worst) is not int or worst <= 0 or s["charged"] + worst > ceiling:
            raise ValueError("query budget would invade the frozen final reservation")
        s["charged"] += worst
        s["requests"][identity] = {
            "status": "open",
            "reserved": worst,
            "actual": 0,
            "operations": {},
        }
        write(self.path, s)

    def tick(self, identity, operation):
        s = self.pending if self.pending is not None else read(self.path)
        r = s["requests"][identity]
        if r["status"] != "open" or r["actual"] >= r["reserved"]:
            raise ValueError("request query envelope exhausted")
        r["actual"] += 1
        r["operations"][operation] = r["operations"].get(operation, 0) + 1
        self.pending = s
        if r["actual"] % self.checkpoint_every == 0:
            self.flush()
        return r["actual"]

    def flush(self):
        if self.pending is not None:
            write(self.path, self.pending)
            self.pending = None

    @contextmanager
    def checkpoint_on_exit(self):
        # The entire request remains charged at its durable worst case until
        # verified cleanup. A hard kill loses at most a progress checkpoint,
        # never its reservation or the protection of the total query ceiling.
        try:
            yield
        finally:
            self.flush()

    def settle(self, identity, cleanup_verified):
        if not cleanup_verified:
            raise ValueError("do not release uncertain queries before verified cleanup")
        self.flush()
        s = read(self.path)
        r = s["requests"][identity]
        if r["status"] != "open":
            raise ValueError("request already settled")
        s["charged"] -= r["reserved"] - r["actual"]
        r["status"] = "settled"
        write(self.path, s)


def append_evidence(workspace, run_id, response):
    """Only successful, bound worker responses may enter the read-only evidence mount."""
    if response.get("run_id") != run_id or response.get("status") != "complete":
        raise ValueError("cross-run/unsettled evidence rejected")
    records = response.get("evidence", [])
    for r in records:
        if (
            r.get("run_id") != run_id
            or r.get("request_id") != response["request_id"]
            or r.get("query_ordinal", 0) <= 0
        ):
            raise ValueError("evidence lacks same-run executed-query provenance")
    path = Path(workspace) / "evidence/observations.jsonl"
    with path.open("ab") as out:
        for record in records:
            out.write(canonical(record) + b"\n")
        out.flush()
        os.fsync(out.fileno())
