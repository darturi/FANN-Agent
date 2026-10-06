from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from .errors import AgentError


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
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO state VALUES (?,?)", (key, canonical(value).decode())
            )

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
        owner = uuid.uuid4().hex
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT * FROM leases WHERE name=?", (name,)).fetchone()
            if old:
                try:
                    os.kill(old["pid"], 0)
                except ProcessLookupError:
                    db.execute("DELETE FROM leases WHERE name=?", (name,))
                else:
                    raise AgentError(f"operation already owns {name}")
            db.execute(
                "INSERT INTO leases VALUES (?,?,?,?)", (name, owner, os.getpid(), time.time())
            )
        try:
            yield
        finally:
            with self.connect() as db:
                db.execute("DELETE FROM leases WHERE name=? AND owner=?", (name, owner))

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
