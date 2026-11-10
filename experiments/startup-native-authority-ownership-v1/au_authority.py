"""Pinned permission plus independent site authority; no production roots enrolled."""

import copy
import math
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

from au_kernel import canonical, digest, trusted_json
from nh_common import HERE, config, inventory, private, sha
from release_policy import SPENT

PRODUCTION_RELEASES = frozenset()
PRODUCTION_SITES = frozenset()


def code_identity():
    return digest(inventory(HERE))


def exact(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError("Complete exact authority schema required")


def finite(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


@dataclass(frozen=True)
class Roots:
    release: str
    site: str
    domain: str

    def __post_init__(self):
        if self.domain not in ("native", "offline-kernel-test") or any(
            not re.fullmatch("[0-9a-f]{64}", s) for s in (self.release, self.site)
        ):
            raise ValueError("Independent trusted digest anchors required")
        if self.domain == "native" and (
            self.release not in PRODUCTION_RELEASES or self.site not in PRODUCTION_SITES
        ):
            raise RuntimeError("Native authority HOLD: no enrolled production roots")


class Lease:
    def __init__(self, owner, binding):
        self._owner, self._binding = owner, binding

    def check(self, argv=None, cleanup=False):
        return self._owner.check(self, argv, cleanup)


class Authority:
    def __init__(
        self,
        roots,
        release_path,
        site_path,
        claim_root,
        kernel,
        clock=time.monotonic,
        reader=trusted_json,
    ):
        if type(roots) is not Roots:
            raise ValueError("Trusted roots object required")
        self.roots, self.paths, self.root, self.kernel, self.clock, self.reader = (
            roots,
            (release_path, site_path),
            private(claim_root),
            kernel,
            clock,
            reader,
        )
        stat = self.root.stat()
        self.root_identity = (stat.st_dev, stat.st_ino, stat.st_uid, stat.st_mode)
        self.claimed = None
        self.lease = None
        self.origin = (os.getpid(), copy.deepcopy(kernel.snapshot()))
        self.validate()

    def validate(self):
        stat = private(self.root).stat()
        if (stat.st_dev, stat.st_ino, stat.st_uid, stat.st_mode) != self.root_identity:
            raise RuntimeError("Authority claim root replaced")
        grant = self.reader(self.paths[0], self.roots.release)
        site = self.reader(self.paths[1], self.roots.site)
        exact(
            grant,
            (
                "schema",
                "domain",
                "nonce",
                "job_id",
                "binding_sha256",
                "code_sha256",
                "image_sha256",
                "limits",
                "host_started",
                "work_deadline",
                "cleanup_deadline",
                "commands",
                "site_sha256",
            ),
        )
        exact(site, ("schema", "domain", "job_id", "kernel", "expires", "limits"))
        if (
            grant["schema"] != "a3.permission.v1"
            or site["schema"] != "a3.site.v1"
            or grant["domain"] != self.roots.domain
            or site["domain"] != self.roots.domain
        ):
            raise ValueError("Authority schema/domain differs")
        if (
            not re.fullmatch("[0-9a-f]{32}", grant["nonce"])
            or not re.fullmatch("[1-9][0-9]{0,9}", grant["job_id"])
            or grant["job_id"] in SPENT
            or grant["job_id"] != site["job_id"]
        ):
            raise ValueError("Fresh identity required; spent job rejected")
        if grant["site_sha256"] != self.roots.site:
            raise ValueError("Independent site identity differs")
        for key in ("binding_sha256", "code_sha256", "image_sha256"):
            if not isinstance(grant[key], str) or not re.fullmatch("[0-9a-f]{64}", grant[key]):
                raise ValueError("Bound digest required")
        if grant["code_sha256"] != code_identity():
            raise RuntimeError("Actual backend code differs from permission")
        cfg = config()
        if (
            digest(grant["limits"]) != digest(cfg["limits"])
            or digest(site["limits"]) != digest(cfg["limits"])
            or grant["image_sha256"] != cfg["image_sha256"]
        ):
            raise ValueError("Original limits/image changed")
        for key in ("host_started", "work_deadline", "cleanup_deadline"):
            if not finite(grant[key]):
                raise ValueError("Strict finite absolute endpoints required")
        start, work, end = (grant[k] for k in ("host_started", "work_deadline", "cleanup_deadline"))
        now = self.clock()
        if (
            not finite(now)
            or not start <= now < end
            or not start < work <= end <= start + 3480
            or work > start + 3240
            or not finite(site["expires"])
            or site["expires"] < end
        ):
            raise ValueError("Original absolute envelope unavailable")
        commands = grant["commands"]
        if (
            not isinstance(commands, list)
            or not 1 <= len(commands) <= 7
            or len(
                {
                    tuple(c)
                    for c in commands
                    if isinstance(c, list) and all(isinstance(a, str) for a in c)
                }
            )
            != len(commands)
        ):
            raise ValueError("Unique bounded explicit command inventory required")
        for argv in commands:
            if (
                not isinstance(argv, list)
                or not argv
                or len(argv) > 64
                or any(not isinstance(a, str) or not a or len(a) > 4096 or "\0" in a for a in argv)
                or not Path(argv[0]).is_absolute()
            ):
                raise ValueError("Explicit absolute command required")
        observed = self.kernel.snapshot()
        if (
            os.getpid() != self.origin[0]
            or observed != self.origin[1]
            or site["kernel"] != observed
        ):
            raise RuntimeError("Live authority/kernel generation differs")
        if self.roots.domain == "native" and observed["cgroup"].strip() in ("0::/", ""):
            raise RuntimeError("Job-private native scope unavailable")
        return grant

    def claim(self, binding_sha256, code_sha256):
        grant = self.validate()
        if (
            self.claimed is not None
            or binding_sha256 != grant["binding_sha256"]
            or code_sha256 != grant["code_sha256"]
            or self.clock() >= grant["work_deadline"]
        ):
            raise RuntimeError("Permission is absent, stale or already claimed")
        path = self.root / (grant["nonce"] + ".claim")
        # An uncertain/partial write is permanently spent; never unlink/retry.
        with path.open("xb") as handle:
            handle.write(
                canonical(
                    {
                        "permission": self.roots.release,
                        "site": self.roots.site,
                        "state": "claimed",
                        "pid": os.getpid(),
                        "binding": binding_sha256,
                    }
                )
            )
            handle.flush()
            os.fsync(handle.fileno())
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        self.claimed = sha(path)
        self.lease = Lease(self, binding_sha256)
        return self.lease

    def check(self, lease, argv=None, cleanup=False):
        grant = self.validate()
        if (
            lease is not self.lease
            or lease._owner is not self
            or sha(self.root / (grant["nonce"] + ".claim")) != self.claimed
        ):
            raise RuntimeError("Unrecognized or changed authority capability")
        if self.clock() >= grant["cleanup_deadline" if cleanup else "work_deadline"]:
            raise TimeoutError("Existing authority endpoint exhausted")
        if argv is not None and list(argv) not in grant["commands"]:
            raise RuntimeError("Unpermitted command")
        return grant


def native_authority(*args, **kwargs):
    raise RuntimeError("Native authority closed: no fresh permission or enrolled production roots")
