"""Bounded original-consumer checks, never a native memory/performance estimate."""
# ruff: noqa: E402

import copy
import dataclasses
import hashlib
import json
import math
import struct
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from exact_vector import (
    PACKAGE,
    FixtureIdentity,
    PackedVector,
    pack_json_vector,
    plain_row,
    sample_rows,
)

sys.path[:0] = [str(PACKAGE), str(PACKAGE / "frozen"), str(PACKAGE / "frozen/vendor")]

import numpy as np
import pyarrow.parquet as pq

import fannagent.snapshot as snapshot_module
from fannagent.broker import Tools
from fannagent.config import WorkloadConfig
from fannagent.errors import AgentError
from fannagent.snapshot import Snapshot
from fannagent.store import canonical, digest
from fannagent.workload import generate


def values(*first):
    return list(first) + [0.0] * (768 - len(first))


def packed_rows(rows):
    return [
        {**row, "vector": pack_json_vector(json.dumps(row["vector"], separators=(",", ":")))}
        for row in rows
    ]


class VectorTests(unittest.TestCase):
    def test_original_json_integer_float_categories_and_bytes(self):
        source = values(0, -0.0, 1, 1.0, -1, -1.0, 1.0000001)
        result = PackedVector.from_values(source).to_list()
        self.assertEqual(canonical(source), canonical(result))
        self.assertEqual([type(x) for x in source], [type(x) for x in result])

    def test_signed_zero_and_binary64_extremes(self):
        source = values(-0.0, 0.0, math.ulp(0.0), -math.ulp(0.0), sys.float_info.max)
        result = PackedVector.from_values(source).to_list()
        self.assertEqual(struct.pack("<768d", *source), struct.pack("<768d", *result))

    def test_values_colliding_in_float32_keep_distinct_original_identity(self):
        left, right = values(1.0), values(1.0 + 2**-30)
        self.assertEqual(
            np.asarray(left, dtype=np.float32).tobytes(),
            np.asarray(right, dtype=np.float32).tobytes(),
        )
        self.assertNotEqual(canonical(left), canonical(right))
        self.assertNotEqual(
            canonical(PackedVector.from_values(left).to_list()),
            canonical(PackedVector.from_values(right).to_list()),
        )

    def test_large_integer_exactness_is_separate_from_numeric_buffer(self):
        source = values(2**100 + 1, -(2**100 + 1))
        result = PackedVector.from_values(source)
        self.assertEqual(canonical(source), canonical(result.to_list()))
        np.testing.assert_array_equal(
            np.asarray(source, dtype=np.float32).view(np.uint32),
            np.asarray(result, dtype=np.float32).view(np.uint32),
        )

    def test_index_negative_slice_and_iteration(self):
        source = values(3, -0.0, 2.0)
        result = PackedVector.from_values(source)
        self.assertEqual(result[0], source[0])
        self.assertEqual(result[-1], source[-1])
        self.assertEqual(result[::-31], source[::-31])
        self.assertEqual(list(result), source)
        with self.assertRaises(IndexError):
            _ = result[768]

    def test_payload_independent_of_input_mutation(self):
        source = values(1.0)
        result = PackedVector.from_values(source)
        source[0] = 0.25
        self.assertEqual(result[0], 1.0)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result._payload = b"bad"

    def test_numpy_view_is_read_only_and_copy_is_owned(self):
        result = PackedVector.from_values(values(1.0))
        view = np.asarray(result)
        self.assertFalse(view.flags.writeable)
        with self.assertRaises(ValueError):
            view[0] = 0
        copied = np.array(result, copy=True)
        copied[0] = 0
        self.assertEqual(result[0], 1.0)

    def test_numpy_dtype_copy_false_rejected(self):
        result = PackedVector.from_values(values(1.0))
        with self.assertRaises(ValueError):
            result.__array__(dtype=np.float32, copy=False)

    def test_nonfinite_boolean_string_and_nested_values_rejected(self):
        for bad in (float("inf"), float("nan"), True, "1", [1.0]):
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError):
                    PackedVector.from_values(values(bad))

    def test_dimensions_and_unexpected_text_rejected(self):
        for bad in ([0.0], [0.0] * 769, tuple(values(1.0))):
            with self.assertRaises(ValueError):
                PackedVector.from_values(bad)
        for bad in ('{"value":1}', "x" * (64 * 1024 + 1), b"[]"):
            with self.assertRaises(ValueError):
                pack_json_vector(bad)

    def test_forged_payload_or_integer_tags_rejected(self):
        for payload, mask, integers in (
            (b"bad", 0, ()),
            (b"\0" * 6144, 1, ()),
            (b"\0" * 6144, 1 << 768, ()),
        ):
            with self.assertRaises(ValueError):
                PackedVector(payload, mask, integers)

    def test_integer_tag_numeric_buffer_disagreement_rejected(self):
        payload = struct.pack("<768d", *values(1.0))
        with self.assertRaises(ValueError):
            PackedVector(payload, 1, (2,))
        payload = struct.pack("<768d", *values(-0.0))
        with self.assertRaises(ValueError):
            PackedVector(payload, 1, (0,))

    def test_no_whole_decoded_list_is_cached(self):
        result = PackedVector.from_values(values(1.0))
        first = result.to_list()
        second = result.to_list()
        self.assertIsNot(first, second)
        self.assertEqual(len(result._payload), 6144)
        self.assertFalse(hasattr(result, "__dict__"))


class ConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(20261030)
        cls.fields = [
            {"name": "total_votes", "type": "integer", "nullable": False},
            {"name": "weight", "type": "float", "nullable": True},
            {"name": "label", "type": "string", "nullable": False},
            {"name": "flag", "type": "boolean", "nullable": False},
        ]
        cls.rows = []
        for i in range(32):
            vector = rng.normal(size=768)
            vector = (vector / np.linalg.norm(vector)).tolist()
            if i == 0:
                vector = values(1, -0.0)
            elif i == 1:
                vector = values(1.0 + 2**-30)
            cls.rows.append(
                {
                    "source_id": 1 if i == 0 else "1" if i == 1 else i + 2,
                    "vector": vector,
                    "metadata": {
                        "total_votes": 108 + i,
                        "weight": None if i % 2 else i + 0.25,
                        "label": str(i),
                        "flag": bool(i % 2),
                    },
                }
            )
        cls.baseline = Snapshot(copy.deepcopy(cls.rows), copy.deepcopy(cls.fields))

    def setUp(self):
        with FixtureIdentity() as scope:
            self.packed = Snapshot(packed_rows(self.rows), copy.deepcopy(self.fields))
        self.record = scope.record
        self.assertIs(snapshot_module.digest, digest)

    def test_original_constructor_function_is_unchanged(self):
        self.assertEqual(
            Path(Snapshot.__init__.__code__.co_filename).resolve(),
            PACKAGE / "frozen/vendor/fannagent/snapshot.py",
        )
        self.assertEqual(self.record["rows"], 32)
        self.assertEqual(self.record["component_calls"], 33)
        self.assertLessEqual(self.record["max_pending_bytes"], 65536)

    def test_full_original_canonical_bytes_and_identity(self):
        plain = {"rows": self.baseline.rows, "fields": self.fields}
        adapted = {"rows": [plain_row(r) for r in self.packed.rows], "fields": self.fields}
        self.assertEqual(canonical(plain), canonical(adapted))
        self.assertEqual(self.packed.identity, self.baseline.identity)
        self.assertEqual(self.packed.data.dataset_hash, self.baseline.data.dataset_hash)

    def test_original_stream_framing_produces_identical_complete_bytes(self):
        with FixtureIdentity() as scope:
            chunks = []
            record = scope.stream.framed(
                {"rows": self.packed.rows, "fields": self.fields},
                scope.canonical,
                sink=chunks.append,
            )
        expected = canonical({"rows": self.baseline.rows, "fields": self.fields})
        self.assertEqual(b"".join(chunks), expected)
        self.assertEqual(record["digest"], hashlib.sha256(expected).hexdigest())

    def test_original_matrix_float32_bits(self):
        np.testing.assert_array_equal(
            self.packed.data.vectors.view(np.uint32), self.baseline.data.vectors.view(np.uint32)
        )
        self.assertEqual(self.packed.data.vectors.dtype, np.float32)

    def test_typed_identifiers_sort_and_maps(self):
        for name in (
            "source_ids",
            "source_to_id",
            "id_to_source",
            "_typed_source_to_id",
            "field_map",
            "reverse_fields",
            "fields",
        ):
            self.assertEqual(getattr(self.packed, name), getattr(self.baseline, name))
        self.assertNotEqual(self.packed.analysis_id(1), self.packed.analysis_id("1"))

    def test_metadata_values_masks_and_description(self):
        for key, expected in self.baseline.data.metadata.items():
            actual = self.packed.data.metadata[key]
            np.testing.assert_array_equal(actual.data, expected.data)
            np.testing.assert_array_equal(actual.mask, expected.mask)
        self.assertEqual(self.packed.description(), self.baseline.description())

    def test_original_query_normalization_and_rejection(self):
        raw = {
            "id": "probe",
            "vector": self.rows[0]["vector"],
            "k": 3,
            "filter": {"field": "total_votes", "op": "gte", "value": 108},
        }
        self.assertEqual(self.packed.query(raw), self.baseline.query(raw))
        raw["vector"] = [0.0]
        errors = []
        for snapshot in (self.baseline, self.packed):
            with self.assertRaises(Exception) as error:
                snapshot.query(raw)
            errors.append((type(error.exception), str(error.exception)))
        self.assertEqual(errors[0], errors[1])

    def test_original_workload_generation(self):
        config = WorkloadConfig(count=20, seed=20261030, k=3)
        self.assertEqual(generate(self.packed, config), generate(self.baseline, config))

    def test_original_save_parquet_schema_and_values(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ("baseline.parquet", "packed.parquet")]
            for snapshot, path in zip((self.baseline, self.packed), paths, strict=True):
                snapshot.save(path)
            self.assertTrue(pq.read_table(paths[0]).equals(pq.read_table(paths[1])))
            self.assertEqual(
                hashlib.sha256(paths[0].read_bytes()).digest(),
                hashlib.sha256(paths[1].read_bytes()).digest(),
            )

    def test_bounded_sample_values_match_original_broker(self):
        args = {"offset": 1, "limit": 3}
        expected = Tools._call(
            SimpleNamespace(
                study=SimpleNamespace(snapshot=self.baseline, permitted=self.baseline.query)
            ),
            "sample",
            args,
        )
        actual = sample_rows(self.packed, args, self.packed.query)
        self.assertEqual(canonical(actual), canonical(expected))
        self.assertTrue(all(type(r["vector"]) is list for r in actual))

    def test_sample_denials_offsets_and_limits_match(self):
        def denied(query):
            raise AgentError("denied")

        for args in ({"offset": -3, "limit": 0}, {"offset": 31, "limit": 1000}, {"offset": 100}):
            for permit in (self.baseline.query, denied):
                expected = Tools._call(
                    SimpleNamespace(
                        study=SimpleNamespace(snapshot=self.baseline, permitted=permit)
                    ),
                    "sample",
                    args,
                )
                self.assertEqual(
                    canonical(expected), canonical(sample_rows(self.packed, args, permit))
                )

    def test_sample_only_materializes_visited_rows(self):
        original = PackedVector.to_list
        calls = []

        def track(vector):
            calls.append(id(vector))
            return original(vector)

        with patch.object(PackedVector, "to_list", track):
            result = sample_rows(self.packed, {"limit": 3}, self.packed.query)
        self.assertEqual(len(result), 3)
        self.assertEqual(len(calls), 3)


