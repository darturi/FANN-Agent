# P3c — risk-separated stopping-model comparison v1

Completed October 24, 2026, America/New_York. Experiment: **NEXT-RISK-01**.

**P3c is complete and independently verified. Neither profile/method produces a qualifying joint result.** Separating recall-loss prediction from savings estimation admits four ensemble selections, but the calibrated static ensemble fails the per-filter development recall reserve and activation economics; the calibrated progress ensemble passes recall but loses on both cost proxies. Both shallow methods choose continue. Original execution remains adopted; no production policy or serving-speed improvement is established.

Close this finite formulation allowance and the bounded P3 investigation with **G3 `closed_negative` for the tested procedures**, not a universal information/family ceiling. The recommended next scope is **B1a / NEXT-SCOPE-01: a read-only feasibility/design audit of query-dependent search effort at fixed index**. Verify actual backend controls and an affordable observation/timing interface before proposing another experiment. B1a is proposed, not performed here. No user or Torch commands are needed now.

## Permanent evidence

| Artifact | Location / identity |
| --- | --- |
| Frozen scientific contract | [contract.json](../agent/experiments/risk-separated-stop-modeling-v1/contract.json), SHA-256 `92928bbca0ca8c1b0a4ac6962d3fe95aa083b96c14e9b49b4ea050c657ae99ae` |
| Implementation and reproduction | [README](../agent/experiments/risk-separated-stop-modeling-v1/README.md); ten locked source files and 919 pinned prior input/artifact files |
| Successful local run | [p3c-20261024-local-v1](../trials/torch-reviews-risk-separated-stop-modeling-v1/runs/p3c-20261024-local-v1/) |
| Complete performance data | [performance.json](../trials/torch-reviews-risk-separated-stop-modeling-v1/runs/p3c-20261024-local-v1/performance.json), SHA-256 `4465d0a7a3386ba2bcd6ed79d05208438ab4a939925ad72a0e35e17a48e0f8b1` |
| Formal verification receipt | [risk-separated-stop-modeling-v1-postrun.json](../agent/docs/verification/risk-separated-stop-modeling-v1-postrun.json), SHA-256 `f103f3f0e793eb73edd430b862c406187754cfda10dce9bb958a7158456d0c57` |
| Independent saved-result replay | [verification-replay.json](../trials/torch-reviews-risk-separated-stop-modeling-v1/runs/p3c-20261024-local-v1/verification-replay.json), [verifier](fannagent-p3c-risk-separated-modeling-2026-10-24/verify_saved.py) |
| Descriptive analysis | [analysis.json](fannagent-p3c-risk-separated-modeling-2026-10-24/analysis.json), [analysis source](fannagent-p3c-risk-separated-modeling-2026-10-24/analyze_saved.py) |
| Prior comparison | [P3b report](fannagent-p3b-grouped-modeling-v1-results-2026-10-24.md), preserved unchanged |
| Current program record | [Roadmap v1.12](fannagent-performance-research-roadmap-2026-10-22.md) |

The contract was frozen at `2026-10-25T00:09:01.895532Z`, October 24 at 8:09 p.m. EDT, before implementation checks or scientific fitting. There were no post-freeze scientific-criterion changes and no failed scientific launches. The initial source/check snapshot, logs and data-only preflight are retained.

## What changed, and what stayed matched

P3b regressed a scalar utility-minus-recall-penalty target. P3c learns **recall loss alone** to choose partitions. Within those same fitting-data partitions it separately estimates savings. This tests a risk-first formulation without doubling tree count or depth.

| Component | Frozen P3c choice |
| --- | --- |
| Risk target | Positive native-minus-stop recall for valid complete top-10; loss 1.0 for any invalid/incomplete result |
| Savings target | Minimum of activation/reuse fixed-stop savings proxies; fitting-row weighted mean within the same retained/pruned leaf |
| Shallow model | One squared-error regression tree, maximum depth 3, minimum eight rows per leaf |
| Flexible model | 64 Extra Trees, maximum depth 8, minimum eight rows per leaf, all features, no bootstrap, one thread |
| Common group pruning | Replace any split with a child supported by fewer than eight distinct fitting vectors by its fitted parent; recompute both parent means from fitting rows |
| Weighting | Each vector totals one; each of its three query cases contributes equally across its reached grid states |
| Risk caps | 0/.00025/.0005/.001/.0025/.005/.01, in recall-fraction units |
| Benefit floors | 0/.1/.25/.5/1/2/4 ms |
| Stop decision | First reached allowed checkpoint satisfying predicted risk ≤ cap **and** predicted benefit ≥ floor; otherwise paid measured same-profile continue |
| Admission | Unchanged valid complete top-10, native floor .95 per filter, lower 95% recall-delta bounds ≥ −.0025 overall and every filter, positive mean activation and reuse proxies overall, nonzero stop count |
| Selection | Best admitted minimum mean savings proxy; exact ties favor smaller risk cap, then larger benefit floor |
| Fixed diagnostic | Cap .0025 / benefit 0, always evaluated; cannot rescue rejected calibration |

