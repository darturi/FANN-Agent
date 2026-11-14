# B2d local implementation and Torch handoff

October 26, 2026. Register **NEXT-PARTIAL-ANN-01**, version **partial-ann.v1**.

**Local readiness passes: 55 source checks and the same 55 checks from the sealed package pass. The package is ready for the user's one Torch submission. No native experiment, index build or Torch job has run.** Native compatibility, quality, A/A and performance remain unassessed. Original execution and all earlier verdicts remain unchanged.

## Scope and implementation

The [isolated implementation](../agent/experiments/partial-ann-v1/) compares native640 on the preserved full HNSW against native640 on exactly one new partial cosine HNSW for actual `total_votes >= 108`. It uses the same 200 exposed vectors and k10, with separate private copies of the full table and original graph. It changes no adopted/public code or prior sealed experiment. No new module, selector, fit, provider or protected evaluation is included.

The [original frozen design](fannagent-partial-ann-v1-design-2026-10-26.md) and [prospective implementation addendum](fannagent-partial-ann-v1-implementation-addendum-2026-10-26.md) govern this package. The original design file is preserved as its pre-implementation snapshot. The addendum specifies site quota checks, bounded native dispatch/finalization, explicit SQL accounting, durable failures and tie-order equivalence without changing the scientific gates or search allowance.

The experimental adapter strictly checks the actual AST/k and privately admitted request identity, preserves parameter/vector formatting, and adds the redundant fixed >=108 conjunct only for the candidate. The public nonpartial-index inspector remains unchanged. Source feasibility does not establish native support: full catalog, binding and actual fresh/cached plans must qualify. The baseline copy cannot acquire the candidate index through the planner.

Both servers retain inherited query settings and a 30-second reader statement timeout. The harness will not start a search with less than 30 seconds left in its acquisition allowance. Every explicit observer/startup/helper execute is counted; search attempts are reserved before dispatch. Failed native calls close their handle without replay. Catalogs are persisted before validation, including rejected raw; charges and checkpoints survive early stops. Full data/index/module verification and cleanup are required before a successful raw lock.

## Local verification

| Check | Result / limit |
| --- | --- |
| Source synthetic correctness suite |55/55 pass,39.278 seconds |
| Sealed-copy synthetic correctness suite |55/55 pass,39.001 seconds |
| Full mocked acquisition and independent raw replay |16,802 attempts,6,400 retained formal calls,3,200 slots,5,700 plan packets; scoped positive gate exercised using synthetic times |
| Valid quality-negative branch |802 attempts; no formal timing or economic verdict |
| Complete cost-futility branch |202 attempts; resource decision only, no positive qualification |
| Rejection and failure checks |Strict predicate/k/mapping/ownership, stale/error handles, original/text OID and partial catalog constraints, fresh/generic/cached wrong-index plans, duplicates, missing/raw timer tampering, incomplete final lock, unknown dispatch/scheduler and unsafe archives |
| Control protections |A/A failure defeats a large apparent benefit; recall reserve can fail despite passing mean floors; conservative economic bounds retained |
| Transport/host/resource checks |Remote checksum sequence, read-only input/module mounts, quota rounding/unknown format, host preflight failure evidence, terminal failed collection and irrevocable reservation |
| Static/package checks |Active new modules pass Ruff; transfer/Slurm/command shell syntax passes; every archive member matches its local file; source/sealed modules match |

These are fake database/results/clock checks, not native measurements or independent policy evidence. Test fixtures are explicitly marked synthetic and cannot submit to Torch. The ordinary native execution method and frozen reference/scorer/runtime anchor are inherited; no local PostgreSQL or ANN index was started.

Records: [source checks](../trials/torch-reviews-partial-ann-v1/local-checks-source.json), [source log](../trials/torch-reviews-partial-ann-v1/local-checks-source.log), [sealed checks](../trials/torch-reviews-partial-ann-v1/local-checks-sealed.json), [sealed log](../trials/torch-reviews-partial-ann-v1/local-checks-sealed.log), [package checks](../trials/torch-reviews-partial-ann-v1/package-checks.json), [preservation inventory](../trials/torch-reviews-partial-ann-v1/preservation-before.json), and [completion receipt](../agent/docs/verification/partial-ann-v1-implementation.json).

