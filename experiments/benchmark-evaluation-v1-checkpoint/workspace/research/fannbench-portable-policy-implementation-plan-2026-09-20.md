# FANNBench revision: portable queries and policies in every database

Implementation plan — 20 September 2026

Status: database execution substrate revised in `harness` 0.4.0. The `same_execution_v2` contract separates dormant native instrumentation, observation-only no-op, and actual policy evaluation as specified in [`fannbench-three-path-overhead-isolation-plan-2026-09-20.md`](fannbench-three-path-overhead-isolation-plan-2026-09-20.md). Policies are installed before warm-up and timed agent requests carry only a hash. Agent-driven policy synthesis, real-data qualification, and held-out evaluation remain future work.

Implementation evidence recorded on 2026-09-20:

- PostgreSQL/pgvector, Elasticsearch, and Weaviate passed the same 27-query eligible-set suite, covering unfiltered, zero-match, full-range int64 (including values beyond float-safe range), float64, Boolean, UTF-8 string, `eq`, `in`, all numeric ranges, and nested `AND`/`OR`/`NOT` cases.
- All three pinned stock containers passed the end-to-end benchmark integration test on arm64 Docker Engine 29.6.1. Stock samples now acknowledge only the harness mode and explicitly report their route and termination reason as unobserved.
- `policy/v1` validation and golden cases, explicit unavailable features, int64 overflow checks, float64 finite checks, five declared execution modes, request pairing, query-level paired effects, correctness failures, timeout aborts, and raw/evaluated result separation are implemented. Engine acknowledgements use a strict typed result contract with required mode, executed path, stop reason, policy identity, checkpoint count, and validated nonnegative finite work counters.
- Engine source is locked to pgvector `8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c`, Elasticsearch `9170df19cae1adb107b7b489b4d82dec66d7a337`, and Weaviate `409d0c771af6a25809993cf807c96c10029ece3d`. Applied patches, reproducible build scripts, image IDs, feature matrices, and remaining limits are recorded under `harness/engines/`.
- The common instrumented route fixture passed for all three engines: 32 samples per engine across four modes, with HNSW and non-HNSW/flat/exact routes, native/no-op/canonical-agent result invariance, no-op/agent observation equivalence, and reduced work for fixed-budget stops when a checkpoint was available. Separate focused engine tests retain stop-policy coverage. Requirement 2 is therefore implemented for the declared one-node experiment profiles.
- `policy_placeholder` runs the identical stock request under a separate paired label on all three databases. Its result contract forbids policy hashes, application, runtime errors, and fallbacks; paired reports mark it `pipeline_placeholder_only`. This makes the full data/query/output pipeline usable before source hooks exist without turning the placeholder into policy evidence.

## 1. Required outcome

Deliver a three-system harness for **PostgreSQL + pgvector, Elasticsearch + Lucene, and Weaviate**, with two mandatory properties:

1. Every query accepted by the harness's shared workload contract has an equivalent execution in all three systems.
2. Every system can execute the deployed stopping policy inside its own search implementation and compare it with that same system's native behavior.

The intended comparisons are:

| System architecture | Baseline | Treatment |
|---|---|---|
| Relational | PostgreSQL/pgvector native execution | PostgreSQL/pgvector with the policy enabled |
| Search engine | Elasticsearch/Lucene native execution | Elasticsearch/Lucene with the policy enabled |
| Specialized vector database | Weaviate native execution | Weaviate with the policy enabled |

An engine that only runs the unmodified benchmark does not satisfy this revision. Completing one policy integration is an intermediate milestone; release requires all three. If a feasibility gate fails, report the failed requirement and propose a replacement or revised implementation. Do not quietly drop a system or change the agent's action to selecting parameters before a query.

“Equivalent queries” means the same logical filtered nearest-neighbor problem over the same canonical dataset, with the same metric and result objective. ANN answers can differ in recall. It does not mean that every SQL, text-search, or vendor-specific operation must be implemented by the other products. The guarantee applies to every accepted harness query, including when a run selects only a subset of the three systems.

Custom, pinned database builds are part of this design. The offline agent produces a small policy artifact. A local runtime inside each database evaluates it; there is no LLM or network round trip at a search checkpoint.

## 2. Current state and changes to earlier proposals

At the time this revision was drafted, the Python harness contained dataset loading, a scalar predicate AST, a MoReVec importer, a cosine oracle, Docker lifecycle management, sequential measurement, and adapters for pgvector, Elasticsearch, and Milvus. The current 0.4.0 harness uses Weaviate and includes the policy artifact, compiler, native runtimes, execution modes, conformance, same-execution acknowledgement, route-aware pairing, and source-level checkpoints. Trace/replay and agent-development infrastructure remain unimplemented.

The [initial harness plan](vector-search-harness-implementation-plan.md) still describes Qdrant and defers policy integration. The [Milvus audit](milvus-fit-audit-2026-09-20.md) records a successful functional substitution but recommends an independent policy engine. The [research plan](learning-data-shape-filtered-ann-project-plan-v2.md) assumes one instrumented engine and excludes multiple engines from its required scope. This revision supersedes those recommendations for system selection, integration obligations, and delivery scope; their other research requirements remain applicable unless explicitly changed here.

Three corrections are necessary before implementation:

