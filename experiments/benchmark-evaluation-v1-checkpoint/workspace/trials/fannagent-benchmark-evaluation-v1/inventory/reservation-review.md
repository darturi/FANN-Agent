# Reserved-query review and clean split

Completed November 10, 2026. This review supersedes the conservative Phase 0 role proposal; its original catalog, manifest, report and checksums remain under `snapshots/phase0-provisional/`. Historical experiment evidence is unchanged.

## Disposition

| Historical pool | Groups | Finding | Restart role |
| --- | ---: | --- | --- |
| Later feature/data-ablation reservation | 37 | Already has stop labels and query-specific recall/latency outcomes from the earlier fixed-bounded run | Development |
| Original bounded calibration | 150 | No recorded calibration consumption, protected outcome artifacts or saved outcome hits | Validation |
| Original bounded test | 150 | No recorded test consumption, protected outcome artifacts or saved outcome hits | Test |
| No historical query-inventory reference | 125 | Unchanged result of the full Phase 0 inventory scan | Additional test |

The 37 are a subset of the original 450 development groups. Their reservation in a later agent exercise did not erase earlier outcome generation. In particular, the fixed-bounded run saved 1,350 development stop-label records and 40,500 development measurement records. All 37 reserved groups occur in those saved records; they also occur in the later native-development results. This is stronger evidence than an inventory-file reference alone. The review records identities and outcome-field presence without recalculating or using their quality/performance values to select a policy.

## Evidence for recovering the 300 protected groups

Four read-only broker databases were inspected: the original bounded run, fixed-bounded run, failed durable preparation, and completed durable run. The three completed study definitions agree exactly on 450 development, 150 calibration and 150 test groups. The failed preparation contains no artifacts. None has `calibration:*`, `test_*` or frozen-policy state. Artifact registries contain no calibration/test outcomes. Broker source records a test entitlement before executing final test, so the absence of that state is meaningful rather than a check only for a successful report.

Saved execution summaries agree: no test consumed, zero calibrations where reported, and no held-out executions in the later zero-search overhead-predictor attempt. This review does not reinterpret that failed attempt's 450-query input inventory as 450 new executions.

A scan of saved JSON and JSONL evidence searched the canonical aliases of all 337 candidate groups. It inspected 125 matching files with 99 distinct byte contents, including ignored files. The recursive check identifies query records with outcome fields such as labels, checkpoints, recall, latency, distances and result IDs. It found prior outcomes for all 37 late reservations and zero hits for the original 300 protected groups. A separate cross-check against the broader Phase 0 vector-based JSONL inventory found those 300 groups only in four byte-identical private `study-queries.jsonl` inputs, not in training, development, acquisition or confirmation cohorts.

`reservation-audit.json` contains per-group assignments, broker artifact counts, summary checks, outcome-identity evidence and SHA256 pins. SQLite main files and available WAL files are pinned and checked unchanged across inspection. `reservation-evidence-files.json` lists every matching saved evidence file, its hash and outcome-group hits. The reproducible implementation is `reservation_audit.py`.

The claim is **no outcome exposure found in the recorded local history, supported by protected-state and saved-outcome checks**. No complete remote/chat access log exists. Query values and split metadata appearing in private manifests are not themselves policy-selection feedback. No holdout neighbor, recall, timing or checkpoint outcomes were generated or opened for this review. The search is bounded by canonical query aliases, known study mappings and the broader earlier vector inventory; unlabeled evidence or unrecorded access cannot be ruled out.

## Frozen split

The authoritative split is `../reviews-small/splits/split-manifest.json`, sealed by `../reviews-small/freeze/split-freeze.json`:

- 450 development groups, including all previously consumed evaluations and the 37 late reservations.
- 150 validation groups, preserving the original calibration role.
- 275 test groups: original 150 test plus all 125 previously unreferenced groups.
- 125 historical exclusions, preserving the earlier workload outside holdout.

No new random reshuffle was performed. All seven predicates share one role per vector. Identical vectors keep that role in overlapping-scale studies. The original 25/100 provisional allocation was never executed and is superseded before any new validation/test feedback.

At 275 independent zero-loss observations, the exact one-sided 95% upper loss-probability bound is approximately 1.0834%. This remains insufficient for a worst-case 0.25 percentage point population mean-recall loss guarantee. Phase 1 must resolve the claim and interval before execution.

`freeze_clean_split.py` checks the evidence hashes, role disjointness, consumed-group placement, outcome-hit exclusions and private-inventory intersections, and refuses to overwrite a differing freeze. The frozen catalog contains 7,000 query/filter records. `../reviews-small/prepare_development.py` verifies the split seal and emits only the 450 development groups (3,150 query/filter requests); it does not load holdout outcomes. Physical engine-field mapping and runtime/ground-truth qualification remain pending.

## Next step

Finalize the study protocol and new episode configuration, qualify the reused runtime on development data, then rerun the agent with development-only feedback. Freeze the candidate pool and selection rule before a single bounded validation selection. Freeze selected policies, baselines, analysis and schedule before test. The historical policy stays as a comparator; the fresh episode is required.
