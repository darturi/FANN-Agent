"""Hindsight search over the agent's actual bounded conjunction language.

The MILP maximizes captured layer-0 traversal work saved, not predicted or
observed wall time. Actual compiled policies are measured after freezing.
"""

import argparse
import hashlib
import itertools
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from scipy import __version__ as scipy_version
from scipy.optimize._highspy import _core as highs_core
from scipy.sparse import coo_array

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE.parent / "filtered-ann-protocol-v2"))
from fannproto.compiler import compile_programs  # noqa: E402
from fannproto.policy import FEATURES, FILTERS, POINTS, choose, decide, rule_hash, validate  # noqa: E402


def filter_name(value):
    return "unfiltered" if value < 0 else "votes" + str(value)


def view(row):
    return {"filter": filter_name(row["filter"]), "observations": row["observations"]}


def gain(row, cp):
    return int(row["native_layer0_work"] - row["actions"][str(cp)]["layer0_work"])


def replay(policy, rows):
    saved = 0
    counts = {str(cp): 0 for cp in (*POINTS, 0)}
    for row in rows:
        cp = choose(policy, view(row)) or 0
        if cp:
            action = row["actions"][str(cp)]
            if action["recall"] + 1e-12 < row["native_recall"]:
                raise ValueError("hindsight policy loses recall: " + row["id"])
            saved += gain(row, cp)
        counts[str(cp)] += 1
    return saved, counts


class Model:
    def __init__(self):
        self.cost, self.lower, self.upper, self.integer = [], [], [], []
        self.ri, self.ci, self.values, self.lo, self.hi = [], [], [], [], []

    def var(self, lower=0, upper=1, cost=0):
        index = len(self.cost)
        self.cost.append(cost)
        self.lower.append(lower)
        self.upper.append(upper)
        self.integer.append(1)
        return index

    def row(self, coefficients, lower=-np.inf, upper=np.inf):
        index = len(self.lo)
        for column, value in coefficients.items():
            if value:
                self.ri.append(index)
                self.ci.append(column)
                self.values.append(value)
        self.lo.append(lower)
        self.hi.append(upper)

    def solve(self, seconds, seed):
        matrix = coo_array(
            (
                np.asarray(self.values, dtype=float),
                (np.asarray(self.ri, dtype=np.int32), np.asarray(self.ci, dtype=np.int32)),
            ),
            shape=(len(self.lo), len(self.cost)),
        ).tocsc()
        activity = matrix @ seed
        if (
            np.any(activity < np.asarray(self.lo) - 1e-6)
            or np.any(activity > np.asarray(self.hi) + 1e-6)
            or np.any(seed < np.asarray(self.lower))
            or np.any(seed > np.asarray(self.upper))
        ):
            raise ValueError("independently replayed incumbent does not satisfy MILP")
        # SciPy's public milp wrapper has no incumbent argument. Use the same
        # bundled HiGHS backend through its pinned native API to pass the witness.
        if scipy_version != "1.16.3":
            raise RuntimeError("native incumbent bridge is pinned to SciPy1.16.3")
        engine = highs_core._Highs()
        for key, value in (
            ("output_flag", False),
            ("threads", 1),
            ("time_limit", float(seconds)),
            ("mip_rel_gap", 0.0),
        ):
            if engine.setOptionValue(key, value) != highs_core.HighsStatus.kOk:
                raise RuntimeError("HiGHS option rejected: " + key)
        model = highs_core.HighsModel()
        lp = model.lp_
        lp.num_col_, lp.num_row_ = len(self.cost), len(self.lo)
        lp.col_cost_, lp.col_lower_, lp.col_upper_ = self.cost, self.lower, self.upper
        lp.row_lower_, lp.row_upper_ = self.lo, self.hi
        lp.integrality_ = [highs_core.HighsVarType.kInteger] * len(self.cost)
        lp.a_matrix_.format_ = highs_core.MatrixFormat.kColwise
        lp.a_matrix_.num_col_, lp.a_matrix_.num_row_ = len(self.cost), len(self.lo)
        lp.a_matrix_.start_ = matrix.indptr
        lp.a_matrix_.index_ = matrix.indices
        lp.a_matrix_.value_ = matrix.data
        if engine.passModel(model) != highs_core.HighsStatus.kOk:
            raise RuntimeError("HiGHS rejected the bounded rule model")
        incumbent = highs_core.HighsSolution()
        incumbent.col_value = seed
        incumbent.value_valid = True
        if engine.setSolution(incumbent) != highs_core.HighsStatus.kOk:
            raise RuntimeError("HiGHS rejected the checked feasible incumbent")
        engine.run()
        status = engine.getModelStatus()
        info, solution = engine.getInfo(), engine.getSolution()
        code = (
            0
            if status == highs_core.HighsModelStatus.kOptimal
            else 1
            if status == highs_core.HighsModelStatus.kTimeLimit
            else 4
        )
        x = np.asarray(solution.col_value) if solution.value_valid else None
        dual = info.mip_dual_bound if info.valid else None
        # A minimization dual cannot exceed an independently valid incumbent.
        if dual is not None and dual > float(np.dot(self.cost, seed)) + 1e-5:
            dual = None
        gap = info.mip_gap if info.valid and math.isfinite(info.mip_gap) else None
        return SimpleNamespace(
            x=x, status=code, message=str(status), mip_dual_bound=dual, mip_gap=gap
        )


