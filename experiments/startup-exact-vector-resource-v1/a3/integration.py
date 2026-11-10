"""Isolated A3 producer/startup integration; native resource release remains closed."""

import hashlib
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from types import MethodType

import exact_vector as X

_LOADING = None


@dataclass(frozen=True)
class FixtureSpec:
    rows: int
    fields_json: bytes
    identity: str

    def __post_init__(self):
        if (
            type(self.rows) is not int
            or not 1 <= self.rows <= 64
            or type(self.fields_json) is not bytes
            or not isinstance(json.loads(self.fields_json), list)
            or len(self.identity) != 64
            or any(c not in "0123456789abcdef" for c in self.identity)
        ):
            raise ValueError("Explicit <=64-row fixture specification required")


@dataclass(frozen=True)
class NativeSpec:
    rows: int
    fields_json: bytes
    identity: str
    package: Path


def code_hashes():
    here = Path(__file__).resolve().parent
    proto = Path(X.__file__).resolve().parent
    files = {
        name: here / name for name in ("integration.py", "run_checks.py", "test_integration.py")
    }
    files.update({name: proto / name for name in ("exact_vector.py", "test_exact_vector.py")})
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()}


def native_spec(package):
    """A future, separately sealed startup resource package must carry all release proofs."""
    package = Path(package)
    if (
        not package.is_absolute()
        or package.is_symlink()
        or package.resolve() == X.PACKAGE.resolve()
    ):
        raise RuntimeError(
            "Only a separate absolute startup-resource release can authorize native rows"
        )
    try:
        manifest = json.loads((package / "manifest.json").read_text())["files"]
        if any(p.is_symlink() for p in package.rglob("*")):
            raise RuntimeError("Native release symlink rejected")
        actual_files = {str(p.relative_to(package)) for p in package.rglob("*") if p.is_file()}
        allowed = {"manifest.json"}
        binding = package / "submission-binding.json"
        if binding.exists():
            value = json.loads(binding.read_text())
            campaign = Path(value["campaign"])
            if (
                set(value) != {"campaign", "package_manifest_sha256"}
                or value["package_manifest_sha256"]
                != hashlib.sha256((package / "manifest.json").read_bytes()).hexdigest()
                or campaign.parent != Path("/home/dar579/torch-reviews-results")
                or not campaign.name.startswith("reviews-startup-exact-vector-resource-v1-")
            ):
                raise RuntimeError("Native resource binding differs")
            allowed.add("submission-binding.json")
        if actual_files != set(manifest) | allowed:
            raise RuntimeError("Unexpected or missing native release file")
        for name, expected in manifest.items():
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts:
                raise RuntimeError("Unsafe native release path")
            if hashlib.sha256((package / relative).read_bytes()).hexdigest() != expected:
                raise RuntimeError("Native release file changed")
        required = {
            "NATIVE-RELEASE.json",
            "QUALIFICATION-AUDIT.json",
            "RESOURCE-CONTRACT.json",
            *[
                f"{kind}-{phase}.json"
                for kind in ("main", "integration")
                for phase in ("source", "sealed")
            ],
        }
        if not required.issubset(manifest):
            raise RuntimeError("Unpinned native release proofs")
        if (
            hashlib.sha256((package / "RESOURCE-CONTRACT.json").read_bytes()).hexdigest()
            != "a4120866fea72befae75e485bc05bc7265314eb64b85839e5436e4c480339b90"
        ):
            raise RuntimeError("Original resource/margin/no-OOM-event contract changed")
        release = json.loads((package / "NATIVE-RELEASE.json").read_text())
        expected_scope = {
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
        }
        target = json.loads((X.PACKAGE / "IMAGE-REFERENCE.json").read_text())
        recipe = {
            name: hashlib.sha256((X.PACKAGE / name).read_bytes()).hexdigest()
            for name in json.loads((X.PACKAGE / "RECIPE-FILES.json").read_text())["files"]
        }
        if (
            release["schema"] != "startup-exact-vector.resource-release.v1"
            or release["name"] != "torch-startup-exact-vector-resource-v1"
            or release["scope"] != expected_scope
            or release["code_sha256"] != code_hashes()
            or release["full_B2f_released"] is not False
        ):
            raise RuntimeError("Native release scope or current code mismatch")
        audit_path = package / "QUALIFICATION-AUDIT.json"
        audit = json.loads(audit_path.read_text())
        phase_hashes = {
            f"{kind}-{phase}.json": hashlib.sha256(
                (package / f"{kind}-{phase}.json").read_bytes()
            ).hexdigest()
            for kind in ("main", "integration")
            for phase in ("source", "sealed")
        }
        if (
            release["qualification_audit_sha256"]
            != hashlib.sha256(audit_path.read_bytes()).hexdigest()
            or audit["status"] != "pass"
            or audit["phase_receipts_sha256"] != phase_hashes
            or audit["final_integrity_verified"] is not True
            or audit["guard_bindings_restored"] is not True
            or audit["denied_actions"] != 0
            or audit["image_sha256"]
            != "7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a"
        ):
            raise RuntimeError("Native target audit/final guard evidence differs")
        for kind, count in (("main", 128), ("integration", release["integration_tests"])):
            if kind == "integration" and count != 56:
                raise RuntimeError("Complete integrated suite required")
            for phase in ("source", "sealed"):
                receipt = json.loads((package / f"{kind}-{phase}.json").read_text())
                if (
                    receipt["status"] != "pass"
                    or receipt["tests_run"] != count
                    or receipt["failures"]
                    or receipt["errors"]
                    or receipt["python"] != "3.12.15"
                    or receipt["actual_provenance"] != target
                ):
                    raise RuntimeError("Incomplete exact-target correctness proof")
                if kind == "integration" and (
                    receipt["source_files_sha256"] != code_hashes()
                    or receipt["denied_actions"]
                    or receipt["skipped"]
                ):
                    raise RuntimeError("Integrated proof/current source mismatch")
                if kind == "main" and receipt["recipe_files_sha256"] != recipe:
                    raise RuntimeError("Original128-case recipe changed")
        fields = json.loads((X.PACKAGE / "origin-source.json").read_text())["metadata"]
        from fannagent.store import canonical

        return NativeSpec(
            247286,
            canonical(fields),
            "54282be380f20bfab05a44e6260e116435aecf5a289a258ae8164a23c187b303",
            package,
        )
    except (OSError, KeyError, ValueError, TypeError) as error:
        raise RuntimeError("Native startup resource release is not qualified") from error


