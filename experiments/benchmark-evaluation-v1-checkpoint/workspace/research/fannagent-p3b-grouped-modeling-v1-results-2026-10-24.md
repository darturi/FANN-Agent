# P3b — grouped stopping-model comparison v1

Completed October 24, 2026, America/New_York. Experiment: **NEXT-MODEL-01**.

**P3b is complete. Neither frozen procedure produced a qualifying stopping policy.** Every one of the twenty profile × method × outer-fold selections fell back to measured profile continue. The fixed Extra Trees diagnostic found positive mean cost proxies, but failed recall protection on unfiltered queries. This closes this finite comparison negatively; it does not establish an information ceiling or justify deploying or compressing the ensemble. Original execution remains adopted. M1, M2, M3 and canonical serving acceptance remain false.

The next proposed step is **P3c / NEXT-RISK-01: one prospectively bounded comparison that separates recall-loss risk from savings prediction**, holding qualified features, action grid and model capacity fixed. Its design and resource contract must be frozen before fitting. No Torch command or new measurement is needed now. P3c has not been implemented or run by this report.

## Evidence and reproducibility

| Artifact | Location / identity |
| --- | --- |
| Frozen scientific contract | [contract.json](../agent/experiments/grouped-stop-modeling-v1/contract.json), SHA-256 `d50ccf6a7b41e7b7af79541c6b0f55cd87ef20acb4842636fb0da63125f1b5c7` |
| Source, pinned inputs and run instructions | [P3b implementation](../agent/experiments/grouped-stop-modeling-v1/README.md); 10 source files, 99 pinned input/validation files |
| Successful run | [p3b-20261024-local-v1](../trials/torch-reviews-grouped-stop-modeling-v1/runs/p3b-20261024-local-v1/) |
| Full results | [performance.json](../trials/torch-reviews-grouped-stop-modeling-v1/runs/p3b-20261024-local-v1/performance.json), SHA-256 `de04f6d303f61516b65c814f2e5071b1653bc1c935c594b77050c2d15cb1368a` |
| Formal receipt | [grouped-stop-modeling-v1-postrun.json](../agent/docs/verification/grouped-stop-modeling-v1-postrun.json), SHA-256 `32f74f6a853ed7272ee213324cbbbb33aace4c341587753b996637facc5f90ca` |
| Independent saved-result replay | [verification-replay.json](../trials/torch-reviews-grouped-stop-modeling-v1/runs/p3b-20261024-local-v1/verification-replay.json), [verifier source](fannagent-p3b-grouped-modeling-2026-10-24/verify_saved.py) |
| Descriptive failure analysis | [analysis.json](fannagent-p3b-grouped-modeling-2026-10-24/analysis.json), [analysis source](fannagent-p3b-grouped-modeling-2026-10-24/analyze_saved.py) |
| Prior evidence boundary | [P3a audit](fannagent-p3a-evidence-audit-2026-10-24.md), [roadmap](fannagent-performance-research-roadmap-2026-10-22.md) |

The successful run's design lock binds the contract, source, local checks, installed package versions and input pins before fitting. Its verification inventory hashes 803 result/model/fit/fold/selection artifacts. All hashes and group boundaries passed a subsequent data-only replay. Prior evidence, production code and production Python environments were preserved.

## Design actually executed

The comparison used the same **200 previously exposed vectors / 600 query-filter cases**, retaining the exact five existing outer folds of forty vectors. All three filter cases for a vector stayed together. Each outer training pool contained 160 vectors, partitioned into four deterministic inner folds: 120 fitting and forty validation vectors per inner fit. All model fitting, group-support pruning and risk/threshold selection used training groups only. There was no full-data refit or globally selected policy.

Within each qualified static23/progress34 profile, the comparison matched decision-time information and the measured action grid: **1/2/4/8/16/32/64/128**, plus same-profile continue. All 4,695 reachable grid stops per profile had actual measured outcomes. Unreachable checkpoints were masked, invalid/incomplete outcomes remained negatives, and IDs, evaluator strata, future states and truth were forbidden predictor inputs.

