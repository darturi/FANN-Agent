# Milvus implementation audit for FANNBench and the stopping-agent study

**Original audit date:** 2026-09-20  
**Implementation update:** 2026-09-20  
**Status:** Qdrant-to-Milvus substitution completed and validated on ARM64  
**Scope:** Assess and now verify Milvus as the specialized vector-database system in FANNBench, while separately evaluating its suitability for the later agent-generated stopping policy.

## Current verdict

Milvus is now the specialized vector-database backend in FANNBench. Qdrant has been removed from the adapter registry, Docker configuration, CLI defaults, experiment defaults, tests, examples, documentation, dependency lock, and generated wheel. The implemented backend pins **Milvus 2.6.23** by multi-architecture image digest and **PyMilvus 2.6.17** in `uv.lock`.

The substitution is functionally successful. The live ARM64 integration suite passed for pgvector, Milvus, and Elasticsearch using the same expanded 15-query workload. That workload covers every portable comparison operator, all four scalar types, nested Boolean expressions, unary `NOT`, quoted and Unicode strings, and empty eligible sets. The Milvus adapter uses parameterized filter templates and completed the workload without backend errors. Exact-result membership was checked separately in the 2.6.23 fit matrix; recall calibration for research workloads remains pending.

Milvus remains **unsuitable as the direct execution engine for the planned in-loop stopping agent through its public API**. A client can select HNSW parameters and filtering strategy before a search, but it cannot observe HNSW checkpoints, distance-computation counts, the candidate or result heaps, or filter-valid fractions during traversal. It also cannot pause, apply an external continue/stop policy, and resume the identical traversal. Milvus should therefore remain the unmodified production-system baseline while the stopping policy runs in a separate instrumentable HNSW implementation.

## Implemented substitution

| Area | Implemented state |
|---|---|
| Backend registry and CLI | `milvus` replaces `qdrant`; defaults now select `pgvector,milvus,elasticsearch` |
| Versions | Milvus 2.6.23 image digest and PyMilvus 2.6.17 are pinned |
| Deployment | One standalone container with embedded etcd and local storage |
| Resource floor | Milvus startup rejects profiles below 4 CPUs or 8 GiB RAM |
| Schema | Explicit `INT64` primary key, `FLOAT_VECTOR`, `VARCHAR` source ID, and typed scalar fields |
| Floating metadata | Stored as `DOUBLE` to preserve the harness's float equality semantics |
| String bounds | Maximum UTF-8 byte lengths are computed and validated before collection creation |
| Vector bounds | Milvus dimensions outside 2–32,768 are rejected before collection creation |
| Indexes | Configured HNSW vector index plus `AUTOINDEX` on every filterable scalar field |
| Readiness | Row count, index count, indexed rows, index state, and collection load state are verified |
| Filtering | Parameterized, fully parenthesized translations for `eq`, `in`, ranges, `and`, `or`, and `not` |
| Search | Explicit cosine metric, configured per-query `ef`, strong consistency, and client deadline |
| Filter strategy | `standard` is the default; `iterative` is an explicit separate configuration |
| Results | Native IDs and cosine similarity scores map into the existing `SearchResult` contract |
| Timeouts | gRPC deadline and PyMilvus timeout failures are classified as timeouts |
| Diagnostics | Milvus declares plans and per-query server timing unsupported rather than fabricating values |
| Run evidence | Server version, SDK version, image digest, architecture, index parameters, and resolved configuration are recorded across the run outputs |
| Resource identity | The Compose file and both Milvus configuration files contribute to the reusable-resource hash |
| Packaging | Compose, `embedEtcd.yaml`, `user.yaml`, and the Milvus adapter are included in the wheel |

The generic `httpx` dependency remains because the Elasticsearch adapter still uses it; there is no Qdrant-specific client or source path remaining in the harness.

## Validation completed after implementation

The implementation was checked at four levels.

### Static and unit validation

