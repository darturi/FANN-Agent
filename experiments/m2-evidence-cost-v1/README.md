# M2 evidence/cost qualification and bound M3

[REPORT.md](REPORT.md) records complete evidence binding, two negative cost-model qualification
results and a successful actual-bound-evidence M3 abstention rehearsal. No new provider, SQL
or protected-data access is involved. Cost ranking stays disabled.

The full immutable artifacts live at
`trials/fannagent-benchmark-evaluation-v1/reviews-small/evidence-m2-v1/` in the shared workspace.
Compact input/result/freeze receipts are retained in `receipts/`. Existing M0/M1 inputs and
freezes are preserved. The signed additive near miss is retained, not repaired by relaxing the
predeclared limits.

Preparation order on a fresh versioned destination:

1. Seal [PLAN.md](PLAN.md) and source inputs before fitting.
2. Run `qualify.py`: fit only the two fixed hypotheses, with entire target programs excluded.
3. Run `bind.py`: bind all 9,436 labels and evaluator-only measured-prefix work with the explicit
   negative cost gate. Verify all 21 v2 bindings' work summaries against M1.
4. Run `rehearse_bound.py`: real evidence, actual gate receipts, scope/quota/resume/replay checks
   and required abstention. Preserve its durable Store trajectories.
5. Run the protocol tests and the separate `run_rehearsal.py` positive synthetic fixture.

Each script preserves completed outputs rather than overwriting them. Reproduction requires a
fresh destination and the pinned M1 inputs; there are no protected-outcome or live-provider tools.
