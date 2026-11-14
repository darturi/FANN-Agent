# P2c activation timing calibration v1 — verified results

Analysis date: October 24, 2026, America/New_York.  
Experiment: **NEXT-CAL-01**. Campaign: `reviews-activation-calibration-v1-20261024T025706Z.c8557262`.  
Decision: **calibration passes in the declared conditioned scope; the execution engineering gate remains `revise_or_retain_original`. Retain original execution and close this finite P2 sequence without adoption. Proceed to bounded P3 information/outcome-coverage diagnosis.**

P2b's activation benefit over original and P2a, and its reuse benefit over original, persist in this new comparison. Additional reuse improvement over P2a remains unestablished. The earlier P2b campaign keeps its `measurement_inconclusive` verdict. This review changes no code, runs no experiment and makes no policy-selection, confirmation, deployment or agent-method claim. [Postrun receipt][receipt], [sealed reconstruction][verification], [frozen contract][contract].

## What P2c measured

P2c uses the unchanged original, P2a and P2b execution implementations and unchanged policies. Before each fresh measured session, it resets policy state and performs exactly two ordinary-native executions of the same query. These condition shared query/index state without preparing or installing the measured policy. Full session admission, profile copy/fingerprint, lazy backend preparation, compilation, installation and first execution remain charged to activation and outer application timing.

The endpoint is **conditioned shared query/index state with a fresh policy/session**. The raw regime name `activation-cold` refers to fresh policy state. It does not mean a cold index, novel first query, fresh connection or fresh server. Conditioning/reset costs are resource-counted and separately reported, but excluded from this restricted service endpoint. The absolute milliseconds and percentages must not be compared across the old P2b and new P2c campaigns as a treatment effect. All improvement claims below use concurrent direct execution-version contrasts within P2c. [Contract][contract], [performance data][performance].

## Integrity, execution and resource verification

The archive checksum matches. All **41 unique regular members**, totaling **719,154,932 uncompressed bytes**, match the existing extraction. The sealed implementation receipt, package manifest, package archive and source files match their pre-dispatch anchors. P2a/P2b/P2c source files remain unchanged.

A fresh reconstruction with the sealed local package verified all **26 locked raw-file hashes**, protected before/after inputs, module/image/profile/index identities, getter qualification, complete coverage, references, actual first-stop proofs, timed IDs/distances, schedule and phase ordering, conditioning outputs and counts, empty policy-state assertions, and full first-admission charges. Both runtime and host exits are zero. No returned Python or shell was executed.

The result matches the download-helper reconstruction exactly. Five floating values differ from the remote result by at most **3.47e-18**, below the frozen **1e-12** tolerance; every discrete value matches. `report.txt` and `calibration.md` reproduce byte-for-byte. The [receipt][receipt] preserves all raw hashes and parity details.

| Item | Verified actual use |
| --- | ---: |
| Completed serial jobs | 2: `20778104`, `20778105` |
| Exposed development vectors / query-filter cases | 200 / 600 |
| Backend/reference searches | 592,242 |
| Included ordinary-native conditioning executions | 96,000 |
| Retained activation/reuse pairs | 192,000 |
| Discarded warmup pairs | 48,000 |
| Fresh session slots / separate eviction installations | 48,000 / 48,000 |
| Provider calls / protected confirmation queries | 0 / 0 |
| Sum of internal elapsed times | 6,769.14 seconds; approximately 112.82 minutes |

Each block uses exactly 296,121 searches and completes within its 10,200-second work deadline. The two-block campaign allowance is consumed. Internal elapsed time is not a billing record or a query-latency endpoint. Labels, rounds, blocks and repetitions remain clustered within **200 independent vectors**, using the frozen 10,000-resample bootstrap with seed 20261019. Intervals are pointwise, not a simultaneous confidence region or a claim across future machines/workloads.

## Do P2b's gains hold?

These pooled candidate means use both identical labels for each execution version within P2c:

| Candidate execution | Fresh-session activation ms | Reuse ms |
| --- | ---: | ---: |
| Original | 7.769017 | 5.336453 |
| P2a | 7.743566 | 5.079864 |
| P2b | **7.597712** | **5.085066** |

Negative gaps favor P2b. Arithmetic savings use the ratio of reported arithmetic means; gate decisions use the separate frozen confidence requirements.

| Direct comparison | Regime | P2b minus reference ms | 95% gap interval ms | Arithmetic saving |
| --- | --- | ---: | --- | ---: |
| P2b versus original | Activation | -0.171305 | [-0.189662, -0.152548] | **2.205%** |
| P2b versus P2a | Activation | -0.145854 | [-0.163744, -0.127846] | **1.884%** |
| P2b versus original | Reuse | -0.251387 | [-0.263132, -0.239246] | **4.711%** |
| P2b versus P2a | Reuse | +0.005202 | [-0.005152, +0.015782] | -0.102%; no established added benefit |

