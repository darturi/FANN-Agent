"""Integrated allocated-host authority and owned Apptainer launch; explicit approval only."""

import os
import re
import shutil
import time
from pathlib import Path

from ni_control_reads import control_read

from au_authority import code_identity
from nh_common import HERE, ROOT, config, read, save, sha
from nh_lifecycle import stop_owned
from nh_storage import draft_command
from ni_authority import BoundOwner, approved, private_record
from ni_groups import LinuxGroups
from ni_guest_entry import recipe
from ni_site import ScopedKernel, SiteClient, resolve_scope, trusted_binary


def runtime_seconds(text):
    m = re.fullmatch(r"(?:(\d+)-)?(\d+):(\d{2}):(\d{2})", text)
    if m is None:
        raise ValueError("Scheduler elapsed time unavailable")
    return int(m[1] or 0) * 86400 + int(m[2]) * 3600 + int(m[3]) * 60 + int(m[4])


class Allocation:
    def __init__(self, package, campaign, record, plan):
        self.package, self.campaign, self.record, self.plan = (
            Path(package),
            Path(campaign),
            record,
            plan,
        )
        self.native = False
        self.binding = None
        approval = approved(
            private_record(campaign / "approval.json"), sha(package / "PLAN.json"), os.getuid()
        )
        if (
            record["approval_sha256"] != sha(campaign / "approval.json")
            or record["job_id"] != os.environ.get("SLURM_JOB_ID")
            or record["dispatch"] != {"status": "submitted", "job_id": record["job_id"]}
        ):
            raise RuntimeError("Known fresh dispatch and explicit approval required")
        self.approval = approval
        self.client = SiteClient(shutil.which("scontrol") or "/usr/bin/scontrol")
        self.runtime_identity = trusted_binary(record["apptainer"])
        self.site = self.client.probe()
        requested = time.monotonic()
        self.job = self.client.job(
            record["job_id"], os.getuid(), record["account"], record["comment"]
        )
        self.started = requested - runtime_seconds(self.job["record"].get("RunTime", "")) - 2
        self.validate()
        self.native = True

    def validate(self):
        approved(
            private_record(self.campaign / "approval.json"),
            sha(self.package / "PLAN.json"),
            os.getuid(),
        )
        if sha(self.campaign / "approval.json") != self.record["approval_sha256"] or self.record[
            "job_id"
        ] != os.environ.get("SLURM_JOB_ID"):
            raise RuntimeError("Allocation permission changed")
        return self.job

    def refresh(self):
        self.validate()
        self.job = self.client.job(
            self.record["job_id"], os.getuid(), self.record["account"], self.record["comment"]
        )

    def bind(self, key):
        if self.binding is not None:
            raise RuntimeError("Authority binding already used")
        self.validate()
        self.binding = key


