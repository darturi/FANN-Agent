# A2 release review: image compatibility hold and bounded inventory handoff

October 29, 2026, America/New_York. NEXT-STARTUP-ATTRIBUTION-01.
**Release review complete; A2 acquisition is not complete or released.**

The review caught a predictable compatibility rejection before spending a Torch
allocation. A1's unchanged `DRIVER-REFERENCE.json` records local CPython **3.12.7**.
The saved runtime build archive's configuration and Python header specify
**3.12.15**. `Driver.install()` compares the complete Python version string before
installing its hooks. Its current reference would reject that image version.
The image's actual executable/library/private-hook behavior still needs direct
inventory; saved build metadata does not attest execution of the SIF.

The unchanged A0 A2.0 gate requires: “Capability stop; no fallback, extra SQL or
costly restore after a known mismatch.” This review therefore holds native
submission and prepares only one small image inventory. It does not change the
reference, select another hook, upgrade dependencies or relax a gate.

## Evidence and diagnosis

| Boundary | Verified fact / limit |
| --- | --- |
| A1 local seal | Manifest `065022eb9428e4a7607b1eafa5784855103e184b174b4b5ac5abd6389827b96a`; archive `d399c84f81f4069b0e63ee539f893f6498ddea1874db02cf1efd779c5bb42e94` remains unchanged |
| Local installed runtime | CPython 3.12.7; A1 reference independently records the same version |
| Saved build configuration | Config SHA `ea7083a544d105d589ac1a3915b7ab8425fe1e867f2afc3ceaf99f0a9a48967f`, matching the original bundle's pinned validation record; environment `PYTHON_VERSION=3.12.15` |
| Saved Python header | `PY_MICRO_VERSION 15`, `PY_VERSION "3.12.15"`; containing uncompressed layer hash matches the config's rootfs diff ID |
| Actual SIF identity | Local file SHA `7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a` matches the original bundle manifest; it has not been executed locally |
| Source mapping placement | A1 validates original function AST/line mappings when snapshot observation starts; any later release must additionally establish this before restore. The inventory checks this mapping without calling either original function |
| Current disposition | No allocation, reservation, binding, image change or A2 submit command created; full B2f remains held |

The saved Docker export is used as build evidence, not treated as the SIF. The
config blob is self-hash verified and its digest matches the manifest-pinned
validation record. The selected header layer's content digest also verifies.
The requirements lock, Dockerfile/definition, validation record and SIF were
checked against the original bundle manifest. Full details are in the
[image reference audit](../trials/torch-reviews-startup-attribution-v1-release/image-reference-audit.json).

An initial controller draft was preserved as unsealed/unreleased when this
mismatch was found. It is not the handoff package and was neither compiled nor
executed. A1 and its guarded controllers remain unchanged.

## What the inventory does

The new isolated `startup-attribution.image-preflight.v1` capsule contains 99
byte-identical A1 source/reference files plus the inventory, contract and receipt
tools. It includes **no query vectors, development evidence, database directories,
graph/module binaries or scheduler entry point**. The 108-file manifest and
109-member regular-file archive were independently verified; source/sealed code
matches exactly. The archive is 219,647 bytes.

The Torch login invocation verifies the capsule and unchanged SIF checksum, then
starts the existing image with only a read-only capsule bind. It records actual
Python/NumPy/Arrow/Psycopg/libpq identity, the nine original private hook definitions
and uncached parser source/signature identities, original producer/constructor
source/AST/line mappings, Arrow default-pool capability and the two literal local
monitoring selfchecks. It calls neither producer nor constructor. It installs no
driver wrapper and executes no database/SQL/search operation. Connection and
child-process APIs are blocked during inspection and restored in `finally`.

The inspector preserves all differences from A1's reference. A completed mismatch
inventory is useful evidence, not a compatibility pass. Even a full match cannot
release the acquisition: allocation proc/cgroup, overhead, lifecycle, complete
accounting and cleanup/replay gates remain pending.

| Finite inventory limit | Bound |
| --- | --- |
| Invocations / Slurm jobs | One / zero; durable exclusive binding prevents repeat invocation |
| ANN/exact searches, SQL, DB connections, snapshots, providers | Zero each |
| Interpreter CPU / wall / address space | 15 seconds / 30 seconds / 2 GiB virtual address space; core dumps disabled |
| Outer image timeout | 60 seconds plus five-second kill grace; package/image hashing precedes this envelope |
| Source reads | 128, at most 64 KiB/file and 4 MiB total |
| Literal monitoring callbacks | At most 16; restore tool/local masks before completion |
| JSON / output files | At most 128 KiB JSON; interpreter file-size cap 128 KiB, outer output-file cap 256 units under Bash `ulimit -f` |
| Capsule | At most 16 MiB /256 files; actual 878,506 bytes |
| Data or mutable state mounted into image | None; only capsule at `/inspect:ro` |

