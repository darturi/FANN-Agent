# B2b exact-top-10 versus native640: frozen comparison contract v1

Frozen October 25, 2026 (America/New_York), before implementation or any new native outcome. ID: **NEXT-EXACT-TOPK-01**. The user authorizes isolated implementation, local checks and a sealed Torch handoff; the user submits the native campaign. This prospective contract and its copied package bytes are immutable after sealing. Original code/execution, every previous experiment/receipt and the B1b2 quality-negative result remain unchanged.

## Question and scope

Can a fixed exact top10 execution path on the unchanged relation beat native640 within any of the four prespecified reports (overall, unfiltered, actual votes>=32, actual votes>=108), after quality, controls and full warm query costs? This is an exposed-development, persistent-reader diagnostic. No router/map is fitted or selected, no activation or serving/agent acceptance is inferred, and no physical/native/framework change is included. A promising context can motivate a new prospective routing design only.

Data:247,286 preserved float32 vectors, dimension768, cosine; same200 exposed vectors/600 cases, k10, same actual filter AST and metadata mapping. No new/reserved/confirmation queries, fits or providers. The60 unconsumed confirmation and37 reserved vectors remain untouched.

Identities: physical graph90f4a709ab3ee7ce40fe7630009b29d5646f6e1e80ceab8c2246cb970d803484; filebase/16384/264013 (1,012,678,656 bytes), SHAdbc14b0912d7e9ad9cd4ddcf806cac081412e66b1861de7ce3629fd81e23b393. Modulee7dcace1f4dfd4ea233256d6cdfc17b3190f3f07cccb6406b479b5ebe8b85811; profileb2974c2c65d40780d207109d9bbd298b2628ea58abde673c0dd479c1a0e52ed3; SIF7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a. Preserve original source320, study reference640 and boot40 as distinct metadata.

## Fixed interventions and ownership

Two cells: `native640` and `exact10`. Both retain hnsw.ef_search640 and iterative_scan off. Both inherit the unchanged ordinary native statement (same WHERE, cosine expression,9g vector serialization and LIMIT k), execution/decoder and independent exhaustive ExactReferenceMixin. That truth generator still omits LIMIT and builds all eligibility/ties; it is never timed as the exact10 treatment.

Only exact10's owned effective binding overrides enable_seqscan=on, enable_indexscan=off, enable_indexonlyscan=off and enable_bitmapscan=off. Origin stays unmodified. Other settings, including JIT/parallel/work_mem, and driver automatic preparation remain unchanged. Do not introduce a new query validator/direct-native method/transport, scalar/partial/partitioned index or module. Startup, snapshot/request admission, first-use, diagnostics and cleanup remain explicit charges.

One immutable owned reader per arm/label. Guard closed/replaced/stale connections and bindings symmetrically inside the full-outer primary timer. A native error closes its handle; no transparent replay or reconnect. Only declared qualification recovery creates replacement readers. Maximum14 admissions,5 simultaneously live. Shared admitted requests use the unchanged snapshot validator once; frozen requests do not permit ID-based reuse of other mutable input.

## Qualification, metadata and exact semantics

One private restore of the existing verified prepared copy; never rebuild the graph. Before and after, verify data bits/metadata, module and physical graph. Record full relation/column/index catalog and scalar statistics; require one ordinary reviews table, expected id/embedding/total_votes columns, primary-key B-tree(id) and one full cosine reviews_hnsw(m16,ef_construction64), with no additional/partial/expression indexes. Unexpected metadata is failed qualification, not normalized away. Catalog/statistics must remain stable during the comparison.

Thirty qualification searches across three fixed fixtures:6 fresh exhaustive truth,12 native640,12 exact10. Alternate original/native/exact handles, inspect both plans before/after error recovery, inject3 transaction errors and prove rollback, closed-handle rejection before budget reservation and explicit new-session recovery. Native640 IDs/distances and all fresh truths must match pinned original evidence. Exact10 must return all strictly better IDs and the required number of boundary ties, valid distance-ordered cosine values and complete top10; mean recall alone is insufficient. Under a changed tie ordering, compare ID-distance mappings and boundary equivalence, not arbitrary tie order.

Native plans must be Limit->reviews_hnsw Index Scan; exact plans must contain a reviews sequential scan with Limit and no index/bitmap/ANN access. Preserve parallel plan nodes when selected. Read unchanged driver preparation threshold/cache capacity and pg_prepared_statements; collect normal EXPLAIN plus EXPLAIN EXECUTE for matching cached statements, with diagnostics prepare=False. These diagnostics may affect prepared-plan choice/counters; that conditioning is part of the declared diagnostic scope, not ordinary-serving qualification. Do not set plan_cache_mode or disable preparation to make plans pass. Require the default inherited prepare_threshold5/prepared_max100 and plan_cache_mode auto; unsupported behavior fails qualification.

Collect plan packets before and after each of600 quality cases for2 readers, and each of600 cases/block for4 warm readers. Together with12 fixture packets:12,012 plan packets when complete (2,412 on quality stop), each2 or3 counted diagnostic SQL statements. Plans redact only the query's literal vector after checking it matches the sealed formatted vector; statement/parameter hashes and structural plan/cached-query identities are preserved. Capture catalog/statistics4 times on success, twice on quality stop. Maximum40,000 observer SQL statements, separately charged; startup/settings and inherited exact-reference diagnostics are also separately counted. No EXPLAIN ANALYZE executes an uncharged search. Planned parallel workers are recorded; actual worker use is not profiled from estimated plans. Allocation wall/resources and Slurm accounting remain the resource record.

