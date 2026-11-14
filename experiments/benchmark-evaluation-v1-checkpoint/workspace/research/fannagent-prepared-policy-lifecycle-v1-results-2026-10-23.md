# P2a prepared-policy lifecycle: measured results and decision

Analyzed October 23, 2026, America/New_York. Campaign: `reviews-prepared-policy-v1-20261023T161756Z.8uq_covr`.

**P2a improves reuse performance, but fails the frozen engineering adoption gate.** Candidate reuse falls from 5.532095 to 5.246006 ms: 0.286089 ms, or 5.171%, faster than original policy execution. The saving is consistent across all three blocks and appears in the eligible strata where repeated preparation was removed. Activation remains essentially unchanged overall, and several activation/control confidence bounds exceed the prospective limits. Retain original execution as the adopted baseline and preserve P2a as a promising experimental component.

No production change, new native experiment, provider request, policy selection or confirmation was performed during this analysis.

## Verification and actual consumption

The [postrun receipt][receipt] records independent local reconstruction with the sealed package. All three allocations completed with successful runtime/host exits, unchanged protected sources, pinned native module/image/profile/index identities, and complete query/arm/regime/repetition/proof coverage. Native/exact/light19 references reproduce the earlier pins. Original and owned execution return identical IDs, distances, recall and actual first-stop outputs/prefixes on the evaluated inventory, including the diagnostic pass.

The [local verifier][verification] passes. The [primary timing report][timing] and [function attribution][profiles] are byte-identical to the remote reports. Complete numerical reports differ at five floating endpoints by at most `5.55e-17`, within the frozen `1e-12` absolute tolerance; discrete results match exactly. Returned code was not executed.

| Item | Actual use |
| --- | ---: |
| Completed serial allocations | 3; jobs 20736459, 20736460, 20736461 |
| Independent development vectors / query-filter cases | 200 / 600, previously exposed |
| Primary retained / discarded warmup pairs | 43,200 / 10,800 |
| Diagnostic vectors / cases | 30 / 90, subset of the development inventory |
| Diagnostic retained / discarded warmup pairs | 6,480 / 1,620 |
| Backend/reference searches | 143,163 |
| Explicit control eviction installations | 12,420, counted separately |
| Provider calls / confirmation queries | 0 / 0 |
| Sum of reported internal elapsed time | 5,188.18 seconds, approximately 86.47 minutes |

Internal elapsed time is not a Slurm billing record. The statistical unit remains the vector, not each filter, repetition, block or profiling call. This campaign consumes the declared one-campaign P2a allowance; it does not authorize automatic repetitions.

## Direct performance against original execution

The table compares original and owned **policy execution**, matched by query, block, regime and repetition. Negative gaps favor owned execution. Each variant also retains its own ordinary-native pairs; those are reported separately and are not subtracted to obtain these contrasts.

| Semantic arm | Regime | Original ms | Owned ms | Owned minus original ms, 95% interval | Arithmetic change |
| --- | --- | ---: | ---: | --- | ---: |
| Candidate | Activation | 9.493442 | 9.503082 | +0.009640 [-0.061361, +0.081151] | 0.102% slower |
| Candidate | Reuse | 5.532095 | 5.246006 | **-0.286089 [-0.330433, -0.242073]** | **5.171% faster** |
| Matched continue | Activation | 11.563403 | 11.592722 | +0.029319 [-0.047469, +0.104582] | 0.254% slower |
| Matched continue | Reuse | 6.854016 | 6.566695 | **-0.287321 [-0.346535, -0.229474]** | **4.192% faster** |
| Routed-native | Activation | 7.394357 | 7.453513 | +0.059156 [-0.011311, +0.130068] | 0.800% slower |
| Routed-native | Reuse | 5.577235 | 5.597992 | +0.020758 [-0.008029, +0.049266] | 0.372% slower |

Candidate reuse meets its dedicated practical-improvement requirements: primary saving lower bound 0.242073 ms exceeds 0.10 ms; the mean log latency-ratio interval `[-0.065700, -0.052834]` lies below `log(0.98)`; outer application saving is 0.286374 ms with interval [0.242188, 0.330940] ms. Outer savings are nearly identical to primary savings, supporting a real full-path reduction rather than movement between timers.

The candidate's three block-level reuse savings are 0.275712, 0.296204 and 0.286350 ms, or 5.115%, 5.146% and 5.254%. Each block's interval favors owned execution. This result is more stable across these blocks than a claim based solely on pooled timing would show.

