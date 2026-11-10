# P3c — risk-separated stopping-model comparison v1

**NEXT-RISK-01** is one local offline formulation comparison, authorized by the
user after P3b's negative result. The frozen [contract](contract.json) has SHA-256
`92928bbca0ca8c1b0a4ac6962d3fe95aa083b96c14e9b49b4ea050c657ae99ae`.
No production changes, new native/database/provider/Torch calls, protected query
access, independent confirmation or full-data policy refit are part of P3c.

Within each qualified static23/progress34 profile, keep P3b's exact five outer
and four inner vector-group folds, eight measured checkpoints, features, model
parameters, seed, weights and distinct-vector pruning. Every model fits ONLY
the recall-loss target: positive native-minus-stop recall for valid complete
top-10, otherwise loss 1.0. At each retained/pruned leaf, separately average
the minimum activation/reuse savings proxy on its fitting rows. These two
outputs share one partition: no extra trees or model-depth increase. All leaf
values, splitting, pruning and calibration are training-only.

Stop at the first reached grid checkpoint satisfying BOTH predicted loss at
most a fixed risk cap AND predicted benefit at least a fixed floor. Risk caps
are 0/.00025/.0005/.001/.0025/.005/.01 recall fraction; benefit floors are
0/.1/.25/.5/1/2/4 ms. Forty-nine inner candidates per cell use full measured
first-stop outcomes, not state-level classification accuracy. Admission keeps
the unchanged complete-top10/native-floor/−.0025 recall lower-bound checks,
positive overall mean proxies in BOTH regimes and a nonzero stop count.
Choose maximum worst-regime proxy, ties smaller risk cap then larger benefit
floor. None qualifies: paid measured same-profile continue. No outer rescue.

Exactly one outer refit per cell supplies both selected gates and the
predeclared diagnostic cap .0025 / benefit 0. Shallow leaf gates compile directly
to stop/continue in the same depth-three tree plus grid/availability guard;
validate against the frozen API and shared interpreter. The 64-tree depth-eight
ensemble remains an offline diagnostic, not a serving implementation.

Report paired P3c-minus-frozen-P3b within each profile/method and
flexible-minus-shallow, including calibrated/fixed-diagnostic results, controls,
all 980 inner assessments and all 4,800 outer cases. No P3b refits or corrections.
Baselines and both inner/outer group assignments must reconstruct exactly.

This is adaptive development on the same 200 exposed vectors / 600 cases.
Inner risk screening and pointwise vector-bootstrap intervals are NOT a
distribution-free risk certificate or independent confirmation. A risk estimate
is a fitted mean, not a confidence upper bound. First-stop actual loss need not
be monotone in these thresholds. Fixed-stop cost proxies do not measure a new
policy's composite-session latency; no P2 optimization credit is subtracted.

The finite ceiling is 100 estimator fits (80 inner + 20 outer), 24 synthetic fits,
one CPU thread, 4 GiB RSS, 60 minutes and 16 GiB metered run reads. A qualifying
development signal permits a separately scoped interface/representation and
actual-latency review. Failure closes this formulation allowance; explicitly
choose justified fresh development diversity or B1 under a new contract.
No extra seed, model, threshold, subgroup routing or automatic Torch followup.

## Reproduction and preservation

The existing isolated P3b environment is reused read-only, with exact versions
in [requirements.txt](requirements.txt); production environments are unchanged.
`input-pins.json` binds 919 permitted original and prior-P3b artifacts. The run
creates a fresh output and refuses overwrites. Local checks must bind the exact
source before fitting. Commands below document execution; do not rerun a
completed or partial campaign to change its verdict.

```bash
cd /Users/danielarturi/Developer/JinyangLiWork
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  VECLIB_MAXIMUM_THREADS=1 \
  trials/torch-reviews-grouped-stop-modeling-v1/local-env/bin/python \
  agent/experiments/risk-separated-stop-modeling-v1/test_comparison.py

# Only after the checked-source receipt exists; NEW_OUTPUT_PATH must be new.
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  VECLIB_MAXIMUM_THREADS=1 \
  trials/torch-reviews-grouped-stop-modeling-v1/local-env/bin/python \
  agent/experiments/risk-separated-stop-modeling-v1/compare.py \
  --output NEW_OUTPUT_PATH
```

The postrun verifier reconstructs saved leaf statistics, OOF scores, gate
selection, first-stop outcomes and reports without calling `.fit`. Failed
preparation/runs and correctness repairs are preserved, never silently replaced.
No user or Torch command is required for this local phase.

## Primary sources

- [scikit-learn 1.7 DecisionTreeRegressor](https://scikit-learn.org/1.7/modules/generated/sklearn.tree.DecisionTreeRegressor.html): squared-error regression, estimator parameters and float32 input semantics.
- [scikit-learn 1.7 ExtraTreesRegressor](https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.ExtraTreesRegressor.html): fixed ensemble parameters and prediction mechanics.
- [Nested cross-validation](https://scikit-learn.org/1.7/auto_examples/model_selection/plot_nested_cross_validation_iris.html): separate inner selection from outer evaluation; this implementation additionally groups vectors.
- [Conformal Risk Control](https://arxiv.org/abs/2208.02814v4): a formal framework with assumptions; P3c does not implement that algorithm or claim its guarantee.
- [P3b results](../../../research/fannagent-p3b-grouped-modeling-v1-results-2026-10-24.md): local empirical motivation and prior exposure boundary.

Risk-only partitions, training-leaf benefits and the gates are project-specific
design choices. The cited methods do not predict this workload's outcome.
