from __future__ import annotations

from typing import Final

from .data import DatasetManifest, Query
from .errors import ValidationError

PORTABLE_PROFILE: Final = "portable_fann_v2"
PORTABLE_PROFILE_VERSION: Final = 2
MIN_DIMENSION: Final = 1
MAX_DIMENSION: Final = 2_000
MIN_K: Final = 1
MAX_K: Final = 100
MAX_FILTER_DEPTH: Final = 16
MAX_FILTER_LEAVES: Final = 128
MAX_MEMBERSHIP_VALUES: Final = 128
MAX_STRING_BYTES: Final = 4_096


def validate_portable_manifest(manifest: DatasetManifest) -> None:
    """Validate the dataset-independent portion of the common engine contract."""

    if manifest.metric != "cosine":
        raise ValidationError(f"{PORTABLE_PROFILE} requires cosine distance")
    if not manifest.normalized:
        raise ValidationError(f"{PORTABLE_PROFILE} requires normalized vectors")
    if not MIN_DIMENSION <= manifest.dimension <= MAX_DIMENSION:
        raise ValidationError(
            f"{PORTABLE_PROFILE} requires dimensions in "
            f"[{MIN_DIMENSION}, {MAX_DIMENSION}], got {manifest.dimension}"
        )


def validate_portable_query(query: Query) -> None:
    def has_null(node: object) -> bool:
        if isinstance(node, dict):
            return node.get("op") in {"is_null", "is_not_null"} or any(
                has_null(v) for v in node.values()
            )
        return isinstance(node, list) and any(has_null(v) for v in node)

    if query.schema_version == 1 and has_null(query.filter):
        raise ValidationError("null predicates require query schema version 2")
    if not MIN_K <= query.k <= MAX_K:
        raise ValidationError(f"{PORTABLE_PROFILE} requires k in [{MIN_K}, {MAX_K}], got {query.k}")
