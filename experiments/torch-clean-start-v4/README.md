# Clean-start policy discovery v4

Status: implementation and offline unit verification only. **No experiment has
been run.** No provider request, database query, SSH session, container, or Slurm
allocation was started while implementing this replacement. The seeded v3 live
workflow remains disabled and its historical results remain unchanged.

This controller uses `claude-opus-5-5`, adaptive thinking, high effort, and up to
16,000 output tokens per request (including reasoning). It discovers one ordinary
`fannagent.broad-stop.v3` policy for the entire workload. Only development cases
are accessible during discovery. After the conversation closes and the policy is
frozen, a separate finalizer can attach the two existing cohort-fitted
`oracle_feasible` artifacts and compare held-out and full-workload latency.

## What changed

| Issue | Implementation |
|---|---|
| Prior empirical evidence | New UUID, randomized query aliases, strict static-input schema, empty evidence/scratch/policy directories, sealed initial workspace, and fresh model conversation. No prior observations, labels, native summaries, truth caches, policies, coefficients, or model history are imported. |
| Narrow search | Threshold, linear, and nonlinear interval/tree synthesis from this run's evidence; grouped cross-validation; custom NumPy/Python; arbitrary legal checkpoint schedules, all 13 causal features, and the unchanged broad v3 VM, including query-local state. No lifetime candidate quota. |
| Evidence acquisition | Agent chooses cases, conditions, checkpoints, and feature bundles. The worker executes fresh native and exact references and actual forced prefixes. It labels only executed prefixes; continuing to native never labels an earlier prefix safe. Same-run references may be reused with producer-query provenance. |
| Feedback | Per-case recall, result counts, resource failures, causal counterexamples, and every timing sample remain available in read-only evidence files. Compact tool replies avoid flooding the model. A lossy candidate does not suppress other candidates' feedback. |
| Feature cost | Agent can profile requested feature bundles with force-continuation and controls. Single-query acquisition timings are explicitly diagnostic. Complete SQL execution and result-materialization latency is the optimization target. |
| Timing | Predeclared 2–6 blocks, randomized case/arm order, one reader/core per bracket, native measurements before/after each case, charged warmups, native clone, empty program, and matched continuation. Group/block bootstrap and per-condition control checks retain all samples. Failed controls are inconclusive. |
| Stopping | Normal finish requires evidence across all seven conditions, at least two completed evaluation rounds and two program structures, plus a substantive stopping report. A selected policy must preserve recall and result count on every development case and show controlled confirmation benefit over native and matched continuation. |
| Budgets/liveness | Query envelopes checked before dispatch, durable reservations/debits, no blind retries, exact scoring and warmups charged, separate discovery/final reservations, context-sized model reservations, bounded research containers, heartbeats around model/tool work, fixed discovery and total clocks. Uncertain work stays charged. |

The structural diversity check ignores numeric threshold and checkpoint changes.
It is a guard against trivial variants, not evidence of exhaustive search.
Grouped cross-validation is diagnostic; native execution remains the quality gate.
The helpers are optional synthesis methods, not additional deployment restrictions.
The latency clock includes SQL execution, transport and row materialization. It
excludes benchmark transaction/attachment setup, EXPLAIN checks, compilation,
snapshot preparation and evidence persistence; those consume the wall-time budget.
The harness caches immutable VM compilation and same-action references outside
that clock, rather than rebuilding them between timed statements.

## Default resource envelope

| Resource | Proposed limit |
|---|---:|
| Total ANN + exact queries, including labels, warmups and controls | 300,000 |
| Discovery allocation | 145,000 |
| Reserved final allocation | 155,000 |
| Model accounting ceiling | $15 |
| Worker wall time / discovery time | 6 hours / 4 hours |
| Offline research action | 240 seconds, 2 GiB, 1 CPU, 128 processes |

For the recorded 1,000-vector split (450 development, 150 validation, 275 test,
125 historical exclusions), the conservative final envelope is
`20 × 7000 + 4 × 1925 + 512 = 148,212` queries. This covers fresh references,
agent/oracle quality checks, two randomized timing blocks and warmups. The test
oracle is evaluated only on its fitted test cohort. Existing same-run development
references can reduce actual final use. The final reservation cannot be borrowed
by discovery. No continuation allocation or budget reset is implemented.

Opus admission uses a fresh token-count estimate plus a margin of the greater of
1,024 tokens or 10%, with the requested maximum output reserved at the reviewed
rates ($4/$20 per million input/output tokens). Actual reported usage settles the
reservation. Unknown billing keeps the reservation; unexpected usage, caching,
model, service tier or envelope violations stop the conversation before tools
execute. Token counting is an estimate: **this admission margin is not an absolute
provider invoice guarantee**. A future operator requiring that guarantee also
needs a provider-side spending limit. No paid request is automatically retried.
Model availability, capabilities and current rates are checked afresh before a
future run; saved v3 provider receipts are not reused.

## Static inputs and isolation

`prepare` accepts an explicit JSON array of cases containing exactly
`handle`, `group`, `role`, `filter`, and `vector`. Every group has one vector and
all seven filters: `-1,743,527,310,192,108,32`. Roles are `development`,
`validation`, `test`, or `excluded_historical`. Vectors for this benchmark have
768 elements. Fields containing empirical results are rejected. Original group
IDs are replaced by fresh aliases; the agent receives development handles and
conditions, not private vectors, exact IDs, protected handles or corpus metadata
derived from previous query runs.

The native worker additionally needs explicit static assets:

