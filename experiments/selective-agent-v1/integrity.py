"""Verify the already sealed Reviews bundle, with progress; Python 3.6+ only."""
import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

EXPECTED_MANIFEST = "5538cb6a4bd03da6a00fae4913fdfe9237b481f902bcd15d98666f2e99af070a"


def safe_file(root, relative):
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or root not in path.parents or not path.is_file():
        raise ValueError("Invalid bundle path: {}".format(relative))
    return path


def load_manifest(root, expected=None):
    root = root.resolve()
    if expected is None:
        expected = EXPECTED_MANIFEST
    raw = safe_file(root, "manifest.json").read_bytes()
    if expected and hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("This is not the sealed October 13 bundle manifest.")
    manifest = json.loads(raw.decode("utf-8"))
    if manifest.get("experiment") != "torch-reviews-first" or not manifest.get("files"):
        raise ValueError("Expected a nonempty torch-reviews-first manifest.")
    for relative, digest in manifest["files"].items():
        if not isinstance(relative, str) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Invalid manifest entry.")
    return manifest


def verify(root, manifest, names=None, progress=None, interval=5):
    root = root.resolve()
    names = list(manifest["files"] if names is None else names)
    started = last = time.monotonic()
    byte_count = 0
    for index, relative in enumerate(names, 1):
        path = safe_file(root, relative)
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
                byte_count += len(chunk)
                now = time.monotonic()
                if progress and now - last >= interval:
                    progress("Reading {}/{}: {}; {:.1f} MiB read; {:.1f}s elapsed".format(index, len(names), relative, byte_count / 2**20, now - started))
                    last = now
        if digest.hexdigest() != manifest["files"][relative]:
            raise ValueError("Checksum mismatch: {}".format(relative))
        if progress and (index == 1 or index % 100 == 0 or index == len(names)):
            progress("Verified {}/{} files; {:.1f} MiB read; {:.1f}s elapsed".format(index, len(names), byte_count / 2**20, time.monotonic() - started))
            last = time.monotonic()
    return {"verified_files": len(names), "verified_bytes": byte_count,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "experiment": manifest["experiment"], "provider_calls_allowed": 0}


def announce(message):
    print(message, file=sys.stderr, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    root = args.bundle.resolve()
    try:
        manifest = load_manifest(root)
        announce("Verifying {} sealed files in {}".format(len(manifest["files"]), root))
        print(json.dumps(verify(root, manifest, progress=announce)), flush=True)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, "Verification failed: {}\n".format(error))


if __name__ == "__main__":
    main()