| Component | Frozen choice |
| --- | --- |
| Shallow method | `DecisionTreeRegressor`, squared error, maximum depth 3, minimum eight rows per leaf |
| Flexible method | `ExtraTreesRegressor`, 64 trees, maximum depth 8, minimum eight rows per leaf, all features, no bootstrap, one thread |
| Common support restriction | After fitting, prune any split with a child containing fewer than eight **distinct fitting vectors**; retain the fitted parent value |
| Common target | Minimum of activation/reuse fixed-stop savings proxies, minus risk weight × positive recall loss, minus 1,000 ms for invalid/incomplete output |
| Weighting | Every vector totals one; its three queries have equal total weight across their reached grid states |
| Fixed risks / score thresholds | Risks 20/80/320/1280; thresholds 0/.1/.25/.5/1/2/4 ms |
| First-stop decision | First reached allowed checkpoint with predicted score at least the threshold; otherwise measured profile continue |
| Inner selection | Pool all four inner OOF folds; choose highest minimum mean savings proxy among qualifying candidates, breaking exact ties toward higher risk then threshold |
| Admission | Complete valid top-10, native recall floor .95 per filter, lower 95% recall-delta bounds ≥ −.0025 overall and every filter, positive mean activation **and** reuse proxies overall, at least one stop |
| Rejection | Explicit same-profile continue; no outer-outcome rescue |
| Fixed diagnostic | Risk 320 / threshold 0 refitted on each outer training pool, regardless of selection; diagnostic cannot rescue a rejection |
| Controls | Analytical native, measured profile continue, fixed checkpoint128 else continue |
| Uncertainty | 10,000 vector-cluster bootstrap resamples, seed 20261019, pointwise intervals conditional on fixed OOF fits |

There was no learned imputation, scaling, feature selection, global quantile fitting or additional seed/model search. The two procedures differ in algorithm, ensemble and depth, so their contrast does not isolate model capacity causally. This shallow regression procedure is also distinct from the earlier first-stop beam fitter.

## Calibrated result: all twenty selections abstain

The table reports 600 held-out cases per row. Positive proxy savings favor stopping. These are reused fixed-stop acquisition costs, **not newly measured learned-policy latency**.

| Profile | Method | Non-continue outer selections / 5 | Stops / 600 | Recall difference, pp | Activation proxy saved, ms | Reuse proxy saved, ms | Qualifying signal |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| static23 | Shallow | 0 | 0 | 0 | −2.250748 | −1.055653 | No |
| static23 | Extra Trees | 0 | 0 | 0 | −2.250748 | −1.055653 | No |
| progress34 | Shallow | 0 | 0 | 0 | −1.870839 | −0.996567 | No |
| progress34 | Extra Trees | 0 | 0 | 0 | −1.870839 | −0.996567 | No |

Recall/validity pass because continue preserves native outcomes. The negative savings are the historical measured cost of continuing through the corresponding profile, relative to its native baseline. They are not a newly observed agent regression; nothing was adopted. The actual system retains original execution rather than installing a profile-continue model.

All calibrated flexible-minus-shallow paired contrasts are exactly zero, with zero-width conditional intervals: both methods chose identical continue actions. This is not evidence that their predictive capacity is equivalent.

## Why selection rejected every candidate

Each row below aggregates five outer training pools × four risks × seven thresholds. The 560 assessments overlap in training data and configurations; they are not 560 independent experiments.

| Profile / method | Inner candidate assessments | Pass recall / validity gate | Positive mean proxies in both regimes | Pass full admission |
| --- | ---: | ---: | ---: | ---: |
| static23 / shallow | 140 | 89 | 50 | 0 |
| static23 / Extra Trees | 140 | 58 | 71 | 0 |
| progress34 / shallow | 140 | 102 | 38 | 0 |
| progress34 / Extra Trees | 140 | 56 | 66 | 0 |
| Total | 560 | 305 | 225 | 0 |

**All 225 positive-proxy candidates fail recall. All 305 recall-passing candidates have nonpositive proxies.** Thirty candidates fail both requirements. Eight shallow/progress34 candidates also produce incomplete results; these remain failures. At risk320 and risk1280 the shallow method makes no inner stops in either profile. The risk1280 ensembles pass recall in every inner candidate, but remain economically negative; some stop rarely, which does not recover profile-continue overhead. Raising risk alone within this frozen grid therefore does not solve the problem.

This documents a risk/savings conflict for the tested utility-regression and calibration procedures. It does not prove that weighted utility regression caused the failure, that no intermediate risk weight could work, or that the qualified observations contain no useful information. No new risk weight, threshold or filter-specific routing rule was selected after seeing these results.

