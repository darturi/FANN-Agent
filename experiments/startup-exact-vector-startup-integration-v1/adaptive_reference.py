"""Exact static image references and bounded pre-restore codec parity."""

import hashlib
import inspect
import json
import struct
import sys
import time
from pathlib import Path

FREEZE_SHA = "2e31c4cedebfc844e30d137c6042e5f30cfd44b7d16d7488d51daa7721b7f91b"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def static(package):
    p = Path(package)
    if sha(p / "STARTUP-FREEZE.json") != FREEZE_SHA:
        raise RuntimeError("Prospective startup freeze differs")
    freeze = json.loads((p / "STARTUP-FREEZE.json").read_text())
    if sha(p / "TARGET-REFERENCE.json") != freeze["target_reference_sha256"]:
        raise RuntimeError("Static exact-image reference differs")
    target = json.loads((p / "TARGET-REFERENCE.json").read_text())
    image = json.loads((p / "reference/IMAGE-REFERENCE.json").read_text())
    formatter = json.loads((p / "FORMATTER-AMENDMENT.json").read_text())["formatter"]
    if (
        image != target["target_reference"]
        or image["python"] != "3.12.15"
        or image["numpy"] != "2.5.3"
        or target["target_formatter_module_sha256"] != formatter["module_source_sha256"]
        or target["image_sha256"]
        != "7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a"
        or target["image_config_sha256"]
        != "ea7083a544d105d589ac1a3915b7ab8425fe1e867f2afc3ceaf99f0a9a48967f"
    ):
        raise RuntimeError("Target image/interpreter/formatter pins disagree")
    return target


def require_actual(package, actual, profile):
    p = Path(package)
    target = static(p)
    if profile not in ("local", "target"):
        raise RuntimeError("Explicit local or exact target reference required")
    expected = (
        target["target_reference"]
        if profile == "target"
        else json.loads((p / "reference/DRIVER-REFERENCE.json").read_text())
    )
    if actual != expected:
        raise RuntimeError("Exact " + profile + " interpreter/private-hook/library mismatch")
    import exact_codec as codec
    import numpy as np

    reference = json.loads((p / "FORMATTER-AMENDMENT.json").read_text())["formatter"]
    codec._guard_formatter()
    if (
        np.__version__ != reference["numpy"]
        or sha(inspect.getsourcefile(codec._FORMAT)) != reference["module_source_sha256"]
        or hashlib.sha256(inspect.getsource(codec._FORMAT).encode()).hexdigest()
        != reference["function_source_sha256"]
    ):
        raise RuntimeError("Effective formatter differs from exact image source")
    return profile


def literal_preflight(package):
    import exact_codec as codec
    import exact_vector as original
    import numpy as np

    from fannagent.store import canonical

    started = time.process_time()
    codec.verify_sources()
    cases = [
        [1, -0.0, 1.0],
        [0.1, -0.25],
        [1.0 + 2**-30],
        [5e-324, -5e-324],
        [2**100 + 1],
        [sys.float_info.max],
        [1e-45],
        [10**20, 1e20],
    ]
    total = compact = raw = 0
    for head in cases:
        values = head + [0.0] * (768 - len(head))
        old = original.PackedVector.from_values(values)
        new = codec.ExactVector.from_values(values)
        if struct.pack("<768d", *new) != old._payload or canonical(new.to_list()) != canonical(
            values
        ):
            raise RuntimeError("Pre-restore exact codec/canonical parity failed")
        with np.errstate(over="ignore", under="ignore", invalid="ignore"):
            if not np.array_equal(
                np.asarray(old, dtype=np.float32).view(np.uint32),
                np.asarray(new, dtype=np.float32).view(np.uint32),
            ):
                raise RuntimeError("Pre-restore float32 matrix bits differ")
        total += len(old._payload)
        compact += int(new.compact)
        raw += int(not new.compact)
    elapsed = time.process_time() - started
    if elapsed > 1:
        raise RuntimeError("Codec literal preflight CPU cap")
    return dict(
        status="pass",
        cases=8,
        compact_cases=compact,
        raw64_cases=raw,
        original_numeric_bytes=total,
        cpu_seconds=elapsed,
        codec_sha256=sha(Path(package) / "exact_codec.py"),
        helper_sha256=sha(Path(package) / "adaptive_reference.py"),
        target_reference_sha256=sha(Path(package) / "TARGET-REFERENCE.json"),
        ANN_searches=0,
        exact_searches=0,
        real_SQL=0,
    )
