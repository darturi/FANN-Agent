# FANNBench execution-path observability plan

Date: 20 September 2026  
Applies to: FANNBench 0.4.0 and the pinned PostgreSQL/pgvector, Elasticsearch/Lucene, and Weaviate versions

## Execution status

Revised and live-qualified on 20 September 2026. Measurement, summary,
diagnostic, and run manifest schemas are now version 4. Stock modes explicitly
report unobserved route and stop metadata. The typed build catalog selects stock
or instrumented images without mixing the two mode families. All three
instrumented engines implement `same_execution_v2`: native bypasses agent
observation, no-op collects the complete feature snapshot without evaluation,
and agent mode evaluates a preinstalled hash-addressed policy. See
[`fannbench-three-path-overhead-isolation-plan-2026-09-20.md`](fannbench-three-path-overhead-isolation-plan-2026-09-20.md).

The common live route fixture passed for pgvector, Weaviate, and
Elasticsearch: 32 measurements per engine across `native`, `policy_noop`,
`fixed_budget`, and `policy_agent`. It deliberately exercised HNSW and
non-HNSW/flat/exact paths. Native, no-op, and canonical always-continue agent
results matched; no-op and agent observations matched; and fixed-budget stops
reduced work when a checkpoint opportunity existed. Separate stop-policy
qualification remains covered by the engine hook tests.

Build artifacts and locks are under `harness/engines/`. The recorded custom
images are pgvector `sha256:a1968116...`, Weaviate `sha256:a63daf97...`, and
Elasticsearch `sha256:2cb70c05...`. The Elasticsearch profile is deliberately
one node and one shard; distributed shard telemetry reduction remains outside
the current experiment profile. The sections below retain the design rationale
and implementation sequence that produced this result.

## 1. Objective

Make every timed measurement truthful about what is and is not known concerning the database's execution route and termination reason.

The immediate objective is to stop describing stock requests as HNSW executions when the stock API did not report that fact. The final objective is for each custom database build to return route, termination, policy application, and work counters from the same execution that produced the measured result.

This work must support both native planner behavior and the later policy experiment. Exact, flat, fallback, and non-policy routes remain valid workload outcomes. They must be reported accurately rather than forced out of the main experiment merely to simplify instrumentation.

## 2. Original gap (closed)

Before schema 3, the stock adapters assigned these values locally after receiving results:

| Backend | Current local path label | Current local stop reason |
|---|---|---|
| PostgreSQL/pgvector | `stock_pgvector_hnsw` | `native_limit` |
| Elasticsearch/Lucene | `stock_elasticsearch_lucene_hnsw` | `native_limit` |
| Weaviate | `stock_weaviate_hnsw` | `native_limit` |

The timed responses did not establish those facts. PostgreSQL can choose a non-HNSW plan, Elasticsearch can use exact fallback in some segments, and Weaviate can use flat search for filtered queries. Schema 3 now reports these stock fields as unobserved. A separate `EXPLAIN` or profile request still describes a separate execution and is not copied into a timed record as proof.

The `effective_mode` value for `stock_native` and `policy_placeholder` remains acknowledged by the adapter rather than by the unmodified server, and schema 3 records that source explicitly.

## 3. Required semantics

### 3.1 Observation sources

Add a strict source enum:

```text
adapter_declared
server_observed
unobserved
```

Use distinct fields because mode acknowledgement and route telemetry can have different sources:

```text
mode_acknowledgement_source
route_observation_source
stop_reason_source
```

Meanings:

- `adapter_declared`: the harness selected the label, but the server did not acknowledge it.
- `server_observed`: the timed server execution emitted the value.
- `unobserved`: no trustworthy value exists for the timed execution.

A separate diagnostic execution never qualifies as `server_observed` for a timed sample.

### 3.2 Execution paths

Use a versioned enum rather than arbitrary strings. Initial values:

```text
stock_route_unobserved
postgresql_pgvector_hnsw
postgresql_non_hnsw
elasticsearch_lucene_hnsw
elasticsearch_lucene_exact
elasticsearch_lucene_mixed
weaviate_hnsw_sweeping
weaviate_hnsw_acorn
weaviate_flat
weaviate_mixed
```

`postgresql_non_hnsw` means the pgvector HNSW hook was not reached. It does not claim whether PostgreSQL used a sequential scan, another index, or a different exact plan unless same-execution executor telemetry proves that narrower statement.

`mixed` is required because an Elasticsearch request can use different routes across segments or shards, and a future distributed Weaviate request may aggregate different routes. Per-component details belong in structured diagnostics or counters; the top-level path must not hide mixed execution.

