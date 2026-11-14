# A3 resource login path failure: corrected handoff for the same unspent allowance

October 31, 2026, America/New_York. D114 / roadmap v1.66.

**The reported attempt failed before reservation or scheduler invocation.** In the
original controller, `before = protected(package, sources)` is line 141;
`sbatch --test-only` is line 179 and reservation creation is line 184. The earlier
binding/reservation guards had passed. The reported 7,297-file / 1,209.5-MiB scan
finished in 95.5s; the subsequent missing-file exception prevented either Slurm
command and any new allocation. The continuation also checks live state before
submit; an existing or uncertain reservation stops it. No earlier spent allowance
is reused and no additional resource allowance is created.

## Cause and correction

The previous handoff passed its embedded `reference/` to the inherited protection
chain. That original helper derives the old exact package as
`package.parent / "torch-exact-topk-v1"`. Under the new scratch capsule this
incorrectly selects a nonexistent child of the resource capsule. The original
main package lived under `/home/dar579`, where the historical sibling exists.
Prior tests mocked the full protection call and missed this context dependency.

The isolated correction first verifies the actual preserved main package against
every file and manifest pinned by the embedded reference, plus its original
binding/reservation. It then invokes unchanged original protection code with
`/home/dar579/torch-startup-attribution-v1-image-reference` as the package context.
Every historical guard remains active, including the exact sibling's full
manifest/file checks. Caller `sys.path` restores on success and every exception,
so historical bootstrap cannot select old helpers for the new controller.
Completed-main checks run once; all other completed source/result checks remain.
There are no symlink workarounds, skipped checks or changes to the old helper.

The original main code, five qualified A3 files, 128+128 original and 56+56 A3
native receipts, all scientific inputs and allocation/scan/reader/margin limits
stay unchanged. The correction uses a separate local source/output and separate
remote transfer/extraction directories. The original 983-file seal/archive and
all **3,035 tracked prior files** retain their hashes. The unchanged controller
uses the same fixed resource reservation, prefix and one-allocation limit.

## Local proof and release

All **110 source + 110 sealed** checks pass, with no errors, failures, skips or
denied external actions. All original 100 local case IDs are preserved. Ten new
regressions reproduce the old missing sibling using the actual inherited
`package.parent` and filesystem/hash checks; pass with the retained home context;
reject changed main bytes, binding, reservation, historical exact bytes, other
results or a substituted embedded context; restore imports on interruption; and
prove protection failure precedes reservation or scheduler calls. These use
bounded synthetic prior packages and an earlier-inventory fixture, rather than
claiming to reproduce the full remote 7,297-file inventory locally. The broader
original protection implementation remains byte-identical and all checks are
retained for the next login/host run.

The production artifact has **984 manifest files / 985 regular members**,
39,067,447 compressed bytes. Manifest SHA-256:
`0bac45da4db9b6db1e19023a11a3368aeb765ad33ca28e5d3f4af36b35e56ca6`. Archive SHA-256:
`92333e1785d0510c45146d359724a55b482d96db44e383b56b88ee20040b4b90`. Complete member/source/hash/old-artifact/preservation,
strict target rejection locally and authentic receipt consumption checks pass.
The original memory decision and eleven scientific/measurement modules remain
unchanged in meaning. Native startup memory is still unqualified.

Offline checks pass four shell syntax checks and upload/failed authentication/
invalid manifest/unsafe campaign cases using SSH/SCP stubs. The continuation
script is extracted exactly from the packaged expanded commands and shipped with
its own SHA-256 sidecar. Both archive and script checksums are verified on upload.
No real SSH, SQL, ANN/exact search or Torch job ran here.

## Current commands and native gate

Use [the corrected short commands](../trials/torch-reviews-startup-exact-vector-resource-v1-path-fix/NEXT-COMMANDS.txt).
The Mac upload writes only `/home/dar579/a3-resource-path-fix-transfer`; the
continuation extracts only into `/scratch/dar579/torch-reviews/a3-resource-path-fix-packages`.
Original upload/extracted artifacts and all results/reservations are preserved.
After **UPLOAD VERIFIED**, the Torch command is:

```bash
bash /home/dar579/a3-resource-path-fix-transfer/torch-next.sh
```

This continues the same unspent **1h / 4 physical CPU / 32 GiB / zero-search**
startup-memory allowance. Original conservative quota checks, strict target,
four verification scans, ten readers/max six, both orders/holds, cleanup,
aggregate peak +2 GiB reserve +2 GiB workspace within the effective limit and no
positive limit/OOM event remain mandatory. No native headroom or memory result is
inferred from local tests. Any actual dispatch uncertainty/failure holds retry;
terminal failure remains collectible. Independent native return verification
and resource replay still precede a memory verdict. Full B2f remains held.

[Failure assessment](../trials/torch-reviews-startup-exact-vector-resource-v1-path-fix/failure-assessment.json),
[pre-code correction freeze](../trials/torch-reviews-startup-exact-vector-resource-v1-path-fix/PATH-FIX-FREEZE.json),
[independent release audit](../trials/torch-reviews-startup-exact-vector-resource-v1-path-fix/release-verification.json),
[offline handoff audit](../trials/torch-reviews-startup-exact-vector-resource-v1-path-fix/handoff-verification.json),
[expanded commands](../trials/torch-reviews-startup-exact-vector-resource-v1-path-fix/COMMANDS.txt).
