# B2a — plan/filter/index feasibility audit

Completed October 25, 2026, America/New_York. Register: **NEXT-PLAN-SCOPE-01**.  
**B2a is complete. GB2a passes scoped source feasibility: GO for one prospective exact-top-10 versus native640 comparison; no router fitting or index rebuild yet.**

The user named B1a, which was already completed on October 24. I explicitly interpreted the request as the next B2a read-only audit. The [original B1a record](fannagent-b1a-search-effort-audit-2026-10-24.md), B1b/B1b2 verdicts and adopted execution remain unchanged.

The next recommended task is **B2b / NEXT-EXACT-TOPK-01**: freeze one bounded comparison of a fixed exact top-10 execution path and unchanged native640 on the same table/data/HNSW graph/module. This is a design recommendation, not an implemented or qualified feature. No code, tests, experiments, fits, policy simulations, DB/native/Torch/provider calls or protected-query values were used in this audit. No user commands are needed now.

## Evidence and preservation

- [Machine-readable findings and option matrix](fannagent-b2a-plan-scope-audit-2026-10-25/audit.json).
- [Pinned source/saved-input inventory](fannagent-b2a-plan-scope-audit-2026-10-25/input-and-source-inventory.json): **349 existing source/code files and 907 immutable source/evidence/input paths**. The previous B1b2 888-file inventory and all its post-run artifacts were verified before this audit; every inventoried immutable hash is checked again after documentation changes.
- [Completion/preservation receipt](../agent/docs/verification/b2a-plan-scope-audit-v1.json) and [documentation checks](fannagent-b2a-plan-scope-audit-2026-10-25/documentation-checks.json).
- [Current roadmap](fannagent-performance-research-roadmap-2026-10-22.md), updated to v1.19.

This audit reads existing source, saved plans/settings/identities, exposed request metadata and primary documentation. It imports no experiment module and computes no new timing/recall confidence intervals. Source hashes prove preservation, not that unrecorded remote metadata has been inspected.

## 1. The current exact evaluator is not an exact top-10 execution benchmark

The [frozen backend](../trials/torch-reviews-native-effort-midpoint-v1/torch-native-effort-midpoint-v1/frozen/vendor/fannagent_pgvector/backend.py), `_statement` at line994, uses the actual predicate and cosine distance with `ORDER BY` and `LIMIT k` for native execution. It omits `LIMIT` when asked for exact truth. The [loaded ExactReferenceMixin](../trials/torch-reviews-native-effort-midpoint-v1/torch-native-effort-midpoint-v1/frozen/reference_backend.py), line8, enables sequential scans, disables index/index-only/bitmap scans in a transaction, checks the plan, fetches **all eligible rows**, and builds eligible IDs, strictly-better IDs and the complete boundary-tie set. The [loader](../trials/torch-reviews-native-effort-midpoint-v1/torch-native-effort-midpoint-v1/frozen/legacy_execution.py), line25, actually composes this mixin with the unchanged Torch backend; the base backend's similarly named reference alone is not the runtime definition.

| Property | Existing authoritative exact reference | Proposed fixed exact top-10 execution |
| --- | --- | --- |
| Purpose | Generate evaluator truth and eligibility/ties | Return one query's top10 to its caller |
| SQL output bound | No `LIMIT` | Preserve native `LIMIT 10` |
| Rows decoded/transferred | Every eligible row | Ten, if at least ten are eligible |
| Exactness proof | Exhaustive scan, full truth construction | Require actual non-ANN plan and independent match to unchanged full truth |
| Existing measurements | Reference acquisition phase charges | None; cannot infer from the left column |
| Data/index/module changes needed by mechanism | None | None; separate experimental setting/plan identity still required |

