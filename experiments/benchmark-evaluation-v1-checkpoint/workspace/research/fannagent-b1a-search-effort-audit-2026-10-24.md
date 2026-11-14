# B1a — fixed-index query-dependent search-effort feasibility audit

Completed October 24, 2026, America/New_York. Register: **NEXT-SCOPE-01**.

**Query-dependent search effort is feasible at the engine level without rebuilding the existing index. It is not implemented or qualified through the current agent API.** The appropriate first control is `hnsw.ef_search`, selected before an ordinary native query. The next step is **B1b / NEXT-EFFORT-01: freeze and implement a separately versioned native-effort interface, qualify it, and acquire a matched 320-versus-640 frontier on the current index before fitting a router**.

B1a passes **scoped feasibility only**. Speed, recall preservation, setting isolation, selector overhead and serving acceptance remain unestablished. Original execution remains adopted; P2/P3 verdicts and M1/M2/M3 remain unchanged. This audit changes documentation only: no code, tests, model fitting, policy search/simulation, database connection, new measurement, provider request, Torch job or protected query-value access. No user commands are needed now.

## Permanent record and boundaries

- [Machine-readable findings](fannagent-b1a-search-effort-audit-2026-10-24/audit.json).
- [Source/input inventory](fannagent-b1a-search-effort-audit-2026-10-24/input-and-source-inventory.json): 324 code/source files, 29 explicit reference inputs and the preserved historical sweep inventory.
- [Audit receipt](../agent/docs/verification/b1a-search-effort-audit-v1.json): final preservation checks, decision, zero-experiment boundary and artifact hashes.
- [Roadmap v1.13](fannagent-performance-research-roadmap-2026-10-22.md).

Read-only inspection covered the live checkout's API/backend/build recipe, the frozen original backend used by the P2/P3 lineage, current physical-index/runtime identities, saved historical effort/size studies and already exposed query metadata. The 122 inputs in the old effort analysis inventory and all six saved analysis outputs match their recorded hashes. Existing confidence intervals were read, not recomputed. The old archive digest is taken from its prior verification receipt, not a fresh archive verification. No experiment or code from those studies was executed/imported.

## 1. The engine has a search-time control

