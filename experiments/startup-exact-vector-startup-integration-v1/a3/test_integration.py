"""Actual integrated producer/startup with frozen consumers and simulated SQL transport."""

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import exact_vector as X
import integration as I
import numpy as np
from fannagent_pgvector.backend import NativeBackend

from fannagent.errors import AgentError
from fannagent.store import canonical, digest

FIELDS = json.loads((X.PACKAGE / "origin-source.json").read_text())["metadata"]
ORIGINAL = NativeBackend.snapshot


def raw_rows():
    vectors = [[1, -0.0] + [0.0] * 766, [1.0 + 2**-30] + [0.0] * 767]
    return [(i, json.dumps(vectors[i % 2]), 108 + i) for i in range(1, 5)]


class Cursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def execute(self, statement):
        self.connection.executed.append(statement.as_string(None))

    def __iter__(self):
        for index, row in enumerate(self.connection.rows):
            if self.connection.visit:
                self.connection.visit(index)
            yield row

    def __exit__(self, *args):
        self.connection.closed_cursors += 1
        if self.connection.on_close:
            self.connection.on_close()


def backend(rows=None, cls=NativeBackend):
    value = cls.__new__(cls)
    connection = SimpleNamespace(
        rows=raw_rows() if rows is None else rows,
        executed=[],
        closed_cursors=0,
        visit=None,
        on_close=None,
    )
    connection.cursor = lambda: Cursor(connection)
    value.connection_calls = 0

    def connect():
        value.connection_calls += 1
        return connection

    value._connect = connect
    value._snapshot = None
    value.config = SimpleNamespace(
        target=SimpleNamespace(
            id_column="id", vector_column="embedding", schema_name="public", resource="reviews"
        )
    )
    value.store = SimpleNamespace(get=lambda key: {"metadata": copy.deepcopy(FIELDS)})
    value.test_connection = connection
    return value


def specification(rows=None):
    reference = backend(rows)
    original = ORIGINAL(reference)
    return I.FixtureSpec(len(original.rows), canonical(FIELDS), original.identity), original


