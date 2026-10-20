# Policy learning and evaluation revision plan

The separately designed [aggressive proposal experiment](AGGRESSIVE_POLICY_PROPOSAL_EXPERIMENT.md)
tests acceptance-oriented versus exploratory agent selection with identical
evidence, features and budgets. It permits recall-losing training proposals while
retaining the existing final overall/per-filter recall and measured latency
criteria. Its status is design only; no model or Torch execution has occurred.

Prepared October 19, 2026. Status: Stage 1 committed as `4a0b419`; Stage 2 import and scorer parity implemented; Stage 3 development qualification and broker interface implemented on `feat/measured-policy-feedback`. The measured-candidate milestone remains open. A separate `predicate-context-v1` study is prepared for native qualification. See [offline policy learning tools](OFFLINE_LEARNING.md) for usage, the [Stage 1 verification record](verification/offline-learning-v1.json) for the original checkpoint, and the [Stage 2/3 verification record](verification/offline-learning-v2.json) for the returned-data pass.

The next revision should give FANNAgent reliable tools for learning inexpensive filtered ANN stopping policies from measured feedback. The first milestone is a candidate with measured training latency savings at the declared recall tolerance, followed by a frozen evaluation on the existing confirmation split. Prepare the learning tools alongside the current Torch batch and use its returned measurements to choose subsequent changes.

## Baseline and experiment boundaries

The workspace contains four independent Git repositories. Preserve these source checkpoints before implementing this plan:

| Repository | Baseline commit | Scope |
| --- | --- | --- |
| agent | `4d1b896` | Existing core and policy learning interfaces |
| agent-pgvector | `b835912352fdda2e830c3b1a2b7f9c7fd1fd31a1` | Runtime fixes, demand collection and frontier statistics optimization |
| harness | `2fd3af8d921dbafbc3a72dd8ff46e8701c6373f7` | Compatibility wrappers around the core shared primitives |
| mini-bench | `7a99e9362c85630ffb18eec136b15a8ce0882c71` | Filtered query observations, recipes, notebooks and qualification evidence |

The current feedback package is `trials/torch-reviews-policy-feedback/` in the workspace parent of these repositories. Its experiment contract fixes `ef_search=640`, lightweight features, 100 learning vector groups with three filter variants, six provisional trees, matched continue controls, fixed probes and a sparse measured oracle. It separates cold policy activation from reused policy execution on warm data and acquires additional actual stopping outcomes. The package permits no confirmation queries or model calls on Torch.

Leave that package, its submitted archive, runtime library, physical index, candidate set, measurement schedule and existing results unchanged. Implement the revision in a separate development branch and a new versioned package. Import returned feedback into a fresh directory after verifying checksums, coverage, getter qualification and preservation checks. Existing research documents and trial scripts outside the four repositories remain separate workspace artifacts; the Git checkpoints do not archive them.

The current study uses a recall noninferiority tolerance of 0.005 overall and per filter, complete valid results, and a native recall floor of 0.95 per filter. This is a default-relative objective. A candidate satisfying it does not automatically establish an absolute recall of 0.95. Preserve the current reported latency definition and distinguish training feasibility, development confirmation and canonical serving acceptance.

## Research basis and scope

