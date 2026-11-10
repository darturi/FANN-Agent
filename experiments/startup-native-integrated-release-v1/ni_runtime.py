"""Full original local runtime reference check; native entry remains closed."""

import argparse
import sys
from pathlib import Path

from nh_common import MAIN, core, offline, read, save


def main():
    offline()
    p = argparse.ArgumentParser()
    for n in ("inner", "workspace", "out"):
        p.add_argument("--" + n, type=Path, required=True)
    p.add_argument("--profile", choices=("local", "target"), default="local")
    a = p.parse_args()
    if a.profile == "target":
        from ni_authority import delegated_ticket

        delegated_ticket()
    core(a.inner)
    denied = []

    def audit(event, args):
        if event in ("socket.connect", "socket.bind", "subprocess.Popen"):
            denied.append(event)
            raise RuntimeError("Runtime reference forbids external calls")

    sys.addaudithook(audit)
    sys.path.insert(0, str(a.workspace / MAIN))
    from sa_driver import provenance

    hardware = None
    if a.profile == "target":
        from hardware import capture

        hardware = capture()
    actual = provenance()
    expected = read(a.inner / "QUALIFICATION-CONTRACT.json")[a.profile + "_reference"]
    if actual != expected:
        raise RuntimeError("Full frozen local provenance differs")
    save(
        a.out,
        {
            "status": "pass",
            "actual_provenance": actual,
            "hardware": hardware,
            "external_attempts": len(denied),
            "native_release": False,
        },
    )


if __name__ == "__main__":
    main()
