# Full-workload and held-out oracle

Prepared for the user's request to measure hindsight latency headroom on both
the 275-vector held-out split (1,925 query/filter cases) and the complete
1,000-vector benchmark (7,000 cases). One acquisition produces separate reports.

The oracle actually executes every earlier checkpoint before accepting a stop
that preserves native Recall@10 and result count. It then replays the frozen
choices without collecting features or running a classifier. Native640, matched
continue, and empty-program controls use the same original graph and reader/CPU
crossover. Exact retrieval is offline scoring only. The primary request timer
treats the hindsight choice as free and records its routing cost separately.

This is an optimistic measured reference within the existing 64-distance
checkpoint boundaries, not a mathematical maximum over all algorithms or noisy
wall-clock minima. See [the protocol](PROTOCOL.md).

## Measured results

Timing job **23567950** completed successfully on November 18. Independent
verification reconstructed all 7,000 choices and all 112,000 timing records,
including source hashes, output quality, schedule, CPU/PID assignments, timer
boundaries, and cumulative reservations. A separate integer-sum calculation
reproduced both cohorts' means and reductions. No case lost native Recall@10
or returned-result count. The two evaluator-only policy tables are exported.

| Cohort, all seven conditions | Cases | Native mean | Oracle mean | Reduction (conditional 95% interval) |
| --- | ---: | ---: | ---: | ---: |
| Held-out subset | 1,925 | 12.174 ms | 4.227 ms | 65.28% (63.63–66.92%) |
| Full workload | 7,000 | 12.316 ms | 4.180 ms | 66.06% (65.18–66.92%) |

For the six-filter primary metric, the reductions are **61.73% held-out** and
**62.70% full workload**. The unfiltered condition has about 86% headroom.

These are **descriptive optimistic headroom estimates**. Aggregate empty/native
controls pass the ±2% equivalence band, but the per-condition 90% intervals do
not all fit inside that band; the predeclared all-condition control requirement
therefore remains inconclusive for both cohorts. Intervals condition on one
timing allocation. Perfect per-query hindsight is free, native retrieval quality
is the reference, and stops use the existing 64-distance checkpoint boundaries.
The full and held-out cohorts overlap. This does not establish a deployable
policy or a mathematical maximum over other algorithms or wall-clock minima.

The exported tables are **not policies in the current agent's v2 DSL**. The
agent accepts bounded causal feature rules only at checkpoint ordinals 16/32/64;
the oracle uses query identity and future quality to choose any reached ordinal
up to 4,096 through a separate evaluator-only runtime arm. It pays no feature
collection or rule-evaluation cost, and choice routing is outside the request
timer. Of 7,000 full-workload choices, 6,850 are outside the agent's permitted
checkpoint set (1,883 of 1,925 on held-out). The oracle additionally preserves
native result count, while the agent's current quality gate preserves recall.
Consequently these percentages are not a validated numerical upper bound for
the current agent policy class. An agent-aligned action oracle needs the same
allowed checkpoints, quality gate, and runtime-cost accounting; bounding the
best expressible policy also requires enforcing the DSL's bounded rule form.
Hindsight by itself does not establish representability or attainability.

Results are in the trial directory's `return-23567950/results/`: `report.json`,
`oracle-full-workload.json`, `oracle-heldout-test.json`, and `oracle-headroom.png`.
`actual-verification.json` records the independent audit. Actual allocated time
across the three jobs is **05:11:56**, with four CPUs and 48GiB per allocation.
The final cumulative reserved charge is **493,388 / 2,000,000 attempts**;
all interrupted and unused reservations remain charged. No provider calls.

## Execution provenance

Execution update, November 18: the user completed Torch MFA. Source job
**23544718** acquired all 7,000 exact references and 4,256 complete oracle choices.
It was deliberately interrupted through its cleanup handler before any primary
timings to replace expensive per-query durable bookkeeping. Its FAILED scheduler
status and complete raw archive are retained. Source verification passed.

Followup **23558871** completed all remaining 2,744 choices with the same
criterion and engine. All 7,000 choices are frozen and independently verified.
After 23,225 fresh validation queries, it was deliberately stopped before primary
timings because measured request throughput would make eight repetitions exceed
the remaining aggregate budget. All raw results and both FAILED states remain.

The final timing schedule uniformly uses four repetitions per case and family,
one complete cycle of four reader/CPU rotations: 112,000 timed requests and
1,120 warmups. Every warmup and timed answer must match its frozen source.
See [the bookkeeping amendment](FOLLOWUP-PROTOCOL.md),
[the uniform repetition amendment](BALANCED-PROTOCOL.md),
`balanced-source-verification-v3.json`, and `balanced-v3-readiness.json`.
The first two allocations used 17,249 seconds; the timing allocation is bounded
at 4,200 seconds. Reservation windows retain all unused and uncertain charges.
Protected outcomes are exposed for this evaluator-only diagnostic; no provider
calls occurred.

The following checks describe preparation before that launch:

- Isolated amd64 PostgreSQL module compiled offline.
- Eleven focused tests and Ruff checks pass.
- Real synthetic PostgreSQL acquisition/replay and timing pass on all seven
  conditions, including empty and partial eligible populations.
- Independent verification reconstructs every prefix selection and all 448
  synthetic timing observations, with CPU/PID/schedule and ledger checks.
- Sealed-input and frozen-source loader checks pass in the pinned container.
- The emulated full native-backend import reported a QEMU segmentation fault;
  its failed log is retained. Full native import is required on Torch before
  submission and has passed there for both launches.
- At preparation, no Torch job, provider request, original-graph query or protected outcome
  access had occurred. The expired SSH session was subsequently replaced by the
  user's MFA-authenticated connection for the execution update above.

The active archive is `oracle-balanced-v3.tar.gz` in the trial directory and
its local sealed inputs are `balanced-kit-v3/`. Earlier seals and failed
preflights are retained. The balanced schedule passed a real synthetic database
test and independent reconstruction of all 224 fixture timing observations.
The v2 native preflight caught a wrapper bind-path error before submission;
v3 changes only those wrappers, with identical tested runtime files.

The amended resource envelope is two acquisition allocations and one timing
allocation, four physical CPUs, 48GiB,
at most six aggregate allocated hours, two million cumulative attempts, no
automatic retry/requeue, and no provider calls. Oracle labels stay evaluator-only.

## Launch and collect

[COMMANDS.txt](COMMANDS.txt) contains the pinned-host MFA connection, upload,
preflight, single submission, collection and local verification commands.
After the user authenticates, the agent can perform the remaining steps.
Do not substitute a new unverified SSH host key or disable host checking.

For a completed return, verify the checksum and scheduler completion, then run:

```sh
agent/.venv/bin/python -B trials/fannagent-benchmark-evaluation-v1/reviews-small/full-workload-oracle-v1/balanced-kit-v3/balanced_analyse.py \
  --results PATH_TO_EXTRACTED_RESULTS \
  --kit trials/fannagent-benchmark-evaluation-v1/reviews-small/full-workload-oracle-v1/balanced-kit-v3
```

`report.json` includes full-workload and held-out mean latency, percent reduction,
paired intervals, per-filter quality/stops/checkpoints, CPU/cycle consistency,
and control diagnostics. Synthetic timing numbers are never benchmark evidence.
