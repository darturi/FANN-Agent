"""Bounded actual producer/runtime integration and strict metadata-only replay."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import adaptive_integration as I
import adaptive_reference as R
import ev_startup
import exact_codec as X
import experiment as E
import numpy as np
import pc_common as C
import test_fixtures as F
from fannagent_pgvector.backend import NativeBackend
from test_integration import ORIGINAL, backend, raw_rows, specification

from fannagent.store import canonical, digest


class ProducerTests(unittest.TestCase):
    def setUp(self):
        self.spec, self.original = specification()
        self.backend = backend()

    def tearDown(self):
        import fannagent.snapshot as snapshot

        self.assertIs(snapshot.digest, digest)
        self.assertIs(NativeBackend.snapshot, ORIGINAL)
        self.assertNotIn("snapshot", self.backend.__dict__)
        self.assertIsNone(I._LOADING)

    def test_mixed_payload_original_identity_sql_constructor_and_matrix(self):
        result = I.load_snapshot(self.backend, self.spec)
        self.assertEqual(result.identity, self.original.identity)
        self.assertEqual(
            canonical([X.plain_row(r) for r in result.rows]), canonical(self.original.rows)
        )
        np.testing.assert_array_equal(
            result.data.vectors.view(np.uint32), self.original.data.vectors.view(np.uint32)
        )
        self.assertEqual([r["vector"].compact for r in result.rows], [False, True, False, True])
        reference = backend()
        ORIGINAL(reference)
        self.assertEqual(self.backend.test_connection.executed, reference.test_connection.executed)
        self.assertEqual(self.backend.test_connection.closed_cursors, 1)
        self.assertEqual(self.backend.connection_calls, 1)
        self.assertTrue(result.data.vectors.flags.owndata)

    def test_each_vector_packed_before_next_transport_row(self):
        count = []
        original = X.pack_json_vector

        def pack(text):
            value = original(text)
            count.append(value)
            return value

        self.backend.test_connection.visit = lambda index: self.assertEqual(len(count), index)
        with patch.object(X, "pack_json_vector", pack):
            I.load_snapshot(self.backend, self.spec)
        self.assertEqual(len(count), 4)

    def test_owned_cache_reused_without_sql(self):
        first = I.load_snapshot(self.backend, self.spec)
        with patch.object(I, "_produce", side_effect=AssertionError("repeat")):
            self.assertIs(I.load_snapshot(self.backend, self.spec), first)
        self.assertEqual(self.backend.connection_calls, 1)

    def test_foreign_cache_rejected_before_connection(self):
        self.backend._snapshot = self.original
        with self.assertRaises(RuntimeError):
            I.load_snapshot(self.backend, self.spec)
        self.assertEqual(self.backend.connection_calls, 0)

    def test_metadata_rejected_before_connection(self):
        self.backend.store.get = lambda key: {"metadata": []}
        with self.assertRaises(RuntimeError):
            I.load_snapshot(self.backend, self.spec)
        self.assertEqual(self.backend.connection_calls, 0)

    def test_bad_json_restores_binding_and_cache(self):
        self.backend.test_connection.rows[1] = (2, "bad", 108)
        with self.assertRaises(ValueError):
            I.load_snapshot(self.backend, self.spec)
        self.assertIsNone(self.backend._snapshot)

    def test_row_count_and_shape_rejected(self):
        for rows in (raw_rows()[:-1], raw_rows() + [raw_rows()[0]], [(1, "[]")]):
            value = backend(rows)
            with self.assertRaises((RuntimeError, ValueError)):
                I.load_snapshot(value, self.spec)
            self.assertIsNone(value._snapshot)
            self.assertNotIn("snapshot", value.__dict__)

    def test_constructor_failure_restores_binding(self):
        self.backend.test_connection.rows[0] = (1, json.dumps([0.0] * 768), 108)
        with self.assertRaises(Exception):
            I.load_snapshot(self.backend, self.spec)
        self.assertIsNone(self.backend._snapshot)

    def test_interrupt_restores_binding_and_cache(self):
        def interrupt(index):
            if index == 1:
                raise KeyboardInterrupt("fixture")

        self.backend.test_connection.visit = interrupt
        with self.assertRaises(KeyboardInterrupt):
            I.load_snapshot(self.backend, self.spec)
        self.assertIsNone(self.backend._snapshot)

    def test_encoder_failure_restores_binding(self):
        with patch.object(X, "pack_json_vector", side_effect=RuntimeError("encoder")):
            with self.assertRaises(RuntimeError):
                I.load_snapshot(self.backend, self.spec)
        self.assertIsNone(self.backend._snapshot)

    def test_nested_load_rejected(self):
        self.backend.test_connection.visit = lambda index: I.load_snapshot(self.backend, self.spec)
        with self.assertRaises(RuntimeError):
            I.load_snapshot(self.backend, self.spec)
        self.assertIsNone(self.backend._snapshot)

    def test_native_and_oversize_specs_rejected(self):
        with self.assertRaises(RuntimeError):
            I.native_spec(E.REFERENCE)
        with self.assertRaises(RuntimeError):
            I.validate_spec(object())
        with self.assertRaises(ValueError):
            I.FixtureSpec(247286, self.spec.fields_json, self.spec.identity)


class StartupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.seed = E.build(Path(cls.tmp.name) / "seed", testing=True)

    def fixture(self, fault=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        return root, F.runtime_fixture(root / "actual", self.seed, fault, adaptive=True)

    def test_actual_compact_startup_retention_limits_and_cleanup(self):
        root, result = self.fixture()
        self.assertIsNone(result["error"])
        status = result["status"]
        self.assertEqual(status["status"], "complete")
        self.assertEqual(status["full_scans"], {"data": 4, "snapshot": 1})
        self.assertEqual(status["reader_connections"], 10)
        self.assertEqual(status["maximum_live_readers"], 6)
        self.assertEqual(status["result"]["admitted_requests"], 200)
        self.assertEqual(status["result"]["executed_requests"], 0)
        self.assertEqual(status["backend_searches"], 0)
        out = result["out"]
        retained = C.read(out / "ev-retention.json")
        self.assertEqual(len({r["snapshot_token"] for r in retained["records"]}), 1)
        for row in retained["records"]:
            self.assertEqual(
                row["adaptive"],
                dict(compact=40, raw64=0, payload_bytes=40 * 3072, matrix_bytes=40 * 768 * 4),
            )
            self.assertTrue(row["retained"])
        self.assertEqual(C.read(out / "source-before.json"), C.read(out / "source-after.json"))
        self.assertTrue(C.read(out / "cleanup.json")["databases_stopped"])
        self.assertTrue(C.read(out / "LOCK.json")["complete"])
        ev_startup.assert_restored()

    def test_actual_raw64_fallback_startup(self):
        with patch.object(F, "VECTOR", [1 + 2**-30] + [0.0] * 767):
            root, result = self.fixture()
        self.assertIsNone(result["error"])
        for row in C.read(result["out"] / "ev-retention.json")["records"]:
            self.assertEqual(row["adaptive"]["raw64"], 40)
            self.assertEqual(row["adaptive"]["payload_bytes"], 40 * 6144)

    def test_exact_target_reference_data_and_actual_local_rejection(self):
        target = R.static(self.seed)["target_reference"]
        local = C.read(self.seed / "reference/DRIVER-REFERENCE.json")
        self.assertEqual(R.require_actual(self.seed, target, "target"), "target")
        self.assertEqual(R.require_actual(self.seed, local, "local"), "local")
        with self.assertRaisesRegex(RuntimeError, "Exact target"):
            R.require_actual(self.seed, local, "target")
        for key in target:
            bad = copy.deepcopy(target)
            bad[key] = None
            with self.assertRaises(RuntimeError):
                R.require_actual(self.seed, bad, "target")

    def test_literal_preflight_exact_bits_and_fallback(self):
        proof = R.literal_preflight(self.seed)
        self.assertEqual(proof["cases"], 8)
        self.assertGreater(proof["compact_cases"], 0)
        self.assertGreater(proof["raw64_cases"], 0)
        self.assertLessEqual(proof["cpu_seconds"], 1)

    def test_all_native_release_paths_held(self):
        for profile in ("legacy", "adaptive"):
            self.assertIs(C.protocol(profile)["native_handoff_released"], False)
        with self.assertRaisesRegex(RuntimeError, "all spent allocations closed"):
            C.require_native_release(self.seed)
        with self.assertRaises(RuntimeError):
            E.build(Path(self.tmp.name) / "never-native")

    def replay_fixture(self):
        root, actual = self.fixture()
        self.assertIsNone(actual["error"])
        campaign, package = F.complete_return(root, actual)
        run = campaign / "run"
        proof = C.read(run / "ev-runtime-preflight.json")
        proof["adaptive_origins"] = {
            n: "/patch/" + n + ".py"
            for n in ("exact_codec", "adaptive_integration", "adaptive_reference")
        }
        F.rewrite(run / "ev-runtime-preflight.json", proof)
        retained = C.read(run / "ev-retention.json")
        for row in retained["records"]:
            n = row["rows"]
            row["adaptive"] = dict(
                compact=n, raw64=0, payload_bytes=n * 3072, matrix_bytes=n * 768 * 4
            )
        F.rewrite(run / "ev-retention.json", retained)
        F.relock(run)
        return root, campaign, package

    def test_metadata_only_replay_cannot_qualify_new_codec(self):
        root, campaign, package = self.replay_fixture()
        result = E.analyze(campaign, root / "analysis", package)
        self.assertEqual(result["outcome"], "offline_adaptive_startup_replay_native_held")
        self.assertIs(result["native_correction_qualified"], False)
        self.assertIs(result["native_memory_qualified"], False)

    def test_relocked_adaptive_proof_tampering_rejected(self):
        root, campaign, package = self.replay_fixture()
        run = campaign / "run"
        mutations = [
            ("ev-runtime-preflight.json", "adaptive_code_sha256", {}),
            ("ev-runtime-preflight.json", "adaptive_target_reference_sha256", "0" * 64),
            ("ev-runtime-preflight.json", "adaptive_origins", {}),
            ("ev-runtime-preflight.json", "native_correction_qualified", True),
            ("adaptive-preflight.json", "cases", 8.0),
            ("adaptive-preflight.json", "compact_cases", True),
            ("adaptive-preflight.json", "original_numeric_bytes", 0),
            ("adaptive-preflight.json", "cpu_seconds", True),
            ("adaptive-preflight.json", "real_SQL", False),
            ("adaptive-preflight.json", "real_SQL", 1),
            ("identity-stream.json", "adaptive_code_sha256", {}),
        ]
        for name, key, bad in mutations:
            with self.subTest(name=name, key=key):
                original = C.read(run / name)
                changed = copy.deepcopy(original)
                changed[key] = bad
                F.rewrite(run / name, changed)
                F.relock(run)
                with self.assertRaises((ValueError, RuntimeError)):
                    E.analyze(campaign, root / "analysis", package)
                self.assertFalse((root / "analysis").exists())
                F.rewrite(run / name, original)

    def test_resealed_source_and_forged_source_map_rejected(self):
        import adaptive_contract as guard

        root, campaign, package = self.replay_fixture()
        codec = package / "exact_codec.py"
        codec.write_text(codec.read_text() + "\n# changed after fixture seal\n")
        cfg = C.read(package / "experiment.json")
        cfg["adaptive_code_sha256"] = guard.code_map(package)
        F.rewrite(package / "experiment.json", cfg)
        F.reseal(package)
        with self.assertRaises(ValueError):
            C.verify(package)

    def test_relocked_retention_count_type_or_bytes_rejected(self):
        root, campaign, package = self.replay_fixture()
        run = campaign / "run"
        original = C.read(run / "ev-retention.json")
        for key, value in (
            ("compact", True),
            ("raw64", -1),
            ("payload_bytes", 0),
            ("matrix_bytes", 0),
        ):
            changed = copy.deepcopy(original)
            changed["records"][0]["adaptive"][key] = value
            F.rewrite(run / "ev-retention.json", changed)
            F.relock(run)
            with self.assertRaises(ValueError):
                E.analyze(campaign, root / "analysis", package)

    def test_actual_failure_eligibility(self):
        self.failed_runtime("eligibility")

    def test_actual_failure_snapshot_identity(self):
        self.failed_runtime("snapshot_identity")

    def test_actual_failure_stream_hash(self):
        self.failed_runtime("stream_hash")

    def test_actual_failure_stream_interrupt(self):
        self.failed_runtime("stream_interrupt")

    def test_actual_failure_stream_deadline(self):
        self.failed_runtime("stream_deadline")

    def test_actual_failure_stream_constructor(self):
        self.failed_runtime("stream_constructor")

    def test_actual_failure_preflight(self):
        self.failed_runtime("preflight")

    def test_actual_failure_sampler(self):
        self.failed_runtime("sampler")

    def test_actual_failure_second_server(self):
        self.failed_runtime("second_server")

    def test_actual_failure_cleanup(self):
        self.failed_runtime("cleanup")

    def test_actual_failure_observer_cleanup(self):
        self.failed_runtime("observer_cleanup")

    def test_actual_failure_cleanup_cancel(self):
        self.failed_runtime("cleanup_cancel")

    def test_actual_failure_cleanup_enter_cancel(self):
        self.failed_runtime("cleanup_enter_cancel")

    def test_actual_failure_cleanup_deadline(self):
        self.failed_runtime("cleanup_deadline")

    def test_actual_failure_cancel_before_sql(self):
        self.failed_runtime("cancel_before_sql")

    def failed_runtime(self, fault):
        root, result = self.fixture(fault)
        self.assertEqual(result["status"]["status"], "failed")
        self.assertFalse(C.read(result["out"] / "LOCK.json")["complete"])
        self.assertEqual(result["status"]["backend_searches"], 0)
        ev_startup.assert_restored()
