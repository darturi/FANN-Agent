"""Bounded read-only configuration compatibility; no allocation authority.

inspect never executes Slurm. replay is closed until an installed dependency
closure has been reviewed and pinned here. Static ELF candidates are evidence,
not a claim about what the deployed loader will actually open.
"""
import argparse
import collections
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import time

CONFIG_SHA = "ba998cfda785eee87ef65023a8fe2caf4f7c3734665eb15af5b76d5a2b603ea6"
CONFIG_BYTES = 16647
CLIENTS = {
    "scontrol": "ed806e144b8de806ee88e5fc066e0aed6c42ab281abf457315fca3e9af82b238",
    "sacctmgr": "60564635b14de58039267be2bf26cb6ba59d064955a9bcf446cdb7a67908b48f",
}
ANCHOR = {"AuthType": "auth/munge", "ClusterName": "torch",
          "SlurmctldHost[0]": "slurm-controller-0", "SlurmctldPort": "6817"}
PACKAGE = Path("/scratch/dar579/torch-reviews/a3-site-compatibility-packages-619d4288ca7a/torch-startup-native-integrated-qualification-v1")
PLAN_SHA = "08a9293c3c4e4386118be6a354476efe27ec61749c421bf85136c426585526b0"
PACKAGE_MANIFEST_SHA = "13d281a4d366b8dabcc0a2dfb5c52629528d02baccde1883c63d40d4cee79cfb"
CAPTURE = Path("/home/dar579/torch-reviews-results/a3-client-config-capture.9rki9gow")
CONFIG = CAPTURE / "export/slurm.conf.2026-11-03T18:05:27"
MANIFEST_SHA = "0ef4872fd4a60229dd5545d764bebc85998d036347d5555ba1be6ed9d2c9f6f2"
RESULTS = CAPTURE.parent
PREFIX = Path("/opt/slurm")
PLUGIN_DIR = PREFIX / "lib64/slurm"
ROOTS = (PREFIX / "lib64", PREFIX / "lib", Path("/lib64"), Path("/usr/lib64"),
         Path("/lib/x86_64-linux-gnu"), Path("/usr/lib/x86_64-linux-gnu"))
ELF_CAP, TOTAL_READ_CAP, OBJECT_CAP = 32 * 1024**2, 256 * 1024**2, 96
FILE_CAP, OUTPUT_CAP, RAW_CAP = 1024**2, 65536, 2 * 1024**2
INSPECTION_SECONDS = 120
# Deliberately no externally supplied boolean/JSON can open native replay.
# Add an exact installed closure only after a separately frozen evidence review.
REVIEWED_NATIVE_CLOSURES = {}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def decode(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("Nonfinite JSON")
    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)


def stamp(s):
    return [s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_gid, s.st_nlink,
            s.st_size, s.st_mtime_ns, s.st_ctime_ns]


def bounded_file(path, cap, *, private=False):
    """No FIFO/device/link reads; stable fd and name generation required."""
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or not 0 <= before.st_size <= cap:
            raise ValueError("Bounded regular file required")
        if private and (before.st_uid != os.getuid() or
                        stat.S_IMODE(before.st_mode) != 0o600 or before.st_nlink != 1):
            raise ValueError("Owned private single-link file required")
        data = bytearray()
        while len(data) <= cap:
            part = os.read(fd, min(131072, cap + 1 - len(data)))
            if not part:
                break
            data.extend(part)
        if (len(data) > cap or len(data) != before.st_size or
                stamp(before) != stamp(os.fstat(fd)) or stamp(before) != stamp(path.lstat())):
            raise RuntimeError("Input changed or exceeded bound")
        return bytes(data), stamp(before)
    finally:
        os.close(fd)


def candidate(data):
    if (not isinstance(data, bytes) or len(data) != CONFIG_BYTES or sha(data) != CONFIG_SHA
            or not data.endswith(b"\n") or b"\0" in data):
        raise ValueError("Exact reviewed candidate bytes required")
    data.decode("utf-8", "strict")
    return data


