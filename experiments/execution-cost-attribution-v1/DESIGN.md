# Execution cost attribution v1: frozen design

Prepared October 23, 2026. Scope: the first P1 experiment in the permanent performance roadmap. Implementation and local simulation do not establish empirical completion of P1 or M1.

## Question and hypotheses

Which functions account for the measured setup and routing penalties of the unchanged selective-policy path, and which operations are candidates for lifecycle changes in a later P2 study?

H1: preparation has a reproducible dominant cost in validation, copying, or identity construction rather than ANN work. H2: routed-native pays application work before it chooses native search, explaining its nonzero gap. Both are hypotheses: profiling must retain evidence that challenges them. The experiment introduces no optimization or policy changes.

## Inputs and invariants

- Sealed selective pilot manifest SHA-256: `082b167507e25009bdb25ea613950cd434ef38608fbcbc6194af19c363d0f6dc`.
- Baseline verification receipt SHA-256: `f5ee1f8a9a5090b687d619487c9a02883441c8e1e993673b030b2ff230e04d91`.
- Candidate semantic identity: `a014a290966444a86614f1e5be1960dad2fb8684044e85e9df82899911062b0d`, credited earlier seed, light19, native bypass for votes108.
- Exact prior x86 module SHA-256: `e7dcace1f4dfd4ea233256d6cdfc17b3190f3f07cccb6406b479b5ebe8b85811`.
- 200 development vectors, all three filters, 600 cases; `ef_search=640`, `k=10`; original physical index and image.
- New package pins native IDs/distances, exact-reference boundary sets, and light19 causal traces by hash from the independently verified prior pilot. It checks the actual stopped policy's prefix and results in each allocation.
- Three arms: frozen candidate, same-conditions matched continue, routed-native. Every arm gets its own randomized native/policy pair. Arm order is deterministic and balanced by rotation across three serial allocations; query order is shuffled using declared seeds.
- No oracle arm, fitting, policy selection, live paper retrieval, model clients, confirmation queries, engine rebuild, or production cutover.

## Two-pass measurement

The primary pass uses the original `execution.Session`, `execution.session`, and `execution.pair` functions without modification. One activation pair, one discarded warmup pair, and three reuse pairs follow an explicit installation eviction and prepared-cache clear. Original preprocessing and installation boundaries remain charged.

Only after the entire primary pass finishes does a separate diagnostic pass run on the first 60 vector groups sorted by SHA-256 of `["diagnostic-v1", group]` under the new protocol's canonical JSON encoding. All filters for each selected vector are retained. `cProfile` wraps session construction and query execution. Its rows and aggregates are stored separately; they never enter primary intervals or speed checks. Phase-order effects and profiler perturbation mean diagnostic versus primary latency differences are not a randomized estimate of profiler overhead.

Profile groups are block × arm × filter × phase (`prepare`, `activation`, `warmup`, `reuse`). Each prepare/activation/warmup group has 60 calls per block; each reuse group has 180. Full function counts, self time, and cumulative time are retained without argument values. Nested inclusive times must not be summed. Output parity is checked against the same-query primary proof.

## Accounting and resources

Per block: getter qualification 921 searches; each of 600 main cases has exact/native/continue references (3), three route/first-stop proofs (3), and 3 arms × 5 pairs × 2 executions (30), totaling `921 + 600 * 36 = 22,521`. Diagnostics add `180 * 3 * 5 * 2 = 5,400`; combined 27,921. Three blocks total 83,763 searches.

Each main arm/case retains four pairs and discards one: 7,200 retained and 1,800 warmups per block. Diagnostics retain 2,160 pairs and discard 540 per block. Explicit eviction installations total `(600 + 180) * 3 = 2,340` per block; these are separately counted SQL operations, not added to the search count. No claim is made that every SQL statement is counted.

Exactly three serial four-CPU, 32-GiB, two-hour allocations; work deadline 6,600 seconds per block including restore/runtime work. A global fixed-protocol reservation is written before dispatch and survives errors/reuploads. Each block is recorded before `sbatch`; uncertain results prevent retry. Inputs are read-only and each job restores a private database copy.

## Verification and analysis

Require package/binary/image/profile/index identities; complete getter checks; unchanged protected sources and prior pilot raw pins; complete expected query/arm/block/regime/repetition coverage; exact native/exact-reference/trace equality to prior pins; clean route and first-stop acknowledgements; result-based recall; preparation/routing arithmetic; correct activation state; and complete profile-call coverage. Invalid, missing, duplicated, truncated, corrupted, or mismatched records fail verification rather than being excluded.

For primary rows, use the original 10,000-resample vector-group bootstrap, seed 20261019, pooling all filters/repetitions/blocks within vectors. Report per-filter and per-block summaries. Keep primary mean log latency-ratio intervals, arithmetic mean latency, and outer application time distinct. Retain the original recall margin 0.005 and native floor 0.95 in descriptive checks, without consuming a selection or confirmation entitlement. Acceptance remains false.

Returned archives are treated as data. Local trusted code verifies hashes, safely extracts regular files, reconstructs summaries, and checks remote/local parity with exact discrete values and absolute floating tolerance `1e-12`.

## Gate and follow-up

G1 can be reviewed when operation-level attribution is consistent across blocks, the component categories reconcile with primary timing, and a bounded next mechanism is identified. If profiler perturbation, a broad interpreter frame, or database wait prevents attribution, record that limitation and design a more focused diagnostic; do not claim a root cause from the agent's earlier narrative.

The next P2 proposal must specify an operation, its necessary lifetime, preservation/invalidation checks, and actual full-path measurement. Do not subtract this study's component costs to claim a hypothetical optimization. A failed performance signal is useful evidence, and the closed selective episode and unconsumed confirmation entitlement remain unchanged.

## Call-path map to investigate

| Measured category | Original path | Attribution question |
| --- | --- | --- |
| Preparation | `Session.__init__` → composite `validate` → core tree validation, reference/guard/depth checks, `deepcopy`, semantic `digest` | Which costs repeat for immutable policies, and what must be checked on each ownership/connection boundary? |
| Routing | Lock/connection check → `snapshot().query` → actual-predicate `route` | Is cost query normalization, predicate routing, locking, or a higher-level call? |
| ANN timer | `execute_probe`, inherited native/policy backend, prepared-policy cache, installation and SQL/transport | Does the apparent application cost include repeated policy preparation or database/transport work? |
| Outer application timer | Original native/policy pair wrapper, plus charged preparation | Does any necessary work fall outside the primary internal timer? |

This map is source-based orientation, not a measured function-level conclusion.
