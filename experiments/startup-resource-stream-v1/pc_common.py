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
NAME = "torch-startup-resource-stream-v1"
VERSION = "startup-resource.stream.v1"
PREFIX = "reviews-startup-resource-stream-v1-"
CONTRACT_SHA = "679dc806e903ee7d202e5851f2cc4ece889aaebf25d3a9c49e5771af29f558db"
if sha(HERE / "CONTRACT.json") != CONTRACT_SHA:
    raise ValueError("Frozen B2f contract changed")
CONTRACT = read(HERE / "CONTRACT.json")
RESOURCE_SHA = "a4120866fea72befae75e485bc05bc7265314eb64b85839e5436e4c480339b90"
RESOURCE_DESIGN_SHA = "fbe4ffbf95f983018ed112b778af637c39ff3fe807ac17176d84bbc66fbb5fc0"
if sha(HERE / "RESOURCE-CONTRACT.json") != RESOURCE_SHA:
    raise ValueError("Frozen resource contract changed")
RESOURCE = read(HERE / "RESOURCE-CONTRACT.json")
STREAM_SHA = "880700840f8cb12f7501fc7171f74c199815afb7d5b356e8f9a1d5369657e815"
STREAM_DESIGN_SHA = "6e7dc63adb305902c17e9604f3d7cf234b1c67faa531319f4bd848fbe1a4d48b"
if sha(HERE / "CORRECTION-DESIGN.json") != STREAM_SHA:
    raise ValueError("Frozen stream contract changed")
