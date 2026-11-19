# Broader deployable oracle comparison

The existing work was checkpointed at commit `795db05` before this change.
The 7,000 cases and frozen 1,925-case test subset are each fitted with hindsight.
This is evaluator-only exposure, not an agent generalization experiment.

The v3 portable policy is a typed expression graph: Boolean combinations,
conditionals, finite float64 arithmetic and comparisons, missing-value tests,
and simultaneous updates of at most 32 query-local numeric registers. It may
declare any ascending checkpoint schedule in 1..4096. Thirteen declared causal
features cover checkpoint/work, eligible count, first/fifth/tenth distance,
frontier distance/gap, retained count and previous-frame/turnover information.
Frontier distance is the nearest pending candidate's cosine distance.
The native collector projects finite cosine distances into [0,2]. The canonical
logger preserves raw `1 + negative_inner_product` values, so independent checks
apply that same native projection, accepting only boundary roundoff within
1e-6 and requiring agreement within 1e-12 after projection. Raw values and
projection events are retained; scale or checkpoint mismatches still fail.
Checkpoint indices are the original canonical expanded-neighborhood boundaries targeting
successive blocks of 64 newly scored layer-zero distances; indices are not exact
work counts. V3 admits earlier and later boundaries than 16/32/64, so gains can
reflect both a broader action schedule and greater rule capacity.
Previous means the preceding declared checkpoint. No IDs, labels, outcome
tables, future state, external calls or index mutation are runtime inputs.
Decision trees and arithmetic models compile through this same format.

Operational bounds are 8 MiB source, 131,072 expression nodes, depth 64,
four MiB compiled tables per policy, and at most 16 million fuel units per
query (the fitted models request two million). Fuel charges one unit per
expression visit, retained node and visited TID, 16 per ranked eligible TID,
one frontier inspection, and 100 for a full turnover comparison. The trusted
native VM gathers only features required by the checkpoint-specialized graph.
Missing numeric inputs propagate unknown; only Boolean true stops. Arithmetic
fault or exhausted fuel disables the policy for that query and continues the
original native search. State starts at zero for every query. No arbitrary
agent code is executed in the database. Agents can write offline fitting
scripts and submit ordinary JSON files via `evaluate_broad_candidates`.

The graph, input vectors, seven conditions, cosine metric, k=10 and ef=640
remain fixed. A fresh native bridge and full canonical prefix chain qualify
the causal capture. Existing actually executed prefix labels are reused;
unknown prefixes are never assumed safe. Recall@10 must be at least the
per-case native recall on the policy's intended fitting cohort. Result-count
loss is reported separately. Test-fitted transfer outside test is diagnostic.
Capture is forced to continue and may use the normal maximum fuel budget;
it is not a deployment policy or a source of reported serving timings.
The timing allocation independently re-executes canonical capture to compare
every frontier/work observation and complete prefix chain before qualification
of the actual frozen policies. Fine threshold trees can memorize causal feature
values on a finite cohort. This is permitted by the broad interface and must
be reported explicitly; it does not establish future-query quality.

Before dispatch, the new comparison is bounded by six aggregate allocated
hours, two million durably reserved ANN requests, four physical CPUs and
48 GiB per allocation, zero provider calls and zero fresh exact queries.
There is no automatic retry or requeue. Source stage reservations and actual
allocated time carry forward. Inputs are sealed by SHA-256 and mounted read
only; private restored graph identity is verified before and after work.

Policies are frozen before timing. The fresh comparison includes native,
ideal, checkpoint-constrained, previous narrow feasible policies and the two
broader feasible policies. Native-output controls exercise each language's
empty program and the broad policies with stopping suppressed. The primary
timer includes native feature collection and VM execution. Hindsight lookup
routing remains outside that timer, consistent with the prior ideal oracle.
Cases keep all samples; uncertainty clusters by the 1,000 query vectors.
Savings use ratios of mean latency. Report all seven conditions and the six
filtered conditions, 20,000 fixed-seed bootstrap draws, 95% uncertainty for
savings, and a strict per-condition 90% control interval inside [0.98,1.02].
Failed control equivalence makes the estimates descriptive. Fitted policies
are best found policies, not a proof of minimum attainable wall-clock time.
