# Four-arm feature/data ablation v1

This is a new, versioned **development** study. It performs zero model/provider
calls. The original agent-generation A/B comparison remains inconclusive with
zero complete pairs. Final recall and latency criteria are unchanged; there is
no canonical confirmation, automatic deployment or reuse of the failed
confirmation split.

| Arm | Available features | Fitting vectors |
|---|---|---:|
| S100 | Current 19 features plus the four qualified static local-filter observations | 100 original |
| S160 | Same static observations | 100 original + 60 additional |
| P100 | Static observations plus 11 bounded layer-zero progress observations | 100 original |
| P160 | Same progress observations | 100 original + 60 additional |

All arms use ordinal checkpoints 1/2/4/8/16/32/64/128 and the same frozen
first-stop tree fitter: depth three plus one guard, minimum eight independent
vector groups per leaf, four-tree beam, seven growth rounds, 13 training-only
quantile cuts and risks 20/80/320/1280. It maximizes the lower of mean activation
and reuse fixed-stop saving proxies minus risk times worst-filter mean recall
deficit, rejecting incomplete results. The only adaptations to the previously
audited fitter are module names and the new feature-group mapping.

## Available data and split

The existing **development-only** catalog contains 450 independent vectors.
Recorded previous exclusions consume 93, and the original learning/consumed
confirmation study consumes another 160. Only 197 unused development vectors
remain. Therefore this package uses **100 vs 160**, instead of the proposed
100 vs 300 pilot, while preserving separate calibration/evaluation and reserves:

- Original fitting: 100 vectors, 300 filter cases.
- Additional fitting: 60 vectors, 180 cases.
- Common development calibration: 40 vectors, 120 cases.
- Common development evaluation: 60 vectors, 180 cases.
- Still reserved: 37 development vectors; their query vectors are not uploaded.

The role assignment is hash ordered with seed 20261022 before outcomes are
collected. Each vector has unfiltered/votes32/votes108 variants, which always
stay in one role. Float32 vector hashes check independence and overlap, including
the original confirmation exclusions. The original 100 queries must exactly
match the sealed previous study, including their vectors and predicates.
The canonical calibration/final-test workload is never read or uploaded.

Fresh evaluation here means disjoint from this study's fitting/calibration and
the recorded earlier stopping studies. It is development evidence; it is not
canonical confirmation and does not erase historical adaptation to the dataset.
Later deployment requires fresh independent confirmation; the consumed split
cannot be reused.

## Progress observations and costs

The legacy static probe remains unchanged: its first 64 encountered graph nodes
may include upper routing, with at most 64 visible tuples inspected. The new
opt-in `progress_filter` group observes **already scored, loaded layer-zero
candidates only**, using their existing cosine distances. It makes at most
eight heap-fetch attempts before each of the eight eligible ordinal checkpoints:
**64 additional attempts per query**, including HOT retries/unsuccessful fetches.
It never samples the upper layers or changes native graph/queue/visit/stop logic.
All reads use the actual query snapshot, bound relation/index and validated
predicate. The static and progress profiles use the same new binary and index.
Native execution has both observations disabled. Cross-binary timing equality
is not asserted; native result/static-prefix equality is qualified.

New features are sampling-window ordinal; cumulative examined/passed/ratio;
recent-window examined/passed/ratio; `progress_has_valid`; and cumulative valid
minimum/mean distance and minimum improvement. Ratios and distance summaries
are **defined as zero for an empty sample**; counts and the Boolean expose this
case. These are explicit feature semantics, not unknown stop-label interpolation.
There is no exact GLS, exact nearest-neighbor truth or future node as input.
No full queue scan, sorting, per-query identity or group assignment is a policy
input. Qualification compares actual heap votes/distances, causal prefixes,
numeric/Boolean/availability getter branches and actual stopped outputs.
Serving execution does not serialize audit receipts. Every metadata read,
getter and policy evaluation stays inside the original policy timer.

## Selection and gates

