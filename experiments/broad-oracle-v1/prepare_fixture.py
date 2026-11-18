"""Prepare actual PostgreSQL probes for v3 semantics and v2 compatibility."""

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDY = ROOT / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
WORK = STUDY / "broad-oracle-v1"
sys.path[:0] = [str(ROOT / "agent/src"), str(HERE)]
from build_runtime import build  # noqa: E402


def main():
    bindings = json.loads((WORK / "capture-bindings.json").read_text())
    roots = [
        (
            [
                "and",
                ["ge", ["feature", "checkpoint"], 3],
                [
                    "or",
                    [
                        "lt",
                        [
                            "div",
                            ["feature", "frontier_gap"],
                            ["add", ["abs", ["feature", "tenth_distance"]], 0.01],
                        ],
                        0.3,
                    ],
                    ["le", ["feature", "qualifying_count"], 9],
                ],
            ],
            {},
            0,
            2000000,
        ),
        (
            ["and", ["ge", ["state", 0], 1], ["available", ["feature", "previous_tenth_distance"]]],
            {"0": ["add", ["state", 0], 1]},
            1,
            2000000,
        ),
        (["gt", ["feature", "tenth_distance"], 0], {}, 0, 5),
        (["gt", ["div", 1, 0], 0], {}, 0, 2000000),
        (["gt", ["mul", 1e300, 1e300], 0], {}, 0, 2000000),
        (["or", True, ["gt", ["div", 1, 0], 0]], {}, 0, 2000000),
        (
            [
                "if",
                ["available", ["feature", "top10_new_since_previous"]],
                ["le", ["feature", "top10_new_since_previous"], 2],
                False,
            ],
            {},
            0,
            2000000,
        ),
    ]
    for arm, (root, updates, slots, fuel) in enumerate(roots, 60):
        policy = {
            "schema": "fannagent.broad-stop.v3",
            "name": "fixture-" + str(arm),
            "rationale": "Native VM semantic probe, not benchmark evidence.",
            "fuel": fuel,
            "state_slots": slots,
            "programs": {
                f: {"checkpoints": [1, 2, 3, 9, 97], "root": root, "updates": updates}
                for f in bindings[0]["policy"]["programs"]
            },
        }
        bindings.append({"arm": arm, "policy": policy, "force_continue": False})
    runtime = build(bindings, WORK / "fixture-runtime-v2")
    target = WORK / "fixture-v2"
    shutil.copytree(
        STUDY / "oracle-variants-v1/fixture-persistent-v2",
        target,
        ignore=shutil.ignore_patterns("checks", "oracle-module.so"),
    )
    (target / "checks").mkdir(mode=0o777)
    (target / "checks").chmod(0o777)
    common = (target / "common.py").read_text().replace("id <= 16000", "id <= 32000")
    (target / "common.py").write_text(common)
    for name in ("functions.sql", "compiled-v3.json", "broad_contract.py"):
        shutil.copyfile(runtime / name, target / name)
    for name in ("smoke_v3.py", "broad_support.py"):
        shutil.copyfile(HERE / name, target / name)
    (target / "bindings.json").write_text(json.dumps(bindings, indent=2) + "\n")
    print(target)


if __name__ == "__main__":
    main()
