# FANNBench three-path overhead-isolation implementation plan

Date: 2026-09-20  
Status: implemented and live-qualified on the local arm64 host  
Scope: testing harness and instrumented engine integrations only; agent training and policy synthesis remain out of scope

Implementation evidence: FANNBench 0.4.0 uses schema 4 and `same_execution_v2`; all three custom images build; 73 non-integration tests pass; and the live pgvector, Weaviate, and Elasticsearch route matrix passes with native/no-op/canonical-agent result equivalence, no-op/agent observation equivalence, server-installed policies, and hash-only timed requests. Focused Go and Java engine contract tests cover observation/evaluation separation, installed-policy lookup, stop, rejection, and fallback behavior. A separate 30-pass synthetic qualification run completed all 2,160 scheduled measurements with no missing, invalid, or failed samples and generated both whole-workload and policy-eligible paired reports. It validates the harness workflow but is not an agent-performance claim.

Qualified local image IDs are pgvector `sha256:a1968116e8d4...`, Elasticsearch `sha256:2cb70c05fa37...`, and Weaviate `sha256:a63daf971be5...`. The definitive synthetic qualification record is run `20260920T190218Z-73a043ad` in the temporary local validation workspace; its manifest pins the full image IDs and patch digests.

## 1. Objective

Revise the instrumented execution design so one paired run can separately estimate:

1. the incremental cost of collecting the runtime observations that a future agent will consume;
2. the incremental cost of invoking the policy interpreter; and
3. eventually, the net effect of applying an agent-generated stopping decision.

The three primary instrumented paths are:

| Mode | Collect agent features | Run policy interpreter | Apply policy stop |
|---|---:|---:|---:|
| `native` | no | no | no |
| `policy_noop` | yes | no | no |
| `policy_agent` | yes | yes | yes when the installed policy returns `stop` |

During this phase, `policy_agent` uses a canonical installed policy whose only action is `continue`. It is therefore behaviorally equivalent to `policy_noop`, but it is intentionally not implementation-identical: it must invoke the real interpreter at every eligible checkpoint.

The existing `fixed_budget` mode remains available as an engineering control for the stopping hook. It is not one of the three overhead-isolation paths and is excluded from observation/interpreter-overhead interpretations.

## 2. Claims this design supports

For a matched query, index, route, and sample:

- `policy_noop - native` estimates incremental agent-observation overhead;
- `policy_agent(always_continue) - policy_noop` estimates interpreter overhead for the canonical placeholder program;
- `policy_agent(always_continue) - native` estimates the total inactive-agent integration overhead.

After learned policies are introduced:

- `policy_agent - native` is the principal end-to-end deployment effect;
- `policy_agent - policy_noop` combines interpreter cost and the effect of applying decisions and must not be labelled pure interpreter overhead;
- measuring the interpreter cost of a particular learned policy independently would require a later shadow-policy control or a separate always-continue calibration policy of comparable complexity.

These are paired statistical estimates, not exact constants. The report must include sample counts, dispersion, and confidence intervals. The word `exact` is reserved for correctness properties, not latency-overhead estimates.

## 3. Important baseline boundary

The current custom `native` path already updates distance, expansion, checkpoint, and route telemetry. If that remains true, `native` versus `policy_noop` cannot isolate the cost of collecting those observations.

Revise `native` so the engine still:

- acknowledges the requested mode and request nonce;
- identifies the executed route;
- reports the native completion reason; and
- uses the same custom binary, physical index, request wrapper, and result assembly path.

But `native` must bypass:

- policy checkpoint accounting;
- construction of policy feature snapshots;
- policy evaluation; and
- checkpoint traces.

An unavoidable hook call and a cheap mode branch may remain in the custom binary. Therefore the supported estimand is **incremental agent-observation overhead beyond the dormant custom hook and common request wrapper**, not the total cost of every source modification. Stock-versus-custom-native fidelity remains a separate qualification exercise.

## 4. Revised execution semantics

### 4.1 `native`

