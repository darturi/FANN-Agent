# B2e: replica and session timing audit

October 26, 2026, America/New_York. NEXT-PARTIAL-CONTROLS-01.
Existing campaign: `reviews-partial-ann-v1-20261027T005510Z.q6rgxprs`, job `21048213_0`.

**B2e is complete. A targeted calibration experiment is justified, subject to a separately frozen design.** The saved evidence identifies progressive within-reader timing transients and a persistent session-associated partial-index gap. It does not identify the causal contribution of backend state, CPU placement, cache state or observer traffic. The captured replica settings, parameters, plans and prepared-plan counters match. There is no supported code correction to make from these traces alone.

**GB2e: GO to one instrumented, qualification-first A/A calibration design; implementation and execution are not ready or authorized by this audit.** B2d remains `measurement_inconclusive`: quality passes, nominal treatment endpoints pass, and all four required A/A intervals fail. Retain original execution and defer B1c, adoption, amortization and independent acceptance. No Torch commands are needed now.

## Evidence boundary and method

This audit reads saved source, JSON and JSONL only. It uses all 16,802 recorded searches, including all 6,400 retained measurements, 3,200 discarded warmups and 6,400 formal conditioning searches; all 3,200 slots, 5,700 plan packets, eight admissions, both session-boundary snapshots and prior verified results. Descriptive strata use recorded block, round, position and repetition. Temporal quarters are explicitly exploratory: consecutive groups of 50 query positions within each block, with no row selection or acceptance use.

No experiment modules were imported or executed. No tests, native/DB queries, new bootstrap replay, model fit, simulation, SSH, Torch or provider call occurred. There was no access to protected query values. Production/experimental/analysis source, prior reports/receipts, raw data, archives and seals remain unchanged; 2,235 prior input file hashes are pinned and checked. The only edits are this report, roadmap/index tracking and new audit JSON documentation. [Scope](../trials/torch-reviews-partial-ann-v1-settings-fix/b2e-audit-2026-10-26/scope.json), [input pins](../trials/torch-reviews-partial-ann-v1-settings-fix/b2e-audit-2026-10-26/preservation-before.json), [descriptive audit](../trials/torch-reviews-partial-ann-v1-settings-fix/b2e-audit-2026-10-26/analysis.json), [completion receipt](../agent/docs/verification/b2e-replica-session-audit-v1.json).

The previously verified archive SHA256 is `0bb845dea4a0f1668a8dc46ebe93ba25f6c0ead65a629606de628bf4219ae055`; sealed package manifest SHA256 is `c77efca4cbf297092a73c3921948209a1762b95a328ba1411154bea1ab4f89b4`. This audit preserves those files and relies on the [completed B2d verification](../trials/torch-reviews-partial-ann-v1-settings-fix/postrun-review-2026-10-26/replay-1/verification.json) and [unchanged performance result](../trials/torch-reviews-partial-ann-v1-settings-fix/postrun-review-2026-10-26/replay-1/performance.json); it does not rerun their inferential analysis or alter their verdict.

## What a replica actually owns

Within each cell, `a` and `b` are separate persistent connections to the **same private PostgreSQL server and same index**, rather than separate graph builds. Full/native640 and partial640 reside on two different restored servers. Therefore different partial graph bytes cannot explain the partial **within-cell** A/A gap. Between-cell timing still includes the separate server environments.

The [experimental ownership source](../agent/experiments/partial-ann-v1-settings-fix/pa_interface.py), lines 38–105 and 139–187, creates a backend object per reader, privately copies its source/index binding, freezes the admitted binding and verifies connection identity, autocommit and idle state. Connections cannot be replaced or retried silently. The shared snapshot and requests are intentionally read-only. There is no replica-label branch that changes native SQL, effort or policy work. The frozen loader uses the original [TorchBackend connection implementation](../trials/torch-reviews-first/runner.py), lines 156–183, through [legacy_execution.py](../trials/torch-reviews-partial-ann-v1-settings-fix/torch-partial-ann-v1-settings-fix/frozen/legacy_execution.py), lines 25–35.

Formal readers are admitted in fixed order: native-a, native-b, partial-a, partial-b. Admission costs are respectively 256.800, 64.208, 203.075 and 78.172 ms. These startup costs are recorded outside warm query latency; they cannot simply be subtracted from the recurring gap. They do show that creation order and label were never independently varied. Each label stays attached to the same connection throughout both blocks. Reversing query/cell/within-round order does not cross labels onto other connections.

## Recorded work and settings match

