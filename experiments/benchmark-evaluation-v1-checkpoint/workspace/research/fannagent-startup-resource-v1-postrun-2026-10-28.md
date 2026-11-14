# Startup-only resource qualification: verified return

Analysis date: October 28, 2026, America/New_York. Protocol: `startup-resource.v1`.
Campaign: `reviews-startup-resource-v1-20261028T020546Z.zdsnk75c`.
Torch job: `21171789_0`.

The job completed successfully, including startup, snapshot validation, both
reader-creation epochs, final integrity checks and cleanup. The frozen verdict is
**`startup_complete_resource_margin_inconclusive`**. Startup execution is now
verified on Torch; the required memory margin is not demonstrated. Full B2f
calibration remains held. No speed, recall or A/A result is produced.

## Archive and reconstruction

The 934,849-byte archive passes its SHA256 sidecar:
`312bf5c02959a1e90514f6ec556914303095eb30c2f87acd9b182010a28320e7`.
All 46 archive members are regular, safe paths and match the extracted raw bytes,
with no additional extracted files. The sealed package manifest remains
`4212507e81abc053aa5045e09a8cb624b789ed0bad4e1e8d1bf69f82f31484d9`.
Every sealed file matches its manifest. A fresh trusted, sealed analyzer replay
matches the download-time analysis exactly; it writes to a separate directory and
preserves the earlier analysis.

The analyzer verifies scheduler/job/package identities, guest and final host
locks, absolute host interpreter/export, stage/SQL limits, request and reader
lifecycle, target/settings/placement/snapshot/copy/source identities, final graph/
module/data/catalog proofs, clean server shutdown, source preservation and memory
coverage. The original source clusters were never started or altered. Initial and
final protected-source evidence agrees. The local postrun preservation receipt
covers 3,442 immutable inputs, including the earlier 3,123 pins, new experiment
source/seal, returned raw and download-time analysis.

| Acquisition check | Verified result |
| --- | --- |
| Slurm terminal state | COMPLETED, exit `0:0`; 13 minutes 28 seconds |
| Runtime acquisition/finalization | 670.390 seconds |
| ANN / exact / executed requests | 0 / 0 / 0 |
| Exposed requests admitted | 200, never executed |
| Readers / maximum live | 10 / 6; both fixed creation orders |
| Database work | 1 snapshot scan, 4 data-verification scans; 171 startup and 56 observer SQL statements |
| Prohibited SQL attempts / plan packets | 0 / 0 |
| Provider calls / fits / confirmations | 0 / 0 / 0 |
| Integrity and cleanup | Final proof verified; working servers stopped; retained/protected sources unchanged |
| Host memory sampler | Complete, 806 frames across 805.039 seconds; largest inter-frame gap 1.030291 seconds |
| Sampler overhead/caps | 4.106 CPU seconds, 75,247 file reads, 29,648,643 bytes read, 11,219,581 raw bytes; all frozen caps satisfied |

The scheduler's later `squeue` message about an invalid job ID is consistent with
a completed job leaving the live queue. Terminal `sacct`, runtime and host records
agree; it does not indicate a new failure.

## Frozen memory gate

The compute trace establishes cgroup v2 and finite 32 GiB limits at the job and
step-user ancestors. All observed job swap usage and its swap limit are zero.
The job-level counters start at zero; its kernel aggregate peak grows from about
40 MiB to exactly 32 GiB during the observed run. Broad system/Slurm ancestor
statistics are not attributed to this job or added to its totals.

| Frozen requirement | Observed | Decision |
| --- | --- | --- |
| Aggregate peak + 2 GiB reserve + 2 GiB workspace allowance must fit 32 GiB | 32 + 2 + 2 = 36 GiB | Required margin short by 4 GiB |
| No positive limit/OOM event delta | `memory.events.max` +592 at the job ancestor | Does not pass |
| OOM / OOM-kill / group-OOM event delta | 0 / 0 / 0 | No recorded OOM event or kill |
| Mapping, phases, sampling and counter coverage | Complete | Supports interpretation of the nonqualifying result |

At a 32 GiB request, this contract requires an observed aggregate peak at or below
28 GiB **and** no prohibited event delta. The observed peak is constrained by the
limit; unconstrained demand is unknown. The 4 GiB gate shortfall is not proof that
a 4 GiB code reduction, or a 36 GiB request, would be sufficient in another run.
Neither the margins nor the resource cap are changed retrospectively.

