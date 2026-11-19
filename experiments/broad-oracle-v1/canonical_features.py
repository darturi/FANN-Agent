"""Project raw canonical cosine telemetry into the existing native v3 contract."""

import math


def cosine_projection(raw):
    if raw is None:
        return None
    if not math.isfinite(raw):
        raise ValueError("nonfinite canonical cosine feature")
    projected = max(0.0, min(2.0, raw))
    # The canonical logger keeps 1 + negative inner product unbounded; the v3
    # collector has always clamped it. Allow only qualified floating roundoff,
    # never a scale, checkpoint or queue-order mismatch.
    if abs(projected - raw) > 1e-6:
        raise ValueError("canonical cosine exceeds the qualified roundoff envelope")
    return projected