The qualitative mechanism survives calibrated measurement: P2b reduces admission/activation cost; P2a already supplies the reuse improvement. P2a itself saves **4.808%** candidate reuse time versus original in P2c. These findings do not reopen P2a's earlier failed gate or P2b's earlier inconclusive gate.

Required saving directions hold in both blocks:

| Candidate contrast | Block 0 saving ms | Block 1 saving ms |
| --- | ---: | ---: |
| P2b activation versus P2a | 0.136903 | 0.154806 |
| P2b activation versus original | 0.170236 | 0.172374 |
| P2b reuse versus original | 0.256297 | 0.246477 |

Candidate activation improves over P2a in every filter: unfiltered saves 0.144799 ms, `votes32` 0.145653 ms and `votes108` 0.147111 ms; all three gap intervals exclude zero. Matched-continue and routed-native activation save 0.148746 ms and 0.174560 ms versus P2a. This is consistent with a shared admission mechanism rather than improved stopping decisions.

Combined candidate reuse gains over original come from unfiltered and `votes32`, saving 0.386590 ms and 0.383299 ms. Native-bypass `votes108` shows no established combined reuse benefit: gap +0.015728 ms, interval [-0.005105, +0.035988]. Against P2a, that bypass stratum has a small positive gap **+0.021879 ms**, interval **[+0.003019, +0.041605]**. It passes the practical nonregression requirements, but should not be described as zero difference or universal P2b improvement. [Complete filter/block results][performance].

## A/A controls now pass

Every mandatory control meets the declared equivalence bounds, including plain native, original, P2a and P2b. All **80 cells / 240 interval checks** pass: both regimes, every filter and overall, with primary and outer intervals wholly inside ±0.10 ms and log-ratio intervals wholly inside ±log(1.02).

| Identical execution path | Required/passing cells | Passing interval checks | Largest absolute primary CI endpoint ms | Largest absolute outer CI endpoint ms |
| --- | ---: | ---: | ---: | ---: |
| Plain native | 8 / 8 | 24 / 24 | 0.021653 | 0.021695 |
| Original, three semantic arms | 24 / 24 | 72 / 72 | 0.061166 | 0.061056 |
| P2a, three semantic arms | 24 / 24 | 72 / 72 | 0.044925 | 0.045050 |
| P2b, three semantic arms | 24 / 24 | 72 / 72 | 0.053297 | 0.053333 |

The largest absolute log-ratio interval endpoint is **0.007414**, within **log(1.02) = 0.019803**. P2b candidate overall activation B-minus-A is +0.008463 ms, interval [-0.006327, +0.023045]; reuse is -0.001724 ms, interval [-0.008104, +0.004458]. Unlike P2b's earlier activation/filter controls, all new per-filter obligations pass.

Equivalence does not require an interval to include zero. Original/candidate activation on `votes32`, for example, has a directional interval [-0.061166, -0.002656] ms while remaining entirely within the practical equivalence band. A small label association can coexist with a calibration pass. Passing the controls supports this declared design at its fixed margins; it does not establish the cause of the earlier order effects or eliminate every timing bias.

The predeclared order diagnostics retain all observations. Candidate activation B-minus-A averages -0.003878 ms in AB rounds and +0.020805 ms in BA rounds. On `votes108`, the respective means are +0.029995 and -0.015691 ms, so the earlier campaign's uniform later-label advantage is not reproduced in that stratum. These are descriptive means without new conditional inferential gates. They do not identify cache, transport or drift as a cause, and no A/A or native gap is subtracted from treatment effects. [Order diagnostics and all control intervals][performance].

## Why the engineering gate still fails

All **144 practical nonregression checks** pass, as do the development quality checks, required block saving directions, dedicated combined reuse improvement and absolute/outer incremental activation targets. The exact frozen P2b gate reports one failure:

> `p2b_vs_p2a/activation-cold: relative saving lower bound below 2%`

The incremental activation mean log-ratio interval is **[-0.022365, -0.017664]**. Its upper endpoint must be at most **log(0.98) = -0.020203**. The implied lower saving bound is **1.751%**, below 2%. Absolute primary and outer saving lower bounds are **0.127846 ms** and **0.126142 ms**, above 0.10 ms. A/A precision is no longer the failing requirement; the remaining practical activation requirement still binds.

P2b's combined activation comparison with original has an implied relative lower saving bound of 2.040%, but the contract specifically requires the **incremental comparison with P2a**. Substituting the easier original reference would change the gate after seeing the results. P2b's combined reuse comparison with original satisfies both absolute and relative requirements. The new verdict is therefore **`revise_or_retain_original`**, not `measurement_inconclusive` and not `pass`.

## Residual costs, ordinary native and quality

Pooled unprofiled candidate constructor preparation is **1.552772 ms original**, **1.555553 ms P2a** and **1.392070 ms P2b**. P2b saves approximately 0.163484 ms versus P2a in this component; the full activation saving is 0.145854 ms. Constructor timing alone cannot replace the full-path result. No new profiler pass was performed, so earlier fingerprint/copy call counts remain historical P2b evidence rather than new P2c measurements.

