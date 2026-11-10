"""Shared deterministic design and identity checks (host Python 3.6+)."""
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    with Path(path).open('x') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b''):
            value.update(chunk)
    return value.hexdigest()