### 3.3 Stop reasons

Add `native_reason_unobserved` to the stop-reason enum. Retain the existing observed reasons:

```text
native_convergence
native_limit
policy_stop
fixed_budget_stop
exhausted
timeout
cancelled
error
```

An adapter may report `native_reason_unobserved` for a successful stock response. Instrumented modes must receive an observed reason from the server. `policy_stop` and `fixed_budget_stop` are valid only when the same server execution confirms that the corresponding stopping action occurred.

### 3.4 Policy opportunity

Add explicit fields:

```text
policy_opportunity: true | false | null
policy_applied: true | false
```

- `true`: the request reached an instrumented search loop at at least one valid checkpoint.
- `false`: the server confirmed that the request followed a route where the policy could not run.
- `null`: the stock server did not expose enough information.

Define `policy_applied` narrowly: it means that the requested policy evaluator ran at least once. It does not mean that the policy stopped the search or improved the result. Thus:

- `native` always reports `policy_applied=false`, even if checkpoints were available;
- `policy_noop` reports `observation_applied=true` after feature collection and always reports `policy_applied=false`;
- `policy_agent` reports `policy_applied=true` only after at least one evaluation;
- `fixed_budget` reports `policy_applied=false` because it is a control mechanism rather than an agent policy;
- `policy_stop` additionally proves that the evaluated agent policy changed termination;
- `policy_evaluation_count` is carried as a required work counter whenever `policy_applied=true`.

`policy_applied=true` requires `policy_opportunity=true`, a server-observed instrumented mode, and a valid policy hash for `policy_agent`.

## 4. Result-schema migration

This changes the meaning of existing output fields, so issue a new schema rather than silently mixing results.

1. Bump the package to 0.3.0.
2. Bump run manifests, measurements, summaries, and diagnostics to schema version 3.
3. Add the three observation-source fields and `policy_opportunity` to `ExecutionMetadata` and `Measurement`.
4. Change `executed_path` and `stop_reason` to strict enums.
5. Preserve schema-2 readers for historical results, but never pool schema 2 and schema 3 automatically.
6. Record a migration note explaining that schema-2 stock path and stop labels were adapter assertions and must not be used for route-specific analysis.

Validation rules:

- `policy_placeholder` must have adapter-declared mode, no policy hash, `policy_applied=false`, and `policy_opportunity=null` unless the server independently reports the route.
- Stock builds must not report server-observed mode, path, stop reason, counters, or checkpoints unless the specific stock API returned them from the timed request.
- `native`, `policy_noop`, `fixed_budget`, and `policy_agent` require server-observed mode acknowledgement.
- Work counters and checkpoint counts require `route_observation_source=server_observed`.
- `policy_stop` requires `policy_applied=true` and a server-observed reason.
- A mixed route may set `policy_opportunity=true` if at least one component reached the hook, while component counts must disclose coverage.

## 5. Phase A: immediate truthful stock behavior

This phase requires no database fork and should happen before additional benchmark runs.

### Implementation

1. Add the new enums and schema-3 fields.
2. Change every stock adapter to return:

```json
{
  "mode_acknowledgement_source": "adapter_declared",
  "route_observation_source": "unobserved",
  "stop_reason_source": "unobserved",
  "executed_path": "stock_route_unobserved",
  "stop_reason": "native_reason_unobserved",
  "policy_opportunity": null,
  "policy_applied": false
}
```

3. Keep `stock_native` and `policy_placeholder` effective-mode labels because the harness controls their paired scheduling, but explicitly identify their acknowledgement as local.
4. Remove integration assertions that merely check for a `stock_*hnsw` string. Assert the exact unobserved contract instead.
5. Add a summary field counting samples by observation source and route. Stock route coverage should appear as unknown rather than zero.
6. Add an experiment-report warning whenever route-specific analysis is unavailable.

### Tests

- Each stock adapter produces the unobserved contract.
- A stock adapter cannot construct server-observed counters or checkpoints accidentally.
- Placeholder samples cannot carry a policy hash, policy opportunity, application, fallback, or runtime error.
- Instrumented modes are rejected when their acknowledgement is not server-observed.
- Schema-2 fixtures remain readable but are marked legacy and route-untrusted.
- All existing three-engine filter, recall, pairing, timeout, and packaging tests continue to pass.

### Exit gate

No new result claims HNSW, an exact route, a stop reason, or a policy opportunity unless the timed server execution supplied that fact.

## 6. Phase B: preserve separate diagnostics without confusing them with timed telemetry

Diagnostics remain useful for feasibility work, but they need explicit provenance.

