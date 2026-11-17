"""Prospective design, capability boundaries, partial/null interpretation and source pins."""

import ast
import collections
import json
import sys
import tarfile
import unittest
from pathlib import Path

from m5_design import (
    ARMS,
    COUNT,
    DECIDE,
    DISTANCE,
    GROUPS,
    TURNOVER,
    blocks,
    choose,
    cpu_for,
    decision,
    ledger,
    masks,
    ordered,
    reader_order,
    role,
)

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[2] / "trials/fannagent-benchmark-evaluation-v1/reviews-small"


class M5(unittest.TestCase):
    def test_attempt_ledger_and_fixed_pool(self):
        expected = ledger()
        self.assertEqual(expected["total"], 214396)
        self.assertEqual(expected["timing"]["timed_ann"], 151200)
        self.assertEqual(expected["timing"]["warmup_ann"], 3360)
        self.assertEqual(expected["timing"]["forced_prefix"], 9436)
        self.assertEqual(expected["work"]["work_ann"], 18900)
        self.assertLess(expected["total"], 225000)
        self.assertEqual(len(ARMS), 6)
        self.assertEqual(
            {n for group in GROUPS for n in group},
            set(ARMS),
        )

    def test_each_fixed_pid_runs_every_role_twice_on_every_condition(self):
        for group, names in enumerate(GROUPS):
            for t in range(7):
                seen = collections.Counter()
                for reader in range(4):
                    for cycle, rotation in blocks(group):
                        seen[reader, role(group, reader, rotation)] += 1
                self.assertEqual(set(seen.values()), {2})
                self.assertEqual(len(seen), 4 * len(names))
                self.assertEqual(
                    {cpu_for(r, t, group, [3, 7, 11, 19]) for r in range(4)}, {3, 7, 11, 19}
                )

    def test_all_query_role_cpu_cycle_cells_complete(self):
        for group, names in enumerate(GROUPS):
            counts = collections.Counter()
            for cycle, rotation in blocks(group):
                for reader in range(4):
                    counts[role(group, reader, rotation), reader, cycle] += 1
            self.assertEqual(set(counts.values()), {1})
            self.assertEqual(len(counts), len(names) * 4 * 2)

    def test_mirrored_query_and_four_reader_williams_orders(self):
        cases = [{"id": f"q-v{i}-votes32"} for i in range(450)]
        for group in range(len(GROUPS)):
            for rotation in range(len(GROUPS[group])):
                self.assertEqual(
                    ordered(cases, group, rotation, 0),
                    list(reversed(ordered(cases, group, rotation, 1))),
                )
                for j in range(450):
                    self.assertEqual(
                        reader_order(j, 0, rotation, 2, group),
                        list(reversed(reader_order(j, 1, rotation, 2, group))),
                    )
        rows = [reader_order(j, 0, 0, 0, 0) for j in range(4)]
        edges = collections.Counter((a, b) for row in rows for a, b in zip(row, row[1:]))
        self.assertEqual(len(edges), 12)
        self.assertEqual(set(edges.values()), {1})

    def test_null_and_zero_stops_and_previous_scheduled_dependency(self):
        p = {"rules": {"votes743": [{"cp": 16, "conditions": [["qualifying_count", "<=", 9]]}]}}
        self.assertTrue(decision(p, "votes743", 16, {"qualifying_count": 0}))
        entry = {"policy": p, "force_continue": False}
        self.assertEqual(choose(entry, "votes743", [{"checkpoint": 16, "qualifying_count": 0}]), 16)
        entry["force_continue"] = True
        self.assertEqual(choose(entry, "votes743", [{"checkpoint": 16, "qualifying_count": 0}]), 0)
        p = {
            "rules": {
                "votes32": [{"cp": 64, "conditions": [["top10_new_since_previous", "<=", 0]]}]
            }
        }
        self.assertEqual(
            masks(p, "votes32"),
            {"16": 0, "32": COUNT | DISTANCE, "64": COUNT | DISTANCE | TURNOVER | DECIDE},
        )
        self.assertFalse(decision(p, "votes32", 64, {"top10_new_since_previous": None}))
        self.assertEqual(masks(p, "votes743"), {"16": 0, "32": 0, "64": 0})

    def test_no_paid_or_reserved_import_before_frozen_loader(self):
        forbidden = {
            "fannagent",
            "fannagent_pgvector",
            "design",
            "policy",
            "execution",
            "database",
            "runtime_base",
            "anthropic",
            "openai",
            "requests",
            "httpx",
        }
        for name in ("m5_run.py", "m5_design.py", "m5_experiment.py", "m5_preflight.py"):
            tree = ast.parse((HERE / name).read_text())
            for node in tree.body:
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn(node.module.split(".")[0], forbidden)
                elif isinstance(node, ast.Import):
                    self.assertFalse({a.name.split(".")[0] for a in node.names} & forbidden)

    def test_native_preflight_mandatory_and_no_requeue_or_retry(self):
        s = (HERE / "submit.sh").read_text()
        self.assertIn("--no-requeue", s)
        self.assertLess(
            s.index("bash ./startup-preflight.sh"), s.index("/opt/slurm/bin/sbatch --test-only")
        )
        s = (HERE / "startup-preflight.sh").read_text()
        self.assertIn("m5_preflight.py", s)
        self.assertNotIn("--loader-only", s)
        s = (HERE / "run-on-compute.sh").read_text()
        self.assertIn("--quality /prior-results/timing", s)
        self.assertIn("trap finish EXIT", s)

    def test_short_serving_output_is_one_approximate_request(self):
        sys.path.insert(0, str(STUDY / "runtime-m5-v1"))
        from serving import request

        class Reader:
            def __init__(self):
                self.calls = []

            def execute(self, sql, params, prepare):
                self.calls.append((sql, params, prepare))
                return self

            def fetchall(self):
                return [(i, 0.1) for i in range(7)]

        reader = Reader()
        reserve = []
        result = request(reader, {"k": 10, "vector": [0.1] * 768}, reserve.append)
        self.assertEqual(reserve, ["ann"])
        self.assertEqual(len(reader.calls), 1)
        self.assertEqual(result["returned_count"], 7)
        self.assertNotIn("+ 0", reader.calls[0][0])
        tree = ast.parse((HERE / "m5_experiment.py").read_text())
        exact_functions = set()
        for fn in tree.body:
            if isinstance(fn, ast.FunctionDef):
                for node in ast.walk(fn):
                    if (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name)
                        and node.func.id == "search"
                    ):
                        if any(
                            k.arg == "exact" and isinstance(k.value, ast.Constant) and k.value.value
                            for k in node.keywords
                        ):
                            exact_functions.add(fn.name)
        self.assertEqual(exact_functions, {"offline"})

    def test_compiled_pool_and_separate_observer_delta(self):
        folder = STUDY / "runtime-m5-v1"
        compiled = json.loads((folder / "compiled-programs.json").read_text())
        self.assertEqual(
            {r["arm"] for r in compiled["bindings"]},
            {a for a in ARMS.values() if a is not None and a >= 20},
        )
        for r in compiled["bindings"]:
            for f, plan in r["observation_plan"].items():
                self.assertEqual(masks(r["policy"], f), plan)
        self.assertEqual(
            (folder / "engine/src/policy_runtime_v2.inc").read_bytes(),
            (HERE.parent / "filtered-ann-protocol-v2/runtime/policy_runtime_v2.inc").read_bytes(),
        )
        delta = json.loads((folder / "observer-delta.json").read_text())
        self.assertEqual(delta["changed_source"], ["src/fannbench.c"])
        self.assertFalse(delta["instrumented_times_enter_primary"])
        with tarfile.open(STUDY / "kits/m1-runtime-qualification-v2/engine-sources.tar.gz") as tf:
            for engine in ("engine", "observer-engine"):
                changed = [
                    str(p.relative_to(folder / engine))
                    for p in sorted((folder / engine).rglob("*"))
                    if p.is_file()
                    and p.suffix in (".c", ".h", ".inc")
                    and p.read_bytes()
                    != tf.extractfile(engine + "/" + str(p.relative_to(folder / engine))).read()
                ]
                self.assertEqual(changed, ["src/compiled_v2.inc"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
