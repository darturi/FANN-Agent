# Frozen design: zero-search snapshot lifetime and I/O attribution

October 28, 2026, America/New_York. `NEXT-STARTUP-ATTRIBUTION-01`, **A0**.
Proposed protocol: `startup-attribution.v1`.

**Status: design frozen before implementation.** No code changes, tests, new
measurements, database work, experiment, SSH or Torch allocation are performed or
released here. A1 implementation/local readiness and any later A2 handoff require
separate requests and gates. Full B2f remains held.

## 1. Question and finite scope

Can bounded observations of the **existing** loading/constructor/verification
path distinguish a cursor/decode transient, constructor validation bracket,
retained-snapshot context or verification/pool/I/O overlap well enough to select
one future remedy design? The study observes one unchanged path; it neither tests
an optimization nor estimates causal savings, recall, A/A equivalence or search
performance. Exact individual allocation/file attribution may remain unresolved.

One later allocation is a **proposed maximum**, not permission to submit:
**one hour, four physical CPUs, 32 GiB, zero ANN/exact searches**. Keep one full
snapshot scan, four complete ID/vote/float32-bit verification scans, 200 admission-
only requests, ten reader admissions/maxsix live, two private working servers and
maxeight live SQL connections. Preserve both creation orders and five-second
holds. Add no full scan, plan/EXPLAIN, fit, confirmation or provider call.

All three failed calibration attempts and both completed resource jobs remain
spent. Preserve their packages, raw, seals, bindings and reservations. There is no
automatic retry, additional block, alternative hook/remedy, larger request or
calibration launch.

Prospective implementation paths, **not created in A0**:

- `agent/experiments/startup-attribution-v1`.
- `trials/torch-reviews-startup-attribution-v1`.
- Torch package `torch-startup-attribution-v1`; controller `sa_control.py`.
- Campaign prefix `reviews-startup-attribution-v1-`.

## 2. Frozen inputs and semantic invariants

Baseline: the actual completed identity-stream package, manifest
`26a7d66b67137e77d5208d7b851b19d980a8a64060defc25cbe418db17190354`;
archive SHA256
`5fa2e92e7b87a4a8fff0ac7cb897e9f116ad8ecf07c4675e185c51f17ffb8689`.
The returned stream archive is
`63ff9b4800faab0a0ece6955ccabfb9c512548a35909cbca0e9b175a73ab3fef`;
the original resource archive is
`312bf5c02959a1e90514f6ec556914303095eb30c2f87acd9b182010a28320e7`.
The machine contract pins 246 actual source/recipe files and all runtime/graph/
module/profile/registry/target/query/source-contract identities.

Keep 247,286 rows, 768 dimensions, all original decoded numeric values, typed ID
ordering, row/list/matrix/maps/metadata and consumer behavior. The exact snapshot
identity remains
`54282be380f20bfab05a44e6260e116435aecf5a289a258ae8164a23c187b303`;
eligibility remains
`eed0dc123868ee61c2ffbadbb066cd36db9e813ce8a7829ed18658f04b6b44d2`.
Retain the already-qualified per-row original-canonical identity helper unchanged,
including its buffer/call/byte caps and scoped digest restoration.

Original producer and constructor functions/code objects execute unchanged. No
source rewrite, AST-generated replacement, alternate constructor, dtype/layout,
cursor/batch/SQL/transaction change, validation shortcut or data/check omission.
Ten readers continue sharing one snapshot; **do not release snapshot roots early**
or force collection as an intervention. Preserve exact original before/after
integrity and source/graph/module checks, including their order and I/O.

Observation adds explicit harness scopes and version-pinned driver wrappers. This
is recorded effective behavior, not implied by an unchanged image hash. A1 must
record every binding, original callable, wrapper/source hash and actual Python,
Psycopg, libpq, Arrow and NumPy identity. Package/library source provenance comes
from the pinned image, not an unverified host installation or dependency upgrade.
Private driver-hook availability is a readiness condition, not assumed native
success.

## 3. Memory checkpoints and original-code observation