Linux defines the `max` counter as attempts to exceed the boundary; reclaim can
avoid an OOM. `memory.stat.file` includes filesystem cache, tmpfs and shared
memory, so it is not a separate additive quantity alongside `shmem`.
[Linux cgroup v2 documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html).
Slurm's cgroup-v2 RSS/MaxRSS includes file cache unless `no_file_cache` is set.
[Slurm cgroup v2 accounting](https://slurm.schedmd.com/cgroup_v2.html).
The saved site configuration reports no such option. This return reports Slurm
MaxRSS `33532588K`, approximately 31.9792 GiB; the direct job-cgroup peak is 32 GiB.
Cache is still charged under the real limit and cannot be subtracted to rescue
this gate. Its reclaimability is not measured here.

## Where pressure occurred

All 592 job limit events accumulate in two adjacent `snapshot_load` sampling
frames: increments of 508 and 84. No further increment occurs during the reader
holds or final verification. Snapshot loading/constructor/identity work lasts
117.844 seconds; the phase boundary does not distinguish those internal steps.

| Phase | Largest sampled job charge, GiB | Job limit-event increment |
| --- | ---: | ---: |
| Host preflight | 15.5098 | 0 |
| Restore and identity checks | 23.1795 | 0 |
| Snapshot loading | 31.9973 | 592 |
| First reader hold | 27.4817 | 0 |
| Second reader hold | 27.1908 | 0 |
| Final verification / cleanup | 28.6098 | 0 |

These are descriptive sampled currents, not phase-specific kernel peaks or
independent repeated measurements. The entire prior peak remains charged to the
frozen gate even after current usage declines.

The near-peak frame records 31.997318 GiB total job charge, with about 14.875885 GiB
`anon`, 17.056358 GiB `file`, and 0.064476 GiB `kernel`. Interface reads are
sequential, not atomic; nested components are not added or subtracted. The actual
runtime maps from container PID 14 to host PID 3254493 with matching starttime and
has a 15.030392 GiB RSS high-water value. Process RSS is a separate measure from
job memory charge. Component maxima elsewhere in the trace are not simultaneous
and must not be summed.

Read-only inspection of the **actual frozen source** identifies candidate
mechanisms, not a measured per-allocation cause:

- `fannagent_pgvector/backend.py::snapshot` decodes every vector into a Python list
  and retains all row dictionaries before constructing the snapshot.
- `fannagent/snapshot.py::Snapshot.__init__` retains those rows and also constructs
  a float32 NumPy vector matrix.
- The snapshot's identity calls `digest` over all rows/fields. In
  `fannagent/store.py`, `canonical` materializes a complete JSON string and then
  UTF-8 bytes before hashing.

The trace localizes pressure to this combined path. It does not prove how much
would be saved by streaming the canonical encoding or changing row storage, nor
that either change alone would satisfy the unchanged resource gate. The source
hashes and exact frame/component calculations are retained in the metrics record.

## Decision and revised critical path

The bounded startup-only acquisition is complete and closed with its recorded
inconclusive margin verdict. It is not another harness failure, a full workload
memory qualification, or authorization to repeat or enlarge the job. The three
failed calibration attempts remain spent; this separate resource allocation also
remains spent. B2d stays `measurement_inconclusive`, original execution is retained,
and B1c remains deferred.

The next step is **NEXT-STARTUP-MEMORY-01**, a read-only snapshot-memory and identity
compatibility audit. Inventory the live representations, allocation lifetimes,
canonical-byte/identity requirements and downstream consumers using existing
source/evidence. Compare prospective bounded-memory remedies, including
incremental identity encoding and reduced duplicate representation, and specify
which source/protocol boundary each would amend. Preserve validation, all rows,
float semantics, exact identities, policies, data, graphs and module. No change or
new allocation is authorized by this postrun analysis.

Critical path: verified startup return → memory/identity compatibility audit →
prospective correction and local-equivalence/resource design → separately
requested implementation/local checks → newly authorized zero-search resource
qualification → independent resource decision → only then a separate full B2f
release/workload-memory review and native scientific gates. Unsupported remedies
return to review; no automatic resource increase, cache subtraction or calibration
submission follows. No Torch command is needed now.

## Evidence and reproduction

- [Raw campaign](../trials/torch-reviews-startup-resource-v1/returned/reviews-startup-resource-v1-20261028T020546Z.zdsnk75c/).
- [Archive/member verification](../trials/torch-reviews-startup-resource-v1/postrun-audit-2026-10-28/archive-verification.json).
- [Fresh sealed reconstruction](../trials/torch-reviews-startup-resource-v1/postrun-audit-2026-10-28/replay/resource.json).
- [Independent phase/component/source metrics](../trials/torch-reviews-startup-resource-v1/postrun-audit-2026-10-28/metrics.json).
- [Postrun receipt](../agent/docs/verification/startup-resource-v1-postrun.json).
- [Frozen design](fannagent-startup-resource-v1-design-2026-10-27.md).

Read-only local replay, preserving the existing download-time analysis:

```bash
PYTHONDONTWRITEBYTECODE=1 \
  /Users/danielarturi/Developer/JinyangLiWork/agent/.venv/bin/python \
  /Users/danielarturi/Developer/JinyangLiWork/trials/torch-reviews-startup-resource-v1/torch-startup-resource-v1/experiment.py analyze \
  --campaign /Users/danielarturi/Developer/JinyangLiWork/trials/torch-reviews-startup-resource-v1/returned/reviews-startup-resource-v1-20261028T020546Z.zdsnk75c \
  --output /private/tmp/startup-resource-replay-unique-output
```

Use a fresh output directory. The original archive/raw/seal and analysis remain
immutable. This analysis ran no new tests, databases, searches, fits, remote calls,
provider calls or experiments, and changed no implementation code.
