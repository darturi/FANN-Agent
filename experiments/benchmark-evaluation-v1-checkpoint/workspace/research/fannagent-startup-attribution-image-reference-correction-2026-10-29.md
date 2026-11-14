# A2 exact-reference correction and native compatibility handoff

October 29, 2026, America/New_York. NEXT-STARTUP-ATTRIBUTION-01, C0–C2.
**Main correction implemented and locally checked. Native target readiness remains
pending; only one zero-database compatibility job is released.**

The main harness now preserves the historical Mac3.12.7 reference and uses a
separate exact3.12.15 image reference derived from the verified image inventory.
All other provenance fields are identical. Native code has no local-reference
fallback, environment selector or patch wildcard. It also validates both original
function sources, AST/line mappings and local monitoring masks before restore.

The corrected source passes **128 local correctness checks** and **128 checks with
the compatibility connection/network/process guards active**, both on Mac
CPython3.12.7. These are not target-runtime passes. The local linux/amd64 execution
emitted a QEMU target SIGSEGV message before producing a Python test receipt. Its
owned container was stopped/removed. Target qualification therefore needs native
Torch hardware. A separately bounded zero-DB compatibility capsule is ready with
**23 source/23 sealed local checks**; the main A2 measurement remains held.

## Frozen correction and implementation

The [C0 correction contract](../agent/experiments/startup-attribution-v1-image-reference/IMAGE-CORRECTION.json)
was recorded before implementing the correction. It binds A0, the original A1
manifest, unchanged SIF/build config, verified raw inventory, historical local
reference, exact image reference, allowed parent changes and all unchanged native
scientific/resource limits. No historical artifact is overwritten.

| Boundary | Implementation / purpose |
| --- | --- |
| Exact reference | `DRIVER-REFERENCE.json` stays byte-identical at3.12.7. `IMAGE-REFERENCE.json` pins the actual3.12.15 interpreter and complete library/libpq/nine-hook/parser provenance. Native Driver/Session/replay always use the image reference |
| Offline fixtures | A test-only helper selects only a complete exact historical-local or image reference. It is never imported by native entry points. Synthetic packages and insufficient/stale/wrong-target receipts cannot submit |
| Pre-restore capability | R00 now validates original source/AST/line/local masks before any source restore. Original code objects still execute later; no alternate producer/constructor or extra function call is introduced. Failure preserves partial capability evidence |
| Native entry guards | Production flag, current source/recipe checks, exact3.12.15 complete provenance and build identity required; no target receipt currently exists, so main production packaging remains blocked |
| Finite main controller | Shared `.torch-startup-attribution-v1-reservation.json`, exclusive binding, known/uncertain dispatch refusal, exact one block0, no dependency/retry. Resolved absolute host Python and export fix retained; pre-submit status is explicit; failed terminal raw remains collectible |
| Independent replay | Requires the strict image reference and pre-restore mapping proof in addition to the unchanged scientific/resource/102-point/dispatch/page/row/role/budget/restoration/lock gates |

The native maximum remains one1h/four-physical-CPU/32GiB **zero-search** acquisition,
one original snapshot/four original full verification scans, original ten readers/
orders/holds/retention, unchanged data/graph/module/policy/SQL and original28GiB/
no-limit-event rule. No original application/vendor/native implementation changes.
All126 original native files and **5,531 earlier source/evidence files** verify
unchanged. Both prior resource verdicts and full B2f hold are preserved.

## Local checks and the unavailable emulated route

The corrected main source includes the original A1 tests plus strict reference,
production/synthetic/stale-proof gates, pre-restore source failure, exact controller
reservation/dispatch/unknown-ID/queue/accounting/failed-collection tests. All128
pass. The full128 also pass inside the added compatibility guard: zero denied
connection/process operations, three allowed fake-launcher shell fixtures and
exact connection-binding restoration. Actual original constructor/driver/parser/
generator/signal/cleanup paths execute with bounded synthetic rows/transport.

