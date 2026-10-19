"""Training diagnostics separate native benefit from the benefit of stopping."""

from collections import defaultdict

import numpy as np

from ..evaluation import bootstrap
from .returned import REGIMES
from .returned_models import ReturnedFeedback
from .statistics import feasible, with_filters


def benchmark_report(evidence: ReturnedFeedback):
    corpus, benchmark = evidence.corpus, evidence.benchmark
    queries = {q.query_id: q for q in corpus.queries}
    reports: dict[str, dict] = {}
    contrasts: dict[str, dict] = {}
    for arm in benchmark.arms:
        reports[arm.arm] = {}
        for regime in REGIMES:
            rows = [p for p in benchmark.pairs if p.arm == arm.arm and p.regime == regime]
            report = with_filters(rows, corpus.queries, corpus.objective)
            reports[arm.arm][regime] = {
                "report": report,
                "training_feasible": feasible(report, corpus.objective),
                "deployable_arm": arm.kind != "oracle",
                "per_block": {
                    str(b): with_filters(
                        [p for p in rows if p.block == b], corpus.queries, corpus.objective
                    )
                    for b in benchmark.schedule.blocks
                },
            }
            if arm.kind != "matched-continue":
                continue
            candidate = arm.matched_candidate
            assert candidate is not None
            control = {(p.query_id, p.block, p.repetition): p for p in rows}
            group_differences = defaultdict(list)
            for pair in benchmark.pairs:
                if pair.arm == candidate and pair.regime == regime:
                    matched = control[(pair.query_id, pair.block, pair.repetition)]
                    group_differences[queries[pair.query_id].group].append(
                        pair.policy_ms - matched.policy_ms
                    )
            values = [float(np.mean(rs)) for rs in group_differences.values()]
            contrasts.setdefault(candidate, {})[regime] = {
                "matched_continue_arm": arm.arm,
                "mean_candidate_minus_control_ms": float(np.mean(values)),
                "gap_ci95_ms": bootstrap(
                    values, corpus.objective.seed, corpus.objective.bootstrap_samples
                ),
                "independent_groups": len(group_differences),
                "interpretation": (
                    "Separate measurements matched by query, allocation and repetition; "
                    "does not replace candidate-versus-native qualification"
                ),
            }
    return {
        "schema_version": 1,
        "format": "fannagent.learning.benchmark-report.v1",
        "scope": "learning",
        "evidence_hash": evidence.evidence_hash,
        "arms": reports,
        "matched_continue_contrasts": contrasts,
        "oracle_arms": [a.arm for a in benchmark.arms if a.kind == "oracle"],
        "canonical_acceptance_established": False,
    }