The pinned upstream pgvector commit is `8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c` (version 0.8.6); the local [build recipe](../agent-pgvector/src/fannagent_pgvector/engine/build.sh) and [provenance](../agent-pgvector/src/fannagent_pgvector/engine/provenance.json) name it. Its `hnsw.ef_search` is a user-settable integer parameter in 1–1000. The scan passes that parameter into the initial layer-zero search. It is a query-time candidate-list size, not an index construction parameter or exact distance-work budget. [Pinned GUC source](https://raw.githubusercontent.com/pgvector/pgvector/8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c/src/hnsw.c), [pinned scan source](https://raw.githubusercontent.com/pgvector/pgvector/8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c/src/hnswscan.c).

| Control | Feasibility at existing index | Decision for first comparison |
| --- | --- | --- |
| `hnsw.ef_search` | Search-time setting; no index rebuild required by this mechanism | Vary only this control; proposed levels 320/640 |
| `hnsw.iterative_scan` | Search-time algorithm/ordering mode; can seek more filtered results | Keep `off`; changing it creates another intervention |
| `hnsw.max_scan_tuples` | Approximate iterative-resumption limit; does not cap the initial scan | Do not treat it as a replacement initial-search work budget |
| `hnsw.scan_mem_multiplier` | Iterative-scan memory control | Keep unchanged with iterative scans off |
| `m`, `ef_construction`, graph/index design | Build-time controls | Excluded from this fixed-index proposal |

The current local instrumentation patch retains the initial call's `hnsw_ef_search` argument ([patch](../agent-pgvector/src/fannagent_pgvector/engine/patches/0001-same-execution-observability.patch)). This is source-level feasibility evidence. Current saved runs establish ordinary 640 behavior with the pinned module; they do not replace native qualification at 320 on that module. No live remote availability, privilege or setting check was made in this audit.

Changing effort changes the search algorithm's candidate set and termination. **An ef 640 stopping prefix is not an ef 320 intervention.** The P3 stopping labels and timing proxies cannot become a multi-effort training matrix. This is an inference from the scan's effort-dependent search and the separately measured historical level outcomes, not a new measurement.

## 2. Current API and timing boundaries need a separate interface

The [strict query schema](../agent/src/fannagent/api/primitives/data.py) exposes vector, `k` and filter, with no effort field. The [runtime profile](../agent/src/fannagent/api/profiles.py) and [tree language](../agent/src/fannagent/api/primitives/policy_tree.py) permit only stop/continue actions. Existing fixed-budget stopping is another stopping intervention, not `ef_search` selection.

Both the [current backend](../agent-pgvector/src/fannagent_pgvector/backend.py) and the [frozen original backend](../trials/torch-reviews-activation-timing-calibration-v1/torch-activation-timing-calibration-v1/frozen/vendor/fannagent_pgvector/backend.py) inspect source settings, bind a connection and apply them through `_settings`/`_bind`. The frozen native path executes ordinary autocommit SQL; its reported timer resets immediately before search, excluding earlier setup. An outer application timer is therefore essential to charge a new selector, validation, connection binding and setting operation.

PostgreSQL session settings persist on a reused connection. `SET LOCAL` instead lasts for a transaction and has no useful effect outside a transaction block. A transaction-local effort override must enclose the search and charge its transaction/control work; it cannot inherit the old autocommit timing boundary for free. [PostgreSQL 17 SET documentation](https://www.postgresql.org/docs/17/sql-set.html).

**Recommended prototype transport:** two immutable effort-bound reader sessions, 320 and 640, sharing one private restored current-index database and observation identity, with sequential dispatch. Keep the preserved origin manifest unchanged and record effective effort as an explicit treatment override. Verify actual settings on bind/reconnect and in conformance; account for both reader initializations, selector/admission and reconnects. This avoids a setting SQL round trip on every reused query, but its benefit and lifecycle correctness are unmeasured. It is a proposed experimental adapter, not an existing supported public interface.

A transaction-local design is a viable alternative only under an explicitly changed timing/transaction contract. Reconnecting for every query would also change cost and lifecycle semantics; the old effort sweep's connection-per-level preparation is not evidence that connection-per-query routing is cheap.

**Reference scope:** “original640” here means the unchanged effort640 study reference used in P1–P3, not the upstream default or a verified production default. The old sweep records source effort320, and the current frozen harness explicitly sets640. Keep the inspected origin, declared study reference and per-arm effective override as separate identities. B1b must record the actual source default too; a gain versus study640 alone is not proof of a gain versus a different production/default setting.

Use the frozen **original** execution as the unwrapped baseline. Existing optimized/dispatch experimental classes are not automatically adopted merely because their source offers useful examples. No existing source manifest, runtime profile, model artifact or acceptance contract is altered by this audit.

## 3. Cheap inputs exist, but provide only three workload contexts

The already exposed frozen package contains 600 cases: 200 with no filter, 200 with actual `m_000000 >= 32`, and 200 with actual `m_000000 >= 108`; all have `k=10`. Query parsing can read these fields before ANN search, without a stopping-profile collector. The [existing parser](../agent-pgvector/src/fannagent_pgvector/native/query_context.py) validates that narrow predicate family. Preserve an explicit filter-presence flag: its unfiltered threshold sentinel 0 does not make an arbitrary threshold-zero predicate semantically identical to no filter.

| Possible input | Availability / limit |
| --- | --- |
| Actual validated filter AST, field/operator/threshold, filter presence and `k` | Available in the request; parsing/normalization cost must still be charged |
| Predicate context in this workload | Three distinct contexts; can support a small predicate-based dispatch table |
| Raw query vector | Present, but no cheap qualified vector-difficulty predictor is established; normalized dimension/norm are not evidence of a useful selector |
| Static/progress stopping observations | Acquired during ANN search; not free pre-query inputs for choosing initial effort |
| Exact selectivity, exact descriptors, truth/native work | Offline/evaluator evidence, not qualified cheap serving inputs |
| Group/query IDs or evaluator labels such as `votes32` | Forbidden selector inputs; use actual predicates, never evaluator labels |

The broker's `count` operation explicitly evaluates the predicate over offline snapshot metadata ([source](../agent/src/fannagent/broker.py)). That operation is not a free server observation. Any selectivity lookup/cache introduced later needs its own validity, invalidation and cost qualification.

**Predictability remains unproven.** The three cheap contexts cannot distinguish individual vector difficulty within a filter. If B1b establishes useful outcomes, the first routing baseline can be at most the eight maps from three validated contexts to two effort levels. That is a small constrained selection task, not justification for a new agent framework or a large learned predictor. No map was fitted, enumerated for performance, selected or simulated in this audit.

## 4. Historical measurements establish mechanism, not a current frontier

The verified [old effort report](../trials/torch-reviews-results/analysis-reviews-ef-sweep-20261019T004327Z.dcFzo0/report.txt) covers 30 exposed vectors / 90 cases, three serial allocations and 25,920 retained native/always-continue pairs. Each allocation varied 80/160/320/640 on its same restored physical index, with iterative scans off. Native/continue equality at each level does **not** imply equal quality across levels.

The following values reproduce its saved equal-weight block means for the work-control's native observations. They are warm-cache historical summaries, not estimates for the current index or an adaptive policy.

| Effort | Reported native ms | Native recall | Complete-result finding in saved report |
| --- | ---: | ---: | --- |
| 80 | 1.082 | 93.00% | Some filtered cases return as few as 1 result |
| 160 | 1.889 | 95.89% | Some filtered cases return 9 results |
| 320 | 3.720 | 97.56% | All return 10 in this historical sample |
| 640 | 6.872 | 98.67% | All return 10 in this historical sample |

Historical320 has 1.1111 percentage points less mean recall than 640, larger than the original 0.5 pp relative-loss margin at the point estimate. This is not a newly computed confidence gate. It warns against simply lowering effort globally or redefining the selected effort's native result as the new quality reference. Filtering after candidate search can produce fewer than `k` results; upstream documents this behavior and the separate iterative-scan option. [pgvector 0.8.6 documentation](https://github.com/pgvector/pgvector/blob/v0.8.6/README.md).

### Identity reconciliation

| Evidence | Physical index | Runtime/evidence compatibility |
| --- | --- | --- |
| Old multi-effort sweep | `6076127834d467a5791fe907f6a5bbc98e5faf637ab08cc98e0ef6b29ddc4259`; file hash starts `8c15a172…` | Earlier runtime profile `3d869e5b…`; four effort levels |
| Current P2/P3 target | `90f4a709ab3ee7ce40fe7630009b29d5646f6e1e80ceab8c2246cb970d803484`; file hash starts `dbc14b09…` | Module `e7dcace1…`, profile `b2974c2c…`; current baseline 640 |
| Historical size sweep, full 247,286 rows | Same index bytes as current target | Effort320 only, earlier profile `3d869e5b…`; not a compatible current multi-level matrix |

The old/current indexes have the same row count, byte size, relation file name and dataset archive hash, but different physical contents. Those shared attributes do not justify pooling. The [current source-index record](../trials/torch-reviews-activation-timing-calibration-v1/torch-activation-timing-calibration-v1/frozen/source-index.json) matches the size-sweep full-size index, not the old effort sweep. Sharing the base SIF hash also does not establish the same loaded module/profile.

The old effort sweep's30 group identifiers have zero overlap with P3's200 identifiers. That is an inventory mismatch, not proof of disjoint vector values or fresh validation. Both pools were already exposed. No vector-value reconciliation or entitlement pooling was performed here. The old size/effort data cannot simply be attached to P3's folds, and the earlier profile/transport costs cannot be transplanted into current economics.

**Coverage conclusion:** a compatible current-index/current-module multi-effort outcome-and-cost matrix is not established. There is historical same-index320 evidence and current 640 evidence in different scopes; preserve both, but acquire matched actual interventions before router modeling. Neither current off-grid stopping gaps nor Light19 gaps need to be filled for this native-effort question.

## 5. Next step: B1b native effort qualification and two-level frontier

Proposed ID: **NEXT-EFFORT-01**. Status: planned, not implemented, run or authorized for dispatch by this document. No code or new measurement follows from B1a.

| Stage | Required work | What it informs / decision gate |
| --- | --- | --- |
| B1b.1 Freeze | Pin current index bytes/module/backend, original 640 baseline, proposed levels 320/640, iterative scans off, exact references, assigned exposed-development cohort, primary/outer timers and every compute/search/analysis limit | One reviewable finite campaign; no budget or protected entitlement is assigned by this audit |
| B1b.2 Implement and check | Experimental native-effort binding/dispatch only; immutable origin/effective settings, allow-listed levels, no policy collector, input validation, error/reconnect/session cleanup and output identity checks | Local correctness ready; preserves current production and closed P2/P3 experiments |
| B1b.3 Native qualification | On a private restored current index, verify actual settings/plans, original-versus-forced640 IDs/distances, alternating320/640 isolation, reconnect/abort behavior, exact-truth independence and unchanged index bytes | Failures close/revise the package; no silent retry, source mutation or index rebuild to pass |
| B1b.4 Measure matched controls/frontier | Pair original 640 and wrapper-forced640, include identical-path A/A controls and matched320/640 outcomes on the same vectors/filters/blocks; charge selector, setting/pool/admission and activation/reuse costs | Establish actual setting/routing overhead and effort/quality tradeoff; frozen practical/equivalence criteria must be set before collection |
| B1b.5 Review | Report complete top-10, recall vs unchanged640 and exact truth, per-filter uncertainty, all errors and actual full-path costs; keep any hindsight opportunity diagnostic | Proceed only if a predeclared frontier/opportunity gate and controls support another bounded selection study; otherwise close or explicitly revise scope |
| Conditional B1c | Prospectively compare the at-most-eight predicate-context maps with grouped calibration/evaluation and measured actual router execution | Useful policy still needs independent acceptance; no automatic reuse of protected samples or framework migration |

Quality must remain referenced to **unchanged original 640**, never the lower effort's own native result. Preserve complete valid top-10, native reference floors and the existing development reserve/final relative-recall criterion unless a genuinely new objective is declared prospectively. A fixed-level 640 fallback for unsupported contexts is an explicit default route; re-running640 after observing a short low-effort result would be a different two-query policy whose full cost must be separately declared, not a free rescue.

The original native timer excludes some setup. A forced640 wrapper must therefore demonstrate acceptable full-path overhead versus unwrapped original 640, not merely compare native SQL timers. Identical-path A/A equivalence, order balance, per-filter checks and a finite stopping rule belong in the new contract. P2c's conditioned endpoint and calibration do not transfer automatically to new reader/pool/session semantics. No current lower-effort serving-gain estimate follows from old aggregate timing subtraction.

Current-index interventions would eventually require a separately prepared Torch package. **No commands are needed now.** The immediate recommended task is B1b's frozen design, experimental implementation and local checks; provide exact Torch commands only when that package and its finite contract are ready.

## 6. Scoped decision

- **B1a complete; GB1 scoped feasibility passes.** There is a specific existing engine control, a plausible low-cost pre-query interface and a concrete comparison that preserves the index.
- **Economic/predictive feasibility remains open.** Current API support, lower-effort recall/completeness, setting isolation, control precision and full-path cost need B1b evidence.
- **Keep original execution and prior conclusions.** P2/P3 negative/inconclusive findings, closed episodes and protected entitlements are unchanged. M1/M2/M3 and canonical acceptance remain unestablished.
- **No broader rebuild/framework project.** Exclude iterative-scan changes, index construction, new search collectors and richer feature learning from the first effort comparison. If the bounded interface/frontier is inadequate, close it before adding interventions.

## Primary sources

1. [pgvector 0.8.6 query options and filtering](https://github.com/pgvector/pgvector/blob/v0.8.6/README.md).
2. [Pinned pgvector GUC definitions](https://raw.githubusercontent.com/pgvector/pgvector/8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c/src/hnsw.c).
3. [Pinned pgvector scan implementation](https://raw.githubusercontent.com/pgvector/pgvector/8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c/src/hnswscan.c).
4. [PostgreSQL 17 session/transaction SET semantics](https://www.postgresql.org/docs/17/sql-set.html).

These establish controls and semantics, not workload performance. The local source/input inventory binds the project-specific evidence underlying the recommendation.
