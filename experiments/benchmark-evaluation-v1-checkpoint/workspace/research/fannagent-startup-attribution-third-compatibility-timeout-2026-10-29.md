# Third A2 compatibility timeout: verified result and budget review

October 29, 2026, America/New_York. Roadmap decision D102.

Job **21382454** failed at the 300-second source-suite limit. The prepared-fixture
changes advanced the run from the previous attempt's 96 passing cases to **119
passing cases**, including the dedicated complete synthetic runtime/checkpoint
case. There are no recorded error, failure or subtest-error events. This is useful
partial correctness evidence, but it does not satisfy the complete 128-source plus
128-sealed qualification gate. Main A2 did not launch.

The remaining problem is a qualification budget that has not accommodated actual
native test preparation and verification. My local 63–64-second checks did not
establish native headroom; issuing the third handoff on that basis was insufficient.
There is no newly observed functional defect to justify another speculative
fixture rewrite. All three compatibility allowances are spent. Further handoffs
are held pending a prospective budget design and release review.

## Verified evidence

Campaign: `reviews-startup-attribution-compatibility-v1-prepared-fixtures-20261030T005654Z.5i2e3ef7`.

| Check | Result |
| --- | --- |
| Returned archive | 12,545 bytes; 16 unique regular members; all bytes match extraction |
| Archive SHA-256 | `5dda69a42a36775b5c9b9b17c253e2e45be6d181d8217944284b57db4fa8e214` |
| Locked raw hashes | All 11 pass; `complete=false` correctly records failure |
| Submission/host job identity | Both bind job 21382454 and the expected campaign |
| Capsule manifest | `417ed38074dabe90a66560605fd93e88d147a89691185b3be6b3e0bf6b57b840`; all 695 sealed files remain intact |
| Native identity | Exact Python 3.12.15, libraries, private hooks and parser reference match |
| Offline constructor dependencies | All three exact hashes match |
| Final host integrity | Capsule and unchanged SIF checks pass |
| Terminal state | Slurm FAILED / 1:0; 00:05:19; source deadline, guest 301.297 seconds, host 315.069 seconds |
| Reported activity | Zero real DB connections, SQL, PostgreSQL servers, ANN/exact searches and provider calls; no main A2 |
| Missing qualification | Final source guard, source target receipt, sealed candidate manifest and both sealed qualification receipts |

The final child restoration and unchanged-seed proofs are absent because the child
was terminated. Final host capsule/SIF integrity is a separate, successful proof;
it cannot replace the missing child proofs. The source guard implementation and
read-only mounts constrain execution, but the timeout's missing final guard counters
must not be silently treated as a completed guard qualification.

The independent audit also rechecks the 68 original main recipe files against the
contract and packaged copy, all 607 A1 parent files, both previous capsules and their
13-file and 16-file failed returns. Previous evidence remains intact. No returned
Python was imported or executed.

[Data-only verifier](../trials/torch-reviews-startup-attribution-compatibility-v1-prepared-fixtures/postrun-audit-2026-10-29/verify_returned.py),
[verification receipt](../trials/torch-reviews-startup-attribution-compatibility-v1-prepared-fixtures/postrun-audit-2026-10-29/returned-verification.json),
[raw campaign](../trials/torch-reviews-startup-attribution-compatibility-v1-prepared-fixtures/returned/reviews-startup-attribution-compatibility-v1-prepared-fixtures-20261030T005654Z.5i2e3ef7/).

## Where the time went

The 330-event ledger contains 120 starts, 119 passes, 90 fixture boundaries and one
suite start. Test 120, `test_original_mapping_mismatch_rejects_before_restore`,
started at 293.788 seconds after the suite-start event. Its clone and reseal
completed; the last recorded boundary is `fixture_reseal.after` at 299.698 seconds.
Its pass and final fixture hash were not reached. Eight other cases had not started.
These events show continued progress through the deadline, rather than a recorded
failure or a long unexplained wait at the end. They do not identify the exact
instruction running when the parent terminated the child.

| Completed fixture stage intervals | Count | Seconds |
| --- | ---: | ---: |
| Actual seed build, archive and baseline preparation | 1 | 46.215 |
| Shared seed/archive verification | 5 | 13.314 |
| Runtime fixture seed hashing | 10 | 25.349 |
| Hardlink/copy fixture cloning | 10 | 30.094 |
| Optimized canonical resealing | 10 | 3.941 |
| Final runtime fixture seed hashing | 9 | 24.790 |
| **Total completed, nonoverlapping fixture stage intervals** | **45** | **143.703** |

These intervals alone consume 47.9% of the 300-second allowance. They exclude other
verification, synthetic runtime work, assertions, setup and teardown. The full
four-signal test takes 76.659 seconds and the complete synthetic runtime/checkpoint
test takes 32.061 seconds. Those case durations **include** their fixture stages;
they must not be added to the table as disjoint costs.

The prepared implementation did remove repeated builds: the event ledger shows one
seed build and five class-request checks. Ten clones and ten reseals complete, but
only nine final fixture seed checks complete; the sixth shared-seed check and final
restoration proof are not observed. Do not promote these partial counts into the
complete local build/fixture proof.

