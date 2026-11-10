# A2 C2B: prospective compatibility budget correction

BUDGET-REVIEW.json independently rechecks the job21382454 ledger, original source
and third failure audit before BUDGET-FREEZE.json. All three earlier native
allowances are spent. This is one distinct correctness qualification, with no retry.

The 20-minute planning option omitted guest preflight and the wrapper's separate
termination reserve. The frozen envelope is21minutes,2physical CPUs,4GiB:

| Component | Seconds |
| --- | ---: |
| Host verification and container startup |90 |
| Guest preflight and exact provenance |30 |
| Complete source suite, including guard/receipt/hash checks |420 |
| Original unpatched standalone candidate build and checks |90 |
| Complete sealed suite, including guard/receipt/hash checks |420 |
| Guest cleanup and terminal publication |30 |
| Container termination |15 |
| Host final verification and locked publication |60 |
| Outer scheduler margin |105 |
| Total |1260 |

Guest envelope:990seconds. Host passes its actual guest endpoint without the old
15-second subtraction; termination has its own reserve. A late container start or
insufficient full phase/tail reserve fails closed, rather than shortening a suite.
Every phase has monotonic timing plus an alarm; publication uses the cleanup
endpoint. Owned synthetic scratch stays available for diagnosis. No background
watchdog thread is introduced.

420seconds is a prospective finite cap, not a measured native upper bound. The
119-pass source prefix, eight unstarted tests, final checks and all sealed costs
leave uncertainty. Any timeout, missing receipt or denied action consumes this
allowance failed/incomplete. Preserve all raw evidence and reservations.

All128 original main cases run in each source/sealed suite. Main68recipe files,
all assertions, strict target3.12.15 references, dependencies, full production
verification, fixture_io.py and check_child.py remain byte-identical to the last
prepared-fixture package. Each child must still prove one actual build/four reuses,
six seed/archive checks and restored builder, ten clones/reseals/unchanged seeds,
restored connection bindings and zero denied actions. The independent standalone
candidate build remains unpatched. Local tests add deadline boundary, phase
admission, cleanup/failure-publication and contract-accounting checks.

Zero real DB/connections/SQL/server/ANN/exact/provider/fit. Main A2 remains held:
its separate1h/4CPU/32GiB code, science and resource rules are unchanged. Native
128+128 success and complete guard/identity/exit/integrity/lock proof must be
independently verified before C3 can seal/review main A2. Local Mac checks provide
correctness evidence without establishing target headroom or scientific results.

Use only this output directory's COMMANDS.txt after local release verification.
Do not resubmit any previous package or reset its reservation.