| Candidate reuse stratum | Saving against original ms | 95% saving interval ms | Arithmetic saving |
| --- | ---: | --- | ---: |
| Unfiltered | 0.428071 | [0.356232, 0.502461] | 7.978% |
| `votes32` | 0.429074 | [0.340969, 0.521879] | 7.627% |
| `votes108`, native bypass | 0.001122 | [-0.042137, 0.045546] | 0.020%; improvement not established |

The saving is concentrated where the prepared-policy handle is actually used. Matched continue also improves on reuse despite unchanged policy decisions. These observations, exact output parity and the function counts below support the intended lifecycle mechanism. They do not establish transfer to untested workloads or better agent reasoning.

## Why the engineering gate fails

The [frozen contract][design] requires the reuse improvement **and** upper confidence bounds no greater than +0.10 ms / `log(1.02)` on primary regressions, plus +0.10 ms on outer regressions, for every arm/regime/filter and overall. Passing candidate reuse alone is insufficient.

The sealed verdict is **`revise_or_retain_original`**. There are 23 endpoint failure flags across 11 arm/regime/stratum cells. These overlapping flags are not 23 independent regressions. There are no identity, output, recall or mechanism failures.

| Representative failing comparison | Point gap ms | 95% gap interval ms | Interpretation |
| --- | ---: | --- | --- |
| Candidate activation, `votes32` | +0.031222 | [-0.093377, +0.152666] | Cannot bound regression below +0.10 ms |
| Candidate activation, `votes108` | +0.071667 | [-0.069834, +0.214527] | Absolute, relative and outer protections fail; worsening is not resolved by this interval |
| Matched-continue activation, overall | +0.029319 | [-0.047469, +0.104582] | Upper absolute/outer bounds narrowly miss |
| Routed-native activation, overall | +0.059156 | [-0.011311, +0.130068] | Overall control nonregression not established |
| Routed-native activation, unfiltered | +0.135101 | [+0.010856, +0.257009] | Measured slowdown in this stratum; magnitude remains uncertain and upper bounds exceed both limits |
| Routed-native reuse, `votes108`, outer time | +0.052766 | [+0.000923, +0.106706] | Small positive outer slowdown; upper bound exceeds +0.10 ms |

Candidate activation **overall** passes the nonregression bounds, with a +0.009640 ms point gap. The per-filter requirements still fail. Most failed activation intervals include zero, so their failure is an inability to establish the required bound, rather than proof of a regression greater than the practical margin. The positive intervals for specific controls also prevent dismissing every failure as harmless noise.

The direct routed-native point gaps vary by block, and its ordinary-native timing varies too. Current evidence does not isolate a source-code cause for that variation. Retain every block/stratum and the original gate; do not subtract control gaps, drop unfavorable observations, enlarge the margin retrospectively or repeat until it passes.

## Comparison with ordinary native and quality

| Candidate execution | Activation vs its paired native | Reuse vs its paired native |
| --- | --- | --- |
| Original | 7.718329 → 9.493442 ms; 22.999% slower | 5.943058 → 5.532095 ms; 6.915% faster |
| Owned | 7.696411 → 9.503082 ms; 23.474% slower | 5.902998 → 5.246006 ms; 11.130% faster |

The owned candidate saves 0.656992 ms against its own paired native on reuse, with a saving interval [0.525458, 0.791129] ms. On activation it adds 1.806671 ms, interval [1.625244, 1.985512] ms. Its original joint activation/reuse latency criterion therefore still fails. The 11.130% figure is not the direct P2a improvement; that is the 5.171% contrast above, because the native baselines differ.

Old and new IDs/distances/stops match exactly. Both candidates retain the earlier -0.016667 percentage-point recall difference against native, interval [-0.050000, 0.000000]; `votes32` carries the loss and still meets the original reserve. Native recall remains 99.35%, 99.15% and 98.60% for unfiltered, `votes32` and `votes108`. There is no added recall loss from P2a on these vectors. This is not independent confirmation, policy selection or canonical serving acceptance.

## What changed, and what remains

All **216 diagnostic profile groups** pass the declared call-count checks: original eligible queries prepare once per query; owned first activation prepares once and owned warmup/reuse prepares zero times. First preparation remains in the original backend timing boundary.

For unfiltered candidate reuse across all three blocks (270 profiled query invocations):

| Function/call-path count per query | Original | Owned |
| --- | ---: | ---: |
| Backend cache `prepare` | 1 | 0 |
| `validate_node` | 2 | 0 |
| Recursive policy-tree `visit` entries | 146 | 0 |
| Recursive `deepcopy` entries | 287 | 0 |
| Policy JSON encoding | 1 | 0 |
| Query normalization through `snapshot().query` | 2 | 2 |

