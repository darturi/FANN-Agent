# FANNAgent benchmark evaluation roadmap

Created: November 10, 2026.  
Status: Phase 0 inventory and reservation review complete; clean query split frozen. Phase 1 protocol is finalized; original-graph development runtime qualification and the new agent episode remain pending.  
Immediate priority: User-run the sealed single reader/CPU/work attribution diagnostic; original timing module, separate counter stage, all six filters and no holdout access. Preserve an inconclusive/negative agent outcome.
Planning horizon: November 2026 through January 2027, subject to results and implementation effort.

## 1. Objective and intended claims

Demonstrate that FANNAgent can generate an executable filtered ANN policy that preserves measured recall and reduces query latency relative to native execution. Establish the result on MoReVec first, investigate scale within that benchmark, then repeat the procedure on two additional published filtered ANN datasets.

Query latency is the primary performance outcome. Measure the complete request on an open reader, including feature collection, policy evaluation, execution, continuation, and result decoding. Report shared lookup construction, connection setup, lookup attachment, warm-up, and full-session costs separately. Setup can be amortized when the assumed lookup and connection lifetimes are explicit.

The research should distinguish three claims:

| Claim | Evidence required |
| --- | --- |
| A useful policy exists on a specified workload | A frozen agent-generated policy passes an independent recall and latency comparison on that workload. |
| The agent procedure works across workloads | The same documented procedure produces separately evaluated policies on three datasets, with unsuccessful episodes included. |
| One policy transfers across sizes or datasets | An unchanged policy is evaluated in those new settings. This is a separate, secondary question. |

Success on one predicate or dataset does not establish the other claims. A finite test establishes evidence within its sampled workload; it cannot guarantee recall preservation for every future query.

This document records a completed query-inventory/reservation audit and defines subsequent experiments. It leaves historical results and their original classifications intact. Its proposed thresholds and resource allocations must be recorded in the relevant experiment protocol before execution; writing this roadmap does not launch jobs or spend provider credits.

### Clean restart decision — November 10, 2026

The user authorized a new policy-generation episode after checking reserved-query exposure. MoReVec supplies a corpus and a published query workload, not an official development/validation/test partition for learning policies. Our clean split is researcher-defined and keeps each vector group together across every predicate and overlapping scale.

The initial Phase 0 pass conservatively excluded every historical query-inventory reference. The subsequent reservation review checked read-only broker state, execution summaries, private study assignments, and 125 saved JSON/JSONL evidence files (99 distinct contents). It recovered the original 150 calibration and 150 test groups: no calibration/test consumption state, no protected-scope outcome artifacts, and no saved outcome hits for their canonical query IDs were found. This is evidence within recorded local history, not a guarantee against unrecorded access.

The later 37-group “reserved” pool is **not** a fresh holdout. All 37 already have stop labels and query-specific recall/latency measurements from the earlier fixed-bounded development run. They remain development groups in this restart. Reservation names do not override prior outcome exposure.

| Frozen role | Independent vector groups | Basis |
| --- | ---: | --- |
| Development | 450 | Original development population, including all historical consumed evaluations and the later 37-group reservation with prior outcomes |
| Validation | 150 | Original protected calibration partition, recovered by the reservation review |
| Test | 275 | Original protected 150 test groups plus all 125 groups without historical query-inventory references |
| Excluded historical | 125 | Earlier workload; retained outside validation/test |

Preserve the original calibration/test roles rather than randomly reshuffling previously studied queries. All seven published conditions and `k=10` are in the intended initial scope. Runtime qualification must establish support on development data; any scope reduction must be fixed before validation selection and test outcomes.

Authoritative artifacts: [reservation review](../trials/fannagent-benchmark-evaluation-v1/inventory/reservation-review.md), [frozen split](../trials/fannagent-benchmark-evaluation-v1/reviews-small/splits/split-manifest.json), [split seal](../trials/fannagent-benchmark-evaluation-v1/reviews-small/freeze/split-freeze.json), and [restart procedure](../trials/fannagent-benchmark-evaluation-v1/reviews-small/protocol/restart-plan.md). The earlier 25-validation/100-test proposal is superseded and preserved under `inventory/snapshots/phase0-provisional/`; it was never executed.

With zero recall-losing groups on the 275-group test, the exact one-sided 95% upper loss-probability bound is approximately 1.0834%. This improves the earlier 2.95% bound but still does not establish worst-case population mean-recall noninferiority within 0.25 percentage points. Phase 1 must state the achievable claim and prespecify suitable recall inference before execution.

Rerun the agent using only development evidence, with grouped folds, recorded prompts/tools/cost, and a fixed proposal budget. The previous policy remains a historical comparator; it cannot replace the requested fresh episode. Freeze the proposal pool and deterministic selection rule before a single bounded validation selection. Do not revise proposals in response to validation. Freeze the selected policy, all baseline settings, analysis and timing schedule before test. Reuse qualified runtime machinery subject to applicability checks.

The split is binding now; model/version, scientific thresholds, runtime qualification, provider usage reconciliation, and the complete study protocol must be fixed before the new episode. This decision does not launch provider calls or remote searches.

### Protocol finalized; original-graph runtime qualification pending

The [study protocol](../trials/fannagent-benchmark-evaluation-v1/reviews-small/protocol/study-protocol.md) and [configuration](../trials/fannagent-benchmark-evaluation-v1/reviews-small/protocol/config.json) are fixed and sealed by [protocol freeze v2](../trials/fannagent-benchmark-evaluation-v1/reviews-small/freeze/protocol-freeze-v2.json). These resolve the roadmap's earlier proposals: finite held-out workload recall preservation with zero per-query losses, .0025 recorded mean-recall margin without an unsupported population-noninferiority claim, .95 adequacy floor, equal weighting of six scalar filters, a separate unfiltered control, tuned-native/fixed/turnover grids, up to nine fresh agent proposals in three rounds/$15, one validation batch, five test allocations/four epochs, paired hierarchical analysis, two primary comparisons with Bonferroni adjustment, 5% practical latency target and 2% identical-code equivalence controls. The protocol, rather than remaining generic recommendations below, governs this study.

An isolated all-predicate runtime module compiled and passed synthetic PostgreSQL smoke across all seven conditions, plus eight focused checks. The full inherited restore loader could not complete under local amd64 emulation (QEMU SIGSEGV); that is retained as an unresolved local target limitation, not called a runtime pass. Native Torch original-graph qualification is mandatory. The user will run the [sealed development-only kit commands](../trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/COMMANDS.txt). The active kit is version2; version1 was an undispatched local draft. See [qualification status](../trials/fannagent-benchmark-evaluation-v1/reviews-small/runtime/qualification-status.md). No provider calls, validation/test searches or new remote jobs have been executed by Codex. Do not rerun the agent until the native return is independently verified and provider usage is reconciled.

### November 11: native640 qualification verified; stronger parent selected as next step

Job 22635567 completed and its return passed local reconstruction for all 3,150 development records, all 7,940 forced outputs, no-stop parity, first-stop decisions, exact eligibility/tie scoring, raw hashes and summary counts. Runtime semantics at native640 are qualified; this does not establish scientific adequacy. Mean native recall is 53.49%/78.98%/94.82% at votes743/527/310, below the fixed 95% floor, with 345/172/23 incomplete outputs. The native640 all-filter generation episode therefore cannot meet the frozen objective. No model call was made.

The user explicitly chose to retain all six scalar filters and strengthen/requalify the native parent. Preserve native640 and its outcome as historical continuity. The [prospective parent plan](../trials/fannagent-benchmark-evaluation-v1/reviews-small/protocol/parent-requalification-plan-v1.json) fixes a development-only sweep at ef_search 640/1000/2048/4096/8192, selecting the smallest common setting meeting >=95% mean recall per condition and ten results for every query. The only engine-source changes are the GUC ceiling and description; settings above 1000 are explicitly extended-effort research execution, not stock pgvector. The graph, metric and frozen query split stay fixed. All seven synthetic smoke conditions passed at 8192. One [sealed Torch kit](../trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/PARENT-COMMANDS.txt) performs the sweep and full requalification at the selected parent. If no setting qualifies, preserve a bounded negative; do not expand the grid automatically.