- All **28 non-Docker tests passed**.
- Ruff passed with no findings.
- Configuration validation rejects unknown Milvus settings and invalid filter strategies.
- Unit tests cover parameterized nested translation, `IN`, quoted string values, empty filters, UTF-8 byte counting, the Milvus dimension limit, and overlong strings.
- A source and configuration scan found no remaining Qdrant references outside ignored historical caches or artifacts; the local wheel was rebuilt afterward.

### Live Milvus integration

The live harness path completed collection creation, deterministic batch insertion, flush, HNSW and scalar index creation, collection loading, readiness verification, warmup, measurement, correctness evaluation, diagnostic reporting, and cleanup.

The fixture used 160 sixteen-dimensional vectors and 15 logical queries. It exercised:

- unfiltered search;
- integer `IN` and ordered ranges; integer equality was covered by the earlier direct fit matrix;
- floating-point equality and ordered comparison;
- Boolean equality and `IN`;
- string equality and `IN`;
- nested `AND`, `OR`, and unary `NOT`;
- unary `NOT` over a numeric range and over string `IN`;
- quoted strings and Unicode strings through filter-template parameters;
- filters with no eligible records.

Milvus completed the workload without query errors. The harness generated exact-ground-truth evaluation records for every response; the integration gate verifies successful execution, while publication-level recall calibration remains a separate task.

### Cross-backend integration

The complete opt-in Docker integration suite passed for:

1. PostgreSQL with pgvector;
2. Milvus;
3. Elasticsearch.

All three systems ran the same expanded fixture and query file. This validates the substitution path and common logical workload; it is not a performance comparison.

### Environment and packaging

- `fannbench doctor --backends milvus` passed on Apple Silicon with Docker 29.6.1 and PyMilvus 2.6.17.
- Docker Compose validation passed.
- The rebuilt wheel contains the Milvus adapter and all three Docker configuration files.
- Integration cleanup left no FANNBench containers, volumes, or networks behind.

## Compatibility with the implemented harness

| Requirement | Current result | Status |
|---|---|---|
| Cosine similarity | Native `COSINE`; greater score means more similar | Implemented and live-tested |
| HNSW controls | `M`, `efConstruction`, and per-query `ef` | Implemented and live-tested |
| Integer filters | equality, `IN`, and ordered ranges | Implemented and live-tested |
| Floating-point filters | equality and ordered ranges with `DOUBLE` metadata | Implemented and live-tested |
| Boolean filters | equality and `IN` | Implemented and live-tested |
| String filters | equality and `IN`; safe quotes and Unicode parameters | Implemented and live-tested |
| Nested logic | nested `AND`, `OR`, and unary `NOT` | Implemented and live-tested |
| Empty eligible set | empty result accepted without a fabricated recall value | Implemented and live-tested |
| Scalar indexes | all filterable fields receive `AUTOINDEX` | Implemented and live-tested |
| Readiness | indexed rows, index states, load state, and row count | Implemented and live-tested |
| Persistence | collection, indexes, and data survived restart in the fit audit | Verified |
| ARM64 | native image, doctor check, and full integration | Verified |
| x86-64 | multi-architecture image exists, but this implementation was not run there | Pending live gate |
| Public query plan | no portable per-query plan in the search result | Unsupported by Milvus API |
| Per-query server time | not returned by the gRPC search result | Unsupported by Milvus API |
| HNSW traversal trace | not exposed through the public client API | Unsupported by Milvus API |

The portable dataset format still permits dimensions up to 65,536. The Milvus adapter now rejects a dataset outside Milvus's 2–32,768 range before creating a collection. The adapter also calculates deterministic `VARCHAR.max_length` values from UTF-8 byte lengths and rejects fields above 65,535 bytes.

## Version boundary retained from the fit audit

The study paper evaluated Milvus 2.6.6 with PyMilvus 2.6.3. That exact pair was tested during the fit audit because reproducing a paper and selecting a dependable harness version are separate requirements.

On 2.6.6:

- integer, float, Boolean, and string leaf predicates passed;
- nested `AND` and `OR` passed when negation was expressed as a leaf operator such as `!=` or `NOT IN`;
- `not (active == true)` and `not (year >= 2000)` caused internal `PhyFilterBitsNode` assertion errors;
- `not (category in [...])` completed but returned the wrong set;
- the logically equivalent leaf forms passed.

