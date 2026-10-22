# FANNAgent

**An LLM-driven research agent for filtered vector-search stopping policies.**

FANNAgent investigates when a vector database can stop searching earlier while
preserving retrieval quality. The model chooses analyses, uses domain tools,
interprets measurements, and proposes bounded policies. A host controller owns
spending, evidence permissions, persistent state, and final acceptance.

Built by [Daniel Arturi (darturi)](https://github.com/darturi). I designed and
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

| Area | Engineering demonstrated |
|---|---|
| Agent orchestration | Prepared-backend context, model/tool turns, recorded experiments, candidate selection, and explicit termination |
| Domain tools | Typed requests, policy validation, bounded correction feedback, and evidence references |
| Durable execution | Saved conversations, evaluation receipts, checkpoints, and recovery across interruptions |
| Cost control | Per-attempt reservations, actual usage accounting, and conservative treatment of ambiguous charges |
| Evaluation boundaries | Development/calibration/test separation, policy freeze, compatibility checks, and host-owned acceptance |
| Database integration | A separately packaged pgvector backend with native observation/stopping, prepared copies, and application sessions |

Research happens outside live query serving. Provider-backed research can use a
networked model API; an accepted policy executes without an LLM in the query path.
The static cited primer supplies research guidance. The system does not perform
autonomous literature retrieval.

## Simulation

The verified first-run path uses the synthetic backend and a scripted model.
It needs no API key, database, Docker daemon, GPU, or paid model call. Installation
requires network access to obtain dependencies. Provide [uv](https://docs.astral.sh/uv/)
and Python 3.12 or 3.13; uv can provision the requested Python runtime.

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

The selected policy showed about 12–14% latency savings in its training study.
On held-out confirmation it retained latency savings but failed the required
recall criterion, so no policy qualified for acceptance. The agent-generation
comparison also remained inconclusive because there were zero complete A/B pairs.
The [results page](docs/results.md) links the recorded evidence and exact limits.

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

Licensed under [MIT](LICENSE), with [third-party notices](THIRD_PARTY_NOTICES.md).
The stable portfolio snapshot is `portfolio-v1`; ongoing research uses separate
branches and workspaces.
