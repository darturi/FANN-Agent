"""Bounded persistent raw evidence and lossless immutable-reference failure snapshots."""

import hashlib
import io
import os
import stat
import tarfile
import time
from pathlib import Path

from nh_common import check_time, digest, encoded, identity, inventory, private, read, relative, sha

CAP = 32 * 1024**2
SLOT = 512 * 1024


class BudgetError(RuntimeError):
    pass


class RawStore:
    def __init__(self, root):
        self.root = private(root)
        for name in ("CONTROL.json", "LOCK.json"):
            with (self.root / name).open("xb") as f:
                f.write(b" " * SLOT)
                f.flush()
                os.fsync(f.fileno())
        self.control({"status": "prepared", "native_release": False})
        self.slot("LOCK.json", {"complete": False, "native_release": False})

    @classmethod
    def existing(cls, root):
        value = cls.__new__(cls)
        value.root = private(root)
        for name in ("CONTROL.json", "LOCK.json"):
            p = value.root / name
            if p.is_symlink() or p.stat().st_size != SLOT:
                raise ValueError("Persistent control reservation missing")
            record = read(p)
            if record["sha256"] != digest(record["record"]):
                raise ValueError("Control checksum differs")
        value.budget()
        return value

    def usage(self):
        files = []
        for p in self.root.rglob("*"):
            s = p.lstat()
            if stat.S_ISLNK(s.st_mode) or not (stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode)):
                raise ValueError("Unsafe raw evidence entry")
            if stat.S_ISREG(s.st_mode):
                files.append(p)
        return sum(p.stat().st_size for p in files), len(files)

    def budget(self, extra=0, new_files=0):
        size, count = self.usage()
        if size + extra > CAP or count + new_files > 256:
            raise BudgetError("Whole return32MiB/256files exhausted")

    def slot(self, name, value):
        body = encoded({"record": value, "sha256": digest(value)})
        if len(body) > SLOT:
            raise BudgetError("Control slot exhausted")
        fd = os.open(self.root / name, os.O_RDWR | os.O_NOFOLLOW)
        try:
            if os.fstat(fd).st_size != SLOT:
                raise ValueError("Control reservation changed")
            data = body + b" " * (SLOT - len(body))
            offset = 0
            while offset < len(data):
                offset += os.pwrite(fd, data[offset:], offset)
            os.fsync(fd)
        finally:
            os.close(fd)

    def control(self, v):
        self.slot("CONTROL.json", v)

    def json(self, name, value):
        relative(name)
        data = encoded(value)
        self.budget(len(data), 1)
        with (self.root / name).open("xb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

    def seal(self, success):
        self.budget()
        files = {
            str(p.relative_to(self.root)): sha(p)
            for p in self.root.rglob("*")
            if p.is_file() and p.name != "LOCK.json"
        }
        self.slot("LOCK.json", {"complete": bool(success), "files": files, "native_release": False})
        self.budget()


class Writer(io.RawIOBase):
    def __init__(self, store, path, deadline, clock):
        self.store, self.deadline, self.clock = store, deadline, clock
        store.budget(new_files=1)
        self.file = path.open("xb")

    def writable(self):
        return True

    def write(self, data):
        check_time(self.deadline, self.clock)
        self.store.budget(len(data))
        return self.file.write(data)

    def flush(self):
        if not self.file.closed:
            self.file.flush()

    def close(self):
        if not self.file.closed:
            self.file.flush()
            os.fsync(self.file.fileno())
            self.file.close()
        super().close()


def names(root):
    result = []
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            result.append(str((Path(parent) / name).relative_to(root)))
    return sorted(result)


def references(root):
    root = Path(root)
    manifest = read(root / "manifest.json")["files"]
    actual = inventory(root)
    if actual != {**manifest, "manifest.json": sha(root / "manifest.json")}:
        raise ValueError("Full immutable reference inventory differs")
    index = {}
    for name, h in actual.items():
        relative(name)
        if not isinstance(h, str) or len(h) != 64:
            raise ValueError("Invalid reference hash")
        index.setdefault(h, name)
    return index


class HashedReader:
    def __init__(self, f, deadline, clock):
        self.f, self.deadline, self.clock = f, deadline, clock
        self.hash = hashlib.sha256()

    def read(self, n=-1):
        check_time(self.deadline, self.clock)
        data = self.f.read(n)
        self.hash.update(data)
        return data


def extra_index(extras, deadline, clock):
    result = {}
    for label, row in (extras or {}).items():
        relative(label)
        if sha(row["path"], deadline, clock) != row["sha256"]:
            raise ValueError("Persistent extra reference changed")
        result[row["sha256"]] = label
    return result


def capture(work, known, store, deadline, clock=time.monotonic, extras=None):
    work = private(work)
    known = Path(known)
    if store.root.is_relative_to(work) or work.is_relative_to(store.root):
        raise ValueError("Capture and raw roots overlap")
    entries = []
    written = set()
    writer = None
    try:
        check_time(deadline, clock)
        index = references(known)
        extra = extra_index(extras, deadline, clock)
        initial = names(work)
        writer = Writer(store, store.root / "failure-payload.tar.gz", deadline, clock)
        with tarfile.open(fileobj=writer, mode="w|gz") as archive:
            for name in initial:
                relative(name)
                p = work / name
                s = p.lstat()
                row = {
                    "path": name,
                    "mode": stat.S_IMODE(s.st_mode),
                    "mtime_ns": s.st_mtime_ns,
                    "atime_ns": s.st_atime_ns,
                    "observed_ctime_ns": s.st_ctime_ns,
                    "observed_device": s.st_dev,
                    "uid": s.st_uid,
                    "gid": s.st_gid,
                    "observed_inode": s.st_ino,
                    "observed_nlink": s.st_nlink,
                }
                if s.st_uid != os.getuid() or row["mode"] & 0o7000:
                    raise ValueError("Unowned/special capture mode")
                if stat.S_ISDIR(s.st_mode):
                    row["kind"] = "directory"
                elif stat.S_ISLNK(s.st_mode):
                    row.update(kind="symlink", target=os.readlink(p))
                elif stat.S_ISREG(s.st_mode):
                    h = sha(p, deadline, clock)
                    row.update(kind="file", sha256=h, bytes=s.st_size)
                    if h in index:
                        row["reference"] = index[h]
                    elif h in extra:
                        row["extra_reference"] = extra[h]
                    else:
                        row["blob"] = h
                        if h not in written:
                            fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW)
                            with os.fdopen(fd, "rb") as source:
                                if identity(os.fstat(fd)) != identity(s):
                                    raise RuntimeError("Capture source changed")
                                reader = HashedReader(source, deadline, clock)
                                member = tarfile.TarInfo(h)
                                member.size = s.st_size
                                member.mode = 0o600
                                archive.addfile(member, reader)
                                if reader.hash.hexdigest() != h or identity(
                                    os.fstat(fd)
                                ) != identity(s):
                                    raise RuntimeError("Captured payload differs")
                            written.add(h)
                else:
                    raise ValueError("Special failure entry cannot be retained losslessly")
                entries.append(row)
                check_time(deadline, clock)
        writer.close()
        writer = None
        if names(work) != initial:
            raise RuntimeError("Work inventory changed during capture")
        for row in entries:
            p = work / row["path"]
            s = p.lstat()
            if (s.st_ino, s.st_mtime_ns, stat.S_IMODE(s.st_mode)) != (
                row["observed_inode"],
                row["mtime_ns"],
                row["mode"],
            ):
                raise RuntimeError("Failure metadata changed")
            if row["kind"] == "file" and sha(p, deadline, clock) != row["sha256"]:
                raise RuntimeError("Failure bytes changed")
        if references(known) != index:
            raise RuntimeError("Persistent references changed")
        if extra_index(extras, deadline, clock) != extra:
            raise RuntimeError("Extra references changed")
        value = {
            "complete": True,
            "entries": entries,
            "reference_manifest_sha256": sha(known / "manifest.json"),
            "extra_references": {label: row["sha256"] for label, row in (extras or {}).items()},
            "payload_sha256": sha(store.root / "failure-payload.tar.gz"),
            "link_scope": "Observed original topology recorded; restoration uses independent files inside a new owned root",
            "native_release": False,
        }
        store.json("failure-manifest.json", value)
        check_time(deadline, clock)
        store.control(
            {"status": "failure_retained", "capture_complete": True, "native_release": False}
        )
        return value
    except Exception as error:
        store.control(
            {
                "status": "failure_retention_incomplete",
                "capture_complete": False,
                "error": {"type": type(error).__name__, "message": str(error)},
                "entries_observed": len(entries),
                "native_release": False,
            }
        )
        return {"complete": False, "error": str(error), "native_release": False}
    finally:
        if writer is not None:
            writer.close()