Before agent generation, verify that return and prospectively pin the new parent/module, primary parent comparator and consistent static-native grid in a protocol amendment. Do not relax recall thresholds or change/open holdout groups. See the [verified result report](../trials/fannagent-benchmark-evaluation-v1/reviews-small/reports/native640-qualification-22635567.md).

### November 11: stronger-parent sweep verified negative

Job 22643346's exit 3 is the predeclared no-adequate-parent result. Its archive, all 15,750 development sweep observations (35 cells), exact-reference recall/completeness scores, eligibility sets and all 3,150 native640 continuity comparisons reconstructed. At 8192 the only incomplete case is `reviews-clean-v0196-votes743` (published ID `r216749`): eight true top 10 neighbors returned, exact ranks 7/9 missing, despite 2475 eligible corpus records. There is no 8192 traversal trace in the negative return; do not infer the precise internal omission mechanism. No agent/holdout calls ran.

Keep all six filters and preserve both native-only failures. The [inspection and recommendation](../trials/fannagent-benchmark-evaluation-v1/reviews-small/reports/parent-sweep-22643346.md) proposes a common exact completion guard: replace a short completed ANN result with exact filtered top 10, identically on native and agent paths, and charge every attempt/guard/fallback in serving time. A labeled offline development replay meets recall/completeness at every existing grid point, but is not a live qualification or latency result. A prospective bounded guard experiment should measure the existing grid and select one common adequate parent by serving cost before model generation. Native iterative scanning remains an alternative baseline/runtime revision; the retained live path currently rejects its discarded-candidate continuation. Do not silently extend the ceiling, drop the hard query/filter, relax criteria, or describe a hybrid parent as unmodified native. No new experiment is launched by this recommendation.

### November 11: common completion guard implemented and kit sealed

The user authorized a common guard on native and agent execution across all six filters. [Implementation](../trials/fannagent-benchmark-evaluation-v1/reviews-small/runtime-guard-v1/README.md) uses one shared function, one exported repeatable-read snapshot, a persistent forced-exact reader, replacement of short outputs, and a timer covering both requests/decoding/guard work. Corruption errors remain errors. Seven unit checks and seven-condition real PostgreSQL fixture checks passed on native and real no-stop policy paths, with short/full responses. The extended-effort module is unchanged from the prior sweep; original-graph guarded execution is not yet qualified.

The [prospective amendment](../trials/fannagent-benchmark-evaluation-v1/reviews-small/protocol/completion-guard-amendment-v1.md) and [sealed plan](../trials/fannagent-benchmark-evaluation-v1/reviews-small/protocol/completion-guard-plan-v1.json) fix all 450 development groups, the existing five effort settings, 15,750 paired quality rows and 126,000 timed requests across four labels/two balanced epochs. Select the adequate common parent by equal-six-filter native guarded serving cost (within 1% choose larger effort), then requalify exact/capture/forced/historical policy paths at that setting. This is development selection on one allocation; preserve all controls and do not claim confirmatory speed. Lifecycle setup/close and warmups are separate. Resource ceiling: 4 physical CPUs, 48 GiB, 8 hours, 225,000 attempts. No provider/validation/test calls.

The [Torch handoff](../trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/GUARD-COMMANDS.txt) is ready. Collect and independently reconstruct that return before pinning the guarded parent for the fresh agent episode. The guard is a common researcher-designed hybrid component, not an agent invention or unmodified native. All prior native-only failures and the frozen query split remain intact.

### November 12: guarded parent verified; fresh episode prepared, paid dispatch blocked

Job 22684501 is scheduler-confirmed COMPLETED/0:0. The [local report](../trials/fannagent-benchmark-evaluation-v1/reviews-small/reports/guard-qualification-22684501.md) verifies 15,750 paired quality rows, 126,000 timed requests, 3,150 selected-parent policy records, 7,940 forced outputs and 203,286 attempts. Guarded native640 is selected by the fixed equal-six-filter serving mean 18.8723 ms. Every condition has 450/450 complete outputs and recall>=95%; the minimum is 96.5556%. This remains one-allocation development selection, not confirmatory speed/equivalence evidence.

The [parent freeze](../trials/fannagent-benchmark-evaluation-v1/reviews-small/freeze/guarded-parent-selection-v1.json) and [agent amendment](../trials/fannagent-benchmark-evaluation-v1/reviews-small/protocol/guarded-parent-agent-amendment-v1.md) pin the hybrid baseline/common guard and prospective static tuning grid. The fresh Anthropic episode is prepared on 450 anonymized development groups only, with three rounds/nine policies/$15, four evaluator checks and usage reconciliation. Model availability GET passed. Generated-program serving cost is still to be measured; saved probe costs are only a development surrogate.

Automatic approval review rejected the paid request **before dispatch** because explicit approval is required for this specific nonpublic payload's external egress to Anthropic. No paid call or bypass occurred. The [disclosure manifest](../trials/fannagent-benchmark-evaluation-v1/reviews-small/development/agent-episode-v1/egress-review.json) and exact first-round preview make the action reviewable. After explicit payload approval, execute the bounded episode, then qualify and measure its new programs before validation. The grouped split and untouched validation/test outcomes remain preserved.

### November 12: fresh agent episode executed, explicit abstention retained

After the user explicitly approved the specific Anthropic payload/destination, the fresh episode ran once with the pinned first request and returned a valid empty policy list. The driver ended on that predeclared abstention; no unused round was dispatched. Usage: 278,319 input tokens, 457 output tokens, $0.561208, one paid call within the three-round/$15 cap. Request/response/charge hashes and the frozen empty pool passed independent verification. No new policy, final live candidate selection or validation/test evaluation resulted. Preserve this as an unsuccessful generation episode, not an impossibility result and not a hidden retry of the old policy.

The [episode report](../trials/fannagent-benchmark-evaluation-v1/reviews-small/reports/agent-episode-v1-2026-11-12.md) records the model's evidence-size/threshold-uncertainty explanation. A data-only hindsight diagnostic finds 1,930/3,150 query/filter cases with some recall-preserving measured forced stop, but does not prove feature separability or deployable latency savings. The next method revision should address evidence presentation and evaluator access (compact predicate-focused evidence and bounded local evaluation), preserving strict recall, the common guard, the current negative result and untouched validation/test. No additional model call or hand-designed substitute was used to rescue this episode.

## 2. Starting point

### 2.1 Existing policy and runtime

The current frozen agent rule uses three opportunities to stop:

| Checkpoint | Stop conditions |
| --- | --- |
| 16 | Frontier gap at least 0.02 and tenth distance at most 0.44 |
| 32 | Frontier gap at least 0.025 and tenth distance at most 0.38 |
| 64 | Frontier gap at least 0.05 |

The comparison baseline stops at checkpoint 32 when frontier gap is at least 0.05. Both otherwise continue native execution. The current implementation uses a reusable shared membership lookup on the original full graph.

Source of record: [frozen candidate and baseline](/Users/danielarturi/Developer/JinyangLiWork/agent/experiments/reviews-persistent-batch-v1/qualified-confirmation/freeze.json).

### 2.2 Evidence to retain

| Evidence | Finding and limit |
| --- | --- |
| Shared lookup, Torch job 22563225 | On 60 queries, all arms had 99% mean recall. Agent stopped on 21 queries; frontier-gap baseline stopped on nine. Mean request times were 22.26 ms agent, 27.77 ms native, and 25.67 ms baseline. Lookup construction was 513 ms; mean attachment was about 2 ms. The original identical-code timing requirements failed, so these are descriptive performance results. |
| Calibration jobs 22574550, 22574554, 22574556 | Three allocations reproduced the quality outputs and lower agent request times. All ran on cs604; they do not constitute replication across three different machines. Original timing controls still failed. |
| Attribution job 22601306 | Identical native-reader gaps tracked PostgreSQL execution and backend CPU. The logging comparison did not identify a clear logging penalty. This narrowed the timing diagnosis without identifying a complete hardware cause or validating the policy's speed. |