Host stdout/stderr/exit code/checksums are saved in a fresh private results
directory outside the package. A durable binding is written before the inventory
and never overwritten. Failed/incomplete evidence stays downloadable. There is
no retry, allocation submission or dependency adjustment in either helper.

## Local validation and immutable handoff

**29 source checks and 29 sealed checks pass.** They cover exact A1 source pins,
archive/member parity, no data/job entry points, real original-function source
mapping, literal monitoring/restoration, version-mismatch preservation, connection
and child-process blocking with exact descriptor restoration, read/callback caps,
occupied monitoring tools, partial capability evidence, unsafe/tampered package
rejection, return identity/status/exit-code/zero-action verification and transfer
authentication/binding failures. The real shell helper is exercised with local
SSH/SCP stubs. No SSH connection or native image execution occurs in the tests.
Ruff lint/format and shell syntax pass. All **5,318 earlier evidence/source files**
remain byte-identical.

The prior A1 155 baseline and 100 source/100 sealed checks remain historical,
unchanged local evidence. They were not reclassified as image compatibility
tests or rerun to imply native qualification.

| Seal | SHA256 |
| --- | --- |
| Inventory manifest | `5f8bbb0dfa50b5346d00e4b60f5a7f3e6757bd48de3f0abe2073a3b882b554ce` |
| Inventory archive | `ccfab40dcd5325e9391f0ffdf76f3e8d73a7e2a343bcae8eed0d35ea6ac76fcb` |

[Handoff verification](../trials/torch-reviews-startup-attribution-v1-release/handoff-verification.json),
[source checks](../trials/torch-reviews-startup-attribution-v1-release/local-checks-source.json),
[sealed checks](../trials/torch-reviews-startup-attribution-v1-release/local-checks-sealed.json),
[capsule source](../agent/experiments/startup-attribution-image-preflight-v1/README.md),
[frozen inventory contract](../trials/torch-reviews-startup-attribution-v1-release/torch-startup-attribution-image-preflight-v1/PROBE-CONTRACT.json).

## User handoff and remaining gates

The user must run the three blocks in
[COMMANDS.txt](../trials/torch-reviews-startup-attribution-v1-release/COMMANDS.txt):
Mac upload/MFA, one Torch login image inventory, then Mac download. No account
setting or Slurm submission is needed. After downloading, reply “Downloaded” or
paste the exact error. Preserve the binding and results on any failure.

| Step | Status / decision | Informs |
| --- | --- | --- |
| A2 release audit | Complete; native release held on reference/build-version mismatch | Prevent predictable failed acquisition |
| A2.0a image inventory | Implemented, locally checked, sealed; user invocation pending | Actual SIF runtime/source/monitor/private-driver identities and complete mismatch set |
| A2.0b compatibility decision | Pending inventory. Review differences explicitly; no automatic reference substitution | Whether a narrowly versioned correction and its own local readiness work are justified, or no-go |
| A2 release / pre-restore gate | Held. A later reviewed artifact must retain original-function mapping/local-mask checks before restore and strict actual-image identity | Only then consider the unchanged maximum one1h/four-physical-CPU/32GiB zero-search allocation |
| A2.1–2.3 native acquisition | Not run; all original identity/lifecycle/102-point/dispatch/page/row/role/budget/restoration/lock/replay requirements remain | Trustworthy attribution, or invalid/incomplete preservation |
| A3 | Pending complete validated acquisition; informative/unresolved rules unchanged | Select a separately frozen remedy, or close unresolved/no-go |

**Revised critical path:** A0 frozen → A1 immutable local readiness → A2 release
audit → image-only inventory → explicit compatibility decision and any separate
correction/readiness → reviewed native handoff → capability before restore →
bounded zero-search acquisition → independent A3 review → separately frozen
remedy/resource qualification → full-workload memory/B2f release review.

Both completed resource verdicts remain margin-inconclusive. The original
28 GiB/no-event acceptance rule, scan counts, data/graph/module, snapshot retention,
CPU/memory/wall/observer limits and zero-search boundary are unchanged. No cache
subtraction, cap increase or full calibration release is inferred.

## Sources

- [A0 frozen design, especially gates and mechanism requirements](fannagent-startup-attribution-v1-design-2026-10-28.md).
- [A1 implementation and limits](fannagent-startup-attribution-v1-implementation-2026-10-29.md).
- [A1 exact driver reference](../trials/torch-reviews-startup-attribution-v1/torch-startup-attribution-v1/DRIVER-REFERENCE.json) and [strict install comparison](../agent/experiments/startup-attribution-v1/sa_driver.py).
- [Original bundle manifest](../trials/torch-reviews-first/manifest.json), [pinned build validation](../trials/torch-reviews-first/validation/runtime-image.txt), [image definition](../trials/torch-reviews-first/runtime.def), [requirements lock](../trials/torch-reviews-first/requirements.lock).
- [Local image-config/header digest-chain audit](../trials/torch-reviews-startup-attribution-v1-release/image-reference-audit.json).

This review uses existing local source/build evidence. It makes no new academic,
performance, native memory or causal claim and required no new literature search.
