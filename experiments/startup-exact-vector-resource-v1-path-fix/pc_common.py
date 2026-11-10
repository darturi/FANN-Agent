"""Pinned B2f contract, durable helpers and finite operation reservations."""

import re
import time
from collections import Counter
from pathlib import Path

from legacy_common import (  # noqa: F401
    PROFILE_SHA,
    SOURCE_MANIFEST,
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
from legacy_common import (
    bootstrap as legacy_bootstrap,
)

HERE = Path(__file__).resolve().parent
NAME = "torch-startup-exact-vector-resource-v1"
VERSION = "startup-exact-vector.resource.v1"
PREFIX = "reviews-startup-exact-vector-resource-v1-"
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
RESOURCE_FREEZE_SHA = "1276241332fffd1fbd76b7c8fc67fddf9ea47977a6372fca6b5d5c4e9a67c042"
RESOURCE_AMENDMENT_SHA = "cb01d50a80ac563cde330ee4ac1905ce9c8536e8ee56a504f450e80b6e80315d"
PATH_FIX_SHA = "fcc616e56485b98dee60de46df063f5d3d4f8e0e60aa14173771139dadc482ee"
RETAINED_MAIN = Path("/home/dar579/torch-startup-attribution-v1-image-reference")


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
        identity_behavior="packed-binary64-integer-tags-original-canonical.v1",
        resource_freeze_sha256=RESOURCE_FREEZE_SHA,
        resource_amendment_sha256=RESOURCE_AMENDMENT_SHA,
        resource_path_fix_sha256=PATH_FIX_SHA,
        native_handoff_released=True,
        stage_seconds=STAGES,
        sql_caps=SQL_CAPS,
        provider_calls_allowed=0,
        confirmation_queries_allowed=0,
        new_fits_allowed=0,
        activation_qualification=False,
        treatment_economics_qualification=False,
    )


def verify_scientific(package, bundle=None):
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
        legacy_bootstrap(p)
        from control import verify as baseverify

        baseverify(p / "frozen", Path(bundle))
    return cfg


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
        self.deadline = min(
            self.started + 3000, float(__import__("os").environ.get("EV_RUNTIME_DEADLINE", "inf"))
        )
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


def verify(package, bundle=None):
    """Check the complete new seal and every original reference/scientific file."""
    p = Path(package)
    if p.is_symlink() or any(f.is_symlink() for f in p.rglob("*")):
        raise ValueError("Resource package symlink prohibited")
    manifest = read(p / "manifest.json")
    actual = {str(f.relative_to(p)) for f in p.rglob("*") if f.is_file()}
    allowed = {"manifest.json"}
    if (p / "submission-binding.json").exists():
        binding = read(p / "submission-binding.json")
        campaign = Path(binding["campaign"])
        if (
            set(binding) != {"campaign", "package_manifest_sha256"}
            or binding["package_manifest_sha256"] != sha(p / "manifest.json")
            or campaign.parent != Path("/home/dar579/torch-reviews-results")
            or not re.fullmatch(
                re.escape(PREFIX) + r"[0-9]{8}T[0-9]{6}Z\.[A-Za-z0-9_-]+", campaign.name
            )
        ):
            raise ValueError("Resource binding differs")
        allowed.add("submission-binding.json")
    if actual != set(manifest["files"]) | allowed:
        raise ValueError("Resource package inventory differs")
    cfg = verify_scientific(p, bundle)
    if sha(p / "RESOURCE-FREEZE.json") != RESOURCE_FREEZE_SHA:
        raise ValueError("Pre-code resource freeze changed")
    if sha(p / "RESOURCE-AMENDMENT-1.json") != RESOURCE_AMENDMENT_SHA:
        raise ValueError("Pre-code bounded metadata adapter amendment changed")
    if sha(p / "PATH-FIX-FREEZE.json") != PATH_FIX_SHA:
        raise ValueError("Frozen resource protection-context correction changed")
    freeze = read(p / "RESOURCE-FREEZE.json")
    ref = p / "reference"
    if sha(ref / "manifest.json") != freeze["baseline"]["reference_manifest_sha256"]:
        raise ValueError("Original main reference manifest differs")
    expected = freeze["baseline"]["reference_files_sha256"]
    if read(ref / "manifest.json")["files"] != expected:
        raise ValueError("Original main reference inventory differs")
    if {str(f.relative_to(ref)) for f in ref.rglob("*") if f.is_file()} != set(expected) | {
        "manifest.json"
    }:
        raise ValueError("Original main reference has unexpected files")
    for name, value in expected.items():
        if sha(safe_file(ref, name)) != value:
            raise ValueError("Original main reference changed: " + name)
    for name, expected_hash in freeze["qualified_native_correctness"]["code_sha256"].items():
        if sha(p / "a3" / name) != expected_hash:
            raise ValueError("Qualified A3 code changed: " + name)
    # Native producer/constructor/eligibility inputs remain the original values.
    for name in (
        "CONTRACT.json",
        "RESOURCE-CONTRACT.json",
        "SCHEDULE.json",
        "origin-source.json",
        "origin-settings.json",
        "DRIVER-HOOKS.json",
        "DRIVER-REFERENCE.json",
        "IMAGE-REFERENCE.json",
        "b2d-catalogs.json",
        "SOURCE-PINS.json",
        "RESOURCE-SOURCE-PINS.json",
        "STREAM-SOURCE-PINS.json",
    ):
        if sha(p / name) != sha(ref / name):
            raise ValueError("Scientific input differs: " + name)
    if not cfg["synthetic_fixture"]:
        for name in ("eligibility.json", "queries.jsonl"):
            if sha(p / name) != sha(ref / name):
                raise ValueError("Native cohort/eligibility changed")
        if cfg["snapshot_identity"] != read(ref / "experiment.json")["snapshot_identity"]:
            raise ValueError("Native snapshot identity changed")
    validate_native_proofs(p)
    return cfg


