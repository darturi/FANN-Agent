# A2 image inventory verified: one Python reference mismatch

October 29, 2026, America/New_York. NEXT-STARTUP-ATTRIBUTION-01, A2.0a.
**Inventory complete and verified; A2 acquisition remains held.**

The only provenance difference is **CPython 3.12.15 in the actual Torch image
versus 3.12.7 in A1's local reference**. The image already has the version frozen
in A0. A1 captured the Mac interpreter version into the reference used by the
native install guard; that is a harness reference error. It should have been
detected during A1 against A0's explicit `expected_runtime_libraries.python`
entry. The release review caught it before any acquisition allocation.

NumPy, Arrow, Psycopg, libpq, all nine private hook definitions and the uncached
query parser match the A1 reference exactly. Original producer/constructor source
and line mappings and the two literal monitoring checks pass. There is no
evidence here of a missing dependency or a changed image requiring an upgrade.

## What ran and what verified

| Item | Verified result |
| --- | --- |
| Result directory | `startup-attribution-image-preflight-v1.QANl63cj` |
| Terminal result | Exit `0`; `inventory_complete_reference_mismatch`; empty stderr |
| Elapsed interpreter wall time | 5.627513442 seconds |
| Actual interpreter | CPython 3.12.15; only differing provenance field |
| NumPy / Arrow / Psycopg | 2.5.3 /22.0.0 /3.3.6; exact matches |
| libpq | Version integer 180006, binary implementation; exact matches |
| Driver hooks / pure parser | Nine exact source-file/function/signature/kind matches; parser exact match |
| Original function mappings | Both expected source hashes, qualified names and all ten mapped lines agree; original code bindings unchanged and local masks clear |
| Literal monitoring | Four events; restored successfully; within the16-callback ceiling |
| Source inspection | 12 reads /246,814 bytes; within128 reads /4 MiB total |
| Arrow import-time default pool | `mimalloc`, zero live/high-water bytes; a capability observation only |
| SQL / DB connections / snapshot calls / searches / providers | Zero each |
| Slurm allocations | Zero; one completed direct image-inventory invocation |
| Native acquisition / resource-margin qualification | False /false; cgroups not measured |

The manifest/archive match the released identities, all108 manifest files and
109 unique regular archive members verify, and the99 copied A1 reference files
match their immutable parent. The downloaded directory contains exactly the four
expected files. All three checksummed payloads agree; the JSON, exit code and
limits are consistent with the sealed contract. A fresh run of the independently
verified **local sealed data-only verifier** agrees. Returned code is not executed.

The independent review also recomputes the complete provenance difference,
compares source-line maps with literals parsed from the sealed original monitor,
checks all zero-action fields, restoration/callback/source-read limits, report
size and the exact image/parent/capsule identities. No new image, database,
experiment, search, test suite, fit, provider request, SSH connection or Torch job
was run during analysis. **5,519 prior source/evidence files are preserved.**

| Artifact | SHA256 |
| --- | --- |
| Returned `image-capability.json` | `fda84beafd88d3b3728f84c769258bd8623cc285d62a78fe8d34830b8916cde9` |
| Capsule manifest | `5f8bbb0dfa50b5346d00e4b60f5a7f3e6757bd48de3f0abe2073a3b882b554ce` |
| Capsule archive | `ccfab40dcd5325e9391f0ffdf76f3e8d73a7e2a343bcae8eed0d35ea6ac76fcb` |
| Parent A1 manifest | `065022eb9428e4a7607b1eafa5784855103e184b174b4b5ac5abd6389827b96a` |
| Unchanged image | `7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a` |

Image identity is associated through the reviewed checksum-verifying host wrapper,
the user's terminal output and returned capsule-bound metadata. This is not
hardware attestation or an independent remote hash read by this analysis.

## Interpretation and limits

The narrow reference-error diagnosis is supported: A0 explicitly freezes
CPython3.12.15, the earlier build/header review indicates3.12.15, and the actual
image now reports3.12.15. Every other captured provenance field is identical.
The current native `Driver.install()` checks the complete Python string, so its
historical A1 reference would reject this otherwise matching image at that guard.

This is a successful inventory with an unresolved release requirement. The full
original producer/constructor, monitored constructor frames, driver-wrapper
generator/transport behavior, signals and teardown were not exercised under
3.12.15 by this inventory. The literal monitor check uses only two tiny functions.
Source-definition equality alone cannot replace those target-runtime checks.

There are also no allocation proc/cgroup, data/graph/module lifecycle, snapshot
memory, observer overhead or full102-checkpoint acquisition measurements here.
The 5.63-second inventory time is not a search/agent performance metric; zero
Arrow import-time pool bytes do not estimate workload memory. Both prior resource
verdicts remain margin-inconclusive and full B2f remains held.

## Compatibility decision and next step

**GO for one isolated target-image reference correction and compatibility-readiness
work. HOLD the A2 acquisition until that corrected artifact is qualified and
separately reviewed for its finite handoff.** No dependency/image upgrade, version
wildcard, skipped guard or repeated image inventory is justified.