| Audit | Existing evidence | Conclusion and limit |
| --- | --- | --- |
| Admission binding | Origin and effective binding are exactly equal for a/b within each cell | No observed wrong target or effort assignment |
| Actual query settings | All six readers have identical recorded values at all four before/after block boundaries, including ef_search 640, iterative scan off and statement timeout 30,000 ms | No recorded a/b GUC mismatch; boundary snapshots are not continuous observation of every possible server state |
| Plans and parameters | 800 corresponding packets per a/b pair; every scientific packet field matches exactly after excluding observer charge timestamps | Same statement/parameter hashes, driver configuration, fresh and cached compact plans, cache counters and expectations within cell |
| Actual index | Full readers use `reviews_hnsw`; partial readers use `reviews_hnsw_votes108_v1` | Correct mechanism within each cell, no replica-specific plan path found |
| Preparation | Psycopg 3.3.6, threshold 5, cache maximum 100 for all; 799 cached packets per measured reader | Equal preparation exposure; first pre-query inspection is empty for each formal reader |
| Generic/custom selection | All 5,690 captured cached entries have `generic_plans=0`; all four formal readers end at recorded custom count 3,193 | A generic-versus-custom split is unsupported by the captured cumulative counters |
| Results and integrity | Prior full verification establishes equivalent repeated ID-distance mappings, correct predicate membership and final data/graph/module integrity | No output divergence explains the timing; integrity does not establish equal cache or CPU state |

