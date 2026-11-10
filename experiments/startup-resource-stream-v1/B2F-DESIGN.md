# B2f: frozen instrumented A/A calibration design

October 26, 2026, America/New_York. NEXT-PARTIAL-CALIBRATION-01.
Protocol `partial-calibration.v1`. **Design frozen only; no code or experiment.**

This contract answers one question: **can a fixed, instrumented warm-reader regime establish equivalence between identical native640 readers and between identical partial640 readers, without hiding physical-session bias?** It follows the [completed B2e audit](fannagent-b2e-replica-session-audit-2026-10-26.md). The full and partial graphs, data, query policies and scientific margins remain unchanged. Connection ownership, CPU placement, warmup and observation boundaries are explicitly controlled in a new measurement scope.

Passing permits a later treatment-comparison design decision. It cannot qualify a partial-index speedup, repair B2d, select a router, establish amortization or authorize adoption. B2d stays `measurement_inconclusive`; original execution remains retained and B1c deferred.

The [machine-readable contract](../trials/torch-reviews-partial-ann-v1-settings-fix/b2f-design-2026-10-26/contract.json), [complete prospective schedule](../trials/torch-reviews-partial-ann-v1-settings-fix/b2f-design-2026-10-26/schedule.json), [count/balance accounting](../trials/torch-reviews-partial-ann-v1-settings-fix/b2f-design-2026-10-26/plan-accounting.json) and [freeze receipt](../agent/docs/verification/partial-calibration-v1-design-freeze.json) form the permanent design record. The receipt pins this document and every design artifact. Changes to scientific choices require a new prospective revision, before implementation or measurements.

## 1. Frozen evidence and scope

Use B2d campaign `reviews-partial-ann-v1-20261027T005510Z.q6rgxprs`, job `21048213_0`, archive SHA256 `0bb845dea4a0f1668a8dc46ebe93ba25f6c0ead65a629606de628bf4219ae055` and package-manifest SHA256 `c77efca4cbf297092a73c3921948209a1762b95a328ba1411154bea1ab4f89b4`. The contract pins source files, the original 200 exposed query/vector groups, truth/results, eligibility, catalog/index identities and B2e evidence. No additional vectors, predicates, effort levels, protected samples, policies, fits or providers are allowed.

Scope remains the actual `total_votes >= 108` predicate, k=10, 768-dimensional vectors, full 247,286-row dataset/global IDs, cosine distance and ef_search=640 with iterative scan off. Keep all B2d reader settings, timeout, Psycopg 3.3.6 automatic preparation threshold 5/cache maximum 100 and `plan_cache_mode=auto`. Preserve administrator versus reader settings, including 4 MiB versus 16 MiB work_mem. No forced generic/custom mode, planner tuning, new extension, module patch, instrumentation extension or EXPLAIN ANALYZE treatment is allowed.

| Identity | Frozen value |
| --- | --- |
| Full target identity | `90f4a709ab3ee7ce40fe7630009b29d5646f6e1e80ceab8c2246cb970d803484` |
| Full graph, both source copies | `base/16384/264013`; 1,012,678,656 bytes; SHA256 `dbc14b0912d7e9ad9cd4ddcf806cac081412e66b1861de7ce3629fd81e23b393` |
| Partial target identity | `6ee32f41235ef0a18143cc5ed37e169265fe3757211ef7df6480c7217f382896` |
| Partial graph | `base/16384/270339`; 202,743,808 bytes; SHA256 `b0300f40eb9917c158855d00fe0a8f36cb1c8aee958fb65b061e4db4d8606700` |
| Native module | SHA256 `e7dcace1f4dfd4ea233256d6cdfc17b3190f3f07cccb6406b479b5ebe8b85811` |
| Runtime image | SHA256 `7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a` |

Fresh catalogs must reproduce the complete existing target structure, predicates, opclasses, relation options and role-specific environment. Graph hashes alone are insufficient. Preserve the full graph on the candidate server as B2d did; no graph rebuilding, reindexing, import, data update, explicit ANALYZE/VACUUM or index deletion is permitted. Any unexpected graph/catalog/runtime identity stops qualification.

