# Four-condition training study v1

This is a new conventional-learning study with zero model/provider calls. The
original generation A/B comparison remains inconclusive (zero complete pairs).
The failed cons_S32_64_128_t002 confirmation is preserved and excluded from all
training and validation. No automatic confirmation or promotion is implemented.
Any subsequent selected deployable policy needs fresh independent confirmation.

| Condition | Available observations | Eligible checkpoint ordinals |
|---|---|---|
| A | Original qualified 19 features | 32, 64, 128 |
| B | Original qualified 19 features | 1, 2, 4, 8, 16, 32, 64, 128 |
| C | Original features plus local filter observations | 32, 64, 128 |
| D | Original features plus local filter observations | 1, 2, 4, 8, 16, 32, 64, 128 |

Local observations are opt-in native getters: the actual predicate threshold,
number of visible tuples inspected, number satisfying the actual predicate and
their ratio. They inspect at most the first 64 distinct graph nodes whose
distance has already been computed, including mandatory upper-layer routing;
at most 64 visible tuples are read. This is a bounded encountered-neighborhood
sample, not an exact GLS value or a continuously updated queue statistic. It
never reads exact nearest-neighbor truth, future nodes, oracle choices or query
identity. Heap visibility uses the query snapshot. All metadata reads and getter
work are inside the policy timer. Missing observations continue search.

The new native module is built separately; original source, binaries, index,
receipts, ledgers, campaigns and failed confirmation are never overwritten. The
same original x86 physical index (247286 rows, 768 dimensions), ef_search=640,
native search settings and timer boundaries are retained. Qualification checks
original native results, every original 19-feature traversal, both collection
modes, actual getters and actual stopped prefixes. The four conditions use the
same new binary, with local instrumentation disabled for A/B and ordinary native.
The native comparator is ordinary search in this new binary. Original/new
result and traversal equality are qualified; cross-binary timing equality is
not assumed. The new observation hook's disabled path still has a branch cost.

## Fitting and interpretation

The only query inventory is the original 100 learning vector groups / 300 filter
cases. The upload contains no confirmation/calibration/final-test query. No
independent vectors are manufactured by repetitions. This first implementation
uses newly measured local features and fixed-stop outcomes on those same groups;
it makes no new-workload generalization claim.

Acquisition measures each available eligible stop in both collection modes,
including activation, one discarded warmup and one reuse pair. Stop outcomes
are executed and prefix-verified, never interpolated. Both continue costs are
measured too. A sparse hindsight oracle chooses among measured base stops that
preserve that case's native recall, otherwise continuing.

Five outer folds hold out 20 complete vector groups each. For each condition,
four inner folds select from risk penalties 20, 80, 320 and 1280 using only the
outer training groups. The fitter is the existing deterministic CART split
algorithm: depth three, minimum eight independent groups per leaf, plus one
availability/checkpoint guard. The feature pool, fitter, risk grid and depth are
identical except for the two declared factors. Fitting weights use actual
recall damage and work reduction. Inner selection uses fixed-stop measured
activation/reuse cost proxies, explicitly not final fitted-policy timings.

An internal recall reserve of 0.0025 on the inner-validation lower bound helps
avoid training-boundary selection. It does not replace the final tolerance of
0.005. If no candidate meets that reserve and positive savings proxies in both
regimes, that fold explicitly continues. No weak candidate is forced into a run.
Twenty fold-specific policies are frozen before timing, including abstentions.

The evaluated unit is an out-of-fold fitting procedure for each condition.
Evaluator-only fold assignment selects the policy that excluded that vector;
no query/group identifier is a deployed policy input. Passing this study does
not qualify one globally fitted deployable policy. There is no full-data refit,
fallback candidate, paid generation or confirmation step in this launcher.

## Unchanged final gates

All results must be valid and complete top-10. Native mean recall must be at
least .95 in each filter. The lower 95% vector-group bootstrap bound of
policy-minus-native recall must be at least -.005 overall AND each filter.
The upper 95% bound of mean log(policy/native latency) must be below zero for
BOTH activation and reuse. Bootstrap: 10000, seed 20261019. No outliers are
discarded, no overhead is subtracted and no timer is substituted after results.

## Schedule and counts

Five serial allocations: build, acquire/qualify/fit, then three measurement
blocks. Each requests four CPUs, 32 GiB and two hours; runtime deadline 6600 s.
The acquisition cap is 38910 backend/reference/qualification calls. Missing
late checkpoints reduce the actual count; every count is journaled. It retains
at most 10800 label/cost pairs and discards at most 5400 warmup pairs. Metadata
verification SQL and policy eviction installations are counted separately.

Each measurement block has 13 arms: A/B/C/D, four matched-continue controls,
base/local continue, fixed-4096/fixed-8192 and sparse oracle. Every arm is paired
with ordinary native. One activation pair, one discarded warmup and three
reuse pairs give 15600 retained pairs/block, 46800 total, and 3900 discarded
warmups/block. The backend-call maximum is 44610/block. Arm order is shuffled
and rotated over blocks; paired native/treatment order is randomized.

The report includes each condition's raw results, per-filter bounds, per-block
variation and the factorial contrasts C-A, D-B, B-A, D-C and interaction
D-C-B+A. These are descriptive training comparisons; no multiplicity-adjusted
causal or generalization discovery is claimed. The original agent-generation
A/B remains inconclusive regardless of these results.

## Commands

Use the saved Mac/Torch commands alongside the upload archive. Submission is
bound to one campaign; do not repeat it after an unknown/partial outcome.
`control.py status` and `control.py collect` recover the saved binding when no
campaign argument is provided. Collection verifies raw data with locally sealed
code, preserves all failures, produces a full archive and checksum, and performs
no automatic fitting or further model call. Independent Mac reanalysis runs the
local `report.py --campaign PATH --package SEALED_LOCAL_PACKAGE`.