**Inference from source:** a different exact-top10 execution endpoint is technically feasible without rebuilding the graph. Limiting output may reduce sorting/materialization/transfer work; it still needs to consider all eligible candidates for exact nearest neighbors absent a suitable distance-order index. No local speedup is predicted. PostgreSQL describes the need to process candidates for explicit ordered selection in its [ORDER BY/index documentation](https://www.postgresql.org/docs/17/indexes-ordering.html).

The existing native method can execute ordinary SQL on a non-HNSW plan; native mode does not require policy checkpoints or an HNSW telemetry acknowledgement. A separately owned reader could bind `enable_seqscan=on`, `enable_indexscan=off`, `enable_indexonlyscan=off`, `enable_bitmapscan=off` and reuse the native statement and result decoding. This is a proposed isolated experimental binding, not a change to the public Query API or an adopted mode. Verify actual plans and exact output: planner switches do not constitute an exactness proof. Preserve the independent reference generator completely.

## 2. What the existing native plans actually establish

The [B1b2 qualification record](../trials/torch-reviews-native-effort-midpoint-v1/returned/reviews-native-midpoint-v1-20261025T172357Z.ybpfkkki/run/qualification.json) contains six non-ANALYZE plans, one480 and one640 plan per fixture context. Each is `Limit → Index Scan(reviews_hnsw)`. Filtered scans retain a `Filter: total_votes >= threshold` field. They contain no actual execution time, rows removed or distance-work measurement. Plan summaries in the audit JSON omit only the long query-vector `Order By` strings; original plans remain unchanged.

| Request context | Actual eligible rows | Fraction of 247,286 | Saved HNSW child `Plan Rows` estimate, both efforts |
| --- | ---: | ---: | ---: |
| Unfiltered |247,286 |100.0000% |247,286 |
| `m_000000 >= 32` |123,692 |50.0198% |123,934 |
| `m_000000 >= 108` |49,498 |20.0165% |49,363 |

The actual counts come from existing database-identity metadata; they are evaluator evidence, not free router observations. The different estimates illustrate why `Plan Rows` is not exact selectivity. These are broad filters, so a scalar index or brute-force exact path is not assumed economical.

Origin settings are sequential scan discouraged, index/index-only/bitmap enabled, source effort320 and iterative scans off; the study's paired reference remains640. Merely enabling sequential scans does not force the planner to abandon HNSW. A “planner-default” treatment also needs its own quality gate because estimated plan cost does not enforce the640-relative recall reserve. PostgreSQL explains [planner switches](https://www.postgresql.org/docs/17/runtime-config-query.html) and that [EXPLAIN costs are arbitrary estimates rather than elapsed milliseconds](https://www.postgresql.org/docs/17/using-explain.html).

Do not reinterpret the native HNSW `Plan Rows` or planner costs as observed candidate work or a calibrated latency predictor. No new EXPLAIN, EXPLAIN ANALYZE or query was run here.

## 3. Index inventory, compatibility and alternatives

The [provisioning recipe](../trials/torch-reviews-size-sweep/database.py), lines87 and103, creates the primary-key table and one full cosine HNSW index. It declares **no scalar total_votes index**. The saved source/index identity and owned-reader origin retain the selected HNSW index, rather than a complete catalog of every index. Consequently the audit cannot prove that no scalar index was added later. A future qualification must capture the complete catalog, table/index definitions, statistics/settings and effective plan before/after; do not rebuild or silently normalize unexpected inputs.

| Option | Existing graph/module compatibility | Main issue / cost | Audit decision |
| --- | --- | --- | --- |
| Fixed exact top10 versus native640 | Same table, graph and module; new experimental planner binding | Actual exact plan, parity, controls and full costs unknown | **GO for a new bounded design only** |
| Let planner choose after `enable_seqscan=on` | Same graph/module possible | May still choose ANN; cost estimates provide no relative-recall guarantee | Do not bundle with first comparison |
| Add scalar B-tree on total_votes | HNSW bytes might stay unchanged; new scalar files/catalog/stats/build cost |20%/50% eligibility; physical lookup and distance sort still needed | Defer; first test a graph-preserving exact path |
| Partial HNSW for threshold subsets | New graphs and target identity | Current backend rejects partial selected HNSW; parameter/custom-plan implication must be qualified | Defer to a separate physical/backend contract |
| Partition table/indexes | New layout, per-partition graphs, target/copy identity | Current backend rejects partitioned relation; range filters may need multiple partitions and global top-k merge | Defer; broader interface work |
| Predicate-aware traversal / ACORN | Not implemented by current native settings or threshold patch | New module; predicate visibility, graph assumptions, MVCC/security and costs need design | Defer as native research |
| Iterative scans or more effort values | Query-time engine controls exist | A distinct intervention; complete results already obtained; no recall repair established | No automatic follow-up or retrospective rescue |

A scalar index cannot be assumed to intersect with ordered HNSW search for free. PostgreSQL's [bitmap-index combination](https://www.postgresql.org/docs/17/indexes-bitmap-scans.html) loses index ordering and may require a separate sort. A new scalar index changes catalog/plan/statistics identity even if selected HNSW bytes remain unchanged.

Both [current backend inspection](../agent-pgvector/src/fannagent_pgvector/backend.py), lines210 and244, and the frozen backend reject partitioned relations and partial/expression selected HNSW indexes. The custom Torch wrapper does not make these unsupported public targets qualified automatically. For partial indexes, PostgreSQL requires [planning-time predicate implication](https://www.postgresql.org/docs/17/indexes-partial.html). Current bound filter parameters and possible [custom versus generic prepared plans](https://www.postgresql.org/docs/17/sql-prepare.html) need actual plan qualification; neither “always usable” nor “never usable with any bound parameter” is justified without that context. Current driver's preparation/cache behavior was not measured or assumed.

### Predicate context is not predicate-aware traversal

The [threshold-context patch](../agent-pgvector/src/fannagent_pgvector/engine/patches/0007-predicate-context.patch) exposes an actual request threshold as a feature; it does not change graph construction or implement predicate-subgraph traversal. The [executor hook](../agent-pgvector/src/fannagent_pgvector/engine/postgresql-17.11-executor.patch) observes the ordinary scan qualification result. These are evidence features, not an implemented ACORN path.

[ACORN v1 Section5.3](https://arxiv.org/html/2403.04871v1#S5.SS3) places ACORN-1's neighbor expansion at query time, while describing an unpruned HNSW construction variant. The local [pgvector SelectNeighbors](../trials/torch-reviews-first/sources/pgvector/src/hnswutils.c), line1172, applies a diversity/pruning heuristic. Therefore it would be inaccurate either to require a dense new index for every ACORN idea or to call the current graph a drop-in ACORN-1 index. A query-only adaptation would be a new native variant with unproven graph compatibility, not a setting change. Published results transfer no workload gain.

[pgvector0.8.6 filtering/iterative guidance](https://github.com/pgvector/pgvector/blob/v0.8.6/README.md#filtering) motivates alternative filtering designs. Local [hnswscan.c](../trials/torch-reviews-first/sources/pgvector/src/hnswscan.c), line252, resumes when its current result list is exhausted. Existing480/640 results already return ten. Changing iterative mode may change behavior, but is not established here as a remedy for the observed relative-recall misses; it is outside the selected exact-path question.

## 4. Legal decision inputs and information limits

The same 600 exposed requests form 200 vector groups and three contexts: no filter, actual `m_000000 >= 32`, actual `m_000000 >= 108`, all `k=10`. [Snapshot field mapping](../agent/src/fannagent/snapshot.py) maps logical m_000000 to physical total_votes. [Filter normalization](../agent-pgvector/src/fannagent_pgvector/native/filters.py) produces parameterized SQL; retain validation, types, filter-presence distinction and costs.

| Input | Permissible role / qualification needed |
| --- | --- |
| Actual validated AST, field/operator/threshold, filter presence, k | Potential future small deterministic route; parsing/ownership and dispatch charged |
| Raw vector | Present in request, but no qualified cheap vector-difficulty predictor exists |
| Eligible count/selectivity | [Broker count](../agent/src/fannagent/broker.py), line284, computes from offline snapshot metadata; no free serving feature. A new stats/cache lookup needs validity/invalidation/cost qualification |
| Planner statistics / estimates | Possible separately qualified metadata input; approximate, catalog-dependent and not measured as a safe latency/recall predictor |
| Query/group IDs, votes32/votes108 evaluator labels, fold IDs, truth/observed recall, timings or acquired outcome | Never route on these; use only genuine decision-time information |
| Stopping/progress/local observations | Require search/feature work; not free pre-query plan selectors |

No map was selected or simulated. A useful fixed-plan cost matrix must precede any selection. The broader filter vocabulary in the API does not create evidence for unobserved predicates. Preserve the 60 unconsumed confirmation and 37 reserved vectors; no new sample entitlement follows from a new mechanism.

## 5. GB2a decision and remaining gaps

**Pass, scoped source feasibility.** A specific supported SQL/setting mechanism can evaluate a meaningfully different quality/cost question on unchanged data/graph/module, using an unchanged independent exact truth. That is sufficient to recommend a finite comparison design. It establishes neither economic feasibility nor useful routing, and assigns no implementation or measurement budget.

| Gap | What is missing | How it is resolved |
| --- | --- | --- |
| U1 current catalog/plans | Complete current scalar/ANN catalog, statistics, exact top10 plan and prepared-plan behavior are not archived as one verified snapshot | Mandatory native-qualification metadata under a new contract; fail on mismatch. No separate live audit command now |
| U2 actual exact execution economics | Exact top10 timings, identical-path controls and full lifecycle cost do not exist | One prospective B2b comparison; do not reuse exhaustive-reference acquisition timings |
| U3 alternative native/physical mechanisms | Partial/partitioned target support and ACORN graph/module/predicate integration are unqualified | Separate scope if later justified; do not bundle into B2b |

B1b remains aggregate `measurement_inconclusive`; B1b2 remains `closed_negative_quality`. The unfiltered480 pass cannot be recycled into a post-hoc router. No repeated480/560/600 ladder, margin relaxation, additional fit or protected evaluation is authorized. Original execution and M1/M2/M3 remain unchanged.

## 6. Recommended B2b preparation and gates

**Proposed ID:** `NEXT-EXACT-TOPK-01`. **Status:** design recommended; not frozen, implemented or run. These are requirements for the next finite contract, not a launch instruction.

| Phase | What it must do | What it informs / gate |
| --- | --- | --- |
| B2b.0 prospective design | Pin the current graph/module/data/backend, exact native statement/formatter, four exact planner overrides, original640 reference, unchanged truth, exposed600-case cohort and primary full-outer timing scope | G0-B2b: complete finite identity/schedule/cost/quality/control/resource contract before code |
| B2b.1 isolated implementation/check/seal | Fixed reader modes with owned origin/effective bindings; preserve validation, timeout/abort/closed-session/error behavior. Keep both reader startup, query/result decoding and guard costs visible | Correctness readiness only; no rewrite of old source or evaluator |
| B2b.2 native qualification/quality | Capture full catalog/stats/settings/cache configuration; verify native HNSW versus exact non-ANN plans, cosine/top10/tie-aware output, predicate validity and repeated/isolation/error recovery. Fresh full truth remains separate | Integrity/semantic failure is failed qualification, not a negative quality decision. Complete valid quality failure closes before timing |
| B2b.3 matched cost/control measurement | Original640 plus independent native640 A/A replicas and exact A/A replicas; balanced temporal blocks, separate acquisition/startup charges, vector-group uncertainty; report all predicates/overall and every attempted call | Establish whether any prospectively defined context has a qualified exact-path opportunity; no fitted map or post-hoc deployment |
| B2b.4 verify/close | Check checksum/raw records, identities/plans/counts/primary timers and unchanged local sealed replay; preserve quality/control/economic failures and actual resources | No useful context: finite negative/inconclusive closure. Supported context: only a separate bounded routing-design decision, not adoption |

For a manageable first comparison, propose **at most one 4CPU/32GiB/two-hour allocation**, a 6,600-second work deadline and **50,000 total backend search attempts** including qualification, fresh full references, conditioning, warmups, controls and retained observations. Use only the same 200 exposed vectors/600 cases; zero providers, fits, confirmation, reserved/new vectors. Exact schedule and derived counts must be sealed before implementation and may be smaller; this is a proposed ceiling, not assigned spending or a ready package. Additional metadata/EXPLAIN statements and startup/cleanup must also be counted and charged, not treated as free. Reaching a bound closes the finite attempt; no automatic extra allocation.

Recommended initial operating scope is a **warm persistent-reader full-outer diagnostic**, matching the known economic question while explicitly recording restore/admission/first-use/conditioning/cleanup. It cannot qualify activation or deployment. Freeze A/A equivalence and practical-benefit/overhead rules prospectively; preserve the 95% reference floors, complete valid top10 and −0.25pp development reserve versus640. Require tie-aware exact correctness against authoritative truth in addition to statistical recall. Fix the setting/plan intervention; do not add JIT, parallelism, work_mem, scalar indexes, new transport/validators or planner-cost tuning. Preserve existing JIT/parallel settings and count actual worker/resource use.

**Revised critical path:** completed B1b2 negative closure → **completed B2a/GB2a scoped GO** → B2b prospective finite contract → isolated implementation/check/seal → native plan/semantic/quality gates → actual new A/A and full-cost frontier → verified context decision → only then consider bounded routing/operating-scope/confirmation. No new framework is justified by this audit. **No user/Torch commands are needed now.**

## Primary sources

The sources below establish mechanisms and caveats, not local performance:

1. [pgvector0.8.6](https://github.com/pgvector/pgvector/blob/v0.8.6/README.md), filtering and iterative scans.
2. [PostgreSQL17 Using EXPLAIN](https://www.postgresql.org/docs/17/using-explain.html).
3. [PostgreSQL17 query-planning controls](https://www.postgresql.org/docs/17/runtime-config-query.html).
4. [PostgreSQL17 partial indexes](https://www.postgresql.org/docs/17/indexes-partial.html).
5. [PostgreSQL17 index combination](https://www.postgresql.org/docs/17/indexes-bitmap-scans.html).
6. [PostgreSQL17 PREPARE](https://www.postgresql.org/docs/17/sql-prepare.html).
7. [PostgreSQL17 ORDER BY/index behavior](https://www.postgresql.org/docs/17/indexes-ordering.html).
8. [ACORN v1](https://arxiv.org/html/2403.04871v1), especially Section5.3.
