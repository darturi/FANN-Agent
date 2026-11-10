"""Pinned B2f contract, durable helpers and finite operation reservations."""

import re
import time
from collections import Counter
from pathlib import Path

from legacy_common import (  # noqa: F401
    PROFILE_SHA,
    SOURCE_MANIFEST,
    bootstrap,
    digest,
    encoded,
    lines,
    parity,
    read,
    replace,
    safe_file,
    save,
    sha,
)

HERE = Path(__file__).resolve().parent
NAME = "torch-partial-calibration-v1"
VERSION = "partial-calibration.v1"
PREFIX = "reviews-partial-calibration-v1-"
CONTRACT_SHA = "679dc806e903ee7d202e5851f2cc4ece889aaebf25d3a9c49e5771af29f558db"
if sha(HERE / "CONTRACT.json") != CONTRACT_SHA:
    raise ValueError("Frozen B2f contract changed")
CONTRACT = read(HERE / "CONTRACT.json")
COUNTS = dict(CONTRACT["counts"], allocations=1, vectors=200, cases=200)
CELLS = ["native640", "partial640"]
MODES = tuple(CELLS)
INDEX = "reviews_hnsw_votes108_v1"
INDEX_BYTES = 1012678656
CRITERIA = dict(
    bootstrap_samples=10000,
    bootstrap_seed=20261019,
    minimum_reference_recall=0.95,
    development_recall_reserve=0.0025,
)
STAGES = CONTRACT["resources"]["stage_seconds"]
SQL_CAPS = dict(observer=13500, startup=1000, truth_helper=4040)
OPERATIONS = dict(
    qualification_exact=2,
    qualification_native640=4,
    qualification_partial640=4,
    reference_exact=200,
    reference_native640=200,
    reference_partial640=200,
    priming=80,
    conditioning=3200,
    warmup=6400,
    measurement=4800,
    diagnostic_conditioning=256,
    diagnostic_warmup=512,
    diagnostic_measurement=384,
)
assert sum(OPERATIONS.values()) == 16242


def context(q):
    if (
        type(q.get("k")) is not int
        or q["k"] != 10
        or q.get("filter") != dict(field="m_000000", op="gte", value=108)
        or type(q["filter"]["value"]) is not int
    ):
        raise ValueError("Only the frozen votes108/k10 requests are allowed")
    return "votes108"


def inventory(items):
    if len(items) != 200 or len({i["group"] for i in items}) != 200:
        raise ValueError("Requires exactly the 200 exposed vector groups")
    for i in items:
        context(i["query"])
        if i["query"]["id"] != i["group"] + "-votes108":
            raise ValueError("Request/group identity differs")
    return sorted(i["group"] for i in items)


def effective(origin, mode):
    import copy

    if mode not in MODES:
        raise ValueError("Unknown cell")
    out = copy.deepcopy(origin)
    out["settings"]["hnsw.ef_search"] = "640"
    return out


def protocol():
    return dict(
        name=NAME,
        version=VERSION,
        prefix=PREFIX,
        counts=COUNTS,
        operations=OPERATIONS,
        contract_sha256=CONTRACT_SHA,
        schedule_sha256=CONTRACT["schedule_sha256"],
        stage_seconds=STAGES,
        sql_caps=SQL_CAPS,
        provider_calls_allowed=0,
        confirmation_queries_allowed=0,
        new_fits_allowed=0,
        activation_qualification=False,
        treatment_economics_qualification=False,
    )


