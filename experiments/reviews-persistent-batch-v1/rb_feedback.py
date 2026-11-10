"""Read-only proposal feedback on the pinned Reviews development cohort."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import fmean

from rb_evidence import (
    ACQUIRE,
    ACQUIRE_PROOFS,
    DATASET_SHA,
    PILOT_PROOFS,
    PILOT_REFS,
    Evidence,
    eligible_ids,
    load_frozen,
    outcome,
    stop_proofs,
)
from rb_plan import (
    CHECKPOINTS,
    FILTERS,
    PILOT_BLOCK,
    PROFILES,
    ROOT,
    SEED_ID,
    digest,
    load_plan,
    pinned,
    pinned_lines,
    require,
)
from rb_stats import exact_truth, quality, result_score

FOLDS = Path("trials/torch-reviews-grouped-stop-modeling-v1/runs/p3b-20261024-local-v1/folds.json")
FOLDS_SHA = "251f582fdbddbc042f0a40e2f3c4f29e75810cbf39d1adc1d7bcbb871421dce2"
PRIOR = Path("trials/reviews-persistent-batch-proposal-v1/episode/proposal.json")
PRIOR_SHA = "0ce789c4315da6e2fb90df92a0e2ae4b41ec6b6082c3eda60b1054a8a6383a1b"
PRIOR_ID = "e7f1ae0465bfe05aaf7d7768adf93ef6c99fe2be1eaa7be3fa73509bea75882b"
PAIR_PINS = (
    "00550a85dc36b65b4e7b267eec40af29d4b70bacbd89de941de907223a735687",
    "e5f437133486ccc97596c17ba992ede04e853862cffba0e5f427723dd2ee5a4e",
)
REGIMES = ("activation-cold", "reused-warm")
COUNTERS = ("layer0_distance_evaluations", "completed_expansions")
COST_COUNTERS = ("feature_collection_ns", "policy_evaluation_ns")
MAX_CANDIDATES = 8
MIN_WORK_SAVING = 0.10


class DevelopmentReplay:
    def __init__(self):
        self.plan = load_plan()
        self.frozen = load_frozen()
        self.eligible = eligible_ids()
        self.folds = json.loads(pinned(ROOT / FOLDS, FOLDS_SHA))["outer"]
        require(
            set(self.folds) == {case.group for case in self.plan.cases.values()}
            and Counter(self.folds.values()) == dict.fromkeys(range(5), 40),
            "Development folds changed",
        )
        self.references = {}
        self.traces = {}
        self.final_states = {}
        self.native_scores = {}
        self.proofs = stop_proofs(ROOT, "static23")
        self.stop_scores = {}
        for row in pinned_lines(ROOT / PILOT_BLOCK / "references.jsonl", PILOT_REFS):
            qid = row["query_id"]
            case = self.plan.cases[qid]
            require(
                qid not in self.references
                and row["group"] == case.group
                and self.frozen.policy.route(case.query) == case.stratum,
                "Development case identity changed",
            )
            traces = row["states"]
            require(set(traces) == set(PROFILES), "Development profiles changed")
            work = []
            for trace in traces.values():
                require(
                    trace and all(s["checkpoint_index"] == i for i, s in enumerate(trace, 1)),
                    "Invalid checkpoint sequence",
                )
                work.append([tuple(s["features"][name] for name in COUNTERS) for s in trace])
            require(
                all(series == work[0] for series in work[1:])
                and all(a[0] < b[0] and a[1] <= b[1] for a, b in zip(work[0], work[0][1:])),
                "Traversal work disagrees across profiles or checkpoints",
            )
            ref = {
                "native": outcome(row, "native"),
                "truth": {key: row[f"truth_{key}"] for key in ("strict", "ties", "k")},
            }
            self.references[qid] = ref
            self.traces[qid] = {}
            self.final_states[qid] = traces["light19"][-1]
            truth = exact_truth(self.frozen, ref, self.eligible[case.stratum])
            score, valid = result_score(self.frozen, truth, ref["native"])
            require(valid and score == row["native_recall"], "Native output changed")
            self.native_scores[qid] = score
            for profile, trace in traces.items():
                grid = {cp: trace[cp - 1] for cp in CHECKPOINTS if cp <= len(trace)}
                self.traces[qid][profile] = grid
                for cp in grid:
                    key = (profile, qid, cp)
                    if key in self.proofs:
                        prefix, output = self.proofs[key]
                        require(digest(trace[:cp]) == prefix, "Saved stop proof prefix changed")
                        self.stop_scores[key] = result_score(self.frozen, truth, output)
        require(self.references.keys() == self.plan.cases.keys(), "Development cohort changed")
        require(
            self.proofs.keys() == self.stop_scores.keys()
            and Counter(key[0] for key in self.proofs)
            == {"light19": 1074, "static23": 4695, "progress34": 4695},
            "Stop proof coverage changed",
        )
        self.costs = self.load_costs()
        self.seed, identity = self.frozen.policy.validate(self.plan.seed, self.plan.config)
        require(identity == SEED_ID, "Credited seed identity changed")

    def load_costs(self):
        costs = {}
        for part, sha in enumerate(PAIR_PINS):
            path = ROOT / ACQUIRE / f"part-{part}" / "pairs.jsonl"
            for row in pinned_lines(path, sha):
                qid, cp, regime = row["query_id"], row["checkpoint"], row["regime"]
                profile = {"base": "static23", "local": "progress34"}[row["family"]]
                case = self.plan.cases[qid]
                key = (profile, qid, cp, regime)
                ref = self.references[qid]["native"]
                output = ref if cp is None else self.proofs[profile, qid, cp][1]
                delta = row["policy_ms"] - row["native_ms"]
                counters = [row["work"][name] for name in COST_COUNTERS]
                require(
                    key not in costs
                    and regime in REGIMES
                    and row["phase"] == "acquisition"
                    and (row["group"], row["stratum"]) == (case.group, case.stratum)
                    and outcome(row, "native") == ref
                    and outcome(row, "policy") == output
                    and row["valid"] == (cp is None or self.stop_scores[profile, qid, cp][1])
                    and math.isfinite(delta)
                    and all(type(n) is int and n >= 0 for n in counters),
                    "Historical cost row differs from saved stop or continue evidence",
                )
                costs[key] = (delta, *counters)
        return costs

    def features(self, profile, qid, cp):
        names = self.frozen.policy.names(self.plan.config, profile)
        values = self.traces[qid][profile][cp]["features"]
        return {name: values.get(name) for name in names}

    def case_label(self, qid):
        case = self.plan.cases[qid]
        return {"vector_group": case.group, "filter": case.stratum, "fold": self.folds[case.group]}

    def first_stop(self, policy, qid):
        if self.plan.cases[qid].stratum not in policy["eligible"]:
            return None
        trace = self.traces[qid][policy["profile"]]
        return self.frozen.predict(policy["tree"], trace.values(), self.frozen.profile)

    def inspect(self, profile, filt, cp):
        rows = []
        for qid, case in self.plan.cases.items():
            if case.stratum != filt:
                continue
            reached = cp in self.traces[qid][profile]
            score = self.stop_scores.get((profile, qid, cp))
            seed_cp = self.first_stop(self.seed, qid)
            seed_state = self.final_states[qid]
            seed_recall = self.native_scores[qid]
            if seed_cp is not None:
                seed_state = self.traces[qid]["light19"][seed_cp]
                seed_recall = self.stop_scores["light19", qid, seed_cp][0]
            rows.append(
                {
                    "evaluator_only": {
                        **self.case_label(qid),
                        "native_recall": self.native_scores[qid],
                        "seed_recall": seed_recall,
                        "seed_stop_checkpoint": seed_cp,
                        "seed_observed_layer0_work": seed_state["features"][COUNTERS[0]],
                        "stop_recall": score[0] if score is not None else None,
                        "valid_top10": score[1] if score is not None else None,
                    },
                    "reached": reached,
                    "runtime_features": self.features(profile, qid, cp) if reached else None,
                }
            )
        return {"profile": profile, "filter": filt, "checkpoint": cp, "cases": rows}

    def evaluate(self, policy, *, seed_work=None):
        native = policy is None
        profile = "light19"
        identity = None
        if not native:
            policy, identity = self.frozen.policy.validate(policy, self.plan.config)
            profile = policy["profile"]

        outcomes, work, actions = {}, {}, {}
        failures = defaultdict(list)
        fold_reports = defaultdict(Counter)
        action_counts = defaultdict(Counter)
        stops_by_checkpoint = defaultdict(Counter)
        for qid, case in self.plan.cases.items():
            trace = self.traces[qid][profile]
            bypass = not native and case.stratum not in policy["eligible"]
            cp = None if native else self.first_stop(policy, qid)
            action = "native" if native else "bypass" if bypass else "continue"
            if cp is not None:
                action = "stop"
                stops_by_checkpoint[case.stratum][cp] += 1
            actions[qid] = (action, cp)
            fold = self.folds[case.group]
            fold_cell = fold_reports[fold, case.stratum]
            fold_cell["cases"] += 1
            action_counts[case.stratum][action] += 1
            if cp is not None:
                fold_cell["stops"] += 1

            state = trace[cp] if cp is not None else self.final_states[qid]
            work[qid] = {name: state["features"][name] for name in COUNTERS}
            for name, value in work[qid].items():
                fold_cell[name] += value
                if seed_work is not None:
                    fold_cell[f"{name}_saved_vs_seed"] += seed_work[qid][name] - value

            key = (profile, qid, cp)
            if cp is None:
                output = self.references[qid]["native"]
                score, valid = self.native_scores[qid], True
            elif key in self.proofs:
                output = self.proofs[key][1]
                score, valid = self.stop_scores[key]
            else:
                fold_cell["missing_stop_proofs"] += 1
                failures["missing_stop_proof"].append((qid, cp, None, None))
                continue

            outcomes[qid] = {"stop": cp is not None, "output": output}
            fold_cell["scored_cases"] += 1
            fold_cell["recall_delta_sum"] += score - self.native_scores[qid]
            if not valid:
                fold_cell["invalid_top10"] += 1
                failures["invalid_top10"].append((qid, cp, score, len(output[0])))
            elif score < self.native_scores[qid]:
                fold_cell["recall_losses"] += 1
                failures["recall_loss"].append((qid, cp, score, len(output[0])))

        saved_recall = None
        if len(outcomes) == len(self.references):
            evidence = Evidence(self.references, self.eligible, {}, {}, {"checked": outcomes})
            saved_recall = quality(self.plan, self.frozen, evidence, "checked")
            if native:
                # The reference is subject to the recall floor and validity, but has no stop.
                saved_recall["passes"] = all(
                    row["passes"] for row in saved_recall["recall"].values()
                )

        report = {
            "policy_identity": identity,
            "profile": None if native else profile,
            "recall": saved_recall,
            "actions_by_filter": dict(action_counts),
            "stops_by_checkpoint": {filt: dict(stops_by_checkpoint[filt]) for filt in FILTERS},
            "observed_work": totals(work),
            "observed_work_by_filter": {
                filt: totals({q: work[q] for q in work if self.plan.cases[q].stratum == filt})
                for filt in FILTERS
            },
            "folds": {
                fold: {filt: dict(fold_reports[fold, filt]) for filt in FILTERS}
                for fold in range(5)
            },
            "counterexamples": {
                reason: {
                    "count": len(rows),
                    "examples": [
                        {
                            **self.case_label(qid),
                            "checkpoint": cp,
                            "native_recall": self.native_scores[qid],
                            "stop_recall": score,
                            "returned_count": count,
                            "runtime_features": self.features(profile, qid, cp),
                        }
                        for qid, cp, score, count in examples_by_fold(rows, self.case_label)
                    ],
                }
                for reason, rows in failures.items()
            },
            "historical_cost_proxies": None if native else self.cost_report(profile, actions),
        }
        return report, work

    def cost_report(self, profile, actions):
        report = {}
        for regime in REGIMES:
            rows = defaultdict(list)
            wanted = Counter()
            for qid, (action, cp) in actions.items():
                if action == "bypass":
                    continue
                wanted[action] += 1
                values = self.costs.get((profile, qid, cp, regime))
                if values is not None:
                    rows[action].append(values)
            report[regime] = {
                action: {
                    "requests": wanted[action],
                    "matched_pairs": len(rows[action]),
                    "mean_added_backend_ms": fmean(r[0] for r in rows[action])
                    if rows[action]
                    else None,
                    "mean_feature_collection_ns": fmean(r[1] for r in rows[action])
                    if rows[action]
                    else None,
                    "mean_policy_evaluation_ns": fmean(r[2] for r in rows[action])
                    if rows[action]
                    else None,
                }
                for action in ("stop", "continue")
            }
        return report


def examples_by_fold(rows, label):
    """Keep one example per filter and fold for each failure kind."""
    examples = {}
    for row in rows:
        case = label(row[0])
        examples.setdefault((case["filter"], case["fold"]), row)
    return examples.values()


def totals(work):
    return {name: sum(row[name] for row in work.values()) for name in COUNTERS}


def comparison(report, work, native_work, seed_work):
    observed = totals(work)
    native = totals(native_work)
    seed = totals(seed_work)
    report["work_vs_native"] = {name: 1 - observed[name] / native[name] for name in COUNTERS}
    report["work_vs_seed"] = {name: 1 - observed[name] / seed[name] for name in COUNTERS}


def screen(report):
    if report["recall"] is None:
        return "reject_missing_stop_proofs"
    if not report["recall"]["passes"]:
        return "reject_recall"
    counter = COUNTERS[0]
    if report["work_vs_seed"][counter] < MIN_WORK_SAVING or any(
        sum(row[f"{counter}_saved_vs_seed"] for row in fold.values()) <= 0
        for fold in report["folds"].values()
    ):
        return "abstain_insufficient_work_headroom"
    warm = report["historical_cost_proxies"]["reused-warm"]
    if any(row["matched_pairs"] != row["requests"] for row in warm.values()):
        return "work_headroom_cost_unmeasured"
    if (
        sum(row["matched_pairs"] * (row["mean_added_backend_ms"] or 0) for row in warm.values())
        >= 0
    ):
        return "abstain_nonpositive_warm_cost_proxy"
    return "proxy_screen_pass"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--candidate", type=Path, action="append", help="One composite policy JSON")
    mode.add_argument("--inspect", nargs=3, metavar=("PROFILE", "FILTER", "CHECKPOINT"))
    args = parser.parse_args()
    if len(args.candidate or []) > MAX_CANDIDATES:
        parser.error(f"At most {MAX_CANDIDATES} proposals per invocation")
    if args.inspect:
        profile, filt, cp = args.inspect
        if profile not in PROFILES or filt not in FILTERS or cp not in map(str, CHECKPOINTS):
            parser.error("Expected an existing profile, filter and allowed checkpoint")

    replay = DevelopmentReplay()
    if args.inspect:
        print(json.dumps(replay.inspect(profile, filt, int(cp)), indent=2, allow_nan=False))
        return

    native, native_work = replay.evaluate(None)
    seed, seed_work = replay.evaluate(replay.seed)
    comparison(seed, seed_work, native_work, seed_work)
    prior, prior_work = replay.evaluate(
        json.loads(pinned(ROOT / PRIOR, PRIOR_SHA)), seed_work=seed_work
    )
    require(prior["policy_identity"] == PRIOR_ID, "Prior revision identity changed")
    comparison(prior, prior_work, native_work, seed_work)
    prior["decision"] = screen(prior)
    candidates = []
    for path in args.candidate or []:
        require(
            path.is_file() and not path.is_symlink() and path.stat().st_size <= 256 * 1024,
            "Invalid policy file",
        )
        policy = json.loads(path.read_bytes())
        require(type(policy) is dict, "Expected one composite policy object")
        report, work = replay.evaluate(policy, seed_work=seed_work)
        comparison(report, work, native_work, seed_work)
        report["decision"] = (
            "reject_duplicate_seed" if report["policy_identity"] == SEED_ID else screen(report)
        )
        candidates.append(report)

    print(
        json.dumps(
            {
                "scope": "saved exposed development only; five original outer folds",
                "pins": {
                    "folds": FOLDS_SHA,
                    "pilot_references": PILOT_REFS,
                    "pilot_proofs": PILOT_PROOFS,
                    "acquisition_proofs": ACQUIRE_PROOFS,
                    "acquisition_pairs": PAIR_PINS,
                    "dataset": DATASET_SHA,
                    "prior_policy": PRIOR_SHA,
                },
                "work_scope": "Traversal counters at first stop or last saved continue checkpoint. "
                "Unknown stops have observed prefix counters but no recall. "
                "Continue omits the tail; work excludes wrapper and collection cost.",
                "cost_scope": "Historical same-profile stop and continue pairs vs native. "
                "Bypass cost and the candidate's own end-to-end latency are unmeasured. "
                "Historical costs are unavailable for light19.",
                "screen": {
                    "minimum_layer0_work_saving_vs_seed": MIN_WORK_SAVING,
                    "positive_work_saving_required_in_each_fold": True,
                    "measured_persistent_request_latency": None,
                    "independent_confirmation": None,
                },
                "native": native,
                "seed": seed,
                "prior_revision": prior,
                "candidates": candidates,
            },
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