On 2.6.23, the same full matrix passed, including all three unary-`NOT` forms. FANNBench now pins 2.6.23 and tests unary negation against the live image. An exact 2.6.6 paper reproduction would require a separate legacy configuration and negation normalization; it must not silently replace the harness baseline.

## Deployment and fairness after the swap

The implemented Compose service uses one Milvus container with embedded etcd and local storage. The container exposes only gRPC port 19530 through host port 19539. Its WebUI and metrics endpoint remain internal. The service mounts packaged `embedEtcd.yaml` and `user.yaml` files and one harness-owned data volume. `docker compose up --wait` performs container health checking, after which the adapter performs application-level readiness validation.

The default profiles are now:

| Profile | CPUs | Memory |
|---|---:|---:|
| `small` | 4 | 8 GiB |
| `standard` | 8 | 16 GiB |

These limits apply to every backend in a comparative run. A custom profile below 4 CPUs or 8 GiB is rejected when starting Milvus. The small integration fixture passing at this resource floor is a correctness result; it does not establish adequate memory for a medium MoReVec experiment. Docker-VM memory must exceed the container limit enough to accommodate Docker and host-side exact evaluation.

Standard pre-filtered HNSW remains the default. Setting `filter_strategy: iterative` creates an explicitly different Milvus configuration and resource identity. It should be reported as a separate strategy rather than mixed into the standard Milvus measurements.

## Fit for subsequent agent integration

The implementation does not change the agent-integration conclusion. The research plan requires a fixed HNSW traversal with declared checkpoints. Each checkpoint needs current-query features such as accumulated distance computations or expansions, filter-valid fractions, and queue, frontier, or result-set summaries. A deployed policy must choose `continue` or `stop`, and replay must reproduce the actual engine trajectory.

Milvus's public interface does not meet that contract:

- a search call runs to completion before returning;
- the result exposes IDs, scores, and requested entity fields rather than visited nodes or distance computations;
- Prometheus exposes aggregate request and stage metrics rather than a query's candidate trajectory;
- `SearchIterator` paginates a large result set rather than exposing HNSW checkpoints or a stop callback;
- the client cannot preserve an in-progress search, run an external policy, and resume the identical traversal.

Knowhere, the vector-search library used under Milvus, contains the lower-level HNSW machinery and internal iterator state. A Milvus/Knowhere fork could add checkpoint callbacks, counters, a stable trace format, and a stop decision. Doing so would require maintaining a custom C++ build and server integration, proving that instrumentation preserves expansion order, and validating replay across the RPC boundary. That is too large to treat as a side effect of the database substitution.

The study paper also reports that its Milvus 2.6.6 path may change strategy or fall back to brute-force search for highly selective or filter-heavy cases. That is useful production behavior, but it confounds a controlled stopping experiment unless the execution path is disclosed. The 2.6.23 public response still does not disclose that path, and the older paper's exact fallback behavior should not be attributed to 2.6.23 without separate instrumentation.

The recommended research architecture remains:

1. Use the implemented Milvus backend as the unchanged specialized vector-database baseline.
2. Implement trajectory capture, replay, and the continue/stop policy in an instrumentable HNSW engine.
3. Give both paths the same vectors, filters, cosine semantics, exact ground truth, recall targets, and resource-accounting rules.
4. Attribute stopping-policy results only to the fixed instrumented traversal and report Milvus separately.

Milvus can support a later coarse agent policy without a fork. Such an agent could choose `ef`, standard versus iterative filtering, or approximate versus exact routing before query submission. That would be a query-planning experiment rather than the in-loop stopping experiment in the current study design.

## Post-swap gates and remaining work

