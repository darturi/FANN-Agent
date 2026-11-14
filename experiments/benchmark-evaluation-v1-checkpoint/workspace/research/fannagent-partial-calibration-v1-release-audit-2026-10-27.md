# B2f release audit after three startup failures

October 27, 2026, America/New_York. Status: **release held**.
The scientific contract remains partial-calibration.v1 / NEXT-PARTIAL-CALIBRATION-01.
This audit does not release another Torch allocation.

## Verified third failure

Campaign reviews-partial-calibration-v1-metadata-fix-20261028T000153Z.y1p9092a,
job21159802_0, FAILED/1:0 after10m44s. The UTC timestamp is October27 locally.
The downloaded archive SHA256 is
`7e383c42372f1953700dd0743f737d3b83f65be301c31d7bda8863d6006ba21e`.
All30 regular members match extracted bytes; raw failed lock, exact previous
package/submission/job identities and scheduler termination verify.

Two readers were admitted; zero backend/search SQL calls, operations, plan
packets, provider calls, fits and confirmation queries ran. No quality, A/A or
performance result exists. Final measurement integrity was not reached.
Both complete source inventories match:2,587 files/4,603,663,760 bytes. Independent
whole-pgdata copy proofs, copied pinned identity sidecars and initial catalogs
match. Protected input receipts match; both reader connections closed and both
working databases shut down, with no recorded cleanup error and shutdown logs.
The original source was never started by this campaign.

All three attempts remain spent:21111616_0/4s (launcher),21129331_0/8m34s
(missing sidecar),21159802_0/10m44s (eligibility guard). Their combined scheduler
elapsed time is19m22s; these are three separate allocations, all with zero ANN
searches. This is an experiment-harness release failure, with repeated missing
startup coverage. It supplies no evidence against the ANN mechanism.

## Root cause and corrective work

The third runtime constructs `{field_map, source_ids, votes}` for hashing. The
pinned eligibility.json has only `{source_ids, votes}`. The same canonical
encoder is used, so including the extra key guarantees a mismatch even with
unchanged IDs/votes. The failure message alone did not prove data drift.

Earlier real-backend tests called acquisition directly and skipped this guard
in pc_runtime.main. Adding real backend methods did not cover the surrounding
startup control flow. Test count and synthetic gate passes were insufficient
release evidence.

The new isolated partial-calibration-v1-identity-fix source keeps eligibility
bytes/schema unchanged and compares only those two keys. It checks the exact
logical field map separately and restores the explicit frozen snapshot identity
comparison present in B2d. That identity covers vectors/metadata/fields; the
existing complete ID/vote/vector-bit guards remain unchanged. Startup now emits
a separate snapshot-qualified proof, required by trusted complete-raw analysis.
Neither a validator nor a pinned identity is weakened.

There is deliberately no production seal, tarball, transfer helper or fourth-job
handoff. The builder rejects non-test packaging. Temporary synthetic packages
remain non-submittable. Historical source/releases/raw/bindings/reservations
stay preserved; production code is unchanged.

## Boundary audit and validation matrix

| Boundary | Local audit/check | Remaining native limitation |
| --- | --- | --- |
| Submission → batch → srun | Existing actual-shell restricted-export regression and absolute interpreter checks retained | Site executable/Slurm availability is only observed on the cluster |
| Host → container | Existing bind/env/path/ownership tests; source is read-only and work separate | Actual container mount, image/kernel and quota availability |
| Retained source → working envelope | Existing full inventory/independent inode/auth/sidecar checks; latest real failed archive proves preservation | Future source availability/clean state must still pass |
| Working server → catalog/data | Full entry-point fixture includes role-specific catalog path and settings; source comparison remains strict | Live full-data float32-bit proof and real server behavior remain native |
| Actual backend construction/binding | Both actual frozen target constructors, admission/bind acknowledgements and SQL settings exercised with synthetic I/O | Real module/reader compatibility remains native |
| Snapshot → pinned identities → requests | Runtime and fixtures use the same whole startup function; full247,286-ID/vote fixture; actual40-row frozen snapshot; changed schema/IDs/votes/mapping/dataset negatives | Full-size snapshot memory and real data identity remain native |
| Thread/core/proc admission | Existing negative ownership/PID/namespace/topology/migration/counter tests retained | Actual four-core mask and required proc capability remain native |
| Full entry point → acquisition | pc_runtime.main itself completes both epochs with actual frozen backend methods and exact16,242/4,200/10 counts; OS/DB replies synthetic | No measured native latency/quality inferred |
| Acquisition → final verification → cleanup | Entry-point tests reach final audits; identity/catalog/server failure paths close resources; cleanup error fails qualification | Future actual source/graph/module/clean shutdown still mandatory |
| Returned raw → trusted decision | Existing complete mocked replay/all56 calculations; new snapshot proof required | Only complete future native raw can qualify calibration |
| Memory/resource release gate | Review recorded peak, frozen loader/identity source and old estimate; request read-only accounting configuration | Open: peak attribution/full-run headroom; release blocked |