class ScopeTests(unittest.TestCase):
    def test_restore_on_constructor_validation_error(self):
        with self.assertRaises(AgentError):
            with FixtureIdentity():
                Snapshot(
                    [
                        {
                            "source_id": 1,
                            "vector": PackedVector.from_values(values(0.0)),
                            "metadata": {},
                        }
                    ],
                    [],
                )
        self.assertIs(snapshot_module.digest, digest)

    def test_restore_on_encoder_failure(self):
        with self.assertRaises(ValueError):
            with FixtureIdentity() as scope:
                scope.digest(
                    {
                        "rows": [
                            {
                                "source_id": 1,
                                "vector": PackedVector.from_values(values(1.0)),
                                "metadata": {"bad": float("nan")},
                            }
                        ],
                        "fields": [],
                    }
                )
        self.assertIs(snapshot_module.digest, digest)

    def test_nested_foreign_and_threaded_scopes_rejected(self):
        with FixtureIdentity():
            with self.assertRaises(RuntimeError):
                with FixtureIdentity():
                    pass
        with patch.object(snapshot_module, "digest", lambda x: "foreign"):
            with self.assertRaises(RuntimeError):
                with FixtureIdentity():
                    pass
        errors = []

        def enter():
            try:
                with FixtureIdentity():
                    pass
            except RuntimeError as error:
                errors.append(error)

        thread = threading.Thread(target=enter)
        thread.start()
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertIs(snapshot_module.digest, digest)

    def test_repeat_native_size_and_unpacked_payload_rejected(self):
        row = {"source_id": 1, "vector": PackedVector.from_values(values(1.0)), "metadata": {}}
        with FixtureIdentity() as scope:
            scope.digest({"rows": [row], "fields": []})
            with self.assertRaises(RuntimeError):
                scope.digest({"rows": [row], "fields": []})
        for rows in ([row] * 65, [plain_row(row)]):
            with self.assertRaises(RuntimeError):
                with FixtureIdentity() as scope:
                    scope.digest({"rows": rows, "fields": []})

    def test_binding_tampering_restores_original(self):
        with self.assertRaises(RuntimeError):
            with FixtureIdentity():
                snapshot_module.digest = lambda x: "changed"
        self.assertIs(snapshot_module.digest, digest)

    def test_source_and_loaded_origin_mismatch_rejected(self):
        with patch("exact_vector.PACKAGE", Path("/unavailable-frozen-package")):
            with self.assertRaises(FileNotFoundError):
                FixtureIdentity()
        with patch.object(snapshot_module, "__file__", "/untrusted/snapshot.py"):
            with self.assertRaises(RuntimeError):
                FixtureIdentity()

    def test_field_encoding_cap_restores_binding(self):
        row = {
            "source_id": 1,
            "vector": PackedVector.from_values(values(1.0)),
            "metadata": {},
        }
        with self.assertRaises(RuntimeError):
            with FixtureIdentity() as scope:
                scope.digest({"rows": [row], "fields": [{"name": "x" * 20000}]})
        self.assertIs(snapshot_module.digest, digest)

    def test_maximum_fixture_rows_complete_without_native_input(self):
        rows = [
            {"source_id": i, "vector": PackedVector.from_values(values(1.0)), "metadata": {}}
            for i in range(64)
        ]
        with FixtureIdentity() as scope:
            result = Snapshot(rows, [])
        self.assertEqual(len(result.rows), 64)
        self.assertEqual(scope.record["component_calls"], 65)


if __name__ == "__main__":
    unittest.main(verbosity=2)