def trusted_path(raw):
    """Check every traversed component, including intermediate symlink targets.

    The sole nonroot exception is the already frozen /opt/slurm ancestor.
    This does not admit a user-owned plugin, directory, config or loader input.
    """
    raw = Path(raw)
    if not raw.is_absolute() or ".." in raw.parts or os.getuid() in (0, 1001):
        raise ValueError("Absolute path and unprivileged non-installation caller required")
    todo, current, rows, links = collections.deque(raw.parts[1:]), Path("/"), [], 0
    def observe(path):
        s = path.lstat()
        if path == PREFIX:
            if (s.st_uid, s.st_gid, stat.S_IMODE(s.st_mode)) != (1001, 1001, 0o755) or not stat.S_ISDIR(s.st_mode):
                raise ValueError("Frozen site ancestor differs")
        elif s.st_uid != 0:
            raise ValueError("Root-owned installed input/ancestor required")
        # Symlink permissions do not govern modification; its parent is checked.
        if not stat.S_ISLNK(s.st_mode) and (s.st_mode & 0o022 or os.access(path, os.W_OK)):
            raise ValueError("Writable installed input/ancestor")
        link = os.readlink(path) if stat.S_ISLNK(s.st_mode) else None
        rows.append({"path": str(path), "generation": stamp(s), "link": link})
        return s, link
    observe(current)
    while todo:
        part = todo.popleft()
        if part in ("", "."):
            continue
        if part == "..":
            current = current.parent
            continue
        path = current / part
        info, link = observe(path)
        if link is not None:
            links += 1
            if links > 40:
                raise ValueError("Symlink traversal bound")
            target = Path(link)
            if target.is_absolute():
                current = Path("/")
                todo.extendleft(reversed(target.parts[1:]))
            else:
                todo.extendleft(reversed(target.parts))
        else:
            if todo and not stat.S_ISDIR(info.st_mode):
                raise ValueError("Directory ancestor required")
            current = path
    return current, rows


def installed(raw, cap=ELF_CAP):
    target, before = trusted_path(raw)
    data, generation = bounded_file(target, cap)
    again, after = trusted_path(raw)
    if again != target or before != after or generation != stamp(target.lstat()):
        raise RuntimeError("Installed path generation changed")
    return data, {"path": str(raw), "resolved": str(target), "bytes": len(data),
                  "sha256": sha(data), "components": before, "generation": generation}