The full entry-point fixture mocks container paths, PostgreSQL responses,
process/resource interfaces, full-data validator outputs and graph files; it
invokes no actual database/process/SSH/provider/native ANN. It uses the actual
frozen reader and native/exact SQL methods. Synthetic final proofs are assertions
about control flow, not evidence that real data, graphs or resources qualify.
The full-size fixture reads only previously exposed ID/vote eligibility, without
loading dataset vectors. No new scientific measurement or fit is performed.

## Memory assessment and next decision

Recorded MaxRSS33534232K converts to31.9807GiB if K denotesKiB, versus a32GiB
request. The job records the explicit guard exception and FAILED/1:0; it does not
record OUT_OF_MEMORY. Do not identify memory as the observed failure cause.

Slurm's MaxRSS interpretation depends on its accounting plugin. With cgroup/v2,
filesystem cache can be included unless no_file_cache is configured. A single
MaxRSS therefore does not establish anonymous-RAM use or remaining headroom.
[Slurm accounting fields](https://slurm.schedmd.com/sacct.html),
[Slurm cgroup accounting](https://slurm.schedmd.com/cgroups.html),
[Slurm accounting configuration](https://slurm.schedmd.com/slurm.conf.html).
The site configuration is not in this raw archive and is requested read-only.

The frozen snapshot loads247,286×768=189,915,648 Python vector components and
retains a float32 matrix (759,662,592 bytes). Its identity code materializes a
canonical full JSON string and encoded bytes; the DB result rows can coexist
until loading returns. Source order makes this a plausible startup peak; no
component attribution or exact peak is claimed. The existing configured
14.25GiB estimate includes a fixed12GiB allowance and is not a verified upper
bound for this whole Python/container/accounting lifecycle. It must not be used
as a readiness guarantee.

Next gates, in order:

1. Verify and preserve all three failures; reproduce each exact harness defect.
2. Pass the actual runtime-entry-point startup/acquisition/finalization fixture,
   direct full-size eligibility schema checks and negative regressions; audit
   the host/container/resource seams and publish exact coverage limitations.
3. Obtain the read-only accounting configuration, separate observed failure from
   peak-memory attribution, and decide whether the frozen32GiB scope is feasible.
   Configuration alone may be insufficient. If headroom remains unsupported,
   design a separate bounded resource qualification or prospective amendment
   before releasing a calibration attempt. Do not silently raise memory or
   rewrite the frozen snapshot implementation.
4. Only after documented release/resource review: seal and check a separate
   release with prior evidence preserved and any additional allocation stated
   explicitly. No such release or allocation is supplied here.
5. A future native run must still pass N0 identity/resources/cores/telemetry →
   conformance/quality → both full epochs → final integrity/cleanup → independent
   all56 unchanged-margin intervals. A scoped pass only permits later treatment
   design review. B2d stays measurement_inconclusive, original execution retained,
   B1c deferred; no retrospective speed/adoption result.

The only user command currently requested submits no job:

```bash
scontrol show config | awk '/JobAcctGatherType|JobAcctGatherParams|ProctrackType|TaskPlugin/'
```

## Evidence and reproduction

- [Third failure verification](../trials/torch-reviews-partial-calibration-v1-identity-fix/failed-archive-verification.json).
- [Local check and preservation records](../trials/torch-reviews-partial-calibration-v1-identity-fix/).
- [Isolated correction source](../agent/experiments/partial-calibration-v1-identity-fix/README.md).
- [Implementation/audit receipt](../agent/docs/verification/partial-calibration-v1-identity-fix-implementation.json).
- [Frozen design](fannagent-partial-calibration-v1-design-2026-10-26.md).
- Actual pinned project sources: metadata-fix pc_runtime.main (three-key guard);
  B2d pa_runtime (two-key eligibility plus dataset identity); frozen Snapshot/store
  canonical encoder; frozen backend.snapshot loader. Their hashes are retained
  in preservation/scientific-parity records, without editing those sources.

Exact final test counts/static/preservation status are recorded in the receipt.
Synthetic correctness remains separate from native/resource qualification.

Final local suite: **119/119 pass**, including six actual entry-point lifecycle
checks and all inherited acquisition/reconstruction/launcher/negative checks.
Lint/format/26 Python ASTs/shell syntax pass. All18 selected scientific/native
files match the prior source exactly; all3,065 prior pins remain unchanged.
During the first combined local suite, the strengthened proof exposed an old
votes-only synthetic replay fixture. It was corrected to the complete frozen
ID/vote schema before the final run; that failed local log/receipt are retained.
No production/sealed release is claimed. R2 resource feasibility stays open.
