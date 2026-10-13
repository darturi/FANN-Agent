"""Validate all release artifacts before installation; standard library only."""

import hashlib
import json
import sys
from pathlib import Path


def verify(root):
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported release manifest")
    for name, expected in manifest["artifacts"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("release artifact escapes bundle")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"release artifact checksum differs: {name}")
    identity = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:20]
    if (root / "release-id").read_text().strip() != identity:
        raise ValueError("release identity differs")
    for name, image in manifest.get("images", {}).items():
        if image.startswith("sha256:") and (root / f"{name}.image").read_text().strip() != image:
            raise ValueError(f"runtime image differs: {name}")
    return identity


if __name__ == "__main__":
    print(verify(Path(sys.argv[1])))
