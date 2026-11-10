"""Torch-only execution on verified copies of the exact retained clusters."""

import argparse
import json
import os
import shutil
import signal
from pathlib import Path

from pc_common import (
    CELLS,
    CONTRACT,
    RESOURCE,
    Budget,
    bootstrap,
    read,
    replace,
    save,
    sha,
    verify,
)
from pc_restore import (
    IDENTITY_SHA,
    clone,
    control_state,
    graph_files,
    inventory,
    verify_data,
    verify_graphs,
)


class Journal:
    def __init__(self, out, budget):
        self.out, self.budget = Path(out), budget
        self.handles, self.buffer = {}, []
        self.hold = False
        self.bytes = 0

    def emit(self, name, row):
        if self.hold:
            self.buffer.append((name, row))
            return
        data = json.dumps(row, sort_keys=True, allow_nan=False) + "\n"
        self.bytes += len(data.encode())
        if self.bytes > 512 * 1024**2:
            raise RuntimeError("Evidence-byte ceiling exhausted")
        if name not in self.handles:
            self.handles[name] = (self.out / (name + ".jsonl")).open("x")
        self.handles[name].write(data)
        self.handles[name].flush()

    def flush_buffer(self):
        buffered, self.buffer = self.buffer, []
        for name, row in buffered:
            self.emit(name, row)

    def checkpoint(self):
        if self.hold:
            raise RuntimeError("Checkpoint cannot enter primary burst")
        self.flush_buffer()
        if (
            sum(p.stat().st_size for p in self.out.rglob("*") if p.is_file())
            > 512 * 1024**2 - 1024**2
        ):
            raise RuntimeError("Whole raw evidence ceiling/reserve exhausted")
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
        self.hold = False
        self.checkpoint()
        for h in self.handles.values():
            h.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--block", type=int, required=True)
    args = parser.parse_args()
    package, out, work = map(Path, ("/patch", "/results", "/run"))
    verify(package)
    if (
        os.uname().sysname != "Linux"
        or os.uname().machine != "x86_64"
        or args.block != 0
        or not os.environ.get("SLURM_JOB_ID")
        or os.environ.get("SLURM_CPUS_PER_TASK") != "4"
    ):
        raise RuntimeError("One declared x86_64 Torch allocation is required")
    bootstrap(package)
    import psycopg
    import pyarrow as pa

    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    from database import start, stop
    from execution import load_backend
    from fannagent_pgvector.profiles import PROFILE
    from pc_interface import audit
    from pc_metadata import Observer
    from pc_proc import Proc
    from pc_settings import inspect_memory
    from pc_snapshot import prepare_requests
    from pc_trace import Trace, category
    from psycopg.conninfo import make_conninfo
    from sr_interface import Factory

    budget = Budget()
    journal = Journal(out, budget)
    trace = Trace(budget, journal.emit)
    original_connect = trace.install(psycopg)
    frozen, Base = load_backend(package / "frozen")
    works = {c: work / c for c in CELLS}
    admins = {}
    factory = None
    proc = None
    before = None
    result = None
    error = None
    started_servers = []
    cleanup_errors = []
    final_verified = False

    def notify(phase, **kw):
        row = dict(
            phase=phase,
            backend_searches=budget.calls,
            provider_calls=0,
            time_ns=__import__("time").monotonic_ns(),
            **kw,
        )
        journal.emit("phases", row)
        replace(out / "progress.json", row)
        print(json.dumps(row), flush=True)

    def alarm(number, frame):
        raise TimeoutError("Native stage/global deadline: " + str(budget.stage))

    for sig in (signal.SIGALRM, signal.SIGTERM, signal.SIGUSR1, signal.SIGINT):
        signal.signal(sig, alarm)
    enter = budget.enter

    def stage(name):
        enter(name)
        signal.setitimer(signal.ITIMER_REAL, max(0.001, budget.remaining()))
        journal.checkpoint()

    budget.enter = stage

    observer = Observer(
        budget, lambda n, r: journal.emit(n, {**r, **getattr(observer, "tags", {})})
    )

    original_check = budget.check

    def checked(allowance=0):
        original_check(allowance)
        if budget.stage != "final_cleanup":
            import time

            health = read(out / "memory-health.json")
            if health["status"] != "running" or time.monotonic_ns() - health["last_ns"] > 5 * 10**9:
                raise RuntimeError("Required host memory sampler unhealthy/stale")

    budget.check = checked

    def reader_context(reader):
        from si_stream import assert_restored

        assert_restored()
        from pc_trace import READER_CONTEXT_SQL

        audit(reader)
        with category("observer"):
            extra = reader.connection.execute(READER_CONTEXT_SQL, prepare=False).fetchone()
        if tuple(extra) != ("auto", "on"):
            raise RuntimeError("Reader session context differs")
        journal.emit("reader-context", dict(reader=reader.identity, extra=list(extra)))

    def final_proof():
        from si_stream import assert_restored

        assert_restored()
        proofs = {}
        for cell, conn in admins.items():
            if sha(works[cell] / "database-identity.json") != IDENTITY_SHA:
                raise RuntimeError("Backend identity metadata changed")
            proofs[cell] = verify_data(conn, Path("/bundle"))
            observer.catalog(conn, cell, "final", candidate=cell == "partial640")
            original = graph_files(works[cell], "base/16384/264013")
            partial = graph_files(works[cell], "base/16384/270339")
            if original != CONTRACT["graphs"]["native640"] or partial != (
                CONTRACT["graphs"]["partial640"]["partial"] if cell == "partial640" else {}
            ):
                raise RuntimeError("Final graph identity changed")
            proofs[cell].update(original_graph_files=original, partial_graph_files=partial)
        if sha("/opt/postgresql/lib/vector.so") != CONTRACT["runtime"]["module_sha256"]:
            raise RuntimeError("Final module changed")
        save(
            out / "final-integrity.json",
            dict(copies=proofs, module_sha256=CONTRACT["runtime"]["module_sha256"]),
        )

    try:
        stage("restore_identity")
        notify("restore_identity")
        if (
            os.environ.get("TORCH_IMAGE_SHA256") != CONTRACT["runtime"]["image_sha256"]
            or PROFILE.fingerprint != CONTRACT["runtime"]["runtime_profile_hash"]
            or PROFILE.native_registry_hash != CONTRACT["runtime"]["registry_hash"]
        ):
            raise RuntimeError("Image/profile/registry differs")
        # Check the explicit read-only bind; never probe it with a write.
        mounts = Path("/proc/self/mountinfo").read_text().splitlines()
        if not any(
            len(m.split()) > 5 and m.split()[4] == "/retained" and "ro" in m.split()[5].split(",")
            for m in mounts
        ):
            raise RuntimeError("Retained source is not proven read-only mounted")
        from si_stream import preflight

        save(out / "identity-preflight.json", preflight(package))
        before = inventory(Path("/retained"))
        save(out / "source-before.json", before)
        verify_graphs(Path("/retained"))
        controls = {c: control_state(Path("/retained") / c / "pgdata") for c in CELLS}
        save(out / "source-control.json", controls)
        proc = Proc(budget, journal.emit)
        save(
            out / "runtime-process.json",
            dict(
                pid=proc.client,
                starttime=proc.client_start,
                cgroup=Path("/proc/self/cgroup").read_text(),
                mountinfo=Path("/proc/self/mountinfo").read_text(),
            ),
        )
        budget.check()
        copies = {}
        for cell in CELLS:
            copies[cell] = clone(Path("/retained") / cell, works[cell])
        if inventory(Path("/retained")) != before:
            raise RuntimeError("Source changed during copies")
        save(out / "copies.json", copies)
        verify_graphs(work)
        if sha("/opt/postgresql/lib/vector.so") != CONTRACT["runtime"]["module_sha256"]:
            raise RuntimeError("Module bytes differ")
        for cell in CELLS:
            # Server children inherit C3; reader backends are repinned explicitly later.
            proc.pin(proc.client, proc.layout["selected"][3])
            try:
                start(works[cell])
            finally:
                proc.pin(proc.client, proc.layout["selected"][0])
            started_servers.append(cell)
            conn = psycopg.connect(
                make_conninfo(
                    frozen.job_connection(works[cell], admin=True), dbname="torch_reviews"
                ),
                autocommit=True,
            )
            admins[cell] = conn
            with category("observer"):
                pid, directory = conn.execute(
                    "SELECT pg_backend_pid(),current_setting('data_directory')", prepare=False
                ).fetchone()
            if Path(directory).resolve() != (works[cell] / "pgdata").resolve():
                raise RuntimeError("Server data path differs")
            proc.pin(pid, proc.layout["selected"][3])
            proc.server(cell, pid, works[cell])
            actual = observer.catalog(conn, cell, "before_build", candidate=cell == "partial640")
            if actual != read(package / "b2d-catalogs.json")[cell]:
                raise RuntimeError(
                    "Complete catalog/statistics differ from exact retained B2d source"
                )
            verify_data(conn, Path("/bundle"))
        save(out / "memory-preflight.json", inspect_memory(admins))
        stage("snapshot_admission")
        factory = Factory(
            Base, Path("/bundle"), works, CONTRACT["targets"], observer, budget, journal.emit
        )
        main = {c: factory.create(c, c.split("640")[0] + "-reference") for c in CELLS}

        def stream_record(value):
            if len(json.dumps(value).encode()) > 65536:
                raise RuntimeError("Identity stream summary cap")
            save(out / "identity-stream.json", value)

        items, snapshot_proof = prepare_requests(main, factory, package, notify, stream_record)
        save(out / "snapshot-qualified.json", snapshot_proof)
        proc.freeze_client_threads()
        for c, r in main.items():
            proc.bind(r, works[c], 0)
            reader_context(r)
        save(out / "runtime-identity.json", CONTRACT["runtime"])
        save(
            out / "restore-qualified.json",
            dict(
                catalogs=True,
                data_rows=247286,
                graph_hashes=True,
                module_sha256=sha("/opt/postgresql/lib/vector.so"),
                source_read_only=True,
            ),
        )
        save(out / "admitted-requests.json", dict(count=len(items), executed=0))
        import time

        for epoch in (0, 1):
            stage("epoch" + str(epoch))
            notify("epoch" + str(epoch) + "_admission")
            for reader in main.values():
                proc.repin(reader, epoch)
            readers = []
            for name in RESOURCE["epoch_creation_order"][str(epoch)]:
                cell = name.rsplit("-", 1)[0]
                reader = factory.create(cell, "e" + str(epoch) + "-" + name)
                readers.append(reader)
                proc.bind(reader, works[cell], epoch)
                reader_context(reader)
            notify("epoch" + str(epoch) + "_hold")
            end = time.monotonic() + RESOURCE["resources"]["epoch_hold_seconds"]
            while time.monotonic() < end:
                budget.check()
                time.sleep(min(0.25, max(0, end - time.monotonic())))
            for reader in readers:
                reader.close()
            journal.checkpoint()
        result = dict(
            outcome="complete_startup_resource_acquisition",
            completed_epochs=2,
            admitted_requests=len(items),
            executed_requests=0,
        )
        if (
            budget.calls
            or trace.search_sql
            or trace.prohibited
            or trace.scans != {"snapshot": 1, "data": 2}
        ):
            raise RuntimeError("Zero-search or initial scan accounting differs")
    except BaseException as exc:
        error = dict(type=type(exc).__name__, message=str(exc))
    finally:
        try:
            journal.hold = False
            journal.flush_buffer()
            stage("final_cleanup")
            notify("finalize_verify_cleanup")
            if factory:
                factory.close()
            if result is not None:
                final_proof()
                final_verified = True
        except BaseException as exc:
            error = error or dict(type=type(exc).__name__, message=str(exc))
        finally:
            if factory:
                try:
                    factory.close()
                except BaseException as exc:
                    cleanup_errors.append(str(exc))
            for conn in admins.values():
                try:
                    conn.close()
                except BaseException as exc:
                    cleanup_errors.append(str(exc))
            for cell in reversed(CELLS):
                try:
                    stop(works[cell])
                except BaseException as exc:
                    cleanup_errors.append(str(exc))
            try:
                if result is not None:
                    verify_graphs(work)
                    save(
                        out / "stopped-copies.json",
                        dict(
                            graphs_match=True,
                            controls={c: control_state(works[c] / "pgdata") for c in CELLS},
                        ),
                    )
            except BaseException as exc:
                cleanup_errors.append(str(exc))
            try:
                if before is not None:
                    after = inventory(Path("/retained"))
                    save(out / "source-after.json", after)
                    if after != before:
                        raise RuntimeError("Protected stopped source changed")
            except BaseException as exc:
                cleanup_errors.append(str(exc))
            psycopg.connect = original_connect
            signal.setitimer(signal.ITIMER_REAL, 0)
        cleanup = dict(
            errors=cleanup_errors,
            all_readers_closed=factory is None or all(r.closed for r in factory.readers),
            databases_stopped=all(not (works[c] / "pgdata/postmaster.pid").exists() for c in CELLS),
        )
        for cell in CELLS:
            log = works[cell] / "server.log"
            if log.is_file():
                shutil.copyfile(log, out / (cell + "-server.log"))
        save(out / "cleanup.json", cleanup)
        if cleanup_errors or not cleanup["all_readers_closed"] or not cleanup["databases_stopped"]:
            error = error or dict(type="RuntimeError", message="Cleanup/source preservation failed")
        if result is not None and not final_verified:
            error = error or dict(
                type="RuntimeError", message="Final scientific integrity unverified"
            )
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
        save(
            out / "status.json",
            dict(
                status="failed" if error else "complete",
                result=result,
                final_integrity_verified=final_verified,
                backend_searches=budget.calls,
                operations=dict(budget.operations),
                sql=dict(budget.sql),
                search_sql=trace.search_sql,
                plan_packets=observer.plan_packets,
                prohibited_sql_attempts=trace.prohibited,
                full_scans=dict(trace.scans),
                reader_connections=len(factory.readers) if factory else 0,
                maximum_live_readers=factory.maximum_live if factory else 0,
                telemetry=proc.charges() if proc else None,
                elapsed_seconds=budget.clock() - budget.started,
                provider_calls=0,
                new_fits=0,
                confirmation_queries=0,
            ),
        )
        journal.close()
        save(
            out / "LOCK.json",
            dict(
                complete=not error,
                files={
                    str(p.relative_to(out)): sha(p)
                    for p in sorted(out.rglob("*"))
                    if p.is_file()
                    and p.name != "LOCK.json"
                    and not p.name.startswith((".", "memory", "host-", "protected-source-"))
                },
            ),
        )
        save(out / "job-exit.json", dict(exit_code=int(bool(error)), work_directory_retained=True))
    if error:
        raise RuntimeError("Failed native qualification/acquisition; preserve raw")


if __name__ == "__main__":
    main()