def seed_policy(rows, name):
    """Find a safe incumbent using hindsight; this heuristic supplies no bound."""
    remaining = (1 << len(rows)) - 1
    clauses = []
    for cp in POINTS:
        reached = sum(1 << i for i, row in enumerate(rows) if str(cp) in row["actions"])
        reached &= remaining
        bad = sum(
            1 << i
            for i, row in enumerate(rows)
            if str(cp) in row["actions"]
            and row["actions"][str(cp)]["recall"] + 1e-12 < row["native_recall"]
        )
        bad &= reached
        weights = [gain(row, cp) if str(cp) in row["actions"] else 0 for row in rows]

        def value(mask):
            total = 0
            while mask:
                bit = mask & -mask
                total += weights[bit.bit_length() - 1]
                mask ^= bit
            return total

        if not reached:
            continue
        if not bad:
            if value(reached) > 0:
                clauses.append({"cp": cp, "conditions": []})
                remaining &= ~reached
            continue
        literals = {}
        for feature in FEATURES:
            observations = [row["observations"].get(str(cp), {}).get(feature) for row in rows]
            values = sorted(
                {x for i, x in enumerate(observations) if x is not None and reached & (1 << i)}
            )
            if not values:
                continue
            unsafe = {x for i, x in enumerate(observations) if x is not None and bad & (1 << i)}
            for operator in ("<=", ">="):
                cuts = {values[-1] if operator == "<=" else values[0]}
                for x in unsafe:
                    rank = values.index(x)
                    if operator == "<=" and rank:
                        cuts.add(values[rank - 1])
                    if operator == ">=" and rank + 1 < len(values):
                        cuts.add(values[rank + 1])
                for cut in cuts:
                    mask = sum(
                        1 << i
                        for i, x in enumerate(observations)
                        if x is not None and (x <= cut if operator == "<=" else x >= cut)
                    )
                    mask &= reached
                    if mask and mask not in literals:
                        threshold = (
                            int(cut) if feature in (FEATURES[0], FEATURES[3]) else float(cut)
                        )
                        literals[mask] = [feature, operator, threshold]
        frontier, visited = {reached: []}, {reached}
        best_mask, best_conditions, best_value = 0, [], 0
        scored = {}
        for _ in range(4):
            candidates = {}
            for mask, conditions in frontier.items():
                kinds = {(x[0], x[1]) for x in conditions}
                for literal_mask, literal in literals.items():
                    if (literal[0], literal[1]) in kinds:
                        continue
                    subset = mask & literal_mask
                    if not subset or subset in visited or subset in candidates:
                        continue
                    proposed = [*conditions, literal]
                    candidates[subset] = proposed
                    if not subset & bad:
                        score = scored.setdefault(subset, value(subset))
                        if score > best_value:
                            best_mask, best_conditions, best_value = subset, proposed, score
            if not candidates:
                break
            visited.update(candidates)
            ratio = sorted(
                candidates,
                key=lambda m: (m & ~bad).bit_count() / (1 + (m & bad).bit_count()),
                reverse=True,
            )
            coverage = sorted(candidates, key=lambda m: (m & ~bad).bit_count(), reverse=True)
            selected = list(dict.fromkeys([*ratio[:32], *coverage[:16]]))
            frontier = {m: candidates[m] for m in selected}
        if best_mask:
            clauses.append({"cp": cp, "conditions": best_conditions})
            remaining &= ~best_mask
    policy = {
        "schema": "fannagent.filtered-ann.v2",
        "name": "oracle_seed_" + name,
        "rules": {name: clauses},
        "rationale": "Safe hindsight incumbent, not an optimality claim.",
    }
    validate(policy)
    replay(policy, rows)
    return policy