The **same 200 exposed vectors / 600 cases** remain in the exact five P3b outer folds and four inner folds. Each inner fit uses 120 training groups and 40 validation groups; each outer refit uses 160 training groups and evaluates 40 held-out groups. Static23/progress34 qualified fields, original execution identity, eight measured checkpoints 1/2/4/8/16/32/64/128, seed, estimator parameters and group support are unchanged. No ID, evaluator stratum, future state, truth or label is a predictor input.

Only risk determines splits. Benefit means use fitting labels, with no independent savings tree or extra partition. Shallow leaves compile the two gates directly into stop/continue, preserving depth 3 plus the existing grid/availability guard. All shallow exports pass frozen validation and shared-interpreter first-stop checks. The ensemble remains an offline diagnostic.

The fitted risk is a mean, **not a confidence upper bound**. Inner OOF gate screening is empirical development admission, not conformal risk control. First-stop actual loss need not be monotone in a threshold. Pointwise 10,000-resample vector-bootstrap intervals condition on fixed OOF fits; prior design adaptation, training uncertainty and repeated candidate inspection are not removed. These are project-specific procedures, not a formal distribution-free guarantee.

## Primary calibrated outcomes

Every row contains 600 held-out cases, with all three filter cases grouped by vector. Recall differences are in percentage points (pp). Positive proxy savings favor the policy; these costs come from existing fixed-stop acquisitions, **not a new learned-policy serving run**.

| Profile / method | Selected outer cells / 5 | Stops / 600 | Recall difference, pp [95% interval] | Development recall gate | Activation proxy saved, ms | Reuse proxy saved, ms | Joint signal |
| --- | ---: | ---: | --- | --- | ---: | ---: | --- |
| static23 / shallow | 0 | 0 | 0 [0,0] | Pass | −2.250748 | −1.055653 | No |
| static23 / Extra Trees | 3 | 236 | −0.1167 [−0.2500, −0.0167] | **Fail per filter** | −0.603150 | +0.032668 | No |
| progress34 / shallow | 0 | 0 | 0 [0,0] | Pass | −1.870839 | −0.996567 | No |
| progress34 / Extra Trees | 1 | 90 | −0.0167 [−0.0500,0] | Pass | −1.371480 | −0.653759 | No |

Static ensemble activation savings have interval **[−0.875996, −0.316607] ms**; reuse **[−0.151679, +0.218702] ms**. Progress activation and reuse intervals are **[−1.529962, −1.195185]** and **[−0.765560, −0.530708] ms**. Their activation-cost proxies are negative throughout the reported intervals. No actual mean-log-latency qualification was attempted.

The static ensemble passes the overall −.25 pp development reserve at its boundary, but votes108 fails: three loss cases, difference −0.15 pp, interval [−0.35,0] pp. Unfiltered and votes32 each have two loss cases and intervals [−0.25,0] pp. The static policy passes the separately replayed original −.5 pp recall criterion, but that does not replace the frozen development gate or establish latency. Progress has one votes108 loss case and passes development recall in every filter. All outputs are complete and valid.

Continuing through a profile retains its measured overhead. Therefore the negative fallback costs are real historical profile-path costs, not invented zero-cost native routing. Nothing has been installed in serving; the adopted original/native path has not been replaced by an always-continue learned policy.

## Inner qualification did not yield a qualifying outer procedure

| Profile / method | Inner assessments | Recall gate pass | Positive proxies in both regimes | Full admission |
| --- | ---: | ---: | ---: | ---: |
| static23 / shallow | 245 | 245 | 0 | 0 |
| static23 / Extra Trees | 245 | 206 | 43 | 9 |
| progress34 / shallow | 245 | 239 | 0 | 0 |
| progress34 / Extra Trees | 245 | 192 | 37 | 3 |
| Total | 980 | 882 | 80 | 12 |

