# Evaluation: turn proposals into measured effects

I designed the evaluation around three separate questions: **can a policy be
executed correctly, does it reduce actual query latency, and what happens to
retrieval quality?** Each question has its own evidence and controls.

This page follows the frozen-proposal timing study behind the
[measured policy case study](../results.md). The core also implements a general
development/calibration/final-test workflow; this historical campaign used its
own declared training and held-out confirmation protocol.

[Architecture](../agent-design.md) · [Oracle](oracle.md) · [Data and queries](workload.md)

## Separate learning, selection, and assessment

| Stage | Evidence and decisions |
|---|---|
| Model-directed proposal generation | The model receives training-only observations, writes its own analysis, and exports policies. The host validates their structure and records assessments. |
| Candidate freeze | Preserve all 12 distinct exports from the two completed exploratory conversations, including their trees, source receipts, semantic hashes, and feature groups. |
| Training timing | Execute all 12 frozen candidates and controls on 300 query/filter cases in 100 vector groups; no model calls, refits, or policy changes occur in this stage. |
| Selection | Among policies meeting the declared training criteria, select by greatest activation-inclusive percentage saving, then fewer decision nodes, then semantic hash. |
| Held-out measurement | Execute the one unchanged selection on 180 cases from 60 disjoint vector groups. Results do not return to the learner for tuning or substitution. |

The selected artifact is `cons_S32_64_128_t002`, exported by the
[recorded agent conversation](agent-run.md). Its full policy hash is identical
in the training and held-out verification records.

## Compare against meaningful controls

Every candidate is paired with **ordinary native search** on the same query and
physical index. This is the primary latency comparator.

| Additional arm | What it helps explain |
|---|---|
| Candidate-specific matched continue | Uses the candidate's feature groups and decision structure, with stopping leaves replaced by continue; reveals the cost of that policy path. |
| Lightweight always-continue | Measures the common observation/interpreter path without an early-stop decision. |
| Fixed work budgets: 4,096 and 8,192 | Tests simple work cutoffs alongside the agent's conditional rules. |
| Sparse hindsight oracle | Measures a retrospective stopping reference using per-query outcome knowledge. |

Savings are computed against measured native execution. Estimated overhead is
never subtracted to manufacture a latency improvement. Matched-control contrasts
help explain effects; they do not replace the native comparison.

## Time activation and reuse separately

**Activation-inclusive latency** covers policy preparation/installation and the
first execution on warm data. The historical records call this
`activation-cold`; "cold" refers to policy activation, not a cold database cache.

**Reuse latency** covers an already activated policy, including the normal
validation, serialization, feature collection, inference, and decoding inside
the frozen reported timing boundary. Both paths also retain an outer application
clock. Trace retrieval remains outside the primary reported query clock.

Training uses two cohorts of six candidates. Each cohort runs 16 arms across
three measurement blocks. Each arm/query/block retains one activation pair and
three reuse pairs after a discarded warmup pair: **115,200 retained pairs across
all training arms**. The selected candidate contributes 900 activation and 2,700
reuse pairs.

Held-out measurement uses six arms, three blocks, one activation pair, and eight
reuse pairs per arm/query/block: **29,160 retained pairs across all held-out
arms**. The selected candidate contributes 540 activation and 4,320 reuse pairs.

Native/policy execution order is randomized within pairs. Arm order is shuffled
and rotated across blocks. Warmups, outliers, returned results, and timing records
are retained; outliers are not discarded from the reported comparisons.

## Score correctness and uncertainty

Each result is checked for validity and a complete top-10 result, then scored
against the exact filtered reference. Recall is reported alongside latency,
overall and separately for `unfiltered`, `votes32`, and `votes108`.

Uncertainty is clustered by **query vector group**: all filter variants and
timing repetitions of one vector stay together. The training and held-out sets
therefore have 100 and 60 independent groups, respectively. The bootstrap uses
10,000 samples with seed `20261019`.

| Predeclared criterion | Requirement |
|---|---|
| Result quality | Complete, valid top-10 results |
| Native reference quality | Mean native recall at least 95% in every filter |
| Recall noninferiority | Lower 95% bound of policy-minus-native recall at least −0.5 percentage points, overall and in every filter |
| Latency improvement | Upper 95% bound of the mean log(policy/native latency) below zero in both activation and reuse |

Headline percentages report arithmetic mean latency savings. The statistical
latency criterion uses mean log-ratios; the two summaries have distinct jobs.
The [results](../results.md) show the observed latency/recall tradeoff, and the
original records retain all qualification decisions.

## Preserve the experiment's identity

The protocol pins candidate hashes, query inventories, the existing physical
index, native module, query driver, timing boundary, source manifests, and
analysis settings. Collection checks native/continue equivalence, actual first
stops, causal prefixes, complete schedule coverage, and raw-file hashes. The
saved verification records describe independent local reproduction of the raw
reports and selection using sealed analysis code.

Inspect the [study contract projection](study-evidence.json),
[training verification](../verification/frozen-proposals-timing-v1-runtime-fix-postrun.json),
and [held-out verification](../verification/frozen-proposals-timing-v1-runtime-fix-confirmation-postrun.json).
These portfolio pages summarize existing records; preparing them did not run new
models, execute database queries, or repeat the scientific analysis.