The authoritative [checkpoint catalog](../trials/torch-reviews-startup-attribution-v1-design/CHECKPOINTS.json)
freezes **102 required checkpoints**, at most **128 records**, each at most 16 KiB.
Successful acquisition requires every required semantic checkpoint exactly once.
Failure prefixes are preserved without fabricating missing checkpoints.

| Group | Required boundaries | What the bracket can inform |
| --- | --- | --- |
| Host | Sampler readiness; original bundle/image verification, resource preflight and protected proofs before/after; container launch/exit; final protection and sampler stop | Input/proof I/O context, host/container attribution and complete sampler coverage |
| Restore/copy | Original retained inventory and graph checks; each clone and its existing source/destination inventories; postcopy inventory/working graphs; each server start | Logical file-role work and charged-memory context without another content scan |
| Snapshot S00–S04 | Producer entry; original execute before/after; decoded rows before tracked cursor close; after close | Full client result versus original row accumulation, and residence across cursor close |
| Constructor S05–S09 | Original constructor entry; matrix before/ready; finite check complete; norm check complete; metadata ready before identity | Retained matrix metadata and validation brackets; short C temporaries may remain unobserved |
| Snapshot S10–S13 | Existing identity start/end; constructor return; validated publication boundary | Known encoding bracket, exact identity and restored binding/monitor state |
| Each verification pass | Full `verify_data` before/after and existing FETCH-return ordinals **1, 1,237, 2,473** | Transaction/full-call/fetch/decode distinctions and original verification/pool context; no added FETCH |
| Reader epochs/finalization | Each creation/hold/close boundary; final reader close; original per-copy catalog/graph proof and server stop; stopped-source/graph/restoration checks | Confirm shared snapshot remains reachable through final integrity, without treating close as release |

### Selected mechanism

Use CPython 3.12 `sys.monitoring`, **tool ID 4**, with **LINE events local only to
the two original code objects**: `NativeBackend.snapshot` and `Snapshot.__init__`.
The frozen source mapping is backend lines 970/982/983/992 and constructor lines
23/54/55/57/61/89, verified by source hash, exact function/AST statement and line table.
Line numbers alone are insufficient. A1 must prove actual callback/frame behavior.

