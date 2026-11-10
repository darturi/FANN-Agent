"""Trusted data-only validation of A3 delegation and original identity accounting."""

import importlib.util
from pathlib import Path

from pc_common import read, sha


def validate(stream, preflight, package, expected_identity, phases):
    p = Path(package)
    expected = read(p / "RESOURCE-FREEZE.json")["qualified_native_correctness"]["code_sha256"]
    if stream["qualified_code_sha256"] != expected or stream["helper_binding_restored"] is not True:
        raise ValueError("Qualified identity delegate/source/restoration differs")
    import hashlib
    import json

    fields = json.dumps(
        read(p / "origin-source.json")["metadata"],
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    metadata = stream["metadata_adapter"]
    if (
        metadata
        != dict(
            status="complete",
            source_reads=1,
            metadata_bytes=len(fields),
            metadata_sha256=hashlib.sha256(fields).hexdigest(),
            restored_before_producer_connection=True,
            original_state_unchanged=True,
            final_binding_restored=True,
        )
        or len(fields) > 16384
    ):
        raise ValueError("Bounded metadata identity/delegation/restoration proof differs")
    reference = p / "reference"
    source = reference / "si_verify.py"
    if sha(source) != read(reference / "manifest.json")["files"]["si_verify.py"]:
        raise ValueError("Original trusted identity verifier changed")
    spec = importlib.util.spec_from_file_location("ev_original_identity_verifier", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate(stream, preflight, reference, expected_identity, phases)
