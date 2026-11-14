# Bounded snapshot identity hashing: implementation and local readiness

October 28, 2026, America/New_York. `NEXT-STARTUP-MEMORY-01`, M2.
Protocol: `startup-resource.stream.v1`.

The pre-code frozen correction is implemented in the new isolated
`agent/experiments/startup-resource-stream-v1` directory. It changes only the
snapshot identity encoding behavior during the single initial acquisition.
Production and all earlier experiment source, packages, raw, bindings and
reservations remain unchanged. No database, ANN/exact search, provider, fit,
real SSH or Torch allocation is run by Codex.

## Exact behavior and preserved boundaries

`si_stream.py` hashes the original fields and each original row through the
unchanged frozen `fannagent.store.canonical`, inserting exact sorted-root framing
and feeding a bounded byte coalescer into SHA256. It never retains a full canonical
document or a list of encoded rows. It preserves numeric spelling, escapes,
separators, row ordering and UTF-8 bytes. Component, total-byte and pending-buffer
caps implement the frozen contract.

`pc_snapshot.prepare_requests` calls the actual frozen backend and Snapshot
constructor inside a scope that temporarily replaces only the snapshot module's
`digest` binding. Store hashing, source files and constructor code stay unchanged.
The binding is restored in finally before validation/publication, including
encoding errors, original constructor rejection, timeout and BaseException paths.
Concurrent/nested construction, unexpected binding, a second invocation and a
cached snapshot without hashing fail closed. Reader-context and final checks
require no active binding. Immutable field containers from the original owned
reader remain accepted without conversion.

Rows, their original decoded numeric values, the NumPy matrix, metadata/ID maps,
validation, query behavior, cursor/SQL/transaction shape, policies, graphs, native
module, image, profile/registry and scientific margins stay unchanged. The
separate eligibility/field-map/full-snapshot guards remain intact. Ten admissions
continue sharing one snapshot. The effective runtime behavior amendment is
explicit in the protocol/manifest and required raw hash provenance.

Before restoring/loading, eight deterministic literal encoder-parity cases run
within the frozen 1 MiB oracle/5 CPU-second caps and existing runtime deadline.
They record the actual CPython/encoder provenance without database work. The real
snapshot then requires exactly one invocation, exactly the original identity and
component/byte/buffer accounting. New phase events and small summaries expose
encoding without recording row/vector payloads or moving work outside deadlines.

## Independent reconstruction and packaging

`si_verify.py` validates returned provenance against sealed helper/frozen source,
actual-interpreter preflight agreement, exact identity, invocation/restoration,
integer counters, framing/component/byte/buffer caps and phase order. The complete
resource analyzer requires these alongside every original source/copy/catalog/
data/graph/module/lifecycle/placement/SQL/cleanup/memory proof. A failed/incomplete
return cannot yield a positive resource result or automatic retry.

The builder starts from the exact immutable original startup seal, retains its
frozen sources/scientific/evidence pins, adds the frozen correction design and
116-source evidence, and protects the previous successful raw campaign and its
package/binding/reservation. New names, work roots, campaign prefixes and once-only
reservation prevent reuse of earlier attempts. The trusted local transfer/ingest
path keeps checksum, archive safety, binding and package identity checks.

The final source and sealed suites each pass **155/155** tests, with zero failures
or errors and verified module origins/source stability. Ruff, formatting, Python
AST and Bash syntax checks pass. Independent release verification checks all
346 manifest files and all 347 regular archive members, 116 source pins, unchanged
scientific/helper/vendor/native bytes and **3,468 unchanged prior inputs**.

- Manifest SHA256: `26a7d66b67137e77d5208d7b851b19d980a8a64060defc25cbe418db17190354`.
- Archive SHA256: `5fa2e92e7b87a4a8fff0ac7cb897e9f116ad8ecf07c4675e185c51f17ffb8689`.

