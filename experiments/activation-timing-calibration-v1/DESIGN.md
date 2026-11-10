# P2c activation timing calibration v1 — frozen contract

Experiment: **NEXT-CAL-01**, prepared October 23, 2026 following the independently verified [P2b result](../../../research/fannagent-admission-profile-identity-v1-results-2026-10-23.md). The user requested implementation, local checks and a ready-to-run package. One implementation and one two-block campaign only. No new stopping policy, native module, provider call, confirmation query or production change.

## Question and operating scope

Can identical execution paths establish the existing per-filter ±0.10 ms / ±log(1.02) equivalence bounds when activation is measured in adjacent counterbalanced crossovers with fixed shared-data conditioning?

P2b's old result remains `measurement_inconclusive`. Its descriptive audit found later-label associations; it did not establish a cause. This experiment tests a separately declared **conditioned-index/query, fresh-policy-session** timing protocol. It does not measure a cold index, first access to a novel query or fresh connection/server. It does not retroactively repair or pool with P2b. No power or interval-width guarantee is made.

Every slot first installs the original eviction sentinel and clears the Python prepared-policy cache. It then performs exactly **two ordinary-native conditioning executions of that query**. Their outputs, times and resource use are recorded. These calls cannot prepare a policy, compile its tree, change active policy installation or create the measured session; runtime checks enforce empty cache/unchanged installation afterward. Two is fixed before dispatch, never increased until timings look favorable. No cache flush, adaptive warmup, latency-based sample rejection, GC setting, thread/transport change or new execution implementation is introduced.

After conditioning ends, a **fresh measured session** is created. All original policy admission, P2b snapshot copying/fingerprinting, binding checks and host wrapper construction remain charged to its first activation pair. First policy preparation, lazy compilation, acknowledged installation and first execution remain inside the original backend/query timers. Outer application time also includes admission. The native A/A control charges its small wrapper construction/overhead and performs ordinary native execution without policy admission. This explicitly restricted measurement objective must be reviewed before any operating-scope or adoption decision.

Conditioning and reset work is excluded from the restricted service-latency endpoint because it defines shared-data state, but is included in the **campaign search/installation ceiling** and separately reported as total native/outer conditioning cost and reset/conditioning wall time. It is not free work or a claimed end-to-end deployment saving. No policy work may be hidden in it.

## Frozen execution and inputs

Use the exact original selective pilot core/adapter and fixed candidate `cons-bypass108`, semantic hash `a014a290966444a86614f1e5be1960dad2fb8684044e85e9df82899911062b0d`. Preserve its seed credit, matched-continue tree, host routed-native empty mask, light19 profile, three filters, all 200 exposed vectors / 600 cases, `ef_search=640`, `k=10`, the physical 247,286-row index, x86 module and image.

Four P2a/P2b execution/validation sources are copied **byte-for-byte**: `pp_backend.py`, `pp_session.py`, `pb_policy.py`, `pb_session.py`. No query normalization, route, SQL, tree validation, native getter, compilation or error behavior is changed. Local AST and protocol-stub checks retain original rejection/numeric/depth/ownership/connection/cache/invalidation semantics. Frozen P2b gate logic is also copied byte-for-byte as `p2b_report_reference.py` and its gate function is reused; its unrelated old analyzer is not called.

There are ten calibration cells:

- Original, frozen P2a (`owned`), and frozen P2b (`admission`) for each of candidate, matched-continue and routed-native: nine cells.
- One plain-native cell across all three filters, without duplicate policy identities: one cell.

Each cell has A/B labels using exactly the same factory/class and raw policy, with distinct fresh sessions and handles. The resulting twenty label/semantic arms retain their own ordinary-native timing pairs. Labels do not change any policy data. Exact/native/light19 references and nine actual policy-path stop proofs are executed once per case; the plain-native proof reuses the ordinary-native reference. Both identical labels are checked against the same proof. All output IDs/distances, quality, actual stop/prefix and native acknowledgements remain required.

## Adjacent crossover schedule

For each query/cell, one hash selects either **A B B A** or **B A A B** across two rounds. Each round has an adjacent A/B pair, with order reversed in the other round. Every slot independently resets policy state, performs the two conditioning executions and creates a fresh session. Reuse measurements stay inside that session, never reuse a prior slot's handle, and do not replace the next slot's cold admission.

Block 1 complements block 0's label order, so each label occupies each of the four slot positions once across the two blocks. Cell order is query-hash shuffled in block 0 and reversed in block 1; this balances average cell position, not every possible ten-cell predecessor/position combination. Query order uses seed `20261022 + block`. Pair-native-versus-subject order is hash-selected from query/cell/block/round/repetition and held identical across A/B within a round.

Each fresh slot runs the existing five-pair schedule: one retained activation pair, one discarded warmup pair and three retained reuse pairs. Each pair executes ordinary native and the subject once. No profiler runs in this campaign; the execution code is unchanged and previously qualified mechanism sources are pinned. There is no adaptive subsampling or optional block.

Raw files separately record references, actual proofs, retained pairs, discarded warmups, conditioning calls and slot phase boundaries. The trusted verifier reconstructs exact query/cell/round/label/repetition order; checks all conditioning outputs, fixed counts, empty policy-state assertions, chronological boundaries and no overlapping phases; and verifies the first pair includes exactly its recorded constructor preparation charge. Query/index conditioning cannot overlap construction or measured execution.

## Analysis and gates

