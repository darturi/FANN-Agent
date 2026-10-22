# Minimum application-ready release implementation plan

Created: October 22, 2026

Status: Portfolio release candidate prepared; hosted CI and publication checks in progress

## Objective

Prepare a public repository link suitable for job applications and a future
portfolio. A reviewer should be able to understand the agent, inspect an actual
provider-backed run, and reproduce a small local demonstration.

Center the presentation on agent engineering. Use the vector-search research as
the concrete problem, the source of domain-specific tools, and the setting for
rigorous evaluation.

Proposed opening description:

> FANNAgent is an offline research agent that investigates stopping policies for
> filtered vector search. It chooses experiments, analyzes measurements, and
> proposes policies within externally enforced budgets and evaluation boundaries.

The intended reader path is:

**README → agent architecture → annotated real run → runnable demo → research results.**

The initial documentation passes are complete. The subsequent request to finish
portfolio readiness authorizes source-install verification, CI, MIT licensing,
author attribution, and publication of the reviewed snapshot. No paid model or
research database execution is part of this release.

## Development boundaries

### Completed documentation-only passes

The initial pass authorized the first three Markdown files below. The subsequent
real-run documentation request also authorizes the walkthrough and curated trace,
plus links and progress updates in those existing documents:

| File | Purpose |
|---|---|
| `docs/APPLICATION_READY_IMPLEMENTATION_PLAN.md` | Record scope, development boundaries, and future completion criteria |
| `docs/agent-design.md` | Explain the existing agent architecture with source and test references |
| `docs/showcase/README.md` | Provide an introductory showcase page focused on agent engineering |
| `docs/showcase/agent-run.md` | Annotate one existing provider-backed conversation |
| `docs/showcase/agent-trace.json` | Store selected original fields and excerpts with source provenance as documentation |

Those initial passes left source, configuration, tests, and research artifacts
unchanged. The release completion pass adds the root README, usage/contribution/
results/demo/validation documents, MIT licensing and notices, and CI. The only
runtime-source edit wraps an overlong controller condition; its syntax tree is
unchanged. No tests, prompts, dependencies, policy semantics, or statistical
criteria were modified.

Verification now includes an isolated clone, locked dependency installation,
existing tests, lint, SDK typing, distribution builds, and the scripted no-key
lifecycle. Original research worktrees, `main`, and experiment records remain
protected. Publication uses `docs/application-ready` and a named portfolio tag,
with a clean companion-backend export rather than changing its research checkout.

Current deliverables:

- [x] Record the documentation-only scope and development boundaries.
- [x] Draft the [agent-design document](agent-design.md) from the existing source.
- [x] Draft the [showcase landing page](showcase/README.md) without changing current
  installation or development instructions.
- [x] Prepare an [annotated real agent run](showcase/agent-run.md) and
  [curated trace](showcase/agent-trace.json) using saved records only.