## Seal and finite campaign

| Artifact / resource | Exact value |
| --- | --- |
| Package | `torch-partial-ann-v1`;161 manifested files /162 regular archive members |
| Manifest SHA256 | `f11159e1b66d9e9cb0259bec45e136eac9bff7a322233a9ac00a4153267c09a4` |
| Archive SHA256 | `b2f7730a24a98ea2a3d29474298064a2500eab8e61911c83130bf705bc97755c` |
| Archive bytes |16,315,887 |
| Frozen runtime anchor SHA256 | `082b167507e25009bdb25ea613950cd434ef38608fbcbc6194af19c363d0f6dc` |
| Scientific design SHA256 | `7a59792f2db41a4c88095231c1682695ab8a112943112bb2c82d774f22dbefcb` |
| Implementation addendum SHA256 | `dc9766f761dd3eb2a69f84e0ec1ba3abbc8814454bea6091bdebab61730e491a` |
| Allocation ceiling |One x86_64 job;3 hours,4CPUs,32GiB;10,200-second work allowance including finalization |
| Search ceilings |10 qualification +192 preview +600 quality +16,000 formal =16,802; valid early stops at202 or802 |
| Readers / controls |8 admissions,6 live maximum;4 scoped A/A interval checks; two complementary blocks |
| Additional SQL ceilings |20,000 observer,4,040 exact-helper,1,000 startup/configuration executes |
| Current actual native/Torch/provider/fit/protected use |0 |

`myquota` plus filesystem bytes/inodes must prove room before submission and on the compute host. Unknown output fails closed; no default quota is assumed. Both-copy memory settings and a conservative client/build/server allowance are checked before the build. These checks do not establish current Torch availability from the Mac. [NYU Torch utility applications](https://services.rt.nyu.edu/docs/hpc/tools_and_software/utils/)

Quality remains both recall means>=.95 and lower95% candidate-minus-baseline recall bound>=−.0025. A/A intervals must lie within±.10ms and±log(1.02). Benefit requires the conservative99.375th-percentile upper gap<=−.10ms and upper log ratio<=log(.98), both block gaps negative, complete quality/controls and final integrity. No threshold or previous result changed.

## User handoff and next gate

Use the [exact commands](../trials/torch-reviews-partial-ann-v1/COMMANDS.txt): Mac upload first; wait for **UPLOAD VERIFIED**; then extract and submit once on Torch. Status is safe after reconnect. After terminal completion, collect on Torch, then download on the Mac. The [transfer helper](../trials/torch-reviews-partial-ann-v1/transfer.sh) authenticates interactively, transfers archive/checksum and explicitly verifies the remote checksum. It submits no job itself.

The job runs independently of the login connection. If the login disconnects, reconnect and use status; do not resubmit. Retain any binding, reservation, extracted package or failed raw. Collection preserves unsuccessful and incomplete campaigns after terminal scheduler proof; unknown dispatch/completion cannot trigger another job. The download helper verifies checksums and replays with trusted sealed local code, never downloaded executables.

**Critical path:** local implementation/checks/seal complete → user upload/once-only submit → resource/restore/build/native qualification → expense preview → full scoped quality → complete two-block A/A/economics and final integrity → collect/download → independent returned-evidence review. Stop at the first failed gate. A complete positive warm result would still need build amortization, maintenance/invalidation and a separately scoped integration/acceptance design. M1/M2/M3 and canonical acceptance remain unestablished.

Internal pre-dispatch review seal1 is retained under the trial directory and marked superseded. It was never uploaded/submitted. Final review removed unused inherited exact-search metadata; the final contract names only the B2d design and native640/partial640 cells. A dedicated regression and secondary-timer tamper check are included in the55-check final suite. Scientific scope/gates and the original frozen design/addendum did not change.
