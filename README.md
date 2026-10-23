# FANNAgent

[![CI](https://github.com/darturi/FANN-Agent/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/darturi/FANN-Agent/actions/workflows/ci.yml)

**A research agent that investigates when vector search can stop early without
missing relevant results.**

A vector database finds similar items, often subject to a filter: for example,
reviews similar to a query that also have at least 32 helpful votes. Searching
longer costs time; stopping too early can miss good matches. FANNAgent gives an
LLM tools to analyze that tradeoff and propose stopping rules. A host controller
enforces spending limits, validates tool requests, saves progress, and checks
whether a proposed rule meets separate quality and latency requirements.

Built by [Daniel Aarao Reis Arturi (darturi)](https://github.com/darturi). I designed and
implemented the project-specific agent system, experimental tooling, and pgvector
integration. FANNAgent builds on mini-swe-agent's base loop and model interfaces;
[contributions and upstream credit](docs/CONTRIBUTIONS.md) identify those boundaries.

## See the agent work

- [Annotated real run](docs/showcase/agent-run.md): ten provider-backed actions,
  a rejected policy and its revision, six research exports, and recorded model
  charges of $0.530724. The model wrote its analysis and explicitly concluded that
  no proposal was accepted.
- [Agent architecture](docs/agent-design.md): tools, context, budgets, sandboxing,
  durable evidence, interruption recovery, and separate evaluation controls.
- [Research results](docs/results.md): training feasibility, held-out failure,
  and the limits of the current findings.
- [Verification record](docs/showcase/validation.md): the checks performed for
  this portfolio snapshot and the qualification boundaries.

## What I built

| Area | Engineering demonstrated | Code to inspect |
|---|---|---|
| Agent orchestration | Model/tool turns, prepared context, recorded experiments, candidate selection, and explicit termination | [Controller](src/fannagent/controller.py) |
| Domain tools | Typed requests, policy validation, correction feedback, and evidence references | [Tool broker](src/fannagent/broker.py) |
| Durable execution | Saved conversations, evaluation receipts, checkpoints, and interruption recovery | [Run store](src/fannagent/store.py), [recovery tests](tests/test_checkpoint.py) |
| Cost control | Per-attempt reservations, usage accounting, and conservative handling of ambiguous charges | [Model adapter](src/fannagent/model.py), [accounting tests](tests/test_model.py) |
| Evaluation boundaries | Separate development/calibration/test data, frozen policies, and host-owned acceptance | [Study controls](src/fannagent/study.py) |
| Database integration | A separately packaged pgvector backend with native observation/stopping and application sessions | [Companion source](https://github.com/darturi/FANN-Agent-pgvector/tree/portfolio-v1) |

Research happens outside live query serving. Provider-backed research can use a
networked model API; an accepted policy executes without an LLM in the query path.
The static cited primer supplies research guidance. The system does not perform
autonomous literature retrieval.

The research question is whether a model can choose useful analyses, features,
and stopping rules from a domain-specific experimental interface. The
[recorded run](docs/showcase/agent-run.md) shows the model writing analysis code,
scanning thresholds, and correcting a rejected policy. Current experiments do
not establish that model-directed search outperforms a deterministic fitter.

## Simulation

The verified first-run path uses the synthetic backend and a scripted model.
It needs no API key, database, Docker daemon, GPU, or paid model call. Installation
requires network access to obtain dependencies. Provide [uv](https://docs.astral.sh/uv/)
and Python 3.12 or 3.13; uv can provision the requested Python runtime.
The commands pin the published `portfolio-v1` snapshot so the example has a
stable source and dependency lock. Install from source as shown here; the
packages are not currently published on PyPI.

```sh
git clone --branch portfolio-v1 --single-branch https://github.com/darturi/FANN-Agent.git
cd FANN-Agent
uv sync --frozen --python 3.12

demo_dir="$(mktemp -d)"
export MSWEA_GLOBAL_CONFIG_DIR="$demo_dir/mini-config"
export MSWEA_SILENT_STARTUP=1
export LITELLM_LOCAL_MODEL_COST_MAP=True

uv run --frozen fannagent init --backend fake --output "$demo_dir/fake.yaml"
uv run --frozen fannagent doctor "$demo_dir/fake.yaml"
uv run --frozen fannagent prepare "$demo_dir/fake.yaml" --run "$demo_dir/run"
uv run --frozen fannagent run "$demo_dir/fake.yaml" --run "$demo_dir/run" --steps 2
uv run --frozen fannagent resume --run "$demo_dir/run"
uv run --frozen fannagent evaluate --run "$demo_dir/run"
uv run --frozen fannagent experiments --run "$demo_dir/run"
uv run --frozen fannagent report --run "$demo_dir/run"
uv run --frozen fannagent status --run "$demo_dir/run"
uv run --frozen fannagent clean --run "$demo_dir/run"
```

Expected milestones are `interrupted` after the two-step run, `frozen` after
resume, and an evaluation with `status: accepted`, `valid: true`, and
`simulated: true`. Status records three completed experiments and a model ledger
with `committed_usd: "0"` and `calls: []`. The report remains at
`$demo_dir/run/REPORT.md` after cleanup.

This demonstrates the lifecycle with predetermined actions and synthetic latency.
It establishes no database speedup or model-directed discovery. The annotated
real run above supplies recorded provider-backed behavior. See the
[local-demo guide](docs/showcase/local-demo.md) for installation details and output.

## Research outcome

The selected policy showed about 12–14% mean latency savings in its training study.
Held-out confirmation recorded 11.673% activation-inclusive and 12.377% reused-policy
mean latency savings, but failed the required recall criterion. No policy qualified
for acceptance. The agent-generation comparison also remained inconclusive because
there were zero complete A/B pairs. The [results page](docs/results.md) links the
recorded evidence and exact limits.

The project demonstrates an implemented agent and evaluation system. Current
evidence does not establish a generally beneficial or production-ready optimizer.

## Development and the database backend

```sh
uv sync --frozen --extra dev --python 3.12
uv run --frozen pytest -m 'not integration'
uv run --frozen ruff check src tests
uv run --frozen mypy src/fannagent/api --check-untyped-defs --follow-imports=silent --ignore-missing-imports
uv build
```

The [pgvector extension](https://github.com/darturi/FANN-Agent-pgvector/tree/portfolio-v1)
is optional for the simulation and maintained as a separate distribution. Its
database requirements and historical native qualification are documented there.
Neither the demo nor ordinary core CI connects to a research database. See the
[operations reference](docs/USAGE.md) and [extension API](docs/EXTENSIONS.md) for
advanced workflows. Source installation is the supported portfolio path; public
package-registry or container-image availability is not required by these commands.

Licensed under [MIT](LICENSE), with [third-party notices](NOTICE.md).
The stable portfolio snapshot is `portfolio-v1`. This default branch provides the
project introduction and development source; ongoing research continues in separate
branches and workspaces.
