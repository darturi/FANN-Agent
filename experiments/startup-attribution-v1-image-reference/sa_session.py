"""Explicit scopes around the original startup operations, with failure-safe teardown."""

import contextlib
import time

from pc_common import save
from sa_driver import Driver
from sa_monitor import preflight
from sa_observe import Observation, Probe


class Session:
    def __init__(self, out, arrow, works=None):
        self.obs = Observation(out, "runtime", Probe(arrow))
        self.driver = Driver(
            self.obs, sockets={c: str(w / "socket") for c, w in works.items()} if works else None
        )
        self.factory = None
        self.finished = False

    def checkpoint(self, name, metadata=None):
        meta = dict(metadata or {})
        if self.factory and self.factory.snapshot is not None:
            readers = self.factory.readers
            if len(readers) > 10:
                raise RuntimeError("Alias proof bound")
            meta["snapshot_aliases"] = dict(
                readers=len(readers),
                shared=sum(r.backend._snapshot is self.factory.snapshot for r in readers),
                rows=len(self.factory.snapshot.rows),
                retained=True,
            )
        self.obs.checkpoint(name, meta)

    def initialize(self, encoder=None):
        self.checkpoint("R00.instrument_preflight.before")
        preflight_cpu = time.process_time()
        capability = {}
        try:
            with self.obs.charge():
                from sa_preflight import original_mapping

                capability["original_source_mapping"] = original_mapping(self.obs)
                capability.update(preflight(self.obs))
                self.driver.install()
                capability.update(driver=self.driver.capability, bindings=self.driver.binding_proof)
        except BaseException as error:
            save(
                self.obs.out / "instrument-capability-failure.json",
                dict(
                    completed=False,
                    type=type(error).__name__,
                    message=str(error)[:2048],
                    partial=capability,
                    actual_driver=getattr(self.driver, "capability", None),
                ),
            )
            raise
        capability["added_preflight_cpu_seconds"] = time.process_time() - preflight_cpu
        if capability["added_preflight_cpu_seconds"] > 1:
            raise RuntimeError("Added preflight CPU ceiling")
        if encoder:
            encoder()
        save(self.obs.out / "instrument-capability.json", capability)
        self.checkpoint("R00.instrument_preflight.after")

    def call(self, name, fn, *args, role=None, **kwargs):
        self.checkpoint(name + ".before")
        start = time.monotonic_ns()
        value = fn(*args, **kwargs)  # unchanged delegated operation, not overhead
        self.checkpoint(name + ".after")
        if role:
            values = dict(logical_bytes=None)
            if role != "clone_scope" and isinstance(value, dict) and "bytes" in value:
                values["logical_bytes"] = value["bytes"]
                values["entries"] = value.get("file_count", value.get("files", 0))
            self.obs.role(role, start, time.monotonic_ns(), **values)
        return value

    def verify(self, fn, conn, bundle, phase, cell):
        name = "V." + phase + "." + cell
        self.checkpoint(name + ".before")
        start = time.monotonic_ns()
        with self.driver.verification(phase, cell):
            value = fn(conn, bundle)
        self.checkpoint(name + ".after")
        self.obs.role(phase + "_data_verify_" + cell.replace("640", ""), start, time.monotonic_ns())
        return value

    def notify(self, phase):
        mapping = dict(
            snapshot_identity_stream="S10.identity_begin",
            snapshot_identity_stream_end="S11.identity_end",
        )
        if phase in mapping:
            self.checkpoint(mapping[phase])

    def cleanup_call(self, name, fn, *args):
        errors = []
        try:
            self.checkpoint(name + ".before")
        except BaseException as exc:
            errors.append(exc)
        try:
            result = fn(*args)
        except BaseException as exc:
            errors.append(exc)
            result = None
        try:
            self.checkpoint(name + ".after")
        except BaseException as exc:
            errors.append(exc)
        if errors:
            raise BaseExceptionGroup("Cleanup and observation failures", errors)
        return result

    def cleanup_proof(self, name, fn, *args, role=None):
        self.obs.cleanup_checkpoint(name + ".before")
        start = time.monotonic_ns()
        value = fn(*args)
        self.obs.cleanup_checkpoint(name + ".after")
        if role:
            try:
                self.obs.role(
                    role,
                    start,
                    time.monotonic_ns(),
                    logical_bytes=value.get("bytes") if isinstance(value, dict) else None,
                    entries=value.get("file_count", 0) if isinstance(value, dict) else 0,
                )
            except BaseException as exc:
                self.obs.invalid.append(type(exc).__name__)
        return value

    def finalize(self, complete):
        # Always restore first, even if observer/probe/summary failed.
        errors = []
        try:
            self.checkpoint("R14.restore_verify.before")
        except BaseException as exc:
            errors.append(exc)
        try:
            if self.driver.monitor:
                self.driver.monitor.restore()
            with self.obs.charge():
                self.driver.restore()
        except BaseException as exc:
            errors.append(exc)
        try:
            if complete and not errors:
                save(self.obs.out / "driver-summary.json", self.driver.finish())
            self.checkpoint("R14.restore_verify.after")
            self.obs.flush()
            self.checkpoint("R15.runtime_complete")
        except BaseException as exc:
            errors.append(exc)
        try:
            self.obs.finish(complete and not errors)
        except BaseException as exc:
            errors.append(exc)
        self.finished = True
        if errors:
            raise BaseExceptionGroup("Diagnostic finalization failures", errors)


@contextlib.contextmanager
def snapshot_monitor(main, diag):
    from fannagent_pgvector.backend import NativeBackend
    from sa_monitor import SnapshotMonitor

    from fannagent.snapshot import Snapshot

    monitor = SnapshotMonitor(NativeBackend.snapshot, Snapshot.__init__, diag.obs)
    diag.driver.monitor = monitor
    try:
        with monitor:
            yield
    finally:
        diag.driver.monitor = None
