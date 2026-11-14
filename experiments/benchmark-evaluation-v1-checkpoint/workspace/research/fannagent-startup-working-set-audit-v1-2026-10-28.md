# Snapshot loading, retention and verification I/O audit

October 28, 2026, America/New_York. `NEXT-STARTUP-MEMORY-02`, W0–W2.

**Decision:** the read-only audit is complete. **Do not launch a cursor-only,
smaller-batch or cleanup-only correction.** Existing evidence does not establish
that any one would satisfy the unchanged 28 GiB/no-limit-event gate. Proceed to a
**design-only freeze for one bounded, zero-search lifetime/I/O attribution study**,
with explicit driver-fetch accounting, before choosing another implementation.
No implementation, test, experiment, allocation or native action is performed or
released by this audit. Full B2f calibration remains held.

## Evidence and interpretation

The audit pins 246 source/recipe files, including all 116 previous consumer-audit
pins and the actual sealed producer/constructor/runtime/verification/ownership
paths. This is an inventory and targeted control-flow review, not a claim that
every inventoried function executes. Both resource campaigns and their existing
trusted verification results remain unchanged:

- Original startup: job `21171789_0`, manifest
  `4212507e81abc053aa5045e09a8cb624b789ed0bad4e1e8d1bf69f82f31484d9`.
- Identity stream: job `21224521_0`, manifest
  `26a7d66b67137e77d5208d7b851b19d980a8a64060defc25cbe418db17190354`.

All 3,961 prior/source/release/raw/analysis inputs are preserved. Trace processing
uses existing JSON/JSONL and static source/AST/size metadata only; it imports no
experiment or database implementation and does not decode dataset/query vectors.
No new samples, tests, fits or scientific measurements are acquired. Official
library/OS documentation supplies interface semantics; it cannot identify which
allocation or file caused a recorded memory charge.

## Snapshot loading and retained representations

The actual chain is `pc_runtime` → `sr_interface.Factory` → owned reader/inherited
Torch backend → frozen `NativeBackend.snapshot` → frozen `Snapshot.__init__`.
Neither the Torch adapter nor the reference/profile wrappers replace the producer.
The current identity-stream scope changes hashing only.

| Representation | Actual source lifetime | Consequence |
| --- | --- | --- |
| Default database cursor result | Unnamed cursor executes the ordered snapshot query, then the list comprehension decodes every row; cursor context exits before `Snapshot(...)` | The full client result overlaps row accumulation. A named cursor could target this transient, but changes portal/transaction/fetch behavior |
| Decoded rows/vector lists | All original IDs, Python numeric values and metadata are accumulated before construction, then retained in `snapshot.rows` | This is persistent storage, not merely the cursor buffer; float32 reconstruction would change original values/identity and consumer semantics |
| Sorted rows and vector-reference list | Constructor sorts an outer list and forms a list of vector references for `np.asarray` | These are reference containers, not another recursive copy of all Python vector values |
| Float32 matrix and validation work | Matrix plus finite/norm checks are constructed before identity hashing; matrix remains in `LoadedDataset` | Dense matrix payload is 759,662,592 bytes / 0.707491 GiB; actual temporaries and allocator residence are unmeasured |
| IDs/maps/fields/masked metadata | Constructor validates/builds them; snapshot/data retain them | Required for membership, query validation, typed IDs and exact logical fields |
| Identity encoding | Current helper streams original canonical components with a 64 KiB pending buffer | Actual identity already passes; this bound does not bound rows/matrix, allocator, cursor or job charge |
| Reader ownership | Factory and all ten backend objects reference the same snapshot | There are no ten separately constructed snapshots to eliminate |
| Finalization | `Factory.close` closes readers; inherited `backend.close` clears connection/binding/policies, but does not clear `_snapshot`; factory retains its snapshot and reader list | Closing connections does not release the live snapshot before final verification. Forced GC cannot collect still-reachable objects |

