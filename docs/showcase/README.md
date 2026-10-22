# FANNAgent

**A budget-controlled research agent for filtered vector-search stopping policies.**

FANNAgent investigates when a vector database can stop searching earlier while
preserving retrieval quality. It gives an LLM tools to inspect permitted data,
form hypotheses, run experiments, analyze measurements, and propose bounded
stopping policies. A host controller manages spending, evidence access, saved
state, and evaluation.

This project demonstrates the engineering involved in connecting model-directed
investigation to a real experimental system: useful tool interfaces, actionable
feedback, durable runs, cost controls, and explicit acceptance boundaries.

## The problem

Filtered nearest-neighbor search must find nearby vectors that also satisfy a
condition, such as a metadata threshold. Search effort varies by query. A rule
that stops early can reduce work while also losing relevant results; instrumentation
and control overhead can consume the apparent saving.

FANNAgent explores candidate stopping rules and measures their consequences.
Research runs happen outside live query serving. Provider-backed research can
call a networked model API; an accepted policy executes without an LLM in the
query-serving path.

## Agent engineering to inspect

| Engineering area | What the repository implements | Starting point |
|---|---|---|
| Orchestration and context | Prepared-backend context, model/tool turns, trajectory persistence, submission, and termination | [Controller](../../src/fannagent/controller.py) |
| Tool interfaces and feedback | Domain operations, host argument validation, bounded errors, and correction handling | [Broker](../../src/fannagent/broker.py), [submission handling](../../src/fannagent/submission.py) |
| Evidence-linked experiments | Hypotheses registered before measurement, recorded outcomes, and evidence references attached to conclusions | [Experiment journal](../../src/fannagent/experiments.py), [research protocol](../RESEARCH_GUIDANCE.md) |
| Model-cost accounting | Per-attempt reservations, recorded usage, conservative treatment of uncertain charges, and saved spending contracts | [Model adapter](../../src/fannagent/model.py), [budget ledger](../../src/fannagent/budget.py) |
| Interruption recovery | Saved conversations and counters, durable evaluation receipts, and explicitly selected candidate checkpoints | [Run store](../../src/fannagent/store.py), [evaluation receipts](../../src/fannagent/evaluation_jobs.py) |
| Execution and evaluation boundaries | Isolated command execution, development evidence permissions, policy freeze, and separate final acceptance | [Environment](../../src/fannagent/environment.py), [study](../../src/fannagent/study.py) |

The model chooses investigations and candidate policies. The controller validates
requests, records what ran, restricts evidence access, and determines whether a
proposal meets acceptance criteria. The
[agent-design walkthrough](../agent-design.md) explains that action path and links
the mechanisms to existing tests.

FANNAgent builds on mini-swe-agent's base loop and model interfaces, with LiteLLM
dispatch. Its project-specific engineering surrounds those components with
domain tools, study orchestration, accounting, recovery, and evaluation. The core
includes a synthetic backend and an extension API; the pgvector integration is a
separate package. Individual contribution and collaborator attribution remain part
of the public-release review.

## A short reading path

1. Read the [agent design](../agent-design.md) for the architecture, one-action
   walkthrough, and division of model decisions and host authority.
2. Follow the [annotated real agent run](agent-run.md): ten provider-backed actions,
   a rejected policy and its revision, six research exports, and an explicit
   conclusion that none was accepted. The [curated trace](agent-trace.json)
   includes selected source evidence and provenance.
3. Inspect [invalid-action recovery coverage](../../tests/test_submission_resilience.py),
   [provider accounting coverage](../../tests/test_model.py), and
   [checkpoint coverage](../../tests/test_checkpoint.py) for concrete behaviors the
   project checks.
4. Read the recorded evidence below, keeping agent behavior, engineering checks,
   and scientific acceptance distinct.

These test links describe existing coverage. No tests or experiments were run to
prepare this documentation.

## Recorded behavior and research outcome

The existing saved records support a precise account of progress:

| Evidence | Recorded outcome | Interpretation |
|---|---|---|
| [Annotated `pair-0-exploratory` conversation](agent-run.md) | Ten provider attempts, one rejected over-depth candidate, a valid revision, and six exported research proposals; recorded model charges $0.530724. | A real model-directed analysis and feedback sequence using the specialized offline proposal runner. No new database timings or final acceptance were established. |
| [Aggressive proposals v2 audit](../verification/aggressive-proposals-v2-postrun.json) | Two exploratory conversations completed and exported 12 distinct policies; four conversations stopped at budget limits. There were zero complete A/B comparison pairs. | Evidence of model-driven proposal generation; the comparison of generation strategies remains inconclusive. |
| [Separate frozen-policy confirmation](../verification/frozen-proposals-timing-v1-runtime-fix-confirmation-postrun.json) | The selected candidate showed latency savings but failed the required recall criterion; neither activation nor reuse qualified. | That confirmation did not establish an acceptable deployment candidate. |

The walkthrough selects excerpts from existing records; the audit links point to
existing verification summaries. No campaign was executed or scientifically
reanalyzed to prepare these pages. They do not establish a general optimization
benefit or production readiness. The [full experiment index](../experiments/README.md)
preserves broader history, including unsuccessful runs. Many underlying raw
campaign artifacts live outside this repository, so its workspace links are not
yet a standalone public evidence bundle.

## Demonstration and publication status

The core has a [scripted simulation example](../../examples/fake.yaml) and
[existing simulation instructions](../../README.md#simulation). It demonstrates
the workflow using predetermined actions and synthetic latency. The annotated
run supplies recorded model-directed investigation. Database performance
requires measured database evidence.

The [real-run walkthrough](agent-run.md) is now available as a documentation
excerpt with its scope and omissions stated. Fresh-clone verification of the
demo, a dedicated results page, and public-access checks remain pending in the
[application-ready implementation plan](../APPLICATION_READY_IMPLEMENTATION_PLAN.md).
The current installation and development instructions remain unchanged.

Claims about budgets are scoped to the configured model API pricing, token bounds,
ceiling, and allowance; infrastructure costs are separate. Execution controls
assume a trusted controller and backend extensions. Literature guidance uses a
pinned cited primer. Performance and compatibility claims remain specific to the
recorded workload, runtime, and qualification scope.
