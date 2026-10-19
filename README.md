# FANNAgent 0.2

FANNAgent is a reusable, offline agent for bounded ANN stopping policies. It owns study splits, spending, candidate selection, frozen policies, evaluation entitlements, reports, and application acceptance. Database integration is supplied by independently installed extensions through `fannagent.api` (API version 1).

For first-time installation, use the [local release bundle](packaging/README.md).
It supplies a repeatable host installer and a Docker controller launcher; container
operation requires no host Python. Packages and images remain local release artifacts.

```sh
bash /path/to/bundle/install.sh --backend pgvector --mode container --directory .fannagent-install
./.fannagent-install/fannagent init --backend pgvector --output pgvector.yaml
./.fannagent-install/fannagent doctor pgvector.yaml --check-source
```

Edit generated target fields and set the referenced credentials before `doctor`.
Simulation uses `--backend fake` and requires no model credentials. Config generation
refuses existing files. Diagnostics create no study or model request. Use the existing
prepare/run/resume/evaluate/report/clean commands through the launcher.

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

New generated configurations enable literature guidance:

```yaml
research:
  mode: guided
```

`guided` supplies a compact, cited research primer and requires a hypothesis before measurements,
followed by a conclusion linked to recorded evidence. `protocol_only` requires the same experiment
records without the primer; `baseline` retains the original exploration protocol. Existing
configurations without `research` retain baseline behavior. Changing modes requires a new run.
The exact primer and prompt are pinned to the run and preserved on resume.

Inspect experiment plans and host-recorded outcomes without a model or database call:

```sh
fannagent experiments --run runs/demo
fannagent experiments --run runs/demo --experiment-id EXPERIMENT_ID
```

See [research guidance and experiments](docs/RESEARCH_GUIDANCE.md) for the tool schema, source
principles, evidence boundaries, interruption behavior, and comparison modes. Guidance does not
change the default-relative recall objective or final acceptance criteria.

The [policy learning and evaluation revision plan](docs/POLICY_LEARNING_REVISIONS.md) describes
the next measured-feedback tools, evidence accounting, candidate archive, and comparison stages.
It preserves the current Torch experiment and introduces changes through a separate version.
The experimental [offline learning tools](docs/OFFLINE_LEARNING.md) provide measured-label fitting,
runtime-interpreter replay, structured feedback and a separate candidate archive without model or
database calls.

Malformed model tool calls, shell syntax, tool arguments, queries, filters, and policies receive bounded `error_info` feedback with field details and a correction hint. Rejected inputs are not rewritten or replayed. The next model turn can issue a corrected request. Three consecutive invalid turns end exploration with `invalid_submission_limit` and a `no_recommendation` report. A fully successful turn resets the streak; other execution failures do not change it. Resume preserves the streak, and reaching the limit is terminal for that run. Model attempts remain billed, including malformed responses. Existing accepted policies take precedence, while this limit does not automatically freeze a candidate checkpoint.

During exploration, the agent can designate a fallback with `fannagent-tool calibrate '{"policy": ..., "checkpoint": true}'`. Only an accepted, valid calibration replaces the saved candidate. Unmarked or rejected calibrations preserve the previous choice; a later failed recalibration of that same policy makes it ineligible. Calibration returns aggregates and the selected `checkpoint_policy_hash`; the full checkpoint and calibration evidence remain private. Older conversations receive this capability notice once on resume, without resetting their history or counters.

If the model budget expires before submission, the controller stops the sandbox and broker and freezes an eligible checkpoint using cached evidence, without another model call or experiment. Run output and `status` show `status: frozen`, `termination_reason: budget_exhausted`, and `finalization_source: checkpoint`. Final evaluation still requires `fannagent evaluate`; only that evaluation can accept the policy for deployment. Its report retains the exhaustion provenance. Without a selected candidate the result is `no_recommendation` with `no_eligible_checkpoint`; invalid checkpoints and freeze failures report distinct reasons and are recoverable through `resume`. Step-limit interruptions remain resumable and explicit abstention does not finalize a checkpoint. Older runs do not infer a fallback from past calibrations.

When the evidence store is full, exhaustion summaries remain available in SQLite and through `report`, including any artifact-storage failures. Successful checkpoint recovery clears the prior exhaustion report atomically with the policy freeze.

Fresh conversations receive compact backend context before their first model call: backend identity, capabilities, dataset dimensions and metadata field mappings, budget totals, and extension-provided target details. Full inspection and feature definitions are available through referenced development artifacts; `fannagent-tool inspect '{}'` remains available for additional detail. Initialization inspection runs on the host without an agent tool action or model request. Baseline scripted runs start with `probe`; guided demonstrations register an experiment first.

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