## 2. Fixed-graph restoration prerequisite

The recorded stopped work directory is:

```text
/scratch/dar579/torch-reviews/partial-ann-v1.tu6x964d/partial-21048213.3xxjxm27
```

Its `native640/pgdata` and `partial640/pgdata` must still be readable. The saved cleanup and retained-directory receipts establish their historical state, not current availability. **Current remote feasibility remains unverified.** Section 12 gives the small read-only inventory needed from the user; it does not start a database or submit a job.

The future implementation must validate source ownership/real paths, reject symlinks, hard-linked writable aliases and external tablespaces, require no source postmaster PID file, and verify clean shutdown using the image's matching PostgreSQL control-data utility. Acquire full stopped-cluster content inventories before copying. Require source consistency across copy and finalization, not just absence of a PID file. Copy each complete stopped cluster once into a new private workspace with independent writable files. Never start, edit, reconfigure or recover the old source directories. Read-only-bind source roots; mount only new copies writable. Authentication/socket setup may change only the new copies' private credentials and runtime paths, without logging secrets or changing query privileges.

Whole-cluster copies must include transaction/WAL state; transplanting just graph relation files into another database is forbidden. This follows PostgreSQL's [file-system backup requirements](https://www.postgresql.org/docs/17/backup-file.html). Use [pg_controldata](https://www.postgresql.org/docs/17/app-pgcontroldata.html) for recorded cluster control state. An unclean, inaccessible or changed source fails the prerequisite; recovery on the old source and a replacement graph are outside this contract.

Before searches and at finalization, verify all data IDs, float32 vector bits and metadata against the original pinned input, both original graphs and the partial graph against the above file identities, and module/image/profile/registry identities. Require the expected whole relation-file families, rejecting additional segments/forks or missing files relative to the recorded inventories. Mutable WAL/statistics/authentication files in **new** working clusters are not expected to retain their initial hashes; graph contents, source clusters and logical scientific data must.

## 3. Connections and placement

Use exactly two private PostgreSQL servers, two persistent main reference/conditioning readers, and two fresh formal reader pairs in each of two epochs. Close the four formal readers between epochs; do not restart or rebuild servers. This is **10 total reader admissions, at most six live readers**, plus two administrator connections: eight live SQL connections maximum. A reader retains one physical backend throughout its epoch; replacement, retry or reconnect fails qualification and never replays a search.

Each formal reader has immutable identity `(epoch, cell, r0/r1, backend PID, process start ticks, server identity)`. Logical `a/b` is only a recorded crossed label and cannot affect query work. Record admission rank and duration. Creation order is:

| Epoch | Formal admission order |
| --- | --- |
| 0 | native-r0, partial-r0, native-r1, partial-r1 |
| 1 | partial-r1, native-r1, partial-r0, native-r0 |

Require four allocated logical CPUs on **four distinct physical cores**, using recorded `(socket, core, logical CPU)` topology. Select the first four representatives in that sorted order, called C0–C3. No access outside the allocation's allowed CPU set. Fewer eligible cores, unreadable topology or denied affinity is a failed qualification, without a larger automatic allocation.

Pin client execution to C0 and owned postmasters/administrator/background processes to C3. Both formal backends and the conditioner for a cell use the **same single CPU**: native C1/partial C2 in epoch 0, native C2/partial C1 in epoch 1. Set affinity before searches and verify readback; record inherited background placement. Keep BLAS/OMP at one thread. Do not change NUMA policy, CPU frequency, scheduler priority, kernel settings or PostgreSQL query GUCs.