1. Add `execution_relation: separate_execution` to every diagnostic artifact.
2. Record whether profiling changes the request, such as Elasticsearch's profile flag or PostgreSQL `EXPLAIN` wrapper.
3. Store a diagnostic path assessment separately from measurement fields.
4. Never backfill a timed measurement from a diagnostic result.
5. Use query ID, mode, configuration hash, and a diagnostic execution ID to make the relationship auditable.

Exit gate: a consumer cannot mistake a separate plan/profile execution for telemetry from the timed request.

## 7. Phase C: PostgreSQL/pgvector same-execution telemetry

### Proposed design

Use transaction-local request context plus backend-local last-execution telemetry in the custom pgvector build.

The adapter executes, on the same persistent connection and in one transaction:

1. `fannbench_begin_execution(context_json)` to clear prior state and install the requested mode, artifact identity, budget, and trace level.
2. The normal filtered nearest-neighbor SQL query.
3. `fannbench_last_execution()` to retrieve telemetry from that exact query.
4. Commit or rollback, with cleanup on error and cancellation.

The pgvector HNSW scan records that its layer-zero loop was reached, the selected mode, checkpoints, distance evaluations, stop action, and termination reason. If the hook is not reached, the wrapper returns `postgresql_non_hnsw`, `policy_applied=false`, and `policy_opportunity=false`; it does not guess the narrower PostgreSQL plan.

### Critical feasibility questions

- Can transaction-local context be installed and cleared safely across errors, rescans, prepared statements, and pooled connection reuse?
- Can the final telemetry be read after the query without altering tuple order or forcing a second execution?
- Can the extension distinguish one query from another when PostgreSQL rescans a plan node?
- Can filtered-result features be obtained at actionable checkpoints without replacing PostgreSQL's normal predicate processing?

### Acceptance tests

- A controlled HNSW query reports `postgresql_pgvector_hnsw` from the server and reaches checkpoints.
- A deliberately non-HNSW query reports `postgresql_non_hnsw` and `policy_opportunity=false`.
- Native and no-op modes return identical results and traversal counters under deterministic controls.
- Fixed-budget mode reduces actual layer-zero work.
- Cancellation and connection reuse leave no mode, policy, or counters in the next request.
- A policy stop returns the candidates already available and does not restart as an exact scan.

## 8. Phase D: Elasticsearch/Lucene same-execution telemetry

### Proposed design

Add a versioned FANNBench request extension or equivalent custom request field. Carry it into every shard and segment search context. Instrument the Lucene kNN path where the actual choice between graph traversal and exact fallback is known.

Each shard returns structured execution metadata in a response extension. The coordinating node validates and aggregates it:

- all approximate segments: `elasticsearch_lucene_hnsw`;
- all exact segments: `elasticsearch_lucene_exact`;
- any combination: `elasticsearch_lucene_mixed`.

Counters include component totals and coverage counts so `mixed` is analytically useful. A deliberate policy stop must be represented as a completed approximate result and must not be treated as native incompleteness that triggers an exact fallback.

### Critical feasibility questions

- Which pinned Elasticsearch request-extension point reaches the kNN query and survives shard serialization?
- Where does the pinned Lucene version decide exact fallback, and can the policy-stop state bypass only unintended fallback without disabling legitimate native routing?
- How should segment-level stop reasons aggregate when some segments converge natively and others stop by policy?
- Can telemetry be returned without enabling the expensive profile API?

### Acceptance tests

- Tests force all-HNSW, all-exact, and mixed segment routes and verify the top-level aggregation.
- Mode and policy hash survive transport to every shard.
- `policy_applied` and opportunity counts match the segments that reached checkpoints.
- Native and no-op modes match in results and work.
- Fixed-budget mode reduces vector evaluations without causing a replacement exact search.
- Timed-out or failed shards remain errors regardless of telemetry.

## 9. Phase E: Weaviate same-execution telemetry

### Proposed design

Carry a versioned execution context from the normal GraphQL request into vector search. Return request-level telemetry through a custom top-level GraphQL response extension or another single response structure, rather than duplicating it on every result object.

Instrument all routes reachable under the configured filter strategy and flat cutoff:

- sweeping HNSW;
- ACORN HNSW;
- flat search;
- mixed execution if the pinned implementation can combine routes.

The flat path reports `policy_opportunity=false` for an HNSW-only policy. Each HNSW path reports whether checkpoints were reached and whether the policy acted.

### Critical feasibility questions

