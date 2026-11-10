"""Passive original fixture delegate; private root lifetime/size observations."""

import sys
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def observe(module, result):
    original = module.runtime_fixture
    tracked = []
    live = set()
    result.update(
        calls=0, peak_live_roots=0, maximum_case_bytes=0, maximum_case_entries=0, restored=False
    )

    def runtime_fixture(*args, **kwargs):
        value = original(*args, **kwargs)
        root = Path(value["package"]).parent
        live.intersection_update({path for path in live if path.exists()})
        live.add(root)
        files = [p for p in root.rglob("*") if p.is_file()]
        directories = sum(p.is_dir() for p in root.rglob("*")) + 1
        result["calls"] += 1
        result["peak_live_roots"] = max(result["peak_live_roots"], len(live))
        result["maximum_case_bytes"] = max(
            result["maximum_case_bytes"], sum(p.stat().st_size for p in files)
        )
        result["maximum_case_entries"] = max(
            result["maximum_case_entries"], len(files) + directories
        )
        return value

    for item in list(sys.modules.values()):
        if item is not None and vars(item).get("runtime_fixture") is original:
            tracked.append(item)
            item.runtime_fixture = runtime_fixture
    try:
        yield result
    finally:
        lost = any(item.runtime_fixture is not runtime_fixture for item in tracked)
        for item in list(sys.modules.values()):
            if item is not None and vars(item).get("runtime_fixture") is runtime_fixture:
                item.runtime_fixture = original
        for item in tracked:
            item.runtime_fixture = original
        result["restored"] = all(item.runtime_fixture is original for item in tracked)
        if lost:
            raise RuntimeError("Fixture observer binding lost")
