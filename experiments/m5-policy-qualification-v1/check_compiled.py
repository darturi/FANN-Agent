"""Exercise exact generated C decisions at boundaries and on unavailable features."""

import ctypes
import itertools
import json
import subprocess
import tempfile
from pathlib import Path

from m5_design import FILTERS, POINTS, choose, decision, masks
from package_kit import RUNTIME, sha, write


def run():
    manifest = json.loads((RUNTIME / "compiled-programs.json").read_text())
    assert manifest["source_hash"] == sha(RUNTIME / "engine/src/compiled_v2.inc")
    programs = manifest["bindings"]
    code = (
        "#include <stdbool.h>\n"
        + (RUNTIME / "engine/src/compiled_v2.inc").read_text()
        + """
int mask(int a,int f,int cp) { return V2Mask(a,f,cp); }
int force(int a) { return V2ForceContinue(a); }
int decide(int a,int f,int cp,int count,double td,double gap,int full,int hasgap) {
  return V2Decision(a,f,cp,count,td,gap,0,full,hasgap,false);
}
"""
    )
    cases = 0
    stops = 0
    with tempfile.TemporaryDirectory(prefix="m5-c-parity-") as temp:
        source = Path(temp) / "probe.c"
        library = Path(temp) / "probe.so"
        source.write_text(code)
        subprocess.run(
            ["cc", "-shared", "-fPIC", "-O2", str(source), "-o", str(library)], check=True
        )
        lib = ctypes.CDLL(str(library))
        lib.decide.argtypes = [ctypes.c_int] * 4 + [ctypes.c_double] * 2 + [ctypes.c_int] * 2
        for entry, t, cp in itertools.product(programs, FILTERS, POINTS):
            name = "unfiltered" if t < 0 else "votes" + str(t)
            assert lib.mask(entry["arm"], t, cp) == masks(entry["policy"], name)[str(cp)]
            assert bool(lib.force(entry["arm"])) == entry["force_continue"]
            for count, td, gap in itertools.product(
                (0, 9, 10),
                (None, 0.329, 0.33, 0.331, 0.34, 0.341),
                (None, 0.099, 0.1, 0.11, 0.12, 0.13),
            ):
                # Only consistent observations: partial populations have no ranked features.
                if count < 10 and (td is not None or gap is not None):
                    continue
                obs = {
                    "checkpoint": cp,
                    "qualifying_count": count,
                    "tenth_distance": td,
                    "frontier_gap": gap,
                    "top10_new_since_previous": None,
                }
                actual = bool(
                    lib.decide(
                        entry["arm"],
                        t,
                        cp,
                        count,
                        td or 0,
                        gap or 0,
                        td is not None,
                        gap is not None,
                    )
                )
                expected = decision(entry["policy"], name, cp, obs)
                assert actual == expected, (entry["arm"], t, obs)
                assert choose(entry, name, [obs]) == (
                    cp if actual and not entry["force_continue"] else 0
                )
                cases += 1
                stops += actual
    assert cases > 3000 and stops > 0
    result = {
        "status": "passed",
        "C_python_decision_cases": cases,
        "true_decisions": stops,
        "generated_source_sha256": sha(RUNTIME / "engine/src/compiled_v2.inc"),
        "boundary_null_partial_and_force_continue_checked": True,
        "study_queries_run": 0,
        "provider_calls": 0,
        "validation_test_outcomes_opened": False,
    }
    write(RUNTIME / "checks/compiled-parity.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    run()
