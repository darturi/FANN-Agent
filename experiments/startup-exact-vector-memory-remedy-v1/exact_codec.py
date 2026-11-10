"""Exact adaptive binary32/raw64 component; no native producer or launch entry."""

from __future__ import annotations

import hashlib
import inspect
import struct
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

import exact_vector as original
import numpy as np

HERE = Path(__file__).resolve().parent
FREEZE_SHA = "2f7107f50b6661d5e5c53318c236e94897387807f87ebab53e123a4a415bfbd7"
FORMAT_REFERENCE_SHA = "f50a6864a4984f500dba2d47cf15039c4419bfe009b7eb1b9a8a3214e68da199"
DIMENSION = 768
FORMAT_NUMPY_VERSION = "2.5.3"
_FORMAT = np.format_float_positional


def verify_sources():
    import json

    freeze_file = HERE / "MEMORY-FREEZE.json"
    if hashlib.sha256(freeze_file.read_bytes()).hexdigest() != FREEZE_SHA:
        raise RuntimeError("Prospective memory freeze changed")
    freeze = json.loads(freeze_file.read_text())
    amendment_file = HERE / "FORMATTER-AMENDMENT.json"
    if hashlib.sha256(amendment_file.read_bytes()).hexdigest() != FORMAT_REFERENCE_SHA:
        raise RuntimeError("Prospective formatter amendment changed")
    amendment = json.loads(amendment_file.read_text())
    if amendment["parent_freeze_sha256"] != FREEZE_SHA:
        raise RuntimeError("Formatter amendment parent differs")
    for name, value in freeze["baseline_files_sha256"].items():
        path = HERE / "baseline" / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != value:
            raise RuntimeError("Original A3 source/test changed: " + name)
    if Path(original.__file__).resolve() != HERE / "baseline/exact_vector.py":
        raise RuntimeError("Original vector module origin differs")
    ref = amendment["formatter"]
    if (
        np.__version__ != ref["numpy"]
        or hashlib.sha256(inspect.getsource(_FORMAT).encode()).hexdigest()
        != ref["function_source_sha256"]
        or hashlib.sha256(Path(inspect.getsourcefile(_FORMAT)).read_bytes()).hexdigest()
        != ref["module_source_sha256"]
    ):
        raise RuntimeError("Pinned shortest formatter provenance differs")
    _guard_formatter()
    original.verify_sources()
    return {**freeze, "effective_formatter": ref}


def _guard_formatter():
    if np.format_float_positional is not _FORMAT or np.__version__ != FORMAT_NUMPY_VERSION:
        raise RuntimeError("Shortest formatter binding/version changed")


def _decode32(value):
    return float(_FORMAT(value, unique=True, trim="-"))


