# FANNBench implementation audit

Original audit: 19 September 2026  
Latest re-audit: 20 September 2026  
Audited target: FANNBench 0.4.0 working tree after the three-path overhead-isolation revision  
Qualification record: `20260920T190218Z-73a043ad` on the local arm64 host

## Audit verdict

| Question | Verdict |
|---|---|
| Is the testing-harness revision complete enough to close the no-op/control issue? | **Yes, for the declared one-node arm64 profiles.** The three paths now perform observably different and correctly labelled work. |
| Can each database execute its own policy produced by the same future agentic system? | **Yes at the runtime boundary.** A separate run can install a distinct artifact for each backend. The policy-generating agent itself remains out of scope and unimplemented. |
| Can the harness test improvement over each database's native baseline? | **Yes.** It supports paired within-database latency, recall, failure, route, and controlled-work comparisons. |
| Can the project currently claim that one agentic system improves all three databases or identify which benefits most? | **No.** No learned policies, real-data study, held-out evaluation, or replicated cross-database comparison has yet been run. |

## Executive assessment

FANNBench now implements the execution substrate required for the proposed
stopping-policy experiment across PostgreSQL/pgvector, Elasticsearch/Lucene,
and Weaviate.

The harness can accept a canonical dataset and query workload, prove complete
filter eligibility, build exact answers, run the same physical index under
`native`, `policy_noop`, `fixed_budget`, and `policy_agent`, and return the
effective mode, actual search route, stop reason, checkpoint count, feature
collection, policy evaluation, and controlled-work counters from the same
timed execution that produced the neighbors.

The former no-op/control blocker is closed. `native` retains only the dormant
custom hook and route acknowledgement; `policy_noop` materializes the complete
agent feature snapshot without invoking an interpreter; and `policy_agent`
materializes that same snapshot and invokes the installed interpreter. The
canonical agent control always continues. This makes native-to-no-op an
observation-overhead comparison and no-op-to-agent an interpreter-overhead
comparison without pretending that the two paths are implementation-identical.

A real policy can alter search termination in every selected system, and the
harness can compare its latency, recall, completeness, and observed work with
the same system's custom-native behavior. Stock modes remain available as an
upstream reference, but their internal route and stop metadata are explicitly
unobserved.

The design also supports the clarified experimental unit: three independent
database experiments using the same policy-generation system but separate
generated policy artifacts. The current CLI accepts one `--policy` artifact per
invocation, so distinct policies are run as three backend-specific runs. It
does not force the three databases to share a policy. A future study must freeze
the generator, inputs, information budget, optimization objective, and compute
budget so that the database remains the intended independent variable.

This does not make the study complete. Real-data qualification, held-out
experimental design, policy-learning infrastructure, replicated policy
generation, cross-run aggregation, broader exact-query conformance,
cross-language interpreter golden tests, x86-64 qualification, and several
lifecycle/reproducibility controls remain open.

## Status against the requirements and research goals

| Requirement | Current status | Evidence and limit |
|---|---|---|
| Every admitted query has an equivalent form in every system | **Satisfied for the current adversarial suites; broader vector-objective proof remains open** | PostgreSQL, Elasticsearch, and Weaviate returned identical complete eligible-ID sets on the 27-query scalar fixture and the four-query field-collision fixture. Logical names are deterministically isolated from physical database fields, and undeclared Parquet columns are rejected. Dedicated exhaustive ranking conformance is still open. |
| Every system can execute a generated agent policy | **Implemented for the one-node experiment profiles** | All three custom builds accept the bounded `policy/v1` representation, expose 64-distance checkpoints on eligible traversal, and acknowledge execution through `same_execution_v2`. Elasticsearch is qualified only for one node and one shard. |
| Each database may receive its own policy from the same generator | **Supported through separate runs** | The runtime does not require cross-database policy identity. One invocation accepts one policy artifact, so three distinct artifacts require three backend-specific runs. |
| Observation overhead is isolated from interpreter overhead | **Implemented and live-qualified** | Native skips feature collection; no-op collects features with zero evaluations; canonical agent collects the same features and evaluates once per snapshot. Paired reports use separate interpretation labels. |
| A single agentic system improves every database over baseline | **Not yet evaluated** | The agentic generator and learned artifacts are not part of FANNBench 0.4.0. The current canonical policy is an always-continue control, not a treatment expected to improve search. |
| The study can identify which database benefits most | **Measurement substrate implemented; comparative conclusion unavailable** | Within-database paired effects and relative deltas are reported. Valid ranking still requires real data, frozen splits, replicated generation/training seeds, uncertainty analysis, and a declared cross-backend aggregation rule. |