class ProducerTests(unittest.TestCase):
    def setUp(self):
        self.spec, self.original = specification()
        self.backend = backend()

    def tearDown(self):
        from fannagent import snapshot

        self.assertIs(snapshot.digest, digest)
        self.assertIs(NativeBackend.snapshot, ORIGINAL)
        self.assertNotIn("snapshot", self.backend.__dict__)
        self.assertIsNone(I._LOADING)

    def test_actual_producer_original_sql_constructor_identity_and_matrix(self):
        result = I.load_snapshot(self.backend, self.spec)
        self.assertEqual(result.identity, self.original.identity)
        self.assertEqual(
            canonical([X.plain_row(r) for r in result.rows]), canonical(self.original.rows)
        )
        np.testing.assert_array_equal(
            result.data.vectors.view(np.uint32), self.original.data.vectors.view(np.uint32)
        )
        reference = backend()
        ORIGINAL(reference)
        self.assertEqual(self.backend.test_connection.executed, reference.test_connection.executed)
        self.assertEqual(self.backend.test_connection.closed_cursors, 1)
        self.assertEqual(self.backend.connection_calls, 1)

    def test_vector_is_packed_before_transport_yields_the_next_row(self):
        count = []
        original = X.pack_json_vector

        def pack(text):
            result = original(text)
            count.append(result)
            return result

        self.backend.test_connection.visit = lambda index: self.assertEqual(len(count), index)
        with patch.object(X, "pack_json_vector", pack):
            I.load_snapshot(self.backend, self.spec)
        self.assertEqual(len(count), 4)
        self.assertTrue(all(type(v) is X.PackedVector for v in count))

    def test_owned_cache_reused_without_sql_or_encoding(self):
        first = I.load_snapshot(self.backend, self.spec)
        with patch.object(I, "_produce", side_effect=AssertionError("repeat producer")):
            self.assertIs(I.load_snapshot(self.backend, self.spec), first)
        self.assertEqual(len(self.backend.test_connection.executed), 1)

    def test_foreign_original_list_cache_is_rejected(self):
        self.backend._snapshot = self.original
        with self.assertRaises(RuntimeError):
            I.load_snapshot(self.backend, self.spec)
        self.assertEqual(self.backend.connection_calls, 0)

    def test_metadata_change_rejected_before_connection(self):
        self.backend.store.get = lambda key: {"metadata": []}
        with self.assertRaises(RuntimeError):
            I.load_snapshot(self.backend, self.spec)
        self.assertEqual(self.backend.connection_calls, 0)

    def test_bad_json_restores_instance_and_leaves_no_cache(self):
        self.backend.test_connection.rows[1] = (2, "bad", 108)
        with self.assertRaises(ValueError):
            I.load_snapshot(self.backend, self.spec)
        self.assertIsNone(self.backend._snapshot)
        self.assertEqual(self.backend.test_connection.closed_cursors, 1)

    def test_extra_missing_or_misshapen_rows_rejected(self):
        for rows in (raw_rows()[:-1], raw_rows() + [raw_rows()[0]], [(1, "[]")]):
            with self.subTest(rows=len(rows)):
                value = backend(rows)
                with self.assertRaises((RuntimeError, ValueError)):
                    I.load_snapshot(value, self.spec)
                self.assertIsNone(value._snapshot)
                self.assertNotIn("snapshot", value.__dict__)

    def test_original_norm_validator_failure_restores_digest(self):
        self.backend.test_connection.rows[0] = (1, json.dumps([0.0] * 768), 108)
        with self.assertRaises(AgentError):
            I.load_snapshot(self.backend, self.spec)
        self.assertIsNone(self.backend._snapshot)

    def test_identity_mismatch_does_not_publish_cache(self):
        bad = I.FixtureSpec(4, canonical(FIELDS), "0" * 64)
        with self.assertRaises(RuntimeError):
            I.load_snapshot(self.backend, bad)
        self.assertIsNone(self.backend._snapshot)

    def test_cancellation_and_cursor_close_failure_do_not_publish(self):
        def cancelled(index):
            if index == 1:
                raise KeyboardInterrupt("fixture cancellation")

        self.backend.test_connection.visit = cancelled
        with self.assertRaises(KeyboardInterrupt):
            I.load_snapshot(self.backend, self.spec)
        self.assertIsNone(self.backend._snapshot)
        self.backend.test_connection.visit = None

        def close_failure():
            raise RuntimeError("cursor close failed")

        self.backend.test_connection.on_close = close_failure
        with self.assertRaises(RuntimeError):
            I.load_snapshot(self.backend, self.spec)
        self.assertIsNone(self.backend._snapshot)

    def test_nested_load_is_rejected_and_outer_binding_restored(self):
        self.backend.test_connection.visit = lambda index: I.load_snapshot(self.backend, self.spec)
        with self.assertRaises(RuntimeError):
            I.load_snapshot(self.backend, self.spec)
        self.assertIsNone(self.backend._snapshot)

    def test_instance_tampering_is_restored_before_publication(self):
        self.backend.test_connection.on_close = lambda: setattr(
            self.backend, "snapshot", lambda: None
        )
        with self.assertRaises(RuntimeError):
            I.load_snapshot(self.backend, self.spec)
        self.assertIsNone(self.backend._snapshot)

    def test_native_and_oversized_specifications_fail_closed(self):
        with self.assertRaises(RuntimeError):
            I.native_spec(X.PACKAGE)
        with self.assertRaises(ValueError):
            I.FixtureSpec(247286, canonical(FIELDS), self.spec.identity)


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.package = Path(self.tmp.name)
        self.spec, self.original = specification()
        self.main = {
            name: SimpleNamespace(backend=backend(), closed=False)
            for name in ("native640", "partial640")
        }
        self.factory = SimpleNamespace(snapshot=None, requests={})
        self.write(
            "eligibility.json",
            {
                "source_ids": self.original.source_ids,
                "votes": [r["metadata"]["total_votes"] for r in self.original.rows],
            },
        )
        self.write("experiment.json", {"snapshot_identity": self.original.identity})
        self.queries = [
            {
                "group": "g" + str(i),
                "query": {
                    "schema_version": 2,
                    "id": "g" + str(i) + "-votes108",
                    "vector": [1.0] + [0.0] * 767,
                    "k": 10,
                    "filter": {"field": "m_000000", "op": "gte", "value": 108},
                },
            }
            for i in range(200)
        ]
        self.query_file()

    def write(self, name, value):
        from pc_common import encoded

        (self.package / name).write_bytes(encoded(value))

    def query_file(self):
        (self.package / "queries.jsonl").write_bytes(
            b"\n".join(canonical(q) for q in self.queries) + b"\n"
        )

    def test_actual_startup_eligibility_200_admissions_and_shared_aliases(self):
        phases = []
        items, proof = I.prepare_requests(
            self.main, self.factory, self.package, self.spec, phases.append
        )
        self.assertEqual(len(items), 200)
        self.assertEqual(proof["snapshot_identity"], self.original.identity)
        self.assertEqual(len(self.factory.requests), 200)
        self.assertEqual(phases, ["snapshot_load", "snapshot_identity", "request_admission"])
        self.assertTrue(
            all(r.backend._snapshot is self.factory.snapshot for r in self.main.values())
        )
        self.assertEqual(self.main["partial640"].backend.connection_calls, 0)
        self.assertTrue(all(r.backend._packed_spec is self.spec for r in self.main.values()))

    def test_eligibility_failure_rolls_back_all_publication(self):
        self.write("eligibility.json", {"source_ids": [], "votes": []})
        with self.assertRaises(RuntimeError):
            I.prepare_requests(self.main, self.factory, self.package, self.spec)
        self.assertIsNone(self.factory.snapshot)
        self.assertFalse(self.factory.requests)
        self.assertTrue(all(r.backend._snapshot is None for r in self.main.values()))
        self.assertTrue(all("_packed_spec" not in r.backend.__dict__ for r in self.main.values()))

    def test_admission_failure_rolls_back_before_aliases(self):
        self.queries[0]["query"]["k"] = 5
        self.query_file()
        with self.assertRaises(ValueError):
            I.prepare_requests(self.main, self.factory, self.package, self.spec)
        self.assertIsNone(self.factory.snapshot)
        self.assertTrue(all(r.backend._snapshot is None for r in self.main.values()))

    def test_closed_reader_and_repeated_startup_rejected(self):
        self.main["partial640"].closed = True
        with self.assertRaises(RuntimeError):
            I.prepare_requests(self.main, self.factory, self.package, self.spec)
        self.main["partial640"].closed = False
        I.prepare_requests(self.main, self.factory, self.package, self.spec)
        with self.assertRaises(RuntimeError):
            I.prepare_requests(self.main, self.factory, self.package, self.spec)

    def test_factory_routes_packed_producer_and_preserves_search_prohibitions(self):
        value = I.factory_type()(
            NativeBackend,
            Path("/bundle"),
            {"native640": Path("/native"), "partial640": Path("/partial")},
            {"native640": {}, "partial640": {}},
            None,
            None,
            lambda *a: None,
            spec=self.spec,
        )
        selected = backend(cls=value.classes["native640"])
        result = selected.snapshot()
        self.assertEqual(result.identity, self.spec.identity)
        for name in ("execute", "query", "run", "prepare", "_statement", "exact_reference"):
            with self.assertRaises(RuntimeError):
                getattr(selected, name)({})

    def test_factory_marks_shared_cache_for_later_readers(self):
        value = I.factory_type()(
            NativeBackend,
            Path("/bundle"),
            {"native640": Path("/native"), "partial640": Path("/partial")},
            {"native640": {}, "partial640": {}},
            None,
            None,
            lambda *a: None,
            spec=self.spec,
        )
        value.snapshot = I.load_snapshot(self.main["native640"].backend, self.spec)
        later = backend()
        later._snapshot = value.snapshot
        reader = SimpleNamespace(backend=later)
        with patch("sr_interface.Factory.create", return_value=reader):
            self.assertIs(value.create("partial640", "later"), reader)
        self.assertIs(I.load_snapshot(later, self.spec), value.snapshot)