- Where is filter-strategy and flat-cutoff routing finalized in the pinned source?
- Can request context propagate through pools and goroutines without leaking into another request?
- Can all early returns release visited lists, locks, and pooled buffers after policy stop?
- Is there a stable response-extension location that the adapter can validate without changing result ranking?

### Acceptance tests

- Controlled queries force sweeping HNSW, ACORN HNSW, and flat routes.
- Route labels come from the timed server response.
- Flat routes report no HNSW policy opportunity.
- Native and no-op modes preserve results and work for each route.
- Fixed-budget and agent stops reduce HNSW work and release all pooled resources.
- Filter-eligible IDs remain identical to the independent evaluator in every strategy.

## 10. Aggregation and analysis rules

Update summaries so route information cannot be silently averaged away.

For every backend and mode report:

- count and fraction by observed route;
- count with route unobserved;
- policy-opportunity count and fraction;
- policy-applied count and fraction;
- policy errors and fallbacks;
- latency and recall for the whole workload;
- latency and recall for each observed route;
- paired policy effects for the whole workload;
- paired effects among pairs where both requests used a comparable policy-eligible route.

The comparable-route subset is secondary. The principal result remains the whole native-planner workload, because a policy that changes routing or applies rarely still has that deployment behavior. Never discard non-HNSW samples from the whole-workload result.

## 11. Route-specific qualification dataset

The current 160-row smoke fixture is too small to prove ANN routing. Add a dedicated opt-in route fixture with enough rows and selective filters to exercise route decisions.

It should include:

- an unfiltered or broad-filter query suitable for HNSW;
- a moderately selective filter;
- a highly selective filter suitable for flat/exact fallback;
- a zero-match filter;
- fewer-than-k eligible rows;
- repeated queries for deterministic no-op comparisons.

Use controlled test configurations to prove that each instrumentation branch is reachable. Keep those results separate from the main native-planner experiment, where routing remains unconstrained.

## 12. Delivery sequence and estimates

| Milestone | Deliverable | Estimate | Exit gate |
|---|---|---:|---|
| O0 | Freeze enums, sources, aggregation rules, and schema-3 migration | 0.5–1 day | Contract reviewed and test fixtures written |
| O1 | Truthful stock/placeholder metadata and legacy-reader behavior | 1–2 days | No unsupported HNSW or stop claims remain |
| O2 | Diagnostic provenance separation | 0.5–1 day | Timed and diagnostic executions cannot be confused |
| O3 | pgvector same-execution route prototype | 2–4 days | HNSW reached versus not reached is server-observed |
| O4 | Weaviate route prototype | 2–3 days | HNSW strategy versus flat is server-observed |
| O5 | Elasticsearch/Lucene route prototype | 3–5 days | HNSW/exact/mixed is aggregated from shards/segments |
| O6 | Cross-engine route fixture, reports, packaging, and regression suite | 2–3 days | All route and observation-source acceptance tests pass |

The immediate honesty repair is approximately 1.5–3 engineering days including schema migration and tests. Full same-execution route telemetry is approximately 8–14 additional engineering days and overlaps substantially with the later source-level stopping-policy work. Estimates are planning ranges; pinned-source feasibility can change them.

## 13. Definition of done

This gap is resolved when all of the following are true:

- Stock and placeholder results make no unsupported route or termination claim.
- Every execution fact records whether it came from the adapter, timed server execution, or was unobserved.
- A separate diagnostic execution cannot populate timed telemetry.
- Every custom engine acknowledges the requested instrumented mode from the server.
- Every timed custom response reports HNSW, exact/flat/non-HNSW, or mixed route from the execution that produced the results.
- Policy opportunity is distinct from policy application.
- Non-policy routes remain visible in whole-workload results.
- Deliberate policy stopping cannot trigger a hidden replacement exact search.
- Route-specific tests exercise every supported route on every pinned build.
- Historical schema-2 stock path labels are documented as route-untrusted and are never pooled automatically with schema-3 results.

## 14. Repository-specific implementation blueprint

### 14.1 Freeze the contract before changing adapters

Add `src/fannbench/schema.py` and make it the only source of output-schema constants:

```text
RUN_SCHEMA_VERSION = 3
MEASUREMENT_SCHEMA_VERSION = 3
SUMMARY_SCHEMA_VERSION = 3
DIAGNOSTIC_SCHEMA_VERSION = 3
EXECUTION_OBSERVABILITY_CONTRACT = "same_execution_v2"
```

Do not change unrelated format versions. Dataset manifests, queries, policy artifacts, conformance reports, preparation reports, and the resource registry have separate schemas and remain at their existing versions unless their own structure changes.

