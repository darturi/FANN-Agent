"""Exact consumer parity and allocation ownership; bounded synthetic fixtures only."""

import copy
import dataclasses
import hashlib
import json
import math
import struct
import sys
import tempfile
import unittest
import weakref
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import exact_codec as C
import exact_vector as X
import fixture_adapter as A
import integration as I
import numpy as np
import pyarrow.parquet as pq

from fannagent import snapshot as snapshot_module
from fannagent.broker import Tools
from fannagent.config import WorkloadConfig
from fannagent.errors import AgentError
from fannagent.snapshot import Snapshot
from fannagent.store import canonical, digest
from fannagent.workload import generate


def values(*first):
    return list(first) + [0.0] * (768 - len(first))


def packed(rows):
    return [{**r, "vector": C.ExactVector.from_values(r["vector"])} for r in rows]


class ExactCodecTests(unittest.TestCase):
    def same(self, source):
        vector = C.ExactVector.from_values(source)
        result = vector.to_list()
        self.assertEqual(canonical(source), canonical(result))
        self.assertEqual([type(v) for v in source], [type(v) for v in result])
        self.assertEqual(struct.pack("<768d", *source), struct.pack("<768d", *result))
        np.testing.assert_array_equal(
            np.asarray(X.PackedVector.from_values(source), dtype=np.float32).view(np.uint32),
            np.asarray(vector, dtype=np.float32).view(np.uint32),
        )
        return vector

    def test_compact_exact_integer_categories_signed_zero_and_decimal_values(self):
        vector = self.same(values(0, -0.0, 1, 1.0, -1, -1.0, 0.1, -0.25))
        self.assertTrue(vector.compact)
        self.assertEqual(len(vector._payload), 3072)

    def test_one_nonroundtripping_scalar_forces_whole_raw64_fallback(self):
        vector = self.same(values(1.0 + 2**-30))
        self.assertFalse(vector.compact)
        self.assertEqual(len(vector._payload), 6144)

    def test_float32_collisions_keep_different_original_identities(self):
        left = self.same(values(1.0))
        right = self.same(values(1.0 + 2**-30))
        self.assertEqual(
            np.asarray(left, dtype=np.float32).tobytes(),
            np.asarray(right, dtype=np.float32).tobytes(),
        )
        self.assertNotEqual(canonical(left.to_list()), canonical(right.to_list()))

    def test_binary64_subnormals_extremes_and_tiny_negative_zero_cases(self):
        vector = self.same(values(math.ulp(0.0), -math.ulp(0.0), sys.float_info.max, -0.0))
        self.assertFalse(vector.compact)

    def test_float32_subnormal_shortest_values_preserve_binary64_parsing(self):
        raw = np.array([1, 2, 3, 0x007FFFFF, 0x00800000], dtype=np.uint32).view(np.float32)
        source = values(*[float(np.format_float_positional(v, unique=True, trim="-")) for v in raw])
        self.assertTrue(self.same(source).compact)

    def test_large_exact_integer_tags_are_never_rounded_away(self):
        self.same(values(2**100 + 1, -(2**100 + 1), 10**20 + 1))

    def test_seeded_arbitrary_binary64_values_fall_back_without_loss(self):
        rng = np.random.default_rng(20261031)
        source = rng.uniform(-1, 1, size=768).tolist()
        self.assertFalse(self.same(source).compact)

    def test_payload_nonexpansion_and_equal_three_slot_object_size(self):
        for source in (values(1.0), values(1.0 + 2**-30)):
            old = X.PackedVector.from_values(source)
            new = C.ExactVector.from_values(source)
            self.assertLessEqual(sys.getsizeof(new._payload), sys.getsizeof(old._payload))
            self.assertEqual(sys.getsizeof(new), sys.getsizeof(old))
            self.assertFalse(hasattr(new, "__dict__"))
            self.assertEqual(len(new.__slots__), 3)

    def test_compact_float32_conversion_is_readonly_shared_data(self):
        vector = self.same(values(1.0))
        view = vector.__array__(dtype=np.float32, copy=False)
        self.assertFalse(view.flags.owndata)
        self.assertFalse(view.flags.writeable)
        self.assertIs(view.base, vector._payload)
        self.assertTrue(np.shares_memory(view, np.frombuffer(vector._payload, dtype="<f4")))

    def test_compact_default_float64_is_exact_readonly_and_copy_false_rejected(self):
        vector = self.same(values(0.1, 1, -0.0))
        self.assertEqual(np.asarray(vector).tobytes(), struct.pack("<768d", *values(0.1, 1, -0.0)))
        self.assertFalse(np.asarray(vector).flags.writeable)
        with self.assertRaises(ValueError):
            vector.__array__(copy=False)

    def test_explicit_owned_copy_and_other_dtype_conversion(self):
        vector = self.same(values(0.1, 1, -0.0))
        copied = np.array(vector, dtype=np.float32, copy=True)
        self.assertTrue(copied.flags.owndata)
        copied[0] = 0
        self.assertEqual(vector[0], 0.1)
        expected = X.PackedVector.from_values(values(0.1, 1, -0.0))
        self.assertEqual(
            np.asarray(vector, dtype=">f8").tobytes(), np.asarray(expected, dtype=">f8").tobytes()
        )

    def test_raw64_fallback_preserves_original_array_copy_semantics(self):
        vector = self.same(values(1.0 + 2**-30))
        self.assertIs(np.asarray(vector).base, vector._payload)
        with self.assertRaises(ValueError):
            vector.__array__(dtype=np.float32, copy=False)

    def test_index_slice_iteration_and_input_mutation_independence(self):
        source = values(0.1, -0.0, 1)
        vector = self.same(source)
        source[0] = 0.25
        self.assertEqual(vector[0], 0.1)
        self.assertEqual(vector[-1], 0.0)
        self.assertEqual(vector[::-17], vector.to_list()[::-17])
        self.assertIsNot(vector.to_list(), vector.to_list())
        with self.assertRaises(IndexError):
            _ = vector[768]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            vector._payload = b"bad"

    def test_nonfinite_boolean_nested_and_wrong_dimension_inputs_fail(self):
        for value in (float("nan"), float("inf"), True, "1", [1.0]):
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                C.ExactVector.from_values(values(value))
        for value in ([1.0], tuple(values(1.0)), values(1.0) + [0.0]):
            with self.assertRaises(ValueError):
                C.ExactVector.from_values(value)

    def test_json_text_and_size_guards_are_retained(self):
        self.assertEqual(C.pack_json_vector(json.dumps(values(0.1))).to_list(), values(0.1))
        for text in ("x" * 65537, b"[]", "{}", "NaN"):
            with self.assertRaises(ValueError):
                C.pack_json_vector(text)

    def test_forged_payload_tag_and_negative_zero_mismatch_rejected(self):
        for args in ((b"x", 0, ()), (b"\0" * 3072, 1, ()), (b"\0" * 3072, 1 << 768, ())):
            with self.assertRaises(ValueError):
                C.ExactVector(*args)
        with self.assertRaises(ValueError):
            C.ExactVector(struct.pack("<768f", *values(-0.0)), 1, (0,))

    def test_nonfinite_forged_compact_payload_is_rejected(self):
        with self.assertRaises(ValueError):
            C.ExactVector(struct.pack("<768f", *values(float("inf"))), 0, ())

    def test_formatter_rebinding_fails_closed_and_restores(self):
        vector = self.same(values(0.1))
        with patch.object(np, "format_float_positional", lambda *a, **k: "0"):
            with self.assertRaises(RuntimeError):
                C.ExactVector.from_values(values(1.0))
            with self.assertRaises(RuntimeError):
                vector.to_list()
        self.assertEqual(vector[0], 0.1)


class OriginalConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(20261031)
        cls.fields = [
            dict(name="total_votes", type="integer", nullable=False),
            dict(name="weight", type="float", nullable=True),
            dict(name="label", type="string", nullable=False),
            dict(name="flag", type="boolean", nullable=False),
        ]
        cls.rows = []
        for i in range(32):
            raw = rng.normal(size=768)
            raw = (raw / np.linalg.norm(raw)).astype(np.float32)
            vector = [float(np.format_float_positional(v, unique=True, trim="-")) for v in raw]
            if i == 0:
                vector = values(1, -0.0)
            if i == 1:
                vector[0] += 2**-40
            cls.rows.append(
                dict(
                    source_id=1 if i == 0 else "1" if i == 1 else i + 2,
                    vector=vector,
                    metadata=dict(
                        total_votes=108 + i,
                        weight=None if i % 2 else i + 0.25,
                        label="\u03bb" + str(i),
                        flag=bool(i % 2),
                    ),
                )
            )
        cls.baseline = Snapshot(copy.deepcopy(cls.rows), copy.deepcopy(cls.fields))
        cls.spec = I.FixtureSpec(32, canonical(cls.fields), cls.baseline.identity)

    def setUp(self):
        self.rows_new = packed(self.rows)
        with A.FixtureIdentity(self.spec) as scope:
            self.candidate = Snapshot(self.rows_new, copy.deepcopy(self.fields))
        self.record = scope.record

    def tearDown(self):
        self.assertIs(snapshot_module.digest, digest)
        self.assertIsNone(X._ACTIVE)

    def test_fixture_contains_both_exact_compact_and_raw_fallback_rows(self):
        compact = [r["vector"].compact for r in self.rows_new]
        self.assertTrue(any(compact))
        self.assertTrue(any(not v for v in compact))

    def test_actual_constructor_and_canonical_identity_bytes_are_unchanged(self):
        self.assertEqual(
            Path(Snapshot.__init__.__code__.co_filename).resolve(),
            X.PACKAGE / "frozen/vendor/fannagent/snapshot.py",
        )
        self.assertEqual(
            canonical([C.plain_row(r) for r in self.candidate.rows]), canonical(self.baseline.rows)
        )
        self.assertEqual(self.candidate.identity, self.baseline.identity)
        self.assertEqual(self.candidate.data.dataset_hash, self.baseline.data.dataset_hash)

    def test_original_framing_sink_matches_complete_canonical_document(self):
        chunks = []
        with A.FixtureIdentity(self.spec) as scope:
            record = scope.stream.framed(
                dict(rows=self.candidate.rows, fields=self.fields),
                scope.canonical,
                sink=chunks.append,
            )
        expected = canonical(dict(rows=self.baseline.rows, fields=self.fields))
        self.assertEqual(b"".join(chunks), expected)
        self.assertEqual(record["digest"], hashlib.sha256(expected).hexdigest())
        self.assertLessEqual(record["max_pending_bytes"], 65536)

    def test_matrix_uint32_bits_and_typed_identifier_maps_match(self):
        np.testing.assert_array_equal(
            self.candidate.data.vectors.view(np.uint32), self.baseline.data.vectors.view(np.uint32)
        )
        for name in (
            "source_ids",
            "source_to_id",
            "id_to_source",
            "_typed_source_to_id",
            "field_map",
            "reverse_fields",
            "fields",
        ):
            self.assertEqual(getattr(self.candidate, name), getattr(self.baseline, name))
        self.assertNotEqual(self.candidate.analysis_id(1), self.candidate.analysis_id("1"))

    def test_metadata_values_masks_and_description_match(self):
        for k, expected in self.baseline.data.metadata.items():
            actual = self.candidate.data.metadata[k]
            np.testing.assert_array_equal(actual.data, expected.data)
            np.testing.assert_array_equal(actual.mask, expected.mask)
        self.assertEqual(self.candidate.description(), self.baseline.description())

    def test_original_query_acceptance_and_rejection_match(self):
        query = dict(
            id="query",
            vector=self.rows[0]["vector"],
            k=3,
            filter=dict(field="total_votes", op="gte", value=108),
        )
        self.assertEqual(self.candidate.query(query), self.baseline.query(query))
        query["vector"] = [0.0]
        errors = []
        for snapshot in (self.candidate, self.baseline):
            with self.assertRaises(Exception) as caught:
                snapshot.query(query)
            errors.append((type(caught.exception), str(caught.exception)))
        self.assertEqual(errors[0], errors[1])

    def test_original_workload_generation_is_equal(self):
        config = WorkloadConfig(count=20, seed=20261031, k=3)
        self.assertEqual(generate(self.candidate, config), generate(self.baseline, config))

    def test_original_parquet_schema_values_and_file_bytes_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / name for name in ("old.parquet", "new.parquet")]
            for snapshot, path in zip((self.baseline, self.candidate), paths, strict=True):
                snapshot.save(path)
            self.assertTrue(pq.read_table(paths[0]).equals(pq.read_table(paths[1])))
            self.assertEqual(paths[0].read_bytes(), paths[1].read_bytes())

    def test_bounded_json_sample_matches_original_broker(self):
        args = dict(offset=1, limit=3)
        expected = Tools._call(
            SimpleNamespace(
                study=SimpleNamespace(snapshot=self.baseline, permitted=self.baseline.query)
            ),
            "sample",
            args,
        )
        actual = C.sample_rows(self.candidate, args, self.candidate.query)
        self.assertEqual(canonical(actual), canonical(expected))

    def test_root_rows_and_data_remain_retained_across_consumers(self):
        token = id(self.candidate.rows)
        payloads = [r["vector"]._payload for r in self.candidate.rows]
        self.candidate.description()
        generate(self.candidate, WorkloadConfig(count=20, seed=1, k=1))
        self.assertEqual(id(self.candidate.rows), token)
        self.assertTrue(
            all(
                r["vector"]._payload is p
                for r, p in zip(self.candidate.rows, payloads, strict=True)
            )
        )

    def test_mutable_matrix_does_not_alias_immutable_row_payloads(self):
        vector = self.candidate.rows[0]["vector"]
        before = canonical(vector.to_list())
        view = np.frombuffer(vector._payload, dtype="<f4" if vector.compact else "<f8")
        self.assertFalse(np.shares_memory(self.candidate.data.vectors, view))
        self.candidate.data.vectors[0, 0] = 0.5
        self.assertEqual(canonical(vector.to_list()), before)

    def test_fixture_adapter_executes_original_constructor(self):
        result = A.construct(packed(self.rows), self.fields, self.spec)
        self.assertEqual(result.identity, self.baseline.identity)