Prepared state is session-scoped; PostgreSQL reports generic/custom **plan choices**, not query execution time. These semantics support interpreting the recorded counts, without assuming that every prepared statement has switched to a generic plan. [PostgreSQL PREPARE](https://www.postgresql.org/docs/17/sql-prepare.html), [pg_prepared_statements](https://www.postgresql.org/docs/17/view-pg-prepared-statements.html). The equality result covers the captured scientific fields, not unavailable internal executor counters or physical CPU state.

## Timing is still changing after the discarded warmup

The [formal measurement loop](../agent/experiments/partial-ann-v1-settings-fix/pa_measure.py), lines 468–545, conditions **both cells using their main reference connections**, then executes one discarded warmup and two retained queries on the selected measured connection. Conditioning a reference connection is not the same intervention as warming the measured connection's private backend state.

All values below are full outer means in milliseconds. Every reader contributes 800 observations at each repetition, with no discarded retained rows.

| Reader | Discarded warmup | Retained 1 | Retained 2 | Paired mean change, 2−1 | Slots where 2 is faster |
| --- | ---: | ---: | ---: | ---: | ---: |
| Native-a | 10.515120 | 8.093004 | 6.619778 | −1.473226 | 94.75% |
| Native-b | 10.050677 | 7.916938 | 6.588370 | −1.328568 | 91.63% |
| Partial-a | 9.429131 | 7.089037 | 6.136259 | −0.952779 | 98.13% |
| Partial-b | 6.828872 | 5.605336 | 5.293011 | −0.312325 | 90.38% |

The SQL-labelled timer also decreases for every reader, and its mean decreases in all eight reader/block combinations. This is consistent with progressive warm-state effects, broadly construed, but does not isolate cache warming from scheduling, frequency or other serial-execution effects. No third retained repetition exists to demonstrate a plateau. A fixed extra warmup count cannot be certified from this run.

The partial gap persists after splitting by repetition: b−a is **−1.483701 ms at retained 1 and −0.843248 ms at retained 2**. Selecting only retained 2 would change the completed analysis and would still leave a large descriptive gap. It is not a valid repair.

## The persistent partial gap is broader than an isolated outlier

The frozen partial A/A mean gap is −1.163475 ms, 95% interval [−1.248541, −1.074538], with b 17.5947% faster in arithmetic mean. The native gap is −0.103736 ms, interval [−0.256442, +0.051242]. All four original absolute/relative intervals fail. Those intervals are quoted from the saved result, not recalculated here.

| Existing stratum | Native b−a outer ms | Partial b−a outer ms |
| --- | ---: | ---: |
| Block 0 | +0.434316 | −0.936053 |
| Block 1 | −0.641789 | −1.390896 |
| Round 0 | +0.084555 | −1.540310 |
| Round 1 | −0.292028 | −0.786639 |
| Within-round position 0 | +0.111989 | −1.313056 |
| Within-round position 1 | −0.319462 | −1.013894 |
| Cell measured first | −0.059802 | −1.270605 |
| Cell measured second | −0.147671 | −1.056344 |

Each row is descriptive and overlaps other rows; these are not independent confirmations or newly passing gates. Labels are balanced in these marginal strata. Every query/block/cell/label occupies both within-round positions once. Partial-b is faster for **193/200 query averages**, whose median b−a gap is −1.162088 ms. The gap is negative in all eight block-by-temporal-quarter summaries, ranging from −0.823332 to −1.824710 ms. Native-b is faster for 103/200 query averages and changes direction across blocks and time. There is no basis for attributing both cells to a single constant label offset.

One scheduling alias remains: within-round position 0 always follows partial-reference conditioning last; position 1 always follows native-reference conditioning last. Label balance avoids an obvious count imbalance but does not identify separate effects of position and last-conditioned cell. A future design must vary these independently if it uses them for causal diagnosis.

## Timer boundary and observer effects

The partial A/A SQL-labelled gap is −1.089842 ms, 93.67% of the outer gap. However, `sql_ms` is **not pure server execution time**: the [sealed backend](../trials/torch-reviews-partial-ann-v1-settings-fix/torch-partial-ann-v1-settings-fix/frozen/vendor/fannagent_pgvector/backend.py), lines 1165–1214, starts the native timer immediately before `conn.execute(...).fetchall()` and stops after ID/distance decoding. It includes client/protocol work, server execution, waits, fetching and decoding. Thus the gap is largely inside that composite boundary; CPU, I/O, transport and decoding contributions cannot be separated. A server-only or wrapper-only root cause is unproved.

The [observer source](../agent/experiments/partial-ann-v1-settings-fix/pa_metadata.py), lines 185–245, inventories prepared state and obtains fresh/cached plans. Across 5,700 packets this produces **17,090 of 17,143 observer SQL calls**: 11,400 inventory/fresh-plan calls plus 5,690 cached-plan explanations. Reader inspection order is fixed before and after each query: native-reference, partial-reference, native-a, native-b, partial-a, partial-b.

These statements omit ANALYZE, so they inspect plans rather than execute additional ANN searches. Nevertheless, `EXPLAIN EXECUTE` can retrieve/replan a cached statement. [PostgreSQL EXPLAIN](https://www.postgresql.org/docs/17/sql-explain.html). Captured counters reconcile with that observer activity: each formal reader performs 2,400 actual searches, the first five are unprepared, and 799 cached explanations add plan decisions; the last inventory sees 3,193 before its final explanation. The first post-query custom count is 1 and the next pre-query count is 2 despite no intervening search on that reader. This is direct evidence that the observer participates in prepared-plan history. It is symmetric in count and captured plans, so it is a plausible perturbation requiring prospective control, not a demonstrated explanation for the a/b difference.

## What remains unidentified

| Hypothesis | Assessment from current evidence | Evidence a calibration would need |
| --- | --- | --- |
| Wrong target, SQL, parameters, recorded GUCs or generic/custom split | Unsupported by matching packets/settings/counters | Preserve these conformance checks; no code or plan-mode change justified |
| Progressive reader-local warmth / serial state | Repetition gradients directly observed; mechanism and plateau unknown | Fixed, fully charged on-reader conditioning schedule and all repetition traces; prospective stability gate |
| Persistent connection/backend or creation-order effect | Logical label is inseparable from connection and creation order | Reader→backend PID→server mapping; crossed label/creation order across fixed connection epochs; report physical-backend contrasts |
| CPU placement, migrations, NUMA, scheduling or frequency | Not measured at the required per-backend/query boundary | Allowed CPU set, placement/migration and CPU/wait proxies with known limitations and overhead |
| Cache/buffer/I/O differences | Cannot infer from current non-ANALYZE plans or composite timer | Predeclared low-overhead counters/diagnostic windows; do not put perturbed diagnostic timing into primary estimates |
| Fixed observer order or conditioning-order alias | Present in source and trace; causal effect unknown | Independently counterbalanced observer/conditioning order or one predeclared observer-free primary window with boundary checks |

[runtime-identity.json](../trials/torch-reviews-partial-ann-v1-settings-fix/collection-recovery-2026-10-26/returned/reviews-partial-ann-v1-20261027T005510Z.q6rgxprs/run/runtime-identity.json) pins image/module/profile/registry, but lacks logical-reader backend PIDs and CPU/cache attribution. [pa_trace.py](../agent/experiments/partial-ann-v1-settings-fix/pa_trace.py), lines 91–123, counts search SQL without saving those per-search details. [pa_job.py](../agent/experiments/partial-ann-v1-settings-fix/pa_job.py), lines 13–43, sets BLAS/OMP thread counts but does not establish per-backend CPU placement. A four-CPU allocation is not that proof. The original runner's older main-path affinity logging is not called by this runtime and cannot fill the missing evidence.

## GB2e decision and next phase

**One targeted calibration is worth designing.** Scoped recall improves by 1.25 percentage points, and the apparent 1.274 ms treatment saving is practically interesting. The 1.163 ms identical-partial gap prevents attribution, while the observed repetition gradient and missing physical identities give a concrete diagnostic question. More seeds or an unchanged repeat would not resolve those aliases. There is no validated single warmup, affinity or driver-setting fix to implement now.

Proposed **B2f / NEXT-PARTIAL-CALIBRATION-01** is the next design task. The following are requirements for its future contract, not an executed or frozen experimental schedule:

| Phase | Must do before advancing | What it informs / decision gate |
| --- | --- | --- |
| B2f.0 fixed-graph and telemetry feasibility | Establish how to obtain immutable physical restores of the exact B2d full and partial graphs; specify reader/PID/server identities and feasible CPU/wait/cache observations | If exact graph restoration or required identities cannot be supported, stop this comparison design; rebuilding is a separate scope |
| B2f.1 freeze mechanism and resources | Fix connection epochs/creation order, label crossover, independent conditioning/observer order, an on-reader warmup sequence, telemetry cadence and all charge categories; choose a prospective stability criterion | Separates persistent backend effects from label/order/warmth; no outcome-adaptive warmup or dropping early bad observations |
| B2f.2 implement and check only after request | Separate experimental package; local ownership, counterbalancing, accounting, stop and identity checks; preserve all old seals | Readiness for a separately authorized calibration allocation, not native evidence |
| B2f.3 bounded native A/A qualification | Run only the fixed calibration contract, all rows retained; evaluate unchanged absolute/relative equivalence margins plus predeclared stability and physical-backend diagnostics | Pass permits a later treatment-comparison decision; failure/insufficient identity stops without extending the budget |
| Later treatment comparison | Separately freeze full native640-versus-partial640 quality/economics, server/placement balance and final integrity under the qualified measurement regime | Only jointly passing controls, quality, economics and final proofs can support scoped benefit; independent acceptance remains later |

The proposed outer spending envelope is **at most one 3-hour, 4-CPU, 32-GiB allocation and 16,802 combined backend search attempts** for calibration, including conformance, any repeated quality checks, conditioning, warmups and retained calls. This is a design ceiling, with **zero allocations or searches authorized now**. B2f.1 must derive and freeze exact reader-admission/live-reader, SQL/observer/telemetry, stage-time and scratch/memory limits within that envelope; inability to do so is a no-launch decision. There is no second allocation, automatic resume, extra effort/index family or protected-sample entitlement. Calibration overhead is fully charged; even a stable warm scope would not establish cold or serving economics.

Unchanged scientific limits remain recall floors ≥0.95; lower 95% recall-delta bound ≥−0.0025; both cells' A/A 95% intervals inside ±0.10 ms and ±log(1.02); future treatment conservative upper gap ≤−0.10 ms and upper log ratio ≤log(0.98), with both block gaps negative. A more complex crossover needs a frozen multiplicity and dependence analysis. Relabeling persistent backend bias so that pooled labels cancel is not calibration: preserve and assess physical-session/epoch contrasts, and forbid selecting the fastest backend or timing regime after results arrive.

The saved [job-exit receipt](../trials/torch-reviews-partial-ann-v1-settings-fix/collection-recovery-2026-10-26/returned/reviews-partial-ann-v1-20261027T005510Z.q6rgxprs/run/job-exit.json) says the stopped work directory was retained. That is a possible route to the exact partial graph, not proof it is still accessible or safely restorable. No remote availability check was made here.

**Revised critical path:** verified inconclusive B2d → completed B2e mechanism/identity audit → freeze B2f fixed-graph, instrumented A/A design → separately requested implementation/local checks → separately authorized bounded calibration → stability and unchanged A/A gate → prospective treatment comparison → only after joint qualification, maintenance/amortization/integration and independent acceptance. If calibration fails within its bound, retain original execution and record closure; do not enlarge the study automatically.

## Progress and handoff

- [x] B2e.0 Pin raw/seal/verdict and declare the no-experiment boundary.
- [x] B2e.1 Reconcile ownership, actual settings, per-replica plans/parameters/preparation and conditioning source.
- [x] B2e.2 Describe all saved repetitions and block/round/position/query patterns; identify timer/observer limitations.
- [x] B2e.3 Record supported transients, unresolved physical state and a conditional calibration-design GO.
- [x] B2e.4 Save report, descriptive evidence, preservation receipt and roadmap tracking.
- [ ] B2f.0–1 Establish restoration/telemetry feasibility and freeze the bounded calibration contract.
- [ ] B2f.2–3 Implementation, checks and native calibration only after separate requests; no commands or job package now.

The [roadmap](fannagent-performance-research-roadmap-2026-10-22.md) is updated to version 1.32. B2e completion does not convert any earlier negative or inconclusive result into a performance success.