1. Enter the same query-scoped control wrapper used by all instrumented modes.
2. Record only mode, nonce, route, and final native reason.
3. At a patched HNSW observation call, mark that the HNSW route was reached and return immediately before counter mutation, feature construction, locking that exists only for observation, or policy evaluation.
4. Never acknowledge a policy hash.
5. Report policy opportunity as unknown (`null`) because the mode deliberately does not count to the checkpoint threshold.
6. Report observation and evaluation counts as zero or absent according to the protocol schema.

### 4.2 `policy_noop`

1. Maintain all counters required by the frozen feature profile.
2. Detect the same safe checkpoints that `policy_agent` uses.
3. Materialize the complete feature snapshot at every checkpoint, including typed unavailable values where appropriate.
4. Record observation count and observation timing.
5. Discard the snapshot after optional trace capture.
6. Do not load or invoke a policy interpreter.
7. Never stop the search and never acknowledge a policy hash.

This becomes the observation-only control. It must no longer claim that a policy was evaluated.

### 4.3 `policy_agent`

1. Execute the exact observation routine used by `policy_noop`.
2. Pass the resulting feature snapshot to the installed interpreter.
3. Record evaluation count, evaluation timing, decision, fallback, and error state.
4. Apply `stop` only when evaluation succeeds and returns `stop`.
5. During this phase, use the canonical `continue` artifact, so result IDs, scores, search work, route, and native completion reason must match `policy_noop` under deterministic test settings.

“The agent policy is the same as no-op” means the observable decision is the same (`continue`), not that the two modes skip the same work.

### 4.4 `fixed_budget`

Keep the existing deterministic stop control. It may reuse checkpoint counters, but it must report that neither an agent feature snapshot nor a policy evaluation occurred unless the implementation explicitly uses those operations. Do not include it in observation-overhead calculations.

## 5. Protocol and schema revision

Bump the engine telemetry contract from `same_execution_v1` to `same_execution_v2` and the measurement/run schema from version 3 to version 4. Do not silently reinterpret old fields in schema 3 records.

### 5.1 Request fields

Retain:

- `mode`
- `request_nonce`
- `feature_profile`
- `k`
- `predicate_leaf_count`
- `experiment_profile`
- `trace_level`
- `fixed_budget` for `fixed_budget`
- `policy_hash` for `policy_agent`

Timed `policy_agent` requests must contain only the policy hash, never policy bytecode or a program digest payload.

### 5.2 Response fields

Retain mode, route, stop, nonce, policy hash, fallback, and error acknowledgement. Add or clarify:

| Field | Meaning |
|---|---|
| `observation_applied` | At least one complete agent feature snapshot was materialized |
| `policy_applied` | The installed policy interpreter ran at least once; false for `policy_noop` |
| `policy_opportunity` | At least one valid policy checkpoint was reached; `null` in `native` because it intentionally does not count checkpoints |
| `checkpoint_count` | Number of observation checkpoints; absent/null in `native` |
| `feature_collection_count` | Number of complete snapshots materialized |
| `feature_collection_ns` | Diagnostic server-side time spent materializing snapshots |
| `policy_evaluation_count` | Number of interpreter invocations; zero in `policy_noop` |
| `policy_evaluation_ns` | Diagnostic server-side interpreter time |

`feature_collection_ns` and `policy_evaluation_ns` are diagnostic decompositions. End-to-end paired latency remains the primary overhead measure because internal timers have their own cost and may not capture every surrounding operation.

### 5.3 Validation invariants

- `native`: `observation_applied=false`, `policy_applied=false`, no policy hash, no checkpoints, no feature or evaluation counts above zero.
- `policy_noop`: no policy hash, `policy_applied=false`, evaluation count zero; when opportunity is true, observation count and checkpoint count are positive and equal.
- `policy_agent`: valid installed policy hash; when opportunity is true and no fallback occurs, observation count, checkpoint count, and evaluation count are positive and equal up to the checkpoint that stopped the query.
- `policy_stop`: valid only for `policy_agent` with a successful evaluation and an applied stop decision.
- exact/flat routes may report no opportunity and zero observation/evaluation counts.
- runtime failure records the error, disables further evaluation for that query, continues native search, and remains visible as fallback.

### 5.4 Python model changes

Update:

- `harness/src/fannbench/schema.py`
- `harness/src/fannbench/models.py`
- `harness/src/fannbench/runner.py`
- `harness/src/fannbench/results.py`