def validate_native_proofs(package):
    """Login-safe, stdlib-only proof checks; guest also uses unchanged native_spec."""
    p = Path(package)
    freeze = read(p / "RESOURCE-FREEZE.json")
    qualified = freeze["qualified_native_correctness"]
    audit = read(p / "QUALIFICATION-AUDIT.json")
    release = read(p / "NATIVE-RELEASE.json")
    hashes = {name: sha(p / "a3" / name) for name in qualified["code_sha256"]}
    scope = dict(
        allocations=1,
        wall_seconds=3600,
        physical_cpus=4,
        memory_gib=32,
        ANN_searches=0,
        exact_searches=0,
        snapshot_scans=1,
        data_verification_scans=4,
        reserve_bytes=2 * 1024**3,
        workspace_bytes=2 * 1024**3,
        positive_limit_events_allowed=False,
        cache_subtraction=False,
    )
    if (
        hashes != qualified["code_sha256"]
        or release["schema"] != "startup-exact-vector.resource-release.v1"
        or release["name"] != NAME
        or release["scope"] != scope
        or release["code_sha256"] != hashes
        or release["integration_tests"] != 56
        or release["full_B2f_released"] is not False
        or release["qualification_audit_sha256"] != sha(p / "QUALIFICATION-AUDIT.json")
        or audit["code_sha256"] != hashes
        or audit["status"] != "pass"
        or audit["job_id"] != "21470341"
        or not audit["final_integrity_verified"]
        or not audit["guard_bindings_restored"]
        or audit["denied_actions"] != 0
        or audit["native_resource_released"] is not False
        or audit["full_B2f_released"] is not False
        or audit["image_sha256"] != CONTRACT["runtime"]["image_sha256"]
    ):
        raise ValueError("Authentic native qualification/release scope differs")
    for name, expected in qualified["proof_packet_sha256"].items():
        if sha(p / name) != expected:
            raise ValueError("Authentic native receipt changed: " + name)
    phases = {
        f"{kind}-{phase}.json": sha(p / f"{kind}-{phase}.json")
        for kind in ("main", "integration")
        for phase in ("source", "sealed")
    }
    if phases != audit["phase_receipts_sha256"]:
        raise ValueError("Native phase audit differs")
    target = read(p / "reference/IMAGE-REFERENCE.json")
    recipes = {
        name: sha(p / "reference" / name)
        for name in read(p / "reference/RECIPE-FILES.json")["files"]
    }
    for name in phases:
        receipt = read(p / name)
        integration = name.startswith("integration-")
        if (
            receipt["status"] != "pass"
            or receipt["python"] != "3.12.15"
            or receipt["tests_run"] != (56 if integration else 128)
            or receipt["actual_provenance"] != target
            or receipt["failures"]
            or receipt["errors"]
        ):
            raise ValueError("Complete exact-target suite required")
        if integration:
            if (
                receipt["source_files_sha256"] != hashes
                or receipt["denied_actions"]
                or receipt["skipped"]
                or not receipt["source_stable"]
            ):
                raise ValueError("Integrated target case/code proof differs")
        elif receipt["recipe_files_sha256"] != recipes:
            raise ValueError("All 128 original-case recipes required")
    return release


