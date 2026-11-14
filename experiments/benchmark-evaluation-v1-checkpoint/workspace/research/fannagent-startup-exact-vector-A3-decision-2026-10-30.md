# A3 remedy decision: exact packed vectors, bounded offline prototype qualified

October 30, 2026, America/New_York. Roadmap D110 / v1.61.

**Decision:** GO to one separate representation remedy: pack each decoded vector
as immutable binary64 bytes plus original integer type/value tags, and restore
ordinary JSON vectors at the identity and bounded sample boundaries. A3's remedy
selection and contract freeze are complete. The bounded offline prototype passes
33 checks. Production integration, exact-target source/sealed correctness and
native resource qualification remain separate gates; **no Torch run is released**.

The original A2 allocation21459623 and all four compatibility allowances remain
spent. The original A2 source/seal/raw/analysis and128+128 test evidence are intact.
There is no main-code/limit change, resubmission, ANN/exact search or B2f release.

## Why this remedy

A2 independently measured +8,029,081,600 bytes of process RSS in the row-decode
bracket, with matching task-anonymous growth. Matrix construction separately
added761,188,352 bytes; cursor close changed RSS by only12KiB. The kernel aggregate
peak hit32GiB and memory max-event delta780, despite successful startup and no
OOM kills. These facts justify investigating the decoded-vector representation.
They do not establish an optimized peak or causal savings.

| Option | A3 disposition |
| --- | --- |
| Float32 rows reconstructed from the existing matrix | Reject: changes original decoded values and identity, even where float32 matrix bits collide |
| Plain binary64 arrays | Insufficient alone: JSON integer/float categories and ordinary JSON serialization would change |
| Cursor-only, smaller batches, close/GC-only | Reject as the selected remedy: does not address the demonstrated retained decoded rows plus matrix and final-verification overlap |
| Packed binary64 plus exact integer tags and explicit row-boundary adapters | Select for an isolated experiment; avoids retaining decoded Python float objects while preserving original values and canonical bytes |
| Larger memory allowance, cache subtraction, omitted verification, early row disposal | Reject: changes the qualification contract |

The representation keeps binary64 float bits, including negative zero and
subnormals. Original Python integers are retained separately with a bit mask,
so integer0 remains0 and float0.0 remains0.0 in canonical JSON. Large integers
retain their exact value even when their numeric buffer conversion rounds;
malformed/nonfinite payloads and inconsistent tags/buffer values are rejected.
The future producer must pack **one decoded vector before appending its row**.
Packing after accumulating all old list vectors would not remedy the original
loading peak and is not an acceptable production integration.

## Frozen consumer review and scope

The immutable [A3 freeze](../trials/torch-reviews-startup-exact-vector-v1/A3-FREEZE.json)
precedes candidate code. Its ten source pins cover the actual frozen native
producer, Snapshot, canonical encoder, workload, row tools, study, eligibility,
admission, identity framing and reader factory. The
[consumer inventory](../trials/torch-reviews-startup-exact-vector-v1/consumer-audit.json)
records actual source references and limits.

| Boundary | Preserved behavior and required adaptation |
| --- | --- |
| NativeBackend.snapshot | Future isolated producer changes only per-row decoded vector storage. Keep original SQL/order/client cursor/transaction/data and fields. This producer is not implemented yet |
| Original Snapshot constructor | Original source/code object, sorting, maps, float32 matrix, finite/norm/dimension/metadata validators and retained rows remain unchanged; PackedVector supplies NumPy array conversion |
| Snapshot identity | Original canonical encoder and unchanged per-row framing; decode at most one packed row to ordinary numeric lists per encoder call, with binding restoration on success/failure |
| Eligibility, count, description, reader sharing | IDs, votes, row count, metadata, maps and shared lifetime remain unchanged; no vector materialization needed |
| Workload generation and queries | Matrix bits, typed anchors, metadata and validated JSON request values remain identical |
| Parquet save | Original save uses matrix plus metadata; schema, values and same-runtime file bytes match |
| Row sampling | Convert one visited row to ordinary JSON before query validation/publication; preserve offsets, limits and permission-denial behavior |

This is **not a drop-in replacement for arbitrary list APIs**. Internal vector
type and mutation behavior change explicitly under a new experiment contract.
Direct arbitrary serialization or third-party code expecting list mutation is
outside this scoped claim. The original public Snapshot API is not changed by
this prototype. A broad product rollout would require a separate consumer/API
review. Existing A2's strict list-vector identity guard stays unchanged; packed
rows must never be routed through that old guard or an implicit fallback.