The final source and sealed receipts identify the exact released code. Archive
member parity, source/seal parity, scientific-byte equality and preservation are
recorded independently. Native availability, full-size encoding CPU time, memory
saving and resource margin remain unmeasured.

## Local coverage and limits

The suite retains the original launcher/host/runtime/zero-search/restore/metadata/
identity/ownership/affinity/budget/memory/sampler/archive/transport/once-only and
independent replay categories. Added coverage includes:

- Exact framed bytes and hashes against the original serializer on bounded
  fixtures, key orders, empty/single/multiple rows, signed zero, integer/float
  spelling, exponent/rounding boundaries, Unicode/escapes and encoding rejection.
- Actual frozen constructor outputs, original row values, NumPy bits, metadata,
  typed ID mapping and query validation; original immutable metadata containers.
- Bounded drains and component/total caps; the original encoder sees only fields
  or one row, never the whole row array/document.
- Actual acquisition/finalization/cleanup for encoding failure, original duplicate-
  ID rejection, deadline, BaseException, byte-cap and preflight failure. A real
  handled POSIX signal also checks binding restoration locally.
- Unexpected/nested/repeated/missing invocation, binding tamper and exact original
  store hashing throughout the scope.
- Independent replay rejection of altered digest, row/component/counter/buffer/
  restoration/provenance/preflight evidence, in addition to every old negative.

All database/process/resource/large-graph proofs in complete fixtures are
synthetic. Vectors are bounded local correctness inputs, not a full-size dataset
or benchmark. The complete-return fixture explicitly fabricates full-size counts
and data/graph/process proofs to exercise independent reconstruction only. Local
checks cannot establish full-size memory or scientific search behavior.

Initial local failures and logs are preserved. They exposed fixture module-path
ambiguity from the baseline harness, rejection of its immutable metadata wrapper,
and an incorrect expectation that an early failure makes no idempotent cleanup
attempt. Tests now enforce current-harness module origins, isolate temporary
import paths, accept the original container semantics and model cleanup before
copies accurately. These corrections were made locally before the final seal.
The check runner also requires unchanged source bytes during the suite and
records all loaded test-module origins.

## Resource handoff and next gate

After concrete source/sealed readiness review, the prepared commands describe one
further user-executed **startup-only** qualification: one hour, four CPUs, 32 GiB;
zero ANN/exact searches; one snapshot/four data scans; ten admissions/maxsix live
and both original creation orders. Original SQL/observer/sampler/storage/phase/
cleanup caps remain unchanged, including the 600-second snapshot/admission stage.

The frozen gate still requires aggregate kernel peak plus 2 GiB reserve and
2 GiB workspace to fit the observed limit capped at 32 GiB, with no prohibited
limit/OOM event delta. No cache subtraction or retrospective cap/margin change.
An inconclusive/failed native result closes that job and returns to review; no
repeat, alternate remedy or larger job follows automatically. A scoped resource
pass still leaves full query-workload memory and B2f release/scientific gates open.

The three failed calibration attempts and original margin-inconclusive resource
job remain spent. No job is submitted by package creation or upload. The user's
once-only submit block is the action that acquires the proposed new allocation.
Full B2f calibration remains held.

- [Frozen design](fannagent-startup-identity-stream-v1-design-2026-10-28.md).
- [Implementation/release receipt](../agent/docs/verification/startup-resource-stream-v1-implementation.json).
- [Source/sealed checks and release evidence](../trials/torch-reviews-startup-resource-stream-v1/).
- [Exact proposed Mac/Torch commands](../trials/torch-reviews-startup-resource-stream-v1/COMMANDS.txt).

Critical path: M2 source/sealed readiness → user executes the separate M3 resource
job → terminal collect/download → trusted independent stream/resource review →
only then possible M4 full-calibration/workload-memory review. Original execution,
B2d's inconclusive measurement verdict and deferred B1c remain unchanged.
