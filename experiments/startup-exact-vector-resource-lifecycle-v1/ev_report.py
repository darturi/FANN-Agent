"""Independent data-only proof of the qualified A3 entry and finite host envelope."""

import math
from pathlib import Path

from pc_common import CONTRACT, read, sha


def require(condition, message):
    if not condition:
        raise ValueError("A3 resource proof: " + message)


def validate(campaign, package):
    p, run = Path(package), Path(campaign) / "run"
    cancellation = read(run / "ev-cancellation.json")
    require(
        type(cancellation) is dict
        and set(cancellation) == {"count", "records", "failed"}
        and type(cancellation["count"]) is int
        and cancellation["count"] == 0
        and type(cancellation["records"]) is list
        and cancellation["records"] == []
        and cancellation["failed"] is False
        and not (run / "cleanup-request.json").exists(),
        "cancellation or observer-loss evidence prevents positive qualification",
    )
    freeze = read(p / "RESOURCE-FREEZE.json")
    code = freeze["qualified_native_correctness"]["code_sha256"]
    preflight = read(run / "ev-runtime-preflight.json")
    require(
        preflight["status"] == "pass"
        and preflight["before_restore"] is True
        and preflight["synthetic_fixture"] is False,
        "native pre-restore gate",
    )
    require(
        preflight["actual_provenance"]
        == read(p / "reference/IMAGE-REFERENCE.json")
        == freeze["runtime_identity"],
        "exact interpreter/private-hook/library provenance",
    )
    require(
        preflight["code_sha256"] == code
        and preflight["reference_sha256"] == sha(p / "reference/IMAGE-REFERENCE.json")
        and preflight["helper_sha256"] == sha(p / "reference/si_stream.py"),
        "current qualified code",
    )
    origins = {
        "exact_vector": "/patch/a3/exact_vector.py",
        "integration": "/patch/a3/integration.py",
        "si_stream": "/patch/reference/si_stream.py",
        "fannagent.snapshot": "/patch/reference/frozen/vendor/fannagent/snapshot.py",
        "fannagent.store": "/patch/reference/frozen/vendor/fannagent/store.py",
        "fannagent_pgvector.backend": (
            "/patch/reference/frozen/vendor/fannagent_pgvector/backend.py"
        ),
    }
    require(
        preflight["module_origins"] == origins and preflight["bindings_restored"] is True,
        "effective source origins/restoration",
    )
    identity = read(p / "experiment.json")["snapshot_identity"]
    import hashlib
    import json

    fields = json.dumps(
        read(p / "origin-source.json")["metadata"],
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    metadata = read(run / "ev-metadata-preflight.json")
    require(
        metadata["status"] == "pass"
        and metadata["cases"] == 8
        and metadata["metadata_bytes"] == len(fields) <= 16384
        and metadata["metadata_sha256"] == hashlib.sha256(fields).hexdigest()
        and 0 <= metadata["cpu_seconds"] <= 1
        and metadata["helper_sha256"] == sha(p / "ev_metadata.py")
        and metadata["original_state_unchanged"] is True
        and metadata["bindings_restored"] is True
        and metadata["real_SQL"] == 0,
        "bounded frozen metadata preflight",
    )
    require(
        preflight["rows"] == 247286
        and preflight["identity"] == identity
        and preflight["ANN_searches"] == preflight["exact_searches"] == 0,
        "scope/count/identity",
    )
    require(read(run / "ev-bindings-final.json") == {"restored": True}, "final bindings")
    retained = read(run / "ev-retention.json")
    require(
        retained["root_released"] is False and len(retained["records"]) == 3, "root lifetime proof"
    )
    records = retained["records"]
    require(
        [r["phase"] for r in records]
        == ["startup_published", "epochs_complete", "final_verification_complete"],
        "retention phase coverage",
    )
    tokens = [r["snapshot_token"] for r in records]
    require(
        all(type(v) is int and v > 0 for v in tokens) and len(set(tokens)) == 1,
        "same retained root",
    )
    for row, readers, live in zip(records, (2, 10, 10), (2, 2, 0), strict=True):
        require(
            row["rows"] == row["packed_vectors"] == 247286
            and row["identity"] == identity
            and row["readers"] == row["shared_aliases"] == readers
            and row["live_readers"] == live
            and row["bindings_restored"] is True
            and row["retained"] is True,
            "packed rows/aliases through final verification",
        )
    final = read(run / "ev-host-integrity.json")
    require(
        final
        == dict(
            status="pass",
            package_manifest_sha256=sha(p / "manifest.json"),
            image_sha256=CONTRACT["runtime"]["image_sha256"],
            reference_manifest_sha256=sha(p / "reference/manifest.json"),
        ),
        "final SIF/capsule/reference integrity",
    )
    host = read(run / "ev-host-timing.json")
    keys = (
        "started",
        "pre_deadline",
        "runtime_started",
        "runtime_deadline",
        "post_started",
        "post_deadline",
        "finished",
        "final_deadline",
    )
    require(
        all(type(host[k]) in (int, float) and math.isfinite(host[k]) for k in keys),
        "finite host timing",
    )
    start = host["started"]
    require(
        abs(host["pre_deadline"] - start - 240) < 1e-6
        and start <= host["runtime_started"] < host["pre_deadline"],
        "host pre cap",
    )
    require(
        0 < host["runtime_deadline"] - host["runtime_started"] <= 3000
        and host["runtime_started"] <= host["post_started"] <= host["runtime_deadline"],
        "runtime envelope",
    )
    require(
        abs(host["final_deadline"] - start - 3480) < 1e-6
        and 0 < host["post_deadline"] - host["post_started"] <= 240
        and host["post_started"]
        <= host["finished"]
        < host["post_deadline"]
        <= host["final_deadline"],
        "post/outer margin",
    )
    require(
        host["wall_seconds"] == 3600
        and host["outer_margin_seconds"] == 120
        and host["termination_and_sampler_stop_inside_post"] is True,
        "unchanged whole budget",
    )
    guest = read(run / "ev-guest-timing.json")
    require(
        all(
            type(guest[k]) in (int, float) and math.isfinite(guest[k])
            for k in ("started", "deadline", "finished")
        ),
        "finite guest timing",
    )
    require(
        host["runtime_started"] <= guest["started"] <= guest["finished"] <= guest["deadline"]
        and guest["finished"] <= host["post_started"]
        and guest["deadline"] == host["runtime_deadline"]
        and 0 < guest["deadline"] - guest["started"] <= 3000
        and guest["cleanup_reserved_seconds"] == 600,
        "guest deadline/cleanup reserve",
    )
    launch = read(run / "host-launch.json")
    require(
        launch["runtime_deadline"] == guest["deadline"]
        and launch["package_manifest_sha256"] == sha(p / "manifest.json")
        and launch["image_sha256"] == final["image_sha256"]
        and launch["python_no_bytecode"] == "1",
        "launch/deadline identity",
    )
    return dict(
        status="pass",
        native_target_qualified=True,
        code_sha256=code,
        exact_provenance=preflight["actual_provenance"],
        roots_retained_through_final_verification=True,
        whole_host_elapsed_seconds=host["finished"] - start,
        ANN_searches=0,
        exact_searches=0,
        scope="startup/admission resource readiness only",
        full_B2f_released=False,
    )