Each of the 16 candidate policies is fitted on its arm's fitting groups only.
The common 40-vector calibration chooses one risk per arm, requiring complete
top-10, native recall >=.95 per filter, lower 95% recall-delta bounds >=-.0025
overall/every filter, and positive saving proxies in both regimes. Highest
worst-regime saving wins; ties prefer larger risk. No eligible candidate means
explicit continue. The `.0025` reserve is internal; final tolerance remains
`.005`. All 16 training masks are checked with the shared interpreter.

The candidate lock precedes any execution of the common evaluation queries.
If every arm abstains, the launcher stops: **no evaluation/timing allocations**.
Otherwise the common 60 evaluation vectors acquire actual fixed-stop outcomes
and execute all four locked policies, checking exact first stops and outputs.
The next timing gate requires a nonconstant calibrated policy with complete
results, unchanged final recall bounds and positive fixed-stop proxies. If
none passes, no timing allocation is submitted. No risk, tree or filter choice
changes after evaluation. The same evaluation sample is then used for timing;
that conditional selection makes this a development result.

The final measured gate remains valid complete top-10, native mean recall >=.95
for each filter, lower 95% vector-group bootstrap policy-minus-native recall
bound >=-.005 overall **and each filter**, and upper 95% mean log latency-ratio
bound <0 in **both activation and reuse**. Bootstrap is 10,000, seed 20261019.
All warmups are preserved and discarded by the fixed rule. No overhead is
subtracted. Offline cost proxies never establish the final latency gate.

Timing has eight arms: the four locked conditions, static/progress continue
controls, a sparse measured hindsight oracle and a fixed `P160-native108`
control. The latter uses the actual predicate to bypass the policy for votes108;
other queries execute the locked P160 policy. Its measured dispatch time is
added to the unchanged ANN timer and also appears in the outer timer. Native
bypass performs actual native searches; it has no invented policy activation,
engine checkpoints or work. Unavailable hybrid work summaries are reported as
unavailable. The routing control never rescues a rejected candidate or launches
timing on its own. Oracle uses hindsight and cannot be deployed.

## Allocations, counts and recovery

Initial submission creates four dependent allocations: build; two acquisition
shards of 100 vectors/300 cases; and offline calibration fitting. Each allocation
has four CPUs, 32 GiB, two hours, a 6600-second work deadline and at most 70,000
backend/reference searches. `advance` is a separate, idempotent gate operation:
after fitting it submits at most one common-evaluation allocation; after that
it submits at most three serial timing allocations. Failed gates terminate the
study with a collectable report. Maximum allocations: **eight**.

- Each initial acquisition: <=39,321 backend searches, including qualification.
- Both acquisitions: <=21,600 retained label/cost pairs and 10,800 warmups.
- Common evaluation: <=24,681 searches including 720 actual candidate proofs;
  <=6,480 retained fixed-stop pairs.
- Each timing block: 17,481 searches, 5,760 retained pairs, 1,440 warmups.
- All three timing blocks: 17,280 retained pairs.
- Maximum campaign searches: **155,766**; provider/model calls: **zero**.
- Metadata receipt SQL and verification SQL are counted separately: two of each
  per acquisition query; inherited control SQL is not represented as a backend search.

The package records a durable binding and per-dispatch journal before real
`sbatch`. Do not resubmit or clear bindings after an unknown/partial outcome.
Repeated `advance` cannot duplicate a known or unknown dispatch. Each allocation
uses an isolated restored database, SCRAM over a private Unix socket and the
original verified physical index backup. No rebuild/download or shared source
mutation is allowed. Sources, prior results and the original financial/scientific
ledger are preserved. Original uncertain charges remain charged.

## Commands and analysis

Use `COMMANDS.txt` for complete Mac/Torch steps. The command interface is:

```
control.py submit ORIGINAL_BUNDLE SOURCE_RESULTS_ROOT
control.py status
control.py advance
control.py collect
```

Status/advance/collect read the package binding, including after a fresh login.
Collection reproduces raw recall/cost labels, full calibration fitting/selection,
locked actual evaluation, timing coverage, arithmetic and final gates with
sealed local code. It produces the full raw/analysis archive and checksum.
On the Mac, use the original local sealed package for independent reanalysis;
never execute returned package code. Reports retain failures and abstentions.
Four-arm contrasts are development descriptions, with no independent causal,
multiplicity-adjusted, generalization or original-agent-A/B success claim.
