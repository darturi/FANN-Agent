# Native640 development qualification: job 22635567

Verified November 11, 2026. The checksummed return was extracted without symlinks or unsafe paths. User-provided scheduler evidence reports COMPLETED/0:0, elapsed 33m13s, step MaxRSS 6,148,540K. Receipt/host exit, graph/module/protocol identities and all raw checksums passed local verification. The guest recorded data/index preservation and cleanup. No provider, validation or test queries were used.

## Runtime result

All 3,150 requests (450 independent development groups x seven conditions) reconstructed successfully. All 3,150 no-stop outputs match native, all 7,940 forced-stop outputs and their live counterparts match, historical first-stop rules replay, and exact eligibility/tie/scoring summaries reconstruct. The guest additionally checked local/shared map features on 70 requests and forced traversal prefixes; those full traces are not retained in the compact return, so those checks rely on the pinned guest rather than an independent local trace replay. Total counted searches: 36,360, under the 40,000 cap. Node cs604, Intel Xeon Platinum 8592+, x86_64. This verifies runtime semantics, not a latency benefit or a useful new policy.

## Scientific readiness

| Condition | Mean native recall | Incomplete outputs /450 | 95% floor |
| --- | ---: | ---: | --- |
| Unfiltered | 99.6444% |0 |Pass |
| votes743 |53.4889% |345 |Fail |
| votes527 |78.9778% |172 |Fail |
| votes310 |94.8222% |23 |Fail |
| votes192 |97.8889% |1 |Pass |
| votes108 |98.9111% |0 |Pass |
| votes32 |99.3778% |0 |Pass |

There are 294/120/7 incomplete cases in votes743/527/310 with no complete allowed forced-stop output at 16/32/64. Thus the permitted stopping action cannot repair every incomplete result there. votes192's single incomplete native case *does* have an eligible earlier stop; it is not proven infeasible. Nonetheless, the native recall floor itself fails three conditions, making the original all-filter episode ineligible under its frozen criteria regardless of new model proposals. Do not spend provider budget on that impossible combined objective.

The user chose to keep all six filters and strengthen/requalify the native parent. The existing engine's GUC ceiling is 1000, and the live continuation path requires a non-iterative initial scan. A new development-only plan raises only the research runtime's ceiling to 8192, preserves the graph/algorithm, tests 640/1000/2048/4096/8192 and chooses the smallest *common* setting meeting per-condition recall and per-query completeness. Settings above 1000 are labeled extended-effort research execution. Native640 stays as historical continuity. No recall threshold, split, validation or test has been changed.

See `../protocol/parent-requalification-plan-v1.json`, its seal `../freeze/parent-plan-freeze-v1.json`, and `../kits/PARENT-COMMANDS.txt`. If no grid point qualifies, retain a bounded negative and do not expand automatically. If a parent qualifies, its module/setting and corresponding static baseline grid must be pinned in a prospective protocol amendment before agent generation.

## Evidence

- `../returns/job-22635567/results/local-verification.json`: complete 3150-record raw replay.
- `../returns/job-22635567/results/extended-verification.json`: exact eligibility/ties,7,940 forced outputs, first-stop decisions, counter and summary reconstruction.
- `../returns/job-22635567/results/receipt.json`: pinned guest integrity/resource/qualification checks.
- The original return archive and sidecar remain unchanged under `../returns/`.

Agent calls/spend in this continuation: 0. Next action: user-run stronger-parent Torch sweep/requalification, then independently verify its return before any model dispatch.
