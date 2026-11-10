"""Reject user-mode emulation and pin four distinct physical x86 cores."""

import os
import platform
import re
import struct
from pathlib import Path


def validate_x86(machine, system, header, cpuinfo, maps, environ):
    if (
        machine != "x86_64"
        or system != "Linux"
        or header[:4] != b"\x7fELF"
        or len(header) < 20
        or header[4:6] != bytes([2, 1])
        or struct.unpack_from("<H", header, 18)[0] != 62
    ):
        raise RuntimeError("Native x86_64 ELF/Linux required")
    vendors = re.findall(r"^vendor_id\s*:\s*(\S+)", cpuinfo, re.M)
    if not vendors or any(v not in ("GenuineIntel", "AuthenticAMD") for v in vendors):
        raise RuntimeError("Native x86 vendor evidence required")
    if any(w in (cpuinfo + "\n" + maps).lower() for w in ("qemu", "rosetta", "tcgcpu")) or any(
        k.upper().startswith(("QEMU_", "ROSETTA")) for k in environ
    ):
        raise RuntimeError("Emulation evidence rejected")
    return vendors[0]


def capture(pin=True):
    header = Path("/proc/self/exe").read_bytes()[:64]
    cpu = Path("/proc/cpuinfo").read_text()
    maps = Path("/proc/self/maps").read_text()
    vendor = validate_x86(platform.machine(), platform.system(), header, cpu, maps, os.environ)
    allowed = sorted(os.sched_getaffinity(0))
    selected = []
    pairs = []
    for n in allowed:
        root = Path("/sys/devices/system/cpu") / ("cpu" + str(n)) / "topology"
        pair = (
            int((root / "physical_package_id").read_text()),
            int((root / "core_id").read_text()),
        )
        if pair not in pairs:
            pairs.append(pair)
            selected.append(n)
        if len(selected) == 4:
            break
    if len(selected) != 4:
        raise RuntimeError("Four distinct physical cores unavailable")
    if pin:
        os.sched_setaffinity(0, set(selected))
    if pin and os.sched_getaffinity(0) != set(selected):
        raise RuntimeError("Physical affinity did not bind")
    return dict(
        machine=platform.machine(),
        system=platform.system(),
        elf_machine=62,
        vendor=vendor,
        selected=selected,
        physical_pairs=pairs,
        emulation_detected=False,
    )