def validate_spec(spec):
    if type(spec) is FixtureSpec:
        return
    if type(spec) is not NativeSpec or native_spec(spec.package) != spec:
        raise RuntimeError("Unqualified native/unknown integration specification")


class Identity(X.FixtureIdentity):
    def __init__(self, spec):
        super().__init__()
        self.spec = spec

    def digest(self, payload):
        self.calls += 1
        if (
            X._ACTIVE is not self
            or self.calls != 1
            or type(payload) is not dict
            or set(payload) != {"rows", "fields"}
            or type(payload["rows"]) is not list
            or len(payload["rows"]) != self.spec.rows
            or type(payload["fields"]) is not list
            or self.store.canonical(payload["fields"]) != self.spec.fields_json
        ):
            raise RuntimeError("Integrated identity count/field/scope mismatch")
        self.record = self.stream.framed(payload, self.canonical)
        if self.record["digest"] != self.spec.identity:
            raise RuntimeError("Integrated exact original identity mismatch")
        return self.record["digest"]


def _produce(backend, spec):
    """Original client cursor/SQL/constructor; pack one decoded vector before append."""
    from fannagent_pgvector.profiles import DATA_PROFILE
    from psycopg import sql

    from fannagent.snapshot import Snapshot
    from fannagent.store import canonical

    fields = backend.store.get("source_manifest")["metadata"]
    if canonical(fields) != spec.fields_json:
        raise RuntimeError("Producer metadata changed before connection")
    conn = backend._connect()
    identifiers = [backend.target.id_column, backend.target.vector_column] + [
        f["name"] for f in fields
    ]
    statement = sql.SQL("SELECT {} FROM {} ORDER BY {}").format(
        sql.SQL(",").join(sql.Identifier(n) for n in identifiers),
        backend.relation,
        sql.Identifier(backend.target.id_column),
    )
    rows = []
    with conn.cursor() as cursor:
        cursor.execute(statement)
        for raw in cursor:
            if len(rows) >= spec.rows or len(raw) != 2 + len(fields):
                raise RuntimeError("Producer row count/shape cap")
            vector = X.pack_json_vector(raw[1])
            rows.append(
                {
                    "source_id": raw[0],
                    "vector": vector,
                    "metadata": dict(zip([f["name"] for f in fields], raw[2:], strict=True)),
                }
            )
    if len(rows) != spec.rows:
        raise RuntimeError("Producer row count differs")
    with Identity(spec):
        result = Snapshot(rows, fields, DATA_PROFILE)
    return result