STREAM = read(HERE / "CORRECTION-DESIGN.json")
COUNTS = RESOURCE["counts"]
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
STAGES = RESOURCE["resources"]["stage_seconds"]
SQL_CAPS = RESOURCE["resources"]["sql_caps"]
OPERATIONS = {}


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
        resource_contract_sha256=RESOURCE_SHA,
        resource_design_sha256=RESOURCE_DESIGN_SHA,
        stream_contract_sha256=STREAM_SHA,
        stream_design_sha256=STREAM_DESIGN_SHA,
        identity_behavior="per-row-original-canonical-sha256-scoped-binding.v1",
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
        or sha(p / "RESOURCE-DESIGN.md") != RESOURCE_DESIGN_SHA
        or sha(p / "DESIGN.md") != STREAM_DESIGN_SHA
        or sha(p / "CORRECTION-DESIGN.json") != STREAM_SHA
        or sha(p / "B2F-DESIGN.md") != CONTRACT["design_sha256"]
        or sha(p / "RESOURCE-CONTRACT.json") != RESOURCE_SHA
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
    resource_pins = read(p / "RESOURCE-SOURCE-PINS.json")
    if set(resource_pins) != set(RESOURCE["source_files_sha256"]):
        raise ValueError("Resource source pin inventory changed")
    for name, entry in resource_pins.items():
        if (
            entry["sha256"] != RESOURCE["source_files_sha256"][name]
            or sha(safe_file(p, entry["file"])) != entry["sha256"]
        ):
            raise ValueError("Resource source evidence changed: " + name)
    pins = read(p / "STREAM-SOURCE-PINS.json")
    if set(pins) != set(STREAM["source_files_sha256"]):
        raise ValueError("Stream source inventory differs")
    for name, item in pins.items():
        if (
            item["sha256"] != STREAM["source_files_sha256"][name]
            or sha(safe_file(p, item["file"])) != item["sha256"]
        ):
            raise ValueError("Stream source evidence differs: " + name)
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
    failed_package = Path("/home/dar579/torch-partial-calibration-v1")
    failed_manifest = read(p / "prior-b2f-manifest.json")
    expected = "41b4e47890ee1134eabbd1836a628954e93ee91e7e7fafb29da63e4da68ae42a"
    if sha(failed_package / "manifest.json") != expected:
        raise ValueError("Failed B2f seal changed")
    for name, h in failed_manifest["files"].items():
        if sha(safe_file(failed_package, name)) != h:
            raise ValueError("Failed B2f package changed: " + name)
    binding = read(failed_package / "submission-binding.json")
    reservation = read(sources / ".torch-partial-calibration-v1-reservation.json")
    for record in (binding, reservation):
        if (
            Path(record["campaign"]).name
            != "reviews-partial-calibration-v1-20261027T155119Z.6rd0lmkp"
            or record["package_manifest_sha256"] != expected
        ):
            raise ValueError("Failed B2f binding/reservation changed")
    result["b2f_failed_seal"] = dict(
        manifest_sha256=expected, binding=binding, reservation=reservation
    )
    previous_launch = Path("/home/dar579/torch-partial-calibration-v1-launch-fix")
    launch_manifest = read(p / "prior-launch-fix-manifest.json")
    launch_sha = "d3ead68818508496a79427fcc624e6c00bc2bf75cfbd553309a315f90627a7c6"
    if sha(previous_launch / "manifest.json") != launch_sha:
        raise ValueError("Previous launcher seal changed")
    for n, h in launch_manifest["files"].items():
        if sha(safe_file(previous_launch, n)) != h:
            raise ValueError("Previous launcher package changed: " + n)
    old_binding = read(previous_launch / "submission-binding.json")
    old_reservation = read(sources / ".torch-partial-calibration-v1-launch-fix-reservation.json")
    for r in (old_binding, old_reservation):
        if (
            Path(r["campaign"]).name
            != "reviews-partial-calibration-v1-launch-fix-20261027T185901Z.98dd224c"
            or r["package_manifest_sha256"] != launch_sha
        ):
            raise ValueError("Previous launcher binding/reservation changed")
    result["previous_launcher_seal"] = dict(
        manifest_sha256=launch_sha, binding=old_binding, reservation=old_reservation
    )
    metadata_package = Path("/home/dar579/torch-partial-calibration-v1-metadata-fix")
    metadata_sha = "794db833de9306045caffbfeca43384f6b45171481bcbb1a21fb51213811615d"
    if sha(metadata_package / "manifest.json") != metadata_sha:
        raise ValueError("Previous metadata seal changed")
    for n, h in read(p / "prior-metadata-fix-manifest.json")["files"].items():
        if sha(safe_file(metadata_package, n)) != h:
            raise ValueError("Previous metadata package changed: " + n)
    binding = read(metadata_package / "submission-binding.json")
    reservation = read(sources / ".torch-partial-calibration-v1-metadata-fix-reservation.json")
    for record in (binding, reservation):
        if (
            Path(record["campaign"]).name
            != "reviews-partial-calibration-v1-metadata-fix-20261028T000153Z.y1p9092a"
            or record["package_manifest_sha256"] != metadata_sha
        ):
            raise ValueError("Previous metadata binding/reservation changed")
    result["previous_metadata_seal"] = dict(
        manifest_sha256=metadata_sha, binding=binding, reservation=reservation
    )
    previous = Path("/home/dar579/torch-startup-resource-v1")
    expected = "4212507e81abc053aa5045e09a8cb624b789ed0bad4e1e8d1bf69f82f31484d9"
    if sha(previous / "manifest.json") != expected:
        raise ValueError("Prior startup seal changed")
    for n, h in read(p / "prior-startup-manifest.json")["files"].items():
        if sha(safe_file(previous, n)) != h:
            raise ValueError("Prior startup package changed: " + n)
    binding = read(previous / "submission-binding.json")
    reservation = read(sources / ".torch-startup-resource-v1-reservation.json")
    for record in (binding, reservation):
        if (
            Path(record["campaign"]).name != "reviews-startup-resource-v1-20261028T020546Z.zdsnk75c"
            or record["package_manifest_sha256"] != expected
        ):
            raise ValueError("Prior startup binding/reservation changed")
    result["prior_startup_seal"] = dict(
        manifest_sha256=expected, binding=binding, reservation=reservation
    )
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
        self.deadline = self.started + 3000
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
        raise RuntimeError("ANN/exact searches prohibited by startup-only contract")

    def sql_reserve(self, category):
        self.check()
        if category not in SQL_CAPS or self.sql[category] >= SQL_CAPS[category]:
            raise RuntimeError("SQL ceiling exhausted: " + category)
        self.sql[category] += 1