Add `observation_applied` to `ExecutionMetadata` and `Measurement`; carry the new counters without converting nanoseconds to floats. Change model validation so instrumented `native` may have `policy_opportunity=None` and no checkpoint/work telemetry. Preserve strict rejection of impossible mode/field combinations.

## 6. One shared feature-collection routine per engine

The central implementation rule is that `policy_noop` and `policy_agent` call the same routine. Do not duplicate feature assembly in mode-specific branches.

Conceptual engine logic:

```text
observe_batch(count):
    record_route()

    if mode == native:
        return continue

    update_observation_counters(count)

    if checkpoint_not_reached:
        return continue

    if mode == fixed_budget:
        return budget_decision()

    features = collect_features()
    record_feature_collection()

    if mode == policy_noop:
        return continue

    decision = evaluate_installed_policy(features)
    record_policy_evaluation(decision)
    return decision
```

The native early return should occur before observation-only locks and allocations where engine architecture permits it. Route tracking must remain query-local and concurrency-safe.

## 7. Backend-specific implementation

### 7.1 pgvector

Files:

- `harness/engines/pgvector/patches/0001-same-execution-observability.patch`
- `harness/src/fannbench/adapters/pgvector.py`
- pgvector engine README, feature matrix, build lock, and regression tests

Actions:

1. Split route acknowledgement from `FannbenchHnswObserveDistances` counter collection.
2. For `native`, set `hnswReached` and return without updating distance/checkpoint/expansion counters.
3. Introduce one `CollectPolicyFeatures` helper used by no-op and agent modes.
4. In no-op, call the helper and discard its returned feature structure.
5. In agent mode, pass that structure to `EvaluatePolicy`.
6. Measure feature and evaluation nanoseconds with PostgreSQL's monotonic timing facility, storing integer nanoseconds.
7. Keep `fannbench_install_policy` as the server-side installation mechanism.
8. Update `fannbench_last_execution` to emit `same_execution_v2` and the revised flags/counters.
9. Verify transaction abort, cancellation, and connection reuse clear all observation timing and count state.

### 7.2 Elasticsearch

Files:

- `harness/engines/elasticsearch/patches/0001-same-execution-observability.patch`
- `harness/src/fannbench/adapters/elasticsearch.py`
- Elasticsearch engine README, feature matrix, build lock, and Java tests

Actions:

1. Refactor `FannbenchKnnSearchStrategy.observeHnswBatch` so native exits before synchronized observation accounting when safe.
2. Add one feature-construction method called by both no-op and agent.
3. Make no-op materialize the feature record without calling `program.evaluate`.
4. Make agent evaluate the same record and measure evaluation nanoseconds.
5. Add a process-local bounded policy registry keyed by policy hash.
6. Add a pre-run installation API in the instrumented Elasticsearch build. Installation parses and validates bytecode, verifies its digest/hash, and returns the installed hash and interpreter version.
7. Remove `policy_program` and `policy_program_sha256` from timed search extensions. The search extension carries only `policy_hash` and fails before traversal if it is unknown.
8. Scope the first implementation explicitly to the existing one-node experiment profile. Distributed installation remains unsupported until registry propagation is designed.
9. Add Java tests for native bypass, no-op observation, agent-continue evaluation, unknown hash rejection, malformed installation, fallback, and request concurrency.

### 7.3 Weaviate

Files:

- `harness/engines/weaviate/patches/0001-same-execution-observability.patch`
- `harness/src/fannbench/adapters/weaviate.py`
- Weaviate engine README, feature matrix, build lock, and Go tests

Actions:

1. Refactor `State.ObserveDistances` so route recording is separate and native returns before observation-only locking/counter work where safe.
2. Add one `collectFeatures` helper shared by no-op and agent.
3. No-op materializes and records the snapshot but never calls `evaluate`.
4. Agent evaluates the same snapshot and records integer timing counters.
5. Add a concurrency-safe, bounded in-process policy registry plus a pre-run installation endpoint.
6. Remove `X-Fannbench-Policy-Program` and its digest from timed requests; retain only `X-Fannbench-Policy-Hash`.
7. Reject unknown hashes before search and report the acknowledged installed hash.
8. Add Go tests covering sweeping HNSW, ACORN when qualified, flat/no-opportunity, concurrent requests, malformed installation, fallback, and cleanup.