## New implementation evidence

The observability revision introduced:

- schema version 4 for manifests, raw/evaluated measurements, summaries, and
  diagnostics;
- explicit `adapter_declared`, `server_observed`, and `unobserved` provenance;
- truthful stock values `stock_route_unobserved` and
  `native_reason_unobserved`;
- strict instrumented execution paths for pgvector HNSW/non-HNSW,
  Elasticsearch HNSW/exact/mixed, and Weaviate sweeping/ACORN/flat/mixed;
- a deterministic policy compiler with a 64-distance checkpoint interval;
- a typed stock/instrumented build catalog that prevents mixed mode families;
- digest-pinned source, patch, and local image records for all three engines;
- route-aware paired summaries that keep whole-workload effects primary and
  report same-route policy-eligible pairs separately;
- planned-schedule coverage that keeps unattempted pairs visible after an abort;
- a shared `metadata_ordinal_v1` mapping that isolates logical metadata names
  from backend-owned physical fields and records the complete mapping in the
  preparation report;
- exact Parquet column-set validation that rejects undeclared input columns;
- separate observation and evaluation counters, with no-op forbidden from
  invoking the policy interpreter;
- explicit policy roles that distinguish the always-continue calibration
  control from a treatment policy;
- pre-warm-up policy installation for Elasticsearch and Weaviate, with only a
  hash transported by timed requests; and
- a deterministic route fixture with broad, selective, rare, zero-match, and
  repeated queries.

The current custom artifacts are:

| Engine | Source | Patch SHA-256 | Instrumented image ID |
|---|---|---|---|
| pgvector 0.8.6 | `8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c` | `eaa8d3294629bb81629e9f2fbcd81679519eaf9d7486dc51cdbcf3a16fcf7ba8` | `sha256:a1968116e8d4d2c9628430955f2658913e8c777e4839c46796dc100737bbe5d9` |
| Weaviate 1.39.2 | `409d0c771af6a25809993cf807c96c10029ece3d` | `c49b22cce6dbb54e39a2eeb0958ede673ddfac0d2a12787c5ff322bec17a4f26` | `sha256:a63daf971be5ec8d14dfab5b06525e5acbefa13b1da345173fa522a40940dc69` |
| Elasticsearch 9.5.4 / Lucene 10.5.1 | `9170df19cae1adb107b7b489b4d82dec66d7a337` | `9263f6c6584d327ca8573eef7f325d9a715e2ac9c2dbd76c6ea8695fe0ef931b` | `sha256:2cb70c05fa37433ff635c72ee822ab6459104c91c7df9c7542e2290661a46dc5` |

The live instrumented route suite passed for all three engines. It produced 32
measurements per engine across the four custom modes. Every successful sample
had server-observed mode, route, and stop provenance. Native, no-op, and the
canonical always-continue agent returned the same IDs. Native reported no
agent-observation counters; no-op and agent collected the same snapshots, and
only agent invoked the interpreter. Fixed-budget stopped at a safe batch
boundary when a checkpoint opportunity existed. Exact/flat/non-HNSW routes
correctly reported no policy opportunity.

For Elasticsearch, the implementation also preserves Lucene's native patience
optimizer inside the request strategy. A deliberate policy stop returns the
already collected HNSW candidates and does not trigger Lucene's normal
replacement exact scan.

Final validation on the Apple Silicon host produced:

- 91 passing non-integration tests and eight intentionally deselected Docker
  tests;
- Ruff and repository whitespace checks with no findings;
- three passing instrumented route tests, one per engine, covering 96 total
  measured samples;
- five passing Docker smoke tests: three stock per-engine runs, the combined
  stock filter-eligibility comparison, and a combined instrumented
  field-collision run across all three engines;
- successful native compilation of the pgvector patch, focused Go tests for
  Weaviate, a build-time Java contract test plus Java 21 compilation for the
  Elasticsearch/Lucene overlays, and clean patch-apply checks against the
  locked upstream commits;
- a 30-pass three-engine calibration qualification with 2,160 successful,
  server-observed measurements, complete schedule coverage, and zero failures;
- successful construction of the 0.4.0 source distribution and wheel; and
- successful installation of that wheel in a clean environment, policy
  validation, packaged Compose discovery, and `doctor --require-policy` with
  all three image IDs verified.

