# Execution cost attribution v1: results and decision

Analyzed October 23, 2026. Campaign: `reviews-execution-cost-v1-20261023T044408Z.a08qpwdi`.

The experiment supports moving from cost attribution to one bounded execution-lifecycle revision. The frozen policy again saves time on reuse and loses time on activation. Function counts and the preserved source identify repeated validation, copying, identity construction, and query normalization as concrete engineering targets. No optimized path was tested, and no policy was selected or independently confirmed.

## Verification and scope

The [postrun receipt][receipt] records independent local analysis with the sealed package. All three blocks completed with successful runtime/host exits, unchanged protected sources, the expected native module/image/profile/index identities, and complete result/proof/profile coverage. The primary pass and diagnostic pass reproduce the pinned reference results and expected stopping behavior.

The local [timing report][timing] and [function attribution][profiles] are byte-identical to Torch's copies. Every discrete value in the complete performance report matches. One confidence-interval endpoint differs by `1.39e-17`, within the protocol's `1e-12` absolute tolerance. The [local verifier result][verification] passes. Returned code was treated as data; analysis used the previously sealed local scripts.

| Item | Actual evidence |
| --- | ---: |
| Completed serial allocations | 3 |
| Independent development vectors / query-filter cases | 200 / 600 |
| Profiled subset: independent vectors / cases | 60 / 180 |
| Primary retained pairs / discarded warmup pairs | 21,600 / 5,400 |
| Diagnostic retained pairs / discarded warmup pairs | 6,480 / 1,620 |
| Backend/reference searches | 83,763 |
| Explicit control eviction installations, counted separately | 7,020 |
| Provider calls / confirmation queries | 0 / 0 |
| Sum of reported internal block elapsed time | 4,307.05 seconds, approximately 71.78 minutes |

Internal elapsed time is not a Slurm billing record. The 200 vectors are the independent units; filters, timing repetitions, and blocks do not increase that count. The profiling subset is drawn from those same development vectors.

## Primary timing: the earlier pattern repeats

These are unprofiled arithmetic mean latencies. Each arm is compared with its own randomized paired ordinary-native baseline. Activation means a newly constructed policy session with installation/prepared-cache eviction; it does not mean cold database buffers.

| Arm | Regime | Paired native ms | Arm ms | Change against native |
| --- | --- | ---: | ---: | ---: |
| Frozen `cons-bypass108` candidate | Activation | 7.841534 | 9.629314 | 22.799% slower |
| Frozen candidate | Reuse | 6.134988 | 5.745601 | 6.347% faster |
| Same conditions, all leaves continue | Activation | 7.842175 | 11.606193 | 47.997% slower |
| Same conditions, all leaves continue | Reuse | 6.007781 | 7.094731 | 18.092% slower |
| Routed-native, empty eligibility mask | Activation | 6.565397 | 8.068760 | 22.898% slower |
| Routed-native | Reuse | 5.803784 | 5.925975 | 2.105% slower |

For the candidate, activation adds **1.787779 ms**, with a vector-group bootstrap 95% interval of **[1.610250, 1.965372] ms**. Reuse saves **0.389387 ms**, interval **[0.252834, 0.527575] ms**. The prespecified mean log latency-ratio intervals also show an activation loss, `[0.188264, 0.222782]`, and a reuse benefit, `[-0.120062, -0.070658]`.

The direction is consistent in every block. Candidate activation is 16.357%, 25.431%, and 27.452% slower; reuse is 10.284%, 4.790%, and 3.937% faster. The changing magnitude argues for retaining paired/block reports in the next study. Comparing this pooled percentage with the earlier pilot's 7.193% reuse saving is not a controlled estimate of a change between campaigns.

Outer application time preserves the same conclusion: the candidate adds 1.547864 ms on activation and saves 0.608008 ms on reuse; routed-native adds 1.516592 ms and 0.133918 ms respectively. The numerical primary and outer results remain distinct.

### Quality and selective application

All retained outputs are valid top-10 results. Native mean recall is 99.35% for unfiltered queries, 99.15% for `votes32`, and 98.60% for `votes108`, satisfying the native floor.

Candidate recall differs from native by **-0.016667 percentage points overall**, interval **[-0.050000, 0.000000] percentage points**. The loss is confined to `votes32`: -0.050000 percentage points, interval [-0.150000, 0.000000]. These bounds satisfy the existing development reserve and final relative-recall margin. They are repeated measurements of already exposed vectors, not fresh evidence of generalization.

| Candidate stratum, reuse | Measured gap vs its paired native | Interpretation |
| --- | ---: | --- |
| Unfiltered | 0.673094 ms faster, approximately 10.816% | Useful stopping signal on development data |
| `votes32` | 0.623534 ms faster, approximately 9.762% | Useful stopping signal with the small recorded recall loss |
| `votes108` | 0.128467 ms slower, approximately 2.217% | Native bypass still pays the surrounding interface cost |

