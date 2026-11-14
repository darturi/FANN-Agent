# FANNAgent performance research roadmap

Created: October 22, 2026, America/New_York.  
Last substantive update: November 4, 2026.  
Version: 1.99.  
Program status: Actual four-file dependency capture verifies:73,986bytes,18ELF objects and34consistent components. Both clients require libslurmfull.so in the recorded RPATH directory omitted by the collector. A frozen one-root metadata correction passes436local checks; all other code/guards/tests/limits remain unchanged. Runtime/native dependency closure is still unqualified; no Torch/job/search occurs here. [E529]–[E534]
Scope: v1.99 reviews actual metadata, reconciles lexical aliases and prepares a separate strict candidate-root capture correction only. Preserve128+128main/276+276A3 tests, all85functional/15kernel IDs, strict one-pass verification,120shelper and every original limit/evidence. All spent grants remain closed; no native replay or allocation is released. [E529]–[E534]

## 1. Objective and interpretation

Improve FANNAgent's ability to discover inexpensive filtered ANN policies while preserving the declared recall objective and independent acceptance process. Retain the preparation/routing cost diagnosis and original execution. The finite stopping investigation and B1b's current320/640 context family have no qualifying result. B1b2 fixed480 now also closes negatively on relative quality. B2a now establishes scoped source feasibility for one fixed exact-top10 versus native640 comparison on unchanged data/graph/module. B2b original native preflight has now failed at the initial catalog guard before any search. Both original and corrected failed raw are verified. Corrected exact10 passes prefix quality but is descriptively56.11x slower in its complete first block; the finite campaign closes incomplete with no full gate verdict. Do not extend it. Completed B2c selected one >=108 partial-HNSW design using the unchanged module, strict experimental validation and two private copies; native feasibility was then unqualified, and public partial-target support remains separate. B2d complete native evidence now verifies scoped partial-index feasibility/quality, but all A/A intervals fail; performance is measurement_inconclusive. Completed B2e finds equal observed work identities, progressive warm-state timing transients and unresolved fixed connection/backend/physical-state aliases. B2f has now spent three attempts, all failing before searches. The third failure exposes a mismatched eligibility record schema and another startup-control-flow coverage gap. Verification and isolated correction/local entry-point tests are complete; release is held pending memory/accounting feasibility and a documented release review. No further calibration job is released. [E219][E220][E221] Retain original execution pending actual evidence; wider features, policy search and agent-framework changes remain conditional.

Track three separate milestones:

| Milestone | Required evidence | What it does not establish |
| --- | --- | --- |
| M1: execution economics resolved | Qualified measured execution with explicit costs and a recorded improve/retain/redirect decision against the predeclared budget | A practically viable learned policy; retaining the original path is a branch decision, not a performance success |
| M2: useful policy | A frozen policy passes its declared independent quality and measured-latency evaluation | Superiority of the agent's research method or canonical serving acceptance unless that separate process also passes |
| M3: improved research method | Repeated controlled episodes demonstrate better qualifying-policy discovery or lower resource consumption under a prespecified analysis | Transfer to unevaluated workloads |

This roadmap proposes future work. An unchecked task is not implemented or authorized for execution merely because it appears here. Existing completed experiments remain governed by their original contracts. Owners, new spending ceilings, compute allocations, and evaluation entitlements must be resolved before the corresponding future campaign starts.

Research recommendations below are project-specific hypotheses informed by the sources in Section 12. Published performance gains are not estimates for this workload.

## 2. Evidence baseline and the latest change in diagnosis

### 2.1 Selective-agent baseline

The `selective-agent-v1` pilot is complete, locally reproduced according to its verification receipt, and closed after the agent's single feedback response. It produced no revision or selected candidate. The receipt was recorded at `2026-10-23T03:33:59Z`, which is October 22 at 11:33:59 p.m. in America/New_York. [E1][E2][E3]

| Item | Recorded result |
| --- | --- |
| Episode | `20261022T192817Z-66ed81d6` |
| Independent development vectors / query-filter cases | 200 / 600 |
| Retained timing pairs / backend-reference searches | 57,600 / 170,163 |
| Pilot allocations | 3 |
| Provider attempts / recorded total provider charge | 8 / $0.238334 |
| Final agent action | Explicit abstention after measured feedback |
| Revision / confirmation allocations | 0 / 0 |
| Selective study's confirmation entitlement | 60 vectors unconsumed at this snapshot |
| Other reserved vectors | 37; not automatically available to a new study |
| Original generation A/B | Inconclusive, zero complete pairs |
| Canonical serving acceptance | False |

Snapshot identities are recorded below so later edits to a linked receipt can be distinguished from the evidence used for this revision. File digests were read during document creation; the campaign archive digest is copied from the verification receipt, not a new archive verification.

| Artifact | SHA-256 |
| --- | --- |
| E1 postrun receipt file | `f5ee1f8a9a5090b687d619487c9a02883441c8e1e993673b030b2ff230e04d91` |
| E2 pilot report file | `d725fbc4816efd5117242d59dcb9ced3cee1ab1e8a56a0f630a7a66d1d288a80` |
| Campaign archive, as recorded in E1 | `c3948d569d62ba2973016f5825e847530c93ceb864b4c6eb15de72ab6b7cefe6` |

The following percentages compare each arm with its own paired native baseline. They are arithmetic mean latency summaries; the recorded qualification decision uses the prespecified confidence bound on mean log latency ratio.

| Arm | Activation latency | Reuse latency | Quality and interpretation |
| --- | --- | --- | --- |
| `cons-bypass108`, credited earlier seed with `votes108` bypass | 24.354% slower; 7.515090 to 9.345339 ms | 7.193% faster; 6.182963 to 5.738252 ms | Development recall checks pass overall and per filter; combined gate fails on activation |
| Fitter restricted to unfiltered queries | 27.620% slower | 0.425% slower | No measured recall loss; no overall reuse qualification |
| Fitter on unfiltered + `votes32` | 29.483% slower | 0.120% faster | No measured recall loss; reuse improvement not established |
| Routed-native control | 22.724% slower | 2.187% slower | No recall loss; integration cost exists even when every query chooses native execution |
| Sparse hindsight oracle | 27.290% faster | 58.985% faster | No measured recall loss; retrospective, nondeployable diagnostic |

For `cons-bypass108`, overall recall difference is -0.016667 percentage points, with a reported 95% interval of [-0.050000, 0.000000] percentage points. The reuse mean log latency-ratio interval is [-0.132163, -0.081617]; the activation interval is [0.209466, 0.243412]. The worst affected filter is `votes32`, whose recall interval still meets the development reserve. These are development findings, not independent confirmation. [E1]

The routed-native control's activation components are especially informative: ANN execution averages 6.152214 ms versus a 6.153126 ms native baseline, but 1.247046 ms preparation and 0.152074 ms routing raise reported total latency to 7.551334 ms. The best candidate records 1.540021 ms preparation and 0.188344 ms routing during activation. These measured categories identify where to investigate; they do not prove which individual operation should be moved or cached. [E1]

### 2.2 Execution cost attribution baseline

`NEXT-COST-01` completed all three serial Torch allocations. Local analysis used the sealed package and independently reconstructed the full result: discrete values match exactly; one floating confidence endpoint differs by `1.39e-17`, below the declared `1e-12` tolerance. The compact timing and attribution reports are byte-identical to the remote reports. G1 passes as an attribution gate; no optimized runtime or independently qualifying policy has been established. [E11][E12][E13][E14][E15][E16]

| Item | Verified result |
| --- | --- |
| Campaign | `reviews-execution-cost-v1-20261023T044408Z.a08qpwdi` |
| Independent development vectors / query-filter cases | 200 / 600; same previously exposed inventory |
| Diagnostic vectors / cases | 60 / 180, subset of the same development vectors |
| Primary retained / discarded warmup pairs | 21,600 / 5,400 |
| Diagnostic retained / discarded warmup pairs | 6,480 / 1,620 |
| Completed allocations / backend-reference searches | 3 / 83,763 |
| Explicit control eviction installations | 7,020, counted separately from searches |
| Provider calls / confirmation queries | 0 / 0 |
| Candidate selection / canonical serving acceptance | None / false |

The following arithmetic means are from the unprofiled primary pass. Each arm uses its own paired native baseline; control gaps cannot be subtracted to claim savings. [E13][E15]

| Arm | Activation: native → arm ms | Activation change | Reuse: native → arm ms | Reuse change |
| --- | --- | ---: | --- | ---: |
| Frozen `cons-bypass108` candidate | 7.841534 → 9.629314 | 22.799% slower | 6.134988 → 5.745601 | 6.347% faster |
| Matched continue | 7.842175 → 11.606193 | 47.997% slower | 6.007781 → 7.094731 | 18.092% slower |
| Routed-native | 6.565397 → 8.068760 | 22.898% slower | 5.803784 → 5.925975 | 2.105% slower |

Candidate activation adds 1.787779 ms, 95% interval [1.610250, 1.965372] ms; reuse saves 0.389387 ms, interval [0.252834, 0.527575] ms. The corresponding mean log latency-ratio intervals are [0.188264, 0.222782] and [-0.120062, -0.070658]. Every block shows the same direction, although reuse saving varies from 3.937% to 10.284%. Outer application timing preserves the activation-loss/reuse-benefit pattern. These are development measurements; the new pooled percentage is not a controlled comparison with the earlier campaign's percentage. [E11][E15]

Candidate recall again differs by -0.016667 percentage points overall, interval [-0.050000, 0.000000]; the loss is confined to `votes32`, whose interval is [-0.150000, 0.000000] percentage points. All output/recall checks pass, but the joint activation-and-reuse latency requirement remains unmet. Native bypass on `votes108` itself adds 0.128467 ms during candidate reuse. [E11][E15]

The attribution narrows the next engineering mechanism:

| Finding | Evidence | Implication / limit |
| --- | --- | --- |
| Session preparation repeatedly builds policy/profile identities | Candidate unprofiled preparation 1.558956 ms; diagnostic preparation records four runtime-profile fingerprints, eight JSON encodings, ownership copying and tree/reference checks per session | Reuse identity only for a privately owned immutable profile/artifact; preserve admission checks |
| A prepared-cache hit retains policy-processing work | Eligible candidate reuse still calls `prepare`, validates the tree twice, copies the input and serializes it before lookup; source order matches function counts | First P2 target: owned prepared-policy state across queries, with bounded invalidation; compilation caching alone has not removed this work |
| Routed-native pays validation and query-boundary work | Unprofiled preparation 1.293546 ms, routing 0.153933 ms on activation and 0.115871 ms on reuse; diagnostic query normalization is much larger than the tiny predicate `route` function | Consider a separate single-normalization revision if bypass cost remains over budget |
| The reported `ANN ms` category includes more than engine search | Backend timer includes policy preparation, SQL construction, transport and decoding | Attribute changes to the correct timer; zero outer preparation on reuse does not imply zero backend preparation |
| Database wait and shared vector formatting remain boundaries | Python profiles show large `psycopg.wait` frames; statement construction formats 768 values and is shared with ordinary native execution | No server/transport root cause or differential vector-formatting penalty established; retain a focused conditional diagnostic |

Function durations are diagnostic and perturbed. Counts identify repeated operations; source inspection explains their order. Inclusive time overlaps descendants and cannot be summed with them or subtracted from primary latency to predict a deployed gain. The [detailed results and lifetime/invalidation map][E12] records the evidence, limitations and bounded P2 sequence.

| New artifact | SHA-256 |
| --- | --- |
| Returned archive | `0c4dc6e995891a488de502cd11ffaed549a65a233064decf4a692fe638704d3e` |
| Sealed package manifest | `4c2f475664784b1851b1274a5c696bccbc55ee41c659a469c3643eb0ca0109c0` |
| E11 postrun receipt | `16647a2486df6f191a764f4600e17ee2437f01352edc76eb3646490ca3b90378` |

### 2.3 Completed P2a original/owned comparison

`NEXT-EXEC-01`, campaign `reviews-prepared-policy-v1-20261023T161756Z.8uq_covr`, completed all three serial allocations and exactly 143,163 searches. Local analysis with the sealed package passes all identity, coverage, reference, old/new output/first-stop and preparation-call checks. Compact timing/attribution reports reproduce byte-for-byte; five floating endpoints differ by at most `5.55e-17`, within the frozen `1e-12` tolerance. [E21][E22][E23][E24][E25][E26]

| Actual consumption | Result |
| --- | --- |
| Independent development vectors / cases | 200 / 600, already exposed |
| Primary retained / discarded warmup pairs | 43,200 / 10,800 |
| Diagnostic vectors / cases; retained / warmup pairs | 30 / 90; 6,480 / 1,620 |
| Completed jobs | 20736459, 20736460, 20736461 |
| Searches / separately counted eviction installs | 143,163 / 12,420 |
| Provider calls / confirmation queries | 0 / 0 |

The following contrasts directly match **owned policy execution versus original policy execution** on query/block/regime/repetition. They do not subtract independently summarized native gaps. Negative gaps favor owned execution. [E23][E24]

| Arm | Regime | Original → owned ms | Owned minus original ms, 95% interval | Arithmetic change |
| --- | --- | --- | --- | ---: |
| Candidate | Activation | 9.493442 → 9.503082 | +0.009640 [-0.061361, +0.081151] | 0.102% slower |
| Candidate | Reuse | 5.532095 → 5.246006 | **-0.286089 [-0.330433, -0.242073]** | **5.171% faster** |
| Matched continue | Activation | 11.563403 → 11.592722 | +0.029319 [-0.047469, +0.104582] | 0.254% slower |
| Matched continue | Reuse | 6.854016 → 6.566695 | **-0.287321 [-0.346535, -0.229474]** | **4.192% faster** |
| Routed-native | Activation | 7.394357 → 7.453513 | +0.059156 [-0.011311, +0.130068] | 0.800% slower |
| Routed-native | Reuse | 5.577235 → 5.597992 | +0.020758 [-0.008029, +0.049266] | 0.372% slower |

Candidate reuse meets its dedicated improvement thresholds: the saving lower bound is 0.242073 ms, its log-ratio interval [-0.065700, -0.052834] is below `log(0.98)`, outer saving is 0.286374 ms, and all blocks save time (5.115%, 5.146%, 5.254%). Eligible unfiltered/`votes32` cases save 0.428071/0.429074 ms; native-bypass `votes108` shows no established gain. All 216 diagnostic groups confirm owned reuse calls cache `prepare` zero times, while original eligible queries still prepare once. [E21][E22]

**The complete engineering gate nevertheless fails: `revise_or_retain_original`.** Twenty-three endpoint flags across eleven comparison cells fail activation/control protections. For example, candidate activation `votes108` has a direct gap interval [-0.069834, +0.214527] ms; matched-continue activation overall reaches +0.104582 ms; routed-native activation overall reaches +0.130068 ms; routed-native reuse `votes108` outer time reaches +0.106706 ms. These upper bounds exceed +0.10 ms even where point changes are small. Candidate activation overall passes its nonregression bounds, but per-filter requirements remain binding.

Most failed activation intervals include zero, so they do not prove a regression greater than the practical margin. Specific controls do show a positive slowdown: routed-native unfiltered activation adds 0.135101 ms, interval [+0.010856, +0.257009]. Retain those observations and the original limits; do not label every failure noise or retrospectively loosen the gate. [E21][E22][E24]

Against each variant's **own ordinary-native baseline**, original candidate reuse saves 6.915% and owned reuse 11.130%; the direct P2a gain remains 5.171%. Owned activation is still 23.474% slower than ordinary native. Recall/output/stopping results match original exactly; the candidate retains its prior -0.016667 percentage-point recall difference versus native, with passing development bounds. No candidate is independently confirmed or selected. [E21][E24]

The main residual is now concrete: owned session admission still costs 1.539285 ms and still computes four profile fingerprints/eight JSON encodings per diagnostic constructor. P2a deliberately did not address those operations. The resulting mechanism is owned semantic profile-identity reuse during admission; its P2b implementation and prospective A/A/precision design are recorded below. Query normalization remains a later separate option. [E22][E26]

| Verified artifact | SHA-256 |
| --- | --- |
| Returned P2a archive | `94a38fb68e593948daceba890182d720bad64c3485f13a357d7adab32fe03319` |
| P2a postrun receipt | `5b2449a02ec55ad4c4670e210dbff9ab51ec9b50a9b7c2312306c206826bfdb5` |

### 2.4 Completed P2b admission and A/A comparison

`NEXT-ADMIT-01`, campaign `reviews-admission-profile-v1-20261023T193304Z.a2mfz4a0`, completed all four blocks. The returned archive checksum and all 81 members match extraction; all 56 locked raw-file hashes, protected input/runtime/index identities, complete coverage, outputs, actual stops/prefixes and diagnostic mechanisms pass sealed local verification. A fresh reconstruction matches the download-helper result exactly; twelve floating endpoints differ from remote by at most `5.55e-17`, under `1e-12`. Timing/attribution reports reproduce byte-for-byte. [E34][E35][E36][E37][E38][E39]

| Actual consumption | Result |
| --- | --- |
| Completed serial jobs | 20753185, 20753186, 20753187, 20753188 |
| Independent development vectors / cases | 200 / 600, previously exposed |
| Primary retained / warmup pairs | 115,200 / 28,800 |
| Diagnostic retained / warmup pairs | 17,280 / 4,320, on the fixed 30-vector subset |
| Searches / eviction installations | 370,884 / 33,120, counted separately |
| Provider calls / confirmation queries | 0 / 0 |

Compare the concurrent references in this campaign; older P2a campaign milliseconds are not the direct P2b baseline. P2b pools its identical A/B labels as repeated observations within each vector, not new independent samples.

| Candidate execution | Activation ms | Reuse ms |
| --- | ---: | ---: |
| Original | 9.593075 | 6.172896 |
| Frozen P2a | 9.592390 | 5.930276 |
| P2b | 9.390738 | 5.922666 |

| Direct P2b contrast | Regime | Gap ms, 95% interval | Arithmetic saving |
| --- | --- | --- | ---: |
| Versus original | Activation | -0.202338 [-0.236616, -0.168284] | 2.109% |
| Versus P2a | Activation | -0.201653 [-0.237160, -0.166512] | 2.102% |
| Versus original | Reuse | -0.250231 [-0.259452, -0.241027] | 4.054% |
| Versus P2a | Reuse | -0.007611 [-0.017850, +0.002364] | 0.128%; added benefit not established |

All required block saving directions, absolute/outer activation improvement, combined reuse improvement, original quality protections and all 144 nonregression endpoints pass. However, incremental activation's mean log-ratio upper endpoint is `-0.019623`, above `log(0.98) = -0.020203`; its implied lower saving bound is 1.943%, below 2%. Do not round this into a pass. [E34][E35]

**The frozen verdict is `measurement_inconclusive`.** A/A equivalence passes all overall and all reuse cells, but six activation/filter cells fail eleven absolute endpoints (five primary, six outer). All 24 relative A/A bounds pass. Examples: candidate/unfiltered primary interval [-0.126423, +0.011039] ms, matched-continue/`votes32` [-0.172466, +0.001670], routed-native/`votes108` [-0.030664, +0.101745]. Failed absolute intervals include zero, establishing insufficient equivalence precision rather than a proven >0.10 ms difference between identical code. Neither overall pooling nor the narrow relative activation miss waives the per-filter A/A obligation. [E34][E35][E36]

The expected mechanism is real: all 576 profile groups pass, fingerprints fall from four to one per constructor, and unprofiled candidate preparation falls from P2a's 1.477747 to 1.280951 ms (13.317%). The private snapshot also raises recursive copy entries from 299 to 1,901; profiler wall time therefore cannot substitute for unprofiled timing. Approximately 1.28 ms preparation remains, and P2b activation still costs 18.6–18.8% more than each label's ordinary-native reference. Outputs/recall/stops remain identical to original; no independent candidate confirmation or agent-method claim follows. [E35][E39]

A descriptive audit of all existing activation A/A rows finds later-label timing associations despite verified Williams position/predecessor balance. For candidate/`votes108`, B-minus-A averages -0.287898 ms when B is later versus +0.318301 when earlier (400 repeated pairs each; still 200 vectors). Similar direction appears in every arm/filter and in ordinary-native pair means. These observations do not isolate cache/drift/transport causes and must not correct treatment gaps. They justify calibration before another optimization. [E35][E40]

**Decision:** close NEXT-ADMIT-01 without adoption; preserve original as adopted baseline and P2a/P2b as experimental references. G2 remains `revise`. Scope `NEXT-CAL-01` with explicit activation/query-conditioning semantics, identical-path controls, adjacent counterbalanced ordering, unchanged margins and a separately declared finite resource cap. No new resources or run are assigned. Propose at most one justified calibration campaign; if unjustified or still inconclusive, explicitly retain original and redirect to bounded P3 rather than repeat indefinitely.

| Verified artifact | SHA-256 |
| --- | --- |
| Returned P2b archive | `4c1b7cef11d40f64a65b2488a1afc0df884be12d10e96c89d50be50083d09a7e` |
| P2b postrun receipt | `ba3f5116ab2583d61fac024dbb899112803fcc7fad18687a9ed64bc5f374a88f` |
| Existing-data order audit | `6a2f12fd54d48d0a15e79ca0203c23c1f39836716d63f46fd614254240b7d929` |

### 2.5 Conditioned activation calibration: verified P2c

`NEXT-CAL-01`, campaign `reviews-activation-calibration-v1-20261024T025706Z.c8557262`, completes its two serial jobs (`20778104`, `20778105`) and exactly 592,242 searches, including 96,000 conditioning executions. The checksum and all 41 archive members match extraction; the sealed replay verifies 26 locked raw hashes, protected runtime/index/input identities, getter and reference proofs, exact outputs/stops, full schedule/phase coverage, conditioning and admission charges. A fresh local reconstruction matches the helper result exactly; five remote floating values differ by at most `3.47e-18`, below `1e-12`; timing/calibration reports reproduce byte-for-byte. [E46][E47][E48][E49][E50][E51]

**A/A calibration passes:** all native/original/P2a/P2b controls, both regimes, every filter and overall satisfy all **80 cells / 240 interval checks**. Largest absolute primary/outer interval endpoints are 0.061166/0.061056 ms, inside ±0.10 ms; the largest absolute log endpoint is 0.007414, inside ±log(1.02). This establishes the declared equivalence precision in the new conditioned scope, not a cause for old order effects, a simultaneous confidence region or retroactive P2b acceptance. Small directional label intervals can still lie within the equivalence margins. [E46][E47][E49]

Concurrent candidate execution means in the new scope are:

| Execution | Fresh-session activation ms | Reuse ms |
| --- | ---: | ---: |
| Original | 7.769017 | 5.336453 |
| P2a | 7.743566 | 5.079864 |
| P2b, pooled identical A/B labels | 7.597712 | 5.085066 |

| Direct candidate contrast | Activation saving | Reuse saving |
| --- | --- | --- |
| P2b versus original | 0.171305 ms, 2.205%; gap interval [-0.189662, -0.152548] ms | 0.251387 ms, 4.711%; gap interval [-0.263132, -0.239246] ms |
| P2b versus P2a | 0.145854 ms, 1.884%; gap interval [-0.163744, -0.127846] ms | No added benefit: gap +0.005202 ms, interval [-0.005152, +0.015782] ms |

Activation savings persist in both blocks and every filter; combined reuse versus original saves in both blocks. P2a already contributes a 4.808% candidate reuse gain versus original in P2c. Candidate bypass reuse versus P2a is slightly slower (+0.021879 ms, interval [+0.003019, +0.041605]), within the practical nonregression limits. Do not claim every stratum improves. These are direct concurrent comparisons, not differences between old/new campaign milliseconds. [E47][E49]

**Engineering verdict: `revise_or_retain_original`.** All 144 nonregression bounds, original quality checks, block directions, combined reuse criteria and absolute/outer activation savings pass. The sole failure is incremental activation versus P2a: log-ratio interval [-0.022365, -0.017664] has upper endpoint above log(0.98) = -0.020203, implying only a **1.751% lower saving bound**, below 2%. Primary/outer absolute saving lower bounds are 0.127846/0.126142 ms, above 0.10 ms. Calibrated measurement supports a modest gain without satisfying the frozen practical requirement. [E46][E47][E48]

Pooled P2b candidate preparation remains 1.392070 ms versus P2a 1.555553 ms. Against its own ordinary native, P2b activation is still 36.876–37.036% slower and reuse 8.298–8.300% faster; the joint native-relative qualifier still fails. Native recall and candidate recall/stops are unchanged; all evidence is exposed development data. No new profiling, independent confirmation or useful-policy/method claim follows. [E47][E49]

Conditioning totals 531.632 seconds of native ANN time / 563.091 seconds of outer time; reset/conditioning/bookkeeping wall time is 651.629 seconds. These overlap and must not be added together. All are resource-counted but outside the explicitly conditioned service endpoint; constructor admission totals 61.397 seconds and stays charged. This scope cannot justify a deployment that needs per-request conditioning without measuring that full cost. [E46][E47]

**Decision:** close this finite P2 sequence without adoption. Retain original execution for bounded P3; G2 becomes `closed_negative` for optimized-path qualification, with the branch decision complete. M1/M2/M3 remain unestablished. P2c's allowance is consumed; no repeat, extra block, retuned conditioning, margin relaxation or automatic P2d optimization. Next is `NEXT-INFO-01` / P3a: an offline coverage/exposure/identity contract and inventory using permitted existing evidence. Fit or acquire outcomes only after the coverage gate and a separate bounded contract. No Torch command is needed now. [E46][E47]

| Verified P2c artifact | SHA-256 |
| --- | --- |
| Returned archive | `22813fb22742b7dec45903594c41e752dc3ee64e6ebe076cccf4d60257d0f599` |
| Postrun receipt | `533adf3dd53e10966c7edb74fbfd570e0e3bdbe8127ccc2f54f393bb893e6aec` |

### 2.6 P3a coverage/feature/identity audit: modeling is supported within a restricted scope

`NEXT-INFO-01` is complete under its frozen data-only contract. The audit verifies 620 source/input files before and after, reconstructs saved actual outcomes and cost labels, checks causal feature prefixes and reconciles catalog/vector aliases without opening reserved/confirmation query values. It performs no fitting, policy simulation, provider/database calls or Torch job. The source is 200 already exposed vectors / 600 cases; the old four-condition 100 vectors are an overlapping subset, not extra independent data. [E52][E53][E54][E55][E56]

| Current static23/progress34 grid coverage | Per profile |
| --- | ---: |
| Nominal 600 cases × eight checkpoints | 4,800 |
| Reached positions with actual stop proofs and all qualified features available | **4,695** |
| Missing labels at reached allowed positions | **0** |
| Positions not reached before search finished | 105 |
| Valid complete top-10 / known incomplete stop outcomes | 4,665 / 30 |
| Measured continue outcomes | 600 |

All 9,390 actual stop proofs reproduce their prefixes and outputs; corresponding static/progress outputs match at every stop. All original label/cost arithmetic is supported by the 21,180 retained acquisition pairs. The allowed stop ordinals are **1/2/4/8/16/32/64/128**, plus continue. The 105 unavailable grid positions are unreachable, not unknown reachable interventions; the 30 incomplete top-10 outcomes per profile are known negatives on votes108 (28 at checkpoint 1, two at checkpoint 2). Preserve these distinctions and every denominator. [E53][E54][E57][E59]

All qualified fields have valid types and no missing values at those allowed reached states. The audit reconstructs eleven progress observations over 95,106 states; static probe statistics stay constant in all 600 trajectories, while progress features change across allowed checkpoints in all 600. Light19 aliases the two filtered trajectories for every vector, but 359 paired grid states across 139 vectors disagree on complete recall preservation. Static23/progress34 already contain the actual validated predicate threshold; query/group IDs and evaluator strata remain forbidden runtime inputs. Variation and aliasing diagnostics do not establish predictive performance or a universal feature ceiling. [E54][E58][E59]

**Coverage gate: pass for restricted development modeling.** Prepare a finite grouped flexible-versus-shallow comparison within static23 and progress34 on the measured grid. No new outcome acquisition is needed first. All 200 vectors are previously exposed, with five existing 40-vector folds; this remains adaptive development, not independent validation. [E54][E55]

**Boundaries:** current-binary Light19 has only 1,074 directly executed stop cells out of 4,695, leaving 3,621 without direct proofs and no complete compatible fixed-stop cost matrix. The older 100-vector Light19 acquisition uses a different binary/profile/registry, despite matching outputs/prefixes; its costs cannot be pooled into current execution. Each current static/progress profile also has 90,411 observed off-grid states without actual stop labels. Those scopes need narrowing or a separately justified targeted acquisition. Any new learned policy still needs native/output and full-path timing evidence later; fixed-stop acquisition timings are proxies. [E53][E54][E55]

**P3a decision at completion (next-step status superseded by Section 2.7):** P3a is complete; final G3 family selection was unassessed. The next step was P3b/NEXT-MODEL-01 contract preparation, with no fitting in that audit or blanket timing campaign. Original execution remains adopted; no Torch command is needed now. Four audit decoder-format assertions were corrected with all versions/logs retained; the receipt records that cumulative compliance with the local 16 GiB read ceiling is not established. Scientific inputs/gates and all zero-experiment boundaries are preserved. [E54][E55]

### 2.7 Completed P3b grouped modeling comparison

`NEXT-MODEL-01`, local run `p3b-20261024-local-v1`, compares depth-three utility regression with a 64-tree depth-eight Extra Trees ensemble within each static23/progress34 profile. The contract was frozen before fitting: same qualified inputs and eight allowed checkpoints, exact five outer vector-group folds, four inner group folds, four risk weights, seven fixed score thresholds, measured first-stop outcomes, distinct-vector leaf support and paid same-profile continue. All 200 vectors / 600 cases were previously exposed. This is adaptive development, not independent confirmation. [E60][E61][E62]

| Profile / method | Non-continue outer selections / 5 | Stops / 600 | Recall difference | Activation / reuse proxy savings, ms | Development signal |
| --- | ---: | ---: | ---: | --- | --- |
| static23 / shallow | 0 | 0 | 0 | −2.250748 / −1.055653 | No |
| static23 / Extra Trees | 0 | 0 | 0 | −2.250748 / −1.055653 | No |
| progress34 / shallow | 0 | 0 | 0 | −1.870839 / −0.996567 | No |
| progress34 / Extra Trees | 0 | 0 | 0 | −1.870839 / −0.996567 | No |

**All twenty calibrated selections choose continue.** Every one of 225 inner candidates with positive mean activation and reuse proxies fails recall; all 305 recall-passing candidates have nonpositive proxies. Thirty fail both. These 560 overlapping assessments are not independent trials. The negative values above reuse measured profile-continue overhead; they are not a new serving regression, and no profile-continue policy is adopted. Zero calibrated paired contrasts reflect identical actions, not equivalence of model capacity. [E63][E65]

The predeclared fixed risk 320 / threshold 0 ensemble diagnostic stops 268/600 static and 216/600 progress cases. Static activation/reuse proxies save +0.454613/+0.924389 ms; progress +0.194550/+0.577725 ms. But overall recall differences are −0.2333 pp [−0.4000, −0.1000] and −0.2500 pp [−0.4667, −0.0833]. Both fail the −0.25 pp development lower-bound reserve; both also fail the original per-filter −0.5 pp replay on unfiltered queries, whose lower bounds are −1.15/−1.25 pp. The diagnostic cannot rescue selection. Its votes32 subgroup is descriptive, not a selected routing policy. Neither ensemble compression nor a pure capacity ceiling follows. [E62][E63][E65]

Fourteen synthetic checks pass; twelve synthetic fits across three test processes stay within cap 24. The scientific run consumes 340/360 estimator fits (11,050 individual trees), 235.661 seconds, 1,070,366,720-byte peak RSS and 841,202,095 metered read bytes, within its one-thread/60-minute/4-GiB/16-GiB limits. All 99 pinned files and ten source files are preserved. Independent data-only replay verifies 803 output hashes, all group/model bounds, 560 admission assessments and 4,800 outer case records, matching reports/paired contrasts within 1e−12 with zero new fits. [E61][E64][E66]

A zero-fit preflight failure from a blocked neighboring bytecode-cache lookup is preserved with its original sources, lock and logs; the corrected guard changes no scientific criterion. No native/DB/provider/Torch/confirmation/protected-query access occurs. New learned-policy latency remains unmeasured. [E61][E67]

**P3b decision at completion (next-step status superseded by Section 2.8):** close P3b negatively for these frozen procedures; G3 became **revise**, with original execution retained. The proposed next comparison was P3c/NEXT-RISK-01, separating risk from savings at fixed information/action/capacity scope. That hypothesis was not a diagnosed cause. [E62][E65]

### 2.8 Completed P3c risk-separated comparison

`NEXT-RISK-01`, run `p3c-20261024-local-v1`, is complete. Its contract was frozen before checks/fitting: learn positive recall loss (invalid/incomplete →1.0) to partition, then separately estimate minimum activation/reuse savings in the same fitting leaves. No additional tree set or depth is added. Preserve P3b's exact outer/inner vector folds, qualified features/actions, seed, weights, group support and paid continue. Forty-nine fixed risk-cap/benefit-floor pairs are calibrated per cell under unchanged recall/complete-result/economics gates. All data remain exposed development evidence. [E68][E69][E75]

| Profile / method | Selected outer cells / 5 | Stops / 600 | Overall recall difference, pp [95% interval] | Development recall | Activation / reuse proxy savings, ms | Joint signal |
| --- | ---: | ---: | --- | --- | --- | --- |
| static23 / shallow | 0 | 0 | 0 [0,0] | Pass | −2.250748 / −1.055653 | No |
| static23 / Extra Trees | 3 | 236 | −0.1167 [−0.2500, −0.0167] | Fail votes108 | −0.603150 / +0.032668 | No |
| progress34 / shallow | 0 | 0 | 0 [0,0] | Pass | −1.870839 / −0.996567 | No |
| progress34 / Extra Trees | 1 | 90 | −0.0167 [−0.0500,0] | Pass | −1.371480 / −0.653759 | No |

Twelve of 980 overlapping inner candidates qualify, occurring in four ensemble cells; none of the shallow candidates has positive economics. Outer static votes108 has a −0.35 pp lower recall bound, failing the −0.25 pp development reserve even though the original −0.5 pp replay passes. Progress passes recall but both cost proxies remain negative. Static/progress activation proxy intervals are entirely negative: [−0.875996, −0.316607] and [−1.529962, −1.195185] ms. Inner admission is not a qualifying outer result. [E70][E71][E73]

The fixed cap .0025/benefit 0 ensembles reduce observed losses from P3b's11/10 to 1/1 and pass development recall in all filters. But their activation proxies are −0.280050/−0.599384 ms; both intervals remain negative. Most diagnostic stops occur at 128. The safer decisions still fail to cover activation economics. Relative to P3b's calibrated always-continue outcome, P3c has better cost proxies; it still does not beat the original native reference or establish actual serving improvement. No post-hoc subgroup routing rescues these outcomes. [E70][E71][E73]

Sixteen synthetic checks use six fits. The scientific run completes exactly100 fits (80 inner +20 shared outer),3,250 trees,102.377 seconds, 0.993 GiB peak RSS and 0.839 GiB metered reads, within one-thread/100-fit/60-minute/4-GiB/16-GiB limits. Independent replay verifies323 output hashes, all 919 pinned prior files, group splits,248,851 training-leaf risk/benefit values,980 candidate assessments,4,800 outer cases, controls and paired contrasts within 1e−12, with zero new fits. No failed scientific run, new dependency install or native/DB/provider/Torch/protected access occurs. [E69][E72][E74]

**P3c decision at completion (B1a progress superseded by Section 2.9):** close P3c's finite formulation allowance and G3's bounded investigation **closed_negative for the tested procedures**. Original execution remains adopted; no information-theoretic ceiling or useful-policy/method success follows. Recommend **B1a/NEXT-SCOPE-01**: read-only audit of fixed-index query-dependent search effort, actual backend knobs, cheap qualified inputs and ordinary-native cost boundary. This scopes an alternative to repeatedly paying a stopping profile's overhead; feasibility/speed are unproven. B1a is proposed only. Fresh development diversity remains conditional on a precise question and new entitlement contract; no automatic acquisition or confirmation reuse. [E69][E70]

### 2.9 Completed B1a fixed-index effort feasibility audit

`NEXT-SCOPE-01` is complete as a read-only audit. The pinned pgvector 0.8.6 source exposes user-settable `hnsw.ef_search` (range 1–1000), passed to initial layer-zero search. Varying it does not require rebuilding the graph. `max_scan_tuples` is an iterative-resumption limit, not an initial-search distance-work cap; keep iterative scans off for the first comparison. These are source/semantic findings, not current lower-effort native qualification. [E76][E77][S26][S27][S28]

The strict query API has no effort field; the bounded policy language supports only stop/continue. The current and frozen backends preserve source settings and use ordinary autocommit for native searches. A new versioned experimental native-effort interface is needed; do not mutate the adopted origin manifest or inherit the old inner SQL timer while hiding selector/setting/session costs. Recommend two immutable 320/640 reader bindings with sequential dispatch, full activation/reuse charges and unwrapped-original 640 versus wrapper-forced 640 controls. A transaction-local alternative must enclose the search and charge transaction work. [E76][E83][S29]

Actual validated predicate context and `k` are pre-query inputs. The600 exposed cases contain only three contexts: no filter, `m_000000 >= 32`, and `>= 108`, all with `k=10`. These can support at most eight simple maps to two efforts, not individual vector-difficulty prediction. Exact selectivity/descriptors are offline; progress probes are not free pre-query information; IDs/evaluator strata remain forbidden selector inputs. No router was fitted or simulated. [E76][E83]

The old effort sweep's122 input hashes and six saved analysis outputs match. Its30 vectors /90 cases /25,920 pairs show native recall93.00/95.89/97.56/98.67% at 80/160/320/640, with incomplete filtered outputs at 80/160. But its index identity is `60761278…`, with physical file hash`8c15a172…`; P3's current index is `90f4a709…`, file hash`dbc14b09…`. The size-sweep full-size index matches current bytes but has only320 evidence in an older runtime/profile. Old/current query-group inventories differ. Do not pool these scopes, assume fresh vectors from ID nonoverlap, or turn640 stopping prefixes into320 outcomes. [E76][E79][E80][E81][E82]

**Baseline scope:** Reference640 is the fixed P1–P3 study setting, not a verified production default. Preserve inspected origin settings separately and record any real source/default baseline in B1b; historical source320 and explicit study640 overrides must not be conflated. [E76]

**Decision:** B1a complete; **GB1 pass, scoped engine feasibility only**. Recommend B1b/NEXT-EFFORT-01: freeze current-index/current-module native interface correctness, matched 320/640 effort outcomes, strict controls, actual selector/pool/setting costs, original 640 quality reference, exposed-data entitlement and finite resources. Implement/check only under that new scope, then provide exact Torch commands. Router fitting waits for a supported frontier; no measurement or budget is assigned by this audit. All 324 inventoried code/source files and prior inputs remain unchanged. [E76][E77][E78]

### 2.10 B1b implementation and prospective Torch frontier

`NEXT-EFFORT-01` **preparation snapshot at v1.14; completed results supersede it in Section2.11**. At preparation it was ready for Torch, not complete as an experiment. The user requested proceeding with B1b after the B1a audit. The [frozen contract][E84], [implementation/reproduction guide][E85], [local verification receipt][E86] and [exact commands][E87] now define one finite native comparison. Original native SQL/execution methods, module, physical index, prior policies and P2/P3 verdicts are unchanged. Local tests exercise protocol behavior with fake readers and synthetic clocks only; they do not qualify the x86 native interface or estimate speed. [E84][E86]

| B1b element | Frozen behavior / purpose |
| --- | --- |
| Intervention | Native `ef_search`320/640 only; iterative scans off; current90f4 index / dbc14b09 file / e7dcace1 module; no rebuild |
| Baselines | Unwrapped original640 study reference, wrapped forced640 overhead control, wrapped forced320, and unwrapped inspected-source320 comparator; actual/default setting metadata recorded separately |
| API / routing boundary | Versioned experimental `{version, effort, query}` envelope; strict existing query validation, actual predicate/k parsing, only integer320/640; unknown valid contexts default640; no fitted router or ID/evaluator-label feature |
| Ownership / isolation | Two private effort-bound reader sessions share the once-loaded immutable snapshot; origin manifests stay unchanged, effective binding views change only effort; replaced/closed/mutated sessions reject, no silent retry |
| Primary timing | Full outer constructor + first query for activation, including **both** wrapped readers, connections/security/settings/binding and validation/selection; same-session reuse after one discarded warmup; native SQL timer secondary only |
| Operating scope | Warm/shared restored index and snapshot, exactly two separate native640 conditioning calls before each fresh slot; excluded restore/reference/qualification/conditioning/audit/cleanup costs recorded separately; no cold-index or production-default claim |
| Controls / pairing | Four identical-path A/A cells, two adjacent counterbalanced ABBA/BAAB rounds, two complementary blocks; direct matched wrapped640/320/source versus original640 contrasts, no control-gap correction |
| Data / quality | Same200 already-exposed vectors /600 cases; fresh exact truth and pinned P2c original640 results; complete valid top10, reference recall floor.95, context recall-delta lower95% bound≥−.0025; −.005 final margin diagnostic only |
| Finite resources | Two serial allocations, each4CPUs/32GiB/2hours;6,600-second work deadline/block;69,636 searches/block /139,272 total; no provider calls, fits, protected queries or extra blocks |
| Local checks | Seventeen tests, including complete600-case schedule, two-block raw roundtrip, vector clustering, raw semantic tamper rejection, connection/binding/error cleanup, allowlist/fallback and durable unknown-dispatch behavior; lint/format and sealed integrity checks |

Each complete block has36 native qualification searches,2,400 exact/native/effort/source reference searches,19,200 conditioning calls and48,000 scheduled executions, including9,600 discarded warmups and38,400 retained observations. It admits14,416 readers and performs14,400 post-slot settings audits. Search counts do not pretend to count every SQL statement. All repetitions stay clustered within the same200 vectors. The analyzer computes56 prespecified summaries,10,000 vector bootstrap resamples each; intervals are pointwise, not independent confirmation or simultaneous guarantees. [E84][E88]

The native gate first verifies actual settings/HNSW plans, alternating effort isolation, original/forced640 output agreement, source320 agreement, exact-transaction independence, actual SQL failure/rollback and explicit new-session recovery. Restored IDs/votes/vector bits and physical index/module hashes are checked; no silent repair or rebuild. Incomplete320 results remain recorded quality failures, never trigger a free640 rerun. Raw ingestion checks full chronological phases, initialization charges, schedule/counts, predicate membership, exact recall, deterministic outputs and remote/local report parity. [E84][E85]

**Prospective GB1b decisions:** A/A requires all four cells, overall and every filter, to fit ±.10ms and ±log(1.02) in each regime:64 interval checks total. Context/regime wrapper640 overhead must have upper95% bounds≤+.10ms and≤log(1.02). Wrapped320 must also pass complete-result/recall protection and establish≥.10ms /2% outer saving versus original640, with saving in both blocks. A supported context can justify a **new B1c design only in that qualified regime**; reuse-only support cannot qualify activation or deployment. No supported context with failed precision yields `measurement_inconclusive`; adequately measured failure yields bounded negative closure. Neither outcome authorizes automatic repeats, more efforts or routing fits. [E84]

Historical v1.14 next action was the Mac upload helper, once-only Torch submission, then status/collect/download in [E87]; these actions are now complete. The controller's reservation/binding prevents duplicate or uncertain resubmission; preserve failures for diagnosis. The completed native/control/frontier result and local metadata recovery are recorded in Section2.11. [E90][E91]

The first undispatched preflight package/receipt were preserved and superseded before delivery after review removed a reporting wrapper from the supposedly unwrapped baseline query timer. A seventeenth regression check protects direct inherited execution. No cohort, margin, budget or native result changed; no job used that preflight. [E85][E86]

### 2.11 Completed B1b native-effort comparison and recovered return

Campaign `reviews-native-effort-v1-20261025T014743Z.p_kspq5v`, user jobs20845494/20845495, completes both blocks and exactly139,272 searches. The [postrun receipt][E90] and [results report][E91] record passing native conformance, all complete/valid top10 outputs, stable actual320/640 references, unchanged current index/module and source preservation. All200 vectors /600 filter cases remain previously exposed development data. Actual consumption:76,800 retained executions,19,200 warmups,38,400 conditioning calls,4,800 reference searches and72 qualification searches. There are zero provider calls, fits or confirmation queries. [E90][E92]

The initial Mac ingestion failed after reconstruction because the remote analyzer saw the campaign through the `/results` container mount and recorded `campaign="results"`; the Mac recorded the actual extracted name. Download/checksum and both native runs were intact. A separate [data-only recovery helper][E94] verifies all40 archive/extracted members, sealed146-file package, exact submission/job identities,26 locked raw files and full unchanged analyzer. It reconciles only the copied top-level campaign metadata field to the proven submission identity. Every other discrete/gate value matches exactly; three floating differences have maximum4.3368e−19, below the original1e−12 tolerance. The [verification record][E93] explicitly distinguishes this scoped recovery from literal unmodified-report parity. Raw data, sealed code, original failed local output, margins and gate logic stay preserved. Four regression checks reject unrelated identity/result/gate changes. No new Torch/DB/native experiment was required. [E90][E93][E94]

| Native path | Full activation mean ms | Full reuse mean ms | Reuse change versus original640 |
| --- | ---: | ---: | ---: |
| Unwrapped original640 |83.302736 |5.519471 | Reference |
| Wrapped forced640 |138.306258 |5.725706 |3.736% slower |
| Wrapped forced320 |134.792358 |3.281898 |40.540% faster |
| Unwrapped inspected-source320 |78.152103 |3.098796 |43.857% faster |

Wrapped320 reuse saves2.237574ms,95% interval[2.180726,2.292328]ms, with savings in both blocks/all filters. All contexts meet the reuse benefit threshold. But forced640 reuse adds0.206235ms,[0.190779,0.221789], and exceeds both .10ms/2% wrapper-overhead bounds in every context. Wrapped320 activation adds51.489622ms,[48.071350,55.218889], with its two-reader admission charged. Activation numbers are descriptive because its A/A precision fails. This new fresh-reader activation scope cannot establish cross-campaign improvement percentages versus P2a/P2b/P2c. [E91][E92]

| Filter | Original640 recall | Effort320 recall | Difference pp |95% difference interval pp |
| --- | ---: | ---: | ---: | --- |
| Overall |99.0333% |98.2333% |−0.8000 |[−1.0833,−0.5333] |
| Unfiltered |99.3500% |98.9500% |−0.4000 |[−0.7000,−0.1500] |
| votes32 |99.1500% |98.6000% |−0.5500 |[−0.9000,−0.2500] |
| votes108 |98.6000% |97.1500% |−1.4500 |[−2.0000,−0.9500] |

Every context fails the−0.25pp development recall reserve. Overall quality is also worse than the−0.50pp final margin throughout its interval; that check remains diagnostic, not independent confirmation. There are46 lower-recall cases (8/11/27 by filter), no higher-recall cases, and554 unchanged-recall cases. These are600 cases clustered into200 vectors, not600 independent observations; repetitions do not create additional quality evidence. [E91][E95]

**Control and branch decision:** reuse A/A passes32/32 interval checks; activation passes2/32 and fails30/32. Preserve the frozen aggregate **`measurement_inconclusive`** verdict. Separately record that all reuse contexts fail quality and wrapper overhead despite passing reuse precision. The finite campaign is complete with **zero supported context/regimes**; retain original execution and defer B1c. A map selecting320 for any whole context inherits that context's failing reserve; all640 offers no effort reduction. This dependency argument fits/selects no router. Repeating activation calibration alone cannot repair unchanged recall/control failures. [E90][E91][E92]

**Historical next action at v1.15 (now completed in Section2.12):** read-only effort/interface revision review, before a new measurement contract. Decide whether an intermediate-effort question and a lower-overhead admission/validation design are justified. No intermediate recall/cost interpolation, new effort value, extra blocks, feature acquisition or protected-data entitlement is established here. Any revised intervention needs a new finite identity/conformance/quality/cost/resource contract. Current B1b allowance is consumed; M1/M2/M3 and independent/canonical acceptance remain unestablished. No user commands are needed now. [E90][E91]

### 2.12 Completed B1-review and prospective B1b2 design

The design-only status below is the preserved v1.16 preparation snapshot. Section2.13 records later implementation and Section2.14 the completed native480 result; statements of pending work below are historical.

`NEXT-EFFORT-REVIEW-01` is complete. The [review][E96], [machine-readable audit][E98] and [preservation receipt][E100] combine existing source and descriptive raw-timer evidence. Wrapped admission opens two readers rather than one: each executes one security check, one target acknowledgement,14 source-setting statements and one timeout statement, or34 versus17 explicit startup SQL calls. Static counts exclude authentication/protocol/internal work and are not per-operation latency measurements. Forced640 preparation averages116.185421ms versus63.873831ms ordinary; activation precision still fails, so these descriptive categories do not qualify a causal savings estimate. [E96][E98]

The same matched forced640 reuse contrast decomposes into+0.081905ms inside the SQL timer and+0.124329ms outside it, totaling+0.206235ms. Extra wrapped vector/schema validation, origin/binding checks and owned copies are visible in source. The outside-SQL term is not isolated validator time; inherited vector formatting/context construction and policy-cache setup are common costs, not established differential causes. Current optimized dispatch/validation is only a design reference and is excluded from the next comparison. Do not remove correctness checks or use query IDs to admit new mutable requests. [E96][E98]

**Decision: GO for one new design, NO-GO for the unchanged wrapper/router or calibration repeat.** Freeze **B1b2 / NEXT-EFFORT-MID-01**, constant native480 versus study640, using one owned bound reader per arm and the unchanged native method/scorer.480 is a prospective midpoint information probe, not a predicted qualifier, interpolation or fitted optimum. Origin320 and boot40 remain provenance; the new claim is only against study640. No effort ladder, post-hoc context map, new validator, transport optimization or pooling dependency is included. [E96][E97][S31][S32]

The [new contract][E97] specifies: isolated implementation/local checks/seal first;30 native conformance searches;1,800 fresh exact/640/480 quality searches; stop by1,830 if the −0.25pp development reserve, native floors or completeness fail. Only passing quality unlocks two complementary temporal blocks within **one**4CPU/32GiB/two-hour allocation (6,600-second work deadline),57,600 more searches and fresh16-interval warm A/A qualification. Total ceiling59,430;14 reader admissions, five live readers. Require at least0.10ms/2% confidence-bound savings overall and per filter with correct direction in both blocks. The600 cases/200 vectors are the same exposed inventory; zero new vectors, providers, fits, protected values or confirmation queries. [E97]

**Scope limit:** persistent-reader full query time is a new prospective diagnostic endpoint. Shared snapshot/request admission, reader startup/first-use, conditioning, audits and cleanup stay separately charged. This does not fix B1b activation precision, establish fresh-session economics, relax the original joint target or qualify serving/agent success. Both blocks share one allocation/database. A pass means only `promising_warm_fixed_configuration`; adoption/operating-scope/independent-entitlement review remains separate. Failure closes this finite probe without automatic extra values or blocks. No package or Torch commands exist yet. [E96][E97][E100]

### 2.13 B1b2 implementation and sealed user comparison

**Historical preparation snapshot at v1.17; Section2.14 supersedes its pending status.** The user requested implementation/local preparation after B1-review. At preparation, **G0-B1b2 local readiness passed; native, quality, A/A and benefit were not assessed.** The [implementation guide][E102], [receipt][E103], [sealed manifest][E104] and [commands][E105] define the prepared package. The original [design][E97] is copied byte-for-byte, SHA09176883…02ed7; its preimplementation status text remains a historical snapshot rather than a changed scientific contract.

The isolated harness keeps inherited native SQL/execution/exact-reference/scoring methods. It binds one effort per owned reader, freezes admitted query/origin/effective containers and includes symmetric stale/closed/replaced-connection guards inside both primary timers. Native SQL errors close the handle; only the explicit qualification recovery creates a new reader. All requests are the existing600/200 exposed inventory, admitted once with the unchanged shared validator; no new public API, selector, direct-native optimization, policy or native module is introduced. [E102][E103]

The code reserves every search attempt before execution.30 conformance calls precede1,800 fresh exact/640/480 references. Complete-data quality failure closes normally at1,830 searches and creates no timing files. Only quality pass permits four benchmark replicas and two temporal blocks in one allocation:28,800 retained executions,9,600 discarded warmups and19,200 conditioning calls; maximum59,430 searches,14 reader admissions/five live readers. Fresh A/A checks all16 intervals; benefit remains0.10ms/2% confidence-bound savings overall/per filter and correct direction in both blocks. Snapshot, admission, first-use, conditioning, audit and cleanup stay separately recorded. [E97][E103]

Independent data-only replay verifies raw count/order/reader/timer containment, settings and native outputs against freshly measured same-effort references before gates. Canonical campaign identity comes from proven submission/package/job metadata; an alias mount does not change reports. The local collector never executes downloaded code. Actual native conformance/quality remain pending; mocks establish no speed or recall result. [E102][E103]

| Local readiness evidence | Verified result |
| --- | --- |
| Source / sealed correctness checks |22 /22 pass; fake connections/results and synthetic clocks only |
| Full mock acquisition |600 cases/200 exposed groups, two temporal blocks,59,430 charged calls; independent raw replay |
| Negative mock branch |1,830 charged calls, no repeated timing, valid negative collect/archive/checksum/replay |
| Integrity checks | Closed/stale/replaced binding, altered primary timer with rehashed lock, missing execution, archive escape, unrelated parity change and uncertain duplicate dispatch rejected |
| Package |150 manifest files;151 regular archive members, byte hashes and shell syntax pass |
| Manifest SHA | `b7ad5be746bfa26bcaf5fbd381b0523c518f3872bb8011d8d00331b399c34bc1` |
| Archive SHA / bytes | `fbd7ac0654bb9ff99f6add7011127caf01c008cd08fb142abe56783ea94e6185` /14,831,467 |
| Prior preservation | All691 prior source/evidence files still match; prior contracts/receipts/raw data untouched |
| New native/DB/provider/Torch/fits/protected values |0; no submitted campaign yet |

**Next user action:** Mac upload, then once-only Torch checksum/extract/submit in [E105]. One4CPU/32GiB/two-hour job contains both temporal blocks; the work deadline is6,600 seconds. Use the new `mid_control.py` status/collect commands; no old controller/path is applicable. After collection, Mac download verifies checksum and replays sealed local analysis. A quality-negative job is complete and should still be collected/downloaded. Keep any failure/unknown reservation; do not repeat submission. [E105]

### 2.14 Completed B1b2 midpoint: negative quality closure

The user's campaign `reviews-native-midpoint-v1-20261025T172357Z.ybpfkkki`, job 20898557/task 0, is complete and independently verified. All 24 returned archive members, 15 locked raw files, 150 sealed package files/151 package archive members and 12 implementation source hashes pass. Fresh unchanged sealed analysis is byte-identical to remote and download-helper reports, without a parity repair. Saved-ID arithmetic independently reproduces all 1,200 current recalls. All 888 immutable input/source/evidence hashes remain preserved; the previously documented outer transfer-helper recovery is explicitly reconciled, not ignored. [E107][E108][E110][E112][E113]

**Native conformance passes; quality fails.** Both efforts produce valid complete sets of 10 results and exceed 95% mean recall overall/per filter. The frozen development gate instead requires the lower 95% bound of 480−640 recall to be at least−0.25 pp in every stratum. Intervals are pointwise development bounds clustered over 200 already exposed vectors, not independent confirmation. [E109]

| Stratum |640 recall |480 recall |480−640, pp |95% delta interval, pp | Reserve verdict; lower-bound shortfall |
| --- | ---: | ---: | ---: | --- | --- |
| Overall |99.0333% |98.8500% |−0.1833 |[−0.3333,−0.0667] | **Fail;0.0833 pp** |
| Unfiltered |99.3500% |99.3000% |−0.0500 |[−0.1500,0] | Pass;0.1000 pp headroom |
| votes32 |99.1500% |99.0000% |−0.1500 |[−0.3500,0] | **Fail;0.1000 pp** |
| votes108 |98.6000% |98.2500% |−0.3500 |[−0.6500,−0.1000] | **Fail;0.4000 pp** |

Shortfall is distance below the −0.25 pp lower-bound threshold, not the observed point loss. Failure to establish noninferiority does not prove the true loss exceeds the margin. The looser−0.50 pp final-margin diagnostic also fails votes108 by 0.15 pp; its other passes cannot replace the development gate. Eleven cases across nine vectors lose one true neighbor each; seven misses are votes108.480 recovers 37 true neighbors versus 320 (+0.6167 pp overall), after all 600 exact/640 outputs and query/index/module identities match; this descriptive improvement still fails the 640-relative gate and supplies no latency comparison or interpolation. [E108][E110][E111]

**Frozen verdict: `closed_negative_quality`.** Exactly 30 conformance+1,800 reference searches=1,830 ran, with 10 reader admissions. No timing blocks, retained executions, warmups or conditioning ran; A/A and benefit are **not assessed**, not failed. Work elapsed859.376 s is not a candidate speed estimate. Native/index/module/protected-source preservation and cleanup pass; zero providers/fits/confirmation/new vectors/protected values. The 57,600 conditional timing searches were skipped as designed. Original execution retained; B1c remains deferred; no post-hoc unfiltered router, 560/600 ladder, extra block or revised margin follows. [E107][E109]

**Historical next recommendation at v1.18 (completed in Section2.15):** B2a / `NEXT-PLAN-SCOPE-01`, a read-only plan/filter/index audit with its own source/identity/input gate, before another experiment. Compare current-engine exact/ANN plan options and distinct filtered-index/traversal alternatives; do not assume broad20%/50% filters favor exact search or that iterative scans repair recall when all outputs already contain 10. This is a proposed scope decision, not completed feasibility or a universal negative effort result. Details, stop/go and revised dependencies appear in Sections 6–7. No user commands now. [E108][S21][S26][S28]

### 2.15 Completed B2a plan/filter/index scope audit

**GB2a passes scoped source feasibility: GO for one new B2b exact-top10 versus native640 design; no router or rebuild.** The user named the already completed B1a; the stated interpretation was to handle the next B2a read-only audit. The original B1a and all prior results remain unchanged. The [report][E115], [findings/matrix][E116], [source inventory][E117] and [receipt][E118] pin 349 existing code/source files and 907 immutable files. No code, tests, measurements, fits, simulations, database/native/provider/Torch or protected-query access occurred.

The loaded exact-reference mixin uses no SQL LIMIT, bypasses index scans, fetches all eligible rows and builds exhaustive truth/eligibility/ties. Native execution uses the same cosine/filter expression with LIMIT k and can execute ordinary non-HNSW SQL. Therefore a separately bound exact-top10 reader can be investigated on the current table/graph/module using four explicit planner-setting overrides, with the native statement/formatter and full truth generator preserved. This is source feasibility, not measured exact execution economics. Existing reference acquisition timers cannot substitute. [E115][E116]

All six saved480/640 fixture plans are Limit→HNSW Index Scan; filtered scans retain executor Filter fields. Saved plans have estimated costs/rows, no actual execution-time/work counters. The recipe declares only primary-key and full HNSW indexes; the saved selected-index identity is not a complete current scalar-index catalog. Capture that catalog/statistics/effective plans/cache configuration at future qualification; no live metadata query was run here. Current filters retain 123,692/49,498 of 247,286 rows (about 50%/20%), so exact/scalar-index savings are unknown. [E115][S33][S34]

| Alternative | Scoped finding | Decision |
| --- | --- | --- |
| Fixed exact top10 versus native640 | Existing SQL/setting mechanism; same graph/module, new effective binding and experiment identity | GO for one prospective B2b design only |
| Planner-default/scalar index | Plan choice does not enforce recall; scalar DDL changes catalog and ordering/cost assumptions | Exclude from initial comparison |
| Partial/partitioned HNSW | New graphs/layout; current public backend rejects partial selected targets and partitioned relations | Defer to separate physical/backend scope |
| ACORN/predicate-subgraph traversal | Current threshold feature is not traversal; ACORN-1 expands during search but documents an unpruned graph variant, unlike current pruning | New native/graph qualification required; no drop-in compatibility claim |
| Iterative scans/extra effort levels | Complete outputs already obtained; distinct interventions | No automatic recall repair, ladder or post-hoc480 router |

Actual predicate AST/k are possible later routing inputs with charged parsing/ownership; offline counts, query IDs/evaluator labels and acquired outcomes are not free decision inputs. No qualified within-filter predictor or economic exact-path family is established. Preserve 60 unconsumed confirmation/37 reserved vectors. [E115][S21][S35][S36][S37]

**Historical next recommendation at v1.19 (now prepared in Section2.16):** B2b / `NEXT-EXACT-TOPK-01` prospective finite design, then isolated implementation/check/seal, native plan/tie-aware semantic/quality qualification and actual fresh A/A/full-outer cost comparison before any router. Proposed ceiling only: one 4CPU/32GiB/two-hour allocation, 6,600-second work deadline, at most 50,000 backend attempts including every acquisition/control/warmup; same 200 vectors/600 cases, zero providers/fits/protected/confirmation/new vectors. Exact schedule/counts/gates must be frozen before code; no package or commands exist. Warm persistent-reader diagnostic cannot qualify activation/adoption. No JIT/parallelism/index/validator/transport tuning is bundled. [E115][E116][E118]

### 2.16 B2b frozen implementation and sealed Torch comparison

The user authorized freezing and implementing the exact-top10 versus native640 comparison, local checks and Torch preparation. **G0-B2b local readiness passes; actual native/performance gates are not assessed.** The [frozen contract][E120], [guide][E121], [implementation receipt][E122], [sealed manifest][E123] and [exact commands][E124] define the new finite study. The B2a report/receipt remain historical source-feasibility evidence; no experiment ran during preparation.

Both cells inherit native SQL/formatter/execution/decoder and the independent exhaustive truth generator byte-for-byte. Native640 retains its study settings. Exact10 keeps effort640 and overrides only seqscan on and index/index-only/bitmap scans off in an owned effective binding; origin320 and boot40 remain separate. No index, module, query validator, direct-native transport, JIT/parallelism/work_mem tuning, router or protected data. Full-outer warm timers include symmetric connection/binding guards; startup/snapshot/admission/first-use/diagnostics/cleanup remain explicit separate charges. [E120][E121]

A private existing prepared copy must pass unchanged data/graph/module checks plus full catalog/scalar-statistics stability.30 fixture searches cover exact/native plans, alternation, native640/truth pins, tie-aware exact output, abort/rollback/closed-reader rejection and explicit new-session recovery.1,800 fresh references then require exact semantic correctness, complete valid top10,95% native floors and−0.25pp development recall reserve overall/per filter. Semantic/plan/catalog/integrity failure is failed qualification, never a valid quality-negative result. Ordinary complete-data quality failure stops at1,830 with no timing phase. [E120][E122]

Only passing quality opens two complementary temporal blocks in one allocation:9,600 slots total, each with one native conditioning call, one discarded warmup and two retained executions. Total40,230 backend searches:19,200 retained,9,600 warmups,9,600 conditioning plus30 qualification/1,800 references. Maximum14 reader admissions/five live; one4CPU/32GiB/two-hour job,6,600-second work deadline. No extra block, attempt or automatic retry. [E120][E123]

All16 native640/exact10 A/A95% intervals must lie inside±.10ms/±log1.02. A context is only promising if both blocks favor exact, quality and every A/A pass, and economic upper bounds show at least.10ms/2% savings. Since any overall/three-filter report could be named promising, Bonferroni-adjust eight one-sided economic bounds (alpha.05/8, bootstrap99.375th percentile). This is development bootstrap evidence, not independent confirmation, a selected router, activation or deployment. [E120]

The collector also verifies12,012 current/cached plan packets on a complete run (2,412 at quality stop), independent statement/query hashes and diagnostic phase timers. It keeps preparation/cache behavior unchanged and audits matching EXPLAIN EXECUTE plans; metadata probes condition cache choice and are part of this declared warm diagnostic scope. Full catalog snapshots are stable, observer SQL is capped at40,000, actual plans cannot be inferred from estimated costs, and planned workers are not actual-worker profiling. Native resource accounting remains one bounded allocation. [E120][S39][S40]

| Local readiness evidence | Verified result |
| --- | --- |
| Source / sealed checks |33 /33 pass; fake connections/results and synthetic clocks only |
| Full acquisition/replay |600 cases/200 exposed vectors, both temporal blocks,40,230 fake searches,12,012 plan packets; independent raw replay |
| Early/negative/error paths | Injected quality stop at1,830; exact semantic error aborts; negative economics collect/archive/parity and terminal failed-job collection pass |
| Integrity | Catalog/index/tuning/cache/plan rejection, tie equivalence, changed distances, missing executions, rehashed primary/diagnostic timers, archive escape, uncertain duplicate submission |
| Package |153 manifest files/154 regular archive members,14,841,564 bytes; every member/source byte matches |
| Manifest SHA | `0124abaa1c472f19e0f778c633f7a4c1cc42f69430f83964a4a14cb90a56f55e` |
| Archive SHA | `01c6d272ac5de658e72c7c8e0bd5c2038a44fa5b5181d83039bf16c79f47b65d` |
| Transport | Shell syntax and4 authentication/transfer/remote-checksum/success mock stages pass; no network/job calls |
| Preservation | All912 prior immutable hashes match; all349 B2a source files and previous experimental evidence untouched |

**Original pre-run handoff (superseded by Section2.17):** E124 was used for one user Torch submission. Job20941363 now reports failed initial catalog qualification with zero searches. Preserve the original package/reservation; use the original controller/helper only to collect and download failed raw via E131. No repeated submission or performance interpretation. [E126][E127]

### 2.17 Original B2b pre-return failure diagnosis and correction preparation (historical)

**Pre-return snapshot; current verification and handoff are in Section2.18.**

User-reported campaign`reviews-exact-topk-v1-20261026T032153Z.9khasec1`, job20941363_0, failed1:0 after6m17s at `HNSW catalog differs from frozen source`. Reported search count0, operations empty, providers0 and protected sources unchanged. Raw archive, full scheduler accounting and cleanup have not yet been independently reviewed. This is failed qualification; no valid recall/economic negative, A/A verdict or graph-change conclusion follows. SSH disconnect did not cancel Slurm execution. [E126][E127]

The catalog query sends PostgreSQL `oid` through `to_jsonb(t)`, producing JSON text. The old validator/mock expect integer264013, so correct text`"264013"` is rejected. Pinned PostgreSQL17.11 sources and a regression reproduce this deterministic defect; other actual remote field differences remain unknown. The old observer did not persist a rejected catalog. [E127][S41][S42]

A separate `exact-topk.v1.catalog-fix` harness expects that exact text ID without coercion, retains every other graph constraint and unchanged SQL, logs raw rejected catalogs/field differences and labels initial catalog progress accurately. The original design, source/seal/receipt/archive and failed reservation remain historical and unmodified. The corrected controller requires pinned original failure identity, zero-search accounting, stopped/closed cleanup, unchanged protected evidence, terminal FAILED accounting and checksum-valid collected archive before any new reservation/sbatch. [E128][E129][E133]

Local/source and sealed suites each pass43 checks; package155 files/156 archive members/14,855,087 bytes; four transport-stage mocks and1,095 prior immutable hashes pass.127 frozen runtime files, reader/quality/statistics/report/host-launcher bytes, catalog SQL and scientific constants remain unchanged. The attempted temporary PG16 scalar fixture could not initialize under sandbox shared-memory restrictions; it ran no SQL and establishes no native qualification. [E129][E130][E132]

**Current user action:** collect the existing failed campaign on Torch, then use the original Mac helper to download/checksum it. Codex verifies actual archive/submission/job/search/cleanup/protected evidence before releasing corrected commands. The corrected package is prepared, not submitted. Its prospective one additional4CPU/32GiB/two-hour allocation preserves6,600s/40,230-attempt maxima and all gates; the original failed allowance remains consumed. No automatic repeat, router or adoption. [E128][E131]

### 2.18 Failed original raw verified; corrected commands released

The downloaded original archive now independently passes checksum,19-member archive/extracted-byte, sealed-package, submission/job/path, terminal FAILED1:0 accounting, zero-search failure, cleanup and integrity checks. One initial native640 reader was admitted and closed; private DB stopped. Captured protected reports are byte-identical across19 groups/1,621 entries; seven prior raw identity groups match the frozen contract. Prepared database identity and module/image/profile/registry/snapshot/eligibility/origin/effective settings match. [E134][E135][E137]

No qualification references, quality, A/A or timing files were acquired; no performance verdict exists. The full rejected catalog is absent, as expected from the old validate-before-save path, so other actual catalog-field differences cannot be retrospectively reconstructed. Reported6m17s retains user-status provenance; the collected scheduler record omits elapsed. Remote binding bytes are absent from the archive: the original helper checked them during download, and the corrected controller rechecks actual binding/package/prerequisites before submission. No integrity waiver or scientific normalization. [E134][E137]

**B2b.R2 and R3 now complete:** release the unchanged separate correction with [E136], superseding only the prior HOLD. Original and corrected seals, original failed raw and1,307 preexisting inputs/artifacts remain preserved. Previous43 source/43 sealed checks remain applicable; no test repetition or implementation change was needed for this data-only review. Archive SHA6773f88b…12c25c; original failure remains failed qualification, not a quality/economic negative. [E129][E132][E134][E135]

**Next user action:** Mac upload using the corrected helper and wait for UPLOAD VERIFIED; Torch checksum/extract/submit exactly once via E136. Its one additional prospective allocation retains the original4CPU/32GiB/two-hour,6,600s/40,230-attempt limits, quality stop and all gates. Original allowance stays consumed. Native exact correctness/catalog/plans must pass before valid quality; only quality pass unlocks two temporal blocks/new A/A/economics. Collect/download and independently verify any corrected return before deciding the next step. No job has been submitted by this review. [E128][E136]

### 2.19 Corrected B2b deadline stop during second temporal block (historical pre-return)

**Pre-return status; independently verified findings and current action are in Section2.20.**

Corrected campaign`reviews-exact-topk-v1-catalog-fix-20261026T050859Z.jrmkwhuy`, job20949301_0, reports FAILED1:0 after1:52:22 with `RuntimeError: Work deadline exhausted`. The application enforces6,600 seconds/110minutes beginning before private restore/initialization, separately from the two-hour Slurm allocation. SSH disconnect was independent. Both original and corrected attempts remain consumed; no resubmission, deadline extension, partial resume or additional allocation follows automatically. [E128][E138][E140]

Reported operations sum to26,247 budgeted attempts:30 qualification,1,800 references,6,105 conditioning,6,104 warmups and12,208 retained executions. Last complete-case progress shows block1/cases163 and26,246 attempts. Counts are consistent with6,104 completed slots (4,800 in block0 plus1,304 in block1),12,208/19,200 retained observations (63.58%), and one later conditioning attempt; actual terminal execution/journal coverage needs returned raw verification. [E138][E140]

Entering warm measurement requires initial catalog/native/exact semantic qualification and a complete passing quality screen in unchanged source. Thus the reported phase indicates these prefix gates passed in the running harness, not independently recomputed acceptance. Final graph/module/catalog/settings checks and complete journals/metadata/locks were not reached. Protected sources unchanged/providers0 are user-reported; cleanup is not yet verified. [E138][E140]

This is an incomplete budget-stop run, not a valid quality/economic negative and not a full A/A or speedup result. The prescribed two-block matrix/all16 A/A intervals cannot be replaced by a completed first block, an available subset or retrospectively extended runtime. Saved prefix quality may be separately verifiable and partial timing may support descriptive cost diagnosis only. Collect/download existing failed raw via E139, then verify identities/cleanup, prefix quality and actual coverage/phase costs before proposing any separately frozen revision. No new source/package change or experiment now. [E139][E140]

### 2.20 Corrected partial return verified: quality pass, very slow exact path, no repeat

All30 regular archive members match checksum/extracted bytes (2,219,553 bytes; SHA6856a060…02ceaf). Submission/job20949301_0, recovery prerequisite for original20941363, terminal FAILED1:0 budget accounting, cleanup and captured protected integrity pass.14 readers/five live, all readers closed/private DB stopped,20 protected groups/1,622 entries identical. Initial prepared graph/data, module/image/profile/registry and snapshot/origin/effective bindings match.1,352 prior inputs/artifacts remain unchanged. [E142][E143]

The **complete qualification/quality prefix is independently verified** using unchanged sealed functions.30 qualification searches pass output/plan/settings/error-isolation checks. All600 fresh references match pinned truth/native640 and independently rescore; the frozen vector-group bootstrap reproduces the saved quality exactly within original tolerance. Exact10 recall is100% in all contexts versus native640 overall99.0333%, unfiltered99.3500%, votes3299.1500%, votes10898.6000%. Overall improvement+0.9667pp,95% interval[+0.5833,+1.4167]pp; all original floors/reserve pass. Exposed development evidence, not confirmation. [E142][E144]

Every recorded timer/search output and the exact schedule prefix validates:6,104 slots,18,312 warm execution records (12,208 retained/6,104 discarded),6,105 conditioning records and8,520 valid plan packets (12 fixture+8,508 journal). Block0 covers600 cases, block1 the first163 complete cases, plus one later conditioning call. Block0 before/after settings pass. Full LOCK/status/metadata/charges/block1 boundary files and successful final index/module audits are missing; full catalog snapshots were never saved. These omissions remain explicit. [E142][E143]

| Complete block0 descriptive context | Native640 outer mean,ms | Exact10 outer mean,ms | Ratio of arithmetic means |
| --- | ---: | ---: | ---: |
| Overall |9.552 |535.980 |56.11x |
| Unfiltered |9.548 |824.633 |86.37x |
| votes32 |9.544 |510.992 |53.54x |
| votes108 |9.564 |272.315 |28.47x |

The separate163-case block1 prefix averages9.829ms versus531.966ms (54.12x); exact is faster in0/763 complete case/block instances. This is descriptive existing-data evidence, not a full economic confidence-gate verdict or proof about other implementations/workloads. [E142][E144]

The observed cost is dominated by exact execution:3,850.07s of4,060.34s in block0 (94.82%) and4,891.11s of5,222.30s of the observed warm window (93.66%). All recorded plan packets cost only19.76s total (14.04s warm). SQL timer means closely track the exact outer query cost; wrapper/observer overhead cannot explain the roughly526ms first-block disadvantage. No CPU/IO/JIT/actual-worker causal attribution is established. Full truth and fresh native/exact references cost587.43/178.08/322.08s separately; restore charge is missing. [E142][E144]

**A/A and final scientific gates remain unassessed:** the required complete two-block matrix is absent. Only descriptive replica point gaps are reported; block0 exact overall B-minus-A+0.4194ms and per-filter points−1.4594 to+1.5360ms do not establish calibrated controls. No post-hoc subset confidence intervals, bootstrap performance tests, relaxed gate or complete-run report were substituted. [E142][E144]

**Disposition:** close the finite B2b campaign as incomplete_budget_exhausted/closed_inconclusive; retain original execution and both consumed allowances. Do not adopt, extend, resume or rerun exact10. Quality pass plus the large unfavorable descriptive gap supports declining more spending; it is not retroactively `closed_negative_economics` under the complete sealed protocol. Recommend B2c/NEXT-ANN-ALTERNATIVES-01: read-only indexed/filter-aware ANN compatibility/mechanism triage, choosing at most one justified prospective design with actual phase-cost estimates and a predeclared cost-sanity/futility stage before any new allocation. No user commands now. [E144][S26][S35][S36]

### 2.21 Completed B2c alternative review and prospective B2d scope

B2c/NEXT-ANN-ALTERNATIVES-01 is complete. **Scoped design GO:** one new cosine HNSW WHERE total_votes>=108 (49,498 eligible rows), keeping the full table/global IDs, original full graph and module. The public inspector rejects partial indexes; the narrower C binding has no explicit predicate rejection but does not force plan choice. Use a separate strict experimental adapter and actual fresh/cached-plan qualification; this is source feasibility, not qualified public support. [E147][E148]

Baseline and candidate need separate private copies so adding the index cannot change the baseline planner's choice. Candidate-only SQL retains the threshold parameter and adds a redundant literal >=108 after strict actual-AST/k10 validation; preserve auto-preparation and settings. This planning-time implication design remains subject to actual native/cache checks. ACORN/native predicate traversal, shadow tables, partitioning, scalar indexes and a second partial index are deferred. [E147][S35][S37][S40]

The frozen B2d contract covers only200 exposed >=108 cases:10 qualification,192 preview,600 quality and16,000 formal searches =16,802 maximum. A24-vector large-loss futility screen precedes full quality. Both native-relative quality gates, four one-context A/A intervals, conservative99.375th-percentile economic bounds, both block directions and final full integrity remain mandatory. Proposed one3h4CPU32GiB allocation,10,200s work deadline and stage/storage/SQL caps are design ceilings, not allocated resources. [E150]

No experiment, test, bootstrap, code/package change or native access occurred;349 source and1,364 prior files preserve their hashes. **Next: B2d isolated implementation/local checks/seal; user commands only after readiness.** Original execution and B2b incomplete/no-repeat status remain unchanged. [E149][E151][E152]

### 2.22 B2d isolated implementation checked and sealed

The user's next-step authorization is complete locally. New experimental code keeps the public nonpartial inspector, adopted execution, frozen runtime and previous experiments unchanged. Two private copies separate the original full graph from one additional >=108 partial graph; strict actual-AST ownership, target catalog, original/fresh/cache plans and all before/after identities remain native qualification gates.55 source and55 sealed mock checks pass, including full acquisition/replay, both early stops, A/A/recall protection, secondary/outer timers, failed collection, unknown dispatch and final metadata identity. [E153][E154][E155][E156]

Seal:161 files/162 regular archive members; every member matches local bytes. The final manifest is `f11159e1b66d9e9cb0259bec45e136eac9bff7a322233a9ac00a4153267c09a4`; archive `b2f7730a24a98ea2a3d29474298064a2500eab8e61911c83130bf705bc97755c`. The frozen runtime anchor is unchanged. Internal pre-dispatch review seal1 is preserved and marked superseded after removing unused inherited metadata; it was never uploaded/submitted. Scientific design/gates unchanged. [E157][E159]

**Historical v1.26 handoff:** [original upload/submission commands][E158], superseded for current use by the quota compatibility repair below. One proposed3h4CPU32GiB allocation,10,200s work allowance, maximum16,802 search attempts; valid cost/quality stops at202/802. Login/compute quota/free-space and native memory/catalog/plan checks fail closed. No native result or new evaluation entitlement follows from local readiness. [E153][E158][S44]

### 2.23 Quota preflight failure and separate compatible seal

The user attempted submission; bundle verification passed, but site myquota parsing failed before reservation, binding, test-only or actual Slurm dispatch. No allocation was consumed by this attempt. The readable display uses lowercase30k, unsupported by the original parser. Literal replay establishes that unit defect; the remote unmatched-row trace cannot be fully reproduced from pasted text without original control bytes. The new parser also strips standard SGR colours, while unknown/malformed/duplicate/missing quota rows still fail closed. [E161][E166]

The separate quota-fix source and seal pass61 source/61 sealed synthetic checks. Exact scientific configuration/runtime/inputs/schedule/measurement/controller/replay/gates remain unchanged; only resource-format parsing, packaging paths, tests and documentation differ. Original packages/source/receipts and1,733 pinned prior files remain unchanged. The repaired package deliberately shares the original reservation: no extra allocation entitlement. Current quotas, free bytes/inodes and prepared footprint must still pass before dispatch and on the compute host. [E162][E163][E164]

**Historical v1.27 handoff, superseded by the failed-job collection below:** new Mac upload/checksum → guarded once-only Torch submission with original binding/reservation absent → resource/restore/build/native qualification → preview → quality → conditional full A/A/economics → final integrity/collect/download → independent replay. One original3h4CPU32GiB/16,802-search ceiling, unchanged gates, no automatic retry or native result from local mocks. Use only the repair commands for new upload/status/collect/download. [E165]

### 2.24 User-reported B2d initial environment failure; collect evidence

Quota preflight now passed and actual job21043219_0 was submitted for campaign `reviews-partial-ann-v1-20261027T000432Z.9haq3pyt`. The earlier21043215 message is the controller's sbatch test-only scheduling estimate, not the dispatched experiment. The actual job is reported FAILED1:0 after4minutes. This allocation is consumed; retain the shared reservation. [E167][E170]

Runtime reports0 backend searches,0 readers,1 observer/5 startup SQL executes and failure `JIT/parallel/work_mem/cache tuning is outside this treatment`. Final integrity is false; no partial build/quality/timing stage was reached according to source ordering. Host protected sources are reported unchanged, but archive/catalog/cleanup/protected identity have not been independently verified. No performance result follows. [E167][E169]

Source identifies an administrator-versus-reader scope issue to investigate: the first administrator catalog passes through the inherited reader environment guard before any reader is configured. The guard requires work_mem16384, jit on, auto plan cache and parallel-per-gather2; mocks supply those values to all catalogs. The failure message does not identify the actual differing value. The later admin memory check also assumes16MiB. Preserve the guard and inspect saved raw before proposing an explicit separately frozen admin/reader/resource correction; do not change GUCs or waive validation from this message alone. [E169]

**Historical v1.28 collection path, now complete:** user collect terminal failed campaign on Torch → Mac download/checksum/failed-raw preservation → Codex independent archive/submission/package/scheduler/catalog/accounting/cleanup/protected verification → decide whether a separate scoped correction is justified → only then prospective local/native gates if separately authorized. No automatic repeat, reset, resume or performance verdict. Use only collection commands now. [E168][E170]

### 2.25 Failed B2d verified; separate settings correction ready

Trusted data-only verification passes21 archive members/163,151 bytes, checksum60ae88ccf64c9f23e15af96d304c1b63f326f8ee52f01a2374ac02a289a20a82; exact submission/package/job/terminal failure,8 incomplete-lock hashes, zero-search/reader charges,6 SQL records and successful cleanup/shutdown.23 protected groups/1,672 entries match before/after. Final scientific integrity remains false, quality/A/A/economics unassessed and original allowance consumed. [E171][E172]

The exact sole guarded difference is torch_owner work_mem4096 (4MiB) versus the reader requirement16384 (16MiB). JIT/cache/parallel-per-gather match. Original failure reproduces; counterfactual classification with only work_mem replaced passes structural checks without changing raw or granting acceptance. Admin catalog was inspected before reader configuration; mocks used reader values for all sessions. Real quota stdout confirms ANSI colours/lowercase30k were correctly handled by the prior repair. [E171][E175]

The prospective correction freezes strict role/phase separation: all16 captured admin fields including4MiB, unchanged reader16MiB and full existing admission audits. The memory proof keeps reader16MiB as its upper bound and the same14.25GiB conservative total inside32GiB. Build memory/workers remain64MiB/0, now inspected/replayed as numeric bytes/int. No query-setting GUC is changed to manufacture a pass. Wrong roles, settings/units, rehashed proof drift or old failed-evidence changes fail closed. [E173][E174]

75 source/75 sealed checks pass;169-file seal/170-member archive and source/frozen/member/preservation proofs pass. Scientific config differs only in name/version/correction/provenance metadata; measurement/interface/scoring/schedule/query-settings and gates are unchanged. One new separately named3h4CPU32GiB correction allowance is proposed; old package/raw/archive/binding/spent reservation must verify and are never reset. No new native job/DB/index experiment here. [E176][E177][E179]

**Historical v1.29 handoff, now executed:** E178 new Mac upload/checksum → one distinct corrected Torch submit → failed-evidence/resource/admin/restore/build checks → actual reader/module/catalog/fresh/cached-plan conformance → preview → quality → conditional complete A/A/economics/final integrity → collect/download → trusted replay. Same202/802/16,802 search branches, no automatic retry/resume/adoption; original retained. [E178][E179]

### 2.26 Corrected B2d reported complete; raw collection prefix recovery

Job21048213_0 is reported COMPLETED0:0/17:17, campaign reviews-partial-ann-v1-20261027T005510Z.q6rgxprs. Status reports16,802 searches, two temporal blocks, quality_pass true, final integrity true,8 readers/six live, no provider/fits/protected queries, and host protected sources unchanged. This is a user status report, not independently verified raw or an A/A/performance verdict. [E180][E183]

The controller hardcodes the old campaign prefix, while corrected common/reporter/transfer require the new prefix. Existing mocks derived names from the new constant and missed this controller path. Ordinary collect/report/download therefore cannot finish. Preserve the original label, raw, code and seal; no scientific change or another allocation is warranted. [E182]

A separate exact-campaign data-only collector verifies manifestc77efca4…89b4, binding/dispatch/job21048213, completed lock hashes/status/cleanup/protection and actual terminal scheduler evidence, then archives. Safe download/extraction checks hashes and identities without executing returned code or changing gates. Eight synthetic checks cover successful collection/ingest, corrupt locks, wrong identity, unknown/running scheduler, partial archives and traversal; all pass.2,166 prior immutable files preserved; no new experiment. [E182][E183]

**Historical v1.30 collection path, now complete:** upload only small recovery helper → Torch raw collection → Mac new-helper download/checksum/extraction → full independent archive/provenance verification and narrowly proven exact-name reconciliation → trusted scientific A/A/economic replay → roadmap branch decision. No original collect/download helper, campaign rename, scientific edit or resubmission. Exact current commands E181. [E180][E181]

### 2.27 B2d complete raw verified; quality passes and controls defeat speed qualification

Archive37 files/1,630,143 bytes, SHA2560bb845dea4a0f1668a8dc46ebe93ba25f6c0ead65a629606de628bf4219ae055, exact job21048213_0/package/submission/dispatch, all raw locks and2,219 prior hashes verify. Native module/data/original+partial graphs, full16,802 attempts/6,400 retained/3,200 slots/5,700 plan packets, charges/settings/cache/quality outputs/final integrity/cleanup and24 protected groups/1,678 entries pass. The source-proven name exception is limited to this exact campaign/package/job, preserves labels/raw/seal, and changes no scientific rule. Two fresh sealed replays agree exactly; acquired quality/preview parity passes. No remote performance JSON was generated by raw collection, so no remote/local economic-parity claim. [E184][E187][E188][E189]

Quality: native98.60%, partial99.85%; delta+1.25pp,95% interval[+0.65,+1.90]pp, both floors/reserve pass. Observed warm outer mean7.304522→6.030911ms,−1.273612ms/17.4359% lower arithmetic mean. Conservative upper gap−1.080889ms and upper ratio0.876162 meet original nominal economic endpoints; both blocks favor partial. These endpoints do not override controls. [E185][E186]

All four A/A intervals fail. Native gap95%[−0.256442,+0.051242]ms and log[−0.037287,−0.006782]; partial[−1.248541,−1.074538]ms and[−0.192124,−0.167537]. Required bounds remain±.10ms/±log1.02. Identical partial replicas differ1.163475ms (17.5947%), close to the1.273612ms treatment contrast. Native A/A changes sign between blocks; partial bias persists. Exact within-round positions/counts balance, and93.67% of partial A/A gap appears in SQL timing. Cause unresolved; no wrapper-only or simple label-count explanation is established. [E185][E186][E188]

**Disposition:** complete finite B2d as measurement_inconclusive, retain original and both consumed allowances. Partial graph193.35MiB/additional20.02% original graph storage; build84.15s. Do not qualify speed, subtract control bias, choose faster replica, compute credible amortization, fit router or adopt. Proposed B2e/NEXT-PARTIAL-CONTROLS-01 is a read-only source/saved-evidence replica/session audit before a separately frozen calibration decision, not an authorized repeat. No user commands. [E186][E190]

### 2.28 Completed B2e replica/session timing audit

All saved traces and source were audited without new execution. Within each cell a/b are distinct persistent connections to the same private server and graph; logical labels never cross connections. All800 paired scientific plan packets per cell match exactly, as do actual boundary GUCs and admission bindings. All5,690 cached entries record generic_plans=0; a generic/custom split is unsupported. Observer EXPLAIN EXECUTE activity explains planning-counter increments and is symmetric in count, but fixed inspection order can perturb state. [E191][E192][S37][S39][S45]

One discarded on-reader warmup does not establish stable timing. Retained2 minus retained1 outer mean is−1.473226/−1.328568ms for native-a/b and−.952779/−.312325ms for partial-a/b. Partial A/A remains−.843248ms even at retained2; b is faster for193/200 query averages and all eight block/temporal-quarter summaries. These are descriptive, with all rows retained and no new gates. Last-conditioned cell and within-round position are perfectly aliased. Physical backend PIDs, CPU placement/migrations and per-search CPU/wait/cache attribution are absent. The SQL-labelled timer includes protocol/fetch/decode, so93.67% inside that timer is not a pure server-time diagnosis. [E191][E192]

**GB2e: GO to one separately frozen instrumented, qualification-first A/A calibration design; no causal fix, implementation or run qualification.** Freeze fixed-graph restoration/telemetry feasibility, reader/backend/epoch identities, independently balanced conditioning/observer order and a fully charged on-reader warmup regime before code. Proposed outer design envelope: at most one3h4CPU32GiB calibration allocation/16,802 total search attempts, zero authorized now; derive exact SQL/admission/stage caps and analysis before launch. Unchanged margins and physical-backend diagnostics must prevent bias cancellation by relabeling. B2d remains inconclusive; original retained. [E191][E194]

### 2.29 B2f bounded instrumented A/A design frozen

Protocol partial-calibration.v1/NEXT-PARTIAL-CALIBRATION-01 freezes exact B2d full/partial graph bytes, complete data/module/image/query identities,200 exposed cases and unchanged margins. Copy only verified stopped whole clusters into new writable workspaces; no graph transplant, rebuild, reindex or old-source startup. Retained source path/three hashes/space must first be inventoried by the user; current availability is not proven. [E195][E196]

The prospective study uses two fresh formal connection epochs with reversed creation order, crossed metadata labels and physical PID/starttime/server identities. Both replicas and conditioner for a cell share a fixed allocated CPU; cells swap CPUs between epochs, with four distinct allocated physical cores required. Each burst has two main conditioners, four fixed discarded on-reader warmups and three retained repeats. Last conditioning cell and reader order are independently balanced; each physical reader has100 a/100 b labels. Bulk plans bound observer-free primary windows; an eight-vector paired observer diagnostic is descriptive only. No component-specific causal fix is assumed. [E195][E197]

Full count:10 conformance+600 fresh quality+80 priming+14,400 primary+1,152 diagnostic=16,242 searches;560 outer-envelope attempts remain unspendable.10 reader admissions/max6 live,4,200 plan packets,13,500 observer/1,000 startup/4,040 truth-helper SQL caps,5,500 telemetry bundles/44,000 proc reads and full finite time/storage/memory rules are frozen. Both original A/A margins apply to physical pairs per epoch, half-epoch protections and retained-adjacency stability:56 timing intervals must all pass. Future economic thresholds stay unchanged and are not evaluated by this calibration. [E196][E198]

**F0-B2f: design freeze pass only.** Runtime graph/core/mandatory telemetry feasibility, later local implementation/seal and one separately authorized native job remain pending. No code, tests, experiment or remote call occurred;2,241 prior inputs preserved. Even a scoped calibration pass permits only a later treatment-design review, never retrospective B2d qualification. [E199][E200]

### 2.30 User source inventory clears preliminary B2f prerequisite

On October27 the user supplied the exact E195§12 read-only output from torch-login-a-0. Both retained pgdata paths and PG_VERSION/pg_control files are listed; the script reached checksums/df/myquota without a PID-file stop. Both original full graph hashes match dbc14b09…e23b393 and the partial graph matches b0300f40…8606700 exactly. This verifies comparison of the supplied report with the frozen contract, not an independent remote file read or complete cluster qualification. [E201][E202]

Conservative reported quota lower bounds: home26,340,700,000 bytes/14,567 files, above3GiB/10,000; scratch4,778,000,000,000 bytes/4,846,599 files. Reported filesystem space is positive. Actual source footprints/file counts and filesystem inode availability remain unmeasured, so the complete scratch gate must still run later. Current graph rebuild/replacement is unjustified; keep design/contract/order unchanged. [E202]

**Source-prerequisite disposition: preliminary_user_reported_inventory_pass.** No more user Torch commands now. Next is separately requested isolated implementation/local correctness/preservation/seal, before a separate native handoff. Actual pg_controldata clean state, safe whole-cluster copies, full source/data/catalog/module/graph proof and allocation core/mandatory telemetry gates remain pending.2,249 prior inputs and every frozen design artifact remain unchanged; no code or experimental activity. B2d stays inconclusive/original retained. [E203][E204]

### 2.31 B2f implementation checked and sealed; one-job handoff ready

The separately requested implementation preserves the prospective design/contract/order byte-for-byte and all prior source/raw/seals. New `torch-partial-calibration-v1` provides guarded independent whole-cluster copies, inherited native/query/result semantics, explicit physical PID/epoch/core identities and telemetry, the exact16,242-search/4,200-plan schedule, raw-only terminal collection and trusted independent local analysis. Unknown dispatches cannot retry; source/graph/required-observation/resource/cleanup failure cannot qualify. [E205][E206]

Source and sealed-package suites each pass78 synthetic correctness checks, including complete mocked acquisition/reconstruction, quality stop, physical/half/stability rejection, unsafe archive/copy/ownership, PID/namespace/affinity and counter drift, missing observations, generic plans and finite budgets. Lint/format/AST/shell checks, complete archive-member byte parity and2,255-file preservation pass. These establish implementation correctness, not native availability or performance. No database process, native ANN experiment, Torch/SSH/provider call, fit or protected query was run by Codex. [E206][E208]

**L0-B2f: implementation readiness pass only.** The next user action is Mac upload, then one Torch submit using E207, followed by status/terminal collect/download. One3h4CPU32GiB allocation; all native N0 gates run before measurement. Both full/partial graphs, policies and all56 unchanged-margin timing checks remain fixed. A scoped all-pass permits only later treatment-design review; no speedup/adoption or retrospective B2d qualification. [E205][E207]

### 2.32 B2f original launch failed before Python; isolated correction prepared

Original campaign reviews-partial-calibration-v1-20261027T155119Z.6rd0lmkp/job21111616_0 records FAILED/2:0 after4s on cs606. The six-file archive checksum1385637e…72fb543, all extracted bytes, original manifest41b4e478…68ae42a and submission/scheduler/log identities verify. The log reports execve(): python3: No such file or directory; no host-wrapper/runtime files exist. Python never launched, zero native searches ran, and no quality/A/A/performance or native-qualification evidence exists. The allocation is spent; full post-run source proofs were never reached. [E209]

The launcher combined sbatch --export=NONE with bare python3 in srun. The failed executable lookup is observed; the exact failed PATH was not captured. Slurm documents absolute executables under restricted export and explicit ALL step export. The separate partial-calibration.v1.launch-fix revision passes a resolved absolute interpreter from submission to the actual batch script, verifies its compute-node presence and actual host identity, and sets SLURM_EXPORT_ENV=ALL plus srun --export=ALL. Native --cleanenv/pinned Python/module and all scientific code/schedule/margins remain unchanged. Old package/raw/binding/reservation must verify and are never reset. [E210][E211]

88/88 source and88/88 sealed synthetic checks pass, including execution of the actual shell launcher with a synthetic srun, restricted inherited export, no python3 on PATH, argument round trips and early interpreter rejection. Full mocked acquisition/reconstruction remains passing. Archive-member parity, shell/static checks and all2,500 prior/captured-failure pins pass. These do not prove compute-node interpreter availability or native performance. [E211][E213]

**Launcher repair readiness: pass; N0–N4 still pending.** E212 labels the proposed corrected handoff as one additional3h4CPU32GiB job/16,242-search ceiling, separately named/reserved. The original4s allocation stays consumed. Preparation/upload submits nothing; user execution of that new submit command requests the additional job. No automatic retry, graph replacement, scientific extension or later treatment experiment follows. [E210][E212]

### 2.33 B2f restored identity-file omission verified; actual-backend correction checked

Launcher-corrected campaign reviews-partial-calibration-v1-launch-fix-20261027T185901Z.98dd224c/job21129331_0 failed at8m34s, before any reader admission/search/plan. Its32-file archive SHA4619d2c9…26cd2dff, member bytes, failed raw lock and submission/seal/scheduler identities verify. Both retained source cells contain the pinned957-byte baseline identity file (SHA28a053d1…9e13d55), but clone copied only pgdata/authentication. Frozen TorchBackend.__init__ requires this sidecar before connecting. No quality/A/A/performance or full N0 qualification exists. [E214][E215]

Whole source-before/source-after inventories match across2,587 files/4,603,663,760 bytes; full copy proofs and initial catalogs match. Host protected inputs remain unchanged; cleanup reports no errors/all readers closed/servers stopped and both server logs confirm shutdown. Final measurement integrity was not qualified. Slurm MaxRSS23572496K is recorded as an observed prefix metric, without a full-run memory claim. The4s first and8m34s second allocations are both spent. [E214]

The separate partial-calibration.v1.metadata-fix rejects missing/unsafe/tampered identity metadata before copying any database files, copies the exact pinned source file privately into both new envelopes, verifies its hash and retains the original private target adapter/catalog/graph guards. Final integrity and independent raw reconstruction now check identity metadata provenance too. No identity is invented, no original-source mutation or validation bypass is introduced. Timed SQL/guards/scoring/schedule/bootstrap/margins and all per-job ceilings remain unchanged. [E215]

The previous shallow backend fake skipped construction, which explains the coverage gap. New tests reproduce the omission with the actual frozen constructor, then exercise both target constructors and the real frozen binding/snapshot/native/exact-reference/cleanup methods through all16,242 mocked calls,4,200 plans and10 admissions/max6 live. Actual-backend complete raw also passes trusted reconstruction/all56 synthetic gates.101 source+101 sealed correctness checks/static/shell/archive/preservation pass;40 synthetic database rows do not establish full-size performance/memory or native compatibility. [E216][E218]

**Historical metadata repair readiness (attempt now failed; see Section2.34): local pass only.** E217 clearly proposes one additional3h4CPU32GiB/16,242-search job, with both earlier attempts spent and protected. Preparation/upload submits nothing; executing the new submit command requests this separate allocation. All native N0–N4 remain mandatory and unqualified; no automatic repeat, scientific change or retrospective B2d qualification. [E215][E217]

### 2.34 B2f third failure verified; release quality and resource gate now block another run

Campaign reviews-partial-calibration-v1-metadata-fix-20261028T000153Z.y1p9092a/job21159802_0 failed1:0 after10m44s. Its30-member checksum/member/raw-lock/submission/package/scheduler evidence verifies. Two readers were admitted;0 searches, plan packets, providers/fits/confirmation queries occurred. Full source inventories2,587 files/4,603,663,760 bytes, whole-copy/identity/catalog/protected receipts and clean shutdown verify. Final scientific integrity and quality/A/A/performance were not reached. All three allocations remain spent. [E219]

The runtime adds field_map to the eligibility object; frozen eligibility.json has only source_ids/votes. This guarantees a hash mismatch on unchanged values. Prior tests used actual frozen backend methods but called acquisition directly and skipped the surrounding startup guard. The isolated correction hashes the unchanged pinned schema, checks the exact field mapping separately, restores the explicit frozen snapshot identity guard, and requires a startup identity proof in trusted complete-raw analysis. No data-drift verdict or validator relaxation. [E220]

New tests invoke pc_runtime.main itself through startup, both complete epochs, final verification and cleanup, with actual frozen reader methods and synthetic OS/DB/resource responses. Startup eligibility/dataset/catalog/server failures and cleanup failure are covered; the full247,286-ID/vote-only schema fixture reproduces the old defect without vectors. Existing actual-shell, protocol, identity, ownership/affinity/budget/archive and complete-replay negatives remain. Full data/process/resource proofs in this fixture are synthetic; no native compatibility, memory or performance is established. Exact final counts and preservation are in E221. [E220][E222]

Recorded MaxRSS33534232K is31.9807GiB under a32GiB request, but the observed failure is the explicit guard exception, not a recorded OOM. Slurm accounting may include filesystem cache; current site settings and full-run anonymous-memory headroom are not known. Frozen snapshot loading materializes Python vectors/NumPy and full canonical JSON identity; this is a source-based peak hypothesis only. The old14.25GiB configured estimate is not a proven whole-process bound. [E220]

**Release hold:** production packaging fails closed. No tarball, transfer helper or fourth allocation is released. Read-only Slurm accounting configuration → explicit resource feasibility decision (or separate prospective resource qualification/amendment design if unsupported) → final release review/seal/checks must precede any new handoff. Frozen limits/margins cannot be silently changed. Native N0–N4 remain mandatory afterward; no retrospective B2d/speed/adoption claim. [E220][E221]

### 2.35 B2f accounting configuration received; targeted resource qualification design justified

User-provided scontrol output reports jobacct_gather/cgroup, JobAcctGatherParams=(null), proctrack/cgroup and task/cgroup,task/affinity. Under cgroup/v2, file cache counts in Slurm RSS/MaxRSS without no_file_cache. The transcript does not establish the failed node's cgroup version, effective RAM/swap/ancestor controls, cache amount, anonymous memory or full-run reserve. Do not subtract speculative cache or infer OOM. The observed failure remains the reproduced startup schema mismatch; no OOM is recorded. [E223][E224]

The read-only configuration request is complete. R2 full-run resource feasibility remains unqualified: prior B2d completed under32GiB with the same full-size loader, but its saved scheduler record has no MaxRSS/component traces and the B2f regime differs. Recommend a prospective startup-only qualification: actual full-size loading/identity/admission, both fixed reader-creation orders (ten admissions/maxsix live), aggregate cgroup limits/peaks/components/events plus process high-water observations, final source safety/cleanup, and0 ANN/exact searches. It performs snapshot/data/admission SQL, not scientific search measurement. [E224]

Freeze all budgets/observations/reserve/workspace decision rules before any implementation/handoff. The outline proposes at most one separate4CPU32GiB/1hour allocation; none is released or automatically added. A startup-only pass cannot qualify per-search memory, quality, A/A or speed. Unsupported/inconclusive resource evidence stops the path for review. No new code/tests/experiment, cap increase or new user command in this review. [E225]

### 2.36 Startup-only qualification frozen, implemented and prepared for Torch

On user request, NEXT-STARTUP-RESOURCE-01/startup-resource.v1 was frozen before code: one additional one-hour, four-CPU, 32 GiB job, zero ANN/exact searches, one snapshot scan and four full data-verification scans, ten admissions with at most six live readers and eight SQL connections, both original creation orders and five-second observation holds. Initial/final data/catalog/graph/module/source/sidecar/cleanup proofs remain mandatory. The original B2f science and spent attempts are unchanged. [E227]

Search methods and operation reservations raise, and an exact SQL allowlist blocks distance/search/EXPLAIN/unknown SQL before the driver. The actual frozen construction/binding/snapshot and corrected identity boundary are exercised without priming or query execution. A separate bounded host sampler starts before bundle verification, covers host/container cgroup v1/v2/visible limits/aggregate peak/components/events/PID RSS through cleanup, and has explicit health/read/CPU/byte/gap/cap handling. Guest/final host locks separate live memory files safely. Trusted local reconstruction checks every zero-search/lifecycle/identity/resource condition. [E228]

The frozen resource decision is deliberately conservative: the largest recorded aggregate peak across visible finite ancestors, plus a 2 GiB reserve and 2 GiB outstanding workspace allowance, must fit the smallest observed finite limit capped at 32 GiB, with complete coverage and no positive limit/OOM delta. No cache subtraction. A completed startup can be margin-inconclusive; component/process highs remain separate. A startup-only pass does not establish full query-workload memory, quality, A/A, performance or automatic calibration release. The source and sealed package each pass 117 local tests; static checks, archive parity and 3,123 unchanged prior files are verified. Native gates are pending. [E227][E229][E231]

### 2.37 Startup-only return verified; startup succeeds but resource margin is inconclusive

User job 21171789_0 completes 0:0 in 13m28s. The 934,849-byte archive SHA256 is 312bf5c02959a1e90514f6ec556914303095eb30c2f87acd9b182010a28320e7; all 46 members equal extracted raw. Fresh trusted sealed replay matches the download-time result. Zero ANN/exact/executed requests, 200 admissions, ten readers/maxsix live, both creation orders, one snapshot/four data scans, source/copy/data/catalog/graph/module/final/cleanup/host locks verify. The startup correction now has actual scoped Torch evidence. [E232][E234][E235][E237]

The complete cgroup-v2 trace has 806 frames, 1.030291s maximum gap and verified process mapping. Actual finite job/step-user limits are 32 GiB, job peak is 32 GiB, swap limit/usage zero. Frozen peak+2 GiB reserve+2 GiB workspace=36 GiB exceeds 32 GiB by 4 GiB; startup ceiling under this rule is 28 GiB. Job max events rise 592, all in snapshot_load; OOM/OOM-kill/group-OOM deltas remain zero. The verdict is startup_complete_resource_margin_inconclusive, not startup failure or workload qualification. Capped peak does not identify unconstrained demand or establish that 4 GiB reduction/a larger request would suffice. [E232][E236]

Near the peak, sampled current is 31.997318 GiB, with about 14.875885 GiB anonymous, 17.056358 GiB file and 0.064476 GiB kernel components read sequentially; runtime RSS HWM is 15.030392 GiB. Components/process highs are separate, not additive or subtracted. Frozen source materializes Python vector rows, a NumPy matrix and full canonical JSON text/bytes; these are candidate mechanisms in the observed phase, not causal allocation measurements. Next is NEXT-STARTUP-MEMORY-01 read-only representation/lifetime/identity/consumer audit and prospective correction design. Full calibration remains held; no code change, new experiment, resource increase or user command is released. [E232][E236]

### 2.38 Snapshot memory compatibility audit complete; narrow identity-streaming design frozen

M0 reviews the actual frozen producer plus runner/inheritance, 116 source files and 137 static references. Ten reader admissions share one snapshot; sorting copies outer references, not every numeric value. Python rows, NumPy matrix and maps/metadata remain retained through finalization. Original rows have actual validator/ID/eligibility, sample, export, workload and audit consumers; float32 reconstruction/discarding would require a broader semantic design. Default snapshot cursor stores results on the client, while all four verification scans already use named server cursors. [E239][E243]

Existing source/trace establishes 6.485254s snapshot SQL within the combined 117.843556s load/constructor/identity phase; runtime RSS remains about 10.61 GiB in both holds. The dense float32 matrix payload is only 0.707491 GiB, not total process memory. No individual allocation sizes, remedy savings or guarantee of the unchanged 28 GiB/no-event startup gate is inferred. [E244]

M1 freezes per-row identity hashing using the unchanged canonical encoder and exact fields/rows framing. Original source/constructor/rows/matrix/cursor/validation/identity remain; only a recorded module-local digest binding is temporarily scoped to the initial acquisition and restored in finally. Component/buffer/byte/count caps, exact byte/hash/error/consumer equivalence, actual entry-point/signal/restoration/cleanup coverage and a later zero-search native gate are specified before code. Generic token iteration, server-cursor change and compact storage are deferred; no global store hash replacement or cache/cap remedy. [E239][E240][E241]

Design feasibility is GO, not local or native readiness. Next is M2 separately requested isolated implementation/local qualification for prospective startup-resource.stream.v1. A later M3 job remains unimplemented/unreleased and needs readiness plus its own authorization; full calibration stays held. No code/test/experiment/remote/native action occurred in M0/M1, and 3,456 earlier inputs remain unchanged. [E242][E245]

### 2.39 Identity-streaming correction implemented; local readiness passes, resource job prepared

M2 implements the exact M1 remedy in a separate startup-resource.stream.v1 harness. Original fields and one original row at a time pass through the unchanged canonical encoder; exact root framing and a bounded 64 KiB byte coalescer feed SHA256. The original Snapshot source/constructor, rows, NumPy values, cursor/SQL/transaction, validators and all later identity checks stay unchanged. Only the snapshot module's digest binding is temporarily scoped to the single initial construction, then restored in finally before validation/publication/admission. Unexpected/concurrent/nested/missing/repeated invocations fail closed. [E240][E246][E248]

Eight literal preflight cases check actual-container original encoder parity/provenance before copy/loading, within the frozen 1 MiB/5 CPU-second/deadline limits. Native construction must reproduce the exact existing snapshot identity with one invocation and bounded component/stream accounting. Small summaries plus distinct encoding phase events are required by trusted independent reconstruction alongside all original resource/lifecycle/integrity proofs. No vector payload or full canonical document is retained by the new hash helper. [E246][E247]

The final source and sealed suites each pass 155 tests, including the actual frozen constructor and acquisition/finalization/cleanup control flow, exact byte/hash/float/consumer checks, a handled POSIX signal, error/deadline/BaseException/restoration cases, trusted complete synthetic replay and semantic tamper rejection. Source/test origins and unchanged bytes during each suite are verified. Initial local fixture/import/wrapper failures and their corrections are preserved. Static checks pass; all 346 manifest files and 347 regular archive members match, including unchanged science/helper/vendor/native bytes and 116 reviewed source pins. All 3,468 prior inputs remain unchanged. Complete native-looking fixture proofs are synthetic; these checks establish local compatibility, not full-size CPU/memory/quality/performance. [E247][E250][E251]

M3 is now a concrete once-only user handoff via E249: one hour, four CPUs, 32 GiB; zero ANN/exact searches, one snapshot/four data scans, ten admissions/maxsix, both original orders and unchanged observer/sampler/deadline/cleanup budgets. Peak+2 GiB reserve+2 GiB workspace must fit the smallest observed finite limit capped at 32 GiB, with complete coverage and no prohibited max/OOM event delta. No cache subtraction, cap/margin change, automatic retry or broader correction. Codex submits no job. A failed/inconclusive return returns to review; even a resource pass needs M4 query-workload memory and full B2f release review. [E246][E247][E249]

### 2.40 Identity-stream resource return verified; native identity passes, margin remains inconclusive

User job 21224521_0 completes0:0 in 11m55s. The829,195-byte archive SHA256 is63ff9b4800faab0a0ece6955ccabfb9c512548a35909cbca0e9b175a73ab3fef; all 48 regular members match raw, the 346-file seal is intact, and fresh trusted reconstruction exactly matches preserved download analysis. Zero searches/executed requests,200 admissions, ten readers/maxsix, both epochs, one snapshot/four data scans,171 startup/56 observer SQL, final source/data/catalog/graph/module integrity and cleanup verify. All 3,947 preserved inputs, including earlier3,468 pins, remain unchanged. [E252][E253][E254][E257]

Actual CPython3.12.15 preflight passes; original snapshot identity54282be380f20bfab05a44e6260e116435aecf5a289a258ae8164a23c187b303 is reproduced for 247,286 rows and 247,287 original-canonical component calls. The2,374,063,027 bytes are hashed in36,226 updates, with 64 KiB maximum pending bytes,9,690-byte maximum row, exactly one invocation and restored binding. Encoding takes61.463s inside the99.927s combined snapshot stage; unchanged600s stage cap passes. This establishes scoped native compatibility, not total-memory qualification. [E255][E256]

Runtime-process RSS high-water is descriptively15.030→11.323 GiB (−3.707 GiB/24.66%), consistent with removing transient encoding buffers. Separate single jobs do not identify an exact causal saving or search-speed benefit. Governing job peak remains 32 GiB at 32 GiB limit; peak+2+2=36 GiB exceeds the cap by4 GiB. Job max events increase259; OOM/kill deltas remain zero. Frozen verdict remains startup_complete_resource_margin_inconclusive; lower process RSS/event count does not rescue the unchanged28 GiB/no-event gate. [E252][E256][E257]

Conservative counter-read brackets attribute114 events wholly before hashing,76 across the load/stream boundary,68 across second-hold/finalization boundary and one wholly in finalization. No later stream-interior increments are observed. Sample labels alone must not assign either boundary delta wholly to one phase. Reader holds still charge about31.306 GiB at job level, with runtime RSS about10.602 GiB and substantial file charge. Components are sequential samples, not additive allocation identities or a cache-subtraction allowance. Hashing is not the sole remaining pressure source. [E256][E258]

Close this second resource job, preserving all three failed calibration attempts and both completed resource jobs as spent. Next is read-only NEXT-STARTUP-MEMORY-02: audit snapshot client-buffer/decoded-row/matrix and verification-I/O lifetimes/constraints from the two existing traces and pinned source, then issue a separate remedy/design GO/no-GO. No cursor/cache/storage remedy is preapproved, and no further code or measurement/job is released. Full B2f remains held; original execution retained/B1c deferred. [E252][E253]

### 2.41 Loading/retention/verification audit complete; targeted attribution design recommended

W0–W2 inspect the actual frozen producer/constructor/runtime/reader/verification/integrity chain and both existing returns. All 246 source/recipe pins, including 116 prior consumer pins, and 3,961 previous/source/release/raw/analysis inputs remain unchanged. No implementation, correctness suite, new measurements or native/remote job. Snapshot loading is client-result buffered, all decoded original rows precede construction, and rows/matrix/maps remain retained. Ten readers share one snapshot. Factory/reader close does not clear the factory/backend snapshot roots, so final data/graph/source checks overlap retained state. [E259][E260][E261]

Verification already uses a named server cursor plus 512-record Arrow batches without read threads. Its four full transaction brackets total 370.580 seconds originally and 333.775 seconds in the streaming run (55.28%/ 56.60% of runtime); corresponding execute intervals sum only 0.033684/0.034982 seconds. Those brackets include iteration/fetch/transfer/decode/bit comparison, not physical I/O alone or exact whole-function time. One max event is strictly inside the first final native verification transaction; 68 cross its initial phase boundary. Source/trace does not identify Arrow-pool, allocator or per-file charge causes. [E262]

The 171 startup + 56 observer counts mean 227 charged API-level statement calls. Raw named-cursor iteration and transaction handling bypass Trace.call; they generate internal commands outside that counter/API allowlist. Pinned Psycopg 3.3.6 defaults imply 2,473 fetches/pass or 9,892 for four passes under unchanged defaults, excluding other driver activity; this is a source calculation, not a measured wire count. Preserve old charge semantics and add a separate prospective finite driver-command ledger before any future handoff. This does not change the already inconclusive memory verdict or imply search SQL. [E263][E264]

No-go for a blind cursor-only, smaller-batch or close/GC-only correction: these do not establish a remedy for the retained hold/final-verification overlap and unchanged 28 GiB/no-event gate. Compact exact-value storage needs a broader consumer contract; skip-check/cache-eviction/cap/margin shortcuts are not selected. GO only to NEXT-STARTUP-ATTRIBUTION-01 A0 design freeze: bounded existing-path lifetime/I/O checkpoints, API-versus-driver/fetch/row/file-role ledgers, allocator/cgroup observations and explicit overhead/interpretability gates, with zero searches/extra full scans. No experiment or allocation is released; full calibration held. [E259][E260]

### 2.42 A0 zero-search diagnostic design frozen; implementation/readiness remains unassessed

The prospective startup-attribution.v1 contract freezes 102 required checkpoints/max128 across host proofs/copy, original client-result receipt, decoded rows/cursor close, matrix-before/ready/finite/norm/metadata, existing identity, both reader epochs and each original final verification/graph/source/stop proof. Original producer/constructor source and code objects remain; local CPython3.12 LINE monitoring targets only those two objects, with512 callback cap, per-location DISABLE, no global/per-row tracing/restart or replacement code. Current-cursor close supplies the pre/post close seam. Monitoring events/callbacks clear before tool4 is freed; snapshot publication requires restoration. Actual image/tool/frame/private-hook compatibility is a later readiness gate, not assumed here. [E265][E267][E269]

Nine pinned driver-hook roles cover normal/prepared API execution, internal commands/deallocation, declaration/description/fetch and snapshot cursor close. Original API caps remain500 startup/100 observer/0 truth-helper. Completed acquisition requires four exact247,286-row verification passes:2,473 fetches/pass at100, final86,9,892 total/989,144 rows; four BEGIN/COMMIT/CLOSE/portal descriptions, zero pending/unknown operations. Prepared/protocol work is separately bounded; family ceiling sum12,336 fits13,000 combined dispatch/request envelope, including64 reserved cleanup operations. This is observed Python-driver accounting, not packets/all wire frames. No extra SQL, scans or fetches are introduced. [E266][E268]

One future job remains a proposed maximum1h4CPU32GiB with original one snapshot/four data scans,200 admission-only requests, ten readers/maxsix, two servers/eight SQL connections and both fixed holds/orders. Preserve original deadlines/600s cleanup and margin/no-event rule; clamp stage/supervisor waits to remaining global wall/reserves rather than adding ceilings. Added telemetry is capped15 CPU/30 observer-wall seconds,64 MiB/8,192 read-stat operations,16 MiB raw; combined sampler+diagnostic stays within60 CPU seconds/512 MiB/500,000 reads. All costs stay charged. No forced GC, cache/pool release or early snapshot disposal. [E265][E266]

A3 may report informative only when all semantic/accounting/health/cleanup proofs pass and a newly separated prespecified cursor/constructor/pool/file-role bracket meets the256 MiB descriptive threshold and consistency conditions. Reconfirming shared retention/capped peak or reconciling fetch counts alone is insufficient. Complete but nondiscriminating evidence closes unresolved; capability/missing-proof/cap/cleanup failure closes invalid/incomplete. Resource margin is separate and cannot release full calibration. A0 has no implementation/tests/runtime probes/native allocation;3,974 inputs/246 source pins preserved. [E265][E269][E270]

### 2.43 A2 release review holds dispatch on image-reference compatibility

A1's strict driver install compares exact runtime provenance, including the full Python version. The unchanged local reference records3.12.7, while the saved image config and Python header specify3.12.15. The config digest matches the original manifest-pinned build validation, and the header layer digest verifies against config rootfs identity; the SIF itself matches its frozen SHA. This is build/source evidence, not an attestation of the actual SIF executable. Native submission is held before spending an allocation. A0's capability-stop rule remains unchanged; no automatic version substitution or dependency upgrade. [E277][E279]

One separately bounded image-only inventory now captures actual image libraries/private-hook/parser identities, original-function source/AST/line mappings and literal monitoring/default-pool capability. It contains no datasets or database/graph binaries, mounts only its source capsule read-only and starts no database or Slurm job. One invocation:15CPU/30interpreter-wall seconds,2GiB virtual address space,60s outer timeout plus5s kill grace,128 source reads/4MiB,16 literal callbacks/128KiB JSON. Exclusive binding and checked download preserve incomplete evidence without retry.29 source/29 sealed checks and exact source/archive verification pass;5,318 old files remain unchanged. The user must upload, run the inventory on Torch login and download it using E282. [E278][E280][E281][E282]

A2 is **not complete**. A completed reference mismatch is useful inventory evidence and still holds release. A complete match would also leave allocation proc/cgroup, overhead/lifecycle/full acquisition and cleanup/replay gates pending. Revised critical path: image inventory → explicit compatibility decision/any separate correction and readiness → reviewed native handoff → pre-restore capability → unchanged bounded zero-search acquisition → independent A3 decision → separate remedy/resource/full-workload qualification. No A2 allocation or full B2f is released. [E277][E278]

### 2.44 A2 image inventory verified; narrow reference correction is justified

The downloaded `startup-attribution-image-preflight-v1.QANl63cj` is complete: exit0, empty stderr,5.627513442s interpreter wall. All four raw files, three payload hashes,108-file manifest/109-member package archive,99 exact A1 reference copies and trusted sealed data-only replay verify. The complete provenance comparison has only one difference: CPython3.12.15 actual versus3.12.7 reference. NumPy2.5.3, Arrow22.0.0, Psycopg3.3.6, binary libpq180006, all nine source/function/signature hook entries and the uncached parser are exact matches. [E283][E285][E286]

A0 already explicitly freezes3.12.15. A1 captured the Mac interpreter version into its image expectation; this is a harness reference error. Torch's image requires no dependency/version change based on this evidence. Both original function source/AST/line mappings, unchanged bindings/local masks, four literal monitoring callbacks/restoration and import-time default Arrow pool capability pass.12source reads/246,814bytes remain within caps. The inventory reports zero SQL/connections/snapshot/search/provider and no allocation/cgroup/margin qualification. The original producer/constructor and full wrapper/generator/signal/cleanup paths were not executed under3.12.15 here. [E283][E286][E288]

Decision: GO isolated exact target-image reference correction plus appropriate3.12.15 source/sealed compatibility readiness, preserving the strict historical Mac/A1 reference. Do not waive patch checks, change dependencies or replay the spent inventory. A later release must check original-function source/line/local-mask capability before restore and qualify the real target-runtime paths. A2 acquisition remains held until corrected readiness and finite handoff review pass; full B2f and both margin-inconclusive resource verdicts remain unchanged. No new user command or allocation is released by this analysis. [E284][E288]

### 2.45 Exact-reference correction locally complete; native compatibility job prepared

The isolated main harness retains the historical Mac3.12.7 reference and pins a separate exact native3.12.15 reference to the verified image inventory. Driver/Session/replay never choose the local reference natively. R00 now validates original source/AST/line/local-mask capability before restore; no original code replacement, extra search/scan or resource-rule change. Production entry points and packaging require current source and exact-target proof; there is no main production artifact or handoff yet.128local and128guarded local checks pass with zero connection/process denials. [E289][E291][E293]

The existing Docker build matched, but local emulated execution emitted QEMU target SIGSEGV and no Python test receipt. The owned container was stopped/removed, OOMKilled=false; exit137 follows that stop. Do not infer a target pass or an image defect. C2 now uses one separately frozen native correctness job:15minutes/two physical CPUs/4GiB; source128+sealed synthetic candidate128, zero SQL/DB/server/ANN/exact/provider/fit. Capsule/source/A1/SIF read-only, private scratch only; guarded child processes, complete fingerprints, deadlines/cleanup and locked terminal raw required.23source/23sealed capsule checks include actual mocked host/guest success/failure, strict dispatch/reservation/collection and guard tests.693manifest/694regular archive members and5,531 earlier inputs verify. [E289][E292][E293]

Only the compatibility job is ready for user upload/submit/status/collect/download via E294. Main A2's one1h4CPU32GiB zero-search acquisition remains held until native3.12.15 source/sealed receipts are independently verified and C3's main production seal/release review passes. Do not retry the spent inventory or failed emulated route, launch main A2/B2f, change references dynamically or increase scientific resource margins. [E290][E294]

### 2.46 Failed C2 verified; offline dependency and fixture correction ready

The first native correctness job21348020 failed after86 completed source successes, a ReplayTests.setUpClass ERROR and the300-second source deadline; source/sealed target receipts, final guard proof and sealed candidate are absent. Its13 regular archive members/eight locked files, job/package identity and exact3.12.15 native provenance verify. Main A2 never launched. Retained user-pasted scratch records identify FileNotFoundError for inputs/local-identity.json; direct actual-constructor regressions reproduce the absence and succeed with the corrected packaged bundle. The old local checks silently used ambient workspace metadata. This is a packaging defect and incomplete target qualification, not a native-reference change. [E295][E296][E297]

Adjacent synthetic runtime failures were23.502/25.325 seconds apart although their runtime bodies took~one second; repeated fixture preparation/copy/reseal work contributes outside runtime elapsed. Its precise components are not isolated. The isolated correction hash-pins/copies all three constructor inputs, hardlinks only immutable ephemeral synthetic fixture files with separate mutable copies and before/after seed verification, emits immediate tracebacks/fail-fast test events, and publishes guard/final host-integrity evidence on failure. Main A2 source/recipe and production copying remain byte-identical.33source/33sealed checks plus128guarded source/128packaged-fixture main checks pass, with zero connection/process denials and all ten seeds verified per integration suite. [E295][E298][E299]

The old native allowance is spent. A distinct one15m2CPU4GiB correction allowance retains300s source/300s sealed/90s candidate/720s guest limits, zero real DB/SQL/server/search and no retry. Native128+128 target results must be independently verified before C3 can prepare a production main A2 seal. The revised path is verified failed C2 → corrected dependency/fixture/reporting package and local checks → one native correction qualification → C3 main seal/release → main A2 → A3 interpretation. User commands are E300; old E294 is historical and must not be resubmitted. [E298][E299][E300]

### 2.47 Second native C2 deadline verified; prepared-fixture qualification ready

Job21367064 has16 verified regular archive members/11 locked files,96source pass events and no recorded test errors. Metadata/provenance and final source/SIF integrity pass; all replay cases and four-signal cleanup pass. The dedicated full-runtime assertion case times out during fixture reseal, before its runtime body; replay setup had already completed a bounded synthetic runtime. Complete source/sealed target and guard receipts remain absent. Four class-setup gaps total184.514seconds; five stacks are in fixture hashing/writes. The missing-file fix worked; native reference drift or an ANN deadlock is not supported. This remains incomplete correctness qualification, with no agent performance or main-workload memory verdict. [E301][E302]

A separately frozen correction runs the real synthetic builder once per child and reuses its fully fingerprinted/checksummed seed for five class requests. Ten hardlinked runtime fixtures retain complete before/after seed hashes; their manifests reuse only just-proved same-inode immutable hashes and recompute all mutable content hashes. Exact inventory, symlink/detached-file, mutation/archive/checksum/native-request/duplicate-target and restoration negatives are tested. The separate unpatched guest candidate builder remains, yielding three full builds per job instead of11. All128source+128sealed cases/assertions and production main recipes/hash/copy behavior are unchanged.43source/43sealed and128source/128packaged-fixture main local checks pass through final guard receipts; direct original-helper manifest parity also passes. [E303][E305][E306]

One local pre-release candidate passed its128cases but stalled in asynchronous diagnostic-watchdog cancellation. Its owned process/sample/candidate were preserved and stopped. A pre-code amendment removes the background dump/cancel thread; synchronous test/fixture-stage events plus fatal-error faulthandler remain. Fresh240-second-bounded local checks complete all final receipts. This Mac3.12.7 observation does not establish a native3.12.15 failure. [E304][E305]

Both earlier compatibility allowances remain spent. The new distinct15m2CPU4GiB allowance retains300s source/300s sealed/90s candidate/720s guest and zero real DB/SQL/server/search; no retry, skipped cases, margin increase or main A2 release. Current local suites take~63–64seconds, but native headroom is still a qualification question. Next: user E307 native128+128 → independent complete identity/build/clone/reseal/restoration/exit/locked-integrity review → C3 main production seal/release → main A2 → A3. [E301][E303][E305][E307]

### 2.48 Third native C2 timeout verified; budget revision precedes another handoff

Job 21382454's 12,545-byte archive has 16 verified regular members and 11 verified locked files. Exact native 3.12.15 provenance, all three constructor dependencies, submission/job identity and separate final capsule/SIF integrity pass. The source ledger has 119 passes, 120 starts and no recorded error/failure/subtest-error events. It includes successful full synthetic runtime/checkpoint and four-signal cleanup cases. Test 120's clone/reseal completes at 299.698 seconds; its result/final seed check, eight unstarted cases, final source guard/target receipt and all sealed qualification are absent. The lock correctly remains incomplete. Final host integrity cannot replace missing child restoration proof. [E308][E309]

Completed nonoverlapping fixture stages consume 143.703 seconds: seed preparation 46.215, five shared-seed/archive checks 13.314, ten seed hashes 25.349, ten clones 30.094, ten reseals 3.941 and nine final seed hashes 24.790. Whole-test durations overlap these stages and cannot be added as independent costs. The A1 manifest retains 298,917,834 content bytes, including a 262,630,951-byte historical evidence file. Original runtime verification still reads the full manifest and nested pin sets; hardlinks do not remove verification reads. The traces do not separate CPU hashing, filesystem wait and internal verification calls. Continued progress to the deadline supports a time-budget mismatch; no new functional failure is recorded. [E308][E309]

All three native allowances are spent; E294/E300/E307 are historical and must not be resubmitted. Recommend C2B: prospectively freeze a time-accounted qualification with all 128+128 cases, strict identities/verification/guards and zero real DB/SQL/search. A 20-minute planning option is 420s source + 90s candidate + 420s sealed + 30s guest cleanup = 960s guest, plus 90s host startup + 60s host cleanup + 90s outer margin. Two CPUs/4GiB could remain unchanged. This is an unqualified sizing proposal, not a released contract or guarantee: remaining native cases, finalization and sealed costs are not measured. No budget-only correction is implemented or submitted in this audit. Native qualification must pass before C3 main seal/release; main A2 remains a separate 1h/4CPU/32GiB zero-search acquisition. [E308][E310]

### 2.49 C2B independently reviewed, frozen and locally ready

The third failure ledger/source recheck supports a prospective budget correction without a fixture rewrite. The 20 m option left guest preflight and the wrapper's separate 15 s termination reserve unallocated. Freeze 21 m / 2 physical CPU / 4 GiB:90 s host startup +990 s guest (30 s preflight+420 s source+90 s candidate+420 s sealed+30 s cleanup) +15 s termination +60 s host cleanup +105 s outer margin.420 s per suite is finite sizing, not measured native headroom; any missing proof/timeout consumes this new allowance with no retry. Review and freeze precede isolated implementation. [E311][E312][E313]

Exact budget validation, complete-phase admission without shortened suites, monotonic/alarm checks, phase timing and bounded cleanup/publication are implemented under a distinct package/reservation.62 source/62 sealed capsule checks include all 43 old cases and deadline/cleanup/publication negatives.128 guarded source/128 packaged-fixture main checks complete final guards and all seed/build/restoration proofs; original reseal parity, source/archive/shell/AST checks and 5,111 earlier files pass. All 128+128 native cases/assertions, fixture helpers, 68 main recipes, references/dependencies and production limits remain unchanged. Local results do not establish native completion or main-workload memory. [E314][E316][E317]

At the v1.54 preparation snapshot, only E315 was current: upload → Torch verify/submit once → status/terminal collect → download → independent complete native 128+128 and identity/build/clone/reseal/seed/guard/cleanup/timing/exit/locked-integrity review. All three earlier allowances remain spent; E294/E300/E307 are historical. C3 main production seal/release follows only after native qualification; main A2 remains unlaunched/held at its original 1 h/4CPU/32GiB, zero ANN/exact searches. Full B2f and prior resource verdicts remain held. No job submitted by this work. [E311][E314][E315]

### 2.50 Native C2B verified; C3 releases unchanged main A2

Job 21443102 completed all 128 source and 128 sealed cases with exact native 3.12.15 provenance, no test errors or denied actions, and complete seed/build/clone/reseal/restoration/cleanup proofs. All 24 archive members and 19 locked files, job/submission identity, terminal COMPLETED/0:0, phase timing and final capsule/SIF integrity verify. Source/candidate/sealed phases took 283.272/37.151/284.598 seconds; guest/host totals were 605.870/618.178 seconds. All four compatibility allowances are now spent, with the earlier three failures retained. No main-workload resource/performance verdict follows. [E318][E319]

C3 freeze precedes a real production seal: 619 manifest files/620 regular archive members. Compared with the native candidate, only two readiness receipts are added and two synthetic/readiness configuration fields change. All 68 recipes and all code/science/main limits remain identical. All 128 actual final-package local cases, strict readiness/controller checks, archive/shell/AST/Ruff and 5,883 prior-file preservation pass. The main package is unbound and no job is submitted here. [E320][E321]

At the v1.55 release checkpoint, E322 was current (now spent by job21459623): Mac upload → Torch verify/submit once → status/terminal collect → Mac download. Main A2 is the original one 1h/4-physical-CPU/32-GiB acquisition with zero ANN/exact searches, one snapshot/four verification scans and all 102 checkpoints. Capability before restore and every original identity/coverage/overhead/resource/restoration/cleanup/lock/replay gate remain required. Independently verify the actual main return before A2 closure and A3; full B2f remains held. E294/E300/E307/E315 must not be resubmitted. [E318][E321][E322][E323]

### 2.51 Conclusions that determine the next work

1. **P2 remains closed with original execution retained.** Its measured mechanism benefits do not satisfy the frozen optimized-execution gate. Preserve every prior negative/inconclusive result and M1's unestablished status.
2. **P3b/P3c close without a joint qualifier.** P3c improves fixed-diagnostic recall, but neither calibrated procedure covers activation costs. Close the finite formulation allowance; do not add seeds, risk thresholds, trees or post-hoc routing. [E69][E70]
3. **Keep the supported scope precise.** Unreachable states are not missing labels, invalid measured stops are not unknown, and off-grid or current Light19 gaps remain real. Profile/binary-specific costs and conditioned timing scopes are not interchangeable.
4. **Information availability is not learnability.** Neither tested richer-profile formulation produces a joint qualifier. Risk calibration and development diversity remain limitations, not reasons to consume protected samples or claim a universal ceiling. [E70]
5. **B1b has no qualifying context; B1c stays deferred.** Reuse effort320 is40.540% faster but loses0.800pp recall overall; every context fails its reserve. Forced640 reuse adds0.206ms, above the overhead limit. Activation precision fails, so the frozen aggregate remains measurement-inconclusive. Repeating calibration cannot repair the unchanged quality/control failures. The completed review now specifies a separate fixed480 native diagnostic; it neither revises B1b nor qualifies routing. [E90][E91][E95][E96][E97]

6. **B1b2 is complete, `closed_negative_quality`.** Native conformance and absolute floors pass; overall/votes32/votes108 development reserve fails. The valid1,830-search stop acquires no timing/A/A/benefit evidence. Retain original execution; completed B2a now recommends a separate exact-top10 comparison design. No router, effort ladder, protected entitlement or user commands. [E107][E108][E109][E115]

7. **B2b remains incomplete and closed without repeat.** Complete block0 exact is56.11x slower; even votes108 is28.47x slower. Completed B2c/B2d establish the separate partial-index mechanism and scoped quality, while B2d fails all A/A intervals and remains measurement_inconclusive. [E144][E147][E184][E186]

8. **A3 resource acquisition is reported failed; collect before diagnosing or correcting.** Job 21542975_0 reports completed admission/epochs/four scans and zero searches, but sampler loss/finalization and cleanup failures prevent qualification. The allowance is spent. Collect all terminal raw via E361 and independently verify actual sampler error, cleanup details, coverage/counters, source preservation and locks. No memory margin, OOM cause, new capsule/retry or full B2f release is established. [E360]–[E362]

Earlier results remain relevant: the prior frozen candidate saved latency but failed held-out recall; CART and first-stop beam procedures later selected only continue; the feature/data ablation selected no nonconstant calibration candidate. None should be relabeled as a successful method comparison. [E4][E5][E6]

### 2.51 Main A2 verified complete; informative attribution does not pass memory margin

Job21459623_0 completed0:0 in14m16s under the original4CPU/32GiB limit. The52-member/1,274,259-byte archive SHA256 is1da3b40f9c92c4b234c22361f1225404170447ed142beccc32865e077a7687a7. Exact member/raw parity,32 guest/45 host locks, original619-file seal/620-member archive and68 source/sealed recipes verify. A fresh trusted sealed replay matches all three download-time analysis files byte for byte. No returned code executes; all128+128 native compatibility cases/strict proofs remain intact. [E333][E334]

All102 checkpoints, one snapshot/four verification scans, ten reader admissions/maxsix, both epochs,200 admitted/zero executed requests, final source/data/graph/module identity, restoration and cleanup pass. Independently reconstructed driver work is10,145 dispatches:227API,9,892fetches,4close,4describe,8transaction and10prepare. Four exact247,286-row passes retain2,473pages each, final86; these are Python-driver dispatches rather than packet counts. Added observers use9.700775 CPU/9.935772 wall seconds and95 LINE callbacks within original caps;853 memory samples cover acquisition. ANN/exact searches, providers/fits/plans/confirmation all remain zero. [E334]

Frozen outcome: **attribution_complete_informative**. Cursor execution to result receipt raises RSS2.213GiB; row decoding adds7.478GiB with matching task-anonymous growth; matrix construction adds0.709GiB. Cursor close changes RSS by only12KiB. Each verification pass shows a0.717GiB sampled default-pool range. Existing file-role brackets show charge variation without allocation-ownership proof; no causal savings or summed component-peak claim follows. [E333][E334]

Separate resource verdict: **startup_complete_resource_margin_inconclusive**. Aggregate kernel peak reaches32GiB, job max-event delta780, OOM/kill deltas0. Successful completion is not an OOM kill, but neither unchanged28GiB effective peak allowance nor no-limit-event condition passes. Next is A3's minimal exact-value consumer/representation/lifetime remedy review and compatibility/resource test freeze before code; no blind cursor/GC/batch change or full B2f release. The one main allocation and all compatibility allowances are spent; do not resubmit. [E333][E335]


### 2.52 A3 selects exact packed vectors; contract frozen and offline feasibility passes

A2's7.478GiB row-decode RSS bracket and preserved-row/matrix overlap justify one separately scoped representation remedy. Plain float32 compaction changes original values; plain binary64 storage loses JSON integer categories and cannot directly satisfy ordinary row serialization. Select binary64 float bytes plus exact original integer category/value tags, with one-row original-canonical encoding and bounded ordinary-JSON sample adapters. Cursor/GC/batch-only, cache subtraction, larger limits, skipped checks and early disposal are not selected. [E336][E337]

A3-FREEZE precedes candidate code and pins ten actual frozen producer/constructor/encoder/consumer files. The new prototype reuses the unchanged Snapshot constructor and original identity framing, preserving exact numeric types/float bits/negative zero, identity bytes/hash, float32 matrix bits, typed IDs/maps, metadata masks, query validation, workload, Parquet and sampled row outputs. Internal vector type/mutation changes explicitly; arbitrary list/third-party API equivalence is outside scope. Original A2's list-vector guard is unchanged and cannot accept this new path implicitly. [E336][E337]

All33 <=64x768 guarded local checks pass on CPython3.12.7/NumPy2.5.3/Arrow22.0.0/Pydantic2.13.5, with zero connection/process attempts. Source stability and756 prior A2 source/seal/raw/analysis/128+128 receipt hashes verify. Initial fixture-contract mistakes and earlier positive logs are retained. This proves bounded local consumer compatibility, not target3.12.15, native memory, savings or main-workload readiness. [E338]

A3's remedy decision is complete. Next is a separate production integration that packs each decoded vector before appending its row, with explicit identity/sample adapters and actual entry/failure/cleanup tests. A distinct frozen finite target-correctness capsule/budget must preserve all old128+128 cases and strict references before any native resource handoff. The unchanged32GiB total-charge limit,2GiB reserve+2GiB workspace and no-positive-limit/OOM-event rule remain mandatory. **No Torch commands are released here**; all A2/compatibility allowances remain spent and full B2f is held. [E336]–[E338]


### 2.53 A3 actual producer/startup integration locally passes; distinct native correctness released

Pre-code integration freeze and native-gate amendment precede the isolated implementation. One vector is packed before appending/requesting the next row; original SQL/client cursor/order and Snapshot constructor remain unchanged. Exact identity is verified with restored instance/digest bindings before cache publication; original eligibility and200 request admissions precede shared aliases, with rollback on parse/count/shape/norm/identity/cursor/cancellation/closed-reader/admission failures. Later readers retain owned cache tags and inherited search prohibitions. Native resource context requires separate manifest/current target proofs/final audit and the unchanged original resource contract. [E339][E340]

All56source/56sealed cases (33prototype+23integration/gate) pass on the exact historical local reference, plus all128+128 unchanged original cases through complete seed/clone/reseal/guard restoration and65source/65sealed capsule controls. Exact target3.12.15 remains unqualified until actual native execution. All789 prior files/68main recipes and guard helpers remain unchanged. The774-file/775-member capsule archive SHA256 is540af999770eeebbca80aa29c228b978a0101b11adf4e0dc4b424c4b4b5f5865; full source/seal/member/command/budget audit passes. [E341]

At v1.62, E342 released one distinct25m2physicalCPU4GiB correctness job (now completed/spent; see §2.54), all128+128 and56+56 cases, zero real DB/SQL/server/ANN/exact/provider/fit. Preserve420/90/420 old phases; add90s per A3 source/sealed phase, complete1170s guest,120s host startup,15s termination,60s host finalization and135s outer margin. No phase shrinks or borrows cleanup; any failure consumes the allowance without retry. Capsule extraction and fixture scratch use private scratch to avoid home inode pressure. [E339][E341][E342]

After terminal collect/download, independently verify complete case/event identities, exact target/private hooks, guards/seeds/restoration, accounting/timing and final capsule/SIF integrity/locks. Only then review a separate native resource acquisition; no memory/savings/quality/performance/B2f qualification follows from correctness. All previous main/compatibility allocations remain spent and no remote/native job was run here. [E343]


### 2.54 A3 native correctness independently qualified; separate resource gate remains

Job **21470341** completed 0:0 in 11m44s. Independent archive/member/raw parity, all 28 run-lock hashes and coverage, scheduler/dispatch/host identity, exact image/private-hook/library reference and final source/capsule/SIF integrity pass. The 52,187-byte return contains 33 regular members; archive SHA-256 is `3edd0524f864aa97869a0ee71fe034c60a36b3cf37e24dfe8995dce455b2e2d3`. All 789 prior files, 68 main recipes and the original 774-file capsule remain unchanged. Returned code is never executed. [E345][E346]

All **368 individual case identities** independently reconcile: original 128 source + 128 sealed and A3 56 source + 56 sealed on exact CPython 3.12.15. Every start/pass pair, module origin, receipt/code hash, guard restoration, one-build/four-reuse proof, seed/clone/reseal event and zero-denial result verifies. No failure, error, skip, missing or duplicate case is promoted. Guest 684.603s and host 699.201s remain inside every frozen phase/deadline/tail/cleanup reserve. Zero real DB/SQL/server/ANN/exact/provider activity is recorded. [E346]

An authentic four-receipt packet and independent qualification audit pass the unchanged trusted local native gate using metadata only, without native-size arrays or a backend. Its temporary hypothetical release is deleted; no persistent resource controller/job or release is created. D112 qualifies native correctness only. All prior allowances, including E342, are spent; do not resubmit. [E346][E347]

GO to a **separate startup-resource protocol/harness freeze, integration and local release review**, then a distinct bounded resource handoff only after those gates pass. Retain original data/graphs/module/identity, one snapshot/four scans, 200 admission-only requests, ten readers/max six, both fixed orders/holds, strict provenance/guards and full cleanup. Aggregate recorded peak + 2 GiB reserve + 2 GiB workspace must remain <=32 GiB, with no positive limit/OOM event, no cache subtraction or early root release. Native memory, causal savings, workload/quality/performance and full B2f remain unqualified. No new Torch command is released. [E345]–[E347]


### 2.55 A3 startup-memory harness locally qualified; new finite resource handoff ready

The pre-code resource freeze retains the original one-hour/four-physical-CPU/32-GiB contract, one snapshot/four full verification scans, 200 admissions/zero executions, ten readers/max six, both fixed creation orders/five-second holds and complete source/data/graph/module/cleanup proofs. All 68 main recipes, five qualified A3 files and 1,956 tracked prior files remain unchanged; original 128+128 and 56+56 native receipts remain exact. [E348][E349][E351]

Actual frozen runner/OwnedReader startup supplies FrozenList metadata. The qualified producer's exact-list check rejected it even though row count, active binding and canonical fields matched. A pre-code amendment introduces a <=16-KiB ordinary metadata read view with byte-identical canonical fields; immutable source/origin/binding objects remain untouched, and the getter restores before returning that read, before the producer connection. New exact-image literal preflight covers the adapter before restore. Prior native correctness remains scoped to the unchanged producer; it is not retroactively claimed to cover the wrapper. [E348][E350]

All **100 source + 100 sealed** cases pass through actual startup/constructor/eligibility/admission and both reader epochs/final scans/cleanup on bounded simulated SQL, host/controller mock transports, independent metadata-only replay/tamper checks and cgroup/margin failures. Missing driver metadata, generated-file fixture collision and local disk-exhaustion failures are retained. Explicit recipes and sequential suites with read-only links only within newly built temporary test seeds fix local packaging/storage; production and database copies remain independent. Original memory decision and eleven scientific/measurement modules are unchanged in meaning. [E348][E351]

The host preserves pre<=240s, runtime<=3000s (including 600s guest cleanup), post<=240s and the full 120s outer margin. Termination/reaping/sampler stop consume post time; expiry stops further heavy verification instead of appending the legacy 30s wait. The final production archive is **983 manifest files / 984 regular members**, 39,063,874 compressed bytes, SHA-256 `9702d0fe3a81efb1051e16d18be63977541d447587335208a6f584e770409044`. Authentic native proof consumption and strict rejection of the historical local interpreter before restore verify; no native memory is inferred. [E351]

Only **E352** is now released: one distinct, unspent startup-memory allocation, private scratch extraction, unchanged conservative quota/inode guards and a unique durable reservation. Offline upload/failed-authentication/invalid-manifest/unsafe-campaign checks pass with SSH/SCP stubs and short private sockets. Any dispatch failure/uncertainty consumes the reservation; no retry of this or any old package. After terminal collect/download, independent full native identity/lifecycle/sampler/locks/integrity/replay must establish the unchanged largest aggregate peak +2 GiB reserve +2 GiB workspace <=32 GiB and no-positive-limit/OOM-event criterion. Workload, quality, A/A, performance, causal savings and full B2f remain held. No job launched here. [E348][E351]–[E353]


### 2.56 A3 resource login path failure precedes reserve; corrected context locally qualifies

The user reports 7,297 files/1,209.5 MiB verified in 95.5s, followed by FileNotFoundError for the old exact package inside the new scratch capsule. Source line 141 calls protection before line 179 scheduler test and line 184 reservation creation. Earlier resource binding/reservation guards had passed; the attempt reached no new allocation. The continuation checks live state again and stops on any existing/uncertain reservation. All older compute allowances stay spent; no additional resource allowance is created. [E354]

The inherited helper resolves `package.parent / "torch-exact-topk-v1"`. Passing embedded reference/ changed that parent. Freeze the isolated wrapper correction before code: verify every actual main home-package file/manifest and its spent binding/reservation against embedded pins, then invoke unchanged original protection with the original main `/home/dar579` context. Preserve all historical exact/source/result checks and restore caller sys.path on success/BaseException. No symlinks, skipped guards, old-source edits or cap changes. [E355][E356]

All **110 source + 110 sealed** cases pass, preserving the original 100 IDs. Ten new filesystem/context/negative/interrupt/pre-reservation regressions exercise the actual inherited sibling/hash calculation on bounded prior fixtures; broader original guards remain byte-identical for real login/host execution. All 3,035 prior files, initial artifact, 68 main recipes, five qualified A3 files and 128+128/56+56 native receipts remain unchanged. New production seal: **984 files / 985 regular members**, SHA-256 `92333e1785d0510c45146d359724a55b482d96db44e383b56b88ee20040b4b90`. Independent archive/source/preservation, strict reference and offline handoff checks pass. [E356][E357]

E358 replaces E352 for the **same unspent** 1h/4physicalCPU/32GiB zero-search startup-memory allocation, keeping the original fixed reservation and campaign prefix. The corrected transfer directory is `/home/dar579/a3-resource-path-fix-transfer`; extraction uses private `a3-resource-path-fix-packages`. Archive and derived one-command continuation each have verified SHA-256 sidecars; originals are untouched. Native memory/coverage/margin verification still requires the later complete return and unchanged aggregate peak +2GiB reserve +2GiB workspace/no-positive-limit/OOM rule. Full workload/B2f remains held. No job launched here. [E358][E359]


### 2.57 A3 resource terminal failure reported; sampler/cleanup raw required

User status binds campaign `reviews-startup-exact-vector-resource-v1-20261031T203754Z.0lyxk3k2` to job21542975, array task21542975_0. Scheduler reports FAILED1:0/16m35s. Runtime reports765.861s, both epochs,200 admitted/zero executed requests,ten readers/maxsix,one snapshot/four full data scans, final_integrity_verified=true and zero backend/search/prohibited SQL/plan/provider/fit/confirmation counts. These are reported receipt fragments, not independently verified native evidence. [E360]

Guest status is failed with generic Cleanup/source preservation failed. Host reports Required memory sampler lost; resource qualification held and Memory sampler did not complete; exit1 and protected_sources_unchanged=true. This does not identify the underlying sampler/cleanup cause or prove retained-source preservation. Detailed memory-summary/health/cleanup, sampler/host/scheduler/server logs, complete source inventories and locked raw remain required. Slurm MaxRSS30071884KiB and sampled per-process high-water values cannot replace the frozen aggregate cgroup peak/event/coverage rule. No OOM or margin verdict follows. [E360]

The resource allowance is now spent. E361 only collects/downloads all terminal failed raw; Invalid job id from squeue is consistent with a finished job and collection separately requires terminal sacct evidence. Preserve every reservation/source/work/result, original source/seals/128+128/56+56 proofs and limits. No new code/capsule, retry, extension or full B2f release before independent complete return audit and any separately frozen evidence-backed correction review. No native/SSH/search action was run here. [E361][E362]


### 2.58 A3 resource failed return independently audited; unchanged aggregate margin already fails

The complete56-member/16,025,465-byte uncompressed return verifies against SHA-256 `cd5949c3c4bfe660f83ce01698972316d1358e2ddbd94ded6bb8c89bbf6d7091`. All49host/34guest lock bindings and coverage,984sealed files, exact target/private hooks/origins and3,035prior file hashes pass. Both completion flags are false; unchanged trusted analyzers reject successful qualification. No returned code was executed. [E363][E365]

Acquisition independently reconciles both creation orders/5s holds,ten distinct readers/maxsix,200admissions/zero executions,one snapshot/four data scans,56observer/171startup SQL and zero searches. Final data/graph/module/catalog identities and retained producer roots/aliases verify. The2,587-file/4,603,663,760-byte retained stopped-source inventory and historical protected-source inventories match before/after, including completed main A2/A3 package/result pins. Generic cleanup failure does not establish source damage. [E363]

The largest recorded kernel high-water among visible finite ancestors is **30,816,649,216bytes =28.700241GiB**. Unchanged2GiB reserve +2GiB workspace gives **35,111,616,512bytes =32.700241GiB**, over32GiB by751,878,144bytes. Even this incomplete-trace lower bound fails the frozen margin; a sampler-only fix cannot qualify it. No cache subtraction, component/RSS summing, lifetime-peak reset or limit relaxation. Positive max/OOM/OOM-kill deltas are zero in recorded task/finite-ancestor coverage; final coverage is incomplete, so no OOM cause or final-peak claim follows. [E363][E364]

Sampler reports `Live process lacks RSS counters` after889successful samples/889.024s, within observer budgets. Separate stat/status reads permit an exit-transition race, but failing PID/raw values are absent; the exact process/transition remains unknown. Host monitor's sampler-loss path sends termination; the guest uses the same generic deadline text for SIGTERM and deadline signals. Guest finish is217.579s into the600s cleanup phase, before stage/global deadlines; this is not evidence that more time is required. Cleanup observed a working postmaster.pid and lacks stopped-copies/control proof despite later flags/logs. Preserve fail-closed treatment. [E363][E364]

D116 closes the resource attempt **failed/unqualified**, keeping native A3 correctness qualified separately. Next: offline evidence-backed review of total startup charge, lifecycle-aware observation and shutdown certification together; prospective freeze/local qualification only if justified. All old/main/correctness/resource allowances are spent; no retry, extension, new capsule or full B2f release. No Torch command is needed now. [E364][E365]


### 2.59 Offline A3 review complete; lifecycle correction checked, memory remedy held

The independent resource audit supports lifecycle corrections but no positive memory verdict. Job-ancestor sampled current during snapshot load is28.22734GiB, with5.09490GiB anonymous and23.07598GiB file components from that same sampled observation. File charge is substantial before producer construction, and client memory rises during construction/final verification. These are descriptive phase observations, not components of the kernel high-water instant or causal savings. The28.700241GiB recorded aggregate lower bound plus4GiB already defeats32GiB. No bounded-cursor/new-representation/original-constructor patch is implemented without a separate justified consumer/correctness design; no cache subtraction or verification/lifetime shortcut. [E366][E369]

Freeze SHA-256 `a390844b3c8e4093f759c251ed3ad737314accac24d9fdf323503698bf4c14f0` precedes creation/implementation of the isolated lifecycle source. A separately frozen amendment precedes the positive replay guard. The sampler brackets PID/starttime, discards mixed-PID counters, records proved terminal/disappearing processes and allows at most one bounded live missing-counter confirmation. Persistent live missing RSS, malformed/membership/permission/cap failures remain fatal; bounded structured failure evidence is durable. Original read/sample/CPU limits and memory decision are unchanged. The historical failing PID/transition remains unknown. [E367]–[E369]

The host records one observer-loss cleanup request, avoiding interruption of known cleanup. A second prospective amendment closes the remaining asynchronous entry race: ordinary cancellation only records a request, and the next existing budget check rejects further ordinary work before driver execution. The handler never raises through an arbitrary cleanup frame. Pure work remains bounded by original stage/global alarms. Every cancellation/observer-loss outcome stays failed. Alarms and original absolute deadlines still interrupt; each heavy cleanup step checks/rearms only remaining time, and expiry prevents more heavy work. Positive replay requires strictly typed zero/empty/false cancellation proof and no observer-loss request, including after status/lock rewriting. [E368][E369]

All **142source +142independent code-snapshot** checks pass with zero errors/skips/denied actions/real SQL/searches/jobs. Original110test files/IDs,5qualified A3 files,128+128/56+56 native proofs and5,163prior files remain unchanged. Thirty-two new regressions include actual mocked runtime cancellation/shutdown, identity/read races, deadline caps, durable failure and relocked positive-proof negatives; the138/140intermediate passing artifacts remain preserved. These are code-only offline checks, not sealed native or exact3.12.15 correction qualification. An actual pre-SQL cancellation regression verifies no driver execution; the unchanged trace conservatively reserves the rejected scan attempt. Native CLI entries/production capsule builder are disabled; no native archive/handoff is created. [E368][E370]

D117 completes the requested offline review and locally qualifies only the lifecycle correction. Memory remains unqualified; the next unresolved gate is a separate source-backed memory remedy design with a prospective freeze. All prior allowances remain spent; no resubmit, extension, new entitlement/capsule/Torch command or full B2f release. [E369][E370]


### 2.60 Exact adaptive memory remedy frozen and locally checked; production/native gates held

Source review identifies a second allocation mechanism: the old PackedVector casts its6144-byte binary64 payload to a separate3072-byte float32 array for the original Snapshot constructor. A pre-code64-row synthetic probe observes all64converted arrays alive together,196,608owned bytes. The new component retains either3072or6144bytes in the same three immutable slots and exposes compact float32 input as a read-only view. The independent audit observes zero separate owned float32 row bytes, with the required matrix preserved and independent of row payloads. These are local structural observations, not native peak or causal savings. [E371][E373]

The exact adaptive32-bit code is accepted only if the pinned shortest-decimal decoder reproduces every original binary64 bit. Any mismatch retains the entire original raw64 vector; exact arbitrary integer tags/values and signed zero survive. This is not the previously rejected unverified float32 truncation. No SQL/cursor/transaction/constructor/validation/data/graph/root-lifetime or resource-decision change is made. Native compaction rate is unknown. [E372][E374]

Freeze `2f7107f50b6661d5e5c53318c236e94897387807f87ebab53e123a4a415bfbd7` precedes candidate creation. It accidentally pins systemNumPy2.3.4 while the approved probe/runner use2.5.3; the first92-case run fails the exact reference guard. A prospective immutable amendment pins only the approved2.5.3function/module before correction, preserving original freeze/failed receipt and dependencies. A later invalid workload-count fixture is corrected to existing valid20 without changing validation. All failed/intermediate evidence remains preserved. [E372]–[E374]

All **94source +94code-snapshot cases** pass, including56original A3 IDs/files unchanged and38new compact/fallback/consumer/allocation/binding/reference/ownership cases. Full original canonical/frame/hash and float32matrix bits, identifiers/maps, masks, query/workload/description, Parquet/file bytes and JSON samples reconcile. Main128+128/A3 56+56 native proofs,142+142lifecycle artifacts,five qualified A3 files and5,445prior files remain unchanged. Fixture construction is limited to64rows and rejects NativeSpec before construction. Zero real SQL/DB/network/subprocess/SSH/ANN/exact/provider/Torch actions. Code snapshots are not native capsules or exact-image qualification. [E373][E375]

If every native vector compacted, payload-only reduction would be759,662,592bytes, only7,784,448bytes beyond the751,878,144-byte observed shortfall; at least244,752of247,286rows would be needed merely to cover that incomplete-trace deficit if all else stayed equal. Those assumptions are unverified. Avoided conversion allocations add a source-backed opportunity but cannot be subtracted from the historical peak. Formatting CPU cost and actual target semantics remain separate gates under unchanged600s snapshot/3000s runtime/1h4CPU32GiB and2+2GiB allowances. [E371][E374]

D118 completes the memory-component design/local prototype only. Next: separately freeze producer integration (pack-before-next-row and original SQL/cursor), expanded source/release/retention guards, actual target formatter/private hooks and exact-image correctness/CPU-budget review. Old native proof does not qualify new code. No native integration, allocation/capsule/handoff or full B2f release is created. All spent allowances stay closed. [E374][E375]


### 2.61 Adaptive startup integration verified offline against exact target references

Prospective freeze `2e31c4cedebfc844e30d137c6042e5f30cfd44b7d16d7488d51daa7721b7f91b` precedes implementation. The isolated harness integrates D118's exact adaptive codec with D117's lifecycle correction. Independent AST comparison verifies that the ordered client-cursor producer changes only its packing call and request admission remains identical. Every vector is packed before transport advances; original Snapshot construction, exact identity, validation, cache rollback and root/reader ownership remain intact. Compact3072-byte payloads require full binary64 roundtrip; any mismatch keeps raw64/6144bytes. No kernel/consumer/SQL/scan/limit change. [E376][E379]

Exact target verification reads the pinned SIF and OCI archive as data: full image/config/layer pins reconcile and ten selected source/ELF files independently match. The target formatter module matches the approved NumPy2.5.3 source exactly; full private-driver hooks and query parser remain pinned. Target CPython3.12.15 is distinct from local3.12.7. Local tests reject the actual local packet as target; supplied target metadata is a comparison only. No target code was executed, version wildcard or dependency update introduced. [E377][E379]

All **272source+272code-snapshot cases** pass with identical IDs, exact local provenance, no errors/skips/denied actions and zero real SQL/DB/ANN/exact/provider/Torch actions. These include142unchanged resource/lifecycle,56original A3,38memory-component and36new integration cases. Tests cover mixed/fallback producer rows, actual bounded startup and all injected sampler/cancellation/shutdown failures, strict retention, relocked proof tampering and resealed source-map forgery. All5,526prior files/2,931,529,861bytes, main128+128/A3 56+56native proofs and previous records are preserved. Initial import-precedence failure and corrected271-case run remain recorded. [E378][E379]

New source maps, module origins, target/formatter pins and literal/count/payload/matrix proofs supplement every old verification rule. Boolean/float counter aliases fail. Metadata-only full-count replay reports `offline_adaptive_startup_replay_native_held`; old native packets cannot qualify the new codec. Native release rejects both profiles before parsing old receipts; producer specs remain <=64-row fixtures. Production builders and CLI entries stay disabled. Original1h/4CPU/32GiB, all stage/sampler/cleanup caps,1+4scans/200admissions/10readers/zero searches and maximum finite-ancestor aggregate peak+2+2GiB rule remain unchanged. [E376][E378][E379]

D119 completes offline startup integration and reference verification. Exact-image runtime semantics, full-size formatter/identity CPU cost, compactability, native sampling/shutdown and aggregate headroom remain unqualified. No native capsule, transfer helper, Torch command, reservation or allocation is created; no spent allowance is reused. Next: separate exact-image correctness/CPU-budget review before any resource qualification design. Full B2f remains held. [E379][E380]


### 2.62 Exact-image correctness/CPU review complete; full target qualification held

Review freeze `5cdd6329d788690142d893f30307a3851327402c3f1271695ff2f2f98cba8742` precedes new review code and pins all72source/snapshot files, full target/local references, original science and5,697prior files. The separate test-only fixture selector expects the real complete target packet for synthetic preflight; it never spoofs actual provenance or edits reference files. Four local guard cases pass. All272+272original local cases and128+128/56+56native proofs remain byte-identical. No production code or dependency changes. [E381][E384][E385]

The exact cached image configEA708… runs with no network, read-only root/workspace, dedicated output writes, finite deadlines and unchanged4CPU/32GiB maxima. Docker reportsamd64image on anaarch64host. The source full-suite attempt emits a QEMU target SIGSEGV during import and hangs; it is preserved then explicitly stopped (exit137,OOMKilledfalse). No full correctness cases complete; snapshot full-suite execution is held after the prerequisite failure. A diagnostic freeze precedes five isolated60-second probes: Python3.12.15,NumPy2.5.3andpsycopg3.3.6import successfully; standalonePyArrow and pinned-fixture imports fault while loadingpyarrow.lib. This is an observed emulated-environment failure, not a candidate bug or native Torch verdict. No PyArrow stub, allocator/SIMD/dependency workaround or interpreter wildcard is used. [E383][E385]

A supplemental prospective kernel freeze then permits only the real codec/original canonical/frame/matrix path without importing PyArrow or constructing Snapshot. **32source+32snapshot kernel cases** pass in the exact interpreter/NumPy image, with binary64 bits, integer categories, signed zero, canonical/frame identity and float32 bits preserved. Full driver/library provenance and full-suite correctness remain explicitly false; none of the planned272+4target cases is relabeled as passed. Both phases record60bounded timing measurements under original probe caps. [E384][E385]

CPU review observes768encoding+768canonical decoder calls per compact float vector, and1536+768for compact integers:379,831,296or569,746,944calls at full row count. The600-second stage allows only2.42634ms total per row, shared by every startup/admission cost; serial formatting cannot divide by four CPUs. Mac producer projections252–411seconds for compact profiles omit native transfer/setup/admission overhead. Exact-image emulated kernel projections exceed600seconds even for oldpacked64, so they qualify neither a Torch pass nor failure. No extrapolation is added to/subtracted from the historical193.633-second native snapshot-to-epoch trace. [E382][E385]

D120 closes this requested review with full target correctness, native CPU/memory and B2f held. Independent audit preserves5,697files/2,938,746,208bytes, all tests, original limits/scans/verification/root lifetimes and aggregate-peak+2+2GiB decision. Next: a separately frozen compatible non-emulatedx86_64exact-image execution path for the complete suite and full startup-stage CPU/wall assessment. No new native capsule, Torch command, reservation, entitlement, retry or spent-allowance reuse is released. [E384]–[E386]


### 2.63 Separate native x86_64 qualification preparation record

This records the v1.73 preparation state. The user-executed job and spent allowance are closed in section 2.64; E389 is historical and must not be used to resubmit.

User-authorized qualification preparation is prospectively frozen at `8da59a6cb15fabe303ec34babc884b168399f7d42e5964eb51e87962b93a20aa`. A new name/prefix/reservation and scratch root isolate one fresh qualification allowance. All earlier jobs/reservations remain spent; durable and in-memory dispatch guards reject stale/uncertain/rejected state and any repeat. Verify/upload/status/collect/download cannot silently submit. The original main/A3 source, every test, private references, all resource limits and memory decision are unchanged. [E387][E390]

The capsule ships its exact input closure and one127-file frozen payload, binding byte-identical aliases read-only. Native preflight requires Linuxx86_64,ELF62,Intel/AMD CPU evidence, no QEMU/Rosetta indicators, four distinct pinned physical-core pairs, exact3.12.15/image/driver/library references and final protected source/SIF checks. Complete native execution will run128+128main and272+4A3 cases per source/sealed phase, with original seed/build/clone/reseal/binding proofs, per-case outcomes, cleanup, timing, locks and terminal scheduler evidence. No real DB/server/provider/search is permitted. [E387][E390]

Whole limits stay1h/4physicalCPU/32GiB,3000s guest including600s cleanup,240s host pre/post and120s outer margin. Guest caps30/420/90/420/600/600/180/600total2940s plus60s bookkeeping. The CPU phase retains120CPU/180wall caps, five fixed profiles,16/64rows and three repeats; it can qualify exact-native bounded measurements and a descriptive600s projection screen, not full startup CPU, compaction, native shutdown or aggregate memory. No automatic resource/main/B2f release follows. Finite phase caps are prospective, not demonstrated native upper bounds; failure spends this allowance with no retry. [E387][E390]

Local**128source+128sealed main**,**276source+276sealed A3**,**39source+39sealed qualification guards** and all60CPU samples pass. The initial local pass catches child bytecode after the parent's-Bflag was not inherited; failed evidence/bytecode is preserved, child setup is corrected without relaxing inventories, and a fresh full mirror passes. All5,757prior files/2,941,374,486bytes and original128+128/56+56native proofs reconcile. Final1,602-file/1,602-member regular archive,33,552,852bytes, all member paths/content hashes, source/sealed readiness and short-socket offline command stubs verify. [E388][E390]

D121 releases only E389's explicit new qualification handoff, not an actual launch. Capsule manifest SHA `1b8c3e7c9ec4e38523b00f440109e47da4c6be31f39737cac6929a70d955eac0`; archive SHA `1e894ff2bd4455d0f8751484242bcd5defb789c658bf7a8b11b1273287d7cb3a`. No SSH/SCP/Slurm/Torch action was executed. Next: user upload, login verify and this one submit; monitor/terminal collect/download even after failure. Never reuse old allowances or repeat submit. Native target/CPU results remain pending; full startup/resource/B2f gates remain held. [E388]–[E391]


### 2.64 Native x86 qualification failed at source-suite cap; allowance closed

User-run job **21595967** in campaign `reviews-startup-adaptive-x86-qualification-v1-20261101T182247Z.svgouzfl` is terminal `FAILED/1:0/00:22:46`. Its 47,804-byte archive SHA `334bedf6fcec3de2afe39d4c7001de62fcda73df676ca94b369893acc62eb8bf`, all 38 regular members/278,429 content bytes, extraction and exact 24-file guest/33-file host lock coverage verify. Both locks honestly retain `complete:false`; the unchanged strict analyzer rejects successful qualification. [E392][E393][E395]

Native hardware and full target reference match: Linux x86_64/ELF62/GenuineIntel, no detected emulation, four distinct physical cores, Python 3.12.15 and exact image/driver/library provenance. Main source and sealed suites each pass all 128 original cases, with strict source/origin/reference/guard/build/clone/reseal/binding proofs. Whole phases take 343.164/336.762 seconds. Candidate build passes in 42.115 seconds. [E393][E394]

A3 source stops at **600.019 seconds**: 165 exact original-order passes, then interruption in `test_resource.ResourceRuntimeTests.test_actual_framing_error_restores`, with no recorded assertion/error outcome. The first 56 original A3 and 38 codec cases passed; full integrated qualification remains incomplete. There are 110 unstarted source cases, 276 unstarted sealed cases and zero CPU measurements. The internal signal 14 alarm is the prospective phase cap, not Slurm's one-hour limit. Neither the incomplete test nor adaptive producer performance is established as faulty. [E393]–[E395]

Five completed resource replay cases consume 279.834 seconds, and five completed runtime cases 181.178 seconds; two preceding between-class gaps take 32.379/37.910 seconds. Actual fixtures already link large immutable seed files but still copy mutable/code files, reseal and run full verification. The return lacks native fixture-stage CPU/I/O attribution, so no hashing/filesystem/cache cause or safe optimization is yet isolated. Local readiness timings did not bound native cost. Do not extend the cap or skip/waive cases. [E394][E395]

Guest cleanup, stopped children, source/capsule/SIF preservation and host postflight pass inside original endpoints. All reported ANN/exact/real SQL/provider counters remain zero. All 1,602 capsule files, integrated/qualification sources, D121 records and 5,757 prior files are unchanged; the postrun preservation map covers 7,428 files including raw. **D122 closes this allowance spent with no retry or reuse.** Next is offline fixture construction/verification/I/O feasibility and prospective correction design only. Freeze any justified correction before implementation. No new Torch command, native entitlement or full adaptive correctness/CPU/memory/resource/B2f release. [E393][E395][E396]

### 2.65 Offline fixture-cost review; equivalent path construction locally verified

Before measurement, the review freeze SHA `b3b11543111f58fdafd9c3e11aeeb1856fae238067351476bd4469d1cbb362f7` binds original source/reference/test/limit identities and one guarded complete local diagnostic. All 276 baseline cases pass in 257.506 wall/251.757 CPU seconds under cProfile. Counts show 50 runtime fixtures, 89 full verifier calls, 292,688 file hashes, 170,854 path checks and 54,392 file copies. Local path/stat/hash work is substantial; the failed native trace still lacks a CPU/I/O subdivision. Inclusive profiler costs overlap and cannot be added or transferred to Torch. [E397][E399][E401]

Source review identifies unused ancestor construction in `safe_file`: it eagerly builds every absolute parent, including ancestors above the verification root, then builds another parent sequence for containment. A separate correction freeze SHA `2cddb3bf29b385c5ee5be8643da7143556b56d4bb79a057004f4d3d5e65ae056` precedes code. The new local wrapper substitutes only this pinned checker and keeps every ordered fresh resolution/symlink observation, input rejection and proper-descendant condition. It constructs parents only until the root and checks a resolved separator-delimited prefix. No SHA, whole verifier, build, copy, reseal or production/main/A3 file is replaced. Nesting and lost/escaped bindings fail closed; aliases restore on success/error. [E398][E400][E401]

All **128 source +128 sealed main**, **276 corrected source +276 independent code-snapshot A3**, and **26+26 differential/helper cases** pass. The baseline adds a further unchanged 276-case observation. Source/case/order/module-origin/full-reference/guard/binding proofs and all 7,490 prior files/3,354,878,626 bytes verify. Both corrected A3 runs retain exactly 292,688 original hashes, 89/88 full/scientific verifier calls, six build requests/eight input copies, 25/66 builder/fixture reseals, 50 fixtures, 54,392 copies, identical requested copy bytes and 500 links. Fresh observations remain **341,707 resolutions/975,641 symlink checks**. No digest/stat/verification cache, omitted case or weakened check is introduced. [E400][E401]

Profiled path-check time is 57.879 seconds baseline versus 44.197 corrected source; whole observations are 257.506, 242.904 source and 240.511 snapshot seconds. These local diagnostic observations support less Python object work without qualifying a native speed factor or 600-second bound. Remaining hash and filesystem work is substantial. Blanket writable links, cached digests and larger/borrowed budgets are rejected; shared seeds, parallel tests and alternate storage require separate isolation/capacity/execution/memory designs. All limits and the aggregate memory decision remain unchanged. [E400][E401]

**D123 completes offline review/local correction only.** Next: a separate native feasibility/storage and verification-cost design that establishes a prospective complete-budget path while preserving all checks. Native exact-target execution, suite fit, producer CPU, startup memory/shutdown/resource and full B2f remain held. All allowances, including 21595967, are spent. No Torch launch, native capsule/command, new entitlement or retry. [E401][E402]

### 2.66 Native budget/storage review; conditional plan and real local admission hold

Review freeze SHA `ffffd3ec1a135b5a1fbdc939f57e34e55fd0275928b78c8dd9db5d7efa4275d0` precedes source/documentation/capacity review. One guarded unchanged synthetic build inspects the 999-file/597,058,181-byte A3 seed. Correction freeze SHA `3e7d190787cf3ff0b761325c3182f9e5eea3af37de0d3cb38015e6c8d0f6de2a` precedes an offline exact-archive staging/admission prototype. Native host, guest, controller, main, A3 files and old decisions remain unchanged. [E403][E404][E407]

The candidate uses an admitted job-private disk directory for byte-identical inputs and temporary correctness fixtures, preserving all original absolute/read-only destinations, image/results identities and full verification. NYU documents `SLURM_TMPDIR`, but the failed return contains no corresponding mount/device/quota/capacity/speed or persistence proof. RAM/shared/unknown storage and unknown user quotas are rejected by the pure record policy; even positive synthetic records retain native qualification/release false. No native collector or mount/container action is executed. [E404][E407]

The conditional capacity envelope is **7,379,306,398 bytes (6.87GiB) /22,498 entries**, inside unchanged **8GiB/30,000** guards. It includes staged input/view, main seed/candidate/archives, four A3 seeds retained conservatively, one full A3 fixture, all ten main mutable clones, original return bound, rounding/metadata and 2GiB/4,096-entry planning margins. Original serial lifetime, immutable-link rules, allocation unit and temporary-output assumptions remain explicit and require full replay/native admission. This is no native high-water measurement or aggregate-memory proof. [E405][E407]

The whole **240+3000+240+120=3600s** budget and all guest phase caps **2940+60=3000s** stay fixed. A new pure policy reserves at least30s for container startup inside preflight: latest launch admission at host start+210, guest readiness by+240 with full guest/post/outer reserves still available. Later/nonfinite/boolean/backward times reject. Native staging, suite and postflight/failure-retention timings remain unproved; no local multiplier is used. Existing native host code is not patched or retrospectively reinterpreted. [E404][E406][E407]

**35source+35snapshot unit checks pass.** Initial31-case/three-error evidence and exact initial source are retained: small positive fixtures initially relied on insufficient real Mac headroom; explicit synthetic capacity now exercises archive internals, while the real guard remains unchanged. Actual Mac admission sees **4,293,951,488 bytes**, below8GiB, and rejects before output creation. Full real staging/new128+128/276+276 integrated replay is **not run**; old passing proofs remain preserved rather than relabelled. Independent streaming verifies all1,602members/372,726,842content bytes without extraction and all10,076prior files/4,608,361,259bytes unchanged. [E406][E407]

**D124 completes the review with full local/native release held.** First obtain at least8GiBreal Mac headroom without deleting protected evidence, then complete integrated local staging/replay. Native release further needs actual job-private storage/quota observations, complete target/timing/memory proofs, controller/binding integration and failed-diagnostic retention inside unchanged post/return limits. No native command, capsule, new allowance, Torch launch or spent-allowance reuse is released. [E407][E408]

### 2.67 Mac capacity recovered with complete evidence preservation

The prospective local preservation plan and verified backup precede replacement of22 byte-identical frozen inputs by independent native copy-on-write clones. All54 candidates retain their contents, complete metadata and exact creation nanoseconds; canonical and unconverted inode/link identities remain unchanged. Existing hardlink groups are excluded. The first metadata attempt stopped before replacement; its exact code/log and the subsequent successful correction/probes remain retained. No prior evidence/test path or byte is deleted. [E409][E410][E412]

Full independent hashing verifies173,943 protected files/17,129,611,037 bytes unchanged. The compressed payload backup, clone-write isolation, physical restoration, per-path metadata and parent timestamps verify. Available Mac space rises from5.03GiB immediately before application to10.40GiB at the final audit, above unchanged8GiB admission and the10GiB cleanup target. The first audit's final timestamp-restoration type error and corrected passing full audit are both retained. Prior main128+128/A3276+276/helper26+26/storage35+35 proofs are preserved, not relabelled as new runs. [E411][E412]

**D125 closes the local storage task only.** Full exact-archive local staging and integrated replay is next; native target/timing/storage/quota/memory/shutdown/resource/B2f gates remain held. All spent allowances stay spent. No Torch launch, native capsule/command, search, provider call or guard reduction. [E412][E413]

### 2.68 Full local exact staging and integrated replay verified

The existing D123/D124 design now completes exact staging of all1,602 files/372,726,842 content bytes with three original semantic-verifier boundaries and complete final original/staged/view integrity. The existing project interpreter matches the full frozen local provenance, including hook/parser hashes. All128+128 main,276+276 A3,35+35 storage and26+26 path-helper cases pass with exact IDs/outcomes/origins and60 bounded CPU samples. The original72-file A3 source/snapshot and all scientific/verification limits remain unchanged. [E416]–[E419]

Each A3 phase retains292,688 original SHA calls,341,707 fresh resolves,975,641 symlink checks and50 original runtime fixtures. Passive observation confirms at most one live fixture root and restored bindings. The frozen capacity envelope and all phase/whole/cleanup/post/raw caps hold locally; these sampled local storage/RSS/time observations supply no native capacity, quota, timing or aggregate-memory qualification. Full hashing verifies185,133 prior files/22,460,438,507 bytes unchanged. [E418][E419]

The first local supervisor stops before tests on an unsupported Darwin virtual-memory hook; a prospective supervisor-only RSS correction retains the scientific32GiB rule. The second local attempt passes helper cases but stops main before cases on the shell interpreter's missing psycopg. A prospective correction selects/pins the existing full-reference project interpreter and verifies provenance before staging. A third local supervisor error follows all128+128 main/276 A3 source passes; a further prospective correction records PIDs/tracebacks and handles only proved exit races, uses lstat and permits owned-process monitoring/signals outside the tool sandbox. The original primary syscall is unproven and all v3 evidence is retained. All preceding attempts, partial data and passing preservation audits remain retained; no dependency or original source/test/helper/native code changes. [E414]–[E419]

**D126 completes full local staging/integrated replay only.** Native exact-target correctness, CPU fit, real job-private mount/device/quota/storage observations, aggregate memory/shutdown/resource evidence, controller/binding integration and failed-diagnostic retention still precede any separately authorized handoff. No native command/capsule, Torch launch, search, new entitlement, spent-allowance reuse or B2f release. [E419][E420]

### 2.69 Offline native harness integration verified; target entry closed

Prospective freezes precede a separate host/guest/controller integration and disabled target adapters. It binds all source/input/runtime/storage identities, rejects stale/known/uncertain/spent dispatch, preserves the original strict staging/readonly aliases, reserves startup inside240s, and delegates all science to the original child/proof validator. No scheduler or native grant is supplied. Target hardware/runtime paths exist but every target entry remains closed. [E421]–[E423]

All81+81 new integration,39+39 original controller,35+35 storage,26+26 path,128+128 main and276+276 A3 cases pass with60 CPU samples. Original full hash/fresh-path counts,50 fixtures per A3 phase, one live root, origins/references/snapshots, all phase/whole/post/raw caps and189,345-file/24,161,087,701-byte preservation verify. The new real597MB/1,000-file failed-fixture proof reconstructs every byte from verified persistent immutable references plus bounded payloads in under2MiB of diagnostics; no truncation/omission. [E424][E425][E427]

All raw records write persistently. The original32MiB/256-file return includes1MiB checksummed control reserve. Failed work is captured after original cleanup/owned-child exit; cap/time/race/special/authority loss explicitly holds completion. A bounded second COW preservation frees headroom without deleting evidence; all17 paths/content/metadata/hardlink invariants verify. Initial local check failures and exact sources remain retained. [E424]–[E427]

**D127 closes offline integration/local verification only.** Actual native job-private/persistent quota/placement authority, exact target/CPU/timing/storage/persistence, aggregate memory/cache/events/shutdown/resource and worst-case retention bounds remain unqualified. A distinct future release/entitlement review is required before any native handoff. Every older allowance stays spent; no Torch, new allocation, search/provider call or B2f release. [E427][E428]

### 2.70 Offline native release review complete; qualification handoff HOLD

Independent source/trace probes expose late readiness arrival accepted with an older start, missing standalone guest handlers, publication outside the accounted endpoint, direct-leader-only native cleanup and incomplete shared target binding/admission. A prospective review/correction/endpoint freeze precedes a separate candidate. Arrival is independently checked, original signals cover publication, writes share cleanup600/post240, completion requires independent exit, native groups require a qualified controller and full frozen manifest/mount/image binding reconciles. No authoritative native group backend or admission issuer is supplied; both native gates stay closed. [E429][E430][E431]

All81+81 original integration,55+55 new release,39+39 controller,35+35 storage,26+26 path,128+128 main and276+276 A3 checks pass:1,280 checks plus60 CPU samples. Original IDs/events/origins/references/full hashes/fresh paths/fixtures and all limits verify. Complete exact staging, publication-inclusive timing, independent local parent exit and195,784-file/27,123,306,137-byte preservation pass. The byte-identical retention code and existing1,000-file/597MB lossless proof are independently reverified without another large copy. [E432][E433][E434]

**D128 completes this offline review, not a native release.** A prospective correctness/CPU handoff still needs concrete qualified native authority/owned-group and live storage/admission/return machinery plus distinct authorization/unspent allowance. Live native observations must be validated within that separately authorized job; complete target/CPU results are its intended outputs. Subsequent resource/B2f release additionally needs complete target/CPU and aggregate memory/cache/event/shutdown/source/return evidence. All old allowances stay spent. No Torch, native capsule/command, new grant or searches. [E434][E435]

### 2.71 Offline authority/ownership backend implemented; native handoff HOLD

A prospective freeze and bounded amendments precede a separate backend. Strict independent permission/site anchors bind immutable code/image/limits/commands, live kernel generation and same-process single-use claims. Production root sets are empty; native authority remains closed. A real Linux guardian registers an exec-blocked child, pins process descriptors and adopts orphaned/session-detached descendants. Stat enumeration is discovery only: successful completion requires direct status, kernel ECHILD, terminal pipe proof and independently observed guardian exit. Scientific nonzero status is preserved. Known-descriptor cleanup remains bounded on authority/observer loss, which always holds qualification. [E436]–[E438]

All 68+68 authority/race/budget/publication models,17+17 actual Linux cases,136+136 inherited integration,39+39 controller,35+35 storage and26+26 path checks pass:642 fresh checks. Exact source/snapshot-v3, old bytes/IDs/origins, shared original proc-read ceilings, publication endpoints and 200,143-file/28,833,842,186-byte preservation verify. Existing128+128 main/276+276 A3/60 CPU proof is freshly reconciled without science re-execution, new full staging or data copies. Local aarch64 Linux kernel tests establish ownership primitives, not x86 scientific correctness, native CPU fit or aggregate memory qualification. [E439][E440][E441]

**D129 closes offline backend implementation/local verification only.** Host/guest adapter wiring, cross-process authority handoff and practical authenticated site-attestation acquisition/provisioning need a prospective integration design. No actual site credential, production root or fresh allowance is issued. A distinct future native release review/authorization remains necessary; target/CPU/memory/resource/B2f and all spent allowances stay closed. [E441][E442]

### 2.72 Offline native integration verified; read-only Torch site check ready

A prospective design and bounded freezes precede host/guest adapters, nested ownership, a shared observer ledger and an immutable pending qualification package. Existing root-owned installed Slurm client/controller authentication plus live UID/job/comment/node/cgroup checks replace the prototype's unproven per-job privileged issuer requirement. A private explicit single-use approval and durable dispatch reservation remain mandatory. Root helpers are monitor-only; actual descriptor exit and ECHILD remain required. Bounded control reads prepay a conservative slice of the original combined ledger. A separate PLAN-bound login adapter compares stable authenticated configuration and retains changing response digests. No scientific source byte is changed by that adapter. [E443]–[E446]

All128+128 main,276+276 A3,278+278 combined models,100+100 old helpers,24+24 actual Linux cases/probes,16 installer,11+11 login adapter,2 read-budget probes and4 sealed CLI scenarios pass:1,656 checks plus60 CPU measurements. Full exact staging, original IDs/events/provenance/fresh hashes/paths/fixtures, all deadlines, independent exit/publication and205,032-file/30,662,112,708-byte preservation reconcile. All43 D129 files remain byte-identical. Earlier failures/replays and all tests are retained; verified COW preserves paths/content/metadata/link groups with inode/ctime changes disclosed. [E446]–[E450]

The1,768-file bundle retains the exact original archive/image references and has no active approval. Mac upload and read-only Torch install/site-check commands are ready; no remote command has run. Actual site/account evidence and explicit authorization for one distinct1hour/4physicalCPU/32GiB zero-search allocation precede submission. Complete non-emulated x86 exact-image correctness/CPU are that future job's outputs; actual storage/placement/quota and strict return must pass there. Aggregate memory/cache/events/sampling/shutdown/resource/B2f remain later gates. Every spent allowance stays closed. [E449]–[E453]

### 2.73 Exact site-prefix compatibility verified; live site/account handoff pending

The user-run installer verified the exact original package, then the root-only ancestor policy held at /opt/slurm. Actual scontrol/sbatch leaves and bin are root-owned; only the unwritable0755 prefix is UID1001:GID1001. A prospective separate admission layer adopts an explicitly recorded, NYU-documented site-prefix policy: exact prefix/owner/group/mode only, root leaf/bin/other ancestors, no caller/world/group write, no unknown client/path and actual generation/hash verification. The same bound layer runs before login and allocated-host controls, while all71 scientific integration files stay byte-identical. Stable identity retains local generations as observations across login nodes. [E454][E455]

All57+57 new models,278+278 inherited integration,11+11 original site models,5+5 real Linux cases,16 installer and4 exact sealed CLI cases pass:722 fresh checks. Complete211,278-file/32,907,014,918-byte preservation and the exact old128+128 main/276+276 A3/60 CPU proof are freshly reconciled without a scientific rerun or new8GiB staging. Old packages/attempts/tests remain intact; all scientific references, strict verification and limits are unchanged. [E456]–[E459]

The configured account users is not silently changed or assumed invalid. The new read-only handoff collects current-user associations and cs partition data; future submission requires the intended historical torch_pr_288_courant association and matching explicit account setting. Actual site/account/partition output and distinct new allocation authorization are pending. Every prior allowance stays spent; no Torch/SSH execution, ANN/exact search, SQL/provider call or new grant occurred. Native target/CPU/resource/B2f remain HOLD. [E459]–[E461]

### 2.74 Live site/project/partition review complete; distinct authorization pending

User-provided output verifies installation of the exact1,778-file candidate and reports Torch Slurm25.05.4/auth-munge, the expected frozen prefix-policy digest and authenticated cluster/controller fields. Current-user associations contain both users and torch_pr_288_courant. The cs partition is UP with AllowAccounts/Groups/Qos ALL, RootOnly NO, ReqResv NO and MaxTime UNLIMITED. The unchanged quota parser accepts the returned home/scratch report above the original conservative byte/inode minima. These are reported site observations, not native scientific/resource qualification. [E462][E463]

The configured environment still says users. The reviewed conditional block sets only that invocation to the intended project after sourcing torch.env; no environment file or package edit is needed. Wrong-account hold and corrected-account acceptance are locally exercised with the returned association data. Exact shell arguments and the explicit one-allocation approval statement are verified with local stubs; no real approval/controller/Slurm execution occurs. All original source/sealed tests, science, references, limits and spent-allowance guards remain unchanged. [E463][E464]

D132 releases a concrete proposal for user review only. Explicit authorization of one distinct1hour/4physicalCPU/32GiB zero-ANN/exact no-retry qualification allocation remains unissued. Knowingly executing the reviewed approve-and-submit block would record that new authorization and submit once; the assistant has not done so. Original fresh site/account/quota/statvfs/image/dry-run checks still precede dispatch. Actual job-local storage/quota, cgroup/UID/node, non-emulated exact x86 runtime, all tests, CPU/deadlines/cleanup/return remain future job outputs. Native memory/resource/B2f and all old allowances stay closed. [E464][E465]

### 2.75 Distinct new qualification authorized and submitted; outcome pending

User-returned output contains the exact explicit new one-allocation approval statement and final submitted dispatch for job21756110. PLAN08a9293c... and manifest13d281a4... match the immutable619d4288ca7a candidate. Account torch_pr_288_courant matches the intended current association; the stable Torch/auth-munge/client/policy identity remains valid across a different login node. The displayed site-check counters describe that read-only substep; the final dispatch record commits the new allowance. [E466][E467]

The1hour/4physicalCPU/32GiB zero-search/no-retry allowance is now committed to this job and cannot be reopened or automatically resubmitted. All older spent allowances stay closed. No code/source/package/test/reference/limit changes occur. Actual queue/running/terminal state and all native scientific, exact runtime/hardware, CPU/deadline/cleanup/return outputs remain unknown pending status and terminal raw. Successful submission grants no target/CPU/memory/resource/B2f verdict. The assistant performs no remote action. [E467]–[E469]

### 2.76 New qualification fails allocated preflight; allowance closed, raw review pending

User status reports parent/batch FAILED/1:0 after38seconds,4CPUs/32G, with preflight-failure ValueError Outside the frozen site-prefix scope and native_qualification false. Extern completion does not override the parent failure. The final live-queue invalid-job message occurs after terminal removal; accounting still records FAILED. The new21756110 allowance is now spent and cannot be reapproved or resubmitted. No native scientific/CPU/resource verdict exists. [E470][E473]

Source isolates that message to fallback validation outside the narrow Slurm site-prefix policy. The short receipt does not reveal whether the allocated host rejected its Slurm client, recorded Apptainer path, or configuration/library path. Original chained scheduler traceback and complete persistent raw are required before a justified correction can be frozen. The427216K batch preflight MaxRSS is not an aggregate scientific memory result. No guard is relaxed and no source/package/test/limit changes. [E471]

The existing controller's collect command independently verifies terminal accounting and preserves the original whole32MiB/256file cap; the prepared command then prints scheduler-21756110.log. A separately checked Mac helper pins the previously trusted DTN key, creates a new local return directory and verifies checksum/member limits/job identity without extraction. Only local fixtures run; no assistant remote retrieval or new allocation occurs. Next is independent raw path/role/startup review. All older evidence and allowances remain closed and preserved. [E471]–[E473]

### 2.77 Allocated SLURM_CONF validation failure isolated; full raw download pending

The user runs terminal collection successfully and returns the original chained scheduler traceback. Allocation construction completed Slurm-client and recorded-Apptainer validation, then failed during the first --version probe's environment construction. trusted_data(os.environ[SLURM_CONF], configuration) rejects a leaf/ancestor under the original root predicate, and the exact configuration-prefix fallback reports Outside the frozen site-prefix scope. No first Slurm probe subprocess or scientific phase was launched. [E474]

This establishes the failing role, not the actual variable value/resolved path or rejected UID/mode/write condition. The traceback alone does not justify treating a guessed cache path as trusted, unsetting configuration blindly or widening the policy. The complete persistent return is collected remotely and must now be downloaded/verified. No code/package/test/limit changes, new allowance or retry occur. Job21756110 stays spent/closed and all native scientific/resource verdicts remain unqualified. [E475][E476]

### 2.78 Complete failed21756110return verified; historical configuration metadata still missing

The user downloads the already collected return using the pinned-key helper. Independent verification streams every one of9regular files/16,283bytes without extraction, rejects unsafe members/duplicates/oversized content, and reconciles SHA-256, receipt, approval, account, plan, submission and terminal records. Parent/batch FAILED1:0/38seconds and the exact SLURM_CONF traceback agree. No scientific phases launched and native_qualification remains false. [E477]

None of the9files records the allocated runtime variable value, resolved configuration pathname or rejected component ownership/mode/write access. No specific exemption, default-path selection or environment bypass can be justified. A login-only diagnostic verifies the unchanged packet/policy, inspects current login path metadata and requests only21756110accounting/stored environment through the existing trusted/bounded client. It prints selected configuration candidates only. Four local mocked cases pass; no actual scheduler client executes during local review. [E478]

Slurm25.05.4 documents optional environment retention and forces SLURM_CONF during environment setup. Stored submission values and current login metadata cannot alone prove historical compute-node state. Missing evidence does not authorize another allocation. The full existing package inventory and original pins/71scientific source files remain unchanged, preserving128+128main and276+276A3 tests, strict verification and limits. Job21756110and all earlier allowances stay spent/closed; native correctness/CPU/memory/resource/B2f remain unqualified. [E479][E480]

### 2.79 Login/accounting metadata route exhausted; site-provenance request prepared

The user runs the checked read-only diagnostic successfully: the packet/policy checks pass, accounting identifies cs624 and FAILED1:0 for21756110, current login SLURM_CONF is null, and stored environment returns NONE with no configuration candidates. NONE does not identify the actual retention settings or reconstruct allocated runtime state. The original launcher does not set or source SLURM_CONF. The existing trace still establishes a nonempty strict-resolved allocated configuration path rejected before the first Slurm subprocess. [E481]

Actual pathname, rejected component ownership/access and the supplying site mechanism remain unknown. The next evidence route under the no-new-allocation constraint is NYU HPC support using existing logs/site configuration. The local unsent request asks for the complete path/symlink/UID/GID/mode/ACL chain and supported compute-node provenance; if history is unavailable it requires current-layout evidence to be labelled as such. It explicitly requests no resubmission, diagnostic allocation or cluster configuration change. No support message is sent by the assistant. [E482][E483]

No guessed cache exception, allocated-variable removal, default-path bypass, compute-node login or policy implementation occurs. Fresh original package inventory and source/evidence pins verify; all71scientific files,128+128main/276+276A3 tests, strict verification and limits remain unchanged. All spent allowances stay closed and native correctness/CPU/memory/resource/B2f remain unqualified. [E484]

### 2.80 Alternate client configuration provenance route frozen before implementation

The user requests an alternate solution. Independent matching-version source review finds that Slurm25.05.4 can serialize current controller/node/partition configuration to an explicit caller-selected local file. The prospective route is to capture that output through the already trusted working login client, validate the actual serialized bytes and complete client dependency closure, pin them with the controller/auth/client anchor in a separate pending PLAN, and supply a kernel-sealed copy only to our scheduler client subprocesses. Historical21756110metadata is not a prerequisite to using a separately qualified future input. No export permission, parser validity or portability is assumed. [E485][E486]

The new design explicitly excludes blind environment unsetting, guessed cache/non-root-owner exemptions, implicit default export destinations and cluster reconfiguration. Existing arbitrary-path root guards, executable/loader checks, munge authentication, job/account/comment/resource checks and kernel allocation authority remain. A new admission wrapper must also enforce the pinned controller identity before authority succeeds; returning AuthType alone is insufficient. Includes, plugins, AuthInfo and relative auxiliary configuration semantics must be resolved; relocating only the main file to a sealed descriptor is not automatically sound. Linux sealing and exact client compatibility need actual tests. [E485][E486]

This is a frozen alternative design, not an implemented correction or release. Next is a bounded login-only snapshot capture helper, local verification and actual user-run export without an allocation, followed by source/snapshot admission and exact-version read-only client checks. All71scientific source files and original site/evidence pins verify unchanged. Preserve128+128main/276+276A3 tests, strict verification, references, limits and every prior artifact. The support draft remains an optional forensic route. All old allowances, including21756110, remain spent/closed; actual future native qualification still needs a separately authorized new allowance after packet review. No such grant is sought or issued now. [E487][E488]

### 2.81 Login-only configuration capture command locally verified and ready

Under a separate capture freeze, the helper checks Torch x86 login context outside allocations, original packet/PLAN/admission policy and semantic references, conservative original quota/headroom, and the exact previously observed Slurm25.05.4 client SHA. It runs baseline/post version/config queries against the known controller/auth/cluster anchor and exactly one native write config with an explicit fresh private output base. It never invokes reconfigure/update, approval/submission, loads a captured configuration or writes previous state. [E489]

The helper retains private logs and a SHA/manifest receipt under a new0700result directory. It enforces10second command bounds with at most1second owned group cleanup,64KiB combined output, an inherited1MiB kernel file-size soft cap never raised, and a conservative2MiB/16file whole capture inside original32MiB/256file ceilings. Missing, empty, unsafe, linked, changed or cap-reached exports and identity/permission/output/deadline failures hold without retry. Native writer exit0 alone cannot succeed; captured_pending_configuration_review explicitly leaves syntax/dependency/admission/native flags false. [E489]

All32source+32independent snapshot tests pass, including actual local fixture subprocess file-size/output/deadline/owned-child cleanup behavior, semantic original packet verification, plan/client/auth/controller races, private raw hashing and protected spent-state preservation. Linux/Torch identity and all scheduler RPCs are mocked; no native Slurm execution or Torch qualification is claimed. Earlier29case pass and exact inputs remain evidence. Original34site/evidence pins,71scientific integration files, full packet/archive/references and preserved full128+128main/276+276A3/60CPU proof verify unchanged. [E490][E491]

The exact copy/paste command body matches checked source and passes shell/Python syntax. Next is one user-run login export and return of the final JSON naming its new directory/SHA; permissions/completeness remain unobserved until that happens. Captured bytes still need private download, full directive/dependency review and exact-version sealed-input compatibility before any new pending qualification packet. All old grants including21756110remain spent/closed; no new allowance is requested or issued. No assistant remote command, actual export, scientific SQL/provider call or ANN/exact search occurs. [E492]

### 2.82 Current login configuration capture reported successful; exact raw download ready

The user reports captured_pending_configuration_review on torch-login-a-0 with16,647configuration bytes, SHA-256 ba998cfda785eee87ef65023a8fe2caf4f7c3734665eb15af5b76d5a2b603ea6 and manifest0ef4872fd4a60229dd5545d764bebc85998d036347d5555ba1be6ed9d2c9f6f2. The expected client SHA, explicit site-prefix component ownership and controller/cluster/auth anchor match. Reported allocations/ANN/exact searches remain0; syntax/dependency/configuration/native flags remain false. Full raw verification is still pending, rather than inferred from terminal echo. [E493][E494]

The prepared Mac helper pins the previous trusted DTN key and exact local code/receipt/scope, fetches only9known rootfiles plus the explicitly named configuration into a fresh private folder, and requires manifest/receipt/content/command/quota consistency under unchanged bounds.14local adversarial and mocked transfer cases pass; no real SSH/scp/export or scheduler command runs locally. No remote packaging or export retry is needed. Next is the exact existing capture download, then complete configuration/dependency review before any use. [E495][E496]

Original released capture/delivery,34site/evidence and71scientific file pins verify unchanged, preserving all128+128main/276+276A3 tests, strict verification, limits and prior evidence. All spent allowances including21756110stay closed. Native target correctness/CPU/memory/resource/B2f remain unqualified; no new grant or job is issued. [E494]

### 2.83 Actual snapshot verified; unchanged candidate and scoped use frozen

All10rawfiles/40,601bytes independently reconcile to the reported capture, including configuration16,647bytes/SHA ba998cfda785eee87ef65023a8fe2caf4f7c3734665eb15af5b76d5a2b603ea6, exact manifest/receipt,5expected commands, identity and conservative quota minima. Baseline/post configuration logs are byte-identical. Static inventory finds192active records/130top-level keys, no active Include,9groups defining374nodes and55partitions with defined node references. All top-level keys match the release schema with native case-insensitive spelling rules; this is not full Slurm syntax/value validation. [E497][E498]

Review of19matching-tag public source files supports normal MUNGE client authentication without daemon JWT alternatives under the preserved environment filter. Private JWT-key copying is excluded. Client startup also invokes certificate-generation/hash/connection/accounting/GRES-context/credential initializers; actual installed plugin/library closure and implicit relative auxiliary inputs remain open. Exported InteractiveStepOptions is shorter than the expanded show config value, so general Slurm round-trip equivalence is not claimed. Failed source retrieval and an initially case-sensitive schema precheck are preserved; only the reviewer was corrected, with no configuration or old code mutation. [E499]

The use policy is frozen before adapter implementation: retain exact captured bytes; an opaque verified kernel-sealed capability may serve only predeclared read-only queries after dependency and compatibility gates. Arbitrary-path/root/loader/auth/job/kernel checks remain; no sbatch/srun mutation/general-purpose config substitution, guessed cache trust or private-key access. Next is local compatibility/dependency harness work and then login-only validation; actual native allocation still requires a separately reviewed packet and distinct explicit grant. No such grant/job occurs. [E500]

Released capture/download/site/science pins,71scientific files, full packet and original semantic references verify unchanged. Preserve128+128main/276+276A3 tests, strict verification, limits and all prior evidence. All spent allowances including21756110remain closed; exact/CPU/memory/resource/B2f remain unqualified. [E501]

### 2.84 Read-only configuration compatibility harness locally verified; native gate closed

D142 freezes the separate harness before implementation and freezes deadline/read-bound hardening before correction. Final review also freezes and adds a pre-import package manifest/PLAN/complete-inventory/Python-source boundary; actual original packet and adversarial import cases pass before old code executes. Exact captured configuration bytes remain unchanged. The helper statically inspects installed ELF/client/plugin/library and loader metadata without executing inspected objects or Slurm; records candidate edges without claiming runtime-loader closure; preserves root-owned leaves/ancestors and only the exact prior installation-prefix ancestor exception. Private JWT keys are excluded. Native replay has no admitted in-code closure, so old jobs or supplied approval booleans cannot trigger it. [E502][E503]

All326final checks pass:74source+74snapshot on macOS,74source+74snapshot functional and15source+15snapshot kernel checks on real ARM Linux. Full memfd seals, denied mutation/mapping/truncation, proc-path reopening, explicit-only FD inheritance, cleanup/deadlines and held verification failures are exercised with fixture children. No deployed/native x86 Slurm or performance proof is inferred. The existing Linux image is pinned with networking disabled and read-only source mounts. Earlier prechecks, the first306-check completion, code snapshots and one incorrectly isolated synthetic interpreter fixture failure are retained; all test IDs remain. Both isolated CLI hold checks pass. Static AST/compile and Ruff F checks pass. [E504]

Fresh preservation verifies86old pinned artifacts,71scientific integration files,10raw capture files/40,601bytes, full original packet and exact semantic references. Earlier128+128main/276+276A3/60CPU replay receipts reconcile unchanged; science is not redundantly rerun. Original strict verification and limits remain unchanged. All spent allowances including21756110stay closed; no Torch remote command, allocation/search/scientific SQL/provider call occurs. [E505]

Next is preparation of the login-only installed dependency inspection command, independent review of returned installed/implicit-input evidence, and a separately frozen exact closure before any native read-only replay can open. Configuration/native admission remains false. Any later native allocation still requires its own reviewed packet and distinct explicit authorization. No such release or grant is issued. [E506]

### 2.85 Login-only dependency inspection command ready

The exact35749byte inspector/SHA b8725d26973a2cf7eeee3f0012c77ec4f7cbec251fa548a551d3e79fb2e1a793 is copied unchanged. A separate command freeze precedes implementation. The Mac uploader verifies local payload and the existing trusted DTN key before authentication, uses strict pinned dtn012 routing and a short private control socket, requires a fresh private destination and uploads only one file. It never overwrites a prior destination or submits work. [E507][E510]

The Torch block runs Python3.12 in isolated/no-bytecode mode. It requires a canonical owned private single-link payload and directory, exact size/SHA and stable descriptor/name/parent generation before compilation, and fixes argv to inspect. The unchanged inspector applies the exact login/no-allocation guard, old package pre-import/complete semantic checks, conservative quota and captured configuration pins, then bounded static installed metadata collection. Original myquota is the only quota subprocess; no Slurm client, loader, ldd, private JWT-key read, replay, approval or job launcher is invoked. Actual metadata/native closure remain unverified. [E511]

All29source+29independent snapshot tests pass without skips/errors/prohibited external attempts, including exact command body, pre-auth wrapper pins, real local bootstrap hold and mocked transfer failures. An initial source guard included its own actively written log; all27unit cases passed but the guard held. That precheck/code and the frozen input-list correction remain preserved; production behavior was unchanged. All326earlier harness-check receipts,34old site/evidence pins,71scientific files, full packet/semantic references and128+128main/276+276A3/60CPU proofs verify unchanged. Shell syntax, Python AST/compile and Ruff F checks pass. [E508][E509]

User upload and login-only inspection are next. Return/preserve the final JSON and bounded evidence for independent installed-dependency review before any separately frozen native read-only replay. Configuration/dependency/native admission remain false. No actual connection/upload/Torch command, job, ANN/exact search, scientific SQL or provider call occurs in preparation; all spent allowances including21756110stay closed. [E512]

### 2.86 Upload session failure reviewed; direct SFTP correction ready

The user authenticates a master connection, then the remote directory-creation session is refused and the BatchMode=yes fallback cannot authenticate. The traceback stops at mkdir before scp; the local held receipt verifies. This does not identify the exact server policy or prove a remote directory state. No inspection, qualifying workload or allocation ran. Original failed code/receipt and previous checks remain evidence. [E513]

Freeze then replace only upload transport: one direct SFTP batch connection, explicit BatchMode=no before -b, ControlMaster=no and ControlPath=none, no remote shell/master. The existing strict trusted dtn012/alias/key, no agent forwarding, exact35749byte payload and original Torch bootstrap stay unchanged. A fresh destination mkdir must succeed, chmod0700 precedes one put -p, then chmod0600; batch errors abort without overwrite, delete, resume or retries. [E516]

All14source+14independent snapshot checks pass. Real installed SFTP/local direct server prove exact bytes/permissions, existing-target abort and missing-source failure. A local fake transport captures actual SFTP argv and ssh -G confirms MFA enabled and mux disabled; real TERM cleanup stops the owned fake SSH process. No actual SSH/SFTP network connection occurs. Original29+29command and326harness proof,34site/evidence pins,71scientific files, full packet/semantic references,128+128main/276+276A3/60CPU proof, strict verification and limits remain preserved. All spent grants including21756110stay closed. [E514][E515]

User runs the replacement Mac uploader, then the unchanged login-only inspection block after success. Installed/native/configuration admission remains false; a transfer failure is not an allocation allowance and none is reused or issued. [E517]

### 2.87 Login preflight timeout reviewed; repeated verification removed under unchanged limits

User-reported execution passes pinned payload/login guards and completes the first S.C.verify. It then enters S.C.quota, repeats S.C.verify and expires inside its nested original common.verify SHA loop at120seconds. A following explicit core call is planned in the old source but never reached. Quota command, capture loading, output-directory creation and dependency inspection are unstarted; no allocation or search occurs. Exact phase durations/deployed dependencies are unknown. [E518]

Freeze then implement separately: keep the pre-import guard and one exact unmodified original full semantic verifier/default core; require pinned ni_control source and precise three-statement repeated quota prefix, then compile only the exact unchanged quota tail in a separate namespace after same-run success. No original module/global/function/file is patched, no verification cache/token is reused, and control source generation/hash is checked. Original quota parser/myquota/environment/statvfs thresholds/30scommand bounds and outer120seconds remain unchanged. [E518]

All424local checks pass:370Mac/ARM Linux source/snapshot functional/kernel checks plus54transport/bootstrap checks. Preserve all74old functional/15kernel IDs and add11source cases for one semantic pass, exact tail, quota return/failure boundaries, source/policy races and deterministic original deadline reproduction. Actual exact-target package verification independently records one full original verifier, one nested core and one mocked quota command with original parser output; only myquota/statvfs are mocked. Mac clocks/that cost model are not native runtime qualification. [E519][E520]

Strict direct-SFTP transport is retained with new pinned39512byte payload/SHA9b8870a49526dbd5309b34815202f0be74687822857eac47ce73659b21d06b7f and fresh directory; new bootstrap changes only path/SHA/size. Success text names the new block; all pre-release code/proofs are preserved. User upload and the NEW login-only inspection block are next. No actual network/Torch command, job, ANN/exact search, scientific SQL or provider call runs here. Every spent allowance including21756110stays closed. All original128+128main/276+276A3 tests,71scientific files, strict verification, limits,60CPUproof and prior evidence remain unchanged; native completion/dependency/qualification stay held. [E521]–[E523]

### 2.88 Login-only inspection reported complete; exact raw retrieval ready

The user reports metadata_captured_pending_dependency_review at /home/dar579/torch-reviews-results/a3-client-config-dependencies.xgzm0ve9. Full strict original verification completes in56.006351844989695seconds and original quota checks in2.069581504998496seconds; the helper returns within its unchanged120second deadline. Allocation/ANN/exact counters are0 and configuration/dependency/native qualification flags remain false. This reports successful metadata collection, not scientific/native resource qualification or full installed-dependency admission. Four raw files are not yet local. [E524]

A separate retrieval freeze fixes quota.json,preflight.json,manifest.json,inspection.json only. Strict direct SFTP/no mux/no remote shell uses two MFA connections to apply64KiB child ceilings to three control files and1MiB to the inspection file, keeping worst-case raw below2MiB/16files without raising parent/hard limits. No remote packaging, new inspection or job occurs. Fresh private local files, strict JSON/member hash/size/manifest, one-pass proof/tail/reported timing and original conservative quota parser/minima are checked. Parser path/SHA are pinned in code after a frozen pre-release hardening; mutable scope JSON cannot choose executable code. Retrieval integrity itself cannot admit DSO/loader/auxiliary closure. [E525][E527]

27source+27independent snapshot checks pass without skips/errors/prohibited actions, including actual local SFTP valid small/>64KiB downloads and kernel size failure with unchanged parent limit, malformed/tampered manifests/proofs/flags, and mocked two-phase transfer. All prior424local proofs,34site/evidence pins,71scientific files,128+128main/276+276A3 tests, strict verification, limits and earlier evidence remain unchanged. No actual network/Torch transfer/command, scientific SQL/provider/search or allowance reuse occurs in preparation. User downloads the exact evidence next; all spent grants including21756110remain closed and native gates stay held. [E526][E528]

### 2.89 Actual dependency capture reviewed; observed RPATH candidate gap corrected

All four returned files/73,986bytes independently verify against manifest/member hashes, native one-pass/quota proof, reported timings, local receipt and private input bounds. Metadata records18ELF objects/19,584,299ELF+loader bytes read,34path components with no conflicting generations,93plugin names and13library directory names, hashed root loader cache and absent preload. Both client pins and existing ownership rules reconcile. Forty multi-name candidate edges resolve to the same captured canonical file through recorded symlinks; this is not runtime-loader resolution. [E529][E530]

Two static edges remain: both clients need libslurmfull.so; their DT_RPATH is /opt/slurm/lib64/slurm and that captured directory lists the name. The collector omitted it from fixed ROOTS and selected only named plugin files there. Therefore the required library/hash/transitive graph was not captured; do not call it absent or substitute the distinct libslurm.so.43 object. Loader cache/hwcaps/build defaults, actual plugin/auxiliary/MUNGE inputs and native sealed-config parsing remain unknown. [E530]

Freeze then implement a separate one-root correction: append only observed PLUGIN_DIR to existing static candidate ROOTS, preserving first-two order and all earlier entries. Every other inspector AST/function, trust/identity/environment rule, strict full one-pass verification/quota semantics,120second cap and all read/object/raw/size/scientific limits are unchanged. Replay table stays empty; no nonroot leaf exception, library/config mutation or untrusted RPATH expansion is introduced. [E531]

436local checks pass:88+88Mac,88+88Linux functional/15+15real ARM Linux kernel and54SFTP/bootstrap cases, all85prior functional/15kernel IDs retained. Three added cases bind the observed path, prove the only ROOTS AST delta and reproduce/fix the missing-library fixture. Exact target package/reference verification still has one full original semantic verifier/core with only quota/statvfs mocked. Original128+128main/276+276A3 tests,71scientific files,34site/evidence pins, all old check/evidence/source copies and limits remain preserved. No actual network/Torch/job/search/provider/SQL action occurs; every spent grant including21756110stays closed. [E532]

New pinned39524byte payload/SHA9abc2dd5f6fb1e6f671f7409c2c8820defdd8b3ebb8584d0f9461c0b96969d40 uses strict direct SFTP and a fresh remote directory, then a new login-only metadata block. User capture/review of libslurmfull and its graph is next; native runtime/CPU/memory/resource qualification and any allocation remain held. [E533][E534]

## 3. Experimental contracts to preserve

- Preserve complete valid top-10 results, native mean recall >= 0.95 per filter, and the declared default-relative recall criterion. The native floor does not itself guarantee absolute policy recall >= 0.95.
- Under the current selective protocol, require lower 95% policy-minus-native recall bounds >= -0.005 overall and in every filter, and an upper 95% mean log latency-ratio bound < 0 in both activation and reuse. Its development admission reserve is -0.0025. These values belong to the existing protocol; changes require a separate version rather than retrospective reinterpretation. [E7]
- Preserve the declared primary timer. Keep full application time and arithmetic latency summaries visible as additional outcomes. Do not subtract measured control costs or estimated overhead to manufacture deployed savings.
- Distinguish cold policy activation from cold database buffers. The current activation regime does not claim a cold database cache.
- Keep all filter strata in workload reports, including queries routed to native. Use each arm's paired baseline and do not derive causal contrasts by subtracting independently summarized baseline gaps.
- Cluster recall and timing uncertainty by independent vector, retaining associated filters, repetitions, and blocks. More checkpoints, filter variants, or timing repetitions do not increase the independent vector count.
- Unmeasured stopping outcomes remain unknown. A surrogate, oracle, or feature trace cannot replace an actual measured intervention where the scorer requires one.
- Preserve source, runtime, profile, dataset, index, policy, ledger, and evidence identities. A new execution path requires qualification and fresh comparison; old timing qualification does not transfer automatically.
- Keep the original consumed confirmation sample consumed. The selective study's separate unconsumed 60-vector entitlement remains bound to its contract until formally reconciled. An abstention does not automatically release it to a multi-method benchmark. [E1][E4][E7]
- Keep the closed selective episode closed. The next implementation or measurement campaign is a new version with its own declared scope; do not resume the terminated episode.
- Development replay, measured training feasibility, independent confirmation, method-comparison evidence, and canonical serving acceptance must be reported as distinct states.

## 4. Progress dashboard

Use statuses `planned`, `ready`, `in_progress`, `waiting_external`, `complete`, `closed_negative`, `closed_inconclusive`, and `deferred`. `closed_inconclusive` can close a finite spent campaign while retaining unassessed positive-qualification gates; it does not mark missing evidence complete. A phase is complete only when its gate record links the required evidence. A negative finding can close a phase successfully without meeting M2 or M3.

| Phase | Workstream | Status | Owner | Gate | Current evidence / next action |
| --- | --- | --- | --- | --- | --- |
| Historical | Selective-agent-v1 episode | complete | Existing study | Historical only | Verified abstention; no candidate; [E1] |
| P0 | Charter, evidence inventory, evaluation design | in_progress | Unassigned | G0 | This roadmap records baseline; budgets, ownership, and entitlement reconciliation pending |
| P1 | Execution cost attribution | complete | User Torch execution; Codex local analysis | G1 pass | Three blocks verified, 83,763 searches; repeated policy/profile work and normalization identified; [E11][E12] |
| P2 | Qualified execution revision or bounded retain-original decision | complete | User Torch execution; Codex sealed analysis | G2 closed_negative; retain original | Finite P2 sequence closes without optimized-path qualification; M1 unestablished; retain original through P3 [E46][E47] |
| P2a | Owned prepared-policy comparison | complete | User Torch execution; Codex local analysis | Engineering gate not passed | 143,163 searches; exact output/stop parity; 5.171% candidate reuse saving; frozen verdict preserved [E21] |
| P2b | Admission/profile identity and measurement precision | complete | User Torch execution; Codex sealed verification | Measurement inconclusive | Four blocks independently verified; 2.102% activation point saving vs P2a; A/A failures and 1.943% relative lower saving bound prevent qualification [E34][E35] |
| P2c | Conditioned activation timing calibration | complete | User Torch execution; Codex fresh sealed verification | Calibration pass; engineering closed_negative | 2 jobs/592,242 searches; 240 A/A and 144 nonregression checks pass; incremental activation lower saving bound 1.751% <2% [E46][E47] |
| P3 | Information/outcome-coverage diagnosis; bounded modeling | complete | Codex | G3 closed_negative, tested procedures | P3a coverage passes; P3b/P3c joint qualifiers absent; retain original and propose B1a scope audit [E69][E70] |
| P3a | Existing outcome/feature/identity audit | complete | Codex | Restricted coverage gate pass | 620 files preserved; 4,695 actual stops per profile, zero reached-grid label gaps; known Light19/off-grid gaps explicit [E53][E54][E55] |
| P3b | Flexible-versus-shallow grouped development comparison | complete | Codex implementation, execution and replay | Closed negative for frozen procedures | 340 fits; 0/20 non-continue selections; diagnostic ensemble fails unfiltered recall; all results preserved [E61][E62][E64] |
| P3c | Risk-separated objective comparison | complete | Codex implementation/execution/replay | Closed negative for finite formulation | 100 fits; 4/20 cells select, no joint outer qualifier; independent replay passes [E69][E70][E72] |
| P4 | Conventional constrained optimization | deferred | Unassigned | G4 | Current stopping branch lacks a supported family; reassess after a new scoped feasibility decision |
| P5 | Active measurement selection | deferred | Unassigned | G5 | Await supported family/G4; no automatic acquisition |
| P6 | Agent feedback, memory, completion, optional prompt tuning | deferred | Unassigned | G6 | Design can start early; comparison awaits useful stable numerical/acquisition tools |
| P7 | Controlled research-method comparison | deferred | Unassigned | G7 | Harness/sample planning can start at P0; execution awaits stable methods and entitlements |
| P8 | Independent policy confirmation and transfer | planned | Unassigned | G8 | Conditional on a frozen eligible candidate and an assigned entitlement |
| B1 | Finite fixed-index effort probes; wider alternatives separate | complete | User Torch execution; Codex saved-data verification | No qualifying frontier; original retained | B1b aggregate inconclusive; B1b2 closes negative quality; B1c deferred [E90][E107][E108] |
| B1a | Fixed-index query-dependent search-effort scope audit | complete | Codex read-only review | GB1 scoped pass only | 324 code/source files preserved; old/current index mismatch and API/timer/input limits recorded; no experiments [E76][E77][E78] |
| B1b | Native-effort interface qualification and matched320/640 frontier | complete | User Torch run; Codex fresh sealed replay | Aggregate measurement_inconclusive; reuse quality/control fail |2 jobs/139,272 searches verified; native conformance pass, A/A reuse32/32 activation2/32; no supported context/regime [E90][E91][E92][E93] |
| B1c | Bounded predicate-context effort routing | deferred | No fit or selection authorized | Current320/640 context family unsupported | Each320 context fails recall reserve; always640 offers no effort reduction and wrapper costs fail; new frontier required [E90][E91] |
| B1-review | Effort/interface scope revision | complete | Codex read-only review | Design-only GO; no wrapper/router/calibration repeat | Existing source/timers audited; B1b2 design frozen before480 outcomes [E96][E100] |
| B1b2 | Fixed480 versus640 quality-first warm native probe | closed_negative | User Torch execution; Codex fresh sealed replay | Native pass; relative quality fail; A/A/benefit not assessed |1 job/1,830 searches; overall/votes32/votes108 fail reserve;888 immutable hashes preserved [E107][E108][E109] |
| B2a | Read-only plan/filter/index feasibility | complete | Codex source/evidence audit | GB2a scoped pass; design GO only | 349 source/code and 907 immutable hashes preserved; recommend fixed exact-top10 B2b; no measurements [E115][E116][E118] |
| B2b | Exact-top10 versus native640 comparison | closed_inconclusive | User allocation spent; Codex partial-return audit complete | Verified incomplete_budget_exhausted; prefix quality pass, full controls/economics/final integrity unassessed | Complete block0 exact56.11x slower;0/763 case-block wins; no repeat/adoption; propose B2c [E142][E143][E144] |
| B2c | Indexed/filter-aware ANN alternative-scope review | complete_scoped_design_go | Codex source/saved-evidence audit complete | One >=108 partial HNSW selected; public inspector/native/cache caveats and costs recorded |349 source/1,364 prior hashes preserved; no experiment/code change [E147][E148][E151] |
| B2d | One partial ANN index versus native640 | complete_verified_measurement_inconclusive | Codex returned-evidence review complete | Quality+1.25pp; observed latency−17.44%, nominal economics pass;0/4 A/A intervals pass | Retain original; B2e complete, B2f design only next; no qualified speed/adoption [E184][E186][E191] |
| B2e | Replica/session timing mechanism audit | complete_read_only_design_GO | Codex audit complete | Plans/settings/counters match; repetition transient/persistent session gap; physical state missing | GO to one bounded instrumented calibration design; cause unresolved, B2d unchanged [E191][E192][E194] |
| B2f | Instrumented A/A calibration | deferred | All prior calibration/resource allowances spent | Native startup margin and workload release unqualified | A3 lifecycle correction is locally checked only. Aggregate memory headroom remains unresolved; no native handoff [E363]–[E370] |
| A2 | Main startup attribution | complete | User Torch execution; Codex independent replay/audit | Attribution complete/informative; resource margin inconclusive | Job 21459623_0, all 102 checkpoints/replay/integrity pass; peak 32 GiB and 780 max events. Allowance spent [E333]–[E335] |
| A3 | Exact-vector representation and startup integration | complete | User native correctness execution; Codex independent audit | Scoped native correctness qualified; memory resource gate failed | Job21470341 passes128+128 old/56+56 A3 cases on exact3.12.15. Resource job21542975_0 is separately failed/unqualified; no current Torch handoff [E345]–[E347][E363]–[E365] |
| A3-resource | Exact-vector startup/admission memory qualification | closed_failed_unqualified | Failed-return audit and separate offline memory-component review complete | Job21542975_0 failed; allowance spent |28.700241GiB aggregate lower bound +4GiB >32GiB remains. Adaptive codec is locally checked only; native headroom/timing unknown and no retry released [E371]–[E375] |
| A3-adaptive-x86 | Complete adaptive target correctness and bounded CPU qualification | closed_failed_unqualified | User Torch execution; Codex data-only return audit | Job 21595967 failed; allowance spent | Main 128+128 pass; A3 source 165 pass/one interrupted at 600s; sealed/CPU unstarted. Offline fixture-cost correction now locally verified; native complete-budget feasibility remains held, no retry [E392]–[E402] |
| A3-fixture-cost | Offline fixture-cost correction | complete_local_only | Codex | Complete original tests and fresh verification work preserved | New integrated replay passes128+128/276+276/26+26 with strict checks; native budget/resource gates remain held [E397]–[E420] |
| A3-budget-storage | Native budget/storage feasibility design and local replay | full_local_replay_pass_native_held | Codex | Exact staging and930 local cases/60 CPU samples pass | 1,602 staged files; serial fixture/lifetime/capacity/whole budget checks pass locally. Native storage/quota/target/CPU/memory/resource/controller gates remain held [E403]–[E420] |
| A3-native-integration | Host/guest/controller and persistent failure integration | offline_verified_native_closed | Codex | 1,170 local checks/60 CPU samples and full lossless recovery | All tests/strict checks/limits and prior evidence preserved; actual native authority/target/resource/retention gates held [E421]–[E428] |
| A3-native-release | Offline native release review | complete_offline_handoff_HOLD | Codex |1,280 local checks/60 CPU samples and195,784 prior hashes pass | Five frozen bounded corrections in separate closed candidate; concrete native authority/group/live-admission backend and fresh allowance absent; no Torch/search/reuse [E429]–[E435] |
| A3-authority-ownership | Offline authority and ownership backend | offline_implemented_verified_handoff_HOLD | Codex | 642 fresh checks,17+17 actual Linux cases and200,143 prior hashes pass | All D128 bytes/tests/limits unchanged; production roots/site provisioning/adapter wiring absent; no Torch, searches, new grant or reuse [E436]–[E442] |
| A3-native-integrated | Offline native integration and qualification package | offline_verified_readonly_site_check_ready | Codex |1,656 checks/60 CPU samples and205,032 protected files pass | Live Torch site/account check and distinct explicit allocation approval pending; native target/CPU/resource/B2f HOLD; no launch/search/reuse [E443]–[E453] |
| A3-site-compatibility | Exact installed-site admission compatibility | offline_verified_readonly_site_account_check_ready | Codex |722 fresh checks and211,278 prior hashes pass; all71 science files unchanged | Actual site/account output and new explicit authorization pending; no launch/grant/reuse [E454]–[E461] |
| A3-site-readiness | Live site/project/partition evidence review | reviewed_new_allocation_authorization_pending | Codex | Exact installation/site policy, intended project association, cs eligibility and reported conservative quota pass | Conditional commands ready; no real approval/submission; all old allowances spent and native results pending [E462]–[E465] |
| A3-native-job21756110 | Distinct native correctness/CPU qualification | submitted_outcome_pending | Codex/user Torch execution | User explicit new allowance and submitted dispatch match verified PLAN/manifest/account |1h4physicalCPU32GiB zero-search/no-retry; no reapproval/resubmit; actual native outcome pending [E466]–[E469] |
| A3-failure21756110 | Allocated-host preflight failure | FAILED_allowance_closed_raw_pending | Codex/user evidence retrieval | FAILED1:0/38s; frozen-prefix scope rejection; native qualification false | No retry/new allowance/guard change; exact role/path needs full traceback; all tests/limits preserved [E470]–[E473] |
| A3-SLURMCONF21756110 | Exact allocated configuration failure role | role_identified_raw_download_pending | Codex/user evidence retrieval | Full chained trace identifies SLURM_CONF validation before first Slurm command/science | Actual path/ownership unknown;21756110 spent; no guard change/new allocation/retry [E474]–[E476] |
| A3-RAW21756110 | Complete failed return reviewed | raw_verified_runtime_config_metadata_missing | Codex/user read-only evidence |9files/16,283bytes reconcile; no scientific launch | No justified exemption/retry; login diagnostic ready; historical runtime remains unknown [E477]–[E480] |
| A3-SITE-PROVENANCE | Historical compute configuration evidence | held_pending_site_metadata | User/NYU HPC support | Login unset/accounting NONE; cs624 identified | Unsent request ready; no guessed correction/new job/retry; historical path unknown [E481]–[E484] |
| A3-PINNED-CLIENT-CONFIG | Alternate future configuration provenance | design_frozen_capture_pending | Codex/user login-only capture | Native Slurm serializer plus pinned immutable config capability | Export/parser/dependency/portability not proven; no implementation, new grant or retry [E485]–[E488] |
| A3-CONFIG-CAPTURE | Bounded login-only snapshot capture | command_locally_verified_ready | User login-node command |32+32checks; exact checked command; unchanged original science | Actual export permissions/config bytes pending; no config admission, grant or job [E489]–[E492] |
| A3-CONFIG-RETURN | Current login snapshot retrieval | reported_success_download_pending | User Mac retrieval |16,647bytes and pinned manifest/config SHA reported;14local download checks pass | Actual raw/config/dependency review pending; no config use, new grant or job [E493]–[E496] |
| A3-CONFIG-USE | Read-only configuration compatibility harness | local_harness_pass_native_gate_held | Codex command preparation/user login-only inspection |326final local checks pass; exact bytes/old code/tests preserved | Actual installed dependency/native parser/sealed-input/compute gates remain open; empty native closure table, no config admitted or new grant [E502]–[E506] |
| A3-Mac-space | Local staging capacity with evidence preservation | complete_local_replay_verified | Codex | 173,943 protected hashes/54 input metadata proofs pass | 22 independent COW paths; 10.40GiB available,8GiB guard unchanged; no deletion, Torch or allowance reuse [E409]–[E413] |
| A3-lifecycle | Process sampling and cancellation/shutdown correction | complete_offline_native_held | Codex freeze, implementation and local verification complete |142source+142code-snapshot checks; all110inherited cases and5,163prior files preserved | Proven exits/PID reuse explicit; persistent live RSS loss fails; cleanup cancellation idempotent with unchanged deadlines and strict replay rejection. No native capsule/command or memory pass [E367]–[E370] |
| A3-memory | Exact adaptive vector memory component | complete_offline_native_held | Prospective freeze/amendment, implementation and independent audit complete |94source+94code-snapshot cases;56inherited cases and5,445prior files preserved | Exact roundtrip32-bit codes or raw64 fallback, three immutable slots, compact float32 constructor views. Production integration/target correctness/memory gate remain held [E371]–[E375] |

### Maintenance procedure

1. Assign an owner and planned resource ceilings before a phase becomes `ready`.
2. Check task boxes only when linked evidence exists. A script, fixture, or packaged job alone is not an empirical result.
3. For each campaign, add an experiment row before dispatch and update it with actual consumption and outcome. Record ambiguous dispatches instead of launching duplicates.
4. Enter the gate verdict, date, reviewer, evidence, and resulting branch. Leave earlier records intact.
5. Update the dashboard, decision log, and next actions. Change the evidence-snapshot date when new results materially change the diagnosis.
6. Link new raw and verification artifacts; do not copy sensitive query inventories, credentials, or protected evaluator data into this roadmap.

## 5. Detailed phases

### P0 — Establish the research and evaluation contract

**Question:** What must the program prove, with which evidence and resources?

**Dependencies:** None. **Planning effort:** 1–2 working days, excluding acquisition of new data.

**Required work:**

- [x] P0.1 Record the verified selective pilot, its abstention, and the revised diagnosis in this roadmap.
- [ ] P0.2 Reconcile permitted development evidence, the consumed earlier confirmation, selective-study entitlements, and other reserves using host-owned identities and exposure records. Do not expose protected vectors to the learner.
- [ ] P0.3 Assign owners and budgets per campaign: provider charges and reservations, attempts, backend/reference calls, CPU-hours, allocation count, wall time, and label acquisition. No new spending is assigned by this document.
- [ ] P0.4 Predeclare the primary research-method comparison, a practically worthwhile effect, repeated-episode count, analysis unit, and handling of unsuccessful/censored episodes.
- [ ] P0.5 Plan sample size using permitted development distributions, including paired recall differences per filter. Specify what an underpowered result will mean before final evaluation.
- [ ] P0.6 Set an execution cost budget in absolute milliseconds and workload-relative terms for activation, reuse, and native bypass. Set a finite number of engineering/measurement rounds before reassessment.
- [ ] P0.7 Separate engineering fixtures, development fitting, method validation, final method evaluation, and canonical policy acceptance in the data-access plan.

**Outputs:** Signed-off charter; evidence/exposure inventory; cost budgets; resource allocation; benchmark and statistical analysis plan.

**Will inform:** Whether subsequent evidence can support M1, M2, or M3, and which measurements are permitted.

**G0:** Pass when ownership, resource ceilings, sample entitlements, endpoints, and stopping rules are concrete. Planning is not complete merely because the roadmap exists.

### P1 — Attribute execution overhead

**Question:** Which operations create the measured activation and routed-native penalties?

**Dependencies:** G0. Read-only evidence organization and harness design may start while G0 is being resolved. **Planning effort:** 2–4 working days plus any approved measurement turnaround.

Completion update, October 23: the scoped G0-P1 diagnostic contract in [DESIGN.md](../agent/experiments/execution-cost-attribution-v1/DESIGN.md) was executed on the same 200 exposed development vectors, with three frozen/control arms and a separate 60-vector profiling pass. All three serial allocations and exactly 83,763 searches completed; provider calls and confirmation queries remain zero. [Implementation verification](../agent/docs/verification/execution-cost-attribution-v1-implementation.json) remains a historical pre-dispatch snapshot. The new [postrun receipt][E11] and [analysis][E12] establish G1; wider program budgets and final-data entitlements remain unresolved.

**Required work:**

- [x] P1.1 Reconcile native, routed-native, matched-continue, and candidate call paths against recorded primary and outer timers. Components reconcile in all verified blocks; the backend category includes preparation/SQL/transport work. [E11][E12]
- [x] P1.2 Map observed preparation/routing work to validation, profile fingerprinting, copying, serialization, tree preparation, statement construction and query normalization. Database wait remains a specific unresolved server/transport boundary rather than an asserted root cause. [E12][E14]
- [x] P1.3 Classify observed operations by proposed artifact/profile, connection/installation and query lifetimes, with ownership/invalidation requirements. The map is complete for planning; safety of a new lifecycle remains P2 qualification work. [E12]
- [x] P1.4 Define a minimal control matrix: native; routed-native; matched continue; and one frozen candidate. Implemented as paired native references for three arms, followed by a separately profiled diagnostic pass; no execution optimization introduced.
- [x] P1.5 Execute the declared randomized/balanced three-block schedule, preserve index/search identities, retain primary and outer application times, and verify diagnostic output/first-stop parity. Profiling remains a separate perturbed pass. [E11][E15][E16]
- [x] P1.6 Produce a measured cost ledger and identify bounded engineering headroom and the remaining gap without double counting or projecting hypothetical speedups. This baseline ledger is in [E12]; the prospective practical cost threshold remains open under P0.6.

**Outputs:** Call-path/cost map; cost attribution report; ranked changes; frozen P1 protocol and bounded comparison requirements for P2.

**Will inform:** Whether reducing redundant setup, simplifying bypass, or changing the integration lifecycle has more value than changing the policy.

**G1:** Pass when each major measured category has an evidenced explanation or a specific unresolved attribution task, and the next revision targets a bounded mechanism. If attribution remains ambiguous, run a diagnostic comparison before modifying several layers.

**Recorded verdict, October 23: pass.** Repeated policy/profile work and query normalization have function-count and source evidence; server/transport wait has an explicit limitation and conditional diagnostic. The first revision is owned prepared-policy state. Passing G1 establishes attribution, not M1 execution savings. [E11][E12]

**Research basis:** Evaluator discrepancy analysis in [S6]; externally controlled measurements in [S7]. This phase applies those principles without changing the final acceptance objective.

### P2 — Qualify the execution path and establish its economics

**Question:** Can the policy interface become inexpensive enough for current useful decisions, and what cost remains?

**Dependencies:** G1 and a scoped prospective cost/resource contract. **Planning effort:** 3–7 working days plus qualification/measurement turnaround. P2a/P2b/P2c comparisons are complete. P2c's scoped calibration passes, but engineering qualification fails; G2 now closes with the retain-original branch. The historical implementation and intermediate decisions below remain preserved.

**Pre-dispatch implementation snapshot, October 23 (preserved):** NEXT-EXEC-01 was implemented in [prepared-policy-lifecycle-v1][E18]. The original backend already accepts prepared-policy state. A private session handle resolves at the original timed preparation expression on first eligible execution and reuses that owned artifact afterward. Full composite admission, first backend preparation, lazy compilation, installation, connection checks, query normalization and routing retain their accounting/behavior. Bypass never resolves a handle. Profile-fingerprint memoization was deferred, keeping that comparison to one lifecycle change.

The copied backend execution body differs only in its function name and preparation expression, enforced by an AST check. The original path remains the frozen original. Local checks cover policy identity, ownership/caller mutation, real query/numeric validation, invalid admission, lazy preparation/compilation, cache eviction/reinstallation, connection/cache/profile replacement, cross-backend rejection, SQL-body equivalence for unbatched and both batch paths, error closure without replay, measurement accounting, integrity and scheduler simulations. These 31 checks establish local correctness evidence; they do not establish x86 native or timing qualification. [E17][E18]

The prospective P2a engineering criterion requires candidate reuse savings of at least 0.10 ms and 2% against original execution using the declared upper confidence endpoints, with at least 0.10 ms outer application savings and the saving direction in every block. Every arm/regime/filter must stay within 0.10 ms and 2% primary regression, and 0.10 ms outer regression. Original validity/recall requirements and exact old/new output/stopping parity remain mandatory. Ordinary-native quality/latency checks are separately reported. See [the frozen contract][E19] for the complete analysis and limitations; an engineering pass is not policy confirmation or an automatic M1 declaration.

The frozen campaign cap was exactly three serial 4-CPU/32-GiB/two-hour allocations, 143,163 searches, and 12,420 separately counted eviction installs. All 200 exposed vectors / 600 cases remain, with six execution arms and a separate 30-vector profiling subset. Only one implementation/campaign was included; failure does not authorize automatic reruns or a second variant. Provider calls and confirmation queries are zero. The implementation receipt preserves the pre-submission state; the campaign subsequently completed and is recorded in [E21].

| Sealed artifact | SHA-256 |
| --- | --- |
| P2a package manifest | `c4c00e12a08963751ab20aed3f195ed3af2a515be40c0bdd619ce57209bca60c` |
| Upload archive | `44a00454b8ae5d739a055e2001a1d8c376ef198a58beda24bff01fd442438ab1` |
| Implementation/check receipt | `777a5393ba742f9198e62f048c3ff569ecfc73023c237643cd03faeada8076b5` |

**Postrun decision, October 23:** native result/first-stop/reference checks and all 216 mechanism groups pass; candidate reuse saves 0.286089 ms (5.171%) directly versus original execution. The frozen engineering gate is `revise_or_retain_original` because activation/control bounds fail. Full details and uncertainty distinctions are in [E22]. Retain original execution as the adopted baseline, preserve frozen P2a as an experimental reference, and scope admission/profile-identity reuse with improved per-filter/control precision. No additional implementation or allocation allowance is assigned by this decision.

**P2b implementation update, October 23:** NEXT-ADMIT-01 now captures a deep-owned immutable semantic profile identity once per session admission, retaining a read-only mapping of privately copied frozen feature definitions and frozen collection groups. Its full copy/fingerprint/binding cost remains charged to activation. The original composite validator changes only the explicit profile binding, enforced by an AST check; complete node/type/numeric/depth/feature/guard validation remains. P2b inherits the byte-identical P2a query method and lazy handle, and both frozen P2a reference files are preserved byte-for-byte. There is no normalization, SQL, native-module or policy change. [E27][E28][E29]

All 45 local correctness/simulation/integrity checks pass, including full four-block driver/report simulation, original rejection semantics, profile/caller mutation isolation, cold accounting, lazy compilation, connection/cache/profile invalidation, real Python SQL-body protocol stubs, error closure, Williams position/predecessor balance, physical-order verification and A/A gate boundaries. The diagnostic simulation observes one original fingerprint per P2b constructor versus four for original/P2a. These checks establish local interfaces and mechanism counts, not x86 native qualification or speed. [E27]

The precision review retains P2a's wide per-filter activation intervals (up to approximately 0.288 ms in width) and varying control point gaps. Four Williams-balanced blocks provide each query/semantic arm equal variant positions and directed predecessors. Original, frozen P2a, and two independently constructed labels of the identical P2b path are measured for all 200 vectors/600 cases. Both A/A labels remain repeated observations inside the same vector cluster, not new independent samples. No interval-width or power guarantee is claimed. [E29][E30]

P2b requires pooled A/A primary/outer intervals wholly within ±0.10 ms and log-ratio intervals within ±log(1.02), in every arm/regime/filter and overall. An interval merely including zero is insufficient. Missing A/A equivalence produces `measurement_inconclusive`, preserving all engineering failures without adopting, correcting by control subtraction, enlarging margins, or repeating automatically. Incremental candidate activation versus P2a must establish ≥0.10 ms/2% primary and ≥0.10 ms outer saving; combined candidate reuse versus original must retain the same minimum benefit. Both comparisons retain every original +0.10 ms/2% primary and +0.10 ms outer nonregression bound, all quality checks and full cold accounting. Block saving directions remain mandatory. Ordinary-native activation/reuse criteria are reported separately. [E29]

The newly scoped P2b allowance is **four serial 4-CPU/32-GiB/two-hour allocations**, a 6,600-second deadline per block, **370,884 searches** and **33,120 separately counted eviction installations**, 115,200 primary and 17,280 diagnostic retained pairs. One implementation/campaign only. At the preserved implementation/packaging snapshot, actual native allocations/searches were zero; subsequent reported completion is recorded below. Protected pilot/P1/P2a inputs/results remain checked. No confirmation, selection or deployment is permitted. [E27][E29]

| P2b sealed artifact | SHA-256 |
| --- | --- |
| Package manifest | `7c82194d375a77f29356e3620d2f011b2b0e452b9954defcb75aaec90f29350d` |
| Upload archive | `c81d06d230dc8df26df7092a211dcc4a976a50b9f12e9a7da4f6f9ca7026ab2f` |
| Implementation receipt | `f9018f2f939b7505294a8fc40d206cd174c37756eee6dbc4dac6bc831b98c772` |

The historical [exact commands][E31] and [Mac transfer helper][E32] preserve the P2b run procedure. The helper authenticates interactively, transfers the durable binding as a file, checks its package identity, then parses it and downloads/verifies the bound archive. An authentication failure exits before JSON parsing or ingestion; this path passed a local mock without contacting Torch. That implementation receipt preserves the pre-dispatch state. The campaign is complete; do not resubmit it.

**P2b Torch status update, October 23:** the user's pasted `pp_control.py status` report identifies campaign `reviews-admission-profile-v1-20261023T193304Z.a2mfz4a0` and jobs `20753185`, `20753186`, `20753187`, `20753188`. All four block statuses say `complete`; all host exits are zero with protected sources reported unchanged; all four top-level Slurm jobs say `COMPLETED`, `0:0`. Reported totals match the frozen cap: 370,884 searches, 33,120 eviction installations, 115,200 primary retained pairs and 17,280 diagnostic retained pairs, with zero provider/confirmation calls. This is a status transcription, not independent raw-result verification. It establishes reported execution completion only; it does not establish native/output/mechanism correctness, A/A equivalence, speed improvement or engineering acceptance. [E33]

**Pre-verification next step (now completed):** collect the existing bound campaign on Torch, download it with the sealed transfer helper and independently reconstruct all evidence. Do not upload, extract, submit or rerun the completed campaign. The archived status receipt SHA-256 is `305af5bee07b1fd08c6adc2272e6835a3262c145768fb3a82a73266d7f7c4b28`. At that stage G2 was `revise` and P2b's gates were unassessed; the completed review below supersedes that status.

**P2b postrun review, October 23:** the completed archive and a fresh sealed reconstruction are now independently verified. Scoped native/output/stop/mechanism checks pass; candidate activation saves 0.201653 ms versus P2a and combined reuse saves 0.250231 ms versus original. All 144 nonregression bounds pass. A/A equivalence nevertheless fails in six activation/filter cells, and the 2% incremental activation saving is not established (lower bound 1.943%). Frozen verdict: `measurement_inconclusive`. The detailed interpretation [E35] supersedes the provisional status for conclusions; earlier receipts remain historical. Keep original adopted execution and scope calibration/finite redirect before another optimization. No new run is assigned.

**Revised sequence after G1:**

| Step | Required action | What it informs / exit |
| --- | --- | --- |
| P2 contract | Scoped NEXT-EXEC-01 targets, owner, resource ceiling and one-campaign stopping rule are frozen in [E19]; broader program economics remain open | Makes the engineering review prospective without assigning budgets to later revisions |
| P2a: owned prepared-policy state | Complete: native/proof/mechanism checks pass and reuse savings are measured; full engineering gate fails [E21][E22] | Preserve experimental component; do not adopt or rerun the exhausted campaign |
| P2b: admission and precision | Implemented and locally checked; immutable per-session profile identity plus frozen four-block Williams/A/A comparison [E27][E29][E30] | Declared native/output/mechanism checks pass; actual admission saving measured; A/A equivalence fails and relative activation saving misses the minimum [E34][E35] |
| P2b measurement | Complete and independently verified [E34]; verdict `measurement_inconclusive` | Preserve the activation/reuse signals and every missed criterion; no adoption or rerun |
| P2c calibration contract | Frozen and completed in [E43][E46]; all 240 A/A interval checks pass in the declared conditioned scope | Calibration succeeds; engineering incremental 2% bound fails; allowance consumed and original retained for bounded P3 |
| Later query-boundary revision, conditional | If residual bypass/normalization warrants another declared allowance, propose single-normalization work with preserved vector/filter/k semantics | Keep separate from admission/profile identity and database transport |
| Conditional residual diagnostic | If database wait blocks a decision, isolate server/transport work under a new focused diagnostic contract before a database-side rewrite | Resolves the part Python profiling cannot attribute |
| G2 review | Complete: retain original under bounded stopping-policy research; optimized-path qualification closes negative [E46][E47] | Original is the common execution identity for P3; M1 remains unestablished |

P2a must preserve rejection of mutable/type-invalid/oversized/deep/nonfinite/incompatible policies, private ownership, bounded caches, correct compilation/installation and eviction behavior, connection/reset/error behavior, and actual first-stop/result parity. Required cold admission work stays charged. A larger reuse lifetime or amortized objective must be declared explicitly rather than moving setup outside the timer to qualify the old criterion.

**Required work:**

- [x] P2.1 Freeze the scoped cost/resource contract and implement one separately identified owned prepared-policy lifecycle revision. Policies, normalization, SQL and database/native sources remain unchanged; package sealed. [E17][E18][E19]
- [ ] P2.2 **Deferred after retain-original decision:** complete broader target-architecture lifecycle qualification before any eventual optimized-path adoption. P2a's declared x86 reference/route/first-stop/activation/reuse checks pass; deliberate mutation, connection/profile replacement and injected-error cases were exercised locally, not as a separate native fault campaign. No adoption campaign follows this negative branch. [E17][E21][E47]
- [ ] P2.3 **Deferred for any future adoption proposal:** complete broader qualification of its final execution identity under a separately justified contract. Current P2b/P2c declared output/getter/stop/phase checks pass; no optimized execution identity is adopted and prior negative/inconclusive gates remain. [E34][E46]
- [x] P2.4 Run the frozen six-arm original/owned matrix in both regimes with unchanged policies, complete coverage and three verified blocks. [E21][E24]
- [x] P2.5 Reconstruct primary and outer timing; candidate reuse saves 0.286089/0.286374 ms respectively, with unchanged first-time preparation accounting and zero owned reuse preparation calls. [E21][E22]
- [x] P2.6 Apply the prospective P2a cost/quality criteria and record the residual/branch: engineering gate fails, original retained as adopted baseline, one admission/precision proposal justified for separate scoping. Broader M1 economics and the next budget remain unresolved. [E21][E22]

P2 is administratively complete through its explicit retain-original branch. The unchecked adoption-only qualifications above are deferred; they do not block P3 using the existing original path and do not count as qualification successes.

**P2b tracking:**

- [x] P2b.1 Review existing exposed timing precision and freeze one admission mechanism, references, A/A design, practical criteria, four-block allowance and finite stop rule. [E29][E30]
- [x] P2b.2 Implement the separate path, run 45 local correctness/simulation checks, lint/format/syntax and seal the upload without changing original/P2a/production sources. [E27][E28]
- [x] P2b.3 Complete four serial blocks; the earlier pasted report is now supported by independently verified raw records. [E33][E34]
- [x] P2b.3a Collect/download, verify archive checksum/all members, and run fresh sealed local replay. [E34][E38]
- [x] P2b.4 Verify raw/runtime/output/stop/mechanism identities and direct comparisons; preserve failed A/A and the relative activation shortfall without corrections or margin changes. [E34][E35]
- [x] P2b.5 Record `measurement_inconclusive`, residual preparation 1.280951 ms and G2 `revise`; original retained as adopted baseline, with one calibration/retain-original proposal next. This campaign allowance is consumed. Broader lifecycle native fault qualification remains required before adoption. [E34][E35]

**P2c tracking:**

- [x] P2c.1 Audit existing activation A/A block/position/variation evidence without dropping observations or changing the estimator. [E40]
- [x] P2c.2 Freeze conditioned-index/query plus fresh-session semantics, adjacent AB/BA crossovers, identical-path controls, grouped analysis, unchanged margins and a two-block finite contract. [E43]
- [x] P2c.3a Implement the separate harness/verifier, pass 44 local checks and seal the package with byte-identical execution/gate references. [E41][E42]
- [x] P2c.3b Complete both user Torch blocks, collect/download and independently reconstruct raw/phase/output/calibration evidence, preserving full admission charges and all strata. Jobs 20778104/20778105; 592,242 searches. [E46][E50]
- [x] P2c.4 Record scoped calibration pass and failed incremental engineering target; explicitly retain original and close the finite P2 sequence. Redirect to bounded P3a coverage diagnosis; no automatic repeated measurement or optimization. [E46][E47]

**P2c pre-dispatch implementation snapshot, October 23 (preserved):** NEXT-CAL-01 is separately implemented at [activation-timing-calibration-v1][E42]. Ten identical-path control cells cover original, P2a and P2b for candidate/matched-continue/routed-native, plus one plain-native cell across all filters. A/B labels use identical factories with fresh state. Each query/cell uses adjacent A/B then B/A rounds (ABBA or BAAB), complemented in block 1. Cell order reverses across the two blocks. All 200 exposed vectors/600 cases remain and are the only independent groups. [E41][E43]

Each fresh slot installs the existing eviction sentinel, clears the Python prepared cache and executes exactly two recorded ordinary-native conditioning calls before constructing its measured session. These calls cannot prepare/install the measured policy. Full constructor admission, P2b copy/fingerprint work, lazy preparation, compilation, installation and first execution remain charged to activation/outer time. Conditioning/reset costs are separately reported and included in resource counts, but excluded from the explicitly restricted service endpoint that assumes conditioned shared data. This does not measure a cold index, novel first query or fresh connection and does not repair old P2b evidence. No profiler or new policy/execution mechanism is introduced. [E43]

The verifier reconstructs physical schedule/phase boundaries, all conditioning outputs/counts, cold-state assertions, first-admission charges, raw hashes, native references and actual stop/prefix parity. All 44 local checks pass, including a complete two-block simulation, rejection/ownership/invalidation, real Python SQL-body stubs, altered/missing phase evidence, per-vector clustering, missing A/A controls, strict equivalence bands, scheduler uncertainty and safe return handling. All four execution/validation files and frozen P2b gate reference are byte-identical; local fake timings are not native qualification or speed evidence. [E41]

All native/original/P2a/P2b identical-path controls must pass the unchanged ±0.10 ms primary/outer and ±log(1.02) ratio bands in every regime/filter and overall: **80 cells / 240 interval endpoints**. The exact frozen P2b engineering gate is reused for direct, uncorrected comparisons in this new scope. No A/A subtraction, outlier deletion, threshold relaxation, previous-data pooling or automatic adoption. If calibration remains inconclusive, retain original and explicitly redirect to bounded P3. Even both gates passing requires operating-scope/lifecycle review; M1/M2/M3 and acceptance stay open. [E43]

The one-campaign P2c ceiling is **two serial 4-CPU/32-GiB/three-hour allocations** (<=6 allocated wall-hours/24 allocated CPU-hours), a 10,200-second work deadline per block, **592,242 total searches** including **96,000 conditioning executions**, and **48,000 separately counted eviction installations**. There are 192,000 retained pairs plus 48,000 discarded warmup pairs. At that pre-dispatch snapshot actual native allocations/searches were zero; the completed campaign below uses the full two-block/search allowance. Every earlier sealed campaign/raw result is protected; no extra block or implementation follows failure/ambiguity/inconclusiveness. [E41][E43]

| P2c sealed artifact | SHA-256 |
| --- | --- |
| Package manifest | `6b6f216977482287838d4c9fbc06e8bb113cb283ff5c8a911ab9055cd7ae6fc0` |
| Upload archive | `f3c442757195476d5d50ff833f8e852114e90bbd6747e78a69b14e1c06302032` |
| Implementation receipt | `178a859a954d193032307817c8ce562028d8174a9294ae939ff86f1741a7d9a2` |

The [exact commands][E44] and [Mac transfer helper][E45] remain the historical runbook. User upload/submission, two serial jobs, collection/download and sealed reconstruction are now complete. Preserve all bindings/reservations; do not submit P2b or P2c again. No user command is needed now.

**P2c postrun review, October 24:** all 41 archive members and 26 locked raw hashes verify; fresh replay reproduces local results exactly and remote results within 3.47e-18. All 80 A/A cells/240 interval checks and 144 nonregression checks pass. P2b candidate activation saves 2.205% versus original and 1.884% versus P2a; reuse saves 4.711% versus original, with no added benefit versus P2a. Incremental activation's relative lower saving bound is 1.751%, below 2%, so the exact engineering verdict is `revise_or_retain_original`. Retain original and close the finite P2 sequence; the old P2b result remains inconclusive. [E46][E47][E48][E49][E50]

Both jobs finish within deadline; actual use is two allocations, 592,242 searches, 96,000 conditioning calls, 192,000 retained pairs, 48,000 discarded warmups and 48,000 separate eviction installs. Conditioning outer cost is 563.091 seconds; reset/conditioning/bookkeeping wall cost is 651.629 seconds (overlapping, not additive). Full constructor preparation remains charged. Calibration passes only for conditioned shared data plus fresh policy/session; general operating-scope and broader native lifecycle adoption reviews remain unestablished/deferred. No new experiment, source change, model or confirmation access occurs during this analysis. [E46][E47]

**Outputs:** Qualified runtime/profile identity, controls with actual timing, and an execution-economics decision.

**Will inform:** Whether current policies have enough practical headroom and which baseline all later methods should share.

**G2:** Prefer a revision that meets the predeclared cost budget. If the finite revision budget is exhausted, explicitly choose either (a) retain the original path and pursue earlier stops under a bounded search, or (b) close this branch and consider B1. **Current decision: (a), retain original for bounded P3; optimized-path qualification closes `closed_negative`.** Calibration passes but the engineering target does not. Administrative closure does not establish M1. The oracle prevents treating a costly path alone as proof that stopping cannot succeed. Never declare M1 from estimated overhead removal. [E46][E47]

### P3 — Inventory stopping outcomes and diagnose information limits

**Question:** After execution economics are understood, is the remaining gap decision quality, representation, outcome coverage, or data diversity?

**Dependencies:** G2 retains original execution. P3a coverage and both P3b/P3c finite comparisons are complete [E55][E61][E69]. G3 closes negative for the tested procedures; no qualifying family. Any later acquisition/timing needs a new justified scope, resources and entitlements. **Planning effort:** historical 3–5 working days plus justified measurement; P3 bounded local work is now complete. This revision runs P3c, with no new measurements.

**Required work:**

- [x] P3.1 / P3a / NEXT-INFO-01 Freeze the offline contract and complete the permitted existing-data coverage/feature/identity audit. Verify 620 files before/after, all 9,390 static/progress stop proofs, causal observations, group/exposure mappings and explicit Light19/off-grid gaps. No Torch/provider/database/protected-query-value access or fitting. Local aggregate-read accounting limitation is recorded in [E55]. [E52][E53][E54]
- [x] P3.2 / coverage gate Pass for current static23/progress34, eight ordinal checkpoints plus continue, on 200 exposed grouped vectors. Zero missing reached-grid labels; all required features available. Preserve 105 unreachable positions and 30 known incomplete stops per profile. No targeted acquisition is needed before this restricted modeling task; Light19/off-grid/new-policy timing scopes remain conditional. [E54][E55][E57]
- [x] P3.3 / P3b / NEXT-MODEL-01 Freeze, implement and execute the finite matched-information/grouped first-stop comparison. All 340 scientific fits, twenty rejections and fixed diagnostics are preserved; independent saved-result replay passes without refitting. Close negatively for these procedures; no new learned-policy latency or independent acceptance. [E60][E61][E64]
- [x] P3.4 Complete the supported saved-data error audit by predicate, native-work difficulty, checkpoint and feature profile. All 225 positive-proxy inner candidates fail recall; diagnostic losses concentrate in unfiltered cases and higher native-work bins. Actual measured stopping outcomes reconstruct, but actual learned-policy execution remains unmeasured; no scorer-to-serving accuracy claim. [E62][E65]
- [x] P3.5 / P3c / NEXT-RISK-01 Freeze and execute the single risk-separated formulation at unchanged information/action/model capacity. Sixteen checks/six synthetic fits, exactly 100 scientific fits, all 980 candidates and 4,800 outer cases retained and independently replayed. Four ensemble cells admit gates, but no joint outer qualifier. No post-hoc rescue or native measurement. [E68][E69][E72][E74]
- [x] P3.6 Close the finite P3c allowance negatively and record G3 closure for the tested procedures. Recommend B1a fixed-index search-effort feasibility/design as the next scope, without executing it. Preserve all exposed-data limitations and confirmation entitlements; fresh development diversity needs a separate precise hypothesis/contract. [E69][E70]

| Finding | Decision |
| --- | --- |
| Flexible model succeeds; deployable policy fails | Investigate compression or a bounded representation extension |
| Both fail with adequate measured coverage | Investigate signal quality and independent training diversity; do not conclude universal impossibility |
| Predictions succeed; timing fails | Return to cost/scorer diagnosis, within the declared reassessment budget |
| Restricted application succeeds | Preserve selective routing and measure coverage/risk/cost together |
| Unknown outcomes dominate | Fill the diagnostic gaps before judging learnability |

**Outputs:** P3a evidence/coverage audit; frozen P3b/P3c sources/contracts/models, all candidates/first-stop outcomes, independent replay and descriptive errors; bounded negative closure and a proposed B1a next scope. No policy/family qualifies; no new serving latency or independent acceptance is established. [E53][E61][E69][E70][E72][E73]

**Will inform:** Which search space and acquisition problem are worth optimizing.

**G3:** The initial coverage gate determines whether to compare models, request bounded actual-stop evidence, or close the family. The final gate passes only with an evidence-supported next family and explicit unknowns, or closes with a negative result. Inventory completion alone is not G3 success. Exposed-data cross-validation is development feedback; prior design adaptation remains a limitation.

**Current G3: closed_negative for the bounded tested procedures.** P3c has no joint qualifier. B1b now completes with native conformance but no qualifying effort context; its formal aggregate remains measurement-inconclusive while reuse quality/overhead independently fail. Current stopping-family P4–P7 and B1c stay deferred. No universal information or native-effort ceiling follows. [E69][E70][E90][E91]

**Research basis:** Intermediate-search information in [S1], filtered-search signals in [S2], selective application in [S5]. E2E's feature choices are hypotheses for this engine, not a reproduced implementation.

### P4 — Establish constrained numerical search as a common baseline

**Question:** What can conventional optimization achieve within the selected policy family and evidence budget?

**Dependencies:** G3 and a fixed execution/evidence interface. **Planning effort:** 3–5 working days plus measured candidate evaluations.

**Required work:**

- [ ] P4.1 Retain the existing CART and first-stop beam procedures as references, including their negative results.
- [ ] P4.2 Choose one additional numerical configuration method, initially SMAC3 or Ax, over a small space of masks, thresholds, depth, and risk settings. Record the choice before comparison; do not start with arbitrary tree structures encoded as a large continuous vector.
- [ ] P4.3 Separate quality constraints from latency objectives and model activation/reuse explicitly. Report recall magnitude, not only a binary per-checkpoint preservation label.
- [ ] P4.4 Use a fixed acquisition schedule initially. Share grammar, qualified inputs, interpreter, scorer, and evidence permissions with the agent.
- [ ] P4.5 Apply a cascade: validate structure/profile; replay measured outcomes; acquire missing outcomes; measure complete candidate execution. Track cost at every stage.
- [ ] P4.6 Compare against the existing references under a common resource contract and archive every candidate, failure, and abstention.

**Outputs:** Reproducible conventional optimizer, measured baseline, scorer-discrepancy report, and common learner interface.

**Will inform:** Whether the LLM should contribute policy-family proposals, experiment selection, or interpretation rather than repeated numerical tuning.

**G4:** Pass when candidate evaluation is consistent across methods and baseline results are reproducible. A positive new policy is not required to finish a valid negative baseline study. Predicted feasibility never replaces measured qualification.

**Research basis:** Constrained optimization in [S8][S10]; algorithm configuration in [S9]; staged evaluation in [S17].

### P5 — Test active measurement selection

**Question:** Can the same measurement resources produce more useful evidence and faster discovery?

**Dependencies:** G4. **Planning effort:** 5–10 working days plus repeated measurement rounds.

**Required work:**

- [ ] P5.1 With the fitter fixed, compare stratified random acquisition, uncertainty/disagreement acquisition, and a decision-focused strategy prioritizing measurements that could change candidate ranking or feasibility.
- [ ] P5.2 Retain a prespecified random-exploration component and per-filter coverage. Avoid repeatedly acquiring highly uncertain but irrelevant states.
- [ ] P5.3 Charge exact references, native/stopped executions, qualification, and failed measurements. A new checkpoint supplies another label but not another independent vector.
- [ ] P5.4 Use the same starting corpus, permitted pool, execution profile, fitter, and spending rules. Preserve action histories so acquisition decisions are auditable.
- [ ] P5.5 Measure progress against independent vectors, labels, database work, money, and elapsed time. Record time-to-qualifier with unsuccessful runs retained as failures or censored observations according to the analysis plan.
- [ ] P5.6 Repeat development episodes. Only after evaluating acquisition independently should the selected strategy be combined with numerical search.

**Outputs:** Acquisition learning curves, repeated-episode results, selected strategy or negative decision, and an explicit evidence-efficiency claim.

**Will inform:** Whether to acquire more evidence, choose evidence differently, or stop investing in the current family.

**G5:** Promote a strategy only under the predeclared efficiency/discovery criterion, with uncertainty reported. A single favorable sequence is insufficient. Keep adaptive training acquisition separate from independently sampled evaluation.

**Research basis:** Active-learning query strategies and acquisition costs in [S11]; information/cost mechanisms in [S12]. These methods motivate the comparison; they do not guarantee savings here.

### P6 — Improve agent feedback, memory, and completion

**Question:** Does better use of the stable tools and evidence improve the researcher's decisions?

**Dependencies:** G5 for the measured comparison; task/rubric and context design may start earlier. **Planning effort:** 3–5 working days; optional prompt optimization is separately budgeted.

**Required work:**

- [ ] P6.1 Present a compact authoritative research state: qualified features and cost, candidate families, supporting/challenging evidence, missing measurements, and reasons for rejection.
- [ ] P6.2 Expose usable remaining budget, including maximum-request reservations, not merely nominal attempts or unsettled dollar balance. Preserve explicit pause/finish/abstention actions.
- [ ] P6.3 Compare current context with structured research memory and actionable feedback, keeping model, tools, evidence, and numerical method fixed.
- [ ] P6.4 Measure duplicated hypotheses, invalid actions, unsupported-feature attempts, evidence linkage, completion/censoring, and qualifying-policy discovery. Calibrate any subjective hypothesis rubric against expert review.
- [ ] P6.5 Consider GEPA only if the benchmark can score outcomes reliably. Optimize on development tasks, select on separate validation tasks, and pin the chosen prompts before final evaluation.
- [ ] P6.6 Preserve model-generated interpretations separately from host measurements. A persuasive explanation cannot override numerical failure.

**Outputs:** Frozen workflow/prompt variant, context/feedback ablation, complete provenance, and a decision about optional prompt optimization.

**Will inform:** Whether the agent adds useful research judgment beyond the common numerical and acquisition tools.

**G6:** Promote changes only with demonstrated efficiency, completion, or discovery benefit and no unacceptable regression under the declared criteria. The latest successful abstention is a baseline behavior to preserve, not proof of comparative superiority.

**Research basis:** Tool and context design in [S13][S14], outcome/trajectory evaluation in [S15], optional reflective optimization in [S16].

### P7 — Compare complete research methods

**Question:** Does the proposed agent method improve qualifying-policy discovery under controlled resources?

**Dependencies:** G6 and frozen task/method definitions. Harness design and sample planning start at P0. **Planning effort:** 5–10 working days plus repeated episodes and measurements.

| Arm | Purpose |
| --- | --- |
| Historical current agent configuration | Quantify change from the existing system; identify any differences in available tools explicitly |
| Conventional optimizer with fixed acquisition | Measure what numerical tools achieve without an LLM researcher |
| Hybrid agent with conventional acquisition | Isolate the agent's role using the common qualified execution/tools |
| Hybrid agent with selected active acquisition | Evaluate the combined method |

The historical configuration is an end-to-end reference if its tool surface differs. Causal claims about reasoning, prompts, acquisition, or search require the matched ablations from P4–P6; do not attribute every difference between historical and hybrid arms to the LLM.

**Required work:**

- [ ] P7.1 Freeze methods, prompts, runtime, workload identities, evaluator, provider settings, budgets, and the main contrast before final evidence is opened.
- [ ] P7.2 Use declared tasks spanning feasible and infeasible cases, with known reference solutions on a subset. Predefine the target distribution; do not choose only tasks on which the new method appears promising.
- [ ] P7.3 Repeat research episodes; distinguish variability across model/search seeds from generalization across independent workload tasks and vectors.
- [ ] P7.4 Evaluate frozen candidates through the host-owned evaluator. If multiple methods/candidates share final data, predeclare the joint comparison/selection procedure and access restrictions.
- [ ] P7.5 Report primary qualifying-discovery frequency and actual cost. Retain unsuccessful, invalid, budget-censored, and abstaining episodes; do not compare only successful-run averages.
- [ ] P7.6 Review failure trajectories and report uncertainty. Use a prespecified sequential procedure if inspecting accumulating results; do not add repetitions until a desired significance threshold appears.

**Outputs:** Method comparison, reproducible artifacts, primary/secondary analyses, and an adoption/rejection/inconclusive decision for M3.

**Will inform:** Whether to adopt the combined agent, retain only a conventional component, or redirect research.

**G7:** Complete the predeclared analysis and report all outcomes. Claim M3 only if the declared improvement criterion is met. One frozen candidate requiring all endpoints to pass is not the same statistical problem as adaptively selecting among many candidates; choose the analysis accordingly.

**Research basis:** Agent evaluation in [S15]; risk calibration and selection in [S18]; repeated inspection in [S19]. Standard conformal risk control additionally requires suitable loss-family assumptions and is not automatically applicable to arbitrary stopping trees. [S20]

### P8 — Independently confirm a selected policy and assess transfer

**Question:** Does a frozen candidate meet its intended use conditions on independent evidence?

**Dependencies:** An eligible frozen candidate, G0's evaluation contract, and a valid unconsumed entitlement. This phase may follow an earlier development qualifier before P7 finishes; doing so establishes M2, not M3. **Planning effort:** 3–5 working days plus confirmation/data turnaround.

**Required work:**

- [ ] P8.1 Freeze policy, execution/profile identity, workload scope, selection provenance, and independent confirmation protocol before dispatch.
- [ ] P8.2 Reserve the exact entitlement, evaluate without learner access, reproduce raw results, and apply the declared quality and latency criteria.
- [ ] P8.3 Record success, failure, or invalid/incomplete execution without replacing the candidate on the same consumed sample. Revisions return to development with an appropriate fresh entitlement.
- [ ] P8.4 Run the separate canonical acceptance/compatibility process before any serving claim or deployment action. Development confirmation alone is not deployment authority.
- [ ] P8.5 If confirmation succeeds, assess unseen predicates, selectivity/correlation regimes, datasets, or k in separate studies, changing one important dimension at a time.
- [ ] P8.6 Report supported coverage, routing behavior, adaptation cost, measured serving savings, and break-even query volume for an explicitly declared reuse scenario.

**Outputs:** Independent confirmation record, canonical acceptance status, operating scope, transfer results, and economic assessment.

**Will inform:** Whether the result is useful for the target workload and where another development cycle is necessary.

**G8:** Mark M2 and canonical acceptance separately with evidence. Transfer claims require their own evaluated scope. A new persistent-session/amortized-installation objective must be declared prospectively; it cannot retrospectively qualify selective-agent-v1.

## 6. Revised critical path and parallel work

The main dependency chain is:

**P0 contract → P1 cost attribution → P2 execution economics → P3 information diagnosis → supported-family decision (current branch: B1 native effort) → conventional constrained baseline/acquisition if justified → P6 workflow freeze → P7 controlled method comparison.**

**Current critical path:** exact adaptive component locally checked → separately frozen production integration/release/retention/source-guard design → effective target formatter/private-hook and exact-image correctness review → resource qualification only after separate authorization. Native compactability, formatting CPU cost and total charge are unqualified; no payload/object-size subtraction establishes the28GiB gate. All prior allowances stay spent; no native handoff or B2f release. [E371]–[E375]

P8 adds independent policy confirmation and operating-scope assessment. A qualifying earlier candidate may enter P8 without waiting for M3; this does not shorten the evidence required to claim improved agent methodology.

| Work | Earliest useful start | Dependency that must be resolved before conclusions |
| --- | --- | --- |
| Offline outcome/feature inventory and bounded formulation comparisons | Complete through B1b2 result review | G3 finite negative closure, B1b no qualifier and fixed480 quality negative; no supported router family [E107][E108] |
| Evaluation harness, task design, statistical/sample planning | P0 | Frozen methods and final evidence entitlements before P7 |
| Fresh independent-data acquisition planning | P0 | Access/exposure reconciliation before any evaluation |
| Research-state and feedback design | P1 | Stable numerical/acquisition tools before P6 comparison |
| Targeted feature or representation design | After P3 identifies a gap | Native qualification and collection cost before empirical use |
| Partial-index measurement calibration design | B2e source/trace audit complete | B2d feasibility/quality pass; unchanged A/A fails. Fixed graph/PID/placement/observer/warmup design must qualify before a new treatment comparison [E184][E191][E192] |

Parallel work describes independent tasks, not an assumption of additional staff or permission to launch concurrent workloads. Do not overlap timing workloads in ways that introduce unmeasured resource contention.

P2/P3 retain their verdicts and execution. B1b supplies a verified compatible current-index320/640 matrix, but its quality/control results do not support B1c. Activation calibration alone cannot repair deterministic recall losses or the passing-precision reuse overhead failure. The completed fixed480 probe also fails relative quality and validly stops before timing. Completed B2a identifies a separate exact-top10 execution question; the exhaustive truth generator is not its benchmark. Original B2b preflight failed before searches; corrected B2b then exhausted its finite deadline and is verified incomplete. No repeat is recommended. B2c/B2d establish partial-index feasibility/quality but inconclusive speed. Completed B2e supports only an instrumented calibration design; no speedup, interpolation, universal ceiling or protected entitlement follows. [E191][E194] [E90][E91][E95][E107][E115][E144][E147][E150]

Planning effort by phase is a scheduling aid, not a delivery commitment. Set calendar dates after P0 assigns staffing, compute availability, and the branches required by G3. Sample acquisition and cluster queues can dominate elapsed time.

## 7. Conditional branches and stop rules

| Condition | Action | Evidence needed before returning to main path |
| --- | --- | --- |
| Setup/bypass cost exceeds budget | Return to P1/P2 only within an unconsumed, explicitly assigned finite revision allowance | Qualified variant plus actual full-path measurements; present P2 allowance is consumed |
| P2c A/A passes but the unchanged incremental engineering target fails (current result) | Close the finite P2 sequence, retain original and start bounded P3a offline coverage diagnosis | G3 coverage/family evidence; no automatic P2d, rerun or added block [E46][E47] |
| Owned policy state improves reuse but cold admission stays costly | Scope one admission/profile-identity revision with original and P2a references | Qualified immutable identity, full cold/outer accounting and prospective paired comparison |
| A nonregression bound fails despite small pooled point changes | Preserve the failed verdict; plan per-filter precision, order diagnostics and identical-path A/A controls | A new finite comparison contract; no post-hoc margin relaxation or repeat-until-pass |
| Admission economics are understood but query normalization/bypass remains costly | Consider a separately identified query-normalization change within a new declared allowance | Preserved validation/routing semantics and actual net full-path benefit |
| Residual policy-path cost is dominated by an opaque database-wait frame | Freeze a focused server/transport diagnostic rather than attributing the entire gap to one operation | A measurement that separates the relevant server and transport boundaries |
| Execution remains costly but earlier stopping has plausible headroom | Explicit retain-original decision at G2; bounded P3/P4 investigation | Realizable candidate decisions, measured recall and latency; oracle alone is insufficient |
| Supported static23/progress34 reached-grid coverage is complete (current P3a result) | Proceed to a bounded matched-information grouped modeling contract | Finite modeling design before fits; no new acquisition required first [E54][E55] |
| Proposed current Light19 or off-grid scope lacks actual outcomes/costs | Narrow to supported scope or justify minimal targeted P3 acquisition | 3,621 current Light19 stop cells or selected off-grid interventions need evidence; no interpolation or cross-binary/profile cost transfer [E54] |
| P3c/B1b finite campaigns complete, no qualified frontier (historical branch) | B1-review justified one separate fixed480 probe; it is now complete and quality-negative | Preserve prior verdicts; no B1c/calibration repeat [E96][E97][E107] |
| B1b2 fixed480 quality fails (current result) | Probe closed at 1,830; original retained; B2a completed scoped source audit | Preserve quality failure; no480 subset rescue, effort ladder or extra timing [E107][E108][E115] |
| B2a identifies a supported relevant alternative (current result) | Prepare B2b fixed exact-top10 versus640 design on unchanged graph/module | GB2a scoped pass only; full catalog/plan/semantic/quality/control/cost evidence still required [E115][E116] |
| B2a lacks a supported mechanism or sufficient saved metadata | Document no-go or exact missing metadata; retain original | No speculative experiment, graph transfer, free selectivity feature or automatic acquisition |
| B1b2 warm A/A or economics fails | Record inconclusive or negative finite-probe closure respectively | No control correction, extra block, activation repair or automatic router fit [E97] |
| Flexible predictor succeeds and bounded student fails | Targeted representation/compression branch | Export/interpreter parity and measured candidate execution |
| Additional feature helps prediction but costs more than it saves | Reject or restrict the feature group | Measured net benefit if proposing selective collection |
| P5/P6 improvements are inconclusive | Retain simpler baseline; record uncertainty | Fresh predeclared study if more evidence is justified |
| Confirmation fails | Close that selection attempt | A new development selection and fresh assigned confirmation entitlement |
| Declared stopping-family investigation budget exhausted without a promising frontier | Consider B1 instead of indefinitely enlarging the same search | Documented negative findings and a new question/budget |

### B1 — Broader optimization scope

**Current status:** B1b is complete and locally verified after the user’s two Torch jobs. Native conformance passes, reuse A/A passes, activation A/A fails; all contexts fail recall reserve and forced640 wrapper overhead. Frozen aggregate: `measurement_inconclusive`; B1c deferred. Retain original execution. B1-review and B1b2 are now complete;480 native conformance passes but relative quality fails overall and both filtered strata. The finite probe closes before timing. B2a is complete and recommends a new exact-top10 design, not router fitting or an effort ladder. [E90][E91][E93][E107][E115]

Potential directions are query-dependent search effort, approximate/exact plan selection, or alternative filtered-search traversal/index designs. MoReVec motivates examining selectivity and query-filter correlation; ACORN provides a distinct filtering-aware traversal/index direction. [S3][S21]

- [x] B1.1 Record why the finite stopping investigation no longer supports more tuning under its allowance: P3c risk protection improves, but activation proxies remain negative; no qualifying family or missing reached-grid-label diagnosis. [E69][E70]
- [x] B1.2 / B1a / NEXT-SCOPE-01 Complete read-only source/API/query-context/timing/identity feasibility audit. Engine ef_search is supported; current API needs an experimental interface. Old effort sweep uses another graph; same-current-index320 evidence has an older profile. Three cheap contexts do not identify within-filter vector difficulty. Preserve all324 code/source hashes; no tests/experiments/fits/native access. [E76][E77][E78]
- [x] B1.3 / B1b / NEXT-EFFORT-01 Freeze native320/640 interface/current identities, original640 and source320 baselines, exact references, full activation/reuse costs, A/A and net-benefit gates, exposed200-vector cohort and one two-allocation/139,272-search contract. Zero protected/provider/fit entitlement. [E84]
- [x] B1b.1 Implement isolated effort envelope and immutable origin/effective bindings; seventeen local correctness tests, full mock driver/two-block serialization/replay, lint/format, sealed package/checksum and shell checks pass. No native qualification follows from mocks. [E85][E86][E88]
- [x] B1b.2 Complete both native qualifications: actual settings/HNSW plans, original/forced640 and source320 outputs, alternating effort isolation, exact-truth independence, SQL rollback/session recovery, restored data and unchanged index/module pass. [E90][E93]
- [x] B1b.3 Complete both serial blocks and full raw return/replay:139,272 searches,76,800 retained observations,19,200 warmups,38,400 conditioning calls; all40 archive members and26 locked raw files verified. Report metadata’s `/results` alias is reconciled to proven submission identity only; all other discrete/gate fields and tolerance checks pass. [E90][E92][E93][E94]
- [x] B1b.4 Apply frozen gates unchanged: reuse A/A32/32 pass, activation2/32; all320 contexts fail recall reserve and forced640 overhead. Preserve formal aggregate measurement_inconclusive and no qualifying context/regime; no B1c, adoption or automatic repeats. [E90][E91]
- [x] B1-review.1 / NEXT-EFFORT-REVIEW-01 Complete read-only admission/validation/quality/identity audit and go/no-go. Pin685 existing files, preserve old gates, freeze one fixed480 native quality-first contract; zero code/tests/experiments. [E96][E97][E98][E99][E100]
- [x] B1b2.0 / NEXT-EFFORT-MID-01 Specify prospective identities, phases, warm-only costs, fresh quality/A/A/benefit gates,30+1,800 early screen and59,430-search/one-allocation maximum. No480 outcome was observed. [E97]
- [x] B1b2.1 Isolated harness,22 source/22 sealed mock checks,150-file manifest/151-member archive, order/input/code seal and exact Torch commands complete; no adopted/frozen code changed or native run occurred. [E102][E103][E104][E105][E106]
- [x] B1b2.2 Native conformance passes; quality-first overall/votes32/votes108 reserve failures correctly stop the job at1,830 searches. No timing/A/A/benefit observations acquired; no conditional workload remains required after failure. [E107][E109]
- [x] B1b2.3 Verify24 archive members,15 locked raw files, exact fresh/remote/download parity and888 immutable files; record `closed_negative_quality`, quantified shortfalls and actual charges. No automatic B1c/adoption/confirmation. [E107][E108][E110][E113]
- [x] B1.4 Keep measured fixed-effort results separate from fixed-index stopping studies; preserve all earlier negative/inconclusive findings and retain original. [E107][E108]

**GB1: pass, scoped feasibility only. GB1b native conformance: pass. GB1b aggregate: measurement_inconclusive; no qualifying context/regime.** Reuse precision passes but recall/overhead fail; activation precision fails. Finite B1b work is complete, allowance consumed, original execution retained. B1b2 now closes `closed_negative_quality`;480 relative quality fails and single-reader timing/admission benefit remains unmeasured because the quality stop was required. No timing rescue, automatic router or deployment follows. [E90][E91][E95][E107][E108]

### B2a — Completed read-only plan/filter/index feasibility

**ID:** `NEXT-PLAN-SCOPE-01`. **Status:** complete; **GB2a scoped pass, GO for B2b design only**. **Owner/reviewer:** Codex source/evidence review. All 349 source/code and 907 immutable hashes pass. No code/test/experiment/fit/simulation/native/DB/provider/Torch/protected access. [E115][E116][E117][E118]

| Step | Completed deliverable | What it informs / limit | Gate |
| --- | --- | --- | --- |
| B2a.1 Mechanics/identity | Native top10 versus exhaustive truth source traced; six saved plans/settings, provisioning DDL and selected graph/module pinned | Same-graph exact endpoint is possible; full current scalar catalog/cache/exact plan remains unknown | Complete, U1 assigned to future native qualification |
| B2a.2 Alternatives/inputs | Exact/scalar/partial/partitioned/traversal matrix; current API/target limits; actual AST/k versus offline selector leakage | Exact top10 is narrowest supported new comparison; current20%/50% filters give no economy guarantee | Complete; no map selection or hidden feature |
| B2a.3 GB2a | Scoped GO plus named unknowns, finite future resource proposal, quality/control/full-cost requirements | Actual supported mechanism justifies design; no performance, implementation or spending acceptance | Complete; B2b design recommended |

- [x] B2a.1 Complete pinned mechanics/identity/unknown inventory. [E116][E117]
- [x] B2a.2 Complete alternatives/input-cost matrix without acquiring new outcomes. [E115][E116]
- [x] B2a.3 Record GB2a scoped GO and one prospective bounded design recommendation. [E118]

Primary distinctions: full truth has no LIMIT and fetches every eligible row; an exact top10 endpoint must be measured independently. Partial targets/partitioned relations are rejected by current public inspection. ACORN-1's query-time expansion does not prove compatibility with current pruned graph; no native GUC implements it. Scalar-index additions change catalog/plan identity even if old HNSW bytes persist. [E115][S21][S33][S34][S35][S36]

### B2b — Frozen, implemented and sealed exact-top10 comparison

**ID:** `NEXT-EXACT-TOPK-01`; correction `exact-topk.v1.catalog-fix`. **Status:** closed_inconclusive, verified finite incomplete_budget_exhausted; partial-return review complete. Qualification/quality prefix pass; full catalog/final integrity/two-block A/A/economics remain unassessed. Retain original, preserve both spent allowances, do not repeat E136. B2c is proposed read-only next. [E142][E143][E144]

| Step | What it must do | What it informs / current gate |
| --- | --- | --- |
| B2b.0 design | Pin graph/module/data, native statement/truth, exact setting overrides, schedule, full cost/quality/A/A/multiplicity/resources | Complete: immutable E120 precedes implementation;40,230 searches/one allocation |
| B2b.1 local preparation | Isolated immutable readers, symmetric guards, strict admission, error lifecycle, metadata/current/cached plans, raw replay, local checks and seal | Complete:33 source/33 sealed checks,153 files/154 archive members; native still pending |
| B2b.2 native/quality | Verify saved qualification/quality prefix and identify unacquired final native audits | Prefix passes unchanged sealed replay across600 references; final full catalog/index/module integrity remains unestablished [E142][E143] |
| B2b.3 controls/cost | Complete two-block/replica matrix,16 A/A intervals and adjusted economic endpoints required | Not fulfilled:12,208/19,200 retained; full gate verdict unavailable. Descriptive complete block0 unfavorable56.11x; no subset rescue [E142][E144] |
| B2b.4 replay/close | Verify available corrected raw, source/identity/quality/timers/coverage and explicitly record missing evidence | Complete partial audit; finite campaign closes incomplete, no repeat/adoption/full performance verdict [E142][E143][E144] |

- [x] B2b.0 Freeze finite design, identities, exact schedule, multiplicity and resources. [E120]
- [x] B2b.1 Implement/check/seal the isolated harness; source/old-evidence preservation and transport mock checks pass. [E121][E122][E123][E125]
- [ ] B2b.2 Corrected actual catalog/plan/semantic/quality gates pass after original failure is verified; original job20941363 already consumed its allowance. [E126][E128]
- [ ] B2b.3 If quality passes, complete two temporal blocks/new A/A and adjusted economic gates within the same allocation. [E120]
- [x] B2b.4 Audit all available corrected partial raw, prefix quality, actual costs and missing full gates; close finite spent campaign incomplete without promoting descriptive costs to performance acceptance. [E142][E143][E144]

Finite contract:30 qualification+1,800 references; quality-negative stop1,830, maximum40,230 backend attempts including19,200 retained,9,600 warmups and9,600 conditioning.12,012 plan packets/4 catalog snapshots on complete acquisition; observer SQL capped40,000 with separate timing.14 admissions/5 live; one4CPU/32GiB/two-hour allocation with6,600-second work deadline. All queries are existing200 exposed vectors/600 cases; zero providers/fits/new or protected vectors/confirmation. Preserve complete valid top10,95% floors,−0.25pp development reserve and exact tie-aware semantics. A/A must pass all16 intervals. Adjusted upper gap/log bounds must meet.10ms/2% and direction in both blocks before calling any of4 reports promising. Bootstrap development evidence is not independent acceptance. [E120][E122]

Primary scope is a conditioned warm persistent reader with unchanged JIT/parallel/work_mem/cache settings. Startup/snapshot/request admission/first-use/plan/catalog audits/conditioning/cleanup are charged separately, never subtracted. EXPLAIN EXECUTE observes and conditions prepared-plan behavior; no unconditioned serving/activation claim follows. Native errors/unknown dispatch/limits do not grant retries or additional blocks. [E120][S39][S40]

### B2b recovery gates and progress

| Step | Must do | What it informs / decision gate | Status |
| --- | --- | --- | --- |
| B2b.R0 record | Preserve pasted job/campaign/failure/resource identity and distinguish status from raw verification | Failed qualification, zero reported searches; no recall/cost/A/A conclusion | Complete status record only [E126] |
| B2b.R1 local correction | Freeze separate addendum, fix exact JSON type, retain identities/gates, persist rejected catalog, verify source/sealed/package/preservation | G0-repair local readiness only; cannot establish native catalog correctness | Complete43/43 checks; original preserved [E128][E129][E130] |
| B2b.R2 failed return | Verify original checksum/archive/submission/job/terminal accounting, zero searches, closed/stopped cleanup and protected hashes | Pass:19 archive members,0 searches, one closed reader/stopped DB, captured protected hashes identical | Complete [E134][E135] |
| B2b.R3 release | After R2, release separate one-attempt commands; new reservation is created only upon future submission | Same seal/gates, original allowance consumed; one additional prospective allocation; no retry reset | Complete handoff E136; not submitted |
| B2b.R4 native continuation | Require full actual initial/final identities, quality/timing and raw replay | Not fulfilled: verified deadline stop; final full checks/complete timing missing. Both allowances spent | Closed incomplete, no automatic continuation. Partial audit complete [E142][E143] |

- [x] B2b.R0 Record reported failure without claiming independently verified raw. [E126]
- [x] B2b.R1 Complete separate prospective correction/local seal and preservation. [E128][E129][E132]
- [x] B2b.R2 Independently verify downloaded failed original, including checksum/accounting/cleanup/protection. [E134][E135]
- [x] B2b.R3 Release separate corrected one-attempt commands after R2 pass; unchanged package. [E136]
- [ ] B2b.R4 Full successful native/final-integrity/two-block A/A/economic protocol was not fulfilled; finite campaign is closed and must not be resumed automatically. [E142][E143]
- [x] B2b partial disposition: independently verify available prefix/quality/timers/coverage, diagnose costs, retain missing-evidence limits and decline repeat spending. [E144]

### B2c — Completed indexed/filter-aware ANN alternative-scope review

**ID:** `NEXT-ANN-ALTERNATIVES-01`. **Status:** complete_scoped_design_go. **Owner/reviewer:** Codex read-only source/saved-evidence review. [Report][E147], [machine audit][E148], [inventory][E149] and [receipt][E151]. No implementation, query, index/module change, fit, provider, protected-vector use or allocation occurred.

| Step | Completed work | Informs / decision |
| --- | --- | --- |
| B2c.1 reconcile | B1/B2a/B2b results, missing full catalogs/final checks and actual phase costs reconciled | No current effort/exact repeat; no retrospective integrity claim |
| B2c.2 shortlist | Partial graph, scalar index, filtered shadow table, partitions and ACORN/native traversal compared | Select one smallest physical intervention; public partial-target rejection remains |
| B2c.3 select | One >=108 partial cosine HNSW with full table/global IDs and unchanged module | Scoped design GO, conditional on experimental adapter/native plans; no production API support |
| B2c.4 resources | Historical build costs and exact-path charge reviewed; finite stage/search/observer/storage ceilings plus early futility frozen | No literature speed transfer; no positive verdict from preview |
| B2c.5 handoff | Separate B2d prospective design records scope, unknowns, quality/controls and terminal outcomes | Implementation/local checks/seal next; no current user command |

- [x] B2c.1–2 Complete evidence/source/cache/alternative-cost review. [E147][E148]
- [x] B2c.3 Record scoped mechanism-design GO and native/public compatibility limits. [E147]
- [x] B2c.4–5 Freeze separate prospective B2d contract before implementation/compute. [E150]

### B2d — Completed partial-ANN diagnostic; measurement inconclusive

**ID:** `NEXT-PARTIAL-ANN-01`; original `partial-ann.v1`, corrected `partial-ann.v1.settings-fix`. **Status:** complete_verified_measurement_inconclusive. Full job21048213_0/raw verify; native/quality/final integrity pass, nominal endpoints pass, all4 A/A intervals fail. Retain original and consumed allowances; B2e complete, B2f design only next, no commands. [E184][E186][E190]

| Step | Must do | Gate / what it informs |
| --- | --- | --- |
| B2d.0 local readiness | Isolated experimental adapter/statement, two-copy ownership, strict catalog/cache/AST/budget/stop/archive checks; preserve public code and old seals | Seal only after local correctness/preservation; mocks cannot qualify native support |
| B2d.1 native preflight/build | One separately authorized allocation; restore two identical full copies, add exactly one >=108 HNSW only on candidate; unchanged module/original graph | Persist full catalogs, raw differences, bytes/settings/identities; any incompatibility stops, no module patch |
| B2d.2 conformance/preview |10 fixture searches and192 ANN preview calls over24 fixed vectors | Stop for complete median ratio>=2, mean gap>=.10ms and >=20/24 slower pairs; passing only permits quality |
| B2d.3 scoped quality |200 fresh full truths +200 baseline640 +200 candidate640 | Complete valid outputs, both recall>=.95, lower95% delta>=−.0025; no timing on valid failure |
| B2d.4 timing/controls | Two complementary blocks, six live readers including two conditioners;16,000 formal queries | Four one-context A/A intervals inside±.10ms/±log1.02; adjusted upper gap<=−.10ms/log ratio<=log.98, both blocks negative |
| B2d.5 final/replay | Full final catalog/data/original+new index/module proof, durable raw lock/cleanup and independent sealed replay | Missing evidence stays incomplete; positive scope only warm >=108 development, no router/adoption |

Prospective cap:16,802 search attempts,8 admissions/max6 live,5,700 plan packets,20,000 observer SQL plus4,040 truth helpers/1,000 startup statements. Proposed one3h4CPU32GiB allocation,10,200s work deadline; restore1,200/build1,800/conformance+preview600/quality2,400/formal2,400/final600 seconds. Scratch/memory/native compatibility must be checked later. Original60 confirmation and37 reserved vectors remain untouched. [E150]

- [x] B2d design frozen before implementation or measurement. [E150]
- [x] B2d.0 Implement/check/preserve/seal isolated comparison;55 source/55 sealed checks,161-file seal and exact commands ready. [E154][E156][E157][E158]
- [x] Repair captured quota-format preflight failure in separate source/seal;61 source/61 sealed checks and1,733 prior hashes pass; shared original allowance preserved. [E161][E164]
- [x] User uploaded/submitted quota-fix once; job21043219_0 reported FAILED at initial environment guard,0 searches/0 readers; allowance consumed. [E167]
- [x] Collect/download and independently verify original failed B2d archive/catalog/accounting/cleanup/protected evidence; exact work_mem mismatch diagnosed. [E171][E172]
- [x] Freeze/implement/check/seal separate settings correction;75 source/75 sealed tests,169-file seal and1,960 prior hashes pass. [E173][E176][E177]
- [x] User executed corrected handoff; job21048213_0 reports completed16,802 searches/two blocks/quality/final integrity. [E180]
- [x] Prepare separate prefix-recovery raw collector,8 local checks and immutable preservation. [E182][E183]
- [x] User collected/downloaded raw; independent exact-name/37-member/full raw/quality/controls/economic replay and fresh parity complete. [E184][E187][E189]
- [x] B2d.1–5 Complete native campaign/review; close measurement_inconclusive on failed A/A, preserve all other scoped evidence and spent allowances. [E186][E190]

### B2e — Completed read-only replica/session control audit

**ID:** NEXT-PARTIAL-CONTROLS-01. **Status:** complete_read_only_design_GO. All existing traces/source audited; no code, tests, bootstrap replay or experiment.2,235 prior hashes preserved. GB2e supports one separately frozen instrumented A/A calibration design; causal root cause and a specific remedial setting remain unproved. B2d remains measurement_inconclusive. [E191][E192][E193][E194]

| Step | Completed work | Informs / decision gate |
| --- | --- | --- |
| B2e.0 evidence boundary | Pin raw/seal/earlier verdict and2,235 inputs; zero-execution scope | Audit cannot replace original gates or create remote facts |
| B2e.1 session/work identity | Per-object connection ownership; identical a/b binding/GUCs and800 paired plan/parameter/cache packets per cell | No observed wrong work or generic/custom divergence; same-cell replicas share one graph/server |
| B2e.2 timing mechanism | Retained1→2 falls across all readers; partial gap remains.843248ms at repeat2 and b faster193/200 query means | Progressive transient plus persistent session-associated effect; no warmup plateau or CPU/cache cause identified |
| B2e.3 prospective design decision | Fixed labels→connections, fixed observer order and conditioner/position alias; physical PID/CPU/wait/cache evidence missing | GO to instrumented calibration design; no blind repeat, faster-backend selection or changed margins |
| B2e.4 handoff | Detailed report/descriptive JSON/provenance/receipt and roadmap updated | B2f feasibility/contract freeze next; no code, allocation or user commands now |

- [x] B2e.0 Pin evidence and read-only scope. [E193]
- [x] B2e.1 Complete ownership/settings/plans/counters/source audit. [E191][E192]
- [x] B2e.2 Complete descriptive repetition/block/round/position/query audit, keeping all rows. [E192]
- [x] B2e.3 Record conditional calibration-design GO and missing causal evidence. [E191]
- [x] B2e.4 Save report/preservation/receipt and update tracking. [E194]

### B2f — Release hold after third startup failure; native gates pending

**ID:** NEXT-PARTIAL-CALIBRATION-01. **Protocol:** partial-calibration.v1. **Status:** release_held_resource_qualification_design_needed. Frozen E195/E196/E197 remain unchanged. Three failed allocations verify, all0 searches; the latest guard hashed the wrong schema. Isolated correction and whole-entry-point local checks are complete. No production package/fourth handoff is released. Requested accounting configuration is received; R2a startup-only resource design/qualification and R3 final release review precede native N0–N4; B2d/original execution unchanged. [E219][E220][E221]

| Phase/gate | Frozen requirement | Informs / current disposition |
| --- | --- | --- |
| B2f.0/F0 fixed scope | Exact stopped-cluster full/partial graph identities, data/module/image/GUCs, required PID/CPU/proc observations and mandatory versus optional capability rules | Contract unchanged; preliminary user-reported source/hash match passes, full clean-copy/native capability remains unverified [E202] |
| B2f.1/F0 prospective freeze | Two fresh connection epochs/reversed creation, crossed labels, fixed cell CPUs with epoch crossover, independent conditioner/order balance,4 warmups+3 retained, bulk observers and paired eight-vector diagnostic; full counts/analysis/stops | Design frozen; no data-adaptive regime or label cancellation; no treatment speed verdict |
| B2f source prerequisite | User E195§12 output received October27: exact paths/control files/three hashes and reported space | Preliminary pass; no PID-file stop; no full clean-shutdown/copy/footprint/core proof. No rebuild/allocation [E201][E202] |
| B2f.2/L0 implementation/readiness | Isolated implementation; full mocked acquisition/reconstruction and negative ownership/PID/namespace/affinity/order/count/stop/archive checks, preservation and immutable seal | Pass:78/78 source and78/78 sealed; lint/format/AST/shell/archive parity;2,255 prior pins unchanged. Synthetic only [E206][E208] |
| B2f.L0-fix launch correction | Verify terminal pre-Python failure and old seal/raw; pass absolute host interpreter and explicit srun export; execute synthetic shell regression and preserve all prior inputs | Complete:6 raw members verified,88 source+88 sealed checks and archive parity; old job remains spent [E209][E211] |
| B2f.L0-metadata restore correction | Verify zero-search second failure and source/copy/cleanup evidence; privately copy only pinned identity sidecar; real frozen constructor/binding/snapshot/native/reference/full-schedule tests | Complete local readiness:32 raw members verify,101 source+101 sealed checks/static/archive parity,2,781 prior pins; no native qualification [E214][E216] |
| B2f.R2–R3 release gate | Supplied accounting configuration reviewed; freeze a separate full-size startup-only resource qualification, justify outstanding workload memory and complete final release review | CONFIG COMPLETE; RESOURCE/RELEASE HELD. No code/run/package in current review; next design only [E224][E225] |
| B2f.3/N0–N3 acquisition | Only after R2–R3 pass, a separate explicitly budgeted new handoff; verify independent stopped-cluster restores, four allocated physical cores, mandatory telemetry, source/data/graphs/module and full cleanup | Actual compatibility remains unassessed; no larger/extra allocation on failure |
| B2f.4/N4 trusted analysis | Complete identity/coverage/final proof plus all56 unchanged-margin physical A/A/half-epoch/retained-stability intervals pass | Scoped calibration qualification only; failure=inconclusive or failed/incomplete qualification, no rescue subset |
| Later treatment comparison | Separate quality/controls/economics/placement-balance/final-proof contract under qualified regime | Not automatically authorized by calibration; adoption/acceptance remain later |

One allocation ceiling:3h4CPU32GiB,10,200s total work including600s final reserve,480s host envelope. Search count10 conformance+600 quality+80 priming+14,400 primary+1,152 diagnostic=16,242; remaining560 below16,802 outer envelope are not spendable.10 admissions/max6 live readers/max8 SQL connections;4,200 plan packets,13,500 observer/1,000 startup/4,040 truth-helper SQL;5,500 telemetry bundles/44,000 proc reads/11,200 affinity operations/60s telemetry. Exact stage, incremental scratch/inode/home/evidence/memory caps in E195/E196. These are unchanged per-attempt ceilings; three attempts are now spent with0 searches, and no further allocation is released. [E196][E198][E219]

Margins unchanged: recall floors≥.95/lower95% delta≥−.0025; A/A intervals inside±.10ms and±log1.02. Require8 cell/epoch physical-pair intervals+16 half-epoch+32 retained-adjacency stability=56 timing intervals, all mandatory.10,000 vector-group bootstrap draws/seed20261019/linear quantiles; pointwise95%, no simultaneous95% claim or endpoint selection. Future economic upper gap≤−.10ms/log ratio≤log.98 at.99375 and both block directions remain fixed but unevaluated here. [E195][E196]

- [x] B2f.0 Freeze exact scientific identities, restoration requirements and required/optional physical observations; actual feasibility remains pending. [E195][E196]
- [x] B2f.1 Freeze explicit order, full charges/stops/margins and independent-analysis contract before code; save preservation/receipt. [E197][E198][E199]
- [x] User returned E195§12 read-only inventory; all three reported hashes match, paths/control files and positive quota headroom recorded. No startup/submission. [E201][E202]
- [x] B2f.2/L0 Implement/check/preserve/seal on user request;78 source+78 sealed synthetic checks and release integrity pass. [E205][E206][E208]
- [x] Original B2f job21111616_0 returned; verify pre-Python FAILED/2:0, zero searches and preserved6-file archive. [E209]
- [x] B2f.L0-fix: implement/check/seal isolated launcher correction; original design and evidence unchanged. [E210][E211]
- [x] Verify second21129331_0 startup identity failure/source preservation/clean shutdown; no searches/readers. [E214]
- [x] B2f.L0-metadata: correct copy/provenance, add actual frozen-backend full integration, check/preserve/seal. [E215][E216]
- [x] Verify third21159802_0 failed eligibility guard;0 searches/two readers, unchanged source/copy/catalog/protection and clean cleanup. [E219]
- [x] B2f.R0–R1: reproduce schema defect; correct isolated startup guards; add full entry-point startup/acquisition/finalization/cleanup and negative regressions. [E221]
- [x] B2f.R2-config: user supplied requested accounting fields; record exact interpretation and compute-node/component/limit gaps. [E223][E224]
- [x] B2f.R2a: freeze NEXT-STARTUP-RESOURCE-01 exact zero-search scope/budgets/observations/decision before code. [E227]
- [x] B2f.R2b: isolated implementation/thorough source+sealed checks/preservation/seal and exact one-additional-allocation commands. [E228][E229][E230]
- [x] B2f.R2c: user resource-only job completed; raw/independent replay verified. Startup complete, memory margin inconclusive; no full-calibration entitlement. [E232][E233]
- [ ] B2f.R3: after R2, complete final release review, separate seal/checks/preservation and explicit additional-allocation handoff. No production package now. [E221]
- [ ] B2f.3/N0–N3: only after R2–R3, acquire complete native qualification/final proof with a separately released bounded job.
- [ ] B2f.4/N4 Independently verify/reconstruct complete raw and decide calibration; no retrospective B2d change.

### B2f.R2 — Startup-only resource qualification, separate from full calibration

**ID:** NEXT-STARTUP-RESOURCE-01. **Protocol:** startup-resource.v1. **Status:** complete_startup_resource_margin_inconclusive; allocation spent, no retry.

| Phase/gate | Must do | Informs / decision |
| --- | --- | --- |
| SQ0 freeze | Exact unchanged source/graphs/module/backend; one-hour, four-CPU, 32 GiB job; zero searches; fixed stages/SQL/telemetry/storage/reserve rules | Complete pre-code freeze E227; no new scientific policy/margin |
| SQ1 local readiness | Exercise actual launcher/host/runtime/frozen startup methods with synthetic boundaries; zero-search guard/negative/cleanup/archive/transport and independent replay checks; immutable seal | Complete local release E229; native availability/memory remains unqualified |
| SQ2 native acquisition | Start bounded sampler; full source/copy/snapshot/admission/lifecycle/final proof with no searches | Complete: 21171789_0/0:0, ten admissions, both epochs, zero searches and verified cleanup [E232][E235] |
| SQ3 independent analysis | Verify archive/locks/job/package/zero-search SQL/lifecycle/source/cleanup/memory; apply frozen total-charge margin | Complete: trusted replay agrees; 32 GiB peak + 4 GiB allowances > 32 GiB, +592 max/0 OOM. Resource margin inconclusive [E233][E236][E237] |
| SQ4 resource decision | Review resource evidence and remaining full-workload requirements | Review outcome: hold full calibration; NEXT-STARTUP-MEMORY-01 read-only audit/design next, no new job [E232] |

- [x] SQ0 design and resource contract frozen before implementation. [E227]
- [x] SQ1 isolated code/local checks/preservation/seal and exact commands. [E229][E231]
- [x] SQ2 user upload/single submit/status/terminal collect/download, verified complete. [E234][E235]
- [x] SQ3 trusted independent reconstruction: startup complete, resource margin inconclusive. [E236][E237]
- [x] SQ4 resource review closes this job with full calibration held; no repeat or larger request. [E232]

### NEXT-STARTUP-MEMORY-01 — M3 complete; native identity passes, resource margin inconclusive

| Phase | Must do | Informs / decision |
| --- | --- | --- |
| M0 audit (complete) | Review actual producer/inheritance, row/vector/NumPy/JSON lifetimes, IDs/identity and all snapshot consumers from existing source/trace | Scoped source feasibility; 116 files/137 references; retained rows/cursor remain required, no measured savings [E239][E243][E244] |
| M1 prospective design (frozen) | Original per-row canonical bytes with exact root framing; scoped digest binding/restoration, bounded buffers/counts, semantic/local/native/resource gates | Complete design-only GO for startup-resource.stream.v1; no implementation/native readiness [E240][E241] |
| M2 implementation/readiness (complete) | Isolated exact-byte hashing, scoped restoration and independent replay; actual entry-point/constructor/cleanup/signal tests, source/seal/static/archive/preservation checks | 155 source/155 sealed pass; 3,468 prior inputs preserved; local compatibility only, native savings unmeasured [E246][E247][E250] |
| M3 resource requalification (complete; closed_inconclusive) | Job21224521_0 and48 raw members/fresh trusted replay verified, zero searches, exact identity/restoration/startup/lifecycle/cleanup | Native compatibility pass;32 GiB peak/+259 max fails frozen margin/no-event qualification; allowance spent, no repeat [E252][E253][E256] |
| M4 later full calibration (conditional) | Satisfy resource and outstanding workload-memory/release requirements before separate handoff | Actual full B2f scientific/native gates remain mandatory |

- [x] M0 read-only consumer/lifetime/identity compatibility audit complete; candidate savings remain unmeasured. [E239][E243][E244]
- [x] M1 first per-row canonical-hash remedy and exact equivalence/resource design frozen before code. [E240][E241]
- [x] M2 isolated implementation/local checks and source/sealed readiness review complete; 155/155 in each suite, archive/static/116 source pins and 3,468 prior inputs pass. [E246][E247][E250]
- [x] M3 user acquisition/terminal collect/download and independent analysis complete: exact full-size identity/startup/cleanup pass; resource margin inconclusive, job spent. E249 commands are historical and must not be rerun. [E252][E253][E257]
- [ ] M4 remains conditional/unreleased; startup-only qualification cannot establish full query-workload memory or release full calibration.

### NEXT-STARTUP-MEMORY-02 — W0–W2 audit complete; GO to attribution design only

**Scope/budget:** Read-only pinned source and both existing resource returns; zero code changes/tests/fits/searches/provider calls/new native measurements/allocations. Keep both inconclusive results and exact identities. Not a preapproved remedy or new experiment. [E252]

| Phase | Must do | Informs / decision gate |
| --- | --- | --- |
| W0 evidence/phase attribution (complete) | Pin both source/raw/seals and reconcile process/phase/transaction brackets | 246 source/recipe pins, 3,961 preserved inputs; one event strictly inside first final verification and boundary uncertainty retained [E261][E262] |
| W1 lifetime/consumer/I/O review (complete) | Trace producer/constructor/shared ownership/close/final checks and current verification/fetch/hash/copy paths | One persistent snapshot; streamed verification/final overlap; API-versus-driver accounting gap; individual allocations/file ownership unmeasured [E259][E263] |
| W2 design decision (complete) | Compare cursor/batch/cleanup/storage/I/O options against exact semantics and unchanged gate | No-go blind single-remedy run; GO separate bounded zero-search lifetime/I/O attribution design only; no implementation/allocation [E259][E260] |

- [x] W0 source/raw/phase/process/transaction evidence reconciled; boundary uncertainty explicit. [E261][E262]
- [x] W1 retained-object/consumer/verification/copy/hash/fetch review complete; accounting gap recorded. [E259][E263]
- [x] W2 GO to separate attribution design, no-go unqualified remedy rerun; no experiments. [E260]

**Critical dependency:** main/A3/lifecycle proofs preserved → exact adaptive component freeze/local consumer/allocation checks complete → prospective producer-integration and exact-target proof design. Old native proofs do not qualify the new type; memory margin remains held and every prior allowance stays spent. [E371]–[E375]

### NEXT-STARTUP-ATTRIBUTION-01 — Native compatibility and C3 complete; main A2 ready

| Phase | Must do | Informs / decision gate |
| --- | --- | --- |
| A0 design only (complete/frozen) | E265/E266 freeze102 checkpoints, exact monitoring/driver binding scope and restoration, API/internal command/fetch/page/row/role semantics, resource/observation/cleanup caps and gates before code | Design-only feasibility; actual image/tool/private-driver behavior unqualified. Both source/seal local readiness and native gates remain mandatory; no implementation/job released [E267][E268][E269] |
| A1 implementation/local readiness (complete) | Isolated harness; actual original-code/private-driver/generator/host/runtime/signal/cleanup paths, bounded counters and independent replay;155 baseline plus100source/100sealed checks | Local readiness passes; no native image/resource/causal/performance claim. A2 release remains separate [E271][E274][E275] |
| A2 release audit (complete / held) | Review exact local/image reference and release gates; identify local3.12.7 versus saved build3.12.15 before dispatch | Native handoff held; unchanged A0 capability-stop rule [E277][E279] |
| A2.0a image inventory (complete/verified) | One5.6275s invocation, exact raw/capsule/parent/hash/replay verification; zero DB/SQL/snapshot/search/job | Only Python patch differs; actual3.12.15 matches A0. Nine hooks/parser/libraries and literal/source mapping capabilities match; full runtime semantics remain unqualified [E283][E286] |
| A2.0b compatibility decision (complete) | Diagnose A1 local-reference capture error; isolated strict target-reference correction now qualifies under exact native 3.12.15 | Historical/local reference retained; no wildcard/fallback/dependency/image change or repeated inventory [E288][E319] |
| C0/C1 correction/local readiness (complete) | Exact references, pre-restore mapping/mask gate and finite controller preserved | Original 128+128 local checks; actual target synthetic 128+128 now verified by C2B. Main real capability/resources remain pending [E289][E319] |
| C2 local emulated route (unqualified/closed) | Existing exact Docker build, bounded local execution; QEMU signal/no Python receipt preserved; owned container removed | No pass inferred, no blind emulated retry [E289][E293] |
| C2 native correctness (failed; raw verified) | Job21348020: ReplayTests setup ERROR then source deadline;86 completed successes, no sealed/guard qualification |13-file return/eight locked files and exact reference verify; omitted offline metadata diagnosed; old allowance spent [E295][E296][E297] |
| C2 fixture/dependency correction (native failed; raw verified) | Job21367064:96source passes/zero error events, metadata/provenance/final-integrity pass; source deadline in fixture reseal |16-file/11-lock verification; second allowance spent; full target correctness unqualified [E301][E302] |
| C2 prepared fixtures (local complete; native failed) | 119 native source passes/no recorded errors; 16-file/11-lock return and exact dependency/provenance/final host integrity verify | Third allowance spent; incomplete child/source/sealed qualification; no retry [E308][E309] |
| C2B budget/correctness (complete, allowance spent) | Native job 21443102: all 128+128 cases and strict final identity/guard/build/seed/cleanup/timing/integrity proofs pass | 24-member/19-lock return verified; no main-workload memory/performance inference; E315 spent [E318][E319] |
| C3 main release (complete; handoff spent) | 619-file production seal/620-member archive, all 128 final-package local cases and native readiness/controller/preservation checks pass | Released main job21459623_0 is now complete; no further allocation or automatic retry [E320][E321][E334] |
| A2 native attribution (complete, informative) | Job21459623_0 COMPLETED0:0/14m16s; all102 checkpoints, strict locks/identity/accounting/overhead/cleanup and fresh replay pass; zero searches | Main allowance spent; new decode/matrix/pool brackets are descriptive;32GiB peak/780max events leave resource margin inconclusive [E333][E334] |
| A3 remedy decision (complete; offline prototype qualified) | Select one exact binary64+integer-tag representation, freeze before code, verify actual canonical/matrix/ID/metadata/query/workload/save/sample consumers in33 bounded guarded cases | Explicit internal type/mutability scope;756 prior files/128+128 receipts preserved. No native correctness, memory or generic-list equivalence claim [E336][E338] |
| Remedy integration (native correctness complete; resource handoff ready) | One-row producer and original constructor/eligibility/admission remain unchanged; bounded metadata view preserves immutable source and exact ordinary fields | All 100+100 new harness cases and old 128+128/56+56 native proofs intact; one new E352 resource allocation only, actual margin pending [E348]–[E353] |
| A3 startup-memory local release (historical; allowance spent) | Corrected context passed110+110checks and launched21542975_0 | Terminal resource failure independently audited; never repeat E358. Offline lifecycle review does not release a new allocation [E363]–[E370] |

- [x] A0 human/machine/checkpoint/driver/source design frozen before code;102 required checkpoints, explicit ledgers/caps/restoration/interpretability and3,974 preserved inputs. [E265][E266][E269]
- [x] A1 isolated implementation and actual-path local source/sealed qualification complete; A0 freeze preserved. A2 actual-image/native qualification remains unreleased. [E271][E272][E275]
- [x] A2 release review: image-reference build mismatch found and dispatch held; A0/A1 preserved. [E277][E279]
- [x] A2.0a source-only inventory implemented,29 source/29 sealed checks and exact archive/member/preservation verification complete; only inventory commands released. [E280][E281][E282]
- [x] User inventory/download and independent verification complete: exact raw/capsule/replay; only Python patch mismatch, actual3.12.15 matches A0; one direct invocation spent,0 allocations. [E283][E285][E286]
- [x] Compatibility decision: GO isolated strict target-reference correction/readiness; no dependency/image change or inventory repeat. [E288]
- [x] C0/C1 correction, strict exact references and pre-restore source/mask gate;128normal/128guarded local tests pass, original inputs preserved. [E289][E291]
- [x] Preserve failed local emulated attempt/no Python receipt and owned-container cleanup; no target pass inferred. [E293]
- [x] Freeze/implement/check/seal one native zero-DB compatibility job,23source/23sealed local checks,693-file seal/694-member archive and exact user commands. [E292][E293][E294]
- [x] Native C2B run/collect/download independently verified complete: job 21443102, all 128+128 cases and final proofs. Fourth compatibility allowance spent. [E319]
- [x] C3 final production seal/release: 619 files/620 members, 128 final-package local checks, exact readiness/controller/archive/preservation pass. Main commands E322 only. [E321][E322]
- [x] Main A2 acquisition/terminal collection/download and independent complete result verification: job21459623_0,52members/32guest+45host locks,102checkpoints, strict fresh replay byte parity; attribution informative, resource margin inconclusive. Main allowance spent. [E333]–[E335]
- [x] A3 remedy decision and consumer/identity/lifetime contract frozen before code;33 guarded offline cases pass with exact canonical/matrix/consumer outputs and756 prior files preserved. [E336]–[E338]
- [x] Separate producer/startup integration, original consumer/entry/failure tests and finite target-correctness capsule locally qualified:56+56 new/128+128 old/65+65 controls,774-file seal/775members,789 prior files preserved. [E339][E341]
- [x] E342 native correctness run/terminal collect/download and independent complete verification: job 21470341, all 368 exact cases, 33 members/28 locks, target/provenance/guards/build/seed/exit/SIF/timing pass. Allowance spent. [E345]–[E347]
- [x] Separate resource freeze/amendment, actual-path source+sealed qualification and independent release/command review complete: all 100+100 cases, 983 files/984 members, 1,956 prior files preserved. [E348]–[E351]
- [x] Verify reported login failure before reserve/scheduler and freeze/check/seal corrected protection context, preserving initial source/archive and all guards. 110+110 cases pass. [E354]–[E357]
- [x] Corrected resource allocation21542975_0 terminal FAILED1:0/16m35s independently verified; resource allowance spent. [E363]
- [x] Complete failed-raw archive/download/source/provenance/locks/timing/sampler/events/cleanup audit; close resource attempt failed/unqualified. Source preservation verifies; sampler lost and shutdown proof absent; recorded aggregate margin already fails. [E363]–[E365]
- [x] Offline startup-memory/sampling/shutdown review; pre-code lifecycle freeze/amendment, isolated correction,142source+142code-snapshot cases, strict replay and5,163prior-file preservation pass. Native paths/production build disabled; no memory change or native release. [E366]–[E370]
- [x] Source-backed memory remedy design, pre-code freeze/reference amendment, bounded exact adaptive prototype and94source+94snapshot checks; all56old A3 cases/main/native/lifecycle proofs and5,445prior files preserved. No native integration or peak claim. [E371]–[E375]
- [ ] Separately freeze production integration, release/source/retention guards, actual target formatter and exact-image correctness/CPU-budget design before further implementation. No native allowance or handoff released. [E374][E375]

**Critical dependency:** main/A3/lifecycle proofs preserved → exact adaptive component freeze/local consumer/allocation checks complete → prospective producer-integration and exact-target proof design. Old native proofs do not qualify the new type; memory margin remains held and every prior allowance stays spent. [E371]–[E375]

**A2/A3 gates:** capability/source/hook proof before restore → exact identity/zero-search/lifecycle/integrity → complete checkpoint/dispatch/page/row/role and overhead reconciliation → restoration/cleanup/locks/fresh trusted replay → new prespecified bracket evidence or unresolved closure. The unchanged28 GiB/no-limit-event resource gate is independent; neither an informative diagnostic nor a startup-only pass releases full B2f. [E266]

## 8. Framework selection policy

| Option | Intended role | When to decide | Current disposition |
| --- | --- | --- | --- |
| Existing controller / mini-swe-agent integration | Research loop, budgets, evidence, recovery | Reassess only against a demonstrated limitation | Retain as baseline |
| SMAC3 | Conventional bounded algorithm configuration | P4 | Candidate numerical baseline [S9] |
| Ax | Explicit outcome-constrained configuration | P4 | Alternative numerical baseline [S10] |
| BoTorch | Custom uncertainty/cost-aware acquisition | P5, if simpler strategies are inadequate | Optional research dependency [S12] |
| GEPA | Optimize instructions using scored execution feedback | P6, after reliable task evaluation | Conditional [S16] |
| Additional orchestrators or critic agents | Workflow changes | Only after a matched benchmark identifies need | Deferred; no measured justification from the latest pilot |

Select the smallest dependency that serves the declared comparison. Do not introduce multiple frameworks and then attribute an end-to-end gain to one of them without ablation.

## 9. Gate, experiment, and decision tracking

### Gate register

Use verdicts `not_assessed`, `pass`, `revise`, `closed_negative`, `closed_inconclusive`, or `deferred`. Append a new dated row when a gate is reconsidered; preserve the earlier verdict.

| Gate | Verdict | Date | Reviewer | Evidence | Resulting action |
| --- | --- | --- | --- | --- | --- |
| GA2.0 release/image compatibility | revise; native release held |2026-10-29 | Local source/build review; actual SIF inventory pending | E277–E282 | Strict local3.12.7 versus saved image-build3.12.15 mismatch; execute only the bounded image inventory, then explicit compatibility decision. No allocation or reference/gate substitution |
| GA2.0a image inventory | pass_inventory; reference mismatch retained |2026-10-29 | Independent existing-data verification | E283–E287 | Complete one invocation; only Python differs and actual matches A0; no full runtime/memory qualification |
| GA2.0b corrected target readiness | revise; native acquisition held |2026-10-29 | Source-backed compatibility review | E283,E288 | GO isolated exact-reference correction and3.12.15 readiness; preserve A1, no version wildcard/dependency upgrade/repeated inventory/new job |
| GC1 local reference correction | pass_local; native target pending |2026-10-29 | Local source/guard/integrity checks | E289,E291,E293 |128+128local checks; native exact reference and pre-restore gate implemented; original bytes preserved |
| GC2 native compatibility release | pass_exact_target_synthetic_correctness; all_four_allowances_spent |2026-10-30 | Data-only full 24-member/19-lock native return, all 128+128 outcomes and final proofs | E318–E319 | No rerun. Proceed only to completed C3 and one unchanged main A2 acquisition |
| GC3 main production release | pass_scoped_handoff; home_inode_recovery_prepared; main_unlaunched |2026-10-30 | Main C3 seal unchanged; current reported home deficit1,108files, state absent; preserving relocation helper passes21 local cases | E326–E330 | User E329 archive preservation/fresh guard → original unspent main submit. Actual relocation/quota pass remain pending |
| G0 | not_assessed | — | Unassigned | Roadmap baseline only | Resolve owners, budgets, entitlements, analysis |
| G0-P1 | pass, scoped diagnostic design only | 2026-10-23 | Codex implementation review | [Diagnostic protocol](../agent/experiments/execution-cost-attribution-v1/DESIGN.md) and local verification | Package ready for user execution; program-wide G0 remains open |
| G0-P2a | pass, scoped design/local checks only | 2026-10-23 | Codex implementation/local review | Frozen criteria/resources [E19], 31 local checks and sealed package [E17] | Ready for user Torch comparison [E20]; no native/G2/M1 claim; wider G0 remains open |
| G1 | not_assessed | — | Unassigned | Implemented protocol only; no new native timing | Await Torch cost-attribution results |
| G1 | pass, attribution only | 2026-10-23 | Codex local analysis review | Three complete blocks, sealed local replay/parity [E11][E12][E16] | Target owned prepared-policy state; retain explicit database-wait limitation; G2/M1 remain open |
| G2 | not_assessed | — | Unassigned | — | Await execution economics |
| P2a engineering | closed_negative | 2026-10-23 | Codex sealed local analysis | Dedicated reuse target passes; complete frozen gate fails on activation/control bounds [E21][E22][E25] | Preserve measured component; no adoption or rerun of this campaign |
| G2 | revise | 2026-10-23 | Codex result review | P2a reuse benefit and residual 1.54 ms admission; failed engineering protections [E21][E22] | Retain original as adopted baseline; P2b now implemented/checked; await its native/A/A/economics review; M1 remains open |
| P2b native/A/A/engineering | not_assessed | — | User collection/download; Codex local result review | Four successful blocks reported in status/Slurm output [E33]; raw evidence not yet verified | Collect/download and independently verify; assess native outputs, actual savings and A/A equivalence before G2 |
| P2b native/A/A/engineering | closed_inconclusive | 2026-10-23 | Codex fresh sealed verification | Native/output/stop/mechanism pass; all nonregression pass; A/A fails and relative activation lower saving bound 1.943% <2% [E34][E35][E38] | Frozen `measurement_inconclusive`; no adoption/rerun or threshold change |
| G2 | revise | 2026-10-23 | Codex result review | Verified P2b 0.202 ms activation saving, residual 1.281 ms admission and inconclusive qualification [E34][E35] | Retain original; scope at most one calibration or explicitly redirect to P3; M1 remains open |
| P2c calibration | not_assessed | — | Unassigned | Descriptive existing-data audit [E40]; no new prospective contract/budget | Scope at most one justified calibration or explicitly retain original and redirect |
| G0-P2c | pass, scoped design/local checks only | 2026-10-23 | Codex implementation/local review | Conditioned-scope contract, 44 local checks and sealed package [E41][E43] | Ready for user two-block campaign; no native equivalence/performance or generalization claim |
| P2c calibration | not_assessed | — | User Torch execution; Codex sealed result review | Package ready; zero native execution [E41] | Verify all controls and full cold charges in the new scope; operating-scope review mandatory |
| P2c calibration | pass, conditioned scope only | 2026-10-24 | Codex fresh sealed verification | All 80 cells/240 interval checks, raw/phase/charge/output identities pass [E46][E47][E50] | Calibration precision established only for conditioned shared data/fresh session; old P2b unchanged |
| P2c engineering | closed_negative | 2026-10-24 | Codex sealed result review | Exact verdict `revise_or_retain_original`; sole failure incremental activation lower saving bound 1.751% <2%; all 144 nonregression checks pass [E46][E48][E49] | No optimized-path adoption or additional campaign under this allowance |
| G2 | closed_negative; retain-original branch complete | 2026-10-24 | Codex result review | Verified calibrated gains do not meet the frozen practical target; restricted operating scope and native activation loss remain [E46][E47] | Retain original for bounded P3; M1 unestablished; wider adoption/lifecycle review deferred |
| G3 | not_assessed | — | Unassigned | P3a restricted coverage passes; no modeling/family decision yet [E54][E55] | Freeze and run the supported P3b comparison before choosing a family/intervention; independent confirmation remains separate |
| P3a coverage/identity | pass, restricted development task | 2026-10-24 | Codex saved-data audit | 620 files preserved; complete actual reached-grid outcomes/qualified features for static23/progress34; overlap/exposure/unknowns explicit [E53][E54][E55] | Freeze P3b model comparison; no immediate Torch acquisition; local aggregate-I/O caveat preserved in receipt |
| G0-P3b | pass, scoped offline design/local checks | 2026-10-24 | Codex implementation/local review | Frozen contract, 99 pinned inputs, fourteen synthetic checks, isolated dependencies; zero-fit preflight preserved [E60][E61][E67] | One campaign up to 360 fits; no new native/provider/Torch/protected access |
| P3b / NEXT-MODEL-01 | closed_negative, frozen procedures only | 2026-10-24 | Codex execution plus independent data-only replay | 340 fits, 0/20 non-continue selections, 560 admission assessments and 4,800 outer records replayed [E61][E64] | No adoption, compression, retuning or serving-speed claim |
| G3 | revise | 2026-10-24 | Codex result review; artifacts available for user review | All positive-proxy inner candidates fail recall; fixed ensemble diagnostic fails unfiltered recall [E62][E65] | Prepare one P3c risk-separated objective contract at fixed feature/action/capacity scope; final family unselected |
| P3c / NEXT-RISK-01 | not_assessed | — | New scoped design/resources to freeze | Proposed formulation hypothesis only; no fit or measurement [E62] | Freeze finite comparison before execution; no Torch command now |
| G4 | not_assessed | — | Unassigned | — | Await conventional baseline |
| G5 | not_assessed | — | Unassigned | — | Await acquisition comparison |
| G6 | not_assessed | — | Unassigned | — | Await workflow comparison |
| G7 | not_assessed | — | Unassigned | — | Await method comparison |
| G8 | not_assessed | — | Unassigned | — | No selected candidate |
| GB1 | deferred | 2026-10-22 | — | Main path remains open | Review only after a scope decision |
| G0-P3c | pass, scoped local design/checks | 2026-10-24 | Codex implementation review | Frozen risk-partition/benefit-leaf contract, sixteen tests/six synthetic fits, baseline preflight and 919 pins [E68][E69][E74] | One 100-fit local campaign; no new native/provider/Torch/protected access |
| P3c / NEXT-RISK-01 | closed_negative, finite formulation | 2026-10-24 | Codex run and independent data-only replay | Exactly 100 fits;4/20 cells select; no joint qualifier; all 980 assessments/4,800 cases and 248,851 leaf values replay [E69][E72] | No adoption, compression, extra fitting or retrospective routing |
| G3 | closed_negative, bounded tested procedures | 2026-10-24 | Codex result review | Safer fixed diagnostics still fail activation economics; calibrated joint gate fails [E70][E71][E73] | Retain original; defer stopping-family P4–P7; recommend B1a feasibility/design, no universal impossibility claim |
| GB1 | not_assessed, proposed B1a scope only | 2026-10-24 | Feasibility/design review pending | P3c closure motivates a new question, not proof of backend support or speed [E70] | Read-only fixed-index search-effort audit proposed; no implementation/measurement or index rebuild |
| G4 | deferred for current stopping branch | 2026-10-24 | Codex dependency review | G3 closes without a qualifying family [E69][E70] | Reassess numerical search only after a new supported-family/cost scope |
| B1a / NEXT-SCOPE-01 | pass, read-only audit complete | 2026-10-24 | Codex source/evidence review | 324 code/source hashes preserved;122 historical input and six saved output hashes match; API/input/timing/identity findings [E76][E77][E78] | No code/tests/experiments; prepare a separate B1b contract |
| GB1 | pass, scoped engine feasibility only | 2026-10-24 | Codex audit review | Search-time ef_search exists; current public API lacks effort action; historical levels are not a current compatible matrix [E76][E83] | Native 320/640 interface/frontier is a justified next comparison; no useful-policy/performance or dispatch permission claim |
| GB1b native/control/frontier (pre-run snapshot) | not_assessed; locally ready at v1.14 | 2026-10-24 | Historical preparation review | Sealed contract/interface and seventeen local checks [E84][E86] | Superseded for current status by completed native/control/frontier rows below |
| G0-B1b preparation (historical snapshot) | pass, scoped local readiness only | 2026-10-24 | Codex implementation/local verification | Frozen contract;17 source and17 sealed tests;146 package files /147 archive members verified; original324 code/source hashes preserved [E86][E88][E89] | Historical readiness only; the campaign is now complete and current native/control/frontier verdicts follow below |
| GB1b native conformance | pass, scoped to frozen current interface/index | 2026-10-25 | Codex fresh unchanged sealed replay | Settings/plans/isolation/errors/recovery, restored data and index/module hashes pass; outputs stable [E90][E93] | Technical feasibility established for measured levels; no policy/performance acceptance |
| GB1b aggregate | measurement_inconclusive; no supported context/regime | 2026-10-25 | Frozen gate replay | Activation A/A2/32, reuse32/32; all contexts fail recall reserve and wrapper overhead [E90][E92] | Complete the finite campaign, retain original, defer B1c; no calibration repeat for unchanged design |
| GB1b reuse frontier | no qualifying context, quality/control failures | 2026-10-25 | Passing-precision reuse result review |40.540% latency saving coexists with−0.800pp recall; forced640 reuse+0.206ms [E91][E95] | No context-only router fitting; scoped effort/interface review before a new contract |
| GB1-review / NEXT-EFFORT-REVIEW-01 | pass, source/evidence review complete; design GO only | 2026-10-25 | Codex read-only review |685 hashes preserved,17/34 startup SQL counts and existing matched timer categories; no code/tests/experiments [E96][E98][E100] | Prepare fixed480 native B1b2; no unchanged wrapper/router/calibration repeat |
| G0-B1b2 local readiness (v1.16 snapshot) | not_assessed | 2026-10-25 | Implementation/local reviewer pending | Prospective design only [E97] | Isolated implementation, mock checks and seal before native execution |
| G0-B1b2 local readiness | pass, scoped implementation/checks only | 2026-10-25 | Codex source/sealed local review |22 source/22 sealed tests, package/archive/shell integrity and691 old hashes pass [E103][E104][E106] | Ready for the user’s one-job quality-first native comparison; no native/performance/adoption claim [E105] |
| GB1b2 native/quality/warm controls/benefit (v1.17 preparation snapshot) | not_assessed | 2026-10-25 | Historical preparation review | No480 outcome existed at preparation [E97] | Superseded by completed rows below; frozen gate unchanged |
| GB1b2 native conformance | pass, frozen interface/index scope | 2026-10-25 | Fresh unchanged sealed replay |30 native/exact qualification searches, settings/HNSW plans/isolation/error recovery and preserved index/module pass [E107][E110] | Technical qualification only; no quality or performance acceptance |
| GB1b2 quality / aggregate | closed_negative_quality | 2026-10-25 | Frozen quality gate and independent saved-ID arithmetic | All absolute floors pass; reserve fails overall/votes32/votes108 by0.0833/0.1000/0.4000pp of lower-bound shortfall [E108][E109][E111] | Complete1,830-search negative closure; original retained; no fixed480 rescue or B1c |
| GB1b2 warm A/A / benefit | not_assessed, quality stop | 2026-10-25 | Saved-data count/file verification |0 temporal blocks; no retained timing/control observations; aa/comparison null [E109][E110] | No speed or A/A verdict; skipped phase is not unfinished work |
| GB2a / NEXT-PLAN-SCOPE-01 (v1.18 snapshot) | not_assessed, proposed read-only review | 2026-10-25 | Historical proposal | B1b2 closure motivated a scope audit [E108] | Superseded by completed scoped decision below |
| GB2a / NEXT-PLAN-SCOPE-01 | pass, scoped source feasibility only | 2026-10-25 | Codex source/saved-evidence audit | Exact-top10 mechanism distinct from exhaustive reference; options/input/identity matrix;349 source/907 immutable hashes pass [E115][E116][E118] | GO B2b design only; no router/rebuild or economy claim |
| G0-B2b / NEXT-EXACT-TOPK-01 (v1.19 snapshot) | not_assessed, design recommended | 2026-10-25 | Historical proposal | Source feasibility only [E115] | Superseded for readiness by local pass below; native outcomes still pending |
| G0-B2b original local readiness | historical local pass; insufficient native fixture | 2026-10-26 | Prior33/33 mocks retained; source-backed OID mismatch now found | Original native initial catalog fails before searches (reported) [E126][E127] | Original E122 remains historical; separate correction required, no v1 retry |
| GB2b original native preflight | failed_qualification, raw verified | 2026-10-26 |19 archive files/submission/job/scheduler/failure/cleanup/protected identities |0 searches; one reader closed/private DB stopped; no quality/A/A/economic result [E134][E135] | Preserve failed allowance; corrected execution only through separate E136 |
| G0-B2b catalog correction | pass, scoped local readiness; R2/R3 recovery pass | 2026-10-26 | Existing43 source/43 sealed checks plus verified failed original | Unchanged strict type fix, logging, guard and scientific seal [E129][E134] | E136 released for one user corrected allocation; actual native/quality/A/A/economics unassessed |
| GB2b corrected deadline stop | closed_inconclusive; verified incomplete_budget_exhausted | 2026-10-26 |30-member archive,26,247 attempts,12,208 retained, cleanup/protected identities verified [E142][E143] | Full final native/A/A/economic protocol incomplete; no formal speed/negative-economics verdict | Retain original; no rerun/extension; propose B2c source review [E144] |
| GB2b quality prefix | pass, scoped development prefix only | 2026-10-26 |30 qualification/600 references, independent scoring and unchanged sealed quality parity | Exact100% versus native99.0333%; reserve/floors pass in every context [E142] | Quality does not establish speed or independent success; no exact adoption |
| GB2b full A/A/economics/final integrity | not_assessed; unavailable complete evidence | 2026-10-26 | Missing final metadata/LOCK/charges/block1 boundary/successful final checks | Descriptive block0 exact56.11x slower,0/763 wins; no formal16-interval or adjusted-benefit gate [E144] | Decline more spending; never infer full gates from partial subset |

| GB2c / NEXT-ANN-ALTERNATIVES-01 | pass, scoped design/source feasibility only | 2026-10-26 | Codex source/saved-evidence/primary-doc audit | One >=108 partial-HNSW design, explicit public/native/cache caveats and finite costs [E147][E148] | B2d design frozen; no experiment/code change or native qualification |
| G0-B2d / NEXT-PARTIAL-ANN-01 | not_assessed, design frozen only | 2026-10-26 | Prospective design, not implementation |200 cases/16,802 max searches, preview/quality/A/A/full final-proof gates [E150] | Implement/check/seal before user commands; no compute now |

| G0-B2d local readiness | pass, local/synthetic/seal only | 2026-10-26 | Codex source+sealed correctness and preservation |55/55 source and sealed suites, archive/member/source hashes and strict final contract identity [E155][E156][E157] | Ready for one user Torch job; no native/index/quality/performance inference |
| G0-B2d quota compatibility | pass, separate local repair only | 2026-10-26 |61 source/61 sealed checks; original preflight failed before allocation | Shared original reservation, identical scientific config/code/gates [E161][E164] | Current E165 handoff supersedes original commands; no extra allocation |
| GB2d original native environment | failed_qualification, independently verified | 2026-10-26 |21 archive files;8 incomplete-lock hashes; FAILED1:0/4minutes;0 searches/readers [E171][E172] | Admin work_mem4096 versus reader16384; cleanup/protected hashes pass; no quality/performance result | Original allowance spent/preserved; separate correction E178 only |
| G0-B2d settings correction | pass, scoped local readiness only | 2026-10-26 |75 source/75 sealed checks,169-file seal and1,960 prior hashes | Explicit admin/reader roles, numeric memory/build proofs and failed-evidence prerequisites [E173][E176] | One separate corrected3h allocation proposed; all actual native gates pending [E178][E179] |
| GB2d corrected native/quality/final integrity | pass, scoped verified development | 2026-10-26 |37-member archive, full16,802 calls/5,700 plans/settings/data/graphs/module and final proof | Recall98.60%→99.85%,+1.25pp,[+.65,+1.90]pp95%; cleanup/protection pass [E184][E185] | Partial-index source/native feasibility and quality supported; no serving/independent acceptance |
| GB2d corrected A/A | fail,0/4 equivalence intervals | 2026-10-26 | Full sealed replay/200 vectors; both native/partial absolute/log controls fail | Partial identical replicas differ1.163ms/17.59%; schedule positions balance [E185][E188] | Gate prevents speed qualification; preserve margins/data and inspect mechanism |
| GB2d corrected economic endpoints | pass nominal endpoints; combined measurement_inconclusive | 2026-10-26 | Outer7.304522→6.030911ms, conservative upper gap−1.080889ms/ratio.876162; both blocks negative | Failed A/A defeats joint acceptance [E185][E186] | Retain original; proposed read-only B2e before any separate calibration; no adoption |
| GB2e proposal snapshot (historical) | not_assessed; proposed read-only scope | 2026-10-26 | Earlier proposal before user-requested B2e audit | Mechanism/missing-evidence GO/no-GO was pending [E186] | No code or measurement/allocation authorized by that proposal |
| GB2e / NEXT-PARTIAL-CONTROLS-01 | GO_to_separate_calibration_design; audit complete | 2026-10-26 | Equal captured plans/settings/counters; repetition transient and persistent partial session gap; physical attribution absent | Instrumented, qualification-first A/A design justified; no causal fix proven [E191][E192][E194] | B2f restoration/telemetry/contract freeze next; no implementation/allocation now |
| G0-B2f proposal snapshot (historical) | not_assessed; proposed design not frozen | 2026-10-26 | No code, tests or new native measurement | Derive finite instrumented physical-session calibration with unchanged margins and all charges [E191] | At most1 proposed3h4CPU32GiB/16,802 calls; zero authorized now; no blind repeat |
| F0-B2f / NEXT-PARTIAL-CALIBRATION-01 | pass_design_freeze_only | 2026-10-26 | Codex source/evidence/primary-doc design work; no tests or native calls | Exact graphs/margins,16,242 calls/two epochs/56 timing intervals, schedule/resource/telemetry/analysis pinned [E195][E196][E197] | User source inventory first; no implementation or native readiness inferred [E199] |
| L0/N0-B2f readiness snapshot (historical) | not_assessed; prerequisites pending | 2026-10-26 | No code or allocation | Source availability, exact whole-cluster restore and actual four-core/mandatory-telemetry capability unverified [E195] | E195§12 read-only output; then separately requested implementation/local checks and later native handoff |
| P0-B2f source inventory | pass_preliminary_user_reported_only | 2026-10-27 | User pasted requested read-only output; Codex compared reported scalars/hashes locally | Both cluster/control paths, no PID stop,3/3 graph matches; conservative home/scratch quota headroom [E201][E202] | Source prerequisite received; next separate implementation/local checks; full N0 clean-copy/resource/compute proof still pending [E203] |
| L0-B2f implementation readiness | pass_local_correctness_and_seal_only | 2026-10-27 | User authorized next implementation/check/seal steps; synthetic full acquisition/reconstruction and negative guards |78/78 source+78/78 sealed, lint/format/AST/shell/archive parity,2,255 old hashes unchanged [E206][E208] | User E207 upload/single submit; N0–N4 actual qualification/results pending; no speed/adoption verdict |
| Launch-B2f original acquisition | failed_pre_python_no_calibration | 2026-10-27 | Job21111616_0 terminal FAILED/2:0/4s; verified archive/log, no runtime files | Bare interpreter could not execute;0 native searches,1 spent allocation; N0–N4 not reached [E209] | Preserve seal/raw/binding/reservation; no automatic repeat or gate verdict |
| L0-B2f launch correction | pass_local_and_sealed_only | 2026-10-27 | Isolated absolute-interpreter/explicit-export correction, actual shell regression under synthetic restricted environment |88 source+88 sealed checks/static/archive parity and2,500 prior/failure pins pass [E211][E213] | Proposed one additional user-submitted job via E212; actual native compatibility unqualified |
| Restore-B2f launcher-corrected attempt | failed_zero_search_metadata_setup | 2026-10-27 |21129331_0 FAILED/1:0/8m34s;32-file archive/raw locks verify | Correct baseline identity file present in both retained cells but omitted from copied work;0 readers/searches; source/copy/cleanup evidence pass, final measurement proof false [E214] | Two spent allocations retained; no quality/A/A or native qualification |
| L0-B2f metadata correction (historical) | pass_local_and_sealed_only | 2026-10-27 | Pinned private sidecar copy/provenance, actual frozen constructor/binding/snapshot/query/reference/complete-fixture regression |101 source+101 sealed checks/static/archive parity,2,781 prior pins preserved [E216][E218] | That attempt is now spent/failed at startup; see E219; no further E217 submission |
| Identity-B2f third attempt | failed_zero_search_schema_guard | 2026-10-27 |21159802_0 FAILED1:0/10m44s;30 archive members verify | Wrong three-key versus two-key hash;2 readers/0 searches; source/cleanup preserved [E219] | Three spent attempts; no performance verdict |
| R1-B2f release audit/correction | pass_local_source_only | 2026-10-27 | Actual runtime-entry-point and full-size ID/vote schema/negative checks; pinned science preserved | Isolated source checked; no production seal or native qualification [E221] | R2 memory review open; R3 seal/handoff held |
| SQ0/SQ1 startup-only resource qualification | pass_local_source_and_seal_only; native_pending | 2026-10-27 | Frozen exact zero-search study, actual launcher/host/runtime startup/cleanup and independent memory replay fixtures | Local receipt E229; no full-size native memory observation | One additional1h4CPU32GiB user job via E230; no full calibration or automatic retry |
| SQ2/SQ3 startup-only resource return | startup_complete_resource_margin_inconclusive | 2026-10-28 | Job 21171789_0 complete; 46 members/raw/fresh replay pass, zero searches, ten readers, final integrity/cleanup | Peak 32 GiB at 32 GiB limit; +592 max/zero OOM; 4 GiB frozen margin shortfall [E232][E236] | Close spent allocation; memory/identity audit next; full calibration held |
| M0/M1 snapshot-memory compatibility | pass_scoped_audit_and_design_only | 2026-10-28 | Actual frozen consumer/lifetime/source review and prospective exact-byte streaming design | 116 files/137 references, source/identity/frame/binding/cap/local/native constraints and 3,456 preserved inputs [E239][E240][E242] | M2 isolated implementation/local qualification next; no tests/experiment/native release now |
| M2 identity-stream local readiness | pass_local_source_and_seal_only; native_pending | 2026-10-28 | Actual frozen constructor/acquisition/finalization/cleanup plus bounded byte/consumer/signal/restoration and trusted synthetic replay tests | 155 source+155 sealed; static/archive parity, immutable science/vendor/116 source pins and 3,468 prior inputs [E246][E247][E250][E251] | One user-executed zero-search M3 resource job via E249; full-size CPU/memory and calibration remain unqualified |
| M3 identity-stream startup/compatibility | pass_scoped_native_startup_identity | 2026-10-28 | Job21224521_0 complete0:0,48-member return/fresh sealed replay agree |247,286 rows/exact original identity/one invocation/restored binding, zero searches, ten readers/final cleanup [E252][E254][E257] | Native compatibility established only in this startup scope; no query/A/A/performance qualifier |
| M3 identity-stream resource | closed_inconclusive | 2026-10-28 | Complete memory trace712 frames; total kernel peak 32 GiB at 32 GiB limit,259 max/zero OOM deltas | 28 GiB/no-event gate unmet; lower runtime RSS11.323 GiB does not qualify total-charge margin [E256][E257] | Close spent job; read-only NEXT-STARTUP-MEMORY-02 next; no retry/new allocation/full calibration |
| W0–W2 working-set audit | pass_read_only_audit_GO_to_attribution_design_only | 2026-10-28 | Static actual-path source/consumer/lifetime/I/O and existing two-trace transaction/memory review | 246 source pins/3,961 preserved inputs; persistent final overlap, streamed verification, API/internal-fetch accounting distinction [E259][E260][E262][E263] | A0 bounded attribution/accounting design freeze next; no qualified single remedy or new job |
| Future SQL/I/O accounting release requirement | revise_before_any_new_handoff | 2026-10-28 | Trace.call excludes raw named-cursor fetch/transaction activity | 227 API calls are not all wire commands; 9,892 default fetches is conditional source model, not measured count [E263] | Retain old API semantics and freeze/add separate finite driver-command ledger; do not reinterpret old caps |
| A0 attribution design freeze | pass_design_freeze_only | 2026-10-28 | Original source/traces plus official CPython and pinned driver-source review; no execution |102 checkpoints, nine hook roles, separate API/driver/protocol/page/row ledgers,13,000 envelope and fixed resource/cleanup/decision caps [E265][E266][E267][E268] | A1 separately requested actual-path implementation/local readiness next; no runtime or native qualification [E269] |

### Experiment register

| ID | Phase | Question / hypothesis | Frozen protocol and identities | Status | Budget / actual use | Results and verification | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HIST-SEL-V1 | Historical | Can selective application produce a qualifying policy after one feedback round? | [E7], episode `20261022T192817Z-66ed81d6` | complete | Recorded $10 provider cap; actual $0.238334, 8 attempts, 3 allocations, 170,163 searches | [E1][E2][E3] | No combined qualifier; abstained; no confirmation |
| NEXT-COST-01 | P1 | Identify preparation/routing functions in the unchanged selective path | [Frozen design](../agent/experiments/execution-cost-attribution-v1/DESIGN.md), manifest `4c2f4756…0109c0`, credited `cons-bypass108` policy | complete; locally verified | Actual: 3 serial allocations, 83,763 searches, 21,600 primary + 6,480 diagnostic retained pairs; 0 provider calls/confirmation queries | [E11][E12][E13][E14][E15][E16]; campaign `20261023T044408Z.a08qpwdi`; [historical implementation snapshot](../agent/docs/verification/execution-cost-attribution-v1-implementation.json) | G1 pass; repeated profile/policy work and query normalization identified; no optimized-path or acceptance claim |
| NEXT-EXEC-01 | P2a | Does backend-owned prepared-policy state reduce real execution cost while preserving behavior? | [E19]; manifest `c4c00e12…9bca60c`; campaign `20261023T161756Z.8uq_covr`; unchanged policies | complete; locally verified; engineering gate not passed | Actual: 3 allocations, 143,163 searches, 12,420 eviction installs, 43,200 primary + 6,480 diagnostic retained pairs; provider/confirmation 0 | [E21][E22][E23][E24][E25][E26]; full native/output/stop/mechanism checks pass | Candidate reuse 5.171% faster; activation/control limits fail; retain original adopted baseline and frozen P2a experimental reference |
| NEXT-ADMIT-01 | P2b | Can immutable semantic profile-identity reuse reduce admission cost with adequate activation/control precision? | [E29]; manifest `7c82194d…f29350d`; campaign `20261023T193304Z.a2mfz4a0`; unchanged policies | complete; independently verified; measurement inconclusive | Actual: 4 allocations, 370,884 searches, 33,120 eviction installs; provider/confirmation 0 | [E34][E35][E36][E37][E38][E39]; descriptive order audit [E40] | 2.102% activation point gain vs P2a, 4.054% reuse vs original; A/A and relative activation criterion prevent qualification; retain original |
| NEXT-CAL-01 | P2c | Can conditioned shared-data, fresh-session crossovers establish the unchanged equivalence bounds? | [E43]; manifest `6b6f2169…7ae6fc0`; campaign `20261024T025706Z.c8557262`; unchanged execution/gate bytes | complete; independently verified; calibration pass, engineering not qualified | Actual: 2 serial allocations, 592,242 searches including 96,000 conditioning, 192,000 retained pairs, 48,000 warmups/evictions each; provider/confirmation 0 | [E46][E47][E48][E49][E50][E51]; all controls and identities pass | 1.884% activation vs P2a, 4.711% reuse vs original; 1.751% lower incremental activation bound fails; retain original and close finite P2 |
| NEXT-INFO-01 | P3a | Which actual stopping outcomes and qualified decision-time features support a learnability comparison? | Frozen data-only contract [E52], 620 input/source hashes [E53], original timing target and separate source cost identities | complete; restricted coverage gate passes | Existing-data audit only; zero fits/searches/DB/provider/Torch; successful primary pass 43 s/1.24 GiB RSS; cumulative local-I/O cap not attested [E55] | [E53][E54][E55][E56][E57][E58][E59] | Static23/progress34 reached-grid modeling supported; current Light19/off-grid/new-policy timing need separate evidence if pursued |
| NEXT-MODEL-01 | P3b | Can a flexible predictor exploit qualified early-stop information that the bounded shallow policy misses? | Frozen matched-information/eight-checkpoint nested-group contract [E60], SHA `d50ccf6a…f1b5c7`; run `p3b-20261024-local-v1` | complete; locally replayed; closed negative for frozen procedures | 340/360 estimator fits, 235.661 s, 0.997 GiB peak RSS, 0.783 GiB metered reads, one thread; zero native/DB/provider/Torch/confirmation | [E61][E62][E63][E64][E65][E66][E67]; all 200 vectors previously exposed | All twenty calibrated selections continue; fixed ensemble diagnostic fails recall; G3 revise, original retained |
| NEXT-RISK-01 | P3c | Can separating loss risk from savings yield a joint qualifier at fixed information/action/capacity? | Frozen contract [E68], SHA `92928bbc…ae99ae`; run `p3c-20261024-local-v1`; exact P3b folds/baselines | complete; independently replayed; closed negative | 100/100 fits, 102.377 s, 0.993 GiB RSS,0.839 GiB metered reads; sixteen checks/six synthetic fits; zero native/DB/provider/Torch/confirmation | [E69][E70][E71][E72][E73][E74][E75]; all 200 vectors exposed | Four ensemble cells admit gates, no joint outer qualifier; close formulation allowance and propose B1a |
| NEXT-SCOPE-01 | B1a | Does fixed-index query-dependent search effort offer a supported affordable interface worth a finite comparison? | Read-only source/evidence audit and metadata/hash inventory [E76][E77][E78] | complete; scoped feasibility pass | Zero code changes/tests/fits/simulations/native/DB/provider/Torch/protected access;324 code/source files unchanged | Effort GUC exists; three cheap contexts; current API/timer constraints and historical index/runtime mismatch explicit [E83] | Prepare B1b interface and actual current 320/640 frontier, not a router fit |
| NEXT-EFFORT-01 | B1b | Can current-index native320/640 preserve isolation and yield a useful quality/cost frontier after full interface costs? | Frozen [E84], manifest35a09d4e…b69c1f; campaign20261025T014743Z.p_kspq5v | complete; verified; aggregate measurement_inconclusive | Actual2 jobs/139,272 searches, zero providers/fits/confirmation;200 exposed vectors | Native pass; reuse A/A32/32, activation2/32; reuse40.540% faster but−0.800pp recall; forced640 reuse+0.206ms; alias-only recovery [E90][E93] | Retain original, defer B1c; read-only scope revision before new measurement |
| NEXT-EFFORT-REVIEW-01 | B1-review | Does a revised effort/interface question justify another comparison after the320/640 failures? | Read-only source/data/primary-documentation review [E96][E98][E99] | complete; design-only GO | Zero code edits/tests/fits/native/DB/provider/Torch/protected access |685 existing files preserved; eager two-reader admission and extra validation identified, no function-level cost attribution [E100] | One prospective global480 native comparison; B1c/calibration repeat remain NO-GO |
| NEXT-EFFORT-MID-01 | B1b2 | Can constant480 preserve640-relative quality and save useful warm native query cost? | Frozen E97; manifestb7ad5be7…c34bc1; campaign20261025T172357Z.ybpfkkki | complete, verified, closed_negative_quality | Actual1 job/1,830 searches/10 reader admissions;0 timing blocks/providers/fits/protected/confirmation | Native pass; reserve fails overall and both filters; all raw/sealed parity and888 immutable hashes pass [E107][E108][E110] | Retain original; B1c deferred; proposed B2a; no speed claim or repeat |
| NEXT-PLAN-SCOPE-01 | B2a | Does another plan/filter/index mechanism justify one distinct finite comparison? | Source/saved-plan/identity/input-cost audit [E115][E116][E117] | complete; scoped design GO | Zero code/tests/fits/simulations/experiments/DB/native/provider/Torch/protected access;349 source/907 immutable files preserved | Distinct exact top10 endpoint source-feasible; exhaustive truth timings and selected-index metadata insufficient for economics/full catalog [E118] | Prepare B2b design; no router or new physical/native branch yet |
| NEXT-EXACT-TOPK-01 | B2b | Can fixed exact10 beat native640 with qualified quality/control/full warm costs on existing graph? | Frozen E120; manifest0124abaa…6f55e; archive01c6d272…7b65d | implemented/locally checked/sealed; awaiting user Torch | One allocation/max40,230 searches;200 existing vectors/600 cases;14 admissions/5 live; observer SQL<=40,000; zero providers/fits/protected/confirmation |33 source/33 sealed mock checks and912 prior hashes pass; native/quality/A/A/economics unassessed [E122][E125] | Upload/submit once E124; preserve failures/unknown dispatch; no router/activation/adoption claim |
| NEXT-EXACT-TOPK-01 catalog-fix | B2b corrected | Same frozen exact10/native640 question; strict catalog type repair | E128/E129, manifest6b2bb0f4…c6f842; job20949301_0 | verified incomplete_budget_exhausted; closed_inconclusive | Actual26,247 attempts/12,208 retained; both finite allowances consumed | Prefix quality pass; complete A/A/economic/final integrity unavailable [E142][E143][E144] | Retain original; no repeat; B2c completed below |
| NEXT-ANN-ALTERNATIVES-01 | B2c | Which distinct indexed/filter-aware ANN mechanism merits one finite design? | Read-only audit, source/input inventory and primary sources [E147][E148][E149] | complete_scoped_design_go | Zero code/tests/experiments/bootstrap/fits/index builds/native/DB/Torch/provider/protected access;349 source/1,364 prior hashes preserved | Select one >=108 partial cosine HNSW; explicit public/C binding/cache/isolation/cost limits [E151] | B2d design only; no native or performance claim |
| NEXT-PARTIAL-ANN-01 design snapshot (historical) | B2d | Can one >=108 partial HNSW beat full-graph native640 under scoped quality/controls/full costs? | Frozen partial-ann.v1 design [E150]; no package/seal yet | design_frozen_only, not implemented/run | Proposed1 allocation/3h/16,802 max searches;200 exposed cases; actual0 searches/allocations | Native/public compatibility, build, preview, quality/A/A/economics/final proof unassessed | Isolated local implementation/checks/preservation/seal next; no user command yet |
| NEXT-PARTIAL-ANN-01 original local readiness (historical) | B2d.0 | Is the two-copy single-index study ready for a bounded native run? | Frozen E150/E153; final manifest f11159e1b66d9e9cb0259bec45e136eac9bff7a322233a9ac00a4153267c09a4 [E157] | implemented/locally checked/sealed; ready for user | Actual55 source/55 sealed mock checks;0 native/index builds/allocations/provider/fits/protected queries | Full and early-stop replay, metadata/plan/timer/ownership/gates/transport/preservation pass; native unassessed [E155][E156][E159] | Original handoff superseded by E165 after quota preflight failure; all native gates remain binding |
| NEXT-PARTIAL-ANN-01 quota compatibility | B2d.0 | Can the site resource guard parse captured quota without loosening capacity or adding entitlement? | Same scientific config/controller; manifest c52355cde583edb684bd250f6e5286fbb29097ef9d6ffd9dc5aac5ca40980845 | repaired/locally checked/sealed; ready for user |61 source/61 sealed mocks;0 native/index builds/allocations | Captured table, strict malformed/insufficient cases, scientific byte parity and1,733 prior hashes pass [E161][E163][E164] | Current E165 upload/once-only handoff; original reservation shared |
| NEXT-PARTIAL-ANN-01 original native attempt | B2d.1 | Does the initial environment qualify? | Manifest c52355cd…080845; campaign reviews-partial-ann-v1-20261027T000432Z.9haq3pyt | failed_environment_verified |1 spent allocation;0 searches/readers | Sole mismatch admin work_mem4096 versus reader16384; cleanup/protection verified [E171][E172] | Preserve spent allowance; correction separately prepared [E173] |
| NEXT-PARTIAL-ANN-01 settings correction | B2d | Does partial640 qualify against preserved full native640? | Frozen E150/E173; manifestc77efca4…89b4; job21048213_0 | complete_verified_measurement_inconclusive |1 consumed corrected allocation/16,802 attempts/200 exposed cases | Native/quality/final pass; nominal endpoints pass;0/4 A/A intervals pass [E184][E185][E186] | Retain original; propose read-only B2e; no rerun/adoption |
| NEXT-PARTIAL-CONTROLS-01 | B2e | What explains identical-replica timing asymmetry, and is calibration justified? | Read-only scope E193; completed B2d raw/seal/verdict fixed | complete_read_only_design_GO |0 new searches/tests/bootstrap/fits/allocations/provider/protected values | Matching work identities; transient plus persistent session gap; missing PID/CPU/cache evidence;2,235 hashes preserved [E191][E192][E194] | GO to B2f instrumented design, root cause unresolved; no commands |
| NEXT-PARTIAL-CALIBRATION-01 proposal (historical) | B2f | Can a fixed-graph instrumented regime qualify A/A and distinguish backend/order/warmth effects? | Prospective requirements only E191; not frozen/implemented | proposed_design_not_frozen | Proposed≤1 allocation/3h4CPU32GiB/16,802 total calls; actual0, no entitlement now | Exact restoration, instrumentation, schedule, charges and analysis pending | Freeze first; separate implementation/readiness and native authorization later; retain original |
| NEXT-PARTIAL-CALIBRATION-01 freeze snapshot (historical) | B2f.0–1 | Can a fixed instrumented regime qualify physical-session A/A without hiding state bias? | Frozen partial-calibration.v1 design/contract/explicit order E195–E198; no package yet | design_frozen_only_prerequisites_pending | Proposed1 job/3h4CPU32GiB/16,242 searches; actual0 code/tests/searches/allocations |56 all-required timing intervals; exact graphs/margins and all charges/stops pinned;2,241 prior files preserved [E199] | Read-only user source inventory; separate implementation/local readiness and native handoff later; B2d unchanged |
| NEXT-PARTIAL-CALIBRATION-01 source prerequisite | B2f pre-implementation | Are retained exact graphs still reported accessible with adequate quota headroom? | Frozen E195–E198 unchanged; user E201 output | preliminary_user_reported_source_pass |0 experiments/allocations/new code; user read-only file checks only |3/3 reported graph matches; paths/control files/no PID stop/space output;2,249 prior hashes preserved [E202][E203] | Next separately requested implementation/local correctness/seal; full native gates unassessed; no more user commands now |
| NEXT-PARTIAL-CALIBRATION-01 implementation | B2f.2/L0 | Can the fixed prospective regime be implemented with auditable ownership/observation/count/analysis guards? | Frozen E195–E198 plus exact completed B2d dependencies; new isolated package | implementation_checked_sealed_native_pending |78 source+78 sealed synthetic checks; actual0 native searches/allocations/provider/protected values | Full mocked acquisition/reconstruction, negative guards, archive parity and2,255 prior files preserved [E206][E208] | User E207 upload and single3h4CPU32GiB submit; all native gates and56-interval verdict pending |
| NEXT-PARTIAL-CALIBRATION-01 launch correction | B2f.L0-fix | Can the pre-Python launch defect be repaired without changing the scientific regime or rewriting the spent attempt? | Verified original6-file failure/archive/seal; new infrastructure revision partial-calibration.v1.launch-fix | launch_correction_checked_sealed_native_pending |88 source+88 sealed synthetic checks; actual original1 failed4s allocation/0 native searches, proposed1 additional job | Absolute interpreter/explicit step export; old package/raw/binding/reservation guards;2,500 prior/failure pins preserved [E209][E211] | E212 handoff explicitly requests one new bounded job; all native gates pending |
| NEXT-PARTIAL-CALIBRATION-01 metadata correction | B2f.L0-metadata | Can correct backend identity metadata be retained without changing scientific identity or bypassing validation? | Verified32-file second failure/seal/source/copy/cleanup plus preserved original attempt | failed_zero_search_schema_guard_verified |101 historical source/sealed checks; third attempt21159802_0 spent/0 searches | Pin/copy identity sidecar; actual frozen backend full integration;2,781 prior files preserved [E214][E216] | E217 consumed; preserve it. New release held pending R2/R3 [E219][E221] |
| NEXT-PARTIAL-CALIBRATION-01 release audit | B2f.R0–R3 | Do startup and resource evidence justify release? | Scientific contract and all earlier failed evidence preserved | release_held_resource_margin_inconclusive | Three failed calibration attempts plus separate successful zero-search resource job | Startup acquisition now verifies; total-charge margin does not [E232][E233] | Read-only memory/identity audit and prospective design before any new job |
| NEXT-STARTUP-RESOURCE-01 | B2f.R2 | Can unchanged startup/admission complete with resource margin and zero searches? | Frozen E227/startup-resource.v1 | complete_startup_resource_margin_inconclusive | One user 1h/4CPU/32GiB job complete; Codex zero native jobs | 46 raw members, fresh sealed replay, trace/source/cleanup and 3,442 preserved inputs [E233][E234][E236] | Allocation closed/spent; next read-only memory compatibility audit, no retry/full calibration |
| NEXT-STARTUP-MEMORY-01 | B2f.R2/M0–M3 | Can identity encoding reduce transient memory while preserving exact snapshot semantics? | Frozen E240/E241; startup-resource.stream.v1 seal [E251] and job 21224521_0 | closed_inconclusive_resource; scoped_native_identity_pass | User: one1h4CPU32GiB/11m55s job, zero searches. Codex: existing-data verification only | Exact identity/startup/cleanup pass; observed runtime RSS15.030→11.323 GiB, job peak 32 GiB/+259 max;48 raw members/3,947 pins verify [E252][E253][E256] | Job spent; no repeat. Next read-only working-set audit; full calibration held |
| NEXT-STARTUP-MEMORY-02 | B2f.R2/W0–W2 | Which loading/retained-representation/verification working sets can safely be reduced under the same gate? | Two existing returns, 246 pinned sources and official driver/Arrow/OS references | complete_read_only_audit_GO_to_attribution_design_only | Zero code/tests/fits/searches/new measurements/allocations | Persistent snapshot/final overlap, streamed checks, 333.775s transaction brackets and API/internal-command gap; allocation/file causality unresolved [E259][E260][E262][E263] | No-go blind single remedy; next A0 design-only freeze, full B2f held |
| NEXT-STARTUP-ATTRIBUTION-01 | B2f.R2/A0 | Can bounded lifetime/I/O and explicit driver accounting distinguish a safe remedy family? | startup-attribution.v1 design/catalogs frozen before code [E265][E266] | complete_design_freeze_only; A1 now locally complete [E272] | A0:0 code/tests/probes/experiments/jobs. Proposed later max1h4CPU32GiB/zero searches, no entitlement released |102 required/max128 checkpoints; exact fetch model,13,000 command/request cap, bounded overhead and non-tautological informative/unresolved gate;3,974 pins unchanged [E269] | A1 actual-path local readiness on separate request; no handoff until qualified; full B2f held |
| NEXT-STARTUP-ATTRIBUTION-01 | A1 local readiness | Does bounded observation preserve original control flow/accounting/cleanup? | Isolated startup-attribution.v1 harness and local sealed artifact [E273][E275] | complete_local_readiness_only; A2_unreleased |155 baseline +100source/100sealed local checks; zero native experiments/jobs/searches |102 checkpoints, real private methods/synthetic transport, full generator/signal/cleanup and negative replay checks;3,987 old inputs preserved | Separate A2 handoff review; actual image capability then native acquisition/replay, or stop; full B2f held |
| NEXT-STARTUP-ATTRIBUTION-01 | A2 release review / image inventory | Does actual frozen image match the locally tested reference? | Exact build-config/header audit; separate source-only inventory capsule [E279][E280] | release_held_image_compatibility; inventory_ready_user_pending |0 allocations/searches; one inventory invocation max15CPU/30wall seconds/2GiB virtual space, no SQL/data mounts |29source/29sealed checks,99 exact references,108-file seal;5,318 old inputs unchanged | User E282 inventory/download → explicit compatibility decision; A2 acquisition/A3 pending, full B2f held |
| NEXT-STARTUP-ATTRIBUTION-01 | A2.0a postrun / compatibility decision | Does the actual image match the frozen target and what correction is justified? | Existing four-file image inventory and immutable parent/source references [E285][E286] | inventory_verified; GO_reference_correction; acquisition_HELD | One direct5.6275s inventory/0Slurm allocations/0SQL/search/snapshot; no new execution in analysis | Only Python differs: actual3.12.15 matches A0;9 exact hook/parser/library checks, four literal callbacks;5,519 prior files unchanged | C0–C3 isolated strict target-reference/3.12.15 readiness/release review; no new commands/job now [E288] |
| NEXT-STARTUP-ATTRIBUTION-01 | C0/C1 implementation; C2 native readiness | Does the corrected source preserve strict binding/control flow under the actual target? | Corrected main source,128normal/128guarded local checks; bounded native compatibility capsule [E291][E292] | local_correction_complete; native_compatibility_ready; main_A2_HELD | One proposed native correctness job max15m/2CPU/4GiB/0SQL/DB/server/search; no job submitted this turn |23source/23sealed capsule checks,693file/694member archive,5,531 preserved inputs; local emulated no-receipt failure retained | User E294 compatibility run/collect/download → independent target review → C3 main seal/release; full B2f held |
| NEXT-STARTUP-ATTRIBUTION-01 | C2 failed/native correction prepared | Does the complete packaged offline runtime preserve target correctness within unchanged bounds? | Verified13-file failed return, retained diagnostics, exact constructor regression and corrected sealed capsule [E296][E297][E299] | original_failed; local_correction_complete; native_pending; main_HELD | Original1allocation spent; distinct1×15m2CPU4GiB/0realSQL/search, same300s source/sealed; no new job by Codex |33source/33sealed/128+128main local checks; ten seed proofs each integration; original main unchanged | User E300 → verified native source/sealed proof → C3 seal/release; no original reservation reuse |
| NEXT-STARTUP-ATTRIBUTION-01 | C2 prepared fixtures qualification | Can exact target correctness complete with redundant test preparation removed? | Verified third failed return and synchronous fixture stages [E308][E309] | prepared_native_failed; all_three_spent; main_HELD | User job 21382454: 1 allocation, source timeout, 0 real SQL/search; 119 source cases passed | 16 files/11 locks/provenance/dependencies/final host integrity pass; complete source/child/sealed proof absent | E307 spent; no resubmission. C2B budget design/review next |
| NEXT-STARTUP-ATTRIBUTION-01 | C2B native qualification / C3 main release | Does the complete exact-target implementation qualify for unchanged main acquisition? | Native 128+128/full final proof, 24-member/19-lock audit and exact production seal [E319][E321] | compatibility_complete_spent; C3_pass; main_ready_unlaunched | One completed 21m correctness allowance; main has one unspent 1h4CPU32GiB zero-search allowance | 619-file/620-member main seal, 128 final local cases, all 68 recipes and 5,883 prior files intact | User E322 main A2 → independent full return verification → A2 closure/A3; no compatibility retry |





| NEXT-A3-NATIVE-RELEASE-01 | Offline release review | Can the integrated candidate be released natively without relaxing limits? | Frozen source/trace review, separate correction and independent full replay [E429]–[E434] | complete_offline; qualification_handoff_HOLD |0 native jobs/searches;1,280 local checks/60 CPU samples |195,784 prior files and every original test/strict guard/limit preserved | Concrete native authority/group/live-admission and bounded-return design; new handoff requires distinct authorization/unspent allowance [E435] |

| NEXT-A3-AUTHORITY-01 | Offline authority/ownership backend | Can fresh authority and complete descendant cleanup be verified without native spending? | Frozen validator/guardian/gate/shared ledger and exact local kernel checks [E436]–[E440] | complete_offline; native_handoff_HOLD | 642 fresh local checks,0 native jobs/searches | All old tests, limits, full replay proof and200,143 prior files preserved | Freeze adapter/authority handoff and practical site-attestation acquisition before implementation; no grant issued [E441][E442] |
| NEXT-A3-INTEGRATED-01 | Offline native integration/package | Can exact complete replay and ownership be sealed without native spending? | Frozen integration,1,656 checks/60 CPU and complete preservation [E443]–[E450] | offline_complete; readonly_site_check_ready |0 Torch jobs/searches | All old tests/references/limits preserved; no grant/reuse | User uploads and runs read-only site check; review before fresh distinct authorization [E451]–[E453] |
| NEXT-A3-SITE-01 | Exact site compatibility and account readiness | Can the actual installed Slurm prefix pass a bounded reviewed policy? | Frozen UID1001 prefix layer,722 checks and full preservation [E454]–[E459] | offline_complete; readonly_handoff_ready |0 new native allocations/searches | All old tests/science/limits preserved | User uploads replacement and returns read-only site/account output before fresh authorization [E460][E461] |
| NEXT-A3-AUTHORIZE-01 | Distinct native qualification proposal | Do current site/project/partition facts support one new finite qualification? | User-return review and exact conditional commands [E462]–[E465] | review_complete_authorization_pending |0 new allocations/searches | Original tests/source/strict verification/limits and all spent guards unchanged | User may explicitly authorize one1h4physicalCPU32GiB zero-search/no-retry allocation; assistant does not launch |
| NEXT-A3-STATUS-21756110 | Read-only status and terminal collection | What happened within the single newly authorized qualification? | User-submitted job21756110 and immutable controller [E466]–[E469] | submitted_outcome_pending |1 committed allowance; observed running/terminal state unknown | All tests/limits/zero-search and no-retry guards unchanged | Obtain status; collect after independent terminal accounting; verify full proof before any native verdict |
| NEXT-A3-RAW-21756110 | Terminal failure collection and offline review | Which allocated-node path/role triggered the preflight hold? | User status and source error location [E470][E471] | raw_collection_pending |21756110 spent;0 retries/new allocations | Original packet/tests/science/verification/limits remain unchanged | Collect exact raw/traceback; independently review and freeze a justified correction before implementation [E472][E473] |
| NEXT-A3-CONFIG-21756110 | Verify read-only sealed client compatibility and dependencies | Can exact deployed clients safely consume the pinned snapshot? | Locally verified source/snapshot harness [E502]–[E506] | user_login_metadata_command_ready_native_gate_closed |0new allocations; all spent closed | Original tests/source/strict verification/limits preserved | Capture the required library from the observed RPATH root, then review its transitive metadata and runtime gates, then separately freeze an exact native read-only replay; no qualification release |

For each new experiment, record model/settings where applicable, policy/profile/runtime/evidence hashes, independent group count, arm schedule, primary endpoints, acquisition rule, unknown-outcome policy, selection rule, and declared final-data access. Link full manifests rather than expanding this table indefinitely.


### Decision log

| ID | Date | Basis | Decision / interpretation | Revisit trigger |
| --- | --- | --- | --- | --- |
| D001 | 2026-10-22 | Routed-native and candidate activation losses [E1] | Promote execution-cost diagnosis before broad new policy search | Qualified full-path costs or evidence of a realizable earlier-stopping family |
| D002 | 2026-10-22 | `cons-bypass108` reuse and recall results [E1] | Keep selective application as a leading direction; retain seed credit | Independent confirmation or a new matched comparison |
| D003 | 2026-10-22 | Oracle saves latency in both regimes [E1] | Preserve earlier-stop investigation; do not claim overhead makes stopping impossible | Feature-sufficiency and actual-stop evidence |
| D004 | 2026-10-22 | Explicit feedback-response abstention [E1][E3] | Preserve completion behavior; deprioritize more turns/framework migration | Repeated matched evidence of workflow/completion failures |
| D005 | 2026-10-22 | Episode closed; zero confirmation allocations [E1] | Do not resume the episode; reconcile unconsumed entitlement before another study | New prospectively declared campaign |
| D006 | 2026-10-23 | Source call-path audit and scoped P1 design | Implement provider-free attribution with unprofiled primary controls and a separate diagnostic pass; preserve policies, runtime, index, and all confirmation entitlements | Verified Torch results and G1 review |
| D007 | 2026-10-23 | Independently verified P1 and frozen source [E11][E12] | Close P1/G1; target repeated pre-cache policy work and profile identity through privately owned prepared state | Qualified P2 comparison or evidence that the ownership boundary cannot be preserved |
| D008 | 2026-10-23 | Candidate reuse improves in every block; activation fails; bypass still costs time [E15] | Retain selective stopping as a development direction, keep the earlier abstention and all acceptance boundaries, and consider normalization separately if residual cost warrants it | G2 actual economics and later independent confirmation |
| D009 | 2026-10-23 | Large Python database-wait frames and shared vector formatting [E12][E14] | Do not label server/transport or common statement work as the identified removable gap; use a focused diagnostic only if residual cost blocks G2 | Boundary-specific residual measurements |
| D010 | 2026-10-23 | Existing prepared-object interface plus local P2a correctness checks [E17][E19] | Use one lazy session-owned handle, preserving first preparation inside the original backend timer and avoiding preparation on bypass; defer fingerprint memoization/normalization; freeze one three-block comparison | Returned native proofs, full-path costs and engineering gate |
| D011 | 2026-10-23 | P2a exact parity/mechanism success and 5.171% candidate reuse gain; frozen complete gate fails [E21][E22] | Close the campaign without adoption; retain original baseline and P2a experimental reference; preserve every failed bound and distinguish uncertainty from proven slowdown | Separately declared qualified comparison meeting all criteria |
| D012 | 2026-10-23 | Admission remains 1.539285 ms with four profile fingerprints/eight encodings; activation/control precision unresolved [E22][E26] | Prioritize scoping admission/profile-identity reuse and A/A/per-filter precision ahead of normalization or broader search; no new budget/run assigned | Reviewable mechanism, cold costs, qualification, control design and finite resource contract |
| D013 | 2026-10-23 | User requests P2b implementation/comparison; frozen P2a profiles and precision review [E27][E30] | Use one owned per-admission fingerprint; preserve full validation/cold charges and exact P2a query body; freeze original/P2a/P2b A/B, Williams balance, strict A/A and engineering gates under one four-block allowance | Native correctness/call counts, A/A equivalence and actual incremental/combined costs |
| D014 | 2026-10-23 | Verified P2b activation/reuse benefit, exact outputs/stops, all nonregression pass, failed A/A and 1.943% relative lower saving bound [E34][E35] | Close P2b without adoption; preserve modest mechanism signal and every failed criterion; original remains adopted baseline | New prospectively qualified evidence, not a P2b rerun or relaxed margin |
| D015 | 2026-10-23 | Descriptive order associations in all A/A activation strata, remaining 1.28 ms admission and heavier profile-copy path [E35][E39][E40] | Calibration before another optimization; scope at most one finite conditioning/order comparison, or explicitly retain original and redirect to P3; no causal subtraction or outlier deletion | Justified contract/budget, calibrated equivalence and measured residual economics |
| D016 | 2026-10-23 | User requests P2c implementation/package; verified order audit and preserved P2b gate [E40][E41] | Freeze one conditioned-index/query fresh-session protocol, full admission/first-use charges, ten A/A cells, adjacent crossovers and two-block finite allowance; keep old execution/gate bytes | Native calibration plus scope/lifecycle review; old P2b verdict unchanged |
| D017 | 2026-10-24 | P2c raw replay verifies; all 240 A/A and 144 nonregression checks pass; incremental activation lower saving bound 1.751% <2% [E46][E47] | Close finite P2 without optimized-path qualification; retain original, preserve modest calibrated benefits and old gates; no retry/retuning/automatic P2d; M1 unestablished | A separately justified future scope/contract, not repeated qualification under this allowance |
| D018 | 2026-10-24 | Calibration resolves scoped precision, but the oracle opportunity remains unproven from deployable information [E47] | Make P3a existing-data outcome/feature/exposure/identity coverage the next dependency; gate model comparison or targeted acquisition on that audit | Frozen coverage contract and explicit proceed/acquire/close decision; protected evaluation entitlements stay bound |
| D019 | 2026-10-24 | P3a verifies every reached static23/progress34 grid stop and all required features; 200 exposed vectors, known invalid/unreachable states [E53][E54][E55] | Pass restricted coverage gate and prepare P3b grouped modeling contract without first reacquiring data; final G3 and M1/M2/M3 remain open | Matched-information, first-stop modeling evidence and finite budget |
| D020 | 2026-10-24 | Current Light19 has 1,074/4,695 actual stop cells; old binary differs; filtered Light19 states alias despite 359 differing targets [E54][E58] | Do not synthesize missing interventions or transfer costs; use qualified actual predicate inputs in richer-profile comparison; keep Light19/off-grid scope conditional | Separately justified profile/action-specific acquisition or a supported narrowing; no automatic Torch job |
| D021 | 2026-10-24 | User requests P3b; contract frozen before 340 fits; source/group/model/first-stop replay passes [E60][E61][E64] | Close NEXT-MODEL-01 negatively for its finite procedures: every calibrated selection continues; no deployment, larger-model or universal-ceiling claim | New prospectively justified formulation or independent development evidence |
| D022 | 2026-10-24 | All 225 positive-proxy candidates fail recall; all 305 recall-passing candidates have nonpositive proxies; fixed ensembles fail unfiltered recall [E62][E65] | G3 revise; propose one P3c risk-separated objective comparison at fixed information/action/capacity. Do not rescue with post-hoc subgroup routing or retune the completed run | Separately frozen finite contract, then qualifying signal or explicit diversity/B1 closure branch; no automatic Torch acquisition |
| D023 | 2026-10-24 | User authorizes all P3c local work; contract frozen before 100 fits; sixteen local checks, group/leaf/outcome replay passes [E68][E69][E72] | Complete one risk-only partition / separate fitting-leaf benefit comparison at unchanged model capacity; preserve all prior evidence and exact P3b folds | Saved joint result, not additional hyperparameter search |
| D024 | 2026-10-24 | Four cells select gates but no joint outer qualifier; fixed diagnostics reduce losses 11/10→1/1 while activation proxies stay negative [E70][E73] | Close P3c allowance and bounded G3 negatively; original retained; no compression/adoption, extra fitting or universal-ceiling claim | New justified scope/entitlement contract, not a P3c rerun |
| D025 | 2026-10-24 | Complete grid labels, persistent activation economics and calibration/fallback instability [E70] | Recommend B1a read-only fixed-index search-effort feasibility/design before further collection; fresh development diversity remains conditional, protected samples remain bound | Verify backend controls, cheap qualified inputs and native cost boundary; explicit GB1 contract before experiment |
| D026 | 2026-10-24 | B1a verifies query-time ef_search in pinned engine, but no effort field/action in current API; native autocommit excludes some setup [E76][E77] | Pass GB1 scoped feasibility only; propose a versioned experimental native-effort interface with explicit origin/effective settings and charged selector/session costs | Native qualification, original 640 controls and actual end-to-end economics |
| D027 | 2026-10-24 | Old multi-effort index 6076 differs in bytes from current 90f4; size-sweep 320 matches graph but not current runtime scope; group inventories differ [E79][E80][E81][E82] | Do not splice historical effort results or640 stopping prefixes into current training/cost labels; no fresh-data claim from ID nonoverlap | Compatible actual current-index/module multi-effort evidence and entitlement reconciliation |
| D028 | 2026-10-24 | Only three validated pre-query contexts in 600 cases; no qualified within-filter vector-difficulty predictor [E76][E83] | B1b native 320/640 frontier before B1c's at-most-eight context maps; compare quality to unchanged640, not each chosen level's native; no framework migration | Frozen controls/quality/resource contract and supported frontier; protected samples unchanged |
| D029 | 2026-10-24 | B1b requires real native-effort interventions, while source320 differs from the historical640 study reference [E84] | Freeze two immutable reader bindings and a separate unwrapped source comparator; retain original640 quality/reference and exact truth | Verify actual settings/default metadata, plans, isolation and identity on the current physical graph |
| D030 | 2026-10-24 | Both-reader initialization is real work; reuse cannot prove fresh-session economics [E84] | Primary full outer timers charge all admission/binding/selector work; evaluate activation and reuse separately, with64 A/A interval checks and fixed .10ms/2% overhead/benefit margins | Reuse-only frontier support permits only a scoped future design; no activation/deployment implication |
| D031 | 2026-10-24 | Isolated implementation,17 local tests and sealed package integrity pass; no new native run [E86][E88][E89] | Mark B1b preparation complete and native/control/frontier pending; hand exact upload/submit/status/collect/download commands to the user | One two-allocation139,272-search campaign; no automatic resubmission, router fitting or protected-query use |
| D032 | 2026-10-25 | Remote reporter used `/results` mount basename; downloaded archive and scientific results intact [E93] | Recover with exact archive/submission/job/package identity proof and one copied campaign-label reconciliation, then unchanged strict parity; preserve all raw/sealed files | Four recovery tests and fresh full replay; no generic parity relaxation or rerun |
| D033 | 2026-10-25 | Native conformance passes; reuse A/A32/32, activation2/32; all contexts fail quality and wrapper overhead [E90][E92] | Complete B1b with frozen aggregate measurement_inconclusive and no qualifying context; retain original and defer B1c | No model selection, adoption or milestone claim; prior verdicts remain unchanged |
| D034 | 2026-10-25 | Deterministic320 recall losses and passing-precision reuse overhead failure remain even if activation calibration improves [E91][E95] | No unchanged-design calibration repeat; propose read-only effort/interface revision review before another bounded contract | No interpolated intermediate labels, extra effort/block, feature acquisition or protected-data entitlement |
| D035 | 2026-10-25 | Source and matched raw timer review show eager second-reader startup, extra query validation/ownership work and remaining common native scaffolding [E96][E98] | Complete B1-review; avoid bundling a new validator/direct path/pool library with the next effort question; preserve required guards | Separate attribution/qualification if such a runtime change is later justified |
| D036 | 2026-10-25 |320 fails reserve,640 is reference, intermediate current-index outcome unknown [E96] | Freeze one global480 midpoint probe against640 using ordinary fixed readers; quality-first and warm-only, one allocation/max59,430 searches; no interpolation, context rescue or effort ladder [E97] | Implementation/local seal and fresh native/quality/A/A/benefit gates before any conclusion; adoption/confirmation separate |
| D037 | 2026-10-25 | Fixed480 B1b2 implementation,22 source/22 sealed checks,151 archive members and691 old hashes verified [E103][E104][E106] | Mark local readiness pass; hand off one quality-first Torch job using new mid_control.py and MFA-safe helper [E105] | Actual native conformance/quality/A/A/benefit and full raw replay before any scoped conclusion; no automatic resubmission, effort expansion or protected access |
| D038 | 2026-10-25 | B1b2 archive/raw/unchanged sealed replay pass; native conformance passes and all mean floors pass, but relative recall lower bounds fail overall/votes32/votes108 [E107][E108][E110] | Close the finite fixed480 probe `closed_negative_quality` after1,830 searches; original retained; no timing or A/A assessed | No post-hoc subset rescue, margin relaxation, extra block,560/600 ladder or independent-confirmation claim |
| D039 | 2026-10-25 |480 recovers37 true neighbors versus320 but still misses11 versus640 across nine vectors; neither quality pass nor480 cost frontier established [E111] | Recommend read-only B2a plan/filter/index mechanism and identity/input-cost audit before another finite contract | GB2a not assessed; no implementation/measurement budget, router fit, new graph/module equivalence or protected entitlement inferred |
| D040 | 2026-10-25 | B2a traces no-LIMIT exhaustive truth versus native LIMIT; existing native SQL supports a separately forced exact plan, with catalog/plan/economics gaps explicit [E115][E116] | Complete GB2a scoped source feasibility; recommend one exact-top10 versus640 B2b design on unchanged graph/module | No measured savings, router fitting or implementation/spending permission;349 source/907 immutable hashes preserved [E118] |
| D041 | 2026-10-25 | Partial/partitioned targets exceed current backend contract; ACORN-1 query expansion still assumes a different unpruned construction, and offline selectivity is not free [E115] | Defer physical/native/selector expansion; freeze the smallest distinct actual execution question first | Future plan/semantic/A/A/full-cost evidence and source identities required; preserve old gates and protected entitlements |
| D042 | 2026-10-25 | User authorizes B2b preparation; actual exact10 costs unknown and multiple predicate reports could be examined | Freeze one same-graph/module exact10/native640 contract with strict semantic/quality gates,16 A/A intervals and eight adjusted economic endpoints;40,230 attempts/one allocation [E120] | No index/JIT/parallel/validator/transport/router change; bootstrap development scope and prepared-plan conditioning explicit |
| D043 | 2026-10-25 |33 source/33 sealed checks,153-file package/154-member archive, four transport-stage mocks and912 prior hashes pass [E122][E123][E125] | Mark G0-B2b local readiness pass; hand off new xt_control.py commands for one user job [E124] | Native/catalog/semantic/quality/A/A/economics remain unassessed; preserve failed/unknown binding and raw results; no automatic repeat |
| D044 | 2026-10-26 | User reports original job20941363 failed initial catalog with0 searches/empty operations/protected unchanged, elapsed6m17s [E126] | Record failed qualification and consumed allowance; no recall, speed or A/A verdict | Original raw/accounting/cleanup remain unverified; collect/download before recovery [E131] |
| D045 | 2026-10-26 | PG17.11 source and regression show to_jsonb(oid) text rejected by original integer fixture/guard [E127][S41][S42] | Freeze separate strict text-ID correction; retain SQL/physical identity/all gates; log rejected raw catalog/field differences |43 source/43 sealed checks are local readiness only;1,095 original hashes preserved [E128][E129][E130] |
| D046 | 2026-10-26 | Corrected155-file seal prepared; original failed raw still missing | Hold corrected run instructions until original checksum/submission/job/zero-search/cleanup/protected/scheduler evidence is reviewed; new controller rejects missing/changed prerequisites | Original reservation retained; prospective one additional bounded allocation only, no automatic repeat or scientific conclusion [E128][E131][E132] |
| D047 | 2026-10-26 |19-member original archive verified;0 searches; FAILED1:0; one reader closed/private DB stopped; captured protected hashes identical across19 groups/1,621 entries [E134] | Complete failed qualification review, retain original failure and consumed allowance; no quality/A/A/economic verdict | Raw rejected catalog absent; reported6m17s remains user-status only; no reconstructed catalog waiver [E137] |
| D048 | 2026-10-26 | Failed-raw prerequisites match and unchanged corrected seal remains valid;1,307 old inputs/artifacts preserved [E135] | Complete R2/R3, release new E136 user commands for one prospective correction allocation; previous43/43 checks remain applicable | Actual corrected catalog/semantic/quality/A/A/cost gates and verified return still required; no automatic retry or adoption |
| D049 | 2026-10-26 | Corrected job20949301 reports6,600s deadline failure in block1,26,247 budgeted attempts/12,208 retained; protected unchanged/providers0 reported [E138] | Record incomplete budget stop; initial qualification/quality pass is only control-flow inference pending raw verification | No full A/A/speed result or quality-negative closure; both allowances consumed [E140] |
| D050 | 2026-10-26 | Complete two-block matrix and final integrity audits were not reached | Collect/download existing raw, audit prefix quality/coverage/phase costs before any prospective resource/design change | Do not extend spent deadline, replay subset through complete analyzer, resume partial block or resubmit E136; retain gates [E139][E140] |
| D051 | 2026-10-26 |30-member corrected archive, prefix qualification/600 quality references, all recorded search/timer/plan prefix and cleanup/protected identities verify [E142][E143] | Promote prefix quality from source inference to pass; exact100%, native99.0333%; keep full catalog/final integrity/controls unassessed | Missing full-protocol evidence is not reconstructed or waived; exposed development scope only |
| D052 | 2026-10-26 | Complete block0 exact535.980ms versus native9.552ms (56.11x);0/763 case-block wins; exact93.66% observed warm wall, plans19.76s [E144] | Close finite campaign incomplete_budget_exhausted; retain original; do not extend or repeat this fixed exact path | Practical no-more-spending decision, not retrospective sealed closed_negative_economics or a universal exact-search ceiling |
| D053 | 2026-10-26 | Lower effort family fails quality; exact path passes quality but has no observed cost opportunity | Recommend planned B2c read-only indexed/filter-aware ANN compatibility/cost triage; choose at most one justified future design | No model/router/index/module work or new compute now; future design requires real compatibility, unchanged gates, cost-grounded caps and prospective futility stage [E144][S26][S35][S36] |
| D054 | 2026-10-26 | B2c alternatives/cost/source review complete [E147][E148] | Select one >=108 partial cosine HNSW for prospective B2d; defer additional indexes, partitions, shadow tables and ACORN | No new performance result or public partial-target qualification |
| D055 | 2026-10-26 | Public inspector rejects partial; C binding has no explicit predicate rejection and does not force planner [E147] | Separate experimental adapter, two private copies and strict actual-context/fresh/cached-plan guards | Unchanged module must qualify; no production validator weakening or module repair |
| D056 | 2026-10-26 | Prior exact consumes93.66% warm time; saved builds have material cost [E144][E148] | Freeze24-vector cost preview and one16,802-search/3h proposal with stage/SQL/storage limits | Preview can stop spending only; no positive economic acceptance |
| D057 | 2026-10-26 | New scope is one fixed >=108 context, same200 exposed vectors [E150] | Preserve .95/−.0025 quality and±.10ms/±log1.02 A/A bounds; retain conservative99.375% economic upper quantile and final integrity | Four unique A/A intervals; no all-context/activation/router/independent claim |
| D058 | 2026-10-26 |349 source/1,364 prior immutable hashes preserved; read-only review complete [E149][E151] | Next work is B2d isolated implementation/local checks/seal; no user command yet | No experiment/bootstrap/fit/native/DB/Torch/provider/protected use in B2c |
| D059 | 2026-10-26 | User authorizes next local B2d implementation/check/seal step | Implement only new experiment; freeze prospective resource/accounting addendum and preserve design/old code/raw | No Torch/native experiment launched [E153][E154] |
| D060 | 2026-10-26 |55 source/55 sealed mocks and archive/161-file source identity pass [E156][E157] | G0 local readiness passes; release exact new handoff | Mocks do not qualify module/partial target, actual recall, A/A or speed |
| D061 | 2026-10-26 | Final metadata review removes unused inherited exact-contract fields; strict regression passes | Preserve internal review seal, issue clean B2d-only final contract | Design/gates/entitlements unchanged; no prior upload/submission/allowance [E155][E159] |
| D062 | 2026-10-26 | Source/data integrity and program limits retained | One3h4CPU32GiB user job, quota/native preflight and202/802/16,802 finite branches | Preserve failed/unknown dispatch; no automatic retry, graph/module repair, router or adoption [E153][E158] |
| D063 | 2026-10-26 | Quota-fix native job21043219_0 fails before searches at first admin environment guard [E167] | Mark allowance consumed; preserve source/seals/binding/reservation and collect raw | No performance result, no automatic retry; exact settings/cleanup/protected identities await verification [E168][E169][E170] |
| D064 | 2026-10-26 | Failed B2d archive proves admin work_mem4096 versus reader16384; cleanup/protection pass [E171][E172] | Preserve failed original; freeze role-specific guard, conservative reader memory bound and numeric build-unit correction | Same policies/scientific margins; no settings tuning or original allowance reuse [E173] |
| D065 | 2026-10-26 |75 source/75 sealed,169-file archive/scope/preservation proofs pass [E176][E177] | Release separately named one-job corrected handoff E178 | Actual partial build/reader conformance/quality/A/A/economics/final proof pending; no native experiment by Codex [E179] |
| D066 | 2026-10-26 | Corrected job21048213_0 reports full completion; controller uses old prefix and reporter expects new [E180][E182] | Preserve successful measurement and labels; separate exact-campaign raw collection8 checks, no scientific/code/seal change | No new allocation or performance verdict; current E181 before trusted raw/reconciliation/replay [E183] |
| D067 | 2026-10-26 |37-member/full raw verifies; exact-name exception proved and two fresh sealed replays agree [E184][E187][E189] | Accept integrity/feasibility/quality evidence, preserve labels/raw/seal | No acquired remote performance JSON; do not claim remote/local economic parity |
| D068 | 2026-10-26 | Recall+1.25pp and apparent latency−17.44%/nominal endpoint pass coexist with0/4 A/A interval passes [E185] | Close B2d measurement_inconclusive, retain original and spent allowances | No faster-replica selection, A/A subtraction, new seeds/blocks, speed/adoption/amortization claim [E186] |
| D069 | 2026-10-26 | Partial A/A gap1.163ms/17.59%,93.67% in SQL, persists across blocks while label positions balance [E188] | Propose read-only B2e session/cache/plan/source mechanism audit before separately frozen calibration | Cause unresolved; no new native run, fitting or gate changes authorized [E190] |
| D070 | 2026-10-26 | B2e matches800 a/b plan packets per cell/settings/counters; progressive repetitions and partial-b faster193/200 query averages [E191][E192] | Complete audit; no supported code/plan-mode correction or causal root cause; preserve B2d verdict | New physical backend/CPU/cache/observer evidence, no selection of retained2/faster replica |
| D071 | 2026-10-26 | Fixed label/session/creation-order and conditioner/position aliases; missing PID/placement attribution [E191] | GB2e GO to one instrumented, bounded, qualification-first A/A calibration design | B2f fixed-graph/telemetry feasibility, prospective contract/charges/margins before separately requested code and run; no allocation now [E194] |
| D072 | 2026-10-26 | B2e missing identities/transients and persistent partial gap justify a fixed instrumented regime [E191] | Freeze B2f physical-session/CPU/order/observer/retained-stability design with exact graph/margin preservation and16,242-call bound | No causal component fix or speed result; all56 timing intervals mandatory, no unused-budget extension [E195][E198] |
| D073 | 2026-10-26 | Saved retained-directory receipt does not prove current stopped-cluster availability | Require read-only user path/three-hash/space inventory before executable fixed-graph preparation | Missing/changed graph stops this scope, no rebuild, source startup or allocation; actual CPU/telemetry gates remain native [E195][E199] |
| D074 | 2026-10-27 | Requested user inventory reports exact retained paths and3/3 graph hashes, positive quota headroom, no PID-file stop [E201] | Clear preliminary source prerequisite; retain frozen design/contract/order and exact graphs | User transcript is not independent remote/full clean-cluster verification; N0 resource/copy/core/telemetry gates remain pending [E202][E203] |
| D075 | 2026-10-27 | No new scientific identity or measurement change required by inventory | Next separate implementation/local readiness; no further user Torch command now | No implicit code/experiment authorization from pasted inventory; preserve original/B2d inconclusive and all margins [E203] |

| D076 | 2026-10-27 | Third zero-search startup failure is a guaranteed schema mismatch; prior real-backend tests skipped runtime startup | Correct separate identity guards and exercise actual runtime entry-point success/failure/cleanup; preserve all three spent attempts | No data drift, ANN quality failure or performance verdict inferred [E219][E220] |
| D077 | 2026-10-27 | MaxRSS31.9807GiB under32GiB and incomplete accounting attribution/full-run memory proof | Hold production builds/handoff; obtain read-only config and document R2 resource feasibility before R3 release review | No fourth job, silent memory increase, frozen-loader rewrite or automatic retry [E220][E221] |

| D078 | 2026-10-27 | Supplied controller config uses cgroup accounting without reported cache exclusion; version/limits/components remain unknown | Complete config request; retain resource hold and GO only to separate startup-only resource qualification design |0 code/tests/experiments/new allocations; no more login commands now; no cache subtraction, OOM inference or cap change [E223][E224][E225] |

| D079 | 2026-10-27 | User authorizes startup-only resource freeze/implementation/checks/handoff with0 ANN/exact searches | Freeze separate startup-resource.v1 before code; preserve held calibration and spent attempts; enforce zero at methods/operations/SQL | No production/scientific/graph/margin change or native experiment by Codex [E227][E228] |
| D080 | 2026-10-27 | Source/sealed local fixtures, actual shell/host/runtime control flow and trusted memory replay pass | Release one additional one-hour, four-CPU, 32 GiB resource-only handoff; actual resource gate remains pending | No bootstrap/timing/quality/adoption verdict, silent cap change or automatic calibration/retry [E229][E230] |
| D081 | 2026-10-28 | Startup resource job 21171789_0 completed; checksum/46 raw members/fresh sealed reconstruction agree | Native startup and ten-admission/cleanup scope verified with zero searches | No search-workload/A/A/quality/speed entitlement [E232][E234][E237] |
| D082 | 2026-10-28 | Job peak reaches 32 GiB limit; +592 max events in snapshot_load, zero OOM; frozen 4 GiB allowances unmet | Close resource job as margin-inconclusive, keep full calibration held; next read-only memory/identity audit | No cache subtraction, retrospective margin/cap change, inferred savings or automatic job [E232][E236] |
| D083 | 2026-10-28 | Consumer/lifetime audit confirms one shared snapshot and real original-row/identity consumers | Preserve rows, numeric values, matrix, maps, cursor and constructor; target transient identity encoding first | No ten-copy remedy, float32 reconstruction or measured allocation attribution [E239][E243][E244] |
| D084 | 2026-10-28 | Existing canonical serializer supports per-row bytes with exact fields/rows framing; SHA updates preserve concatenated bytes | Freeze scoped first remedy, binding/restoration, buffers/counts/equivalence and unchanged later resource gates before code | Design feasibility only; implementation/local/native gates unassessed, full calibration held [E240][E241][E242] |
| D085 | 2026-10-28 | Exact original-canonical streaming and actual constructor/acquisition/cleanup/restoration regressions pass 155 source and 155 sealed checks | Mark M2 complete for local readiness; retain every initial local failure/correction, old seal/raw and native limitations | 346 manifest files/347 archive members, unchanged science/helper/vendor/source pins, 3,468 preserved inputs; no full-size native saving claim [E246][E247][E250][E251] |
| D086 | 2026-10-28 | Separate startup-resource.stream.v1 package and once-only commands prepared under the frozen M1/native resource contract | Next is one user-executed M3 zero-search qualification; collect terminal raw and independently decide resource margin before any M4 | One hour/four CPUs/32 GiB, original 2+2 GiB margins/no max/OOM deltas, no retry/cache subtraction/cap increase; full calibration held [E249][E247] |
| D087 | 2026-10-28 | Job21224521_0 complete;48-member raw/fresh replay and exact original snapshot identity/restoration/lifecycle/cleanup verify | Complete scoped native identity/startup gate, preserving zero-search scope and all scientific limitations | Original data/graphs/module/policies unchanged; no query-quality/A/A/search-speed/adoption claim [E252][E253][E257] |
| D088 | 2026-10-28 | Total-job peak remains 32 GiB/+259 max despite lower observed runtime RSS; pressure predates hashing and reappears near finalization | Close M3 resource allowance inconclusive; next read-only working-set audit before any separate remedy design | No event-label overattribution at boundaries, cache subtraction, cap/margin change, automatic retry or full-calibration release [E256][E258] |
| D089 | 2026-10-28 | Existing source/trace confirms one snapshot persists through reader close and overlaps streamed final checks; four verification transaction brackets total 333.775s | Complete W0–W2 audit, preserve per-allocation/per-file and boundary uncertainty | 246 source pins/3,961 inputs preserved; no implementation/test/measurement or native job [E259][E260][E262] |
| D090 | 2026-10-28 | Raw cursor/transaction delegation bypasses Trace.call for internal commands; pinned default source implies many fetches | Clarify old SQL counts as API-level; require a separately bounded driver-command ledger before any new handoff | No claim of measured 9,892 wire commands, silent cap change or retroactive resource-verdict change [E263] |
| D091 | 2026-10-28 | Cursor-only/batch-only/close-only options do not establish a remedy for retained/final overlap and unchanged gate | GO only to bounded zero-search lifetime/I/O attribution design freeze; no unqualified next remedy run | A0 must preserve exact semantics/scans/margins, bound instrumentation/commands, and define interpretability/futility; no allocation now [E259][E260] |
| D092 | 2026-10-28 | Original-code local monitoring plus explicit original cursor-close/harness seams can describe required bracket checkpoints | Freeze A0 mechanism,102 checkpoints, bounded metadata and exact teardown before implementation | CPython/tool/frame/private-driver/source behavior remains untested; A1 actual-path proof required, no AST/source rewrite or fallback [E265][E267][E269] |
| D093 | 2026-10-28 | API counters exclude internal fetch/transaction/prepared activity; fixed four-pass/default100 shape permits finite prospective ledger | Freeze original API caps plus separate actual dispatch/protocol/page/row accounting; sum family caps12,336 within13,000 including64 cleanup reserve | Exact9,892 successful fetches required but not claimed observed; no double count, extra SQL/scans or retroactive cap reinterpretation [E266][E268] |
| D094 | 2026-10-28 | New observations must distinguish previously unresolved mechanism brackets; resource margin and scientific qualification remain separate | Freeze informative/unresolved/capability-invalid outcomes and all local/native release gates; next A1 only on separate request |256 MiB is descriptive triage only; no guarantee of savings, new allocation/retry, cache subtraction or full calibration [E265][E269] |

| D095 |2026-10-29 | Actual original-code monitoring/private-driver/entry/signal/cleanup and independent replay/archive checks pass locally | Complete A1 local readiness with155 baseline and100source/100sealed checks; preserve local fixture failure/correction and all old inputs | No native/scientific/resource qualification from synthetic transport or metadata counts [E271][E274][E275] |
| D096 |2026-10-29 | Guarded local seal is complete; actual image/cgroup/private-library capability remains unmeasured | Next only separate A2 release/handoff review and pre-restore capability gate | No job/commands now; no automatic substitute/retry/cap/margin change; full B2f held [E271][E272] |
| D097 |2026-10-29 | A1 reference3.12.7 differs from saved image-build3.12.15; actual SIF inventory pending | Hold native dispatch; release only one bounded source-only image inventory and require separate compatibility review | No reference substitution/upgrade/retry/job; preserve A0/A1 and both resource verdicts; full B2f held [E277][E279][E282] |
| D098 |2026-10-29 | Verified actual3.12.15 matches A0; A1 Mac3.12.7 is the sole reference difference; all hooks/parser/libraries match | GO isolated exact image-reference correction and target-runtime readiness; HOLD acquisition until corrected artifact/release review | Preserve historical references/gates, no patch waiver/upgrade/repeat; one inventory spent,0allocations; no commands now [E283][E286][E288] |
| D099 |2026-10-29 | Main correction128normal/128guarded local pass; local emulated target failed/no Python receipt | Prepare only one bounded native zero-DB compatibility job before main release;23source/23sealed capsule checks and exact handoff pass | No main A2/B2f, target pass, scientific/resource/dependency change or automatic retry;5,531 prior inputs preserved [E289][E293][E294] |
| D100 |2026-10-29 | C2 failed return verifies; scratch/constructor proof identifies missing metadata and repeated fixture preparation | Isolated dependency/fixture/failure-reporting correction;33+33capsule and128+128main local checks; one distinct bounded native qualification | Original allowance spent, source/graph/module/data/policies/margins unchanged; no blind cap increase, retry, main A2 or B2f [E295]–[E300] |
| D101 |2026-10-29 | Second C2 verifies96passes/zero errors and a fixture-preparation deadline; metadata/reference/final integrity pass | Freeze/implement one-build-per-suite prepared fixtures and equivalent hardlink reseals; remove a locally caught async-watchdog finalization stall;43+43/128+128 complete local checks | One distinct native qualification only; all cases/caps/main source/margins preserved. Both old allowances spent; no main A2/B2f or partial-prefix promotion [E301]–[E307] |
| D102 |2026-10-29 | Third C2 verifies 119 passes/no errors, 143.703s of fixture stages and another 300s source timeout; final host integrity passes, final child/source/sealed proof absent | Hold further handoffs; recommend C2B prospective compatibility time-budget revision using native evidence, keeping all 128+128 cases and main code/limits | All three allowances spent; no new code/capsule/test/experiment/job, no retrospective pass or main A2/B2f release. Twenty-minute option is planning only [E308]–[E310] |
| D103 |2026-10-30 | Independent C2B trace/source review finds the 20 m option omits explicit preflight/termination;420 s per suite remains prospective sizing | Freeze 21 m / 2 CPU / 4 GiB accounting; isolated time/cleanup/proof correction, 62+62 capsule/128+128 main local checks; one distinct E315 handoff | All three old allowances spent; native qualification remains pending; original main code/limits/strict 128+128 / zero-search intact. No job/main A2/B2f launch [E311]–[E317] |
| D104 |2026-10-30 | Native C2B job 21443102 independently verifies all 128+128 cases and final proofs; fourth compatibility allowance complete/spent | Freeze/build/review unchanged main production seal; 619 files/620 members, 128 final local cases and strict native readiness; release E322 only | All 68 main recipes/code/limits unchanged, 5,883 prior files intact. No main launch or B2f release; actual resource/coverage/overhead/cleanup/replay gates remain [E318]–[E323] |
| D105 |2026-10-30 | User reports login /home conservative-capacity rejection after full 7,297-file verification; source confirms no reservation/binding/Slurm reached | Record unspent main allowance and prepare E325 read-only actual quota/statvfs/state/inode report; file-quota pressure is supported by prior 420-file margin but current deficit is unknown | No source/seal/gate/threshold/cleanup/compute changes. Preserve all old evidence and reservations; no main submit until capacity/state proof [E324][E325] |
| D106 |2026-10-30 | Read-only report confirms home conservative file headroom8,892/10,000; main binding/reservation absent, bytes/filesystem pass | Freeze/implement/test a reversible helper moving only three failed C2 capsule trees to archive with full hash/metadata proof and original-path symlinks;21 local cases; exact E329 continuation | No main code/science/limit/guard change, result/reservation edits or remote action here. All old allowances spent, main still unspent; fresh archive/home checks required [E326]–[E330] |
| D107 |2026-10-30 | Mac helper upload fails before SCP: OpenSSH control socket plus temporary suffix exceeds macOS path limit | Use short private /private/tmp socket directories in both external Mac transfer helpers; offline long-TMPDIR success/failure/cleanup checks pass | Relocation payload, main source/seal/archive/tests/limits unchanged; actual socket binding is blocked by the local execution sandbox; no SSH or native action [E331] |
| D108 |2026-10-30 | Native helper reports all three relocations complete; final guard has 9,676/10,000 free files, 324 short | One idempotent recheck of archive preservation and fresh headroom, with physical home inode count; original main submit only after helper success | Main unlaunched/unspent; quota delay unproven; no further relocation, spent-job retry or threshold/source change [E332] |
| D109 |2026-10-30 | Main A2 job21459623_0 completes0:0/14m16s; all52members,32guest/45host locks and strict fresh replay verify | Close A2 informative:7.478GiB row-decode RSS growth and new matrix/pool/file-role brackets; move to A3 remedy contract review | Peak32GiB and780max events keep resource margin inconclusive; no OOM kills, causal savings, native retry or full B2f release; all main/compatibility allowances spent [E333]–[E335] |
| D110 |2026-10-30 | Verified A2 decode bracket and frozen-consumer audit support one exact-value storage remedy; plain arrays alone lose JSON integer type semantics | Freeze binary64+integer-tag/per-row canonical/sample contract before code;33 guarded local original-consumer checks pass,756 prior files preserved | A3 decision complete; internal type/mutation scope explicit, no native producer/target/memory qualification or Torch command; all old allowances spent, full B2f held [E336]–[E338] |
| D111 |2026-10-30 | A3 producer/startup and receipt-gated native context qualify locally:56+56 new,128+128 unchanged and65+65 control cases, full artifact/789-file preservation pass | Release one distinct25m2CPU4GiB zero-DB correctness capsule,775archive members; scratch extraction and unique durable reservation | All old allowances spent. Exact native target remains pending; failure spends new allowance/no retry. No resource/memory/B2f release [E339]–[E343] |
| D112 |2026-10-31 | Native job 21470341 independently passes all 128+128 original and 56+56 A3 cases on exact CPython 3.12.15; 33 returned members/28 locks, guards, timing and integrity verify | Qualify scoped native correctness; export authentic proof packet and GO to separate resource protocol/harness integration and local release review | All allowances spent; original code/seals/limits intact. No native memory/savings qualification, new resource command or full B2f release [E345]–[E347] |
| D113 |2026-10-31 | Actual frozen-reader fixture identifies exact-list metadata boundary; pre-code bounded adapter preserves canonical bytes, immutable state and pre-connection restoration. All 100+100 checks, complete seal/1956-file preservation and offline handoff audit pass | Release one distinct unlaunched 1h/4CPU/32GiB zero-search startup-memory allocation E352 with strict target/source/proof and unchanged conservative margin | Main A2 and five qualified A3 files/128+128/56+56 proofs remain unchanged; all old allowances spent. Native memory, workload, savings/performance and full B2f remain unqualified [E348]–[E353] |
| D114 |2026-10-31 | Initial resource protection fails before reserve/sbatch; original sibling lookup needs actual home-package context. All 110+110 corrected checks, original case IDs/guards and 3,035 prior-file hashes pass | Release corrected E358 continuation using verified main home context and separate transfer/extraction paths, same unspent reservation/prefix/one-allocation limit | Original main/A3/native proofs and all limits unchanged; initial artifact preserved. No additional allowance, actual native memory or full B2f release [E354]–[E359] |
| D115 |2026-10-31 | User reports job21542975_0 FAILED1:0/16m35s; acquisition/epochs/scans/final integrity complete but sampler and cleanup fail | Record resource allowance spent and release terminal collection/download only; independently audit full raw before cause/correction | No margin/causal savings/OOM diagnosis, source-change conclusion, new capsule/retry or full B2f release; source/limits/proofs unchanged [E360]–[E362] |
| D116 |2026-10-31 | Complete failed return independently verifies; aggregate28.700241GiB +4GiB exceeds32GiB, sampler lost and shutdown proof absent | Close A3 resource failed/unqualified; offline total-charge/sampler/shutdown review before any prospective correction freeze | All3,035prior files, source inventories,128+128/56+56 proofs and limits preserved; no retry/new capsule/new native entitlement or full B2f release [E363]–[E365] |
| D117 |2026-10-31 | Offline A3 review finds no justified single memory patch; sampling/shutdown corrections source-backed | Freeze before code; isolated lifecycle correction passes142source+142code-snapshot checks and5,163prior-file preservation | Original tests/native proofs/producer/main/limits unchanged; no exact-image correction qualification, native capsule, retry/entitlement or full B2f release [E366]–[E370] |
| D118 |2026-10-31 | Source/64-row probe shows retained64-bit payloads and overlapping float32 row conversions; exact roundtrip subset can use32-bit codes | Freeze one nonexpanding adaptive codec before code;94+94local cases and5,445prior-file preservation pass | Native fraction/CPU/target/peak unqualified; no producer integration, allowance/capsule/handoff, gate relaxation or B2f release [E371]–[E375] |
| D119 |2026-11-01 | Exact adaptive codec can be integrated without changing original producer SQL/constructor/admission/lifecycle science | Freeze before code;272+272local cases, exact SIF/OCI target-reference checks and5,526prior-file preservation pass | Target execution/full-size CPU/compactability/native shutdown/aggregate peak held; no native handoff, allowance reuse, search or B2f release [E376]–[E380] |
| D120 |2026-11-01 | Exact-image full suite hits standalone PyArrow import fault under local emulation; serial decoder cost needs explicit CPU proof | Freeze review/diagnostics/kernel scope;32+32target kernel cases,4local guard cases and5,697prior-file audit pass | Full target suite0complete/native CPU/memory/B2f held; preserve all272+272local cases/limits; no production fix, dependency change, Torch handoff or allowance reuse [E381]–[E386] |
| D121 |2026-11-01 | Prepare distinct non-emulated target correctness and bounded CPU qualification under unchanged limits | Freeze before code;128+128main/276+276A3/39+39controller local cases,60CPU samples,1,602-member archive and5,757prior-file audit pass | One new unlaunched1h4CPU32GiB handoff only; all old allowances spent, no SSH/job/search, native target/full startup CPU/memory/B2f pending or held [E387]–[E391] |
| D122 |2026-11-01 | Job 21595967 failed after main 128+128 pass and A3 source 165 passes/one interrupted at its 600s cap; full raw and preservation verify | Close qualification allowance spent; retain incomplete target/CPU gates and review fixture construction/verification/I/O offline before any prospective correction | All tests, strict checks, source/image and limits preserved; no demonstrated CPU/I/O cause, native retry, new entitlement or resource/B2f release [E392]–[E396] |
| D123 |2026-11-01 | Complete local profile and source review identify unused ancestor construction within strict path checking | Freeze before code; separate equivalent checker passes 128+128 main/276+276 A3/26+26 helper cases, identical hash/verification/fresh-observation counts and 7,490-file preservation | Original code/tests/limits and all fresh checks preserved; local diagnostic savings do not establish native 600s fit. Complete-budget feasibility/storage design next; no native command, allowance reuse or B2f release [E397]–[E402] |
| D124 |2026-11-01 | Conditional disk plan fits fixed guards; complete budget requires container-startup reserve within preflight; real Mac staging fails8GiB headroom | Freeze before prototype;35+35units/all1,602archive members/10,076prior files verify. Hold full local replay and every native release gate | No guard reduction, prior-file deletion, new native host/capsule/command or spent-allowance reuse. At least8GiBlocal headroom and full replay precede any separately justified native handoff [E403]–[E408] |

| D125 |2026-11-01 | Mac staging requires real headroom without evidence/test loss | 22 byte-identical frozen inputs consolidated with independent COW clones; all173,943 protected hashes and54 metadata/creation checks pass; 10.40GiB free>8GiB guard | Full local staging/replay remains pending; all science/tests/limits/strict checks preserved. No Torch, native handoff, search or spent-allowance reuse [E409]–[E413] |

| D126 |2026-11-01 | D125 capacity enables full exact local staging/replay; three local setup failures identify supervisor-only portability/runtime/permission admission issues | Retain failures, freeze corrections before code;930 local cases/60 samples, full stage/fresh checks/lifetimes and185,133-file preservation pass under unchanged caps | Local stage/replay complete; no native target/CPU/quota/storage/aggregate-memory/resource/controller qualification, Torch handoff, allowance reuse or B2f release [E414]–[E420] |

| D127 |2026-11-01 | Native integration needs explicit startup/identity/storage and bounded persistent failure handling | Freeze separate core/adapters;81+81 new plus all original suites/60 samples, real597MB lossless recovery and189,345-file preservation pass | Target entry closed, no new grant/dispatch or source/test/limit relaxation; actual native authority, target/timing/storage/persistence/memory/resource/retention gates remain held [E421]–[E428] |

| D128 |2026-11-02 | Closed target paths contained readiness/signal/publication/group/binding release gaps | Freeze five bounded corrections, preserve all original tests, verify1,280 local checks/60 CPU samples and195,784 prior files | Native handoff HOLD: concrete authority/group/live-admission backend and fresh allowance absent; downstream target/CPU/memory/resource/B2f still held; no Torch/search/reuse [E429]–[E435] |

| D129 |2026-11-02 | Native entry needed concrete authority and ownership primitives without spending another allowance | Freeze separate backend;642 fresh checks including17+17 actual Linux cases pass; all D128 bytes, full prior science proof and200,143 prior files preserved | Offline backend only; production trust/site provisioning/adapter integration and native handoff remain HOLD; no Torch/search/grant/reuse [E436]–[E442] |
| D130 |2026-11-02 | Complete the remaining offline path to a distinct native qualification | Frozen integration and pending package;1,656 checks/60 CPU,205,032 protected files and exact sealed CLI pass | Read-only upload/site-check ready; actual site evidence and explicit new approval pending; no Torch/search/grant/reuse; target/resource/B2f HOLD [E443]–[E453] |
| D131 |2026-11-02 | Live site metadata disproved the all-ancestors-root assumption; torch.env account is users | Freeze exact prefix policy for login and allocated host;722 checks and full prior preservation pass;71 science files unchanged | Replacement read-only handoff ready; actual site/account review and distinct new authorization pending; no launch/search/grant/reuse [E454]–[E461] |
| D132 |2026-11-03 | Review actual installed-site/project/partition output before a new native allowance | Site/project/cs/reported conservative quota pass; per-invocation project correction and exact conditional commands verified locally | No new authorization/grant/job; native outputs pending; code/tests/limits and all old allowances unchanged [E462]–[E465] |
| D133 |2026-11-03 | Record explicit user authorization and actual distinct native dispatch | Job21756110 submitted with correct PLAN/manifest/project; allowance committed under unchanged1h4physicalCPU32GiB zero-search/no-retry contract | Native state/outcome pending; all older allowances remain spent; no code/test/limit change or assistant remote action [E466]–[E469] |
| D134 |2026-11-03 | Native qualification fails preflight before a qualifying result | Job21756110 FAILED1:0/38s; scope guard holds; exact raw/traceback retrieval prepared under old caps | Allowance spent/closed; no retry/new grant/guard relaxation; role/path and native results unqualified [E470]–[E473] |
| D135 |2026-11-03 | Full traceback identifies allocated configuration validation as the failed gate | SLURM_CONF role confirmed before first Slurm probe/scientific launch; remote collection succeeds | Local full raw/path metadata pending; no guessed exemption/code change/new grant/retry; allowance closed [E474]–[E476] |
| D136 |2026-11-03 | Complete failed21756110return independently verified |9files/16,283bytes; exact configuration role confirmed, actual path metadata absent | No policy correction justified; read-only metadata diagnostic checked; no retry/new allowance/science changes [E477]–[E480] |
| D137 |2026-11-03 | Read-only login/accounting diagnostic returns no configuration metadata | cs624 identified, current SLURM_CONF unset, stored environment NONE | Local unsent support request ready; no policy correction, new grant, retry or source/test/limit change [E481]–[E484] |
| D138 |2026-11-03 | Alternate client-configuration design frozen | Current controller export, PLAN-pinned dependency closure and sealed descriptor can avoid historical cache dependency, conditionally | Design only; export/parser/portability gates open; no new grant, retry, source/test/limit changes [E485]–[E488] |
| D139 |2026-11-03 | Login-only configuration capture command locally verified |32source+32snapshot checks, real local fixture process bounds, original package/semantic references preserved | Ready for user login capture only; no export/client/Torch job or fresh grant locally; no configuration admitted [E489]–[E492] |
| D140 |2026-11-03 | Current login capture reported successful; exact retrieval helper ready |16,647bytes/config+manifest hashes and expected identity;14local download checks | Full raw/download/dependency review pending; no config admitted, export retry, grant or native job [E493]–[E496] |
| D141 |2026-11-03 | Actual capture/static/source review; unchanged candidate and scoped use frozen |10files/40,601bytes and identity/quota verified;192records/noInclude;19release sources reviewed | No adapter/config admission yet; library/native parser/sealed-input/compute gates open; all spent closed [E497]–[E501] |
| D142 |2026-11-04 | Implement and locally verify isolated read-only compatibility/dependency harness |326final source/snapshot Mac/Linux checks, strict old packet/reference preservation; real sealed-FD proof | Empty native closure table; installed/native gates pending; no Torch/grant/search/retry [E502]–[E506] |
| D143 |2026-11-04 | Prepare/verify login-only metadata command and pinned-key upload |29source+29snapshot checks; original326harness proofs/packet/tests/limits preserved | User upload/inspection ready; no connection/job/grant/search; native gate closed [E507]–[E512] |
| D144 |2026-11-04 | Review refused upload session; freeze/verify direct SFTP correction |14source+14snapshot checks including actual local protocol/options/cleanup; old failure/tests/payload preserved | Replacement user upload only; no network/Torch/job/search here; all spent closed [E513]–[E517] |
| D145 |2026-11-04 | Review120slogin verification timeout; freeze/verify separate cost correction |424local checks; one exact original semantic verifier plus unchanged quota tail, original tests/caps/source preserved | New user upload/login block only; native completion pending, no Torch/job/search/reused grant [E518]–[E523] |
| D146 |2026-11-04 | Record successful reported login metadata capture; prepare exact evidence retrieval |56.006sfull strict verifier/2.070squota reported;27source+27snapshot download checks, old tests/limits preserved | Four raw files/download/dependency review pending; no new inspection/job/search/grant [E524]–[E528] |
| D147 |2026-11-04 | Verify actual metadata and freeze/fix observed RPATH capture gap |4files/73,986bytes,18objects/34consistent components;436local checks, only ROOTS delta | User corrected candidate capture next; runtime/native gates held, no Torch/job/search/reused grant [E529]–[E534] |

### Open questions and risks

| ID | Question / risk | Owner | Resolution phase | Evidence required |
| --- | --- | --- | --- | --- |
| R1 | Preparation/hot-policy work located; server/transport decomposition remains unresolved | Codex attribution review complete; P2 owner unassigned | P1 resolved for first mechanism; conditional P2 diagnostic | [E11][E12]; investigate residual wait only if it blocks the declared cost decision |
| R2 | Can the final lifecycle identity preserve compatibility, invalidation, and error behavior? | Codex P2b scoped review complete; next owner unassigned | P2 | P2b declared native outputs/stops/activation/reuse and mechanisms pass [E34]; deliberate negative cases remain local, with broader native lifecycle qualification required before adoption |
| R3 | Are useful stopping decisions predictable and economical from qualified inputs? | Codex bounded P3 complete | Closed for tested procedures; conditional later scope | P3c improves fixed-diagnostic recall but fails activation economics; objective/model/diversity limits remain unresolved, no universal ceiling [E69][E70] |
| R4 | Is the evidence pool sufficiently diverse, rather than merely rich in checkpoints? | Codex exposure audit complete; diversity question open | P0/P3b | Exactly 200 already exposed vectors; older 100 overlap and folds are not fresh validation [E53][E54]; later independent diversity remains unresolved |
| R5 | Which independent final samples can each future comparison use? | Unassigned | P0 | Host-owned entitlement/exposure records |
| R6 | Does the development scorer rank real execution accurately? | Codex fixed-stop/model replay complete; native review unassigned | Any future qualifying family | All P3c outcomes/controls reconstruct; new-policy composite-session latency remains unmeasured. No serving improvement inferred from proxies [E69][E72] |
| R7 | Will a method comparison have sufficient task and episode coverage? | Unassigned | P0/P7 | Prespecified sample/analysis plan and uncertainty |
| R8 | Are remote runtime/index resources still accessible and reproducible? | B1b native identity/conformance pass | Resolved for B1b only |90f4 index/e7dc module and restored data/reader settings verified before/after; any new interface/effort needs its own conformance [E90][E93] |
| R9 | Will each lifecycle change reduce full-path cost rather than move it outside the primary timer? | Codex P2c review complete | P2 scoped accounting resolved | P2c phase/charge replay passes and primary/outer activation savings agree; full constructor/first-use charges remain included [E46][E47]; future mechanisms need new contracts |
| R10 | Can identical activation paths establish per-filter equivalence at the unchanged practical limits? | Codex sealed review complete | Resolved within P2c conditioned scope | All 80 cells/240 interval checks pass [E46][E47]; old P2b remains inconclusive and no cross-scope precision guarantee follows |
| R11 | Can profile identity reuse avoid costly repeated private-profile copying under a valid lifetime? | Unassigned | Deferred; finite P2 closed | Historical P2b fingerprints fall 4→1, recursive copy entries rise 299→1,901; profiler times do not predict unprofiled gains [E35][E39]. P2c is not authorization for another mechanism |
| R12 | Does the conditioned shared-data scope answer the eventual operating requirement without hiding cold work? | Codex scoped limitation recorded; wider owner unassigned | Wider adoption review deferred; original retained | P2c records 563.091 seconds conditioning outer cost / 651.629 seconds reset/conditioning wall (overlapping); full admission remains charged [E46][E47]. No cold-index/novel-query/fresh-connection/deployment claim; engineering already fails |
| R13 | Are three cheap predicate contexts enough to route effort safely? | No supported320 context under current reserve | Read-only scope revision | Every context fails quality; no fitted router or qualified within-context predictor; protected samples remain untouched [E90][E91] |
| R14 | Does effort binding/pool/selector cost erase savings or leak settings? | Isolation passes; current wrapper overhead fails | B1b complete, revised design conditional | Forced640 reuse+0.206ms; two-reader activation costly and poorly calibrated. Revise only under new scope; no causal function attribution or free setup assumption [E90][E91] |
| R15 | Can historical effort data be pooled with current evidence? | Codex B1a audit | Resolved: no automatic pooling | Different physical index, older profiles and distinct group inventories; retain old data as scoped historical mechanism evidence [E76][E82] |
| R16 | Will fixed480 meet quality before spending on repeated timing? | Codex result review complete | Resolved negative for this probe | Relative reserve fails overall/votes32/votes108; valid stop at1,830, no timing/A/A data; no universal effort ceiling [E107][E108] |
| R17 | Does a warm persistent-reader diagnostic answer the eventual lifecycle requirement? | Wider operating-scope owner unassigned | Deferred; B1b2 quality-negative | Startup/first-use/cleanup remain charged; no480 timing/admission or activation qualification acquired [E107][E108] |
| R18 | Can a distinct plan/filter/index mechanism offer a better quality/cost family? | Codex audit complete | B2a source feasibility resolved; economics open in B2b | Exact-top10 mechanism supported by source; no local speed prediction or fitted route [E115][E118] |
| R19 | Are complete catalog/cache/statistics and final identities established? | Partial review complete; future mechanism qualification retains gap | Open for any new mechanism | Recorded8,520 plans/settings prefix validate; full catalog snapshots/final index/module checks never saved/reached. Do not fill from source inference [E142][E143] |
| R20 | Does current exact10 offer useful economics, and should its schedule be extended? | Codex current-family review complete | No repeat recommended; full formal economics unavailable | Complete block0 exact56.11x slower, best observed filter28.47x,0/763 wins; exact occupies93.66% warm window. Redirect to read-only B2c [E144] |
| R21 | Can unchanged module and strict experimental adapter execute the partial target with fresh/cached plans? | B2d native evidence review complete | Resolved within experimental partial640 scope | Actual full/cached plans, unchanged module and index identity verify; public partial-target API/serving support remains separate [E184][E191] |
| R22 | Are new graph build/storage/maintenance and two-copy resource economics useful? | B2d evidence review complete | Build/storage measured; benefit/amortization unqualified |193.35MiB extra graph/20.02% original,84.15s build; failed A/A prevents benefit qualification; maintenance/serving remain deferred [E186] |
| R23 | What causes the persistent partial-session gap and progressive repetitions? | Codex B2e complete; calibration prospective | Cause unresolved; targeted design justified | Matching recorded identities; missing physical backend/CPU/wait/cache evidence, fixed observer/order aliases; instrumented B2f required [E191][E192] |
| R24 | Can the exact B2d partial graph be safely restored? | Startup resource native return reviewed | Resolved for this startup copy, not future allocations | Complete source/copy inventories, final graph/catalog/data/module proofs and clean shutdown verify; every future job must requalify [E232][E237] |
| R25 | Does the allocation expose required cores and owned-process telemetry? | Startup resource native return reviewed | Scoped startup placement/PID/proc mapping verified; full B2f search telemetry pending | Actual four-core selection, ten reader placements and host/container mapping verify; no timing/search evidence [E232][E237] |
| R26 | Does coverage exercise actual startup/control-flow and cleanup? | Local and startup native review complete | Scoped startup now verified on Torch | Prior entry-point/negative regressions plus complete resource acquisition; future correction needs its own coverage [E229][E232] |
| R27 | Does32GiB support frozen margin and later workload? | Failed native attempt; adaptive codec component locally checked | MEMORY UNQUALIFIED; all allowances spent | Maximum payload-only arithmetic exceeds known shortfall by just7.4MiB if every row compacts; native fraction/CPU/peak unknown. Avoided conversion buffers are structural evidence only. No gate change/retry/cache subtraction [E371]–[E375] |
| R28 | Does scoped streaming preserve the exact original identity and restore all bindings? | M3 actual full-size/container proof complete | Scoped native compatibility pass | Original identity reproduced for 247,286 rows,247,287 components, one invocation/restored binding; actual preflight/provenance and independent replay pass. Total-memory/full workload remain separate [E252][E253][E257] |
| R29 | Which loading/retained/verification mechanism supports a next remedy? | A2 informative; exact-vector producer native-qualified and resource harness locally qualified | New resource acquisition ready; causal savings unmeasured | A2 decode RSS +7.478 GiB remains descriptive. Fresh E352 tests scoped startup margin; no cross-run subtraction or workload inference [E333][E348]–[E353] |
| R30 | Are internal driver commands/fetches bounded and observed? | A2 native accounting independently reconciled | Scoped main A2 accounting verified | All 10,145 dispatches, including 9,892 fetches, reconcile across one snapshot/four verification scans. Driver calls are distinct from network packets; a new A3 resource job must requalify [E333][E334] |
| R31 | Do monitoring/driver hooks preserve original control flow and cleanup? | A2/native producer proofs preserved; new full owned-reader/host/runtime local tests pass | Exact-image resource wrapper/cleanup still requires native return | Strict current target provenance before restore; bounded metadata/delegate restoration and full lifecycle proofs required. No old receipt is claimed to cover the new wrapper [E348][E350][E351] |
| R32 | Is the corrected package compatible with actual target control flow? | Exact native original and A3 cases independently verified | NATIVE CORRECTNESS COMPLETE; resource readiness pending | Job 21470341 preserves all 128+128 old and 56+56 A3 cases on exact 3.12.15; no memory/quality/performance inference or spent-command retry [E345]–[E347] |
| R33 | What finite time contract accommodates complete native correctness and final proofs? | C2B and A3 correctness completed within prospective full budgets | RESOLVED FOR COMPLETED CORRECTNESS JOBS; allowances spent | C2B job 21443102 and A3 job 21470341 pass all source/sealed phases and final proofs. No prior timeout is relabeled and no resubmission is released [E319][E346] |

## 10. Immediate next actions

- [x] Freeze, implement and locally verify separate authority/ownership backend:642 fresh checks,17+17 actual Linux cases and200,143 prior hashes pass. Original tests/strict verification/limits and full science proof are preserved; no native authority/allowance release. [E436]–[E442]
- [x] Complete frozen offline host/guest integration, practical authenticated Slurm authority, bounded compatibility corrections and immutable pending bundle;1,656 checks/60 CPU samples and complete preservation pass. [E443]–[E451]
- [x] Review actual UID1001 Slurm prefix failure and preserve old installed package. Freeze and verify exact login/allocated-host compatibility:722 fresh checks; all71 scientific files and all prior evidence remain intact. [E454]–[E460]
- [x] Review the user-run exact installation/site/project/cs/quota evidence and prepare concrete conditional one-allocation commands with a temporary project override. No code/package/env-file change or new grant. [E462]–[E464]
- [x] User explicitly authorizes the distinct finite allowance and submits job21756110; exact PLAN/manifest/project match. The new allowance is committed; no approval/submission rerun is permitted. [E466][E467]
- [x] Receive terminal21756110 FAILED/1:0/38s preflight status and close its allowance. No qualification result or retry is authorized. [E470][E473]
- [x] User collects terminal raw remotely and returns the full chained trace, identifying the failed role as allocated SLURM_CONF validation before first Slurm probe/science. [E474]
- [x] Independently verify and inspect every file of the complete21756110return, reconciling9files/16,283bytes, checksum, receipt, plan/account/approval/submission and terminal failure. Actual allocated configuration path/metadata are absent. [E477]
- [x] User runs the checked login-only diagnostic: cs624 identified; login SLURM_CONF unset and stored environment NONE. No configuration metadata recovered. [E481]
- [ ] Optional forensic route: obtain existing site/log evidence through the prepared NYU HPC request, distinguishing historical allocated metadata from current site layout. No new allocation or spent retry. [E482]–[E484]
- [x] Independently review and freeze alternate prospective client-configuration provenance design before implementation, without relaxing arbitrary-path trust or scientific limits. [E485][E486]
- [x] Prepare and locally verify the bounded login capture command:32source+32snapshot checks, exact body/syntax and original packet/reference/source preservation. [E489]–[E491]
- [x] User reports successful current login capture and returns its full final JSON with16,647bytes/config+manifest SHA and explicit unqualified flags. [E493]
- [x] Download and independently verify all10capturefiles/40,601bytes; complete static/source review and freeze unchanged candidate/scoped read-only use before adapter implementation. [E497]–[E500]
- [x] Freeze/build/locally verify separate read-only compatibility/dependency harness;326final checks pass, original tests/strict verification/limits preserved, native closure table remains empty. [E502]–[E506]
- [x] Prepare and verify exact login-only dependency inspection and pinned-key upload commands;29source+29snapshot command checks pass without a real connection or job. [E507]–[E512]
- [ ] Develop locally verified compatibility/dependency harness, capture actual installed dependency closure and perform exact-version login-only sealed-input validation before config use/release. No new allocation or spent reuse; original tests/strict verification/limits remain mandatory. [E501]


- [x] Complete frozen offline native release review and separate bounded correction:1,280 local checks/60 CPU samples, strict full replay and195,784 prior hashes pass. Native handoff HOLD; no new allowance or Torch commands. [E429]–[E435]
- [x] Concrete authority/ownership backend is verified in D129 and host/guest integration is complete in D130. Live Torch site/account evidence and job-local storage admission remain pending. A native job still needs distinct explicit authorization; target/CPU/resource/B2f remain unqualified. [E436]–[E453]


- [x] Complete user Torch execution, independent local verification and Codex G1 review for NEXT-COST-01. [E11][E12][E16]
- [ ] Assign remaining program owners/resources and future gate reviewers. P3a/P3b/P3c scoped contracts, local limits and correctness/result reviews are complete; wider P0 and any B1 comparison remain open.
- [ ] Reconcile evaluation entitlements and evidence exposure without opening protected query values to a learner.
- [x] Define NEXT-EXEC-01's prospective practical improvement/nonregression thresholds, resource ceiling and one-campaign stopping rule. Broader program/next-revision budgets remain open. [E19]
- [x] Record the measured P1 call-path attribution, lifetime/invalidation map and explicit limits of database-wait attribution. [E12]
- [x] Implement P2a, run local correctness checks, freeze the old/new comparison and seal the user upload. [E17][E18][E19]
- [x] Complete user upload/submission/collection of all three P2a blocks. Campaign and resource consumption are preserved in [E21].
- [x] Ingest with sealed local code; verify native/output/first-stop/mechanism parity; reconstruct primary/outer effects and preserve the failed engineering gate. G2 verdict: revise, with original retained as adopted baseline. [E21][E22][E25]
- [x] Scope and implement NEXT-ADMIT-01's privately owned semantic profile identity and original/P2a/new references, preserving cold costs and original validation/quality criteria. [E27][E29]
- [x] Review exposed timing precision, freeze Williams balance/identical-path A/A criteria and a finite four-block contract; run 45 local checks and seal the package. [E27][E29][E30]
- [x] Receive P2b status reporting all four jobs completed, successful host exits and unchanged protected sources. Preserve the report without promoting it to raw verification. [E33]
- [x] Collect/download P2b, verify archive/all raw files and fresh sealed parity; preserve `measurement_inconclusive`, all A/A failures and the relative activation shortfall. [E34][E35][E38]
- [x] Audit existing activation A/A order/variation evidence descriptively, without correction or exclusion. [E40]
- [x] Freeze and implement NEXT-CAL-01's conditioned shared-data/fresh-session protocol, full cold charges, identical controls, grouped analysis, unchanged margins and finite two-block allowance; pass 44 local checks and seal the package. [E41][E43]
- [x] Complete both user P2c blocks, collection/download, archive/member/raw verification and fresh sealed reconstruction. [E46][E50]
- [x] Review scoped calibration pass and failed engineering target; close finite P2 with G2 retain-original branch, M1 unestablished, and no extra block/retrospective P2b repair. [E46][E47]
- [x] Freeze NEXT-INFO-01/P3a contract and complete existing outcome/feature/exposure/identity audit, with all source hashes and unknowns preserved. No experiment or model fit. [E52][E53][E55]
- [x] Apply P3a coverage gate: pass restricted static23/progress34 grid modeling; no immediate acquisition needed. Current Light19/off-grid/new-policy timing gaps remain explicit. [E54][E55]
- [x] Freeze NEXT-MODEL-01/P3b matched information/actions, vector-group folds, training-only selection, first-stop objectives, invalid outcomes, Codex owner/reviewer and finite budget. [E60]
- [x] Implement, check and run P3b; independently reconstruct saved selections/outcomes without fitting; record negative finite-procedure closure and G3 revise. [E61][E62][E64]
- [x] Audit P3b errors by predicate/difficulty/stage/profile and choose one next formulation hypothesis without changing the completed verdict. [E65]
- [x] Freeze NEXT-RISK-01/P3c risk-separated formulation, unchanged information/action/capacity and quality reserve, finite gates/resources; implement/check/run and independently replay all results. [E68][E69][E72][E74]
- [x] Close P3c and bounded G3 negatively; retain original, preserve safer-but-uneconomic diagnostics and recommend B1a feasibility/design before another experiment. No serving-speed or independent-success claim. [E69][E70]
- [x] Complete B1a/NEXT-SCOPE-01 read-only audit; pass scoped feasibility, preserve code/evidence, reconcile old/current index/runtime/query inventories and cheap-input limits. [E76][E77][E78]
- [x] B1b preparation: frozen contract, experimental implementation, seventeen local checks and sealed package complete. [E84][E85][E86][E88]
- [x] Verify and decide B1b: completed native campaign and recovered local analysis; formal aggregate inconclusive, no supported context/regime. No new user/Torch commands. [E90][E91][E93]
- [x] Complete NEXT-EFFORT-REVIEW-01; audit saved/source costs, retain B1b gates and freeze B1b2's one fixed480 quality-first warm design. No code/tests/experiment or user commands. [E96][E97][E100]
- [x] Complete B1b2 isolated implementation/local correctness/seal and exact commands; preserve original execution and all prior evidence. [E102][E103][E104][E106]
- [x] User B1b2 job/collection/download and Codex archive/raw/fresh sealed verification complete. Close `closed_negative_quality`; retain original and B1c deferred. No user commands now. [E107][E108][E110]
- [x] Complete B2a/NEXT-PLAN-SCOPE-01 source/saved-plan/identity/input-cost/alternative audit; GB2a passes scoped feasibility. Preserve349 source/907 immutable files and every prior verdict; no experiment/code/fit/native access. [E115][E116][E118]
- [x] Freeze/implement/check/seal B2b/NEXT-EXACT-TOPK-01; preserve original and prior inputs; source/sealed/transport/package checks complete. [E120][E121][E122][E123][E125]
- [x] User submitted original B2b once; reported job20941363 initial catalog failure consumes its allowance, with zero searches and no scientific result. [E126]
- [x] Diagnose OID/JSON mock defect; freeze/implement/check/seal separate correction; retain original source/receipt/archive and1,095 prior hashes. [E127][E128][E129][E130]
- [x] User collected/downloaded original failed B2b; Codex independently verified19 archive members, failed qualification, cleanup and integrity. [E134][E135]
- [x] Release separately named, unchanged corrected seal after failed-raw review passes. [E136]
- [x] User submitted corrected job20949301; reported deadline stop consumes its separate allowance. Preserve partial raw and both reservations. [E138]
- [x] User collected/downloaded corrected partial raw; verify30 members,26,247 counted attempts, cleanup/protection,600 quality references,12,208 retained and8,520 plan packets. [E142][E143]
- [x] Codex independently verified corrected prefix quality, exact journal coverage/outputs/timers and phase costs; retain missing final audits and unassessed complete control/economic gates. [E142][E144]
- [x] Close finite B2b incomplete; retain original and both spent allowances, decline extension/repeat of exact10. [E143][E144]
- [x] Complete B2c/NEXT-ANN-ALTERNATIVES-01 read-only evidence/source/cache/cost/alternatives review, scoped single-mechanism GO and preservation. [E147][E148][E149][E151]
- [x] Freeze separate B2d/NEXT-PARTIAL-ANN-01 design: one >=108 partial cosine HNSW, isolated copies, early futility, full scoped quality/controls/final proofs and finite resources. [E150]
- [x] Complete B2d isolated implementation,55 source/55 sealed local correctness, preservation and final161-file seal; release commands. [E154][E155][E156][E157][E159]
- [x] Preserve B2d quota preflight output and original seal; prepare separate compatible seal with61/61 checks and unchanged scientific identities/shared reservation. [E161][E164]
- [x] User: quota-fix upload/submission complete; job21043219_0 reported initial environment failure and consumes the one allocation. Preserve reservation. [E167]
- [x] User collected/downloaded failed B2d; Codex verified21 members, exact admin work_mem mismatch,0 searches, cleanup and23 protected groups. [E171][E172]
- [x] Separate correction frozen/implemented/checked/sealed,75 source/75 sealed; original code/raw/reservations preserved. [E173][E176][E179]
- [x] User corrected submission reports complete, quality/final integrity true and both blocks/16,802 attempts. [E180]
- [x] Separate exact-name collection helper/checks ready; source/seals/campaign/raw preserved. [E182][E183]
- [x] Full B2d archive/identity/name recovery/quality/A/A/economic/final proof verified; two fresh exact-parity replays. [E184][E187][E189]
- [x] Close finite B2d measurement_inconclusive:0/4 A/A intervals pass; retain quality/native opportunity and original execution without speed/adoption claim. [E186][E190]
- [x] Complete B2e/NEXT-PARTIAL-CONTROLS-01 read-only session/source/plan/order/repetition audit; document GB2e calibration-design GO and unresolved causal state. [E191][E192][E194]
- [x] B2f.0–1/NEXT-PARTIAL-CALIBRATION-01: freeze exact graph/margin identities, explicit orders,16,242-call bound, all telemetry/resource/analysis/stops and56 timing gates. No code/tests/experiment. [E195][E196][E197][E199]
- [x] User ran E195§12 read-only inventory and returned output; paths/control files and3/3 graph hashes match, no PID stop, reported quota headroom. [E201][E202]
- [x] Compare user-reported preliminary source inventory to frozen requirements and record limited pass; full clean-cluster/resource/CPU/telemetry feasibility remains a mandatory future gate. [E202][E203]
- [x] B2f implementation/local correctness/preservation/seal and exact Torch handoff prepared on user request. [E205][E206][E207]
- [x] Verify original pre-Python failure and isolate/check/seal its launcher correction. [E209][E210][E211]
- [x] Verify second zero-search startup failure/source/cleanup, repair omitted identity metadata and add actual frozen-backend full local integration. [E214][E215][E216]
- [x] Verify third zero-search B2f failure; reproduce wrong eligibility schema and improve actual runtime-entry-point/cleanup coverage. [E219][E221]
- [x] Receive/review B2f read-only accounting configuration; accounting family/options known, resource feasibility still unqualified. [E223][E224]
- [x] Freeze/implement/check/preserve/seal startup-resource.v1 on explicit user request; zero ANN/exact searches and all old boundaries preserved. [E227][E229]
- [x] User resource-only handoff, terminal collect/download and independent verification complete. Startup pass/resource margin inconclusive; no full calibration launch. [E232][E233]
- [x] NEXT-STARTUP-MEMORY-01 M0/M1: read-only allocation/consumer/identity audit and first correction design frozen; no code/tests/new experiment/job. [E239][E240][E242]
- [x] M2: isolated per-row original-canonical identity hashing, thorough local checks and independent source/sealed readiness complete; 155/155 each, static/archive parity and 3,468 earlier pins pass. [E246][E247][E250]
- [x] M3: user job 21224521_0/terminal collect/download and independent stream/resource verification complete; exact identity/startup/cleanup pass, resource margin inconclusive; allowance spent. [E252][E253][E257]
- [x] NEXT-STARTUP-MEMORY-02 W0–W2 audit complete: retained/verification overlap and API/internal-fetch gap documented; no single remedy qualified. [E259][E260][E263]
- [x] NEXT-STARTUP-ATTRIBUTION-01 A0: zero-search design frozen before code, with102 checkpoints, explicit internal ledgers, resource/overhead/cleanup and informative/unresolved gates. [E265][E266][E269]
- [x] A1: isolated implementation,155 baseline regressions and100source/100sealed actual-path checks, independent replay/archive parity and3,987-input preservation pass. A2 handoff remains unreleased. [E271][E272][E275]
- [x] A2 finite release review caught image-reference compatibility mismatch and held dispatch before spending a job. [E277][E279]
- [x] Prepare/check/seal source-only image inventory with29source/29sealed checks, exclusive binding, authenticated transfer and exact commands. [E280][E281][E282]
- [x] Verify completed user image inventory: four raw files/three payload hashes,108manifest/109archive members and trusted replay. Only Python differs; actual3.12.15 matches A0, identifying A1 reference capture error. [E283][E286]
- [x] Record GO isolated exact-reference correction/readiness; preserve one completed inventory and5,519 prior files. [E284][E287][E288]
- [x] C0/C1 exact native-reference correction and pre-restore source/mask proof implemented;128normal/128guarded local checks pass. [E289][E291]
- [x] Preserve failed bounded local emulated attempt and cleanup; no target pass inferred. [E293]
- [x] C2 native zero-DB compatibility package frozen/implemented/sealed;23source/23sealed local checks and exact handoff pass, no job submitted. [E292][E293][E294]
- [x] First C2 native run/collect/download verified failed:13 archive members/eight locked files, exact reference; missing metadata diagnosed. Old allowance spent. [E296][E297]
- [x] Freeze/implement/check separate dependency/fixture/reporting correction:33source/33sealed and128source/128packaged-fixture main checks, original bytes preserved. [E298][E299]
- [x] Corrected C2 user run/collect/download verified failed:96passes/no errors;16-file/11-lock/provenance/dependency/final-integrity proof; second allowance spent. [E302]
- [x] Freeze/implement prepared fixtures and synchronous-diagnostic amendment;43source/43sealed and128source/128packaged cases pass through complete final guards; actual manifest equivalence and prior-byte preservation pass. [E303][E304][E305][E306]
- [x] User prepared C2 qualification E307 collected/downloaded and independently verified failed: job 21382454, 119 passes/no errors, 16-file/11-lock return, exact identities and final host integrity. Third allowance spent. [E308][E309]
- [x] C2B independent trace/source budget review and prospective 21 mfull critical-path freeze precede isolated budget/accounting implementation. All 128+128 native cases and main code/limits preserved. [E312][E313]
- [x] Complete local 62 source/62 sealedcapsule and 128 guarded source/128 packaged-fixture main checks, original reseal parity, source/archive/cleanup/preservation release review. One distinct E315 handoff ready; no job submitted. [E314][E315]
- [x] User C2B native 128+128/full guard/build/seed/timing/cleanup/exit/lock qualification and independent return review complete. [E319]
- [x] C3 production seal and final local/readiness/controller/archive/preservation review complete; main-only E322 commands ready, no job submitted. [E321][E322]
- [x] Main A2 E322 acquisition/terminal collect/download and independent complete replay verified: job 21459623_0, attribution complete/informative; resource margin inconclusive. Allowance spent. [E333]–[E335]
- [x] A3 remedy/producer/startup integration and distinct native correctness independently verified: job 21470341, all 368 cases, exact target/provenance/guards/timing/final integrity pass. Allowance spent. [E345]–[E347]
- [x] Separate resource protocol/harness/amendment, 100 source + 100 sealed checks, production seal and independent complete release/offline handoff audit pass. One distinct E352 allocation released, unlaunched. [E348]–[E353]
- [x] Complete21542975_0 failed-raw collection/download/independent audit and failed-unqualified closure. Original package/proofs/source preserved; recorded aggregate headroom fails independently of sampler/shutdown loss. [E363]–[E365]
- [x] Complete offline memory/sampling/shutdown review and prospective lifecycle correction/local qualification;141+141guarded cases pass, original tests/proofs/limits preserved. No native qualification or memory remedy claimed. [E366]–[E370]
- [x] Freeze and locally verify exact adaptive memory-component design:94+94cases, raw64 fallback and original consumer/identity/matrix/ownership parity. Native headroom remains unqualified. [E371]–[E375]
- [ ] Prospective production-integration and exact-target proof design, with original snapshot/runtime deadlines and all source/scientific guards; no spent-allowance reuse/new entitlement or native handoff. [E374][E375]
- [ ] B2f.R3 final release review/seal/checks before any new handoff; production packaging currently blocked. [E221]
- [ ] Only after a qualified startup-resource correction, outstanding query-workload memory review and R3, consider a separately scoped full calibration allocation and complete N0–N4. All prior calibration/resource/attribution/correctness allowances are spent; no new job released. [E335][E347]
- [x] Preserve B2b incomplete-matrix/no-repeat closure and both consumed exact-top10 allowances; no retrospective acceptance. [E142][E144]
- [ ] Prepare P7 benchmark design and reconcile final evaluation entitlements independently of P3's exposed-data diagnostics.
- [x] Freeze P2b hypothesis, identities, resources and acceptance analysis before dispatch. Future campaigns retain the same reviewable-contract requirement. [E29]

## 11. Local evidence sources

These links are relative to this roadmap. E1–E10 preserve the original saved-evidence baseline; E11–E16 record independently recomputed P1 evidence. E17–E20 preserve the P2a pre-dispatch implementation/contract. E21–E26 record v1.4's independent local reconstruction and interpretation of the user's completed P2a campaign. E27–E32 record v1.5's separate P2b implementation, local checks, precision review and sealed run instructions. E33 preserves v1.6's provisional user-reported completion. E34–E40 record v1.7's independent raw verification, inconclusive qualification and descriptive order audit; these supersede provisional status for conclusions. E41–E45 preserve v1.8's P2c pre-dispatch implementation, scoped contract and user commands. E46–E51 preserve v1.9's P2c verification, scoped calibration pass, engineering shortfall and retain-original/P3a decision. E52–E59 record v1.10's frozen data-only audit, coverage/identity/feature evidence, restricted modeling decision and explicit remaining scopes. E60–E67 record v1.11's frozen P3b implementation/contract, completed 340-fit local campaign, independent replay and negative finite-procedure result. E68–E75 record v1.12's frozen risk-separated P3c design,100-fit run, independent reconstruction and negative joint closure. E76–E83 preserve v1.13's completed read-only B1a audit. E84–E89 record v1.14's frozen B1b contract, isolated implementation, seventeen local checks, sealed package and exact Torch instructions. E90–E95 record v1.15's completed B1b raw verification, fresh unchanged sealed replay, proven mount-name metadata recovery, measured quality/cost/control results and no-B1c decision. E96–E101 record v1.16’s completed source/saved-timer review, prospective B1b2 design,685-file preservation inventory and documentation receipt. E102–E106 record v1.17’s isolated B1b2 implementation,22 source/22 sealed correctness checks, exact package integrity and user commands. Mocks are local correctness simulations, not native measurements. E107–E114 record v1.18’s completed native B1b2 quality-negative return, fresh sealed/ID-based verification, quantified shortfalls, preservation and proposed read-only B2a. The user ran the one1,830-search job; this revision ran no new native/database/provider/Torch experiment, scientific fit or protected-query access. E115–E119 record v1.19’s completed B2a source/saved-plan/identity/input audit, scoped exact-top10 design GO,349-source/907-file preservation and documentation checks. No new experiment or implementation occurred. E120–E125 record v1.20’s frozen B2b contract, isolated implementation,33 source/33 sealed checks, exact package/command identities and912-file preservation. Native gates remain unassessed. E126–E133 record v1.21’s user-reported zero-search failed qualification, source-backed type diagnosis, frozen separate correction,43 source/43 sealed checks,1,095-file preservation and collection-only current handoff. That pre-return snapshot is historical. E134–E137 record v1.22’s independently verified original failure/cleanup/integrity and release of the unchanged separate corrected handoff. That release snapshot is historical. E138–E141 record v1.23’s user-reported corrected deadline failure, source/counter interpretation and collection-only next step, with1,315 earlier files preserved. That status snapshot is historical. E142–E146 record v1.24’s independently verified partial return, prefix quality pass, descriptive severe exact-path cost, phase accounting, incomplete finite closure/no repeat and proposed B2c review, preserving1,352 prior files. No new experiment, scientific implementation change or submission. E147–E152 record v1.25’s completed B2c read-only alternatives/binding/predicate/cache/cost audit, scoped GO and separate frozen B2d design, preserving349 source/1,364 prior files. No implementation/tests/experiments/bootstrap/native or protected access; B2d gates remain future. E153–E160 record v1.26’s isolated B2d implementation/addendum,55 source/55 sealed correctness checks, final161-file seal and once-only handoff, with349 source/1,370 prior files preserved. The internal undispatched review seal is retained as superseded; no native/index/Torch/provider/fit/protected use occurred. Earlier sources/receipts remain unchanged.

| ID | Source | Use / limitation |
| --- | --- | --- |
| E1 | [Selective-agent pilot postrun verification][E1] | Authoritative selective-episode summary, per-arm statistics, cost components, provenance, and abstention |
| E2 | [Selective-agent pilot report][E2] | Compact timing/quality comparison; percentages are each arm versus its paired native baseline |
| E3 | [Selective-agent implementation and episode record][E3] | Current closed-episode status, qualification history, and execution counts |
| E4 | [Earlier frozen-policy held-out confirmation][E4] | Latency benefit but recall failure; consumed sample, not fitting input |
| E5 | [Offline first-stop fitter comparison][E5] | CART/beam procedures continued; no new measured policy latency |
| E6 | [Feature/data ablation report][E6] | All arms stopped after calibration without nonconstant selection |
| E7 | [Selective-agent protocol and workflow][E7] | Existing gates, budgets, split rules, timing boundaries, and one-feedback-round contract |
| E8 | [Offline learning interface documentation][E8] | Measured outcomes, unknown labels, candidate archive, and qualification boundaries |
| E9 | [Agent design][E9] | Existing controller, sandbox, evidence, and serving responsibilities |
| E10 | [Master experiment index][E10] | Broader chronology, reproduction instructions, and historical limitations |
| E11 | [Cost-attribution postrun receipt][E11] | Archive/package/raw identities, exact counts, local/remote parity, primary statistics and Codex G1 review |
| E12 | [Cost-attribution interpretation and P2 mechanism][E12] | Detailed results, profiled-call interpretation, proposed lifetimes/invalidation and residual limits |
| E13 | [Locally reconstructed primary timing report][E13] | Unprofiled arithmetic means; each arm has its own paired native |
| E14 | [Locally reconstructed function attribution][E14] | Separate perturbed diagnostic pass; per-block/arm/filter/phase self and inclusive times |
| E15 | [Complete local performance data][E15] | Vector-group intervals, per-filter/per-block statistics, all function profiles and raw hashes |
| E16 | [Local sealed-analysis verifier result][E16] | Passing remote/local parity under the frozen tolerance; no acceptance/confirmation claim |
| E17 | [P2a implementation/check receipt][E17] | Preserved pre-dispatch identities, 31 local tests, syntax/lint/sealed checks, caps and zero execution at that snapshot |
| E18 | [P2a implementation and runbook][E18] | Owned-handle lifecycle, local checks, upload/submit/status/collect/download and recovery instructions |
| E19 | [Frozen P2a comparison contract][E19] | Unchanged policies, timing/ownership boundaries, engineering criteria, 143,163-search resource cap and finite stopping rule |
| E20 | [Generated exact Mac/Torch commands][E20] | Preserved upload/submission/collection/ingestion runbook for the now-completed campaign; do not resubmit |
| E21 | [P2a postrun verification receipt][E21] | Archive/raw/runtime identities, complete native/stop/mechanism checks, actual consumption, direct comparisons and failed engineering gate |
| E22 | [P2a measured interpretation and next decision][E22] | Reuse benefit, activation/control uncertainty, ordinary-native comparison, remaining admission cost and proposed next scope |
| E23 | [Reconstructed P2a timing/gate report][E23] | Each variant versus paired native and direct owned/original comparisons, with all gate failure strings |
| E24 | [Complete reconstructed P2a performance data][E24] | All vector-group/filter/block intervals, profiles, contrasts and raw hashes |
| E25 | [P2a sealed local verifier result][E25] | Passing local/remote parity; no acceptance or confirmation claim |
| E26 | [Reconstructed P2a function attribution][E26] | Separate diagnostic function counts/times; confirms removed reuse preparation and unchanged constructor work |
| E27 | [P2b implementation/check receipt][E27] | Historical pre-dispatch snapshot: 45 local checks, unchanged references, sealed identities, finite caps and zero native execution at packaging |
| E28 | [P2b implementation/runbook][E28] | One per-admission identity, full original validation and inherited P2a query path |
| E29 | [Frozen P2b engineering/A/A contract][E29] | Four labels/three policies, Williams schedule, full cold costs, strict A/A equivalence and finite allowance |
| E30 | [Existing-data P2b precision review][E30] | P2a interval/block evidence, ordering limits, no power guarantee or control subtraction |
| E31 | [Generated exact P2 b commands][E31] | Historical runbook for the completed campaign; do not resubmit |
| E32 | [Generated Mac transfer helper][E32] | Interactive authentication, file-based binding parse, identity/checksum checks and sealed ingestion |
| E33 | [P2b user-reported Torch completion][E33] | Preserved historical status/Slurm snapshot; superseded for conclusions by E34 |
| E34 | [P2b postrun verification receipt][E34] | Archive/raw/runtime identities, fresh sealed parity, all contrasts, mechanisms, actual consumption and inconclusive gate |
| E35 | [P2b measured results and next decision][E35] | Original/P2a comparisons, A/A assessment, relative saving shortfall, residual copying cost and calibration/retain proposal |
| E36 | [Fresh reconstructed P2b timing report][E36] | All direct comparisons and literal A/A/engineering failure strings |
| E37 | [Complete fresh P2b performance data][E37] | Vector/filter/block intervals, individual native references, profiles and raw hashes |
| E38 | [Fresh sealed P2b verifier][E38] | Passing local/remote parity; verification success is distinct from the inconclusive engineering gate |
| E39 | [P2b diagnostic function attribution][E39] | 576 diagnostic groups; fingerprint/copy tradeoff; timing perturbation prevents treating these as primary speed |
| E40 | [Existing-data activation order audit][E40] | Descriptive all-row position/variation evidence; no new experiment, causal attribution, outlier exclusion or correction |
| E41 | [P2c implementation/check receipt][E41] | 44 checks, execution/gate byte identities, package/archive pins, finite cap and zero native execution |
| E42 | [P2c implementation/runbook][E42] | Fixed conditioning, adjacent AB/BA crossovers, native/original/P2a/P2b controls and raw-phase verifier |
| E43 | [Frozen P2c scope/gates/resources][E43] | Conditioned shared query/index plus fresh-session objective, full admission charges, strict equivalence and finite redirect |
| E44 | [Generated exact P2c commands][E44] | New-package upload, two-job single submission, status/collect and sealed ingestion |
| E45 | [Generated P2c Mac transfer helper][E45] | Interactive authentication, binding/campaign identity checks and checksum/sealed replay |
| E46 | [Verified P2c postrun receipt][E46] | Archive/41 members/26 locked hashes, fresh parity, actual resources, all A/A and engineering outcomes, retained-original decision |
| E47 | [P2c results and next-step analysis][E47] | Calibrated concurrent comparisons, complete scope limits, practical gate failure and bounded P3a coverage branch |
| E48 | [Fresh sealed P2c timing report][E48] | Direct contrasts and unchanged gate failures; byte-identical to remote |
| E49 | [Fresh sealed P2c performance data][E49] | All 80 A/A cells, order diagnostics, filters/blocks, accounting and 144 nonregression endpoints |
| E50 | [Fresh P2c reconstruction verification][E50] | Remote/local parity at frozen tolerance; no selection, confirmation or acceptance |
| E51 | [Fresh sealed P2c calibration scope report][E51] | Conditioned shared-data/fresh-session interpretation and full-charge/no-correction limitations |
| E52 | [Frozen P3a data-only contract][E52] | Permitted exposed inputs, protected exclusions, no fitting/experiments, local limits and scoped decision rule |
| E53 | [Complete P3a saved-data audit][E53] | 620 source/input hashes, proof/label/prefix reconstruction, runtime identities, group/exposure and all profile/filter/stage counts |
| E54 | [P3a results and modeling/acquisition decision][E54] | Complete restricted coverage, qualified information/aliasing, exact remaining gaps, adaptive-development and proxy limits |
| E55 | [P3a audit receipt][E55] | Artifact/source pins, zero new experiments/fits, restricted coverage pass, final G3 open and local aggregate-I/O accounting caveat |
| E56 | [P3a data-validation implementation][E56] | Reproducible hash/join/count/causal-prefix checks; no fitting, policy search, DB or network |
| E57 | [P3a coverage matrix][E57] | Every static/progress filter/checkpoint denominator, reachable/invalid/recall/cost-proxy count |
| E58 | [P3a qualified-feature alias diagnostics][E58] | Identical Light19 filtered traces with 359 differing complete-recall-preservation targets; descriptive only |
| E59 | [P3a aggregate coverage/feature summary][E59] | Matched stop outputs, constant static/dynamic progress observations, Light19/off-grid gaps and native recall |
| E60 | [Frozen P3b scientific contract][E60] | Matched information/actions, nested vector folds, bounded utility models, fixed selection/diagnostics, resources and finite stop rule |
| E61 | [P3b postrun verification receipt][E61] | Source/dependency/input/output identities, local checks, 340 fits, resources, replay, negative gate and preserved zero-fit failure |
| E62 | [P3b results and next gate][E62] | Calibrated abstention, diagnostic recall/savings conflict, limitations and P3c formulation hypothesis |
| E63 | [Complete P3b performance data][E63] | All calibrated/fixed-diagnostic reports, controls, paired vector contrasts and selected/continued cells |
| E64 | [Independent saved-result replay][E64] | 560 admission assessments / 4,800 outer cases, canonical model/group checks and 1e−12 report parity; zero refits |
| E65 | [P3b descriptive failure analysis][E65] | 225 positive-proxy recall failures, 305 recall-passing nonpositive candidates, filter/stage/difficulty errors and pruning counts |
| E66 | [P3b local correctness receipt][E66] | Fourteen synthetic checks, twelve total synthetic fits, lint/format, exact source hashes and guarded API import |
| E67 | [Preserved P3b preflight repair][E67] | Zero-fit failed launch, bytecode-cache guard repair, unchanged scientific contract and original source/log preservation |
| E68 | [Frozen P3c scientific contract][E68] | Risk-only partitions/separate leaf benefits, matched capacity/folds/actions, finite gates/resources and closure branch |
| E69 | [P3c postrun receipt][E69] | Local checks,919 prior pins,100-fit resources, all source/output identities, replay, negative joint result and next scope |
| E70 | [P3c results and closure][E70] | Calibrated/fixed diagnostics, P3b proxy comparison, risk/economics limits and proposed B1a feasibility/design |
| E71 | [Complete P3c performance data][E71] | All profile/method/phase reports, controls, selected cells and paired contrasts |
| E72 | [Independent P3c saved-result replay][E72] | Model/leaf statistics,980 inner assessments,4,800 outer cases, baseline/control reconstruction and 1e−12 parity; zero fits |
| E73 | [P3c descriptive analysis][E73] | Inner-to-outer transfers, predicate/stage/difficulty errors, pruning and finite negative closure |
| E74 | [P3c local-check receipt][E74] | Sixteen tests/six synthetic fits, lint/format, guarded API and exact P3b report preflight |
| E75 | [P3c implementation/reproduction][E75] | Risk/benefit semantics, source layout, exact local recipe, preservation/stop rules and primary sources |
| E76 | [B1a feasibility audit and proposed B1b stages][E76] | Engine control, unsupported current effort API, cheap-input limits, native timer/isolation requirements and scoped recommendation |
| E77 | [B1a read-only audit receipt][E77] | Source/input preservation, zero code/tests/experiments, scoped feasibility pass and unchanged milestone boundaries |
| E78 | [B1a source/input inventory][E78] | 324 code/source files,29 explicit references and old 122-input/six-output hash inventory |
| E79 | [Historical ef-sweep verified report][E79] | Thirty exposed vectors, old-graph four-level native quality/speed/complete-result tradeoff; no current-index transfer |
| E80 | [Historical ef-sweep verifier receipt][E80] | Saved25,920-pair/216-conformance verification and output hashes; archive digest is historical |
| E81 | [Historical ef-sweep detailed analysis][E81] | Pinned raw inventory, block/control/per-filter results and scope limitations |
| E82 | [Current P2/P3 physical-index identity][E82] | Current90f4 graph/file hashes; matches historical full-size320 graph, differs from old ef-sweep 6076 graph |
| E83 | [B1a machine-readable findings][E83] | Control/API/feature/identity/coverage findings, proposed two-level native interface and no router fitting |
| E84 | [B1b frozen prospective contract][E84] | Native320/640 envelope, source/original references, scope, costs, conformance, finite resources and regime-specific gates |
| E85 | [B1b implementation/reproduction guide][E85] | Source layout, local checks, MFA-safe transfer and exact collection/ingestion workflow |
| E86 | [B1b preparation verification receipt][E86] | Historical pre-run snapshot: seventeen source/sealed checks, preservation and unassessed native/frontier state |
| E87 | [B1b exact Mac/Torch commands][E87] | Upload, once-only verification/extraction/submission, status, collect and checksum/sealed download replay |
| E88 | [B1b sealed package manifest][E88] |146 pinned files; manifest35a09d4e…b69c1f;14,810,618-byte archive2a25b90d…e37291 |
| E89 | [B1b local check/integrity records][E89] | Full two-block mock raw replay, timer tamper rejection, lint/format/package verification and prior-input preservation |
| E90 | [B1b completed-campaign receipt][E90] | Exact counts/identities, native/control/quality/economic results, scoped metadata recovery and no-B1c decision |
| E91 | [B1b verified results and interpretation][E91] | Full latency/recall/A/A tables, limitations, retained original and next read-only revision scope |
| E92 | [Fresh unchanged sealed B1b replay][E92] | All comparison/interval/gate values reconstructed from original raw data |
| E93 | [B1b archive/raw/metadata recovery verification][E93] | All40 archive members, exact submission/job/package proof, scoped campaign alias reconciliation and original tolerance |
| E94 | [Data-only B1b campaign-identity recovery helper][E94] | No sealed/raw/gate changes; four regression checks reject unrelated differences |
| E95 | [B1b descriptive result audit][E95] |46 quality-loss cases, filter outcomes, arithmetic contrasts and preserved formal verdict |
| E96 | [Completed B1-review and go/no-go][E96] | Admission/validation/lifetime/source/timer audit, limits and fixed480 design recommendation |
| E97 | [Prospective B1b2 fixed-effort contract][E97] | Detailed phases, identities, quality-first stop, warm-only A/A/benefit and one-allocation59,430-search ceiling; no implementation/run |
| E98 | [B1-review machine-readable audit][E98] | Existing per-block timer means, matched forced640 timer decomposition, static SQL counts and no-experiment decision |
| E99 | [B1-review immutable input inventory][E99] |685 hashes,146 sealed B1b files,40 returned files and prior324/29/128 hash checks |
| E100 | [B1-review completion/preservation receipt][E100] | Documentation-only changes, post-review preservation and unassessed B1b2 execution gates |
| E101 | [B1-review documentation checks][E101] | New evidence/link/reference and contract-count checks; no execution correctness/performance claim |
| E102 | [B1b2 implementation/reproduction guide][E102] | Single-reader ownership, unchanged native/scorer methods, quality-first/warm-only scope and exact local workflow |
| E103 | [B1b2 implementation/local-readiness receipt][E103] |22 source/22 sealed tests, zero native runs,691 prior-file preservation and unassessed native/quality/control gates |
| E104 | [B1b2 sealed manifest][E104] |150 files; manifestb7ad5be7…c34bc1;14,831,467-byte archivefbd7ac06…e6185 |
| E105 | [B1b2 exact Mac/Torch commands][E105] | MFA-safe upload/download, once-only single-job submission, status and collection |
| E106 | [B1b2 local check/integrity records][E106] | Full/early-stop mocks, negative collect/archive/replay, rehashed timer and coverage rejection; package/shell/preservation/documentation checks |
| E107 | [B1b2 post-run verification receipt][E107] | Completed1,830-search campaign; negative quality, exact parity, source/evidence preservation and unassessed timing |
| E108 | [B1b2 result interpretation and next scope][E108] | Recall reserve shortfalls, case counts, matched320 descriptive quality and proposed B2a |
| E109 | [B1b2 fresh sealed performance][E109] | Frozen quality/charge/gate reconstruction; no timing/A/A/benefit observations |
| E110 | [B1b2 independent return verification][E110] | Fresh/remote/download reports byte-identical; saved-ID and matched quality identities checked |
| E111 | [B1b2 saved descriptive arithmetic][E111] | 11 misses/nine vectors versus640;37 recovered versus320; no new bootstrap or latency comparison |
| E112 | [B1b2 input/preservation inventory][E112] | 888 immutable files and mutable-document before hashes; explicit transport-only exception |
| E113 | [B1b2 archive/preservation proof][E113] | 24 returned and151 package members match bytes;691 prior preparation files preserved |
| E114 | [B1b2 documentation/preservation checks][E114] | Local links/reference/progress/gate consistency and final888-file preservation; no experiment claim |
| E115 | [B2a plan/filter/index feasibility report][E115] | Loaded truth/native paths, saved plans, alternative/input-cost matrix, named unknowns and B2b design recommendation |
| E116 | [B2a machine-readable audit][E116] | Scoped GB2a GO; seven alternative classes; identities, compact plans, eight findings and finite future proposal |
| E117 | [B2a source/input inventory][E117] | 349 existing code/source files and907 immutable paths; prior888 inputs/post-run outputs verified before review |
| E118 | [B2a completion/preservation receipt][E118] | Source/evidence hashes preserved; zero code/tests/experiments/fits/simulations/native access; no user commands |
| E119 | [B2a documentation checks][E119] | New evidence/source links, phase/gate/progress consistency and final907-file preservation |
| E120 | [Frozen B2b exact-top10 contract][E120] | Preimplementation identity, metadata/semantic/quality/control/multiplicity/timer and resource contract |
| E121 | [B2b implementation/reproduction guide][E121] | Fixed reader bindings, unchanged native/truth methods, metadata/replay and exact local workflow |
| E122 | [B2b implementation/local-readiness receipt][E122] | 33 source/33 sealed checks, zero native experiments,912-file preservation and pending actual gates |
| E123 | [B2b sealed package manifest][E123] | 153 files;0124abaa…6f55e;154-member archive01c6d272…7b65d |
| E124 | [B2b exact Mac/Torch commands][E124] | MFA/local/remote checksum staging; once-only xt_control.py submit/status/collect and sealed download |
| E125 | [B2b local correctness/integrity checks][E125] | Full and failure mocks, initial corrected check history, catalog/cache/timer/tie integrity, archive/helper/preservation/documentation checks |
| E126 | [Original B2b user-reported failure][E126] | Job20941363/campaign/zero-search failure; explicitly not raw-verified |
| E127 | [Catalog failure diagnosis and recovery][E127] | Source-backed OID defect, limits, unchanged scope and revised critical path |
| E128 | [Frozen catalog correction addendum][E128] | Separate version/allowance, strict type repair, recovery prerequisites and unchanged scientific design |
| E129 | [Catalog correction readiness receipt][E129] |43 source/43 sealed checks,155-file seal, preservation and pending raw/native gates |
| E130 | [Catalog correction local checks][E130] | Source/sealed regressions, original rejection reproduction, failed fixture limit, package/transport/scientific/preservation proof |
| E131 | [Current failed-v1 collection commands][E131] | Original Torch collect then original Mac download; no new job or old reservation reset |
| E132 | [Separate corrected sealed manifest][E132] |155 files;6b2bb0f4…c6f842;156-member archiveb15b0b4b…75f95b; unchanged seal now released through E136 |
| E133 | [Separate correction source guide][E133] | Exact text check, retained constraints, rejected-catalog diagnostics and conditional workflow |
| E134 | [Original B2b failed-return verification][E134] |19 archive members, identity/accounting/cleanup/protected evidence; no searches or performance result |
| E135 | [Failed-run completion and corrected-release receipt][E135] | Raw failure verified, original/corrected evidence preserved, unchanged correction commands released; no job submission |
| E136 | [Historical corrected submit/run commands][E136] | Used for job20949301, now terminal failed by user report; allowance consumed; use E139 collection only |
| E137 | [Verified failure interpretation and next step][E137] | What is verified, missing catalog/binding/elapsed limits, unchanged scientific scope and R4 dependencies |
| E138 | [Corrected deadline-stop status record][E138] | User-reported job/campaign/attempts/partial progress; explicitly not raw verified |
| E139 | [Corrected failed-run collection-only commands][E139] | Existing corrected controller collect, then corrected Mac helper download; no new job |
| E140 | [Deadline-stop interpretation and audit scope][E140] | Internal110-minute limit, source-inferred prefix quality, partial coverage and no full gate/subset rescue |
| E141 | [Deadline-stop preservation/documentation records][E141] |1,315 earlier inputs/artifacts preserved, unchanged scientific code/packages and current status/phase tracking |
| E142 | [Corrected partial-return analysis][E142] |30 archive members,600 verified quality references, exact schedule/timer/output/plan prefix, descriptive costs and missing full gates |
| E143 | [Corrected partial-return completion receipt][E143] | Incomplete finite closure, verified prefix quality/cleanup/protection and1,352 prior-file preservation; no new experiment |
| E144 | [Verified partial results and next-scope recommendation][E144] | Quality/latency/phase/A/A limits; no repeat of exact10; proposed read-only B2c tasks/gates |
| E145 | [Data-only partial analysis source][E145] | Imports trusted sealed validators, verifies available prefix without invoking complete-run gates; no raw/sealed modification |
| E146 | [Partial-review checks/preservation][E146] | Original/corrected code/packages/raw preserved, document/progress/hash checks and no-new-run record |
| E147 | [Completed B2c alternative-scope report][E147] | Selected one >=108 partial-HNSW design; public/C binding distinction, isolated copies, predicate/cache and cost/maintenance caveats |
| E148 | [B2c machine findings][E148] | Source findings, saved costs, option decisions, activity limits and prospective counts/gates |
| E149 | [B2c source/input preservation inventory][E149] |349 source and1,364 immutable prior-file hashes; prior roadmap/index digests |
| E150 | [B2d prospective partial-ANN design][E150] | Design only:200 cases/16,802 max searches,24-vector futility, strict native/quality/A/A/economic/final-proof/resource gates |
| E151 | [B2c completion/preservation receipt][E151] | Read-only completion; source/evidence preservation and no-code/no-run record |
| E152 | [B2c documentation checks][E152] | Link/progress/count/hash consistency; no correctness tests or experiments |
| E153 | [B2d prospective implementation addendum][E153] | Quota/memory/deadline/SQL/durable-failure details; original scientific contract unchanged |
| E154 | [Isolated B2d source][E154] | Private two-copy/single partial index, actual predicate/plan/identity and finite acquisition/replay/control implementation |
| E155 | [B2d local completion/handoff report][E155] | Scope,55 source/55 sealed checks, final seal, resource limits and remaining native gates |
| E156 | [B2d local checks/package verification][E156] | Source/sealed JSON/logs and package-checks.json; all mocks, no native performance evidence |
| E157 | [B2d final sealed manifest][E157] |161 manifested files and immutable scientific design/runtime/code/input identities |
| E158 | [B2d exact once-only run commands][E158] | Explicit Mac upload/checksum, Torch submit/status/collect and Mac download/replay |
| E159 | [B2d implementation/readiness receipt][E159] | Final hashes, preserved prior inputs, local readiness and no native/submission claims |
| E160 | [B2d preservation inventory][E160] |1,370 prior immutable hashes and349 existing source files; allowed mutable roadmap/index snapshots |
| E161 | [B2d quota failure/repair report][E161] | Pre-dispatch failure, conservative format fix,61/61 local checks, separate seal and current critical path |
| E162 | [Isolated quota repair source][E162] | Resource parser aliases/SGR, unchanged scientific runtime and shared reservation |
| E163 | [Quota repair local/package records][E163] | Captured quota,61 source/61 sealed checks, archive proof and1,733 prior hashes |
| E164 | [Quota repair completion receipt][E164] | Scientific byte parity, immutable preservation, no allocation consumed and pending native gates |
| E165 | [Current quota-fix commands][E165] | Corrected upload/extract/once-only submit, new-path status/collect and trusted download/replay |
| E166 | [User preflight output][E166] | Bundle verified; myquota parsing stops before reservation/binding/Slurm |
| E167 | [B2d submitted-job failure output][E167] | Actual21043219 dispatch and initial-settings failure;0 reported searches/readers |
| E168 | [Current B2d collection-only commands][E168] | Torch collect, then existing quota-fix Mac download; no submission |
| E169 | [B2d environment-failure source interpretation][E169] | Admin/reader guard ordering, exact mismatch unknown and failed-raw review requirements |
| E170 | [B2d native-failure status/preservation receipt][E170] | User-reported provisional failure, consumed allowance,1,928 prior hashes and no new experiment |
| E171 | [Verified failed B2d data analysis][E171] |21-member checksum/lock/SQL/accounting/cleanup/protection proof and exact admin work_mem mismatch |
| E172 | [Failed B2d postrun receipt][E172] | Trusted data-only verification; original allowance consumed, no performance result |
| E173 | [Frozen settings correction contract][E173] | Explicit roles, unchanged reader policies/gates, numeric memory/build units and one separate corrected allowance |
| E174 | [Isolated settings correction source][E174] | Role/resource/replay/provenance correction only; adopted/prior code unchanged |
| E175 | [Settings correction completion report][E175] | Failure diagnosis,75/75 checks, exact seal, scope limits and handoff |
| E176 | [Settings correction local/package proof][E176] |75 source/75 sealed, full mock replay, rehashed tampering/prerequisites,1,960 prior hashes |
| E177 | [Settings correction manifest][E177] |169 files; scientific runtime/data/schedule/source provenance pinned |
| E178 | [Current settings-fix exact commands][E178] | New upload/checksum, one distinct corrected Torch submit/status/collect/download |
| E179 | [Settings correction readiness receipt][E179] | Full scientific scope diff, preservation, zero new native activity and pending gates |
| E180 | [Corrected B2d completion status][E180] | User-reported full runtime/quality/final integrity, unverified A/A/economics |
| E181 | [Current exact-campaign collection commands][E181] | Small-helper Mac upload, Torch raw collect, new-helper Mac download; no job |
| E182 | [Collection recovery source/checks][E182] | Eight data/scheduler tests, strict one-campaign manifest/job/lock guards and safe ingest |
| E183 | [Completion/collection recovery receipt][E183] | Prefix source diagnosis,2,166 prior files preserved, no scientific edits or new experiment |
| E184 | [Complete B2d raw/identity verification][E184] |37 archive members; native/settings/results/locks/graphs/cleanup/protection; exact-name recovery proof |
| E185 | [Unchanged sealed B2d performance replay][E185] | Quality pass/nominal economic endpoint pass, all A/A intervals fail, measurement_inconclusive |
| E186 | [B2d results and next-step report][E186] | Quantified quality/timing/controls/costs/limits; retain original and propose read-only B2e |
| E187 | [Fresh B2d replay parity][E187] | Two independent fresh processes exactly agree; no remote economic-parity claim |
| E188 | [Existing-data B2d descriptive audit][E188] | Replica/block/SQL gaps, exact label-position balance, bytes/build/phase costs; no new gates |
| E189 | [B2d data-only verifier/replay wrapper][E189] | Exact bound-name exception only, no raw/seal/scientific code change |
| E190 | [B2d postrun completion receipt][E190] | Complete verified inconclusive result,2,219 prior hashes, zero new experiment and proposed B2e |
| E191 | [B2e replica/session source and timing report][E191] | Completed read-only audit, timer/observer/physical-state limits, conditional instrumented calibration-design GO and phased handoff |
| E192 | [B2e saved-data descriptive evidence][E192] | All rows, exact a/b plan/settings equality, preparation/observer reconciliation, repetition/block/round/position/query summaries; no inference |
| E193 | [B2e scope and input pins][E193] | Declared read-only questions/prohibitions and2,235 prior immutable hashes |
| E194 | [B2e completion/preservation receipt][E194] | Completed scoped design GO, unchanged B2d verdict and2,235 inputs, zero code/test/experiment/bootstrap/native use |
| E195 | [Frozen B2f instrumented calibration design][E195] | Exact graphs/margins, phases/gates/resources/observation/analysis and §12 read-only user inventory |
| E196 | [B2f machine-readable frozen contract][E196] | All scientific/runtime identities,16,242 calls,56 required timing intervals and ancillary caps |
| E197 | [B2f explicit prospective order][E197] | All primary/diagnostic bursts, fixture queries, physical creation order and3,392 formal/diagnostic plan-order rows; no outcomes |
| E198 | [B2f design arithmetic and balance][E198] | Exact counts, independent position/conditioner balance and crossed labels; planning consistency only, no tests/simulations |
| E199 | [B2f design freeze/preservation receipt][E199] | Documentation-only freeze,2,241 prior input hashes preserved, actual readiness/native feasibility pending |
| E200 | [B2f scope and preservation inventory][E200] | Explicit user no-code/no-experiment scope and unchanged prior inputs |
| E201 | [User Torch source-inventory transcript][E201] | October27 read-only reported paths/control-file metadata,3 graph hashes, df/myquota; normalized display transcription |
| E202 | [B2f preliminary source-inventory assessment][E202] | Exact reported hash comparisons, conservative quota arithmetic, scoped pass and pending clean-copy/native gates |
| E203 | [B2f source-inventory receipt][E203] |2,249 prior pins/frozen design preserved; no code/experiment/remote activity; next local implementation only when requested |
| E204 | [B2f source-inventory preservation and evidence][E204] | Immutable prior pins, structured assessment and documentation consistency |
| E205 | [B2f implementation and handoff report][E205] | Isolated implementation, native guard/observation/analysis details, validation limits and critical path |
| E206 | [B2f implementation receipt][E206] | Source/sealed checks, immutable package/archive identity, prior preservation and native-pending status |
| E207 | [B2f exact Mac/Torch commands][E207] | Interactive upload, one submit, reconnect-safe status, terminal collect and trusted local download analysis |
| E208 | [B2f release checks and preservation][E208] | Synthetic check records/logs, source pins, shell/archive byte verification and complete preservation inventory |
| E209 | [B2f original launcher failure verification][E209] |6-file checksum/member parity, exact job/seal/log/scheduler identity, zero-search failure and spent allocation |
| E210 | [B2f isolated launcher correction][E210] | Absolute interpreter/explicit step export, Slurm primary sources, unchanged scientific regime and separate-allocation scope |
| E211 | [B2f launcher-correction implementation receipt][E211] |88 source+88 sealed checks, immutable new release, scientific parity and2,500-file preservation |
| E212 | [Corrected B2f exact handoff commands][E212] | Clearly labelled one additional job; original binding/reservation retained; status/collect/download |
| E213 | [B2f launcher-correction release evidence][E213] | Actual shell regression, failed-archive verification, static/seal/member/scientific parity and preservation |
| E214 | [B2f metadata startup failure verification][E214] |32-member checksum/lock/identity proof, zero searches/readers, exact retained metadata/source/copies/catalogs/cleanup |
| E215 | [B2f identity restoration correction][E215] | Actual omitted file/constructor contract, exact pinned private copy, stronger real-frozen-backend tests and limits |
| E216 | [B2f metadata correction implementation receipt][E216] |101 source+101 sealed checks, new release integrity/scientific parity and2,781 prior inputs preserved |
| E217 | [Metadata-corrected exact handoff commands][E217] | Historical third attempt now consumed/failed; preserve commands, do not resubmit |
| E218 | [B2f metadata correction release evidence][E218] | Failure reconstruction, actual frozen-backend full mock fixture/replay, static/shell/archive/scientific preservation |
| E219 | [Third B2f failure verification][E219] |30 archive members/failed lock/source/copy/catalog/protection/cleanup;0 searches/2 readers |
| E220 | [B2f release-quality and memory audit][E220] | Systemic startup coverage defect, guarded schema correction, boundary matrix, resource uncertainty and revised critical path |
| E221 | [B2f identity-correction/audit receipt][E221] | Exact source correctness/static/preservation records; production release held/no new allocation |
| E222 | [B2f local audit evidence][E222] | Entry-point tests/logs, source pins, scientific parity, immutable preservation and release hold |
| E223 | [User-supplied Torch accounting configuration][E223] | Controller fields reported from login; no independent remote execution or compute-node cgroup/version/memory components |
| E224 | [B2f accounting interpretation and resource decision][E224] | Primary-source conditional cache semantics, explicit remaining gaps and prospective startup-only resource qualification outline |
| E225 | [B2f accounting-review receipt][E225] | Data/documentation only;3,115 prior files preserved,119 prior checks retained, resource release held |
| E226 | [B2f accounting-review evidence][E226] | Transcript/structured assessment/current hold/preservation/document checks; no new allocation |
| E227 | [Frozen startup-only resource design][E227] | Pre-code scope/identities/stages/caps/zero-search enforcement and conservative resource decision |
| E228 | [Startup-only implementation and handoff report][E228] | Actual startup/reader/host sampler/lifecycle/return reconstruction, coverage and limits |
| E229 | [Startup-resource implementation/release receipt][E229] | Exact source/sealed checks, native pending, archive/scientific parity and 3,123 prior files preserved |
| E230 | [Exact startup-only Mac/Torch commands][E230] | One additional one-hour, four-CPU, 32 GiB job/zero searches; upload/once submit/status/terminal collect/download |
| E231 | [Startup-resource release evidence][E231] | Pre-code freeze, local logs/checks, immutable package/archive/transport/preservation records |
| E232 | [Startup-resource verified return and decision][E232] | Complete startup/zero searches; actual cgroup limit pressure, frozen margin shortfall, next read-only memory audit |
| E233 | [Startup-resource postrun receipt][E233] | Archive/fresh sealed replay/scoped decision, preservation and no new code or experiment |
| E234 | [Startup archive/member verification][E234] | SHA256, 46 extracted members/raw hashes, trusted unchanged package and replay parity |
| E235 | [Startup resource raw campaign][E235] | Scheduler/source/SQL/lifecycle/final integrity/cleanup and full host memory trace |
| E236 | [Independent memory/phase/source metrics][E236] | 592 snapshot-load max events, 32 GiB peak, simultaneous-frame components, caveats and source hypotheses |
| E237 | [Fresh sealed startup-resource reconstruction][E237] | Complete startup, resource-margin inconclusive, no workload/calibration qualification |
| E238 | [Startup-resource postrun audit evidence][E238] | Preserved earlier roadmap, independent metrics/replay and 3,442 immutable input/document checks |
| E239 | [Snapshot-memory consumer/identity compatibility audit][E239] | One shared snapshot, allocation lifetimes, real consumer constraints and narrow remedy selection |
| E240 | [Frozen prospective identity-stream correction design][E240] | Exact per-row canonical framing/binding/buffers/semantic/local/native resource gates; no code yet |
| E241 | [Machine correction-design contract][E241] | Source/runtime/data/graph/identity pins, selected change and unchanged budgets/margins |
| E242 | [Snapshot-memory audit/design receipt][E242] | M0/M1 complete, no tests/experiments/implementation, 3,456 earlier inputs preserved |
| E243 | [Source/reference/inheritance inventory][E243] | 116 file hashes/137 static references; actual runner/producer and reviewed consumer boundary |
| E244 | [Existing-trace lifetime review][E244] | Snapshot SQL 6.485254s, retained process RSS and matrix payload calculation; no new measurements |
| E245 | [Snapshot-memory audit/freeze evidence][E245] | Pre-code design freeze, contract/source pins, prior roadmap, preservation and documentation checks |
| E246 | [Identity-stream implementation and local readiness report][E246] | Scoped exact-byte correction, original semantics, local failure corrections, test limits and M3/M4 gates |
| E247 | [Identity-stream implementation/release receipt][E247] | 155 source/155 sealed checks, static/parity/preservation, zero native activity and prepared resource handoff |
| E248 | [New isolated identity-stream harness][E248] | Component/framing/buffer/scoped binding, actual acquisition, independent provenance/replay and bounded tests |
| E249 | [Exact once-only M3 Mac/Torch commands][E249] | One1h4CPU32GiB zero-search qualification, status/terminal collect/download; no full calibration |
| E250 | [Source/sealed checks and preservation evidence][E250] | Final and initial local logs, loaded-module origins, before/after hashes and documentation checks |
| E251 | [Independent stream release verification][E251] | Manifest/archive byte parity, immutable science/helper/vendor/source pins and exact code identities |
| E252 | [Verified identity-stream resource return and decision][E252] | Native identity/startup pass, resource-margin inconclusive, descriptive comparison and next read-only audit |
| E253 | [Identity-stream postrun receipt][E253] | Archive/replay/preservation identities, frozen gate decision, zero Codex native activity and no new allocation |
| E254 | [Independent stream archive verification][E254] |48 safe regular members/raw byte equality, intact346-file seal and scheduler/host0:0 |
| E255 | [Identity-stream raw campaign][E255] | Original native identity/preflight/phases/SQL/memory/source/cleanup evidence; immutable |
| E256 | [Independent stream memory/comparison metrics][E256] | Observed RSS24.66% lower, unchanged32 GiB peak/+259 max, phase/process mappings and comparison limits |
| E257 | [Fresh trusted stream resource reconstruction][E257] | Exact parity with download-time result; startup complete, unchanged resource margin inconclusive |
| E258 | [Identity-stream postrun audit evidence][E258] | Counter-bracket attribution, analysis utilities, prior roadmap,3,947 preserved inputs and document checks |
| E259 | [Read-only snapshot working-set audit and recommendation][E259] | Actual producer/retained/final lifetimes, streamed verification, remedy no-go and separate A0 design next |
| E260 | [Working-set audit receipt][E260] | W0–W2 complete,246 source pins/3,961 preserved inputs, zero implementation/tests/new measurements/jobs |
| E261 | [Working-set source/function inventory][E261] | Actual effective code/consumer/runner/recipe hashes and reviewed function line ranges |
| E262 | [Existing-trace working-set derivations][E262] | Four verification transaction brackets, execute/iteration distinction, process/component contexts and event brackets |
| E263 | [API versus driver-command accounting review][E263] | Trace delegation gap, pinned default fetch model, no measured wire count, future finite-ledger requirement |
| E264 | [Working-set audit evidence and primary references][E264] | Input size metadata, official pinned driver/Arrow/OS references, decision/preservation/documentation evidence |
| E265 | [Frozen zero-search attribution design][E265] | Original-code checkpoint mechanism, internal ledgers, finite resource/cleanup/interpretability and later readiness gates |
| E266 | [Machine attribution-design contract][E266] | Pinned inputs/invariants,102 checkpoints, hooks, counters, limits and no-code/no-allocation boundary |
| E267 | [Frozen checkpoint catalog][E267] |102 named host/runtime/producer/constructor/verification/finalization points, source-line mapping and window semantics |
| E268 | [Frozen driver-hook catalog][E268] | Nine pinned3.3.6 roles, exact delegation/ownership/provenance and API-versus-command/protocol distinctions |
| E269 | [A0 freeze/verification receipt][E269] | Human/machine/catalog freeze hashes before implementation,246 source/3,974 prior pins unchanged, no execution |
| E270 | [A0 design evidence and references][E270] | Source pins, primary reference limits, freeze/preservation/document checks and prior roadmap |
| E271 | [A1 implementation/local-readiness report][E271] | Mechanisms, actual-path tests, fixture correction, limits and revised critical path |
| E272 | [A1 implementation verification receipt][E272] | Local gate complete; native handoff unreleased; tests/seals/preservation |
| E273 | [New isolated A1 harness][E273] |102 checkpoints, original-code monitor, nine driver hooks, ownership/ledgers/cleanup and replay |
| E274 | [A1 local checks and preserved iterations][E274] |155 baseline, source/sealed receipts, fixture failure/correction and module origins |
| E275 | [Independent A1 seal/preservation verification][E275] | Exact archive/science/helper/vendor/source pins and3,987 prior files unchanged |
| E276 | [A1 immutable local readiness manifest][E276] | Guarded local artifact; no A2 native handoff or commands |
| E277 | [A2 release review and inventory handoff][E277] | Reference/build mismatch, hold, finite source-only inventory and revised critical path |
| E278 | [A2 review verification receipt][E278] | Native release held; inventory ready; source/sealed/preservation identities |
| E279 | [Pinned image-build/reference audit][E279] | Exact config/header digest-chain and bundle pins; actual SIF execution remains pending |
| E280 | [Image-only capsule and local evidence][E280] |29source/29sealed checks,99 exact A1 reference copies; no data/job interfaces |
| E281 | [Inventory handoff/archive verification][E281] |108manifest/109regular archive members; exact SHA256/source parity;5,318 old inputs preserved |
| E282 | [Exact image-only user commands][E282] | Mac upload → one Torch login inventory → Mac download; no Slurm submit |
| E283 | [Verified image inventory and compatibility decision][E283] | Sole Python reference error, exact matches, limits and C0–C3 critical path |
| E284 | [Image inventory postrun receipt][E284] | Existing-data verification, preservation, GO correction/HOLD acquisition |
| E285 | [Original downloaded image inventory][E285] | Four raw files; no SQL/snapshot/search/job, source and literal checks only |
| E286 | [Independent inventory verification][E286] | Exact seals/raw/replay/provenance/maps/counts; no returned code execution |
| E287 | [Image inventory audit evidence][E287] | Sealed replay, preservation, verification recipe and prior roadmap/index |
| E288 | [Strict target-reference correction boundary][E288] | Explicit local/native identities, exact3.12.15 readiness and reviewed release requirements; no implementation/release yet |
| E289 | [Exact-reference correction and native compatibility handoff][E289] | Local implementation, evidence limits, emulated failure and revised critical path |
| E290 | [Correction/compatibility implementation receipt][E290] |128+128local main checks;23+23capsule checks; main held/native correctness handoff only |
| E291 | [Isolated corrected main harness][E291] | Strict image/local references, pre-restore source/mask gate and conditional finite controller |
| E292 | [Frozen native zero-DB compatibility contract][E292] | One15m2CPU4GiB source/sealed correctness job; no real DB/SQL/server/search |
| E293 | [Independent compatibility release verification][E293] |693manifest/694archive members, exact bytes/seals/checks/5,531 prior inputs; failed local Docker attempt preserved |
| E294 | [Exact native compatibility user commands][E294] | Mac upload → Torch submit/status/terminal collect → Mac download; not main A2 |
| E295 | [C2 failure diagnosis and isolated fixture correction][E295] | Missing metadata, deferred traceback, fixture preparation evidence, correction and revised gates |
| E296 | [Verified failed C2 return][E296] |13 archive members/eight locked files, exact provenance, incomplete target proof |
| E297 | [Retained scratch diagnostics and diagnosis][E297] | User-pasted missing-file evidence and23.502/25.325-second phase gaps; synthetic counters |
| E298 | [Preimplementation correction freeze][E298] | Distinct one-job allowance; unchanged15m2CPU4GiB/zero-search bounds and gates |
| E299 | [Corrected compatibility release verification][E299] |33source/33sealed and128source/128packaged-fixture main checks, identities and preservation |
| E300 | [Exact corrected compatibility commands][E300] | Distinct package/reservation; Mac upload, Torch submit/status/collect, Mac download |
| E301 | [Verified second C2 deadline and prepared-fixture correction][E301] |96passes/no errors, fixture I/O, local finalization amendment, bounds and revised path |
| E302 | [Verified second failed native return][E302] |16-member/11-lock archive, exact dependency/provenance/final integrity, events and stacks |
| E303 | [Preimplementation prepared-fixture freeze][E303] | One real build per suite, equivalent reseals, all cases/limits preserved |
| E304 | [Local watchdog amendment and preservation][E304] | Observed local cancellation stall, owned-process stop, synchronous diagnostics and rerun |
| E305 | [Prepared-fixture release verification][E305] |43source/43sealed/128source/128packaged complete guards, identities and prior preservation |
| E306 | [Actual unchanged-helper manifest equivalence][E306] | Byte-for-byte canonical manifest parity on bounded fixture; no production cache |
| E307 | [Exact prepared-fixture qualification commands][E307] | Mac upload → Torch verify/submit/status/collect → Mac download; separate qualification only |
| E308 | [Verified third compatibility timeout and budget review][E308] | 119 native passes/no recorded errors, disjoint fixture costs, retained large package and C2B design gates |
| E309 | [Third failed native return verification][E309] | 16-member/11-lock checksum/byte/job/identity/provenance/dependency/final-host proof; child/source/sealed qualification absent |
| E310 | [Third C2 postrun decision receipt][E310] | D102/v 1.53; three spent allowances, no handoff and prospective budget-only next step |
| E311 | [C2B budget correction and local release][E311] | Independent review, full accounting, unchanged main, pending native gate |
| E312 | [Independent C2B budget review][E312] | Native ledger/source evidence and 21 m decision before implementation |
| E313 | [Prospective C2B budget freeze][E313] | Full critical-path sum, limits and finite failure branch |
| E314 | [C2B exact release verification][E314] | 62+62 capsule/128+128 main checks, source/archive/preservation |
| E315 | [Current exact C2B commands][E315] | One new compatibility qualification only; all earlier allowances spent |
| E316 | [C2B decision receipt][E316] | D103/v1.54; native pending, C3/main held |
| E317 | [C2B compatibility contract][E317] | Exact target/limits/cases/main identities and zero-search scope |
| E318 | [Verified native C2B and C3 main release][E318] | Exact native completion, production transition and remaining main gates |
| E319 | [Independent native C2B return audit][E319] | 24 members/19 locks, all 128+128 cases and complete final proofs |
| E320 | [C3 production freeze][E320] | Unchanged science/code/main limits before final seal |
| E321 | [C3 production release verification][E321] | 619 files/620 members, 128 final local cases, readiness/controller/preservation |
| E322 | [Current main A2 commands][E322] | One 1h4CPU32GiB zero-search acquisition; all compatibility commands historical |
| E323 | [Native C2B/C3 decision receipt][E323] | D104/v1.55; main ready/unlaunched, resource qualification pending |
| E324 | [Main login preflight incident assessment][E324] | User-reported home guard; verified source ordering, no allocation consumed, current deficit unknown |
| E325 | [Read-only main capacity diagnostic commands][E325] | Current myquota/statvfs, state presence and top-level inode usage; no submit or cleanup |
| E326 | [Confirmed home file quota and preserving relocation][E326] |1,108-file deficit, exact scope, local checks and remaining native gates |
| E327 | [Preimplementation relocation freeze][E327] | Three failed capsule trees only, archive proof, original-path aliases and strict guards |
| E328 | [Relocation helper release verification][E328] |21 local cases, byte/metadata/recovery tests, source/seal parity and exact helper hash |
| E329 | [Current quota recovery and main continuation commands][E329] | Helper-only upload → verified preserving relocation → fresh guard → original main submit/status/collect/download |
| E330 | [Home inode recovery decision receipt][E330] | D106/v1.57; actual relocation and main launch pending |
| E331 | [Mac transfer socket correction receipt][E331] | D107/v1.58; both external helpers corrected; actual upload and main launch pending |
| E332 | [Native relocation and quota-wait assessment][E332] | User-reported preservation complete; main submission not reached; exact single recheck commands alongside receipt |
| E333 | [Main A2 postrun interpretation][E333] | Completed diagnostic, new descriptive brackets and separate inconclusive resource gate; A3 remedy contract next |
| E334 | [Main A2 independent return audit][E334] |52members/32guest+45host locks/68recipes; fresh strict replay exact parity; zero searches |
| E335 | [Main A2 closure decision receipt][E335] | D109/v1.60; main allocation spent, full B2f held, no native handoff |
| E336 | [A3 exact-vector remedy decision][E336] | Source/consumer review, alternatives, explicit internal type contract,33 guarded offline cases and separate release gates |
| E337 | [A3 pre-code design freeze][E337] | One exact binary64+integer-tag representation plus boundary adapters; no native allowance/commands released |
| E338 | [A3 offline decision receipt][E338] |33cases, source stability,756 prior files/128+128 receipts preserved; production/native target/resource gates pending |
| E339 | [A3 integration and correctness handoff][E339] | Actual producer/startup/gates, local tests, complete finite accounting and next return gates |
| E340 | [A3 pre-code integration freeze][E340] | Original128+128 plus all A3 source/sealed checks, unchanged main limits and distinct25m correctness budget |
| E341 | [A3 independent local release audit][E341] |774files/775members,65+65/56+56/128+128 checks,789 prior files preserved; native target pending |
| E342 | [A3 historical correctness commands — completed/spent][E342] | Original handoff preserved; job 21470341 collected/downloaded/verified. Do not submit again; no resource job |
| E343 | [A3 integration release decision receipt][E343] | D111/v1.62; all old allowances spent; separate exact-target correctness ready, resources/B2f held |
| E344 | [Reported A3 native completion assessment][E344] | User-pasted job21470341 COMPLETED0:0/11m44s,368cases/cleanup/zero DB reported; full native return verification pending |
| E345 | [A3 native correctness postrun interpretation][E345] | D112/v1.64; exact-target correctness verified, independent full-case/integrity/timing proof and remaining resource gate |
| E346 | [A3 independent native return audit][E346] | All 368 cases, 33 members/28 locks, exact target/module/code/guard/deadline proofs, authentic receipt consumption and 789 prior files preserved |
| E347 | [A3 native correctness closure receipt][E347] | Correctness allowance complete/spent; native target qualified, resources/memory/B2f unreleased; no new Torch command |
| E348 | [A3 startup-memory harness readiness and handoff][E348] | Actual boundary findings, bounded adapter, complete 100+100 local qualification, unchanged resource rule and remaining native gate |
| E349 | [A3 pre-code resource harness freeze][E349] | One new allocation; original one-hour/4CPU/32GiB/scans/orders/cleanup/margin and all spent allowances preserved |
| E350 | [A3 pre-code bounded metadata amendment][E350] | Actual FrozenList boundary evidence; <=16KiB exact ordinary view, immutable state and getter restored before connection |
| E351 | [A3 independent resource release audit][E351] | 983 files/984 members; all 100+100 cases, authentic proof consumption, source/strict-reference checks and 1,956 prior files preserved |
| E352 | [Initial A3 resource commands — superseded][E352] | Preserved initial artifact; login protection failed before reserve/scheduler. Do not repeat this handoff; corrected same-allowance commands are E358 |
| E353 | [A3 resource harness release decision receipt][E353] | D113/v1.65; distinct resource handoff ready/unlaunched. Actual native memory, workload, quality/performance and B2f unqualified |
| E354 | [A3 login path failure assessment][E354] | 7,297-file report; protection line141 before scheduler179/reserve184, no allocation reached |
| E355 | [A3 pre-code protection-context correction freeze][E355] | Original context/guards/code/limits/artifact retained; same unspent allowance and reservation identity |
| E356 | [A3 corrected resource handoff analysis][E356] | Cause, bounded filesystem regression, 110+110 checks, original proof scope and one-command continuation |
| E357 | [A3 corrected independent release audit][E357] | 984 files/985 members, original100 IDs and 3,035 prior files preserved; memory unqualified |
| E358 | [Historical corrected A3 resource commands — allowance spent][E358] | Job21542975_0 independently verified terminal failed; never submit/continue again |
| E359 | [A3 path-correction release decision][E359] | D114/v1.66; original login attempt unspent, corrected handoff ready, actual native memory/B2f pending |
| E360 | [Reported A3 resource terminal-failure assessment][E360] | Job21542975_0 FAILED1:0/16m35s; sampler/cleanup fail despite complete admission/epochs/scans reported; full return unverified |
| E361 | [Historical A3 failed-raw collection commands][E361] | Terminal collection/download completed and independently audited; no further command needed |
| E362 | [Reported A3 failed-resource decision receipt][E362] | D115/v1.67; allowance spent, native memory/full B2f unqualified; raw audit and specific cause pending |
| E363 | [Independent failed A3 native return audit][E363] |56members,49host/34guest locks, acquisition/source/provenance/counters verify; native outcome failed |
| E364 | [A3 resource failure analysis and next gate][E364] | Recorded28.700241GiB +4GiB exceeds32GiB; sampler/cleanup failures; offline review only |
| E365 | [A3 resource audited-failure decision][E365] | D116/v1.68;3,035prior files preserved; all allowances spent, no native handoff |
| E366 | [Offline A3 total-charge and lifecycle review][E366] | Original phase observations; no causal saving, storage patch or headroom claim |
| E367 | [Pre-code offline lifecycle freeze][E367] | Source/scope/limits/preservation pins; positive replay amendment separately frozen |
| E368 | [Independent offline lifecycle verification][E368] |142source+142code-snapshot checks,110inherited IDs and5,163prior files preserved; no native release |
| E369 | [Offline A3 review and correction report][E369] | Sampling/shutdown fixes, unchanged memory hold and next design gate |
| E370 | [Offline A3 lifecycle decision receipt][E370] | D117/v1.69; no native capsule/command, all spent allowances closed |
| E371 | [Pre-code unchanged-constructor allocation probe][E371] |64synthetic rows,196,608overlapping owned conversion bytes; arithmetic only, no native savings |
| E372 | [Prospective exact adaptive memory freeze][E372] | Three slots, per-vector full-bit roundtrip or raw64 fallback, original limits and held native gates |
| E373 | [Independent memory-component verification][E373] |94source+94snapshot cases,56old IDs and5,445prior files; compact-view allocation evidence |
| E374 | [A3 memory remedy design and limitations][E374] | Exactness/ownership/reference amendment, original consumers, native uncertainty and next integration gate |
| E375 | [A3 memory-component decision][E375] | D118/v1.70; offline component only, all spent allowances closed, no native handoff |
| E376 | [Prospective adaptive startup freeze][E376] | Source/scope/target/preservation pins saved before implementation; no native release |
| E377 | [Direct exact-SIF/OCI target references][E377] | Ten selected source/ELF files and full driver/formatter pins match; target code not executed |
| E378 | [Independent adaptive startup verification][E378] |272source+272snapshot cases,236preserved IDs/5,526prior files, unchanged limits and source lifetimes |
| E379 | [A3 offline startup integration report][E379] | Exactness, source/retention/replay guards, failure evidence and remaining target/CPU/memory gates |
| E380 | [A3 startup integration decision][E380] | D119/v1.71; all spent allowances closed, no Torch launch/command or native entitlement |
| E381 | [Prospective exact-image review freeze][E381] | Full test/reference/source/preservation pins; source unchanged, no native release |
| E382 | [A3 serial CPU-budget review][E382] | Decoder counts,16/64-row repeated timings and strict cross-hardware inference limits |
| E383 | [Isolated exact-image import diagnostics][E383] | Python/NumPy/psycopg pass; PyArrow and bootstrap SIGSEGV/hang under emulation |
| E384 | [Independent exact-image review verification][E384] |32+32kernel cases; full suite0complete,5,697prior files and all272+272local cases preserved |
| E385 | [Exact-image correctness and CPU review report][E385] | Failed environment prerequisite, kernel-only scope, CPU uncertainty and next complete gate |
| E386 | [A3 exact-image review decision][E386] | D120/v1.72; full correctness/CPU/memory held, all spent allowances closed |
| E387 | [Prospective non-emulated x86 qualification freeze][E387] | Exact source/reference/test/limit/one-shot scope and old-allowance preservation |
| E388 | [Independent native qualification release verification][E388] |128+128main/276+276A3/39+39control local checks,60CPU samples and archive/source/5,757prior-file verification |
| E389 | [Historical A3 qualification commands][E389] | Once-only handoff consumed by job 21595967; allowance spent, never repeat submit |
| E390 | [Non-emulated x86 qualification handoff report][E390] | Native guards, complete budgets/proofs, bounded CPU scope and local failure/correction evidence |
| E391 | [A3 native qualification preparation decision][E391] | D121/v1.73; one fresh unlaunched allowance, no resource/B2f release |
| E392 | [A3 native failed-return archive inventory][E392] | All 38 regular members, exact checksum/paths/content and extraction verified |
| E393 | [Independent A3 native failure verification][E393] | Main 128+128 pass, A3 165 passes/one interrupted, locks/provenance/cleanup and 5,757 prior files verified |
| E394 | [Native A3 case order and timing][E394] | Exact completed/interrupted/unstarted cases and nonoverlapping measured durations; no CPU/I/O attribution |
| E395 | [A3 native qualification failure report][E395] | Frozen source-phase cap exhausted, spent allowance, limits preserved and offline fixture-cost review next |
| E396 | [A3 native qualification postrun decision][E396] | D122/v1.74; no retry, new native command, target/CPU/memory/resource or B2f release |
| E397 | [Prospective offline fixture-cost review freeze][E397] | Complete guarded local profile, immutable source/test/reference/limit and 7,490-file preservation scope |
| E398 | [Prospective equivalent path-checker correction freeze][E398] | Frozen before code; same fresh filesystem checks/hashes and scoped restoration with no native release |
| E399 | [Complete baseline fixture-cost profile][E399] | 276 original cases; hash/path/stat/copy counts and overlapping local diagnostic function times |
| E400 | [Independent fixture-cost correction verification][E400] | 128+128 main/276+276 A3/26+26 helper, identical original operations/fresh observations and 7,490 prior files |
| E401 | [Offline A3 fixture-cost report][E401] | Source-backed correction, rejected shortcuts, diagnostic limits and outstanding native budget/storage gates |
| E402 | [A3 fixture-cost correction decision][E402] | D123/v1.75; local correction only, all spent allowances closed, no native capsule/command or B2f release |
| E403 | [Prospective native budget/storage review freeze][E403] | Exact caps, source/archive identity, source/data review and 10,076-file preservation |
| E404 | [Prospective offline staging/admission correction freeze][E404] | Safe exact materialization, quota/mount consistency, startup reserve and explicit native holds |
| E405 | [Conditional disk/inode capacity envelope][E405] | 6.87GiB/22,498 entries within unchanged guards; lifetime/margin/block-size assumptions explicit |
| E406 | [Independent budget/storage review verification][E406] |35+35units,1,602streamed members, real Mac guard rejection, all old tests/proofs/10,076files preserved |
| E407 | [A3 native budget/storage feasibility report][E407] | Full time arithmetic, storage evidence, local hold and outstanding native/retention/binding gates |
| E408 | [A3 budget/storage decision][E408] | D124/v1.76; review complete, full local replay/native release held, all spent allowances closed |
| E409 | [Prospective Mac space-preservation plan][E409] | Exact candidate scope, unchanged8GiB guard,10GiB target and complete preservation requirements |
| E410 | [Verified cleanup implementation pin][E410] | Canonical/backup/map identities; nanosecond creation correction and fresh probes before successful application |
| E411 | [Full Mac preservation and capacity audit][E411] | 173,943 full hashes/54 metadata proofs;22 COW paths, real headroom and verified recovery |
| E412 | [Mac storage preservation report][E412] | No prior path/byte deletion; retained initial failures, independent clone/recovery proofs and next local replay boundary |
| E413 | [Mac storage decision][E413] | D125/v1.77; local capacity ready, full replay pending and all native/spent-allowance gates held |
| E414 | [Original full local replay execution freeze][E414] | Existing source/checks/caps and complete staging/replay scope before execution |
| E415 | [Local supervisor portability correction freeze][E415] | Unsupported Darwin VM hook; exact owned-PID RSS guard, original memory rule/native holds unchanged |
| E416 | [Pinned existing-runtime correction freeze][E416] | Full local provenance required before staging; no dependency or original code/test changes |
| E417 | [Local permission and exit-monitor correction freeze][E417] | Durable child PID/traceback, lstat footprint, strict exit proof and owned-process telemetry/signals; all limits retained |
| E418 | [Full local staging and integrated replay verification][E418] | 930 cases/60 CPU samples,1,602 staged files, fresh full checks/lifetimes/caps and prior preservation |
| E419 | [Full local A3 staging/replay report][E419] | Retained local setup failures; exact local result and outstanding native/retention/controller gates |
| E420 | [Full local A3 replay decision][E420] | D126/v1.78; local stage/replay complete, all native release/spent-allowance gates held |
| E421 | [Offline native integration design freeze][E421] | Frozen/preserved local integration evidence; no native entitlement |
| E422 | [Disabled target adapter freeze][E422] | Frozen/preserved local integration evidence; no native entitlement |
| E423 | [Integration source/input/runtime pin][E423] | Frozen/preserved local integration evidence; no native entitlement |
| E424 | [Full offline integration verification][E424] | Frozen/preserved local integration evidence; no native entitlement |
| E425 | [Real failed-fixture capture and restoration][E425] | Frozen/preserved local integration evidence; no native entitlement |
| E426 | [Evidence-preserving COW headroom continuation][E426] | Frozen/preserved local integration evidence; no native entitlement |
| E427 | [Offline native integration report][E427] | Frozen/preserved local integration evidence; no native entitlement |
| E428 | [Offline native integration decision][E428] | D127/v1.79; offline verified, target entry/native release and all spent allowances closed |
| E429 | [Offline native release review freeze][E429] | D128/v1.80; offline only, native qualification/resource/B2f held; no grant/reuse/search |
| E430 | [Offline native release correction freeze][E430] | D128/v1.80; offline only, native qualification/resource/B2f held; no grant/reuse/search |
| E431 | [Native release source/trace findings][E431] | D128/v1.80; offline only, native qualification/resource/B2f held; no grant/reuse/search |
| E432 | [Native release local verification][E432] | D128/v1.80; offline only, native qualification/resource/B2f held; no grant/reuse/search |
| E433 | [Independent local exit/completion checks][E433] | D128/v1.80; offline only, native qualification/resource/B2f held; no grant/reuse/search |
| E434 | [Offline native release review report][E434] | D128/v1.80; offline only, native qualification/resource/B2f held; no grant/reuse/search |
| E435 | [Offline native release review decision][E435] | D128/v1.80; offline only, native qualification/resource/B2f held; no grant/reuse/search |
| E436 | [Offline authority/ownership design][E436] | D129/v1.81; offline backend verified, native handoff/production roots/allowances closed |
| E437 | [Bounded failure cleanup freeze][E437] | D129/v1.81; offline backend verified, native handoff/production roots/allowances closed |
| E438 | [Final authority/backend implementation pin][E438] | D129/v1.81; offline backend verified, native handoff/production roots/allowances closed |
| E439 | [Authority/backend verification][E439] | D129/v1.81; offline backend verified, native handoff/production roots/allowances closed |
| E440 | [Existing full replay fresh strict reconciliation][E440] | D129/v1.81; offline backend verified, native handoff/production roots/allowances closed |
| E441 | [Offline authority/ownership report][E441] | D129/v1.81; offline backend verified, native handoff/production roots/allowances closed |
| E442 | [Offline authority/ownership decision][E442] | D129/v1.81; offline backend verified, native handoff/production roots/allowances closed |
| E443 | [Native integration prospective freeze][E443] | D130/v1.82; offline verified; read-only site-check ready; actual native handoff/approval pending; no launch/search/reuse |
| E444 | [Bounded shared control-read freeze][E444] | D130/v1.82; offline verified; read-only site-check ready; actual native handoff/approval pending; no launch/search/reuse |
| E445 | [Stable-site login adapter freeze][E445] | D130/v1.82; offline verified; read-only site-check ready; actual native handoff/approval pending; no launch/search/reuse |
| E446 | [Final scientific implementation pin][E446] | D130/v1.82; offline verified; read-only site-check ready; actual native handoff/approval pending; no launch/search/reuse |
| E447 | [Complete final integrated replay][E447] | D130/v1.82; offline verified; read-only site-check ready; actual native handoff/approval pending; no launch/search/reuse |
| E448 | [Independent completion and all-check reconciliation][E448] | D130/v1.82; offline verified; read-only site-check ready; actual native handoff/approval pending; no launch/search/reuse |
| E449 | [Sealed pending qualification package][E449] | D130/v1.82; offline verified; read-only site-check ready; actual native handoff/approval pending; no launch/search/reuse |
| E450 | [Native integration release report][E450] | D130/v1.82; offline verified; read-only site-check ready; actual native handoff/approval pending; no launch/search/reuse |
| E451 | [Native integration decision][E451] | D130/v1.82; offline verified; read-only site-check ready; actual native handoff/approval pending; no launch/search/reuse |
| E452 | [Zero-allocation Torch site check][E452] | D130/v1.82; offline verified; read-only site-check ready; actual native handoff/approval pending; no launch/search/reuse |
| E453 | [Exact qualification commands pending authorization][E453] | D130/v1.82; offline verified; read-only site-check ready; actual native handoff/approval pending; no launch/search/reuse |
| E454 | [Exact site-prefix compatibility freeze][E454] | D131/v1.83; offline verified; live site/account output and distinct allocation approval pending; no launch/search/reuse |
| E455 | [Actual live layout and account observations][E455] | D131/v1.83; offline verified; live site/account output and distinct allocation approval pending; no launch/search/reuse |
| E456 | [Final site compatibility implementation pin][E456] | D131/v1.83; offline verified; live site/account output and distinct allocation approval pending; no launch/search/reuse |
| E457 | [Site compatibility local verification][E457] | D131/v1.83; offline verified; live site/account output and distinct allocation approval pending; no launch/search/reuse |
| E458 | [All prior preservation and exact science reconciliation][E458] | D131/v1.83; offline verified; live site/account output and distinct allocation approval pending; no launch/search/reuse |
| E459 | [Replacement immutable pending package][E459] | D131/v1.83; offline verified; live site/account output and distinct allocation approval pending; no launch/search/reuse |
| E460 | [Site compatibility report][E460] | D131/v1.83; offline verified; live site/account output and distinct allocation approval pending; no launch/search/reuse |
| E461 | [Read-only Torch site/account command][E461] | D131/v1.83; offline verified; live site/account output and distinct allocation approval pending; no launch/search/reuse |
| E462 | [User-returned read-only site/account evidence][E462] | D132/v1.84; reported site readiness reviewed; distinct new allocation approval remains unissued; no launch/search/reuse |
| E463 | [Live site/project/partition review][E463] | D132/v1.84; reported site readiness reviewed; distinct new allocation approval remains unissued; no launch/search/reuse |
| E464 | [Concrete approval/submission proposal pending explicit authorization][E464] | D132/v1.84; reported site readiness reviewed; distinct new allocation approval remains unissued; no launch/search/reuse |
| E465 | [Live site readiness decision][E465] | D132/v1.84; reported site readiness reviewed; distinct new allocation approval remains unissued; no launch/search/reuse |
| E466 | [Actual new qualification submission receipt][E466] | D133/v1.85; one distinct allowance committed to21756110; native state/outcome pending; no retry or old allowance reuse |
| E467 | [New committed allowance and dispatch review][E467] | D133/v1.85; one distinct allowance committed to21756110; native state/outcome pending; no retry or old allowance reuse |
| E468 | [Read-only job21756110 status command][E468] | D133/v1.85; one distinct allowance committed to21756110; native state/outcome pending; no retry or old allowance reuse |
| E469 | [Native qualification submitted decision][E469] | D133/v1.85; one distinct allowance committed to21756110; native state/outcome pending; no retry or old allowance reuse |
| E470 | [Reported terminal preflight failure21756110][E470] | D134/v1.86;21756110 FAILED and spent; raw review pending; no retry/new allowance or qualification |
| E471 | [Initial source review without speculative correction][E471] | D134/v1.86;21756110 FAILED and spent; raw review pending; no retry/new allowance or qualification |
| E472 | [Exact terminal collection and traceback command][E472] | D134/v1.86;21756110 FAILED and spent; raw review pending; no retry/new allowance or qualification |
| E473 | [Failed native allowance closure decision][E473] | D134/v1.86;21756110 FAILED and spent; raw review pending; no retry/new allowance or qualification |
| E474 | [Exact SLURM_CONF traceback role finding][E474] | D135/v1.87; configuration role identified, actual path/raw pending; no code/limit/new allowance/retry |
| E475 | [Pinned-key spent-job return download helper][E475] | D135/v1.87; configuration role identified, actual path/raw pending; no code/limit/new allowance/retry |
| E476 | [Allocated configuration failure-role decision][E476] | D135/v1.87; configuration role identified, actual path/raw pending; no code/limit/new allowance/retry |
| E477 | [Verified complete failed return][E477] | D136/v1.88; full raw verified, runtime configuration metadata unknown; no correction/new allocation/retry |
| E478 | [Read-only configuration metadata command][E478] | D136/v1.88; full raw verified, runtime configuration metadata unknown; no correction/new allocation/retry |
| E479 | [Unchanged package/source and strict checks][E479] | D136/v1.88; full raw verified, runtime configuration metadata unknown; no correction/new allocation/retry |
| E480 | [Failed return review decision][E480] | D136/v1.88; full raw verified, runtime configuration metadata unknown; no correction/new allocation/retry |
| E481 | [User-returned unavailable configuration metadata][E481] | D137/v1.89; site metadata pending, no code/limit/new allowance/retry or message sent |
| E482 | [Configuration provenance finding][E482] | D137/v1.89; site metadata pending, no code/limit/new allowance/retry or message sent |
| E483 | [Unsent NYU HPC evidence request][E483] | D137/v1.89; site metadata pending, no code/limit/new allowance/retry or message sent |
| E484 | [Configuration metadata dependency decision][E484] | D137/v1.89; site metadata pending, no code/limit/new allowance/retry or message sent |
| E485 | [Pinned client configuration alternative freeze][E485] | D138/v1.90; alternate design frozen, capture/dependencies/portability pending; no implementation or allowance |
| E486 | [Independent matching-version source and alternative review][E486] | D138/v1.90; alternate design frozen, capture/dependencies/portability pending; no implementation or allowance |
| E487 | [Alternate design preservation check][E487] | D138/v1.90; alternate design frozen, capture/dependencies/portability pending; no implementation or allowance |
| E488 | [Alternate design decision][E488] | D138/v1.90; alternate design frozen, capture/dependencies/portability pending; no implementation or allowance |
| E489 | [Capture specification freeze][E489] | D139/v1.91; login command locally verified, actual capture pending; no job/grant/search |
| E490 | [Final64capture checks and exact command binding][E490] | D139/v1.91; login command locally verified, actual capture pending; no job/grant/search |
| E491 | [Capture-stage original science/reference preservation][E491] | D139/v1.91; login command locally verified, actual capture pending; no job/grant/search |
| E492 | [Ready login-only configuration capture command][E492] | D139/v1.91; login command locally verified, actual capture pending; no job/grant/search |
| E493 | [User-reported successful current capture receipt][E493] | D140/v1.92; capture reported, local full download/review pending; no grant/search/native job |
| E494 | [Reported capture finding and next dependency gates][E494] | D140/v1.92; capture reported, local full download/review pending; no grant/search/native job |
| E495 | [Pinned-key exact capture download command][E495] | D140/v1.92; capture reported, local full download/review pending; no grant/search/native job |
| E496 | [Fourteen local retrieval checks][E496] | D140/v1.92; capture reported, local full download/review pending; no grant/search/native job |
| E497 | [Actual capture independent raw verification][E497] | D141/v1.93; actual snapshot reviewed, scoped use frozen; dependency/native compatibility gates open, no job/grant/search |
| E498 | [Complete captured configuration inventory][E498] | D141/v1.93; actual snapshot reviewed, scoped use frozen; dependency/native compatibility gates open, no job/grant/search |
| E499 | [Pinned release-source dependency review][E499] | D141/v1.93; actual snapshot reviewed, scoped use frozen; dependency/native compatibility gates open, no job/grant/search |
| E500 | [Captured configuration use freeze before adapter implementation][E500] | D141/v1.93; actual snapshot reviewed, scoped use frozen; dependency/native compatibility gates open, no job/grant/search |
| E501 | [Captured configuration review decision][E501] | D141/v1.93; actual snapshot reviewed, scoped use frozen; dependency/native compatibility gates open, no job/grant/search |
| E502 | [Harness freeze][E502] | D142/v1.94; local harness pass, installed/native gate held; no Torch/grant/search |
| E503 | [Implementation and independent snapshot pin][E503] | D142/v1.94; local harness pass, installed/native gate held; no Torch/grant/search |
| E504 | [326 final local compatibility checks][E504] | D142/v1.94; local harness pass, installed/native gate held; no Torch/grant/search |
| E505 | [Fresh prior preservation and strict semantic verification][E505] | D142/v1.94; local harness pass, installed/native gate held; no Torch/grant/search |
| E506 | [Offline compatibility harness decision][E506] | D142/v1.94; local harness pass, installed/native gate held; no Torch/grant/search |
| E507 | [Login dependency command freeze][E507] | D143/v1.95; user metadata inspection ready, native gates held; no actual connection/job/grant/search |
| E508 | [29 source and 29 snapshot command checks][E508] | D143/v1.95; user metadata inspection ready, native gates held; no actual connection/job/grant/search |
| E509 | [Unchanged harness/science/strict semantic preservation][E509] | D143/v1.95; user metadata inspection ready, native gates held; no actual connection/job/grant/search |
| E510 | [Pinned-key user Mac upload command][E510] | D143/v1.95; user metadata inspection ready, native gates held; no actual connection/job/grant/search |
| E511 | [Exact user Torch login-only inspection command][E511] | D143/v1.95; user metadata inspection ready, native gates held; no actual connection/job/grant/search |
| E512 | [Login-only dependency command release decision][E512] | D143/v1.95; user metadata inspection ready, native gates held; no actual connection/job/grant/search |
| E513 | [Upload failure and frozen direct-SFTP correction][E513] | D144/v1.96; transfer-only correction, no actual network/job/search; native gates held |
| E514 | [14 source and 14 snapshot SFTP correction checks][E514] | D144/v1.96; transfer-only correction, no actual network/job/search; native gates held |
| E515 | [Preserved old tests/code/failed receipt and strict references][E515] | D144/v1.96; transfer-only correction, no actual network/job/search; native gates held |
| E516 | [Replacement one-connection SFTP Mac command][E516] | D144/v1.96; transfer-only correction, no actual network/job/search; native gates held |
| E517 | [Direct SFTP correction decision][E517] | D144/v1.96; transfer-only correction, no actual network/job/search; native gates held |
| E518 | [Login timeout cost review and correction freeze][E518] | D145/v1.97; local corrected preflight pass, native/runtime gates held; no Torch/job/search |
| E519 | [424 local source/snapshot checks][E519] | D145/v1.97; local corrected preflight pass, native/runtime gates held; no Torch/job/search |
| E520 | [Exact original target one-pass verification and quota proof][E520] | D145/v1.97; local corrected preflight pass, native/runtime gates held; no Torch/job/search |
| E521 | [Cost-corrected user Mac upload][E521] | D145/v1.97; local corrected preflight pass, native/runtime gates held; no Torch/job/search |
| E522 | [New pinned user login-only inspection block][E522] | D145/v1.97; local corrected preflight pass, native/runtime gates held; no Torch/job/search |
| E523 | [Login verification cost correction decision][E523] | D145/v1.97; local corrected preflight pass, native/runtime gates held; no Torch/job/search |
| E524 | [User-reported completed metadata capture][E524] | D146/v1.98; metadata capture reported complete, raw review pending; no new job/search/grant |
| E525 | [Frozen exact dependency-evidence download][E525] | D146/v1.98; metadata capture reported complete, raw review pending; no new job/search/grant |
| E526 | [27 source and 27 snapshot retrieval checks][E526] | D146/v1.98; metadata capture reported complete, raw review pending; no new job/search/grant |
| E527 | [User Mac exact evidence download][E527] | D146/v1.98; metadata capture reported complete, raw review pending; no new job/search/grant |
| E528 | [Reported metadata completion and retrieval decision][E528] | D146/v1.98; metadata capture reported complete, raw review pending; no new job/search/grant |
| E529 | [Actual dependency return independent raw verification][E529] | D147/v1.99; actual metadata reviewed, corrected capture locally ready, native gate held |
| E530 | [Complete metadata/component/alias review][E530] | D147/v1.99; actual metadata reviewed, corrected capture locally ready, native gate held |
| E531 | [Frozen observed-RPATH candidate correction][E531] | D147/v1.99; actual metadata reviewed, corrected capture locally ready, native gate held |
| E532 | [436 local checks and preservation][E532] | D147/v1.99; actual metadata reviewed, corrected capture locally ready, native gate held |
| E533 | [New strict metadata upload command][E533] | D147/v1.99; actual metadata reviewed, corrected capture locally ready, native gate held |
| E534 | [Actual dependency review and correction decision][E534] | D147/v1.99; actual metadata reviewed, corrected capture locally ready, native gate held |






[E1]: ../agent/docs/verification/selective-agent-v1-pilot-postrun.json
[E2]: ../trials/torch-reviews-selective-agent-v1/runs/20261022T192817Z-66ed81d6/measurements/pilot/report.txt
[E3]: ../agent/docs/verification/selective-agent-v1-implementation.json
[E4]: ../trials/torch-reviews-results/reviews-frozen-proposals-timing-v1-runtime-fix-confirmation-20261021T160807Z.n5yrz2mk-analysis/report.txt
[E5]: ../trials/torch-reviews-results/offline-first-stop-fitter-v1-20261022/report.txt
[E6]: ../trials/torch-reviews-results/reviews-feature-data-ablation-v1-20261022T154122Z.duo0d70y-analysis/report.txt
[E7]: ../agent/experiments/selective-agent-v1/README.md
[E8]: ../agent/docs/OFFLINE_LEARNING.md
[E9]: ../agent/docs/agent-design.md
[E10]: ../agent/docs/experiments/README.md
[E11]: ../agent/docs/verification/execution-cost-attribution-v1-postrun.json
[E12]: fannagent-execution-cost-attribution-v1-results-2026-10-23.md
[E13]: ../trials/torch-reviews-execution-cost-attribution-v1/analysis-local/reviews-execution-cost-v1-20261023T044408Z.a08qpwdi/report.txt
[E14]: ../trials/torch-reviews-execution-cost-attribution-v1/analysis-local/reviews-execution-cost-v1-20261023T044408Z.a08qpwdi/attribution.md
[E15]: ../trials/torch-reviews-execution-cost-attribution-v1/analysis-local/reviews-execution-cost-v1-20261023T044408Z.a08qpwdi/performance.json
[E16]: ../trials/torch-reviews-execution-cost-attribution-v1/analysis-local/reviews-execution-cost-v1-20261023T044408Z.a08qpwdi/verification.json
[E17]: ../agent/docs/verification/prepared-policy-lifecycle-v1-implementation.json
[E18]: ../agent/experiments/prepared-policy-lifecycle-v1/README.md
[E19]: ../agent/experiments/prepared-policy-lifecycle-v1/DESIGN.md
[E20]: ../trials/torch-reviews-prepared-policy-lifecycle-v1/COMMANDS.txt
[E21]: ../agent/docs/verification/prepared-policy-lifecycle-v1-postrun.json
[E22]: fannagent-prepared-policy-lifecycle-v1-results-2026-10-23.md
[E23]: ../trials/torch-reviews-prepared-policy-lifecycle-v1/analysis-local/reviews-prepared-policy-v1-20261023T161756Z.8uq_covr/report.txt
[E24]: ../trials/torch-reviews-prepared-policy-lifecycle-v1/analysis-local/reviews-prepared-policy-v1-20261023T161756Z.8uq_covr/performance.json
[E25]: ../trials/torch-reviews-prepared-policy-lifecycle-v1/analysis-local/reviews-prepared-policy-v1-20261023T161756Z.8uq_covr/verification.json
[E26]: ../trials/torch-reviews-prepared-policy-lifecycle-v1/analysis-local/reviews-prepared-policy-v1-20261023T161756Z.8uq_covr/attribution.md

[E27]: ../agent/docs/verification/admission-profile-identity-v1-implementation.json
[E28]: ../agent/experiments/admission-profile-identity-v1/README.md
[E29]: ../agent/experiments/admission-profile-identity-v1/DESIGN.md
[E30]: ../agent/experiments/admission-profile-identity-v1/PRECISION.md
[E31]: ../trials/torch-reviews-admission-profile-identity-v1/COMMANDS.txt
[E32]: ../trials/torch-reviews-admission-profile-identity-v1/transfer.sh
[E33]: ../agent/docs/verification/admission-profile-identity-v1-torch-status.json
[E34]: ../agent/docs/verification/admission-profile-identity-v1-postrun.json
[E35]: fannagent-admission-profile-identity-v1-results-2026-10-23.md
[E36]: ../trials/torch-reviews-admission-profile-identity-v1/analysis-review/reviews-admission-profile-v1-20261023T193304Z.a2mfz4a0/report.txt
[E37]: ../trials/torch-reviews-admission-profile-identity-v1/analysis-review/reviews-admission-profile-v1-20261023T193304Z.a2mfz4a0/performance.json
[E38]: ../trials/torch-reviews-admission-profile-identity-v1/analysis-review/reviews-admission-profile-v1-20261023T193304Z.a2mfz4a0/verification.json
[E39]: ../trials/torch-reviews-admission-profile-identity-v1/analysis-review/reviews-admission-profile-v1-20261023T193304Z.a2mfz4a0/attribution.md
[E40]: fannagent-admission-profile-identity-v1-order-audit-2026-10-23.json

[E41]: ../agent/docs/verification/activation-timing-calibration-v1-implementation.json
[E42]: ../agent/experiments/activation-timing-calibration-v1/README.md
[E43]: ../agent/experiments/activation-timing-calibration-v1/DESIGN.md
[E44]: ../trials/torch-reviews-activation-timing-calibration-v1/COMMANDS.txt
[E45]: ../trials/torch-reviews-activation-timing-calibration-v1/transfer.sh
[E46]: ../agent/docs/verification/activation-timing-calibration-v1-postrun.json
[E47]: fannagent-activation-timing-calibration-v1-results-2026-10-24.md
[E48]: ../trials/torch-reviews-activation-timing-calibration-v1/analysis-review/reviews-activation-calibration-v1-20261024T025706Z.c8557262/report.txt
[E49]: ../trials/torch-reviews-activation-timing-calibration-v1/analysis-review/reviews-activation-calibration-v1-20261024T025706Z.c8557262/performance.json
[E50]: ../trials/torch-reviews-activation-timing-calibration-v1/analysis-review/reviews-activation-calibration-v1-20261024T025706Z.c8557262/verification.json
[E51]: ../trials/torch-reviews-activation-timing-calibration-v1/analysis-review/reviews-activation-calibration-v1-20261024T025706Z.c8557262/calibration.md
[E52]: fannagent-p3a-evidence-audit-2026-10-24/contract.json
[E53]: fannagent-p3a-evidence-audit-2026-10-24/audit.json
[E54]: fannagent-p3a-evidence-audit-2026-10-24.md
[E55]: ../agent/docs/verification/p3a-evidence-audit-v1.json
[E56]: fannagent-p3a-evidence-audit-2026-10-24/audit.py
[E57]: fannagent-p3a-evidence-audit-2026-10-24/coverage.csv
[E58]: fannagent-p3a-evidence-audit-2026-10-24/feature-diagnostics.json
[E59]: fannagent-p3a-evidence-audit-2026-10-24/coverage-summary.json
[E60]: ../agent/experiments/grouped-stop-modeling-v1/contract.json
[E61]: ../agent/docs/verification/grouped-stop-modeling-v1-postrun.json
[E62]: fannagent-p3b-grouped-modeling-v1-results-2026-10-24.md
[E63]: ../trials/torch-reviews-grouped-stop-modeling-v1/runs/p3b-20261024-local-v1/performance.json
[E64]: ../trials/torch-reviews-grouped-stop-modeling-v1/runs/p3b-20261024-local-v1/verification-replay.json
[E65]: fannagent-p3b-grouped-modeling-2026-10-24/analysis.json
[E66]: ../trials/torch-reviews-grouped-stop-modeling-v1/local-checks.json
[E67]: ../trials/torch-reviews-grouped-stop-modeling-v1/preflight-repair.json
[E68]: ../agent/experiments/risk-separated-stop-modeling-v1/contract.json
[E69]: ../agent/docs/verification/risk-separated-stop-modeling-v1-postrun.json
[E70]: fannagent-p3c-risk-separated-modeling-v1-results-2026-10-24.md
[E71]: ../trials/torch-reviews-risk-separated-stop-modeling-v1/runs/p3c-20261024-local-v1/performance.json
[E72]: ../trials/torch-reviews-risk-separated-stop-modeling-v1/runs/p3c-20261024-local-v1/verification-replay.json
[E73]: fannagent-p3c-risk-separated-modeling-2026-10-24/analysis.json
[E74]: ../trials/torch-reviews-risk-separated-stop-modeling-v1/local-checks.json
[E75]: ../agent/experiments/risk-separated-stop-modeling-v1/README.md
[E76]: fannagent-b1a-search-effort-audit-2026-10-24.md
[E77]: ../agent/docs/verification/b1a-search-effort-audit-v1.json
[E78]: fannagent-b1a-search-effort-audit-2026-10-24/input-and-source-inventory.json
[E79]: ../trials/torch-reviews-results/analysis-reviews-ef-sweep-20261019T004327Z.dcFzo0/report.txt
[E80]: ../trials/torch-reviews-results/analysis-reviews-ef-sweep-20261019T004327Z.dcFzo0/verification.json
[E81]: ../trials/torch-reviews-results/analysis-reviews-ef-sweep-20261019T004327Z.dcFzo0/analysis.json
[E82]: ../trials/torch-reviews-activation-timing-calibration-v1/torch-activation-timing-calibration-v1/frozen/source-index.json
[E83]: fannagent-b1a-search-effort-audit-2026-10-24/audit.json
[E84]: ../agent/experiments/native-effort-frontier-v1/DESIGN.md
[E85]: ../agent/experiments/native-effort-frontier-v1/README.md
[E86]: ../agent/docs/verification/native-effort-frontier-v1-implementation.json
[E87]: ../trials/torch-reviews-native-effort-frontier-v1/COMMANDS.txt
[E88]: ../trials/torch-reviews-native-effort-frontier-v1/torch-native-effort-frontier-v1/manifest.json
[E89]: ../trials/torch-reviews-native-effort-frontier-v1/local-checks/
[E90]: ../agent/docs/verification/native-effort-frontier-v1-postrun.json
[E91]: fannagent-native-effort-frontier-v1-results-2026-10-25.md
[E92]: ../trials/torch-reviews-native-effort-frontier-v1/analysis-review/reviews-native-effort-v1-20261025T014743Z.p_kspq5v/performance.json
[E93]: ../trials/torch-reviews-native-effort-frontier-v1/analysis-review/reviews-native-effort-v1-20261025T014743Z.p_kspq5v/verification.json
[E94]: ../agent/experiments/native-effort-frontier-v1/recover_campaign_identity.py
[E95]: ../trials/torch-reviews-native-effort-frontier-v1/analysis-review/reviews-native-effort-v1-20261025T014743Z.p_kspq5v/descriptive-analysis.json

[E96]: fannagent-effort-interface-review-2026-10-25.md
[E97]: fannagent-native-effort-midpoint-v1-design-2026-10-25.md
[E98]: fannagent-effort-interface-review-2026-10-25/audit.json
[E99]: fannagent-effort-interface-review-2026-10-25/input-inventory.json
[E100]: ../agent/docs/verification/effort-interface-review-v1.json
[E101]: fannagent-effort-interface-review-2026-10-25/documentation-review.json

[E102]: ../agent/experiments/native-effort-midpoint-v1/README.md
[E103]: ../agent/docs/verification/native-effort-midpoint-v1-implementation.json
[E104]: ../trials/torch-reviews-native-effort-midpoint-v1/torch-native-effort-midpoint-v1/manifest.json
[E105]: ../trials/torch-reviews-native-effort-midpoint-v1/COMMANDS.txt
[E106]: ../trials/torch-reviews-native-effort-midpoint-v1/local-checks/

[E107]: ../agent/docs/verification/native-effort-midpoint-v1-postrun.json
[E108]: fannagent-native-effort-midpoint-v1-results-2026-10-25.md
[E109]: ../trials/torch-reviews-native-effort-midpoint-v1/analysis-review/reviews-native-midpoint-v1-20261025T172357Z.ybpfkkki/replay/performance.json
[E110]: ../trials/torch-reviews-native-effort-midpoint-v1/analysis-review/reviews-native-midpoint-v1-20261025T172357Z.ybpfkkki/verification.json
[E111]: ../trials/torch-reviews-native-effort-midpoint-v1/analysis-review/reviews-native-midpoint-v1-20261025T172357Z.ybpfkkki/descriptive.json
[E112]: ../trials/torch-reviews-native-effort-midpoint-v1/analysis-review/reviews-native-midpoint-v1-20261025T172357Z.ybpfkkki/input-inventory.json
[E113]: ../trials/torch-reviews-native-effort-midpoint-v1/analysis-review/reviews-native-midpoint-v1-20261025T172357Z.ybpfkkki/archive-preservation.json
[E114]: ../trials/torch-reviews-native-effort-midpoint-v1/analysis-review/reviews-native-midpoint-v1-20261025T172357Z.ybpfkkki/documentation-checks.json

[E115]: fannagent-b2a-plan-scope-audit-2026-10-25.md
[E116]: fannagent-b2a-plan-scope-audit-2026-10-25/audit.json
[E117]: fannagent-b2a-plan-scope-audit-2026-10-25/input-and-source-inventory.json
[E118]: ../agent/docs/verification/b2a-plan-scope-audit-v1.json
[E119]: fannagent-b2a-plan-scope-audit-2026-10-25/documentation-checks.json

[E120]: fannagent-exact-topk-v1-design-2026-10-25.md
[E121]: ../agent/experiments/exact-topk-v1/README.md
[E122]: ../agent/docs/verification/exact-topk-v1-implementation.json
[E123]: ../trials/torch-reviews-exact-topk-v1/torch-exact-topk-v1/manifest.json
[E124]: ../trials/torch-reviews-exact-topk-v1/COMMANDS.txt
[E125]: ../trials/torch-reviews-exact-topk-v1/local-checks/

[E126]: ../agent/docs/verification/exact-topk-v1-torch-failure-2026-10-26.json
[E127]: fannagent-exact-topk-v1-catalog-failure-2026-10-26.md
[E128]: fannagent-exact-topk-v1-catalog-fix-design-2026-10-26.md
[E129]: ../agent/docs/verification/exact-topk-v1-catalog-fix-implementation.json
[E130]: ../trials/torch-reviews-exact-topk-v1-catalog-fix/local-checks/
[E131]: ../trials/torch-reviews-exact-topk-v1-catalog-fix/RECOVER-FAILED-V1.txt
[E132]: ../trials/torch-reviews-exact-topk-v1-catalog-fix/torch-exact-topk-v1-catalog-fix/manifest.json
[E133]: ../agent/experiments/exact-topk-v1-catalog-fix/README.md

[E134]: ../trials/torch-reviews-exact-topk-v1-catalog-fix/failed-v1-verification-2026-10-26/verification.json
[E135]: ../agent/docs/verification/exact-topk-v1-failure-postrun.json
[E136]: ../trials/torch-reviews-exact-topk-v1-catalog-fix/RUN-CORRECTED.txt
[E137]: fannagent-exact-topk-v1-failure-verification-2026-10-26.md

[E138]: ../agent/docs/verification/exact-topk-v1-catalog-fix-deadline-status-2026-10-26.json
[E139]: ../trials/torch-reviews-exact-topk-v1-catalog-fix/deadline-stop-2026-10-26/COLLECT-ONLY.txt
[E140]: ../trials/torch-reviews-exact-topk-v1-catalog-fix/deadline-stop-2026-10-26/INTERPRETATION.md
[E141]: ../trials/torch-reviews-exact-topk-v1-catalog-fix/deadline-stop-2026-10-26/

[E142]: ../trials/torch-reviews-exact-topk-v1-catalog-fix/partial-review-2026-10-26/analysis.json
[E143]: ../agent/docs/verification/exact-topk-v1-catalog-fix-partial-postrun.json
[E144]: fannagent-exact-topk-v1-catalog-fix-partial-results-2026-10-26.md
[E145]: ../trials/torch-reviews-exact-topk-v1-catalog-fix/partial-review-2026-10-26/analyze_partial.py
[E146]: ../trials/torch-reviews-exact-topk-v1-catalog-fix/partial-review-2026-10-26/
[E147]: fannagent-b2c-ann-alternatives-audit-2026-10-26.md
[E148]: fannagent-b2c-ann-alternatives-audit-2026-10-26/audit.json
[E149]: fannagent-b2c-ann-alternatives-audit-2026-10-26/input-and-source-inventory.json
[E150]: fannagent-partial-ann-v1-design-2026-10-26.md
[E151]: ../agent/docs/verification/b2c-ann-alternatives-audit-v1.json
[E152]: fannagent-b2c-ann-alternatives-audit-2026-10-26/documentation-checks.json
[E153]: fannagent-partial-ann-v1-implementation-addendum-2026-10-26.md
[E154]: ../agent/experiments/partial-ann-v1/
[E155]: fannagent-partial-ann-v1-implementation-2026-10-26.md
[E156]: ../trials/torch-reviews-partial-ann-v1/
[E157]: ../trials/torch-reviews-partial-ann-v1/torch-partial-ann-v1/manifest.json
[E158]: ../trials/torch-reviews-partial-ann-v1/COMMANDS.txt
[E159]: ../agent/docs/verification/partial-ann-v1-implementation.json
[E160]: ../trials/torch-reviews-partial-ann-v1/preservation-before.json
[E161]: fannagent-partial-ann-v1-quota-fix-2026-10-26.md
[E162]: ../agent/experiments/partial-ann-v1-quota-fix/
[E163]: ../trials/torch-reviews-partial-ann-v1-quota-fix/
[E164]: ../agent/docs/verification/partial-ann-v1-quota-fix.json
[E165]: ../trials/torch-reviews-partial-ann-v1-quota-fix/COMMANDS.txt
[E166]: ../trials/torch-reviews-partial-ann-v1-quota-fix/submission-preflight-output.txt
[E167]: ../trials/torch-reviews-partial-ann-v1-quota-fix/native-failure-2026-10-26/user-submission-status.txt
[E168]: ../trials/torch-reviews-partial-ann-v1-quota-fix/native-failure-2026-10-26/COLLECT-ONLY.txt
[E169]: ../trials/torch-reviews-partial-ann-v1-quota-fix/native-failure-2026-10-26/INTERPRETATION.md
[E170]: ../agent/docs/verification/partial-ann-v1-quota-fix-native-failure-2026-10-26.json
[E171]: ../trials/torch-reviews-partial-ann-v1-quota-fix/failure-review-2026-10-26/analysis.json
[E172]: ../agent/docs/verification/partial-ann-v1-quota-fix-failure-postrun.json
[E173]: fannagent-partial-ann-v1-settings-fix-design-2026-10-26.md
[E174]: ../agent/experiments/partial-ann-v1-settings-fix/
[E175]: fannagent-partial-ann-v1-settings-fix-2026-10-26.md
[E176]: ../trials/torch-reviews-partial-ann-v1-settings-fix/
[E177]: ../trials/torch-reviews-partial-ann-v1-settings-fix/torch-partial-ann-v1-settings-fix/manifest.json
[E178]: ../trials/torch-reviews-partial-ann-v1-settings-fix/COMMANDS.txt
[E179]: ../agent/docs/verification/partial-ann-v1-settings-fix-implementation.json
[E180]: ../trials/torch-reviews-partial-ann-v1-settings-fix/collection-recovery-2026-10-26/status.json
[E181]: ../trials/torch-reviews-partial-ann-v1-settings-fix/collection-recovery-2026-10-26/COMMANDS.txt
[E182]: ../trials/torch-reviews-partial-ann-v1-settings-fix/collection-recovery-2026-10-26/
[E183]: ../agent/docs/verification/partial-ann-v1-settings-fix-completion-status-2026-10-26.json
[E184]: ../trials/torch-reviews-partial-ann-v1-settings-fix/postrun-review-2026-10-26/replay-1/verification.json
[E185]: ../trials/torch-reviews-partial-ann-v1-settings-fix/postrun-review-2026-10-26/replay-1/performance.json
[E186]: fannagent-partial-ann-v1-settings-fix-results-2026-10-26.md
[E187]: ../trials/torch-reviews-partial-ann-v1-settings-fix/postrun-review-2026-10-26/parity.json
[E188]: ../trials/torch-reviews-partial-ann-v1-settings-fix/postrun-review-2026-10-26/descriptive.json
[E189]: ../trials/torch-reviews-partial-ann-v1-settings-fix/postrun-review-2026-10-26/verify_and_replay.py
[E190]: ../agent/docs/verification/partial-ann-v1-settings-fix-postrun.json
[E191]: fannagent-b2e-replica-session-audit-2026-10-26.md
[E192]: ../trials/torch-reviews-partial-ann-v1-settings-fix/b2e-audit-2026-10-26/analysis.json
[E193]: ../trials/torch-reviews-partial-ann-v1-settings-fix/b2e-audit-2026-10-26/
[E194]: ../agent/docs/verification/b2e-replica-session-audit-v1.json
[E195]: fannagent-partial-calibration-v1-design-2026-10-26.md
[E196]: ../trials/torch-reviews-partial-ann-v1-settings-fix/b2f-design-2026-10-26/contract.json
[E197]: ../trials/torch-reviews-partial-ann-v1-settings-fix/b2f-design-2026-10-26/schedule.json
[E198]: ../trials/torch-reviews-partial-ann-v1-settings-fix/b2f-design-2026-10-26/plan-accounting.json
[E199]: ../agent/docs/verification/partial-calibration-v1-design-freeze.json
[E200]: ../trials/torch-reviews-partial-ann-v1-settings-fix/b2f-design-2026-10-26/
[E201]: ../trials/torch-reviews-partial-ann-v1-settings-fix/b2f-source-inventory-2026-10-27/user-output.txt
[E202]: ../trials/torch-reviews-partial-ann-v1-settings-fix/b2f-source-inventory-2026-10-27/review.md
[E203]: ../agent/docs/verification/partial-calibration-v1-source-inventory-2026-10-27.json
[E204]: ../trials/torch-reviews-partial-ann-v1-settings-fix/b2f-source-inventory-2026-10-27/
[E205]: fannagent-partial-calibration-v1-implementation-2026-10-27.md
[E206]: ../agent/docs/verification/partial-calibration-v1-implementation.json
[E207]: ../trials/torch-reviews-partial-calibration-v1/COMMANDS.txt
[E208]: ../trials/torch-reviews-partial-calibration-v1/
[E209]: ../trials/torch-reviews-partial-calibration-v1-launch-fix/failed-archive-verification.json
[E210]: fannagent-partial-calibration-v1-launch-fix-2026-10-27.md
[E211]: ../agent/docs/verification/partial-calibration-v1-launch-fix-implementation.json
[E212]: ../trials/torch-reviews-partial-calibration-v1-launch-fix/COMMANDS.txt
[E213]: ../trials/torch-reviews-partial-calibration-v1-launch-fix/
[E214]: ../trials/torch-reviews-partial-calibration-v1-metadata-fix/failed-archive-verification.json
[E215]: fannagent-partial-calibration-v1-metadata-fix-2026-10-27.md
[E216]: ../agent/docs/verification/partial-calibration-v1-metadata-fix-implementation.json
[E217]: ../trials/torch-reviews-partial-calibration-v1-metadata-fix/COMMANDS.txt
[E218]: ../trials/torch-reviews-partial-calibration-v1-metadata-fix/
[E219]: ../trials/torch-reviews-partial-calibration-v1-identity-fix/failed-archive-verification.json
[E220]: fannagent-partial-calibration-v1-release-audit-2026-10-27.md
[E221]: ../agent/docs/verification/partial-calibration-v1-identity-fix-implementation.json
[E222]: ../trials/torch-reviews-partial-calibration-v1-identity-fix/
[E223]: ../trials/torch-reviews-partial-calibration-v1-identity-fix/accounting-review-2026-10-27/user-config-output.txt
[E224]: fannagent-partial-calibration-v1-accounting-review-2026-10-27.md
[E225]: ../agent/docs/verification/partial-calibration-v1-accounting-review-2026-10-27.json
[E226]: ../trials/torch-reviews-partial-calibration-v1-identity-fix/accounting-review-2026-10-27/
[E227]: fannagent-startup-resource-v1-design-2026-10-27.md
[E228]: fannagent-startup-resource-v1-implementation-2026-10-27.md
[E229]: ../agent/docs/verification/startup-resource-v1-implementation.json
[E230]: ../trials/torch-reviews-startup-resource-v1/COMMANDS.txt
[E231]: ../trials/torch-reviews-startup-resource-v1/
[E232]: fannagent-startup-resource-v1-postrun-2026-10-28.md
[E233]: ../agent/docs/verification/startup-resource-v1-postrun.json
[E234]: ../trials/torch-reviews-startup-resource-v1/postrun-audit-2026-10-28/archive-verification.json
[E235]: ../trials/torch-reviews-startup-resource-v1/returned/reviews-startup-resource-v1-20261028T020546Z.zdsnk75c/
[E236]: ../trials/torch-reviews-startup-resource-v1/postrun-audit-2026-10-28/metrics.json
[E237]: ../trials/torch-reviews-startup-resource-v1/postrun-audit-2026-10-28/replay/resource.json
[E238]: ../trials/torch-reviews-startup-resource-v1/postrun-audit-2026-10-28/
[E239]: fannagent-startup-memory-audit-v1-2026-10-28.md
[E240]: fannagent-startup-identity-stream-v1-design-2026-10-28.md
[E241]: ../trials/torch-reviews-startup-memory-audit-v1/CORRECTION-DESIGN.json
[E242]: ../agent/docs/verification/startup-memory-audit-v1.json
[E243]: ../trials/torch-reviews-startup-memory-audit-v1/source-inventory.json
[E244]: ../trials/torch-reviews-startup-memory-audit-v1/trace-lifetime-review.json
[E245]: ../trials/torch-reviews-startup-memory-audit-v1/
[E246]: fannagent-startup-identity-stream-v1-implementation-2026-10-28.md
[E247]: ../agent/docs/verification/startup-resource-stream-v1-implementation.json
[E248]: ../agent/experiments/startup-resource-stream-v1/
[E249]: ../trials/torch-reviews-startup-resource-stream-v1/COMMANDS.txt
[E250]: ../trials/torch-reviews-startup-resource-stream-v1/
[E251]: ../trials/torch-reviews-startup-resource-stream-v1/release-verification.json
[E252]: fannagent-startup-resource-stream-v1-postrun-2026-10-28.md
[E253]: ../agent/docs/verification/startup-resource-stream-v1-postrun.json
[E254]: ../trials/torch-reviews-startup-resource-stream-v1/postrun-audit-2026-10-28/archive-verification.json
[E255]: ../trials/torch-reviews-startup-resource-stream-v1/returned/reviews-startup-resource-stream-v1-20261028T151219Z.hmj9cwut/
[E256]: ../trials/torch-reviews-startup-resource-stream-v1/postrun-audit-2026-10-28/metrics.json
[E257]: ../trials/torch-reviews-startup-resource-stream-v1/postrun-audit-2026-10-28/replay/resource.json
[E258]: ../trials/torch-reviews-startup-resource-stream-v1/postrun-audit-2026-10-28/
[E259]: fannagent-startup-working-set-audit-v1-2026-10-28.md
[E260]: ../agent/docs/verification/startup-working-set-audit-v1.json
[E261]: ../trials/torch-reviews-startup-working-set-audit-v1/source-inventory.json
[E262]: ../trials/torch-reviews-startup-working-set-audit-v1/trace-working-sets.json
[E263]: ../trials/torch-reviews-startup-working-set-audit-v1/command-accounting-review.json
[E264]: ../trials/torch-reviews-startup-working-set-audit-v1/
[E265]: fannagent-startup-attribution-v1-design-2026-10-28.md
[E266]: ../trials/torch-reviews-startup-attribution-v1-design/ATTRIBUTION-DESIGN.json
[E267]: ../trials/torch-reviews-startup-attribution-v1-design/CHECKPOINTS.json
[E268]: ../trials/torch-reviews-startup-attribution-v1-design/DRIVER-HOOKS.json
[E269]: ../agent/docs/verification/startup-attribution-v1-design.json
[E270]: ../trials/torch-reviews-startup-attribution-v1-design/




## 12. Academic and industry sources

Sources were reviewed in the research conversation on October 22, 2026; key method/documentation links were rechecked while creating this file. Paper URLs are versioned where available. Live documentation may change; record installed versions and exact settings when a future campaign selects a library. The BoTorch link is explicitly development documentation, not a production-version recommendation. B1-review rechecked the pinned engine/scan, versioned PostgreSQL, Psycopg3.3.6 pool documentation and HNSWv4 sources on October25; these supply mechanisms, not predictions or a dependency recommendation.

| ID | Primary source | Evidence type / relevant contribution | Application and limit |
| --- | --- | --- | --- |
| S1 | Li et al., [Improving Approximate Nearest Neighbor Search through Learned Adaptive Early Termination](https://www.pdl.cmu.edu/PDL-FTP/BigLearning/mod0246-liA_abs.shtml), SIGMOD 2020 | Published research; intermediate search observations and learned termination | Motivates query-dependent decisions; not a filtered-pgvector reproduction |
| S2 | Xia et al., [E2E: Efficient Filtered AKNN Search via Adaptive Termination](https://arxiv.org/html/2602.06721v2), KDD 2026, v2 | Published research; §§3–4 discuss filter/distance interaction, early probing, and predicted effort | Motivates targeted signals and budget prediction; collection semantics and overhead require local qualification |
| S3 | [Filtered Approximate Nearest Neighbor Search in Vector Databases: System Design and Performance Analysis](https://arxiv.org/html/2602.11443v1), 2026 preprint | Global/local selectivity analysis and filtered-search benchmarking | Guides workload strata and broader plan-selection hypotheses; offline GLS is not automatically a runtime feature |
| S4 | Xu, Weinberger, Chapelle, [The Greedy Miser: Learning under Test-time Budgets](https://www.cs.cornell.edu/~kilian/papers/greedymiser.pdf), ICML 2012 | Published research; incorporates feature acquisition cost into learning | Supports cost-aware feature selection; does not remove preparation/routing costs |
| S5 | Geifman and El-Yaniv, [SelectiveNet](https://proceedings.mlr.press/v97/geifman19a.html), ICML 2019 | Published research; prediction with a reject option and coverage/risk tradeoff | Conceptual basis for selective application, not a proposal to install a neural serving model |
| S6 | Cheng et al., [AI-Driven Research for Databases](https://arxiv.org/html/2604.06566v1), 2026 preprint | Evaluator bottlenecks; §5.2 investigates proxy/full-system disagreement | Supports development-scorer audits; final criteria stay frozen |
| S7 | Balasingam et al., [JetStream](https://arxiv.org/html/2608.22476v1), 2026 preprint | §2.1 separates synthesis stages and externally controlled evaluation | Supports measurement-driven stages; generated query accelerators differ from bounded stopping policies |
| S8 | Gelbart, Snoek, Adams, [Bayesian Optimization with Unknown Constraints](https://proceedings.mlr.press/r12/university14b.html), UAI 2014 | Published research; noisy objective/constraint modeling | Motivates numerical search; surrogate feasibility is not acceptance |
| S9 | Lindauer et al., [SMAC3](https://arxiv.org/abs/2109.09831v2), JMLR 2022 | Published research; configurable optimization across problem instances | Candidate conventional baseline for a bounded family |
| S10 | Meta, [Ax outcome constraints](https://ax.dev/docs/recipes/outcome-constraints/) | Official implementation documentation; explicit outcome and baseline-relative constraints | Candidate implementation; statistical qualification still belongs to the external evaluator |
| S11 | Settles, [Active Learning Literature Survey](https://burrsettles.com/pub/settles.activelearning_20090109.pdf), technical report, 2009 | Query strategies, batch acquisition, costs, and feature acquisition | Informs controlled acquisition comparisons; no universal label-efficiency guarantee |
| S12 | [BoTorch multi-fidelity knowledge-gradient tutorial](https://botorch.org/docs/next/tutorials/multi_fidelity_bo) | Official development documentation; information/cost-aware acquisition | Optional mechanism after simpler baselines; cheap replay is not automatically a calibrated fidelity of full execution |
| S13 | Anthropic, [Writing effective tools for agents](https://www.anthropic.com/research/writing-tools-for-agents), September 2025 | First-party engineering guidance; meaningful and economical tool feedback | Informs P6 ablation; vendor experience is not a local causal result |
| S14 | Anthropic, [Effective context engineering for AI agents](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents), September 2025 | First-party engineering guidance; compaction and structured notes | Informs research-state design; evidence and budgets remain host-authoritative |
| S15 | Anthropic, [Demystifying evals for AI agents](https://www.anthropic.com/research/demystifying-evals-for-ai-agents), January 2026 | First-party engineering guidance; repeated trials, outcome/trajectory grading | Supports method benchmark; numerical quality and timing remain programmatically evaluated |
| S16 | Agrawal et al., [GEPA](https://arxiv.org/abs/2507.19457v2), ICLR 2026 | Published research; reflective prompt optimization using execution feedback | Optional after reliable task evaluation; other-task gains do not predict FANNAgent gains |
| S17 | Novikov et al., [AlphaEvolve](https://arxiv.org/html/2506.13131v1), 2025 white paper | Evaluator-guided evolutionary search and staged evaluation | Motivates evaluation cascades and candidate diversity; not a requirement for a larger agent architecture |
| S18 | Angelopoulos et al., [Learn then Test](https://arxiv.org/abs/2110.01052v5) | Research framework; calibration through hypothesis testing | Candidate basis for future selection/evaluation design, under its assumptions |
| S19 | Howard et al., [Time-uniform, nonparametric, nonasymptotic confidence sequences](https://arxiv.org/abs/1810.08240v9), Annals of Statistics 2021 | Published statistical research; inference under repeated inspection | Addresses sequential monitoring with suitable assumptions; not automatic protection against arbitrary adaptive candidate selection |
| S20 | Angelopoulos et al., [Conformal Risk Control](https://arxiv.org/abs/2208.02814v4) | Research framework; bounded monotone loss risk control | Investigate only after defining a suitable loss/family and checking assumptions |
| S21 | Patel et al., [ACORN](https://arxiv.org/abs/2403.04871v1), 2024 | Research on predicate-aware graph traversal/index design | Broader B1 direction, separate from fixed-index stopping and its performance claims |
| S22 | [scikit-learn 1.7 DecisionTreeRegressor](https://scikit-learn.org/1.7/modules/generated/sklearn.tree.DecisionTreeRegressor.html) | Official versioned estimator documentation, including float32 prediction inputs | P3b shallow baseline and observed export parity; no workload performance guarantee |
| S23 | [scikit-learn 1.7 ExtraTreesRegressor](https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.ExtraTreesRegressor.html) | Official versioned ensemble documentation | P3b offline flexible diagnostic; no serving/deployability claim |
| S24 | [Nested versus non-nested cross-validation](https://scikit-learn.org/1.7/auto_examples/model_selection/plot_nested_cross_validation_iris.html) | Official model-selection example | Separate inner selection from outer evaluation; P3b additionally enforces vector grouping; prior adaptation remains |
| S25 | [scikit-learn common pitfalls](https://scikit-learn.org/1.7/common_pitfalls.html) | Official leakage and learned-preprocessing guidance | Keep fitting/pruning/selection training-only; does not turn exposed development into independent confirmation |
| S26 | [pgvector 0.8.6 README](https://github.com/pgvector/pgvector/blob/v0.8.6/README.md) | Official versioned query options/filtering/iterative-scan documentation | Search-time effort mechanism and filtered completeness caveat; no local router performance guarantee |
| S27 | [Pinned pgvector GUC definitions](https://raw.githubusercontent.com/pgvector/pgvector/8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c/src/hnsw.c) | Primary source at local build recipe's exact commit | ef_search range/user-setting semantics; iterative limits do not cap initial scan |
| S28 | [Pinned pgvector HNSW scan](https://raw.githubusercontent.com/pgvector/pgvector/8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c/src/hnswscan.c) | Primary implementation at same commit | Effort-dependent initial search/resumption; no reuse of 640 stopping prefixes as320 outcomes |
| S29 | [PostgreSQL 17 SET](https://www.postgresql.org/docs/17/sql-set.html) | Official session/transaction setting semantics | SET LOCAL must enclose the query in a transaction; pool isolation/full costs need new qualification |
| S30 | [PostgreSQL17 pg_settings](https://www.postgresql.org/docs/17/view-pg-settings.html) | Official current-setting/unit/source/boot/reset/context metadata | B1b audits real session values/default metadata; inspected source320 and declared reference640 stay distinct |
| S31 | [Psycopg3.3.6 connection-pool documentation](https://github.com/psycopg/psycopg/blob/3.3.6/docs/advanced/pool.rst) | Official tagged lifecycle/capacity/configure/reset/recovery guidance | Supports explicit connection-reuse scope and startup accounting; B1b Pool is custom, no psycopg_pool adoption or installed-version claim |
| S32 | Malkov and Yashunin, [HNSW](https://arxiv.org/abs/1603.09320v4),2018v4 | Primary algorithm paper, hierarchical proximity-graph search | Background only; no local480 guarantee, graph-transfer permission or observed gain |
| S33 | [PostgreSQL17 Using EXPLAIN](https://www.postgresql.org/docs/17/using-explain.html) | Official estimated-plan cost/row and actual-analysis semantics | Saved non-ANALYZE costs/rows are not actual latency/work or exact selectivity |
| S34 | [PostgreSQL17 query planning](https://www.postgresql.org/docs/17/runtime-config-query.html) | Official planner switches and cost/cache behavior | Setting intent needs actual plan qualification; no planner-cost fitting or exactness proof from flags |
| S35 | [PostgreSQL17 partial indexes](https://www.postgresql.org/docs/17/indexes-partial.html) | Official planning-time predicate implication | Partial ANN targets need new graph/compatibility scope and parameter/custom-plan checks |
| S36 | [PostgreSQL17 combining indexes](https://www.postgresql.org/docs/17/indexes-bitmap-scans.html) | Official bitmap combination and ordering loss | Scalar index does not supply a free ordered-HNSW intersection or speed guarantee |
| S37 | [PostgreSQL17 PREPARE](https://www.postgresql.org/docs/17/sql-prepare.html) | Official custom/generic cached-plan behavior | Qualify actual driver/cache/plans; generic parameter plans may not imply a partial predicate |
| S38 | [PostgreSQL17 indexes and ORDER BY](https://www.postgresql.org/docs/17/indexes-ordering.html) | Official ORDER BY/LIMIT scan/sort tradeoff | Exact top10 can bound output but still needs candidate work; no local speed inference |
| S39 | [PostgreSQL17 EXPLAIN](https://www.postgresql.org/docs/17/sql-explain.html) | Official JSON/EXECUTE versus ANALYZE semantics | B2b inspects actual cached/current plan structure without executing uncharged ANALYZE searches |
| S40 | [Psycopg3.3.6 automatic preparation](https://github.com/psycopg/psycopg/blob/3.3.6/docs/advanced/prepare.rst) | Official tagged prepare-threshold/cache/prepare=False behavior | Keep inherited query preparation; observer diagnostics do not auto-prepare; no driver-version or native timing inference from docs |
| S41 | [PostgreSQL17.11 JSON type categorization][S41] | Pinned primary implementation; built-in OID uses its ordinary output category | Source-backed serialization diagnosis; not actual remote catalog verification |
| S42 | [PostgreSQL17.11 jsonb scalar conversion][S42] | Pinned primary implementation; ordinary output becomes JSON text | Require faithful catalog fixture; no waiver of graph identity or native qualification |
| S43 | [PostgreSQL17 CREATE INDEX][S43] | Official partial/build/locking/concurrent-build semantics | New graph build and maintenance are charged; private ordinary build does not qualify concurrent deployment |
| S44 | [NYU Torch utility applications][S44] | Official myquota command/output and quota reporting | Strict conservative space/inode preflight before allocation and restore; unknown current format fails closed, no assumed default quota |
| S45 | [PostgreSQL17 pg_prepared_statements][S45] | Official session-local prepared inventory; cumulative generic/custom plan-choice counts | Interpret equal B2e counters with S37/S39; counters and non-ANALYZE plans are not execution-time/CPU/cache telemetry |
| S46 | [PostgreSQL17 cumulative statistics][S46] | Official activity/counter configuration, update and snapshot semantics | Boundary context only; no exact query cache attribution or settings reset |
| S47 | [PostgreSQL17 session information][S47] | pg_backend_pid and session identity functions | Tie actual connection to backend; namespace/starttime/server proof remains mandatory |
| S48 | [Linux sched_setaffinity][S48] | Primary API permission, effective-mask/cpuset and inheritance semantics | Fixed allocation-local placement is a tested scope intervention, not exclusive-core or speed proof |
| S49 | [Linux proc PID stat][S49] | Process identity, CPU ticks/resolution, faults and last CPU fields | Required coarse burst context, not a pure high-resolution server timer |
| S50 | [Linux proc PID status][S50] | Namespace IDs, allowed sets and context-switch fields | Validate physical process/placement and retain observation limitations |
| S51 | [Linux proc PID I/O][S51] | Read/write byte counters and access/counter caveats | Diagnostic deltas only; no assumed PostgreSQL buffer-hit proof |
| S52 | [Linux kernel scheduler statistics][S52] | Per-task CPU/runqueue counters and format semantics | Optional capability with enabled-state/availability record; absent accounting is not zero wait |
| S53 | [PostgreSQL17 file-system backup][S53] | Consistent whole-cluster copy requirements | Copy exact stopped cluster; no graph-file transplantation or old-source restart |
| S54 | [PostgreSQL17 pg_controldata][S54] | Offline control-state inspection | Matching runtime utility records clean-state prerequisite; absence of PID file alone is insufficient |



[S1]: https://www.pdl.cmu.edu/PDL-FTP/BigLearning/mod0246-liA_abs.shtml
[S2]: https://arxiv.org/html/2602.06721v2
[S3]: https://arxiv.org/html/2602.11443v1
[S4]: https://www.cs.cornell.edu/~kilian/papers/greedymiser.pdf
[S5]: https://proceedings.mlr.press/v97/geifman19a.html
[S6]: https://arxiv.org/html/2604.06566v1
[S7]: https://arxiv.org/html/2608.22476v1
[S8]: https://proceedings.mlr.press/r12/university14b.html
[S9]: https://arxiv.org/abs/2109.09831v2
[S10]: https://ax.dev/docs/recipes/outcome-constraints/
[S11]: https://burrsettles.com/pub/settles.activelearning_20090109.pdf
[S12]: https://botorch.org/docs/next/tutorials/multi_fidelity_bo
[S13]: https://www.anthropic.com/research/writing-tools-for-agents
[S14]: https://www.anthropic.com/research/effective-context-engineering-for-ai-agents
[S15]: https://www.anthropic.com/research/demystifying-evals-for-ai-agents
[S16]: https://arxiv.org/abs/2507.19457v2
[S17]: https://arxiv.org/html/2506.13131v1
[S18]: https://arxiv.org/abs/2110.01052v5
[S19]: https://arxiv.org/abs/1810.08240v9
[S20]: https://arxiv.org/abs/2208.02814v4
[S21]: https://arxiv.org/abs/2403.04871v1
[S22]: https://scikit-learn.org/1.7/modules/generated/sklearn.tree.DecisionTreeRegressor.html
[S23]: https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.ExtraTreesRegressor.html
[S24]: https://scikit-learn.org/1.7/auto_examples/model_selection/plot_nested_cross_validation_iris.html
[S25]: https://scikit-learn.org/1.7/common_pitfalls.html
[S26]: https://github.com/pgvector/pgvector/blob/v0.8.6/README.md
[S27]: https://raw.githubusercontent.com/pgvector/pgvector/8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c/src/hnsw.c
[S28]: https://raw.githubusercontent.com/pgvector/pgvector/8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c/src/hnswscan.c
[S29]: https://www.postgresql.org/docs/17/sql-set.html
[S30]: https://www.postgresql.org/docs/17/view-pg-settings.html
[S31]: https://github.com/psycopg/psycopg/blob/3.3.6/docs/advanced/pool.rst
[S32]: https://arxiv.org/abs/1603.09320v4

[S33]: https://www.postgresql.org/docs/17/using-explain.html
[S34]: https://www.postgresql.org/docs/17/runtime-config-query.html
[S35]: https://www.postgresql.org/docs/17/indexes-partial.html
[S36]: https://www.postgresql.org/docs/17/indexes-bitmap-scans.html
[S37]: https://www.postgresql.org/docs/17/sql-prepare.html
[S38]: https://www.postgresql.org/docs/17/indexes-ordering.html

[S39]: https://www.postgresql.org/docs/17/sql-explain.html
[S40]: https://github.com/psycopg/psycopg/blob/3.3.6/docs/advanced/prepare.rst

[S41]: https://github.com/postgres/postgres/blob/REL_17_11/src/backend/utils/adt/jsonfuncs.c#L5608-L5705
[S42]: https://github.com/postgres/postgres/blob/REL_17_11/src/backend/utils/adt/jsonb.c#L764-L772
[S43]: https://www.postgresql.org/docs/17/sql-createindex.html
[S44]: https://services.rt.nyu.edu/docs/hpc/tools_and_software/utils/
[S45]: https://www.postgresql.org/docs/17/view-pg-prepared-statements.html
[S46]: https://www.postgresql.org/docs/17/monitoring-stats.html
[S47]: https://www.postgresql.org/docs/17/functions-info.html
[S48]: https://man7.org/linux/man-pages/man2/sched_setaffinity.2.html
[S49]: https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html
[S50]: https://man7.org/linux/man-pages/man5/proc_pid_status.5.html
[S51]: https://man7.org/linux/man-pages/man5/proc_pid_io.5.html
[S52]: https://docs.kernel.org/scheduler/sched-stats.html
[S53]: https://www.postgresql.org/docs/17/backup-file.html
[S54]: https://www.postgresql.org/docs/17/app-pgcontroldata.html

## 13. Change log

| Date | Version | Change | Execution performed |
| --- | --- | --- | --- |
|2026-11-02 |1.81 | Freeze and locally verify offline A3 authority/ownership backend | 642 fresh checks,17+17 actual Linux cases and200,143 prior files verify; all D128 bytes/tests/limits unchanged, full saved science proof reverified. Production roots, site provisioning, adapter wiring and native handoff stay HOLD; no Torch/search/new grant/reuse |
|2026-11-02 |1.80 | Complete frozen offline A3 native release review | Five bounded lifecycle/admission corrections,1,280 local checks/60 CPU samples and195,784 preserved hashes pass. Native qualification handoff HOLD; concrete authority/group/live-admission backend and fresh allowance absent; no Torch, search, command/capsule release or spent-allowance reuse |
| 2026-10-22 | 1.0 | Created permanent roadmap; incorporated verified selective pilot and abstention; promoted execution economics; added phase tasks, gates, critical dependencies, tracking registers, and sources | Documentation creation and read-only source review only; no code changes or experiments |
| 2026-10-23 | 1.1 | Implemented and packaged NEXT-COST-01; added scoped diagnostic gate, progress, and runbook links | 16 local interface/simulation/integrity tests and lint; no provider requests, database experiments, or Torch submissions |
| 2026-10-23 | 1.2 | Closed P1/G1 with verified cost attribution; recorded repeated policy/profile work, query normalization and unresolved database-wait boundary; narrowed P2, revised critical path, progress, gates, decisions and evidence links | User completed the three-block Torch campaign; this revision verified returned data locally and recomputed sealed reports only; no new source changes, remote experiments, provider calls or confirmation queries |
| 2026-10-23 | 1.3 | Implemented/checked P2a; froze one six-arm original/owned comparison, practical thresholds and resource cap; added sealed identities, commands, tracking and current critical path | 31 local correctness/simulation/integrity tests, lint/format, module/shell syntax and package verification; no native DB experiment, Torch submission, provider request or confirmation query |
| 2026-10-23 | 1.4 | Verified completed P2a; recorded 5.171% direct candidate reuse saving, unchanged outputs/stops, failed engineering gate and G2 revise; retained original baseline and proposed admission/profile identity plus A/A/precision planning | Local data-only extraction, sealed recomputation/parity and research records only; user's completed campaign used 3 allocations/143,163 searches; no new run, source change, provider call or confirmation |
| 2026-10-23 | 1.5 | Implemented/checked/sealed NEXT-ADMIT-01 P2b; one charged immutable admission fingerprint, original/P2a/P2b A/B references, four Williams-balanced blocks, strict A/A and incremental/combined engineering gates; updated tracking and critical path | 45 local checks, lint/format/syntax, package/archive integrity and mock authentication-failure check; 4-allocation/370,884-search finite cap; zero native execution/provider/confirmation and no production change |
| 2026-10-23 | 1.6 | Recorded user-pasted P2b completion for jobs 20753185–20753188; advanced current path to collection/download and independent raw verification; preserved unassessed A/A/engineering gates | Status transcription and progress records only; no new experiment, code change, source modification or independent performance verdict |
| 2026-10-23 | 1.7 | Independently verified P2b; recorded modest activation/combined reuse savings, failed activation A/A equivalence and relative improvement bound, preserved `measurement_inconclusive`, and changed the critical path to one finite calibration/retain-original decision | Local checksum/archive/raw verification, fresh sealed reconstruction and existing-data descriptive audit only; no code change, new experiment, provider or confirmation access |
| 2026-10-23 | 1.8 | Implemented/checked/sealed NEXT-CAL-01 P2c: explicit conditioned-index/query fresh-session scope, fixed native conditioning, adjacent ABBA/BAAB, all native/original/P2a/P2b controls and unchanged frozen engineering logic | 44 local checks on source and sealed package, lint/format/syntax, archive and all-case schedule verification; two-allocation/592,242-search finite cap; no native job, provider/confirmation or production change |
| 2026-10-24 | 1.9 | Independently verified completed P2c: scoped A/A calibration passes all 240 interval checks, all 144 nonregression checks pass, incremental activation confidence target fails; retain original, close finite P2 without M1 and move critical path to bounded P3a coverage/identity diagnosis | Local checksum/member/raw verification, fresh sealed reconstruction/parity and documentation only; user campaign used 2 allocations/592,242 searches; no code change, new experiment, provider or confirmation access |
| 2026-10-24 | 1.10 | Completed P3a data-only coverage/feature/identity audit: complete static23/progress34 reached-grid outcomes support restricted grouped modeling; preserve Light19/off-grid/cost gaps and evidence exposure; revised critical path to finite P3b contract | 620 source/input files verified before/after; no fits, policy searches/simulations, DB/provider/Torch calls or protected query-value access; decoder revisions/logs and local cumulative-I/O accounting caveat preserved in receipt |
| 2026-10-24 | 1.11 | Completed P3b frozen grouped utility-regression/Extra Trees comparison; all calibrated selections continue; fixed ensembles fail unfiltered recall; close finite procedures negatively, G3 revise, propose one P3c risk-separated formulation | Local implementation, fourteen correctness checks/twelve synthetic fits; 340 scientific fits, independent 560-assessment/4,800-case replay, descriptive analysis and documentation; zero native/DB/provider/Torch/confirmation/protected access; zero-fit preflight preserved |
| 2026-10-24 | 1.12 | Completed frozen P3c risk-separated comparison; four cells select gates but no joint outer qualifier; safer diagnostics fail activation economics; close finite P3/G3 negatively and propose B1a fixed-index search-effort feasibility/design | Sixteen checks/six synthetic fits;100 scientific fits, 102.377 s, 0.993 GiB RSS; independent248,851-leaf/980-assessment/4,800-case replay; zero new native/DB/provider/Torch/confirmation/protected access; prior evidence/production preserved |
| 2026-10-24 | 1.13 | Completed B1a source/API/input/timing/identity audit; scoped GB1 engine feasibility passes, native effort API/frontier unqualified; old/current graph mismatch prevents pooled labels; next B1b current native 320/640 interface/frontier before routing | Read-only source/metadata/hash review and documentation only;324 code/source files unchanged,122 old raw-input/six analysis-output hashes pass; zero code changes/tests/fits/simulations/native/DB/provider/Torch/protected access |
| 2026-10-24 | 1.14 | Implemented and sealed B1b/NEXT-EFFORT-01 native320/640 interface/current-index comparison with original640 and source320 references, full reader/selector costs, strict A/A and regime-specific frontier gates; user Torch run is now the critical path |17 source/17 sealed tests including full two-block mock serialization/replay and semantic tamper rejection; lint/format/shell/package/archive checks;324 prior code/source +29 consulted inputs +128 historical files preserved; zero native/DB/provider/Torch/fits/protected access; no performance verdict |
| 2026-10-25 |1.15 | Verified completed B1b: native conformance passes, reuse A/A32/32 but activation2/32;320 reuse40.540% faster with−0.800pp recall, forced640 reuse overhead fails; formal aggregate measurement_inconclusive, no B1c context, original retained | User2-job/139,272-search campaign; all40 returned archive members/26 locked raw files and fresh unchanged sealed replay verified; one proven `/results` campaign-label reconciliation, three floating differences≤4.34e−19; four recovery checks; zero new native/DB/provider/Torch/fits/protected access |
| 2026-10-25 |1.16 | Completed B1-review; audited admission/validation and existing timer categories; froze B1b2 fixed480-versus640 quality-first warm native design, with detailed gates/critical path and no B1c/adoption claim | Documentation only;685 existing hashes preserved, including146 sealed and40 returned files; zero code edits/tests/new native/DB/provider/Torch/fits/simulations/protected access. Proposed one allocation, stop by1,830 on failed quality, max59,430; implementation/checks/seal pending |
| 2026-10-25 |1.17 | Implemented/checked/sealed fixed480-versus640 B1b2 under the unchanged quality-first warm contract; one user Torch job is now the critical path |22 source/22 sealed mock checks,150 package files/151 archive members, syntax/lint/format and691 prior hashes pass. No new native/DB/provider/Torch experiment, fit or protected access; native/quality/A/A/benefit remain unassessed; original retained |
| 2026-10-25 |1.18 | Verified completed B1b2: native conformance/absolute floors pass; fixed480 fails recall reserve overall/votes32/votes108 by0.0833/0.1000/0.4000pp of lower-bound shortfall; close finite probe negative and propose read-only B2a plan/filter/index audit | User1 job/1,830 searches; this revision verifies24 archive members/15 locked files, byte-identical unchanged sealed replay, saved-ID recalls and888 immutable hashes; no new experiment/code/fit/native/DB/provider/Torch/protected access; timing/A/A/benefit not assessed |
| 2026-10-25 |1.19 | Completed B2a read-only plan/filter/index audit; scoped GO for one fixed exact-top10 versus native640 design on unchanged graph/module; defer router and broader physical/native changes |349 source/code and907 immutable hashes verified; saved plans/source/metadata and primary docs only; zero code/tests/experiments/fits/simulations/DB/native/provider/Torch/protected access. No implementation or assigned measurement budget; no user commands |
| 2026-10-25 |1.20 | Freeze/implement/check/seal B2b exact10 versus native640 on unchanged graph/module/data/native query/full truth; add catalog/cache/semantic controls,16 A/A intervals and eight adjusted economic endpoints; user Torch handoff is next |33 source/33 sealed mock checks,153 manifest files/154 archive members, four staged transport mocks and912 old hashes pass. No native/DB/provider/Torch experiment, scientific fit, protected data or job submission; native/performance gates not assessed |
| 2026-10-26 |1.21 | Record original B2b job20941363 user-reported zero-search catalog failure; reproduce OID/JSON integer-mock defect; freeze/check/seal strict separate correction and recovery gates; revise critical path to failed-raw collection/verification before corrected command release |43 source/43 sealed mock checks,155 files/156 archive members, four transport mocks, unchanged scientific constants/127 frozen files and1,095 prior hashes. Three temporary PG16 initdb attempts blocked before SQL; no existing DB/ANN/native/Torch/provider/fit/protected execution. Raw review and corrected native gates pending; original retained |
| 2026-10-26 |1.22 | Independently verify original failed B2b archive/identity/accounting/cleanup/protection; complete R2/R3 and release unchanged separate correction commands; critical path returns to one user corrected native allocation |19 regular archive members/153,662 bytes verified;0 searches, one reader closed/private DB stopped,19 protected groups/1,621 entries identical;1,307 prior files preserved. Existing43/43 local checks retained; no scientific code/package changes, new experiments, fits, native/DB/provider/Torch/protected access or submission. Corrected native gates remain pending |
| 2026-10-26 |1.23 | Record user-reported corrected job20949301 internal deadline failure during block1; distinguish prefix quality inference from independent verification and partial timings from full gates; critical path is collect/verify/phase-cost review before any new scope | Read-only source/counter review and documentation only;26,247 reported attempts/12,208 retained;1,315 prior files preserved. No code/package change, tests, experiments, fits, native/DB/provider/Torch/protected access or submission. Corrected raw/cleanup/quality/coverage unverified; both allowances consumed |
| 2026-10-26 |1.24 | Independently verify corrected partial return/quality/coverage/phase costs; finite B2b closes incomplete with no full A/A/economic verdict; exact56.11x slower in block0 and0/763 wins supports no repeat; propose read-only B2c alternatives review |30 archive members,600 reference records,12,208 retained/6,104 slots/6,105 conditioning/8,520 plan packets validate; saved quality bootstrap replayed once, descriptive timing arithmetic only;1,352 prior files preserved. No new searches/experiments/fits/native/DB/provider/Torch/protected use or scientific source/package changes; final audits remain missing |
| 2026-10-26 |1.25 | Complete read-only B2c source/evidence/cache/cost/alternative review; scoped GO for one >=108 partial cosine HNSW and freeze B2d design only |349 source/1,364 prior hashes preserved; public partial rejection and C binding/planner limits explicit; two private copies,24-vector preview,16,802-search cap and full quality/A/A/economic/final-proof gates. No code/tests/experiments/bootstrap/index build/native/DB/Torch/provider/protected use or allocation; next local implementation/check/seal, no user command |
| 2026-10-26 |1.26 | Implement/check/seal isolated B2d single >=108 partial-index comparison; release once-only Torch commands |55 source/55 sealed mock checks;161-file/162-member final archive; clean B2d contract identity, preserved internal undispatched review seal and349 source/1,370 prior hashes. No adopted/public/prior artifact change, native/index experiment, provider/fit/protected/Torch call or allocation. Actual resource/native/quality/A/A/economic/final proofs pending |

| 2026-10-26 |1.27 | Repair B2d quota preflight display compatibility in separate seal; current handoff uses quota-fix | User failure before reservation/Slurm consumes no allocation;61 source/61 sealed checks,162-file seal, unchanged scientific config/runtime/gates and shared original reservation;1,733 prior files preserved. Native/index/quality/A/A/economics pending; no new experiment/submission by Codex |

| 2026-10-26 |1.28 | Record submitted B2d job21043219_0 initial environment failure and switch current handoff to collection only |0 reported searches/readers, allowance consumed; source shows admin/reader guard scope to audit, exact mismatch/raw/cleanup/protection unverified.1,928 prior hashes preserved; no source/seal change, test, new experiment or submission by Codex |

| 2026-10-26 |1.29 | Verify failed B2d and exact admin4MiB/reader16MiB mismatch; freeze/implement/check/seal separate correction and release exact commands |21 archive members/cleanup/23 protected groups verified;75 source/75 sealed,169-file seal, same scientific settings/gates and1,960 prior hashes. Old allowance spent; one separate corrected allocation proposed, no new native/DB/index/Torch/provider/fit/protected experiment by Codex |

| 2026-10-26 |1.30 | Record reported full corrected B2d completion; repair collection only for actual old-prefix label | Job21048213_0 reports16,802 searches/quality/final integrity true; A/A/economics unverified. Separate raw collector8 checks and2,166 prior hashes pass, no measurement/source/seal/raw/name changes or new job. Current small-helper upload/collect/download then independent review |

| 2026-10-26 |1.31 | Verify complete B2d raw, exact-name recovery and fresh sealed parity; close measurement_inconclusive and propose read-only B2e |37 archive files/16,802 attempts/quality98.60→99.85%/final integrity pass; observed17.44% lower latency and nominal endpoints pass but0/4 A/A intervals pass.2,219 prior hashes preserved; no scientific edits, new experiment/provider/fit/native/Torch/protected use; original retained, no commands now |
| 2026-10-26 |1.32 | Complete B2e read-only replica/session audit and conditional calibration-design GO | Matching plans/settings/counters; repetition transient, persistent partial gap and missing physical backend/CPU/cache evidence. Propose B2f fixed-graph instrumented A/A design within finite envelope, no code/tests/bootstrap/experiments/remote calls.2,235 prior inputs preserved; B2d stays inconclusive/original retained; no commands |
| 2026-10-26 |1.33 | Freeze bounded B2f instrumented A/A design and read-only source-inventory handoff | Exact full/partial graphs/data/module/margins; two fresh physical-session epochs,16,242 searches/56 timing intervals and all ancillary/resource/analysis stops.2,241 prior inputs preserved; no code/tests/experiments/simulations/bootstrap/remote/native calls. Source availability and later actual readiness remain pending; B2d unchanged/original retained |
| 2026-10-27 |1.34 | Record preliminary B2f source-inventory pass from user read-only output | Both retained cluster/control paths/no PID stop/3 reported graph hashes match; quota headroom recorded. Frozen design/contract/order unchanged;2,249 prior pins preserved. No code/tests/experiments/assistant remote calls. Full clean-copy/resource/core/telemetry proof remains pending; separate implementation/local readiness next, no more user commands |
| 2026-10-27 |1.35 | Implement/check/seal B2f and prepare exact one-job handoff |78 source+78 sealed synthetic checks, lint/format/AST/shell/archive parity;2,255 prior files preserved. Frozen design/graphs/policies/margins unchanged. No native experiment, allocation, SSH/provider/fit/protected query. User upload/single submit next; all native gates pending, B2d inconclusive/original retained |
| 2026-10-27 |1.36 | Verify pre-Python B2f launch failure; implement/check/seal separate absolute-interpreter/export correction | Original21111616_0 FAILED/2:0/4s,6 raw members verify,0 searches/1 spent allocation.88 source+88 sealed checks, actual shell regression/static/archive/scientific parity and2,500 prior/failure pins pass. One additional user-launched job proposed; all native gates pending, no scientific/adoption change |
| 2026-10-27 |1.37 | Verify second zero-search B2f startup failure; correct pinned identity sidecar restoration and broaden actual frozen-backend integration |32-member archive/copy/source/cleanup proof;21129331_0 failed after8m34s/0 readers or searches.101 source+101 sealed checks with real frozen methods/mocked DB, static/shell/archive/scientific parity and2,781 prior pins preserved. Two spent attempts retained; one additional user job proposed, all native gates pending |

| 2026-10-27 |1.38 | Verify third zero-search B2f failure; correct eligibility schema/restore separate identity guards; audit and test actual runtime startup/acquisition/finalization/cleanup; hold production release for resource feasibility |30-member archive/source/copy/catalog/cleanup verify; offline entry-point/negative/full-size ID-vote checks only;3,065 prior pins preserved. Three attempts remain spent; no fourth package/job/handoff, native experiment, SSH/provider/fit/protected access. R2 read-only accounting/resource decision and R3 final release gate precede any new allocation |

| 2026-10-27 |1.39 | Record supplied cgroup accounting configuration; distinguish conditional cache-inclusive MaxRSS from anonymous RAM/effective limit; keep resource hold and recommend startup-only qualification design | Read-only transcript/source/primary-doc review;3,115 prior pins preserved, no code/tests/experiments/native/DB/SSH/provider/fit/protected access or allocations.119 prior local checks remain historical; config request complete, no more user commands now |

| 2026-10-27 |1.40 | Freeze/implement/check/seal separate startup-only resource qualification and release exact one-job Torch handoff | One1h4CPU32GiB/zero ANN/exact search scope, ten admissions/host memory sampler/conservative resource-only replay. Exact source/sealed/static/archive/transport checks in E229; 3,123 prior pins unchanged. No Codex native/DB/ANN/Torch/provider/fit/protected experiment. Full calibration held, three earlier attempts spent |

| 2026-10-28 |1.41 | Verify completed zero-search startup return and record resource-margin inconclusive outcome | 46-member archive/fresh sealed replay, ten admissions/final cleanup pass. Actual v2 job peak/limit 32 GiB, +592 max events in snapshot_load/zero OOM; frozen allowances short by 4 GiB. Preserve 3,442 inputs. Next read-only snapshot memory/identity compatibility audit; no implementation, new experiment/job, cache subtraction or full calibration release |

| 2026-10-28 |1.42 | Complete M0 snapshot allocation/consumer/identity audit and freeze M1 narrow correction design before code | Per-row original canonical hashing selected; keep rows/NumPy/cursor/validation/identity and fixed resource margin. 116 source files/137 references and existing traces only, 3,456 inputs preserved. No code/tests/new measurements/experiment/remote job. Next M2 isolated implementation/local qualification; M3 native and full B2f remain held |

| 2026-10-28 |1.43 | Complete M2 isolated original-canonical identity streaming, actual-entry/constructor/restoration/cleanup and independent replay qualification; seal separate startup-resource.stream.v1 and prepare exact M3 resource-only commands | 155 source/155 sealed checks, static/archive/source parity, 116 source pins and 3,468 prior inputs preserved. Bounded synthetic/offline checks only; zero native DB/search/provider/fit/SSH/Torch jobs. Native saving/CPU/margin unmeasured; next one user-executed1h4CPU32GiB zero-search qualification, then independent review; full B2f held |

| 2026-10-28 |1.44 | Verify completed identity-stream resource job 21224521_0; native exact-identity/startup/cleanup pass, unchanged margin/no-event gate remains inconclusive |48-member archive/intact346-file seal/fresh replay exact parity; runtime RSS HWM15.030→11.323 GiB descriptively, job peak 32 GiB/+259 max,0OOM. Counter-boundary attribution and3,947 preserved inputs verified. No implementation change/tests/new scientific/native/DB/search/provider/fit/SSH/Torch job. Next read-only working-set audit; full B2f held, no new commands/allocation |

| 2026-10-28 |1.45 | Complete read-only W0–W2 snapshot-loading/retention/verification I/O audit; document persistent final overlap, full transaction costs and API/internal-fetch accounting gap; recommend separate A0 attribution design | 246 source/recipe pins including earlier 116, two existing traces and official references only;3,961 prior inputs unchanged. No code/tests/new measurements/DB/search/provider/fit/SSH/Torch job. No-go blind cursor/batch/cleanup remedy; GO design-only bounded zero-search lifetime/I/O/command ledger; full B2f held, no new commands/allocation |

| 2026-10-28 |1.46 | Freeze A0 startup-attribution.v1 before code:102 checkpoints, local original-code monitoring, nine driver-hook roles, explicit API/dispatch/fetch/protocol ledgers and bounded resource/cleanup/interpretation gates | Documentation/source/primary-reference review only;246 source and3,974 prior inputs preserved. Zero code/tests/runtime probes/new measurements/experiments/DB/search/provider/fit/SSH/Torch jobs. Proposed one1h4CPU32GiB/zero-search job remains unreleased. Next separately requested A1 actual-path implementation/local readiness; full B2f held |

|2026-10-29 |1.47 | Complete A1 isolated implementation and local readiness; preserve A0, actual-code/driver/entry/signal/cleanup/replay and guarded seal |155 baseline and100source/100sealed checks;3,987 old files/246pins preserved. No native experiment/job/search/provider/fit/SSH. Separate A2 handoff review/image capability remains next; full B2f held |

[E271]: fannagent-startup-attribution-v1-implementation-2026-10-29.md
[E272]: ../agent/docs/verification/startup-attribution-v1-implementation.json
[E273]: ../agent/experiments/startup-attribution-v1/README.md
[E274]: ../trials/torch-reviews-startup-attribution-v1/
[E275]: ../trials/torch-reviews-startup-attribution-v1/release-verification.json
[E276]: ../trials/torch-reviews-startup-attribution-v1/torch-startup-attribution-v1/manifest.json

|2026-10-29 |1.48 | Complete A2 release review; catch reference/build Python mismatch before dispatch; hold native release and prepare one source-only image inventory |29source/29sealed checks,99 exact references,108-file seal/109-member archive;5,318 prior files preserved. No new image/DB/experiment/search/provider/fit/SSH/job. Actual SIF inventory and explicit compatibility decision precede any separate corrected native handoff; A0/A1 unchanged, full B2f held |
|2026-10-29 |1.49 | Verify completed one image inventory and identify sole local3.12.7 versus required/actual3.12.15 reference error; GO isolated strict target-reference correction/readiness, HOLD acquisition | Exact four raw files/three payload hashes,108manifest/109archive/99reference files and fresh sealed data-only replay;5,519 prior inputs preserved. No new code/reference/dependency change, tests/image/experiment/DB/search/provider/fit/SSH/job. Nine hooks/parser/libraries/source maps and four literal callbacks pass, not full runtime/memory qualification; no new user commands |
|2026-10-29 |1.50 | Implement isolated strict image-reference correction and pre-restore gate;128normal/128guarded local checks pass. Preserve unqualified local emulated SIGSEGV/no-receipt attempt; prepare one native zero-DB compatibility handoff |23source/23sealed capsule checks,693file/694member archive and5,531 old inputs preserved. No actual ANN/exact/native SQL/provider/fit/Torch job. Only one15m2CPU4GiB compatibility allowance released; main A2/C3/full B2f held, scientific/data/graph/module/policy/resource margins unchanged |

[E277]: fannagent-startup-attribution-v1-release-review-2026-10-29.md
[E278]: ../agent/docs/verification/startup-attribution-v1-release-review.json
[E279]: ../trials/torch-reviews-startup-attribution-v1-release/image-reference-audit.json
[E280]: ../trials/torch-reviews-startup-attribution-v1-release/
[E281]: ../trials/torch-reviews-startup-attribution-v1-release/handoff-verification.json
[E282]: ../trials/torch-reviews-startup-attribution-v1-release/COMMANDS.txt

[E283]: fannagent-startup-attribution-image-preflight-v1-postrun-2026-10-29.md
[E284]: ../agent/docs/verification/startup-attribution-image-preflight-v1-postrun.json
[E285]: ../trials/torch-reviews-startup-attribution-v1-release/returned/startup-attribution-image-preflight-v1.QANl63cj/
[E286]: ../trials/torch-reviews-startup-attribution-v1-release/postrun-audit-2026-10-29/inventory-verification.json
[E287]: ../trials/torch-reviews-startup-attribution-v1-release/postrun-audit-2026-10-29/
[E288]: ../trials/torch-reviews-startup-attribution-v1-release/postrun-audit-2026-10-29/compatibility-decision.json

[E289]: fannagent-startup-attribution-image-reference-correction-2026-10-29.md
[E290]: ../agent/docs/verification/startup-attribution-image-reference-correction.json
[E291]: ../agent/experiments/startup-attribution-v1-image-reference/README.md
[E292]: ../agent/experiments/startup-attribution-compatibility-v1/COMPATIBILITY-CONTRACT.json
[E293]: ../trials/torch-reviews-startup-attribution-compatibility-v1/release-verification.json
[E294]: ../trials/torch-reviews-startup-attribution-compatibility-v1/COMMANDS.txt

[E295]: fannagent-startup-attribution-compatibility-fixture-fix-2026-10-29.md
[E296]: ../trials/torch-reviews-startup-attribution-compatibility-v1/postrun-audit-2026-10-29/returned-verification.json
[E297]: ../trials/torch-reviews-startup-attribution-compatibility-v1/postrun-audit-2026-10-29/retained-diagnostics-and-diagnosis.json
[E298]: ../trials/torch-reviews-startup-attribution-compatibility-v1-fixture-fix/FIX-FREEZE.json
[E299]: ../trials/torch-reviews-startup-attribution-compatibility-v1-fixture-fix/release-verification.json
[E300]: ../trials/torch-reviews-startup-attribution-compatibility-v1-fixture-fix/COMMANDS.txt

|2026-10-29 |1.51 | Verify failed native C2, identify omitted offline metadata, and implement isolated dependency/fixture/failure-reporting correction |13-file/eight-lock failed return; exact provenance, user-retained missing-file diagnostics and actual constructor reproduction.33source/33sealed plus128source/128packaged-fixture main checks; prior inputs/main recipe preserved. Distinct one15m2CPU4GiB/zero-DB handoff only, unchanged caps/margins; original allowance spent, main A2/C3/full B2f held |

[E301]: fannagent-startup-attribution-prepared-fixtures-2026-10-29.md
[E302]: ../trials/torch-reviews-startup-attribution-compatibility-v1-fixture-fix/postrun-audit-2026-10-29/returned-verification.json
[E303]: ../trials/torch-reviews-startup-attribution-compatibility-v1-prepared-fixtures/PREPARATION-FREEZE.json
[E304]: ../trials/torch-reviews-startup-attribution-compatibility-v1-prepared-fixtures/PREPARATION-AMENDMENT-1.json
[E305]: ../trials/torch-reviews-startup-attribution-compatibility-v1-prepared-fixtures/release-verification.json
[E306]: ../trials/torch-reviews-startup-attribution-compatibility-v1-prepared-fixtures/actual-reseal-equivalence.json
[E307]: ../trials/torch-reviews-startup-attribution-compatibility-v1-prepared-fixtures/COMMANDS.txt

|2026-10-29 |1.52 | Verify second C2 failed return and remove redundant offline fixture preparation before a distinct qualification |96native source passes/no errors,16-member/11-lock return and positive metadata/provenance/final integrity; source deadline in fixture prep.43source/43sealed plus128source/128packaged local cases with final guards,1build/4reuses/10equivalent reseals, actual manifest parity. Local watchdog stall caught/preserved/removed; synchronous events rerun. Both old allowances spent; distinct15m2CPU4GiB/all128+128/same300s caps only. Original main recipes/margins preserved; C3/main A2/full B2f held |

[E308]: fannagent-startup-attribution-third-compatibility-timeout-2026-10-29.md
[E309]: ../trials/torch-reviews-startup-attribution-compatibility-v1-prepared-fixtures/postrun-audit-2026-10-29/returned-verification.json
[E310]: ../agent/docs/verification/startup-attribution-compatibility-prepared-fixtures-postrun.json

|2026-10-29 |1.53 | Verify third native C2 timeout and replace the stale handoff with a prospective compatibility-budget review | Data-only 16-member/11-lock archive, 119 passes/no recorded errors and final host identity/integrity pass. Completed fixture stages 143.703s; full child/source/sealed proofs absent. All three allowances spent; no code/capsule/test/experiment/SSH/job or new command. C2B budget-only design/review next, 20m sizing option not frozen/released; main A2/C3/full B2f held |

[E311]: fannagent-startup-attribution-compatibility-budget-correction-2026-10-30.md
[E312]: ../trials/torch-reviews-startup-attribution-compatibility-v1-budget-fix/BUDGET-REVIEW.json
[E313]: ../trials/torch-reviews-startup-attribution-compatibility-v1-budget-fix/BUDGET-FREEZE.json
[E314]: ../trials/torch-reviews-startup-attribution-compatibility-v1-budget-fix/release-verification.json
[E315]: ../trials/torch-reviews-startup-attribution-compatibility-v1-budget-fix/COMMANDS.txt
[E316]: ../agent/docs/verification/startup-attribution-compatibility-budget-correction.json
[E317]: ../agent/experiments/startup-attribution-compatibility-v1-budget-fix/COMPATIBILITY-CONTRACT.json

|2026-10-30 |1.54 | Independently review C2B against native ledger/source, freeze 21 mcomplete time accounting and implement isolated compatibility correction | 62 source/62 sealedcapsule+128 guarded source/128 packaged main cases, all seed/restoration proofs, original reseal parity, exact archive/source/5,111 prior-file preservation. All three old allowances spent; one distinct 21 m / 2 CPU / 4 GiBzero-search handoff E315 only. No native job or main A2 launched; C3/main/full B2f held; original main code/limits unchanged |

[E318]: fannagent-startup-attribution-native-compatibility-C3-release-2026-10-30.md
[E319]: ../trials/torch-reviews-startup-attribution-compatibility-v1-budget-fix/postrun-audit-2026-10-30/returned-verification.json
[E320]: ../trials/torch-reviews-startup-attribution-v1-image-reference/C3-release-2026-10-30/C3-FREEZE.json
[E321]: ../trials/torch-reviews-startup-attribution-v1-image-reference/C3-release-2026-10-30/release-verification.json
[E322]: ../trials/torch-reviews-startup-attribution-v1-image-reference/COMMANDS.txt
[E323]: ../agent/docs/verification/startup-attribution-native-compatibility-C3-release.json

|2026-10-30 |1.55 | Independently verify complete native C2B and complete C3 unchanged main production release | Job21443102: 24-member/19-lock return, all 128+128 cases and strict final proofs. Main 619-file/620-member seal and 128 final local cases, all 68 recipes/5,883 prior files preserved. All four compatibility allowances spent; E322 releases one unchanged 1h4CPU32GiB zero-search main job, still unlaunched. Resource/full B2f gates remain pending/held |

[E324]: ../trials/torch-reviews-startup-attribution-v1-image-reference/login-preflight-2026-10-30/incident-assessment.json
[E325]: ../trials/torch-reviews-startup-attribution-v1-image-reference/login-preflight-2026-10-30/COMMANDS-read-only.txt

|2026-10-30 |1.56 | Record main login home-capacity preflight stop before any reservation or Slurm dispatch | User reports 7,297-file/1,209.5MiB/159.5s verification then /home capacity rejection. Prior conservative file headroom only420 above requirement, main extraction620files plus directories; actual current deficit unknown. E325 read-only report next; no cleanup/code/cap/seal/limit/test/native job changes, main allowance unspent |

[E326]: fannagent-startup-attribution-home-inode-relocation-2026-10-30.md
[E327]: ../trials/torch-reviews-startup-attribution-v1-image-reference/home-quota-relocation-2026-10-30/RELOCATION-FREEZE.json
[E328]: ../trials/torch-reviews-startup-attribution-v1-image-reference/home-quota-relocation-2026-10-30/release-verification.json
[E329]: ../trials/torch-reviews-startup-attribution-v1-image-reference/home-quota-relocation-2026-10-30/COMMANDS.txt
[E330]: ../agent/docs/verification/startup-attribution-home-inode-relocation.json

|2026-10-30 |1.57 | Confirm home file-quota deficit and prepare preserving archive relocation plus original main continuation | Reported20,108used/29,000conservative limit leaves8,892 versus10,000. Three failed C2 capsule trees only; archive copies verified before duplicate cleanup, original paths symlinked, all result/reservation/current main bytes unchanged.21 local checks and helper/command release pass; no remote movement/job, all main gates/limits unchanged, unspent main submit only after fresh capacity proof |

[E331]: ../trials/torch-reviews-startup-attribution-v1-image-reference/home-quota-relocation-2026-10-30/socket-path-fix-2026-10-30/verification.json

|2026-10-30 |1.58 | Correct Mac SSH control socket path after failed helper upload | Both external transfer helpers use short private directories independent of TMPDIR; offline checks pass with no real SSH/SCP. All main and relocation payload bytes remain unchanged; upload, relocation and original main submit remain pending |

[E332]: ../trials/torch-reviews-startup-attribution-v1-image-reference/home-quota-relocation-2026-10-30/native-relocation-quota-wait-2026-10-30/assessment.json

|2026-10-30 |1.59 | Record completed native preservation and final quota wait | All three moves reported verified, but current quota has 9,676 free files versus frozen 10,000; main submit not reached. Prepare one idempotent recheck with physical inode count; all source/seals/tests/verification/limits unchanged |

[E333]: fannagent-startup-attribution-main-A2-postrun-2026-10-30.md
[E334]: ../trials/torch-reviews-startup-attribution-v1-image-reference/postrun-audit-2026-10-30/returned-verification.json
[E335]: ../agent/docs/verification/startup-attribution-main-A2-postrun.json

|2026-10-30 |1.60 | Independently verify completed main A2 and close diagnostic informative | Job21459623_0 COMPLETED0:0/14m16s;52members,32guest/45host locks,102checkpoints,strict fresh replay parity,68recipes/128+128cases preserved; zero searches. Decode RSS+7.478GiB;32GiB peak/780max events leave resource margin inconclusive. Main/four compatibility allowances spent; A3 remedy contract next, full B2f held |

[E336]: fannagent-startup-exact-vector-A3-decision-2026-10-30.md
[E337]: ../trials/torch-reviews-startup-exact-vector-v1/A3-FREEZE.json
[E338]: ../agent/docs/verification/startup-exact-vector-A3-decision.json

|2026-10-30 |1.61 | Complete A3 remedy selection/contract freeze and bounded offline prototype | One exact binary64+integer-tag representation with per-row canonical/JSON sample adapters;33 guarded cases pass,756 prior A2 files and128+128 receipts unchanged. Internal type/mutation scope explicit; native producer/integration/target correctness/resource qualification remain unreleased, all old allowances spent, full B2f held |

[E339]: fannagent-startup-exact-vector-integration-qualification-2026-10-30.md
[E340]: ../trials/torch-reviews-startup-exact-vector-integration-v1/INTEGRATION-FREEZE.json
[E341]: ../trials/torch-reviews-startup-exact-vector-compatibility-v1/release-verification.json
[E342]: ../trials/torch-reviews-startup-exact-vector-compatibility-v1/COMMANDS.txt
[E343]: ../agent/docs/verification/startup-exact-vector-integration-qualification.json

|2026-10-30 |1.62 | Complete isolated A3 producer/startup integration and release a distinct finite native correctness qualification |56+56 integrated/128+128 unchanged/65+65 control cases pass;774-file775-member archive and789 prior-file preservation verify. One new25m2CPU4GiB zero-DB job E342 only; native target pending, resource/B2f held, old allowances spent |

[E344]: ../trials/torch-reviews-startup-exact-vector-compatibility-v1/reported-completion-2026-10-31/assessment.json

|2026-10-31 |1.63 | Record reported A3 native correctness completion and request terminal collection/download | Job21470341 COMPLETED0:0/11m44s; all128+128/56+56, cleanup and zero real DB/SQL/searches reported. Allowance spent; archive verification pending, no source changes/retry/resource/B2f release |


[E345]: fannagent-startup-exact-vector-native-correctness-postrun-2026-10-31.md
[E346]: ../trials/torch-reviews-startup-exact-vector-compatibility-v1/postrun-audit-2026-10-31/returned-verification.json
[E347]: ../agent/docs/verification/startup-exact-vector-native-correctness-postrun.json

|2026-10-31 |1.64 | Independently qualify A3 native correctness from the downloaded return | Job 21470341: all 128+128 unchanged and 56+56 A3 cases on exact 3.12.15; 33 members/28 locks, guards, deadlines, cleanup and integrity verify. Authentic proof packet qualifies metadata-only gate; all allowances spent. Separate resource harness/local release next, no resource/memory/B2f release |


[E348]: fannagent-startup-exact-vector-resource-readiness-2026-10-31.md
[E349]: ../trials/torch-reviews-startup-exact-vector-resource-v1/RESOURCE-FREEZE.json
[E350]: ../trials/torch-reviews-startup-exact-vector-resource-v1/RESOURCE-AMENDMENT-1.json
[E351]: ../trials/torch-reviews-startup-exact-vector-resource-v1/release-verification.json
[E352]: ../trials/torch-reviews-startup-exact-vector-resource-v1/COMMANDS.txt
[E353]: ../agent/docs/verification/startup-exact-vector-resource-readiness.json

|2026-10-31 |1.65 | Qualify separate A3 startup-memory harness locally and release one fresh finite resource handoff | Pre-code metadata adapter preserves frozen reader state and exact bytes; 100+100 checks, 983-file/984-member seal, 1,956 prior-file hashes, authentic native proofs and offline commands verify. Original main/A3 code and 1h/4CPU/32GiB/zero-search/margin unchanged; new allowance unlaunched, all old allowances spent, actual memory/workload/B2f held |


[E354]: ../trials/torch-reviews-startup-exact-vector-resource-v1-path-fix/failure-assessment.json
[E355]: ../trials/torch-reviews-startup-exact-vector-resource-v1-path-fix/PATH-FIX-FREEZE.json
[E356]: fannagent-startup-exact-vector-resource-path-fix-2026-10-31.md
[E357]: ../trials/torch-reviews-startup-exact-vector-resource-v1-path-fix/release-verification.json
[E358]: ../trials/torch-reviews-startup-exact-vector-resource-v1-path-fix/NEXT-COMMANDS.txt
[E359]: ../agent/docs/verification/startup-exact-vector-resource-path-fix.json

|2026-10-31 |1.66 | Correct A3 resource login historical-package context and continue the same unspent allowance | Initial failure before reserve/sbatch; actual main home context verified before unchanged original guards. 110+110 checks, 984-file/985-member seal and 3,035 prior-file preservation pass; separate checked transfer/continuation, same fixed reservation, no new budget or native memory/B2f verdict |


[E360]: ../trials/torch-reviews-startup-exact-vector-resource-v1-path-fix/reported-failure-2026-10-31/assessment.json
[E361]: ../trials/torch-reviews-startup-exact-vector-resource-v1-path-fix/reported-failure-2026-10-31/COMMANDS.txt
[E362]: ../agent/docs/verification/startup-exact-vector-resource-reported-failure.json

|2026-10-31 |1.67 | Record reported terminal A3 resource failure and spend allowance; collection only next | Job21542975_0 FAILED1:0/16m35s; complete admission/epochs/scans/final integrity reported, sampler and cleanup fail. Full native raw unverified; no memory/OOM/source-cause verdict, code/limit change, retry or B2f release |

[E363]: ../trials/torch-reviews-startup-exact-vector-resource-v1-path-fix/postrun-audit-2026-10-31/returned-verification.json
[E364]: ../trials/torch-reviews-startup-exact-vector-resource-v1-path-fix/postrun-audit-2026-10-31/REPORT.md
[E365]: ../agent/docs/verification/startup-exact-vector-resource-postrun.json

|2026-10-31 |1.68 | Independently audit failed A3 resource return and close unqualified | Source/acquisition/zero-search proofs verify; observed28.700241GiB aggregate +4GiB exceeds32GiB; sampler loss/shutdown proof fail. All3,035prior files and original native tests preserved, allowance spent; offline design review only, no retry/new capsule/B2f release |

[E366]: ../trials/torch-reviews-startup-exact-vector-resource-offline-review-v1/REVIEW.json
[E367]: ../trials/torch-reviews-startup-exact-vector-resource-offline-review-v1/OFFLINE-FREEZE.json
[E368]: ../trials/torch-reviews-startup-exact-vector-resource-offline-review-v1/offline-verification.json
[E369]: ../trials/torch-reviews-startup-exact-vector-resource-offline-review-v1/REPORT.md
[E370]: ../agent/docs/verification/startup-exact-vector-resource-offline-review.json

|2026-10-31 |1.69 | Complete offline A3 review and prospectively frozen lifecycle correction |142source+142code-snapshot checks,5,163prior files/all tests/native proofs/limits preserved. Sampling/shutdown handling improved offline; aggregate headroom remains unqualified. No memory patch, native capsule, Torch command, retry/new entitlement or full B2f release |

[E371]: ../trials/torch-reviews-startup-exact-vector-memory-remedy-v1/review-probe.json
[E372]: ../trials/torch-reviews-startup-exact-vector-memory-remedy-v1/MEMORY-FREEZE.json
[E373]: ../trials/torch-reviews-startup-exact-vector-memory-remedy-v1/verification.json
[E374]: ../trials/torch-reviews-startup-exact-vector-memory-remedy-v1/REPORT.md
[E375]: ../agent/docs/verification/startup-exact-vector-memory-remedy.json

|2026-10-31 |1.70 | Freeze and locally verify exact adaptive A3 memory-component remedy |94source+94snapshot checks preserve56old cases, all native/lifecycle proofs and5,445prior files. Full-bit32-bit-code acceptance or raw64 fallback; compact views avoid separate row conversions. Native compactability/CPU/peak held; no production integration, new allowance/capsule/Torch handoff or B2f release |

[E376]: ../trials/torch-reviews-startup-exact-vector-startup-integration-v1/STARTUP-FREEZE.json
[E377]: ../trials/torch-reviews-startup-exact-vector-startup-integration-v1/TARGET-REFERENCE.json
[E378]: ../trials/torch-reviews-startup-exact-vector-startup-integration-v1/verification.json
[E379]: ../trials/torch-reviews-startup-exact-vector-startup-integration-v1/REPORT.md
[E380]: ../agent/docs/verification/startup-exact-vector-startup-integration.json

|2026-11-01 |1.71 | Freeze and verify offline adaptive A3 startup integration against exact target references |272source+272code-snapshot cases,236inherited IDs and5,526prior files preserved; exact SIF/OCI selected files and formatter/driver pins verified. Source/retention/replay/native-release guards hold; original tests/limits/memory decision unchanged. No target execution, native qualification/capsule/Torch command/search/allowance reuse or B2f release |

[E381]: ../trials/torch-reviews-startup-exact-vector-exact-image-review-v1/REVIEW-FREEZE.json
[E382]: ../trials/torch-reviews-startup-exact-vector-exact-image-review-v1/CPU-BUDGET-REVIEW.json
[E383]: ../trials/torch-reviews-startup-exact-vector-exact-image-review-v1/run-output/diagnostics.json
[E384]: ../trials/torch-reviews-startup-exact-vector-exact-image-review-v1/verification.json
[E385]: ../trials/torch-reviews-startup-exact-vector-exact-image-review-v1/REPORT.md
[E386]: ../agent/docs/verification/startup-exact-vector-exact-image-review.json

|2026-11-01 |1.72 | Complete frozen A3 exact-image correctness/CPU review with full qualification held | Standalone PyArrow import faults under localamd64/AArch64emulation; full-suite0cases complete.32+32supplemental exact-kernel cases and4local guards pass;5,697prior files/all272+272tests and limits preserved. Serial CPU projections remain unqualified; no production/dependency/limit change, Torch launch/command, new entitlement or allowance reuse |

[E387]: ../trials/torch-reviews-startup-adaptive-x86-qualification-v1/QUALIFICATION-FREEZE.json
[E388]: ../trials/torch-reviews-startup-adaptive-x86-qualification-v1/release-verification.json
[E389]: ../trials/torch-reviews-startup-adaptive-x86-qualification-v1/COMMANDS.txt
[E390]: ../trials/torch-reviews-startup-adaptive-x86-qualification-v1/REPORT.md
[E391]: ../agent/docs/verification/startup-adaptive-x86-qualification.json

|2026-11-01 |1.73 | Freeze and locally verify distinct A3 non-emulated correctness/CPU handoff |128+128main/276+276A3/39+39controller cases and60CPU samples pass;1,602-file/member capsule and5,757prior files preserved. One new unlaunched1h4CPU32GiB qualification command only; original code/tests/limits/memory decision unchanged, no SSH/Torch/search or spent-allowance reuse; native target/full CPU/memory/B2f pending or held |

[E392]: ../trials/torch-reviews-startup-adaptive-x86-qualification-v1/postrun-audit-2026-11-01/archive-inventory.json
[E393]: ../trials/torch-reviews-startup-adaptive-x86-qualification-v1/postrun-audit-2026-11-01/verification.json
[E394]: ../trials/torch-reviews-startup-adaptive-x86-qualification-v1/postrun-audit-2026-11-01/case-timing.json
[E395]: ../trials/torch-reviews-startup-adaptive-x86-qualification-v1/postrun-audit-2026-11-01/REPORT.md
[E396]: ../agent/docs/verification/startup-adaptive-x86-qualification-postrun.json

|2026-11-01 |1.74 | Verify failed native A3 qualification and close its allowance | Job 21595967 FAILED/22m46s: main 128+128 pass, A3 165 passes/one interrupted at 600s, sealed/CPU unstarted. All 38 return members, failed locks, source/image/cleanup, exact hardware/reference and 5,757 prior files verify. Tests/limits/zero searches preserved; offline fixture-cost design next, no retry/new native release |

[E397]: ../trials/torch-reviews-startup-adaptive-fixture-cost-v1/REVIEW-FREEZE.json
[E398]: ../trials/torch-reviews-startup-adaptive-fixture-cost-v1/CORRECTION-FREEZE.json
[E399]: ../trials/torch-reviews-startup-adaptive-fixture-cost-v1/baseline-profile/profile.json
[E400]: ../trials/torch-reviews-startup-adaptive-fixture-cost-v1/verification.json
[E401]: ../trials/torch-reviews-startup-adaptive-fixture-cost-v1/REPORT.md
[E402]: ../agent/docs/verification/startup-adaptive-fixture-cost.json

|2026-11-01 |1.75 | Freeze and locally verify an equivalent A3 fixture path checker after complete cost review | 128+128 main/276+276 A3/26+26 helper pass; 7,490 prior files and all original source/tests/limits preserved. Same 292,688 hashes/341,707 fresh resolutions/975,641 symlink observations; unused Python ancestors avoided. Native 600s fit/CPU/memory/resource held; no Torch launch, native command/capsule, new allowance or reuse |

[E403]: ../trials/torch-reviews-startup-adaptive-budget-storage-v1/REVIEW-FREEZE.json
[E404]: ../trials/torch-reviews-startup-adaptive-budget-storage-v1/CORRECTION-FREEZE.json
[E405]: ../trials/torch-reviews-startup-adaptive-budget-storage-v1/capacity-plan.json
[E406]: ../trials/torch-reviews-startup-adaptive-budget-storage-v1/verification.json
[E407]: ../trials/torch-reviews-startup-adaptive-budget-storage-v1/REPORT.md
[E408]: ../agent/docs/verification/startup-adaptive-budget-storage.json

|2026-11-01 |1.76 | Complete A3 native budget/storage feasibility review with local and native release held | Fixed caps close; conditional6.87GiB/22,498-entry plan and35+35units pass,1,602archive members/10,076prior files verify. Mac~4GiBfree<8GiBguard prevents full real staging/replay. Original tests/checks/limits intact; no Torch launch, native capsule/command, new allowance or reuse |
[E409]: ../trials/torch-reviews-a3-mac-space-preservation-v1/SPACE-PLAN.json
[E410]: ../trials/torch-reviews-a3-mac-space-preservation-v1/apply-code-pin-attempt-2.json
[E411]: ../trials/torch-reviews-a3-mac-space-preservation-v1/verification.json
[E412]: ../trials/torch-reviews-a3-mac-space-preservation-v1/REPORT.md
[E413]: ../agent/docs/verification/a3-mac-space-preservation.json
[E414]: ../trials/torch-reviews-startup-adaptive-budget-storage-v1/full-local-replay-20261101-v1/EXECUTION-FREEZE.json
[E415]: ../trials/torch-reviews-startup-adaptive-budget-storage-v1/full-local-replay-20261101-v2/EXECUTION-FREEZE.json
[E416]: ../trials/torch-reviews-startup-adaptive-budget-storage-v1/full-local-replay-20261101-v3/EXECUTION-FREEZE.json
[E417]: ../trials/torch-reviews-startup-adaptive-budget-storage-v1/full-local-replay-20261101-v4/EXECUTION-FREEZE.json
[E418]: ../trials/torch-reviews-startup-adaptive-budget-storage-v1/full-local-replay-20261101-v4/verification.json
[E419]: ../trials/torch-reviews-startup-adaptive-budget-storage-v1/full-local-replay-20261101-v4/REPORT.md
[E420]: ../agent/docs/verification/startup-adaptive-full-local-replay.json
[E421]: ../trials/torch-reviews-startup-native-harness-integration-v1/DESIGN-FREEZE.json
[E422]: ../trials/torch-reviews-startup-native-harness-integration-v1/NATIVE-ADAPTER-FREEZE.json
[E423]: ../trials/torch-reviews-startup-native-harness-integration-v1/IMPLEMENTATION-PIN.json
[E424]: ../trials/torch-reviews-startup-native-harness-integration-v1/verification.json
[E425]: ../trials/torch-reviews-startup-native-harness-integration-v1/failure-recovery-proof.json
[E426]: ../trials/torch-reviews-startup-native-harness-integration-v1/headroom/attempt-2/reclaim-result.json
[E427]: ../trials/torch-reviews-startup-native-harness-integration-v1/REPORT.md
[E428]: ../agent/docs/verification/startup-native-harness-integration.json

[E429]: ../trials/torch-reviews-startup-native-release-review-v1/REVIEW-FREEZE.json
[E430]: ../trials/torch-reviews-startup-native-release-review-v1/CORRECTION-FREEZE.json
[E431]: ../trials/torch-reviews-startup-native-release-review-v1/release-findings.json
[E432]: ../trials/torch-reviews-startup-native-release-review-v1/verification.json
[E433]: ../trials/torch-reviews-startup-native-release-review-v1/completion-checks.json
[E434]: ../trials/torch-reviews-startup-native-release-review-v1/REPORT.md
[E435]: ../agent/docs/verification/startup-native-release-review.json

[E436]: ../trials/torch-reviews-startup-native-authority-ownership-v1/DESIGN-FREEZE.json
[E437]: ../trials/torch-reviews-startup-native-authority-ownership-v1/FAILURE-CLEANUP-FREEZE.json
[E438]: ../trials/torch-reviews-startup-native-authority-ownership-v1/IMPLEMENTATION-PIN.json
[E439]: ../trials/torch-reviews-startup-native-authority-ownership-v1/verification.json
[E440]: ../trials/torch-reviews-startup-native-authority-ownership-v1/prior-replay-reverification.json
[E441]: ../trials/torch-reviews-startup-native-authority-ownership-v1/REPORT.md
[E442]: ../agent/docs/verification/startup-native-authority-ownership.json

[E443]: ../trials/torch-reviews-startup-native-integrated-release-v1/DESIGN-FREEZE.json
[E444]: ../trials/torch-reviews-startup-native-integrated-release-v1/CONTROL-READ-BUDGET-FREEZE.json
[E445]: ../trials/torch-reviews-startup-native-integrated-release-v1/SITE-OBSERVATION-FREEZE.json
[E446]: ../trials/torch-reviews-startup-native-integrated-release-v1/final/IMPLEMENTATION-PIN.json
[E447]: ../trials/torch-reviews-startup-native-integrated-release-v1/final/verification.json
[E448]: ../trials/torch-reviews-startup-native-integrated-release-v1/final/completion-checks.json
[E449]: ../trials/torch-reviews-startup-native-integrated-release-v1/final/package-verification.json
[E450]: ../trials/torch-reviews-startup-native-integrated-release-v1/REPORT.md
[E451]: ../agent/docs/verification/startup-native-integrated-release.json
[E452]: ../trials/torch-reviews-startup-native-integrated-release-v1/final/TORCH-SITE-CHECK.txt
[E453]: ../trials/torch-reviews-startup-native-integrated-release-v1/final/COMMANDS-PENDING-AUTHORIZATION.txt

[E454]: ../trials/torch-reviews-startup-native-site-compatibility-v1/DESIGN-FREEZE.json
[E455]: ../trials/torch-reviews-startup-native-site-compatibility-v1/observations.json
[E456]: ../trials/torch-reviews-startup-native-site-compatibility-v1/IMPLEMENTATION-PIN.json
[E457]: ../trials/torch-reviews-startup-native-site-compatibility-v1/verification.json
[E458]: ../trials/torch-reviews-startup-native-site-compatibility-v1/prior-verification.json
[E459]: ../trials/torch-reviews-startup-native-site-compatibility-v1/package-verification.json
[E460]: ../trials/torch-reviews-startup-native-site-compatibility-v1/REPORT.md
[E461]: ../trials/torch-reviews-startup-native-site-compatibility-v1/TORCH-SITE-CHECK.txt

[E462]: ../trials/torch-reviews-startup-native-site-compatibility-v1/site-readiness-review-2026-11-03/site-check-return.json
[E463]: ../trials/torch-reviews-startup-native-site-compatibility-v1/site-readiness-review-2026-11-03/review.json
[E464]: ../trials/torch-reviews-startup-native-site-compatibility-v1/site-readiness-review-2026-11-03/TORCH-APPROVE-AND-SUBMIT-PENDING.txt
[E465]: ../agent/docs/verification/startup-native-site-readiness.json

[E466]: ../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/submission-return.json
[E467]: ../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/review.json
[E468]: ../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/TORCH-STATUS.txt
[E469]: ../agent/docs/verification/startup-native-qualification-submitted.json

[E470]: ../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/failure-review-2026-11-03/reported-terminal.json
[E471]: ../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/failure-review-2026-11-03/review.json
[E472]: ../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/failure-review-2026-11-03/TORCH-COLLECT-AND-TRACEBACK.txt
[E473]: ../agent/docs/verification/startup-native-qualification-preflight-failure.json

[E474]: ../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/failure-review-2026-11-03/slurm-conf-trace-review/finding.json
[E475]: ../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/failure-review-2026-11-03/download-return-21756110.sh
[E476]: ../agent/docs/verification/startup-native-slurm-conf-failure-review.json

[E477]: ../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/failure-review-2026-11-03/raw-return-review/archive-verification.json
[E478]: ../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/failure-review-2026-11-03/raw-return-review/TORCH-CONFIG-METADATA.txt
[E479]: ../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/failure-review-2026-11-03/raw-return-review/preservation-verification.json
[E480]: ../agent/docs/verification/startup-native-return-21756110-review.json

[E481]: ../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/failure-review-2026-11-03/metadata-unavailable-review/user-return.json
[E482]: ../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/failure-review-2026-11-03/metadata-unavailable-review/finding.json
[E483]: ../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/failure-review-2026-11-03/metadata-unavailable-review/NYU-HPC-REQUEST.txt
[E484]: ../agent/docs/verification/startup-native-configuration-metadata-unavailable.json

[E485]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/DESIGN-FREEZE.json
[E486]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/REVIEW.txt
[E487]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/PRESERVATION.json
[E488]: ../agent/docs/verification/startup-native-pinned-client-configuration-design.json

[E489]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/capture-v1/CAPTURE-FREEZE.json
[E490]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/capture-v1/verification.json
[E491]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/capture-v1/preservation-verification.json
[E492]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/capture-v1/TORCH-CAPTURE.txt

[E493]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/capture-return-9rki9gow/reported-receipt.json
[E494]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/capture-return-9rki9gow/finding.json
[E495]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/capture-return-9rki9gow/download-return.sh
[E496]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/capture-return-9rki9gow/download-checks.json

[E497]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/snapshot-review-v1/raw-verification.json
[E498]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/snapshot-review-v1/configuration-inventory.json
[E499]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/snapshot-review-v1/source-review.json
[E500]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/snapshot-review-v1/CONFIGURATION-USE-FREEZE.json
[E501]: ../agent/docs/verification/startup-native-captured-configuration-review.json

[E502]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/compatibility-v1/HARNESS-FREEZE.json
[E503]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/compatibility-v1/IMPLEMENTATION-PIN.json
[E504]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/compatibility-v1/verification.json
[E505]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/compatibility-v1/final-preservation-verification.json
[E506]: ../agent/docs/verification/startup-native-client-configuration-compatibility.json

[E507]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-command-v1/COMMAND-FREEZE.json
[E508]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-command-v1/verification.json
[E509]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-command-v1/preservation-verification.json
[E510]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-command-v1/upload-from-mac.sh
[E511]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-command-v1/TORCH-INSPECT.txt
[E512]: ../agent/docs/verification/startup-native-login-dependency-command-ready.json

[E513]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-command-v1/sftp-upload-correction-v1/TRANSPORT-FREEZE.json
[E514]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-command-v1/sftp-upload-correction-v1/verification.json
[E515]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-command-v1/sftp-upload-correction-v1/preservation-verification.json
[E516]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-command-v1/sftp-upload-correction-v1/upload-from-mac.sh
[E517]: ../agent/docs/verification/startup-native-dependency-sftp-transport-correction.json

[E518]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/verification-cost-correction-v1/DESIGN-FREEZE.json
[E519]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/verification-cost-correction-v1/verification.json
[E520]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/verification-cost-correction-v1/exact-target-verification.json
[E521]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/verification-cost-correction-v1/upload-from-mac.sh
[E522]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/verification-cost-correction-v1/TORCH-INSPECT.txt
[E523]: ../agent/docs/verification/startup-native-login-verification-cost-correction.json

[E524]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-return-xgzm0ve9/reported-result.json
[E525]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-return-xgzm0ve9/DOWNLOAD-FREEZE.json
[E526]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-return-xgzm0ve9/verification.json
[E527]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-return-xgzm0ve9/download-from-mac.sh
[E528]: ../agent/docs/verification/startup-native-dependency-inspection-reported.json

[E529]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-review-xgzm0ve9-v1/raw-verification.json
[E530]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-review-xgzm0ve9-v1/metadata-review.json
[E531]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-review-xgzm0ve9-v1/DESIGN-FREEZE.json
[E532]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-review-xgzm0ve9-v1/verification.json
[E533]: ../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-review-xgzm0ve9-v1/upload-from-mac.sh
[E534]: ../agent/docs/verification/startup-native-dependency-capture-review.json
