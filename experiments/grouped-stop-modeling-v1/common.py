"""Fixed local protocol, source guards and accounting; no provider/DB imports."""

import datetime
import hashlib
import importlib.abc
import importlib.metadata
import json
import resource
import sys
import time
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[2]
BASE = ROOT / "trials/torch-reviews-grouped-stop-modeling-v1"
CONTRACT_SHA = "d50ccf6a7b41e7b7af79541c6b0f55cd87ef20acb4842636fb0da63125f1b5c7"
START = time.monotonic()
READ_BYTES = 0
FITS = 0


def sha(path):
    global READ_BYTES
    path = Path(path)
    READ_BYTES += path.stat().st_size
    if READ_BYTES > 16 * 1024**3:
        raise RuntimeError("Source read ceiling exceeded")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    global READ_BYTES
    path = Path(path)
    READ_BYTES += path.stat().st_size
    with path.open() as stream:
        return json.load(stream)


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")


def contract():
    if sha(SOURCE / "contract.json") != CONTRACT_SHA:
        raise ValueError("Frozen scientific contract changed")
    return read(SOURCE / "contract.json")


def check_limits(*, fit=False):
    global FITS
    if fit:
        FITS += 1
    if FITS > 360 or time.monotonic() - START > 3600:
        raise RuntimeError("Finite modeling fit/wall budget exceeded")
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > 4 * 1024**3:
        raise RuntimeError("Local memory budget exceeded")


def versions():
    names = [
        "numpy",
        "scipy",
        "scikit-learn",
        "joblib",
        "threadpoolctl",
        "pydantic",
        "pydantic-core",
        "annotated-types",
        "typing-extensions",
        "typing-inspection",
    ]
    return {"python": sys.version, "packages": {n: importlib.metadata.version(n) for n in names}}


def verify_inputs():
    pins = read(SOURCE / "input-pins.json")
    for relative, expected in pins["files"].items():
        path = ROOT / relative
        if path.is_symlink() or sha(path) != expected:
            raise ValueError("Pinned source changed: " + relative)
    return pins


def load_api():
    pins = read(SOURCE / "input-pins.json")
    sys.path.insert(0, str(ROOT / pins["frozen_vendor"]))
    from fannagent_pgvector.profiles import PROFILE

    if PROFILE.fingerprint != contract()["operating_identity"]["runtime_profile_hash"]:
        raise ValueError("Frozen runtime/profile identity differs")
    return PROFILE


def offline_guard(output=None):
    class NoClients(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in {
                "openai",
                "anthropic",
                "litellm",
                "psycopg",
                "psycopg2",
                "transformers",
            }:
                raise RuntimeError("Offline modeling forbids client import " + fullname)
            return None

    sys.meta_path.insert(0, NoClients())
    pins = read(SOURCE / "input-pins.json")
    allowed = {str((ROOT / p).resolve()) for p in pins["files"]}
    evidence_roots = [str(ROOT / "trials"), str(ROOT / "research")]
    exempt = [str(BASE / "local-env")]
    if output is not None:
        exempt.append(str(Path(output).resolve()))
        # Ignore untracked neighboring caches; all trusted Python sources stay pinned.
        sys.pycache_prefix = str(Path(output).resolve() / "unused-bytecode-cache")

    def audit(event, args):
        if event in {
            "socket.connect",
            "socket.connect_ex",
            "socket.getaddrinfo",
            "subprocess.Popen",
            "os.system",
        }:
            raise RuntimeError("Offline modeling forbids " + event)
        if event == "open" and isinstance(args[0], (str, bytes)):
            path = str(Path(args[0].decode() if isinstance(args[0], bytes) else args[0]).resolve())
            if path in allowed and isinstance(args[1], str) and any(c in args[1] for c in "wax+"):
                raise RuntimeError("Pinned evidence is read-only: " + path)
            if any(path.startswith(p + "/") for p in evidence_roots):
                if path not in allowed and not any(path.startswith(p + "/") for p in exempt):
                    raise RuntimeError("Unassigned evidence/file access: " + path)

    sys.addaudithook(audit)


def timestamp():
    return datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