Local readiness iterations are retained. An initial parent-byte check correctly
blocked the existing synthetic fixtures' replaced eligibility/query files; the
exception is restricted to the synthetic flag, which native guards reject. A
pre-restore test was corrected to expect original cleanup attempts for both cells
even though no server was started. Native integrity requirements are unchanged.

The existing Docker image config matches the frozen build. One local bounded
attempt used linux/amd64, network none, read-only root/workspace,2CPUs/3GiB/128PIDs
and bounded tmpfs/deadline. It logged `qemu: uncaught target signal 11` without a
Python test receipt and remained running. The owned container was explicitly
stopped; recorded exit137 follows that stop, `OOMKilled=false`, and the container
was removed. This does not establish an image defect or a target correctness
result. No second emulated attempt or dependency change was made.

## Native compatibility design and gates

The [native compatibility contract](../agent/experiments/startup-attribution-compatibility-v1/COMPATIBILITY-CONTRACT.json)
was frozen before implementation. This is a separate correctness allowance, not
the main A2 acquisition or a full calibration. It starts no database and measures
no ANN/exact/SQL workload. It runs the exact existing SIF on native Torch hardware
to qualify the source and a sealed **synthetic** candidate,128 tests each.

| Resource / operation | Bound |
| --- | --- |
| Allocations / wall / CPU / memory | Maximum one15-minute/two-physical-CPU/4GiB job |
| Host startup / guest / host cleanup / outer margin |90 /720 /60 /30s; waits clamp to remaining absolute reserves |
| Guest source / candidate build / sealed / cleanup |300 /90 /300 /30s within720s |
| SQL / real DB connections / PostgreSQL servers / ANN/exact / fits/providers | Zero each |
| Original-function fixtures | At most64x768 rows or metadata-only counts; no full snapshot scan |
| Scratch / home return headroom | Conservative4GiB /128MiB, plus existing image/package; quota/free-space preflight before submission |
| Raw evidence / archive |4MiB /8MiB; no dataset/candidate directory returned |
| Inputs | Capsule/source/parent/code/SIF read-only; private scratch/output only; no retained/prepared DB or other-results mount |

The capsule carries immutable original data as existing hash/copy inputs for the
integrity fixtures; these are not measured outcomes. The M3 test-path alias maps
to A1's byte-identical original native files. The new compatibility job cannot
submit the main A2 job. It has its own exclusive reservation and binding; rejected
or uncertain dispatch is preserved without retry.

Test children block real connection APIs and Python network operations. Only the
existing fake-launcher shell fixtures may spawn. Each child must restore exact
connection descriptors, exit successfully and report zero guard denials. The
audit hook exists only for that child's lifetime. Exact image provenance, source/
recipe hashes,128 source/128 sealed results, terminal exit and locked raw are all
required. Source failure prevents candidate/sealed progress. Host and guest
failure paths preserve incomplete evidence and attempt cleanup; capsule/SIF hashes
are checked again before final host publication.

The target receipt's frozen build-config field identifies the original build
reference; the native wrapper independently verifies the SIF SHA. Neither field
is a hardware attestation. No successful target or memory qualification is
inferred before native results return.

| Gate | Current status / decision |
| --- | --- |
| C0 boundary | Frozen; historical references/source/old evidence preserved |
| C1 implementation/local readiness | Complete:128 normal and128 guarded local checks; original data/native files unchanged |
| C2 emulated target | Unqualified; failed local execution/no Python receipt preserved; owned container removed |
| C2 native harness | Ready:23source/23sealed checks, actual mocked host/guest entry success/failure, guard/launcher/dispatch/terminal collection, archive/source/preservation checks |
| C2 native execution | User command pending. One15m/2CPU/4GiB zero-DB job; all target checks must pass; no automatic retry |
| C3 main production release | Held. Independently verify source/sealed native receipts and exact packaged code/recipe, then build/review final main production seal and release its separate finite handoff |
| A2/A3/full B2f | Main acquisition and A3 remain pending; full B2f and resource-margin holds unchanged |

