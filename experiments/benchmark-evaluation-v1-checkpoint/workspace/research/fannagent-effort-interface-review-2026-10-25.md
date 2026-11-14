# B1-review: native effort and interface decision

Date: October 25, 2026, America/New_York.  
Review: `NEXT-EFFORT-REVIEW-01`, complete.  
Scope: existing source, saved results and primary documentation only. No execution code changed; no tests, database/native/Torch calls, fits, policy simulations or new experiments ran.

**Decision: prepare one quality-first, fixed `ef_search=480` versus `640` native comparison. Do not proceed to B1c or reuse B1b's two-reader routing interface.** The [prospective B1b2 design](fannagent-native-effort-midpoint-v1-design-2026-10-25.md) specifies one allocation, an early quality stop, fresh A/A controls and a warm persistent-reader objective. It is a design, not an implemented or measured improvement. Original execution remains adopted; P2/P3/B1b verdicts, confirmation entitlements and M1/M2/M3 are unchanged.

## Evidence that constrains the decision

The [verified B1b report](fannagent-native-effort-frontier-v1-results-2026-10-25.md) remains authoritative. Its formal aggregate verdict is `measurement_inconclusive`, with no qualifying context/regime. Reuse precision passes all 32 intervals, but effort320 loses 0.800 percentage points of recall overall and every context fails the development reserve. The forced640 wrapper adds 0.206235 ms during reuse and fails overhead protection. Activation A/A passes only 2/32 intervals. Better activation precision would not fix the unchanged recall or reuse-overhead failures.

This review rereads existing raw timers to describe boundaries; it does not rerun the analyzer, construct new confidence intervals, fit a router or reinterpret a failed gate. The [machine-readable audit](fannagent-effort-interface-review-2026-10-25/audit.json) records the arithmetic calculation and source-derived call counts. The [input inventory](fannagent-effort-interface-review-2026-10-25/input-inventory.json) pins 685 existing files, including all 146 sealed B1b files, all 40 returned files and prior evidence. All 324 prior code/source, 29 consulted-input and 128 historical raw/output hashes still match.

## Admission work: avoid the second reader when effort is constant

B1b's [custom Pool](../agent/experiments/native-effort-frontier-v1/ef_interface.py) eagerly constructs and binds both320 and640 readers for every fresh session, even when a forced-effort cell will use only one. Both readers load local identities, construct backend/profile state, open a connection, verify reader privileges, bind the target and install session settings. The two-reader ownership and setting-isolation checks serve a correctness purpose; their work is real.

The [Torch reader](../trials/torch-reviews-first/runner.py), inherited [frozen backend](../trials/torch-reviews-native-effort-frontier-v1/torch-native-effort-frontier-v1/frozen/vendor/fannagent_pgvector/backend.py) and saved effective bindings show 17 explicit startup `conn.execute` calls per reader: one security check, one target-binding acknowledgement, 14 source-setting statements and one statement-timeout statement. B1b therefore executes 34 such startup calls for its wrapped session versus 17 for the ordinary single reader. These static counts exclude connection authentication, protocol/internal server work, shared snapshot creation, audit and cleanup; they are not a claim about 17 measured network round trips or their individual durations.

Existing retained activation timers, averaged equally across the two complete blocks:

| Path | Reader preparation ms | First query outer ms | Total activation ms |
| --- | ---: | ---: | ---: |
| Ordinary native640 | 63.873831 | 19.428905 | 83.302736 |
| Wrapped forced640 | 116.185421 | 22.120838 | 138.306258 |
| Wrapped forced320 | 118.331285 | 16.461073 | 134.792358 |

The forced640 preparation category adds 52.311590 ms; the full activation gap is 55.003523 ms. These descriptive categories locate the additional admission work. Failed activation precision and the lack of operation-level timers prevent a qualified causal estimate for any particular JSON read, copy, setting statement or connection. There is no prediction that deleting one reader will save exactly this amount.

A fixed480 versus640 question needs one bound reader per arm. It does not need an online effort envelope, a selector or a second product reader. Experimental A/B replicas are controls, not a four-reader serving design. Persistent readers can avoid repeated admission in the measured scope, but startup and cleanup must still be recorded; no assumed request count amortizes them into a claimed serving gain.

