"""Benign nested-guardian integration fixture; never a native scientific entry."""

import os
import subprocess
import sys
import time
from pathlib import Path

from nh_lifecycle import stop_owned
from nh_retention import RawStore
from ni_authority import delegated_ticket, guest_owner
from ni_groups import LinuxGroups


def main():
    ticket = delegated_ticket(sys.argv[1], sys.argv[2], native=False)
    if ticket["domain"] != "local-kernel-test" or os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("Offline nested fixture only")
    raw = Path(sys.argv[3])
    store = RawStore.existing(raw)
    end = min(ticket["maximum_guest_end"], time.monotonic() + 1.5)
    owner = guest_owner(ticket, ticket["binding_sha256"], end, time.monotonic() + 15)
    groups = LinuxGroups(owner.lease, store, end, owner.cleanup_end)
    proc = None
    handle = None
    try:
        with (raw / "guest-fixture.log").open("x") as log:
            proc, handle = groups.spawn(ticket["commands"][0], stdout=log, stderr=subprocess.STDOUT)
            while proc.poll() is None:
                if time.monotonic() >= end:
                    raise TimeoutError("Nested fixture phase deadline")
                time.sleep(0.05)
            if time.monotonic() >= end:
                raise TimeoutError("Nested fixture completion late")
            code = proc.returncode
            proof = groups.finish(handle)
            handle = None
            store.json(
                "delegated-fixture-proof.json",
                {
                    "science_exit": code,
                    "proof": proof,
                    "native_release": False,
                    "budget": owner.kernel.budget.usage(),
                },
            )
            return code
    finally:
        if handle is not None:
            stop_owned(groups, handle, proc, owner.cleanup_end)
            groups.finish(handle)
        owner.kernel.close()


if __name__ == "__main__":
    raise SystemExit(main())