In `src/fannbench/models.py`:

1. Add `ObservationSource` with `adapter_declared`, `server_observed`, and `unobserved`.
2. Add `ExecutionPath` with the values in section 3.2.
3. Add `StopReason.NATIVE_REASON_UNOBSERVED`.
4. Add `mode_acknowledgement_source`, `route_observation_source`, `stop_reason_source`, and `policy_opportunity` to `ExecutionMetadata`.
5. Change `executed_path` from free text to `ExecutionPath`.
6. Change `Measurement.schema_version` to 3 and mirror the new execution fields there.
7. Keep execution fields nullable on error and timeout measurements because no successful response was decoded. Require all source fields, path, and stop reason on successful measurements.
8. Encode the mode invariants in one model validator rather than distributing them across adapters.

The validator matrix is:

| Requested/effective mode | Mode source | Route and stop source | Policy opportunity | Policy applied |
|---|---|---|---|---|
| `stock_native` | `adapter_declared` | `unobserved` | `null` | `false` |
| `policy_placeholder` | `adapter_declared` | `unobserved` | `null` | `false` |
| `native` | `server_observed` | `server_observed` | `true` or `false` | `false` |
| `policy_noop` | `server_observed` | `server_observed` | `true` or `false` | observation true after a snapshot; policy always false |
| `fixed_budget` | `server_observed` | `server_observed` | `true` or `false` | `false` |
| `policy_agent` | `server_observed` | `server_observed` | `true` or `false` | true only after an evaluation |

Additional invariants:

- `stock_route_unobserved` requires unobserved route and stop sources.
- Every other path requires `route_observation_source=server_observed`.
- `native_reason_unobserved` requires `stop_reason_source=unobserved`.
- Observed stop reasons require `stop_reason_source=server_observed`.
- Nonempty work counters and non-null checkpoint counts require a server-observed route.
- `policy_opportunity=false` requires zero checkpoints and zero policy evaluations.
- `policy_applied=true` requires a positive `policy_evaluation_count`.
- `policy_stop` requires `policy_agent`, `policy_applied=true`, and a valid effective policy hash.
- `fixed_budget_stop` requires `fixed_budget` mode.
- `policy_noop` cannot report `policy_stop`.

Update the package version in `pyproject.toml` and `src/fannbench/__init__.py` together. Add a unit test that fails if they diverge.

### 14.2 Preserve schema-2 results without trusting them

The harness currently writes results but has no general result-bundle reader. Add the reader while performing this migration so historical bundles have an explicit interpretation.

In `src/fannbench/results.py`:

1. Add `read_measurements(path, *, allow_legacy=False)`.
2. Parse schema 3 directly into `Measurement`.
3. Reject schema 2 by default with a message explaining that stock route labels were adapter assertions.
4. When `allow_legacy=True`, return a legacy envelope that retains the original record and adds:

```json
{
  "source_schema_version": 2,
  "route_metadata_trusted": false,
  "legacy_interpretation": "adapter_asserted_route_and_stop"
}
```

5. Do not silently rewrite a legacy HNSW label to an observed schema-3 HNSW route.
6. Refuse to pass schema-2 and schema-3 records together to `summarize`.

Add a short migration note to `docs/formats.md`. Historical latency, recall, failures, and returned IDs remain usable. Historical route-specific coverage, route-specific performance, stop-reason counts, and policy-opportunity analysis do not.

### 14.3 Centralize stock execution metadata

Add a helper in `src/fannbench/adapters/base.py`:

```text
stock_execution_metadata(context) -> ExecutionMetadata
```

It returns the complete unobserved contract from section 5. Replace the handwritten `ExecutionMetadata` construction in:

- `src/fannbench/adapters/pgvector.py`;
- `src/fannbench/adapters/elasticsearch.py`;
- `src/fannbench/adapters/weaviate.py`.

This avoids three slightly different interpretations of stock behavior. The helper must accept only `stock_native` and `policy_placeholder`; passing an instrumented mode is an error.

### 14.4 Propagate and validate the new metadata

In `src/fannbench/runner.py`:

1. Copy all new fields from `SearchResult.execution` into successful `Measurement` records in `_measure_raw`.
2. Leave response-derived execution fields absent for exceptions and timeouts.
3. Replace the current generic “server acknowledged mode” check in `_evaluate_measurement` with source-aware validation:
   - adapter acknowledgement is permitted only for stock and placeholder;
   - custom modes require server acknowledgement;
   - a missing or contradictory custom acknowledgement invalidates the sample;
   - an unobserved stock route remains valid but unavailable for route analysis.
