# Startup-only resource qualification implementation and handoff

October 27, 2026 America/New_York. NEXT-STARTUP-RESOURCE-01 / startup-resource.v1.

The separately frozen startup-only study is implemented in
agent/experiments/startup-resource-v1. It requests one additional one-hour, four-CPU, 32 GiB
allocation beyond the three spent calibration attempts. No full calibration is
released, and no native experiment/job is run by Codex.

## Frozen identity and zero-search boundary

[Design](fannagent-startup-resource-v1-design-2026-10-27.md) SHA256:
`fbe4ffbf95f983018ed112b778af637c39ff3fe807ac17176d84bbc66fbb5fc0`.
Resource contract SHA256:
`a4120866fea72befae75e485bc05bc7265314eb64b85839e5436e4c480339b90`.
Both were saved before implementation. The original B2f design/contract/schedule,
data, full/partial graphs, module, image, policies and margins are preserved.
The prior held calibration source/reports/seals/raw/bindings/reservations remain
unchanged; the new study uses its own package/prefix/binding/reservation.

Zero ANN and exact searches is enforced at three independent boundaries:
private search methods raise, search-operation reservations always raise, and the
traced SQL boundary admits only exact role/settings/binding/catalog/full-data/
snapshot/PID queries. Unknown SQL, distance ordering, EXPLAIN, unexpected settings
or targets and excess scans are rejected before driver execution. One snapshot,
four full data-verification scans, ten admissions/maximum six live readers and zero
plan packets are independently reconstructed. The 200 exposed requests are
validated but never executed. Full database verification/admission SQL still runs.

The runtime uses actual frozen constructors/binding/snapshot and the corrected
eligibility guard. It hashes only the pinned source_ids/votes schema, separately
checks exact field mapping and full snapshot identity, and copies/rechecks the
pinned private identity sidecar before any database copy. Both fixed reader
creation orders and CPU crossover are exercised without priming or query work.
Default read-only/plan-cache state and physical reader/core identities are audited.

## Resource accounting and lifecycle

A separate host process starts before original-bundle validation and continues
through source postflight/cleanup, avoiding the client's snapshot/GIL limitation.
It resolves actual memory-cgroup membership and mount roots for v1/v2, samples
visible ancestors, records finite/unlimited/absent root controls correctly, and
captures aggregate/current/peak/component/event plus PID/starttime/RSS data.
The sampler is pinned to C3; actual host/container/core mapping is retained.
It never writes cgroup controls, resets peaks, drops caches or probes other jobs.

A missing basic mapping/counter, stale/unhealthy sampler, unexpected process/group
or resource cap requests bounded failure/cleanup. Optional missing peak/event
coverage and observation gaps cannot produce a positive resource margin. Source
integrity and clean working-server shutdown remain necessary on complete returns.
The original source is read-only and never started.

Host launch uses the verified absolute interpreter and explicit step export.
Guest evidence locks exclude live host memory files and their atomic temporary
files. A final host lock covers all data after sampler join and protection checks.
Terminal startup/host/sampler failures remain collectible; no automatic retry or
reservation reset exists. The transfer helper verifies both remote files before
printing UPLOAD VERIFIED, after interactive MFA.

The independent local analyzer checks package/campaign/scheduler/locks, all
zero-search SQL and scan counts, actual reader admission/order/lifetime/settings/
physical placement, snapshot/source/copy/final/cleanup and host-sampler evidence.
It computes the frozen total-charge rule without subtracting cache: largest
observed finite-ancestor kernel peak + 2 GiB reserve + 2 GiB outstanding-work allowance
must fit the smallest observed finite limit capped at 32 GiB. Limit/OOM deltas,
missing coverage or gaps prevent a margin pass. It reports component and process
high-water values separately without claiming simultaneous maxima.

A complete startup near the memory cap is resource-margin inconclusive, even if
cache is large. It is not automatically an OOM or a reason to increase resources.
A scoped margin pass cannot establish per-search memory, recall, A/A, speed,
adoption or readiness to run full calibration without its separate review.

## Local checks and release evidence

The final source and sealed package each passed **117 tests**, with zero failures
or errors. AST parsing, Ruff checks and formatting under the repository's Python
configuration, and Bash syntax checks passed. The dynamic frozen `fannagent`
imports are explicitly classified as first-party for import sorting; embedded
prior evidence is preserved byte for byte. Coverage includes:

- Actual shell launcher under restricted PATH/export, absolute argument roundtrip,
  unavailable/relative interpreter rejection and once-only/unknown dispatch.
- Actual host and container-runtime entry points with mocked OS/DB boundaries;
  actual frozen constructors/binding/snapshot methods; complete ten-admission
  lifecycle, final audits and zero-search SQL accounting.
- All three earlier failure mechanisms, changed snapshot/data/field/eligibility,
  missing/tampered/symlink sidecar, copy independence, sampler loss and cleanup
  failure; failed startup cannot qualify.
- v1/v2 membership/mount-root/root-interface/ancestor handling, changed/negative/
  reset/missing counters, PID replacement/disappearance, sampler caps/health/
  affinity and complete/negative memory decisions without cache rescue.
- Independent full returned-data reconstruction and rejection of modified locks,
  scope/counts/readers/snapshot/source/final/cleanup; path/symlink/archive guards.
- Actual upload script with local mocked SSH/SCP for authentication/transfer/
  remote-checksum failure and success; no real network or native experiment.

Database rows, processes, resource interfaces, full-data validation outputs and
large graph proofs in entry-point/replay fixtures are synthetic. Forty synthetic
vectors exercise actual frozen snapshot methods; a separate 247,286-ID/vote-only
fixture exercises the full eligibility schema without dataset vectors. These
checks do not establish native availability or full-size memory/performance.

Initial local failures/logs are preserved. A legacy synthetic fixture/expectation
and missing imports caught during the new host/restore checks were corrected
before the final release. A later lock review also caught and corrected the
live sampler temporary-file race. The final source/receipt hashes and sealed
results identify the released version.

The final manifest covers 221 files; the archive has those files plus the manifest,
and every archived byte matches the sealed package. All 3,123 preserved production
and earlier evidence files are unchanged. Release identities:

- Manifest SHA256: `4212507e81abc053aa5045e09a8cb624b789ed0bad4e1e8d1bf69f82f31484d9`.
- Archive SHA256: `df8a7a8cbebd549ffd9ab5acfc0ee6d2e49c74cb0bd46d00e636fcc3d0269ab6`.
- [Independent release verification](../trials/torch-reviews-startup-resource-v1/release-verification.json).
- [Source checks](../trials/torch-reviews-startup-resource-v1/local-checks-source.json)
  and [sealed checks](../trials/torch-reviews-startup-resource-v1/local-checks-sealed.json).

- [Implementation/release receipt](../agent/docs/verification/startup-resource-v1-implementation.json).
- [Local checks, release and preservation evidence](../trials/torch-reviews-startup-resource-v1/).
- [Exact Mac/Torch commands](../trials/torch-reviews-startup-resource-v1/COMMANDS.txt).

## User handoff and next gate

Upload on the Mac, wait for verified transfer, run the single new Torch extraction/
submit block, then use status. After terminal state (including a failure), collect
on Torch and download on the Mac with the supplied helper. Preserve all old and
new packages/bindings/reservations/raw. No second submit on errors or reconnect.

Critical path: frozen startup design/local source+sealed readiness → one user
resource-only allocation → terminal collection/trusted independent analysis →
explicit resource decision → only then possible full-calibration release review.
B2d remains measurement_inconclusive; original execution retained; B1c deferred.