Evidence links: [shared lookup verification](/Users/danielarturi/Developer/JinyangLiWork/trials/reviews-persistent-batch-native-v1/confirmation-shared-v1/job-22563225/verification.json), [three-allocation verification](/Users/danielarturi/Developer/JinyangLiWork/trials/reviews-persistent-batch-native-v1/confirmation-calibration-v1/campaign-Wxv353/verification.json), [attribution verification](/Users/danielarturi/Developer/JinyangLiWork/trials/reviews-persistent-batch-native-v1/confirmation-attribution-v1/job-22601306/verification.json).

The repeated 60-query cohort remains evidence for its original frozen comparison. Its results have now been examined and cannot supply a fresh test for a subsequently selected policy.

### 2.3 Published MoReVec workload

The downloaded Small Reviews release contains 1,000 distinct query vectors. Each of seven query files contains that same vector set: no filter, then `total_votes >= 743`, `527`, `310`, `192`, `108`, and `32`. Local inspection verified the array shapes and equality of the vector sets. The importer reads the published HDF5 `test` arrays. [Local importer](/Users/danielarturi/Developer/JinyangLiWork/harness/src/fannbench/datasets/morevec.py:233)

MoReVec supplies a published query workload, rather than a prescribed development/validation/test partition for learning policies. We will describe our policy-learning partitions explicitly. The authors publish Reviews sizes of 247,286, 1,496,493, and 2,598,267 vectors, and reuse query vectors across filter conditions. [MoReVec paper, Sections 6.3–6.4](https://arxiv.org/html/2602.11443v1#S6.SS3)

## 3. Phase sequence and dependencies

| Phase | Main question | Deliverable | Dependency |
| --- | --- | --- | --- |
| 0. Query inventory and exposure audit | Which published queries can still support independent evaluation? | Completed local audit, reservation review, and frozen 450/150/275 split; 125 excluded | Complete for documented local coverage |
| 1. Study protocol | What exactly will count as a successful result? | Fixed scope, endpoints, baselines, and analysis | Phase 0 |
| 2. Development and runtime qualification | Can the agent produce a valid, economical candidate? | Development evidence, validation ranking, qualified executable rule | Phase 1 |
| 3. Freeze and package | Is the complete comparison reproducible? | Immutable policies, analysis, schedule, and Torch kit | Phase 2 |
| 4. MoReVec test | Does the selected rule preserve recall and save query time? | Independently verified test report | Phase 3 |
| 5. MoReVec size study | Does the result depend on dataset size? | At least one larger-scale evaluation | Phase 4; design fixed before its test outcomes |
| 6. Second and third datasets | Does the procedure produce useful policies elsewhere? | Two additional dataset reports | First MoReVec evaluation complete |
| 7. Synthesis and publication artifacts | What do all results support? | Reproducible evidence package and paper-ready analysis | All planned evaluations |

A valid negative MoReVec result is a completed evaluation. It should inform the next phase and appear in the final results. Infrastructure invalidity requires correction; statistical uncertainty requires an appropriately designed replication. These outcomes should not be conflated.

### Artifact organization

Keep this roadmap in the research directory. Use the experiment root `/Users/danielarturi/Developer/JinyangLiWork/trials/fannagent-benchmark-evaluation-v1/`. Phase 0 artifacts are under `inventory/`; the frozen first-study assignments and split seal are under `reviews-small/splits/` and `reviews-small/freeze/`. Historical provisional artifacts are retained separately.

Store the shared query catalog and exposure audit under `inventory/`. Give each dataset/size study its own directory containing `protocol/`, `splits/`, `development/`, `validation/`, `freeze/`, `kits/`, `returns/`, and `reports/`. Keep cross-study results under `synthesis/`. The deliverable filenames below are relative to the appropriate study directory or shared inventory. Record status, artifact locations, and the next task in a short campaign `README.md` as phases complete.

## 4. Phase 0 — Inventory published queries and audit exposure

**Purpose:** Establish an honest boundary between policy development and evaluation before new searches or model calls.

### Work

1. Inventory the local published query files, filter definitions, database files, source versions, and checksums. Record vector dimension, metric, IDs, and query counts. Inspect ground-truth structure without exposing held-out outcomes to policy selection.
2. Build a query catalog keyed by vector content. Record both the raw source hash and the exact canonical representation used at runtime. Reconcile float conversions and normalization rather than assuming differing serialized hashes imply differing vectors.
3. Associate every query/filter pair with its vector group. Apply the same group identity across filenames, aliases, filters, and any overlapping scales.
4. Audit previous development, validation, confirmation, qualification, and diagnostic inventories. Use manifests and access records where available. Record uncertainty about missing histories explicitly.
5. Distinguish ordinary access to the indexed corpus or public file metadata from exposure of query-specific outcomes, traces, or feedback used in choosing a policy. Computing hashes does not itself train a policy. Conservatively exclude groups whose relevant exposure cannot be established.
6. Produce counts for known development exposure, known consumed evaluation, other historical reservations, and genuinely available evaluation groups. Do not infer availability by subtracting only the latest 200 and 60 queries from 1,000.
7. Construct reproducible group-disjoint development, validation, and test partitions. Historical exposed groups belong on the development side of a new study. Validation groups must be disjoint from development; test groups must remain outside selection.

### Split decision

Do not prescribe an arbitrary 60/20/20 split before the audit. Use exposed data efficiently for development, reserve a bounded validation pool for selection, and preserve enough untouched groups for the intended test precision. Record the algorithm, seed, group counts, exclusions, and hashes.

If enough untouched published queries remain, use them directly. If too few remain, record the precision limit before deciding whether to use a disjoint published MoReVec table/scale, obtain a new query release, or add separately sourced queries. Supplemental queries must be labeled as a separate workload. Renaming old queries or reassigning known outcomes to a new split cannot create an independent test.

Keep original benchmark query semantics, including any self-match convention. Preserve original IDs and verify how the benchmark maps ground truth to database rows.

### Deliverables and completion criterion

- `query-catalog.jsonl`: source identity, vector group, filter, provenance, exposure evidence, and proposed role.
- `exposure-audit.md`: coverage, unknowns, and remaining independent sample size.
- `split-manifest.json`: deterministic assignments and overlap checks.

Phase 0 is complete when we can state the actual test population and its limitations without assuming that an old holdout is still untouched. This phase needs no ANN searches, exact searches, or provider calls.

## 5. Phase 1 — Define the MoReVec study protocol

**Purpose:** Make the future result interpretable before seeing test performance.

### 5.1 Scope and independent variables

Use Small Reviews at `k=10` for the first study. Start engineering checks with `votes108` to reuse the qualified path. The preferred first benchmark report covers all six published scalar filters, with the unfiltered condition as a control and `votes108` identified for continuity.

If supporting all filters requires a substantial runtime redesign, narrow the first confirmatory claim to `votes108` before opening the test. Record that scope explicitly. Decide how remaining filters will be evaluated without reusing test feedback to select their policies.

| Variable | First MoReVec study | Later work |
| --- | --- | --- |
| Dataset size | Small fixed | Medium, then Large |
| Predicate | Published Reviews thresholds; scope frozen before test | Other published predicate types |
| Number of neighbors | `k=10` | A bounded sensitivity study after the primary result |
| Index and engine | Same engine and physical graph within each paired comparison | Additional independent builds if graph robustness is claimed |
| Connection lifetime | Persistent readers, explicit warm-up and request count | Additional lifetimes for amortization analysis |
| Agent configuration | One recorded procedure and budget | Repeated independent episodes |
| Concurrency | Serial requests initially | Separate future throughput study |

Choose the primary filter weighting in advance. Equal weighting across published filter conditions is the default proposal; also show each filter separately. Do not choose weights after observing where the policy succeeds.

### 5.2 Comparison arms

| Arm | Role and selection rule |
| --- | --- |
| Original native640 | Continuity reference and the unchanged parent execution of the current candidate. |
| Tuned native | Strong static baseline. Select its search settings using development/validation data under the same declared recall requirement. |
| Frozen checkpoint-32 gap rule | Preserve gap at least 0.05 as the historical comparator. |
| Tuned fixed effort/checkpoint | Establish whether simple static effort reduction explains the benefit. Select on development/validation only. |
| Turnover rule | A simple adaptive comparator using the existing feature definition. Select its parameters on development/validation only. |
| Agent-generated policy | One selected executable policy, with its complete provenance. |
| Identical-code replicas | Measure order and reader imbalance for the relevant timing contrasts. |

Report two distinct comparisons: agent versus its unchanged native parent, and agent versus the best eligible tuned native baseline. The first isolates the effect of the stopping intervention. The second supports the stronger practical claim that agent generation improves on ordinary native tuning.

Do not call a comparison recall-matched when its measured recall differs materially. Show the development recall/latency trade-off and the final test recall alongside latency. A policy beating native640 alone is a narrower result than beating tuned native.

The existing candidate is retained as a historical comparator. The user-requested restart requires a fresh agent proposal episode. Select its new policies using development and one bounded validation selection; treat all old confirmation results as exposed development evidence.

### 5.3 Recall requirements

Before test execution, record the absolute recall floor, relative noninferiority margin, per-filter requirements, confidence method, and treatment of incomplete result sets.

Two historical margins differ: the older development code uses `-0.0025` recall units, while the recent confirmation code uses `-0.005`. These are 0.25 and 0.5 percentage points. The new protocol must resolve the difference explicitly rather than inheriting one accidentally. [Development statistics](/Users/danielarturi/Developer/JinyangLiWork/agent/experiments/reviews-persistent-batch-v1/rb_stats.py:15), [confirmation analysis](/Users/danielarturi/Developer/JinyangLiWork/agent/experiments/reviews-persistent-batch-v1/qualified-confirmation/analyze.py:19)

Recommended working specification:

- Require valid, unique, eligible results and the correct result count. Define scoring separately for filters with fewer than `k` eligible records.
- Retain the historical 95% native recall floor as a proposed adequacy check, subject to the study's stated recall objective. Conditions where native cannot meet it are reported, not silently dropped.
- Use a paired mean-recall noninferiority analysis, with 0.25 percentage points as the proposed maximum loss allowance. Record the final choice before test outcomes are available.
- For the stronger statement “preserved measured recall on the test queries,” additionally require zero observed query-level recall losses against the declared reference. Aggregate gains must not conceal individual losses.
- Report absolute recall, paired difference, lower confidence bound, recall-losing query count, and loss magnitude for every filter.

Use vector groups as independent quality observations. Repeating a query hundreds of times does not increase the independent recall sample size. A bootstrap interval of exactly zero after observing no losses is not a population guarantee. Also report a suitable one-sided upper bound on the probability of a recall-losing query. With zero losses among `n` independent groups, the approximate 95% upper bound is `3/n`; the exact binomial calculation should be used in the report. If the available pool cannot establish the desired bound, narrow the claim rather than changing the criterion after testing.

The chosen formal recall interval must handle this zero-loss case without assuming that an unobserved failure is impossible. Predeclare a suitable bounded-outcome or exact conservative method and its sampling assumptions. Report the fixed benchmark-set result separately from inference about future queries. For example, zero losses on 300 independent groups gives an upper loss-probability bound near 1%; it does not by itself establish a worst-case population mean-recall loss below 0.25 percentage points. Phase 0 must expose such precision limits before the protocol is frozen.

### 5.4 Query latency and statistical plan

Use the arithmetic mean complete-request time as the primary latency endpoint. Report milliseconds, the ratio of arm means, percentage latency reduction, and speedup with clearly stated definitions. Retain median and p95 as secondary distribution summaries.

Proposed primary practical target: at least 5% lower mean query latency than the declared native comparator, with a 95% interval supporting that reduction. A smaller statistically supported gain remains a result, but does not satisfy that practical target. This is a recommendation to freeze prospectively, not an existing user-imposed requirement.

Use development timings to set the query count, allocation count, epochs, and precision target. Budget for five independent Torch allocations initially, subject to the power/precision calculation. Prefer compatible hardware; record nodes and CPU identities. Repeated allocations on one node support a temporal replication claim, not a machine-general claim.

The schedule should balance arm order, predecessor, reader label, and query position. Use mirrored or Williams-style orders and record their seeds. Replicate every query across arms, preserving the pairing. Analyze repeated queries and allocation-level variation together; do not treat every timing repetition as an independent query. With few allocations, show each allocation's effect and explain the limits of allocation-level inference. Repetition should address the levels where variation arises. [Kalibera and Jones, 2013](https://kar.kent.ac.uk/33611/45/p63-kaliber.pdf)

For the new study, a relative identical-code equivalence requirement of approximately 2% is a proposed control criterion. Freeze its exact interval procedure and which families must pass. The historical additional ±0.10 ms requirement remains part of historical reports; it is not automatically the scientific criterion for this study. A failure of the newly specified control makes the affected contrast inconclusive. Do not subtract an observed control gap from treatment timings to manufacture a passing result.

Set multiplicity handling for primary filters and confirmatory comparisons before execution. Distinguish overall claims from claims that every filter benefits. Specify a fixed replication plan and rules for missing or invalid allocations to avoid repeatedly collecting data until a favorable interval appears.

### Deliverable

`study-protocol.md` and machine-readable configuration containing all scope, endpoint, scoring, sampling, baseline, timing, and decision choices. Phase 1 ends when no scientific threshold depends on later test outcomes.

## 6. Phase 2 — Develop policies and qualify the runtime

**Purpose:** Select a deployable policy using development and validation data while preserving the test boundary.

### 6.1 Targeted implementation qualification

1. Reuse the existing original-graph capture, native continuation, and shared lookup implementation.
2. Qualify stop and continue behavior on development queries: valid outputs, correct checkpoint features, and unchanged native continuation when the policy declines to stop.
3. Verify forced-stop outcomes against actual execution, including difficult cases and cases that do not reach a checkpoint. Reuse prior qualifications only when their engine, graph, metric, and feature assumptions still apply.
4. Verify exact filtered ground truth against the imported representation, including ties, ID mapping, missing metadata, and insufficient matches. Published ground truth may be used once these conventions agree; recompute only when necessary.
5. Account for the complete lookup design across the selected predicates. Measure total construction, memory, and attachment cost if multiple threshold lookups are built. A single-predicate build estimate cannot stand in for an unlimited predicate workload.
6. Time the feature path on both stops and continues. Keep detailed logging or profiling outside primary timings unless its inclusion is explicitly part of the protocol.

Perform engineering checks on development or dedicated qualification queries. Opening test outcomes to debug the implementation would weaken their later independence.

### 6.2 Agent development and validation

Provide the agent with the literature context, feature definitions, development outcomes, recall failures, and measured cost information. Exact outcomes and oracle choices can supply training labels; the executable policy may use only information available before its stop decision.

Use grouped folds within the 450 development groups for iteration. Hold the 150 validation groups outside those folds. Freeze the proposal pool, baseline candidates and deterministic selection rule before one bounded validation selection; provide no validation feedback for proposal revision in this episode. Keep all 275 test groups outside generation, tuning and selection.

Record the model/version, prompts, tools, random seeds where supported, proposals, rejection reasons, token usage, and dollar cost. Register manual edits separately so the paper can distinguish agent proposals from researcher-designed rules.

For a first bounded episode, use up to three proposal rounds and a proposed $15 provider ceiling, matching the scale of the previous proposal exercise. This is a planning allocation for a future run. Record this as a new episode with a frozen development-only input bundle. The old rule winning a comparison does not substitute for the requested fresh episode. Reconcile provider usage and finalize model/version and budget in Phase 1 before calling the provider.

Screen candidates in this order:

1. Executability and allowed feature access.
2. Valid outputs and development recall.
3. Validation recall under the fixed criteria.
4. Measured complete-query latency and continuation overhead.
5. The predeclared selection rule, including tie-breaking and a native fallback.

Work saved and oracle opportunity are diagnostics. Select the final candidate using measured serving cost, rather than assuming fewer distances guarantee lower latency.

### Deliverables and completion criterion

- `development-report.md` with candidate and baseline comparisons.
- `agent-episodes.jsonl` with complete proposal provenance and costs.
- `validation-selection.json` with a deterministic final selection.
- Runtime qualification evidence for the selected graph, features, and lookup.

Complete the phase when one candidate meets the development/validation criteria or the bounded search finds none. If none qualifies, record a negative selection outcome. Investigate a specifically evidenced missing signal or runtime cost before spending on additional model rounds.

## 7. Phase 3 — Freeze the comparison and prepare the Torch kit

**Purpose:** Make evaluation executable without discretionary changes after test results appear.

Freeze the selected policy, native parent, tuned native setting, simple baselines, feature semantics, shared lookup format, engine/module identity, database and index identities, query assignments, timing schedule, metrics, analysis code, and planned replication count. If a composite policy contains predicate-specific rules, include every branch and the fallback behavior.

Build a kit that performs input checks, launches the fixed workload, records raw output and timings, writes machine and scheduler metadata, and creates a checksummed return archive. Test submission and collection parsing locally, including duplicate scheduler records and completed jobs that no longer appear in `squeue`.

Use development data for a complete rehearsal of packaging, restore, ownership checks, mount paths, execution, cleanup, collection, and local report reconstruction. Preserve the original graph for the paired comparison.

Operational requirements:

- Use a compatible available Torch allocation rather than pinning an arbitrary node with a multi-day queue.
- Request memory from a measured footprint and allow for restore/build overhead. Do not carry 32 GiB forward automatically to larger datasets.
- Keep setup and primary timing boundaries explicit in the raw records.
- Supply separate, copyable SSH submission, status, collection, and SFTP upload/download commands with stable local artifact paths.
- Make local verification independently reconstruct remote summaries from raw data.

Deliverables: `freeze.json`, the sealed kit, checksum sidecars, a rehearsal report, and `COMMANDS.txt`. Phase 3 ends when the kit and analysis can be executed unchanged.

## 8. Phase 4 — Run and report the MoReVec test

**Purpose:** Answer the first confirmatory question on the previously specified published-query partition.

Execute the complete frozen comparison across the planned allocations. Test outcomes become available to analysis only after policy selection and freeze. Computing quality once and reusing verified output identities for later timing repetitions is acceptable when the graph and execution remain identical; every timed execution must still have its output checked.

Verify checksums, job completion, resource identities, query completeness, stop decisions, output validity, and data/index integrity. Reconstruct the analysis locally. Report missing and invalid observations using the prespecified rules.

### Required result tables

| Table | Required contents |
| --- | --- |
| Quality | Independent groups, recall, paired differences and bounds, loss counts/magnitudes, incomplete results, per-filter results. |
| Query performance | Mean, median, p95, paired differences, ratios, reduction, speedup, intervals, and per-allocation results. |
| Timing controls | Identical-code effect estimates and intervals, order/position summaries, and verdict under the new protocol. |
| Policy behavior | Stop coverage by checkpoint/filter, continuation cost, work saved, and native fallback frequency. |
| Setup and resources | Lookup build time/bytes, connection and attach cost, warm-up time, memory footprint, and full-session totals. |
| Research cost | Agent rounds, tokens, dollars, development searches, test searches, and Torch allocations. |

Report setup amortization with explicit assumptions. For `C` connections and `Q` total measured queries, show:

`total cost = shared build + sum(connection setup + attach + warm-up + requests + close)`.

Show total cost divided by `Q` separately from request latency. For positive mean request saving `s`, the simple shared-build break-even is `build / s` queries before connection effects; also calculate break-even including incremental attach/warm-up costs under stated connection lifetimes. If `s` is uncertain or nonpositive, report the corresponding limit instead of a misleading single break-even point.

### Result dispositions

| Outcome | Next action |
| --- | --- |
| Recall and latency criteria pass | State the scoped result and proceed to scale and dataset replication. |
| Recall passes; latency interval is inconclusive | Preserve the policy. Use the predeclared replication or a new, prospectively specified timing study. |
| Latency improves; recall fails | Report failure of the combined objective. Use observed failures for a later development episode with a new independent test. |
| Both fail | Record a valid negative result; assess the feature/selection/runtime bottleneck on exposed evidence. |
| Implementation or integrity failure | Repair and requalify. Record whether any test outcomes were exposed and whether the repair could affect selection. |
| Candidate beats native640 but not tuned native | Report the narrower achievement and the static-tuning explanation. |

Do not alter thresholds or discard troublesome queries to rescue this test. An operational retry of unchanged code is different from policy revision, but must retain failure evidence and the complete analysis history. New work follows the recorded protocol and applicable project instructions.

Deliverables: `test-report.md`, raw returns, local verification, complete result tables, and a concise disposition. This completes the user's initial MoReVec development-and-test objective, regardless of whether the result is positive.

## 9. Phase 5 — Evaluate dataset size within MoReVec

**Purpose:** Make scale a planned experimental variable and determine whether the Small result survives larger graphs.

Use the published Reviews Medium and Large releases. Run at least one larger scale before completing both additional datasets. Prefer the full three-size series when implementation and memory permit.

### Two separate experiments

| Experiment | What stays fixed | What it establishes |
| --- | --- | --- |
| Adaptation, primary | Agent procedure, development budget, evaluation definitions, and baseline-selection method | Whether the agent can generate a useful policy at each size. A separate policy may be selected at each size. |
| Transfer, secondary | The Small policy's executable thresholds and decisions | Whether that particular policy transfers unchanged. |

Plan group assignments across scales before their outcomes are opened. An identical query vector must keep the same role if shared across a pooled learning study. If Small test feedback later informs a Medium policy, exclude overlapping groups from Medium's fresh test or clearly report a transfer/adaptation experiment on already exposed queries. Record prompt and researcher-feedback provenance between stages.

### Controls for interpreting size effects

- Hold dimension, distance metric, `k`, and index construction settings constant where feasible. Record every justified difference.
- Compare published predicates at overlapping qualifying fractions, and report the actual fraction at each size. A fixed numeric threshold can change selectivity and should not alone identify a size effect.
- Recompute or verify filtered ground truth for each database population. Small ground truth cannot score a larger database.
- Record graph construction, insertion order/seed, index footprint, runtime memory, and whether data/index fit in memory. Published sizes need not be nested or distribution-identical; verify rather than assume.
- Use the same hardware/resource policy where possible. If a larger size requires more memory or different hardware, explain the resulting scope of the comparison.
- Plot size against recall, relative query time, stop coverage, build/attach cost, and memory. Include both adaptation and transfer results with separate labels.

This is a controlled scale study within practical limits, not proof that cardinality is the only changing property. Multiple independent graph builds are a later robustness extension if the paper claims independence from graph realization.

Deliverables: `scale-protocol.md`, per-size freezes/reports, and `scale-summary.md`. Defer a full Cartesian sweep over every size, `k`, index setting, predicate type, and concurrency level until the primary mechanism is established.

## 10. Phase 6 — Repeat on two additional published filtered ANN datasets

**Purpose:** Evaluate the agent procedure beyond the original Reviews setting.

Choose both additional datasets using workload coverage and implementation feasibility before examining their policy outcomes. Preserve a selection log if a source is unavailable or incompatible. A valid negative result is not a reason to replace a dataset.

### Candidate shortlist and feasibility work

| Candidate | Contribution | Check before committing |
| --- | --- | --- |
| Big ANN filtered-track YFCC-10M | Published image/tag workload with different geometry and predicate semantics. The release uses 192-dimensional byte vectors, L2 distance, and query predicates with one or two tags. | Preserve the metric and tags; qualify the signal path for L2; plan full index memory. Record exact byte-to-float conversion if required. Do not silently substitute cosine. |
| SPCL arXiv for FANNS | Published text queries, metadata filters, and filtered ground truth; useful contrast with Reviews. | The release uses 4,096-dimensional vectors. Check engine/index support and memory before choosing it. This is a candidate, not a ready-to-run commitment. |

Sources: [Big ANN official filtered-track documentation](https://github.com/harsha-simhadri/big-ann-benchmarks/blob/main/neurips23/README.md), [SPCL dataset card](https://huggingface.co/datasets/SPCL/arxiv-for-fanns-medium/blob/main/README.md).

The dimensionality concern is concrete: upstream pgvector 0.8.1 defines a 2,000-dimensional HNSW limit for its `vector` path. Verify the exact retained build rather than assuming arXiv can use the current engine unchanged. Truncating embeddings, changing distance, or changing representation can change the benchmark question. If a published compatible variant is unavailable, select another published filtered workload or document a deliberate engine extension and qualify it separately. [Upstream source](https://raw.githubusercontent.com/pgvector/pgvector/v0.8.1/src/hnsw.h)

Do not count Movies and Reviews alone as three independent benchmark families. Additional datasets should contribute materially different vectors and filtering conditions. Do not manufacture filters on an ordinary ANN corpus and describe them as an existing filtered benchmark.

### Procedure for each dataset

1. Pin published source files, metric, metadata semantics, query workload, ground truth, and any official split.
2. Preserve official held-out queries when available. Otherwise publish a reproducible grouped split, using only development/validation feedback for selection.
3. Qualify import, exact scoring, native execution, checkpoint signals, stops, continuation, and shared lookup behavior on development data. Cosine-specific distance validation must not be reused blindly for L2.
4. Select native and simple adaptive baselines with the same method and comparable effort used on MoReVec.
5. Run the frozen agent procedure under the stated budget, select one policy, freeze, and independently evaluate.
6. Report all predicate categories, unsupported cases, native fallback, setup cost, and the combined quality/performance result.

Freeze the high-level agent method after MoReVec. Dataset adapters and dimension/metric changes are expected; novel reasoning tools or new search strategies introduced later constitute a method revision. Document such revisions and, if making a uniform three-dataset claim, rerun the relevant development/evaluation procedure consistently without recycling exposed test queries.

For stronger evidence about the agent, predeclare repeated independent generation episodes. A practical extension is three episodes per dataset, with all selected policies frozen before test outcomes are inspected. Report success rate and cost per successful policy. Select any single headline policy on validation data. Keep this extension distinct from the minimum one-policy-per-dataset evaluation.

Deliverables: two dataset qualification records, split manifests, agent episode records, policy freezes, and independent test reports.

## 11. Phase 7 — Combine results and prepare publication artifacts

**Purpose:** State exactly what the completed experiments establish.

Build one result matrix with a row for each dataset, size, filter category, and policy episode. Include valid failures, native fallbacks, inconclusive timing results, and implementation exclusions with reasons.

The final analysis should answer:

1. On which workloads did an agent-generated policy meet both recall and query-latency criteria?
2. Did it beat tuned native and simple adaptive rules, or only the historical native640 setting?
3. How did size and qualifying fraction change savings, safety, continuation overhead, and setup amortization?
4. What proportion of the available hindsight opportunity did the deployable policy capture, using an oracle clearly labeled as retrospective?
5. How consistently did the agent succeed across episodes, and how much development cost did success require?
6. Which limitations remain: one engine, fixed graphs, in-memory execution, serial requests, particular predicates, or limited independent query counts?

Present per-dataset effects before any aggregate. If reporting an aggregate speedup, define weights and aggregation in advance; a geometric mean across declared comparable conditions is a possible summary. Do not pool millions of repeated timings as if they were independent samples or let a large dataset's query count determine the weighting accidentally.

Publish source references, conversion details, split hashes, protocols, policies, agent provenance, runtime versions, timing schedules, raw returns, analysis code, and reproduction commands. Include one table for per-query performance and another for setup/session economics.

Deliverables: `overall-results.md`, publication figures, reproducibility instructions, a complete claim/limitation checklist, and an artifact index.

### November 12: compact/tool continuation verified within original allowance

The user authorized compact filter-focused evidence and bounded local evaluator access using the two remaining requests. Request2 submitted three speculative policies to one full-development evaluator batch; request3 authored three final programs. Six records contain five distinct programs, three of which pass replay on all3,150 development cases with zero individual recall losses and all condition floors met. All six filters plus unfiltered remain included; votes743 continues natively. Failed exploratory policies and the original abstention are retained.

The final response had leading prose and one JSON fence. The strict parser rejection remains preserved; separately recorded envelope recovery extracted the unchanged programs without another request. Independent receipt/charge/hash/replay reconciliation passed. Original allowance is exhausted: three total requests, $0.725544 total, below $15. No fourth request is authorized by the remaining dollars. No validation/test outcomes were opened, no final policy selected, and actual new-program latency remains unmeasured. See the [continuation report](../trials/fannagent-benchmark-evaluation-v1/reviews-small/reports/agent-compact-continuation-2026-11-12.md) and [eligible programs](../trials/fannagent-benchmark-evaluation-v1/reviews-small/development/agent-episode-v2-compact/eligible-policies.json). Next: live development qualification/timing under the existing selection rules, before validation; the best scalar surrogate is only about4% lower and is not evidence of the practical5% target.

### November 12: three-policy compilation and Torch kit prepared

The three replay-eligible model programs are compiled unchanged into a new x86_64 module using a copied engine. Generated-C first-stop decisions match all9,450 policy/development-case combinations. Seven-condition real PostgreSQL synthetic smoke, seven guard unit checks and full-size synthetic return-verifier checks passed. Local checks remain distinct from original-graph qualification; failed build/staging logs are retained.

The sealed [Torch kit](../trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/agent-policy-qualification-v1.tar.gz) and [commands](../trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/AGENT-COMMANDS.txt) qualify all3,150 development cases for every program and time50,400 complete requests plus1,120 warmups. Two mirrored epochs use A/B readers for native640 and all three policies, the common exact completion guard, immutable membership and a shared exported snapshot. Resource ceiling:4 physical CPUs,48GiB,8 hours,160,000 ANN/exact attempts; the [versioned development amendment](../trials/fannagent-benchmark-evaluation-v1/reviews-small/protocol/agent-policy-qualification-amendment-v1.md) records the larger workload. No provider call, final selection or validation/test access is included. Original-graph parity, actual cost and the Slurm completion gate remain pending.

### November 13: job22928562 independently verified; modest development leader

[Compiled-policy return verified](../trials/fannagent-benchmark-evaluation-v1/reviews-small/reports/agent-policy-qualification-22928562.md): all9,450 agent cases,50,400 timing records,1,120 warmups and81,456 ANN/capture/exact attempts reconstruct. Slurm COMPLETED0:0,49m08s; original graph/data, live feature/first-stop/output parity and all quality gates pass. All three policies preserve every development query's recall, with all seven condition means>=.95. All six filters remain included; validation/test outcomes are unopened.

Observed equal-scalar means: native19.274893ms, conservative19.251483ms, moderate19.153754ms, broad18.659077ms. Broad is the unique development nominee (3.19% reduction), not a final selected policy or established5% practical win. Its A/B point gaps at votes108/32 are2.17%/4.16%; conditional single-allocation bootstrap diagnostics do not establish equivalence or replace confirmatory inference. Retain the valid allocation and its limitations. Recommendation: prepare/seal the complete required comparator pool, all three unchanged eligible agent programs and bounded four-epoch validation schedule; no new model requests, threshold edits, opportunistic reruns or holdout access now. The current job does not qualify all final comparator families.

### November13: primary experiment redesigned without serving completion

The user directed removal of the exact completion guard from actual native and agent queries. Exact search is retained solely as an offline recall evaluator, never an answer replacement. Short valid results now score missing neighbors as misses; recall denominator remains min(k,eligible_count). The95% absolute floor is reported separately instead of blocking a relative-preservation comparison. Zero individual recall losses relative to actual raw native640 remains the quality criterion. Split, predicates, graph, features and5% practical target are unchanged. Historical hybrid experiments remain preserved; their timing effects do not carry over.

The [full revised protocol](../trials/fannagent-benchmark-evaluation-v1/reviews-small/protocol/study-protocol-unguarded-v1.md), [redesign/rescore report](../trials/fannagent-benchmark-evaluation-v1/reviews-small/reports/unguarded-redesign-2026-11-13.md) and [sealed Torch commands](../trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/UNGUARDED-COMMANDS.txt) govern the next run. Raw-output replay still gives zero losses for all three fixed policies; native recall is53.49%/78.98%/94.82% in votes743/527/310, now visible scientific outcomes. No unguarded timing gain has been established.

The kit measures native40/80/160/320/640, noop640 and three unchanged policies over450 development groups/all7 conditions:28,350 quality family results,113,400 timings,2,520 warmups,3,150 captures and3,150 separately executed offline exact references =150,570 attempts. Four CPUs/48GiB/8 hours/160,000-attempt cap. Exact readers close before approximate phases; serving has no exact capability. Module and policies match job22928562. Policies were generated with guarded development labels: this is an explicitly labeled unguarded transfer evaluation, not a new generation episode. Local unit/PostgreSQL/reader-capacity/verifier checks pass. No provider calls or validation/test access; original-graph fresh unguarded latency remains pending. Complete comparator qualification and selection freeze are still required before any validation batch.

### November13: unguarded job23045686 verified; timing attribution unresolved

[Independent unguarded report](../trials/fannagent-benchmark-evaluation-v1/reviews-small/reports/unguarded-development-23045686.md):28,350 quality family outputs,113,400 timings,2,520 warmups and150,570 attempts all reconstruct. Slurm COMPLETED0:0,43m47s; original graph/eligibility/module, all live policy/raw-output parity and cleanup pass. Exact search was restricted to3,150 offline references; zero serving exact calls, with541 short answers retained per native640/noop/agent family. All three policies preserve actual raw native recall. All six filters remain included; validation/test unopened.

Observed scalar means: native64011.820408ms, noop11.047757ms, conservative10.873694ms, moderate10.954517ms, broad12.012871ms. Conservative is the nominal complexity-tiebroken nominee (moderate within1%); native640 is the only recall-preserving native grid setting. However native A/B gaps2.20%–4.50%, broad/moderate systematic reader gaps and a6.54% faster always-continue control prevent attribution of conservative's nominal8.01% reduction to learned stopping. No final performance/equivalence claim or practical-target pass. Preserve this scientifically valid allocation and all control results. Recommendation: one prospectively bounded development-only attribution diagnostic with unchanged policies, counterbalanced reader roles and backend/CPU/order measurements, before completing the comparator pool and any validation freeze. No automatic rerun, threshold edit, new provider request or holdout access.

### November13: fixed counterbalanced diagnostic sealed; agent performance not presumed successful

The user authorized a single development-only reader/CPU/search-work diagnostic and asked whether the agent itself should be revisited. [Agent disposition](../trials/fannagent-benchmark-evaluation-v1/reviews-small/reports/agent-performance-disposition-2026-11-13.md): current programs preserve exposed-development recall, but robust attributable performance success has not been demonstrated; held-out robustness is unknown. A roughly1ms gap can be measurement/context variation. This is neither proof of a win nor proof the model is incapable; preserve the bounded episode honestly rather than rescue it indefinitely.

The [prospective diagnostic](../trials/fannagent-benchmark-evaluation-v1/reviews-small/protocol/reader-attribution-v1.md) rotates five unchanged roles through20 persistent backends/filter and four allocated CPUs in ten mirrored Latin blocks, every backend running every role twice.630,000 timings use the byte-identical original module;15,750 work-count queries use a separate observer module/restore, with their instrumented times excluded. Total684,950 attempts including6,300 offline references; zero serving exact calls. Four CPUs/48GiB/8h/750,000 maximum; no automatic rerun, policy edit, provider call or validation/test access. Schedule/role/CPU unit checks, seven-condition PostgreSQL smokes under both modules and full-size fabricated-return/corruption/paired-analysis checks pass. [Upload/submit/progress/collection commands](../trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/ATTRIBUTION-COMMANDS.txt). The original-graph diagnostic remains pending the user-run Torch return. If attribution or useful net savings remain unestablished, retain a negative/inconclusive result; any revised agent evidence/objective/runtime action space needs a new version and separately authorized generation budget.

### November13: pre-revamp state committed; proposed agent protocol v2

The current code and compact source/evidence checkpoint were committed in agent/ at c3f7a48 and6250bd4 before drafting a new plan. The checkpoint archives1,044 source/report/metadata files and records hashes/locations for larger raw artifacts retained locally; no remote push. Other repository HEADs are pinned in its manifest.

The proposed [comprehensive agent protocol revamp](fannagent-agent-protocol-revamp-2026-11-13.md) separates runtime engineering, raw recall preservation, search-work reduction and attributable net latency. It sequences the existing attribution diagnostic, versioned observation masks/partial-stop qualification, raw-reference compact evidence, bounded typed tools, one newly authorized episode, real finalist cost and protected selection/testing. The proposed new episode is capped at$15/six paid requests/nine candidate submissions/twelve domain-tool calls, not an extension of the exhausted old allowance. It adds matched continue-only controls and proposes a prospectively declared three-contrast confirmatory family. Procedure replication and policy transfer remain separate. This is a plan only: it does not activate new semantics, alter the sealed diagnostic, spend provider credits, submit Torch jobs or open holdouts. The current next action remains the existing fixed diagnostic return, with no automatic repeat or presumption of agent success.

### November14: protocol-v2 local implementation; attribution submission remains first

The user authorized executing the revamp plan and clarified that the sealed reader-attribution diagnostic has not yet been submitted. Its kit and freeze hashes are unchanged; the supplied upload/submission commands remain the next Torch action. No new Torch job or provider call was launched locally.

The [local v2 implementation](../agent/experiments/filtered-ann-protocol-v2/README.md) now includes a deterministic causal DSL/compiler, predicate/checkpoint observation masks, qualified-on-synthetic-fixtures partial/zero stops, matched continue-only controls, raw-native evidence rebuild and a bounded typed controller using the existing Store/Budget. Thirty-six targeted tests, generated-C/Python decision parity, two seven-condition PostgreSQL smokes and a complete scripted campaign pass. These are local semantic/controller checks, not original-graph or latency qualification. All six filters and unfiltered remain in scope; exact search has no serving role; protected outcomes remain unopened.

All3,150 development rows were rebuilt with7,940 known full-prefix labels and1,496 still-missing reached partial-prefix labels. The1,964 cases with some known raw-recall-preserving full stop are an oracle opportunity count, not a policy or speed result. The bundle is cost-unqualified; generation is blocked pending verified M0 attribution, original-graph v2 qualification, completed prefix/cost evidence and new episode authorization. The next v2 development kit's measurement contract must follow M0. [Machine-readable execution status](../agent/docs/plans/agent-protocol-v2-execution-status.json) and source/artifact-bound local receipts preserve these limits and the failed rehearsal that exposed a subsequently fixed artifact-scope collision.

### November15: M0 job23074287 startup failure and deployment repair

The user supplied FAILED1:0 scheduler evidence (9seconds) and a `Use a clean process` traceback at the pinned loader, before restore or exact/ANN work. The diagnostic had imported its schedule as `design`, colliding with the inherited frozen package's reserved `design` root. This is a startup failure, not a benchmark result. The original archive/freeze and remote failed run are preserved; the failed archive and logs still need collection and independent verification.

The [deployment repair](../agent/experiments/reader-attribution-startup-fix-v1/README.md) renames only the diagnostic schedule module and its three import consumers, and requires native timing/work backend import preflights before sbatch. Schedule bytes, actual entrypoint, queries, policies, serving, both search modules, scoring/analysis logic, all six filters and bounds remain unchanged. Six repair checks, both corrected frozen-loader checks and the full-size fabricated-return verifier pass. Full backend imports encountered a PyArrow crash under local Mac x86 QEMU; this is retained as a readiness limitation, with native Torch preflight mandatory before a corrected job can queue. No new job, provider call or held-out outcome access was performed by Codex.

The new [deployment freeze](../trials/fannagent-benchmark-evaluation-v1/reviews-small/freeze/reader-attribution-startup-fix-v1.json) identifies `reader-attribution-v1-startup-fix.tar.gz` without altering the original study freeze. Use the [failure collection/upload/submission commands](../trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/ATTRIBUTION-STARTUP-FIX-COMMANDS.txt) for one manual corrected submission after successful native startup checks. No automatic retry, performance-positive replacement rule or generation extension is introduced. Attribution and later protocol stages remain pending.

### November16: M0 return23303080 verified; proceed to bounded runtime/evidence qualification

The [reader/CPU/work assessment](../trials/fannagent-benchmark-evaluation-v1/reviews-small/reports/reader-attribution-assessment-23303080.md) passes the frozen verifier and an independent full-tensor/quality/work reconstruction. All630,000 original-module timings,14,000 warmups,15,750 quality results,15,750 work queries,6,300 offline exact references and1,400 role assignments reconcile to684,950 attempts. There are140 actual timing backend PIDs across seven conditions; each runs each role twice on the declared four physical CPUs. Work queries' direct-kernel CPU samples match their singleton affinity. Both native backend preflights pass; user-provided sacct is COMPLETED0:0 (3:42:45). The failed23074287 archive is verified to contain no measurements and remains preserved. Exact search is scoring only; no guard or serving exact calls exist.

The equal-six-filter means are native14.212ms, continue14.380ms, Conservative14.272ms, Moderate14.034ms and Broad13.676ms. Continue is1.18% slower with zero per-query mismatches on all five graph-work counters, so its former6.54% advantage did not reproduce. Broad saves3.77% latency and5.30% vector-score calls, with zero query-level recall losses; its primary advantage persists on all four CPUs and both cycles. Its95% group-bootstrap speedup interval is3.01–4.59%, conditional on one allocation and exposed development. Votes32 supplies82.47% of the net scalar millisecond saving (19.06% faster there); selective conditions are nearly flat/slower. All six filters remain. Native's541 short outputs per family remain scored as misses. The absolute95% recall floor is still diagnostic only.

M0 is complete as a valid diagnostic supporting current role/work attribution; the earlier control anomaly's specific cause remains unidentified because node and schedule changed. No final policy is promoted, nominee changed, new provider call made, allocation repeated or protected outcome opened. The current policies have localized useful work savings; robust final performance/generalization and the proposed5% practical target remain unestablished. Do not pool the old/new jobs or subtract historical control gaps.

The [outcome freeze](../trials/fannagent-benchmark-evaluation-v1/reviews-small/freeze/reader-attribution-assessment-v1.json) and [generation gates](../trials/fannagent-benchmark-evaluation-v1/reviews-small/reports/protocol-v2-gates-after-M0.json) close M0 and block generation at M1 original-graph qualification. The next task is to seal one bounded M1 runtime/prefix/cost kit: qualify selective observations/actual partial outputs and native bridge parity, recheck all reached prefixes including1,496 missing partial labels, and obtain real feature-plan/full-serving costs under a resource-feasible CPU/reader crossover with matched continue controls. M2 must bind those labels/costs before any newly authorized bounded M4 episode. Runtime engineering and agent discovery remain separate contributions; validation/test stay unopened.

## 12. Resource plan and operating priorities

### Torch

Treat compute availability as generous, as requested. Spend it on independent queries, baseline tuning, exact references, repeated allocations, and larger datasets. Human attention, queue delay, test independence, and implementation reliability are the scarcer resources.

Bundle work to reduce SSH/SFTP interaction. Avoid arbitrary machine pinning and choose replication counts from precision needs. Preserve source and raw evidence without recreating elaborate one-off approval machinery for every routine analysis step. Existing historical contracts remain attached to their original experiments.

### Provider budget

The user's stated total is approximately $400 through January; approximately $5 had been spent when last reported. Reconcile current usage before a new campaign rather than treating that old figure as the live balance.

Proposed planning allocations, with unused amounts remaining available:

| Work | Suggested ceiling |
| --- | ---: |
| Initial MoReVec proposal episode | $15, up to three rounds |
| Larger-scale MoReVec adaptation | $30 combined initially |
| First episode on each additional dataset | $15 each |
| Optional repeated episodes | A separately logged pool, sized after initial results |

These first three allocations total $75. They are proposed ceilings, not minimum spending or a new provider authorization. Preserve most of the overall budget for useful refinements and repeated episodes after the first formal result.

### Effort sequence

| Work block | Planning estimate, excluding queues | Priority |
| --- | --- | --- |
| Exposure audit and protocol | 1–2 focused working days | Immediate |
| Reused runtime qualification and development | 2–4 working days; longer if predicate support changes | Immediate after protocol |
| Kit, rehearsal, test, verification | 1–3 working days plus planned allocations | First milestone |
| Medium/Large size study | 3–5 working days plus builds/allocations | Before completing both new datasets |
| Additional datasets | Estimate after compatibility audit | Sequential replication |
| Synthesis and artifact preparation | Begin with the first report; consolidate after replication | Continuous |

These are sequencing estimates, not promised dates. The compatibility and exposure audits should replace them with measured estimates.

## 13. Risks and bounded responses

| Risk | Response |
| --- | --- |
| Published test pool largely exposed | Audit first; use genuinely disjoint published groups where possible; label supplemental queries and limit claims honestly. |
| Overfitting to one vote threshold | Include published filter conditions in the frozen scope; show per-filter safety and benefit. |
| Static native tuning explains the gain | Include tuned native and fixed-effort baselines selected without test feedback. |
| Timing controls remain imbalanced | Apply the new prespecified criterion; use bounded replication or targeted diagnostics for the affected contrast. Avoid indefinite infrastructure work. |
| Recall appears perfect on a small sample | Report finite-sample bounds and independent group counts; do not interpret a zero bootstrap width as universal safety. |
| Shared setup grows across predicates or sizes | Measure total lookup footprint and lifecycle costs, including invalidation/rebuild assumptions. |
| New dataset exceeds engine or memory limits | Resolve before policy experiments; preserve published semantics or document a different scope. |
| Agent loop changes between datasets | Version the method and distinguish method development from evaluation. |
| Test-driven iteration creates optimistic results | Preserve the result; move exposed cases to development for the next version and use a new independent test. |

## 14. Immediate execution checklist

- [x] Inventory published Small Reviews source files and query groups.
- [x] Reconcile exposure across local historical manifests, vector aliases and saved outcome identities; document limits of local access history.
- [x] Report recovered protected groups and achievable recall precision: 275 test groups, zero-loss upper probability bound approximately 1.0834%.
- [x] Freeze group-disjoint partitions: 450 development / 150 validation / 275 test / 125 historical exclusions; intended scope is all six scalar filters plus unfiltered control, with runtime qualification pending.
- [x] Resolve recall margins and fix the latency endpoint, practical target, and timing-control rule in the sealed study protocol.
- [x] Fix baseline-selection, agent-selection, and replication procedures; provider usage reconciliation remains a pre-dispatch operational check.
- [x] Reuse and qualify the required runtime path on development data; common completion guard and guarded native640 parent verified.
- [ ] Select the candidate on development/validation, freeze, and prepare the Torch kit.
- [ ] Run and independently verify the MoReVec test.
- [ ] Proceed to the planned size study and two additional datasets, retaining all outcomes.

The unguarded-development and M0 attribution returns are verified. Following valid diagnostic23303080, the next task is the bounded M1 original-graph v2 runtime/prefix/cost package, with all six filters and exact search used only for offline scoring. Broad has a modest work-supported conditional development benefit, but final practical/replicated/held-out performance remains unestablished. M0 is not repeated. The original three-request provider allowance is exhausted at$0.725544; M1/M2 qualification and new concrete episode authorization remain required before generation. No validation/test outcomes may be opened before the revised complete pool and selection/comparison freezes are ready.
