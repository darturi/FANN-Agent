# B2f implementation and Torch handoff

October 27, 2026, America/New_York. NEXT-PARTIAL-CALIBRATION-01 /
`partial-calibration.v1`. Local implementation readiness; native gates pending.

The user requested execution of the next implementation/check/seal steps after
returning the read-only source inventory. The isolated implementation is
[agent/experiments/partial-calibration-v1](../agent/experiments/partial-calibration-v1/).
Production code, previous experimental sources, sealed packages, raw results,
verification receipts and the frozen scientific design remain unchanged.

The [design](fannagent-partial-calibration-v1-design-2026-10-26.md), contract and
schedule are copied byte-for-byte into the new package. Their historical freeze
status remains intact. No new graph, effort level, sample, policy, margin or
measurement regime was selected during implementation.

## What was implemented

The controller creates a new `reviews-partial-calibration-v1-…` campaign and
exactly-one-allocation reservation, then records dispatch intent before sbatch.
Unknown/rejected dispatches are preserved rather than retried. A dedicated srun
step binds the job task to its allocated cores. Status/collection use the durable
binding; collection captures terminal Slurm evidence including available MaxRSS
and archives raw data without a remote timing verdict. The MFA transfer helper
completes authentication before reading JSON and verifies both transfer hashes.

The retained whole clusters are bound read-only. Native qualification requires
clean shutdown from the pinned image's pg_controldata, complete file inventories,
matching graph hashes, safe ownership/link layout and independent complete copies
including WAL/transaction files. Existing private authentication is copied only
into new private workspaces. Both new servers use separate sockets. No retained
source is started or altered. Complete ID/vote/vector-bit parity, full prior
catalog/statistics equality and module/graph identity are verified. New servers
must stop cleanly; graph hashes and control states are checked after stopping.

Physical observations bind each reader to PID, start ticks, parent postmaster,
role/database, unique server/socket, epoch and singleton CPU. The client occupies
C0, servers/admin/background C3, and both replicas/conditioner of each cell share
C1 or C2, swapped in the second epoch. The task mask must expose exactly four
distinct physical cores. Required proc data, thread count, namespace/affinity and
monotonic counters fail closed. Optional schedstat/NUMA/frequency metadata use
fixed availability flags; disabled scheduler wait accounting is unavailable.
Observed process high-water RSS and optional Slurm MaxRSS are retained separately
from the conservative configured memory bound. They are not advertised as an
exact simultaneous allocation peak.

The frozen schedule controls both epochs, ten reader admissions, four warmups and
three retained calls per primary burst, independent conditioner/order balance,
bulk plans and the eight-vector observer diagnostic. Primary trace output is
buffered and proc/observer SQL stays outside the seven on-reader calls. Diagnostic
modes both have per-call proc bracketing; only ON adds the specified plans. No
mode selection or diagnostic rescue is implemented.

Every search attempt reserves its operation before execution. Exact complete
counts remain 16,242 searches, 4,200 plan packets, 4,800 primary retained calls and
384 diagnostic retained calls. Valid quality failure stops at 610. All frozen
SQL/read/affinity/telemetry/time/evidence/storage/memory ceilings apply, including
the unspendable 560 remaining outer-envelope attempts. Resource, identity,
required-observation, execution, final-proof or cleanup failure prevents a pass.
Raw failures are preserved without an automatic extension.

The independent local verifier checks raw locks, package/campaign/scheduler and
resource identities, complete orders/counts, all outputs/truths, plans/counters,
physical mappings, telemetry coverage and final preservation/cleanup. It then
recomputes scoped quality and all 56 physical A/A, half-epoch and retained-stability
intervals at the frozen margins. Creation-order orientation and observer timings
are descriptive. Trusted locally sealed code reads returned data; downloaded code
is never executed.

## Validation and limits

The release includes passing source and sealed-package correctness receipts,
static lint/format/AST and shell syntax checks, archive-member byte parity and a
before/after preservation inventory. See the
[implementation receipt](../agent/docs/verification/partial-calibration-v1-implementation.json)
and [release evidence](../trials/torch-reviews-partial-calibration-v1/).

The local suite covers synthetic full acquisition and independent reconstruction,
quality stop, physical/half/stability rejection fixtures, unsafe archives/copies,
foreign ownership, stale/closed/replaced connections, PID reuse, namespace and
CPU drift, missing required observations, unavailable optional observations,
negative/decreasing counters, generic plans, count/resource caps, unknown dispatch
and non-overwriting reservations. These are correctness fixtures, not performance
or native feasibility evidence. No PostgreSQL process, native ANN experiment,
Torch job, SSH session, provider request, fit or protected query was run by Codex.

Actual source consistency/restoration, mandatory proc access, CPU placement,
quota/memory and execution compatibility remain N0 gates on Torch. Local mocks
cannot establish them. Failures must be collected and reviewed without deleting
the reservation or replacing the graphs.

## Handoff and decisions

Use [COMMANDS.txt](../trials/torch-reviews-partial-calibration-v1/COMMANDS.txt):
Mac upload → one Torch submit → status → terminal collect → Mac download/local
verification. The release archive and checksum are in that same directory.
Upload alone does not submit a job. A failed extraction/submission must be
reported with its output; do not repeat the entire block.

The revised critical path is completed implementation/local readiness/seal →
user upload/single submit → native N0 restoration/resource/identity/telemetry
qualification → N1 conformance/quality → N2 both complete epochs → N3 final
integrity/cleanup → independent N4 all-56 decision. A complete pass is only
`calibration_qualified_scoped`, allowing a later treatment-design review. A
complete timing failure is `calibration_inconclusive`; failed/missing acquisition
proof cannot qualify. No later treatment experiment is automatically authorized.
B2d stays `measurement_inconclusive`; original execution remains retained and
B1c deferred. No partial-index speedup or adoption verdict is established here.
