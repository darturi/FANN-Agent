# B2f instrumented A/A calibration — launcher correction

Isolated infrastructure revision `partial-calibration.v1.launch-fix` of the unchanged
`partial-calibration.v1` / NEXT-PARTIAL-CALIBRATION-01 contract.
See LAUNCH-CORRECTION.md for the verified failure, absolute interpreter/export fix
and explicitly separate additional-allocation handoff.
The byte-identical DESIGN.md, CONTRACT.json and SCHEDULE.json are the prospective
scientific record. Their historical “design only” status describes their freeze;
the later implementation does not rewrite it.

This package asks whether identical readers can meet the unchanged equivalence
margins in a defined regime. It cannot establish a partial-index speedup or repair
B2d. Original execution remains retained and B1c deferred.

## Execution and guards

`pc_control.py` reserves one separately named campaign before dispatch, preserves
uncertain submissions, and collects raw data for successful or failed terminal
jobs. It never retries. `pc_job.py` verifies prior evidence and quota/footprint
floors, then binds the retained stopped clusters read-only into the pinned image.
`pc_restore.py` requires matching pg_controldata clean shutdown, inventories every
file, rejects links/special/foreign-owned entries, and makes independent whole
copies with unchanged authentication. It never starts the retained source.

The unchanged native backend/module/data/graphs/policies remain pinned. Only the
new copies can start. Full input ID/metadata/vector-bit parity, complete recorded
catalogs/statistics and graph/module hashes must pass before search and after
measurement. Failed cleanup cannot qualify. Startup logs and failed raw remain
collectible; no implicit replacement graph or larger run is allowed.

One Slurm allocation: 3 hours, 4 CPUs, 32 GiB. An srun step establishes the task
mask; qualification requires exactly four distinct physical cores within that
mask. C0 is the client, C3 administrators/postmasters/background, C1/C2 the cells,
swapped in epoch 1. Proc records bind each reader to PID/start ticks/server/socket
and enforce affinity, thread, namespace and monotonic-counter guards. Optional
schedstat, NUMA and frequency metadata have explicit availability semantics.

Two main readers remain open; four fresh formal readers are created and closed
per epoch, with reversed creation order. Maximum 10 reader admissions, six live
readers and two existing administrators. Each primary burst has two conditioning
searches, then four on-reader warmups and three retained calls. Proc samples sit
outside that seven-call interval, and SQL/result trace writes are buffered.
Diagnostic ON/OFF uses the frozen eight vectors and per-call proc bracketing in
both modes. Only ON adds the specified plan packets. It is descriptive only.

Complete acquisition is exactly 16,242 attempted searches, 4,200 plan packets,
4,800 primary retained calls and 384 diagnostic retained calls. A valid quality
stop occurs at 610 searches. The other 560 attempts in the outer envelope cannot
be spent. Fixed stage, SQL, proc-read, affinity, telemetry-time and evidence-size
ceilings apply. No provider calls, fits or protected queries are permitted.

`pc_report.py` uses only trusted local sealed code to reconstruct returned data:
raw locks, package/campaign/Slurm identities, copy/source/final proofs, complete
orders/counts, truth/results, plans, physical identities and telemetry. All 56
physical-pair, temporal-half and adjacent-retained intervals are required at the
original margins. Diagnostics and crossed labels cannot rescue a failure.
Complete all-pass means `calibration_qualified_scoped`, permitting only later
treatment-design review; other complete timing outcomes are
`calibration_inconclusive`. Missing proof prevents qualification. Failed raw is
preserved without a selected-subset verdict or automatic retry.

## Local correctness

Run only from the local workspace, with its pinned dependencies available:

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/danielarturi/Developer/JinyangLiWork/agent/.venv/bin/python \
  /Users/danielarturi/Developer/JinyangLiWork/agent/experiments/partial-calibration-v1-launch-fix/run_checks.py \
  --phase source --receipt /private/tmp/b2f-local-checks.json
```

The tests use synthetic connections and process files, including a full mocked
acquisition and independent raw reconstruction. They do not start PostgreSQL,
execute native ANN, contact Torch/providers, or establish performance/availability.
The release receipt separately records source and sealed-package checks,
archive-member parity and preservation of earlier files.

## Torch handoff

Use the exact release commands in
`/Users/danielarturi/Developer/JinyangLiWork/trials/torch-reviews-partial-calibration-v1-launch-fix/COMMANDS.txt`.
The accompanying transfer.sh performs interactive MFA before reading binding JSON,
checks both transfer hashes and invokes the trusted local sealed verifier after
collection. Preserve all packages, reservations and bindings on failure.