class BoundaryAndAllocationTests(unittest.TestCase):
    def source(self, n=4):
        return [dict(source_id=i, vector=values(1.0), metadata={}) for i in range(n)]

    def test_compact_constructor_has_no_owned_float32_row_buffers(self):
        rows = self.source(64)
        baseline = Snapshot(rows, [])
        spec = I.FixtureSpec(64, canonical([]), baseline.identity)
        source = packed(rows)
        original = C.ExactVector.__array__
        calls = []
        live = {}
        peaks = [0]

        def observe(self, *args, **kwargs):
            array = original(self, *args, **kwargs)
            self_test.assertFalse(array.flags.owndata)
            self_test.assertIs(array.base, self._payload)
            key = id(array)
            live[key] = array.nbytes
            peaks[0] = max(peaks[0], sum(live.values()))
            calls.append(array.flags.owndata)
            weakref.finalize(array, lambda: live.pop(key))
            return array

        self_test = self
        with patch.object(C.ExactVector, "__array__", observe):
            result = A.construct(source, [], spec)
        self.assertEqual(calls, [False] * 64)
        self.assertEqual(live, {})
        self.assertEqual(peaks[0], 64 * 768 * 4)
        self.assertEqual(result.data.vectors.tobytes(), baseline.data.vectors.tobytes())

    def test_native_unknown_and_oversized_specs_rejected_before_constructor(self):
        for spec in (
            None,
            SimpleNamespace(rows=247286),
            I.NativeSpec(247286, b"[]", "0" * 64, Path("/unreleased")),
        ):
            with patch("fannagent.snapshot.Snapshot", side_effect=AssertionError("constructor")):
                with self.assertRaises(RuntimeError):
                    A.construct([], [], spec)
        spec = I.FixtureSpec(1, b"[]", "0" * 64)
        with self.assertRaises(RuntimeError):
            A.construct(self.source(65), [], spec)

    def test_wrong_identity_restores_original_binding(self):
        spec = I.FixtureSpec(4, b"[]", "0" * 64)
        with self.assertRaises(RuntimeError):
            A.construct(packed(self.source()), [], spec)
        self.assertIs(snapshot_module.digest, digest)
        self.assertIsNone(X._ACTIVE)

    def test_original_norm_and_duplicate_identifier_failures_are_retained(self):
        source = self.source()
        source[0]["vector"] = values(0.0)
        with self.assertRaises(AgentError):
            A.construct(packed(source), [], I.FixtureSpec(4, b"[]", "0" * 64))
        source = self.source()
        source[1]["source_id"] = source[0]["source_id"]
        with self.assertRaises(AgentError):
            A.construct(packed(source), [], I.FixtureSpec(4, b"[]", "0" * 64))

    def test_identity_interrupt_and_foreign_binding_restore(self):
        baseline = Snapshot(self.source(), [])
        spec = I.FixtureSpec(4, b"[]", baseline.identity)
        import si_stream

        for error in (KeyboardInterrupt("fixture"), RuntimeError("fixture")):
            with patch.object(si_stream, "framed", side_effect=error):
                with self.assertRaises(type(error)):
                    A.construct(packed(self.source()), [], spec)
            self.assertIs(snapshot_module.digest, digest)
            self.assertIsNone(X._ACTIVE)
        with self.assertRaises(RuntimeError):
            with A.FixtureIdentity(spec):
                snapshot_module.digest = lambda p: "foreign"
        self.assertIs(snapshot_module.digest, digest)

    def test_nested_and_concurrent_identity_scope_are_rejected(self):
        spec = I.FixtureSpec(1, b"[]", "0" * 64)
        with A.FixtureIdentity(spec):
            with self.assertRaises(RuntimeError):
                with A.FixtureIdentity(spec):
                    pass
        with patch("exact_vector.threading.current_thread", return_value=object()):
            with self.assertRaises(RuntimeError):
                with A.FixtureIdentity(spec):
                    pass

    def test_formatter_and_original_source_provenance_are_pinned(self):
        freeze = C.verify_sources()
        self.assertEqual(freeze["effective_formatter"]["numpy"], np.__version__)
        self.assertFalse(freeze["native_producer_integration"])
        self.assertFalse(freeze["native_memory_qualified"])

    def test_wrong_numpy_version_is_rejected_without_wildcard(self):
        vector = C.ExactVector.from_values(values(1.0))
        with patch.object(np, "__version__", "2.3.4"):
            with self.assertRaises(RuntimeError):
                C.verify_sources()
            with self.assertRaises(RuntimeError):
                C.ExactVector.from_values(values(1.0))
            with self.assertRaises(RuntimeError):
                vector.to_list()