## Quality-first phase

After qualification:600 exhaustive truths+600 native640+600 exact10=1,800 searches, in a fixed sealed shuffled order. Validate all queries, native640/truth identity and exact semantics. Exact semantic/plan/integrity failure aborts qualification, never becomes a valid quality-negative result. Require all complete/valid top10; both mean recall floors>=.95 overall/per filter; lower95% exact10-minus-native640 bound>=-.0025 in every report. Bootstrap200 vectors (all three filters clustered),10,000 samples, seed20261019. Pointwise development bounds;-.005 final-margin diagnostic only. Complete-data quality failure closes at1,830 searches with no timing files.

## Finite warm schedule and accounting

Only quality pass admits four replicas: native640-a/b, exact10-a/b, plus the original reference. Two complementary temporal blocks share one allocation/database. For each case/block, deterministically randomize cell order, then reverse it in block1; each cell's labels follow ABBA or BAAB, swapped in block1. Reverse query order in block1. Eight slots/case/block. Each slot has1 native640 conditioning search,1 discarded warmup and2 retained executions on its selected replica. Conditioning and warmups are outside primary retained timers and charged; retained full outer time includes guards/native scaffolding/query/decoding. Record containing monotonic timestamps, secondary inherited SQL time, outputs and reader IDs for every attempt. Metadata probes surround each case outside the primary intervals and are charged, not subtracted.

| Item | One block | Campaign |
| --- | ---: | ---: |
| Slots |4,800 |9,600 |
| Retained executions |9,600 |19,200 |
| Discarded warmups |4,800 |9,600 |
| Conditioning searches |4,800 |9,600 |
| Timing-phase searches |19,200 |38,400 |
| Qualification / quality references | — |30 /1,800 |
| Total backend search attempts | — |**40,230** |

Exactly one x86_64 allocation,4CPUs,32GiB,two hours;6,600-second work deadline. Every search attempt reserves before execution; never retry unknown dispatch or failed native calls. Deadline, operation ceiling or incomplete acquisition closes failed/incomplete, without extrapolation or another allocation. Metadata SQL budget is40,000 and does not increase the search allowance. Zero provider/model/confirmation/new or protected-vector access.

## A/A, benefit and decisions

For each cell, compare label b versus a by paired round/repetition within query/block. Require all16 pointwise95% interval checks (2 cells x overall+3 filters x gap/log ratio) inside ±.10ms and ±log1.02. Any failure gives measurement_inconclusive; no subtraction, correction, deletion or added block. Extra repetitions/filters do not increase independent vector count.

Estimate exact10 versus native640 by equal-weight labels, rounds, retained repetitions and blocks, clustered by200 vectors. Report arithmetic mean outer gap, mean log ratio, ordinary95% intervals, primary/secondary/phase charges and block directions. Because any of4 reports could be labeled promising, gate8 one-sided economic bounds with Bonferroni alpha=.05/8=.00625: use bootstrap99.375th percentile upper bounds for gap and log ratio. Require adjusted upper gap<=-.10ms and adjusted upper log ratio<=log.98, quality already passed, all A/A passed and negative mean gaps in both blocks. These are development bootstrap bounds, not finite-sample guarantees or independent confirmation. Report selection multiplicity explicitly.

Verdicts: failed native/metadata/semantic/integrity acquisition -> failed/incomplete, no performance conclusion; valid quality failure -> closed_negative_quality; A/A failure -> measurement_inconclusive; no context passes -> closed_negative_economics; any prespecified context passes -> promising_warm_context_frontier, listing qualifying contexts for a future design only. Overall/all-filter benefit is separately visible; no global deployment or retrospective mixed route follows. M1/M2/M3/canonical acceptance remain false, original execution retained.

## Reproduction, preservation and handoff

Implement under agent/experiments/exact-topk-v1 only; copy frozen originals byte-for-byte into a new local package. Pin this design, B2a receipt and prior B1b/B1b2 evidence; lock raw records and strict submission/package/job identities. Verify returned archives with unchanged local sealed code; never execute downloaded code. Remote and local reports use proven submission identity, strict discrete/gate parity and float tolerance1e-12.

Local checks use fake database connections/results and synthetic clocks only: full600-case/two-block acquisition/replay, early gate/semantic stops, prepared/custom plan and index/catalog rejection, tie-safe correctness, exact budget/order/timer/ownership coverage, archive safety, uncertain submission refusal and transport-failure staging. They establish no native correctness or performance. Seal only after checks and source preservation pass, then provide a new MFA-safe helper with explicit local/upload/remote-checksum stages and exact once-only submit/status/collect/download commands. Both success and failed raw campaigns remain collectable; preserve failed/unknown bindings and never resubmit automatically.

Primary references: [B2a audit](fannagent-b2a-plan-scope-audit-2026-10-25.md), [PostgreSQL17 EXPLAIN](https://www.postgresql.org/docs/17/sql-explain.html), [PostgreSQL17 PREPARE](https://www.postgresql.org/docs/17/sql-prepare.html), [Psycopg automatic preparation](https://www.psycopg.org/psycopg3/docs/advanced/prepare.html). They establish API/plan semantics, not local gains.