The twelve admitted configurations occur in only four outer cells; they are overlapping candidates, not twelve independent successes. Sixty-eight positive-proxy candidates fail recall;870 recall-passing candidates have nonpositive proxies. Every inner candidate produces complete top-10 results. No shallow candidate has positive economics.

All four chosen caps are.005. Their inner-to-outer transfers illustrate the remaining instability:

| Profile / outer fold | Chosen benefit floor, ms | Inner activation proxy saved, ms | Outer activation / reuse proxy saved, ms | Outer loss cases /120 |
| --- | ---: | ---: | --- | ---: |
| static23 / 0 | 0 | +0.380603 | +0.738303 / +0.868123 | 1 |
| static23 / 2 | .5 | +0.092042 | −0.569087 / +0.082946 | 0 |
| static23 / 3 | .25 | +0.922692 | +1.326214 / +1.348466 | 6 |
| progress34 / 0 | .1 | +0.289888 | +0.624385 / +0.732711 | 1 |

The remaining cells incur paid continue. Static fold 2 loses activation benefit after refit/held-out evaluation; fold 3 carries most static recall losses. No individual fold or subgroup is selected after the fact as a successful policy. The nested procedure, including rejections and fallback costs, is the reported object.

## Comparison with P3b and fixed diagnostics

Relative to P3b's calibrated ensemble, which always continued, P3c's paired activation/reuse savings-proxy differences are +1.647599/+1.088322 ms for static and +0.499359/+0.342808 ms for progress. All four conditional difference intervals are positive. **This is an improvement over P3b's profile-continue proxy outcome, not a measured serving improvement or a win over original execution.** P3c activation savings versus the original native reference remain negative. The shallow methods are unchanged at continue.

The predeclared fixed diagnostic isolates another tradeoff:

| Profile / fixed diagnostic | Stops / 600 | Recall-loss cases | Overall recall difference, pp [95% interval] | Activation / reuse proxy saved, ms | Development recall gate |
| --- | ---: | ---: | --- | --- | --- |
| P3b static, risk 320 / score 0 | 268 | 11 | −0.2333 [−0.4000, −0.1000] | +0.454613 / +0.924389 | Fail |
| P3c static, cap .0025/benefit 0 | 361 | 1 | −0.0167 [−0.0500,0] | **−0.280050** / +0.135503 | Pass |
| P3b progress, risk 320 / score 0 | 216 | 10 | −0.2500 [−0.4667, −0.0833] | +0.194550 / +0.577725 | Fail |
| P3c progress, cap .0025/benefit 0 | 298 | 1 | −0.0167 [−0.0500,0] | **−0.599384** / −0.137173 | Pass |

P3c's fixed diagnostics pass development recall in all filters and have no unfiltered/votes32 loss; each has the same single votes108 loss at checkpoint 128. Static activation interval [−0.516213, −0.050924] ms and progress[−0.774447, −0.423819] ms remain negative. Risk protection improves observed recall but does not recover activation economics.

Paired P3c-minus-P3b fixed-diagnostic activation savings worsen by 0.734662 ms (static) and 0.793934 ms (progress), while overall recall improves by 0.2167/0.2333 pp. Different formulation and gate definitions prevent interpreting this as an isolated causal effect of model capacity. Neither diagnostic can rescue calibration.

The P3c diagnostic mainly stops late: static checkpoints 32/64/128 contribute 4/94/263 stops, progress 4/58/236. Calibrated static stops 1/31/71/133 cases at 16/32/64/128; all seven losses occur at 128. Six of those seven losses are in the evaluator-only native-work bin 10,000–19,999. Progress's calibrated one loss also occurs at 128. Full filter/stage/difficulty denominators and loss records are in the analysis JSON. No future-work counter or evaluator bin is proposed as a runtime input.

Analytical native remains zero by definition; paid continue and fixed checkpoint 128 controls reproduce P3b exactly. The fixed checkpoint 128 control still fails recall. There are **no new timing A/A controls** because no timings were acquired; old P2b/P2c findings remain unchanged. No control subtraction, P2 savings credit or profile/binary cost transplantation is used.

## Correctness, independent reconstruction and resources

