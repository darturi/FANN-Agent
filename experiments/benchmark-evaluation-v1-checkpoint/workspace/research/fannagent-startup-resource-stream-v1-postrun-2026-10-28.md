# Snapshot identity streaming: verified startup-only return

Analysis date: October 28, 2026, America/New_York. Protocol: `startup-resource.stream.v1`.
Campaign: `reviews-startup-resource-stream-v1-20261028T151219Z.hmj9cwut`.
Torch job: `21224521_0`.

The job completed successfully. The streaming implementation reproduces the exact
original snapshot identity, restores the original binding and completes both
reader epochs, final integrity verification and cleanup. Its frozen verdict is
**`startup_complete_resource_margin_inconclusive`**. The correction is compatible
with this actual full-size startup, but does not establish the required total-job
memory margin. Full B2f calibration remains held. There is no recall, A/A or search
performance result because the job performs zero ANN/exact searches.

## Verification and scope

The 829,195-byte archive passes its SHA256 sidecar:
`63ff9b4800faab0a0ece6955ccabfb9c512548a35909cbca0e9b175a73ab3fef`.
All 48 regular members have safe unique paths and exactly match extracted raw,
without additional extracted files. The original 346-file seal remains intact;
manifest SHA256 is
`26a7d66b67137e77d5208d7b851b19d980a8a64060defc25cbe418db17190354`.
The sealed package archive also matches its release receipt. Fresh trusted local
reconstruction exactly matches the preserved download-time `resource.json`.
Returned code is not executed.

The sealed analyzer verifies scheduler/package/campaign identity, guest/final host
locks, startup/SQL/phase/sampler budgets, placement, snapshot/admission/reader
lifecycle, original data/catalog/graphs/native module/source/sidecars, final
integrity and clean shutdown. Protected retained sources agree before/after.
The local preservation check covers 3,947 prior/release/raw/analysis inputs,
including all 3,468 earlier pins. Implementation source and existing evidence are
unchanged. This review runs only existing-data reconstruction/analysis; no native
DB, search, provider, fit, SSH, Torch job or new scientific experiment.

| Acquisition check | Verified result |
| --- | --- |
| Scheduler | COMPLETED, exit `0:0`, 11m55s; four CPUs, 32 GiB |
| Runtime acquisition/finalization | 589.732 seconds |
| ANN / exact / executed requests | 0 / 0 / 0 |
| Requests admitted / epochs | 200 / 2 |
| Reader admissions / maximum live | 10 / 6; both frozen creation orders |
| Data work | One snapshot scan and four data-verification scans |
| SQL | 171 startup + 56 observer; zero search/prohibited attempts/plan packets |
| Provider calls / fits / confirmations | 0 / 0 / 0 |
| Integrity / cleanup | Verified; all readers closed, working databases stopped, sources protected |
| Memory coverage | 712 frames over 711.033s; maximum gap 1.029625s; host/container process mapping verified |
| Sampler charges | 3.048 CPU seconds; 66,595 reads; 26,250,235 read bytes; 9,885,100 raw bytes, within unchanged caps |

The post-completion `squeue` invalid-job-ID message is consistent with absence from
the live queue; scheduler terminal records, runtime and host exit agree.

## Exact full-size identity compatibility

Eight actual-container preflight cases pass using CPython 3.12.15 and the original
encoder, consuming 527 oracle bytes and 0.000297 CPU seconds. The provenance
matches between preflight and real construction and agrees with the sealed helper
and unchanged snapshot/store source.

| Streaming requirement | Verified result |
| --- | --- |
| Original snapshot identity | `54282be380f20bfab05a44e6260e116435aecf5a289a258ae8164a23c187b303` |
| Rows / original-canonical component calls | 247,286 / 247,287 |
| Total encoded bytes | 2,374,063,027 (2.211019 GiB), incrementally hashed |
| Fields / row bytes / separators / framing | 130 / 2,373,815,591 / 247,285 / 21 |
| Largest row / pending buffer | 9,690 bytes / 65,536 bytes |
| Hash updates / invocations | 36,226 / exactly one |
| Completion / binding restoration | Both verified before later validation/admission |
| Identity encoding elapsed | 61.463 seconds inside the existing deadline |

The combined snapshot load/constructor/identity stage takes 99.927 seconds,
including 38.262 seconds before the stream phase and a 5.694-second snapshot SQL
execution. SQL timing does not isolate client decoding/constructor allocations.
The 600-second stage cap remains satisfied. No full-document buffer is created by
the new helper; its 64 KiB pending-buffer bound is not a bound on the constructor,
retained snapshot, database client or total job memory.

## Frozen resource gate and comparison