4. Put `execution_observability_contract: same_execution_v2` in the run manifest.
5. Bump only the run manifest to schema 3 in this file. Keep preparation and conformance versions unchanged.
6. Add manifest-level counts of successful samples with observed and unobserved routes after measurements are finalized.

In `src/fannbench/results.py`:

1. Serialize the new fields to JSONL and Parquet.
2. Continue encoding `work_counters` as deterministic JSON for Parquet.
3. Add a visible limitation to `experiment.md` when any successful sample has an unobserved route.
4. State that placeholder comparisons exercise scheduling and reporting only.

## 15. Reporting changes

### 15.1 Summary coverage

In `src/fannbench/statistics.py`, add these scalar fields to every per-query and per-backend row:

```text
observed_route_samples
unobserved_route_samples
policy_opportunity_samples
policy_no_opportunity_samples
policy_opportunity_unobserved_samples
policy_applied_samples
policy_stopped_samples
```

Add `route_counts` and `stop_reason_counts` maps to JSON summaries. When producing CSV, encode those maps in stable JSON columns named `route_counts_json` and `stop_reason_counts_json` rather than relying on Python dictionary formatting.

An unknown route counts as unknown coverage. It must never be converted to zero HNSW executions or zero policy opportunities.

### 15.2 Paired effects

Retain the existing whole-workload paired comparison as the primary result. Add a secondary `paired_effects_comparable_route` table with the following admission rule:

1. both pair members succeeded and passed correctness checks;
2. both have `route_observation_source=server_observed`;
3. both have the same `ExecutionPath` value;
4. both agree on whether a policy opportunity existed;
5. that opportunity is true for policy-effect analysis.

Report candidate, admitted, route-mismatch, route-unobserved, invalid, and missing pair counts. Never substitute the secondary table for the whole-workload result. A policy that is rarely eligible or changes routing still has that whole-workload deployment outcome.

### 15.3 Command-line presentation

Extend the `fannbench run` result table in `src/fannbench/cli.py` with a compact `Route observed` column such as `78/81`. Do not print a guessed route name. The detailed route distribution stays in `summary.json` and `summary.csv`.

## 16. Diagnostic provenance implementation

Change `Adapter.collect_diagnostic` in `src/fannbench/adapters/base.py` to accept the `ExecutionContext`. Update all three adapters accordingly. This fixes the current behavior where the runner loops over modes but does not pass the mode into the diagnostic request.

Each diagnostic record written by `src/fannbench/runner.py` receives:

```json
{
  "schema_version": 3,
  "diagnostic_execution_id": "a unique UUID",
  "execution_relation": "separate_execution",
  "requested_mode": "native",
  "profile_changes_execution": true,
  "timed_measurement_id": null
}
```

`profile_changes_execution` is true for Elasticsearch profiling and PostgreSQL `EXPLAIN ANALYZE` if it is ever enabled. A plain PostgreSQL `EXPLAIN` should state that it plans rather than executes. Weaviate's unavailable diagnostic still gets the same provenance envelope.

Do not add a mechanism that copies diagnostic routes into `Measurement`.

## 17. Engine-build and runtime selection

The current runtime has one hard-coded image per backend. Same-execution telemetry requires explicit stock and instrumented build identities.

### 17.1 Build catalog

Replace the flat entries in `src/fannbench/engine_builds.py` with a typed catalog keyed by backend and variant:

```text
pgvector.stock
pgvector.instrumented
elasticsearch.stock
elasticsearch.instrumented
weaviate.stock
weaviate.instrumented
```

Each entry records image digest, upstream commit, patch digest, protocol version, supported modes, and build status. An instrumented entry is unavailable until its image digest and patch digest are present.

Mode selection determines the variant:

- `stock_native` and `policy_placeholder` use the stock build;
- `native`, `policy_noop`, `fixed_budget`, and `policy_agent` use the instrumented build;
- a single backend run cannot mix stock and instrumented modes.

The decisive experiment is `native` versus `policy_agent` inside one instrumented binary and one physical index. `stock_native` versus an instrumented mode is not a valid estimate of policy effect because the binaries differ.

### 17.2 Docker runtime

In `docker/compose.yaml`, parameterize each service image with a backend-specific environment variable. In `src/fannbench/runtime/docker.py`:

1. resolve the selected build before starting the service;
2. inject its immutable image digest into Compose;
3. remove the duplicate `IMAGES` source of truth;
4. include variant, image digest, upstream commit, patch digest, and architecture in the resource configuration hash;
5. prevent an indexed volume created by one build variant from being reused by another;
6. record the resolved build in the run manifest.

