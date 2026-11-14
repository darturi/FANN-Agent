# B2d quota preflight compatibility repair

October26,2026. NEXT-PARTIAL-ANN-01 / partial-ann.v1, packaging revision `quota-fix`.

**The user's submission stopped before reservation, binding, sbatch test-only or actual job dispatch. No experiment allocation was consumed by this attempt. A separate corrected package passes61 source and61 sealed-copy local checks.** Native compatibility, index build, quality, A/A, economics and final integrity remain unassessed. Original execution remains adopted.

## Failure and precise scope

The [captured submission output](../trials/torch-reviews-partial-ann-v1-quota-fix/submission-preflight-output.txt) shows bundle verification succeeds and resource preflight rejects the myquota display. The [readable table](../trials/torch-reviews-partial-ann-v1-quota-fix/myquota-captured.txt) uses `50GB/30k` for home and `5.00TB/5.00M` for scratch. The original parser does not accept lowercase `k`; literal replay raises that unit error. The remote trace instead reports unmatched rows. The paste cannot establish original terminal-control bytes, so that exact row-match difference remains unknown. The repair also handles standard ANSI SGR colour wrappers; it rejects unknown controls and malformed/duplicate/missing relevant rows.

Only the new [isolated repair source](../agent/experiments/partial-ann-v1-quota-fix/) changes. Original source, sealed packages, logs, receipts and all1,733 prior immutable files remain byte-identical. Production/adopted code is unchanged. The new package retains the exact scientific `experiment.json`, runtime, inputs, schedule, designs, measurement/replay code and controller; only quota parsing, packaging paths, tests and readiness documentation differ. There is no quota bypass or relaxed margin. Current myquota and filesystem capacity are rechecked at login and on the compute node.

The captured snapshot produces conservative available home bounds26,988,400,000 bytes and15,013 inodes, exceeding the fixed3GiB/10,000 home reserve. Scratch bounds are4,784,590,000,000 bytes and4,850,576 inodes; the actual prepared-footprint requirement still must pass at submission. These are bounds from the reported snapshot, not a live availability claim. File-count percentages are not used to increase headroom.

## Verification and seal

| Check | Result |
| --- | --- |
| Source local checks |61/61 pass;39.737 seconds |
| Sealed-copy local checks |61/61 pass;40.44 seconds |
| New regressions |Captured real display, abbreviation case, standard terminal colours, unknown/malformed rows, full resource preflight and insufficient quota |
| Retained coverage |Original55 mocked complete/early-stop acquisitions, raw replay, recall/A/A protection, timers, catalog/plan/ownership, failed collection and uncertain-dispatch checks |
| Scientific identity |Configuration, runtime, data/cohort/schedule, policies, measured/replay code and gates byte-identical to original seal |
| Package verification |162 manifested files/163 regular archive members; every archive member matches local bytes; source/sealed modules match |
| Static checks |Active modules Ruff and shell syntax pass |
| Prior preservation |1,733 pinned immutable files unchanged |
| New native/index/DB/provider/SSH/Torch calls, fits or protected queries |0 |

Manifest SHA256 `c52355cde583edb684bd250f6e5286fbb29097ef9d6ffd9dc5aac5ca40980845`. Archive SHA256 `b142e1159078e746be26442a7fd374b6e45f2f46379e023b7d1122a5f137142a`, 16,319,190 bytes. Frozen runtime anchor `082b167507e25009bdb25ea613950cd434ef38608fbcbc6194af19c363d0f6dc` remains unchanged. Original manifest `f11159e1b66d9e9cb0259bec45e136eac9bff7a322233a9ac00a4153267c09a4` and archive `b2f7730a24a98ea2a3d29474298064a2500eab8e61911c83130bf705bc97755c` remain preserved.

These tests use synthetic connections/results/clocks and mocked resource calls. They establish readiness, not native performance, actual capacity or quality.

## Handoff and critical path

Use only the new [COMMANDS.txt](../trials/torch-reviews-partial-ann-v1-quota-fix/COMMANDS.txt) and [transfer helper](../trials/torch-reviews-partial-ann-v1-quota-fix/transfer.sh). Upload on Mac; wait for UPLOAD VERIFIED; then extract and submit the new `/home/dar579/torch-partial-ann-v1-quota-fix` package once on Torch. Preserve the original package and failed output.

The scientific experiment name and campaign prefix remain original. **The controller deliberately shares `.torch-partial-ann-v1-reservation.json` with the original package.** Commands also require the original binding to be absent. This repair grants no second allocation and cannot bypass an existing reservation. If a guard or preflight fails, preserve all files and inspect the full output rather than deleting evidence or automatically retrying. After successful submit, use the new path for status/collect and the new Mac helper for download/replay.

Critical path: corrected upload/checksum → guarded once-only submission/current resource proof → restore/two-copy build/native qualification →202-search preview →802-search scoped quality → conditional16,802-search full matrix/A/A/economics → final integrity/cleanup → collect/download → trusted independent replay. One proposed3h4CPU32GiB allocation,10,200s work ceiling, unchanged quality/control/economic gates. Stop at the first failing gate. A positive scoped result still needs separately designed amortization/maintenance/integration and independent acceptance; B1c stays deferred.

Records: [source checks](../trials/torch-reviews-partial-ann-v1-quota-fix/local-checks-source.json), [sealed checks](../trials/torch-reviews-partial-ann-v1-quota-fix/local-checks-sealed.json), [package proof](../trials/torch-reviews-partial-ann-v1-quota-fix/package-checks.json), [preservation inventory](../trials/torch-reviews-partial-ann-v1-quota-fix/preservation-before.json) and [completion receipt](../agent/docs/verification/partial-ann-v1-quota-fix.json).
