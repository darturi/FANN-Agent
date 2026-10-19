# Policy learning and evaluation revision plan

Prepared October 19, 2026. Status: Stage 1 implemented and verified on `feat/measured-policy-feedback`; Stage 2 awaits verified feedback from the running experiment. See [offline policy learning tools](OFFLINE_LEARNING.md) for usage and the [verification record](verification/offline-learning-v1.json) for checks and evidence identities.

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

### Stage 3 Align learning qualification and resume feedback rounds

Audit the learner and broker qualification path against the study objective. Distinguish a conservative proposal label such as `preserves_default` from aggregate empirical acceptance at tolerance 0.005. Preserve every measured per-query recall loss in reports. Replace any unconditional zero-loss proposal rejection only in the new study version, with tests proving that the declared aggregate constraints remain enforced. Keep legacy locks and serving acceptance behavior unchanged.

Provide bounded feedback bundles containing measured premature stops, unnecessary continuation, uncertain decisions and cases whose cheap score disagrees with actual latency. Link each observation to its measurement record. An explanation must distinguish a measured fact from a hypothesis for another experiment.

Archive all candidates by content hash with their policy, runtime profile, evidence version, fitting configuration, measured outcomes and selection status. Resume should recover the recorded result and selected candidate without rerunning ambiguous operations. A saved candidate remains provisional until it passes the required later evaluation.

Resume model work only as an explicitly executed next stage under the original durable $15 campaign ledger, counting prior confirmed charges and uncertain reservations. Set per-round model and measurement limits in advance. Reaching a turn or spending limit must retain supported candidates or a clear abstention reason.

**Completion criterion:** a frozen candidate demonstrates measured training savings at the declared recall criterion, or the round ends with a specific evidence-backed abstention and a bounded next investigation.

### Stage 4 Test information sufficiency when failures persist

Use measured failures to determine whether the current feature interface can distinguish cases that require different stopping decisions. Repeated fitting cannot separate identical allowed inputs. Quantify the conflicting states and their recall consequences before proposing additional runtime observations.

If needed, test one cheap query-side input, such as the actual predicate threshold or a permitted selectivity summary, in a separate feature ablation. Verify the getter, scope, availability, inference cost and prefix behavior before exposing it to the learner. Freeze a new feature profile and give the same information to the conventional baselines. Executor feedback and richer frontier statistics require their own measured engineering justification.

**Completion criterion:** the added information improves measured quality or latency enough to pay its collection cost. Otherwise retain the simpler interface and report its limitations.

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
