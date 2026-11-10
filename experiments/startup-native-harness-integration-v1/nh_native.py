"""Allocated-host process adapter; no scheduler and no usable native grant."""

import os
import subprocess
import time

from nh_common import closed_native, read
from nh_storage import draft_command


def launch(context, on_ready, store):
    closed_native()
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("A distinct authorized allocation would be required")
    spec = draft_command(
        context["inner"],
        context["integration"],
        store.root,
        context["work"],
        context["image"],
        context["apptainer"],
        context["host_started"] + 3240,
    )
    argv = spec["argv"]
    position = argv.index(str(context["image"]))
    argv[position:position] = ["--env", "NX_HOST_STARTED=" + str(context["host_started"])]
    proc = None
    ready = None
    with (store.root / "host-native.log").open("x") as log:
        try:
            proc = subprocess.Popen(
                argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
            )
            store.json("native-owned-pid.json", {"pid": proc.pid})
            while proc.poll() is None:
                marker = store.root / "native-ready.json"
                if ready is None and marker.exists():
                    value = read(marker)
                    ready = on_ready(value["binding_sha256"], value["guest_started"])
                limit = ready["guest_end"] if ready else context["host_started"] + 240
                if time.monotonic() >= limit:
                    raise TimeoutError("Original ready/guest absolute endpoint")
                store.budget()
                time.sleep(0.1)
            if proc.returncode or ready is None:
                raise RuntimeError("Target guest incomplete or readiness missing")
            return read(store.root / "guest-status.json")
        finally:
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)


if __name__ == "__main__":
    closed_native()
