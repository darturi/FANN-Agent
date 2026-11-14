# FANNBench exact vector conformance implementation plan

Date: 2026-09-20  
Status: implemented and live-qualified on the local arm64 host  
Severity addressed: medium for harness construction; high before comparative research results are trusted  
Scope: exact vector-result equivalence, distance normalization, backend route proof, conformance reporting, fixtures, tests, and benchmark gating

Implementation evidence: FANNBench now writes conformance schema 2 under the
`exact_vector_conformance_v1` contract. The deterministic exact fixture passes
against the pinned pgvector, Elasticsearch, and Weaviate images. The maximum
observed absolute distance error was `2.3162841866763983e-8`, below the
versioned `1e-6` absolute and relative tolerances. The non-integration suite
passes with 102 tests; all five stock Docker tests and all three instrumented
Docker tests pass. The source distribution and wheel build successfully, and
the wheel contains the conformance module, exact fixture, and shared physical
field mapping.

## 1. Goal

Add an untimed qualification check that proves each database can produce the
same exact filtered nearest-neighbor answer as the harness oracle, within a
declared floating-point tolerance.

In simple terms, before FANNBench measures how fast an approximate search is,
it will ask the database to do a slower, exhaustive search and verify:

1. the database searched only records allowed by the filter;
2. it returned the correct number of results;
3. it returned the records that truly belong in the top `k`;
4. the results are ordered by increasing cosine distance;
5. the reported distances agree with the oracle closely enough to account for
   ordinary floating-point rounding; and
6. the query really used the database's exact route rather than accidentally
   using its approximate HNSW index.

This check is a correctness gate, not a performance measurement. Its runtime
and database work must never be included in benchmark latency.

## 2. What this change does and does not claim

### It will prove

- The canonical vectors, filters, IDs, and cosine-distance convention are
  interpreted consistently by pgvector, Elasticsearch, Weaviate, and the
  Python oracle.
- Each backend has a known exact-search route that works for every query
  admitted to conformance.
- Top-`k` membership and ordering are correct, including duplicate vectors,
  ties at the `k` boundary, empty result sets, and result sets smaller than
  `k`.
- Backend-reported distances are numerically consistent with the canonical
  oracle within a versioned tolerance.

### It will not require

- Approximate HNSW results to exactly match the oracle. Approximate quality
  continues to be measured with recall and tie-aware recall.
- Bit-for-bit identical floating-point values across engines. The engines use
  different numeric implementations, so the contract uses explicit absolute
  and relative tolerances.
- The agent-policy path to exist. Exact conformance qualifies the testing
  harness and applies equally to the native, no-op, and future agent-policy
  experiments.
- Exact search to be fast. It is deliberately outside the timed trial.

## 3. Canonical exact-result contract

Create one versioned contract, tentatively named
`exact_vector_conformance_v1`.

### 3.1 Canonical distance

The oracle remains the source of truth. For every eligible stored vector
`x` and normalized query vector `q`, compute:

```text
canonical_distance = 1 - dot(float64(x_as_stored_float32),
                             float64(q_as_validated_float32))
```

This definition is important: conformance compares the databases with the
vectors that were actually admitted to the canonical dataset, rather than
with higher-precision source values that the databases never received.

Centralize this calculation in `oracle.py` so ground-truth construction,
tie handling, and exact conformance cannot develop separate definitions.

### 3.2 Result count

For each query:

```text
effective_k = min(query.k, eligible_record_count)
```

The exact backend must return exactly `effective_k` distinct IDs. It must
return zero records when nothing is eligible and all eligible records when
fewer than `k` are eligible.

### 3.3 Validity rules

Every returned ID must:

- exist in the canonical dataset;
- satisfy the query filter;
- occur only once; and
- include a finite numeric distance.

Any violation fails conformance before top-`k` membership is considered.

### 3.4 Distance tolerance

Start the v1 contract with:

```text
absolute tolerance = 1e-6
relative tolerance = 1e-6
```

For every returned ID, compare the backend's normalized distance with the
oracle distance for that same ID using both tolerances. Record the absolute
error, relative error, maximum error, and the configured tolerances.

