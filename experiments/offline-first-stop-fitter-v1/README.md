# Offline first-stop fitter comparison v1

Compare the existing CART fitter with a small tree search that scores complete
queries at their first predicted stop. This is conventional offline fitting,
with **zero further model/provider calls, database calls or remote jobs**.
The original agent-generation A/B remains inconclusive with zero complete pairs.
The final recall and timing criteria remain unchanged. No new runtime features,
native optimizations or feature-cost subtraction are part of this comparison.

## Frozen design

The only inputs are the previously verified four-condition learning campaign
`reviews-four-condition-training-v1-20261022T032823Z.qx3frkhp`, its 4,698 actual
fixed-stop executions and its sealed local package. `input-pins.json` fixes 63
raw files, the full source archive, package manifest and original core sources.
The failed confirmation is not a fitting input. Imported code is the sealed
local package and original local core, never the downloaded campaign package.
Networking, subprocess creation and model-client imports are blocked in the
comparison process. Read-only source checks run before and after computation.

Both fitters use the same four A/B/C/D feature/checkpoint conditions, the same
five outer vector-group folds and four inner folds, the same risk grid
20/80/320/1280, depth three plus an availability/checkpoint guard and minimum
eight distinct training vector groups per split branch. Feature and checkpoint
replications do not add independent groups. The shared policy interpreter
checks exported policies. Only actually executed stop outcomes are usable;
unknown outcomes and missing qualified observations fail rather than interpolate.

The original CART is independently rerun and must exactly reproduce its
entire original fit lock. Its weighted per-state impurity objective is unchanged.

The new beam search starts with both constant actions. Each expansion replaces
one leaf by a numeric feature split with stop/continue children in either
orientation. It keeps four distinct training decision masks, carries incumbents
and grows for at most seven rounds, with maximum three split levels. Identical
training masks prefer fewer nodes then a deterministic lexical tree order.
Candidate cuts are 13 quantiles from .05 through .95, computed once using only
eligible measured states in that fit's training groups. Integer cuts round up.
Local tied cuts use their fixed enumeration order. The CART baseline instead
recomputes its quantiles per node; that search difference is part of the method
comparison. This finite search makes no claim to find the best possible policy.

Each candidate is evaluated at its **first** eligible stop for every training
query. Invalid/incomplete outcomes are infeasible. Its training score is:

```
min(mean activation proxy ms saved, mean reuse proxy ms saved)
  - risk_weight * max(mean nonnegative recall deficit overall and per filter)
```

The objective uses actual recall damage and measured fixed-stop timing proxies,
not binary checkpoint classification or distance work. It is a training loss,
not a recall guarantee. It permits useful splits even if weighted impurity would
reject them. Only inner validation selects the risk weight. Selection retains
the original lower-bound development reserve of -.0025 overall and each filter,
native recall >=.95 per filter, complete valid top-10 and positive mean savings
proxies in both regimes. Highest worst-regime proxy wins, ties prefer higher
risk. No eligible candidate explicitly continues. Outer held-out labels do not
control candidate search, risk selection or fit thresholds. No full-data refit
or globally deployable policy selection is performed.

## Reporting and interpretation

Replay reports native-relative recall and fixed-stop timing proxies on the
same 100 learning vectors / 300 query-filter cases for each procedure. Bootstrap
uses 10,000 vector-group resamples, seed 20261019. The unchanged final recall
criterion requires complete valid top-10, native mean recall >=.95 per filter,
and lower 95% recall-delta bounds >=-.005 overall AND every filter.

**New policy latency is unmeasured.** Fixed-stop proxy savings cannot establish
the final upper-95%-mean-log-latency-ratio criterion in activation or reuse,
because preparation, observation and interpretation costs of the newly fitted
policy have not been executed. There is no final combined acceptance, automatic
Torch submission or confirmation. All selection diagnostics and OOF outputs are
retained even if the procedures fail.

This is adaptive development on already examined learning data. Fixed group
folds prevent direct fold leakage, but do not remove prior design adaptation.
Intervals condition on fitted decisions; training uncertainty is not separately
bootstrapped. No new independent vectors are created. Future optimized policies
require fresh independent confirmation; the consumed split cannot be reused.

Before the first original-data fit, the runner saves `design-lock.json` with the
full design, source hashes, input pins and runtime versions. A failed run stays
preserved. Final output hashes and source/input preservation are verified.

## Reproduce locally

From `/Users/danielarturi/Developer/JinyangLiWork`:

```bash
trials/morevec-reviews-durable-workflow/runtime-install-v2/releases/3af24dc1ab9c8dffdfc7-pgvector/bin/python \
  agent/experiments/offline-first-stop-fitter-v1/test_comparison.py

trials/morevec-reviews-durable-workflow/runtime-install-v2/releases/3af24dc1ab9c8dffdfc7-pgvector/bin/python \
  agent/experiments/offline-first-stop-fitter-v1/compare.py \
  --output trials/torch-reviews-results/offline-first-stop-fitter-v1-NEW
```

Always use a new output path. See `comparison.json`, `report.txt`, all 20 fold
receipts, exact OOF row outcomes, fit lock and `verification.json`.