## 8. Policy installation and canonical placeholder

Add a checked-in canonical artifact, for example:

`harness/examples/policies/always-continue.json`

Its root is the literal `continue`, it uses the frozen feature/checkpoint profile, and its hash is recorded in the run manifest. The runner continues to require an explicit policy for `policy_agent`; the canonical file is supplied by calibration and integration commands rather than hidden as an implicit default.

`Adapter.install_policy` must mean server installation for every instrumented backend:

1. compile once in the harness;
2. transmit before warm-up;
3. parse and validate once in the engine;
4. acknowledge hash, digest, interpreter version, and instruction count;
5. reference by hash during warm-up and measurement;
6. reject an unknown or mismatched hash before executing a query.

The manifest records installation acknowledgement separately for every backend. Per-query policy transfer/parsing is prohibited by the v2 protocol.

## 9. Runner and CLI behavior

Files:

- `harness/src/fannbench/cli.py`
- `harness/src/fannbench/runner.py`
- `harness/src/fannbench/engine_builds.py`
- `harness/engines/*/upstream.lock.json`

Actions:

1. Keep existing public mode names to avoid unnecessary CLI churn.
2. Update help text to define no-op as observation-only rather than a policy evaluation.
3. Install the agent policy before all warm-up passes.
4. Keep randomized within-pair mode order; record the realized order and policy installation acknowledgement.
5. Record whether the installed artifact is structurally always-continue. This permits the report to label agent-versus-no-op as interpreter overhead only for calibration runs in which no policy stop occurred.
6. Require `same_execution_v2` in doctor/build manifests before permitting the revised modes.
7. Do not automatically subtract measured overhead from reported agent latency. Always report observed end-to-end latency.

## 10. Statistics and reporting

Files:

- `harness/src/fannbench/statistics.py`
- `harness/src/fannbench/results.py`
- reporting tests and result documentation

Add paired comparisons:

| Baseline | Treatment | Interpretation condition |
|---|---|---|
| `native` | `policy_noop` | `observation_overhead` |
| `policy_noop` | `policy_agent` | `interpreter_overhead` only when policy is always-continue and no stops occurred; otherwise `agent_incremental_effect` |
| `native` | `policy_agent` | `inactive_agent_overhead` for the always-continue policy; later `net_agent_effect` |
| `native` | `fixed_budget` | existing deterministic stopping control |

For overhead rows report:

- candidate, valid, missing, invalid, route-mismatched, and no-opportunity pair counts;
- mean and median paired latency delta;
- relative paired latency delta;
- 95% query-level bootstrap interval;
- recall delta and result-equivalence failures;
- aggregate feature collection and evaluation counts/times;
- route-stratified results.

Change comparable-route filtering so a `native` baseline is not required to claim a checkpoint opportunity. It must have the same server-observed eligible route as the treatment; the no-op/agent member must report a real opportunity. Exact and flat routes remain visible in whole-workload results but are excluded from policy-eligible overhead estimates.

Use a minimum repeated calibration configuration sufficient for uncertainty reporting. The one-pass route integration fixture remains a correctness test and must not be used to make overhead claims.

## 11. Test plan

### 11.1 Python contract tests

Extend:

- `harness/tests/test_runner.py`
- `harness/tests/test_execution_observability.py`
- `harness/tests/test_statistics.py`
- adapter unit tests

Test the full mode/field invariant matrix, schema-v3 rejection or explicit legacy loading, v2 parsing, paired interpretation labels, and route/opportunity filtering.

### 11.2 Native engine unit tests

For C, Java, and Go implementations, feed the same deterministic sequence of observation batches and assert:

- native records a route but no feature snapshots or evaluations;
- no-op records the expected snapshots and zero evaluations;
- agent with the canonical policy records the same snapshots plus matching evaluations;
- no-op and agent return continue at every checkpoint;
- agent runtime failure falls back and continues;
- fixed budget still stops at the expected safe boundary;
- query state is isolated across concurrent requests and cleared after failure.

### 11.3 Live integration matrix