The tolerance is a contract constant, not a hidden adapter setting. Changing
it requires a new contract version or an explicitly recorded compatibility
change. Before freezing v1, run the live adversarial suite on the supported
backend versions and tighten or relax the value only from observed evidence.

NaN, infinity, missing scores, or values outside the tolerance always fail.

### 3.5 Ranking and ties

Use these rules so harmless tie ordering does not create a false failure:

1. Results must be nondecreasing by normalized distance, allowing only the
   declared tolerance.
2. Every eligible ID whose oracle distance is strictly better than the
   `k`-boundary distance must be present.
3. Remaining slots may be filled by any eligible IDs tied with the boundary
   within tolerance.
4. An ID strictly worse than the boundary outside tolerance fails.
5. When distances are tied, adapters should request canonical-ID ascending as
   the secondary sort. This makes output reproducible, but membership remains
   tie-aware so a database rounding difference at the boundary is not treated
   as a substantive ranking error.

Report two facts separately:

- `canonical_order_match`: whether IDs exactly match the oracle's deterministic
  distance/ID ordering; and
- `tie_aware_top_k_match`: whether the result is mathematically valid under
  the tolerance.

The second field determines conformance. The first is useful diagnostic
evidence.

## 4. Public adapter interface

### 4.1 Add an exact-search result type

Add an immutable model or dataclass, for example:

```python
ExactSearchResult(
    ids: list[int],
    distances: list[float],
    method: str,
    route_evidence: dict[str, Any],
    raw_score_kind: str | None = None,
)
```

`distances` must already be converted to the canonical cosine-distance scale.
Adapter-specific values such as Elasticsearch scores may be retained in
`route_evidence` for diagnosis, but comparison code must not need to know each
backend's scoring formula.

### 4.2 Extend `Adapter`

Add:

```python
execute_exact_query(
    resource_name: str,
    query: Query,
) -> ExactSearchResult
```

Also extend `AdapterCapabilities` with a versioned exact-vector capability,
such as:

```text
exact_vector_search: bool
exact_vector_method: str | None
```

Do not silently fall back to the ordinary approximate `execute_query` method.
If a backend cannot prove an exact route, the capability is false and the
qualification must fail clearly.

### 4.3 Separate exact resource preparation where needed

Add optional lifecycle hooks only for backends that require a different
physical resource:

```python
prepare_exact_resource(dataset, benchmark_resource_name) -> Preparation
exact_resource_name(benchmark_resource_name) -> str
delete_exact_resource(benchmark_resource_name) -> None
```

The default implementation can reuse the benchmark resource. Weaviate will
override it to use a sibling flat-index collection.

Do not encode this special case in the runner. The runner should ask the
adapter to prepare and address its exact resource.

## 5. Backend-specific exact routes

### 5.1 pgvector

Use the same table and scalar filter indexes, but make the vector ordering
expression ineligible for the HNSW expression index:

```sql
SELECT id,
       embedding <=> %(query_vector)s::vector AS distance
FROM <resource>
WHERE <translated_filter>
ORDER BY (embedding <=> %(query_vector)s::vector) + 0, id
LIMIT %(k)s
```