Local capsule checks exposed a self-rebuild copying a prior manifest into a new
seal; the candidate is retained as superseded. The fix excludes only manifest/
binding metadata and has a positive sealed-rebuild regression. Host/guest entry
coverage and final input-protection checks were then added. Those local candidates
and fixture-only failures are preserved and were never deployed or submitted.

## Verified compatibility handoff

| Artifact | Verified identity |
| --- | --- |
| Manifest | `fb850640e4fe71c0a05ce6439b97586232701bbfaacfa08b348c927fb5844439` |
| Archive | `987c1611a354aca2080218e7ba40cc7fd086801e4004681ed66ad9f30b07f0e2` |
| Files / regular unique archive members |693 /694 |
| Archive bytes |20,332,368 |
| Corrected main source | Exact bytes match the128-check local receipt and128-check guarded integration receipt |
| Capsule source/sealed checks |23 /23 pass; source fingerprints and module origins verify |
| Lint/format/shell | Pass;60 Python files formatted; both launch/transfer scripts parse |
| Earlier source/evidence |5,531 hashes unchanged |
| New Torch jobs / actual ANN/exact/native SQL/providers/fits |0 each |

[Independent release verification](../trials/torch-reviews-startup-attribution-compatibility-v1/release-verification.json),
[main local evidence](../trials/torch-reviews-startup-attribution-v1-image-reference/),
[capsule checks/evidence](../trials/torch-reviews-startup-attribution-compatibility-v1/),
[implementation receipt](../agent/docs/verification/startup-attribution-image-reference-correction.json).

## User handoff and revised critical path

The user needs to run the three stages in
[COMMANDS.txt](../trials/torch-reviews-startup-attribution-compatibility-v1/COMMANDS.txt):
Mac upload, one Torch compatibility submission/status/terminal collect, then Mac
download. The job name is `fann-a2-compat-v1`; its controller is `cc_control.py`.
It is distinct from the completed direct image inventory and the unreleased main
diagnostic. Preserve all results on failure and report the exact output.

**Critical path:** C1 local correction complete → user C2 native zero-DB source/
sealed compatibility → independent return/guard/identity verification → C3 main
production seal/review → separately released main A2 zero-search acquisition →
independent A3 informative/unresolved decision → separate remedy/resource/full-
workload qualification → possible B2f release review.

There is no new performance, recall, A/A, causal-memory or resource-margin result
from this implementation. The purpose is to resolve a specific release prerequisite
before asking Torch to restore databases for the main diagnostic.

## Sources

- [Verified image inventory and compatibility decision](fannagent-startup-attribution-image-preflight-v1-postrun-2026-10-29.md) and [exact decision boundary](../trials/torch-reviews-startup-attribution-v1-release/postrun-audit-2026-10-29/compatibility-decision.json).
- [Immutable A0 design](fannagent-startup-attribution-v1-design-2026-10-28.md), [A1 implementation](fannagent-startup-attribution-v1-implementation-2026-10-29.md), [unchanged image reference](../agent/experiments/startup-attribution-v1-image-reference/IMAGE-REFERENCE.json).
- [Corrected main harness](../agent/experiments/startup-attribution-v1-image-reference/README.md), [native compatibility harness](../agent/experiments/startup-attribution-compatibility-v1/README.md), [native contract](../agent/experiments/startup-attribution-compatibility-v1/COMPATIBILITY-CONTRACT.json).
- [Failed emulated attempt and cleanup](../trials/torch-reviews-startup-attribution-v1-image-reference/target-container-source.json), [source local checks](../trials/torch-reviews-startup-attribution-v1-image-reference/local-checks-source.json), [guarded128-check receipt](../trials/torch-reviews-startup-attribution-compatibility-v1/local-main-guarded-checks.json).

All technical conclusions are tied to existing local source, verified image data
and these bounded correctness checks. No new literature search was required.
