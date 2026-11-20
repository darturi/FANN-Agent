# Clean-start Opus 5.5 replacement and feasible-oracle comparison

Completed November 20, 2026, America/New_York. Run
`c3735ec6f1b14fbabfde895c0d9892d4`, Torch job `23800555`, executed source
`a1fe405`. The user explicitly approved this fresh replacement after the first
episode's filesystem failure. The failed episode remains a separate charged record.

**Opus voluntarily abstained. No learned policy qualified, so the deployable
outcome is native continuation and 0% operational latency savings on both cohorts.**
The same global frozen native outcome was evaluated on both workloads. The two
existing `oracle_feasible` v3 policies were rerun unchanged, one fitted policy per
reported cohort, after the model closed. All final timing control gates passed.

| Cohort | Cases | Agent operational savings | `oracle_feasible` savings | Oracle 95% interval | Gap from native outcome |
|---|---:|---:|---:|---:|---:|
| Held-out, 275 vectors × 7 filters | 1,925 | 0% | **67.67%** | 65.96–69.38% | 67.67 percentage points |
| Full, 1,000 vectors × 7 filters | 7,000 | 0% | **68.03%** | 67.13–68.91% | 68.03 percentage points |

**Quality qualification differs on the full workload:** its oracle has zero
recall losses but returns fewer results than native on **three cases**. It fails
the agent's strict count-preservation gate. The held-out oracle has zero recall
or count losses and passes that gate. These are measured hindsight capacity
references, not certified global optima or evidence that the agent could discover
the same policies from its limited development evidence.

## Native timing and quality

Savings are one minus the ratio of mean arm latency to its adjacent randomized
native baseline. Times include SQL execution, transport and row materialization,
including policy feature/VM overhead. Compilation, database/snapshot setup,
transaction/attachment metadata and persistence are outside this clock and inside
the allocation budget. Each family has its own randomized paired native baseline.

| Cohort / arm | Mean paired native | Mean arm | Measured savings |
|---|---:|---:|---:|
| Held-out native-outcome adapter | 11.004 ms | 11.018 ms | −0.129% |
| Held-out feasible oracle | 11.018 ms | 3.562 ms | 67.671% |
| Full native-outcome adapter | 11.188 ms | 11.207 ms | −0.175% |
| Full feasible oracle | 11.214 ms | 3.585 ms | 68.029% |

The empty adapter's small measured overhead is retained in the raw estimates;
abstention deploys native, with zero early stops and 0% operational savings. The
raw report's gaps use these slightly negative adapter estimates; the headline
gaps above compare the oracle with operational native continuation. No positive
agent latency claim is supported.

| Cohort / arm | Recall-loss cases | Count-loss cases | Resource-fault cases | Early-stop cases |
|---|---:|---:|---:|---:|
| Held-out agent outcome | 0 | 0 | 0 | 0 |
| Held-out oracle | 0 | 0 | 0 | 1,923 |
| Full agent outcome | 0 | 0 | 0 | 0 |
| Full oracle | 0 | 3 | 0 | 6,996 |

The full oracle's count losses are `q0081-v527` (development, 9 versus 10
results), `q0808-v527` (validation, 6 versus 7), and `q0013-v310` (validation,
7 versus 9). Exact-scored recall remains equal to native on these cases: 0.7,
0.6 and 0.5. Recall preservation therefore does not imply count preservation.
The oracle was not repaired or refitted using these final results.

| Filter | Held-out oracle savings | Full oracle savings |
|---|---:|---:|
| Unfiltered | 88.19% | 87.60% |
| Votes ≥ 743 | 64.07% | 65.19% |
| Votes ≥ 527 | 53.25% | 53.87% |
| Votes ≥ 310 | 50.55% | 52.66% |
| Votes ≥ 192 | 61.67% | 62.79% |
| Votes ≥ 108 | 72.18% | 71.71% |
| Votes ≥ 32 | 84.09% | 82.75% |

## What the agent actually searched