## Fixed ensemble diagnostic: savings with unacceptable tail loss

The predeclared risk320 / threshold0 diagnostic evaluates a model independently of whether inner calibration admitted it. All twenty diagnostic fits and outcomes are retained. Both shallow diagnostics still choose continue on all 600 cases.

| Extra Trees profile | Stops | Recall-loss cases | Overall recall difference, pp [95% interval] | Activation proxy saved, ms [95% interval] | Reuse proxy saved, ms [95% interval] |
| --- | ---: | ---: | --- | --- | --- |
| static23 | 268 / 600 | 11 | −0.2333 [−0.4000, −0.1000] | +0.454613 [+0.144626, +0.756939] | +0.924389 [+0.709103, +1.136249] |
| progress34 | 216 / 600 | 10 | −0.2500 [−0.4667, −0.0833] | +0.194550 [−0.062975, +0.454187] | +0.577725 [+0.378141, +0.778505] |

Both overall recall lower bounds fail the development reserve of −0.25 percentage points. Each would pass the original −0.5 pp bound **overall**, but both fail that original criterion on unfiltered queries, so neither passes the original joint recall replay either.

| Profile | Filter | Stops / 200 | Loss cases | Recall difference, pp [95% interval] | Activation / reuse proxy saved, ms |
| --- | --- | ---: | ---: | --- | --- |
| static23 | unfiltered | 149 | 10 | −0.65 [−1.15, −0.25] | +2.661432 / +2.566213 |
| static23 | votes32 | 100 | 1 | −0.05 [−0.15, 0] | +0.643717 / +1.019456 |
| static23 | votes108 | 19 | 0 | 0 [0, 0] | −1.941310 / −0.812502 |
| progress34 | unfiltered | 131 | 8 | −0.65 [−1.25, −0.20] | +2.208480 / +2.113381 |
| progress34 | votes32 | 75 | 2 | −0.10 [−0.25, 0] | +0.138033 / +0.503542 |
| progress34 | votes108 | 10 | 0 | 0 [0, 0] | −1.762865 / −0.883749 |

The votes32 rows are descriptive subgroup findings, not a selected restricted policy. Adding a post-hoc bypass would require a new prospective comparison using actual qualified predicate inputs, training-only calibration and correct whole-session costs. The table is not permission to route by evaluator stratum or claim free native fallback.

The fixed diagnostic never produces incomplete top-10 results. Static23 stops at checkpoints 16/32/64/128 on 49/110/69/40 cases; losses occur on 0/5/5/1 cases. Progress34 stops on 30/91/76/19 cases, with 0/2/7/1 losses. Ten of eleven static losses and nine of ten progress losses occur in the descriptive native-work bin 10,000–19,999, which contains 354/600 cases. Seven loss cases overlap between profiles; the union is fourteen query-filter cases. Native work is an evaluator-only difficulty descriptor here, not a proposed runtime input or new selection rule.

The ensemble finds additional stopping behavior, but the needed evidence for “flexible succeeds, shallow fails; compress the ensemble” is absent. Progress34 is not demonstrated superior to static23; their cost profiles differ, the comparison is descriptive, and neither qualifies.

## Controls and measurement boundary

Analytical native has zero savings and zero recall difference by definition. Measured profile continue has the overhead shown above and zero recall difference. Fixed checkpoint128 else continue stops 498/600 cases, with sixteen recall-loss cases and overall difference −0.2667 pp [−0.4333, −0.1333]. Its static activation/reuse proxies are +0.363135/+0.578797 ms; progress proxies are +0.316834/+0.526264 ms. It fails the development recall gate and the original per-filter replay on votes108, whose lower bound is −0.85 pp. A late fixed stop is therefore not a qualifying alternative.

No new timings were acquired, so there are no new timing A/A controls to assess. P2b/P2c A/A conclusions remain unchanged. No control subtraction, P2 optimization credit, binary/profile cost transplantation or conditioned P2c timing was used to manufacture savings.

## Correctness, consumption and preserved failure

Fourteen synthetic tests passed, with lint/format checks and a guarded frozen-API import. Three test processes consumed twelve synthetic estimator fits in total, within the separate cap 24. Initial failures were in the test oracle's NumPy scalar casting; the oracle was corrected before scientific fitting. All test logs are retained.

