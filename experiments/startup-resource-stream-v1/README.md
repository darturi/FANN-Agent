# Bounded snapshot identity streaming

Implements the pre-code frozen startup identity-stream design in an isolated
harness. The actual frozen backend, Snapshot constructor, source rows, NumPy
matrix, cursor, validation and query behavior stay unchanged. During the single
initial snapshot acquisition, only the snapshot module's digest binding is
scoped to per-row original-canonical encoding with exact document framing and
incremental SHA256. The original binding is restored in finally, including
encoding, constructor, deadline and BaseException failures.

Component/byte/buffer/invocation caps and effective source/interpreter/encoder
provenance are recorded. No full canonical document or encoded row list is
retained. Eight small literal parity cases qualify the actual interpreter before
copying/loading; their work is bounded and separate from the real identity.
The trusted local analyzer independently requires exact identity, restoration,
provenance, counter/framing/cap and phase proofs alongside every existing zero-
search/source/copy/lifecycle/cleanup/memory requirement.

The study performs exactly zero ANN or exact searches. It retains one snapshot
scan, four data-verification scans, 200 admission-only requests, ten reader
admissions/maxsix live and both creation orders. A proposed user resource job
retains one hour/four CPUs/32 GiB, all prior deadlines/observer/sampler/storage
caps, 2 GiB reserve plus 2 GiB workspace and the event-free resource gate.
No cache subtraction or automatic retry, alternate remedy or memory increase.

All previous packages/raw/bindings/reservations stay spent and protected,
including the completed margin-inconclusive startup-resource.v1 return. This
implementation does not qualify memory savings, query workload, quality, A/A,
speed, adoption or full B2f calibration. Full calibration remains held.

Tests are synthetic/offline. They use the actual frozen constructor/backend and
runtime/host/launcher/replay paths with mocked SQL/process/full-data/graph proofs;
no native database, provider, fit, real SSH or Torch allocation is run locally.
The final source/sealed receipts identify the checked version and limitations.
Use only the final checked COMMANDS.txt if/when executing its separate user
resource-only handoff. Preserve all failed local candidates and terminal raw.