def make_ticket(context, store, commands):
    a = context["authority"]
    work = Path(context["work"])
    budget = work / "observer-budget"
    fd = os.open(budget, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
    os.write(fd, b"\0" * 16)
    from au_budget import ReadBudget
    from ni_control_reads import prepay

    context["control_precharge"] = prepay(ReadBudget(fd))
    s = os.fstat(fd)
    raw = control_read("self/cgroup")
    mounts = control_read("self/mountinfo")
    scope = resolve_scope(raw, mounts, a.record["job_id"])
    kernel = ScopedKernel(fd, scope, privileged_runtime=True)
    for name in ("host-claims", "guest-claims", "authority"):
        (work / name).mkdir(mode=0o700)
    t = {
        "schema": "a3.host-delegation.v1",
        "domain": "native",
        "nonce": a.approval["nonce"],
        "binding_sha256": context["binding_sha256"],
        "code_sha256": code_identity(),
        "image_sha256": config()["image_sha256"],
        "archive_sha256": config()["original_archive_sha256"],
        "manifest_sha256": config()["original_manifest_sha256"],
        "host_started": context["host_started"],
        "latest_ready": context["host_started"] + 240,
        "maximum_guest_end": context["host_started"] + 3240,
        "host_post_end": context["host_started"] + 3480,
        "uid": os.getuid(),
        "job_id": a.record["job_id"],
        "commands": commands,
        "budget_inode": s.st_ino,
        "budget_device": s.st_dev,
        "budget_path": "/work/observer-budget",
        "claims_path": "/work/guest-claims",
        "limits": config()["limits"],
        "host_boot": kernel.snapshot()["boot"],
    }
    save(work / "authority/ticket.json", t)
    return t, kernel


def launch(context, on_ready, store):
    a = context["authority"]
    a.refresh()
    guest_context = {
        "inner": "/qual",
        "workspace": str(ROOT),
        "work": "/work",
        "science": "/results/science",
        "profile": "target",
        "bridge_snapshot": "/integration-sealed",
    }
    ticket, kernel = make_ticket(context, store, recipe(guest_context))
    work = Path(context["work"])
    started = context["host_started"]
    spec = draft_command(
        context["inner"],
        HERE,
        store.root,
        work,
        context["image"],
        context["apptainer"],
        started + 3240,
    )
    # draft ends: image, python, /integration/nh_guest.py
    argv = spec["argv"][:-2] + [
        "python",
        "/integration/ni_guest_entry.py",
        "--ticket",
        "/authority/ticket.json",
        "--expected",
        sha(work / "authority/ticket.json"),
    ]
    pos = argv.index(str(context["image"]))
    argv[pos:pos] = [
        "--bind",
        str(work / "authority") + ":/authority:ro",
        "--bind",
        str(context["bridge_snapshot"]) + ":/integration-sealed:ro",
    ]
    owner = BoundOwner(
        work / "host-claims",
        kernel,
        context["binding_sha256"],
        [argv],
        started + 3240,
        started + 3480,
        ticket["nonce"],
        True,
        a.refresh,
    )
    groups = LinuxGroups(owner.lease, store, started + 3240, started + 3480, context["host_python"])
    context["host_owner"] = owner
    context["host_groups"] = groups
    ready = None
    proc = None
    handle = None
    with (store.root / "host-native.log").open("x") as log:
        try:
            proc, handle = groups.spawn(
                argv,
                stdout=log,
                stderr=-2,
                env={
                    k: v
                    for k, v in {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}.items()
                    if not k.startswith(("APPTAINERENV_", "SINGULARITYENV_"))
                    and k
                    not in (
                        "APPTAINER_BIND",
                        "APPTAINER_BINDPATH",
                        "SINGULARITY_BIND",
                        "SINGULARITY_BINDPATH",
                        "LD_PRELOAD",
                        "PYTHONHOME",
                    )
                },
            )
            while True:
                marker = store.root / "native-ready.json"
                if ready is None and marker.exists():
                    row = read(marker)
                    if (
                        row["nonce"] != ticket["nonce"]
                        or row["binding_sha256"] != context["binding_sha256"]
                    ):
                        raise RuntimeError("Unrelated native readiness")
                    ready = on_ready(row["binding_sha256"], row["guest_started"])
                deadline = ready["guest_end"] if ready else started + 240
                if time.monotonic() >= deadline:
                    raise TimeoutError("Original ready/guest endpoint")
                store.budget()
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
            if proc.returncode or ready is None:
                raise RuntimeError("Native guest incomplete")
            if time.monotonic() >= ready["guest_end"]:
                raise TimeoutError("Complete container/guardian exceeded original guest endpoint")
            context.setdefault("_host_post_started", time.monotonic())
            groups.finish(handle)
            handle = None
            return read(store.root / "guest-status.json")
        finally:
            context.setdefault("_host_post_started", time.monotonic())
            end = min(context["_host_post_started"] + 240, started + 3480)
            if handle is not None:
                stop_owned(groups, handle, proc, end)
                groups.finish(handle)
            store.json(
                "host-owned-proof.json",
                {
                    "proof": groups.proof,
                    "guardian_exit": groups.process.returncode if groups.process else None,
                    "shared_budget": kernel.budget.usage(),
                    "control_precharge": context["control_precharge"],
                    "independent_host_authority": a.job,
                },
            )
            kernel.close()