[JetStream](https://arxiv.org/html/2608.22476v1) informs the separation between generated candidates and externally controlled measurement. [AI Driven Research for Databases](https://arxiv.org/html/2604.06566v1) informs investigation of disagreements between development scores and real execution. Apply these ideas first to the existing bounded stopping problem.

Keep the shape model, development scorer and final evaluator distinguishable. A shape model predicts workload behavior; a development scorer helps allocate measurement effort; the final evaluator judges the frozen result using the declared workload and quality criteria. Changes to screening or experiment selection must preserve those final criteria.

## Revision sequence

### Stage 1 Prepare the learning tools while the batch runs

Deliver a versioned feedback schema, a trusted offline policy evaluator, structured failure reports and a candidate archive. Develop them against existing training exports and small test fixtures. This stage requires no new paid model requests or Torch executions.

The feedback schema should retain:

- Query vector group, filter stratum, checkpoint identity and evidence origin.
- Runtime profile, qualified feature list, numeric semantics and artifact hashes.
- Actual stopped recall, result validity and completeness, native reference and causal prefix verification.
- Candidate, matched continue and native timings, with activation state, allocation, warmup and repetition recorded.
- Explicitly unknown outcomes for unmeasured checkpoints, including the requested measurement needed to resolve them.

Implement the evaluator as a host controlled library and a narrow learner tool. Reuse `fannagent.api.policy` validation and interpretation instead of allowing each model run to implement policy semantics. For a candidate, determine its actual first decision on each recorded trajectory and attach an outcome only when the corresponding stopped execution was measured and its prefix verified. Availability guards, invalid inputs, overflow and missing features must follow the existing runtime contract.

Report measured safe and failing stops, unmeasured stops, continued queries, per-filter outcomes and independent group coverage separately. Treat predicted work and estimated latency as development diagnostics. They may prioritize measurements but cannot certify recall or replace the measured latency criterion. Avoid interpolating recall across unmeasured checkpoints.

Keep fitting and scoring separately callable so both an agent and conventional methods can use them. Include a deterministic fitter over the same bounded policy language. Keep the permitted features and policy complexity fixed for the initial comparison. Evaluate generalization with vector groups held apart, with all filter variants of a vector in the same fold.

**Completion criterion:** the offline tool reproduces decisions from the actual interpreter on fixtures and existing training exports, preserves unknown labels, enforces feature qualification and emits reproducible reports without confirmation access.

**Completed October 19:** added the versioned training corpus, data-only source importer, shared-interpreter evaluator, explicit missing-label requests, measured timing assessor, deterministic tree fitter with vector-group validation, information-conflict diagnostics and a separate content-addressed candidate archive. The full non-integration suite passed 193 tests; lint and the new module's type checks passed. All six original trees reproduced their recorded first decisions on 300 queries each, with zero disagreements. All 52 protected package and archive files remained unchanged.

The saved evidence contains 2,397 actual stopping outcomes, but it does not cover every proposed stop. The offline fit remains provisional; no measured latency benefit or acceptance has been established. Generated local corpus, fit, assessment and archive artifacts are retained under the ignored `agent/runs/learning-v1/` directory. Raw-result and receipt verification for the returned batch remains Stage 2 work.

### Stage 2 Incorporate the returned Torch measurements

Verify the full results and the smaller feedback export before using either. Keep original and updated training evidence separately identified. Confirm that only permitted learning groups are present and that each measured stop retains its original causal feature prefix.

Analyze the returned batch in this order:

1. Check result validity, label coverage, unchanged runtime identities and consistency across allocations.
2. Compare cold activation with reused policy execution under the matched warmup schedule.
3. Compare each candidate with its matched continue control to identify the benefit of stopping.
4. Compare each candidate with native execution to establish its net deployed benefit.
5. Inspect per-filter recall loss, timing regressions and remaining unknown decisions.

Retain allocation summaries and uncertainty grouped by independent query vector across repetitions and filter variants. Additional repetitions do not create additional independent vectors. Training selection among six candidates does not establish confirmation significance.

Keep installation costs visible. Use the current reported latency as the primary metric for this campaign. A future amortized installation objective requires a separately declared reuse scenario before a new comparison. Do not subtract an estimated constant from measured query latency.

**Completion criterion:** one reproducible report identifies which candidates merit further development and whether failures arise from measurement cost, poor stopping decisions, insufficient labels or missing information. An unsuccessful batch remains a usable outcome.

**Implementation update October 19:** the returned-feedback adapter verifies both archives, all raw file identities, original and acquired labels, runtime getters, actual results, interpreter decisions and complete timing coverage. It normalizes 3,884 actual stopping outcomes and 57,600 pairs across 16 arms and three allocations. Independent scorer parity reproduces all saved summaries and feasibility decisions within `1e-12` roundoff. The six learned candidates fail qualification; the per-query hindsight oracle remains a retrospective comparator. The benchmark report retains native and matched-continue comparisons separately.

### Stage 3 Align learning qualification and resume feedback rounds

Audit the learner and broker qualification path against the study objective. Distinguish a conservative proposal label such as `preserves_default` from aggregate empirical acceptance at tolerance 0.005. Preserve every measured per-query recall loss in reports. Replace any unconditional zero-loss proposal rejection only in the new study version, with tests proving that the declared aggregate constraints remain enforced. Keep legacy locks and serving acceptance behavior unchanged.

Provide bounded feedback bundles containing measured premature stops, unnecessary continuation, uncertain decisions and cases whose cheap score disagrees with actual latency. Link each observation to its measurement record. An explanation must distinguish a measured fact from a hypothesis for another experiment.

Archive all candidates by content hash with their policy, runtime profile, evidence version, fitting configuration, measured outcomes and selection status. Resume should recover the recorded result and selected candidate without rerunning ambiguous operations. A saved candidate remains provisional until it passes the required later evaluation.

Resume model work only as an explicitly executed next stage under the original durable $15 campaign ledger, counting prior confirmed charges and uncertain reservations. Set per-round model and measurement limits in advance. Reaching a turn or spending limit must retain supported candidates or a clear abstention reason.

**Completion criterion:** a frozen candidate demonstrates measured training savings at the declared recall criterion, or the round ends with a specific evidence-backed abstention and a bounded next investigation.

**Implementation update October 19:** `measured-feedback-v2` supplies aggregate recall qualification, bounded failure feedback and a broker-compatible tool interface. It can archive provisional candidates and immutably freeze a measured candidate for later confirmation without changing old locks or serving gates. A separately declared four-setting conventional tree grid uses the returned labels. New first stops remain measurement requests; model execution and new Torch measurements have not been resumed. This implements the development interface, not the completion criterion above.

The offline pass archived the six failed original trees and four new conventional fits. The new fits contain 49, 0, 32 and 11 unknown stops respectively; the zero-request fit always continues. Deduplication leaves 49 distinct actual-stop requests across 49 learning queries, with at most one requested checkpoint per query. The saved plan is prepared for measurement and makes no latency claim. All 211 non-integration tests, lint and type checks passed; 125 protected files and the original 42-attempt ledger were verified unchanged.

### Stage 4 Test information sufficiency when failures persist

Use measured failures to determine whether the current feature interface can distinguish cases that require different stopping decisions. Repeated fitting cannot separate identical allowed inputs. Quantify the conflicting states and their recall consequences before proposing additional runtime observations.

If needed, test one cheap query-side input, such as the actual predicate threshold or a permitted selectivity summary, in a separate feature ablation. Verify the getter, scope, availability, inference cost and prefix behavior before exposing it to the learner. Freeze a new feature profile and give the same information to the conventional baselines. Executor feedback and richer frontier statistics require their own measured engineering justification.

**Completion criterion:** the added information improves measured quality or latency enough to pay its collection cost. Otherwise retain the simpler interface and report its limitations.

**Narrow ablation brought forward:** the returned evidence has identical qualified trajectories for `votes32` and `votes108` for all 100 vectors, including 275 conflicting measured native-preservation states across 82 vectors. This supports a controlled predicate-context test without proving that a common conservative policy cannot succeed. `prepare-ablation` creates the separate `predicate-context-v1` manifest, actual query-context records and planned profile. Both arms share evidence, folds, fitting grid, policy limits, quality criteria and the original ledger. The context getter now has local synthetic ARM correctness qualification; native x86 qualification and Reviews equivalence/overhead measurements remain pending. Existing timings are not transferred to that arm.

### Stage 5 Evaluate shape knowledge as a separate mechanism

After the first measured policy result, introduce a small shape artifact with defined predictions, support counts, evidence provenance and uncertainty. Candidate targets include local filter prevalence, required search effort or the probability that further exploration improves the result.

Score these predictions on held-apart development groups before assessing downstream policy value. Compare direct policy synthesis with shape-assisted synthesis under the same raw evidence, policy language and budget. Include a conventional learner using the same shape representation. A stored explanation or additional metadata alone does not establish structural acquisition.

Keep the first shape representation small and independently inspectable. A general simulator, arbitrary generated evaluator code and unrestricted search-space evolution remain later extensions.

**Completion criterion:** the shape artifact adds held-out predictive value and a measurable downstream benefit, or the study reports that the explicit acquisition stage did not help.

## Evidence accounting and controlled comparisons

Separate a shared-evidence experiment from an active-acquisition experiment. Begin with shared evidence to isolate the value of the learner. If acquisition is subsequently claimed as a contribution, compare the agent with random and conventional uncertainty-based selection from the same permitted pool.

Record distinct labeled vector groups and query-filter cases, exact reference construction, stopped interventions, trace generation, approximate executions, database time, model charges, fitting and tuning cost, and calibration or confirmation use. Separate benchmark preparation, optimizer-visible evidence and evaluator-only evidence. Cached reuse may avoid another execution, but it must retain its acquisition provenance and declared accounting treatment. Evaluator-driven label construction, including hardness-boundary preparation, belongs in this ledger.

Use native execution, calibrated fixed stopping, a simple hand rule, the current deterministic trees, a same-feature conventional learner and direct agent synthesis as comparators. Give comparable methods the same inputs, policy limits and quality selection procedure. The shape stage adds the same-representation conventional learner and the direct-synthesis ablation.

The principal result is a latency and recall learning curve against evidence and total adaptation cost. Also report feature overhead, tail behavior, stability across synthesis runs and the deployment query volume needed to recover adaptation cost. Compare different methods under a declared common compute budget as well as any model spending cap.

## Verification and release gates

Add focused tests for the following contracts:

- Exact interpreter agreement, first-stop selection, missing inputs and qualified feature enforcement.
- Unknown outcome preservation, truncated or mismatched prefix rejection and explicit label provenance.
- Vector-group split isolation and deliberate rejection of confirmation records in learner exports.
- Reproduction of the declared recall summary, tolerance boundary behavior and per-filter checks.
- Separate cold and reused activation records without changing the timing boundary.
- Content-addressed candidate recovery, budget preservation and idempotent result retrieval.

Use the existing synthetic native fixture for decision and transport conformance before a fresh Torch package. Any runtime or feature change requires its own native equivalence and overhead measurements. Keep learning tools outside the timed query path.

Freeze the candidate, feature profile, scorer version, evidence receipt and measurement contract before the existing development confirmation split is evaluated. Retain the separate canonical calibration, final-test and serving acceptance gates. If development confirmation is used to revise a candidate, record that consumption and use fresh protected evidence for a new independent claim.

The source checkpoint checks passed 15 focused pgvector tests, 58 harness compatibility tests and 127 mini-bench tests excluding PostgreSQL integration. These establish the checked local contracts; the Torch measurements and later acceptance gates determine the performance result.

## Implementation ownership and first milestone

Put the reusable feedback models, scorer, reports and archive in the core agent, using the existing public policy API, broker, experiment journal and store. Introduce a small learning module boundary as needed rather than adding a new production distribution. The pgvector extension continues to own native execution, exact references and feature qualification. Trial packages continue to own the pinned Torch acquisition recipe. Extend the harness only where it needs to consume the new evidence contract; mini-bench remains an observer and analysis tool.

Implement Stages 1 through 3 before expanding the runtime interface or shape model. Completion of this plan's first milestone means a fully traceable, measured candidate and an independent frozen confirmation evaluation, with an abstention path when the evidence does not support a candidate.

## Native predicate context and the next bounded measurement batch

The experimental native `query_predicate_threshold` getter is implemented in
`agent-pgvector` as the explicit `PredicateContextBackend` research adapter.
Its profile matches the predeclared `predicate-context-v1` fingerprint. The
legacy profile and twelve-argument execution ABI are preserved. Extraction of
the actual predicate scalar and binding in the existing begin batch are inside
the policy timing boundary; the new registry and trace normalization validate
that the returned scalar agrees with the actual query.

Local ARM native qualification passed on 4,000 synthetic rows: forty trajectory
comparisons, forty getter branches, int64 boundaries, unfiltered/zero semantics,
disabled availability, invalid-binding rejection and rollback recovery. See
`agent-pgvector/verification/predicate-context-v1.json` and
`agent-pgvector/docs/PREDICATE_CONTEXT.md`. This establishes local correctness;
x86 native execution, Reviews overhead, full copy/deployment and any learned
context policy remain unqualified. Old timings cannot qualify the new profile.

The separate `trials/torch-reviews-training-stops` package collects exactly the
49 distinct unknown outcomes requested by the four fixed depth/risk artifacts.
Three serial allocations each repeat those 49 actual stopped executions and
measure all four artifacts plus matched controls on the 300 learning queries.
This produces 147 requested-label executions and 32,400 retained native/policy
timing pairs (activation and reuse). It uses the existing verified Torch module,
profile, data and physical index, without incorporating predicate context into
the missing-outcome comparison. No remote jobs or provider calls were made
while preparing the package. Independent reporting checks exact requested
coverage, actual causal prefixes, preserved outcomes and measured timing.

After that batch returns, verify the raw artifacts, add only the 49 actual
outcomes, and reassess the four predeclared candidates. Continue the context
ablation under its separate qualification/profile and matching-baseline
requirements. Confirmation remains sealed and the original $15 model ledger
continues to cover any later paid learning.

## Prepared Torch x86 qualification and controlled context ablation

`trials/torch-reviews-predicate-ablation-v1` is the next separate, gated package.
It updates the training source to all 3,933 verified actual outcomes, including
the 49 newly measured first stops, while preserving the predeclared group folds,
feature definitions, fitting grid and quality objective. It permits no provider
calls or confirmation queries. This batch is a controlled CART feature ablation;
a context-aware direct-agent refit and CART-versus-agent comparison remain a
separate later model round under the same original ledger.

The Slurm dependency chain builds the pinned native C overlay inside the existing
SIF, qualifies the x86 getter and original causal trajectories on the original
physical index, freezes four CART fits under each profile, then measures block
zero before releasing serial blocks one and two. The old ABI and both new policy
profiles must preserve native results and all original feature values. Getter
boundaries, disabled availability, invalid/missing bindings and lifecycle reset
are qualification gates. No fitting precedes the gate and no refitting follows
new outcome/timing acquisition in this batch.

Both feature arms use the same candidate binary and policy driver. Native timing
uses the frozen ordinary-query driver, keeping the context validation/binding
cost in the policy/outer comparisons. Twenty-four arms include eight candidate
policies, matched-continue policies, plain/getter continue and two fixed-work
baselines under both profiles. Three allocations retain 86,400 pairs. New first
stops are actually measured under both profiles with unchanged causal prefixes;
unknown outcomes are never interpolated. The report verifies the frozen fitting
identity and raw coverage, reproduces each summary and pairs context/baseline
arms to estimate the feature's incremental cost/effect.

Local native synthetic qualification covers eight fits, all 24 arms, paired stop
acquisition, old-binary rejection, altered-lock rejection, raw coverage checks
and repeatable data-only export. It establishes package mechanics on ARM. Actual
x86 qualification and Reviews feature benefit remain pending the Torch run.

## Verified predicate ablation and prepared insertion/bypass study

The predicate campaign `reviews-predicate-ablation-20261019T235922Z.ilxcioru`
has now returned and been independently verified: 86,400 timing pairs, all eight
reproduced fits, and the actual predicate scalar at all 48,147 checkpoints.
Native x86 getter qualification passed. No candidate satisfies both the declared
per-filter recall and timing criteria. Context depth-three policies avoid early
stops on votes108, reducing recall-losing queries from 13 to three relative to
baseline risk-20, but the votes32 confidence bound still fails. Baseline continue
costs about 0.964 ms on activation and 0.786 ms on reuse; paired incremental plain
context cost is about 0.049 ms on reuse. The full independent result is retained
under the campaign's sibling `-analysis` directory.

`trials/torch-reviews-insertion-bypass-v1` is a separate execution-only study.
It retains seven representative frozen policy/control seeds, decomposing the
legacy driver, private prepared handles, fused initialization/ANN exchange and
query-only static bypass. A separate context arm restricts policy eligibility to
unfiltered queries. There are 29 predeclared arms, 300 learning queries, three
allocations and 104,400 retained pairs. It performs zero refits or provider calls.

Preparation is charged in cold timing. Every reused query is validated, routing
comes from its actual predicate, and both backend and outer clocks include it.
Bypass invokes ordinary native SQL and emits no fabricated checkpoint/work
observations. Native/fused acknowledgements, first stops, causal prefixes and
all 2,100 source-arm outcomes must qualify before measurement. The exact prior
qualified x86 binary is copied unchanged; no native source/index rebuild occurs.
The original 0.005 overall/per-filter noninferiority margin, vector-cluster
intervals, native recall floor and sealed confirmation split remain in force.

The implementation is opt-in in `agent-pgvector.optimized`. It also exposes the
optimized route through its application policy session; the default registered
backend retains its previous execution path. Failed policy execution is never
automatically replayed by the low-level probe. Application fallback remains
caller-controlled. Original scientific inputs and the same spending ledger are
preserved. New x86 execution qualification and Torch speedup remain pending.

## Verified insertion/bypass result and dispatch study

The insertion campaign `reviews-insertion-bypass-20261020T064451Z.ycqo7_i_`
returned 104,400 pairs, including 20,400 bypass pairs. Its x86 execution and
causal prefixes passed qualification; independent reconstruction reproduced all
raw results, per-filter recall bounds and paired timing effects. No arm qualifies
with activation or reuse. Baseline CART/static passes recall but costs +0.794 ms
on activation and +0.374 ms reused on the declared clock. The unfiltered-only
context arm passes recall but costs +0.848/+0.287 ms. Unrestricted context fails
the votes32 recall bound; fixed-8192 fails overall and per-filter bounds.

The reductions are real relative to the preceding policy path: prepared handles
save about 0.21 ms reused, fused exchanges save 0.22-0.26 ms on activation, and
static bypass further saves 0.468/0.405 ms for baseline CART. Always-continue
bypass still has residual cost. CPU profiling identifies vector text formatting,
query validation, repeated routing proof and policy-only Python setup as targets.

`trials/torch-reviews-dispatch-overhead-v1` freezes a new execution-only study:
five existing policies, six eligibility scenarios, and previous/validation/
routing/dispatch paths yield 24 arms. Three allocations retain 86,400 pairs on
the same 300 learning queries, 100 vector groups, three predicates and index.
Cold timing includes private-handle preparation and the entire checked query.
No query vector/value cache or untimed query preparation is introduced. Native
and outer application clocks are both retained; the original 0.005 per-filter
margin, 0.95 native recall floor and log-ratio timing gate are unchanged.

The opt-in adapter specialization retains shared model/filter validation and
falls back to the general validator for other inputs. It bounds proof/SQL-shape
caches and avoids policy-only context setup on native bypass. C-level vector
formatting must equal the frozen .9g encoding. Qualification checks all 7,200
arm/query executions and 1,800 traced prefixes before freezing the plan. A
separate synthetic 768-D CPU profile runs outside primary measurement, with no
Reviews data or database searches. No new policy, fit, label, provider call or
confirmation query is authorized by this study. New x86 dispatch execution must
qualify on Torch; local ARM evidence establishes package mechanics only.
