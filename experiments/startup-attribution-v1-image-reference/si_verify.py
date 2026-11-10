"""Data-only independent validation of stream provenance/accounting and scope."""

import json
import re
from pathlib import Path

from pc_common import read, sha


def validate(stream, preflight, package, expected_identity, phases):
    package = Path(package)

    def need(value, why):
        if not value:
            raise ValueError("Identity stream: " + why)

    need(stream["status"] == "complete" and stream["error_type"] is None, "incomplete")
    need(
        stream["invocations"] == 1 and stream["digest_completed"] and stream["binding_restored"],
        "invocation/restoration proof",
    )
    need(0 <= stream["elapsed_ns"] <= 600 * 10**9, "elapsed cap")
    p = stream["provenance"]
    need(p == preflight["provenance"], "preflight/acquisition provenance differs")
    need(
        p["implementation"] == "CPython"
        and p["python_version"].startswith("3.12.")
        and p["cache_tag"] == "cpython-312",
        "interpreter",
    )
    need(
        p["binding_module"] == "fannagent.snapshot"
        and p["binding_name"] == "digest"
        and p["original"] == "fannagent.store.digest",
        "binding target",
    )
    need(p["helper_sha256"] == sha(package / "si_stream.py"), "helper source")
    for label in ("snapshot", "store"):
        need(
            p["sources"][label] == sha(package / "frozen/vendor/fannagent" / (label + ".py")),
            "frozen source",
        )
    for key in ("encoder_sha256", "json_module_sha256"):
        need(bool(re.fullmatch("[a-f0-9]{64}", p[key])), "encoder provenance")
    need(
        preflight["status"] == "pass"
        and preflight["cases"] == 8
        and 0 < preflight["oracle_bytes"] <= 1024**2
        and 0 <= preflight["cpu_seconds"] <= 5,
        "literal parity preflight",
    )
    value = stream["stream"]
    n = 247286
    counters = (
        "rows",
        "component_calls",
        "fields_bytes",
        "rows_bytes",
        "separator_bytes",
        "framing_bytes",
        "total_bytes",
        "max_row_bytes",
        "max_pending_bytes",
        "hash_updates",
    )
    need(all(type(value[k]) is int and value[k] >= 0 for k in counters), "integer counters")
    need(
        value["digest"] == expected_identity
        and value["rows"] == n
        and value["component_calls"] == n + 1,
        "identity/row/component count",
    )
    fields = json.dumps(
        read(package / "origin-source.json")["metadata"],
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    need(value["fields_bytes"] == len(fields) <= 16384, "fields bytes")
    need(
        0 < value["max_row_bytes"] <= 65536
        and n <= value["rows_bytes"] <= n * value["max_row_bytes"],
        "row byte cap",
    )
    need(
        value["separator_bytes"] == n - 1
        and value["framing_bytes"] == len(b'{"fields":') + len(b',"rows":[') + len(b"]}"),
        "framing accounting",
    )
    total = sum(
        value[k] for k in ("fields_bytes", "rows_bytes", "separator_bytes", "framing_bytes")
    )
    need(value["total_bytes"] == total <= 16 * 1024**3, "total bytes")
    need(
        value["max_pending_bytes"] == min(total, 65536)
        and value["hash_updates"] == (total + 65535) // 65536,
        "bounded writer accounting",
    )
    names = [p["phase"] for p in phases]
    need(
        names.count("snapshot_identity_stream") == names.count("snapshot_identity_stream_end") == 1,
        "phase coverage",
    )
    start, end = (
        names.index(name) for name in ("snapshot_identity_stream", "snapshot_identity_stream_end")
    )
    need(
        names.index("snapshot_load") < start < end < names.index("snapshot_identity"), "phase order"
    )
    need(stream["elapsed_ns"] <= phases[end]["time_ns"] - phases[start]["time_ns"], "phase elapsed")
    return dict(
        identity=expected_identity,
        rows=n,
        invocations=1,
        component_calls=n + 1,
        total_bytes=total,
        max_pending_bytes=value["max_pending_bytes"],
        binding_restored=True,
        provenance=p,
    )
