"""Frozen hindsight experiment; no model, learner or policy-selection interface."""

import hashlib
import json
import math

FILTERS = (-1, 743, 527, 310, 192, 108, 32)
FAMILIES = ("native", "oracle", "matched", "empty")
SEED = "reviews-full-workload-oracle-v1-20261117"
MAX_ATTEMPTS = 2_000_000
MAX_CHECKPOINTS = 4096
PACKAGE_SHA = "b596c69bbab0bb49d720df02b820e5a9f2c1652a47e67b6b327f16f8769663bc"
IMAGE = "7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def group(qid):
    return qid.rsplit("-", 1)[0]


def qualifies(output, recall, native_output, native_recall):
    # Preserve result count even when the original ANN answer is short.
    return len(output) >= len(native_output) and recall + 1e-12 >= native_recall


def validate_output(output, eligible, truth):
    require(len(output) <= min(10, len(eligible)), "oversized answer")
    require(len({i for i, _ in output}) == len(output), "duplicate IDs")
    require(
        all(i in eligible and math.isfinite(d) and -1e-6 <= d <= 2.000001 for i, d in output),
        "invalid ID/distance",
    )
    require(len(truth) >= min(10, len(eligible)), "incomplete exact reference")
    if not eligible:
        return 1.0
    boundary = max(d for _, d in truth)
    return sum(d <= boundary + 1e-6 for _, d in output) / min(10, len(eligible))


def ordered(cases, rotation, cycle):
    rows = sorted(
        cases,
        key=lambda q: hashlib.sha256(f"{SEED}:{rotation}:{group(q['id'])}".encode()).digest(),
    )
    return rows[::-1] if cycle else rows


def reader_order(position, rotation, cycle, filter_index):
    order = [(r + position + rotation + filter_index) % 4 for r in (0, 1, 3, 2)]
    return order[::-1] if cycle else order


def schedule(cases, filter_index):
    """Each PID runs each family twice, mirrored in the second cycle."""
    for cycle in (0, 1):
        for rotation in range(4) if not cycle else reversed(range(4)):
            for position, q in enumerate(ordered(cases, rotation, cycle)):
                for reader in reader_order(position, rotation, cycle, filter_index):
                    yield cycle, rotation, reader, FAMILIES[(reader + rotation) % 4], q


def prefix_signature(states):
    keys = ("index", "target", "actual_layer0_distances", "features")
    return [{key: states[i][key] for key in keys} for i in sorted(states)]


def prefix_chain(signature):
    """Compact comparable identities of the canonical and actually executed prefixes."""
    previous = b""
    result = []
    for state in signature:
        previous = hashlib.sha256(
            previous + json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
        ).digest()
        result.append(previous.hex())
    return result
