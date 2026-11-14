# Filtered Vector Search Test Harness: Initial Implementation Plan

Status: proposed implementation plan, September 2026. This document specifies the first release; it does not claim that the software, compatibility checks, or experiments have already been completed.

## 1. Goal and agreed scope

Build a small, reproducible, local-first command-line harness for comparing filtered approximate nearest-neighbor search (FANNS) across established database systems.

The user supplies:

1. A subset of supported database systems.
2. The location of a downloaded dataset, converted once into the harness's documented format.
3. One or more files containing queries in a common, database-independent format.

The harness ensures that each selected database contains the same dataset snapshot, runs the same logical workload against each database, and returns timing, retrieval-quality, and failure statistics. Optional native query plans or profiles are collected where supported. Explicit cleanup commands reclaim harness-owned storage.

The first release is a benchmarking tool, not an agent or a new search algorithm. Its design must nevertheless preserve the provenance and extension points needed for later dataset analysis, query-difficulty estimation, and agent experiments.

### First-release commitments

| Include in the first release | Deliberately defer |
|---|---|
| PostgreSQL + pgvector, Qdrant, Elasticsearch | More database adapters, distributed deployments, managed cloud services |
| Existing dense embeddings and scalar metadata | Generating embeddings from arbitrary text, images, or documents |
| A common query format and faithful adapter translation | Arbitrary SQL, joins, text/vector hybrid scoring, nested or array filters |
| Cosine similarity, fixed-dimensional float32 vectors | Additional distance metrics and vector representations |
| Sequential, single-client workloads | Concurrent-load and saturation testing |
| Exact filtered ground truth and measured recall | Automatic tuning to a target recall |
| Timing, errors, import/readiness time, storage observations | Uniform low-level engine instrumentation |
| Optional native plans/profiles, with explicit unsupported cases | A universal query-plan representation |
| Persistent data reuse and scoped cleanup | Automatic eviction of user data or global Docker cleanup |
| Versioned results and experiment manifests | A UI, agent, learned stopping policy, or model training |
| Small correctness fixtures and a real benchmark importer | GLS, clustering, geometry, and hardness analyzers themselves |

## 2. Database cross section

Use three database adapters and one independent correctness oracle.

| System | What it represents | Initial configuration direction | Diagnostic treatment |
|---|---|---|---|
| PostgreSQL + pgvector | A relational database with vector search integrated into SQL, scalar indexes, and a query optimizer | HNSW vector index, appropriate scalar indexes, refreshed planner statistics, explicitly configured iterative scanning | Native JSON `EXPLAIN`; optional execution diagnostics collected outside timing |
| Qdrant | A purpose-built vector database with structured payload filtering | Dense-vector HNSW collection, payload indexes, single-node deployment | Record public configuration and available diagnostics; do not invent a SQL-like plan |
| Elasticsearch | A search engine combining structured filters with Lucene vector retrieval | One primary shard, no replicas, explicit vector index/quantization settings, keyword/numeric metadata mappings | Native search profiling where supported by the pinned version |
| FAISS CPU Flat search | An exact vector-search library used to establish correct answers | Exact search over the eligible rows for each filter | Oracle only; not presented as a database-service competitor |

This is a cross section of **system architectures and filtering/execution behavior**, not an exhaustive cross section of ANN algorithms. Starting with HNSW in all three reduces one source of variation while retaining meaningful differences in optimizer behavior, filter handling, storage, and API overhead. The systems are established projects rather than research-only prototypes; selection is not a claim about their precise market-share ranking.

The initial scope does not represent IVF/PQ-heavy designs, disk-oriented ANN, GPU search, distributed operation, or proprietary cloud services. Those require separate configurations or later adapters. Adding another similar HNSW service initially would add setup and maintenance work before expanding this coverage substantially.

