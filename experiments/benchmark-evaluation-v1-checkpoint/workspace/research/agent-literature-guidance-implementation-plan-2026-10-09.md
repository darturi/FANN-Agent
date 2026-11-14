# Implementation plan for literature guidance in FANNAgent

Revision implemented and verified locally, October 9, 2026. The paid Claude smoke test is deferred at the user's request; comparative effectiveness remains unassessed.

Milestones 1–4 and deterministic verification in Milestone 5 are implemented. The core non-integration suite passed 147 tests, pgvector's offline suite passed 33, and changed-module lint and public SDK typing passed. All three research modes passed clean installed-wheel workflows for both fake and independent backends, alongside connection-free pgvector discovery. Built wheels and source distributions are retained under each package's `dist/research-guidance/`. See [implementation status](../agent/IMPLEMENTATION_STATUS.md), [workflow documentation](../agent/docs/RESEARCH_GUIDANCE.md), and [verification evidence](verification/agent-literature-guidance-2026-10-09/verification.json).

Give the offline agent a compact, cited account of relevant ANN research and require it to state a testable hypothesis before acquiring experimental evidence. Record what it measured and how the result influenced its policy. The intended outcome is a trajectory whose experiment choices can be inspected against both published principles and actual observations.

Implement this within the existing core agent and its broker. Claude continues to choose its experiments. The policy language, backend stopping semantics, recall acceptance criteria, monetary contract, and separate final evaluation retain their current responsibilities. Implementation and verification began after the mini-bench execution record reported completion at 2026-10-09 14:54:31 UTC. Verification used fake and independent backends and mocked providers; no paid provider trial or new database benchmark was started.

## Current implementation and revision boundary

The shared prompt in `agent/src/fannagent/controller.py` explains the objective, tools, runtime inputs, policy representation, and calibration requirement. It explicitly delegates experiment selection to the model. `Tools.startup_context` supplies backend, dataset, capability, feature-registry, and budget context. Neither supplies a literature primer.

The broker already provides the evidence needed for this revision: development queries, probes, actual stopping labels, descriptors, candidate evaluation, and aggregate calibration. The store saves conversations, content-addressed artifacts, and durable state. Reuse these interfaces rather than adding a research service or another model.

A recorded explanation establishes what the model claimed before an experiment. Schema validation can check its fields and references; it cannot establish that the model understood a paper or that its conclusion follows from the evidence. Keep those separate in reporting and review.

## Design decisions

| Area | Proposed decision |
| --- | --- |
| Literature delivery | Ship a versioned, reviewed primer in the core package and include its compact text in the initial system prompt. |
| Experiment accountability | Require a bounded experiment plan before evidence-producing broker operations and a conclusion before explicit candidate submission. |
| Citation policy | Accept registered principle IDs. Permit hypotheses based on measurements or exploration without forcing a literature citation. |
| Experiment selection | Preserve autonomous selection, batching, Python analysis, and candidate revision. |
| Evidence linkage | Have the host record operation outcomes, query identities, policy hashes, and returned evidence automatically. |
| Additional model calls | Introduce no automatic literature retrieval, critic, or summarization calls. Planning and conclusions use ordinary agent turns. |
| Compatibility | Make guidance explicit in new generated configurations. Preserve the behavior and saved messages of existing configurations and runs. |
| Success criteria | First establish reproducible guidance and evidence records. Assess any benefit to evidence efficiency or policy quality separately. |

## Milestone 1 Build the cited primer

Add `agent/src/fannagent/guidance.py` and `assets/research_primer_v1.json`. Use a single structured source for both the rendered primer and the machine-readable principle registry, avoiding separate copies that can disagree.

Each source entry records a stable source ID, title, authors, versioned URL, relevant sections, and verification date. Each principle records its ID, concise claim, source sections, applicability limits, suggested investigation, and classification as a literature finding or a project rule. Store paraphrases rather than paper excerpts.

Start with two papers and these three literature principles:

| Principle ID | Content | Application to this agent |
| --- | --- | --- |
| `E2E_QUERY_EFFORT` | Query-dependent search effort motivates adaptive termination. | Investigate which development queries permit early stopping while preserving default recall. |
| `E2E_FILTER_SIGNALS` | Early filter observations can complement distance signals when estimating filtered-search cost. | Investigate supported filter and distance features together, with feature availability and collection cost made explicit. |
| `GLS_LOCAL_ALIGNMENT` | Global and local selectivity describe the relationship between metadata predicates and vector neighborhoods. | Use existing exact descriptors to diagnose variation among queries with similar global selectivity. |

