# Small Reviews query exposure audit — superseded provisional snapshot

**Superseded before execution:** See [reservation review](reservation-review.md) and the authoritative [frozen study split](../reviews-small/splits/split-manifest.json). The new split is 450 development / 150 validation / 275 test / 125 exclusions. The original report below is retained for provenance; it is not the current split.

Audit date: November 10, 2026 (America/New_York). Scope: local published release and local historical query inventories. No ANN/exact searches, database execution, provider requests, or remote jobs were performed.

## Finding

There are 1,000 distinct published query vector groups and 7,000 query/filter pairs. All seven files contain exactly the same ordered float64 query vectors. Each group receives one role across every filter. The local audit identifies 125 groups without a historical query-inventory reference, not 740 groups obtained by subtracting only the latest 200 and 60.

| Exclusive classification | Vector groups | New role |
| --- | ---: | --- |
| Frozen controlled-batch development | 200 | Development |
| Consumed evaluations, including the recent 60 and an earlier 60 | 120 | Development, retaining consumed provenance |
| Explicit feature/data-ablation reservation | 37 | Excluded; preserve reservation |
| Other historical inventories with unresolved outcome-access history | 518 | Excluded conservatively |
| No reference found in audited local query inventories | 125 | Provisionally available |
| Total | 1,000 | |

The 518 are **not** all demonstrated policy exposure. They include old qualification/study populations and canonical partitions. An input file or reservation alone does not show that its results influenced policy selection. Exclusion is conservative because complete access records are unavailable. No historical classification has been rewritten.

The earlier bounded contract reserved 750 groups (450 development, 150 calibration, 150 test). Old canonical workloads cover another 125 groups. Query vectors in these inventories are reconciled by content rather than by assuming similarly named IDs identify the same source row. The explicit 37-group reservation is within the earlier development population; it is not an additional independent pool.

## Inventory and identity

`source-inventory.json` records source file SHA256 checksums, sizes, shapes, dtypes, filters, and schema. Small Reviews contains 247,286 corpus rows of dimension 768. Retained canonical manifests specify cosine. Published filter conditions are unfiltered and total_votes >= 743, 527, 310, 192, 108, 32. Their published ground-truth arrays each have 100 neighbors per query. This audit inspects their schema, not neighbor/distance outcomes.

`query-catalog.jsonl` has one record per query/filter pair, retaining the source row, query source ID, importer alias, float64 source-vector hash, importer float32 hash, normalized float32 hash, role, and evidence pointer. Source file checksums are in the companion inventory. Group identity uses little-endian float32 content, consistently across all predicates. Original float64 content is retained as a separate hash.

Historical matching first uses exact float32 bytes, including the runtime-normalized representation. Older decimal serialization is accepted only with a unique match within a maximum coordinate difference of 2e-7. Every accepted match must identify exactly one source group. The runtime formatter's nine significant digits round-trip float32 values. No equality is inferred solely from different serialized hashes or filename aliases.

`storage-inventory.json` pins both canonical dataset versions and relevant importer/runtime source. Corpus source IDs and canonical row IDs are checked against v2 Parquet without reading vector outcome labels. Query source IDs occur in the corpus. No self-match removal is introduced. Official ground-truth self-match/tie behavior, float-conversion effects, and exact scoring remain Phase 2 qualification work. Existing physical PostgreSQL graph/backup identities must also be requalified before execution; this audit does not assert that an unmounted database has been checked.

## Audit coverage and uncertainty

The reproducible scan uses `rg --files --hidden --no-ignore`, excludes installed dependencies and release trees, and examines query-bearing JSONL filenames across the workspace, including ignored canonical data. It audits 662 files with 64 distinct byte contents. Duplicate packages/returns retain separate provenance paths and shared hashes. `historical-query-files.json` records query groups, aliases, file hashes and unmatched 768-dimensional records. `group-evidence.json` indexes matching historical references. `excluded-outcome-files.json` lists JSONL paths omitted because they are not query inventories. No outcome metrics are reported or used for selection.

The metadata extractor inspects query/request objects and their vectors/IDs, not checkpoint/result fields. Generic JSON artifact catalogs and archives are not exhaustively mined; known catalog-backed reservations are reconciled from their explicit split/hash manifest. Unmatched records can belong to other datasets or synthetic fixtures and do not imply new Reviews groups. The source and split manifests, existing staging source, and known query catalogs provide the coverage boundary.

There is no complete local/remote/chat access log. Consequently, “available” means **no historical reference found under this audit**, conditional on that coverage. It is not proof that nobody has ever inspected those queries. If later evidence identifies exposure, preserve this manifest and issue a versioned replacement before policy selection; never silently relabel an exposed group as test. Additional archive/remote history can reduce, but must not retrospectively enlarge, a consumed test.

## Provisional split and achievable precision

The deterministic split uses seed `fannagent-benchmark-evaluation-v1:phase0:20261110`. Sort the 125 available groups by SHA256(seed + ':' + float32 vector hash), reserve the first 25 for bounded validation, and the remaining 100 for test. Exposed development and consumed evaluations stay on the development side. Other historical groups remain excluded. `split-manifest.json` records all assignments, input hashes and disjointness checks. It is provisional until Phase 1 accepts the precision and audit-coverage assumptions; no validation/test outcomes have been opened for this selection.

With zero recall-losing queries, the exact one-sided 95% binomial upper loss-probability bound is `1 - 0.05^(1/n)`:

| Independent groups | Upper bound |
| ---: | ---: |
| Entire available pool: 125 | 2.3681% |
| Proposed test: 100 | 2.9513% |

Seven filter observations per group and repeated timing executions do not multiply the independent sample size. These bounds assume independent sampled groups and do not establish a 0.25 percentage point worst-case population mean-recall noninferiority margin. About 299 zero-loss groups are needed for a 1% loss-probability bound; 1,197 for 0.25%. A finite-set recall result and population inference must be reported separately.

Phase 1 should either adopt a scoped fixed-benchmark claim and an appropriate conservative recall interval with this precision limit, or obtain a genuinely disjoint workload before committing to a stronger population target. A different scale cannot automatically solve this: identical vectors must keep the same role across overlapping scales. Supplemental queries require a separate workload label.

## Reproduction and disposition

From the workspace root, run sequentially:

```sh
harness/.venv/bin/python trials/fannagent-benchmark-evaluation-v1/inventory/audit.py
harness/.venv/bin/python trials/fannagent-benchmark-evaluation-v1/inventory/finalize.py
harness/.venv/bin/python trials/fannagent-benchmark-evaluation-v1/inventory/storage_inventory.py
```

These commands refresh the local snapshot; preserve/version it before future exposure. The inventory and conservative split decision are complete for the stated local coverage. Fresh-test availability is conditional, and precision is limited. The next task is Phase 1: fix scope, recall inference, comparisons, selection rules and timing protocol before any policy generation or test execution.
