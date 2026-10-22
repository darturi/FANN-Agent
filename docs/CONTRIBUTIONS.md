# Contributions and upstream credit

Daniel Arturi ([darturi](https://github.com/darturi)) designed and implemented
FANNAgent's project-specific code, experimental tooling, and pgvector integration.
This attribution was confirmed by the project author during portfolio preparation.

| Contribution | Code or evidence to inspect |
|---|---|
| Domain-agent orchestration and prepared-run context | [Controller](../src/fannagent/controller.py), [startup-context coverage](../tests/test_startup_context.py) |
| Domain tools and validation feedback | [Broker](../src/fannagent/broker.py), [submission tracking](../src/fannagent/submission.py), [recovery coverage](../tests/test_submission_resilience.py) |
| Persistent evidence and resumable runs | [Store](../src/fannagent/store.py), [evaluation receipts](../src/fannagent/evaluation_jobs.py), [checkpoint coverage](../tests/test_checkpoint.py) |
| Model API accounting | [Budgeted model adapter](../src/fannagent/model.py), [ledger](../src/fannagent/budget.py), [accounting coverage](../tests/test_model.py) |
| Research guidance and experiment records | [Guidance](../src/fannagent/guidance.py), [experiment journal](../src/fannagent/experiments.py) |
| Policy learning and scientific evaluation | [Offline learning](../src/fannagent/learning/), [study controls](../src/fannagent/study.py), [results](results.md) |
| Backend SDK and integration boundary | [Public API](../src/fannagent/api/), [SDK guide](EXTENSIONS.md) |
| Native pgvector integration, instrumentation, and execution studies | [Separate extension source](https://github.com/darturi/FANN-Agent-pgvector/tree/portfolio-v1) and its qualification records |

The [annotated real run](showcase/agent-run.md) shows a model using the supplied
experimental interface and writing its own Python analysis. Those generated
analysis scripts are agent outputs. The interface, runner, controls, and
evaluation implementation are project engineering.

## Upstream responsibilities

mini-swe-agent 2.4.6 supplies the base `DefaultAgent` loop and model interfaces.
FANNAgent's `BudgetedModel` integrates those interfaces with project accounting
and validation. LiteLLM provides model dispatch. The showcased archived proposal
study uses a specialized runner around the core model adapter and offline
evaluator, rather than the ordinary core CLI loop.

The pretrained models, their training, and those upstream frameworks are not
FANNAgent implementations. NumPy, PyArrow, Pydantic, Typer, and the other declared
dependencies retain their own authorship and licenses. Shared neutral primitives
originated in the FANNBench harness; its notice is retained in
[third-party notices](../NOTICE.md).

The [research primer](RESEARCH_GUIDANCE.md) credits the papers that informed its
guidance. FANNAgent does not claim authorship of those papers or the underlying
datasets. PostgreSQL and pgvector remain upstream database projects; the extension
preserves their notices separately.