The candidate passes the descriptive reuse checks and fails activation. The joint current criterion therefore remains unmet. This campaign performs no candidate selection, and the earlier agent episode remains closed with abstention.

## Cost ledger and function attribution

### The unprofiled categories reconcile

| Arm / regime | Preparation ms | Routing ms | Backend timer ms | Total ms |
| --- | ---: | ---: | ---: | ---: |
| Candidate / activation | 1.558956 | 0.180726 | 7.889632 | 9.629314 |
| Candidate / reuse | 0 | 0.136274 | 5.609327 | 5.745601 |
| Matched continue / activation | 1.579670 | 0.183090 | 9.843433 | 11.606193 |
| Matched continue / reuse | 0 | 0.139356 | 6.955375 | 7.094731 |
| Routed-native / activation | 1.293546 | 0.153933 | 6.621281 | 8.068760 |
| Routed-native / reuse | 0 | 0.115871 | 5.810105 | 5.925975 |

The report calls the backend component `ANN ms`. Its timer includes Python policy preparation, statement construction, database requests, transport, and decoding; it is not an isolated engine-search timer. A zero preparation value on reuse means session construction is no longer charged. It does not mean policy preparation has disappeared inside the backend timer.

At pooled means, candidate activation's preparation plus routing is 1.739682 ms, compared with its 1.787779 ms measured gap. Routed-native preparation plus routing is 1.447479 ms, compared with a 1.503362 ms gap. These are arithmetic reconciliations of recorded categories, not predictions that all of that work can be eliminated. The entire gap must be remeasured after an actual revision.

### Preparation repeatedly constructs identities and validates policy structure

Across all blocks and filters, candidate session preparation averages 3.024189 ms under profiling, compared with the unprofiled 1.558956 ms preparation category. The diagnostic times are perturbed and cannot be substituted into primary timing.

Per candidate session construction, profiles record:

- Four runtime-profile fingerprint evaluations, with 1.122580 ms inclusive diagnostic time in total.
- Eight JSON encoder calls, with 0.761796 ms exclusive diagnostic time.
- Five model-serialization calls, with 0.292476 ms exclusive diagnostic time.
- 299 recursive `deepcopy` entries and 146 recursive policy-tree visits.

These are recursive function-entry counts, not 299 complete copies or 146 full-policy validations. Fingerprint time includes serialization descendants, so it must not be added to the JSON/model times. The frozen [profile fingerprint implementation][fingerprint-source] serializes the profile each time; the [core validator][validator-source] and [composite validator][composite-source] request that identity repeatedly. Ownership copies and bounds/feature/guard checks also account for preparation work.

### The prepared cache still does work before a hit

On eligible candidate reuse queries, the diagnostic records one `PreparedPolicyCache.prepare` call, two `validate_node` calls, 146 recursive tree visits, 287 recursive `deepcopy` entries, and one policy JSON encoding per query. For the unfiltered stratum across the three blocks, `prepare` averages 1.356025 ms inclusive diagnostic time per query.

The [frozen cache source][cache-source] explains the order: validate the original tree, own/copy the input, validate the owned tree, serialize it, check plain-JSON semantics, construct the content key, then look up the cached prepared policy. Reusing a compiled artifact therefore retains substantial work needed to establish that a mutable caller-supplied object is still the same valid input.

This is the strongest bounded P2 target. A backend-owned, validated policy handle could preserve ownership and compatibility while avoiding re-establishing the same artifact identity on every query. Whether that design is safe and fast remains to be qualified and measured. The profiled 1.356025 ms is not an expected unprofiled saving.

### Routing is largely a query-boundary question

`Session.query` normalizes the query through `snapshot().query` before selecting its branch. Eligible policy execution normalizes it again inside `_execute_probe`; bypass does so once. The profile call counts reproduce those paths.

For routed-native unfiltered reuse, `snapshot().query` averages 0.184249 ms inclusive diagnostic time; the predicate `route` function averages approximately 0.000806 ms. This example identifies query validation/normalization as a more plausible target than the small branch-selection function. The primary routed-native routing category is 0.115871 ms across all strata.

The backend also formats all 768 vector values into SQL parameters on each call. That work is shared with ordinary native execution and is not established as the cause of the differential overhead. No native-side function profile was collected. Any later query-representation or statement change needs a matched comparison with equivalent normalization and numeric semantics.

### Database wait is an unresolved boundary

`psycopg.connection.wait` dominates profiled query duration. That frame combines time waiting for real database/search work and communication; this Python profile cannot separate server ANN work, interpreter work, scheduling, and transport. It does not establish that extra SQL round trips or a particular engine operation are the dominant removable cost.

Matched continue's 1.086950 ms reuse penalty confirms a cost to taking the policy path without useful stopping. It does not assign that entire penalty to validation or SQL. Retain a focused server/transport diagnostic as a conditional follow-up if residual costs after the first lifecycle change prevent G2 from closing.

## Lifetimes and the next bounded comparison

This table proposes lifetimes; it does not certify the proposed implementation.