The 30-pass qualification is a contract and reporting gate, not a performance
result. It used eight synthetic queries, one canonical always-continue policy,
and one local execution session. Across all three backends, every no-op/agent
pair had equal aggregate feature-collection counts, every no-op evaluation
count was zero, every agent evaluation count matched its collected snapshots,
and recall delta was zero. The observed latency deltas are not treated as
stable overhead estimates until independent repetitions under controlled host
conditions establish their uncertainty and repeatability.

## Alignment with the intended experiment

The intended independent variable is the database system, not a shared policy
artifact. The correct future experiment is therefore:

1. freeze one agentic policy-generation procedure and one evaluation protocol;
2. give it the database-specific development evidence allowed by the study;
3. generate and freeze one policy artifact per database and per declared seed;
4. evaluate each artifact only against its own database's native baseline on
   held-out workloads; and
5. compare normalized within-database improvements, uncertainty, failure rate,
   recall trade-offs, and policy opportunity coverage across databases.

FANNBench now supports steps 3 and 4 at the runtime boundary. It does not yet
implement steps 1 and 2, automate the three-run experiment bundle, or define
the step-5 cross-database ranking. Raw latency across databases must not be used
to decide which database “benefits most”; that conclusion must be based on
within-database treatment effects under equivalent study conditions.

## Engine implementation summary

### PostgreSQL/pgvector

The request initializes transaction-scoped execution state. The pgvector HNSW
hook acknowledges every custom mode. In observing modes it counts layer-zero
distance work; no-op builds and discards the shared feature snapshot, while
agent mode evaluates that snapshot. Fixed-budget and policy stops occur only at
safe traversal boundaries. Native exits before observation accounting.
PostgreSQL plans that do not use HNSW are reported as `postgresql_non_hnsw` and
do not pretend to offer policy checkpoints.

### Weaviate

Request-scoped control travels through the existing API context into HNSW.
Sweeping and ACORN routes, flat fallback, checkpoint work, stop decisions, and
runtime policy errors are returned on the GraphQL response. The adapter
installs and digest-validates the compiled artifact before warm-up; timed agent
requests send only its hash.

### Elasticsearch/Lucene

A built-in search extension transports control data through shard
serialization. Lucene records the actual vector-reader choice rather than
assuming that an HNSW index means HNSW executed. Level-zero HNSW work supplies
checkpoints; exhaustive and direct exact scans are counted without exposing a
stopping opportunity. The response header is attached to the ordinary timed
search response.

The current deployment is one Elasticsearch node with one shard. The state is
concurrency safe within that node. A distributed profile would need explicit
shard telemetry transport and coordinator reduction before it could make the
same claim.

## Closed findings

| Prior finding | Current disposition |
|---|---|
| Qdrant could not execute all admitted filters | **Superseded.** The active cross-section is pgvector, Elasticsearch, and Weaviate. |
| Milvus did not expose the required traversal control | **Superseded.** Weaviate replaced it and now executes the policy in its search loop. |
| Stock adapters guessed HNSW and `native_limit` | **Closed.** Stock paths and reasons are unobserved; custom paths are server-observed. |
| No database could execute the policy | **Closed.** All three custom builds passed the same four-mode route suite. |
| No common native policy representation | **Closed for execution.** A deterministic bounded bytecode is compiled once and evaluated server-side by C, Java, and Go implementations. |
| No-op skipped the machinery whose overhead it was meant to measure | **Closed.** No-op now executes the exact feature-collection path used by agent mode, records collection count/time, performs zero evaluations, and never stops. |
| Native still paid feature-collection overhead | **Closed for the declared estimand.** Native returns before observation counters and feature materialization; the dormant hook, common wrapper, mode branch, and route acknowledgement remain intentionally shared. |
| Timed requests transferred or parsed policy bytecode | **Closed.** Policies are installed before warm-up; timed agent requests carry only the installed hash. |
| Policy stops could be replaced by Elasticsearch exact fallback | **Closed.** Policy/fixed stop bypasses that fallback. |
| The placeholder could be mistaken for a treatment | **Closed.** It remains adapter-declared, carries no policy hash, and is labeled `pipeline_placeholder_only`. |
| Invalid IDs and malformed results looked successful | **Closed.** They are correctness failures and make the run incomplete. |
| Elasticsearch partial responses looked successful | **Closed.** Timeouts and failed shards are rejected. |
| Evaluation ran inside the timed request stream | **Closed.** Correctness evaluation occurs afterward. |
| Aborted schedules hid unattempted pairs | **Closed.** The manifest records the planned schedule and summaries report expected, recorded, and missing measurements plus missing pair members. |
| Logical metadata names could collide with backend-owned fields | **Closed for the declared canonical schema.** All metadata fields use the shared `metadata_ordinal_v1` physical encoding in schema creation, ingestion, filters, diagnostics, and eligible-ID checks. Extra Parquet columns are rejected, old physical schemas cannot be silently reused, and a live collision fixture passed all three engines. |