pgvector documents filtered and iterative index scans; Qdrant documents filter-aware indexing; Elasticsearch documents filtered kNN and exact-search fallbacks. Consequently, the harness must allow an engine to choose an exact strategy and must not label every measured execution as graph traversal merely because an HNSW index exists. [pgvector documentation](https://github.com/pgvector/pgvector), [Qdrant indexing](https://qdrant.tech/documentation/manage-data/indexing/), [Elasticsearch kNN](https://www.elastic.co/docs/solutions/search/vector/knn)

## 3. First dataset and workload

### Recommendation

Use **MoReVec Movies** as the first substantive dataset. It provides existing 768-dimensional, normalized text embeddings and numeric metadata suitable for filtered queries. Start integration testing with its approximately 10,000-row release, then use its approximately 100,000-row release for the first comparative experiment. Its connection to the GLS paper makes it a useful foundation for the planned research extension. [MoReVec/GLS paper](https://arxiv.org/abs/2602.11443), [authors' benchmark artifact](https://github.com/aabylay/ANN-benchmark-HQ)

The medium Movies release is reported as 99,560 records. Its float32 vectors alone occupy about 306 MB; actual requirements also include metadata, indexes, database overhead, temporary import storage, and the oracle. This is a sizing estimate, not a measured deployment footprint.

Provide three separately named workloads:

- **Synthetic smoke fixture:** approximately 2,000 records, 32 dimensions, deterministic metadata, and edge-case queries. Fast setup and correctness checks; not evidence of real-world performance.
- **MoReVec small integration workload:** a fixed, seeded selection of approximately 100 queries, `k=10`, including unfiltered queries and numeric filters at several actual selectivities.
- **MoReVec medium experiment workload:** the same query semantics at the larger published scale; start with 100 queries and allow expansion to the available published workload. Include restrictive through broad filters, and later add `k=1, 40, 100` as distinct workload configurations.

The importer will read the authors' HDF5 dataset/query/filter files and emit canonical dataset and query files. Their repository distinguishes these artifacts, so the converter must validate their relationships rather than assume that any one HDF5 file is self-contained. [Artifact layout and loader](https://github.com/aabylay/ANN-benchmark-HQ)

### Dataset acceptance gate

Before committing the importer, inspect the actual downloaded release and verify:

1. Download availability, source terms, and whether redistribution is allowed. A repository's code license does not automatically cover its data. Do not bundle the dataset with the package.
2. File hashes, dimensions, row counts, IDs, metadata types, normalization, and filter definitions.
3. Whether query vectors overlap with base records. Preserve and document the published self-match policy for a reproduction workload; any held-out variant receives a different workload identity and recomputed ground truth.
4. Whether published queries and filters can be represented by the first-release scalar-filter contract without changing semantics. Do not reinterpret a serialized genre field as an array without inspecting it.
5. Memory, disk, and setup time on the small release before importing the medium release.

If the source release is unavailable or its terms are unsuitable, finish harness engineering with the synthetic fixture and identify a replacement real dataset before making empirical database comparisons. Do not silently substitute random metadata and call it the original benchmark.

Every backend in a comparison receives **exactly the same canonical snapshot**. A smaller snapshot is a new experiment for all backends. Subsampling invalidates full-dataset ground truth and changes filter prevalence; recompute both. MoReVec alone will not establish generality across data distributions. A later second dataset or controlled hardness workload should test that limitation. [Hardness-controlled benchmark paper](https://arxiv.org/abs/2606.14193)

## 4. Public CLI

Use the working command name `fannbench`. Commands below describe the interface to implement, not commands available today.

```sh
# Check Docker, architecture, available resources, and adapter dependencies.
fannbench doctor --backends pgvector,qdrant,elasticsearch

# Convert already-downloaded benchmark files once; preserve the source files.
fannbench datasets import --format morevec --source /path/to/download \
  --table movies --scale small --output /path/to/canonical/movies-small

# Inspect schema, dimensions, identity, size, and query compatibility.
fannbench datasets inspect --dataset /path/to/canonical/movies-small/manifest.yaml

# Import/reuse data and execute the same workload against selected backends.
fannbench run --backends pgvector,qdrant,elasticsearch \
  --dataset /path/to/canonical/movies-small/manifest.yaml \
  --queries /path/to/queries-a.jsonl --queries /path/to/queries-b.jsonl \
  --profile standard --config /path/to/experiment.yaml \
  --output /path/to/results

# Add native diagnostics or remove this run's database copies afterward.
fannbench run --backends pgvector,qdrant \
  --dataset /path/to/canonical/movies-small/manifest.yaml \
  --queries /path/to/queries.jsonl --include-plans --cleanup-after-run

# List harness-owned database copies, resource identities, and disk observations.
fannbench status

# Preview exact targets, then explicitly delete one registered database copy.
fannbench clean --resource RESOURCE_ID --dry-run
fannbench clean --resource RESOURCE_ID --yes
```

`run` performs preparation automatically. A separate `prepare` command supports import/index creation without benchmarking. Query files may be repeated; file order, query order, and duplicate-ID validation are deterministic. A single-query file works without a separate execution path.

Configuration precedence is explicit: command-line overrides, experiment file, then packaged defaults. Save the fully resolved configuration. Reject unknown fields and unsupported options rather than silently ignoring them. Exit codes distinguish complete success, incomplete/backend failure, and invalid input/environment errors. A failed selected backend makes the overall run incomplete even if others finish successfully.

## 5. Dataset and query contracts

### Canonical dataset

Use a versioned YAML manifest plus Parquet records. The importer creates these files; users should not have to construct hashes or ID mappings manually.

Each record contains:

- `id`: unique, nonnegative signed-64-bit canonical ID, shared by all adapters and the oracle.
- `source_id`: the original identifier, preserved as a string.
- `vector`: a fixed-length float32 list.
- Declared scalar metadata fields with explicit integer, float64, boolean, or string types.

The manifest records schema version, dataset name, source provenance and terms, source/canonical file hashes, row count, dimension, metric, normalization procedure, filterable fields, and any sampling or conversion seed. Store a deterministic source-ID mapping. This avoids incompatibilities between database-specific ID formats.

For the first release, use cosine similarity over identically prepared vectors. Validate finite values and reject zero vectors. Normalize once under a documented procedure, record the transformation, and pass the same float32 vectors to every backend and the oracle. Engine-internal representation or normalization differences must still be recorded; the claim is identical input, not bit-identical internal arithmetic.

Filterable fields must be present and non-null in this initial contract. Nullable, nested, or array-valued source fields remain available in the preserved source files, but cannot be silently coerced into supported canonical filters. Fail conversion or require an explicitly documented transformation if the intended workload needs unsupported values.

### Canonical queries

Use JSON Lines: one versioned query object per line. Each contains a unique query ID, either an inline vector or a reference to an external query-vector table, positive `k`, and an optional filter expression. Exactly one vector source is required.

Illustrative query against the MoReVec metadata schema:

```json
{
  "schema_version": 1,
  "id": "movies-q0001",
  "vector_ref": {"file": "query-vectors.parquet", "id": "v0001"},
  "k": 10,
  "filter": {
    "and": [
      {"field": "year", "op": "gte", "value": 2000},
      {"field": "avgrating", "op": "gte", "value": 7.0}
    ]
  }
}
```

The example is formatted over several lines for readability; JSONL files store each complete object on one line. Resolve relative vector-file paths relative to the query file, not the current working directory. Hash referenced files as part of workload identity.

Supported predicates are scalar `eq` and `in`; numeric `lt`, `lte`, `gt`, and `gte`; and Boolean `and`, `or`, and `not`. String equality is case-sensitive and exact, with no tokenization or normalization. Reject type mismatches, null predicates, and unsupported operations. Restrict portable `k` and dimensions to the intersection supported by the selected, pinned adapters.

One pure Python predicate evaluator defines the contract for validation and ground truth. Each adapter translates this expression tree into its native query format. Use parameterized SQL and validated field mappings; queries are data, not executable code. Do not post-filter an unfiltered top-k response in the harness: that changes the intended query.

The common query file contains logical semantics, not backend knobs. Store `ef_search`, candidate budgets, iterative-scan limits, and similar controls in namespaced experiment configuration. A query's metric must match the prepared dataset/index metric.

## 6. Architecture and adapter boundary

Implement a Python 3.12 package with a small CLI over reusable application services. Suggested dependencies are Typer, Pydantic, NumPy, PyArrow, h5py, FAISS CPU, the three official/database-specific clients, and pytest. Lock actual compatible versions during the compatibility milestone.

Keep the following boundaries; they can initially be small modules rather than a large framework:

```text
harness/
  pyproject.toml, uv.lock
  src/fannbench/
    cli/           commands, progress, exit codes
    contracts/     dataset, query, filter, configuration, result schemas
    datasets/      canonical validation and MoReVec conversion
    adapters/      pgvector, qdrant, elasticsearch
    runtime/       Docker lifecycle, resource registry, readiness checks
    oracle/        exact filtered search and recall evaluation
    runner/        sequential execution and measurement protocol
    results/       manifests, incremental records, exports, summaries
  docker/          pinned Compose definitions
  examples/        fixture and experiment configurations
  tests/          unit, contract, integration, end-to-end tests
  docs/           setup, formats, methodology, troubleshooting
```

The service layer must not depend on terminal rendering or argument parsing. It returns structured results and emits progress events so a later UI can reuse it.

Each adapter implements a bounded interface:

- `capabilities()` and `validate_configuration()`.
- `prepare_dataset()` and `wait_until_ready()`.
- `execute_query()` returning IDs, native scores, response metadata, and any supported server timing.
- `collect_diagnostics()` with an explicit capability/status result.
- `inspect_storage()` and scoped `delete_dataset()`.

Docker orchestration is separate from query translation. The initial release manages its own local containers; attaching to arbitrary existing or production servers is out of scope. Use harness-owned Compose projects/volumes, localhost bindings, and local credentials that are never exported in result manifests.

Keep the registry and caches in a platform-appropriate per-user application-data directory, with an explicit `--state-dir` override. Record its resolved location in each manifest. Give each independently removable database copy its own owned volume. Use a registry lock to reject overlapping benchmark/cleanup operations on the same managed resources.

Capability declarations cover supported predicates, dimensions, metrics, native plans/profiles, server timing, and resource observations. Reserve optional declarations for visited-node counts, number of distance computations, search traces, and custom stopping hooks. Absence is `unsupported` or `unavailable` with a reason, never a fabricated zero.

## 7. Import, index configuration, and reuse

The execution lifecycle is:

1. Validate all input files and selected capabilities before starting expensive work.
2. Compute dataset, workload, and configuration identities; create the run manifest.
3. Build or load exact ground truth, then release large oracle buffers before database measurement.
4. For each backend, start only its container, prepare/reuse the dataset, verify readiness, warm up, measure, collect optional diagnostics, and stop the container.
5. Finalize results; perform requested scoped cleanup without deleting results.

Large dataset reads and imports are batched. Avoid loading duplicate copies of the entire dataset into Python memory. Input preflight checks Docker VM resources and available disk; estimates are labeled estimates and checked again after the small-data pilot.

### Indexing policy

Use a documented baseline configuration, not undocumented vendor defaults. Begin with HNSW `M=16` and construction effort around 128 where supported, then pin adapter-specific settings after feasibility testing. These numbers are starting configuration choices, not optimal or equivalent search budgets.

- **pgvector:** bulk load, build the vector/scalar indexes, run `ANALYZE`, verify index validity, and configure strict-order iterative scanning plus explicit limits. Let the optimizer select an access path; do not force an ANN plan by default.
- **Qdrant:** define payload indexes for filterable fields before HNSW construction, enable the intended indexing settings, and wait for indexing/optimization readiness. A healthy HTTP endpoint alone is insufficient. [Qdrant indexing guidance](https://qdrant.tech/documentation/manage-data/indexing/)
- **Elasticsearch:** explicitly map metadata and vectors, use one shard and zero replicas, refresh imported data, and verify visibility and index health. Prefer unquantized HNSW for the initial comparable-input baseline if the selected version supports it. Pin the index type rather than accepting changing dimension-dependent defaults; a quantized alternative is a distinct configuration. Do not force-merge by default. [Dense-vector mapping](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/dense-vector)

Readiness checks must establish expected record count, query visibility, required indexes, and backend-specific completion criteria. Persistent background indexing means “not ready” or a clearly labeled readiness failure, not a valid steady-state benchmark. Ordinary engine maintenance can still occur during queries; disclose it where observable.

Persist a resource registry with states such as `loading`, `indexing`, `ready`, and `failed`. Reuse only when dataset identity, schema, engine/image version, adapter schema, and index-affecting settings match and live readiness checks succeed. Query-only settings do not require reimporting; index settings do. Never treat matching collection names or counts alone as proof of identical contents. All managed data is immutable between imports; external mutation invalidates reuse.

Interrupted imports are not marked ready. Retry idempotent ingestion with stable IDs or rebuild only the exact incomplete harness-owned resource. Avoid broad deletion or a complex row-level resume protocol in version one.

Record total preparation-to-ready time. Where import, index construction, and optimization overlap, report that explicitly rather than adding overlapping durations into a misleading total.

## 8. Benchmark and correctness protocol

### Exact filtered ground truth

For each query, first identify all records satisfying the filter; then compute the exact nearest `min(k, eligible_count)` records among them. Filtering the unfiltered top-k is not equivalent.

Use FAISS CPU Flat search in bounded batches, with an independently checked NumPy implementation on small fixtures. Reuse eligible-subset work where practical, but cap cache memory. Oracle runtime and memory are reported separately and excluded from database latency. Native FAISS installation is a compatibility gate; do not silently substitute an approximate oracle.

Cache ground truth using the dataset hash, query/workload hash, metric, `k`, normalization/precision policy, self-match policy, oracle implementation version, and tie policy. Never reuse full-dataset answers for a sampled dataset.

For each returned response, validate unique known IDs, filter satisfaction, and result count. Record:

- Requested `k`, eligible count, expected maximum count, actual count, duplicates, and predicate violations.
- ID-based recall with denominator `min(k, eligible_count)` and that denominator explicitly recorded. When at least `k` records qualify, this is ordinary Recall@k.
- A tie-boundary flag and a separately named tie-aware recall metric, using a documented numerical tolerance and exact distances. This prevents equally valid boundary ties from being hidden as arbitrary backend failures. Canonical ground-truth ordering is distance then ID.
- For zero eligible rows, recall is undefined (`null` with a reason); an empty result is the correct response. A timeout is a failure, not a successful response with zero recall.

### Timed workload

Defaults for the first release:

| Setting | Default and meaning |
|---|---|
| Backend concurrency | One running benchmark database at a time |
| Query concurrency | One outstanding request; no native bulk-search API |
| Warmup | Five complete workload passes, excluded from measurements |
| Measurement | Thirty complete workload passes; configurable |
| Query order | Seeded shuffle per pass, with identical schedules for every backend |
| Backend order | Seeded order saved in the manifest |
| Timeout | Explicit configurable request deadline; initial default 30 seconds |
| Query retries | Disabled during measurement |
| Result payload | IDs and scores only; no returned vectors or full documents |
| Cache condition | Warmed steady-state workload; no cold-cache claim |

A single query receives five warmups and thirty measurements under these defaults. For stronger experimental conclusions, repeat complete experiments with different seeds/backend orders; repeated requests against one built index are not independent index builds.

Compile logical filters, resolve vectors, and prepare request inputs outside timing. Start a monotonic high-resolution timer immediately before invoking the native client and stop after the response is received and decoded. This intentionally includes ordinary client serialization, transport, server execution, and decoding. Exclude file reads, ground truth, result validation, printing, and report generation. Keep connections open and save client/transport settings; do not describe these latencies as pure engine CPU time.

Store native server-reported timing separately, with its documented meaning. Never subtract guessed overhead or combine incompatible server timing fields into a universal metric. For Elasticsearch, set both the result size and kNN `k` explicitly and use the kNN filter position that preserves filtered-search semantics. [Elasticsearch kNN API](https://www.elastic.co/docs/solutions/search/vector/knn)

Flush raw measurements incrementally with bounded buffering. Do not print or synchronously export large files inside the request timer. Detect timeouts and partial responses; attempt supported cancellation, and do not issue the next measurement while timed-out work may still be running. Abort/restart the affected backend workload if quiescence cannot be established, preserving the partial run.

### Summaries and interpretation

Return per-query and per-backend/workload summaries: successful sample count, median/mean latency, tail percentiles when supported by sample count, errors/timeouts, returned-count distribution, and recall. Preserve raw data regardless of whether a summary is available.

Use a documented quantile estimator. Suppress p95 below 100 successful samples and p99 below 1,000 successful samples, with `insufficient_samples` as the reason. These are conservative reporting thresholds, not guarantees of statistical confidence. Thus thirty repetitions support a per-query median, not a credible per-query p99. A larger pooled workload may support tail summaries, but label them as workload-level and record its query mix. Summaries over successes must also display failures; do not hide timeout censoring behind a fast successful-request percentile.

Report serial workload throughput as successful queries divided by measured workload wall time, including failed-request waits and normal runner gaps but excluding preparation, warmup, and diagnostics. Also report attempted-query throughput and failure rate. This is not maximum system QPS under load.

Compare latency **alongside recall and failures**. Equal numerical settings such as `ef_search=128` and `num_candidates=128` do not imply equal work or quality. Version one measures explicit configurations; it does not promise recall-matched tuning or declare a universal winner. Later calibration must use a separate development workload.

## 9. Optional plans and diagnostic artifacts

`--include-plans` triggers a separate diagnostic pass after timed measurements, normally once per logical query. The timed requests remain unprofiled.

- PostgreSQL: save JSON `EXPLAIN`; if execution/buffer instrumentation is requested, label it as a separate `EXPLAIN ANALYZE` execution.
- Elasticsearch: save the native profile response and identify which portions of kNN execution the pinned version actually exposes. Profiling has overhead and may not describe every internal stage. [Search profiling](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-profile)
- Qdrant: return `plan_status: unsupported` unless the pinned public API genuinely provides a plan. Configuration, collection information, or usage counters may be saved separately, but are not renamed “query plans.”

Every artifact includes query ID, configuration hash, engine version, collection timestamp, collection method, and status/reason. An unsupported plan does not fail an otherwise valid benchmark. A diagnostic rerun is not proof of the exact access path of an earlier timed execution; describe any inferred strategy accordingly.

## 10. Results and experiment documentation

Each run has a unique output directory:

```text
run-ID/
  manifest.json          resolved inputs, versions, hardware, protocol, provenance
  measurements.jsonl     incremental per-request timings, status, returned IDs/scores
  measurements.parquet   typed analysis export of the same measurement data
  summary.json           complete structured summaries
  summary.csv            convenient flat comparison table
  preparation.json       import/index/readiness and storage observations
  diagnostics/           native artifacts and capability/status records
  logs/                  redacted operational logs
  experiment.md          generated human-readable experiment record
```

All schemas are versioned. Preserve native scores with their metric/interpretation; do not compare raw score magnitudes across backends. Canonical distances needed for correctness can be computed outside timing.

The manifest includes dataset/workload checksums; source and sampling details; query and backend order; repetitions and seeds; all tuning parameters; image digests; server/client/package versions; harness release/commit and dirty-state information when available; CPU architecture, OS, memory, Docker engine/VM details and limits; thread settings; relevant timestamps; and completeness/errors.

The experiment record contains the question being tested, exact invocation, workload description, resolved configuration, summary, and limitations. Allow an optional user note or hypothesis. This basic documentation belongs in version one even though richer research reports come later.

Checksums and pins reproduce inputs and configuration, not bit-identical latency or necessarily identical parallel index construction. Record index-build parallelism and available seeds. If an engine cannot guarantee deterministic builds, state that limitation and distinguish reuse of an index from rebuilding it.

## 11. Laptop/university operation and cleanup

Use Docker Compose for single-node services and run the CLI natively. Native Apple Silicon and Linux x86-64 are validation targets. The compatibility gate checks exact image manifests and package wheels; do not silently run an x86 image under emulation on the M1. If emulation is explicitly chosen later, label it and exclude it from native comparisons.

Offer two initial resource profiles, applied equally across selected backends:

- `small`: two database CPUs and 4 GiB database memory; intended for the smoke/small dataset after feasibility checks.
- `standard`: four database CPUs and 8 GiB database memory; the starting point for the 64 GB MacBook and medium dataset.

The host/Docker VM also needs headroom for the runner, oracle, OS, database page cache, and import peaks. Container limits are budgets, not predictions of actual use. Set engine-specific memory controls within those budgets and record them; identical memory limits do not imply identical cache policies. Preflight must not silently shrink a dataset or alter a backend's configuration to make it fit.

Check Docker availability, native architecture, available disk, VM allocation, port conflicts, and required host settings. Report actionable failures on restricted university machines; never change host kernel settings automatically. Run on AC power where possible and document other significant host workloads. Compare systems within one machine/profile; do not treat a laptop run versus a university run as a controlled head-to-head result.

CPU/RAM sampling is optional, explicitly timed/coarse, and labeled with its source. On macOS, distinguish database-container usage from Docker VM and host memory. It is not a reliable per-query CPU attribution mechanism for short queries.

### Storage lifecycle

Preserve database copies by default, but stop their containers after use to release active resources. Stopping does not free persistent disk. Record resource ownership and approximate sizes, distinguishing database-reported index size, volume usage, and logical vector bytes.

Cleanup supports three separately scoped categories: database copies/volumes, derived oracle caches, and canonical converted datasets. The default `clean --resource` and `--cleanup-after-run` remove only the selected database copies. They do not remove original downloads, canonical inputs, or results. Cache/input removal requires an explicit separate option and exact target.

Preview targets, require explicit confirmation for manual destructive cleanup, and enforce ownership checks. Never use a global Docker prune, delete unrelated volumes, or drop an arbitrary database by name. A volume may be deleted only when every resource it contains belongs to the requested cleanup scope. Preserve partial results on interruption; cleanup failures are separately reported.

Document that dropping a table or collection does not always shrink its backing files immediately. Deleting a harness-owned volume reclaims its Docker storage, but Docker Desktop's host disk image may retain allocated space until separately compacted. Report observed reclaimed space without promising immediate host-file shrinkage.

## 12. Packaging and tests

Package a normal Python project with `pyproject.toml`, a console entry point, and a committed `uv.lock`. Provide a short professor-facing quick start, example configurations, sample query files, and a tiny freely redistributable fixture. Do not require cloud accounts or a GPU.

The eventual quick-start path should be approximately:

```sh
uv sync --locked
uv run fannbench doctor
uv run fannbench run --config examples/smoke.yaml
```

Docker and uv are documented prerequisites; do not install them or change system configuration without the user's action. Pin validated container releases by digest, including architecture information, and retain a compatibility matrix. Resolve exact database/client/FAISS versions during milestone 0 rather than claiming untested combinations are supported. [uv project locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)

Testing layers:

1. **Unit tests:** schemas, hashes, ID mapping, normalization, filter semantics, configuration precedence, quantiles, recall/ties, zero-eligible queries, deterministic ordering, and redaction.
2. **Adapter contract tests:** translation of every supported predicate, correct result size, parameter handling, unsupported capabilities, and fidelity to the pure predicate evaluator. Small exhaustive/exact-mode tests isolate semantic errors from approximation.
3. **Docker integration tests:** import, readiness, query, reuse, changed-dataset/config invalidation, cleanup, and native diagnostics for each adapter.
4. **Approximate-search tests:** no invalid or duplicate results; expected recall on stable fixtures with conservative settings. Do not require arbitrary ANN settings to reproduce exact top-k or assert fragile absolute timing thresholds.
5. **Failure/lifecycle tests:** bad paths, malformed vectors, duplicate IDs, incompatible fields, missing Docker, unavailable ports, resource exhaustion, import interruption, timeout with work still running, partial results, and cleanup that must leave unrelated resources intact.
6. **End-to-end test:** one command benchmarks the fixture on all three systems and produces validated outputs, explicit capability statuses, and a reproducible rerun manifest.

Run unit tests on every change and Docker integration tests in appropriate CI/release environments. Validate both native Apple Silicon and Linux x86-64 before advertising both as supported. A clean-machine setup rehearsal, ideally on the professor's target platform, is a release acceptance step.

## 13. Future statistics and agent integration

These extensions shape the saved identities and capability boundaries now; they do not expand the first release into an analysis or learning project.

### Three distinct kinds of information

| Kind | Examples | Collection and availability |
|---|---|---|
| Dataset-level summaries | Attribute frequencies, numeric distributions, cluster sizes, cluster-attribute relationships, vector density summaries | Offline preprocessing; record cost, sampling, and dependence on fitted clustering choices |
| Query/workload-conditioned properties | Filter selectivity, GLS, distance gaps, neighborhood density, rank of the kth eligible point in unfiltered order | Depend on query/filter/metric/neighborhood; some require expensive evaluator-only computation |
| Engine runtime telemetry | Visited/valid counts, queue composition, distance statistics, number of distance computations (NDC) | Require engine support or instrumentation; available during or after a particular execution |

E2E's especially relevant features are the observed valid fraction among visited vertices, the prospective valid fraction in the search queue, and distance/queue statistics from early probing. Its adaptive termination uses a predicted search-work budget. These are not interchangeable with a static attribute histogram or an offline neighborhood statistic. A stock database API may expose neither those internal states nor an in-loop stopping hook. [E2E paper](https://arxiv.org/abs/2602.06721)

Therefore, preserve two future routes: an agent choosing exposed settings before a query, and an instrumented engine enabling decisions during traversal. The second requires a separate feasibility milestone, likely starting with one engine. Do not claim that the initial three adapters implement E2E.

### GLS definition and scope

Implement GLS later according to the paper, with an explicit neighborhood parameter `L` separate from the requested result count `k`:

```text
global_selectivity = matching_records / dataset_records
local_selectivity  = matching_records_in_unfiltered_L_nearest_neighbors / L
GLS(query, filter, L) =
    (local_selectivity - global_selectivity)
    / (local_selectivity + global_selectivity)
```

Require a nonempty dataset, `1 <= L <= N`, and positive global selectivity; otherwise return an explicit undefined status. The neighborhood is the unfiltered neighborhood, not the filtered ground-truth result set. Positive GLS indicates local enrichment, negative GLS depletion. A dataset/workload summary aggregates these per-query values; it is not an intrinsic scalar of the dataset independent of its queries and filters. [GLS definition, Section 4](https://arxiv.org/abs/2602.11443)

Save the mean and distribution alongside global/local selectivities, query/filter identities, neighborhood size, self-match policy, and exact-versus-approximate method. Flag cases where `L * global_selectivity` is small: empty local neighborhoods can drive GLS to -1 without establishing strong structural anti-correlation. Do not silently smooth the published formula. Cache unfiltered neighborhoods separately from filtered recall ground truth.

Other later candidates include attribute skew, cluster-attribute contingency tables, within/between-cluster distances, local density, intrinsic-dimension estimates, and the unfiltered rank needed to encounter k eligible results. Each needs a definition, compute budget, and validation. Treat them as potential explanatory features, not universal predictors of FANNS cost; their relevance depends on algorithm, filter, and search strategy. [Hardness-controlled benchmark study](https://arxiv.org/abs/2606.14193)

### Extension contract and leakage protection

A future analyzer consumes immutable dataset/workload references and returns a versioned statistics artifact. Each feature records scope, definition/version, parameters, sampling seed, precision/approximation, compute time, and availability stage: `offline`, `pre_query`, `during_query`, `post_query`, or `evaluator_only`.

Keep train, calibration, and test workload identities. The harness's access to exact neighbors and observed recall does not authorize a later agent to see them before answering test queries. If exact GLS or another expensive property is given to an agent, explicitly define and charge for that access, or label it an oracle-information experiment. Measure instrumentation and feature-extraction overhead separately and include it in agent-policy performance claims.

Reserve fields and small interfaces now; defer a plugin registry, model framework, automated parameter sweeps, and training pipelines until there is a concrete use case.

## 14. Implementation sequence and acceptance gates

No deadline is assumed. Complete milestones in order; retain working CLI paths as adapters are added.

| Milestone | Work | Completion evidence |
|---|---|---|
| 0. Compatibility and data check | Inspect the real MoReVec files/terms; validate native images and Python dependencies; choose exact pins and baseline settings | Compatibility matrix, source-file inventory, reproducible small-data sizing trial, no hidden emulation |
| 1. Contracts and oracle | Canonical schemas, synthetic fixture, filter evaluator, query loading, exact oracle, result schemas | Unit tests cover semantic edge cases and independently verified ground truth |
| 2. First end-to-end adapter | pgvector lifecycle, import/reuse, readiness, execution, raw results, scoped cleanup | One CLI command produces timings and recall, then safely reruns using the same index |
| 3. Cross-system execution | Qdrant and Elasticsearch adapters, payload/scalar mappings, capability checks | All three ingest the identical snapshot and pass filter/result contract tests |
| 4. Measurement and diagnostics | Warmups/repetitions, summaries, exports, optional plans/profiles, timeout handling, resource observations | Auditable timing boundaries, complete manifests, tested incomplete-run and cleanup behavior |
| 5. Real-data and setup release | MoReVec converter/workloads, documentation, packaging, native-platform rehearsals | Small real-data run on all three; medium-scale pilot; clean setup and documented resource limits |
| Later A. Statistical analysis | GLS and selected dataset/query statistics | Verified formulas, cost/provenance records, exact/estimated separation, workload distributions |
| Later B. Agent/instrumentation research | Calibration splits, tuning policies, engine hooks where available | Fair information budgets, frozen evaluation protocol, measured feature overhead and recall |

If a backend fails the native/resource feasibility gate, document the specific version/platform limitation and continue with the working subset. Do not silently replace it with a different service. Resolving or explicitly accepting that limitation is necessary before claiming the full three-backend release is complete.

## 15. Definition of done for the initial release

The initial release is complete when:

- A new user can install the package, run `doctor`, and execute the documented smoke experiment without editing source code.
- The CLI accepts a backend subset, a canonical dataset manifest, and one or more query files.
- All three adapters can execute the same validated logical workload over the same snapshot on documented supported hardware.
- Output includes raw request timings, meaningful summaries, recall/correctness, errors, preparation/storage observations, and sufficient provenance to repeat the experiment.
- Optional diagnostics produce native artifacts or an honest unsupported status, without contaminating the timed pass.
- Dataset reuse is validated, resource-constrained sequential operation works, and cleanup only removes explicitly selected harness-owned data.
- The real-data importer and at least one MoReVec workload are exercised; performance results are not based only on the synthetic fixture.
- Unit, integration, lifecycle, and end-to-end checks pass, and setup instructions have been rehearsed on the advertised architectures.

The immediate next action after approval of this plan is milestone 0—not implementing an agent, computing every proposed statistic, or running a large benchmark sweep.
