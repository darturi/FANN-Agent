# B2f restored identity metadata correction

October 27, 2026, America/New_York. Infrastructure revision
`partial-calibration.v1.metadata-fix`; scientific contract remains
`partial-calibration.v1` / NEXT-PARTIAL-CALIBRATION-01.

## Verified failure and scope

The launcher correction succeeded in job21129331_0. The returned campaign
`reviews-partial-calibration-v1-launch-fix-20261027T185901Z.98dd224c` has32 regular
archive members; checksum/member parity, failed raw locks and exact
submission/package/scheduler identities verify. Archive SHA256:
`4619d2c984843aa6c47eafddd39c293782334cda1cfa096f17e0fb2526cd2dff`.

The missing file was `/run/native640/database-identity.json`. Status records
zero searches, zero reader admissions and zero plan packets. Both retained
source cells actually contain the exact pinned957-byte file (SHA256
28a053d17b4b92336923319772baa88c58391450829ff833bed118a124ef5ffe).
The copy routine omitted that file outside pgdata. The unmodified frozen
TorchBackend constructor reads it before opening a reader connection.

Full source-before/source-after inventories match:2,587 files/4,603,663,760 bytes.
Independent whole-pgdata copy proofs and initial catalogs match. Both working
servers stopped, with clean shutdown messages and empty cleanup errors; protected
input receipts match. Final measurement integrity was never qualified. No
conformance, quality, A/A or performance result exists. Slurm reported MaxRSS
23572496K; this observation does not establish remaining full-run memory headroom.
The4s original attempt and this8m34s attempt are both spent allocations.

## Correction and unchanged boundaries

Before copying a cluster, require a private, owned, ordinary, single-link identity
file whose bytes exactly match the frozen source-index identity. Copy those bytes
into each fresh working envelope, set private permissions and verify the copied
hash. Missing, unsafe or changed metadata fails before copying database files.
The working identity is rechecked during final integrity verification, and
trusted local reconstruction checks the copied proof against the retained source
and the pinned hash.

Both cells intentionally retain the original full-index baseline identity file.
The existing private bound-class adapter then selects the exact native640 or
partial640 target in memory, with the unchanged actual catalog/graph guards.
No partial identity is invented and no validator is bypassed. No retained source,
previous package, raw, binding, reservation, graph, module, data or policy changes.
The absolute-interpreter/export correction is retained.

The only runtime changes are restoration/provenance guards outside the measured
query path. Native SQL, timers, scoring, priming/conditioning/warmup/repetition
orders, telemetry regime, quality and all56 timing gates remain unchanged. One
proposed additional job keeps the3h4CPU32GiB/16,242-search ceiling. No automatic
retry or resetting of either spent attempt is allowed.

## Stronger local coverage

Earlier mocks supplied backend state directly and skipped the actual frozen
constructor. The new regression reproduces the precise omission by running the
old copy routine followed by the actual frozen constructor. The corrected copies
then pass both actual target constructors without opening a real connection.
Missing/tampered/symlink metadata is rejected before any copy.

The new complete fixture loads the unmodified frozen backend through the same
loader used on Torch (redirecting only its container-local runner filename to
the identical pinned local file). It uses actual construction, binding, snapshot
loading, native execution, exact reference and cleanup methods. Only PostgreSQL
responses are synthetic. It completes both epochs, all16,242 calls,4,200 plan
packets, ten admissions/max6 live readers and exact schedule/SQL accounting.
Trusted complete-raw reconstruction and all56 gate calculations are also checked.
The existing synthetic protocol, launcher, ownership/PID/affinity/archive/budget
and negative-outcome checks remain in the suite.

These are correctness tests with40 synthetic database rows and the200 exposed
request IDs. They are not a native experiment, a full-size memory measurement,
a new calibration result or proof of remaining compute-node compatibility.
No native database process, Torch submission, provider request, fit or protected
query is run during preparation.

## Required handoff and decision

Use only the separately named corrected package/campaign/reservation. Original
seals and both failed archives/bindings/reservations must remain verifiable.
Executing the clearly labelled new submit command requests **one additional**
allocation, beyond the two spent jobs; preparation/upload submits nothing.

The critical path remains native N0 restoration/identity/resource/core/telemetry
qualification → conformance/quality → complete two epochs → final preservation/
cleanup → independent complete-raw/all56 decision. A scoped calibration pass
permits only later treatment-design review. B2d remains measurement_inconclusive,
original execution retained and B1c deferred; no speed/adoption verdict is made.

Primary project sources: frozen runner.py TorchBackend.__init__, frozen
source-index.json, prior pc_restore.clone and the verified failed raw. Exact
source and artifact hashes are retained in the release/implementation receipts.