Affinity restricts eligible execution CPUs, subject to the allocation/cpuset; permission and effective masks must be checked. It does not prove exclusive hardware or eliminate external interference. [Linux sched_setaffinity](https://man7.org/linux/man-pages/man2/sched_setaffinity.2.html). Record socket/core/thread/NUMA topology and memory-allowed sets. Core assignment is a prospective measurement intervention, not a claimed proven fix. Swapping cores together with fresh epochs cannot identify a standalone causal core effect.

## 4. Exact sequence and primary timing boundary

1. Restore and verify identities/resources; record required telemetry capabilities before any search.
2. Run two fixed exposed-query fixtures (the first two canonical query IDs in schedule.json): two full exact searches, four full native searches and four partial native searches, **10 searches** total. Repeated native outputs must match the pinned results.
   For each fixture: pre-plan both main readers, execute one full exact, perform two ANN repeats per cell with cell order alternating by fixture/repeat parity, then post-plan both mains. This calibration uses the same two main connections throughout; native rollback/recovery fixtures are not repeated. Later local negative ownership checks remain required.
3. Recompute full truth and both native outcomes for all 200 cases: **600 searches**. All outputs must pass exact independent scoring and pinned full/partial result parity. Apply the unchanged quality gate before formal readers. Each quality query has pre/post plans on both mains, one exact truth and one search per cell; cell order alternates by canonical rank parity.
4. Admit epoch 0 formal readers and perform **10 fixed priming ANN searches per reader**, using the first canonical query. These 40 calls are charged and checked, never primary observations. This traverses driver preparation without forcing its plan mode.
5. Epoch 0: bulk pre-plans → primary window → bulk post-plans → paired observer diagnostic → close formal readers.
6. Admit epoch 1 readers in reversed creation order, apply the fixed CPU crossover and repeat 40 priming calls. Epoch 1: paired observer diagnostic → bulk pre-plans → primary window → bulk post-plans → close formal readers.
7. Final data/graph/module/catalog/source-integrity and cleanup checks; save raw, locks, complete accounting and terminal status on every exit. No treatment-benefit analysis or interim A/A selection occurs on Torch.

Canonical query order is sorted by SHA256 of `partial-calibration.v1/primary/20261026/` plus query ID, then query ID. Epoch 1 reverses that order. All explicit order rows are frozen in schedule.json; no runtime random choice or adaptive repetition is allowed.

Each epoch visits every query and both cells. For each cell/query, execute one burst on each formal reader. Before **each burst**, execute one conditioning query on each main cell reader, then on the selected formal reader execute **four discarded warmups followed by three retained repetitions**. Every result must reproduce the appropriate fresh reference mapping. Four warmups are a fixed prospective probe, not an established plateau; the stability gate may reject it.

The primary window has no SQL plan/settings/statistics observations or proc-file reads between these seven on-reader searches. Collect only existing outer/backend timer values and in-memory result/identity accounting; validate results outside the timer and buffer records. Flush trace data after the post-burst telemetry sample. Preserve the existing full outer query timer as primary, with its guards, request/SQL preparation, protocol, execution, fetch and decode work. The inherited SQL-labelled timer is secondary and remains a composite client/server boundary. Do not subtract telemetry, conditioning or setup costs from allocation accounting.

For canonical rank r=0…199 and epoch e, cell order uses bit 0 of r XOR e; formal reader order uses bit 1 XOR e XOR cell index; last-conditioned cell uses bit 2 XOR e and is held the same for both reader bursts of that query. These factors decouple last conditioning from first/second reader position. Each epoch/cell/physical reader has exactly 50 query bursts in each position-by-last-conditioner combination. The frozen crossed-label formula gives each physical reader 100 `a` and 100 `b` labels per epoch; labels never substitute for physical identities in acceptance.

## 5. Observation contract and overhead

Resolve `pg_backend_pid()` on each admitted connection, with `prepare=False`, and verify its namespace-visible `/proc` PID, start ticks, parent/postmaster, role/database and unique new server/socket path. Recheck the physical mapping at epoch boundaries and through proc start-time checks. A reused or replaced PID, unexplained child query worker, cross-server target or changed effective affinity fails. [PostgreSQL session information](https://www.postgresql.org/docs/17/functions-info.html).

| Observation | Mandatory cadence | Use and limit |
| --- | --- | --- |
| `/proc/PID/stat`, `/proc/PID/status`, `/proc/PID/io`, affinity; backend and client | Before/after each primary on-reader burst; before/after each diagnostic on-reader search | CPU ticks/resolution, last CPU, faults, context switches, allowed CPU/memory sets, read/write byte deltas; primary attribution is burst-level |
| Sample timestamps, elapsed observation cost, parser/capability metadata | Every telemetry bundle | Fully charge observer work; reject missing required fields, identity drift or invalid counter deltas |
| `/proc/PID/schedstat` | Same cadence when available; capability frozen before searches | Optional finer CPU/runqueue context; missing/disabled accounting is unavailable, never inferred zero |
| NUMA maps and readable governor/frequency metadata | Epoch boundaries only, if accessible | Optional context, without changing policy or requiring privileged tools |
| Catalog/settings/prepared counters and plans | Fixed boundary/bulk and diagnostic cadence below | Verify work identity; observations are charged and are not per-query server execution telemetry |
| Existing PostgreSQL cumulative I/O/buffer/activity counters | Initial, each epoch start/end and final, from existing administrators only | Window context with lag/caching caveats; no resets, forced flushes, new role grants or instrumentation settings |

Required proc data must be readable for the owned backends and client; inability stops qualification. Optional capabilities have one fixed availability record and cannot trigger a different timing schedule. No perf, eBPF, privileged access, continuous polling or background sampler is introduced. The scheduler counter's nanosecond fields do not establish nanosecond measurement accuracy; tick counters keep their declared coarse resolution. [Linux proc stat](https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html), [status](https://man7.org/linux/man-pages/man5/proc_pid_status.5.html), [I/O](https://man7.org/linux/man-pages/man5/proc_pid_io.5.html), [kernel scheduler statistics](https://docs.kernel.org/scheduler/sched-stats.html).

Before and after each primary epoch, inspect all 200 queries on all four formal readers in the explicit boundary order rows in schedule.json. Use epoch query order and rotate the base reader order by query position modulo four, reversing on post-boundary XOR epoch. Each reader occupies each inspection position 50 times per boundary. This gives 3,200 formal boundary plan packets. Each packet contains prepared inventory, non-ANALYZE fresh plan, cached EXPLAIN EXECUTE, statement/parameter hashes and preparation configuration. Qualifying plans must use the correct actual target, match within each replica pair and preserve the recorded custom-plan regime; unexpected generic selection or replica divergence stops rather than forcing another plan mode. Capture all mismatches before stopping. Boundary plans are a narrower observation guarantee than a per-search execution plan; no claim otherwise.

Each cached explanation can affect prepared-plan history and must be counted. These counts are not ANN executions or latency measures. [pg_prepared_statements](https://www.postgresql.org/docs/17/view-pg-prepared-statements.html), [EXPLAIN](https://www.postgresql.org/docs/17/sql-explain.html). PostgreSQL cumulative counters are delayed and transaction-cached, so their deltas are not exact per-query cache attribution; keep autocommit observation and record intervals. [PostgreSQL statistics](https://www.postgresql.org/docs/17/monitoring-stats.html).

## 6. Small paired observer diagnostic

Select exactly eight of the same 200 vectors by SHA256 of `partial-calibration.v1/observer/20261026/` plus query ID, then query ID. The selection and all burst orders are frozen in schedule.json. For each vector in each epoch, run paired `observer-off` and `observer-on` modes, each visiting both cells/readers with the same four warmups/three retained repetitions and two conditioning searches per burst. Alternate which mode runs first over the eight vectors and reverse in epoch 1.

Both diagnostic modes have proc bracketing for each of the seven on-reader searches per burst; conditioning calls retain standard timers only. Only `on` adds pre/post plan inspection of all six readers for that query, with rotated inspection order. This yields 192 plan packets. Neither diagnostic mode supplies primary timing observations; proc bracketing itself makes diagnostic-off different from the primary burst boundary. With only eight vectors this is a bounded descriptive diagnostic, with no benefit/causal-success gate or mode selection. Its results cannot rescue a failed primary gate or authorize another observer regime. The primary observer-free regime was chosen before these measurements.

## 7. Exact finite counts and resources

| Search category | Count at complete acquisition |
| --- | ---: |
| Conformance fixtures | 10 |
| Fresh quality: 200 exact +200 full +200 partial | 600 |
| Formal reader priming: 2 epochs ×4 readers ×10 | 80 |
| Primary conditioning: 1,600 bursts ×2 | 3,200 |
| Primary discarded warmups: 1,600 ×4 | 6,400 |
| Primary retained calls: 1,600 ×3 | 4,800 |
| Diagnostic conditioning: 128 bursts ×2 | 256 |
| Diagnostic warmups: 128 ×4 | 512 |
| Diagnostic retained calls: 128 ×3 | 384 |
| **Total** | **16,242** |

This is below B2e's 16,802 outer envelope. The remaining **560 are not spendable**. At conformance completion the search count is 10; at complete quality stop, 610; after full epoch 0, 8,426. Every attempted search reserves its charge before dispatch. Failed calls count; never retry or fill a missing observation.

Exactly 4,200 plan packets at completion: eight conformance fixture packets, 800 pre/post quality packets, 3,200 formal bulk packets and 192 diagnostic packets. Their SQL count is at most 12,600. Allow at most 900 additional observer SQL statements: **13,500 observer**, **1,000 startup**, **4,040 truth-helper** statements in total. Record actual categories and errors. No ANALYZE execution, hidden search SQL or counter reset is allowed.

Primary telemetry requires 3,200 backend/client sample bundles; diagnostic telemetry requires 1,792. Including admission/boundary samples, cap all bundles at **5,500**, proc-file read attempts at **44,000**, and affinity operations at **11,200**. These are simultaneous caps, including optional reads; no retry loops. Total measured telemetry wall time must stay ≤60 seconds and inside stage/global limits. All observation time and filesystem bytes are reported; a primary query timer excluding this work does not make it free.

The frozen allocation ceiling is **one x86_64 job, 3 hours, 4 CPUs, 32 GiB**. Nothing is allocated or submitted now. Work deadline is 10,200 seconds including finalization; host preflight/wrapper envelope is 480 seconds, leaving 120 seconds below Slurm wall. Reserve the last 600 work seconds for final proof/cleanup; start no new search after 9,600 seconds. Stage ceilings cannot borrow unused time:

| Stage | Maximum seconds |
| --- | ---: |
| Restore, identity, telemetry/resource qualification | 1,800 |
| Conformance and fresh quality | 2,400 |
| Epoch 0, including admission/priming/plans/diagnostic | 1,800 |
| Epoch 1, including admission/priming/plans/diagnostic | 1,800 |
| Final identity proof and cleanup | 600 |

The 8,400-second sum is below the global deadline; unused global headroom cannot add searches or extend a stage. No extra allocation, automatic resume or budget reset. An unknown submission outcome is preserved and reconciled before any further action; never submit again just because a binding is absent.

Measure source cluster footprints B0/B1 and file counts F0/F1 before copying. Require conservative free scratch/quota ≥`ceil(1.2*(B0+B1+2GiB))`, with F0+F1+10,000 free inodes. This is incremental space for new copies plus WAL/evidence reserve, beyond existing source occupancy. Require 3 GiB/10,000 inodes free in results/home. Evidence cap is 1 GiB. Both filesystem and conservative quota bounds must pass; unknown units/output fail closed. No new graph/build scratch is authorized. Keep two 128 MiB-buffer/max_connections=16 servers and the prior conservative 14.25 GiB configured memory bound within 32 GiB; record actual observed peak separately. No smaller data or changed settings workaround.

## 8. Frozen analysis and unchanged margins

The independent resampling unit remains the **200 already exposed vector groups**, not calls, repetitions or physical sessions. Condition inference on these particular server/backend epochs; two epochs do not estimate a population of sessions or machines. Use 10,000 group-bootstrap draws, seed 20261019, float64 arithmetic and linear percentile quantiles, retaining all matched rows. Use the same sampled group indices jointly across complete 200-group endpoints; for half-epoch endpoints resample the corresponding 100 groups with that fixed method/seed. Never pool historical B2d rows or select a passing subset. Prospective inference is specified here and is not executed during design freeze.

**Quality:** fresh mean recall of both cells ≥0.95 and the 95% lower paired recall-delta bound ≥−0.0025. Stable valid top10 IDs/distances, predicate membership, ties and exact-truth parity are required for every recorded search. Failure stops at quality with no formal calibration verdict.

**Physical A/A:** for each cell and epoch, pair r1 versus r0 on query/repetition. For each group, average the three outer differences and the three log ratios separately, then bootstrap group means. Require each 95% gap interval entirely within **[−0.10,+0.10] ms**, and each 95% log interval entirely within **[−log(1.02),+log(1.02)]**. Four cell/epoch contrasts give **eight required interval checks**. Creation-order orientation is also reported explicitly; relabeling cannot turn a failure into a pass.

**Temporal protection:** repeat these physical-session contrasts separately for the first and last 100 executed queries in each cell/epoch. The same equivalence limits apply: **16 additional required interval checks**. This prevents large opposing within-epoch half effects from qualifying through averaging.

**Retained stability:** for each cell/epoch/physical reader, evaluate retained2−retained1 and retained3−retained2, with the corresponding paired log ratios, over all 200 groups. Require all intervals inside the same unchanged equivalence limits: **32 additional interval checks**. No early retained row is discarded, and no extra warmup is added if this fails.

**All 56 timing intervals must pass.** This is one all-required qualification decision; there is no search among endpoints or individually selected success claim. The fixed 95% intervals are pointwise, not advertised as simultaneous 95% coverage. Their joint use is an intersection requirement; no multiplicity waiver permits a failed endpoint. Bootstrap precision/coverage and query clustering remain conditional approximations, with no claim that repeated calls add independent vectors. No power simulation or precision guarantee is made; failure to establish equivalence within this finite design stays inconclusive.

The original future economic limits are preserved but **not evaluated here**: conservative 99.375th-percentile upper treatment gap ≤−0.10 ms, upper log ratio ≤log(0.98) and both block gaps negative. Observed native-versus-partial means may be listed descriptively without a treatment benefit verdict. A later comparison must independently freeze quality/controls/economics, placement balance and final proof; no automatic treatment experiment follows calibration.

## 9. Decision gates and terminal outcomes

| Gate | Must establish | Failure / what passing informs |
| --- | --- | --- |
| F0 design freeze | Contract, explicit schedule, graph/input identities, counts, instrumentation and analysis pinned before code | Complete in this design-only task; not local/native readiness |
| L0 implementation readiness | Later isolated package, negative ownership/PID/namespace/affinity/tampering/count/order/stop/archive checks; all old inputs preserved | No Torch experiment until separately requested implementation passes |
| N0 environment/restoration | Source availability/clean state, whole independent copies, exact graph/data/module/catalog identity, cores, mandatory telemetry, quota/memory | `failed_qualification`, possibly zero searches; preserve evidence, no replacement graph |
| N1 conformance/quality | Fixed fixtures plus full fresh scoped quality and mapping parity | Native mismatch: failed qualification; valid quality failure: `closed_negative_quality` |
| N2 complete acquisition | Exact schedule/counts/identities/telemetry coverage; no replay or unexpected observer work | `incomplete` or `failed_qualification`; never analyze a selected complete subset as passing |
| N3 final integrity/cleanup | Data/graphs/module/source inventories, catalogs, all readers closed and both new servers stopped; raw locks/scheduler/protection receipts | Missing/failed final proof prevents any calibration pass |
| N4 independent trusted analysis | Reconstruct exact rows/gates with future trusted sealed source; all56 timing intervals pass | Complete failure: `calibration_inconclusive`; complete pass: `calibration_qualified_scoped`, allowing only later treatment-design review |

Record all failed/negative/incomplete outcomes and actual spent resources. Stop on identity, required-observation, stage/global/resource or output failure. Never loosen margins, change affinities/warmups/observer mode, add vectors/epochs, pick a faster PID, subtract A/A bias or reinterpret B2d after seeing results. A passing primary gate need not identify which component caused improvement; a diagnostic association cannot establish a server-only cause from the composite timer.

## 10. Required evidence for the later implementation

The future package must preserve this design, contract and complete schedule byte-for-byte; use a separately named package/campaign/reservation. Expected names are `torch-partial-calibration-v1` and `reviews-partial-calibration-v1-…`. Do not modify any B2d/B2e source, package, raw, receipts, reservation or submission binding. Require the exact completed B2d evidence as a dependency, not as reusable compute entitlement.

Persist admission/PID/server/CPU/namespace capability records; catalogs/GUCs/plans/cache counters; all search results/timers and charge reservations; conditioning/warmup/retained stage identity; observer/telemetry intervals and costs; initial/final source/data/graph/module proofs; quota/memory/peak/scheduler and cleanup records. Every exit gets a durable failure or completion record, raw-file lock and accounting. A local mock can establish implementation correctness only, not native resource or telemetry availability. Trusted local reconstruction must never execute downloaded code; retain strict discrete parity and 1e−12 float tolerance. Exact deployment commands come only with the later implemented and checked package.

## 11. Progress and revised critical path

- [x] Freeze unchanged graph/data/module/query/margin identities.
- [x] Freeze explicit two-epoch physical-session/CPU/order design and primary/diagnostic boundaries.
- [x] Freeze 16,242-search count, all ancillary/resource caps, 56 timing checks and terminal rules.
- [x] Save design provenance, schedule/accounting and roadmap/index tracking.
- [ ] User returns read-only source availability/hash/space output below.
- [ ] Later implementation and local correctness/preservation/seal checks, only when requested.
- [ ] Actual compute/core/telemetry qualification and bounded native calibration, only after a separate execution handoff.

**Critical path:** frozen B2f design → verify retained source availability and exact graphs → separately requested implementation/local readiness/seal → separate one-job handoff → native N0–N3 → independent N4 → only if qualified, freeze a later treatment comparison. A missing source or failed finite calibration retains original execution and closes this attempted scope without an automatic repeat.

## 12. What is needed from the user

Nothing further is needed to freeze this design. **Before an executable package can be prepared for this exact fixed-graph comparison, return the following read-only Torch inventory.** Run it in an existing Torch login shell and paste its output. It reads the three graph files for checksums and reports paths/space; it does not start PostgreSQL, change files, submit a job or run an experiment. No upload or allocation is required.

```bash
(
  set -euo pipefail
  b2f_source=/scratch/dar579/torch-reviews/partial-ann-v1.tu6x964d/partial-21048213.3xxjxm27

  ls -ld "$b2f_source" \
    "$b2f_source/native640/pgdata" \
    "$b2f_source/partial640/pgdata"

  for b2f_cell in native640 partial640; do
    if test -e "$b2f_source/$b2f_cell/pgdata/postmaster.pid"; then
      printf 'STOP: postmaster.pid exists for %s; preserve it and report this output.\n' "$b2f_cell"
      exit 1
    fi
    ls -l "$b2f_source/$b2f_cell/pgdata/PG_VERSION" \
      "$b2f_source/$b2f_cell/pgdata/global/pg_control"
  done

  sha256sum \
    "$b2f_source/native640/pgdata/base/16384/264013" \
    "$b2f_source/partial640/pgdata/base/16384/264013" \
    "$b2f_source/partial640/pgdata/base/16384/270339"

  df -Pk "$b2f_source" /home/dar579/torch-reviews-results
  myquota
)
```

The first two hashes must be `dbc14b0912d7e9ad9cd4ddcf806cac081412e66b1861de7ce3629fd81e23b393`; the third must be `b0300f40eb9917c158855d00fe0a8f36cb1c8aee958fb65b061e4db4d8606700`. Missing paths or mismatches are useful stopping evidence; do not reconstruct a graph or delete a PID file. These checks establish only preliminary availability/hash/space information. Full stopped-cluster consistency, copy safety and compute-node telemetry/core feasibility remain mandatory future gates.

After that evidence is reviewed, implementation/local checks require a separate request. No `submit`, `sbatch`, database startup or experimental command is ready now.

## 13. Preservation and sources

This freeze used existing source and returned evidence plus the primary PostgreSQL/Linux references linked above. It generated a prospective order manifest and checked its arithmetic/balance; it did not generate timings/outcomes, simulate performance, run tests or execute experiment modules. No code, prior raw/packages/receipts or scientific gates changed. All 2,241 prior pinned inputs remain unchanged. [Scope and preservation](../trials/torch-reviews-partial-ann-v1-settings-fix/b2f-design-2026-10-26/), [freeze receipt](../agent/docs/verification/partial-calibration-v1-design-freeze.json).
