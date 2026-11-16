# Filtered ANN protocol v2: local implementation

This implements the local portion of [the revamp plan](../../docs/AGENT_PROTOCOL_REVAMP_V2.md).
M0 job23303080 and [M1 job23376796](../m1-assessment-v1/REPORT.md) are verified.
The v2 runtime and all9,436 reached-prefix labels are qualified on the original development graph.
The [M2/M3 assessment](../m2-evidence-cost-v1/REPORT.md) binds complete labels/work and preserves
both failed precision models. The new [uncertainty-aware contract](../uncertainty-shortlist-v1/REPORT.md)
qualifies conditional M5 experiment selection with explicit abstention. Bound M3 positive and
negative paths pass;61 tests pass. No external model episode, validation or test has run.

| Stage | Current evidence | Remaining work |
| --- | --- | --- |
| M0 attribution | Job23303080 verified: counterbalanced Broad benefit with reduced work; continue advantage did not reproduce; failed23074287 retained | Complete diagnostic; no repeat or final policy promotion. Use its evidence to freeze M1 measurement design |
| M1 runtime | Job23376796 verifies masks, partial outputs, native/legacy work bridge,781,200 timings and984,396 attempts; both native preflights pass | Complete; preserve the original export error and local ID-lookup correction; no rerun |
| M2 evidence/shortlist | Complete labels/work; point precision remains failed; whole-pair envelope checks qualify conditional<=3 M5 nominees with<=1-point interval regret | Actual M5 cost remains mandatory; prepare the concrete M4 payload/rates/transport/budget |
| M3 controller | All61 tests; real-bound positive selection, four-way/native abstention, unsupported estimates, quotas/resume and unauthorized-paid blocking pass | Concrete new provider authorization remains required |
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
recall from its count. This initial builder is preserved separately from the complete M1 export.
M1's [assessor/exporter](../m1-assessment-v1/assess.py) adds the actual partial labels:2,313 cases
have some raw-native-relative recall-preserving reached prefix, versus1,964 using full prefixes
alone. These are oracle diagnostics, not executable policies or measured speedups. Both bundles
remain explicitly cost unqualified. M2 binds the complete export and evaluator-only prefix work.
The fixed additive and ridge hypotheses failed their prospective limits. Their signed
coefficients/errors and measured plan facts remain available; no unsupported surrogate ranks
programs. Added partial/preserving/zero/lossy categories and work feedback remain bounded tools.
The new [uncertainty contract](../uncertainty-shortlist-v1/PLAN.md) reuses the signed model without
refitting, adds a3.5364-point empirical envelope and qualifies only conditional experiment
selection. It does not mark the point model accurate or forecast new-program latency as measured.

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

## Current qualification and next action

The [M0 assessment](../reader-attribution-assessment-v1/REPORT.md) verifies all630,000 original-module
timings, reader/CPU assignments, work counters and684,950 attempts. Native/continue graph counters
match on every query; Broad saves3.77% aggregate latency and5.30% vector-score work on this one
allocation, concentrated in votes32. The full native startup checks passed and the failed first
allocation's empty measurement return is preserved. No M0 rerun is recommended.

The [M1 assessment](../m1-assessment-v1/REPORT.md) verifies the original-graph runtime, all labels,
781,200 measured requests and the exact984,396-attempt ledger. Three historical transfers retain
all outputs/recalls with fewer feature passes. Broad saves5.55% versus same-block native (conditional
95% interval4.58–6.57%), concentrated in votes32; this is development engineering evidence, not
final policy promotion. Native anchors differ across blocks, so their costs must not be pooled.
The packaged export failed on zero-padded IDs after writing the cost library; its original log is
preserved and a separate local normalized fold lookup passes typed evidence/fold validation.

The [M2/M3 assessment](../m2-evidence-cost-v1/REPORT.md) is complete: all labels/work are bound,
but neither fixed latency model qualifies. The additive proxy is a near miss (Broad votes527
error2.024 points, CPU13 error2.232 points versus the declared2-point limit); the ridge proxy also
fails primary error checks. Limits are not relaxed. M3 verifies nine tools/six scripted submissions,
bounded counterexamples/work, quotas, resume, pre-transport blocking and explicit abstention with
the real binding; the separate positive fixture never becomes actual-data qualification.

The [uncertainty-aware revision](../uncertainty-shortlist-v1/REPORT.md) now passes outer whole-pair
coverage and bound M3. It retains all three known policies as diagnostic nominees; a fourth
ambiguous semantic test variant causes abstention. The selector proves its conditional bound
against exhaustive interval corners. The deployed envelope is3.5364 native-ratio points; its
coverage for new programs/allocations is unproven and actual M5 timings remain required.

The first positive M3 context overflow is preserved. Compact evaluate/compare views keep full
registry records; active feedback deploymentv2 completes the same three scripted responses at
4,900/19,714/35,731 request bytes under the unchanged50,000 bound plus8,192 reserved headroom.
Next is concrete M4 payload/rates/transport/budget preparation and new provider authorization.
No further Torch job is needed now. All six filters and scoring-only exact search remain;
validation/test stay unopened. Precise point-cost ranking remains disabled.

Compact local receipts and external-artifact hashes are in `receipts/`. Generated engines,
binaries, full evidence, SQLite trajectories and logs remain under the study's workspace paths.
Validation/test outcomes remain unopened.