def load_snapshot(backend, spec):
    """Bind only the selected owned instance, restore before publishing its cache."""
    global _LOADING
    from fannagent_pgvector.backend import NativeBackend

    validate_spec(spec)
    if not isinstance(backend, NativeBackend):
        raise RuntimeError("Only the frozen owned startup backend is allowed")
    X.verify_sources()
    if (
        _LOADING is not None
        or threading.current_thread() is not threading.main_thread()
        or len(threading.enumerate()) != 1
        or "snapshot" in backend.__dict__
    ):
        raise RuntimeError("Nested/concurrent/foreign producer binding")
    previous = backend._snapshot
    if previous is not None:
        if (
            backend.__dict__.get("_packed_spec") is not spec
            or previous.identity != spec.identity
            or len(previous.rows) != spec.rows
            or any(type(r["vector"]) is not X.PackedVector for r in previous.rows)
        ):
            raise RuntimeError("Cached snapshot is not the qualified packed value")
        return previous
    _LOADING = backend
    bound = MethodType(lambda self: _produce(self, spec), backend)
    backend.snapshot = bound
    candidate = None
    try:
        candidate = backend.snapshot()
        if backend.__dict__.get("snapshot") is not bound or backend._snapshot is not previous:
            raise RuntimeError("Producer instance binding/cache changed during load")
    finally:
        backend.__dict__.pop("snapshot", None)
        backend._snapshot = previous
        _LOADING = None
    # Digest/instance bindings are already restored, and all constructor checks passed.
    backend._snapshot = candidate
    backend._packed_spec = spec
    return candidate


def prepare_requests(main, factory, package, spec, notify=lambda *a: None):
    """Actual integration entry: validate identity, eligibility and admission before aliases."""
    from pc_common import lines
    from pc_results import admit
    from pc_snapshot import validate_snapshot

    if factory.snapshot is not None or factory.requests:
        raise RuntimeError("Startup state already published; never repeat")
    readers = list(main.values())
    if not readers or len(readers) > 10:
        raise RuntimeError("Reader scope differs")
    before = [
        (
            r.backend._snapshot,
            "_packed_spec" in r.backend.__dict__,
            r.backend.__dict__.get("_packed_spec"),
        )
        for r in readers
    ]
    try:
        notify("snapshot_load")
        snapshot = load_snapshot(main["native640"].backend, spec)
        notify("snapshot_identity")
        proof = validate_snapshot(snapshot, package)
        notify("request_admission")
        items = admit(snapshot, lines(package / "queries.jsonl"))
        requests = {row["query"]["id"]: row["query"] for row in items}
        for reader in readers:
            if reader.closed:
                raise RuntimeError("Reader closed before publication")
        factory.snapshot = snapshot
        factory.requests = requests
        for reader in readers:
            reader.backend._snapshot = snapshot
            reader.backend._packed_spec = spec
        return items, proof
    except BaseException:
        factory.snapshot = None
        factory.requests = {}
        for reader, (previous, present, tag) in zip(readers, before, strict=True):
            reader.backend._snapshot = previous
            if present:
                reader.backend._packed_spec = tag
            else:
                reader.backend.__dict__.pop("_packed_spec", None)
        raise


def factory_type():
    """Extend the existing search-prohibited startup factory, without changing its source."""
    from sr_interface import Factory as OriginalFactory

    class Factory(OriginalFactory):
        def __init__(self, *args, spec, **kwargs):
            validate_spec(spec)
            super().__init__(*args, **kwargs)
            self.spec = spec
            for cell, parent in list(self.classes.items()):

                class PackedStartup(parent):
                    def snapshot(self):
                        return load_snapshot(self, spec)

                self.classes[cell] = PackedStartup

        def create(self, *args, **kwargs):
            reader = super().create(*args, **kwargs)
            if self.snapshot is not None:
                reader.backend._packed_spec = self.spec
            return reader

    return Factory
