# Startup-only resource qualification v1

One separate1h4CPU32GiB allocation, exactly0 ANN/exact searches. DESIGN.md and
RESOURCE-CONTRACT.json were frozen before implementation. The original B2f
CONTRACT/SCHEDULE/B2F-DESIGN and all native/data/graph inputs remain unchanged.

pc_runtime.main performs exact whole-copy/data/catalog/snapshot/admission checks,
both fixed reader-creation orders, ten admissions/maxsix live, final integrity
and cleanup. sr_interface prohibits search entry points; pc_common reservations
and pc_trace's exact SQL allowlist reject searches before driver execution.
Snapshot/data-verification and role/settings SQL are allowed and separately capped.

A separate bounded host sampler starts before original-bundle verification and
continues through cleanup; it records actual cgroup v1/v2 mapping/ancestor limits,
peak/current/components/events, process RSS and host/container PID mapping. No
cache dropping or cgroup writes. Kernel aggregate peak plus fixed2GiB reserve
and2GiB unmeasured-workspace allowance must fit the smallest finite limit capped
at32GiB, with complete observation/event coverage, for a startup-only margin pass.
Otherwise a complete startup is resource-margin inconclusive. Components are
never subtracted to create a pass. Full workload memory/calibration stays unqualified.

pc_job contains the absolute-host-interpreter/export correction and bounded
sampler/container supervision. Guest and final host evidence have separate locks,
so active host memory files are never incorrectly frozen by the guest. Terminal
failures remain collectible; once-only binding/reservation prevents automatic retry.
Trusted local sr_report independently validates raw/zero-search/lifecycle/source/
cleanup/memory evidence and computes the scoped resource decision.

Local tests use synthetic OS/process/SQL responses and the actual frozen backend
constructor/binding/snapshot methods. They never start PostgreSQL, execute native
ANN, submit to Torch or contact SSH/providers. See the final implementation receipt
for actual test/static/archive/scientific/preservation results and limits.

Use the final release COMMANDS.txt for Mac upload, one Torch submission, status,
terminal collect and Mac download. This is one additional allocation beyond the
three failed calibration attempts. It does not release a full calibration run.