## Remaining findings

### 1. [P1] Conformance does not yet prove the complete vector objective

The current conformance command proves that each database selects the same
filter-eligible IDs. Exact ranking, distance interpretation, fewer-than-k
behavior, and boundary ties are checked by the central oracle during benchmark
evaluation, but there is no dedicated backend-native exhaustive conformance
mode or generated expression suite.

Why it matters: the 27-query fixture is strong evidence for its cases, but it
is not a general proof for every workload admitted by the bounds.

Potential solution: add an untimed exact-search route per backend, generate
bounded valid predicates and edge-valued datasets, compare ordered top-k under
declared tolerances and tie rules, and save minimized disagreement bundles.

### 2. [P1] The shared agentic generator and held-out study are not implemented

`policy_agent` executes a supplied artifact, which is enough to measure a
policy's effect. The system does not yet collect the full development evidence,
train or prompt the common agentic system, generate independent database-
specific policies, compare it with non-agent policy search, freeze winners, or
evaluate those artifacts on held-out workloads.

Why it matters: the database-side treatment is now measurable, but the research
method that produces the three treatments while keeping the generator constant
is still absent.

Potential solution: add trace/replay or a declared live calibration workflow,
freeze development/calibration/test splits, expose the same policy language and
information/compute budget to agent and non-agent baselines, repeat generation
across declared seeds, and archive every emitted artifact with database,
generator, prompt, tool, model, and training provenance.

### 3. [P1] Real-data qualification has no evidence

The importer exists, but there is no verified MoReVec snapshot, frozen split,
self-match rule, or archival result bundle in the workspace.

Potential solution: verify source terms, import and hash the small then medium
datasets, record sampling and self-match treatment, and run conformance plus
native/no-op controls before policy development begins.

### 4. [P1] Cross-database policy runs are not yet one auditable experiment bundle

The runner accepts one policy artifact per invocation. This correctly permits
three independent backend-specific runs, but there is no first-class bundle
that binds those runs to one generator version, dataset split, protocol,
information budget, seed schedule, and cross-database analysis.

Why it matters: without that bundle, the final “which database benefits most”
comparison can accidentally mix policies or runs produced under different
conditions. Raw latency and absolute work counts are not comparable across
engine architectures.

Potential solution: add a study manifest whose children are one run per
database/policy/seed, validate shared experimental fields, and report normalized
within-database effects with confidence intervals, opportunity coverage, recall
constraints, and failures. Keep the individual policy hashes distinct.

### 5. [P2] Native interpreters need a shared golden conformance suite

The live route suite covers canonical-continue and fixed-budget behavior;
focused Go and Java tests additionally cover stop, rejection, and fallback,
and the Python evaluator has boundary tests. pgvector is compile- and
integration-qualified rather than covered by a focused native C corpus. There
is not yet a cross-language suite covering every operator, int64 overflow,
division by zero, unavailable features, malformed bytecode, and runtime
fallback behavior in C, Java, and Go.

Potential solution: serialize one golden corpus and run it directly against
each native evaluator during image builds. Require identical decision or error
classification before accepting an image lock.

### 6. [P2] Portable work counters cover the policy-controlled layer only

The common `distance_evaluations` counter measures layer-zero work used for
checkpoints. Upper-layer and entry-point work is outside that counter. This is
consistent within each native/no-op/agent comparison, but it is not total
vector work and should not be presented as such across systems.

Potential solution: keep the current counter as the portable decision budget,
add separately named engine counters for upper-level and other scoring work,
and report both controlled work and total work where the engine can observe it.

### 7. [P2] Distributed Elasticsearch telemetry is not implemented

The harness profile intentionally uses one node and one shard. A multi-node or
multi-shard experiment would need per-shard state, route aggregation, summed
counters, deterministic error handling, and response transport to the
coordinator.

Potential solution: either keep one shard as an explicit study constraint or
implement a versioned shard result extension and coordinator reducer before
expanding the deployment profile.