class NativeReleaseTests(unittest.TestCase):
    """Synthetic metadata only; never instantiate native-size vectors or open a DB."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.package = Path(self.tmp.name) / "torch-startup-exact-vector-resource-v1-fixture"
        self.package.mkdir()
        (self.package / "RESOURCE-CONTRACT.json").write_bytes(
            (X.PACKAGE / "RESOURCE-CONTRACT.json").read_bytes()
        )
        self.release = {
            "name": "torch-startup-exact-vector-resource-v1",
            "schema": "startup-exact-vector.resource-release.v1",
            "integration_tests": 56,
            "code_sha256": I.code_hashes(),
            "full_B2f_released": False,
            "scope": {
                "allocations": 1,
                "wall_seconds": 3600,
                "physical_cpus": 4,
                "memory_gib": 32,
                "ANN_searches": 0,
                "exact_searches": 0,
                "snapshot_scans": 1,
                "data_verification_scans": 4,
                "reserve_bytes": 2 * 1024**3,
                "workspace_bytes": 2 * 1024**3,
                "positive_limit_events_allowed": False,
                "cache_subtraction": False,
            },
        }
        target = json.loads((X.PACKAGE / "IMAGE-REFERENCE.json").read_text())
        recipe = {
            name: hashlib.sha256((X.PACKAGE / name).read_bytes()).hexdigest()
            for name in json.loads((X.PACKAGE / "RECIPE-FILES.json").read_text())["files"]
        }
        for kind, count in (("main", 128), ("integration", 56)):
            for phase in ("source", "sealed"):
                receipt = {
                    "status": "pass",
                    "tests_run": count,
                    "failures": 0,
                    "errors": 0,
                    "python": "3.12.15",
                    "actual_provenance": target,
                    "source_files_sha256": I.code_hashes(),
                    "recipe_files_sha256": recipe,
                    "skipped": 0,
                    "denied_actions": 0,
                }
                (self.package / f"{kind}-{phase}.json").write_bytes(canonical(receipt))
        self.seal()

    def seal(self):
        phases = {
            f"{kind}-{phase}.json": hashlib.sha256(
                (self.package / f"{kind}-{phase}.json").read_bytes()
            ).hexdigest()
            for kind in ("main", "integration")
            for phase in ("source", "sealed")
        }
        audit = {
            "status": "pass",
            "phase_receipts_sha256": phases,
            "final_integrity_verified": True,
            "guard_bindings_restored": True,
            "denied_actions": 0,
            "image_sha256": "7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a",
        }
        (self.package / "QUALIFICATION-AUDIT.json").write_bytes(canonical(audit))
        self.release["qualification_audit_sha256"] = hashlib.sha256(canonical(audit)).hexdigest()
        (self.package / "NATIVE-RELEASE.json").write_bytes(canonical(self.release))
        files = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in self.package.iterdir()
            if p.name != "manifest.json"
        }
        (self.package / "manifest.json").write_bytes(canonical({"files": files}))

    def test_metadata_only_complete_release_yields_fixed_native_spec(self):
        mount = self.package.parent / "patch"
        self.package.rename(mount)
        self.package = mount
        spec = I.native_spec(self.package)
        self.assertEqual(spec.rows, 247286)
        self.assertEqual(
            spec.identity, "54282be380f20bfab05a44e6260e116435aecf5a289a258ae8164a23c187b303"
        )
        I.validate_spec(spec)

    def test_wrong_code_or_relaxed_resource_rule_rejected(self):
        self.release["code_sha256"] = {}
        self.seal()
        with self.assertRaises(RuntimeError):
            I.native_spec(self.package)
        self.release["code_sha256"] = I.code_hashes()
        self.release["scope"]["memory_gib"] = 64
        self.seal()
        with self.assertRaises(RuntimeError):
            I.native_spec(self.package)

    def test_partial_legacy_or_integrated_target_proof_rejected(self):
        for name in ("main-source.json", "integration-sealed.json"):
            path = self.package / name
            original = path.read_bytes()
            receipt = json.loads(original)
            receipt["tests_run"] -= 1
            path.write_bytes(canonical(receipt))
            self.seal()
            with self.assertRaises(RuntimeError):
                I.native_spec(self.package)
            path.write_bytes(original)

    def test_unlocked_extra_file_and_changed_receipt_rejected(self):
        extra = self.package / "unexpected.json"
        extra.write_text("{}")
        with self.assertRaises(RuntimeError):
            I.native_spec(self.package)
        extra.unlink()
        (self.package / "main-source.json").write_text("{}")
        with self.assertRaises(RuntimeError):
            I.native_spec(self.package)


if __name__ == "__main__":
    unittest.main(verbosity=2)