@dataclass(frozen=True, slots=True, eq=False)
class ExactVector(Sequence):
    """Three slots, two fixed payload lengths, exact original integer categories."""

    _payload: bytes
    _integer_mask: int
    _integers: tuple[int, ...]

    def __post_init__(self):
        _guard_formatter()
        if (
            type(self._payload) is not bytes
            or len(self._payload) not in (DIMENSION * 4, DIMENSION * 8)
            or type(self._integer_mask) is not int
            or not 0 <= self._integer_mask < 1 << DIMENSION
            or type(self._integers) is not tuple
            or any(type(v) is not int for v in self._integers)
            or self._integer_mask.bit_count() != len(self._integers)
        ):
            raise ValueError("Exact vector structure differs")
        if not self.compact:
            original.PackedVector(self._payload, self._integer_mask, self._integers)
            return
        data = np.frombuffer(self._payload, dtype="<f4")
        if not np.isfinite(data).all():
            raise ValueError("Nonfinite compact payload")
        rank = 0
        for i in range(DIMENSION):
            if self._integer_mask & (1 << i):
                if struct.pack("<d", float(self._integers[rank])) != struct.pack(
                    "<d", _decode32(data[i])
                ):
                    raise ValueError("Integer category/value and compact buffer differ")
                rank += 1

    @property
    def compact(self):
        return len(self._payload) == DIMENSION * 4

    @classmethod
    def from_values(cls, values):
        return cls.from_original(original.PackedVector.from_values(values))

    @classmethod
    def from_original(cls, value):
        _guard_formatter()
        if type(value) is not original.PackedVector:
            raise ValueError("Pinned original packed vector required")
        with np.errstate(over="ignore", under="ignore", invalid="ignore"):
            data = value.__array__(dtype=np.float32)
        compact = bool(np.isfinite(data).all())
        if compact:
            for i in range(DIMENSION):
                if struct.pack("<d", _decode32(data[i])) != value._payload[i * 8 : i * 8 + 8]:
                    compact = False
                    break
        payload = data.astype("<f4", copy=False).tobytes() if compact else value._payload
        return cls(payload, value._integer_mask, value._integers)

    def __len__(self):
        return DIMENSION

    def __getitem__(self, index):
        _guard_formatter()
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(DIMENSION))]
        if not isinstance(index, int):
            raise TypeError("Integer or slice required")
        if index < 0:
            index += DIMENSION
        if not 0 <= index < DIMENSION:
            raise IndexError(index)
        if self._integer_mask & (1 << index):
            rank = (self._integer_mask & ((1 << index) - 1)).bit_count()
            return self._integers[rank]
        if self.compact:
            return _decode32(np.frombuffer(self._payload, dtype="<f4")[index])
        return struct.unpack_from("<d", self._payload, index * 8)[0]

    def __iter__(self) -> Iterator[int | float]:
        _guard_formatter()
        values = (
            (_decode32(n) for n in np.frombuffer(self._payload, dtype="<f4"))
            if self.compact
            else (n for (n,) in struct.iter_unpack("<d", self._payload))
        )
        rank = 0
        for i, value in enumerate(values):
            if self._integer_mask & (1 << i):
                yield self._integers[rank]
                rank += 1
            else:
                yield value

    def __array__(self, dtype=None, copy=None):
        _guard_formatter()
        if not self.compact:
            result = np.frombuffer(self._payload, dtype="<f8")
            if dtype is not None and np.dtype(dtype) != result.dtype:
                if copy is False:
                    raise ValueError("Requested dtype requires a copy")
                result = result.astype(dtype)
            elif copy:
                result = result.copy()
            return result
        requested = np.dtype("<f8") if dtype is None else np.dtype(dtype)
        if requested == np.dtype("<f4"):
            view = np.frombuffer(self._payload, dtype="<f4")
            return view.copy() if copy else view
        if copy is False:
            raise ValueError("Requested dtype requires exact reconstruction/copy")
        values = np.fromiter((float(v) for v in self), dtype="<f8", count=DIMENSION)
        if requested != values.dtype:
            return values.astype(requested)
        if copy:
            return values
        values.setflags(write=False)
        return values

    def to_list(self):
        return list(self)


def pack_json_vector(text):
    return ExactVector.from_original(original.pack_json_vector(text))


def plain_row(row):
    if (
        type(row) is not dict
        or set(row) != {"source_id", "vector", "metadata"}
        or type(row["vector"]) is not ExactVector
        or type(row["source_id"]) not in (int, str)
        or type(row["metadata"]) is not dict
    ):
        raise ValueError("Expected exact adaptive vector row")
    return {**row, "vector": row["vector"].to_list()}


def sample_rows(snapshot, args, permit):
    from fannagent.errors import AgentError

    result = []
    for row in snapshot.rows[max(0, int(args.get("offset", 0))) :]:
        public = plain_row(row)
        try:
            permit({"id": "sample", "vector": public["vector"], "k": 1})
        except AgentError:
            continue
        result.append(public)
        if len(result) >= min(100, max(1, int(args.get("limit", 20)))):
            break
    return result


if __name__ == "__main__":
    raise RuntimeError("Offline memory component only; no native execution or allowance")