The model was `claude-opus-5-5`, adaptive thinking/high effort, 16,000 maximum
output tokens per request. Its 38 settled paid calls cost **$10.387208**:
2,418,442 input tokens ($9.673768) and 35,672 output tokens ($0.713440). Input
context accounted for 93.1% of that cost. The audit counts 25 research-container
actions, four with code errors, four acquisitions, two feature profiles, one
generic fit, two search plans, and two completed candidate evaluation rounds.
Two additional evaluate invocations failed before native admission.

The agent acquired **3,957 actual prefix observations across 74 of 450
development vector groups**, covering all seven conditions. Its main acquisition
used 50 groups × 7 conditions and ten checkpoints, producing 3,423 observations.
These counts come from actual evidence, rather than its approximate stopping
report, which said 66 groups and about 7,300 queries. Actual discovery use was
**8,565 ANN/exact queries**.

| Candidate | Structure | Screen | Recall-loss / count-loss cases | Descriptive savings | Result |
|---|---|---:|---:|---:|---|
| `c1` | Per-filter/checkpoint depth-3 trees; 10 checkpoints, 11 features including checkpoint; 878 graph nodes | 14 cases / 2 vectors | 3 / 1 | 40.17% | Unsafe; controls also failed |
| `c2` | Frontier-gap margin rules; checkpoints 16/32/64 on four filters; 14 graph nodes | 98 cases / 14 unseen development vectors | 1 / 0 | 1.79% | Unsafe; controls also failed |

The candidate files are preserved as **unsafe exploratory artifacts**, not
deployment nominees. The second candidate's 95% savings interval was
−0.19–4.45%. Neither candidate reached the full 3,150-case development
confirmation gate. No full confirmation was attempted.

The stopping report cites observed recall plateaus, nonmonotone prefix labels
and a gap-rule failure on an unseen development group. It concludes that its
remaining conservative rules were unlikely to deliver a resolvable benefit. This
is the agent's decision, not proof that more search could not succeed. It left
**40,785 discovery queries, $3.383824 of the shared model budget, and substantial
discovery time unused**. `resource_exit` is false. The model-closed receipt's
generic `model_exhausted: true` flag means the conversation is closed; the
settled ledger and disposition establish that it did not exhaust its budget.

Both agent and oracle used the same broad v3 deployment language and caps:
8 MiB source, 131,072 graph nodes, expression depth 64, 4 MiB tables, 32
query-local state slots and 16 million fuel. Policies cannot access query IDs,
labels, future traversal, external I/O or mutate the index. The agent used
small trees and rules fitted to acquired development samples; the cohort-wide
hindsight oracle artifacts contain 9,083 nodes (held-out) and 33,813 (full), with
checkpoint declarations 1–226. Neither oracle uses state. Shared expressiveness
does not supply shared labels, optimization coverage or generalization evidence.

## Acquisition defect and qualification limits

The executed source's capture helper ORed feature-availability predicates.
Including `checkpoint` could specialize that predicate to true and remove the
other collector dependencies. Two initial acquisitions, **203 observations**,
therefore lacked the requested nonconstant feature values. Their prefix labels
were still obtained from actual forced-prefix executions. The agent diagnosed
the null values itself and requested later bundles without `checkpoint`; these
collected the nonconstant features. No coordinator advice or runtime source
change was supplied to the open conversation.

This defect cost evidence and model effort and is a material limitation of the
qualified workflow. Initial frame/VM qualification did not check preservation of
every requested collector mask. After model closure, commit `e623c4e` changed the
capture predicate to AND and added the missing regression. All 92 regressions
passed. **That future fix was not applied to the executed episode or final
comparison**, which remained sealed at `a1fe405`. Candidate quality and the
final comparison used actual native outputs and are not fabricated from missing
features.

## Measurement, isolation and completeness

The original graph contains 247,286 reviews with 768-dimensional vectors. Native
correctness, output/feature/state/fault/fuel parity, independent forced prefixes,
cleanup and the data-free research sandbox were qualified. Rejected early timing
qualifications exposed large cache-order bias and wide controls; those failures
and costs remain preserved. The accepted protocol uses four pinned readers,
adjacent randomized native/arm order on one reader per pair, charged per-case
warmups, and explicit read-only preparation of all 123,618 index pages in a
4 GiB PostgreSQL buffer pool. The source snapshot and index identity are unchanged.