Update `fannbench doctor --require-policy` to check that all selected instrumented variants have immutable images and declare `same_execution_v2`, rather than checking only for the string `policy_agent`.

## 18. Engine implementation work packages

### 18.1 PostgreSQL/pgvector first

Use the pinned pgvector v0.8.6 source. Implement a backend-local execution state with a random request nonce.

Add SQL-callable functions in the patched extension:

```text
fannbench_begin_execution(context_json) -> request_nonce
fannbench_last_execution(request_nonce) -> telemetry_json
```

The adapter performs begin, the normal nearest-neighbor query, and telemetry retrieval on the same persistent connection and in one transaction. Transaction and resource-owner callbacks clear state on commit, rollback, error, and cancellation. The nonce prevents stale telemetry from being attributed to a later request.

Patch the layer-zero path around `HnswSearchLayer` and resumable scan handling in `src/hnswscan.c`. Record at minimum:

- whether the hook was reached;
- layer-zero and upper-layer distance evaluations;
- checkpoint and policy-evaluation counts;
- configured and actual stop boundary;
- termination reason;
- requested and effective mode;
- requested and effective policy hash.

If the hook was not reached after a successful SQL query, return `postgresql_non_hnsw` and `policy_opportunity=false`. Do not infer a narrower PostgreSQL plan.

The three-control-request wrapper adds overhead. Use the identical wrapper for `native`, `policy_noop`, `fixed_budget`, and `policy_agent`, and compare those modes with one another. Record server query timing separately if exposed, while retaining existing end-to-end latency as the primary operational measure.

Deliverables under `engines/pgvector/`:

- a patch file rather than an edited vendor tree;
- build script and Dockerfile;
- updated source lock with patch and image digests;
- upstream unit/regression tests;
- cancellation, rescan, and connection-reuse test script;
- protocol transcript showing both HNSW and non-HNSW responses.

### 18.2 Weaviate second

Use the pinned Weaviate v1.39.2 source. Carry a versioned context from the public request into the vector-search call. Prefer a GraphQL top-level `extensions.fannbench` response. If the pinned response layer cannot support that safely, use a versioned response header containing the same bounded JSON payload. Do not duplicate telemetry on every returned object.

Instrument the final route choice and these execution paths:

- sweeping HNSW;
- ACORN HNSW;
- flat search;
- mixed execution if the pinned source can combine routes.

Use request-scoped immutable context passed through function arguments or Go `context.Context`; do not use package globals. Aggregate goroutine-local counters only for work belonging to the request nonce. Verify that every early stop and cancellation releases visited lists, locks, and pooled buffers.

Deliverables under `engines/weaviate/` mirror the pgvector package and add race-enabled tests for context isolation and pool cleanup.

### 18.3 Elasticsearch/Lucene third

Use the pinned Elasticsearch v9.5.4 and its pinned Lucene dependency. Begin with a feasibility spike that proves a versioned request context reaches every shard and segment and that a bounded response extension returns without enabling the profile API.

Instrument where Lucene chooses graph traversal versus exact filtered fallback. Emit component records containing route, opportunity, evaluation count, work counters, and stop reason. Aggregate at the coordinating node:

- every component HNSW: `elasticsearch_lucene_hnsw`;
- every component exact: `elasticsearch_lucene_exact`;
- any combination: `elasticsearch_lucene_mixed`.

A policy stop is a completed approximate execution state. Add a regression that proves it does not enter `AbstractKnnVectorQuery` exact fallback afterward. Preserve existing partial-shard, timeout, and failure semantics.

Deliverables under `engines/elasticsearch/` include the core/plugin patch, Gradle test target, custom image build, source/image digests, request/response transcript, and segment-composition tests.

## 19. Qualification fixtures and test matrix

### 19.1 Harness unit tests

Add or update:

- `tests/test_models.py`: every valid and invalid source/path/stop/mode combination;
- `tests/test_runner.py`: field propagation, source-aware acknowledgement, errors, and timeouts;
- `tests/test_results.py`: schema-3 JSONL/Parquet output and guarded schema-2 reading;
- `tests/test_statistics.py`: coverage counts, route maps, whole-workload pairs, and comparable-route exclusions;
- `tests/test_cli.py`: route-coverage display and policy doctor behavior;
- adapter tests: exact stock helper contract for all three engines.

Prefer table-driven invariant tests over one test per individual field.

### 19.2 Stock live tests

Update `tests/integration/test_docker_smoke.py` so every successful stock and placeholder sample asserts:

