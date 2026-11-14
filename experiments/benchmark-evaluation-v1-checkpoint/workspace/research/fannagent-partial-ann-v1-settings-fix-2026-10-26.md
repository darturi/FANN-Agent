# B2d failed-run verification and settings-scope correction

October26,2026. NEXT-PARTIAL-ANN-01; corrected protocol `partial-ann.v1.settings-fix`.

**Failed job21043219_0 is independently verified. The sole mismatched guarded setting is administrator work_mem4096 (4MiB) versus the reader expectation16384 (16MiB). This was a harness session-scope defect, not a measured policy or performance failure. The separate correction passes75 source and75 sealed-copy local checks. No new native job/index/search experiment has run.** Original execution remains adopted; B1c deferred.

## Returned evidence and diagnosis

The [data-only verifier](../trials/torch-reviews-partial-ann-v1-quota-fix/failure-review-2026-10-26/verify_failed.py) uses trusted original local sealed code, never downloaded executables. It verifies checksum, every archive member against extracted bytes, exact campaign/submission/package/job identity, all8 incomplete-lock hashes, terminal FAILED1:0/4minute accounting, zero search/reader charges and all6 explicit SQL records. [Analysis](../trials/torch-reviews-partial-ann-v1-quota-fix/failure-review-2026-10-26/analysis.json); [postrun receipt](../agent/docs/verification/partial-ann-v1-quota-fix-failure-postrun.json).

Archive:21 regular members,163,151 bytes; SHA256 `60ae88ccf64c9f23e15af96d304c1b63f326f8ee52f01a2374ac02a289a20a82`. Cleanup reports all readers closed, private DBs stopped and no errors; server log confirms shutdown. All23 protected groups/1,672 captured entries are identical before/after. Native final scientific integrity remains false, and quality/A/A/economics are unassessed. The original allocation is spent and preserved. No result was promoted from an incomplete lock.

| Guarded setting | Captured torch_owner | Original reader expectation | Diagnosis |
| --- | --- | --- | --- |
| work_mem (pg_settings raw kB) |4096 |16384 | Sole failing field:4MiB admin versus16MiB reader |
| plan_cache_mode |auto |auto | Matches |
| jit |on |on | Matches |
| max_parallel_workers_per_gather |2 |2 | Matches |

The original guard failure reproduces exactly. In a separate counterfactual copy, replacing only work_mem permits all original structural catalog checks; returned data is never modified. Runtime called this guard on the first administrator connection before reader creation. Local mocks supplied reader values for every catalog, missing this boundary.

Actual returned quota stdout also contains ANSI SGR colours and lowercase30k; the quota repair correctly handled both and resource checks passed. The original raw row-match discrepancy is now explained by real colour control bytes rather than guessed formatting.

## Frozen correction and implementation

The [prospective correction contract](fannagent-partial-ann-v1-settings-fix-design-2026-10-26.md) was frozen before code/checks; SHA256 `fe1f8a76b32977e7cd47d1bb569da9ef3e7d90a63e1a517db511a7fa00c989e1`. Original design/addendum remain unchanged. New [isolated source](../agent/experiments/partial-ann-v1-settings-fix/) and package preserve all prior source/seals/raw/receipts.