def elf64(data, machines=(62,)):
    """Static ELF parser: neither dlopen nor execution of a target/loader."""
    if len(data) < 64 or data[:7] != b"\x7fELF\x02\x01\x01":
        raise ValueError("ELF64 little-endian version1 required")
    (kind, machine, version, entry, phoff, shoff, flags, ehsize, phentsize,
     phnum, shentsize, shnum, shstrndx) = struct.unpack_from("<HHIQQQIHHHHHH", data, 16)
    if kind not in (2, 3) or machine not in machines or version != 1 or ehsize != 64 or phentsize != 56 or not 0 < phnum <= 1024:
        raise ValueError("Unsupported ELF type/machine/header")
    def region(start, size):
        if start < 0 or size < 0 or start > len(data) or size > len(data) - start:
            raise ValueError("ELF region outside file")
        return data[start:start + size]
    region(phoff, phnum * phentsize)
    loads, dynamics, interp = [], [], []
    for i in range(phnum):
        typ, flg, off, addr, paddr, size, memsize, align = struct.unpack_from("<IIQQQQQQ", data, phoff + 56 * i)
        region(off, size)
        if size > memsize:
            raise ValueError("ELF file/memory size mismatch")
        if typ == 1:
            loads.append((addr, size, off))
        elif typ == 2:
            dynamics.append((off, size))
        elif typ == 3:
            raw = region(off, size)
            if not raw.endswith(b"\0") or b"\0" in raw[:-1] or not 1 < len(raw) <= 4096:
                raise ValueError("Invalid ELF interpreter")
            value = raw[:-1].decode("ascii", "strict")
            if not value.startswith("/") or ".." in Path(value).parts:
                raise ValueError("Absolute ELF interpreter required")
            interp.append(value)
    if len(interp) > 1 or len(dynamics) > 1:
        raise ValueError("Duplicate ELF interpreter/dynamic segment")
    values = collections.defaultdict(list)
    if dynamics:
        off, size = dynamics[0]
        if size % 16 or not size:
            raise ValueError("Invalid ELF dynamic size")
        terminated = False
        for pos in range(off, off + size, 16):
            tag, value = struct.unpack_from("<qQ", data, pos)
            if tag == 0:
                terminated = True
                break
            values[tag].append(value)
        if not terminated:
            raise ValueError("Unterminated ELF dynamic table")
    text_tags = {1: "needed", 14: "soname", 15: "rpath", 29: "runpath"}
    output = {"machine": machine, "type": kind, "interpreter": interp[0] if interp else None,
              "needed": [], "soname": [], "rpath": [], "runpath": [],
              "dynamic_flags": {str(t): values[t] for t in (30, 0x6ffffffb) if t in values}}
    if any(values[t] for t in text_tags):
        if len(values[5]) != 1 or len(values[10]) != 1 or not 0 < values[10][0] <= FILE_CAP:
            raise ValueError("Unique bounded ELF string table required")
        addr, size = values[5][0], values[10][0]
        mappings = [(off + addr - start, size) for start, count, off in loads
                    if start <= addr and addr - start + size <= count]
        if len(mappings) != 1:
            raise ValueError("Unambiguous file-backed ELF string table required")
        strings = region(*mappings[0])
        for tag, name in text_tags.items():
            if tag != 1 and len(values[tag]) > 1:
                raise ValueError("Duplicate singleton ELF string tag")
            for index in values[tag]:
                if index >= len(strings) or b"\0" not in strings[index:]:
                    raise ValueError("Unterminated ELF string")
                value = strings[index:strings.index(0, index)].decode("utf-8", "strict")
                if not value or len(value) > 4096 or any(ord(c) < 32 for c in value):
                    raise ValueError("Invalid ELF string")
                output[name].append(value)
    if len(output["needed"]) != len(set(output["needed"])):
        raise ValueError("Duplicate ELF dependency")
    return output


def stable_configuration(text):
    values = {}
    for line in text.splitlines():
        m = re.fullmatch(r"\s*(AuthType|ClusterName|SlurmctldPort|SlurmctldHost\[[0-9]+\])\s*=\s*(\S.*?)\s*", line)
        if m:
            if m[1] in values:
                raise ValueError("Duplicate controller identity")
            values[m[1]] = m[2]
    if values != ANCHOR:
        raise ValueError("Pinned controller/auth identity differs")
    return values


def query_spec(role):
    # No caller-provided options, path, user, job identity or configuration mutation.
    specs = {
        "version": ("scontrol", ("--local", "--version")),
        "configuration": ("scontrol", ("--local", "show", "config")),
        "partition": ("scontrol", ("--local", "--oneliner", "show", "partition", "cs")),
        "associations": ("sacctmgr", ("--readonly", "-n", "-P", "show", "associations", "where", "user=dar579",
                                      "format=Cluster,User,Account,Partition,QOS,DefaultQOS")),
    }
    if role not in specs:
        raise ValueError("Predeclared read-only query role required")
    client, args = specs[role]
    return (str(PREFIX / "bin" / client), *args)


def capability_environment(fd):
    # Overrides held exactly as in the old adapter, which remains untouched.
    if any(os.environ.get(k) for k in ("SLURM_CONF_SERVER", "SLURM_CONFIG", "LD_PRELOAD", "PYTHONHOME")):
        raise ValueError("Unreviewed scheduler/loader override")
    # The initial harness has no reviewed loader-path closure, so don't inherit it.
    if os.environ.get("LD_LIBRARY_PATH"):
        raise ValueError("Loader-path closure not reviewed")
    env = {k: v for k, v in os.environ.items() if k in ("LANG", "LC_ALL", "TZ", "HOME", "USER", "LOGNAME")}
    env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
    env["SLURM_CONF"] = f"/proc/self/fd/{fd}"
    return env