## Query work: distinguish differential overhead from common work

| Boundary | Source finding | Consequence |
| --- | --- | --- |
| Additional wrapped validation | `Pool.query` calls `Snapshot.query`, which performs strict schema/filter/k validation, float32 dimension/finite/unit-norm checks and a JSON-compatible owned output conversion over the 768-value vector | This is additional work relative to B1b's already-validated ordinary native input; do not label all of its duration from a broad timer gap |
| Wrapper ownership checks | Each wrapped query checks both connections, their bindings and unchanged origin manifests before selecting a reader | A future dynamic interface must preserve ownership, stale-handle rejection and setting isolation; deleting checks is not a qualified optimization |
| Extra copies at admission | The bound backend makes effective-setting views; Pool also owns copies of origin/effective bindings and expected state | Possible simplification for a single immutable reader, without modifying the adopted source manifest |
| Common native scaffolding | The inherited `_execute_probe` constructs SQL/vector text, a nonce, execution-context/group metadata and begin parameters even on the ordinary native branch | Both ordinary and wrapped paths pay this work. It is a separate hypothesis, not the established differential wrapper cause |
| Common policy-cache construction | `NativeBackend.__init__` constructs `PreparedPolicyCache(PROFILE)`; its constructor copies/fingerprints profile state | Native-only setup may admit a later simplification, but no native policy compilation occurs here and there is no isolated cost estimate |
| Existing current implementation | Current [dispatch](../agent-pgvector/src/fannagent_pgvector/dispatch.py) and [query validation](../agent-pgvector/src/fannagent_pgvector/query_validation.py) contain a guarded native-direct path and specialized validation with shared-validator fallback | Useful design references; this review neither adopts nor benchmarks them. Mixing them into the next effort comparison would confound the intervention and require new qualification |

For the **same forced640 versus original640 reuse contrast**, matched by query, block, round and repetition and averaged across A/B labels, the saved timer categories decompose as follows:

| Category | Wrapped minus ordinary, ms |
| --- | ---: |
| Full outer query | +0.206235 |
| Inner SQL timer | +0.081905 |
| Work outside that SQL timer | +0.124329 |

This is an arithmetic decomposition of one matched contrast, not subtraction of separately summarized baseline studies. The outside-SQL term includes everything outside the inner timer in both paths; it is not isolated validation time. The SQL term includes transport/result decoding and does not prove additional engine work. The decomposition supports simplifying the question before profiling another runtime; it cannot promise a 0.124329 ms optimization.

Any later validation optimization must preserve invalid-input rejection, finite/dimension/unit-norm semantics, permitted filters/k, owned immutable admitted state, connection/binding identity, rollback/close behavior and explicit new-session recovery. Query IDs, cached prior outputs and evaluator strata cannot substitute for validating a new mutable request. Those changes are excluded from B1b2.

## Why one intermediate effort is worth a bounded probe

