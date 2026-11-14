# B2c — indexed and filter-aware ANN alternatives

Completed October 26, 2026, America/New_York. Register: **NEXT-ANN-ALTERNATIVES-01**.

**B2c is complete. Scoped design GO: one partial cosine HNSW index for the existing `total_votes >= 108` context, compared with native640 on the preserved full index.** The next phase is **B2d / NEXT-PARTIAL-ANN-01**, whose [prospective design](fannagent-partial-ann-v1-design-2026-10-26.md) is frozen separately. Implementation, local correctness checks, sealing and native qualification remain future work. No Torch command is needed now.

This is a source and saved-evidence review. No scientific code, package or prior result was changed; no test, experiment, bootstrap, fit, simulation, index build, database/native/Torch/provider call or protected-query access was performed. Document verification consists of hashes, links and arithmetic. The [inventory](fannagent-b2c-ann-alternatives-audit-2026-10-26/input-and-source-inventory.json) preserves **1,364 prior files**, including the prior 1,352-file baseline and **349 source files**. [Machine findings](fannagent-b2c-ann-alternatives-audit-2026-10-26/audit.json), [completion receipt](../agent/docs/verification/b2c-ann-alternatives-audit-v1.json), [document checks](fannagent-b2c-ann-alternatives-audit-2026-10-26/documentation-checks.json) and the [roadmap](fannagent-performance-research-roadmap-2026-10-22.md) track the handoff.

## 1. What carries forward

The [verified B2b partial-return review](fannagent-exact-topk-v1-catalog-fix-partial-results-2026-10-26.md) closes its finite comparison as `incomplete_budget_exhausted`, with prefix qualification/quality passing and complete A/A, economic and final integrity gates unassessed. Its exact10 path is descriptively **56.11 times slower** in the complete first block, **28.47 times slower** even for votes108, and faster in **0 of 763** complete case/block comparisons. Those observations support declining another exact10 allocation; they do not supply a completed negative economic verdict.

Saved phase accounting assigns **4,891.108 seconds / 93.66%** of the observed warm window to exact10 query calls, versus 92.763 seconds to native calls and 14.042 seconds to warm plan diagnostics. The exact path, rather than recorded plan inspection, dominates that schedule. This does not attribute the query cost to CPU, I/O or JIT. No new timing interval was calculated here.

The current index has 247,286 vectors of dimension768. Existing metadata records 123,692 eligible rows for votes32 and **49,498 / 20.0165%** for votes108. The completed B1 effort family supplies no qualifying router family; P2/P3 verdicts and original adopted execution remain unchanged. The 200 development vectors are already exposed. The 60 unconsumed confirmation and 37 reserved vectors remain untouched.

The complete actual B2b catalogs were not archived, and successful final index/module checks were never reached. Reading the provisioning recipe now does not recover that missing evidence. A new physical-index study must collect its own initial and final catalogs and integrity checks.

## 2. Alternatives and scope decision

| Alternative | Work it could avoid | Required change and costs | B2c decision |
| --- | --- | --- | --- |
| Repeat exact10 or change its schedule | No new candidate-work reduction established | Already very slow; another allocation would repeat the mechanism | No repeat; preserve incomplete closure |
| Scalar B-tree on total_votes plus exact distance ordering | Some table eligibility work | New scalar index/build/statistics; 20%/50% populations remain broad; ordered distance processing still required | Defer; no free intersection with ordered HNSW |
| **One partial cosine HNSW, predicate >=108** | Search graph contains only eligible rows | One new graph, experimental target validation and predicate-specific SQL; build/storage/update costs | **Select for one bounded prospective design** |
| Additional >=32 partial index or a family of partial indexes | More contexts | Additional graphs, maintenance and selection scope | Exclude from first study |
| Filtered ordinary shadow table and ordinary HNSW | Similar graph restriction | Duplicate table/data lifecycle, source/snapshot/global-ID mapping and eligibility semantics | Defer; keeping the full table avoids those extra changes |
| Partitioned table/indexes | Prune eligible partitions | New layout, per-partition graphs/global top-k semantics; public target inspector rejects partitions | Defer; larger interface and maintenance scope |
| ACORN-style predicate-aware traversal | Avoid irrelevant distance work inside graph search | Native implementation, predicate visibility/MVCC/security and graph compatibility; possible new construction | Defer; larger uncertain native scope |
| Iterative scans or another effort ladder | Change result acquisition | Current cases already return ten; quality reserve remains binding | No automatic continuation of the closed effort family |

