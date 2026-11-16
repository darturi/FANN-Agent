"""Hash-bound M1 original-graph qualification/cost phase; no protected or provider interface."""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from time import monotonic, perf_counter_ns

from common import publish, require, sha, write
from m1_design import ARMS, FILTERS, GROUPS, ledger
from m1_experiment import load_programs, offline, quality, timing, work

HERE = Path(__file__).resolve().parent
PACKAGE_SHA = "b596c69bbab0bb49d720df02b820e5a9f2c1652a47e67b6b327f16f8769663bc"
IMAGE = "7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a"


def main():
    p = argparse.ArgumentParser()
    for name in ("package", "bundle", "prepared", "work", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--phase", choices=("timing", "work"), required=True)
    p.add_argument("--quality", type=Path)
    args = p.parse_args()
    args.ef = 640
    args.fixture = False
    args.previous_attempts = 0
    args.native_work = None
    sys.path.insert(0, str(args.package))
    from rb_native import (
        BASE_MANIFEST,
        RUNNER,
        load_stage,
        memory_events,
        resource_limits,
        watchdog,
    )

    require(
        os.uname().machine == "x86_64" and os.environ.get("SLURM_JOB_ID", "").isdigit(),
        "requires x86 Slurm compute allocation",
    )
    binding = json.loads((HERE / "binding.json").read_text())
    plan = json.loads((HERE / "m1-plan.json").read_text())
    pins = {
        "queries.jsonl": "queries_sha256",
        "compiled-programs.json": "programs_sha256",
        "m1-plan.json": "plan_sha256",
        "serving.py": "serving_source_sha256",
        "startup.py": "startup_source_sha256",
        "prior-references.jsonl": "prior_references_sha256",
        "expected.jsonl": "expected_sha256",
    }
    for name, key in pins.items():
        require(sha(HERE / name) == binding[key], "M1 input changed: " + name)
    require(
        plan["attempts"] == ledger()
        and plan["global_attempt_cap"] == 1000000
        and plan["timing_groups"] == [list(g) for g in GROUPS],
        "prospective schedule/ledger changed",
    )
    key = args.phase + "_module_sha256"
    require(
        sha(HERE / (args.phase + "-module.so"))
        == sha("/opt/postgresql/lib/vector.so")
        == binding[key],
        "wrong phase module",
    )
    require(sha(args.bundle / "images/runtime.sif") == IMAGE, "runtime image changed")
    queries = [json.loads(line) for line in (HERE / "queries.jsonl").read_text().splitlines()]
    require(
        len(queries) == len({q["id"] for q in queries}) == 3150
        and all(len(q["vector"]) == 768 for q in queries),
        "frozen query coverage/dimensions changed",
    )
    source_ids = {
        int(re.fullmatch(r"reviews-clean-v(\d+)-(?:unfiltered|votes\d+)", q["id"])[1])
        for q in queries
    }
    require(
        source_ids == set(binding["development_source_indices"]) and len(source_ids) == 450,
        "non-development input",
    )
    stage = load_stage(args.package, PACKAGE_SHA)
    require(
        sha(args.bundle / "manifest.json") == BASE_MANIFEST
        and sha("/opt/torch-reviews/runner.py") == RUNNER,
        "base capsule changed",
    )
    base = json.loads((args.bundle / "manifest.json").read_text())["files"]
    for name in (
        "images/runtime.sif",
        "inputs/reviews.parquet",
        "inputs/local-identity.json",
        "experiment.json",
    ):
        require(sha(args.bundle / name) == base[name], "base dataset/input changed: " + name)
    ready = json.loads((args.prepared / "READY.json").read_text())
    require(
        ready["architecture"] == "x86_64"
        and ready["image_sha256"] == IMAGE
        and json.loads((args.prepared / "database-identity.json").read_text())
        == stage.index
        == binding["graph"],
        "prepared graph identity changed",
    )
    for folder in (args.package, args.bundle, args.prepared, HERE):
        require(os.statvfs(folder).f_flag & os.ST_RDONLY, "inputs must be mounted read-only")
    runner, Backend = stage.frozen.execution.load_backend(stage.source)
    from startup import install

    startup = install(stage.frozen.restore)
    for d in (args.work, args.output):
        require(
            d.is_dir() and not any(d.iterdir()) and not d.stat().st_mode & 0o077,
            "require private empty output/work",
        )
    (args.work / "socket").mkdir(mode=0o700)
    (args.work / ".torch-owned").write_text(os.environ["SLURM_JOB_ID"] + "\n")
    cache = None
    if args.phase == "work":
        require(
            sha(HERE / "native-work-reference.jsonl") == binding["native_work_reference_sha256"],
            "native work bridge input changed",
        )
        args.native_work = {
            r["id"]: r["counts"]
            for r in (
                json.loads(line)
                for line in (HERE / "native-work-reference.jsonl").read_text().splitlines()
            )
        }
        require(
            set(args.native_work) == {q["id"] for q in queries},
            "native work bridge query coverage differs",
        )
        require(
            args.quality is not None and os.statvfs(args.quality).f_flag & os.ST_RDONLY,
            "qualified timing input must be read-only",
        )
        receipt = json.loads((args.quality / "receipt.json").read_text())
        require(
            receipt["status"] == "M1_timing_complete"
            and receipt["job_id"] == os.environ["SLURM_JOB_ID"]
            and receipt["programs_sha256"] == binding["programs_sha256"],
            "work/quality binding differs",
        )
        require(
            sha(args.quality / "quality.jsonl") == receipt["raw_sha256"]["quality.jsonl"],
            "quality cache digest differs",
        )
        cache = {
            (r["id"], n): value
            for r in (
                json.loads(line)
                for line in (args.quality / "quality.jsonl").read_text().splitlines()
            )
            for n, value in r["results"].items()
        }
        require(len(cache) == 3150 * len(ARMS), "quality cache coverage differs")
        args.previous_attempts = receipt["searches"]["total"]
    import rb_native

    rb_native.MEMORY_BYTES = 48 * 1024**3
    limits, memory_group = resource_limits()
    events = memory_events(memory_group)
    from psycopg import connect
    from psycopg.conninfo import make_conninfo

    counter = {"total": 0}
    started = monotonic()
    entries = load_programs()
    with watchdog(22500 if args.phase == "timing" else 4500):
        try:
            identity = stage.frozen.restore(
                stage.source,
                args.bundle,
                args.prepared,
                args.work,
                runner,
                extra_sql=(
                    HERE / ("functions.sql" if args.phase == "timing" else "work-functions.sql")
                ).read_text(),
            )
            require(identity == binding["graph"], "private restore graph changed")
            dsn = make_conninfo(
                runner.job_connection(args.work, admin=True), dbname="torch_reviews"
            )
            with connect(dsn, autocommit=True) as keeper, keeper.transaction():
                keeper.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                require(
                    keeper.execute("SELECT current_setting('max_connections')").fetchone()
                    == ("32",),
                    "reader capacity changed",
                )
                keeper.execute("SET LOCAL idle_in_transaction_session_timeout=0")
                keeper.execute("LOCK TABLE public.reviews IN SHARE MODE NOWAIT")
                args.snapshot = keeper.execute("SELECT pg_export_snapshot()").fetchone()[0]
                heap, index = keeper.execute(
                    "SELECT 'public.reviews'::regclass::oid,'public.reviews_hnsw'::regclass::oid"
                ).fetchone()
                rows = keeper.execute(
                    "SELECT ctid::text,total_votes FROM ONLY public.reviews"
                ).fetchall()
                source = keeper.execute("SELECT id,total_votes FROM ONLY public.reviews").fetchall()
                require(
                    len(source) == len({i for i, _ in source}) == 247286,
                    "corpus/source ID mapping differs",
                )
                maps = []
                for t in FILTERS:
                    start = perf_counter_ns()
                    meta = publish(args.work / f"membership-{t}.bin", heap, index, rows, t)
                    meta["build_ns"] = perf_counter_ns() - start
                    maps.append(meta)
                write(args.output / "membership-setup.json", maps)
                write(args.output / "private-startup.json", startup)
                eligible = {
                    t: {i for i, votes in source if t < 0 or votes is not None and votes >= t}
                    for t in FILTERS
                }
                write(
                    args.output / "eligibility.json",
                    {str(t): sorted(values) for t, values in eligible.items()},
                )
                prior = {
                    r["id"]: r
                    for r in (
                        json.loads(line)
                        for line in (HERE / "prior-references.jsonl").read_text().splitlines()
                    )
                }
                expected = {
                    r["id"]: r
                    for r in (
                        json.loads(line)
                        for line in (HERE / "expected.jsonl").read_text().splitlines()
                    )
                }
                require(
                    set(prior) == set(expected) == {q["id"] for q in queries},
                    "development reference coverage differs",
                )
                truths = offline(Backend, args, queries, eligible, prior, counter)
                if args.phase == "timing":
                    cache, summary = quality(
                        Backend, args, queries, eligible, truths, expected, counter, entries
                    )
                    require(
                        summary["prefixes"]
                        == {"reached": 9436, "partial": 1496, "all_actual_outputs_scored": True},
                        "prefix inventory changed; do not invent missing labels",
                    )
                    timing(Backend, args, queries, eligible, cache, counter)
                else:
                    summary = work(Backend, args, queries, eligible, truths, cache, counter)
                stage.frozen.verify_import(runner, args.bundle, args.work)
        finally:
            stage.frozen.stop(args.work)
            for t in FILTERS:
                (args.work / f"membership-{t}.bin").unlink(missing_ok=True)
            stage.frozen.verify_index(args.work, stage.index)
    require(memory_events(memory_group) == events, "memory limit event")
    require(counter == ledger()[args.phase], "exact phase attempt ledger differs")
    receipt = {
        "status": "M1_" + args.phase + "_complete",
        "job_id": os.environ["SLURM_JOB_ID"],
        "phase": args.phase,
        "split_sha256": binding["split_manifest_sha256"],
        "module_sha256": binding[key],
        "programs_sha256": binding["programs_sha256"],
        "runtime_profile": binding["runtime_profile"],
        "plan_sha256": binding["plan_sha256"],
        "serving_source_sha256": binding["serving_source_sha256"],
        "searches": counter,
        "summary": summary,
        "limits": limits,
        "graph": stage.index,
        "data_index_before_after": True,
        "cleanup_verified": True,
        "exact_serving_calls": 0,
        "offline_exact_queries": 3150,
        "provider_calls": 0,
        "validation_test_queries": 0,
        "groups": 450,
        "conditions": 7,
        "elapsed_seconds": monotonic() - started,
        "machine": {"hostname": os.uname().nodename, "architecture": os.uname().machine},
        "raw_sha256": {p.name: sha(p) for p in args.output.iterdir() if p.is_file()},
    }
    write(args.output / "receipt.json", receipt)
    print("M1_" + args.phase.upper() + "_QUALIFICATION_PASSED", flush=True)


if __name__ == "__main__":
    main()