Effort320 is fast but fails quality. Effort640 is the study reference and offers no reduction against itself. There is an unanswered current-index quality/cost question between them. The [pinned pgvector source](https://raw.githubusercontent.com/pgvector/pgvector/8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c/src/hnsw.c) makes `ef_search` a user-settable search parameter in1–1000; the [versioned documentation](https://github.com/pgvector/pgvector/blob/v0.8.6/README.md) describes its speed/recall tradeoff. This supports an actual intervention without rebuilding the graph, not interpolation of this workload's recall.

Choose **480**, the arithmetic midpoint, before observing any480 outcome. This is an information probe, not a fitted optimum, estimated safe effort, binary search or assumption of monotone returned sets. Neither the320/640 data nor the old four-level sweep on another physical graph establishes what480 will do. Values such as560/600 are plausible alternatives but lack a measured preference here; a ladder that continues until a point passes is not the finite proposal.

The question is deliberately simpler: can **one global constant** satisfy all three filters' quality reserve and deliver useful warm native savings against640? A passing answer may make routing unnecessary in this scope. A failure closes this one probe; it does not prove all intermediate values or wider plans/indexes fail. No post-hoc per-context480/640 map rescues a failed global comparison.

Session-bound immutable effort is consistent with [PostgreSQL17 setting scope](https://www.postgresql.org/docs/17/sql-set.html); exact-reference transaction-local settings must roll back without changing the reader's session effort. Connection reuse is a standard lifecycle mechanism: [Psycopg3.3.6's pool documentation](https://github.com/psycopg/psycopg/blob/3.3.6/docs/advanced/pool.rst) describes keeping connections ready while managing configuration, reset, failed connections and capacity. B1b's Pool is custom, not `psycopg_pool`. Installing that separate package would not fix the recall loss or eliminate validation, so no new dependency is proposed.

The [HNSW paper](https://arxiv.org/abs/1603.09320v4) supplies algorithmic background. It supplies no workload-specific quality bound or license to transfer the historical6076 graph's measurements to the current90f4 graph.

## Decision gates and revised critical path

The detailed [B1b2 contract](fannagent-native-effort-midpoint-v1-design-2026-10-25.md) defines counts, ownership, costs, analysis and stopping rules. Its phases are:

| Phase | Required work | What it informs / decision gate | Status |
| --- | --- | --- | --- |
| Review | Audit existing costs, validation/lifetimes, quality and identities; choose one prospective question | GO for the fixed480 design; NO-GO for unchanged wrapper/router or activation recalibration | Complete |
| Implementation and local readiness | Isolated harness; unchanged frozen native SQL/scorer; mock correctness/error/count/identity/replay checks; seal source, cohort, order and budget | G0-B1b2: implementation matches this design before any native execution | Planned; no code/package yet |
| Native conformance | Actual settings, target/index/module, HNSW plans, exact-reference independence, alternating reader isolation and error/new-session recovery | Reject invalid runtime; do not treat a failure as a scientific quality result | Planned |
| Quality screen | Fresh exact, native640 and native480 outcomes on the same200 exposed vectors/600 cases | Require completeness/validity, native floor and −0.25pp development reserve overall/per filter; otherwise stop by1,830 searches | Planned |
| Conditional warm measurement | Two complementary temporal blocks in one job; same native method/guards, fixed readers, new A/A and full outer timers | G-AA first, then min0.10ms/2% savings overall/per filter and direction in both blocks; max59,430 total searches | Planned, contingent on quality |
| Verified decision | Check archive/identities/raw coverage, independent data-only replay and exact gate parity; retain failed/censored work | Negative, inconclusive or promising **warm fixed configuration only**; no automatic adoption, B1c or confirmation | Planned |

Critical path: **completed review/design → requested isolated implementation/local checks/seal → one user Torch submission → native conformance → quality screen → conditional warm A/A and benefit measurement → verified replay → scoped branch decision**. The implementation stage must provide exact commands after the package exists. No user commands or new experiment are needed for this review.

The proposed maximum is one4CPU/32GiB/two-hour allocation, a6,600-second work deadline and59,430 searches. Quality failure uses at most1,830. Provider calls, fits, new vectors, protected values and confirmation queries have zero allowance. Both timing blocks share one allocation/database and do not establish independent-host reproducibility. All200 vectors are exposed development data.

A positive result would justify an operating-scope/adoption and independent-entitlement review; it would not solve the original joint activation/reuse objective or establish an improved agent method. A failed precision gate remains inconclusive, without control subtraction or more blocks. Failed quality/economics closes the finite probe. Broader plan-selection or filtering-aware index work is a subsequent separately justified branch, not an automatic effort sweep.

## Progress record and preservation

- [x] Existing B1b quality/control verdicts and source/input identities reconciled.
- [x] Static admission/validation/lifetime audit and descriptive timer decomposition completed.
- [x] Go/no-go recorded; one intermediate effort and prospective phased contract specified.
- [x] Roadmap and experiment index updated; [review receipt](../agent/docs/verification/effort-interface-review-v1.json) records hashes and documentation checks.
- [ ] B1b2 implementation/local readiness and sealed commands.
- [ ] Native conformance/quality and, conditionally, warm comparison.
- [ ] Verified result and scoped decision.

All prior source, sealed code, returned data and receipts remain preserved. This document supersedes only B1b's historical “next: read-only review” action; it does not rewrite B1a/B1b contracts or any result. See [roadmap v1.16](fannagent-performance-research-roadmap-2026-10-22.md).
