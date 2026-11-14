# P2b admission profile identity: measured results and decision

Analyzed October 23, 2026. Campaign: `reviews-admission-profile-v1-20261023T193304Z.a2mfz4a0`.

**The completed data verify successfully and show modest activation savings, but P2b does not pass qualification.** Candidate activation is 2.109% faster than concurrent original execution and 2.102% faster than concurrent P2a. Reuse is 4.054% faster than original, with no established additional gain over P2a. The frozen verdict is **`measurement_inconclusive`**: six activation/filter A/A cells fail absolute equivalence, and the required 2% incremental activation saving is not established by the log-ratio confidence bound. Original execution remains the adopted baseline. P2a/P2b remain experimental references.

No new experiment, provider call, policy selection, confirmation query, production change or sealed-source modification was performed during this analysis. The offline order audit uses the existing completed raw data only.

## Independent verification and actual consumption

The [postrun receipt][receipt] records checksum verification, all 81 regular archive members checked against extraction, unchanged sealed source/package identities, and a fresh reconstruction with the sealed local analysis code. All 56 locked raw-file hashes pass, with complete coverage, unchanged protected inputs and pinned module/image/profile/physical-index identities. Original/P2a/P2b outputs, IDs, distances, recall, route/actual stops, feature prefixes and acknowledgements match on the declared inventory. All 576 diagnostic profile groups pass the mechanism checks.

The [fresh verifier][verification] passes. Its complete numerical result matches the earlier download-helper reconstruction exactly. Compared with the remote result, twelve floating endpoints differ by at most `5.55e-17`, below the frozen `1e-12` tolerance; all discrete results match. The [timing report][timing] and [function attribution][profiles] reproduce remotely generated reports byte-for-byte. Returned code was not executed.

| Item | Actual use |
| --- | ---: |
| Completed serial allocations | 4; jobs 20753185, 20753186, 20753187, 20753188 |
| Independent exposed development vectors / query-filter cases | 200 / 600 |
| Primary retained / discarded warmup pairs | 115,200 / 28,800 |
| Diagnostic vectors / cases | 30 / 90, fixed subset of the development inventory |
| Diagnostic retained / discarded warmup pairs | 17,280 / 4,320 |
| Backend/reference searches | 370,884 |
| Separately counted eviction installations | 33,120 |
| Provider calls / confirmation queries | 0 / 0 |
| Sum of reported internal elapsed time | 10,076.31 seconds, approximately 167.94 minutes |

Internal elapsed time is not a billing record or a query-speed metric. All four blocks completed within their deadlines with successful host/runtime exits and unchanged protected inputs. The single P2b campaign allowance is consumed; no automatic repetition follows an inconclusive gate. Repeated blocks, filters and A/A labels remain clustered within 200 independent vectors.

## Performance against concurrent original and P2a execution

These are the three versions of the unchanged candidate measured in this campaign. P2b pools its two fresh identical-path labels as repeated observations within each vector. Compare these concurrent references; older P2a campaign times were measured under different timing conditions and must not be used as the direct baseline for a P2b speed claim.

| Candidate execution | Activation ms | Reuse ms |
| --- | ---: | ---: |
| Original | 9.593075 | 6.172896 |
| Frozen P2a | 9.592390 | 5.930276 |
| P2b, pooled A/B | **9.390738** | **5.922666** |

Negative gaps below favor P2b. Intervals use the frozen 10,000-resample vector-group bootstrap, retaining all filters, blocks and repetitions.

| Direct comparison | Regime | P2b minus reference ms | 95% gap interval ms | Arithmetic saving |
| --- | --- | ---: | --- | ---: |
| P2b versus original | Activation | -0.202338 | [-0.236616, -0.168284] | **2.109%** |
| P2b versus P2a | Activation | -0.201653 | [-0.237160, -0.166512] | **2.102%** |
| P2b versus original | Reuse | -0.250231 | [-0.259452, -0.241027] | **4.054%** |
| P2b versus P2a | Reuse | -0.007611 | [-0.017850, +0.002364] | 0.128%; added benefit not established |