Sixteen synthetic tests pass, using six estimator fits in one test process, within cap 24. Checks cover vector weighting, invalid severity, separate benefits, earliest two-gate stopping, unreachable states, paid continue, float32 split boundaries, held-out-label isolation, risk-partition invariance to benefit changes, group pruning of both parent means, shared-interpreter parity, ensemble/export restrictions, inner splits, conservative selection ties, vector-bootstrap coverage and offline access guards. Ruff lint/format pass. The guarded data-only preflight reproduces all frozen P3b reports exactly before scientific fitting.

| Scientific consumption | Actual / ceiling |
| --- | --- |
| Estimator fits | **100 /100**:80 inner +20 shared selected/diagnostic outer refits |
| Individual trees | 3,250:50 shallow +3,200 ensemble trees |
| Wall time | 102.377 seconds / 3,600 |
| Peak RSS | 1,065,762,816 bytes, 0.993 GiB / 4 GiB |
| Metered run reads | 900,497,365 bytes, 0.839 GiB / 16 GiB |
| CPU threads | 1 |
| New native searches / DB / provider / Torch allocations | 0 / 0 / 0 / 0 |
| Protected query-value / confirmation access | 0 / 0 |
| New dependency installations / production changes | 0 / 0 |

The existing isolated P3b environment was reused read-only with exact pinned versions. No full-data policy refit, globally selected policy, new native qualification or final confirmation occurred. Earlier source/receipt/evidence hashes and the user's unrelated modified proposal document remain unchanged.

The independent verifier imports no model-fitting module. It checks 323 result hashes, all 100 model files and 3,250 trees, disjoint training/validation/outer groups, feature identities and leaf support. It independently reconstructs **248,851 training-leaf risk/benefit values and 494,452 retained nodes**, then reproduces every inner-model prediction, all 980 assessments/selections, all 4,800 outer first-stop cases, original baselines, controls and all paired reports within 1e−12. Its fit/measurement count is zero. Descriptive analysis also performs no fitting or additional selection.

## Closure and next scope

1. **NEXT-RISK-01 closes negative.** P3c has no joint qualifier. Preserve every candidate and fold, no additional cap/floor/model/seed/subgroup tuning, no ensemble compression or serving adoption from this run.
2. **G3 closes negative for the bounded P3 investigation.** P3a coverage remains valid, and P3b/P3c results stand. This does not prove stopping is universally impossible or that the features contain no usable signal. M1/M2/M3 and canonical acceptance remain false. P4–P7's stopping-family path stays deferred until a supported family exists.
3. **Recommend B1a/NEXT-SCOPE-01 before another collection campaign.** Audit only whether the fixed-index backend exposes query-dependent search-effort controls with cheap qualified inputs and an explicit ordinary-native timing baseline. Produce a feasibility decision, exact compatibility/cost unknowns and, if supported, a finite prospective comparison design. Do not presume any knob exists, rebuild an index, run a database/provider job or change production during that audit.
4. **Keep fresh development diversity as a conditional alternative.** Inner/outer instability makes it a legitimate unresolved issue, but this result does not specify the required cohort size or establish that more data will cover profile activation costs. Require a precise question and new data/compute entitlement contract before acquisition. Existing protected/confirmation samples remain bound; no automatic reuse.

B1a is the recommended next task, not an experiment launched by P3c. User involvement begins only if a later justified comparison requires Torch authentication/execution; exact commands must accompany that package. No commands are needed for this completed phase.

## Primary methodology sources

- [scikit-learn 1.7 DecisionTreeRegressor](https://scikit-learn.org/1.7/modules/generated/sklearn.tree.DecisionTreeRegressor.html): squared-error regression, parameters and float32 input handling.
- [scikit-learn 1.7 ExtraTreesRegressor](https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.ExtraTreesRegressor.html): estimator and ensemble mechanics.
- [Nested versus non-nested cross-validation](https://scikit-learn.org/1.7/auto_examples/model_selection/plot_nested_cross_validation_iris.html): separate inner selection from outer evaluation; grouping is additionally enforced here.
- [Angelopoulos et al., Conformal Risk Control, v4](https://arxiv.org/abs/2208.02814v4): formal expected-risk framework with assumptions, not the algorithm/guarantee implemented in this empirical first-stop comparison.

The specific target, leaf benefits, gates and finite budgets are explicit project choices. Sources support mechanics and limits, not empirical success on this workload; results come from the linked locked local artifacts.
