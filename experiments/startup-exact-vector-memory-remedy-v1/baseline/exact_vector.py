"""A3 offline prototype. No native producer, database, search or launch entry point."""

from __future__ import annotations

import hashlib
import json
import math
import struct
import threading
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path("/Users/danielarturi/Developer/JinyangLiWork")
PACKAGE = (
    ROOT
    / "trials/torch-reviews-startup-attribution-v1-image-reference"
    / "torch-startup-attribution-v1-image-reference"
)
FREEZE = ROOT / "trials/torch-reviews-startup-exact-vector-v1/A3-FREEZE.json"
DIMENSION = 768
MAX_ROWS = 64
_ACTIVE = None


@dataclass(frozen=True, slots=True, eq=False)
class PackedVector(Sequence):
    """Own binary64 bytes plus original integer categories and exact integer values."""

    _payload: bytes
    _integer_mask: int
    _integers: tuple[int, ...]

    def __post_init__(self):
        if (
            type(self._payload) is not bytes
            or len(self._payload) != DIMENSION * 8
            or type(self._integer_mask) is not int
            or not 0 <= self._integer_mask < 1 << DIMENSION
            or type(self._integers) is not tuple
            or any(type(v) is not int for v in self._integers)
            or self._integer_mask.bit_count() != len(self._integers)
        ):
            raise ValueError("Packed vector structure differs")
        integer_index = 0
        for index, (value,) in enumerate(struct.iter_unpack("<d", self._payload)):
            if not math.isfinite(value):
                raise ValueError("Nonfinite packed vector")
            if self._integer_mask & (1 << index):
                expected = float(self._integers[integer_index])
                if struct.pack("<d", expected) != self._payload[index * 8 : index * 8 + 8]:
                    raise ValueError("Integer category/value and numeric buffer differ")
                integer_index += 1

    @classmethod
    def from_values(cls, values):
        if type(values) is not list or len(values) != DIMENSION:
            raise ValueError("Exactly 768 decoded JSON numeric values required")
        integers, numeric, mask = [], [], 0
        for index, value in enumerate(values):
            if type(value) not in (int, float):
                raise ValueError("Only original JSON integer/float values supported")
            converted = float(value)
            if not math.isfinite(converted):
                raise ValueError("Finite original numeric values required")
            if type(value) is int:
                mask |= 1 << index
                integers.append(value)
            numeric.append(converted)
        return cls(struct.pack("<" + "d" * DIMENSION, *numeric), mask, tuple(integers))

    def __len__(self):
        return DIMENSION

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(len(self)))]
        if not isinstance(index, int):
            raise TypeError("Integer or slice required")
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError(index)
        if self._integer_mask & (1 << index):
            rank = (self._integer_mask & ((1 << index) - 1)).bit_count()
            return self._integers[rank]
        return struct.unpack_from("<d", self._payload, index * 8)[0]

    def __iter__(self) -> Iterator[int | float]:
        integer_index = 0
        for index, (value,) in enumerate(struct.iter_unpack("<d", self._payload)):
            if self._integer_mask & (1 << index):
                yield self._integers[integer_index]
                integer_index += 1
            else:
                yield value

    def __array__(self, dtype=None, copy=None):
        import numpy as np

        result = np.frombuffer(self._payload, dtype="<f8")
        if dtype is not None and np.dtype(dtype) != result.dtype:
            if copy is False:
                raise ValueError("Requested dtype requires a copy")
            result = result.astype(dtype)
        elif copy:
            result = result.copy()
        return result

    def to_list(self):
        return list(self)


def pack_json_vector(text):
    if type(text) is not str or len(text.encode()) > 64 * 1024:
        raise ValueError("Vector JSON text/type cap")
    return PackedVector.from_values(json.loads(text))


def plain_row(row):
    if (
        type(row) is not dict
        or set(row) != {"source_id", "vector", "metadata"}
        or type(row["vector"]) is not PackedVector
        or type(row["source_id"]) not in (int, str)
        or type(row["metadata"]) is not dict
    ):
        raise ValueError("Expected an exact packed row")
    return {**row, "vector": row["vector"].to_list()}


def sample_rows(snapshot, args, permit):
    """Original broker sample semantics, with one row converted at its JSON boundary."""
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


def verify_sources():
    frozen = json.loads(FREEZE.read_text())
    for relative, expected in frozen["consumer_source_sha256"].items():
        if hashlib.sha256((PACKAGE / relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError("A3 consumer source differs: " + relative)
    import si_stream

    import fannagent.snapshot as snapshot
    import fannagent.store as store

    for module, relative in (
        (snapshot, "frozen/vendor/fannagent/snapshot.py"),
        (store, "frozen/vendor/fannagent/store.py"),
        (si_stream, "si_stream.py"),
    ):
        if Path(module.__file__).resolve() != PACKAGE / relative:
            raise RuntimeError("A3 loaded consumer origin differs")
    return snapshot, store, si_stream


class FixtureIdentity:
    """At most 64 rows: this prototype deliberately cannot admit native-size input."""

    def __init__(self):
        self.snapshot, self.store, self.stream = verify_sources()
        self.original = self.store.digest
        self.bound = self.digest
        self.calls = 0
        self.record = None

    def __enter__(self):
        global _ACTIVE
        if (
            _ACTIVE is not None
            or threading.current_thread() is not threading.main_thread()
            or len(threading.enumerate()) != 1
            or self.snapshot.digest is not self.original
        ):
            raise RuntimeError("Unexpected/concurrent/nested A3 fixture identity")
        _ACTIVE = self
        self.snapshot.digest = self.bound
        return self

    def canonical(self, value):
        if type(value) is list:
            return self.store.canonical(value)  # original field encoder
        return self.store.canonical(plain_row(value))

    def digest(self, payload):
        self.calls += 1
        if (
            _ACTIVE is not self
            or self.calls != 1
            or type(payload) is not dict
            or set(payload) != {"rows", "fields"}
            or type(payload["rows"]) is not list
            or not 1 <= len(payload["rows"]) <= MAX_ROWS
            or type(payload["fields"]) is not list
            or any(type(r.get("vector")) is not PackedVector for r in payload["rows"])
        ):
            raise RuntimeError("A3 fixture identity scope/count/type cap")
        self.record = self.stream.framed(payload, self.canonical)
        return self.record["digest"]

    def __exit__(self, typ, value, traceback):
        global _ACTIVE
        intact = self.snapshot.digest is self.bound and _ACTIVE is self
        self.snapshot.digest = self.original
        _ACTIVE = None
        if not intact and typ is None:
            raise RuntimeError("A3 fixture binding changed; original restored")