The candidate's incremental activation savings versus P2a are 0.296141, 0.194428, 0.150803 and 0.165239 ms across the four blocks. Its combined reuse savings versus original are 0.245559, 0.259480, 0.240036 and 0.255847 ms. Every required block point direction is favorable. Primary and outer activation savings versus P2a agree closely: 0.201653 versus 0.201569 ms, so this is not merely movement between the declared timers.

The broader semantic controls show the same activation direction: matched-continue saves 0.201744 ms versus P2a (interval [0.161058, 0.243641]), and routed-native saves 0.169173 ms ([0.141126, 0.198097]). Neither shows an established additional reuse benefit versus P2a. This supports an admission mechanism shared across policies, rather than improved stopping decisions.

For candidate reuse versus original, unfiltered and `votes32` save 0.378205 and 0.376337 ms. The native-bypass `votes108` gap is +0.003850 ms, interval [-0.013929, +0.021293]; there is no established bypass reuse improvement. In this campaign the frozen P2a reference itself saves 3.930% candidate reuse time versus original, reproducing its mechanism without reopening its earlier failed engineering gate.

## Why the engineering qualification does not pass

All **144 declared nonregression endpoints** pass: both P2b-versus-P2a and P2b-versus-original, three semantic arms, both regimes, every filter and overall, with absolute primary, relative primary and outer bounds. Original development quality protections and the dedicated combined reuse benefit also pass. There is no correctness, identity, quality or mechanism failure.

The incremental activation target passes its absolute and outer requirements: both saving lower bounds exceed 0.10 ms. It nevertheless misses the separate relative requirement. Candidate activation versus P2a has mean log latency-ratio interval `[-0.026659, -0.019623]`. The upper endpoint must be no greater than `log(0.98) = -0.020203`; its implied lower saving bound is **1.943%**, below 2%. The 2.102% figure is the arithmetic point saving; it is not a confidence guarantee. Preserve this narrowly failed criterion rather than rounding it into a pass.

Even if this relative criterion had passed, A/A equivalence would still be mandatory. The frozen analysis therefore reports `measurement_inconclusive`, with the independent engineering shortfall retained in its failure list. Passing A/A later would not retroactively repair this result.

## A/A controls: overall and reuse pass; activation/filter precision remains insufficient

The two P2b labels use the same factory, query code and policies with independently constructed sessions. Equivalence requires entire 95% intervals within ±0.10 ms for primary and outer gaps and ±log(1.02) for the mean log ratio. An interval that merely includes zero does not establish equivalence.

| A/A endpoint | Passing cells | Required cells |
| --- | ---: | ---: |
| Primary absolute interval | 19 | 24 |
| Outer absolute interval | 18 | 24 |
| Relative log-ratio interval | 24 | 24 |

All overall comparisons and all reuse comparisons pass. Eleven absolute endpoint flags arise from **six activation/filter cells**, not eleven independent code regressions:

| Semantic arm / filter | Primary B-minus-A 95% interval ms | Outer 95% interval ms | Failing bounds |
| --- | --- | --- | --- |
| Candidate / unfiltered | [-0.126423, +0.011039] | [-0.126419, +0.011172] | Primary, outer |
| Candidate / `votes32` | [-0.102816, +0.037634] | [-0.103007, +0.037796] | Primary, outer |
| Matched-continue / unfiltered | [-0.064115, +0.115679] | [-0.064158, +0.115788] | Primary, outer |
| Matched-continue / `votes32` | [-0.172466, +0.001670] | [-0.172748, +0.001577] | Primary, outer |
| Routed-native / `votes32` | [-0.099361, +0.026442] | [-0.100055, +0.026815] | Outer only |
| Routed-native / `votes108` | [-0.030664, +0.101745] | [-0.029984, +0.103796] | Primary, outer |

Every failed absolute interval includes zero; these failures do not establish that identical code differs by more than 0.10 ms. They establish that this campaign does not meet the required absolute equivalence precision in those strata. One candidate/unfiltered activation log-ratio interval favors B while remaining inside the relative equivalence band; do not characterize every A/A directional effect as exactly zero. Different absolute and log-ratio estimands need not have identical significance results.

