# A3 exact-vector native correctness independently qualified

October 31, 2026, America/New_York. Roadmap D112 / v1.64.

**Job 21470341 is independently verified complete.** It ran the unchanged exact
SIF and CPython 3.12.15, completed 0:0 in 11m44s, and passed all **368 individual
cases: 128 source + 128 sealed original A2 cases and 56 source + 56 sealed A3 cases**.
The native correctness allowance is spent; do not submit it again.

This qualifies the scoped producer/consumer/startup integration under the exact
image. It does not qualify native startup memory, causal savings, workload memory,
quality/A/A, performance or full B2f. All previous inconclusive resource verdicts
and their original acceptance rules remain unchanged. No resource command or
new native allocation is released by this verification.

## Archive, identity and complete-case reconstruction

Campaign: `reviews-startup-exact-vector-compatibility-v1-20261031T014056Z.3twju78d`. The returned archive is **52,187 bytes / 33 regular
members**, SHA-256 `3edd0524f864aa97869a0ee71fe034c60a36b3cf37e24dfe8995dce455b2e2d3`.
Every member equals extracted raw; unsafe/duplicate/nonregular/link paths and
unexpected inventories are rejected. All 28 run-lock hashes and complete coverage
verify. Submission, manifest, scratch package, absolute host Python, scheduler,
launch/exit and final capsule/SIF integrity identities agree.

The original 774-file/775-member correctness capsule remains
`540af999770eeebbca80aa29c228b978a0101b11adf4e0dc4b424c4b4b5f5865`; manifest
`31def95d859395541fdac0a9ec04e40091788f51d571076477e8d08fcff8a199`. All 68 main recipes, integration/prototype code and all 789
tracked prior files are unchanged. The native module and test origins are exact:
legacy source runs from its frozen source tree, legacy sealed from the actual
standalone built candidate, A3 source from its two declared directories, and all
A3 sealed modules from `/work/integration-sealed`. No returned Python executes.

The audit reconstructs expected test IDs from the unchanged ASTs and checks
one ordered start/pass pair for **every** case in each suite. There are no missing,
duplicate, extra, skipped, failed or setup-error cases. All four native receipts
match the exact 3.12.15 image/private-hook/library reference, image config and
current code hashes. The A3 receipts additionally prove stable source, exact
module origins, all 56 IDs and zero denied actions.

Both original 128-case guards establish one real synthetic build/four reuses,
six seed checks, ten clones/reseals/unchanged seeds, restored connection bindings,
and only three permitted existing fake launcher shells. All 94 fixture-stage
events per suite reconcile. A3 guards record zero actual builds/clones/shells,
restored bindings and zero connection/subprocess attempts. The actual native
startup-entry tests use simulated SQL transport, not a database.

Zero real database connections, SQL, servers, ANN/exact searches or providers
are recorded. Guest and host exit 0, child cleanup and final source/capsule/SIF
integrity pass. The scheduler independently reports COMPLETED 0:0 for the job,
batch, extern and step. The earlier scheduling-test ID 21470340 was not the bound
allocation; the actual dispatch and completed job are 21470341.

## Complete finite timing proof

| Guest phase | Frozen cap, seconds | Observed complete phase, seconds |
| --- | ---: | ---: |
| preflight | 30 | 0.905 |
| source | 420 | 311.052 |
| candidate | 90 | 40.396 |
| sealed | 420 | 313.630 |
| integration_source | 90 | 9.389 |
| integration_sealed | 90 | 9.219 |
| guest_cleanup | 30 | 0.007 |

Guest total **684.603s** remains below 1170s; host total **699.201s** remains below
its 1365s endpoint, inside the 25-minute allocation including 135s outer margin.
All phase windows, ordering, full caps/tail reserves and cleanup/publication
endpoints verify. Source/sealed complete phases took 311.052/313.630s including
postchecks; A3 complete source/sealed phases took 9.389/9.219s. No cap was shortened,
borrowed or retroactively changed to make this result pass.

These are finite correctness-run observations, not startup or performance
estimates. The small-fixture job's memory/RSS cannot establish the real 247,286-row
resource margin.

## Verified proof packet and release-gate rehearsal

The audit exports unchanged native receipts as `main-source.json`,
`main-sealed.json`, `integration-source.json` and `integration-sealed.json`, plus
an independent `QUALIFICATION-AUDIT.json`. Each file is hash-bound to the actual
return; the audit records exact code, final integrity, guard restoration and image.

An ephemeral metadata-only fixture consumed these authentic proofs through the
unchanged trusted integration `native_spec` gate, with the original resource
contract and fixed 247,286-row identity. It returned the expected specification
without allocating native-size arrays, creating a backend, connecting to a DB or
launching anything. The temporary hypothetical release was deleted. **No persistent
NATIVE-RELEASE.json or resource controller/job was created.** The permanent packet
contains qualification evidence only.

[Independent audit](../trials/torch-reviews-startup-exact-vector-compatibility-v1/postrun-audit-2026-10-31/returned-verification.json),
[audit source](../trials/torch-reviews-startup-exact-vector-compatibility-v1/postrun-audit-2026-10-31/verify_returned.py),
[qualified receipt packet](../trials/torch-reviews-startup-exact-vector-compatibility-v1/postrun-audit-2026-10-31/qualified-receipts/).

## Next gate

GO to a **separate startup-resource experiment design, integration and local
release review** using the qualified unchanged producer. Freeze a distinct new
allowance and effective harness before code/release. Keep original data/graphs/
module/identity, one snapshot/four full verification scans, 200 admission-only
requests, ten readers/max six, both fixed orders/holds, strict provenance/guards,
all deadlines/limits and final integrity/cleanup.

The resource criterion remains aggregate recorded peak + 2 GiB reserve + 2 GiB
unmeasured workspace <=32 GiB, with no positive limit/OOM event, no cache subtraction
and no early snapshot-root release. Unknown coverage or inadequate margin closes
inconclusive, not a pass. Native correctness alone cannot satisfy that criterion.
Full-workload and B2f releases remain separate even after a scoped startup pass.

**No further Torch command is needed for this completed qualification.** Do not
rerun any spent package. A new resource handoff must wait for its own frozen,
locally verified protocol/controller/collection/replay and release checks.