[Source event ledger](../trials/torch-reviews-startup-attribution-compatibility-v1-prepared-fixtures/returned/reviews-startup-attribution-compatibility-v1-prepared-fixtures-20261030T005654Z.5i2e3ef7/run/guard-source.events.jsonl),
[test log](../trials/torch-reviews-startup-attribution-compatibility-v1-prepared-fixtures/returned/reviews-startup-attribution-compatibility-v1-prepared-fixtures-20261030T005654Z.5i2e3ef7/run/checks-source.log).

## Source audit and limits of the diagnosis

The A1 manifest covers 298,917,834 content bytes. Its largest file,
`frozen/inputs/development-evidence.json`, is 262,630,951 bytes. The synthetic fixtures
retain this immutable historical material even though their actual row payloads
are small. They are therefore not small packages for copying and verification.

The actual builder verifies its parent, copies the full manifest inventory, hashes
the output, calls the real verifier and creates an archive. The runtime still
calls the unchanged `pc_common.verify` before its operational body. That verifier
checks the package manifest and several nested parent/native/evidence pin sets,
which revisit content. The prepared helper deliberately leaves those production
checks intact, while fully hashing its own seeds before and after every fixture.
Hardlinks remove bulk copying; they do not remove byte reads and hashing.

This explains substantial remaining preparation/verification work. The traces do
not separately measure native filesystem wait, CPU hashing, metadata operations or
each internal verifier call. Do not attribute all 143.703 seconds to storage, claim
an exact total byte-read count, or infer an application performance regression.
The source progress improved between attempts, but these separate allocations are
not a paired benchmark of the helper optimization.

[Builder](../agent/experiments/startup-attribution-v1-image-reference/experiment.py),
[production verifier](../agent/experiments/startup-attribution-v1-image-reference/pc_common.py),
[runtime entry](../agent/experiments/startup-attribution-v1-image-reference/pc_runtime.py),
[synthetic fixtures](../agent/experiments/startup-attribution-v1-image-reference/sa_fixtures.py),
[prepared helper](../agent/experiments/startup-attribution-compatibility-v1-prepared-fixtures/fixture_io.py).

## Next step and decision gates

The recommended next work is **C2B: a prospective compatibility-budget revision**,
with no additional fixture optimization unless this audit exposes a concrete
semantic defect. Keep all 128 source and 128 sealed cases, strict references,
full verification, guard restoration and zero real DB/SQL/search requirements.
This changes only the future correctness qualification's time contract; it must
not alter the failed result, scientific gates, main A2 resource limits or B2f margins.

| Phase | Required work | What it informs / gate |
| --- | --- | --- |
| C2B.0 — complete, data-only | Verify this return, stage durations, remaining cases and source verification costs; preserve all attempts | Current 300-second source cap is demonstrably insufficient; no recorded functional failure. No retrospective pass or retry |
| C2B.1 — pending design | Freeze separate suite, candidate-build, guest, host and cleanup budgets; account for their complete critical-path sum and explicit headroom | Decide whether a finite revised qualification is justified; no dispatch until the budget and release criteria are reviewable |
| C2B.2 — pending implementation | Make only the isolated compatibility time/accounting changes; preserve fixture/main bytes; check deadline boundaries, cleanup, failure publication and complete local source/sealed guards | Complete local reviewable capsule and exact commands; local elapsed time remains supporting evidence rather than a native upper bound |
| C2B.3 — held | One separately bound native qualification, followed by independent full source/sealed/guard/identity/exit/integrity verification | Require every original case and final proof. Any timeout or missing proof closes that allowance failed; no automatic continuation or retry |
| C3 and main A2 — held | Only after C2B.3 passes, seal/review main A2 and then run its separate zero-search diagnostic | Actual startup memory/retention/verification-I/O evidence for A3; no agent-speed or calibration qualification by inference |

For the next design review, a **20-minute planning option** can allocate 420 seconds
to each suite, 90 to the standalone candidate build and 30 to guest cleanup:
`420 + 90 + 420 + 30 = 960` guest seconds. Keeping 90 host-startup and 60
host-cleanup seconds leaves 90 outer-margin seconds under 1,200 seconds. Retain
two physical CPUs and 4 GiB for compatibility only. This is an explicit sizing
proposal, **not a frozen contract or released capsule**. The source prefix already
exceeds the old cap; the remaining native cases, final receipts and sealed suite
are unmeasured, so 420 seconds is not an empirical upper bound or a promise of
completion. The design must make that uncertainty and its finite failure branch
explicit rather than presenting another local pass as a native guarantee.

**Revised critical path:** verified third failed return → C2B budget freeze/review
→ budget-only implementation and complete local checks → one independently
verified native qualification → C3 main production seal/release → main A2 → A3.
No new capsule, experiment, test-suite execution, SSH or Torch submission was made
in this audit. No user command is needed now; preserve the current package,
reservation, archive and scratch directory.
