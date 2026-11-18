# Hindsight oracle variants

The user requested three separately named comparisons on both the complete
1,000-vector workload (7,000 query/filter cases) and the 275-vector held-out
subset (1,925 cases). Each feasible policy is optimized in hindsight on its
reported cohort. These are retrospective capability diagnostics, not tests of
learning or generalization from development data.

| Variant | Hindsight freedom | Executable constraints |
| --- | --- | --- |
| `oracle_ideal` | Per-case earliest safe stop at any reached checkpoint | Dedicated evaluator-only stop arm; free choice |
| `oracle_constrained` | Per-case earliest safe choice at 16/32/64, otherwise native continuation | Same legal actions as the agent, but query-specific hindsight selection remains free |
| `oracle_feasible` | Hindsight selection of one complete policy per cohort | Unchanged agent v2 validator/compiler; at most three ascending clauses/filter, one per legal checkpoint; at most four comparisons/clause; only the four declared causal features |

The existing oracle results are registered as historical `oracle_ideal`
measurements. Their additional native-result-count constraint remains recorded.
The new comparison uses the actual agent quality gate consistently: no case may
lose native Recall@10. Duplicate, oversized, ineligible, or nonfinite outputs
remain invalid. A short answer is scored as misses and is never completed by
exact search. All exact references are reused evaluator-only inputs.

Feasibility requires a normal `fannagent.filtered-ann.v2` JSON artifact with
no query IDs, fold IDs, labels, lookup table or future state in its executable
rules. The unchanged validator and compiler must accept it. Native compiled
decisions, selective feature masks, actual outputs, and quality must match
reference replay on every case of the intended cohort. Serving measurements
include actual feature collection and rule evaluation for `oracle_feasible`.

The fitter searches the full conjunction form using finite observed threshold
equivalence classes, including missing-value semantics and first-stop behavior.
Its optimization objective is traversal work saved, with rule complexity as a
tie-break. Solver bounds/gaps are explicit. Native request latency is then
measured; work is not presented as time, and a work-optimal or best-found rule
is not relabeled a proven wall-clock optimum.

Original source results and protected-outcome exposure records remain intact.
No generated oracle label enters the ordinary agent training/feedback service.
Both hindsight cohorts overlap and neither result is a confirmatory agent test.

Fresh work reuses the same 247,286-row, 768-dimensional cosine graph, k=10,
native ef=640, and iterative scans off. Resource reservations precede queries;
uncertain and unused reservations remain charged. All case coverage, source
hashes, prefix proofs, compiler identities, outputs, timing boundaries and
allocation outcomes are retained. No provider calls are needed.

## Completed comparison

Capture job 23604734 and timing job 23610319 both completed successfully.
Independent verification covered 56,000 qualification requests and 448,000
primary timings. Aggregate allocated time was 9,410 seconds (2:36:50), with
four physical CPUs and 48 GiB per allocation.

| All seven conditions | Full workload: 7,000 cases | Held-out: 1,925 cases |
| --- | ---: | ---: |
| `oracle_ideal` | 68.25% savings | 67.52% savings |
| `oracle_constrained` | 55.12% savings | 54.67% savings |
| `oracle_feasible` | 17.98% savings | 27.20% savings |

The six-filter primary feasible results are 12.81% and 21.61%, respectively.
All variants have zero per-case native recall losses on their intended cohorts.
Feasible policies also preserve native result counts; the two lookup variants
have a few full-workload count losses under the common recall-only gate.

The feasible policies passed the actual unchanged agent validator/compiler and
native execution checks. They are best-found expressible policies, with unresolved
work optimization gaps. Strict per-condition timing equivalence controls did not
all pass, so latency estimates remain descriptive. The test-fitted policy has
147 recall losses outside its fitted cohort, retained in the evidence.

The [complete report](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/oracle-variants-v1/artifacts-v1/REPORT.md)
contains confidence intervals, per-condition results, controls and work bounds.
The [artifact registry](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/oracle-variants-v1/artifacts-v1/registry.json)
links ordinary feasible DSL files separately from evaluator-only lookup policies.
See [reproduction commands](COMMANDS.md) and the [timing protocol](TIMING-PROTOCOL.md).

The committed `results/` directory preserves the compact report, policies and certificates.
`checkpoint.json` records identities of the larger external raw returns; Git does not
contain those raw archives or the database.