1. Administrator catalogs must match the full captured16-field environment, including4MiB work_mem. Reader catalogs retain the original16MiB/JIT/cache/parallel requirements and complete existing admission audits. Actual session role and phase must agree; unknown/missing/drifted fields fail with expected/actual details. No admin query work_mem is SET to force equivalence, and reader settings are unchanged.
2. Memory preflight records actual admin4MiB and reader16MiB separately, using the larger value for the same conservative four-workspace/16-connection bound on both128MiB servers. The unchanged12GiB reserve yields14.25GiB total, below32GiB. Trusted replay recomputes the proof and rejects rehashed arithmetic tampering.
3. Build controls remain64MiB maintenance memory/zero parallel maintenance workers. Inspection now returns numeric bytes/int workers `[67108864,0]`, validated in runtime and replay. This fixes a second prospective representation mismatch: comparing current_setting text with pg_settings raw numeric strings. PostgreSQL documents session-local settings and separate setting/unit fields; pg_size_bytes supplies an explicit byte boundary. [pg_settings](https://www.postgresql.org/docs/17/view-pg-settings.html), [settings and size functions](https://www.postgresql.org/docs/17/functions-admin.html).
4. New submission/host protection pins and requires the failed campaign's21 raw files, archive/checksum, old package, binding and spent reservation. A new distinct protocol/reservation permits exactly one separately proposed corrected allocation; it never deletes/reuses the old allowance. These are read-only prerequisite checks.

Scientific differences are limited to version/name/provenance/correction metadata. Source/native640/partial640 settings, two private copies, unchanged full table/global IDs/original graph/module,200 exposed vectors/k10, seeds/schedule, scoring, primary timers, search accounting, preview, quality/A/A/economic gates and final proofs are unchanged. Measurement/interface/statistics/trace/quota/controller/host modules and the entire frozen anchor remain byte-identical. No production/adopted code changes.

## Local checks and exact seal

| Check | Result |
| --- | --- |
| Source synthetic suite |75/75 pass;54.485s |
| Sealed-copy synthetic suite |75/75 pass;54.543s |
| New boundary checks |Captured admin accepted only as admin; reader16MiB retained; all admin-field drift/unknown roles/wrong phases rejected; runtime memory/build helpers exercised; strict bytes/types and rehashed role/memory/build tampering rejected; failed-evidence/binding/reservation requirements enforced |
| Retained checks |Original61 correctness checks including full16,802 synthetic acquisition/replay,202/802 early stops, recall/A/A protection, timers, ownership/plans, quota and unknown dispatch/failure collection |
| Static/integrity |Active modules Ruff and shell syntax pass; every archive member/source module matches its sealed bytes;1,960 prior immutable files preserved |
| Native/DB/index/provider/Torch/SSH/fits/protected-query work by Codex |0 |

Manifest `c77efca4cbf297092a73c3921948209a1762b95a328ba1411154bea1ab4f89b4`;169 manifested files/170 archive members. Archive `55ebd8f3ff57fc73c61a8945337a13818c048c8f6a1a5b0eec84c887a7f21d92`,16,340,359 bytes. Frozen anchor `082b167507e25009bdb25ea613950cd434ef38608fbcbc6194af19c363d0f6dc` unchanged. [Source checks](../trials/torch-reviews-partial-ann-v1-settings-fix/local-checks-source.json), [sealed checks](../trials/torch-reviews-partial-ann-v1-settings-fix/local-checks-sealed.json), [package proof](../trials/torch-reviews-partial-ann-v1-settings-fix/package-checks.json), [preservation](../trials/torch-reviews-partial-ann-v1-settings-fix/preservation-before.json), [receipt](../agent/docs/verification/partial-ann-v1-settings-fix-implementation.json).

These are synthetic/local correctness checks, not actual native index/plan/performance qualification. The full native treatment remains unassessed and must pass every original gate.

## Exact handoff and critical path

Use only [new commands](../trials/torch-reviews-partial-ann-v1-settings-fix/COMMANDS.txt) and [new transfer helper](../trials/torch-reviews-partial-ann-v1-settings-fix/transfer.sh). On Mac upload; wait for UPLOAD VERIFIED. On Torch checksum/extract the distinct settings-fix package and submit once. The old failed package/raw/archive/binding/reservation must remain available and unchanged. Status/collect use `/home/dar579/torch-partial-ann-v1-settings-fix/pa_control.py`; Mac download uses the settings-fix helper for trusted local replay.

One separately proposed3h4CPU32GiB/10,200s corrected allocation, same202/802/16,802 search bounds. No SSH or job was launched here. Preserve both old/new reservations and all failures; no automatic retry/resume. If a guard fails, return its full output.

Critical path: verified original failure -> frozen correction/local75+75/seal complete -> new upload/checksum and one corrected submit -> prior-evidence/resource/admin/restore/build checks -> actual reader/module/catalog/fresh/cached-plan conformance -> preview -> scoped quality -> complete two-block A/A/economics -> full final integrity/cleanup -> collect/download -> independent sealed replay. First failed gate stops. Scoped positive evidence would still require separate build-amortization/maintenance/integration and independent acceptance; no current adoption or routing claim.
