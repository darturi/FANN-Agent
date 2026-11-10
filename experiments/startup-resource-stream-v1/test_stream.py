import copy
import hashlib
import math
import signal
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import experiment as E
import pc_common as C
import si_stream as H
from test_fixtures import META, VECTOR, rewrite, snapshot

import fannagent.snapshot as module
import fannagent.store as store


class ByteParityTests(unittest.TestCase):
    def check(self, payload, **kw):
        oracle = store.canonical(payload)
        self.assertLessEqual(len(oracle), 4 * 1024**2)
        pos = 0

        def sink(chunk):
            nonlocal pos
            self.assertEqual(chunk, oracle[pos : pos + len(chunk)])
            pos += len(chunk)

        before = copy.deepcopy(payload)
        result = H.framed(payload, store.canonical, sink=sink, **kw)
        self.assertEqual(pos, len(oracle))
        self.assertEqual(result["digest"], hashlib.sha256(oracle).hexdigest())
        self.assertEqual(result["total_bytes"], len(oracle))
        self.assertEqual(payload, before)
        return result

    def test_empty_single_multiple_rows(self):
        for n in (0, 1, 2, 64):
            with self.subTest(n=n):
                self.check(
                    dict(
                        rows=[
                            dict(source_id=i, vector=VECTOR, metadata={"total_votes": 108})
                            for i in range(n)
                        ],
                        fields=META,
                    )
                )

    def test_keys_and_typed_numeric_spelling(self):
        self.check(dict(rows=[dict(z=0, a=-0.0, b=0.0, c=1.0, d=1)], fields=[{"z": 1, "a": False}]))
        self.assertNotEqual(
            self.check(dict(rows=[{"v": 0}], fields=[]))["digest"],
            self.check(dict(rows=[{"v": 0.0}], fields=[]))["digest"],
        )

    def test_original_immutable_metadata_containers(self):
        from pc_interface import freeze

        self.check(
            dict(
                fields=freeze(META),
                rows=[dict(vector=VECTOR, source_id=1, metadata=freeze({"total_votes": 108}))],
            )
        )

    def test_float_boundaries(self):
        self.check(
            dict(
                fields=[],
                rows=[
                    dict(v=v)
                    for v in (
                        5e-324,
                        -2.2250738585072014e-308,
                        1e-6,
                        1e20,
                        math.nextafter(1.0, 2.0),
                        -1.7976931348623157e308,
                    )
                ],
            )
        )

    def test_escaping_nested_unicode(self):
        self.check(
            dict(
                rows=[
                    {"x": ["\u03bb\U0001f600", '\n\r\t\\"', None, True, False, {"z": 1, "a": 2}]}
                ],
                fields=[{"name": "\ud800"}],
            )
        )

    def test_boundaries_drains_and_no_retained_chunks(self):
        for size in (1, 7, 128, 65536):
            with self.subTest(size=size):
                value = self.check(
                    dict(fields=[], rows=[{"v": "x" * 1000} for _ in range(64)]), buffer_max=size
                )
                self.assertLessEqual(value["max_pending_bytes"], size)
        writer = H.Writer()
        writer.feed(b"a" * 65536)
        self.assertEqual(len(writer.buffer), 0)

    def test_original_encoder_only_receives_fields_or_single_row(self):
        payload = dict(rows=[{"x": i} for i in range(64)], fields=[])
        seen = []

        def canonical(value):
            self.assertIsNot(value, payload)
            self.assertIsNot(value, payload["rows"])
            seen.append(id(value))
            return store.canonical(value)

        H.framed(payload, canonical)
        self.assertEqual(seen, [id(payload["fields"]), *[id(r) for r in payload["rows"]]])

    def test_original_encoding_errors(self):
        cycle = {}
        cycle["x"] = cycle
        for value in (float("nan"), float("inf"), object(), cycle):
            payload = dict(fields=[], rows=[{"v": value}])
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises((ValueError, TypeError)) as baseline:
                    store.canonical(payload)
                with self.assertRaises(type(baseline.exception)):
                    H.framed(payload, store.canonical)

    def test_component_caps(self):
        for payload in (
            dict(fields=["x" * 17000], rows=[]),
            dict(fields=[], rows=[{"v": "x" * 66000}]),
        ):
            with self.assertRaises(RuntimeError):
                H.framed(payload, store.canonical)

    def test_total_byte_cap_no_fallback(self):
        with self.assertRaises(RuntimeError):
            H.framed(dict(fields=[], rows=[{"x": 1}]), store.canonical, maximum=10)

    def test_exact_root_keys_and_arrays_required(self):
        for value in ({"rows": []}, {"fields": [], "rows": [], "x": 1}, {"fields": [], "rows": ()}):
            with self.assertRaises(RuntimeError):
                H.framed(value, store.canonical)


class BindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.package = E.build(Path(cls.tmp.name) / "seed", testing=True)
        cfg = C.read(cls.package / "experiment.json")
        cfg.update(fixture_snapshot_rows=40, snapshot_identity=snapshot().identity)
        rewrite(cls.package / "experiment.json", cfg)

    def tearDown(self):
        self.assertIs(module.digest, store.digest)
        H.assert_restored()

    def construct(self):
        return module.Snapshot(
            [
                dict(source_id=i, vector=list(VECTOR), metadata={"total_votes": 108})
                for i in range(40)
            ],
            META,
        )

    def test_actual_constructor_identity_values_matrix_and_query(self):
        baseline = self.construct()
        canonical = store.canonical
        digest = store.digest
        with H.ScopedIdentity(self.package) as scope:
            self.assertIs(store.canonical, canonical)
            self.assertIs(store.digest, digest)
            actual = self.construct()
        self.assertEqual(actual.identity, baseline.identity)
        self.assertEqual(actual.rows, baseline.rows)
        self.assertEqual(actual.source_to_id, baseline.source_to_id)
        self.assertEqual(actual.field_map, baseline.field_map)
        self.assertEqual(actual.data.vectors.tobytes(), baseline.data.vectors.tobytes())
        self.assertEqual(
            actual.data.metadata["m_000000"].tolist(), baseline.data.metadata["m_000000"].tolist()
        )
        q = {
            "id": "x",
            "vector": VECTOR,
            "k": 10,
            "filter": {"field": "total_votes", "op": "gte", "value": 108},
        }
        self.assertEqual(actual.query(q), baseline.query(q))
        self.assertTrue(scope.record["binding_restored"])
        self.assertEqual(scope.record["invocations"], 1)
        self.assertEqual(scope.record["stream"]["component_calls"], 41)

    def test_failure_before_hash_original_validation(self):
        with self.assertRaises(Exception):
            with H.ScopedIdentity(self.package):
                module.Snapshot([], META)

    def test_hash_failure_restores(self):
        with patch.object(H, "framed", side_effect=RuntimeError("injected")):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                with H.ScopedIdentity(self.package):
                    self.construct()

    def test_baseexception_and_deadline_restore(self):
        for error in (KeyboardInterrupt(), TimeoutError("deadline")):
            with self.subTest(error=type(error).__name__):
                with patch.object(H, "framed", side_effect=error):
                    with self.assertRaises(type(error)):
                        with H.ScopedIdentity(self.package):
                            self.construct()

    def test_actual_posix_deadline_signal_restores_binding(self):
        def alarm(number, frame):
            raise TimeoutError("actual handled signal")

        def interrupt(*args, **kwargs):
            signal.raise_signal(signal.SIGUSR1)
            raise AssertionError("Signal handler did not run")

        previous = signal.signal(signal.SIGUSR1, alarm)
        try:
            with patch.object(H, "framed", side_effect=interrupt):
                with self.assertRaisesRegex(TimeoutError, "actual handled signal"):
                    with H.ScopedIdentity(self.package):
                        self.construct()
        finally:
            signal.signal(signal.SIGUSR1, previous)

    def test_nested_and_second_invocation_rejected(self):
        with H.ScopedIdentity(self.package):
            with self.assertRaises(RuntimeError):
                with H.ScopedIdentity(self.package):
                    pass
            self.construct()
        with self.assertRaises(RuntimeError):
            with H.ScopedIdentity(self.package):
                self.construct()
                self.construct()

    def test_cached_snapshot_missing_call_fails(self):
        with self.assertRaisesRegex(RuntimeError, "Exactly one"):
            with H.ScopedIdentity(self.package):
                pass

    def test_unexpected_original_binding_not_overwritten(self):
        original = module.digest

        def other(x):
            return "bad"

        try:
            module.digest = other
            with self.assertRaises(RuntimeError):
                with H.ScopedIdentity(self.package):
                    pass
            self.assertIs(module.digest, other)
        finally:
            module.digest = original

    def test_tampered_binding_restored_and_rejected(self):
        with self.assertRaises(RuntimeError):
            with H.ScopedIdentity(self.package):
                self.construct()
                module.digest = lambda x: "bad"

    def test_scope_rejects_wrong_fields_rows_and_dimension(self):
        for payload in (
            dict(fields=[], rows=[]),
            dict(
                fields=META,
                rows=[
                    dict(source_id=i, vector=[1], metadata={"total_votes": 108}) for i in range(40)
                ],
            ),
        ):
            with self.assertRaises(RuntimeError):
                with H.ScopedIdentity(self.package) as scope:
                    scope.digest(payload)

    def test_nonmain_thread_precondition(self):
        with patch.object(H.threading, "enumerate", return_value=[object(), object()]):
            with self.assertRaises(RuntimeError):
                with H.ScopedIdentity(self.package):
                    pass

    def test_native_preflight_is_bounded_and_no_active_binding(self):
        result = H.preflight(self.package)
        self.assertEqual(result["cases"], 8)
        self.assertLessEqual(result["oracle_bytes"], 1024**2)
        self.assertLessEqual(result["cpu_seconds"], 5)
        H.assert_restored()

    def test_incompatible_preflight_fails(self):
        with patch.object(H, "framed", return_value={"digest": "bad"}):
            with self.assertRaises((KeyError, RuntimeError)):
                H.preflight(self.package)