The pooled candidate A/A activation point gap is -0.024183 ms, interval [-0.060290, +0.011688]. Across blocks it is -0.085124, -0.058079, -0.024761 and +0.071233 ms. Pooling is required by the contract but does not remove the per-filter obligations.

### Existing-data order audit

The [descriptive raw-data audit][order] retains every activation A/A pair and uses the already recorded schedule. For each semantic arm/filter, 400 pairs place B later and 400 place B earlier. Each vector contributes four blocks; the counts are repeated observations, not 800 independent vectors. Selected conditional means:

| A/A stratum | B-minus-A when B is later ms | B-minus-A when B is earlier ms |
| --- | ---: | ---: |
| Candidate / unfiltered | -0.155516 | +0.042349 |
| Candidate / `votes108` | -0.287898 | +0.318301 |
| Routed-native / unfiltered | -0.307176 | +0.340076 |
| Routed-native / `votes32` | -0.418330 | +0.343608 |

Later labels are faster in all nine arm/filter conditional comparisons; ordinary-native pair means show a similar direction. The audit also finds broad single-pair variation: candidate/unfiltered A/A differences range from -7.323768 to +5.302488 ms, while the median is +0.002454 ms. Keep all those observations; no trimmed estimate replaces the frozen primary result.

This is an observational association, not a causal estimate of caching, drift, transport or a particular code operation. The Williams schedule passed position and predecessor checks. Balance limits systematic label-position imbalance across the four blocks; it does not make within-query conditioning effects disappear or guarantee a 0.10 ms interval. These findings justify focused measurement calibration before another optimization, not an A/A subtraction, dropped blocks, post-hoc margin relaxation or automatic rerun.

## Mechanism and residual cost

The expected call-count mechanism passes in all 576 groups. Original/P2a constructors still compute four profile fingerprints; P2b computes one and captures one private snapshot. Lazy backend preparation remains charged inside first activation and makes zero calls on owned reuse. Unchanged query normalization remains outside this optimization.

| Unprofiled constructor preparation, candidate | Mean ms |
| --- | ---: |
| Original | 1.472158 |
| P2a | 1.477747 |
| P2b A | 1.279903 |
| P2b B | 1.281999 |
| P2b pooled | **1.280951** |

The candidate's constructor saving versus P2a is 0.196796 ms, or 13.317% of constructor time, accounting for most of its approximately 0.202 ms end-to-end activation reduction. Matched-continue and routed-native constructor costs fall by 13.412% and 14.019%. Approximately 1.28 ms candidate preparation remains.

The private snapshot introduces a real work tradeoff. On unfiltered candidate constructors, recursive `deepcopy` entries rise from 299 to 1,901, including 56 Pydantic `__deepcopy__` entries per P2b constructor. Fingerprints fall from four to one; JSON encodings fall from eight to five. Recursive entries are not complete-object copy counts. Profiled constructor wall time rises from approximately 2.827 ms for P2a to approximately 4.747 ms for P2b, despite the unprofiled improvement. This illustrates profiler perturbation of a call-heavy path; diagnostic times cannot be substituted for the primary timing result or subtracted to predict a future gain.

A future owned validation context could investigate avoiding repeated full-profile copying under a precisely declared binding lifetime, but its invalidation, immutable ownership and first-use costs would need a new contract. That is not the immediate next implementation; measurement calibration comes first.

## Ordinary native, quality and limits

Each P2b label retains its own ordinary-native pairs. Candidate activation is still **18.597% / 18.806% slower** than native for A/B, adding approximately 1.474 / 1.485 ms. Reuse is **10.783% / 10.741% faster**, saving approximately 0.716 / 0.713 ms. Its joint activation/reuse latency qualifier therefore still fails. Those reuse percentages are versus ordinary native; the direct gain over original policy execution is 4.054%.

