# P3b — grouped stopping-model comparison v1

**NEXT-MODEL-01** compares a depth-three regression tree with a 64-tree Extra
Trees ensemble on the existing qualified static23/progress34 evidence. The user
authorized P3b after the completed P3a coverage audit. This is local offline
adaptive development: no native/database/provider calls, Torch submission,
protected evaluation access, deployment or full-data policy refit.

The [frozen contract](contract.json) is the scientific design. Its SHA-256 is
`d50ccf6a7b41e7b7af79541c6b0f55cd87ef20acb4842636fb0da63125f1b5c7`.
The 200 previously exposed vectors / 600 cases stay together in the exact five
outer group folds. Each outer training pool has four deterministic inner group
folds. Every model, split, group-support pruning decision and learned parameter
uses its fitting groups only. Runtime feature columns are matched within each
profile. Query IDs, evaluator strata, future observations, truth and labels are
never predictor inputs.

Both methods regress the same fixed-stop utility-minus-recall-risk target, with
an explicit invalid-result penalty and equal total weight per vector. Every
split whose child has fewer than eight distinct fitting vectors is pruned to
the fitted parent value. Depth three plus the checkpoint/availability guard is
the shallow policy's representation limit. The flexible ensemble is an offline
diagnostic predictor, not a serving runtime extension.

The only allowed stop ordinals are 1/2/4/8/16/32/64/128. Every decision is evaluated
at its first predicted stop using an actual measured outcome, or the measured
same-profile continue outcome. Unreachable checkpoints are masked, never
imputed. Invalid measured outcomes remain negative outcomes. Fixed-stop costs
are proxies; new tree/composite-session latency is unmeasured.

Four risks and seven fixed score thresholds are selected through pooled inner
OOF first-stop outcomes. Selection requires valid complete top-10, native recall
floor .95 per filter, lower 95% recall-delta bounds >= -.0025 overall and each
filter, positive mean activation/reuse proxies and a nonzero stop count. Ties
prefer larger risk, then larger threshold. No qualified inner candidate means
explicit measured profile continue. Outer outcomes never rescue rejected
candidates. The original -.005 recall replay criterion is separately reported;
actual final latency and independent acceptance remain unassessed.

A fixed risk320/threshold0 diagnostic is evaluated regardless of selection.
It cannot rescue a rejection. Analytical native, measured profile-continue and
fixed-checkpoint128 controls are predeclared. Report all candidates/folds,
canonical JSON models, first-stop records, paired vector-bootstrap contrasts,
errors and failure records. Bootstrap intervals are pointwise and condition on
the fixed OOF fits; prior adaptation/training uncertainty remains.

`models.py` reconstructs scikit-learn's float32 split partitions as runtime
predicates, including midpoint rounding. Unpruned predictions must match
scikit-learn before applying the common group-support pruning. The shallow
export then passes the frozen policy validator and shared interpreter's
first-stop checks. This is observed-data interface evidence, not native fault
qualification or proof of deployment performance.

The isolated environment lives under
`trials/torch-reviews-grouped-stop-modeling-v1/local-env`; requirements and
installation receipts are preserved outside production environments. The
scientific run limits are 360 estimator fits, one CPU thread, 4 GiB RSS, 60
minutes, 16 GiB metered reads, zero external calls and one frozen nested
campaign. Local synthetic tests are separate (at most 24 fits). No retuning,
extra seeds/folds/model families, global refit or automatic Torch acquisition
follows results.

## Local commands

From `/Users/danielarturi/Developer/JinyangLiWork`:

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  trials/torch-reviews-grouped-stop-modeling-v1/local-env/bin/python \
  agent/experiments/grouped-stop-modeling-v1/test_comparison.py

# Run only after local-checks.json binds the checked source; preserve outputs.
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  trials/torch-reviews-grouped-stop-modeling-v1/local-env/bin/python \
  agent/experiments/grouped-stop-modeling-v1/compare.py --output NEW_OUTPUT_PATH
```

Do not rerun a completed/incomplete campaign to improve its verdict. Review the
saved receipt and failure record. Earlier raw evidence and protected query
values remain read-only. No Torch command is part of this phase.

## Primary methodology sources

- [scikit-learn 1.7 ExtraTreesRegressor](https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.ExtraTreesRegressor.html): model definition and bounded parameters.
- [scikit-learn 1.7 DecisionTreeRegressor](https://scikit-learn.org/1.7/modules/generated/sklearn.tree.DecisionTreeRegressor.html): shallow model and prediction semantics.
- [Nested versus non-nested cross-validation](https://scikit-learn.org/1.7/auto_examples/model_selection/plot_nested_cross_validation_iris.html): separate inner selection from outer evaluation.
- [scikit-learn 1.7 common pitfalls](https://scikit-learn.org/1.7/common_pitfalls.html): keep learned preprocessing/selection inside training groups.
- [P3a coverage audit](../../../research/fannagent-p3a-evidence-audit-2026-10-24.md): local measured-outcome, profile, exposure and identity boundary.

These justify methods and evidence handling; published examples do not predict
this workload's result. The group pruning and fixed utility target are explicit
project-specific design choices, not claims about scikit-learn defaults.
