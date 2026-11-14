# Snapshot memory and identity compatibility audit

October 28, 2026, America/New_York. `NEXT-STARTUP-MEMORY-01`, M0–M1.

**Decision:** a scoped first correction is feasible for implementation/local
qualification: hash the snapshot's existing canonical identity document one row
at a time, preserving its exact framing and the original serializer. Freeze that
design separately. Do not change snapshot storage, database cursors, validation,
policies or the native module in the first correction. This is design feasibility;
no memory saving, native readiness or full-calibration release is established.

This audit reads existing source and traces only. It executes no implementation,
local correctness suite, database, ANN/exact search, model, provider or remote job.
The previous startup return stays `startup_complete_resource_margin_inconclusive`.

## Evidence boundary

The actual frozen producer is the vendor tree inside the sealed
`torch-startup-resource-v1` package, manifest
`4212507e81abc053aa5045e09a8cb624b789ed0bad4e1e8d1bf69f82f31484d9`.
Its complete successful zero-search return is
`reviews-startup-resource-v1-20261028T020546Z.zdsnk75c`, archive SHA256
`312bf5c02959a1e90514f6ec556914303095eb30c2f87acd9b182010a28320e7`.
The source inventory covers 116 frozen vendor/harness/runner/runtime-recipe files and
137 static reference occurrences; the consumer interpretation below reviews that
overapproximation rather than treating every `.snapshot` reference as a live call.
Source hashes and prior evidence are preserved in the audit directory. The
Torch runner matches its original bundle manifest, and neither its adapter nor
the exact-reference/profile wrappers override the frozen snapshot producer.

The pinned image recipe uses Python 3.12; the dependency lock selects Psycopg
3.3.6, NumPy 2.5.3 and PyArrow 22.0.0. The saved host interpreter version is not
proof of the container's patch version. A later correction must record the actual
container interpreter/encoder provenance and check parity there, using the same
image. No dependency upgrade is proposed.

## Allocation and lifetime inventory

| Representation or work | Creation and lifetime in the frozen path | Compatibility implication |
| --- | --- | --- |
| Database snapshot result | Unnamed default Psycopg cursor in `PgvectorBackend.snapshot`; client result buffer lives during row decoding and the cursor context closes before `Snapshot(...)` | Python iteration alone does not make result storage incremental. Preserve cursor/SQL/transaction behavior in the first correction |
| Python rows and vector lists | `json.loads` produces original numeric values in each row; all row dictionaries are retained before construction | Preserve original numeric values and row metadata; do not round-trip through float32 or discard rows |
| Sorted outer row list | Constructor creates a new sorted outer list; row dictionaries/vector lists are referenced, not recursively copied by `sorted` | Do not count this as another complete copy of every vector; retain exact typed identifier ordering |
| ID maps, fields and metadata arrays | Constructor validates identifiers, builds maps/schema and masked metadata | Typed IDs, masks, logical fields and exact validation behavior remain required |
| Float32 matrix | Constructor adds `np.asarray(..., dtype=np.float32)`; shared through `LoadedDataset` | Its dense payload alone is 759,662,592 bytes, about 0.707491 GiB; that is not total snapshot memory |
| Numeric validation temporaries | Finite and normalization checks happen before identity construction | Preserve original operations/tolerances; transient sizes depend on the actual library and are not measured here |
| Complete identity JSON | `digest({'rows': rows, 'fields': fields})` calls full JSON serialization and UTF-8 encoding before SHA256 | Complete serialized text/bytes are unnecessary for the hash result; target only this transient allocation |
| Retained snapshot | Constructor retains both original rows and NumPy/metadata representations | Persists through requests, reader epochs and final verification via runtime/factory references |
| Reader ownership | `prepare_requests` assigns the same snapshot to both main readers; `Factory.create` assigns it to later readers | Ten admissions share one snapshot; there is no ten-fold snapshot duplication to remove |
| Full data verification | `verify_data` uses a named server cursor and 512-row Parquet batches | Already distinct from snapshot loading; preserve the four scans and bit comparison |

