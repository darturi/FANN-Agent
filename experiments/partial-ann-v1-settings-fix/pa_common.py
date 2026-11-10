"""Finite B2d contract; no database or experimental execution on import."""

import copy
import re
import time
from collections import Counter
from pathlib import Path

from legacy_common import (
    PROFILE_SHA as PROFILE_SHA,
)
from legacy_common import (
    SOURCE_MANIFEST as SOURCE_MANIFEST,
)
from legacy_common import (
    bootstrap as bootstrap,
)
from legacy_common import (
    digest as digest,
)
from legacy_common import (
    encoded as encoded,
)
from legacy_common import (
    lines as lines,
)
from legacy_common import (
    parity as parity,
)
from legacy_common import (
    read as read,
)
from legacy_common import (
    replace as replace,
)
from legacy_common import (
    safe_file as safe_file,
)
from legacy_common import (
    save as save,
)
from legacy_common import (
    sha as sha,
)

NAME = "torch-partial-ann-v1-settings-fix"
PREFIX = "reviews-partial-ann-v1-settings-fix-"
VERSION = "partial-ann.v1.settings-fix"
DESIGN_SHA = "7a59792f2db41a4c88095231c1682695ab8a112943112bb2c82d774f22dbefcb"
ADDENDUM_SHA = "dc9766f761dd3eb2a69f84e0ec1ba3abbc8814454bea6091bdebab61730e491a"
CORRECTION_SHA = "fe1f8a76b32977e7cd47d1bb569da9ef3e7d90a63e1a517db511a7fa00c989e1"
CELLS = ["native640", "partial640"]
MODES = tuple(CELLS)
FILTERS = ["votes108"]
INDEX = "reviews_hnsw_votes108_v1"
SEED = 20261026
CRITERIA = dict(
    aa_absolute_ms=0.10,
    aa_ratio=1.02,
    minimum_saving_ms=0.10,
    maximum_ratio_for_benefit=0.98,
    development_recall_reserve=0.0025,
    final_recall_margin_diagnostic_only=0.005,
    minimum_reference_recall=0.95,
    bootstrap_samples=10000,
    bootstrap_seed=20261019,
    benefit_upper_quantile=0.99375,
)
COUNTS = dict(
    allocations=1,
    temporal_blocks=2,
    vectors=200,
    cases=200,
    qualification_searches=10,
    preview_vectors=24,
    preview_searches=192,
    futility_stop_searches=202,
    reference_searches=600,
    quality_stop_searches=802,
    slots_per_block=1600,
    retained_executions_per_block=3200,
    discarded_warmups_per_block=1600,
    conditioning_searches_per_block=3200,
    timing_searches_per_block=8000,
    searches_total=16802,
    reader_admissions_quality_stop=4,
    reader_admissions_total=8,
    maximum_live_readers=6,
    aa_interval_checks=4,
    plan_packets=5700,
)
OPERATIONS = {
    "qualification_exact": 2,
    "qualification_native640": 4,
    "qualification_partial640": 4,
    "preview_conditioning": 48,
    "preview_warmup": 48,
    "preview_measurement": 96,
    "reference_exact": 200,
    "reference_native640": 200,
    "reference_partial640": 200,
    "conditioning": 6400,
    "warmup": 3200,
    "measurement": 6400,
}
STAGES = dict(
    restore=1200, build=1800, qualification_preview=600, quality=2400, formal=2400, final=600
)
SQL_CAPS = dict(observer=20000, truth_helper=4040, startup=1000)
MAX_SECONDS = 10200
INDEX_BYTES = 1012678656


def context(q):
    p = q.get("filter")
    if (
        type(q.get("k")) is not int
        or q["k"] != 10
        or not isinstance(p, dict)
        or set(p) != {"field", "op", "value"}
        or p["field"] != "m_000000"
        or p["op"] != "gte"
        or type(p["value"]) is not int
        or p["value"] != 108
    ):
        raise ValueError("Only the actual single m_000000>=108 predicate and k10 are supported")
    return "votes108"


def inventory(items):
    if len(items) != 200 or len({i["group"] for i in items}) != 200:
        raise ValueError("Requires exactly200 exposed vectors/selected cases")
    for i in items:
        if context(i["query"]) != "votes108" or i["query"]["id"] != i["group"] + "-votes108":
            raise ValueError("Selected query/group identity differs")
    return sorted(i["group"] for i in items)


def effective(origin, mode):
    if mode not in MODES:
        raise ValueError("Unsupported fixed reader mode")
    out = copy.deepcopy(origin)
    out["settings"]["hnsw.ef_search"] = "640"
    return out


