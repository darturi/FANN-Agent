# Filtered ANN protocol v2: local implementation

This implements the local portion of [the revamp plan](../../docs/AGENT_PROTOCOL_REVAMP_V2.md).
The next Torch submission is still the sealed `reader-attribution-v1` diagnostic (M0).
The v2 runtime has **synthetic qualification only**. No new model episode, original-graph
v2 qualification, validation or test has run.

| Stage | Current evidence | Remaining work |
| --- | --- | --- |
| M0 attribution | Existing kit and freeze preserved; user reports it was not submitted | Submit once; independently verify the return and resolve attribution |
| M1 runtime | Deterministic compiler, feature masks and partial/zero stops pass local tests and synthetic PostgreSQL smokes | Freeze an M0-informed schedule and one bounded original-graph qualification/cost kit; qualify native/legacy bridge and every reached prefix |
| M2 evidence | All 3,150 development rows rebuilt against raw native640; 7,940 known full-prefix labels; 1,496 missing partial-prefix labels | Measure missing prefixes and component costs, including uncertainty, on the original graph; qualify provenance before enabling cost ranking |
| M3 controller | Typed tool dispatcher, durable accounting, registry, deterministic compilation and scripted end-to-end rehearsal pass | Bind the eventual qualified cost library, approved episode and pinned provider transport/rate contract |
| M4–M6 | No requests or protected evaluation run | Follow the gates in the plan; retain negative/inconclusive outcomes |

## What is implemented

`fannproto/policy.py` defines the versioned causal DSL. The compiler derives each predicate's
checkpoint observations from its rules. Count-only rules skip top-ten ranking; a predicate
without rules does no feature collection. Turnover at checkpoint64 depends on checkpoint32,
even when there is no decision at32. Missing values make comparisons false. Rules can stop
with zero through ten actual results; missing neighbors still reduce recall. There is no
completion guard and no runtime access to exact labels.

`runtime/policy_runtime_v2.inc` and `prepare_runtime.py` stage a copied engine with new arm
numbers20–59. Old arms remain under their old semantics. The thirteen current bindings are
three historical transfer variants, their matched continue-only controls, and seven researcher
qualification probes. **None is a new agent discovery.** Matched controls evaluate the same
comparisons and masks but force continuation. Audit frames are for qualification and must be
disabled during eventual serving timing. This prototype adds no per-distance work counters.

`build_evidence.py` checks returned-file hashes, the frozen development membership, vector-group
fold algorithm and full seven-condition inventory. It exports anonymous groups, exposed fold
labels, causal observations and evaluator-only recall labels. It never infers a missing prefix's
recall from its count. The 1,964 cases with some known recall-preserving full stop describe oracle
opportunity, not an executable policy or a measured speedup. The bundle remains explicitly cost
unqualified. The component-cost estimator is a development surrogate interface; its values are
never described as a new policy's measured latency. Its real uncertainty and timing contract
must be completed from M0/M1 before use.

`fannproto/controller.py` reuses the general agent's `Store` and `Budget`. Its five native tools
inspect development, explain bounded cases, evaluate programs, compare registered candidates
and submit/abstain. There is no shell, SQL, arbitrary file, network or holdout tool. Invalid and
duplicate proposals consume submission slots. Limits are six model requests, $15, twelve domain
tools, nine submissions, three per batch and three finalists. Reservations precede transport;
usage settles before parsing. Interrupted/uncertain calls require audit, with no automatic retry.
Resume preserves model/rates, prompt/tools, transcript, evidence and qualification gates.

The transport is injected. This experiment has **no credential loader or installed paid-provider
adapter**. The exhausted old allowance is not reused. A concrete new payload, current model/rate
check and new authorization are required before M4. `fannproto/rehearsal.py` uses intentionally
fake labels, costs and rates; fixture data cannot authorize a real paid model.

## Local verification

From the workspace root:

```bash
agent/.venv/bin/python -B -m pytest agent/experiments/filtered-ann-protocol-v2/tests -q
agent/.venv/bin/ruff check agent/experiments/filtered-ann-protocol-v2
```

The local receipt records36 tests, including 3,000 randomized Python/generated-C decision
comparisons, null/partial behavior, mask dependencies, quota and budget enforcement, accounting
for malformed responses, idempotent tool deliveries, interrupted-call recovery, transcript
binding and evidence rejection. Two isolated x86 PostgreSQL fixtures each check thirteen
programs across all seven conditions and native-after-v2 role switches. The second has no rows
in the strictest filter and verifies four zero-output stops. These are semantic checks on a
synthetic8d partial graph, **not** original-graph performance evidence.

To rebuild evidence or run a scripted rehearsal, choose fresh output directories:

```bash
agent/.venv/bin/python -B agent/experiments/filtered-ann-protocol-v2/build_evidence.py --output /tmp/v2-evidence
agent/.venv/bin/python -B agent/experiments/filtered-ann-protocol-v2/run_rehearsal.py --output /tmp/v2-rehearsal --evidence /tmp/v2-evidence/evidence.json
```

To stage a local engine, use `prepare_runtime.py --destination /tmp/v2-runtime`. It includes the
synthetic SQL, smoke script, copied engine and supporting modules. In the pinned
`fannagent/torch-reviews-first:20261013` x86 image, mount that directory at `/qual`, build with
`make PG_CONFIG=/opt/postgresql/bin/pg_config OPTFLAGS=`, and copy `engine/vector.so` to
`/qual/vector.so`. In a fresh disposable container, install that module to
`/opt/postgresql/lib/vector.so` and run `/qual/smoke_runtime.py` as `nobody` with
`PYTHONPATH=/qual:/opt/torch-reviews/vendor`. Use a separate fresh container with
`SYNTHETIC_HIGH_VOTE_COUNT=0` for the zero-output case; default7 exercises partial results.
Keep `--network none`. Preserve failed evidence rather than overwriting it.

## Next Torch action

Use the existing workspace file
`trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/ATTRIBUTION-COMMANDS.txt`.
Upload the existing archive and SHA sidecar, verify and submit once, and return the actual job
ID. Its four-CPU/48GiB/eight-hour ceiling, attempt ledger, original timing module, counter module
and all six filters are unchanged. It permits exact search only for offline scoring. The next
v2 Torch kit will be sealed after this diagnostic determines the measurement contract.

Compact local receipts and external-artifact hashes are in `receipts/`. Generated engines,
binaries, full evidence, SQLite trajectories and logs remain under the study's workspace paths.
Validation/test outcomes remain unopened.