pgvector's versioned guidance describes post-scan filtering and suggests partial ANN indexes for a small number of recurring predicates. That supports investigating this mechanism; it supplies no local speed or recall estimate. [pgvector0.8.6 filtering](https://github.com/pgvector/pgvector/blob/v0.8.6/README.md#filtering)

PostgreSQL explains that bitmap combinations lose index ordering. A scalar filter index therefore is not a free ordered-HNSW intersection. [PostgreSQL17 combining indexes](https://www.postgresql.org/docs/17/indexes-bitmap-scans.html)

## 3. Compatibility: public rejection, narrower source feasibility

The [public backend inspector](../agent-pgvector/src/fannagent_pgvector/backend.py), lines210–249, requires an ordinary relation and a valid, ready, **nonpartial**, nonexpression cosine HNSW target. Merely specifying a partial index name in the public configuration will fail. This audit does not qualify partial indexes for the public API or recommend weakening that validator.

The narrower [C target binding](../trials/torch-reviews-first/sources/pgvector/src/fannbench.c), lines358–385, validates relation/index association, bigint ID, embedding key and HNSW access method, then stores the binding. It has no explicit partial-predicate rejection. **Inference:** an isolated experiment can try binding a carefully validated partial index using the existing module, with a separate experimental catalog/target adapter. Actual compatibility remains unverified until native qualification. Fail closed if the unchanged module cannot execute it; do not bundle a module patch or rebuild into this study.

Binding is **not a planner hint**. It does not make ordinary SQL use that index. The scan hook at lines1585–1593 returns early for native mode, so native execution cannot rely on the policy-path wrong-index guard either. Every experimental cell needs actual fresh and matching cached-plan inspection.

The [current request SQL](../agent-pgvector/src/fannagent_pgvector/backend.py), lines989–1003, binds the threshold as a parameter. PostgreSQL must prove the query implies a partial-index predicate at planning time; an arbitrary parameter does not provide that proof for a generic plan. [PostgreSQL17 partial indexes](https://www.postgresql.org/docs/17/indexes-partial.html)

The candidate-only statement will retain the parameter and add the fixed conjunct `AND total_votes >= 108`, **only after validating that the request is exactly the supported single >=108 predicate with k10**. This conjunct is semantically redundant in that context and makes the fixed predicate visible during planning. This is a proposed SQL change, not proof of planner selection. Reject other contexts before dispatch. Keep nine-significant-digit vector formatting, result decoding, driver auto-preparation and inherited planner settings. Record preparation counters and inspect matching cached plans; do not force custom plans or disable preparation to make the treatment pass. [PostgreSQL17 PREPARE](https://www.postgresql.org/docs/17/sql-prepare.html), [Psycopg3.3.6 preparation](https://github.com/psycopg/psycopg/blob/3.3.6/docs/advanced/prepare.rst)

## 4. Isolate the comparison and preserve identities

Creating a partial index beside the baseline in one database could change the baseline's chosen plan. The design therefore uses **two private copies of the same frozen prepared database**, running serial query calls within one allocation:

| Copy | Table and original full HNSW | Additional object | Required timed plan |
| --- | --- | --- | --- |
| Baseline | Preserved complete table and original graph | None | Original full HNSW at ef_search640 |
| Candidate | Identical complete table and original graph | Exactly one partial cosine HNSW WHERE total_votes>=108 | New partial HNSW at ef_search640 |

Keep global row IDs, vector bits, metadata, logical field mapping, image/module, full original graph and snapshot fixed. The candidate intentionally changes catalog identity, adds one graph and changes one statement's predicate text. It must not be described as an unchanged-graph-only intervention. Separate copies also change cache isolation: this is a persistent-reader, two-copy warm diagnostic, with symmetric conditioning and explicitly reported memory/startup costs. A later shared-service integration needs its own study.

Expected preserved identities include graph `90f4a709ab3ee7ce40fe7630009b29d5646f6e1e80ceab8c2246cb970d803484`, full index file `base/16384/264013`, 1,012,678,656 bytes, SHA256 `dbc14b0912d7e9ad9cd4ddcf806cac081412e66b1861de7ce3629fd81e23b393`; module `e7dcace1f4dfd4ea233256d6cdfc17b3190f3f07cccb6406b479b5ebe8b85811`; profile `b2974c2c65d40780d207109d9bbd298b2628ea58abde673c0dd479c1a0e52ed3`; image `7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a`. Source320, study reference640 and boot40 remain distinct.

## 5. Why native traversal is deferred

The [existing predicate-context patch](../agent-pgvector/src/fannagent_pgvector/engine/patches/0007-predicate-context.patch) supplies a request feature; it does not implement predicate-subgraph traversal. The current [SelectNeighbors](../trials/torch-reviews-first/sources/pgvector/src/hnswutils.c), line1172, prunes candidate neighbors. ACORN-1 puts neighbor expansion at query time, but its described construction omits HNSW pruning. Therefore the current graph is not established as a drop-in ACORN-1 graph. A query-only adaptation would be a new native variant with a graph-compatibility question, rather than a settings change. [ACORN v1, Section5.3](https://arxiv.org/html/2403.04871v1#S5.SS3)

A native variant would also need predicate evaluation against visible tuples, safe metadata access, transaction/security behavior, counters, full query costs and relative-recall qualification. It remains a legitimate later research direction if the selected smaller physical intervention fails, with a new design rather than automatic escalation.

## 6. Cost-grounded bounded handoff

Historical [size-sweep build records](../trials/torch-reviews-results/reviews-size-sweep-20261019T021505Z.jbrSqB/preparation/) give the following observed costs. They are different graph populations and an earlier preparation environment, not forecasts for the selected partial index.

| Historical rows | Index build seconds | Total provision seconds |
| --- | ---: | ---: |
|50,000 |92.835 |236.535 |
|100,000 |273.553 |433.114 |
|200,000 |596.139 |787.639 |
|247,286 |764.062 |990.650 |

These records support allowing explicit build time rather than treating a 49,498-row index as free. They do not justify scaling query latency by row count. PostgreSQL documents ordinary versus concurrent build work; the prospective experiment uses an ordinary build on its private, write-frozen candidate copy. Concurrent deployment and update maintenance are outside this diagnostic. [PostgreSQL17 CREATE INDEX](https://www.postgresql.org/docs/17/sql-createindex.html)

The [frozen B2d design](fannagent-partial-ann-v1-design-2026-10-26.md) sets one proposed three-hour allocation, 4 CPUs / 32 GiB, a 10,200-second work deadline, stage caps and **16,802 maximum search attempts**. It adds a **24-vector cost preview** before all 200 quality references. A very large cost disadvantage stops early; preview success cannot qualify performance. No allocation is created or consumed by B2c.

The scoped quality gate remains mean recall>=.95 for both paths and a candidate-minus-baseline lower95% recall bound>=−.0025. Four A/A interval checks cover two cells and gap/log ratio for this one context. Economic bounds retain the conservative99.375th-percentile upper bound, −.10ms and log(.98) targets, and both-block direction. Missing data or failed final integrity cannot become a complete positive or negative performance result.

Build, two-copy restore, connection admission, plan observation, warmup, conditioning, retained queries, analysis, bytes and cleanup are separately charged. A positive warm result would still require build-amortization and update/freshness evaluation: break-even queries = incremental build seconds / (per-query saving milliseconds /1000). There is no claim that the warm treatment improves activation, all predicates, production operation, a learned policy or the agent's research method.

## 7. Decision and remaining gates

| Gate | Current evidence | Disposition |
| --- | --- | --- |
| B2c source/evidence review | Options, SQL/cache semantics, binding/inspector distinction and saved costs reconciled | Complete |
| B2c mechanism/design | One fixed >=108 partial HNSW, full table retained, unchanged module, isolated copies | Scoped GO for B2d design/local implementation |
| B2d implementation/local checks/seal | Not performed | Next task; experimental adapter and strict rejection/plan/budget/archive checks required |
| Native catalog/module/plan compatibility | Source inference only; no new live catalog or build | Unassessed; abort if unchanged module/actual plans fail |
| Preview/quality/A/A/economics/final integrity | No new measurements | Unassessed; finite stop rules in separate design |
| Adoption, router, protected confirmation, M1/M2/M3 | No new supporting result | Retain original; B1c deferred |

The critical path is **B2c complete → B2d isolated implementation and local checks → sealed handoff → one separately authorized native preparation/qualification/cost preview → full scoped quality → two-block A/A/economics and final integrity → independent returned-evidence verification**. Stop at the first failed gate. A native failure does not authorize a module patch, a second predicate, another allocation or a new effort sweep. The next user action comes after a checked, sealed package and exact commands are ready.
