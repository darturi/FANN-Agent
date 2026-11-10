"""Private explicit approval plus existing scheduler/kernel authority and delegation."""

import copy
import os
import re
import stat
import time
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from ni_control_reads import control_read

from au_authority import Lease, code_identity, finite
from nh_common import config, digest, private, read, save, sha
from ni_site import ScopedKernel, resolve_scope
from release_policy import SPENT

APPROVAL_TEXT = (
    "I authorize one new zero-search A3 qualification allocation: "
    "1 hour, 4 physical CPUs, 32 GiB; no retry."
)


def approved(record, plan_sha, uid):
    keys = {
        "schema",
        "approval",
        "plan_sha256",
        "uid",
        "nonce",
        "allocations",
        "ANN_searches",
        "exact_searches",
        "retry",
    }
    if (
        not isinstance(record, dict)
        or set(record) != keys
        or record["schema"] != "a3.explicit-approval.v1"
        or record["approval"] != APPROVAL_TEXT
        or record["plan_sha256"] != plan_sha
        or type(record["uid"]) is not int
        or record["uid"] != uid
        or not isinstance(record["nonce"], str)
        or not re.fullmatch("[0-9a-f]{32}", record["nonce"])
        or type(record["allocations"]) is not int
        or record["allocations"] != 1
        or type(record["ANN_searches"]) is not int
        or record["ANN_searches"] != 0
        or type(record["exact_searches"]) is not int
        or record["exact_searches"] != 0
        or record["retry"] is not False
    ):
        raise RuntimeError("Distinct explicit approval is absent or differs")
    return record


def private_record(path):
    p = Path(path)
    private(p.parent)
    s = p.lstat()
    if not stat.S_ISREG(s.st_mode) or stat.S_IMODE(s.st_mode) != 0o600 or s.st_uid != os.getuid():
        raise ValueError("Private user-owned permission record required")
    return read(p)


class BoundOwner:
    def __init__(
        self,
        root,
        kernel,
        binding,
        commands,
        work_end,
        cleanup_end,
        nonce,
        native,
        refresh=lambda: None,
    ):
        self.root = private(root)
        self.kernel = kernel
        self.origin = copy.deepcopy(kernel.snapshot())
        self.pid = os.getpid()
        self.code = code_identity()
        self.binding = binding
        self.commands = [list(c) for c in commands]
        self.work_end = work_end
        self.cleanup_end = cleanup_end
        self.nonce = nonce
        self.native = native
        self.refresh = refresh
        self.lease = Lease(self, binding)
        save(
            self.root / "lease.json",
            {
                "pid": self.pid,
                "binding": binding,
                "nonce": nonce,
                "code": self.code,
                "native": native,
            },
        )
        self.claim_sha = sha(self.root / "lease.json")

    def check(self, lease, argv=None, cleanup=False):
        if (
            lease is not self.lease
            or lease._owner is not self
            or os.getpid() != self.pid
            or self.kernel.snapshot() != self.origin
            or sha(self.root / "lease.json") != self.claim_sha
            or code_identity() != self.code
        ):
            raise RuntimeError("Authority/binding/process/code generation changed")
        if not time.monotonic() < (self.cleanup_end if cleanup else self.work_end):
            raise TimeoutError("Original authority endpoint exhausted")
        if argv is not None:
            if list(argv) not in self.commands:
                raise RuntimeError("Command not in explicit phase plan")
            self.refresh()
        return {
            "nonce": self.nonce,
            "binding_sha256": self.binding,
            "code_sha256": self.code,
            "image_sha256": config()["image_sha256"],
            "limits": config()["limits"],
            "commands": self.commands,
            "work_deadline": self.work_end,
            "cleanup_deadline": self.cleanup_end,
            "native": self.native,
        }


def readonly_mount(mountinfo, path):
    p = Path(path)
    matches = []
    for line in mountinfo.splitlines():
        left, sep, right = line.partition(" - ")
        if not sep:
            continue
        fields = left.split()
        if len(fields) < 6 or "\\" in fields[4]:
            continue
        m = Path(fields[4])
        if p == m or p.is_relative_to(m):
            matches.append((len(m.parts), fields[5].split(",")))
    matches.sort(reverse=True)
    if not matches or "ro" not in matches[0][1]:
        raise RuntimeError("Host delegation must be bound read-only")