The recursive counts are function entries, not complete-policy validation/copy counts. Profiled cache preparation averages 1.294761 ms inclusive on original reuse; this perturbed diagnostic duration must not be interpreted as an unprofiled saving. Actual unprofiled eligible-stratum savings are approximately 0.428–0.429 ms.

Session admission remains expensive: owned candidate preparation averages **1.539285 ms** unprofiled, versus original 1.540914 ms. The unfiltered diagnostic constructors still perform **four runtime-profile fingerprints and eight JSON encodings** in both variants. Profiled fingerprint time is approximately 1.071 ms inclusive within approximately 2.9 ms profiled constructor time. These nested durations overlap and do not predict removable unprofiled cost.

Owned routing also remains 0.185846 ms on activation and 0.136869 ms on reuse. Routed-native still pays 1.286570 ms preparation plus approximately 0.117 ms reuse routing. Query normalization and the opaque server/transport wait boundary remain, but neither was changed by P2a.

## Roadmap decision and next step

1. **Close NEXT-EXEC-01 as verified, with mixed evidence and a failed engineering gate.** Record the reuse benefit and preserve all failures. G2 is `revise`; M1, M2, M3 and serving acceptance remain unestablished. Original execution stays the adopted baseline. P2a remains a frozen experimental reference, not a production cutover.
2. **Scope one admission/profile-identity revision before another measurement campaign.** The first proposed mechanism is reuse of a semantic runtime-profile identity derived from a privately owned immutable profile, while preserving original policy admission/type/depth/feature checks and required cold charges. P2a deliberately left this repeated constructor work unchanged; it is a more direct next target for the still-large activation deficit than broad policy search.
3. **Resolve comparison precision prospectively.** Use the exposed raw timing distributions for per-filter/order/precision planning. Include an identical-path A/A control and balanced old/new measurements in the next declared design, so activation/control variation can be assessed against the +0.10 ms limit. An A/A control diagnoses the measurement path; it does not exempt a failed bound.
4. **Preserve attribution of the new change.** Keep original and frozen P2a references, change only admission/profile identity, freeze practical criteria, sample/allocation ceilings and a finite stop rule before dispatch, and retain full primary/outer/cold costs. Do not combine a normalization rewrite or database transport change with it. No new implementation, resource ceiling or run is assigned by this analysis.
5. **After the new G2 review, proceed or redirect explicitly.** Query normalization stays a separate conditional follow-up. P3 policy-information diagnosis follows a chosen execution identity/economics decision; P4–P7 method comparisons remain downstream. Protected confirmation entitlements and the closed selective episode remain unchanged.

## Artifacts

| Artifact | SHA-256 |
| --- | --- |
| Returned archive | `94a38fb68e593948daceba890182d720bad64c3485f13a357d7adab32fe03319` |
| Sealed P2a manifest | `c4c00e12a08963751ab20aed3f195ed3af2a515be40c0bdd619ce57209bca60c` |
| Postrun receipt | `5b2449a02ec55ad4c4670e210dbff9ab51ec9b50a9b7c2312306c206826bfdb5` |

The [complete locally reconstructed data][performance] include every filter/block interval, all function profiles, raw hashes and all gate failure strings. The [roadmap][roadmap] tracks the resulting branch. The [implementation receipt][implementation] remains the preserved pre-dispatch snapshot.

[receipt]: ../agent/docs/verification/prepared-policy-lifecycle-v1-postrun.json
[timing]: ../trials/torch-reviews-prepared-policy-lifecycle-v1/analysis-local/reviews-prepared-policy-v1-20261023T161756Z.8uq_covr/report.txt
[profiles]: ../trials/torch-reviews-prepared-policy-lifecycle-v1/analysis-local/reviews-prepared-policy-v1-20261023T161756Z.8uq_covr/attribution.md
[performance]: ../trials/torch-reviews-prepared-policy-lifecycle-v1/analysis-local/reviews-prepared-policy-v1-20261023T161756Z.8uq_covr/performance.json
[verification]: ../trials/torch-reviews-prepared-policy-lifecycle-v1/analysis-local/reviews-prepared-policy-v1-20261023T161756Z.8uq_covr/verification.json
[design]: ../agent/experiments/prepared-policy-lifecycle-v1/DESIGN.md
[implementation]: ../agent/docs/verification/prepared-policy-lifecycle-v1-implementation.json
[roadmap]: fannagent-performance-research-roadmap-2026-10-22.md