The default Psycopg result is stored on the client; named cursors fetch partial
results and retain server portal state. Python iteration alone does not change
that storage boundary. [Psycopg cursor semantics](https://www.psycopg.org/psycopg3/docs/advanced/cursors.html).

The original rows have real validator, sampling/export, broker, workload and
identity consumers. Retaining only the float32 matrix, changing list/array APIs,
or lazily reconstructing rows requires a separate exact-value/serialization/
consumer contract. The current rows/matrix are not safely removable by inspection
alone. Conversely, retaining a cursor variable after context exit does not prove
its former result buffer is still live. Freed objects, allocator residence and
resident process memory are distinct; no per-object byte attribution is available.

## Verification is already streamed, but its work is under-described

`pc_restore.verify_data` already uses a named cursor inside a transaction. It reads
the same complete ordered database result and the Parquet source in 512-record
batches, explicitly disabling Arrow read threads. Every row checks ID/votes and
both vectors' exact float32 bits. All four complete scans remain mandatory.

Arrow 22's constructor defaults do not enable memory mapping or pre-buffering;
its batch-size argument limits yielded records, not every internal allocation or
OS cache page. This source therefore does not support a claim that verification
holds only 512 records' worth of total memory, nor a diagnosis of accidental
whole-table `read_table()` use. Internal decode buffers/allocator retention are
not separately observed. [Pinned Arrow 22 source](https://github.com/apache/arrow/blob/apache-arrow-22.0.0/python/pyarrow/parquet/core.py).

The recorded transaction-enter/exit events enclose complete iteration and bit
comparison. The `execute()` records enclose only declaration/execution through the
wrapper, not subsequent named-cursor fetching and client work:

| Verification transaction | Original run | Stream run |
| --- | ---: | ---: |
| Initial native copy | 95.519 s | 81.960 s |
| Initial partial copy | 91.912 s | 79.684 s |
| Final native copy | 92.296 s | 83.969 s |
| Final partial copy | 90.853 s | 88.162 s |
| Four transaction brackets | 370.580 s | 333.775 s |
| Four logged `execute()` intervals combined | 0.033684 s | 0.034982 s |

Those brackets occupy 55.28% / 56.60% of recorded runtime respectively. They are
not exact whole-function timers: final source-exhaustion/count checks also occur
after transaction exit. These separate single runs do not establish a causal
speedup. The brackets include server fetch, transfer, decoding and comparison;
they do not separate those costs or measure physical I/O alone.

**Accounting correction:** the previously reported 171 startup + 56 observer SQL
counts are **227 charged API-level statement calls**, not all SQL commands or
protocol messages. `pc_trace.Cursor.__iter__` returns the raw driver's iterator,
and its transaction context delegates to the raw connection. Driver-internal
fetch/close/transaction commands do not traverse `Trace.call` or its counter and
API allowlist. This is an observability/accounting gap, not evidence of new search
SQL or a positive resource result.

Psycopg 3.3.6 sets default server-cursor iteration size to 100; iteration calls its
internal fetch generator, which emits fetch commands directly. With unchanged
defaults and 247,286 rows, the source-implied model is 2,473 fetches per pass, or
9,892 over four passes, excluding declaration/close/transaction/describe activity.
**This is a conditional source calculation, not a measured wire-command count.**
The old counters retain their original API meaning; any future design must add a
separate finite driver-command ledger and explicit semantics instead of silently
relaxing or reinterpreting earlier caps.
[Pinned server-cursor iteration](https://raw.githubusercontent.com/psycopg/psycopg/3.3.6/psycopg/psycopg/_server_cursor.py),
[pinned fetch/default implementation](https://github.com/psycopg/psycopg/blob/3.3.6/psycopg/psycopg/_server_cursor_base.py).

## Verification I/O and memory overlap

The executed source hashes the original bundle/image and protected evidence,
inventories retained clusters, independently copies both clusters, hashes source
and destination inventories, verifies graphs, scans both databases against the
Parquet source, loads the snapshot, then repeats data/graph/source proofs during
finalization and protected-source proofs on the host. Hash implementations mostly
stream bounded chunks. Small hash buffers do not bound the filesystem working set.

Captured copied cluster sizes are 2,124,958,446 and 2,478,697,398 bytes, with distinct
source/destination inodes. Local stat metadata records a 762,046,870-byte Parquet
file and 294,445,056-byte image. The existing bundle log records 7,297 verified
files / about 1,209.5 MiB read. These are file/logical-work sizes, **not additive
cgroup charge, measured physical I/O or a per-file cache map**. Repeated reads may
reuse pages; copies use independent files. Prior evidence hashing and database
access also occur, so the file counter cannot be assigned to Parquet or graphs
alone.

The new trace further narrows the overlap:

- Before snapshot construction, restore/verification already reaches about
  23.488 GiB total job charge with a runtime RSS below 0.84 GiB.
- During reader holds, the job remains about 31.306 GiB while runtime RSS is about
  10.602 GiB. One frame has about 10.658 GiB anonymous and 20.572 GiB file charge.
  No full-result cursor is intentionally retained by the producer at this point.
- The pre-hash sample near the limit contains about 9.943 GiB anonymous and
  21.984 GiB file charge. There are 114 strictly pre-hash max events; 76 cross the
  load/hash boundary.
- Of the 69 finalization-label events, 68 cross the phase/first-final-verification
  boundary; **one is wholly bracketed inside the first final native-copy
  verification transaction**. Exact attribution of those 68 remains unresolved.
- Identical initial verification code runs below 0.84 GiB runtime RSS, whereas
  final verification reaches about 11.323 GiB while the snapshot is still live.
  This establishes different lifetime context, not an 11 GiB verification buffer.

The cgroup total includes descendants, anonymous memory and filesystem-cache
charge; the file category includes tmpfs/shared-memory cache. Sequential component
reads and separate process highs must not be added/subtracted or treated as atomic
object accounting. Neither page ownership nor reclaimability is established by
these traces. [Linux cgroup v2 documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html#memory).

## Remedy review and decision

| Proposed action | Audit result | Disposition |
| --- | --- | --- |
| Named snapshot cursor alone | Can target a full client result, but leaves original retained rows/matrix and final verification overlap | Source-feasible candidate; **no-go as a sufficient next correction** without attribution and separate transaction/identity/fetch qualification |
| Smaller verification batch / disable threads | Current implementation already uses 512 and disabled read threads; no internal allocation/pool attribution | No blind tuning or rerun |
| Close readers / force GC | Readers already close; live snapshot references remain. Releasing those roots needs a terminal-lifecycle contract and does not solve pre-hash pressure by itself | No cleanup-only remedy or forced collection |
| Compact/lazy exact-value row representation | Could address persistent representation, but changes actual consumers, serializer/API/lifetime behavior | Broader separate semantic design; do not substitute float32 values or claim guaranteed savings |
| Skip/reorder verification or remove hashes | Alters required before/after integrity evidence or conditioning | Excluded as a shortcut |
| Drop cache, allocator trim, raise memory or weaken margins | Changes measured conditions/question; no proof of sufficient saving | Not selected; frozen no-subtraction/no-event gate remains |
| Bounded lifetime/I/O attribution | Directly addresses missing producer/constructor/verification subphases, allocator context and driver-command accounting | **GO to design-only freeze; no implementation or allocation now** |

No candidate currently has enough evidence for a guaranteed event-free peak at or
below 28 GiB. This is a limited decision about the available evidence, not a proof
that the workload cannot fit in 32 GiB or that a broader remedy cannot help.

## Recommended next step and decision gates

Next: **NEXT-STARTUP-ATTRIBUTION-01 / A0**, freeze a bounded zero-search observation
design before code. It must specify:

1. Producer checkpoints around result receipt, row decoding/cursor close,
   constructor/matrix/validation, existing identity stream and publication, plus
   host verification/copy and each final data/graph/source proof. Choose a scoped,
   locally testable mechanism that preserves the original producer/constructor,
   values, query/transaction semantics and error/cleanup behavior.
2. Explicit API-call versus driver-command/fetch/row and file-role byte ledgers.
   Preserve existing API charges; derive separate finite internal-command caps
   from the pinned driver rather than pretending the old 100-observer cap covers
   thousands of internal fetches. Raw row/vector/credential values are unnecessary.
3. Bounded cgroup/process and available allocator/Arrow-pool observations at those
   boundaries, with explicit overhead/health/provenance/byte/read/time caps. No
   per-element object walk, full allocation trace, forced GC or cache eviction.
4. No new ANN/exact searches, model/provider work or extra full data scans. Keep
   original data/graphs/module/policies/identity/integrity/creation orders and the
   same resource-margin rule. Do not grant a larger allocation by implication.
5. Interpretability/futility gates: state which observations would distinguish a
   cursor transient, constructor temporary, persistent representation or
   verification/pool/I/O overlap. If bounded instrumentation cannot distinguish a
   required fact, stop at design review. Any later native observation is diagnostic,
   not another automatic performance qualifier or retry of the spent M3 campaign.

Critical path: **W0/W1/W2 audit complete → A0 separate attribution design freeze →
separately requested implementation/thorough local readiness → only then a
separately released bounded zero-search acquisition → choose/freeze one evidence-
backed remedy → correctness/resource qualification → possible full-workload memory
and B2f release review.** No new job is released now. Original execution, B2d's
inconclusive performance verdict and deferred B1c remain unchanged.

**No Torch commands are needed.**

[Source pins/function ranges and existing-trace derivations](../trials/torch-reviews-startup-working-set-audit-v1/).
[Audit receipt](../agent/docs/verification/startup-working-set-audit-v1.json).
[Latest verified resource return](fannagent-startup-resource-stream-v1-postrun-2026-10-28.md).
[Roadmap](fannagent-performance-research-roadmap-2026-10-22.md).
