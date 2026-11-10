"""A2 image inventory only: never starts a database, loads a snapshot or submits work."""

import argparse
import contextlib
import hashlib
import json
import os
import platform
import signal
import sys
import time
from pathlib import Path

NAME = "torch-startup-attribution-image-preflight-v1"
PARENT = "065022eb9428e4a7607b1eafa5784855103e184b174b4b5ac5abd6389827b96a"
IMAGE = "7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a"
MAX_REPORT = 128 * 1024


def read_json(path):
    return json.loads(Path(path).read_text())


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def verify(root):
    root = Path(root).resolve()
    manifest = read_json(root / "manifest.json")
    names = manifest["files"]
    if len(names) > 256:
        raise ValueError("Capsule file ceiling")
    actual = set()
    total = 0
    for p in root.rglob("*"):
        if p.is_symlink():
            raise ValueError("No capsule symlinks")
        if p.is_file():
            actual.add(str(p.relative_to(root)))
            total += p.stat().st_size
    if actual != set(names) | {"manifest.json"} or total > 16 * 1024**2:
        raise ValueError("Capsule inventory/size differs")
    for n, expected in names.items():
        rel = Path(n)
        if rel.is_absolute() or ".." in rel.parts or file_sha(root / rel) != expected:
            raise ValueError("Capsule content differs: " + n)
    if file_sha(root / "PARENT-A1-MANIFEST.json") != PARENT:
        raise ValueError("A1 parent identity differs")
    parent = read_json(root / "PARENT-A1-MANIFEST.json")["files"]
    contract = read_json(root / "PROBE-CONTRACT.json")
    if contract["parent_A1_manifest_sha256"] != PARENT or contract["image_sha256"] != IMAGE:
        raise ValueError("Probe identity differs")
    if contract["native_handoff_released"] is not False or contract["searches"] != 0:
        raise ValueError("Probe is not a zero-search inventory")
    for n, expected in contract["reference_files_sha256"].items():
        if parent.get(n) != expected or file_sha(root / "reference" / n) != expected:
            raise ValueError("Original reference changed: " + n)
    return contract


class Meter:
    """Only source text and scalar counts; no process/cgroup/resource qualification."""

    def __init__(self):
        self.reads = self.bytes = self.calls = self.lines = 0

    @contextlib.contextmanager
    def charge(self):
        yield

    def read_file(self, path):
        self.reads += 1
        if self.reads > 128:
            raise RuntimeError("Source-read ceiling")
        with Path(path).open("rb") as handle:
            data = handle.read(65537)
        self.bytes += len(data)
        if len(data) > 65536 or self.bytes > 4 * 1024**2:
            raise RuntimeError("Source-byte ceiling")
        return data.decode("utf-8")

    def callback(self, line=False):
        self.calls += 1
        self.lines += int(line)
        if self.calls > 16:
            raise RuntimeError("Literal callback ceiling")


def compare(actual, reference):
    if set(actual) != set(reference):
        raise ValueError("Provenance field inventory differs")
    return {
        k: {"reference": reference[k], "actual": actual[k]}
        for k in actual
        if actual[k] != reference[k]
    }


@contextlib.contextmanager
def no_external_actions():
    """Defence in depth: all routes in this probe are inspection only."""
    import socket
    import subprocess

    import psycopg

    def blocked(*args, **kwargs):
        raise RuntimeError("Image inventory prohibits connections and child processes")

    targets = [
        (psycopg, "connect"),
        (psycopg.Connection, "connect"),
        (psycopg.AsyncConnection, "connect"),
        (socket, "socket"),
        (subprocess, "Popen"),
    ]
    originals = [(owner, name, owner.__dict__[name]) for owner, name in targets]
    try:
        for owner, name in targets:
            setattr(owner, name, blocked)
        yield
    finally:
        for owner, name, original in reversed(originals):
            setattr(owner, name, original)


