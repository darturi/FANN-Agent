# Research results and limits

FANNAgent implements a model-directed investigation and policy-evaluation system
for filtered vector search. The selected policy demonstrated latency savings in
training and confirmation, but failed the held-out recall requirement. No policy
qualified for acceptance in that confirmation.

These are summaries of existing records. No model generation, database timing,
fitting, or scientific reanalysis was performed for the portfolio release.

## Agent behavior

The [annotated provider-backed conversation](showcase/agent-run.md) records ten
requests, $0.530724 in model charges, an over-depth policy rejected by the host,
a valid revision, and six research exports. The model explicitly concluded that
none was accepted. Its candidates used existing training outcomes; predicted work
savings were not measured latency improvements.

The full v2 generation campaign recorded 56 provider attempts across six
conversations, two completed exploratory conversations, four budget-censored
conversations, and 12 distinct exported policies. There were zero complete A/B
pairs. That comparison cannot establish that exploratory selection is superior to
acceptance-oriented selection. See the
[generation postrun record](verification/aggressive-proposals-v2-postrun.json).

## Frozen-policy timing and confirmation

The workload used the Reviews campaign's physical index with 247,286 rows and
768-dimensional vectors, `ef_search=640`, top-10 queries, and three strata:
unfiltered, `votes32`, and `votes108`. The tested policy was
`cons_S32_64_128_t002`. Native default execution was the comparator.

The timing studies measured activation-inclusive and reused-policy query latency.
The final gate required valid complete results, a native recall floor, the lower
95% grouped recall-delta bound at least −0.5 percentage points overall and in every
filter, and statistically supported latency improvement in both regimes.
Bootstrap settings and exact criteria remain in the source records.

| Stage | Independent vector groups | Retained timing pairs | Activation latency saving | Reuse latency saving | Outcome |
|---|---:|---:|---:|---:|---|
| Training selection | 100 | 115,200 | 12.690% | 13.545% | Training-feasible selection; confirmation still required |
| Held-out confirmation | 60 | 29,160 | 11.673% | 12.377% | Recall failed overall and in `votes32`/`votes108`; no accepted candidate |

These percentages are recorded arithmetic mean latency savings. The statistical
latency gate uses a confidence bound on mean log-ratios; those are distinct
summaries. Repetitions and filter variants do not increase independent-group counts.

| Confirmation measure | Recorded value |
|---|---:|
| Native overall mean recall | 99.500% |
| Policy overall mean recall | 98.944% |
| Overall recall-delta 95% interval, percentage points | [−1.056, −0.167] |
| Required lower bound | ≥ −0.500 percentage points |
| Final selection | `no_qualified_candidate` |

The failed confirmation remains a failed confirmation. The policy is not promoted
on training performance, and diagnostic controls or hindsight oracles do not
supply a replacement after inspecting confirmation results.

Sources: [training postrun record](verification/frozen-proposals-timing-v1-runtime-fix-postrun.json)
and [confirmation postrun record](verification/frozen-proposals-timing-v1-runtime-fix-confirmation-postrun.json).
They identify saved inputs, source manifests, raw-file hashes, timing contracts,
and the earlier independent local reproduction. This page does not claim a new
independent reproduction.

## What can be concluded

The project demonstrates real tool use, custom model-written analysis, persistent
records, validation feedback, cost accounting, and explicit separation between
research proposals and acceptance. Its history also shows why work savings,
training recall, and a completed conversation are insufficient evidence for a
deployable optimization. The current findings support neither a general
latency/quality guarantee nor production readiness.

The physical database/index, full raw campaign archives, and original runtime
images are external research assets. They are not installed by the portfolio
demo. Verification summaries and the curated run trace are accessible in this
repository; the [historical experiment index](experiments/README.md) contains
additional workspace-relative provenance and links requiring external assets.
Full campaign reproduction needs those assets and its qualified runtime. The
[local simulation](showcase/local-demo.md) verifies a synthetic lifecycle and
establishes no database performance result.