| Measure | Original startup job | Identity-stream job | Interpretation |
| --- | ---: | ---: | --- |
| Aggregate kernel job peak | 32.000 GiB | 32.000 GiB | No demonstrated improvement in the governing peak |
| Effective finite limit | 32 GiB | 32 GiB | Unchanged |
| Peak + 2 GiB reserve + 2 GiB workspace | 36 GiB | 36 GiB | Both exceed the limit by 4 GiB |
| Job `max` event delta | 592 | 259 | Both fail the required no-event condition |
| OOM / OOM-kill / group-OOM deltas | 0 / 0 / 0 | 0 / 0 / 0 | Neither records an OOM or kill |
| Runtime-process RSS high-water | 15.030 GiB | 11.323 GiB | Observed decrease of 3.707 GiB / 24.66% |
| Combined snapshot stage | 117.844s | 99.927s | Descriptive elapsed-time difference |
| Scheduler elapsed | 13m28s | 11m55s | Descriptive total-job difference |

The process-memory decrease is consistent with removing large transient identity
buffers. These are separate single jobs, not a randomized paired memory or timing
comparison: the decrease does not establish a causal saving of exactly 3.707 GiB,
a search-speed improvement or a portable effect. Process RSS and aggregate job
charge measure different things. They must not be substituted or subtracted.
The aggregate peak is still constrained at the limit, so unconstrained demand is
unknown. Lower event counts do not qualify a gate requiring zero events.

At this limit the frozen rule requires peak at most 28 GiB **and** no prohibited
event delta. Both conditions remain unmet. No cache is subtracted, no margin or
cap is changed, and a larger allocation is not inferred to be sufficient.

## Where the remaining pressure is observed

| Phase label | Largest sampled job charge, GiB | Sample-label `max` delta |
| --- | ---: | ---: |
| Host preflight | 15.906 | 0 |
| Restore/identity verification | 23.488 | 0 |
| Snapshot load before stream | 32.000 | 114 |
| Identity stream | 31.292 | 76, at the load/stream boundary |
| First reader hold | 31.306 | 0 |
| Second reader hold | 31.306 | 0 |
| Final verification/cleanup | 32.000 | 69, including 68 at its initial boundary |

Counter deltas cover intervals between reads. Exact phase attribution requires
checking those intervals against phase transitions, not simply assigning the
later sample's label. There are **114 events wholly bracketed before hashing**,
**76 across the load/stream boundary**, **68 across the second-hold/finalization
boundary**, and **one wholly bracketed within finalization**. No additional events
are observed in the interior of the subsequent stream samples. The two boundary
deltas cannot be assigned entirely to one side. These details are retained in the
independent phase-attribution receipt.

A near-peak pre-stream frame contains 31.999931 GiB current charge, about
9.943089 GiB `anon`, 21.984222 GiB `file` and 0.072178 GiB `kernel`. During the
holds, runtime RSS is about 10.602 GiB while job charge is about 31.306 GiB; one
frame records about 10.658 GiB anonymous and 20.572 GiB file charge. Components
come from sequential interface reads, are not atomic allocation measurements, and
nested `shmem` is not added to `file`. Separate component maxima are not summed.

This proves that hashing is not the sole remaining pressure source. The trace
supports investigating snapshot loading/retained representations and verification
I/O working sets. It does not isolate which client/constructor allocation or file
caused a specific charge, establish reclaimability, or qualify a cursor/storage/
cache remedy. The unchanged source still retains original decoded rows and the
NumPy representation; the earlier source audit also records client-buffered
snapshot loading and named-cursor data-verification scans.

## Decision and next step

M3 is complete and closed as **resource-margin inconclusive**. Its exact identity,
startup, lifecycle and cleanup gates pass; its resource gate does not. This fifth
total consumed allocation consists of three failed calibration attempts and two
completed startup-only resource jobs. Every package/raw/binding/reservation stays
spent; do not rerun the M3 submit commands.

The next step is **NEXT-STARTUP-MEMORY-02, a read-only working-set audit** using the
two existing traces and pinned source:

1. Separate snapshot client buffering, decoding, retained rows/matrix and
   verification-read lifetimes from observed job/file/anonymous charges. Preserve
   all uncertainty about allocation identity and sequential sampling boundaries.
2. Review actual consumer/validation/ordering/transaction constraints and the
   existing verification I/O paths. Assess whether any next remedy can preserve
   exact identities, unchanged data/graphs/module/policies and the same resource
   gate. Do not assume a server cursor or cache-control operation is already safe.
3. Produce a GO/no-GO and, only if justified, a separately frozen bounded design
   with explicit equivalence/resource tests. If existing evidence cannot resolve
   a necessary fact, specify the smallest targeted measurement rather than
   launching it. No implementation or new allocation follows automatically.

Revised critical path: verified M3 nonpass → existing-source/trace working-set
review → separate design decision → separately requested implementation/local
readiness → only then any separately released native resource qualification →
possible full-workload memory/release review and full B2f gates. Original execution
is retained; B2d remains measurement-inconclusive, and B1c stays deferred.

**No Torch commands are needed now.** Full calibration remains held.

[Independent archive/replay/metrics/preservation evidence](../trials/torch-reviews-startup-resource-stream-v1/postrun-audit-2026-10-28/).
[Postrun receipt](../agent/docs/verification/startup-resource-stream-v1-postrun.json).
[Original resource-return report](fannagent-startup-resource-v1-postrun-2026-10-28.md).
[Roadmap](fannagent-performance-research-roadmap-2026-10-22.md).