Handle/coalesce each semantic checkpoint once. Every visited LINE location,
selected or not, returns `DISABLE` after its bounded handling, preventing a
per-row list-comprehension trace. Cap all LINE callbacks at **512**, including the
bounded preflight. Enable no global events, descendant-code/per-element tracing,
`sys.settrace`, profile hooks or `restart_events`. This mechanism is source-
feasible, not locally or natively qualified in A0.
[CPython monitoring interface](https://docs.python.org/3.12/library/sys.monitoring.html),
[PEP 669](https://peps.python.org/pep-0669/).

S03/S04 use a scoped wrapper around the **one tracked original snapshot cursor's**
existing `_close` entry/return; they add no close or fetch. Other original cursor
closures delegate normally. This separates the end of row decoding from cursor
resource release without inserting code into the producer. The existing identity
phase seam supplies S10/S11; explicit harness scopes supply repeated-operation
boundaries. There is no source-line instrumentation during the four row loops.

A checkpoint may read a validated frame only long enough to obtain O(1) scalar
metadata: row count, matrix shape/dtype/nbytes and a bounded shared-alias proof
across at most ten reader objects. Never retain frames, locals dictionaries,
rows, matrices or fetch pages; never render/serialize values or traverse vectors.
Callback/frame mismatch aborts observation, rather than switching to a different
instrumentation strategy.

Before publication, clear both local masks and any owned global mask, unregister
the callback, **then** free tool ID 4, and prove no active monitoring remains.
Freeing the identifier alone does not clear events/callbacks. Existing digest and
original producer/constructor bindings must also be intact. Driver accounting
remains explicitly active only through owned connection teardown, then restores
before final locks. Tool occupancy, a pre-existing tracer/profile/monitor, source
mismatch or concurrent Python snapshot activity stops capability qualification.

## 4. Checkpoint fields, overhead and limitations

Each record brackets its own collection with monotonic start/end times and records
role/sequence, PID/starttime and mapped cgroup identity. Required data:

- Job, step-user and task scopes: current/peak/events plus anonymous/file/kernel
  components. The original host sampler still covers all visible ancestors.
- Process RSS/HWM, fault and I/O counters; those are distinct from job charge and
  logical file bytes.
- Original Arrow default-pool live bytes/backend and nullable pool high-water.
  The pool is not replaced, reset or trimmed. A missing live-byte capability stops
  before restore; the default pool does not cover every NumPy/driver/native
  allocation. Actual image methods/provenance must be qualified in A1.
- Optional `smaps_rollup` and Python allocated-block count, with explicit missing/
  unsupported reasons. Block counts are not bytes; no GC is invoked to stabilize
  them. [Python allocated-block semantics](https://docs.python.org/3.12/library/sys.html#sys.getallocatedblocks).
- O(1) source/matrix/alias metadata where available, plus cumulative work and
  observation ledgers. No password, parameter, query/vector or raw row values.

Samples are sequential read windows, not atomic allocation measurements. Process,
pool and cgroup quantities are not added/subtracted to manufacture a saving.
Checkpoint overhead and every kernel peak remain included in real resource use.
High-water counters may mask a later smaller transient; a temporary between
checkpoints may be missed. Neither null nor unsupported means zero.

| Observation limit | Frozen maximum |
| --- | ---: |
| Required / maximum checkpoints | 102 / 128 |
| LINE callbacks / all hook entry-exit callbacks | 512 / 65,536 |
| Added diagnostic CPU / observer wall | 15 s / 30 s |
| One synchronous checkpoint | 1 s |
| Added read/stat operations / read bytes | 8,192 / 64 MiB |
| One read file | 64 KiB |
| Diagnostic raw / buffered pending / failure reserve | 16 MiB / 256 KiB / 128 KiB |
| Checkpoint / command / role / summary record | 16 KiB / 768 B / 1 KiB / 256 KiB |
| Operation-role records / metadata entries | 256 / 50,000 |
| Sampler + added diagnostic CPU combined | 60 s |
| Sampler + added reads combined | 500,000 operations / 512 MiB |

Original sampler period 1 s, maximum gap 5 s, maximum 3,600 samples/256 MiB raw
and whole-run 512 MiB evidence cap stay unchanged. Added observations fit inside
combined limits; no extra resource allowance is granted. Added preflight uses at
most two tiny literal monitoring functions/16 events, no SQL or data arrays, and
at most one added CPU second; existing encoder preflight limits remain. It cannot
substitute for A1 actual-constructor integration.

Observer overhead includes bookkeeping, probes, logging, installation/restoration
and read/stat work. It excludes the unchanged delegated operation duration only
for that **overhead counter**, with nested observers charged once. Reported driver
intervals include delegation; absolute stage/runtime/job deadlines charge all work.
No observed time or memory is subtracted to claim baseline performance.

## 5. Internal fetch and driver-command accounting

Keep the original API counters and caps: startup 500, observer 100, truth-helper 0.
The prior 171+56 counts retain that meaning. A separate ledger records observed
**Python-driver command dispatches**, not network packets, authentication/startup
exchanges, all individual protocol frames or database-internal execution.

The [hook catalog](../trials/torch-reviews-startup-attribution-v1-design/DRIVER-HOOKS.json)
freezes nine version-specific roles: internal connection commands/deallocation,
ordinary/prepared cursor sends/preparation, server declaration/description/fetch,
and snapshot-cursor close. Wrappers preserve call arguments, results, exceptions
and generator `yield/send/throw/close/return`; no retry or fetch is introduced.
Actual driver source/signatures/paths must match the pinned Psycopg 3.3.6 image and
be sealed by A1. [Driver command/deallocation paths](https://raw.githubusercontent.com/psycopg/psycopg/3.3.6/psycopg/psycopg/_connection_base.py),
[cursor send paths](https://raw.githubusercontent.com/psycopg/psycopg/3.3.6/psycopg/psycopg/_cursor_base.py).

API attempts receive capability tokens. Exactly one ordinary-or-prepared execution
link completes each API call; four allowed data-query API calls map to actual
DECLARE dispatches, **not an extra SELECT plus DECLARE**. Preparation/description
are separate protocol requests. Helpers/deallocation fallbacks reference their
lower dispatch instead of double counting it. Reject pipeline mode or any
uncovered command route before release.

Only the two original owned sockets/datadirs, two admins and ten readers are
admitted: 12 total connections/maxeight live. A bounded pending-connect token
covers connection initialization; there is no general unknown-connection bypass.
Before dispatch, validate the active API or original verification/cleanup scope,
exact template/generated name and remaining caps. FETCH uses the original fixed
cursor, size 100 and pass ordinal; BEGIN/COMMIT belong to four original nonnested
verification transactions. ROLLBACK/existence probes are failure cleanup only;
prepared-name cleanup is restricted to names owned by the recorded registry.
Unknown SQL, nested/savepoint/two-phase transactions, pipeline, COPY, streaming
query variants, distance/search and EXPLAIN routes reject before dispatch.

Completed acquisition requires, per verification pass: **2,473 fetches**, **2,472
full 100-row pages plus one 86-row page**, 247,286 returned rows and no extra
exhaustion fetch. Across four passes: **9,892 fetches / 989,144 rows**. Require four
BEGIN, four COMMIT, four named CLOSE, four portal descriptions, zero ROLLBACK/
existence probes/pending/unknown/blocked operations. Record actual ordinary versus
prepared execution and cleanup; do not infer counts solely from this formula.
[Original iteration and fetch behavior](https://raw.githubusercontent.com/psycopg/psycopg/3.3.6/psycopg/psycopg/_server_cursor.py),
[default/fetch/declaration implementation](https://raw.githubusercontent.com/psycopg/psycopg/3.3.6/psycopg/psycopg/_server_cursor_base.py).

| Dispatch/request family | Hard ceiling |
| --- | ---: |
| API executions, including four DECLAREs | 600 |
| Verification FETCH | 9,892 |
| Verification CLOSE / cursor-existence cleanup probe | 4 / 4 |
| Transaction controls, including failed-prefix cleanup | 32 |
| SQL prepared deallocation | 600 |
| Protocol preparation / portal description / prepared Close | 600 / 4 / 600 |
| Sum of family ceilings | 12,336 |
| Combined envelope | 13,000; work 12,936 + 64 reserved cleanup |

Family ceilings are not entitlements to add commands: successful exact sequence
and scope checks remain mandatory. Prepared-cleanup SQL and protocol Close are
classified without counting one operation twice. No database queries are added
for telemetry. Log unique reserved attempt IDs and matched completion/error
intervals, normalized family/API/pass IDs and counters without raw parameters.
Bounded buffering avoids per-fetch fsync; success requires a complete flush and
no pending attempt. A hard-killed prefix can undercount pending work and cannot
qualify; preserve it rather than inventing exact call accounting.

## 6. Logical I/O role ledger

Record original bundle/image/protected proofs, retained inventories, graph hashes,
independent copies/source and destination inventories, initial/final data checks,
snapshot load, stopped proofs and final host protection. Use existing return
metadata/manifests and bounded stat metadata; add no content read or hash pass.
Counts from the deepest role own logical bytes; parent operation summaries link
to them without duplicate addition.

Where a function supplies only hashes or a byte quantity is unavailable, record
that quantity as unknown with reason and retain operation boundaries/counts.
Completeness means every required role is covered and every byte field is honestly
classified, **not** that physical file I/O/page ownership has been measured.
Do not infer cache allocation from file size, sum repeated cached reads as charge,
or treat temporal file-charge coincidence as per-file causation.

## 7. Resource and cleanup contract

Keep the original Slurm/host/runtime limits: one hour/four physical CPUs/32 GiB,
3,000-second runtime including **600 seconds cleanup reserve**, 1,500-second
restore, 600-second snapshot/admission, 120 seconds per epoch, 600-second final
cleanup; host pre/post at most 240 seconds each, supervisor ceiling 3,030 seconds
and outer margin 120 seconds. They are ceilings, not additive entitlements.

Use an absolute host monotonic deadline inside the 3,600-second wall limit. Clamp
native waits to the smaller of the supervisor ceiling and remaining wall time
minus host-post and outer reserves; clamp runtime/stage budgets likewise while
preserving cleanup. Observation never extends a deadline or borrows a cleanup
reserve for more acquisition. All observer/logging work remains charged.

Handle SIGALRM/SIGTERM/SIGUSR1/SIGINT and BaseException through `finally`. Restore
monitoring before publication or error reporting; retain only the declared
bounded driver accounting through original rollback/close, then restore all
original methods/bindings before final guest/host locks. Do not disable observation
and continue toward a positive verdict after a cap/health error. Reserve the final
64 driver operations and 128 KiB minimal failure evidence inside existing totals;
if full telemetry fails, attempt original validated cleanup and preserve both the
primary failure and cleanup errors. An observer error at a mandatory close or
rollback must not suppress the saved original teardown: record invalidity,
delegate cleanup once through the reserved minimal lane without heavy probes,
then preserve both errors. If accounting is incomplete, success is impossible;
acquisition does not resume. No new query/reconnection is a cleanup remedy.

Close all readers/admins, stop only the two owned working servers, prove stopped
control/graph state and absence of live PID markers, compare protected inputs,
flush evidence and complete independent guest/host locks. Never start or modify
retained clusters, delete an earlier binding/reservation or remove failed raw.
Missing cleanup/source proof closes the job invalid/incomplete. SIGKILL cannot
establish success. Cleanup failure never triggers automatic submission.

The separate memory gate is unchanged:

`largest visible finite-ancestor kernel peak + 2 GiB reserve + 2 GiB workspace`

must fit the smallest observed finite limit capped at 32 GiB, with no positive
max/OOM/kill/failcnt delta, complete mapping and coverage. At 32 GiB this requires
peak at most 28 GiB. No cache subtraction, counter reset, forced GC, allocator trim,
Arrow pool release, cache eviction or resource/margin increase. An informative
diagnostic may still be resource-margin inconclusive; even a scoped margin pass
cannot release full query-workload memory or full B2f.

## 8. Decision gates and interpretation

| Gate | Required evidence | Failure/action |
| --- | --- | --- |
| A0 design freeze | This document, machine contract/catalog/source/evidence pins and recorded hashes precede code | Complete for design only; no readiness/native claim |
| A1 local readiness | Actual original producer/constructor and real CPython monitoring; bounded original fixtures; actual driver-generator routes with synthetic transport, prepared/unprepared/deallocation and exception/throw/close cases; complete accounting/checkpoint/overhead/replay/archive/cleanup negatives | Do not package/release an unqualified alternative. Preserve failures and amend design explicitly if mechanism cannot comply |
| A2.0 capability before restore | Actual pinned image/library/function/source/signature identity, tool/frame/monitor selfcheck, source/host/sampler/resource prerequisites | Capability stop; no fallback, extra SQL or costly restore after a known mismatch |
| A2.1 semantic/integrity | Original snapshot/eligibility, stream limits, zero searches, original counts/data/graph/module/SQL/transactions, both epochs and shared ownership | Invalid/incomplete; preserve prefix and clean up |
| A2.2 observation/accounting | All 102 checkpoints, ordered source mapping, actual dispatch/page/row reconciliation, no pending/unknown command, role ledger and all overhead/health/raw/CPU/read/time caps | Invalid/incomplete; no selective subset or imputed zeros |
| A2.3 cleanup and independent replay | Original close/stop/source proofs, exact hook restoration, guest/host locks, safe archive/binding/seal and fresh trusted reconstruction | No diagnostic/resource pass without complete proof |
| A3 interpretation | All preceding gates, prespecified family evidence below and uncertainty retained | Informative for one later design, or valid unresolved closure; no remedy/adoption/job automatically |

Use a **256 MiB descriptive triage threshold**, distinct from every scientific or
resource margin. Report checkpoint before/after current and high-water changes,
not causal allocation sizes. Prespecified evidence families:

- **Cursor/decode transient:** execute-to-decoding/close brackets, original counts
  and at least one material observed process/anonymous excursion or decrease.
- **Constructor/validation bracket:** matrix metadata plus original statement
  ordering and material RSS/HWM/pool observation. Older HWM or a missed C temporary
  can leave this unresolved; absence of a new peak is not proof of no allocation.
- **Retained context:** same bounded snapshot aliases/row/matrix metadata at
  publication, both holds and final reader close; describe measured residence and
  stability within 256 MiB. Do not call that residence live object byte size.
- **Verification/pool overlap:** all four exact row/fetch ledgers, full-call/
  transaction boundaries and material default-pool/process variation in its
  source/lifetime context. Pool coverage does not include all native allocations.
- **File-charge operation coincidence:** material observed file charge change
  bracketed by a known original I/O role and its logical work. No file-owner,
  reclaimability or physical-I/O causation claim follows.

An informative result requires a **new discriminating bracket fact**, not merely
reconfirmation of shared retention, the capped peak or reconciliation of fetch
counts. Cursor evidence must separate result receipt/decoding or original close;
constructor evidence must isolate matrix-before/ready or validation boundaries;
pool evidence must show material pool variation in an exact pass; file-role
evidence requires material file-charge change with both process-RSS and anonymous
changes below 256 MiB. The machine contract freezes these consistency conditions.
Retained-context evidence is a control and cannot qualify by itself.

Complete, healthy data with at least one such new supported family may close as
`attribution_complete_informative` for a future remedy design. Otherwise close as
`attribution_complete_unresolved`. Capability/missing-proof/overhead/cleanup
failure is `capability_stop_or_invalid_incomplete`. Preserve resource verdict
separately. Every outcome spends the one later allocation if submitted; no repeat,
extra sampling, changed threshold, broad allocation tracing or remedy follows.

## 9. Later local checks and revised critical path

No checks are executed in A0. A1 must retain applicable prior 155-check coverage
categories and add actual interpreter/constructor/driver control-flow tests:

- Exact original byte/hash/value/matrix/metadata/query-validation behavior and
  shared snapshot lifetime with monitoring active/inactive, including 3.12
  inlined-comprehension callback bounds, frame/source mismatch, duplicate/missing
  checkpoint and tool occupancy/teardown checks.
- Actual driver source/signatures and ordinary/prepared/declaration/fetch/
  deallocation/transaction routes with bounded synthetic transport; prove each
  lower operation is delegated once and no hidden route escapes the ledger.
- Actual entry/host/runtime failure, generator throw/close, signals/deadlines,
  budget exhaustion and restoration/cleanup; complete synthetic raw reconstruction
  plus semantic tamper and archive/once-only failures.
- Bounded fixtures only: at most 64 rows × 768 dimensions and 4 MiB canonical
  oracle per dataset, no full-size vector generation, DB experiment, benchmark,
  scientific bootstrap/fit or protected query access. Fixture proofs cannot
  establish full-size memory/overhead or actual runtime support.
- Source and sealed execution of relevant local checks; exact science/vendor/
  helper/source preservation, manifest/archive parity and concrete release review
  before commands. Actual counts/results must be reported, not assumed from 155.

**Critical path:** A0 frozen → separately requested A1 implementation/local
readiness → separately released one A2 zero-search diagnostic → trusted A3
informative/unresolved decision → separate evidence-backed remedy design and
qualification → possible full-workload memory/release review and full B2f gates.

**No Torch commands are needed or released by A0.** Original execution is retained,
B2d remains measurement-inconclusive and B1c remains deferred.

[Machine design, checkpoint/driver catalogs and source pins](../trials/torch-reviews-startup-attribution-v1-design/).
[Design receipt](../agent/docs/verification/startup-attribution-v1-design.json).
[Preceding read-only audit](fannagent-startup-working-set-audit-v1-2026-10-28.md).
[Roadmap](fannagent-performance-research-roadmap-2026-10-22.md).