Conditioning consumes **531.632 seconds** of recorded native ANN time and **563.091 seconds** of outer time across 96,000 calls. Reset/conditioning/bookkeeping wall time before construction totals **651.629 seconds**. These are overlapping accounting views, not additive savings. Across 48,000 slots, the constructor preparation charges total **61.397 seconds**, and those charges remain included in activation. A deployment that needed this conditioning per fresh request would need its costs included in a separately declared endpoint; P2c does not establish such a deployment gain.

Against each label's own ordinary-native reference, P2b candidate activation still adds **2.046 / 2.055 ms**, or **36.876% / 37.036%** for A/B. Reuse saves approximately **0.460 ms**, or **8.300% / 8.298%**. Both reuse qualifiers pass; both activation qualifiers fail. These native-relative figures have a different reference from the direct original/P2a execution comparisons above. The plain-native control also includes a wrapper whose timing is charged; its A/A pass does not require that wrapper's total equal bare backend timing and does not supply a correction factor.

Original/P2a/P2b outputs and actual stops match on the declared inventory. Native recall remains **99.35%, 99.15%, 98.60%** on unfiltered, `votes32`, `votes108`. Candidate recall is **99.35%, 99.10%, 98.60%**. Its overall difference remains -0.016667 percentage points, interval [-0.050000, 0.000000], with the earlier small loss confined to `votes32` and inside the development reserve. There is no added execution-version quality loss. All observations use the same exposed development vectors; independent policy confirmation and canonical serving acceptance remain absent.

## Roadmap decision and next step

1. **Close NEXT-CAL-01 as verified.** Record scoped calibration pass and engineering `revise_or_retain_original`; retain all prior gates and the full resource use. The single P2c allowance is consumed. No extra block, retuned warmup, threshold relaxation, repeated calibration or automatic P2d optimization follows.
2. **Close the present P2 branch with an explicit retain-original decision.** Original execution remains the adopted baseline for subsequent bounded stopping-policy research; P2a/P2b remain preserved experimental references. G2 is `closed_negative` for optimized-execution qualification, with its administrative branch decision complete. M1, M2 and M3 remain unestablished. A general operating-scope/native lifecycle adoption review is deferred because the engineering gate already fails.
3. **Prepare P3a / NEXT-INFO-01 as the next offline task.** Inventory existing permitted development trajectories, qualified runtime features, actual stop proofs, vector identities/exposure and execution-cost identities. Report measured versus unknown stopping outcomes by filter/stage/policy before fitting anything. Separate diagnostics that reuse exposed vectors from any independent evaluation. Do not assign P2c's conditioned timings to the retained original operating scope.
4. **Use a coverage gate before modeling or new measurement.** If measured outcomes support a comparison, freeze vector-group folds, leakage controls, a flexible-versus-deployable-shallow comparison, first-predicted-stop evaluation, objectives, owner and finite budget. If coverage is inadequate, specify the smallest targeted acquisition contract and its cost instead of interpolating missing labels or broadly remeasuring everything. Neither fitting nor acquisition is implemented or run by this review.
5. **Advance G3 only from that evidence.** Distinguish missing outcomes, inadequate features, limited policy representation and inadequate independent diversity. Select at most one justified intervention, or close the current family. P4 numerical search, P5 acquisition and later agent/framework changes remain conditional on G3. Existing confirmation entitlements and the closed selective episode retain their contracts.

The next dependency is the **offline coverage/identity inventory**, not another Torch timing job. **No user command is needed now.** Any later targeted Torch acquisition must first have a separate reviewable contract, resource ceiling and exact run instructions. The [roadmap][roadmap] records the revised critical path and task boxes; this document does not authorize additional compute or data access.

## Artifact identities

| Artifact | SHA-256 |
| --- | --- |
| Returned P2c archive | `22813fb22742b7dec45903594c41e752dc3ee64e6ebe076cccf4d60257d0f599` |
| Sealed package manifest | `6b6f216977482287838d4c9fbc06e8bb113cb283ff5c8a911ab9055cd7ae6fc0` |
| Historical implementation receipt | `178a859a954d193032307817c8ce562028d8174a9294ae939ff86f1741a7d9a2` |
| Postrun receipt | `533adf3dd53e10966c7edb74fbfd570e0e3bdbe8127ccc2f54f393bb893e6aec` |

[receipt]: ../agent/docs/verification/activation-timing-calibration-v1-postrun.json
[verification]: ../trials/torch-reviews-activation-timing-calibration-v1/analysis-review/reviews-activation-calibration-v1-20261024T025706Z.c8557262/verification.json
[performance]: ../trials/torch-reviews-activation-timing-calibration-v1/analysis-review/reviews-activation-calibration-v1-20261024T025706Z.c8557262/performance.json
[contract]: ../agent/experiments/activation-timing-calibration-v1/DESIGN.md
[roadmap]: fannagent-performance-research-roadmap-2026-10-22.md