The independent unit stays the **vector**: 200 groups, all filters/blocks/rounds/labels/repetitions clustered together. Use the original 10,000-resample vector bootstrap, seed 20261019. Twenty labels, two rounds and two blocks do not create new independent vectors. Retain every observation, including inconvenient blocks/outliers. The reported confidence intervals are pointwise; no simultaneous-region or cross-workload generalization claim is made.

For each of the ten identical-path cells, both regimes, every filter and overall (80 cells total), require the complete two-sided 95% primary and outer B-minus-A intervals to lie within `[-0.10,+0.10]` ms and the complete log-ratio interval within `[-log(1.02),+log(1.02)]`. All **240** endpoints must pass. Including zero alone is insufficient. Missing cells/regimes/filters fail verification. Native/original/P2a controls are mandatory as well as P2b controls. All identities, raw hashes, counts, outputs and original quality checks are required.

Also report uncorrected direct P2a-versus-original, P2b-versus-P2a and P2b-versus-original contrasts in this **new scope**. Within each query/block/round/regime/repetition, average the two reference labels and contrast each treatment label against that reference average, retaining their shared vector cluster. No ordinary-native gap subtraction or A/A correction is used. Report every semantic arm/regime/filter and overall, with block-specific direct contrasts and descriptive AB/BA orientation means by filter/block.

The exact frozen P2b engineering criteria remain binding: candidate incremental activation versus P2a must establish at least 0.10 ms/2% primary and 0.10 ms outer saving with the saving direction in both blocks; candidate combined reuse versus original must meet the same minimum benefit and block directions; all 144 absolute/relative/outer nonregression bounds and original development recall/native-floor protections remain required. Original candidate activation/reuse versus ordinary-native qualifiers are reported separately. All native/original/P2a/P2b A/A cells must additionally qualify before an engineering pass in this conditioned scope can be interpreted.

Report `calibration_gate=pass` only if all new A/A bounds pass, otherwise `measurement_inconclusive`. Preserve the frozen engineering failure strings and override its displayed verdict to `measurement_inconclusive` if any new calibration control fails. A calibration pass with failed engineering criteria remains `revise_or_retain_original`. Even both passing means qualified evidence in the new restricted scope, **not** retroactive P2b acceptance, M1/M2/M3, selection, deployment or canonical serving acceptance. Operating-scope review and broader native lifecycle qualification remain separate requirements.

## Finite resources and branch

| Item | Per block | Whole campaign |
| --- | ---: | ---: |
| Serial allocations | 1 | At most 2 |
| CPU / RAM / wall limit | 4 CPUs / 32 GiB / 3 hours | <=6 allocated wall-hours, 24 allocated CPU-hours |
| Internal work deadline | 10,200 seconds | One fixed deadline per block |
| Getter searches | 921 | 1,842 |
| Exact/native/trace references | 1,800 | 3,600 |
| Actual original/P2a/P2b path proofs | 5,400 | 10,800 |
| Native conditioning executions | 48,000 | 96,000 |
| Paired timing executions including warmups | 240,000 | 480,000 |
| Total backend/reference searches | **296,121** | **592,242** |
| Fresh slots / constructor charges | 24,000 | 48,000 |
| Retained activation + reuse pairs | 96,000 | 192,000 |
| Discarded warmup pairs | 24,000 | 48,000 |
| Separately counted eviction installations | 24,000 | 48,000 |
| Provider calls / protected confirmation queries | 0 / 0 | 0 / 0 |

Per-block search formula: `921 + 600 × (3 references + 9 proofs + 10 cells × 2 rounds × 2 slots × (2 conditioning calls + 5 pairs × 2 executions))`. Evictions are separate SQL operations; not every SQL statement is counted. These are compute ceilings, not runtime predictions. The two-block design balances crossover positions; it is not a power guarantee.

Two `afterok` serial jobs restore/stop private databases. Durable protocol reservation, package binding and per-block dispatch records prevent duplicate/reupload submission; uncertain dispatch is not retried. Earlier pilot/P1/P2a/P2b sealed inputs and completed raw results are checked and remain read-only. A failed, incomplete, unknown or inconclusive campaign consumes this allowance. Do not add blocks, change margins, repeat until pass, retune conditioning or combine a new optimization.

If calibration is unjustified or still inconclusive, retain original execution and explicitly redirect to bounded P3 information diagnosis. If calibration passes, review engineering results and operating scope before choosing a baseline. Any further mechanism/version needs a separately justified contract; this package does not grant another campaign.

## Integrity and return handling

Manifest anchors: original pilot `082b167507e25009bdb25ea613950cd434ef38608fbcbc6194af19c363d0f6dc`; P2a `c4c00e12a08963751ab20aed3f195ed3af2a515be40c0bdd619ce57209bca60c`; P2b `7c82194d375a77f29356e3620d2f011b2b0e452b9954defcb75aaec90f29350d`. P2b postrun receipt `ba3f5116ab2583d61fac024dbb899112803fcc7fad18687a9ed64bc5f374a88f` binds the failed prior gate and all raw hashes. The new manifest pins all sources/contracts/inputs and copied reference bytes.

Data-only ingestion uses sealed local code and never returned Python/shell. It rejects links, traversal, nonregular/duplicate members, over 10,000 files, over 256 MiB per file or over 2 GiB total. Remote/local discrete values must match exactly; floating tolerance remains 1e-12. Local protocol simulations, AST checks and fake timings are correctness evidence only; native qualification, equivalence and performance await this Torch campaign.