Revise `harness/tests/integration/test_instrumented_observability.py` to run native, no-op, fixed-budget, and agent with the canonical continue policy on each qualified route.

For every deterministic query assert:

- native, no-op, and agent IDs and scores are equal;
- their observed routes match;
- no-op and agent distance/expansion/checkpoint observations match;
- no-op has positive feature collection and zero policy evaluations on eligible routes;
- agent has matching positive feature collection/evaluation counts;
- agent acknowledges the canonical hash and never reports `policy_stop`;
- no policy program appears in a timed request;
- fixed budget continues to demonstrate that the stop hook can change work.

Add installation/failure cases for unknown hash, malformed bytecode, digest mismatch, restart without installation, timeout/cancellation, and post-failure connection or worker reuse.

### 11.4 Overhead qualification run

Create a non-smoke calibration profile with repeated passes and balanced mode order. Run it separately for each backend on one fixed host with background load controlled. Acceptance is not “overhead equals zero”; acceptance is:

- all paired samples are accounted for;
- result equivalence holds for all three continue paths;
- observation and interpreter estimates are emitted with confidence intervals;
- route-stratified estimates are available;
- no timed request performs policy installation, transfer, or parsing; and
- repeated runs produce directionally stable estimates or explicitly show that the effect is below the platform's measurement resolution.

## 12. Documentation changes

Update:

- `harness/engines/protocol.md`
- `harness/engines/README.md`
- each engine README and feature matrix
- CLI documentation and troubleshooting guide
- the active portable-policy and execution-observability plans
- the audit status after qualification

Use the terms:

- **observation-only control** for `policy_noop`;
- **canonical continue policy** for the current `policy_agent` artifact;
- **observation overhead** for native-versus-no-op;
- **placeholder interpreter overhead** for no-op-versus-agent in the calibration phase; and
- **net agent effect** for native-versus-agent after learned stopping policies exist.

Do not describe the current no-op as executing a policy, and do not describe a one-pass smoke test as an overhead measurement.

## 13. Ordered implementation sequence

1. Freeze this semantic decision and update the protocol document first.
2. Add schema-v4 Python models and validation tests.
3. Add the canonical continue artifact and manifest provenance.
4. Refactor paired statistics and labels before generating new results.
5. Implement real server-side policy installation for Elasticsearch and Weaviate; retain pgvector installation.
6. Refactor pgvector into shared observation plus optional evaluation and update native telemetry.
7. Refactor Elasticsearch equivalently and add Java tests.
8. Refactor Weaviate equivalently and add Go tests.
9. Rebuild all custom images and update patch/image/source lock records.
10. Run Python unit/lint/package checks.
11. Run the live route matrix and failure/isolation tests for all three engines.
12. Run the repeated overhead-calibration profile and inspect JSONL, Parquet, summary JSON/CSV, paired effects, and manifests.
13. Update active research plans and close the no-op-control audit issue only after the acceptance gates below pass.

## 14. Acceptance gates

The revision is complete only when all of the following hold:

1. `native` does not materialize agent feature snapshots or evaluate a policy.
2. `policy_noop` materializes the exact feature snapshot path used by agent mode and never evaluates or stops.
3. `policy_agent` with the canonical artifact evaluates at every eligible checkpoint and always continues.
4. Native, no-op, and canonical-agent results are equivalent on every qualified route.
5. No-op and canonical-agent work/checkpoint observations are equivalent under deterministic fixtures.
6. Telemetry distinguishes observation from evaluation without overloading `policy_applied`.
7. Elasticsearch and Weaviate cache validated policies before warm-up; timed requests carry only a hash.
8. Paired reports separately label observation overhead, placeholder interpreter overhead, and total inactive-agent overhead.
9. Missing, invalid, timed-out, and route-incomparable pairs remain visible.
10. Unit, engine-native, integration, lint, and package checks pass on the qualified architecture.

## 15. Explicit non-goals

This revision does not implement:

- agent training or policy synthesis;
- data-shape learning;
- learned-policy shadow execution;
- final real-data or held-out evaluation;
- distributed policy-registry propagation;
- cross-architecture qualification beyond separately scheduled release work; or
- a claim about which database benefits most.

It establishes the controlled measurement substrate needed for those later stages.