- Source availability and a visible search loop establish possible integration points, not completed feasibility. Build and exercise the hook through the database interface before accepting a system.
- Lucene collector early termination can interact with exact-search fallback. A collector wrapper alone is not enough evidence that the database will return the intended stopped result.
- A portable policy interface does not require identical HNSW graphs, traversal paths, or learned coefficients across engines. It requires precisely defined inputs and actions. A single frozen artifact must be executable by all three; separately trained artifacts and cross-engine transfer are distinct experiments.

The pre-revision Git baseline preserves the former Milvus adapter and configuration, and old result bundles remain readable as historical artifacts. The active Milvus path was removed following the user's explicit substitution direction. The three replacement source gates have now passed, and the CLI selects the instrumented images for the four custom modes while preventing stock and custom modes from being mixed in one backend run.

## 3. Experimental invariants

### Native behavior remains the main baseline

Use the database's normal planner, predicate execution, and exact-search fallbacks in the main experiment. When it chooses exact search, the stopping policy does not intervene and the result is marked `policy_applied=false`. Such queries remain in whole-workload results. Report separately how often the policy had an opportunity to act.

A separately named `controlled_hnsw` configuration may constrain routing to diagnose the policy's effect on ANN traversal. Both baseline and treatment use the same constraints. Results from that configuration cannot be described as improvement over unrestricted native optimization.

Native defaults and a reasonably tuned native configuration are separate baselines. Tune search budgets against development/validation data and freeze them before final testing. The policy should be compared with a credible native configuration at the declared recall requirement, not only with a weak default.

### Hold each engine's index and execution settings fixed

Within each native-versus-policy pair, hold dataset snapshot, physical index, graph construction, filter semantics, metric, candidate handling, expansion order, thread settings, and maximum search budget fixed. Only the additional stopping decision and its observation/execution overhead may differ.

Do not rebuild an index separately for each mode: equal construction seeds are not proof of an identical graph. Switch modes against one immutable prepared resource; where separate stock and custom servers are required, use a verified compatible snapshot/clone and record its identity.

Across engines, preserve identical canonical input and logical queries. Different physical layouts and native algorithms are part of the architectural cross-section. Equal `ef` and `num_candidates` values are not assumed to represent equal work.

### Define the action precisely

The first policy action is **additional early stopping** at safe checkpoints. `continue` resumes the native traversal and permits its own stopping condition to take effect. It does not revive an exhausted traversal or override native convergence, SQL `LIMIT`, safety limits, or timeouts.

Overriding native termination to search longer is a different extension requiring a new protocol. This revision measures savings or harm from earlier stopping, plus policy overhead and any quality loss. It does not promise that stopping alone can improve recall.

## 4. Common workload contract

Implement a versioned profile, `portable_fann_v2`, used by every comparative run. Backend-only experiments must be labeled outside this profile. Validate against the full three-engine profile even when only one backend is selected.

| Area | Proposed v2 contract |
|---|---|
| Query | Single-vector filtered top-k retrieval; exact mode available for conformance |
| Vector input | Finite, nonzero, normalized float32 vectors; normalization performed once and recorded |
| Metric | Cosine distance; native score retained separately from canonical distance |
| Dimensions | 1–2,000, subject to boundary verification on pinned builds |
| Result size | Initially 1–100; the existing broader limit is not portable until validated and explicitly added |
| Metadata | Present, non-null scalar signed int64, finite float64, Boolean, and UTF-8 string |
| Equality/membership | `eq` and nonempty `in` for all four metadata types |
| Ordered comparisons | `lt`, `lte`, `gt`, `gte` for numeric fields |
| Composition | Nested `and`, `or`, and unary `not`; empty AND/OR expressions rejected |
| Initial expression bounds | Depth at most 16, at most 128 leaves, at most 128 values per membership expression |
| String semantics | Exact whole-value, case-sensitive equality; no implicit trimming, case folding, or Unicode normalization |
| Initial string bound | 4,096 UTF-8 bytes, tested with all mappings and transports |
| Outside the profile | Nulls, missing fields, arrays, joins, text/hybrid ranking, regex, geo predicates, multiple vectors, and updates during measurement |

The dimension cap reflects pgvector's documented float32 HNSW limit. These bounds are proposed implementation choices, not a claim that all products have identical native limits. Confirm the exact profile with tests before freezing its version. Existing files outside it receive a precise preflight error; do not silently truncate vectors, lower k, rewrite values, or run only the systems that happen to accept them. [pgvector HNSW types](https://github.com/pgvector/pgvector#hnsw)

### Data and predicate translation