### 8. [P2] The overhead calibration is qualified once, not replicated

The 30-pass run proves that pairing, accounting, labels, counters, and exports
work. It does not establish a stable observation- or interpreter-overhead
estimate. Only one definitive run on one host is treated as qualification
evidence, and the fixture has eight synthetic queries.

Why it matters: these overheads are small relative to request noise. A single
session can produce sign changes or unstable rankings that should not be
interpreted as a database property.

Potential solution: run independently restarted calibration blocks, control
background load and engine concurrency, retain every block, analyze block-level
effects, and declare values below resolution when confidence intervals remain
too wide. Do not subtract these estimates from the primary end-to-end result.

### 9. [P2] Reproducibility and failure qualification remain incomplete

The manifests record image/source/patch identity and Docker resources, and the
0.4.0 wheel has passed a clean-install check. The study has only been exercised
on Apple Silicon. Thread counts, CPU affinity, compiler identities, interrupted
ingestion, restart/reuse, timeout quiescence, concurrent request isolation, and
x86-64 behavior need retained evidence.

Potential solution: freeze engine concurrency settings, record toolchain
versions, qualify x86-64, and add opt-in lifecycle tests for interrupted import,
restart, cancellation, and exact scoped cleanup.

## Release-gate assessment

| Gate | Status |
|---|---|
| Portable scalar validation and physical field isolation | **Passed on both arm64 adversarial fixtures** |
| Complete eligible-ID equivalence on the adversarial fixture | **Passed on arm64** |
| Dedicated exact vector-objective conformance | **Not implemented** |
| Truthful stock route and stop provenance | **Passed** |
| Same-execution custom route and stop telemetry | **Passed for all three one-node profiles** |
| Native/no-op/fixed-budget/agent modes | **Passed for all three engines** |
| Native performs no agent observation or evaluation | **Passed on the route fixture and strict response validators** |
| Native/no-op/canonical-agent result equivalence | **Passed on the route fixture and 30-pass qualification** |
| No-op/agent feature-collection equivalence | **Passed: aggregate counts matched in every qualified backend** |
| No-op performs zero policy evaluations | **Passed: zero evaluations in every qualified sample** |
| Canonical agent evaluates once per collected snapshot and never stops | **Passed** |
| Timed agent requests carry only an installed policy hash | **Passed for all three engine integrations** |
| Intentional stop reduces controlled traversal work | **Passed when a checkpoint opportunity exists** |
| C/Java/Go full golden interpreter agreement | **Partially tested; full corpus open** |
| Whole-workload and comparable-route paired summaries | **Implemented** |
| Planned, missing, invalid, timed-out, and incomparable pairs remain visible | **Implemented; timeout-abort accounting unit-tested** |
| Stable replicated overhead estimates | **Not established; current 30-pass run is a qualification only** |
| Real MoReVec qualification | **Not performed** |
| Shared agentic generator with independent per-database policies | **Not implemented** |
| Held-out agent-policy evaluation | **Not implemented** |
| Cross-database benefit ranking | **Not yet scientifically supported** |
| arm64 synthetic qualification | **Passed** |
| x86-64 qualification | **Not performed** |
| Distributed Elasticsearch profile | **Not supported** |

## Recommended next work

1. Add backend-native exact ranking conformance and generated predicate cases.
2. Add the cross-language policy golden corpus to all image gates.
3. Acquire, hash, and freeze the real-data development/calibration/test
   workloads and self-match rules.
4. Specify and implement the common agentic generator, then produce independent
   per-database policies under equal information and compute budgets.
5. Add a study-level manifest and analyzer that bind the three database runs
   while preserving distinct policy hashes and comparing normalized
   within-database effects.
6. Replicate the overhead calibration in independent controlled blocks and
   qualify x86-64, concurrency, recovery, cancellation, and cleanup before
   publishing performance conclusions.

The testing-harness phase is ready to hand off to agent-system and study-design
work. This is a release decision for the current harness scope, not approval to
publish claims of agent improvement.

Detailed design records:

- [FANNBench three-path overhead-isolation plan](fannbench-three-path-overhead-isolation-plan-2026-09-20.md)
- [FANNBench execution-path observability plan](fannbench-execution-path-observability-plan-2026-09-20.md)
- [Portable query and policy implementation plan](fannbench-portable-policy-implementation-plan-2026-09-20.md)
- [Logical-to-physical field isolation plan](fannbench-field-name-isolation-plan-2026-09-20.md)
