# B2f accounting configuration review

October 27, 2026, America/New_York. Decision: **configuration request complete;
resource feasibility unqualified; full calibration release held**.
No code changes, local test reruns, experiments or allocations in this review.

## What the supplied output establishes

The user ran scontrol show config on torch-login-a-1 and reported:

| Setting | Reported value |
| --- | --- |
| JobAcctGatherType | jobacct_gather/cgroup |
| JobAcctGatherParams | (null) |
| ProctrackType | proctrack/cgroup |
| TaskPlugin | task/cgroup,task/affinity |
| TaskPluginParam | (null type) |

This is user-provided controller configuration, not an independently captured
configuration from failed compute task21159802_0. It identifies the accounting
family, process tracking and task plugins. No no_file_cache option is reported.
It does not identify the compute node's cgroup/v1 versus v2 implementation.
Slurm supports differing cgroup versions between compute nodes.
[Slurm cgroup implementation](https://slurm.schedmd.com/cgroup_v2.html).

Under Slurm cgroup/v2 accounting, RSS/MaxRSS includes filesystem cache unless
no_file_cache is set. Thus the31.9807GiB reported peak can include file-backed
cache if that implementation was active. It cannot be interpreted directly as
31.9807GiB of Python heap or anonymous process memory. The output does not
quantify the cache contribution or prove cache explains the peak.
[Slurm accounting behavior](https://slurm.schedmd.com/cgroup_v2.html),
[no_file_cache option](https://slurm.schedmd.com/slurm.conf.html).

The presence of task/cgroup also does not establish ConstrainRAMSpace,
AllowedRAMSpace, swap policy or the effective job/step/ancestor limit. Those
controls belong to cgroup.conf and runtime hierarchy state. A32GiB Slurm request
is not independent evidence of every effective memory limit.
[Slurm resource controls](https://slurm.schedmd.com/cgroup.conf.html).

## What changes in the diagnosis

The accounting question is narrower now: the plugin family and absence of a
reported cache-exclusion option are known. The old request for those fields is
complete. No further login-node configuration command is requested now.

The recorded exception is still Snapshot eligibility changed, followed by
FAILED1:0 and verified cleanup. There is no recorded OOM state/event in the
returned evidence. Its actual schema mismatch is already reproduced and
corrected in the isolated, locally checked source. This configuration supplies
no reason to change that cause or to assume the32GiB ceiling must increase.

However, neither a large cache nor sufficient full-run headroom is established.
The archive contains no job-cgroup anonymous/file/kernel breakdown or effective
limit, and process telemetry before the guard has no sampled RSS values.
Subtracting an estimated cache, dismissing the peak, or qualifying the old
14.25GiB configured estimate would be unsupported. Memory feasibility remains
open; no fourth full calibration is released.

The prior B2d campaign completed16,802 searches with the same full-size frozen
snapshot and a32GiB request. Its saved scheduler evidence lacks MaxRSS and memory
component traces. That is scoped evidence the loader has completed under a
related bounded setup, not a B2f peak/headroom measurement. Connection layout and
acquisition/observation regimes differ. It cannot replace the missing resource
qualification or reopen B2d's failed A/A verdict.

## Next step: a separate startup-only resource qualification design

GO to prospective design only. Before a full calibration handoff, design a small
qualification that exercises the actual full-size startup and reader lifecycle
with explicit memory accounting, then terminates before any ANN or exact search.
It uses the corrected, locally checked startup boundary and unmodified frozen
backend, data, graphs and module. It performs real snapshot/data-verification
and reader-admission SQL; zero ANN searches does not mean zero database work.

The outline to freeze before implementation:

| Step | Must do | Informs / stop condition |
| --- | --- | --- |
| Q0 provenance and resource context | Verify immutable source/seals, whole stopped-cluster copies, role-specific catalogs, module/image and allocated four-core identity; record host/container cgroup version, paths, relevant ancestors and effective limits | Actual accounting/enforcement scope; missing identity, limit or mandatory observation stops qualification |
| Q1 instrument startup | Capture aggregate current/peak memory, available anonymous/file/kernel components, memory pressure/limit/OOM events and process high-water marks across copying, server startup, full data verification, snapshot construction, hashing and request admission | Whether the high peak coincides with cache charge, full Python materialization or another phase; a sampled breakdown is not an exact breakdown at a historical total peak |
| Q2 reader lifecycle | Exercise both fixed creation orders, ten admissions/maxsix live readers/two admin connections with the one shared full-size snapshot; no priming, conditioning, native/exact references or measured bursts | Memory and cleanup through the required admission envelope; does not measure per-search workspace or qualify timing/recall |
| Q3 final integrity and cleanup | Close readers, stop only working servers, verify original source inventories and required working graph/module identities; preserve complete raw on any outcome | Correct cleanup and source safety remain mandatory |
| Q4 independent resource review | Compare actual limits/phase peaks/components with a prospectively declared reserve and conservative outstanding SQL/native-workspace allowance; retain missing-observation/inconclusive outcomes | Only a supported resource-readiness decision can precede final release review; no performance/calibration pass follows |

For cgroup/v2, suitable interfaces include memory.current, memory.peak (if the
installed kernel exposes it), memory.stat, memory.events and memory.max, with
relevant ancestor scope. Fields overlap; component totals must not be summed
naively. File-backed memory is not automatically all disposable. If the node
uses v1, explicitly defined compatible observations or a fail-closed stop must
be frozen; never assume v2 from the present transcript.
[Kernel cgroup memory interfaces](https://docs.kernel.org/admin-guide/cgroup-v2.html).

Proposed design ceiling, **not an issued entitlement or executable contract**:
at most one separate4CPU32GiB allocation, at most1hour, exactly0 ANN/exact
searches,0 providers/fits/protected samples, no automatic retry. Before code or
handoff, freeze exact host/work/finalization stage reserves, SQL/telemetry/read/
byte/storage caps, sample schedule, required versus optional fields, memory
reserve/workspace decision rule and complete-failure collection/reconstruction.
This proposal does not raise the frozen calibration's resource ceiling or spend
another allocation. Any required resource change must be prospective and explicit.

A startup-only pass cannot establish the full search workload's peak, quality,
A/A or performance. Its purpose is to expose startup compatibility/resource
problems before a full calibration. A later calibration design/release must still
justify remaining workload resources and preserve all scientific gates.

## Revised critical path and current user action

Verified three failures and119 local checks → supplied accounting configuration
recorded → freeze startup-only resource qualification and its decision rules →
separate local implementation/checks/release review → only then an explicit
bounded user handoff → complete resource-only evidence review → full calibration
release review → native N0–N4 unchanged. A negative or inconclusive resource result
stops this path for further review; it never authorizes a larger automatic run.

No command is needed from the user now. Preserve all three failed attempts and
retained clusters; the earlier scontrol request is complete. Existing calibration
packages/reservations remain spent and must not be resubmitted.

## Evidence

- [Supplied configuration transcript](../trials/torch-reviews-partial-calibration-v1-identity-fix/accounting-review-2026-10-27/user-config-output.txt).
- [Structured assessment](../trials/torch-reviews-partial-calibration-v1-identity-fix/accounting-review-2026-10-27/assessment.json).
- [Current release hold](../trials/torch-reviews-partial-calibration-v1-identity-fix/accounting-review-2026-10-27/RELEASE-HOLD.json).
- [Prior failure and release audit](fannagent-partial-calibration-v1-release-audit-2026-10-27.md).
- [Review receipt](../agent/docs/verification/partial-calibration-v1-accounting-review-2026-10-27.json).

B2d stays measurement_inconclusive, original execution retained and B1c deferred.
No scientific margin, policy, graph, module, code or consumed allowance changes.
