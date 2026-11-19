import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from canonical_features import cosine_projection  # noqa: E402


def test_raw_float_roundoff_uses_the_native_cosine_projection():
    assert cosine_projection(-(2**-23)) == 0.0
    assert cosine_projection(2 + 2**-23) == 2.0
    assert cosine_projection(0.375) == 0.375
    assert cosine_projection(None) is None


@pytest.mark.parametrize("raw", [math.inf, -math.inf, math.nan, -0.1, 2.1])
def test_projection_cannot_hide_invalid_or_misaligned_features(raw):
    with pytest.raises(ValueError):
        cosine_projection(raw)
