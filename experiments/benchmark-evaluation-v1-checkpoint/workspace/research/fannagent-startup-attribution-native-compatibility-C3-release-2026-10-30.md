# Native C2B verified; C3 releases the unchanged main A2 acquisition

October 30, 2026, America/New_York. Roadmap D104 / v1.55.

C2B job **21443102** is independently verified complete. C3 production sealing,
local final-package checks and release review also pass. Main A2 is now ready for
the user's one **1-hour / 4-physical-CPU / 32-GiB** zero-search attribution job.
It remains unlaunched. Full B2f remains held; the old resource findings remain
margin-inconclusive.

## Independent native return verification

The [data-only audit](../trials/torch-reviews-startup-attribution-compatibility-v1-budget-fix/postrun-audit-2026-10-30/returned-verification.json)
checks all 24 unique regular archive members (44,693 bytes), all 19 locked hashes,
exact submission/campaign/job identity, successful Slurm terminal records for the
job and its steps, exit zero, and complete publication. Archive SHA-256:
`d14c18156de50e163f69917802c779e0f64b087220ff7e1aaa1baa593712ffb4`.
No returned Python was imported or executed.

Both native suites run **all 128 original cases**, with no error/failure/subtest
error events, complete suite-end events and the exact expected case inventory.
The native Python 3.12.15 image provenance, libraries, all nine private hooks and
uncached parser match the unchanged reference. Every main recipe and Python source
hash matches current trusted source and the sealed synthetic candidate.

Each child proves one actual build, four reuses, six full seed/archive checks,
restored builder, ten clones, ten reseals, ten unchanged seed proofs and forty
separate mutable copies. Connection bindings restore; denied connections and
processes are zero. Guest cleanup and final host capsule/SIF integrity pass.

| Recorded phase | Seconds | Cap |
| --- | ---: | ---: |
| Guest preflight | 0.836 | 30 |
| Complete source phase | 283.272 | 420 |
| Original standalone candidate build | 37.151 | 90 |
| Complete sealed phase | 284.598 | 420 |
| Guest overall | 605.870 | 990 |
| Host overall | 618.178 | 1,155 before outer margin |

Slurm reports COMPLETED / 0:0 / 00:10:22. Phase timing, full-phase admission tails,
cleanup/publication endpoints and the frozen 21-minute envelope reconcile. These
are completed correctness-qualification observations, not a general native runtime
bound or a startup-workload memory/performance result. Reported real DB connections,
SQL, PostgreSQL servers, ANN/exact searches, providers and main A2 launches are zero.

All four compatibility allowances are now spent: jobs 21348020, 21367064 and
21382454 remain failed/incomplete; 21443102 is complete. E294/E300/E307/E315 are
historical and must not be resubmitted. No prior result is promoted or reset.

## C3 production seal and release review

[C3-FREEZE.json](../trials/torch-reviews-startup-attribution-v1-image-reference/C3-release-2026-10-30/C3-FREEZE.json)
precedes production sealing. Exact native source/sealed receipts are staged without
rewriting their contents. The earlier local and failed emulated evidence remains
intact. The builder includes the original 128-case local proof and the verified
128-case native source proof as production readiness receipts; independent C3
review additionally requires the complete native sealed proof.

The final production package has **619 manifest files / 620 unique regular archive
members**. Relative to the qualified 617-file native synthetic candidate, it adds
only LOCAL_CHECKS.json and TARGET_CHECKS.json, and changes only the two experiment
configuration fields synthetic_fixture and local_readiness. Reconstructing the
synthetic configuration reproduces the native candidate hash exactly. All 68 main
recipes, code, assertions, strict references, source data/graphs/module/policies,
A0/A1 identities, production copies/hashing/verification and scientific/resource
rules remain byte-identical.

The actual final production seal passes all **128 local cases** through the
unchanged guarded checker and synthetic fixture helper, including final build,
seed, restoration and signal/cleanup proofs. Local Python is 3.12.7; elapsed
suite time is 63.166 seconds. Controller verify and strict native-release
readiness pass; controller status reports Not submitted. Ruff, AST and launcher/
transfer shell checks pass. Archive bytes, source/seal parity, transfer binding,
finite controller and all 5,883 prior file hashes verify.

[Release verification](../trials/torch-reviews-startup-attribution-v1-image-reference/C3-release-2026-10-30/release-verification.json)
binds production manifest SHA-256
`2bc40b4bf802ad333bca5bbc1e60f3a6219d456a48bf8a30a79a3328e37829df` and archive SHA-256
`f2a7f4e5117dc84fa5758bcba8a941ac8ff9d4456ebca0c10e5fa8f487f07ff1`.

## Current handoff and remaining A2 gates

[Current main A2 commands](../trials/torch-reviews-startup-attribution-v1-image-reference/COMMANDS.txt)
are Mac upload → Torch checksum/extract/submit once → status → terminal collection,
including failure → Mac download. The package is currently unbound and its main
allowance is unspent. The fixed .torch-startup-attribution-v1-reservation.json
protects against reupload/retry; never delete or reset it. No SSH, native image,
actual DB/query, ANN/exact search, provider, fit or Torch submission was performed
by Codex in this review. A local CLI typo was rejected by argparse before packaging;
its log is preserved and the correct package command then completed.

Main A2 retains one snapshot scan, four original verification scans, all 102
checkpoints, original reader/server order and holds, stage/deadline/observation
caps, 2-GiB reserve plus 2-GiB workspace allowance, and no cache subtraction.
Original source/image/hook/monitor/proc/cgroup capability must pass before restore.
Any failure stops under the frozen contract with partial evidence preserved and
no automatic retry.

After the user's run, independently verify actual identities, coverage, dispatch/
page/row/role/overhead accounting, resource evidence, restoration, cleanup, locked
integrity and fresh trusted replay before closing A2. Informative attribution and
valid unresolved/inconclusive closure are separate from a memory-margin pass.
Only then may A3 select one evidence-backed remedy or stop. No full-workload memory,
quality, A/A, performance or B2f release follows from C2B/C3.