Psycopg documents default cursor results as client-stored; named cursors retrieve
results incrementally. Switching the snapshot cursor would also alter its server
portal/transaction behavior and needs a separate qualification.
[Official cursor documentation](https://www.psycopg.org/psycopg3/docs/advanced/cursors.html).

## Observed lifetime evidence and remaining uncertainty

The original trace records the snapshot SQL execution over 6.485254 seconds,
inside a 117.843556-second `snapshot_load` phase. This does not time row decoding,
NumPy construction or identity serialization individually. All 592 job-limit
events occur in that combined phase; assigning them to one allocation would
require new observations.

The runtime's largest sampled RSS in `snapshot_load` is about 14.8306 GiB; its
process high-water counter reaches 15.030392 GiB. Sampled RSS then remains about
10.6101/10.6104 GiB in the two reader holds and reaches 11.3308 GiB during final
verification. These are existing per-process observations, not live object sizes
or quantities to subtract from the job's 32 GiB peak.

The retained footprint, remaining client buffering, allocator behavior and charged
file cache may still consume the margin after identity streaming. Removing the
full JSON buffers does not establish a 4 GiB total-charge reduction, nor guarantee
an event-free aggregate peak at or below 28 GiB. No speculative cache subtraction,
cache eviction, memory-cap increase or additional job follows from this audit.

## Consumer compatibility matrix

| Consumer | Fields/semantics that must survive | First-remedy consequence |
| --- | --- | --- |
| `pc_snapshot.validate_snapshot` | Original source IDs/votes, exact logical map, exact full snapshot identity and row count | Keep all inputs and the separate two-key eligibility guard; expected full identity remains unchanged |
| `Snapshot.query` and query-validation fallback | Profile, manifest dimension, reverse fields, metadata types/operators, finite/norm checks and error classification | Execute the original constructor and query methods; no validation rewrite |
| `Factory` / owned readers | Shared snapshot object and unchanged backend connection/binding state | Scope the hash behavior only during initial construction; restore before later admissions |
| `Study` and workload preparation | Dataset identity, ID mapping, original anchors, matrix and metadata | No new identity namespace or data-layout change; do not run these consumers during this audit |
| Broker sample/count/descriptors | Original `rows[*].vector`, metadata, row count and offline dataset representation | Float32 reconstruction of original rows is not an identity-preserving substitute |
| Native `_qualify` and audit reconstruction | Original row vectors for qualification requests, snapshot matrix/metadata for membership | No hidden qualification/search is permitted by a startup-only correction |
| `Snapshot.save` / description | Float32 matrix, original metadata, source IDs, fields and identity | Public exports and descriptions remain unchanged; no serving/API claim |
| Store and other hashes | `canonical` bytes for artifacts, manifests and persistent store records | Do not globally replace `fannagent.store.canonical` or `digest` |

The frozen full identity is
`54282be380f20bfab05a44e6260e116435aecf5a289a258ae8164a23c187b303`.
Eligibility remains
`eed0dc123868ee61c2ffbadbb066cd36db9e813ce8a7829ed18658f04b6b44d2`.
Equivalent JSON values are insufficient: the full serialized bytes, ordering,
numeric spelling, escapes, separators and UTF-8 encoding must match.

## Remedy selection

| Option | Assessment | Disposition |
| --- | --- | --- |
| Per-row canonical hashing with exact outer framing | Keeps the existing serializer/float formatting and original data; bounds serialized working data to a row and small buffer | Select as the first isolated correction |
| Generic JSON token iterator | Also avoids a full document, but introduces a different iteration path and many Python-level token operations | Defer; no measured CPU/saving comparison; unnecessary first change |
| Server-side snapshot cursor | May remove a client result buffer, but changes cursor/transaction/SQL accounting; original rows still retained | Defer to a separate design if needed; data-verification cursors already use this mechanism |
| Compact rows or float32-backed replacement | Could reduce persistent storage, but affects original row vector values, exact identity and sample/export consumers | Defer; needs broader semantic/API design |
| Full streaming reconstruction of constructor | Broadens changes to validation, sorting, metadata, maps and lifecycle | Defer; exceeds the narrow first remedy |
| Skip identity/data checks, keep a claimed identity, drop rows, reduce dataset/readers, trim allocator or drop cache | Changes required evidence or measured conditions | Excluded |
| Raise memory or weaken reserves | Does not answer the frozen resource question | Not selected; any future resource amendment requires a new explicit design |

The selected framing follows the existing sorted root keys, `fields` then `rows`.
Serialize `fields` and each original row separately with the unchanged
`canonical` function, inserting only the exact structural punctuation; feed those
bytes to incremental SHA256. Python documents that successive hash updates are
equivalent to hashing their concatenation.
[Hashlib](https://docs.python.org/3.12/library/hashlib.html).
The ordinary JSON encoder's settings define its bytes; do not substitute another
canonical-JSON standard or serializer.
[JSON documentation](https://docs.python.org/3.12/library/json.html).
CPython's encoder source also distinguishes whole-document encoding from token
iteration; this motivates retaining the existing per-row encoder path, not a
claim about measured runtime performance.
[CPython 3.12 source](https://github.com/python/cpython/blob/v3.12.0/Lib/json/encoder.py).

## Design freeze and next gate

The [prospective correction design](fannagent-startup-identity-stream-v1-design-2026-10-28.md)
and its machine contract freeze the exact binding scope, framing, buffer/work
caps, semantic checks, local regression requirements, provenance and proposed
zero-search native gates. Design feasibility is GO; implementation/local readiness
and native/resource gates are unassessed.

M0 audit and M1 design are complete. Next is a separately requested isolated
implementation and local qualification (M2). Only after that readiness review and
a new authorized handoff could M3 run one proposed resource-only job; none is
released now. Full B2f calibration stays held. No Torch commands are needed.

Evidence: [source/reference inventory](../trials/torch-reviews-startup-memory-audit-v1/source-inventory.json),
[existing-trace lifetime metrics](../trials/torch-reviews-startup-memory-audit-v1/trace-lifetime-review.json),
[machine design](../trials/torch-reviews-startup-memory-audit-v1/CORRECTION-DESIGN.json),
[audit receipt](../agent/docs/verification/startup-memory-audit-v1.json).