def protocol():
    return dict(
        name=NAME,
        design_sha256=DESIGN_SHA,
        implementation_addendum_sha256=ADDENDUM_SHA,
        cells=CELLS,
        reader_modes=list(MODES),
        selected_context="votes108",
        version=VERSION,
        settings_correction_sha256=CORRECTION_SHA,
        counts=COUNTS,
        operations=OPERATIONS,
        criteria=CRITERIA,
        stage_seconds=STAGES,
        sql_caps=SQL_CAPS,
        maximum_seconds=MAX_SECONDS,
        resources=dict(cpus=4, memory_gib=32, wall_hours=3),
        seed=SEED,
        source_manifest_sha256=SOURCE_MANIFEST,
        index_bytes_cap=INDEX_BYTES,
        provider_calls_allowed=0,
        confirmation_queries_allowed=0,
        new_fits_allowed=0,
        activation_qualification=False,
        independent_confirmation=False,
    )


def verify(package, bundle=None):
    p = Path(package)
    m = read(p / "manifest.json")
    if m["version"] != VERSION:
        raise ValueError("Package version differs")
    actual = {str(f.relative_to(p)) for f in p.rglob("*") if f.is_file()}
    if actual - set(m["files"]) - {"manifest.json", "submission-binding.json"}:
        raise ValueError("Unexpected package file")
    for n, h in m["files"].items():
        if sha(safe_file(p, n)) != h:
            raise ValueError("Package changed: " + n)
    cfg = read(p / "experiment.json")
    for k, v in protocol().items():
        if cfg.get(k) != v:
            raise ValueError("Contract differs: " + k)
    if sha(p / "frozen/manifest.json") != SOURCE_MANIFEST:
        raise ValueError("Frozen anchor differs")
    for n, h in read(p / "frozen/manifest.json")["files"].items():
        if sha(safe_file(p / "frozen", n)) != h:
            raise ValueError("Frozen source changed: " + n)
    for n, h in cfg["pinned_evidence_sha256"].items():
        if sha(safe_file(p, n)) != h:
            raise ValueError("Evidence differs: " + n)
    if sha(p / "DESIGN.md") != DESIGN_SHA or sha(p / "IMPLEMENTATION-ADDENDUM.md") != ADDENDUM_SHA:
        raise ValueError("Frozen B2d design/addendum differs")
    if sha(p / "SETTINGS-CORRECTION.md") != CORRECTION_SHA:
        raise ValueError("Settings correction design changed")
    items = lines(p / "queries.jsonl")
    if inventory(items) != cfg["development_groups"]:
        raise ValueError("Cohort differs")
    raw = [
        i
        for i in lines(p / "frozen/inputs/queries.jsonl")
        if i["query"].get("filter") == {"field": "m_000000", "op": "gte", "value": 108}
    ]
    if items != raw:
        raise ValueError("Selected input differs from frozen exposed inventory")
    from pa_measure import order_manifest

    if read(p / "order.json") != order_manifest(items):
        raise ValueError("Schedule differs")
    if (
        read(p / "origin-settings.json") != cfg["source_settings"]
        or cfg["source_settings"]["hnsw.ef_search"] != "320"
        or cfg["source_settings"]["hnsw.iterative_scan"] != "off"
    ):
        raise ValueError("Origin settings differ")
    if bundle is not None:
        bootstrap(p)
        from control import verify as oldverify

        oldverify(p / "frozen", Path(bundle))
    return cfg


def protected(package, sources):
    from legacy_common import protected as original

    result = original(Path(package), Path(sources))
    p = Path(package)
    cfg = read(p / "experiment.json")
    prior = p.parent / "torch-exact-topk-v1-catalog-fix"
    for n, h in read(p / "prior-corrected-manifest.json")["files"].items():
        if sha(safe_file(prior, n)) != h:
            raise ValueError("Corrected B2b source differs: " + n)
    if sha(prior / "manifest.json") != cfg["prior_corrected_manifest_sha256"]:
        raise ValueError("Corrected B2b seal differs")
    from pa_recovery import verify_failed

    result["failed_b2d"] = verify_failed(p, sources)
    result["corrected_exact_package"] = {"manifest_sha256": cfg["prior_corrected_manifest_sha256"]}
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
        raise ValueError("Campaign/submission/package/job identity differs")
    return name


class Budget:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.started = clock()
        self.deadline = self.started + MAX_SECONDS
        self.stage = None
        self.stage_end = self.deadline - 600
        self.calls = 0
        self.operations = Counter()
        self.sql = Counter()
        self.stages = []

    def enter(self, name):
        if name not in STAGES or any(s["name"] == name for s in self.stages):
            raise RuntimeError("Unknown/repeated stage")
        now = self.clock()
        end = min(now + STAGES[name], self.deadline - (0 if name == "final" else 600))
        if end <= now:
            raise RuntimeError("Work deadline exhausted")
        self.stage = name
        self.stage_end = end
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
            or self.calls >= COUNTS["searches_total"]
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
