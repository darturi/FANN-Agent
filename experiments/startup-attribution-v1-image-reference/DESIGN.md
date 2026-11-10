# Frozen prospective design: bounded snapshot identity hashing

October 28, 2026, America/New_York. Parent: `NEXT-STARTUP-MEMORY-01`, M1.
Proposed protocol: `startup-resource.stream.v1`.
Status: **design frozen before implementation; implementation and native gates unassessed**.

## 1. Question, scope and authorization boundary

Can a scoped change to snapshot identity encoding preserve every original identity,
row/value and validation outcome while allowing startup to satisfy the unchanged
32 GiB resource gate? The first implementation question is exact compatibility;
the later native question is measured resource margin. Neither is answered by
this design alone.

This freezes one remedy: per-row canonical encoding with incremental SHA256.
Do not combine it with cursor, row-storage, dtype, normalization, validation,
allocator, cache, policy, graph, module, dependency or resource changes. The
previous startup study stays complete/margin-inconclusive. All three earlier
calibration failures and that resource allocation remain spent.

This audit/design authorizes no implementation, tests, new experiment or allocation.
M2 implementation/local checks and M3 native execution require their respective
later requests/readiness. One future resource-only allocation is a proposed
maximum, not a currently released job. Full B2f remains held.

Prospective isolated paths, to create only during implementation:

- Source: `agent/experiments/startup-resource-stream-v1`.
- Local output: `trials/torch-reviews-startup-resource-stream-v1`.
- Torch package: `torch-startup-resource-stream-v1`.
- Campaign prefix: `reviews-startup-resource-stream-v1-`.

Do not edit/reseal prior packages or reuse their bindings/reservations.

## 2. Frozen inputs and semantic requirements

Use the complete source/seal/raw identities in the machine contract. The baseline
is startup-resource.v1 manifest
`4212507e81abc053aa5045e09a8cb624b789ed0bad4e1e8d1bf69f82f31484d9`.
Keep the same image, data, retained stopped clusters, exact graphs, module,
profile/registry, settings, target identities, exposed 200 requests and original
B2f scientific contract/schedule/margins. Preserve all source files byte for byte;
only a separately recorded runtime hash binding changes during acquisition.

Snapshot identity must remain exactly
`54282be380f20bfab05a44e6260e116435aecf5a289a258ae8164a23c187b303`;
eligibility stays
`eed0dc123868ee61c2ffbadbb066cd36db9e813ce8a7829ed18658f04b6b44d2`.
Keep 247,286 rows, 768 dimensions, exact typed ordering/IDs, original decoded
numeric values, metadata, masked arrays, NumPy matrix, field mapping and original
constructor/query validation. Do not regenerate original rows from float32 data.

The original canonical encoding is the existing `json.dumps` configuration:
sorted keys, separators `,` and `:`, ASCII escaping, no indentation, circular
checks enabled, nonfinite values rejected, and UTF-8 bytes. Keep its existing
number formatting and default type behavior by calling the unchanged frozen
`fannagent.store.canonical` on each bounded component. Do not use another JSON
library, a different canonicalization standard or a hash of float32 bytes.

## 3. Exact stream and bounded work

The input identity document has exactly `rows` and `fields`. After the original
constructor's validations and sorting, its sorted root keys are `fields`, `rows`.
Emit this byte sequence in order:

1. `{"fields":`.
2. The original canonical bytes of the original `fields` list.
3. `,"rows":[`.
4. For each original row in existing order: a comma before every row after the
   first, followed by that row's original canonical bytes.
5. `]}`.