- A stopped regular-file-only PostgreSQL PGDATA snapshot with the unchanged
  `torch_reviews` corpus/index: 247,286 rows in `public.reviews`, fields `id`,
  `embedding`, `total_votes`, index `reviews_hnsw`. Other user tables are rejected.
  The source is hashed and mounted read-only; each action uses a private copy.
- A v3-capable engine **software** source tree. All compiled study/v2/v3 policy
  headers are replaced by empty stubs/fresh compilation. Legacy arms are disabled;
  only the private generic forced-prefix primitive and new v3 programs can attach.
- An explicit hashed Apptainer runtime image with PostgreSQL, compiler, Python,
  NumPy and psycopg, plus a separate data-free Python/NumPy Docker research image
  pinned by its local `sha256:` image ID. Docker uses `--pull=never`.

The research container sees only the new agent workspace. Task, generic API and
current-run evidence are mounted read-only; policy/scratch are writable. It has
no network, credentials, host home, private worker files, old run directories,
native database or oracle artifacts. Arbitrary Python runs there; the trusted
worker accepts validated JSON programs rather than agent-supplied native code.

## Entry points

Commands below are a **future execution recipe**, not a record of execution.
Use explicit new paths; no command defaults to an earlier trial or oracle kit.

```sh
PYTHONPATH=experiments/torch-clean-start-v4 .venv/bin/python -m fannclean --help

PYTHONPATH=experiments/torch-clean-start-v4 .venv/bin/python -m fannclean prepare \
  --root /NEW/STAGE \
  --cases /STATIC/CASES.json \
  --engine-source /STATIC/V3_ENGINE_SOFTWARE \
  --snapshot /STATIC/STOPPED_PGDATA \
  --runtime-image /STATIC/RUNTIME.sif \
  --research-image sha256:REVIEWED_LOCAL_IMAGE_ID
```

Preparation performs file operations only. It does not create an authorization,
launch a worker, pull an image, contact a provider or fit an initial policy. Stage
paths in `deployment.json` refer to assets on the future worker host. Prepare
where those static assets are available, and copy the sealed package to the
controller host before either workspace has acquired evidence. Run the local
controller with its prepared package and point the mailbox at the worker copy.
Worker and controller may also use the same stage on one host.

A future authorized run must have an `authorization.json` bound to the run UUID,
SHA-256 of `package-seal.json`, purpose `clean_start_discovery`, status
`authorized`, and the user's concrete run instruction. **None is created by this
implementation.** This gate keeps preparation from accidentally starting a run.

Inside one separately authorized allocation of at most six hours, four CPUs:

```sh
PYTHONPATH=/NEW/STAGE/code/experiments/torch-clean-start-v4 \
  python3 -B -m fannclean.worker serve --root /NEW/STAGE
```

From the controller host, with the existing local Anthropic credential kept
outside the package and an already authenticated/pinned SSH connection:

```sh
PYTHONPATH=/LOCAL/STAGE/code/experiments/torch-clean-start-v4 \
  python3 -B -m fannclean run-agent --root /LOCAL/STAGE \
  --worker-root /NEW/STAGE --ssh-host VERIFIED_HOST \
  --known-hosts /PINNED/KNOWN_HOSTS --control-path /EXISTING/SSH_SOCKET
```

Omit SSH options for a local worker. `status` uses the same mailbox options.
The worker stops after 15 idle minutes without a current heartbeat, cannot be
revived by a late heartbeat, and will not restart over an old ledger/cache.

Only after `host/model-closed.json` and `host/freeze.json` exist:

```sh
PYTHONPATH=/LOCAL/STAGE/code/experiments/torch-clean-start-v4 \
  python3 -B -m fannclean finalize --root /LOCAL/STAGE \
  --worker-root /NEW/STAGE --ssh-host VERIFIED_HOST \
  --known-hosts /PINNED/KNOWN_HOSTS --control-path /EXISTING/SSH_SOCKET \
  --oracle-full /PRIVATE/ORACLE_FEASIBLE_FULL.json \
  --oracle-test /PRIVATE/ORACLE_FEASIBLE_TEST.json
```

The finalizer reads oracle files only after verifying model closure, binds them
to the immutable agent freeze, and requests one final attempt. The worker returns
no final measurements to the model. Final JSON reports both cohorts, recall and
count losses separately, resource faults, conditional latency intervals, failed
controls, and the descriptive gap to the appropriate feasible oracle. An oracle
with count losses is explicitly marked as failing the strict quality comparator.

If delivery is uncertain, retrieve the **existing** UUID recorded under
`transport/`; do not resubmit with a new UUID. Raw completed queries, request
logs, reservations and cleanup receipts remain private for an audit. There is no
automatic continuation, experiment restart, or second final attempt.

## Verification and remaining limits

Run `pytest -q experiments/torch-clean-start-v4/tests` with the repository's Python
environment. Tests prohibit real HTTPS requests and subprocesses and use synthetic
backends/provider responses. They cover isolation, acquisition provenance, unsafe
prefix labels, per-case feedback, timing completeness, quality/control gates,
stopping, query/model budgets, no retry, liveness, source neutralization, VM audit
parity, membership format, and final freeze privacy.

The new PostgreSQL/container path has **not** been executed or qualified on Torch.
Its build compatibility, snapshot startup/cleanup, timing controls, throughput
and completion within the envelope need verification during a separately
authorized run. Improved search tools and Opus do not guarantee reaching the
hindsight oracle. Labels and feature collection now have a real acquisition cost;
the hindsight oracle has cohort-wide labels the agent must earn. Single-allocation
intervals omit adaptive selection and allocation variability. The historical
held-out cohort has already been examined by earlier hindsight studies; it is
protected from this agent's discovery, not a newly untouched scientific test set.