| Operation | Proposed lifetime | Required preservation or invalidation rule |
| --- | --- | --- |
| Runtime profile fingerprint / derived feature kinds | Backend-owned immutable profile snapshot | New identity or rejection when semantic profile changes; caller mutation cannot alter the snapshot |
| Composite/tree validation, ownership copy, semantic identity | Owned policy artifact or prepared session | Full validation on admission/change; no shared mutable caller tree; preserve type, size, depth, nonfinite-value, feature and guard rejection |
| Prepared tree, feature groups, lazy bytecode | Backend-owned artifact bound to the qualified profile | Preserve cache limits, compilation/installation accounting, eviction, reset, errors, and cross-backend isolation |
| Installation acknowledgement | Live connection plus installed artifact identity | Reinstall after eviction or relevant connection/reset transition; never infer installation from an artifact cache hit |
| Connection ownership / closed-state checks | Each query | Preserve current failure semantics; no replay after a failed policy execution |
| Query/filter normalization, vector numeric checks, routing | Each distinct query | One authoritative boundary where feasible; preserve actual-predicate routing, dimensions, finite/normalization rules, k and identifier mapping |
| SQL/transport and server execution | Each execution | Remains measured; optimize only under a separately bounded hypothesis |

The proposed sequence is:

1. **P2 contract:** declare practical activation/reuse/bypass targets, one initial conceptual revision, resource ceilings, and a finite reassessment allowance. Program-wide P0 and confirmation entitlements remain unresolved.
2. **P2a:** qualify owned prepared-policy state, including stable profile identity and artifact ownership. Keep cheap per-query connection/install checks. Full first-time admission, compilation, installation and all required setup remain visible in activation and outer application accounting.
3. **P2 measurement:** compare the unchanged candidate, matched continue and routed-native with their own paired native baselines under old/new execution identities. Preserve all filters, primary timing, outer timing, output proofs and grouped uncertainty. Freeze policies throughout.
4. **G2 decision:** accept a measured execution revision, retain the original path under a bounded earlier-stopping investigation, or redirect. If bypass/query-boundary overhead remains above the prospective budget, consider one separate normalization revision; if database wait is the blocker, specify a focused diagnostic before a database-side rewrite.
5. **P3 onward:** remeasure the broader frozen policy set and diagnose decision/feature/outcome limits before numerical search, acquisition, or workflow changes.

G1 passes as an attribution gate: major preparation and hot-path mechanisms have evidence, unresolved database wait has an explicit limit, and the next conceptual change is bounded. G2, M1, M2, M3 and canonical serving acceptance remain unestablished. No implementation or remote experiment is authorized merely by this analysis.

## Artifact identities and sources

| Artifact | SHA-256 |
| --- | --- |
| Returned archive | `0c4dc6e995891a488de502cd11ffaed549a65a233064decf4a692fe638704d3e` |
| Sealed package manifest | `4c2f475664784b1851b1274a5c696bccbc55ee41c659a469c3643eb0ca0109c0` |
| Postrun receipt | `16647a2486df6f191a764f4600e17ee2437f01352edc76eb3646490ca3b90378` |

The [frozen design][design], [complete performance data][performance], [verification receipt][receipt], and the source links above are the primary sources for this result. Academic/framework sources remain in the [research roadmap][roadmap]; no new literature review was needed to interpret this measured campaign.

[receipt]: ../agent/docs/verification/execution-cost-attribution-v1-postrun.json
[timing]: ../trials/torch-reviews-execution-cost-attribution-v1/analysis-local/reviews-execution-cost-v1-20261023T044408Z.a08qpwdi/report.txt
[profiles]: ../trials/torch-reviews-execution-cost-attribution-v1/analysis-local/reviews-execution-cost-v1-20261023T044408Z.a08qpwdi/attribution.md
[verification]: ../trials/torch-reviews-execution-cost-attribution-v1/analysis-local/reviews-execution-cost-v1-20261023T044408Z.a08qpwdi/verification.json
[performance]: ../trials/torch-reviews-execution-cost-attribution-v1/analysis-local/reviews-execution-cost-v1-20261023T044408Z.a08qpwdi/performance.json
[design]: ../agent/experiments/execution-cost-attribution-v1/DESIGN.md
[roadmap]: fannagent-performance-research-roadmap-2026-10-22.md
[fingerprint-source]: ../trials/torch-reviews-execution-cost-attribution-v1/torch-execution-cost-attribution-v1/frozen/vendor/fannagent/api/profiles.py
[validator-source]: ../trials/torch-reviews-execution-cost-attribution-v1/torch-execution-cost-attribution-v1/frozen/vendor/fannagent/api/policy.py
[composite-source]: ../trials/torch-reviews-execution-cost-attribution-v1/torch-execution-cost-attribution-v1/frozen/policy.py
[cache-source]: ../trials/torch-reviews-execution-cost-attribution-v1/torch-execution-cost-attribution-v1/frozen/vendor/fannagent_pgvector/prepared.py
