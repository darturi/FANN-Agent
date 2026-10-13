from __future__ import annotations

import hashlib
import json
import os
import platform
import sqlite3
import stat
import subprocess
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from .errors import AgentError


def lock_owner_alive(owner):
    """Unknown namespaces fail closed; a host command can reclaim its dead host owner."""
    if owner.get("controller"):
        result = subprocess.run(["docker", "container", "inspect", owner["controller"]],
                                capture_output=True, text=True, timeout=15)
        if result.returncode:
            missing = "no such container: " + owner["controller"].lower()
            if missing in result.stderr.lower():
                return False
            raise AgentError("cannot verify operation owner; check the Docker daemon")
        return bool(json.loads(result.stdout)[0]["State"]["Running"])
    if owner.get("machine") != platform.node():
        return True
    try:
        os.kill(owner["pid"], 0)
    except ProcessLookupError:
        return False
    return True


def read_lock(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as handle:
        return json.load(handle)


@contextmanager
def lock_guard(directory, name, candidate):
    # Hard-link creation is atomic across host and Docker Desktop kernels. Unlike
    # flock/lockf it also arbitrates metadata updates on Desktop's shared filesystem.
    guard = directory / (name + ".guard")
    for attempt in range(20):
        try:
            os.link(candidate, guard)
            break
        except FileExistsError:
            if attempt == 19:
                raise AgentError("operation lock update is busy or was interrupted; "
                                 "verify its .locks guard owner before recovery") from None
            time.sleep(0.02)
    try:
        yield
    finally:
        guard.unlink()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


class Store:
    def __init__(self, root: Path, *, create: bool = False):
        self.root = root.resolve()
        if create:
            self.root.mkdir(parents=True, mode=0o700, exist_ok=True)
        if not self.root.exists():
            raise AgentError(f"run directory does not exist: {root}")
        # Reopening a busy run must not execute schema/configuration writes before
        # the caller reaches its operation lease. ReadOnlyStore remains available.
        for operation in ("run", "prepare"):
            path = self.root / ".locks" / (operation + ".owner")
            if path.exists() and lock_owner_alive(read_lock(path)):
                raise AgentError(f"operation already owns {operation}; "
                                 "use status/report or reclaim a dead host owner from that host")
        self.path = self.root / "state.sqlite3"
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS artifacts(hash TEXT PRIMARY KEY, kind TEXT,
                    scope TEXT, bytes INTEGER, path TEXT);
                CREATE TABLE IF NOT EXISTS charges(id TEXT PRIMARY KEY, reserved INTEGER,
                    actual INTEGER, status TEXT, metadata TEXT);
                CREATE TABLE IF NOT EXISTS leases(name TEXT PRIMARY KEY, owner TEXT,
                    pid INTEGER, started REAL);
            """)
        os.chmod(self.path, 0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, key: str, default=None):
        with self.connect() as db:
            row = db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key: str, value):
        self.set_many({key: value})

    def set_many(self, values: dict, *, delete: tuple[str, ...] = ()):
        """Publish related state pointers after their artifacts are durable."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.executemany(
                "INSERT OR REPLACE INTO state VALUES (?,?)",
                [(key, canonical(value).decode()) for key, value in values.items()],
            )
            db.executemany("DELETE FROM state WHERE key=?", [(key,) for key in delete])

    @contextmanager
    def _artifact_directory(self, scope):
        if scope not in {"private", "development"}:
            raise AgentError("invalid artifact scope")
        parent = self.root / ("workspace" if scope == "development" else "private")
        parent.mkdir(mode=0o700, exist_ok=True)
        descriptors = []
        try:
            parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            descriptors.append(parent_fd)
            try:
                os.mkdir("artifacts", mode=0o700, dir_fd=parent_fd)
            except FileExistsError:
                pass
            folder_fd = os.open(
                "artifacts", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd
            )
            descriptors.append(folder_fd)
            yield folder_fd, parent / "artifacts"
        except OSError:
            raise AgentError("artifact path is unsafe or unavailable") from None
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)

    def put(self, kind: str, value, *, scope: str = "private", limit: int | None = None) -> str:
        content = canonical(value)
        identity = hashlib.sha256(content).hexdigest()
        if limit is None:
            limit = (self.get("config") or {}).get("evidence", {}).get("max_bytes")
        with self._artifact_directory(scope) as (folder_fd, folder), self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            used = db.execute("SELECT COALESCE(SUM(bytes),0) FROM artifacts").fetchone()[0]
            old = db.execute("SELECT scope FROM artifacts WHERE hash=?", (identity,)).fetchone()
            if old and old[0] != scope:
                raise AgentError("artifact cannot cross evidence scopes")
            if limit and not old and used + len(content) > limit:
                raise AgentError("evidence storage limit reached")
            filename = f"{identity}.json"
            if not old:
                temporary = f"{identity}.{uuid.uuid4().hex}.tmp"
                fd = os.open(
                    temporary,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600,
                    dir_fd=folder_fd,
                )
                try:
                    with os.fdopen(fd, "wb") as handle:
                        handle.write(content)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(temporary, filename, src_dir_fd=folder_fd, dst_dir_fd=folder_fd)
                finally:
                    try:
                        os.unlink(temporary, dir_fd=folder_fd)
                    except FileNotFoundError:
                        pass
                db.execute(
                    "INSERT INTO artifacts VALUES (?,?,?,?,?)",
                    (
                        identity,
                        kind,
                        scope,
                        len(content),
                        str((folder / filename).relative_to(self.root)),
                    ),
                )
        return identity

    def read(self, identity: str, *, agent: bool = False):
        with self.connect() as db:
            row = db.execute("SELECT * FROM artifacts WHERE hash=?", (identity,)).fetchone()
        if not row or (agent and row["scope"] != "development"):
            raise AgentError("artifact is unavailable in this scope")
        with self._artifact_directory(row["scope"]) as (folder_fd, _):
            fd = os.open(
                f"{identity}.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=folder_fd
            )
            with os.fdopen(fd, "rb") as handle:
                info = os.fstat(handle.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_size != row["bytes"]:
                    raise AgentError("artifact file type or length changed")
                content = handle.read()
        if hashlib.sha256(content).hexdigest() != identity:
            raise AgentError("artifact identity changed")
        return json.loads(content)

    @contextmanager
    def lease(self, name: str):
        if name not in {"run", "prepare"}:
            raise AgentError("unknown operation lock")
        directory = self.root / ".locks"
        directory.mkdir(mode=0o700, exist_ok=True)
        owner = "atomic-v1:" + uuid.uuid4().hex
        candidate = directory / (uuid.uuid4().hex + ".pending")
        fd = os.open(candidate, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
        record = {"owner": owner, "pid": os.getpid(), "machine": platform.node(),
                  "controller": os.environ.get("FANNAGENT_CONTROLLER")}
        with os.fdopen(fd, "w") as handle:
            json.dump(record, handle)
            handle.flush()
            os.fsync(handle.fileno())
        path = directory / (name + ".owner")
        acquired = False
        try:
            with lock_guard(directory, name, candidate):
                if path.exists():
                    previous = read_lock(path)
                    if lock_owner_alive(previous):
                        raise AgentError(f"operation already owns {name}; "
                                         "dead host owners must be reclaimed from that host")
                    path.unlink()
                with self.connect() as db:
                    db.execute("BEGIN IMMEDIATE")
                    old = db.execute("SELECT * FROM leases WHERE name=?", (name,)).fetchone()
                    if old and not old["owner"].startswith("atomic-v1:"):
                        try:
                            os.kill(old["pid"], 0)
                        except ProcessLookupError:
                            pass
                        else:
                            raise AgentError(f"legacy operation already owns {name}")
                    os.link(candidate, path)
                    acquired = True
                    db.execute("DELETE FROM leases WHERE name=?", (name,))
                    db.execute("INSERT INTO leases VALUES (?,?,?,?)",
                               (name, owner, os.getpid(), time.time()))
            yield
        finally:
            try:
                if acquired:
                    with lock_guard(directory, name, candidate):
                        if read_lock(path)["owner"] != owner:
                            raise AgentError("operation lock ownership changed")
                        with self.connect() as db:
                            db.execute("DELETE FROM leases WHERE name=? AND owner=?", (name, owner))
                        path.unlink()
            finally:
                candidate.unlink()

    def secret(self, key: str, value: str | None = None):
        path = self.root / "secrets.json"
        data = json.loads(path.read_text()) if path.exists() else {}
        if value is not None:
            data[key] = value
            temp = path.with_suffix(".tmp")
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as handle:
                json.dump(data, handle)
                handle.flush()
                os.fsync(handle.fileno())
            temp.replace(path)
        return data.get(key)


class ReadOnlyStore(Store):
    """Open existing state without schema creation, chmod, WAL changes, or writes."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.path = self.root / "state.sqlite3"
        if not self.path.is_file():
            raise AgentError(f"run state does not exist: {root}")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            yield db
        finally:
            db.close()

    def set(self, key, value):
        raise AgentError("inspection state is read-only")

    def set_many(self, values, *, delete=()):
        raise AgentError("inspection state is read-only")

    @contextmanager
    def _artifact_directory(self, scope):
        if scope not in {"private", "development"}:
            raise AgentError("invalid artifact scope")
        parent = self.root / ("workspace" if scope == "development" else "private")
        parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            folder_fd = os.open(
                "artifacts", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd
            )
            try:
                yield folder_fd, parent / "artifacts"
            finally:
                os.close(folder_fd)
        finally:
            os.close(parent_fd)
