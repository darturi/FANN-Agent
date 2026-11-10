"""Read-only source capture; Python 3.6+ and no credential reads outside results."""
import hashlib
import json
from pathlib import Path


def digest(path):
    result=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):result.update(chunk)
    return result.hexdigest()


def capture(root):
    root=root.resolve()
    paths=sorted(root.rglob('*'))
    if any(p.is_symlink() for p in paths):raise ValueError('Source result tree contains symlinks')
    return {str(p.relative_to(root)):digest(p) for p in paths if p.is_file()}


def check_pinned(root, pin):
    expected=json.loads(pin.read_text())
    actual=capture(root)
    for name,value in expected['files'].items():
        if actual.get(name)!=value:raise ValueError('Completed baseline file differs: '+name)
    return actual