Feed the bytes in order to SHA256 and return its lowercase hexadecimal digest.
Preserve all original row references/values; do not sort, copy, cast or mutate
them again. Never build the full stream, a list of encoded rows, an unbounded
join, a full string/byte document, or a persisted canonical snapshot file.
Repeated hash updates preserve the result only when the concatenated bytes are
identical. [Hashlib](https://docs.python.org/3.12/library/hashlib.html).

Scope and work caps for the one full native identity:

| Item | Frozen cap/requirement |
| --- | --- |
| Full snapshot digest invocations | Exactly 1 |
| Rows / dimensions | Exactly 247,286 / 768; same source provenance |
| Canonical component calls | Exactly 247,287: fields once, each row once |
| Encoded fields | At most 16 KiB |
| Encoded single row | At most 64 KiB |
| Pending byte coalescer | At most 64 KiB; drain synchronously into SHA256 |
| Total streamed bytes | At most 16 GiB, including fields/framing/commas |
| Raw evidence | Only small counts/digest/provenance/timing records; no row/vector payloads |
| Encoding working storage | Bounded per-row intermediates and coalescer; 1 MiB design allowance, not a measured whole-process bound |

These bounds apply to this pinned scalar/row schema, not arbitrary JSON strings,
large dictionaries or untrusted general objects. Existing loader/schema/source
proofs establish the input domain; explicit component-size checks enforce the
stream contract. Preserve the original constructor's rejection of invalid data.
A scope/size/count/canonicalization error aborts acquisition; do not fall back to
whole-document encoding, normalize values or accept a claimed identity.

## 4. Binding, lifecycle and provenance

Reuse the actual frozen backend loader and `Snapshot` constructor unchanged.
During the one explicit initial `backend.snapshot()` call, a new isolated harness
context temporarily binds **only the `digest` name in the loaded snapshot module**
to the scoped stream helper. The original module-local binding must first be the
expected frozen `fannagent.store.digest` object. The original store module's
`canonical` and `digest`, backend methods and all files remain untouched.

This binding is permitted only at the single-threaded snapshot-acquisition seam,
before shared snapshot publication. No concurrent/nested snapshot construction or
second stream invocation is permitted. It is not a general thread-safe product
API. Do not monkeypatch all store hashing or introduce a replacement constructor.

Restore the original binding in `finally` for success, encoding/validation errors,
deadline signals and any `BaseException`. Restore before checking/reporting
restoration failures or publishing the snapshot. Require the exact original
callable afterwards and no active context before admission/reader epochs/final
checks. Failure to restore makes the run failed and still triggers cleanup.
A process kill cannot qualify; files and other processes retain original code.

Record the effective behavior amendment explicitly in the new manifest and raw
provenance. Original image/profile hashes alone do not describe this runtime
change. Record source/helper hashes, target module/binding, actual container Python
implementation/version, JSON encoder source provenance, one invocation, component/
byte/buffer counts, exact returned identity and successful restoration.

Add lightweight phase events immediately around streaming, and a bounded summary
artifact (at most 64 KiB), without serializing data or moving any work outside the
existing deadline/accounting scope. These are diagnostics, not a search timer.
The host sampler and actual constructor remain in the complete acquisition path.

## 5. Local readiness gate M2 (prospective; not run here)

All applicable original 117-check coverage categories remain required. Add
meaningful checks at the actual seams:

- Compare the concatenated framed output byte for byte against the original
  canonical document on bounded fixtures, then compare SHA256. Cover root/row/
  metadata key insertion orders, empty/single/multiple rows at the serializer
  layer, signed zero, int versus float spelling, exponent/rounding cases,
  escaped/non-ASCII strings and rejection of nonfinite/unsupported/cyclic input.
  The native wrapper still rejects an unsupported target/domain.
- Use the original serializer as oracle only on bounded fixtures: at most 64 rows
  of 768 dimensions per dataset and at most 4 MiB per canonical oracle. No full-size
  dataset/vector generation, performance benchmark or scientific experiment.
- Exercise the actual frozen backend and constructor with synthetic SQL rows,
  original validation, exact snapshot/query outputs and typed maps. Verify row
  numeric values and NumPy bits, not just the final hash. Keep rows and matrix
  shared across both main readers and later admissions.
- Exercise actual runtime entry, snapshot module binding/restoration, and host
  launch/sampler/finalization/cleanup. Include helper failure, constructor failure
  before hashing, identity mismatch, count/size/cap exhaustion, unexpected binding,
  nested invocation and deadline interruption. Verify all global bindings after
  success and every exception; verify store hashing remains original throughout.
- Observe the byte writer under bounded fixtures: buffer/component maxima and
  drains are within caps and chunks are not retained as the dataset grows.
  Verify a full-document fallback cannot silently satisfy the helper contract.
- Keep the actual zero-search method/operation/SQL guards; actual launcher under
  restricted export/PATH, prior three failure regressions, restore/sidecar/identity
  checks, separate locks, failed-result collection, transport/once-only/archive
  guards and complete independent raw replay/negative cases.
- Repeat the relevant suite from the sealed candidate; verify source/seal/archive
  parity, frozen science/data/module/graphs, source preservation, syntax/style and
  exact commands. Preserve initial failed local candidates/logs; release only a
  concretely checked version. No test-count shortcut establishes native readiness.

Record actual test counts and all mock boundaries. Local correctness cannot
qualify full-size peak memory or time.

## 6. Prospective native gate M3 (not released)

Keep the original zero-search resource envelope: one proposed one-hour allocation,
four physical CPUs, 32 GiB; same two copies, one snapshot scan, four data checks,
ten admissions/maxsix live/eight SQL connections, both original creation orders
and five-second holds. Keep 0 ANN/exact/quality/reference/priming/warmup/searches,
0 EXPLAIN/plan packets, 0 provider/fit/confirmation work.

Carry over all original SQL/storage/process/sampler/raw/read/CPU/phase caps and
source/graph/sidecar/cleanup requirements without increase. In particular: runtime
3,000 seconds includes the 600-second cleanup reserve; snapshot/admission stage
600 seconds; host pre/post 240 seconds each; same 1 Hz sampler, 5-second gap cap,
32 processes, 806 prior samples retained as historical evidence only. Increased
CPU cost must fit these deadlines; no automatic extension or retry.

Before loading the real dataset, use at most 32 deterministic literal parity
cases, at most 1 MiB total canonical oracle bytes and 5 CPU seconds, within the
existing runtime envelope. This records actual container encoder behavior and
fails before restore on incompatibility. It performs no database/search work;
its helper counters are separate from the one real identity invocation. The
actual full snapshot must then match the previously pinned identity and complete
all original guards. No original full-size hash rerun is required as an oracle.

The complete trusted analyzer must require the new hash provenance, one-invocation/
component/byte accounting, restoration proof, exact frozen identity, unchanged
all-source/data/catalog/graph/module evidence, both epochs, source preservation,
shutdown, complete memory mapping/coverage/events and all old caps. Independent
review uses the known identity plus input proofs and sealed software; streamed
byte length alone is not semantic proof.

The gate remains: largest aggregate kernel peak over visible finite ancestors,
plus 2 GiB reserve and 2 GiB workspace allowance, must fit the smallest observed
finite limit capped at 32 GiB, with no positive prohibited limit/OOM event delta.
No cache subtraction, summed process/component highs or lowered reserve. A native
startup pass still does not qualify query-workload memory, A/A, quality or speed.

Outcomes: complete scoped resource-margin pass; complete margin-inconclusive; or
failed/incomplete acquisition. Any nonpass closes the proposed finite job and
returns to review. Do not automatically activate a deferred remedy, repeat the
study, raise resources or resume full calibration.

## 7. Decisions and critical path

| Gate | Required result | Current state |
| --- | --- | --- |
| M0 audit | Allocation/consumer/identity constraints and limitations documented | Complete, read-only |
| M1 design | One narrow remedy, immutable inputs, equivalence/binding/buffer/deadline/resource rules frozen | Complete, design feasibility only |
| M2 implementation/local readiness | Actual source/sealed checks and preservation; concrete reviewable package | Not implemented/assessed; next requested work |
| M3 native resource qualification | Separately released zero-search acquisition and independent unchanged resource gate | Not authorized/released |
| M4 full B2f release | Resource plus remaining workload-memory/release review, then scientific native gates | Held |

Critical path: M0/M1 complete → M2 isolated implementation/local qualification →
readiness/release review → separately authorized M3 resource acquisition →
independent margin decision → possible M4 full-calibration review. A nonpass
returns to review. No Torch command is needed for M0/M1.