1. Validate Parquet/Arrow scalar types before conversion. Reject fractional IDs, duplicate IDs, overflow, nonfinite values, undeclared metadata, and mismatched schema declarations.
2. Require normalized canonical vectors. Importers may normalize source data, but must save the resulting snapshot and hashes. Reject a manifest that declares unnormalized canonical inputs.
3. Define float equality over the canonical float64 value after parsing, not decimal display text. Canonicalize signed zero consistently in stored metadata and predicate literals; reject NaN and infinities. Numeric range boundaries remain exact comparisons, without an invented epsilon.
4. Translate predicates to parameterized SQL, Elasticsearch term/terms/range/bool queries, and Weaviate typed filters. Membership can use a documented native operator or an OR of exact equalities.
5. Use PostgreSQL deterministic exact text comparison, Elasticsearch `keyword` with no normalizer or truncating `ignore_above` configuration, and Weaviate whole-field tokenization with no stopword-induced loss. Test empty strings, whitespace, punctuation, case, quotes, and distinct Unicode representations. If a backend cannot preserve an admitted string, introduce a tested injective encoding for its equality-only field mapping and literals; never silently change logical semantics. [Weaviate tokenization](https://docs.weaviate.io/weaviate/concepts/indexing/inverted-index)
6. Preserve canonical IDs. Weaviate requires a stable UUID mapping: encode the canonical nonnegative int64 ID injectively into a fixed UUID layout, retain the canonical ID as metadata, and round-trip it. Do not use an unchecked hash as the identity mapping.
7. Validate large int64 values through actual client/server transports, especially values above 2^53. A product accepting an integer type is insufficient if an intermediate JSON representation rounds it.
8. Map logical metadata names to validated physical field names, and record that mapping. Reject or map collisions with engine-reserved names, including the pgvector adapter's `embedding` column. Use the same mapping for loading, filtering, diagnostics, and ID retrieval.

### Proving equivalence

Add an untimed `eligible_ids` conformance operation that retrieves every matching ID, with pagination, without ANN. Compare the complete sets with the independent predicate evaluator; matching counts alone do not prove equality. Include unfiltered, zero-match, fewer-than-k, nested-negation, numeric-boundary, float-membership, and Boolean-membership cases.

Then run exact vector search over the matching rows and compare the top-k objective with the independent oracle. Use a declared distance tolerance and boundary-tie rule. Strictly better neighbors cannot be replaced by extra tied neighbors for full recall credit. An empty eligible set has no recall denominator and must be reported separately.

Use deterministic adversarial fixtures plus generated expression/data cases. Save a minimal reproducer whenever the engines disagree. Live conformance tests are required in addition to translator unit tests. [Weaviate filter API](https://docs.weaviate.io/weaviate/api/graphql/filters)

## 5. Shared policy and telemetry contract

### Policy artifact

Define `policy/v1` as a bounded, declarative decision tree or expression AST with `continue` and `stop` leaves. Initial limits: 255 AST nodes, depth 8, no loops, no recursion, no I/O, and a bounded shape-model table of at most 64 KiB. Treat these limits as configuration decisions frozen before evaluation.

The manifest includes policy hash, shape-model hash, required feature profile, interpreter version, training provenance, numeric semantics, checkpoint schedule, and allowed engine profiles. Resolve and validate it before warmup. Unknown features or incompatible artifact versions fail installation.

Implement a Python reference evaluator and C, Java, and Go evaluators with common golden test vectors. Use explicitly defined int64 counter operations and float64 statistical operations; specify conversions, division-by-zero handling, finite-value checks, evaluation order, and overflow behavior. Do not let language-specific truthiness or numerical rules determine decisions.

Counters must remain integer-valued when a conversion to float64 could lose precision. Quantize any derived input only through a documented shared rule. The same input record must cause the same decision in every evaluator, including near threshold boundaries.

The agent's output remains inspectable and inexpensive. No arbitrary generated native code is needed for the initial implementation. Compilation to a faster form can be added later only after proving equivalence with the reference evaluator.

### Feature availability is a feasibility result

Do not promise that every engine naturally has a filter-qualified top-k heap at every node visit. In particular, pgvector's index scan does not directly see all PostgreSQL predicate outcomes. Candidate heaps and qualifying result heaps are different objects.

During feasibility, produce a per-engine feature matrix with definition, observation point, scope, availability, and cost. Freeze a mandatory shared profile only after it works in all three:

| Feature group | Intended meaning | Acceptance condition |
|---|---|---|
| Request | k and approved predicate descriptors | Same semantic definition everywhere |
| Work | Actual vector-distance evaluations, unique discoveries, completed expansions | Count separately; an engine's generic “visited” counter cannot stand in for all three |
| Progress | Checkpoint index and work since the previous checkpoint | Same checkpoint rule with explicit safe-boundary rounding |
| Qualified results | Already observed, distinct, snapshot-visible qualifying candidates and their best-k distances | Only exposed when that qualification has actually been evaluated |
| Search trajectory | Recent distance/result improvement and frontier summaries | Record which queue/population is measured; do not substitute a candidate-heap threshold for a top-k threshold |
| Shape memory | Approved fixed-size summaries acquired from development data | Same lookup definitions and information budget |

Features whose meanings cannot be aligned remain optional engine-specific diagnostics. A portable artifact cannot require them. Missing values are explicitly typed unavailable, never fabricated zeros. The first prototype can use work counters alone, but the gate must establish enough common observations to support the intended filter-aware, shape-conditioned policy before declaring the research integration feasible.

Filter observation may itself require work that the native engine would not have done yet. If necessary, perform that observation identically in `policy_noop` and `policy_agent`, account for it in their latency, and compare both to native execution. Verify that it does not alter the native traversal. Do not supply an oracle-computed eligibility bitmap to the treatment without charging and disclosing that preprocessing.

### Checkpoints and termination

Begin with a target checkpoint every 64 layer-zero vector-distance evaluations. Invoke the policy at the next safe expansion/batch boundary, record the actual count and overshoot, and distinguish entrypoint/upper-layer work from policy-controlled work. Tune checkpoint frequency on development data and freeze it for evaluation.

The treatment must not change queue capacities, expansion order, candidate acceptance, filter strategy, or result assembly when it continues. On `stop`, finalize results already available at the approved checkpoint. Do not execute a replacement exact search, restart ANN, or send a second larger query to simulate continuation.

Where an index returns unfiltered candidates, completing the ordinary predicate checks on the already-buffered candidates can be part of finalization; log and charge that work. Do not claim those outcomes were available as policy inputs before they were evaluated.

Record distinct reasons: `native_convergence`, `native_limit`, `policy_stop`, `fixed_budget_stop`, `exhausted`, `timeout`, `cancelled`, and `error`. Deliberate policy stopping is a completed approximate answer, not a transport timeout. Wrong IDs, duplicates, predicate violations, excessive result counts, and malformed scores are correctness failures. Short answers and low recall are measured quality outcomes with explicit counts.

If runtime evaluation fails, disable the policy for the rest of that query, continue native execution, and record the failure and fallback. Such samples stay visible in deployment metrics and cannot be counted as successful agent decisions. Native hard limits always remain effective.

## 6. Mandatory execution modes and baseline verification

| Mode | Purpose |
|---|---|
| `stock_native` | Unmodified pinned upstream build, used to verify the experimental build |
| `native` | Custom build with dormant hook/route acknowledgement but agent observation disabled; main paired baseline |
| `policy_noop` | Full feature-observation path, no interpreter invocation, always continuing |
| `fixed_budget` | Deterministic stopping using the same checkpoint mechanism |
| `policy_agent` | Preinstalled policy evaluated on the same no-op feature snapshots; canonical always-continue policy during overhead calibration |

`policy_placeholder` is an additional temporary harness mode, not a scientific treatment. It executes the identical `stock_native` request so dataset loading, paired scheduling, validation, and result generation can be exercised before custom builds exist. It always records `policy_applied=false`, carries no policy hash or telemetry, and is excluded from claims about policy effects.

Hand-written and conventional learned policies use the same artifact interface and telemetry as the agent policy. They are required scientific comparators in the later agent evaluation.

`stock_native` versus custom `native` verifies the fork; `policy_noop` versus `native` estimates observation cost; canonical always-continue `policy_agent` versus `policy_noop` estimates placeholder interpreter cost; learned `policy_agent` versus `native` measures deployment benefit or harm. Once policies can stop, agent versus no-op combines evaluation cost and decision effects and is not labelled pure interpreter overhead. Report these comparisons without subtracting estimated overhead from the principal end-to-end metric.

Prove that the no-op path returns the same answers and, under deterministic replay settings, the same expansion/distance-evaluation sequence as native. For stock equivalence, use compatible index snapshots and inspect the minimal source diff. Ordinary timing noise is handled statistically; persistent changes in work or routing are investigated rather than dismissed as noise.

## 7. Engine integrations and feasibility gates

### 7.1 PostgreSQL + pgvector — investigate first

Start from PostgreSQL 17 and pgvector 0.8.6, the current harness family; pin the actual PostgreSQL patch version and all source revisions. Inspect `hnswscan.c`, the implementation of `HnswSearchLayer`, the executor's predicate evaluation, ordering, and `LIMIT` interaction. Pgvector normally returns candidates to PostgreSQL, which applies the scalar filters afterward. [pgvector scan source](https://github.com/pgvector/pgvector/blob/v0.8.6/src/hnswscan.c), [PostgreSQL index executor](https://github.com/postgres/postgres/blob/REL_17_STABLE/src/backend/executor/nodeIndexscan.c)

Implementation sequence:

1. Add query-scoped work counters and safe early-stop checkpoints to the HNSW layer-zero search. Keep insertion/index-building calls outside the policy path.
2. Expose mode and installed policy hash through transaction-local settings. Reset all state after query completion, cancellation, and connection reuse.
3. Make the scan finalize the candidates already found when stopping. Confirm strict ordering, filter evaluation, and SQL `LIMIT` remain valid; distinguish stopping index work from merely ceasing client result fetching.
4. Prototype a query-local feedback channel from the executor for predicate results already evaluated. Determine which observations are available during the initial HNSW batch and later iterative batches.
5. If qualifying statistics are insufficient, compare a narrow executor instrumentation patch with a custom scan wrapper. Select the least invasive design that preserves the native candidate sequence and provides usable observations. Do not assume a normal pgvector-only extension can supply arbitrary executor feedback.
6. Evaluate tuple visibility under the active snapshot. Handle deleted/nonvisible tuples, rescan, zero matches, and fewer-than-k matches. Counting a raw index TID as a qualifying row is invalid.
7. Keep PostgreSQL planning intact in the principal profile. Record sequential, scalar-index, bitmap, HNSW, and relevant sort/limit paths from the actual execution. Provide lightweight executed-path metadata; separately collected `EXPLAIN` is supporting evidence only.

Gate: through an ordinary SQL query, show a no-op policy with unchanged native results/work; show a fixed policy stopping actual HNSW computation earlier; show valid filtered results; and establish useful, honestly timed common features. If this needs a different traversal or a new prefiltering algorithm to work, it has failed the current stopping-only design and needs a revised proposal. A count-only callback without a usable filter-aware policy path is insufficient.

### 7.2 Elasticsearch + Lucene

Start with the current Elasticsearch 9.5.4 pin if it builds reproducibly; determine its exact Lucene dependency from source. Do not substitute Lucene 10.3.1 merely because its API documentation was inspected. Build the Elasticsearch-integrated route, not only a standalone Lucene demonstration.

Implementation sequence:

1. Trace the actual kNN request, collector manager, vector codec/searcher, filtered traversal, segment merging, and fallback path used by the pinned configuration.
2. Add request-scoped mode/policy selection and a collector/searcher hook for checkpoint observations and stop decisions. Use a normal extension mechanism only if it reaches the needed path; otherwise maintain a bounded source patch.
3. Distinguish intentional `policy_stop` from visit-budget exhaustion, timeout, and incomplete native execution throughout the enclosing query. Preserve native fallback for native conditions.
4. Verify that intentional stopping returns the current valid approximate answer instead of triggering an exact scan. Never falsify timeout or exact-completion metadata to accomplish this. Lucene 10.3.1's enclosing vector query illustrates why this must be inspected: incomplete ANN results can trigger exact fallback. Reverify the behavior in Elasticsearch's actual pinned path. [Lucene enclosing kNN query](https://github.com/apache/lucene/blob/releases/lucene/10.3.1/lucene/core/src/java/org/apache/lucene/search/AbstractKnnVectorQuery.java)
5. Count actual scoring calls as well as collector visits. `KnnCollector` exposes visit accounting, but additional state may require searcher instrumentation. [Lucene collector interface](https://lucene.apache.org/core/10_3_1/core/org/apache/lucene/search/KnnCollector.html)
6. Start integration diagnostics with one immutable segment and one shard. One shard does not imply one HNSW graph: normal indices can have many segments. Freeze and record segment topology.
7. Before release, support multi-segment execution with a request-owned accumulator and serial, deterministic segment scheduling for replay. Define whether a stop applies to the current segment or whole request. The shared v1 action is whole-query ANN stopping: merge all results already found and avoid starting further ANN segment work after acceptance. If this cannot be made faithful, constrain and disclose the shared deployment profile before release rather than mixing segment-local and query-global policies.
8. Validate timed-out and failed-shard responses independently from legitimate ANN policy completion. Preserve exact-route queries and native exact fallbacks in the main workload. [Elasticsearch filtered kNN behavior](https://www.elastic.co/docs/solutions/search/vector/knn)

Gate: an Elasticsearch API request can choose each mode, including on a filtered query with fallback potential; policy stopping reduces measured search work; native/no-op remain equivalent; and the response is valid with an explicit termination reason. A custom collector that is never called by the server, or one that causes a replacement exact scan, fails.

### 7.3 Weaviate

Use Weaviate 1.39.2 as an initial source-inspection candidate, not an already validated deployment pin. Freeze server, client, source SHA, and image digests after build and conformance checks. The source contains search-layer queues, allow-list handling, strategy selection, and distances suitable for instrumentation. [Weaviate HNSW source](https://github.com/weaviate/weaviate/blob/v1.39.2/adapters/repos/db/vector/hnsw/search.go)

Implementation sequence:

1. Add query-scoped policy execution to the existing layer-zero HNSW loop, with normal result finalization on stop and all pools/locks released on every path.
2. Pass mode, policy hash, and trace settings through the actual query transport to the search loop. Keep policy control fields separate from the logical filter.
3. Add the harness adapter, deterministic ID mapping, typed metadata mappings, supplied-vector ingestion, readiness, exact conformance retrieval, query execution, and scoped cleanup.
4. Use explicit HNSW and uncompressed vectors for the first shared profile; disable automatic vectorization. Pin all search and index configuration.
5. Preserve the selected native filter strategy and flat-search cutoff in the main native/agent pair. Instrument every native HNSW strategy reachable under that configuration. An ACORN-style route must not silently fall back to a sweeping-only policy implementation.
6. Use forced sweeping and disabled flat cutoff only as a named controlled configuration, equally applied to its baseline and treatment. The main experiment retains the native decision to perform flat search. [Weaviate filtering strategies](https://docs.weaviate.io/weaviate/concepts/filtering)
7. Verify gRPC deadlines, partial batch ingestion, index readiness, reuse, restart, result transport, and background-work observations on both target CPU architectures.

Gate: the database API—not an isolated Go function—executes all modes; the shared filters pass full eligible-set comparison; stop saves real work; and the no-op path preserves native behavior, including flat-search routing.

### Common evidence package for every engine

Save upstream/source/image identifiers, patch files, reproducible build recipe, common-filter report, fixed-policy query transcript, native/no-op comparisons, checkpoint trace, termination reason, actual path, and measured observation overhead. Include zero-match, selective, broad, and unfiltered cases, plus at least one fixture verified to exercise real ANN traversal. Small fixtures that route entirely to exact search cannot certify the hook.

Complete all three evidence packages before promoting the revised selection or retiring Milvus. Open-source availability alone is not an acceptance criterion.

## 8. Harness implementation work

Extend the existing modules rather than undertake an unrelated rewrite.

| Existing location | Required changes |
|---|---|
| `src/fannbench/models.py`, `filters.py`, `data.py` | Versioned shared profile, typed validation, bounds, exact literal semantics, schema migration |
| `adapters/base.py` | Portable capabilities, conformance operations, policy installation/validation, execution context, structured completion metadata |
| `adapters/pgvector.py`, `elasticsearch.py` | Pass mode/policy identity, collect actual executed-path/termination data, native error handling |
| New `adapters/weaviate.py` | Full lifecycle/query adapter plus filter and ID mapping |
| New `policy/` package | Artifact schema, reference evaluator, verifier, feature definitions, interpreter golden cases |
| New `conformance.py` | Full eligible-set comparison, exact-search comparison, mismatch artifacts |
| New `traces.py` | Checkpoint records, provenance, bounded storage, replay validation |
| `runner.py` | Policy mode matrix, request context, paired schedules, separate evaluation, abort/quiescence handling |
| `oracle.py` | Canonical cosine validation, independent exact checks, corrected tie accounting, reusable bounded caches |
| `results.py`, `statistics.py` | Mode-aware grouping, paired effects, quality/correctness status, overhead and policy coverage |
| `runtime/docker.py`, `runtime/registry.py` | Versioned custom images, multiple Weaviate ports, build-aware resource identity, truthful lifecycle states |
| `docker/`, `pyproject.toml`, `uv.lock` | Build recipes/assets, pinned Weaviate client, removal of Milvus-only dependencies after migration |
| `tests/`, `docs/`, `examples/` | Conformance, engine-hook, pairing, lifecycle, packaging, and method documentation |

Add `harness/engines/{pgvector,elasticsearch,weaviate}/` for source lock files, build instructions, patches, feature mappings, and engine integration tests. Keep downloaded upstream source/build products outside the package. The current workspace has no Git repository: establish version control for the implementation and preserve a current-source baseline before engine modifications; do not make publication to a remote a prerequisite.

The adapter API should accept a separate `ExecutionContext` containing mode, artifact hash, feature profile, experiment profile, and trace level. The `Query` remains a backend-independent logical query. Backends must acknowledge the effective policy hash and mode; a server silently ignoring a requested policy fails the run.

Cache policy artifacts in the server before warmup. Policy changes must not trigger index rebuilds. Resource identity includes dataset/schema/index hashes, engine build, patch hash, architecture, and registry ownership; run identity additionally includes workload, mode, artifact, search settings, and schedule. Native-versus-agent pairs must have identical resource/index identities.

## 9. Correctness and measurement repairs required first

Carry forward the [existing audit](fannbench-audit-2026-09-19.md); switching databases does not resolve the generic findings. Reproduce each relevant issue against the current code and close it with targeted evidence.

| Work package | Required repair |
|---|---|
| Canonical input/oracle | Reject unnormalized canonical input; enforce metadata/ID types and numeric limits; correct boundary-tie recall; verify NumPy/FAISS agreement on nondegenerate fixtures |
| Result validity | Separate transport, execution, correctness, and quality outcomes; reject duplicate/unknown/filter-invalid IDs, malformed lengths, and excessive counts |
| Timeout/partial response | Stop the affected backend workload after unresolved timeout; cancel and verify quiescence or stop the container before proceeding; reject unintended Elasticsearch partial responses |
| Measurement | Move full-dataset evaluation outside the timed stream; cache immutable lookup information within memory limits; report evaluation time separately |
| Lifecycle | Propagate stop failures; namespace resources by registry identity; recover or explicitly rebuild interrupted harness-owned imports; verify required indexes before reuse |
| CLI/artifacts | Fix stderr error handling and exit codes; use collision-resistant, bounded diagnostic filenames including mode/run/query identity |
| Import/provenance | Preserve numeric thresholds without lossy `int(float(...))`; validate MoReVec scale; archive sampling, self-match policy, actual server/client versions, build IDs, hardware and VM settings |

The old Qdrant translation failure becomes a regression case in the common suite. It does not establish that Weaviate passes the same case. Historical audit results remain dated; add current disposition rather than rewriting them as if the original run tested the new system.

Run fast schema/oracle/interpreter tests on every change. Run live conformance and policy-hook integration suites whenever an engine patch, adapter, mapping, or transport changes. Run the full three-engine mode matrix before release. Engine source tests should verify queue/expansion behavior; database tests should verify the same behavior survives planner, executor, API, and lifecycle integration. Include policies that always continue, stop at several fixed checkpoints, and deliberately evaluate invalid arithmetic. Test rescan, cancellation, subsequent connection reuse, and failed artifact installation for leaked state. No positive-performance threshold is required to pass a correctness test.

## 10. Trace capture, replay, and agent integration

### Trace design

Each development trace identifies dataset/index/build, engine, query, mode, predicate, checkpoint schedule, feature profile, and native route. Each checkpoint records counters, available features, result/candidate state needed for validation, and termination information. Keep row IDs and ground-truth labels out of the deployed feature interface.

Collect full traces in explicit development/diagnostic runs. Main latency runs collect only bounded scalar metadata needed to identify the actual path and outcome. Match collection settings within each comparison, and measure the residual instrumentation overhead. Do not time full trace serialization and present it as normal deployment cost.

Replay is limited to the same engine, index, traversal settings, feature semantics, and query. A native trace ends at native termination; it cannot predict a policy that continues past that point. A long-budget reference trajectory is a separately configured run and is not a trace of the lower-budget native baseline.

Test replay by choosing many checkpoint stops, running them live, and comparing returned IDs, distances within declared tolerance, and work counters. Include pgvector buffered-candidate filtering and Elasticsearch segment merging. A replay mismatch must be resolved before using replay for calibration; until then use live execution.

### Preparing for the later learning agent

Provide a stable development interface for loading allowed traces, evaluating a proposed artifact, returning validation feedback, and recording evidence/computation cost. The database integrations use hand-written fixtures first and do not depend on a functioning LLM synthesis pipeline.

Split queries into development/training, validation/calibration, and final test sets before learning. Group related query vectors/filter combinations to avoid trivial leakage. Freeze artifacts and calibration before final testing. Runtime inputs must never include true recall, true answer IDs, or future checkpoints.

Use the same policy language and information budgets for an agent-generated policy, conventional learned policy, hand-written policy, and fixed-budget policy. Per-engine trained policies test whether the synthesis method works in each engine. Executing one frozen policy unchanged in all engines is an additional transfer test; it must not be confused with retraining.

Export the bounded shape model separately from the stopping policy, with evidence and acquisition cost. Preserve the existing research plan's offline learning and held-out evaluation requirements.

## 11. Paired evaluation and reporting

Run one database at a time with one outstanding request, a fixed immutable snapshot, and documented warm-cache conditions. Preserve CPU/memory allocation and thread settings. Randomize balanced native/agent order within query pairs or short blocks; record seed, ordering, and pair ID. Warm both modes and install artifacts before measurement.

For each engine, report:

- Native and agent end-to-end latency, paired differences, and uncertainty.
- Recall@k against the same exact oracle, including distributions, per-query losses, and target failures.
- Result completeness, invalid responses, timeouts, policy errors, and fallbacks.
- Distance computations, expansions, qualifying observations, checkpoint count, and time spent producing features/evaluating policy where measurable.
- Whole-workload effect plus effect among queries where the policy actually ran; exact-route and zero-eligible cases remain visible.
- Observation/runtime overhead from no-op mode and fixed-budget/conventional-policy comparisons.
- Acquisition/calibration cost and amortization when average deployed savings are positive.

Use the principal effect `latency_agent - latency_native`; negative values mean faster treatment. Report recall difference alongside it. Do not describe a faster but below-target policy as an improvement at the target recall.

Repeated measurements of one query and checkpoints within one trajectory are not independent query samples. Compute paired summaries and confidence intervals at the query level, using a grouped bootstrap or another predeclared suitable method. Missing pairs are reported, never silently removed to improve the result. Successful-pair timing statistics must accompany total failure rates.

Report each engine separately before any aggregate. Do not infer policy benefit by subtracting pgvector time from Weaviate time. Do not call sequential request throughput saturation throughput or include offline oracle work in database throughput.

## 12. Proposed CLI and output contract

The doctor, conformance, policy-validation, and run interfaces are implemented. The custom builds passed their one-node gates and all four instrumented modes are available; trace and replay are still planned.

```sh
fannbench doctor --backends pgvector,elasticsearch,weaviate --require-policy

fannbench conformance --backends pgvector,elasticsearch,weaviate \
  --dataset /path/to/manifest.yaml --queries /path/to/queries.jsonl

fannbench policy validate --artifact /path/to/policy.json \
  --backends pgvector,elasticsearch,weaviate

fannbench run --backends pgvector,elasticsearch,weaviate \
  --dataset /path/to/manifest.yaml --queries /path/to/queries.jsonl \
  --modes stock_native,policy_placeholder \
  --config /path/to/experiment.yaml \
  --output /path/to/results

# Target once custom builds are available:
fannbench run --backends pgvector,elasticsearch,weaviate \
  --dataset /path/to/manifest.yaml --queries /path/to/queries.jsonl \
  --modes native,policy_noop,fixed_budget,policy_agent \
  --policy /path/to/policy.json --fixed-budget 4096 \
  --config /path/to/experiment.yaml --output /path/to/results

fannbench trace --backend pgvector --mode native \
  --dataset /path/to/manifest.yaml --queries /path/to/development.jsonl \
  --config /path/to/experiment.yaml --output /path/to/traces

fannbench replay --trace /path/to/trace-manifest.json \
  --policy /path/to/policy.json --validate-live
```

Version result schemas so old reports cannot be pooled accidentally. Add engine build/patch identity, effective mode/policy hash, profile versions, index identity, pair ID, executed path, policy-applied flag, stop reason, actual checkpoint count, work counters with availability, and correctness/quality statuses.

Archive `manifest.json`, raw `measurements.jsonl`/Parquet, `conformance.json`, `builds.json`, preparation/readiness records, `paired-effects.csv`, mode summaries, and optional trace manifests. Summaries group by engine, mode, experiment profile, and artifact; never mix modes under a single backend row. Policy artifacts and evaluation splits accompany the final bundle.

## 13. Delivery sequence, estimates, and decision gates

Estimates below are engineering person-days for an experienced developer, not elapsed-time promises or measured build effort. Work may overlap where independent, but the gates are sequential. Three engine integrations materially expand the earlier one-engine semester scope.

| Milestone | Work and artifact | Dependencies | Estimate | Exit gate |
|---|---|---|---|---|
| M0: specification and reproducibility | Versioned contract, baseline snapshot/version control, build/source inventory, actual Lucene dependency, feasibility fixtures | None | 2–3 days | Requirements and native/treatment semantics executable as checks |
| M1: trustworthy substrate | Audit repairs, exact oracle validation, typed canonical inputs, failure/lifecycle handling | M0 | 5–8 days | Correctness failures cannot produce a successful comparison |
| M2a: pgvector feasibility | SQL-to-HNSW stop demonstration, executor feature assessment, no-op equivalence | M0; uses repaired oracle from M1 | 5–8 days | Stop, usable features, filtered finalization, and faithful baseline proven |
| M2b: Elasticsearch feasibility | Server collector/searcher integration, intentional-stop/fallback behavior, segment design | M0; M1 verification | 4–7 days | API-level stop reduces work without unintended exact fallback |
| M2c: Weaviate feasibility | Query-to-search-loop hook, typed filter/ID proof, native strategy checks | M0; M1 verification | 3–5 days | API-level policy and common filters work |
| M3: shared runtime | Frozen feature contract, C/Java/Go evaluators, artifact installation, golden cases, all modes | All M2 gates | 6–10 days | Same artifact/input semantics on all three engines |
| M4: harness and migration | Full Weaviate adapter, mode-aware runner/results, packaged builds, retire active Milvus backend | M1–M3 | 4–6 days | One command compares all modes on all three databases |
| M5: replay and evaluation | Checkpoint capture, live/replay tests, paired schedules, statistics, calibration interface | M3–M4 | 5–8 days | Measured policy effect and overhead are attributable and reproducible |
| M6: release qualification | Real-data pilot, architecture checks, failure/restart/reuse tests, clean install and documentation | M1–M5 | 4–6 days | Complete reproducible bundle satisfying both hard requirements |

Total planning range: **38–61 engineering days**, roughly 8–13 full-time engineering weeks before open-ended agent-method research. Upstream build problems or invasive PostgreSQL changes can exceed this range. Reserve contingency and revise the schedule after M2 rather than promising all three as a minor adapter change.

Start the engine investigation with pgvector because predicate feedback is the largest uncertainty. Time-box each spike to its range. At its limit, produce a concrete feasibility result and smallest remaining blocker; do not spend another month on an undefined hook. A failed spike triggers a revised proposal that still satisfies both requirements. Reducing to two systems or leaving one as baseline-only requires an explicit scope decision.

Milvus retirement happens only at M4 after all M2 gates and the shared runtime pass. Preserve old run readability and scoped cleanup for legacy Milvus resources, or provide a documented cleanup tool retaining their exact ownership/configuration. Do not automatically delete existing volumes. Remove active Milvus defaults, adapter registration, dependencies, packaged configuration, and wheel assets together; do not redirect the name `milvus` to another engine.

Update the README, compatibility/methodology/formats documents, examples, and earlier plan/audit status notes to point to this revision. Preserve historical audit evidence and label superseded recommendations. Record current validated status separately from the target state.

## 14. Release acceptance checklist

The revision is complete only when all of the following have evidence:

- [ ] All three systems have pinned, rebuildable source and images with recorded patch/toolchain identities.
- [ ] The global portable profile rejects incompatible data/queries before resource preparation, regardless of selected backend subset.
- [ ] Each system matches exact eligible ID sets and the declared exact nearest-neighbor objective on adversarial and generated conformance cases.
- [ ] Every system runs native, no-op, fixed-budget, and actual artifact modes through its real database query interface.
- [ ] One portable frozen policy artifact executes in all three; feature definitions and interpreter decisions pass common test vectors.
- [ ] Stock/custom-native and native/no-op comparisons establish behavioral fidelity on real ANN paths.
- [ ] An intentional stop reduces search work in a suitable case without replacing the search, silently changing filters, or triggering unintended fallback.
- [ ] The intended filter-aware features are actually available at usable checkpoints; their cost is measured.
- [ ] Native planning and exact routes remain represented in whole-workload native-versus-policy comparisons.
- [ ] Policy identity, actual path, stop reason, errors, and quality failures are recorded for every applicable sample.
- [ ] Trace replay reproduces live stopping under the declared profile, or replay is explicitly unavailable and calibration uses live runs.
- [ ] No oracle labels, final-test answers, or future observations enter runtime policy inputs.
- [ ] Paired reports include latency, recall, failures, overhead, and coverage without hiding negative results.
- [ ] MoReVec small and medium runs use verified real artifacts and preserve source, sampling, and self-match provenance.
- [ ] Supported ARM64 and x86-64 builds pass qualification, or the release explicitly supports only the validated architecture without claiming the other.
- [ ] Clean installation, packaged assets, interrupted ingest, restart, timeout, connection reuse, and scoped cleanup are verified.
- [ ] Active documentation agrees on the three required systems and distinguishes implemented capability from proposed work.

These gates certify that the infrastructure can evaluate the future agent fairly. They do not require the agent to outperform native execution; a measured detriment or no improvement is a valid outcome.