class SealedConfiguration:
    def __init__(self, data):
        self.data = candidate(data)
        self.fd = None

    def __enter__(self):
        if sys.platform != "linux" or not hasattr(os, "memfd_create"):
            raise RuntimeError("Real Linux sealed descriptor required")
        self.fd = os.memfd_create("a3-reviewed-slurm-conf", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
        try:
            pending = memoryview(self.data)
            while pending:
                written = os.write(self.fd, pending)
                if written <= 0:
                    raise RuntimeError("Short descriptor write")
                pending = pending[written:]
            self.seals = fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL
            fcntl.fcntl(self.fd, fcntl.F_ADD_SEALS, self.seals)
            os.lseek(self.fd, 0, os.SEEK_SET)
            self.check()
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def check(self):
        if self.fd is None or fcntl.fcntl(self.fd, fcntl.F_GET_SEALS) & self.seals != self.seals:
            raise RuntimeError("Complete immutable seals required")
        s = os.fstat(self.fd)
        if not stat.S_ISREG(s.st_mode) or s.st_size != len(self.data):
            raise RuntimeError("Sealed descriptor size/type differs")
        if os.pread(self.fd, len(self.data) + 1, 0) != self.data:
            raise RuntimeError("Sealed descriptor content differs")

    def __exit__(self, *_):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


def bounded_process(argv, env, passed_fds, log, events, timeout=10, maximum=OUTPUT_CAP):
    """Private internal runner; query_spec and closure gate precede this call.

    Always kill our process group, even if its leader exited successfully. A child
    holding the output pipe may otherwise outlive the ten-second deadline.
    """
    if not 0 < timeout <= 10 or not 0 < maximum <= OUTPUT_CAP:
        raise ValueError("Original command ceiling exceeded")
    row = {"argv": list(argv), "status": "held", "output_incomplete": False}
    events.append(row)
    started, process, data = time.monotonic(), None, bytearray()
    selector = selectors.DefaultSelector()
    try:
        with Path(log).open("xb", buffering=0) as handle:
            os.chmod(log, 0o600)
            process = subprocess.Popen(argv, env=env, pass_fds=passed_fds, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       start_new_session=True, close_fds=True, cwd="/")
            os.set_blocking(process.stdout.fileno(), False)
            selector.register(process.stdout, selectors.EVENT_READ)
            deadline = started + timeout
            while selector.get_map():
                left = deadline - time.monotonic()
                if left <= 0:
                    row["output_incomplete"] = True
                    raise TimeoutError("Ten-second command ceiling")
                for key, _ in selector.select(min(0.05, left)):
                    block = os.read(key.fd, min(8192, maximum + 1 - len(data)))
                    if not block:
                        selector.unregister(key.fileobj)
                        continue
                    keep = block[:maximum - len(data)]
                    handle.write(keep)
                    data.extend(keep)
                    if len(keep) != len(block):
                        row["output_incomplete"] = True
                        raise ValueError("Complete combined-output bound exceeded")
            code = process.wait(timeout=max(0.001, deadline - time.monotonic()))
            row["exit_code"] = code
            os.fsync(handle.fileno())
            if code:
                raise RuntimeError("Read-only client failed; bounded raw retained")
        text = bytes(data).decode("utf-8", "strict")
        if "\0" in text:
            raise ValueError("Binary scheduler response")
        row["status"] = "pass"
        return text
    except BaseException as error:
        row.update(status="held", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=1)
            process.stdout.close()
        selector.close()
        row["output_bytes"] = len(data)
        row["elapsed_seconds"] = time.monotonic() - started


def require_login():
    host, u = socket.gethostname(), os.uname()
    if (u.sysname != "Linux" or u.machine != "x86_64" or os.getuid() != 3213387 or
            not re.fullmatch(r"torch-login(?:-[a-z]-[0-9]+)?", host.split(".")[0]) or
            any(os.environ.get(k) for k in ("SLURM_JOB_ID", "SLURM_JOBID", "SLURM_STEP_ID"))):
        raise RuntimeError("Only dar579 on a Torch x86_64 login outside allocation")
    if os.environ.get("TORCH_RESULTS_ROOT") != str(RESULTS):
        raise ValueError("Original results root required")
    if RESULTS.resolve(strict=True) != RESULTS:
        raise ValueError("Canonical original results root required")
    s = RESULTS.lstat()
    if not stat.S_ISDIR(s.st_mode) or s.st_uid != os.getuid() or s.st_mode & 0o022:
        raise ValueError("Owned non-writable-by-others results directory required")


class Inspector:
    def __init__(self):
        self.deadline = time.monotonic() + INSPECTION_SECONDS
        self.bytes = 0
        self.objects, self.edges, self.directory_rows, self.inputs = {}, [], [], []

    def tick(self):
        if time.monotonic() >= self.deadline:
            raise TimeoutError("Inspection ceiling reached; no retry")

    def directory(self, raw):
        self.tick()
        target, before = trusted_path(raw)
        if not target.is_dir():
            raise ValueError("Installed directory required")
        names = []
        # Bound the iterator itself rather than materializing arbitrary contents.
        with os.scandir(target) as entries:
            for entry in entries:
                if len(names) >= 1024:
                    raise ValueError("Installed directory inventory bound")
                names.append(entry.name)
        again, after = trusted_path(raw)
        if again != target or before != after:
            raise RuntimeError("Installed directory changed")
        self.directory_rows.append({"path": str(raw), "resolved": str(target),
                                    "components": before, "names": sorted(names)})
        return names

    def add(self, raw):
        self.tick()
        raw = Path(raw)
        # Resolve and validate before even looking at a shared object's magic.
        canonical, _ = trusted_path(raw)
        if str(canonical) in self.objects:
            return
        if len(self.objects) >= OBJECT_CAP:
            raise ValueError("Installed ELF object bound")
        size = canonical.stat().st_size
        if self.bytes + size > TOTAL_READ_CAP:
            raise ValueError("Installed ELF total read bound")
        data, proof = installed(raw, min(ELF_CAP, TOTAL_READ_CAP - self.bytes))
        self.bytes += len(data)
        parsed = elf64(data)
        self.objects[str(canonical)] = {**proof, "elf": parsed}
        self.tick()
        # Candidate paths only. No loader cache/hwcaps/default-selection claim.
        for needed in parsed["needed"]:
            if not re.fullmatch(r"[A-Za-z0-9_.+\-]+", needed):
                self.edges.append({"from": str(canonical), "needed": needed, "candidates": [], "hold": "non-simple dependency name"})
                continue
            candidates = []
            for root in ROOTS:
                path = root / needed
                if path.is_symlink() or path.exists():
                    candidates.append(str(path))
            self.edges.append({"from": str(canonical), "needed": needed, "candidates": candidates,
                               "hold": "candidate paths are not proof of runtime loader selection"})
            for path in candidates:
                self.add(path)
        if parsed["interpreter"]:
            self.add(parsed["interpreter"])

    def collect(self):
        for name, expected in CLIENTS.items():
            path = PREFIX / "bin" / name
            self.add(path)
            resolved, _ = trusted_path(path)
            if self.objects[str(resolved)]["sha256"] != expected:
                raise RuntimeError("Pinned client differs")
        names = self.directory(PLUGIN_DIR)
        for name in sorted(names):
            # Names only for all entries; never inspect private configuration/key files.
            # These are source-derived candidates, never a closure claim. The
            # complete directory name/generation inventory retains fallback
            # evidence without spending the bounded read budget on all daemon
            # and unrelated workload plugins.
            if re.fullmatch(r"(?:auth_munge|hash_k12|tls_none|accounting_storage_slurmdbd|cred_munge|gres_gpu|certgen_[A-Za-z0-9_]+)\.so(?:\.[0-9.]+)?", name):
                self.add(PLUGIN_DIR / name)
        for root in ROOTS[:2]:
            if root.exists():
                for name in self.directory(root):
                    if re.fullmatch(r"libslurm[A-Za-z0-9_+.-]*\.so(?:\.[0-9.]+)?", name):
                        self.add(root / name)
        for name in ("/etc/ld.so.cache", "/etc/ld.so.preload"):
            self.tick()
            p = Path(name)
            if p.is_symlink() or p.exists():
                data, proof = installed(p, min(FILE_CAP, TOTAL_READ_CAP - self.bytes))
                self.bytes += len(data)
                if self.bytes > TOTAL_READ_CAP:
                    raise ValueError("Total inspection read bound")
                self.inputs.append(proof)
                if name.endswith("preload") and data.strip():
                    raise ValueError("Nonempty system loader preload requires review")
            else:
                # Absence still anchored to a checked parent generation.
                _, chain = trusted_path(p.parent)
                self.inputs.append({"path": name, "absent": True, "parent_components": chain})
        self.tick()
        return self.evidence()

    def evidence(self):
        return {"objects": self.objects, "dependency_candidates": self.edges,
                "directories": self.directory_rows, "loader_inputs": self.inputs,
                "total_elf_and_input_bytes": self.bytes,
                "dependency_closure_verified": False,
                "unresolved_gates": ["actual runtime loader/cache/hwcaps selection",
                    "RPATH/RUNPATH and implicit build defaults", "plugin fallback and runtime-only initialization",
                    "relative auxiliary input behavior", "MUNGE socket identity and authentication",
                    "native parser and sealed descriptor compatibility"],
                "configuration_admitted": False, "native_qualification": False}


def verify_import_boundary(package):
    package = Path(package)
    if package.resolve(strict=True) != package:
        raise ValueError("Canonical original package required")
    raw, _ = bounded_file(package / "manifest.json", FILE_CAP)
    if sha(raw) != PACKAGE_MANIFEST_SHA:
        raise ValueError("Original package manifest differs before import")
    files = decode(raw)["files"]
    if not isinstance(files, dict) or not 0 < len(files) <= 2048:
        raise ValueError("Bounded original package inventory required")
    for name, digest in files.items():
        if (not isinstance(name, str) or not name or Path(name).is_absolute() or
                ".." in Path(name).parts or "\\" in name or
                not isinstance(digest, str) or not re.fullmatch("[a-f0-9]{64}", digest)):
            raise ValueError("Unsafe original manifest member")
    found = set()
    for root, dirs, names in os.walk(package, followlinks=False):
        for name in dirs:
            if not stat.S_ISDIR((Path(root) / name).lstat().st_mode):
                raise ValueError("Original package directory link rejected")
        for name in names:
            path = Path(root) / name
            relative = str(path.relative_to(package))
            if not stat.S_ISREG(path.lstat().st_mode) or relative not in {*files, "manifest.json"}:
                raise ValueError("Unexpected original importable/member")
            found.add(relative)
            if len(found) > len(files) + 1:
                raise ValueError("Original inventory bound")
    if found != {*files, "manifest.json"}:
        raise ValueError("Missing original importable/member")
    plan, _ = bounded_file(package / "PLAN.json", FILE_CAP)
    if sha(plan) != PLAN_SHA:
        raise ValueError("Original PLAN differs before import")
    for name, digest in files.items():
        if name.endswith(".py"):
            data, _ = bounded_file(package / name, FILE_CAP)
            if sha(data) != digest:
                raise ValueError("Original Python source differs before import")


def verify_original():
    verify_import_boundary(PACKAGE)
    sys.path.insert(0, str(PACKAGE / "readiness"))
    import site_control as S
    plan = S.C.verify(PACKAGE)
    if (Path(S.__file__).resolve() != PACKAGE / "readiness/site_control.py" or
            S.sha(PACKAGE / "PLAN.json") != PLAN_SHA or
            S.sha(Path(S.__file__)) != plan["admission_control_sha256"] or
            S.sha(Path(S.T.__file__)) != plan["site_trust_sha256"] or
            S.T.POLICY != plan["site_trust_policy"]):
        raise RuntimeError("Original packet/entry/trust policy differs")
    # No monkeypatch/install: leave original policy untouched.
    return S.C.quota(PACKAGE)


def load_capture():
    manifest, _ = bounded_file(CAPTURE / "manifest.json", OUTPUT_CAP, private=True)
    if sha(manifest) != MANIFEST_SHA:
        raise ValueError("Original capture manifest differs")
    entries = decode(manifest)
    relative = "export/" + CONFIG.name
    row = entries.get(relative)
    if row != {"bytes": CONFIG_BYTES, "sha256": CONFIG_SHA}:
        raise ValueError("Manifest candidate binding differs")
    raw, _ = bounded_file(CONFIG, FILE_CAP, private=True)
    return candidate(raw)


def save(path, value, cap=FILE_CAP):
    data = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    if not 0 < cap <= FILE_CAP or len(data) > cap:
        raise ValueError("Evidence file bound")
    with path.open("xb") as f:
        os.chmod(path, 0o600)
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


@contextlib.contextmanager
def hard_deadline(seconds=INSPECTION_SECONDS):
    if not 0 < seconds <= INSPECTION_SECONDS:
        raise ValueError("Inspection ceiling cannot increase")
    previous = signal.getitimer(signal.ITIMER_REAL)
    if previous != (0.0, 0.0):
        raise RuntimeError("Existing real-time timer must remain unchanged")
    handler = signal.getsignal(signal.SIGALRM)
    def expired(_number, _frame):
        raise TimeoutError("Complete login helper deadline; no retry")
    signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, seconds)
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, handler)