All original rows, metadata and the shared snapshot remain alive through the
original holds and final verification. There is no forced collection, cache/pool
release, early-root disposal or omitted scan. A3 does not change the original
float32 matrix dtype or normalize/round input values.

## Offline implementation and checks

The candidate is isolated in
[exact_vector.py](../agent/experiments/startup-exact-vector-v1/exact_vector.py).
It has no backend, native producer, controller or launch entry point. Its fixture
identity scope rejects more than64 rows. Tests use at most64x768 synthetic values
and the actual frozen Snapshot/JSON/workload/query/save/tool consumer functions.
No returned campaign code is executed.

All **33 guarded checks pass** on CPython3.12.7, NumPy2.5.3, Arrow22.0.0 and
Pydantic2.13.5. This is local correctness, not target3.12.15 or memory/performance
qualification. The checks cover:

- Exact complete canonical byte/hash parity, int/float categories, signed zero,
  subnormals, float32 rounding collisions and large exact integer tags.
- Original constructor, float32 uint32 matrix bits, mixed typed IDs/maps,
  metadata values/masks, description, query validation, seeded workload and
  original Parquet schema/values/file-byte parity.
- Original Tools sample values, offsets/limits/denials and only visited-row
  materialization; no whole decoded-list cache in packed vectors.
- Owned/read-only payload, malformed data/caps/forged tag rejection, source and
  loaded-origin mismatches, repeated/nested/threaded/foreign binding rejection,
  constructor/encoder failure cleanup and digest restoration.
- Explicit database/socket/subprocess denials: **zero attempted connections or
  processes**. No SQL, ANN/exact searches, SSH, native job or provider call.

Initial local fixture errors referenced the wrong tool class, LoadedDataset
attribute and a too-small workload count. Their log is preserved; the fixtures
were corrected to the actual frozen Tools, dataset_hash and minimum workload
contract. The resulting29-case suite passed, then additional tag/framing/cap
negatives and the64-row boundary produced the33-case guarded result. No original
case was removed or changed. A guarded positive run before import cleanup is
also retained rather than overwritten.

All **756 tracked preexisting A2 source/seal/raw/analysis/verification files**
remain byte-identical. Existing128+128 native compatibility receipts remain
qualified for unchanged A2; the33 new checks do not replace them. The
[local receipt](../trials/torch-reviews-startup-exact-vector-v1/local-checks.json)
binds exact candidate hashes and source stability. Ruff passes. Each packed
float payload is exactly6,144 bytes at768 dimensions; this layout fact is not a
native heap/peak or savings estimate, and integer tags/object overhead add cost.

## Next release gates and commands

A3's evidence-backed remedy decision is complete. Before a future native run:

1. Integrate the one-row-at-a-time packing producer and explicit sample/identity
   adapters into a **separate** experiment with pinned effective-source provenance.
   Keep the original A2 package and all old runtime paths sealed and unchanged.
2. Extend actual entry-point/failure/cleanup/identity/consumer tests, preserve all
   old128+128 cases and strict exact references, then freeze a distinct finite
   source/sealed target-correctness capsule and budget. No old job can be reused.
3. Independently verify complete native target correctness before releasing a
   new bounded startup resource acquisition. Its contract must preserve original
   data/graphs/module/identity, one snapshot/four scans, reader orders/holds,
   time/CPU/memory/SQL/storage/cleanup ceilings and zero searches.
4. Apply the unchanged total peak +2GiB reserve +2GiB workspace <=32GiB rule,
   with no positive limit/OOM event and no cache subtraction. Full-workload,
   quality/A/A/performance and B2f release remain separate even after a scoped pass.

**There are no Torch commands for this A3 decision/prototype.** Native commands
must wait for those concrete integration, correctness and release checks.

For repeatable local consumer tests, without overwriting a receipt:

```bash
cd /Users/danielarturi/Developer/JinyangLiWork
PYTHONDONTWRITEBYTECODE=1 agent/.venv/bin/python -B -m unittest discover \
  -s agent/experiments/startup-exact-vector-v1 -p 'test_*.py' -v
```

[Guarded checks](../trials/torch-reviews-startup-exact-vector-v1/local-checks-guarded.log),
[A2 verified basis](fannagent-startup-attribution-main-A2-postrun-2026-10-30.md).
