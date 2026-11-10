"""Torch-only two-copy physical-index study, with durable early-stop evidence."""

import argparse
import json
import os
import shutil
import signal
import time
from pathlib import Path

from pa_common import (
    INDEX,
    PROFILE_SHA,
    Budget,
    bootstrap,
    digest,
    lines,
    read,
    replace,
    save,
    sha,
    verify,
)


class Journal:
    def __init__(self, out, budget):
        self.out = out
        self.budget = budget
        self.handles = {}

    def emit(self, name, row):
        if name not in self.handles:
            self.handles[name] = (self.out / (name + ".jsonl")).open("x")
        h = self.handles[name]
        h.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
        h.flush()

    def checkpoint(self):
        for h in self.handles.values():
            h.flush()
            os.fsync(h.fileno())
        replace(
            self.out / "charges-checkpoint.json",
            dict(
                searches=self.budget.calls,
                operations=dict(self.budget.operations),
                sql=dict(self.budget.sql),
                stages=self.budget.stages,
                stage=self.budget.stage,
                elapsed_seconds=self.budget.clock() - self.budget.started,
            ),
        )

    def close(self):
        self.checkpoint()
        for h in self.handles.values():
            h.close()


def graph_files(work, filepath):
    if not __import__("re").fullmatch(r"base/[0-9]+/[0-9]+", filepath):
        raise ValueError("Unsafe index filepath")
    directory = work / "pgdata" / Path(filepath).parent
    name = Path(filepath).name
    files = {p.name: sha(p) for p in sorted(directory.glob(name + "*")) if p.is_file()}
    if not files:
        raise RuntimeError("New graph files missing")
    return files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--block", required=True, type=int)
    args = parser.parse_args()
    package, out, work = map(Path, ("/patch", "/results", "/run"))
    cfg = verify(package)
    if os.uname().machine != "x86_64" or args.block != 0 or not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Single declared Torch allocation required")
    source = read(package / "frozen/experiment.json")
    if os.environ.get("TORCH_IMAGE_SHA256") != source["image_sha256"]:
        raise RuntimeError("Image differs")
    bootstrap(package)
    import psycopg
    from database import prepare, stop
    from execution import load_backend
    from fannagent_pgvector.profiles import PROFILE
    from pa_interface import Factory
    from pa_measure import admit, measure
    from pa_metadata import Observer
    from pa_trace import Trace, category
    from psycopg.conninfo import make_conninfo
    from runtime_base import verify_import, verify_index

    budget = Budget()
    journal = Journal(out, budget)
    trace = Trace(budget, journal.emit)
    original_connect = trace.install(psycopg)
    frozen, Base = load_backend(package / "frozen")
    works = {m: work / m for m in ["native640", "partial640"]}
    factory = None
    admins = {}
    expected = None
    newgraph = None
    result = None
    error = None
    cleanup_errors = []
    started = time.perf_counter_ns()
    final_verified = False

    def notify(phase, **fields):
        replace(
            out / "progress.json",
            dict(phase=phase, backend_searches=budget.calls, provider_calls=0, **fields),
        )
        print(json.dumps(dict(phase=phase, backend_searches=budget.calls, **fields)), flush=True)

    def alarm(number, frame):
        raise TimeoutError("Stage/global deadline exhausted: " + str(budget.stage))

    for sig in (signal.SIGALRM, signal.SIGTERM, signal.SIGUSR1, signal.SIGINT):
        signal.signal(sig, alarm)
    enter = budget.enter

    def stage(name):
        enter(name)
        signal.setitimer(signal.ITIMER_REAL, max(0.001, budget.remaining()))
        journal.checkpoint()

    budget.enter = stage
    from pa_settings import build_controls, inspect_memory

    observer = Observer(budget, journal.emit)
    try:
        budget.enter("restore")
        notify("restore_and_verify")
        host = read(out / "resource-preflight.json")
        if host["memory_gib"] != 32:
            raise RuntimeError("Resource preflight missing")
        stat = os.statvfs(work)
        if stat.f_bavail * stat.f_frsize < host["quota"]["/scratch"]["required_bytes"]:
            raise RuntimeError("Scratch capacity changed")
        for mode, directory in works.items():
            directory.mkdir(mode=0o700)
            for name in ["socket", "tmp"]:
                (directory / name).mkdir(mode=0o700)
            (directory / ".torch-owned").write_text(os.environ["SLURM_JOB_ID"] + "\n")
            expected = prepare(
                package / "frozen", Path("/bundle"), Path("/prepared"), directory, frozen
            )
            admins[mode] = psycopg.connect(
                make_conninfo(frozen.job_connection(directory, admin=True), dbname="torch_reviews"),
                autocommit=True,
            )
            observer.catalog(admins[mode], mode, "before_build", candidate=False)
        if (
            sha("/opt/postgresql/lib/vector.so") != source["module_sha256"]
            or PROFILE.fingerprint != PROFILE_SHA
        ):
            raise RuntimeError("Module/profile identity differs")
        save(out / "database-identity.json", expected)
        save(out / "memory-preflight.json", inspect_memory(admins))
        journal.checkpoint()
        budget.enter("build")
        notify("build_partial_index")
        c = admins["partial640"]
        buildstart = time.perf_counter_ns()
        build_settings = build_controls(c, budget)
        with category("observer"):
            c.execute(
                "CREATE INDEX "
                + INDEX
                + " ON public.reviews USING hnsw (embedding vector_cosine_ops) "
                "WITH (m=16,ef_construction=64) WHERE total_votes >= 108",
                prepare=False,
            )
            c.execute("CHECKPOINT", prepare=False)
            # Restore admin timeout; comparison readers still inherit their original30s.
            c.execute("SET statement_timeout=30000", prepare=False)
        cat = observer.catalog(c, "partial640", "after_build", candidate=True, stable=False)
        new = next(i for i in cat["indexes"] if i["relname"] == INDEX)
        newgraph = dict(index=new, files_sha256=graph_files(works["partial640"], new["filepath"]))
        newgraph["index_identity"] = digest(newgraph)
        save(
            out / "build.json",
            dict(
                start_ns=buildstart,
                end_ns=time.perf_counter_ns(),
                graph=newgraph,
                build_settings=list(build_settings),
            ),
        )
        targets = {
            "native640": dict(
                index=dict(oid=expected["index_oid"], relname="reviews_hnsw"),
                index_identity=expected["index_identity"],
            ),
            "partial640": dict(
                index=dict(oid=int(new["oid"]), relname=INDEX),
                index_identity=newgraph["index_identity"],
            ),
        }
        for directory in works.values():
            verify_index(directory, expected)
        observer.catalog(admins["native640"], "native640", "after_build", candidate=False)
        save(out / "targets.json", targets)
        journal.checkpoint()
        # Snapshot/admission are charged interstage work, still within build cap/global reserve.
        factory = Factory(Base, Path("/bundle"), works, targets, observer, budget, journal.emit)
        reference = factory.create("native640", "initial-native-reference")
        if reference.origin["settings"] != cfg["source_settings"]:
            raise RuntimeError("Source settings changed")
        snapshot = reference.backend.snapshot()
        factory.snapshot = snapshot
        eligibility = dict(
            source_ids=snapshot.source_ids,
            votes=[r["metadata"]["total_votes"] for r in snapshot.rows],
        )
        if (
            digest(eligibility) != sha(package / "eligibility.json")
            or snapshot.identity != cfg["snapshot_identity"]
        ):
            raise RuntimeError("Snapshot/eligibility differs")
        items = admit(snapshot, lines(package / "queries.jsonl"))
        factory.requests = {i["query"]["id"]: i["query"] for i in items}
        save(
            out / "shared-initialization.json",
            dict(
                snapshot_identity=snapshot.identity,
                eligibility_sha256=digest(eligibility),
                admitted_requests=200,
                source_effort=320,
                reference_effort=640,
                origin=reference.origin,
                two_private_copies=True,
            ),
        )
        save(
            out / "runtime-identity.json",
            dict(
                module_sha256=source["module_sha256"],
                image_sha256=source["image_sha256"],
                runtime_profile_hash=PROFILE.fingerprint,
                registry_hash=PROFILE.native_registry_hash,
                synthetic_mock=False,
            ),
        )
        result = measure(
            factory,
            reference,
            budget,
            package,
            out,
            items,
            notify,
            journal.emit,
            journal.checkpoint,
        )
    except BaseException as e:
        error = dict(type=type(e).__name__, message=str(e))
        notify("failed", error=error)
    finally:
        try:
            budget.enter("final")
            notify("finalize_verify_cleanup")
            signal.setitimer(signal.ITIMER_REAL, max(0.001, min(470, budget.remaining() - 130)))
            if result is not None:
                final = {}
                for mode, directory in works.items():
                    verify_index(directory, expected)
                    verify_import(frozen, Path("/bundle"), directory)
                    observer.catalog(admins[mode], mode, "final", candidate=mode == "partial640")
                    final[mode] = dict(
                        original_graph_files=graph_files(directory, expected["index_filepath"]),
                        data_bits_verified=True,
                    )
                if newgraph["files_sha256"] != graph_files(
                    works["partial640"], newgraph["index"]["filepath"]
                ):
                    raise RuntimeError("Partial graph bytes changed")
                if sha("/opt/postgresql/lib/vector.so") != source["module_sha256"]:
                    raise RuntimeError("Native module changed")
                final["partial640"]["partial_graph_files"] = graph_files(
                    works["partial640"], newgraph["index"]["filepath"]
                )
                final["module_sha256"] = sha("/opt/postgresql/lib/vector.so")
                save(out / "final-integrity.json", final)
                final_verified = True
        except BaseException as e:
            if error is None:
                error = dict(type=type(e).__name__, message=str(e))
        finally:
            signal.setitimer(signal.ITIMER_REAL, max(0.001, min(130, budget.remaining())))
            if factory:
                try:
                    factory.close()
                except BaseException as e:
                    cleanup_errors.append(str(e))
            for c in admins.values():
                try:
                    c.close()
                except BaseException as e:
                    cleanup_errors.append(str(e))
            for mode, directory in works.items():
                try:
                    stop(directory)
                except BaseException as e:
                    cleanup_errors.append(str(e))
                if (directory / "server.log").exists():
                    shutil.copyfile(directory / "server.log", out / (mode + "-server.log"))
            signal.setitimer(signal.ITIMER_REAL, 0)
            psycopg.connect = original_connect
        cleanup = dict(
            all_readers_closed=not factory or all(r.closed for r in factory.readers),
            databases_stopped=all(
                not (d / "pgdata/postmaster.pid").exists() for d in works.values()
            ),
            errors=cleanup_errors,
        )
        save(out / "cleanup.json", cleanup)
        if cleanup_errors or not cleanup["all_readers_closed"] or not cleanup["databases_stopped"]:
            error = error or dict(type="RuntimeError", message="Reader/database cleanup failed")
        if error:
            save(
                out / "failure.json",
                dict(
                    **error,
                    backend_searches=budget.calls,
                    operations=dict(budget.operations),
                    partial_result=result,
                ),
            )
        elif not final_verified:
            error = dict(type="RuntimeError", message="Final integrity missing")
        if error is None:
            expected_calls = {
                "closed_cost_futility": 202,
                "closed_negative_quality": 802,
                "complete_measurement": 16802,
            }[result["outcome"]]
            if budget.calls != expected_calls:
                error = dict(type="RuntimeError", message="Terminal search count differs")
        if error and not (out / "failure.json").exists():
            save(
                out / "failure.json",
                dict(**error, backend_searches=budget.calls, operations=dict(budget.operations)),
            )
        save(
            out / "status.json",
            dict(
                status="failed" if error else "complete",
                result=result,
                backend_searches=budget.calls,
                operations=dict(budget.operations),
                sql=dict(budget.sql),
                search_sql=trace.search_sql,
                final_integrity_verified=final_verified,
                provider_calls=0,
                confirmation_queries=0,
                new_fits=0,
                reader_connections=len(factory.readers) if factory else 0,
                maximum_live_readers=factory.maximum_live if factory else 0,
                elapsed_seconds=(time.perf_counter_ns() - started) / 1e9,
            ),
        )
        save(
            out / "job-exit.json",
            dict(exit_code=int(error is not None), work_directory_retained=True),
        )
        journal.close()
        save(
            out / "LOCK.json",
            dict(
                package_manifest_sha256=sha(package / "manifest.json"),
                complete=error is None,
                files_sha256={
                    p.name: sha(p)
                    for p in sorted(out.iterdir())
                    if p.is_file()
                    and p.name
                    not in [
                        "LOCK.json",
                        "progress.json",
                        "protected-source-before.json",
                        "resource-preflight.json",
                    ]
                },
            ),
        )
    if error:
        raise RuntimeError(error["message"])
    notify("complete", outcome=result["outcome"])


if __name__ == "__main__":
    main()