```text
mode_acknowledgement_source == adapter_declared
route_observation_source == unobserved
stop_reason_source == unobserved
executed_path == stock_route_unobserved
stop_reason == native_reason_unobserved
policy_opportunity is null
policy_applied is false
```

The existing filter, recall, pairing, timeout, and cleanup assertions remain.

### 19.3 Instrumented route fixture

Add `src/fannbench/datasets/route_fixture.py` and a checked-in small query specification. Generate enough deterministic rows to force meaningful routing while keeping generated data out of Git. Include:

- no filter or a broad filter;
- moderate selectivity;
- high selectivity;
- zero matches;
- fewer than `k` matches;
- repeated identical queries;
- configurations for Weaviate sweeping and ACORN.

Use controlled test settings to make each route reachable. Keep these qualification settings separate from the main experiment, where the native planner is free to choose. The test succeeds only if the server reports the intended route; client-side assumptions do not count.

Add `tests/integration/test_instrumented_observability.py`, guarded by `FANNBENCH_RUN_INSTRUMENTED_TESTS=1`, with this minimum matrix:

| Backend | Required observed cases |
|---|---|
| pgvector | HNSW and non-HNSW |
| Weaviate | sweeping HNSW, ACORN HNSW, and flat |
| Elasticsearch | HNSW, exact, and mixed |

For each policy-eligible route run `native`, `policy_noop`, `fixed_budget`, and a deterministic test policy. Assert native/no-op result equivalence, fixed-budget work reduction, truthful opportunity/application, valid result predicates, and no hidden replacement search.

### 19.4 Failure and isolation tests

For every custom build test:

- cancellation during traversal;
- request timeout;
- malformed context;
- unknown policy hash;
- connection or worker reuse after failure;
- concurrent requests with different modes and nonces;
- empty eligible set;
- early native termination before the first checkpoint;
- policy stop immediately after the first legal checkpoint.

The next request must always start with cleared state and zero counters.

## 20. Reviewable delivery units

Implement the work as seven independently reviewable changes:

| Change | Scope | Depends on | Completion evidence |
|---|---|---|---|
| A | Schema constants, enums, validators, v2 reader, version 0.3.0 | none | unit tests for the complete invariant matrix |
| B | Stock adapters, runner propagation, reports, diagnostics provenance | A | non-Docker suite and three stock live tests |
| C | Typed build catalog and Docker variant selection | A | stock regression plus unavailable-instrumented failure test |
| D | pgvector telemetry patch and adapter transport | B, C | HNSW/non-HNSW and state-isolation gates |
| E | Weaviate telemetry patch and adapter transport | B, C | sweeping/ACORN/flat and race gates |
| F | Elasticsearch/Lucene telemetry patch and adapter transport | B, C | HNSW/exact/mixed and no-refallback gates |
| G | Cross-engine route fixture, comparative summaries, documentation, release qualification | D, E, F | all acceptance commands pass |

Changes D, E, and F can proceed independently after B and C. PostgreSQL is the recommended first implementation because it can validate the end-to-end contract with the smallest distributed surface. Elasticsearch remains last because segment and shard aggregation plus exact fallback create the largest feasibility risk.

## 21. Verification commands and release gate

Run after every harness change:

```bash
uv run ruff check .
uv run pytest -m "not integration"
```

Run after change B and before release:

```bash
FANNBENCH_RUN_DOCKER_TESTS=1 uv run pytest tests/integration/test_docker_smoke.py
```

Run for each available custom build and for final qualification:

```bash
FANNBENCH_RUN_INSTRUMENTED_TESTS=1 uv run pytest tests/integration/test_instrumented_observability.py
uv run fannbench doctor --require-policy
```

Before accepting agent-policy measurements, execute one complete run containing `native`, `policy_noop`, `fixed_budget`, and `policy_agent` for all three backends. Inspect the resulting manifest, JSONL, Parquet, summary JSON/CSV, paired-effect tables, and diagnostics. Release only when:

1. the schema and build identity are immutable and complete;
2. every custom sample has same-execution server telemetry;
3. native and no-op controls agree within the declared deterministic behavior;
4. fixed-budget tests demonstrate real work-counter reduction;
5. policy stops never cause exact fallback or a second search;
6. route-unobserved samples appear only in stock or placeholder runs;
7. whole-workload and comparable-route estimates are both present and clearly labeled;
8. all custom images, patches, upstream commits, and protocol versions are digest-pinned.

At that point the harness can support the intended causal comparison: the native baseline and agent treatment execute in the same database build, over the same physical index and logical workload, while the server reports whether the agent actually had an opportunity to intervene and whether it did.