def fit_filter(rows, name, *, seconds=180):
    """One conjunction per legal checkpoint, up to four comparisons each.

    Repeated bounds on a feature/operator can be canonicalized to their strongest
    bound. Consequently eight possible bound kinds cover every legal clause.
    Thresholds at distinct observed values cover every nonempty cohort decision
    equivalence class; an empty clause action can always be disabled.
    """
    seed = seed_policy(rows, name)
    seed_saved, _ = replay(seed, rows)
    model = Model()
    enabled, bounds, matches = {}, {}, {}
    first = {}
    scale = 28  # greater than all 24 bound + 3 enabled-clause tie-break costs
    for cp in POINTS:
        enabled[cp] = model.var(cost=1)
        specs = []
        for feature in FEATURES:
            values = sorted(
                {
                    row["observations"].get(str(cp), {}).get(feature)
                    for row in rows
                    if row["observations"].get(str(cp), {}).get(feature) is not None
                }
            )
            if not values:
                continue
            ranks = {value: index + 1 for index, value in enumerate(values)}
            for operator in ("<=", ">="):
                active = model.var(cost=1)
                # Shared monotone cut bits encode exactly the inclusive thresholds
                # over observed values, without weak big-M rank constraints.
                bits = [model.var() for _ in values]
                missing = model.var()
                model.row({missing: 1, active: 1}, lower=1, upper=1)
                for bit in bits:
                    model.row({bit: 1, active: 1}, lower=1)
                anchor = bits[0] if operator == "<=" else bits[-1]
                model.row({anchor: 1}, lower=1, upper=1)
                for left, right in zip(bits, bits[1:]):
                    sign = 1 if operator == "<=" else -1
                    model.row({left: sign, right: -sign}, lower=0)
                bounds[cp, feature, operator] = (active, bits, values, missing)
                specs.append((feature, operator, active, bits, ranks, missing))
        model.row({**{s[2]: 1 for s in specs}, enabled[cp]: -4}, upper=0)
        for index, case in enumerate(rows):
            reached = str(cp) in case["actions"]
            z = model.var(upper=int(reached))
            matches[index, cp] = z
            if not reached:
                continue
            comparisons = []
            for feature, operator, active, bits, ranks, missing in specs:
                value = case["observations"][str(cp)].get(feature)
                comparisons.append(missing if value is None else bits[ranks[value] - 1])
            model.row({z: 1, enabled[cp]: -1}, upper=0)
            for h in comparisons:
                model.row({z: 1, h: -1}, upper=0)
            model.row(
                {z: 1, enabled[cp]: -1, **{h: -1 for h in comparisons}}, lower=-len(comparisons)
            )
    for index, case in enumerate(rows):
        for ci, cp in enumerate(POINTS):
            proof = case["actions"].get(str(cp))
            safe = proof is not None and proof["recall"] + 1e-12 >= case["native_recall"]
            stop = model.var(upper=int(safe), cost=-scale * gain(case, cp) if proof else 0)
            first[index, cp] = stop
            z = matches[index, cp]
            previous = [matches[index, before] for before in POINTS[:ci]]
            model.row({stop: 1, z: -1}, upper=0)
            for before in previous:
                model.row({stop: 1, before: 1}, upper=1)
            model.row({stop: 1, z: -1, **{before: 1 for before in previous}}, lower=0)
    model.row(
        {
            first[index, cp]: gain(case, cp)
            for index, case in enumerate(rows)
            for cp in POINTS
            if str(cp) in case["actions"]
        },
        lower=seed_saved,
    )
    witness = np.zeros(len(model.cost))
    seed_clauses = {clause["cp"]: clause for clause in seed["rules"][name]}
    for cp in POINTS:
        clause = seed_clauses.get(cp)
        witness[enabled[cp]] = int(clause is not None)
        tests = {(f, op): value for f, op, value in clause["conditions"]} if clause else {}
        for feature, operator in itertools.product(FEATURES, ("<=", ">=")):
            spec = bounds.get((cp, feature, operator))
            if spec is None:
                continue
            active, bits, values, missing = spec
            cut = tests.get((feature, operator))
            witness[active], witness[missing] = int(cut is not None), int(cut is None)
            for bit, value in zip(bits, values, strict=True):
                witness[bit] = int(
                    cut is None or (value <= cut if operator == "<=" else value >= cut)
                )
    for index, case in enumerate(rows):
        selected = choose(seed, view(case)) or 0
        for cp in POINTS:
            observation = case["observations"].get(str(cp))
            witness[matches[index, cp]] = int(
                observation is not None and decide(seed, name, cp, observation)
            )
            witness[first[index, cp]] = int(selected == cp)
    result = model.solve(seconds, witness)
    if result.status not in (0, 1):
        raise RuntimeError("hindsight optimizer failed: " + result.message)
    clauses = []
    if result.x is not None:
        for cp in POINTS:
            if result.x[enabled[cp]] < 0.5:
                continue
            conditions = []
            for feature, operator in itertools.product(FEATURES, ("<=", ">=")):
                spec = bounds.get((cp, feature, operator))
                if spec is None or result.x[spec[0]] < 0.5:
                    continue
                selected = [index for index, bit in enumerate(spec[1]) if result.x[bit] > 0.5]
                index = max(selected) if operator == "<=" else min(selected)
                value = spec[2][index]
                value = int(value) if feature in (FEATURES[0], FEATURES[3]) else float(value)
                conditions.append([feature, operator, value])
            clauses.append({"cp": cp, "conditions": conditions})
    policy = {
        "schema": "fannagent.filtered-ann.v2",
        "name": "oracle_feasible_" + name,
        "rules": {name: clauses},
        "rationale": "Cohort-wide hindsight traversal-work fit.",
    }
    validate(policy)
    saved, stops = replay(policy, rows)
    if result.x is not None:
        predicted = sum(
            gain(case, cp) * round(result.x[first[index, cp]])
            for index, case in enumerate(rows)
            for cp in POINTS
            if str(cp) in case["actions"]
        )
        if predicted != saved:
            raise ValueError("MILP/unchanged DSL replay mismatch")
    if saved < seed_saved:
        policy["rules"] = seed["rules"]
        saved, stops = replay(policy, rows)
    relaxed = sum(
        max(
            [
                0,
                *(
                    gain(case, cp)
                    for cp in POINTS
                    if str(cp) in case["actions"]
                    and case["actions"][str(cp)]["recall"] + 1e-12 >= case["native_recall"]
                ),
            ]
        )
        for case in rows
    )
    dual = getattr(result, "mip_dual_bound", None)
    upper = relaxed
    if dual is not None and math.isfinite(dual):
        upper = min(upper, max(saved, math.floor((27 - dual + 1e-5) / scale)))
    certificate = {
        "filter": name,
        "cases": len(rows),
        "objective": "layer0_distance_evaluations_saved",
        "solver": "pinned scipy._highspy/HiGHS; independently checked incumbent",
        "scipy_version": scipy_version,
        "solver_status": int(result.status),
        "solver_message": result.message,
        "time_limit_seconds": seconds,
        "variables": len(model.cost),
        "constraints": len(model.lo),
        "work_saved": saved,
        "safe_incumbent_work_saved": seed_saved,
        "solver_threads": 1,
        "work_saved_upper_bound": upper,
        "work_gap": upper - saved,
        "work_optimality_proven": upper == saved,
        "solver_mip_gap": getattr(result, "mip_gap", None),
        "relaxed_legal_action_work_bound": relaxed,
        "stop_counts": stops,
        "latency_optimality_proven": False,
    }
    return policy, certificate