| Gate | Status | Required next action |
|---|---|---|
| Pin server and SDK versions | Complete | Keep updates explicit and rerun the contract suite before changing either version |
| Replace Qdrant across source, runtime, tests, docs, and wheel | Complete | None |
| Dimension and UTF-8 string preflight | Complete | Retain unit coverage |
| Portable filter contract | Direct 2.6.23 matrix and expanded adapter smoke completed on ARM64 | Repeat the adapter smoke on x86-64 before publishing cross-platform claims |
| Supported Milvus resource floor | Complete | Increase Docker-VM allocation before medium data |
| Separate standard and iterative filtering | Complete | Benchmark and report them under distinct configuration identities |
| Restart persistence and cleanup isolation | Complete in fit/integration tests | Retain as release checks |
| Small MoReVec pilot | Pending | Run exact-result and resource checks on the converted small dataset |
| Medium MoReVec pilot | Pending | Size Docker memory first, then run readiness, recall, and stability checks |
| Recall-target calibration | Pending | Calibrate each engine independently; equal `ef` values do not represent equal work |
| x86-64 integration | Pending | Run the full Docker integration suite on the intended Linux host |
| Timeout quiescence | Partially complete | Timeout classification is implemented; prove cancellation or stop/rebuild the backend after a deadline before sequential measurements continue |
| Earlier FANNBench audit findings | Pending where not separately fixed | Resolve the remaining evaluator, lifecycle, timeout, and reporting findings before producing research results |
| Stopping-agent execution engine | Pending | Demonstrate trace, checkpoint, continue/stop, replay, and overhead measurement in an instrumentable engine |

The database substitution itself is complete. Publication-quality benchmarking remains gated by the MoReVec pilots, recall calibration, x86-64 validation, timeout quiescence, and the unresolved findings in the broader FANNBench audit.

## Evidence and sources

Implemented project material:

- [`harness/src/fannbench/adapters/milvus.py`](../harness/src/fannbench/adapters/milvus.py)
- [`harness/src/fannbench/adapters/__init__.py`](../harness/src/fannbench/adapters/__init__.py)
- [`harness/src/fannbench/models.py`](../harness/src/fannbench/models.py)
- [`harness/src/fannbench/runtime/docker.py`](../harness/src/fannbench/runtime/docker.py)
- [`harness/docker/compose.yaml`](../harness/docker/compose.yaml)
- [`harness/tests/test_milvus.py`](../harness/tests/test_milvus.py)
- [`harness/tests/test_translations.py`](../harness/tests/test_translations.py)
- [`harness/tests/integration/test_docker_smoke.py`](../harness/tests/integration/test_docker_smoke.py)
- [`learning-data-shape-filtered-ann-project-plan-v2.md`](learning-data-shape-filtered-ann-project-plan-v2.md)
- [`2602.11443v1.pdf`](../background/2602.11443v1.pdf)

Primary online sources retained from the fit audit:

- [Milvus 2.6 standalone prerequisites](https://milvus.io/docs/v2.6.x/prerequisite-docker.md)
- [Milvus 2.6 standalone Docker deployment](https://milvus.io/docs/v2.6.x/install_standalone-docker.md)
- [Milvus metric types and vector dimensions](https://milvus.io/docs/v2.6.x/metric.md)
- [Milvus filtered search](https://milvus.io/docs/v2.6.x/filtered-search.md)
- [Milvus HNSW parameters](https://milvus.io/docs/hnsw.md)
- [Milvus search iterator](https://milvus.io/docs/with-iterators.md)
- [Milvus metrics dashboard](https://milvus.io/docs/metrics_dashboard.md)
- [Milvus releases](https://github.com/milvus-io/milvus/releases)
- [Knowhere HNSW implementation](https://github.com/zilliztech/knowhere/blob/main/src/index/hnsw/faiss_hnsw.cc)

## Audit limitations

- The post-swap live fixture was intentionally small and establishes functional compatibility only.
- The earlier 500-row fit fixture and the implemented 160-row integration fixture do not support throughput, tail-latency, index-build-time, or large-scale memory conclusions.
- The full MoReVec corpus has not yet been loaded through the implemented adapter.
- ARM64 is the only architecture exercised after the substitution; x86-64 remains a required release and research gate.
- The absence of public traversal state was assessed from the client response, documented APIs, metrics surface, and source inspection; a custom Milvus/Knowhere build could expose additional state.
- The 2.6.6 fallback behavior comes from the cited study and must be reverified for 2.6.23 before making claims about the current engine's internal execution path.