All four execution variants return exactly matching results/stops on this inventory. The candidate retains its earlier -0.016667 percentage-point recall difference versus native, interval [-0.050000, 0.000000]; `votes32` carries the earlier loss and remains within the frozen development reserve. Native recall remains 99.35%, 99.15% and 98.60% across the three filters. There is no added P2b recall loss on these exposed vectors. This is not independent confirmation, policy selection, improved agent reasoning or canonical serving acceptance.

## Roadmap decision and next step

1. **Close NEXT-ADMIT-01 as independently verified, with `measurement_inconclusive`.** Record the modest activation signal, retained reuse benefit, complete nonregression success, missed 2% activation bound and all A/A failures. Keep original execution as the adopted baseline; preserve frozen P2a/P2b components without production cutover. G2 remains `revise`; M1/M2/M3 remain unestablished.
2. **Complete the offline measurement diagnosis now.** The descriptive order audit is saved with the raw file hashes. Its results support testing activation conditioning/order precision, without changing the existing estimator or verdict.
3. **Scope NEXT-CAL-01 before further optimization.** Propose at most one separately versioned calibration comparison with identical-path original/native and P2b controls, adjacent counterbalanced A/B and B/A order, explicit shared query/index conditioning and policy/session activation semantics. Keep actual admission, lazy preparation and installation charged; warm conditioning must not hide the operation being measured. Record ordering and relevant environment/block metadata. Freeze grouped analysis, unchanged practical margins, finite resources and a stop rule before implementation or dispatch. No new budget or run is assigned by this analysis.
4. **Make the next branch finite.** If one justified calibration contract can establish adequate equivalence, review execution economics using the qualified design. If it is unjustified or remains inconclusive, explicitly retain original execution and redirect to bounded P3 information diagnosis rather than repeating indefinitely. No P2b rerun or threshold relaxation.
5. **Defer additional mechanisms.** Profile-snapshot lifetime/copying, normalization and transport remain separate conditional proposals. Broader policy/agent-method changes, independent data entitlements and the closed selective-agent episode retain their earlier gates.

## Artifacts

| Artifact | SHA-256 |
| --- | --- |
| Returned archive | `4c1b7cef11d40f64a65b2488a1afc0df884be12d10e96c89d50be50083d09a7e` |
| Sealed P2b manifest | `7c82194d375a77f29356e3620d2f011b2b0e452b9954defcb75aaec90f29350d` |
| Postrun receipt | `ba3f5116ab2583d61fac024dbb899112803fcc7fad18687a9ed64bc5f374a88f` |
| Descriptive order audit | `6a2f12fd54d48d0a15e79ca0203c23c1f39836716d63f46fd614254240b7d929` |

The [complete performance data][performance] retain every filter/block interval, individual-label/native report, profile group and gate failure. The [roadmap][roadmap] records the revised critical path. The [implementation receipt][implementation] and [user-pasted status receipt][status] remain preserved historical snapshots.

[receipt]: ../agent/docs/verification/admission-profile-identity-v1-postrun.json
[verification]: ../trials/torch-reviews-admission-profile-identity-v1/analysis-review/reviews-admission-profile-v1-20261023T193304Z.a2mfz4a0/verification.json
[timing]: ../trials/torch-reviews-admission-profile-identity-v1/analysis-review/reviews-admission-profile-v1-20261023T193304Z.a2mfz4a0/report.txt
[profiles]: ../trials/torch-reviews-admission-profile-identity-v1/analysis-review/reviews-admission-profile-v1-20261023T193304Z.a2mfz4a0/attribution.md
[performance]: ../trials/torch-reviews-admission-profile-identity-v1/analysis-review/reviews-admission-profile-v1-20261023T193304Z.a2mfz4a0/performance.json
[order]: fannagent-admission-profile-identity-v1-order-audit-2026-10-23.json
[roadmap]: fannagent-performance-research-roadmap-2026-10-22.md
[implementation]: ../agent/docs/verification/admission-profile-identity-v1-implementation.json
[status]: ../agent/docs/verification/admission-profile-identity-v1-torch-status.json