def validate_ticket(ticket, code, uid, now):
    required = {
        "schema",
        "domain",
        "nonce",
        "binding_sha256",
        "code_sha256",
        "image_sha256",
        "archive_sha256",
        "manifest_sha256",
        "host_started",
        "latest_ready",
        "maximum_guest_end",
        "host_post_end",
        "uid",
        "job_id",
        "commands",
        "budget_inode",
        "budget_device",
        "budget_path",
        "claims_path",
        "limits",
        "host_boot",
    }
    if (
        not isinstance(ticket, dict)
        or set(ticket) != required
        or ticket["schema"] != "a3.host-delegation.v1"
        or ticket["domain"] not in ("native", "local-kernel-test")
    ):
        raise ValueError("Complete host delegation required")
    if (
        any(
            not finite(ticket[k])
            for k in ("host_started", "latest_ready", "maximum_guest_end", "host_post_end")
        )
        or not ticket["host_started"] <= now < ticket["maximum_guest_end"]
        or ticket["latest_ready"] != ticket["host_started"] + 240
        or ticket["maximum_guest_end"] != ticket["host_started"] + 3240
        or ticket["host_post_end"] != ticket["host_started"] + 3480
    ):
        raise ValueError("Original host/guest/outer reserves differ")
    if (
        type(ticket["uid"]) is not int
        or ticket["uid"] != uid
        or ticket["code_sha256"] != code
        or digest(ticket["limits"]) != digest(config()["limits"])
        or ticket["image_sha256"] != config()["image_sha256"]
        or ticket["archive_sha256"] != config()["original_archive_sha256"]
        or ticket["manifest_sha256"] != config()["original_manifest_sha256"]
    ):
        raise RuntimeError("Delegated identity/code/original limits differ")
    if (
        ticket["domain"] == "native"
        and ticket["host_boot"] != control_read("sys/kernel/random/boot_id").strip()
    ):
        raise RuntimeError("Host boot generation differs")
    if ticket["domain"] == "native" and (
        not re.fullmatch("[1-9][0-9]*", ticket["job_id"]) or ticket["job_id"] in SPENT
    ):
        raise ValueError("Fresh actual host job required")
    if not re.fullmatch("[0-9a-f]{32}", ticket["nonce"]) or not re.fullmatch(
        "[0-9a-f]{64}", ticket["binding_sha256"]
    ):
        raise ValueError("Exact nonce/binding required")
    return ticket


def delegated_ticket(path=None, expected=None, native=True):
    p = Path(path or os.environ.get("NI_TICKET", "/authority/ticket.json"))
    wanted = expected or os.environ.get("NI_TICKET_SHA", "")
    if not re.fullmatch("[0-9a-f]{64}", wanted) or sha(p) != wanted:
        raise RuntimeError("Independent host ticket identity missing")
    ticket = validate_ticket(read(p), code_identity(), os.getuid(), time.monotonic())
    if native:
        if ticket["domain"] != "native":
            raise RuntimeError("Fixture delegation cannot grant native work")
        readonly_mount(control_read("self/mountinfo"), p)
    return ticket


def guest_owner(ticket, binding, work_end, cleanup_end):
    if ticket["binding_sha256"] != binding:
        raise RuntimeError("Host/guest binding differs")
    fd = os.open(ticket["budget_path"], os.O_RDWR | os.O_NOFOLLOW)
    s = os.fstat(fd)
    if (
        (s.st_dev, s.st_ino) != (ticket["budget_device"], ticket["budget_inode"])
        or s.st_size != 16
        or s.st_uid != os.getuid()
        or stat.S_IMODE(s.st_mode) != 0o600
    ):
        os.close(fd)
        raise RuntimeError("Shared original observer budget differs")

    raw = control_read("self/cgroup")
    mounts = control_read("self/mountinfo")
    scope = resolve_scope(raw, mounts) if ticket["domain"] == "native" else None
    kernel = ScopedKernel(fd, scope)
    owner = BoundOwner(
        ticket["claims_path"],
        kernel,
        binding,
        ticket["commands"],
        work_end,
        cleanup_end,
        ticket["nonce"],
        ticket["domain"] == "native",
    )
    return owner


_STAGE = ContextVar("integrated_stage_authority", default=None)


@contextmanager
def stage_authority(authority):
    if getattr(authority, "native", False) is not True:
        raise RuntimeError("Live allocated host required for native staging")
    authority.validate()
    token = _STAGE.set(authority)
    try:
        yield
    finally:
        _STAGE.reset(token)


def require_stage_authority():
    authority = _STAGE.get()
    if authority is None:
        raise RuntimeError("Native stage entry has no admitted allocation")
    authority.validate()
