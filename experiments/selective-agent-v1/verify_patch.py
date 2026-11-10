"""Check this patch and the unchanged original bundle. Host Python 3.6+."""
import hashlib
import json
import sys
from pathlib import Path

import integrity


def check(patch, bundle, full=True):
    patch, bundle = patch.resolve(), bundle.resolve()
    manifest = json.loads(integrity.safe_file(patch, 'manifest.json').read_text())
    if manifest['original_manifest_sha256'] != integrity.EXPECTED_MANIFEST:
        raise ValueError('Patch targets a different original bundle.')
    for name, expected in manifest['files'].items():
        path = integrity.safe_file(patch, name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Patch checksum mismatch: ' + name)
    original = integrity.load_manifest(bundle)
    if full:
        integrity.announce('Verifying original bundle; patch and image are separate, unchanged inputs.')
        return integrity.verify(bundle, original, progress=integrity.announce)
    return original


if __name__ == '__main__':
    try:
        print(json.dumps(check(Path(sys.argv[1]), Path(sys.argv[2]))))
    except (OSError, ValueError, KeyError, IndexError) as error:
        raise SystemExit('Verification failed: ' + str(error))