def fit(rows, cohort, output, *, seconds=180):
    selected = [r for r in rows if cohort == "full_workload" or r["role"] == "test"]
    policy = {
        "schema": "fannagent.filtered-ann.v2",
        "name": "oracle_feasible_" + cohort,
        "rules": {},
        "rationale": "Evaluator-only hindsight fit in the agent's unchanged DSL.",
    }
    certificates = []
    for name in FILTERS:
        subset = [r for r in selected if filter_name(r["filter"]) == name]
        if not subset:
            raise ValueError("missing filter: " + name)
        print(
            json.dumps(
                {"phase": "fit_filter", "cohort": cohort, "filter": name, "cases": len(subset)}
            ),
            flush=True,
        )
        one, certificate = fit_filter(subset, name, seconds=seconds)
        policy["rules"].update(one["rules"])
        certificates.append(certificate)
        (output / (cohort + "-fit-progress.json")).write_text(
            json.dumps(certificates, indent=2) + "\n"
        )
    validate(policy)
    saved, stops = replay(policy, selected)
    _, compiled = compile_programs([{"arm": 20, "policy": policy, "force_continue": False}])
    (output / ("oracle_feasible-" + cohort + ".json")).write_text(
        json.dumps(policy, sort_keys=True, indent=2) + "\n"
    )
    audit = {
        "cohort": cohort,
        "cases": len(selected),
        "policy_rule_hash": rule_hash(policy),
        "unchanged_validator_passed": True,
        "unchanged_compiler_passed": True,
        "compiled_source_hash": compiled["source_hash"],
        "work_saved": saved,
        "stop_counts": stops,
        "per_filter": certificates,
        "latency_optimality_proven": False,
        "hindsight_fit": True,
    }
    (output / (cohort + "-fit-certificate.json")).write_text(json.dumps(audit, indent=2) + "\n")
    return policy, audit


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds-per-filter", type=float, default=180)
    parser.add_argument("--cohort", choices=("full_workload", "heldout_test"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    data = [json.loads(line) for line in args.cases.open()]
    for cohort in (args.cohort,) if args.cohort else ("full_workload", "heldout_test"):

        def file_hash(path):
            with path.open("rb") as handle:
                return hashlib.file_digest(handle, "sha256").hexdigest()

        protocol = HERE.parent / "filtered-ann-protocol-v2/fannproto"
        manifest = {
            "cohort": cohort,
            "cases_sha256": file_hash(args.cases),
            "fitter_source_sha256": file_hash(Path(__file__).resolve()),
            "validator_source_sha256": file_hash(protocol / "policy.py"),
            "compiler_source_sha256": file_hash(protocol / "compiler.py"),
            "seconds_per_filter": args.seconds_per_filter,
            "scipy_version": scipy_version,
            "python_version": sys.version,
            "hindsight_fit": True,
            "objective": "layer0 work saved, then rule complexity",
            "latency_optimality_claim": False,
        }
        (args.output / (cohort + "-fit-inputs.json")).write_text(
            json.dumps(manifest, indent=2) + "\n"
        )
        fit(data, cohort, args.output, seconds=args.seconds_per_filter)