The first launch, preserved under the accidentally dated directory `p3b-20261025-local-v1`, failed before corpus loading with **zero scientific fits**: the offline guard rejected a neighboring Python bytecode-cache lookup. Cache lookups were redirected into the fresh output directory with bytecode writing disabled. The scientific contract did not change. Its original source snapshot, local-check receipt, design lock, failure and logs are preserved in the [preflight repair record](../trials/torch-reviews-grouped-stop-modeling-v1/preflight-repair.json).

| Successful scientific campaign | Actual / limit |
| --- | --- |
| Estimator fits | 340 / 360: 170 shallow and 170 ensembles |
| Individual trees | 11,050, including 10,880 ensemble trees |
| Breakdown | 320 inner fits + twenty fixed-diagnostic outer refits; no selected-risk additional refits |
| Wall time | 235.661 seconds / 3,600 seconds |
| Peak RSS | 1,070,366,720 bytes, about 0.997 GiB / 4 GiB |
| Metered run reads | 841,202,095 bytes, about 0.783 GiB / 16 GiB |
| CPU threads | 1 |
| New native searches / DB / provider / Torch allocations | 0 / 0 / 0 / 0 |
| Protected query-value / confirmation access | 0 / 0 |

Every unpruned canonical model matched scikit-learn predictions on observed fitting/evaluation feature rows. Group pruning reduced shallow nodes 2,404→2,288 and ensemble nodes 2,464,588→1,571,026; all leaves respect eight distinct fitting vectors. Shallow exports pass the frozen policy validator and shared interpreter first-stop checks. This is observed interface parity, not native fault qualification or serving-latency evidence.

The independent saved-result verifier checked all model hashes, 11,050 trees, every inner/outer group split, all **560 inner admission assessments** and **4,800 outer first-stop case records**. It reconstructed each outer action directly from canonical trees and actual measured outcomes, then recomputed reports and paired contrasts within 1e−12. It made zero new fits or measurements. The descriptive analysis likewise imports no modeling code and only summarizes locked results.

## Decision gates and next step

1. **Close NEXT-MODEL-01:** complete, independently replayed, negative for these frozen procedures. Preserve all candidates and the explicit fallback; no threshold rescue, rerun or extra forest fitting.
2. **G3 = revise:** no qualifying family selected. Keep original execution. Do not advance automatically to SMAC/Ax, acquisition optimization, prompt tuning, framework migration, ensemble compression or independent confirmation.
3. **Prepare P3c / NEXT-RISK-01:** isolate one formulation change: model recall-loss risk separately from potential savings, at unchanged runtime-information/action/model-capacity scope. Freeze training-only grouped risk calibration, candidate count, finite resources, unchanged quality reserve, full first-stop evaluation and paid continue before any fit. This is a hypothesis motivated by the observed conflict, not a confirmed cause. Explicitly account for prior adaptation to these 200 vectors.
4. **P3c gate:** a qualifying development signal permits representation/interface review and a separately contracted actual-latency comparison. Failure closes that finite formulation allowance; choose either justified fresh **development** diversity under a new entitlement/measurement contract or B1's broader optimization scope. Do not repeat exposed-data tuning indefinitely. Protected evaluation samples stay bound to their existing contracts.

Existing static23/progress34 grid labels suffice for this proposed formulation test. Current Light19/off-grid gaps remain conditional, and no newly fitted policy's composite-session latency has been measured. Neither grouped OOF evaluation nor a conditional bootstrap removes prior design adaptation or establishes generalization. A future policy still needs independent quality and actual-latency evidence before M2.

## Primary methodology sources

- [scikit-learn 1.7 DecisionTreeRegressor](https://scikit-learn.org/1.7/modules/generated/sklearn.tree.DecisionTreeRegressor.html): shallow estimator and float32 input semantics.
- [scikit-learn 1.7 ExtraTreesRegressor](https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.ExtraTreesRegressor.html): ensemble parameters and prediction behavior.
- [Nested versus non-nested cross-validation](https://scikit-learn.org/1.7/auto_examples/model_selection/plot_nested_cross_validation_iris.html): separate model selection from outer evaluation.
- [scikit-learn common pitfalls](https://scikit-learn.org/1.7/common_pitfalls.html): training-only learned transformations/selection and leakage prevention.

The utility target, distinct-vector pruning, resource ceilings and quality gates are explicit project choices. The sources justify estimator/evaluation mechanics; they do not establish that these choices will work on this workload. All empirical conclusions above come from the linked local artifacts.