The [results page](results.md), [contribution statement](CONTRIBUTIONS.md),
[local demo](showcase/local-demo.md), and [validation record](showcase/validation.md)
now track release completion. Hosted CI and public-link checks will be completed before
the stable core portfolio tag is issued. The author explicitly approved public
publication of both reviewed snapshots. The companion source is available at
[`portfolio-v1`](https://github.com/darturi/FANN-Agent-pgvector/tree/portfolio-v1);
the core branch is published while hosted CI is verified.

### Release boundaries

- Select a named release snapshot when publication work is authorized. Ongoing
  research can continue independently; selecting a snapshot does not freeze the
  active development branch.
- Apply publication completion criteria to that snapshot. They are not new
  prerequisites for running experiments or continuing feature development.
- Preserve model prompts, tool behavior, spending contracts, policy semantics,
  workload splits, evaluation entitlements, and acceptance criteria during the
  documentation work. Functional changes require a separate implementation scope.
- Preserve historical experiment files and outcomes. Publication summaries cite
  existing evidence; they do not overwrite records or reinterpret failures as
  successful acceptance.
- Keep future demo and CI checks isolated from private databases, active research
  runs, and paid providers. Runtime demo outputs belong in disposable directories.
- If installation or CI exposes a functional problem, record the issue and define
  a scoped fix. Do not broaden the publication pass into a refactor or change
  scientific criteria to obtain a passing check.
- The author confirmed sole project-specific implementation and selected MIT.
  Publish only the reviewed branch/tag and a clean companion-source snapshot.
  Keep local and remote core `main`, active research branches, original backend
  checkout, raw artifacts, and verification records unchanged.

### Description and claim boundaries

Describe the system as an offline, LLM-driven, tool-using research agent with
host-enforced study boundaries, persistent state, and model-cost accounting.
Explain that offline means research outside live query serving; provider-backed
research can use networked model APIs. Describe spending controls in terms of the
configured pricing/token assumptions, ceiling, and allowance; infrastructure costs
are a separate scope.

Credit mini-swe-agent for its base loop and interfaces. Tie individual contribution
claims to verified authorship. Distinguish the static cited research primer from
autonomous literature search, synthetic demonstrations from real model behavior,
and policy proposals from accepted deployments. Claims of production readiness,
general performance improvement, or guaranteed security require further evidence.

## Scope and current gaps

The local review found substantial source code, tests, verification records, and
experiment history. The publication work should make that material understandable,
accessible, and reproducible from the selected public snapshot.

Observed at planning time:

- Recent core work is on a feature branch, with additional uncommitted work.
- The pgvector extension is a separate repository with no configured remote in
  the reviewed checkout.
- The README begins with installation instructions that assume a local release
  bundle; public package and image publication remain pending release gates.
- The experiment index depends on sibling workspace directories and artifacts
  that a clone of FANN-Agent does not include.
- Ordinary tests and verification records exist, but no GitHub Actions workflows
  were tracked in the reviewed core repository.
- Neither the core nor the extension had a top-level project license.
- Public access to the configured GitHub remote was not verified.

Recheck these observations when implementation begins. Preserve unrelated work
already present in the checkout.

## 1. Select the exact version to showcase

### Tasks

- [x] Review the current feature branch and uncommitted work; select the completed
  pieces that belong in the application-ready snapshot.
- [x] Select a stable core commit and a compatible pgvector extension commit.
- [ ] Keep the existing package separation and establish an accessible repository
  for the extension.
- [ ] Document compatible versions, working repository links, and the exact clone
  directory names required by any source-install instructions.
- [x] Review the selected files and Git history for credentials, private data,
  logs, and material that should not be published.
- [ ] Confirm which research material can be shared and document collaborators
  and upstream contributions.
- [x] Choose and add an appropriate project license for each published repository.

### Completion criteria

- The selected public snapshot contains every file needed by its instructions.
- Both packages have accessible source and documented compatible revisions.
- The publication review is complete before source or evidence is made public.
- Unrelated unfinished research work is preserved.

## 2. Explain the agent design and individual contributions

### Deliverables

- Revised `README.md`.
- New `docs/agent-design.md`, including an architecture diagram.

### Tasks

- [x] Rewrite the README in this reading order: problem, why an agent is useful,
  agent capabilities, individual contributions and upstream components,
  architecture, real run, local demo, results, and limitations.
- [x] Explain which decisions the model makes and which constraints the controller
  enforces.
- [x] Explain that policy research happens offline and that deployed stopping
  policies do not require an online LLM call.
- [x] Credit mini-swe-agent for the base agent loop and interfaces.
- [x] Identify the orchestration, domain tools, persistence, controls, and
  evaluation work implemented in this project, with accurate attribution.
- [x] Document the capabilities below and link each to implementation code and
  relevant existing tests.

| Capability | What the explanation must demonstrate |
|---|---|
| Agent orchestration | How context, model actions, observations, and termination fit together |
| Tool design | How domain operations become usable tools with validated arguments and actionable feedback |
| Durable state | How conversations, experiment records, and candidate checkpoints survive interruption |
| Cost control | How reservations, retries, uncertain charges, and spending limits are enforced |
| Execution boundaries | How the sandbox and broker control access to database operations and evidence |
| Evaluation | How development, calibration, final testing, and acceptance remain separated |

Starting points for the implementation walkthrough include
`src/fannagent/controller.py`, `model.py`, `broker.py`, `environment.py`,
`budget.py`, `store.py`, `experiments.py`, `submission.py`, and `study.py`.
Verify the published revision before adding precise source links.

### Completion criteria

- A new reader can explain the purpose and current outcome of the project.
- A technical reviewer can follow one model action through validation, execution,
  recorded evidence, and the next decision, and locate the corresponding code.
- Individual contributions and framework responsibilities are explicit.

## 3. Publish one annotated real agent run

This is the primary evidence of model-directed agent behavior. The deterministic
simulation in step 4 serves a separate reproducibility purpose.

Documentation is prepared for `pair-0-exploratory` in the v2 proposal study.
It includes an actual structural rejection and revision, the six exported
proposals, and recorded cost and outcome. The study-specific runner and its
training-only evidence scope are explicit. External publication remains part of
step 6.

### Deliverables

- New `docs/showcase/agent-run.md`.
- A small sanitized structured trace, such as
  `docs/showcase/agent-trace.json`.

### Tasks

- [x] Inspect existing provider-backed runs and select one with a coherent sequence:
  initial context, hypothesis, tool calls, measurements, revised decision, and
  recorded outcome.
- [x] Start by assessing the two completed exploratory conversations recorded in
  the aggressive-proposals v2 study. Verify their suitability and artifact
  availability before selecting either.
- [x] Record the model, source identity, request count, recorded cost, and terminal
  status of the chosen run. Use the sealed manifest for this archive; do not
  invent a historical Git revision.
- [x] Present the task, working question, tool arguments, relevant observations,
  evidence references, and conclusions in a readable annotated sequence. Label
  editorial interpretations; this runner did not use the ordinary guided-mode
  hypothesis journal.
- [x] Identify what the model chose and what the controller enforced at each
  important point.
- [x] Sanitize credentials, private query data, infrastructure details, and other
  unsuitable material; label omissions and abridged excerpts.
- [x] Preserve the original outcome, including budget exhaustion or abstention
  where applicable. Keep provenance to the source records.
- [x] Include an actual policy-validation rejection and revision, plus recorded
  budget handling.
  Both examples come from the selected conversation; no synthetic fixture is
  presented as an observed event.
- [x] Confirm that an existing run is suitable. No new paid run is needed for this
  walkthrough; any future evidence gap is a separate decision.

### Completion criteria

- A visitor can inspect concrete evidence of model-directed investigation without
  accessing the original workspace.
- The presented decisions are connected to actual tool results and recorded
  evidence.
- The outcome and limitations are accurate, and synthetic examples are labeled.

## 4. Provide a reproducible local demonstration

### Deliverables

- Verified source-install and demo instructions in the README, with additional
  detail in `docs/showcase/local-demo.md` if needed.
- Representative output from the verified workflow.

### Tasks

- [x] Use the existing `examples/fake.yaml` simulation.
- [x] Document supported prerequisites and exact source-install commands without
  assuming unpublished packages or local release bundles are available.
- [x] Document the prepare, run, resume, evaluate, and report sequence.
- [x] Verify the instructions in a clean environment using the selected snapshot.
- [x] Include representative output showing experiment records and tool activity,
  interruption and resume, a frozen policy, subsequent evaluation, and the final
  report.
- [x] Clearly label the demonstration as a deterministic simulation and explain
  its relationship to the provider-backed run and real database integration.
- [x] Document cleanup and the files generated by the demo.

### Completion criteria

- A fresh clone completes the documented workflow without credentials, paid model
  calls, private files, or sibling research directories.
- The output demonstrates the documented lifecycle and is explicitly identified
  as simulated evidence.

## 5. Publish a concise, accessible results page

### Deliverables

- New `docs/results.md`.
- The small supporting summaries or accessible artifacts needed to substantiate
  its results table.

### Tasks

- [x] State the research question, workload, baseline, acceptance criteria, and
  current conclusion.
- [x] Include one concise results table with appropriate provenance and limits.
- [x] Include the held-out confirmation finding: a candidate achieved latency
  savings but failed the recall requirement. Verify all numbers against the
  selected evidence before publication.
- [x] Explain what the evaluation revealed and how the system handled that result.
- [x] Distinguish implemented agent capabilities, database engineering checks,
  exploratory findings, and confirmed performance outcomes.
- [x] Publish selected supporting summaries with working links; replace local
  workspace references in the main reader path.
- [x] State data-access requirements and the scope of hardware/environment
  qualification where relevant.
- [x] Preserve the full internal experiment history without making it a prerequisite
  for understanding the public showcase.

### Completion criteria

- Every headline claim has accessible supporting evidence.
- The page accurately separates implemented capabilities from demonstrated
  research outcomes.
- Reading the showcase does not require the original `trials/`, `harness/`,
  `release/`, or other private workspace directories.

## 6. Validate and publish the selected snapshot

### Deliverables

- New `.github/workflows/ci.yml`.
- A short validation record, such as `docs/showcase/validation.md`.
- A tagged, reviewed public snapshot.

### Tasks

- [x] Add CI for ordinary tests, linting, the existing SDK typing check, package
  building, and the scripted demo.
- [x] Fix failures exposed by those checks and record the exact validation scope.
- [x] Keep environment-dependent database qualification documented separately
  from checks that run in ordinary CI.
- [x] Confirm that CI and demo commands cannot initiate paid model calls or access
  private databases.
- [x] Perform the final setup and demo review from a fresh clone.
- [ ] Review GitHub while signed out: repository access, extension access, source
  references, evidence links, setup instructions, attribution, and results.
- [ ] Tag the reviewed snapshot and use a stable link for applications.

### Completion criteria

- CI passes on the exact selected snapshot.
- The local demo works from the published source.
- All primary links work for an unauthenticated visitor.
- Validation records distinguish current checks from historical qualification.

## Definition of application-ready

- [x] The README gives a clear explanation of the problem, the agent, individual
  contributions, and current outcome.
- [x] The agent-design document connects important engineering decisions to code
  and tests.
- [x] An annotated provider-backed run demonstrates actual model-directed work.
- [x] A fresh clone can run the deterministic demonstration without private
  dependencies or paid calls.
- [x] The results page has accessible evidence and appropriately scoped claims.
- [ ] The selected source is accessible, attributed, licensed, and reviewed for
  private material.
- [ ] CI, public links, and the tagged snapshot have been checked.

## Later work outside this minimum release

- Hosted interactive agent or portfolio website.
- Package-registry or public container-image publication.
- Additional database backends.
- New research experiments or improved optimization results.
- Broader hardware and production deployment qualification.
- A promotional video or GIF, unless it proves inexpensive to produce from the
  verified demo.

The minimum release is complete when the reader path and completion criteria
above are satisfied. Further research success is not a prerequisite for presenting
the agent engineering and existing findings accurately.
