# Exact adaptive vector memory component — offline only

The prospective MEMORY-FREEZE.json selects one nonexpanding representation:
3072-byte binary32 storage only after every reconstructed binary64 bit equals the
original payload; otherwise retain the original6144-byte binary64 payload. Exact
integer tags/values remain. This is an explicit new internal type with three
immutable slots, not a change to the original PackedVector or public list API.

Compact vectors expose a read-only zero-copy binary32 NumPy view to the unchanged
Snapshot constructor. Other requested dtypes reconstruct exact values; copy=False
fails when conversion needs allocation. Full original canonical bytes, signed
zero, float/int categories, float32 matrix bits and consumers remain required.
The original constructor, SQL, cursor, data, graphs, code and all limits stay
unchanged. No root is released early and no cache/GC/verification shortcut is used.

The baseline directory preserves all five qualified A3 files byte-for-byte. The
56 original local cases run alongside new exactness/allocation/consumer cases.
The fixture adapter accepts only the original <=64-row FixtureSpec and has no
database or producer path. Real network/process/SQL calls are denied by the local
runner. No native capsule, controller, transfer helper or Torch command is supplied.

The pre-code probe demonstrates overlapping per-row float32 conversion buffers
in the unchanged constructor on64synthetic rows. Compact views need no separate
row data buffers. This structural observation and payload arithmetic do not
establish native savings or sufficient headroom. Actual native compactability,
formatter CPU cost, exact-image correctness and total cgroup peak remain unknown.
The largest aggregate peak +2GiB reserve +2GiB workspace <=32GiB/no-positive-event
criterion and existing stage deadlines are unchanged.

All prior allowances remain spent. This component cannot inherit the old native
proofs as qualification. A separately frozen production integration and exact-image
correctness review must precede any resource-release discussion; no new native
entitlement or full B2f release follows from local checks.