def verify(package, bundle=None):
    p = Path(package)
    m = read(p / "manifest.json")
    if m["version"] != VERSION:
        raise ValueError("Protocol manifest differs")
    actual = {str(f.relative_to(p)) for f in p.rglob("*") if f.is_file()}
    if actual - set(m["files"]) - {"manifest.json", "submission-binding.json"}:
        raise ValueError("Unexpected package file")
    for name, h in m["files"].items():
        if sha(safe_file(p, name)) != h:
            raise ValueError("Package changed: " + name)
    cfg = read(p / "experiment.json")
    if any(cfg.get(k) != v for k, v in protocol().items()):
        raise ValueError("Implementation contract differs")
    if (
        sha(p / "CONTRACT.json") != CONTRACT_SHA
        or sha(p / "DESIGN.md") != CONTRACT["design_sha256"]
        or sha(p / "SCHEDULE.json") != CONTRACT["schedule_sha256"]
        or sha(p / "frozen/manifest.json") != SOURCE_MANIFEST
    ):
        raise ValueError("Frozen scientific boundary differs")
    for name, h in read(p / "frozen/manifest.json")["files"].items():
        if sha(safe_file(p / "frozen", name)) != h:
            raise ValueError("Frozen native implementation changed: " + name)
    pins = read(p / "SOURCE-PINS.json")
    if set(pins) != set(CONTRACT["source_files_sha256"]):
        raise ValueError("Source pin inventory differs")
    for original, entry in pins.items():
        if (
            entry["sha256"] != CONTRACT["source_files_sha256"][original]
            or sha(safe_file(p, entry["file"])) != entry["sha256"]
        ):
            raise ValueError("Pinned design evidence differs: " + original)
    items = lines(p / "queries.jsonl")
    inventory(items)
    if sha(p / "queries.jsonl") != cfg["queries_sha256"]:
        raise ValueError("Exposed cohort changed")
    if bundle is not None:
        bootstrap(p)
        from control import verify as baseverify

        baseverify(p / "frozen", Path(bundle))
    return cfg


def protected(package, sources):
    from legacy_common import protected as prior

    p, sources = Path(package), Path(sources)
    result = prior(p, sources)
    cfg = read(p / "experiment.json")
    previous = Path(cfg["prior_b2d_package"])
    m = read(p / "prior-b2d-manifest.json")
    if sha(previous / "manifest.json") != cfg["prior_b2d_manifest_sha256"]:
        raise ValueError("B2d package identity changed")
    for name, h in m["files"].items():
        if sha(safe_file(previous, name)) != h:
            raise ValueError("B2d package changed: " + name)
    result["b2d_settings_seal"] = {"manifest_sha256": cfg["prior_b2d_manifest_sha256"]}
    return result


def campaign_identity(campaign, package):
    r = read(Path(campaign) / "submission.json")
    name = Path(r["campaign"]).name
    if (
        not re.fullmatch(re.escape(PREFIX) + r"[0-9]{8}T[0-9]{6}Z\.[A-Za-z0-9_-]+", name)
        or r["package_manifest_sha256"] != sha(Path(package) / "manifest.json")
        or r["counts"] != COUNTS
        or set(r["jobs"]) != {"block-0"}
        or r["dispatch"] != {"block-0": {"status": "submitted", "job_id": r["jobs"]["block-0"]}}
    ):
        raise ValueError("Campaign/package/submission identity differs")
    return name


class Budget:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.started = clock()
        self.deadline = self.started + 10200
        self.stage = None
        self.stage_end = self.deadline - 600
        self.stages = []
        self.calls = 0
        self.operations = Counter()
        self.sql = Counter()

    def enter(self, name):
        if name not in STAGES or any(s["name"] == name for s in self.stages):
            raise RuntimeError("Unknown/repeated stage")
        now = self.clock()
        end = min(now + STAGES[name], self.deadline - (0 if name == "final_cleanup" else 600))
        if end <= now:
            raise RuntimeError("Work deadline exhausted")
        self.stage, self.stage_end = name, end
        self.stages.append(dict(name=name, start=now, end=end))

    def remaining(self):
        return min(self.deadline, self.stage_end) - self.clock()

    def check(self, allowance=0):
        if self.stage is None or self.remaining() <= allowance:
            raise RuntimeError("Stage/work deadline exhausted: " + str(self.stage))

    def reserve(self, operation):
        self.check(30)
        if (
            operation not in OPERATIONS
            or self.calls >= 16242
            or self.operations[operation] >= OPERATIONS[operation]
        ):
            raise RuntimeError("Search/operation ceiling exhausted")
        self.calls += 1
        self.operations[operation] += 1

    def sql_reserve(self, category):
        self.check()
        if category not in SQL_CAPS or self.sql[category] >= SQL_CAPS[category]:
            raise RuntimeError("SQL ceiling exhausted: " + category)
        self.sql[category] += 1