The final run retained **73,850 primary timing rows**, covering two complete
blocks (readers 0 and 1), plus 98 arm/condition warmups. Clone and empty controls
pass every overall and per-filter 90% interval gate within [0.98, 1.02] on both
cohorts. Overall clone/empty ratios were 0.999810/1.002328 held-out and
0.999794/1.002408 full. The 95% latency intervals use 10,000 joint vector-group
and block bootstrap draws. They condition on one allocation and the selected
policies, with only two timing blocks; they omit allocation and policy-selection
variability.

All **15,925 quality rows** are present: 7,000 agent, 7,000 full oracle, and
1,925 held-out oracle. Every quality execution receives a compiled/reference VM
decision audit. Fixed 16-vector panels also check independent forced-prefix
outputs (112 cases for each oracle, 224 actual forced queries); the native
outcome has no stop to force. The final request made 190,919 query attempts,
including 6,486 fresh exact references; 514 references were reused with
same-episode provenance. No reference from an earlier experiment was reused.

The initial package had zero observations, fitted policies, scratch or prior
messages. The model could read only its task/API and this run's development
evidence. Protected vectors, truth, credentials, old experiment directories and
oracle artifacts were excluded from its data-free networkless research container.
The model closed and freeze digest
`dc435b8d468ce8377d2de6a68b1409acf87cbdd3e4f0c20e1e4260c6271147a9`
was verified before either oracle was opened. The finalizer returned no final
feedback to the model. The read-only report used the pinned Apptainer runtime
for NumPy, dispatching no further native queries or provider calls.

The full workload contains development, validation, test and historical groups.
Earlier hindsight studies have examined these cohorts. They remain protected
from this model's discovery, rather than being restored to a never-inspected
scientific holdout. The fitted oracles are cohort-specific; the global agent
artifact is the same on both cohorts. These differences limit causal attribution
of the performance gap to the model or search algorithm alone.

## Accounting and saved evidence

| Resource | Replacement | Earlier qualification + failed episode | Total | Authorized cap |
|---|---:|---:|---:|---:|
| Paid model accounting | $10.387208 | $1.228968 | **$11.616176** | $15 |
| ANN + exact attempts | 199,484 | 55,650 | **255,134** | 300,000 |
| Allocated seconds | 7,328 | 4,891 | **12,219 (3h23m39s)** | 21,600 |

The replacement ledger contains 192,484 ANN and 7,000 exact queries across nine
settled requests. All query journals match charged counts, with complete unique
ordinals. Worker status is `completed_frozen_comparison`, private cleanup is
verified, and Slurm reports `COMPLETED`, exit `0:0`. The allocation was explicitly
released after the report and evidence were saved. No further episode or final
attempt was launched.

Curated data: [metrics](metrics.json), [raw final report](final-report.json),
[accounting](accounting.json), [independent audit](audit.json),
[discovery audit](discovery-audit.json), [agent freeze](agent-freeze.json),
[oracle bindings](oracle-bindings.json), [scheduler](scheduler-accounting.txt),
[report execution](report-execution.json), and [artifact hashes](artifact-hashes.json).
Unsafe prototypes: [tree](unsafe-tree.json), [gap rule](unsafe-gap-rule.json).
The referenced oracle artifacts remain in `experiments/broad-oracle-v1/results/`.

Raw package, conversation, usage, tool actions, journals, returns and compiled
module are preserved in the sibling workspace:
`trials/fannagent-benchmark-evaluation-v1/reviews-small/torch-clean-start-v4/replacement-prepared-v1/`.
The verified return archive SHA-256 is
`f23b55e64732a60179e2836007b0398e7cf76d47e20c9b2a8c011927ef8f11d1`;
compiled module archive SHA-256 is
`1b38df22efc6a6082623eb081b04cde12d322cf02f67411fb4f3758014d3608b`.
These raw archives are outside this Git repository; cloning the repo alone does
not retrieve them.

Reproduce the saved-return audit without native/provider work:

```sh
.venv/bin/python experiments/torch-clean-start-v4/results/comparison-v1/assess.py \
  --trial ../trials/fannagent-benchmark-evaluation-v1/reviews-small/torch-clean-start-v4/replacement-prepared-v1
```