def require_native_release(package):
    import ast

    p = Path(package)
    cfg = verify(p)
    if cfg["synthetic_fixture"] or cfg["local_readiness"] != "source_and_target_checks_passed":
        raise RuntimeError("Synthetic/unqualified resource package cannot launch")
    code = {f.name: sha(f) for f in p.glob("*.py")}
    expected = set()
    for module in ("test_memory", "test_resource", "test_host_resource"):
        for node in ast.parse((p / (module + ".py")).read_text()).body:
            if isinstance(node, ast.ClassDef):
                expected.update(
                    module + "." + node.name + "." + method.name
                    for method in node.body
                    if isinstance(method, ast.FunctionDef) and method.name.startswith("test_")
                )
    if not expected:
        raise RuntimeError("Complete explicit resource case inventory required")
    for filename, phase in (("LOCAL_CHECKS.json", "source"), ("SEALED_CHECKS.json", "sealed")):
        checks = read(p / filename)
        if (
            checks["status"] != "pass"
            or checks["phase"] != phase
            or checks["source_files_sha256"] != code
            or checks["errors"]
            or checks["failures"]
            or checks["skipped"]
            or checks["denied_actions"]
            or checks["source_stable"] is not True
            or checks["module_origins_verified"] is not True
            or checks["tests_run"] != checks["expected_tests"]
            or checks["tests_run"] != len(expected)
            or set(checks["test_ids"]) != expected
            or len(checks["test_ids"]) != len(expected)
        ):
            raise RuntimeError("Current complete guarded source and sealed harness checks required")
    return cfg


def bootstrap(package):
    legacy_bootstrap(package)
    from ev_startup import configure

    configure(Path(package))


def original_protection(reference, retained_main, sources):
    """Use verified original code with its original sibling-package context."""
    import importlib.util
    import sys

    before = list(sys.path)
    try:
        spec = importlib.util.spec_from_file_location(
            "ev_original_common", Path(reference) / "pc_common.py"
        )
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        return original.protected(Path(retained_main), Path(sources))
    finally:
        # Historical bootstrap must not select old helpers for the new caller.
        sys.path[:] = before


def protect_entry(key, entry, sources):
    directory = Path(entry["directory"])
    for name, expected in entry["files_sha256"].items():
        if sha(safe_file(directory, name)) != expected:
            raise ValueError("Completed evidence changed: " + key + "/" + name)
    if "binding" in entry:
        binding = read(directory / "submission-binding.json")
        reservation = read(Path(sources) / entry["reservation_name"])
        for value in (binding, reservation):
            if any(value.get(k) != v for k, v in entry["binding"].items()):
                raise ValueError("Spent binding/reservation differs: " + key)


def protected(package, sources):
    """Keep every original guard, anchored to the preserved main home package."""
    p, sources = Path(package), Path(sources)
    ref = p / "reference"
    additions = read(p / "PROTECTED-ADDITIONS.json")
    main = additions["completed_main_A2"]
    manifest_sha = sha(ref / "manifest.json")
    if (
        Path(main["directory"]) != RETAINED_MAIN
        or manifest_sha != read(p / "RESOURCE-FREEZE.json")["baseline"]["reference_manifest_sha256"]
        or main["files_sha256"]
        != {**read(ref / "manifest.json")["files"], "manifest.json": manifest_sha}
        or main["binding"]["package_manifest_sha256"] != manifest_sha
        or main["reservation_name"] != ".torch-startup-attribution-v1-reservation.json"
    ):
        raise ValueError("Pinned original main protection context differs")
    # Verify every original main byte and its spent binding before bootstrap can
    # import from that tree. This also avoids duplicate verification below.
    protect_entry("completed_main_A2", main, sources)
    result = original_protection(ref, RETAINED_MAIN, sources)
    result["completed_main_A2"] = main
    for key, entry in additions.items():
        if key == "completed_main_A2":
            continue
        protect_entry(key, entry, sources)
        result[key] = entry
    return result