def inspect():
    require_login()
    # Also hold hostile loader overrides before importing the original packet.
    capability_environment(-1)
    quota = verify_original()
    load_capture()
    os.umask(0o077)
    out = Path(tempfile.mkdtemp(prefix="a3-client-config-dependencies.", dir=RESULTS))
    inspector = Inspector()
    result = {"status": "held", "new_allocations": 0, "ANN_searches": 0, "exact_searches": 0,
              "configuration_admitted": False, "dependency_closure_verified": False, "native_qualification": False}
    try:
        result["evidence"] = inspector.collect()
        result["status"] = "metadata_captured_pending_dependency_review"
    except BaseException as e:
        result.update(error_type=type(e).__name__, error=str(e), evidence=inspector.evidence())
    save(out / "quota.json", quota, OUTPUT_CAP)
    save(out / "inspection.json", result)
    files = {p.name: {"bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in out.iterdir()}
    if len(files) + 1 > 16 or sum(v["bytes"] for v in files.values()) + FILE_CAP > RAW_CAP:
        raise ValueError("Whole inspection raw ceiling")
    save(out / "manifest.json", files, OUTPUT_CAP)
    print(json.dumps({"directory": str(out), **{k: v for k, v in result.items() if k != "evidence"}}, indent=2))
    return result["status"] != "metadata_captured_pending_dependency_review"


def check_reply(role, text):
    if role == "version":
        if text.strip() != "slurm 25.05.4":
            raise ValueError("Pinned native version differs")
    elif role == "configuration":
        stable_configuration(text)
    elif role == "partition":
        # One explicitly requested partition; no inference of resource approval.
        rows = text.strip().splitlines()
        if len(rows) != 1 or not rows[0].startswith("PartitionName=cs "):
            raise ValueError("Expected cs partition record")
    elif role == "associations":
        accounts = set()
        for row in text.splitlines():
            if not row.strip():
                continue
            parts = row.split("|")
            if (len(parts) != 6 or parts[0] != "torch" or parts[1] != "dar579" or
                    not re.fullmatch(r"[A-Za-z0-9_-]+", parts[2])):
                raise ValueError("Current-user association response differs")
            if parts[3] in ("", "cs"):
                accounts.add(parts[2])
        if "torch_pr_288_courant" not in accounts:
            raise ValueError("Expected project association absent")
    else:
        raise ValueError("Unknown reply role")


def query_candidate(role, data, verify_inputs, log, events):
    """Internal query mechanism; public CLI first requires its in-code closure.

    verify_inputs rechecks exact reviewed installed generations. It is injected
    for local fixture-process checks, never selectable through CLI arguments.
    """
    argv = query_spec(role)  # Validate before descriptors or process creation.
    candidate(data)
    verify_inputs()
    with SealedConfiguration(data) as sealed:
        env = capability_environment(sealed.fd)
        sealed.check()
        try:
            try:
                text = bounded_process(argv, env, (sealed.fd,), log, events)
            finally:
                sealed.check()
                verify_inputs()
            check_reply(role, text)
            return text
        except BaseException as e:
            if events:
                events[-1].update(status="held", verification_error_type=type(e).__name__, verification_error=str(e))
            raise


def replay(profile):
    # Deliberately gate before login probes, file reads, FDs or processes.
    if profile not in REVIEWED_NATIVE_CLOSURES:
        raise RuntimeError("No reviewed installed dependency closure; native replay held")
    pin = REVIEWED_NATIVE_CLOSURES[profile]
    required = {"configuration_sha256", "controller", "inputs", "directories", "absent_inputs", "reviewed_gates"}
    gates = {"native_dependency_closure", "auxiliary_input_semantics", "loader_selection", "plugin_initialization", "munge_socket"}
    if (set(pin) != required or pin["configuration_sha256"] != CONFIG_SHA or pin["controller"] != ANCHOR or
            set(pin["reviewed_gates"]) != gates or any(pin["reviewed_gates"][k] is not True for k in gates) or
            not pin["inputs"] or not pin["directories"]):
        raise ValueError("Complete separately reviewed exact closure required")
    require_login()
    capability_environment(-1)
    verify_original()
    data = load_capture()
    # Freeze requires two bounded whole-input passes, before/after the replay.
    if len(pin["inputs"]) > OBJECT_CAP or sum(row["bytes"] for row in pin["inputs"]) > TOTAL_READ_CAP // 2:
        raise ValueError("Reviewed input/read bound")
    client_paths = {str(PREFIX / "bin" / name): value for name, value in CLIENTS.items()}
    by_path = {row["path"]: row for row in pin["inputs"]}
    if len(by_path) != len(pin["inputs"]) or any(by_path.get(path, {}).get("sha256") != value for path, value in client_paths.items()):
        raise ValueError("Both exact native clients must be pinned")
    def verify_inputs(full=False):
        for row in pin["inputs"]:
            if full:
                _, current = installed(row["path"], ELF_CAP)
                if current != row:
                    raise RuntimeError("Reviewed installed input differs")
            else:
                target, chain = trusted_path(row["path"])
                if str(target) != row["resolved"] or chain != row["components"] or stamp(target.lstat()) != row["generation"]:
                    raise RuntimeError("Reviewed installed input generation differs")
        for row in pin["directories"]:
            check = Inspector()
            check.directory(row["path"])
            if check.directory_rows != [row]:
                raise RuntimeError("Reviewed installed directory differs")
        for row in pin["absent_inputs"]:
            path = Path(row["path"])
            if path.exists() or path.is_symlink() or trusted_path(path.parent)[1] != row["parent_components"]:
                raise RuntimeError("Reviewed absent input differs")
    verify_inputs(full=True)
    os.umask(0o077)
    out = Path(tempfile.mkdtemp(prefix="a3-client-config-compatibility.", dir=RESULTS))
    events, result = [], {"status": "held", "configuration_admitted": False,
                          "dependency_closure_verified": False, "native_qualification": False,
                          "new_allocations": 0, "ANN_searches": 0, "exact_searches": 0}
    try:
        for role in ("version", "configuration", "partition", "associations", "configuration", "version"):
            query_candidate(role, data, verify_inputs, out / f"query-{len(events)}.log", events)
        verify_inputs(full=True)
        result["status"] = "login_compatibility_completed_pending_independent_review"
    except BaseException as e:
        result.update(error_type=type(e).__name__, error=str(e))
    save(out / "commands.json", events, OUTPUT_CAP)
    save(out / "receipt.json", result, OUTPUT_CAP)
    print(json.dumps({"directory": str(out), **result}, indent=2))
    return result["status"] != "login_compatibility_completed_pending_independent_review"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inspect")
    p = sub.add_parser("replay")
    p.add_argument("profile")
    args = parser.parse_args()
    with hard_deadline():
        return inspect() if args.command == "inspect" else replay(args.profile)


if __name__ == "__main__":
    raise SystemExit(main())
