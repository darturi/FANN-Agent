# A3 adaptive startup integration (offline)

The prospective design is `STARTUP-FREEZE.json`, SHA256
`2e31c4cedebfc844e30d137c6042e5f30cfd44b7d16d7488d51daa7721b7f91b`.
This isolated harness integrates the D118 exact adaptive codec with D117 startup,
sampling and shutdown. All historical sources, native receipts and allowances
remain preserved. Production builds, native CLI entries and native release are
closed for both legacy and adaptive profiles.

`adaptive_integration.py` uses the original bounded FixtureSpec, client cursor,
ordered SELECT, metadata fields, Snapshot constructor and request validation.
It packs each vector before advancing the cursor. Original binary64 bits, integer
categories, canonical identity and float32 matrix bits are exact. A vector uses a
3072-byte payload only after exact roundtrip acceptance; otherwise it retains
6144 bytes. The constructor matrix owns independent mutable data. No extra
GC/cache subtraction, early root release, omitted checks or changed deadline.

`ev_startup.py` explicitly selects the adaptive profile for synthetic fixtures.
Pre-restore checks bind the codec/helper sources, original five A3 sources, full
private-driver provenance and exact NumPy formatter source. New code maps and
retention counts are recorded through admission and all reader epochs. Replay
retains every old verification rule and also checks the new source, target,
literal and retention proofs. Synthetic replay always reports native held.
The old native correctness packet qualifies only the original packed64 code.

`TARGET-REFERENCE.json` records static inspection of the pinned runtime SIF and
its matching OCI image: CPython 3.12.15, NumPy 2.5.3, ten selected source/ELF
members and the full frozen driver provenance. Direct reads of the SIF filesystem
match the selected OCI members. Local checks run under approved CPython 3.12.7;
they compare target reference data and reject the actual local interpreter as
the target. They do not execute the target interpreter or qualify native CPU,
compactability, shutdown or aggregate memory.

All limits remain unchanged: 1h, 4 physical CPUs, 32GiB, 3000s runtime including
600s cleanup, all original host/stage/sampler caps, one snapshot scan, four full
data verification scans, 200 admission-only requests, ten readers/max six live,
two servers/max eight SQL connections, and zero searches/provider calls.
The resource rule remains max aggregate kernel peak across visible finite
ancestors +2GiB reserve +2GiB workspace <= min(32GiB, finite limits), with no
positive memory limit/OOM/failcnt events. Offline checks do not imply this gate.

The guarded runner includes all 142 lifecycle/resource cases, all 56 original A3
cases, all 38 memory-component cases, and new producer/runtime/replay cases.
Each row-allocating fixture is bounded to 64 rows. Full-count replay is explicitly
synthetic metadata. No native capsule, transfer helper, submit command or new
allowance is created. All spent allowances remain closed.