The pgvector maintainer documents adding an expression such as `+ 0` as a way
to bypass the approximate index while preserving other useful indexes:
[pgvector issue 734](https://github.com/pgvector/pgvector/issues/734).
The official pgvector documentation also distinguishes exact search from the
approximate HNSW and IVFFlat indexes:
[pgvector README](https://github.com/pgvector/pgvector/blob/master/README.md).

Implementation requirements:

1. Use the existing logical-to-physical filter translation.
2. Return database distance directly as canonical cosine distance.
3. Add `id` as the explicit secondary sort.
4. Run `EXPLAIN (FORMAT JSON)` for the exact statement before qualification.
5. Recursively inspect the plan and fail if the HNSW index name or an HNSW
   vector index scan appears.
6. Record the complete plan JSON, database version, index name, and exact
   method `pgvector_expression_bypass_v1`.
7. Do not globally disable all PostgreSQL index scans; scalar indexes used by
   the filter should remain available.

### 5.2 Elasticsearch

Use a `script_score` query over the complete filtered candidate set rather
than a `knn` query:

```json
{
  "size": "effective_k",
  "query": {
    "script_score": {
      "query": "translated filter or match_all",
      "script": {
        "source": "cosineSimilarity(params.query_vector, 'vector') + 1.0",
        "params": {"query_vector": "..."}
      }
    }
  },
  "sort": ["_score descending", "internal canonical ID ascending"]
}
```

Elasticsearch documents that the vector functions in `script_score` linearly
scan every document matched by the inner query:
[script score query documentation](https://www.elastic.co/docs/reference/query-languages/query-dsl/query-dsl-script-score-query).

Implementation requirements:

1. Add an adapter-owned numeric canonical-ID field to the Elasticsearch
   mapping and bulk documents. Use a reserved internal physical name rather
   than a user logical name.
2. Sort by `_score` descending and that numeric ID ascending.
3. Convert the returned score to canonical distance with
   `distance = 2.0 - score`.
4. Keep the raw score in diagnostic evidence.
5. Assert that the generated request contains `script_score` and contains no
   `knn` block.
6. Verify or clearly require `search.allow_expensive_queries=true`, because
   exact script scoring may otherwise be rejected.
7. Record the request shape, index mapping, cluster version, and method
   `elasticsearch_script_score_scan_v1`.
8. Increment `BACKEND_STORAGE_SCHEMA_VERSION` because the stored mapping gains
   an internal field. This prevents reuse of an incompatible old index.

Elasticsearch represents scores as positive 32-bit floating-point numbers, so
small differences from the float64 oracle are expected and belong under the
declared tolerance rather than exact equality:
[function score documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-function-score-query.html).

### 5.3 Weaviate

Do not reuse the HNSW benchmark collection for exact conformance. Create a
sibling conformance collection containing the same vectors and properties but
configured with:

```text
vectorIndexType = flat
distance metric = cosine
quantization = disabled
```

Weaviate documents the flat index as a brute-force index that compares against
every vector and provides perfect recall:
[vector indexing tutorial](https://docs.weaviate.io/weaviate/tutorials/vector-indexing-deep-dive).
It also documents `flat` as a supported vector-index type:
[vector-index configuration reference](https://docs.weaviate.io/weaviate/config-refs/indexing/vector-index).

Implementation requirements:

1. Derive a deterministic, length-safe sibling resource name from the normal
   benchmark resource and an exact-resource schema version.
2. Reuse the same physical metadata mapping and record data.
3. Create the sibling collection with `flat` before inserting records.
4. Query it with the same translated filter and request canonical ID plus
   `_additional.distance`.
5. Add canonical-ID ordering locally only after receiving all distance-valid
   results; do not hide an incorrectly ranked database response.
6. Inspect the live collection schema before every reuse and require `flat`,
   cosine distance, the expected vector dimension, expected property mapping,
   and disabled quantization.
7. Record the schema evidence, server version, resource identity, and method
   `weaviate_flat_v1`.
8. Register the exact collection as an owned resource and delete it whenever
   cleanup deletes the paired benchmark collection.

Weaviate states that `vectorIndexType` cannot be changed after collection
creation, which is why a separate collection is required:
[collection definition reference](https://docs.weaviate.io/weaviate/config-refs/collections).

## 6. Oracle and comparison implementation

Refactor `src/fannbench/oracle.py` around a reusable exact-distance view.

Suggested internal types and functions:

```text
ExactCandidateSet
  eligible_ids
  eligible_positions
  canonical_distances
  canonical_order
  effective_k
  boundary_distance

build_exact_candidate_set(dataset, query) -> ExactCandidateSet
evaluate_exact_result(candidate_set, exact_result, tolerances)
    -> ExactConformanceEvaluation
```

`exact_ground_truth` should consume `build_exact_candidate_set`, so normal
recall evaluation and exact conformance share one ordering and tie definition.

`ExactConformanceEvaluation` should include at least:

- `passed`;
- `expected_count` and `actual_count`;
- `duplicate_ids`, `unknown_ids`, and `predicate_violations`;
- `missing_strictly_better_ids`;
- `returned_strictly_worse_ids`;
- `canonical_order_match` and `tie_aware_top_k_match`;
- `order_violation_count`;
- per-ID expected and actual distance for mismatches;
- maximum absolute and relative distance error;
- tolerance values; and
- boundary distance and whether a boundary tie occurred.

Keep the in-memory comparison exhaustive. Limit only the number of mismatch
examples embedded in the summary JSON; write the complete mismatch data to a
separate failure artifact.

## 7. Runner behavior and report format

### 7.1 Qualification sequence

For each backend and prepared dataset, run these checks in order:

1. inspect and verify physical storage;
2. compare the complete filter-eligible ID set;
3. prepare or resolve the exact-search resource;
4. prove the exact route;
5. run exact vector conformance for every qualification query;
6. write the conformance report; and
7. only if every required check passed, begin warmup and timed trials.

An exact failure must prevent measurements for that backend. It must not be
reported as a low recall result, because it indicates a harness or translation
problem rather than normal ANN approximation.

### 7.2 Conformance JSON v2

Bump `conformance.json` from schema version 1 to 2. Preserve the current
filter check under its own section and add exact-vector evidence.

Suggested shape:

```json
{
  "schema_version": 2,
  "contract": "exact_vector_conformance_v1",
  "status": "passed",
  "tolerances": {"atol": 1e-6, "rtol": 1e-6},
  "backends": {
    "pgvector": {
      "passed": true,
      "filter_eligibility": {"passed": true},
      "exact_vector": {
        "passed": true,
        "method": "pgvector_expression_bypass_v1",
        "queries_checked": 12,
        "max_absolute_distance_error": 0.0000001,
        "max_relative_distance_error": 0.0000002,
        "query_results": []
      },
      "route_proof": {}
    }
  }
}
```

Each per-query entry should include counts, pass flags, boundary-tie status,
and bounded mismatch examples. Route evidence may be stored directly when
small or referenced by a relative artifact path when large.

### 7.3 Failure bundles

On failure, write a deterministic reproduction bundle, for example:

```text
conformance-failures/<backend>/<query-id>.json
```

Include:

- dataset hash and query JSON;
- canonical eligible IDs and distances;
- backend IDs, normalized distances, and raw scores;
- translated backend filter;
- exact request or SQL with parameter values safely separated;
- route proof and inspected storage configuration;
- backend image/version and adapter method version; and
- every comparison reason.

The bundle must contain enough data to reproduce the failure without rerunning
the timed benchmark. Do not include credentials or full connection strings.

### 7.4 Standalone and benchmark commands

Keep the existing `fannbench conformance` command, but update its help text to
say that it checks both complete filter eligibility and exact vector results.

The benchmark command should invoke the same implementation. There must be no
separate, weaker benchmark-only conformance path.

Run exact conformance once per backend/resource/query-set identity, before all
trial repetitions. Do not rerun it inside warmup or measurement loops.

For the first implementation, prefer rerunning the untimed check on each
benchmark invocation. Only add cache reuse later if the cache key includes:

- canonical dataset and query hashes;
- backend name and live version;
- container image digest or equivalent build identity;
- backend storage-schema version;
- exact method and contract versions;
- adapter configuration affecting vectors, filters, or scoring; and
- tolerances.

Never silently sample eligible candidates. If a declared conformance dataset
is too large for exhaustive qualification, fail with a clear limit message or
use an explicitly declared qualification dataset; do not label a sampled
check as exact.

## 8. Deterministic adversarial fixture

Add a small generated fixture dedicated to exact-vector conformance, for
example `src/fannbench/datasets/exact_fixture.py`.

It should be fast enough for every Docker smoke run and contain:

- exact duplicate vectors with different canonical IDs;
- several vectors tied exactly at the `k` boundary;
- near ties just inside and just outside the tolerance;
- orthogonal and antipodal vectors;
- positive, zero, and negative cosine similarities;
- filters selecting none, one, fewer than `k`, exactly `k`, and more than `k`;
- `k=1`, a normal middle value, and the profile maximum where practical;
- nested `and`, `or`, and `not` filters;
- each portable scalar type and comparison operator;
- logical field names that exercise the physical-name isolation layer; and
- at least one high-dimension case near the portable-profile limit, separated
  from the small smoke fixture if runtime requires it.

Generate vectors deterministically, normalize them using the same dataset
writer, and reject zero, NaN, or infinite vectors. Store the generation seed
and fixture version in the manifest provenance.

Use two fixture tiers:

- `exact_smoke_v1`: small and mandatory in ordinary integration CI; and
- `exact_boundary_v1`: larger dimensional and generated edge cases for the
  qualification workflow and release CI.

## 9. Implementation phases

### Phase A: freeze the contract and shared models

Files:

- `src/fannbench/contracts.py` or a new `conformance.py`
- `src/fannbench/models.py`
- `src/fannbench/adapters/base.py`
- `docs/formats.md`

Actions:

1. Define contract name, tolerance constants, and conformance schema version.
2. Add `ExactSearchResult` and `ExactConformanceEvaluation`.
3. Add exact-search capabilities and adapter hooks.
4. Define explicit serialization and finite-number validation.
5. Document the canonical distance, count, tie, order, and pass rules before
   writing backend-specific code.

Exit condition: unit tests can construct valid and invalid exact results, and
the contract is understandable without reading an adapter.

### Phase B: unify oracle exact calculations

Files:

- `src/fannbench/oracle.py`
- `tests/test_oracle.py`

Actions:

1. Implement the reusable exact candidate set.
2. Make `exact_ground_truth` use it.
3. Implement exact-result evaluation.
4. Preserve existing recall and tie-aware recall behavior.
5. Add exhaustive unit cases for empty sets, fewer-than-`k`, duplicates,
   unknown IDs, filter violations, wrong counts, wrong ranking, exact ties,
   near ties, and distance tolerance boundaries.

Exit condition: deliberately corrupted synthetic backend results fail for one
clear reason, while valid alternate boundary-tie members pass.

### Phase C: implement backend routes and route proof

Files:

- `src/fannbench/adapters/pgvector.py`
- `src/fannbench/adapters/elasticsearch.py`
- `src/fannbench/adapters/weaviate.py`
- `src/fannbench/field_names.py`
- adapter translation and physical-schema tests

Actions:

1. Implement pgvector's expression-bypass query and plan inspection.
2. Add Elasticsearch's internal numeric ID, storage-schema migration,
   script-score query, score conversion, and request assertion.
3. Implement the versioned Weaviate flat sibling collection and lifecycle.
4. Normalize every result to canonical distance in the adapter.
5. Return method and route evidence with every exact result.
6. Treat unverifiable or unexpected routes as failures, not warnings.

Exit condition: each adapter proves its exact method and returns the expected
result type against the small fixture.

### Phase D: integrate the runner and artifacts

Files:

- `src/fannbench/runner.py`
- `src/fannbench/results.py`
- `src/fannbench/runtime/registry.py`
- `src/fannbench/cli.py`
- runner and registry tests

Actions:

1. Compose filter and exact checks into one conformance operation.
2. Add exact-resource registration, reuse verification, and cleanup.
3. Write conformance schema v2 and route evidence.
4. Write complete failure bundles with bounded summaries.
5. Gate warmups and measurements on the combined result.
6. Keep exact-query time out of measurement records and summary statistics.
7. Update progress and error messages to identify the failing query and check.

Exit condition: a forced exact mismatch aborts before the first warmup, while
a passing qualification proceeds through the existing three execution modes.

### Phase E: fixtures, integration tests, and documentation

Files:

- `src/fannbench/datasets/exact_fixture.py`
- `src/fannbench/datasets/__init__.py`
- `tests/integration/test_docker_smoke.py`
- new exact-conformance integration tests as needed
- `README.md`
- `docs/methodology.md`
- `docs/formats.md`
- `docs/compatibility.md`

Actions:

1. Add both deterministic fixture tiers.
2. Qualify all three live backends with the smoke fixture.
3. Run the boundary suite on all supported image versions.
4. Verify old approximate and instrumented routes are unchanged.
5. Document exact route, tolerance, tie behavior, cost, and failure handling.
6. Update compatibility claims only after live evidence exists.

Exit condition: the documented qualification command passes all three
backends and the resulting artifact contains enough evidence to audit every
claim.

## 10. Test matrix

### Unit tests

- Canonical float64 distance from stored float32 inputs.
- Correct deterministic order by distance then canonical ID.
- Exact and near boundary ties.
- Absolute and relative tolerance boundaries.
- NaN, infinity, and missing distances.
- Duplicate, unknown, ineligible, missing, and extra IDs.
- Zero eligible records and fewer records than `k`.
- Alternative valid tied IDs.
- Score conversion for Elasticsearch.
- Exact-query construction and physical filter translation for every backend.
- Route-proof parser rejects approximate routes.
- Failure artifact redacts endpoint credentials.

### Integration tests with live containers

- One passing exact query for each backend.
- Full `exact_smoke_v1` suite for each backend.
- pgvector plan contains no HNSW vector index path.
- Elasticsearch exact request scans the filtered set through script scoring
  and has no `knn` section.
- Weaviate exact resource reports `vectorIndexType=flat` and the benchmark
  resource remains HNSW.
- All three agree on filters and tie-aware top-`k` membership.
- A deliberately altered vector or score causes a gate failure before timing.
- Cleanup removes both normal and conformance-only resources.
- Resource reuse rejects an old Elasticsearch mapping and a non-flat Weaviate
  exact collection.

### Regression tests

- Existing stock-native search still uses each backend's intended ANN route.
- Existing no-op and policy-placeholder collection paths are unchanged.
- Existing recall calculations produce the same values.
- Field-name isolation remains active in exact queries and resources.
- Package build includes the new fixture and modules.

## 11. Acceptance criteria

This issue is resolved only when all of the following are true:

1. `fannbench conformance` checks exact vector results as well as filter IDs.
2. All three adapters expose an explicit exact method with recorded route
   proof.
3. Every exact result uses the same documented cosine-distance scale.
4. Top-`k` comparison handles boundary ties without hiding genuinely worse
   results.
5. Distance comparison uses versioned, reported tolerances and records maximum
   observed error.
6. Empty, undersized, tied, and adversarial result sets pass on every live
   backend.
7. A wrong ID, wrong order, wrong distance, or accidental ANN route fails
   qualification.
8. Failure prevents warmup and timed measurements and creates a complete
   reproduction bundle.
9. The ordinary benchmark resources and ANN execution paths remain unchanged.
10. The full unit suite, package checks, and three-backend Docker qualification
    pass.
11. Methodology, format, and compatibility documents match the implementation.

## 12. Recommended implementation order

Implement the work in this dependency order:

```text
contract and models
  -> shared oracle comparison
  -> pgvector exact route
  -> Elasticsearch exact route and storage-schema bump
  -> Weaviate flat-resource lifecycle
  -> combined runner gate and artifacts
  -> adversarial fixtures
  -> live three-backend qualification
  -> documentation and compatibility claim
```

Pgvector is the best first vertical slice because it needs no second data
resource. Elasticsearch should follow because its internal ID changes the
storage schema. Weaviate comes third because its separate flat collection adds
the most lifecycle work. The runner should not declare the new conformance
schema complete until all three adapter implementations can populate it.

## 13. Main risks and controls

| Risk | Control |
|---|---|
| An “exact” query silently uses ANN | Require and save backend-specific route evidence; fail closed. |
| Floating-point noise creates false failures | Compare normalized per-ID distances with versioned absolute and relative tolerances. |
| Ties create unstable ID order | Use a numeric ID secondary sort and a tie-aware membership rule. |
| Weaviate's exact setup changes the benchmark | Use a separate flat collection; leave the HNSW collection untouched. |
| Conformance work contaminates timing | Complete it before warmup and never write it as a measurement. |
| Exhaustive search is expensive | Run once per qualification identity, never per repetition; do not silently sample. |
| Old resources are reused with new assumptions | Version storage and exact resources and verify live schemas before reuse. |
| Failure summaries omit necessary evidence | Write complete per-query reproduction bundles and bounded human-readable summaries. |

## 14. Completion evidence to retain

When implementation is complete, retain:

- the exact contract and tolerance version;
- the passing `conformance.json` from all three backends;
- backend route evidence;
- maximum observed absolute and relative distance errors;
- the container image digests and server versions;
- the generated-fixture versions and hashes;
- the complete automated test output; and
- confirmation that measured ANN routes still match the intended backend
  configurations.

This evidence will support the later scientific claim that differences in ANN
quality or policy performance come from the systems being compared, rather
than from mismatched filters, distance conventions, or ground-truth logic.