def restore(store, known, destination, deadline, clock=time.monotonic, extras=None):
    known = Path(known)
    destination = Path(destination)
    manifest = read(store.root / "failure-manifest.json")
    if (
        manifest["complete"] is not True
        or sha(known / "manifest.json") != manifest["reference_manifest_sha256"]
    ):
        raise ValueError("Complete unchanged reference manifest required")
    references(known)
    extra_index(extras, deadline, clock)
    if {label: row["sha256"] for label, row in (extras or {}).items()} != manifest.get(
        "extra_references", {}
    ):
        raise ValueError("Extra reference identity differs")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Preserve existing restore target")
    private(destination.parent)
    rows = manifest["entries"]
    seen = set()
    for row in rows:
        relative(row["path"])
        if row["path"] in seen:
            raise ValueError("Duplicate restore path")
        seen.add(row["path"])
    with tarfile.open(store.root / "failure-payload.tar.gz", "r:gz") as archive:
        members = archive.getmembers()
        wanted = {r["blob"] for r in rows if "blob" in r}
        if (
            len(members) != len(wanted)
            or {m.name for m in members} != wanted
            or any(
                not m.isfile()
                or len(m.name) != 64
                or any(c not in "0123456789abcdef" for c in m.name)
                for m in members
            )
            or sum(m.size for m in members) > 7379306398
        ):
            raise ValueError("Unsafe bounded payload members")
        if sha(store.root / "failure-payload.tar.gz") != manifest["payload_sha256"]:
            raise ValueError("Failure payload changed")
        destination.mkdir(mode=0o700)
        for row in sorted(rows, key=lambda r: (len(Path(r["path"]).parts), r["path"])):
            check_time(deadline, clock)
            p = destination / row["path"]
            for parent in p.parents:
                if parent == destination:
                    break
                if parent.is_symlink():
                    raise ValueError("Restore parent symlink prohibited")
            if row["kind"] == "directory":
                p.mkdir(mode=0o700)
            elif row["kind"] == "symlink":
                p.symlink_to(row["target"])
                os.utime(p, ns=(row["atime_ns"], row["mtime_ns"]), follow_symlinks=False)
            elif row["kind"] == "file":
                if "reference" in row:
                    relative(row["reference"])
                    source = known / row["reference"]
                    if sha(source, deadline, clock) != row["sha256"]:
                        raise ValueError("Changed persistent reference")
                    stream = source.open("rb")
                elif "extra_reference" in row:
                    source = Path(extras[row["extra_reference"]]["path"])
                    if sha(source, deadline, clock) != row["sha256"]:
                        raise ValueError("Changed extra reference")
                    stream = source.open("rb")
                else:
                    stream = archive.extractfile(row["blob"])
                with stream, p.open("xb") as target:
                    for block in iter(lambda: stream.read(1024**2), b""):
                        check_time(deadline, clock)
                        target.write(block)
                if sha(p, deadline, clock) != row["sha256"] or p.stat().st_size != row["bytes"]:
                    raise ValueError("Restored bytes differ")
                p.chmod(row["mode"])
                os.utime(p, ns=(row["atime_ns"], row["mtime_ns"]))
            else:
                raise ValueError("Unknown snapshot entry")
        for row in reversed(rows):
            if row["kind"] == "directory":
                p = destination / row["path"]
                p.chmod(row["mode"])
                os.utime(p, ns=(row["atime_ns"], row["mtime_ns"]))
    return {"complete": True, "entries": len(rows), "native_release": False}
