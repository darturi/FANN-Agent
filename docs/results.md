# Measured performance of an agent-generated policy

**The agent exported a stopping policy that reduced actual database query
latency.** On the 300-case training workload, `cons_S32_64_128_t002` reduced mean
latency by **12.69% including activation** and **13.54% on reuse**, while mean
Recall@10 changed from **99.00% to 98.90%**. The same frozen policy also reduced
latency on the separate 180-case held-out workload.

The case study connects model-directed analysis to a concrete systems artifact
and its measured latency/recall tradeoff.

[Agent run](showcase/agent-run.md) · [Architecture](agent-design.md) ·
[Oracle](showcase/oracle.md) · [Evaluation](showcase/evaluation.md) · [Workload](showcase/workload.md)

## From agent output to database execution

In `pair-0-exploratory`, the model inspected training evidence, wrote threshold
scans and a staged fitter, handled host validation feedback, and exported six
policies. One export was `cons_S32_64_128_t002`:

```text
If any required feature is unavailable: continue.
At checkpoint 32, stop if frontier_count <= 983.
At checkpoint 64, stop if retained_result_count <= 1415.
At checkpoint 128, stop if completed_expansions >= 417.
Otherwise: continue.
```

The model chose the analysis, checkpoint combination, features, and thresholds.
The host validated the tree and recorded its offline assessment. The
[annotated conversation](showcase/agent-run.md) and
[original tree in the curated trace](showcase/agent-trace.json) preserve those
actions and the artifact.

A subsequent study froze all 12 distinct exports from the two completed
exploratory conversations and measured each against native database search.
No further model calls, fitting, or policy edits occurred in the timing stage.
The selected policy's hash remained
`b2f646df66ee7ad563d0cc5cc7d9c0cc49e7194cf1585af987a626335df0102f`
through both training and held-out measurement. Its source receipt and semantic
identity are in the [study evidence](showcase/study-evidence.json).

## Actual latency and retrieval quality

The workload is a 247,286-row, 768-dimensional Reviews index, cosine HNSW,
`ef_search=640`, `k=10`, with unfiltered, `votes32`, and `votes108` queries.
Each vector appears in all three filter conditions.

| Query set | Timing regime | Native mean | Policy mean | Latency saving | Native → policy mean Recall@10 |
|---|---|---:|---:|---:|---:|
| Training: 100 vectors / 300 cases | Activation-inclusive | 10.327 ms | 9.016 ms | 12.69% | 99.00% → 98.90% |
| Training: 100 vectors / 300 cases | Reuse | 9.140 ms | 7.902 ms | 13.54% | 99.00% → 98.90% |
| Held-out: 60 vectors / 180 cases | Activation-inclusive | 9.866 ms | 8.714 ms | 11.67% | 99.50% → 98.94% |
| Held-out: 60 vectors / 180 cases | Reuse | 7.591 ms | 6.651 ms | 12.38% | 99.50% → 98.94% |

Activation includes policy preparation/installation and first execution on warm
data. Reuse measures an already activated policy. All numbers are rounded from
the original reports; percentages use unrounded means. These timings include
the costs inside the original frozen policy timer, with no estimated overhead
subtracted. [Methodology and timing boundaries](showcase/evaluation.md).

## Where the savings appear

| Filter | Training activation saving | Training reuse saving | Held-out activation saving | Held-out reuse saving |
|---|---:|---:|---:|---:|
| `unfiltered` | 13.40% | 13.79% | 12.08% | 12.93% |
| `votes32` | 12.21% | 13.37% | 11.70% | 12.23% |
| `votes108` | 12.48% | 13.48% | 11.24% | 11.99% |

The reports retain each filter's recall and uncertainty alongside its latency.
Overall training recall change was **−0.10 percentage points**, with a grouped
95% interval of **[−0.233, 0.000]**. Held-out recall change was **−0.556 percentage
points**, with interval **[−1.056, −0.167]**. These measurements describe a
latency/recall tradeoff on the stated workload. Qualification under the
predeclared quality requirements is recorded separately in the source reports.

## What this demonstrates about the system

The model independently wrote analysis and fitting code through the supplied
interface, produced executable decision trees, corrected a structural error
using host feedback, and exported artifacts that could be frozen and measured.
The system made that path inspectable through command records, policy hashes,
receipts, paired timings, and grouped quality measurements.

The selected conversation used ten provider attempts and recorded **$0.530724**
in model API charges. Its original offline assessment estimated **31.00% less
search work** for this policy. That estimate and the later **13.54% reuse latency
reduction** measure different things; the actual native timing stage establishes
the latency result.

## Source records

- [Training verification](verification/frozen-proposals-timing-v1-runtime-fix-postrun.json): all 12 candidates, two cohorts, six blocks, 115,200 retained timing pairs across all arms, and the selected policy's statistics.
- [Held-out verification](verification/frozen-proposals-timing-v1-runtime-fix-confirmation-postrun.json): one unchanged selection, three blocks, 29,160 retained pairs across all arms, per-filter measures, and qualification decisions.
- [Generation verification](verification/aggressive-proposals-v2-postrun.json): proposal counts, model accounting, and the separate generation-comparison outcome.
- [Study evidence](showcase/study-evidence.json): selected projections from the saved packages, including policy lineage and query inventories.

These pages summarize existing records; no generation, database timing, fitting,
or scientific reanalysis was performed for this documentation update. The
original records preserve the full study outcomes. Full campaign reproduction
requires the external physical index, raw archives, and qualified runtime.
