# FANNAgent 0.2

FANNAgent is a reusable, offline agent for bounded ANN stopping policies. It owns study splits, spending, candidate selection, frozen policies, evaluation entitlements, reports, and application acceptance. Database integration is supplied by independently installed extensions through `fannagent.api` (API version 1).

```sh
pip install fannagent                         # simulation and saved-result inspection
pip install fannagent fannagent-pgvector      # add PostgreSQL/pgvector
fannagent backends list
fannagent backends describe pgvector
```

Core installation has no `fannbench`, PostgreSQL driver, Elasticsearch client, or concrete extension dependency. Discovery loads descriptors and configuration/profile metadata without connecting to databases. Two production distributions are provided; the SDK and shared algorithms live in the core.

## Simulation

Use `examples/fake.yaml` (schema version 2), or copy its contents into a local configuration file:

```sh
fannagent prepare examples/fake.yaml --run runs/demo
fannagent run examples/fake.yaml --run runs/demo --steps 2
fannagent resume --run runs/demo
fannagent evaluate --run runs/demo
fannagent status --run runs/demo
fannagent report --run runs/demo
fannagent clean --run runs/demo
```

Simulation uses its own features, eight-batch checkpoints and synthetic latency. It establishes no database performance result. Paid models retain the existing verified rate-card, token-bound and monetary ceiling contract. Preparation and required capabilities are checked before model spending. Resume cannot change the monetary contract.

Fresh conversations receive compact backend context before their first model call: backend identity, capabilities, dataset dimensions and metadata field mappings, budget totals, and extension-provided target details. Full inspection and feature definitions are available through referenced development artifacts; `fannagent-tool inspect '{}'` remains available for additional detail. Initialization inspection runs on the host without an agent tool action or model request. Fresh scripted runs start with `probe`.

The initialized conversation is saved before the first model call and new trajectories record `startup_context_version=1`. Resume retains saved messages and counters without adding or refreshing startup context. Older scripted conversations retain their original inspect-first action sequence. No run-schema or policy migration is required.

## Pgvector

See `../agent-pgvector/README.md` and its schema-v2 example. The extension owns physical restore, native execution, exact SQL, source identifiers and cleanup. Build the self-contained image with `fannagent-pgvector-build`; the source recipe and patches ship in its wheel. Build the development sandbox with `fannagent-workspace-build`. No sibling harness checkout is needed for either installed package.

```sh
fannagent inspect pgvector.yaml --run runs/pg
fannagent prepare pgvector.yaml --run runs/pg
fannagent run pgvector.yaml --run runs/pg
fannagent resume --run runs/pg
fannagent evaluate --run runs/pg
fannagent report --run runs/pg
fannagent deploy --run runs/pg --target runs/explicit-compatible-copy
fannagent clean --run runs/pg
```

Application entry point remains `fannagent.client.open_session(run)`. Sessions return original source identifiers. Accepted policy and environment compatibility are verified by the core; extensions implement session query and close. Pgvector marks ordinary-query fallback and allows callers to disable it.

## Extension authors and development

Read [the SDK guide](docs/EXTENSIONS.md). The test-only independent distribution in `tests/extensions/independent/` demonstrates different features, string identifiers, five-step checkpoints and distinct work units against an unchanged core wheel. It is not a third production package.

```sh
uv sync --extra dev
uv pip install -e ../agent-pgvector            # optional during pgvector development
uv run pytest -m 'not integration'
uv run mypy src/fannagent/api --check-untyped-defs --follow-imports=silent --ignore-missing-imports
uv run ruff check src tests
uv build
```

Each distribution has its own metadata, lockfile, tests, build and release notes. The harness's 0.4.1 compatibility wrappers depend on the core's public primitives; production packages never depend on the harness.

## Run compatibility and TODOs

New operational runs use schema version 2. Convert old configuration `target` and `copy` sections into extension-owned `backend.options`, and move CPU/memory/evidence settings into common sections. Existing runs remain inspection-only: `status` and `report` do not initialize writable SQLite state. Resume, preparation, evaluation, deployment, serving and cleanup reject legacy runs. Use the pinned 0.1 environment for necessary legacy operations; no old ledgers, ownership records or policies are migrated or reset.

Weaviate and Elasticsearch/Lucene remain TODOs for separate packages. Historic inspectors are retained in unshipped `deferred/` reference material and have no active registrations. Additional metrics, streaming analysis, larger data strategies, search-effort optimization and production cutover remain separate work. Public package/image publication, paid-model smoke tests and native AMD64 qualification are separate release gates.