The first two derive from [E2E version 2, especially Sections 3 and 4](https://arxiv.org/html/2602.06721v2). The third derives from [the MoReVec and GLS paper version 1, Section 4](https://arxiv.org/html/2602.11443v1). These motivate hypotheses; they do not establish that a particular threshold or rule will work on the prepared pgvector copy. E2E's predictor and its reported performance are not implemented by supplying this primer.

Explain the following separately as project rules:

- Returning enough qualifying records does not establish nearest-neighbor recall. Evaluate against exact references and the ordinary default execution.
- Exact neighborhood descriptors and stopping labels are development evidence. Only approved, available runtime features can drive a deployed policy.
- A stopping rule controls a fixed, qualified search opportunity. Missing features, non-HNSW routes, or an absent opportunity require the behavior declared by the backend.
- Measure actual stopping and complete query latency, including feature and policy overhead; distance-work savings alone do not establish a speed improvement.
- Preserve development, calibration, and final-test boundaries. Calibration feedback is aggregate, and final testing remains evaluator-only.

Include one worked example and one caution about treating a correlation as evidence for further investigation rather than a causal explanation. Keep the initial primer below 8 KiB of UTF-8 text, with roughly 700–900 words as an editorial target. Persist the full manifest separately.

**Gate:** Every literature claim has a supporting section and a clear applicability limit. Every suggested runtime signal maps to the selected feature registry or is explicitly described as offline evidence. The primer does not imply a universal recall guarantee or a faithful reproduction of another system.

## Milestone 2 Integrate guidance and pin it to the run

Introduce an optional common `research` configuration with three modes:

| Mode | Agent behavior |
| --- | --- |
| `baseline` | Existing prompt and experiment behavior. |
| `protocol_only` | Explicit hypothesis and conclusion protocol, without the literature primer. |
| `guided` | The same protocol plus the cited primer. |

New `init` output, examples, and trial templates select `guided`. An absent `research` field means the existing baseline behavior, allowing old hand-written configurations and saved runs to continue predictably. Omit the field from public serialization when it is absent, so existing configuration identities remain stable. Changing modes requires a new run.

For a fresh guided run, collect backend context, resolve the primer against the available feature profile, and render the system prompt before constructing the first provider request. Filter suggested experiments by capability without rewriting the cited scientific claim. For example, do not recommend a live queue-valid ratio when the backend only permits an offline reconstruction.

Persist the selected mode, primer manifest and hash, rendered prompt hash, and `research_protocol_version=1` before the first model request. Expose an approved development artifact containing the primer and its source registry. Include its reference and compact protocol information in startup context. Keep this metadata separately versioned from the existing startup-context and checkpoint protocols.

On resume, use the run's saved messages and exact primer snapshot. Do not replace the primer with the current package's copy or insert new literature into an existing baseline conversation. Reject an unsupported recorded protocol version before model spending. Resume must retain the mode, experiment state, invalid-turn accounting, and monetary contract.

Check the conservative request-size bound against the expanded prompt before dispatch. If the configured input bound is too small, return an actionable error without a provider call. Do not silently enlarge that bound or alter the rate card.

**Gate:** The first request contains the intended primer and protocol; the saved trajectory predates that request. Resume reproduces the same guidance identity without duplicate messages, and configurations without the new field preserve existing behavior.

## Milestone 3 Record hypotheses and experimental evidence

Add internal schemas and persistence helpers in `agent/src/fannagent/experiments.py`. Add one broker operation, `experiment`, with `start`, `finish`, `get`, and `list` actions. Keep the upstream bash tool and the standard-library tool client unchanged; this remains a `fannagent-tool` operation.

### Starting an experiment

Require a brief plan containing:

- A stable client key for registration retries and a purpose: investigation, candidate evaluation, or calibration.
- A testable hypothesis and why this experiment is useful now.
- A basis: registered literature principles, previous permitted evidence, or an explicitly exploratory idea.
- The intended comparison, observations to collect, and measurements to inspect.
- An expected observation and an observation that would challenge the hypothesis.
- The next decision if supported or challenged, including a possible policy change when a candidate already exists.

Bound the serialized plan to 6 KiB and individual prose fields to 512 characters. These are concise scientific justifications, not requests for private chain-of-thought. Validate principle IDs against the pinned registry and evidence references against development access rules. Do not require invented citations for exploratory hypotheses. `protocol_only` accepts measurement and exploratory bases using the same schema.

The host assigns the experiment ID and persists the plan before admitting measurements. Reusing a client key with identical content returns the original ID; conflicting content returns correction feedback. Allow one open experiment per run, consistent with the current sequential controller. One experiment can span multiple turns and multiple probes.

### Admitting operations and collecting outcomes

In `guided` and `protocol_only`, require an open experiment for `count`, `descriptors`, `probe`, `audit`, `labels`, `development_evaluate`, and `calibrate`. Orientation operations—`inspect`, `queries`, `sample`, and `artifact`—remain available without a plan. Local policy `validate` remains available and attaches to the active experiment when present.

At the broker boundary, attach empirical operations to the active experiment automatically. This avoids adding a required ID to every existing operation. Record a pending operation before execution, then its success or failure, actual query hash or policy hash where applicable, artifact references, and bounded returned observations. Explicitly record timeouts and absent stopping opportunities.

Preserve existing tool results and scientific validation. The journal should reference existing evidence rather than duplicate traces. For calibration, expose only the aggregates already returned by the current calibration tool; never publish private rows, private stopping labels, or test references through experiment records. Reuse the same host operation recording for baseline comparisons, marking those actions as unplanned.

Python analysis remains available in the sandbox. Its commands and output already belong to the trajectory. A conclusion can describe derived observations, but they must be distinguished from host-measured values and linked to the permitted input artifacts. Do not treat arbitrary model-written files as authoritative measurement records.

### Concluding an experiment

Require `finish` to provide an assessment—supported, challenged, or inconclusive—a short observation summary, evidence references, and the resulting decision. Bound the conclusion to 4 KiB. Validate references against recorded observations and the permitted supporting evidence declared in the plan. Store the model's assessment separately from trusted operation outcomes.

Reject missing plans, unknown principles, invalid references, conflicting retries, and malformed conclusions through the existing bounded `InvalidSubmission` feedback. These are structural checks; they do not judge scientific persuasiveness. Retain the existing three-invalid-turn limit and charge accounting.

For explicit `submit`, require the submitted policy hash to appear in a completed experiment with successful calibration for that exact candidate. The existing study remains authoritative about calibration eligibility and freezing. Finish the experiment before submission because freezing closes development tools.

Budget exhaustion must still be able to freeze an eligible designated checkpoint. An incomplete model conclusion must not invalidate otherwise accepted cached calibration. The host marks an open experiment interrupted and records checkpoint finalization provenance without another model call or measurement. Explicit abstention and step-limit interruption retain their existing outcomes.

### Example experiment

Hypothesis: among queries with comparable global match fractions, locally sparse qualifying neighborhoods may make a rule based only on finding `k` qualifying records stop too early.

Basis: `GLS_LOCAL_ALIGNMENT`, `E2E_FILTER_SIGNALS`, and any prior development observations.

Measurement: compare permitted development queries using neighborhood descriptors and actual stopping labels; inspect how much later work improves recall relative to ordinary execution.

Possible revision: consider an available filter or progress signal alongside the qualifying-result count. Challenge: if local sparsity does not distinguish late improvements, abandon that explanation and investigate another signal. Exact GLS remains a diagnostic rather than a runtime policy input.

**Gate:** Every evidence-producing action in a protocol run has a plan saved beforehand and a host-recorded outcome. An invalid plan prevents the database operation. Failed experiments and contrary evidence remain visible. Submission and checkpoint recovery preserve existing scientific acceptance criteria.

## Milestone 4 Preserve the journal and expose it for review

Use the existing SQLite state and artifact mechanisms, keeping authoritative experiment state private and publishing sanitized development projections. Store each bounded record separately rather than repeatedly rewriting an ever-growing journal. Retain compact indexes and durable pending-operation status; publish state pointers only after referenced artifacts are durable.

Make `start` and `finish` idempotent. On interruption, resume an open experiment without pretending it has concluded. If the controller crashed during an operation, report its outcome as unknown unless a durable result proves completion. Do not automatically replay a database measurement to repair a journal.

If artifact storage is exhausted, retain a bounded SQLite record of the operation and storage failure, following the existing exhaustion-report approach. If a plan cannot be saved durably, do not admit new measurements. Preserve the existing ledger and eligible checkpoint recovery paths.

Extend read-only `status` and `report` output with the guidance identity, experiment counts and states, candidate origins, and incomplete records. Provide a separate journal view or CLI command for plan → observations → conclusion → candidate relationships. Keep the final acceptance report's current scientific fields and test results intact; new provenance is additive. Older reports show guidance as unrecorded or baseline rather than infer it retrospectively.

Current calibration permits repeated aggregate feedback during candidate selection. Record those rounds transparently. This revision does not turn that behavior into a one-use calibration protocol or a statistical guarantee for future queries; a stricter selection protocol would be separate work.

**Gate:** Reviewers can identify the primer used, read the hypothesis preceding a measurement, inspect supporting evidence, and follow a submitted or recovered candidate to its calibration. Journal access cannot reveal evidence that existing tools withhold.

## Milestone 5 Verify behavior and assess the revision

Run verification after mini-bench terminates. Begin with the fake backend and mocked provider so failures can be exercised without paid calls or Docker workloads.

| Area | Required verification |
| --- | --- |
| Primer | Registered citations and principle IDs; source classifications; byte bound; capability-aware suggestions; inclusion in built wheels and source distributions. |
| First request | Primer and protocol present; persisted before dispatch; input-bound rejection makes zero provider calls. |
| Compatibility | Old configurations retain their hashes and behavior; old trajectories resume unchanged; guided runs retain their exact primer snapshot across package updates. |
| Admission | Missing plan, bad reference, or invalid schema prevents the measured backend call; correction feedback uses existing accounting. |
| Evidence | Actual query and policy identities recorded; multiple operations attach to one experiment; errors and unknown outcomes remain distinct. |
| Isolation | Unknown and private artifact references rejected; calibration journals expose only existing aggregates; final-test references remain unavailable. |
| Recovery | Registration and conclusion retries are idempotent; resume preserves open experiments; journal-storage failure does not silently repeat a measurement. |
| Finalization | Explicit submission has candidate provenance; eligible budget checkpoints still freeze with an interrupted experiment; invalid or absent checkpoints retain current outcomes. |
| Extensibility | Fake and independent extension tests remain free of pgvector assumptions; pgvector guidance respects its feature availability and stopping scope. |

Update scripted demonstrations to exercise start → probe → conclusion → candidate calibration → conclusion → submit without a provider. Keep baseline demonstrations available. Reuse startup-context, model, submission-resilience, checkpoint, workflow, and installation tests, adding focused experiment tests where the current suites do not cover the new boundaries.

After deterministic verification, perform one small configured Claude trial on the prepared copy. Check that it states a falsifiable hypothesis, gathers appropriate evidence, and records a defensible decision. A valid abstention is an acceptable outcome. This is a behavior smoke test, not evidence that the revision improves optimization.

For effectiveness, compare `baseline`, `protocol_only`, and `guided` across fresh runs with the same model, workload/splits, backend state, rate contract, and declared monetary and evidence budgets. Separate the effect of explicit planning from the additional literature guidance. Retain actual prompt/token costs and measured execution counts; equal ceilings do not imply equal numbers of experiments. The current controller enforces money, but does not enforce a labeled-query budget, so the comparison runner must define and enforce any common evidence cap rather than imply it already exists.

Measure time and charges to first passing candidate, distinct queries labeled, exact-reference and calibration work, accepted-candidate frequency, and final recall/latency under the existing criteria. Inspect hypothesis relevance, contrary-evidence handling, citation correctness, and conclusion-to-policy links on a declared sample. Use multiple synthesis runs to assess variability before making a benefit claim; choose the run count and primary endpoint in the evaluation protocol before viewing final outcomes.

**Release gate:** Protocol correctness, resume compatibility, evidence isolation, packaging, and a small paid behavior trial pass. An improvement in policy quality or evidence efficiency requires separate comparative results.

## Expected file changes and delivery order

| Files | Revision |
| --- | --- |
| New `agent/src/fannagent/guidance.py` and `assets/research_primer_v1.json` | Source registry, principle definitions, bounded rendering, and capability-aware suggestions. |
| `agent/src/fannagent/config.py`, `onboarding.py`, examples, and generated templates | Explicit guidance modes and compatible serialization. |
| `agent/src/fannagent/controller.py` | Prompt assembly, pinned guidance metadata, resume handling, scripted protocol, and interruption provenance. |
| New `agent/src/fannagent/experiments.py` | Typed plans/conclusions, durable state, idempotency, operation records, and permitted projections. |
| `agent/src/fannagent/broker.py` and `submission.py` | Experiment operation, admission checks, evidence linkage, and bounded correction feedback. |
| `agent/src/fannagent/cli.py` and reporting helpers | Read-only guidance and experiment inspection alongside current reports. |
| Core tests and pgvector startup-context tests | Meaningful boundary, compatibility, failure, and packaging checks. |
| `agent/README.md` and `IMPLEMENTATION_STATUS.md` | User workflow, example, recorded qualification, and interpretation limits. |

Deliver primer and configuration integration first, then the experiment protocol, then reporting and recovery behavior. Complete deterministic verification before the small paid trial. The final comparative study follows functional release readiness and can report an inconclusive or negative result.

The revision adds no live paper search, retrieval index, extra critic agent, Bayesian optimizer, explicit shape-model acquisition stage, engine patch, or policy-language extension. Those would each change a separate part of the method and should be evaluated independently.
