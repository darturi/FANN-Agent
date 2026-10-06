# ruff: noqa: E501
import ast
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_workflow import configuration

from fannagent.api import (
    AgentError,
    Capabilities,
    IncompatibleExtension,
    LegacyRun,
    UnsupportedCapability,
    require_capabilities,
    validate_capabilities,
    validate_policy,
)
from fannagent.api.conformance import check_descriptor, check_observation
from fannagent.backends import discover, extension
from fannagent.backends.fake import PROFILE
from fannagent.cli import report, status
from fannagent.controller import open_run
from fannagent.snapshot import Snapshot
from fannagent.store import Store


def test_sdk_import_does_not_load_database_or_model_modules():
    code = 'import sys; import fannagent.api; assert not any(n.startswith(("fannbench", "psycopg", "litellm", "minisweagent", "fannagent_pgvector", "elasticsearch")) for n in sys.modules)'
    subprocess.run([sys.executable, "-c", code], check=True)


def test_core_import_boundary():
    root = Path(__file__).parents[1] / "src/fannagent"
    for path in root.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                names = [n.name for n in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            assert not any(
                n.startswith(("fannbench", "psycopg", "fannagent_pgvector", "elasticsearch"))
                for n in names
            ), path


def test_duplicate_and_unsupported_descriptor(monkeypatch):
    import fannagent.backends as loader

    monkeypatch.setattr(
        loader,
        "entry_points",
        lambda **kw: [SimpleNamespace(name="dupe"), SimpleNamespace(name="dupe")],
    )
    with pytest.raises(IncompatibleExtension, match="duplicate"):
        discover()
    manifest = extension_fake_manifest()
    with pytest.raises(IncompatibleExtension, match="API"):
        replace(manifest, api_versions=(2,)).validate()
    monkeypatch.setattr(
        loader, "entry_points", lambda **kw: [SimpleNamespace(name="bad", load=lambda: object())]
    )
    with pytest.raises(IncompatibleExtension, match="descriptor"):
        extension("bad")

    class Malformed:
        def manifest(self):
            return {}

        def normalize_options(self, options, origin):
            return options

        def create(self, options, context):
            return object()

    monkeypatch.setattr(
        loader, "entry_points", lambda **kw: [SimpleNamespace(name="bad", load=lambda: Malformed())]
    )
    with pytest.raises(IncompatibleExtension, match="malformed"):
        extension("bad")


def extension_fake_manifest():
    from fannagent.backends.fake import extension as fake

    return fake.manifest()


def test_capability_requirements_precede_study():
    backend = SimpleNamespace(describe_capabilities=lambda: Capabilities("fake", stopping=True))
    with pytest.raises(IncompatibleExtension, match="stopping"):
        validate_capabilities(backend, extension_fake_manifest())
    with pytest.raises(UnsupportedCapability):
        require_capabilities(backend, study=True)


def test_profile_hash_is_semantic_and_policy_bound():
    changed = PROFILE.model_copy(update={"checkpoint_interval": 9})
    assert changed.fingerprint != PROFILE.fingerprint
    cosmetic = PROFILE.model_copy(
        update={"guidance": "changed wording", "native_registry_hash": "separate-wire-identity"}
    )
    assert cosmetic.fingerprint == PROFILE.fingerprint
    policy = validate_policy(PROFILE.scripted_policy, PROFILE)
    with pytest.raises(AgentError, match="incompatible"):
        validate_policy(policy, changed)


def test_typed_identifier_mapping_has_no_collisions():
    rows = [{"source_id": i, "vector": [1.0, 0.0], "metadata": {}} for i in (1, "1", "01")]
    snapshot = Snapshot(rows, [])
    assert snapshot.analysis_id(1) != snapshot.analysis_id("1")
    assert snapshot.source_ids[snapshot.analysis_id("01")] == "01"
    with pytest.raises(AgentError):
        Snapshot([{**rows[0], "source_id": True}], [])


def test_conformance_helpers(tmp_path):
    _, _, backend = open_run(tmp_path / "run", configuration())
    check_descriptor(extension_fake_manifest(), backend)
    query = backend.snapshot().query(
        {"id": "check", "k": 10, "vector": backend.snapshot().rows[0]["vector"]}
    )
    evidence = check_observation(backend, query)
    assert evidence["checkpoints"][0]["work"]["unit"] == "synthetic_batches"


def test_legacy_inspection_does_not_rewrite_sqlite(tmp_path, capsys):
    store = Store(tmp_path / "legacy", create=True)
    store.set("config", {"model": configuration().model.model_dump(mode="json")})
    store.set("report", store.put("report", {"status": "no_recommendation", "valid": True}))
    with store.connect() as db:
        db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    before = store.path.read_bytes()
    status(store.root)
    report(store.root)
    assert before == store.path.read_bytes()
    with pytest.raises(LegacyRun, match="legacy"):
        open_run(store.root)
    assert before == store.path.read_bytes()


def test_truncated_evidence_cannot_label_a_stop(tmp_path):
    from dataclasses import replace

    from fannagent.study import Study

    c, s, backend = open_run(tmp_path / "run", configuration())
    s.set("prepared", backend.prepare_copy().serialize())
    study = Study(c, s, backend)
    original = backend.collect_evidence
    backend.collect_evidence = lambda result: replace(original(result), truncated=True)
    labels = study.stop_labels(study.development[0]["query"])
    assert labels["status"] == "truncated" and labels["cost"] is None
    assert not labels["labels"]


def test_profile_mismatch_cannot_label_a_stop(tmp_path):
    from dataclasses import replace

    from fannagent.study import Study

    c, s, backend = open_run(tmp_path / "run", configuration())
    s.set("prepared", backend.prepare_copy().serialize())
    study = Study(c, s, backend)
    original = backend.collect_evidence
    backend.collect_evidence = lambda result: replace(
        original(result), runtime_profile_hash="incompatible"
    )
    with pytest.raises(AgentError, match="identity"):
        study.stop_labels(study.development[0]["query"])


def test_extension_artifacts_are_namespaced(tmp_path):
    _, store, backend = open_run(tmp_path / "run", configuration())
    core = store.put("private_evaluator", {"protected": True})
    with pytest.raises(AgentError, match="namespace"):
        backend.context.artifacts.read(core)
    own = backend.context.artifacts.put("manifest", {"owned": True})
    assert backend.context.artifacts.read(own) == {"owned": True}


def test_nonportable_policy_payload_is_rejected():
    with pytest.raises(AgentError, match="invalid policy"):
        validate_policy(
            {"name": "invalid", "root": "continue", "shape_model": {"x": float("nan")}}, PROFILE
        )


def test_mixed_work_units_cannot_establish_hardness(tmp_path):
    from dataclasses import replace

    from fannagent.api import WorkMeasure
    from fannagent.study import Study

    c, s, backend = open_run(tmp_path / "run", configuration())
    s.set("prepared", backend.prepare_copy().serialize())
    study = Study(c, s, backend)
    original = backend.collect_evidence

    def inconsistent(result):
        evidence = original(result)
        return replace(
            evidence,
            checkpoints=tuple(
                replace(x, work=WorkMeasure(x.work.value, "other_units"))
                for x in evidence.checkpoints
            ),
        )

    backend.collect_evidence = inconsistent
    with pytest.raises(AgentError, match="work units"):
        study.stop_labels(study.development[0]["query"])