| Phase / gate | Required next work | Informs |
| --- | --- | --- |
| A2.0a inventory | Complete; preserve exact raw/contract/parent/archive and spent one-invocation binding | Actual image identities and the complete mismatch set |
| C0 correction boundary | Pin a separate exact image reference from this verified report; retain the original3.12.7 A1/local reference and all earlier seals. The only provenance change is the expected native Python patch version3.12.15 | Explicitly correct the target binding while preserving local evidence; no retrospective A1 image qualification |
| C1 isolated implementation | Give native entry points the strict image-bound reference; make local fixture expectations explicit. Synthetic/local references must be unable to submit or select the native reference through a fallback. Add original-function source/AST/line/local-mask validation before restore | Correct rejection/acceptance context; preserve all original hooks, SQL, code objects, data, policies and scientific/resource gates |
| C2 compatibility readiness | Source/sealed correctness, exact strict mismatch negatives, real driver/parser/generator/prepared/unprepared routes, monitored original producer/constructor, signals and cleanup; establish appropriate evidence under the exact3.12.15 interpreter | Whether the existing mechanisms work under the frozen target runtime. Local3.12.7 tests and the four literal image callbacks alone are insufficient |
| C3 reviewed release | Recheck manifest/archive, preservation, capability-before-restore, absolute launcher Python, one-allocation reservation, status/terminal collection, failed-prefix download, deadlines and cleanup | Concrete finite A2 handoff only after compatibility readiness passes |
| A2.1–2.3 acquisition | Still pending; unchanged max one1h/four-physical-CPU/32GiB job, zero searches, original one snapshot/four scans/readers/orders/holds and all102 checkpoints/ledgers/integrity/restoration/locks | Whether a complete trustworthy native attribution can be acquired |
| A3 | Only after complete independently verified acquisition, apply original informative/unresolved rules and separate resource rule | One separately frozen remedy, or unresolved/no-go closure |

The local/native distinction must be explicit, not a relaxed version comparison.
A corrected native reference must continue to reject3.12.7 and any unexpected
patch/library/hook/parser/source identity in the image. The original A1/local
reference remains strict for its own fixtures and historical receipts. The
correction should bind the existing image SHA, this complete reference and its
source report hashes. Corrected acceptance is not established in this review.

If C2 needs Torch to exercise the exact interpreter, prepare a separately bounded
zero-DB compatibility fixture capsule with explicit limits and checks before
issuing any new command. Do not reuse the completed inventory's binding or assume
its15CPU/30wall envelope covers a larger test suite. No such additional execution
or full acquisition is released here.

**Revised critical path:** verified image inventory → isolated exact-reference
correction → target3.12.15 compatibility readiness → reviewed finite native handoff
→ full capability before restore → bounded zero-search acquisition → independent
A3 decision → separate remedy/resource/full-workload qualification → possible B2f
release review. The one inventory is complete; no repeat is needed. There are no
new user commands at this analysis step.

## Sources and reproduction

- [Raw inventory](../trials/torch-reviews-startup-attribution-v1-release/returned/startup-attribution-image-preflight-v1.QANl63cj/image-capability.json) and [returned checksums](../trials/torch-reviews-startup-attribution-v1-release/returned/startup-attribution-image-preflight-v1.QANl63cj/SHA256SUMS).
- [Independent verification](../trials/torch-reviews-startup-attribution-v1-release/postrun-audit-2026-10-29/inventory-verification.json), [sealed replay](../trials/torch-reviews-startup-attribution-v1-release/postrun-audit-2026-10-29/sealed-replay.json) and [review receipt](../agent/docs/verification/startup-attribution-image-preflight-v1-postrun.json).
- [A0 exact expected runtime](../agent/experiments/startup-attribution-v1/ATTRIBUTION-DESIGN.json), [frozen design](fannagent-startup-attribution-v1-design-2026-10-28.md), [historical A1 reference](../agent/experiments/startup-attribution-v1/DRIVER-REFERENCE.json) and [strict install comparison](../agent/experiments/startup-attribution-v1/sa_driver.py).
- [Release review](fannagent-startup-attribution-v1-release-review-2026-10-29.md), [build/reference audit](../trials/torch-reviews-startup-attribution-v1-release/image-reference-audit.json), [unchanged probe implementation](../agent/experiments/startup-attribution-image-preflight-v1/README.md) and [probe contract](../trials/torch-reviews-startup-attribution-v1-release/torch-startup-attribution-image-preflight-v1/PROBE-CONTRACT.json).

Existing-data replay only, from the workspace root:

```sh
PYTHONDONTWRITEBYTECODE=1 agent/.venv/bin/python \
  trials/torch-reviews-startup-attribution-v1-release/torch-startup-attribution-image-preflight-v1/experiment.py \
  check-return --directory \
  trials/torch-reviews-startup-attribution-v1-release/returned/startup-attribution-image-preflight-v1.QANl63cj
```

This review relies on returned data and immutable local source; no new external
technical claim or literature search is needed.