def collect(root, report=None):
    report = report if report is not None else {}
    contract = verify(root)
    reference_dir = Path(root) / "reference"
    # These are the same staged original packages used by A1 and the proposed job.
    sys.path[:0] = [
        str(reference_dir),
        str(reference_dir / "frozen"),
        str(reference_dir / "frozen/vendor"),
    ]
    from no_models import enforce

    enforce()
    import numpy  # noqa: F401
    import psycopg  # noqa: F401
    import pyarrow

    with no_external_actions():
        from fannagent_pgvector.backend import NativeBackend
        from sa_driver import provenance
        from sa_monitor import EXPECTED, MAPS, SnapshotMonitor, idle, preflight

        from fannagent.snapshot import Snapshot

        meter = Meter()
        actual = provenance(meter.read_file)
        reference = read_json(reference_dir / "DRIVER-REFERENCE.json")
        differences = compare(actual, reference)
        report.update(actual_driver=actual, A1_reference_differences=differences)
        idle()
        monitor = SnapshotMonitor(NativeBackend.snapshot, Snapshot.__init__, meter)
        monitor.validate()
        for tool in range(6):
            if any(sys.monitoring.get_local_events(tool, c) for c in monitor.codes):
                raise RuntimeError("Pre-existing original local masks")
        literal = preflight(meter)
        idle()
        pool = pyarrow.default_memory_pool()
        live, backend = pool.bytes_allocated(), pool.backend_name
        if type(live) is not int or live < 0 or not isinstance(backend, str) or not backend:
            raise RuntimeError("Arrow default-pool capability unavailable")
        report.update(
            schema="startup-attribution.image-inventory.v1",
            status="inventory_complete_reference_mismatch"
            if differences
            else "inventory_complete_reference_match",
            actual_driver=actual,
            A1_reference_differences=differences,
            original_function_mapping=dict(
                source_sha256=list(EXPECTED),
                qualified_names=[f.__module__ + "." + f.__qualname__ for f in monitor.functions],
                mapped_lines=[sorted(m) for m in MAPS],
                original_bindings_unchanged=tuple(f.__code__ for f in monitor.functions)
                == monitor.codes,
                local_masks_clear=True,
            ),
            literal_monitoring=literal,
            arrow_default_pool=dict(
                live_bytes=live, backend=backend, high_water_bytes=pool.max_memory()
            ),
            accounting=dict(
                source_reads=meter.reads, source_bytes=meter.bytes, literal_callbacks=meter.calls
            ),
            native_handoff_released=False,
            allocation_qualification=False,
            resource_margin_qualification=False,
            cgroup_capability="not measured by this image-only inventory",
            searches=0,
            snapshot_calls=0,
            database_connections=0,
            SQL=0,
            slurm_submissions=0,
            provider_calls=0,
            limits=contract["limits"],
        )
        return report


def limits():
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (128 * 1024, 128 * 1024))

    def timeout(number, frame):
        raise TimeoutError("Image-only inventory wall deadline")

    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(30)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["verify", "inspect"])
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    if args.command == "verify":
        verify(root)
        print("Image-only capsule verified; no job or database action")
        return
    started = time.monotonic()
    report = {}
    code = 1
    try:
        if platform.system() != "Linux" or platform.machine() != "x86_64":
            raise RuntimeError("Inspect inside the unchanged x86_64 Torch image")
        if os.environ.get("SA_VERIFIED_IMAGE_SHA256") != IMAGE:
            raise RuntimeError("Use the checksum-verifying host wrapper")
        limits()
        report = collect(root, report)
        code = 0
    except BaseException as error:
        report.update(
            schema="startup-attribution.image-inventory.v1",
            status="inventory_incomplete",
            error_type=type(error).__name__,
            error=str(error)[:2048],
            native_handoff_released=False,
        )
    finally:
        signal.alarm(0)
    report.update(
        image_sha256=IMAGE,
        parent_A1_manifest_sha256=PARENT,
        capsule_manifest_sha256=file_sha(root / "manifest.json"),
        elapsed_seconds=time.monotonic() - started,
    )
    raw = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    if len(raw.encode()) > MAX_REPORT:
        raise RuntimeError("Image inventory report ceiling")
    print(raw)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
