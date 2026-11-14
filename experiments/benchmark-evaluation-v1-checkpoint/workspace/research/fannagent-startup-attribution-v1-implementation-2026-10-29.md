# A1: startup attribution implementation and local readiness

Completed October 29, 2026, America/New_York; implementation began October 28. NEXT-STARTUP-ATTRIBUTION-01.
Protocol `startup-attribution.v1`. **A1 complete for local readiness only.**

The frozen A0 instrumentation is implemented in a new isolated harness and
verified from both source and its sealed copy. There is no new native result,
resource-margin qualification, performance claim or Torch allocation. A2 remains
unreleased; the controller, submit/dispatch routes and both native entry points
reject a native launch from this A1 artifact. Full B2f stays held.

## What changed

| Boundary | Implementation and purpose |
| --- | --- |
| Original snapshot | Local LINE monitoring, tool4, on the original producer and constructor only; source/AST/line-table/frame checks, DISABLE and complete mask/callback/tool restoration. Existing raw cursor close supplies S03/S04; the unchanged scoped identity helper supplies S10/S11. No alternate producer/constructor executes. |
| Memory observations |102 mandatory checkpoints:12host/90runtime. Mapped job/step-user/task current/peak/events/anon/file/kernel, owned-process RSS/HWM/fault/I/O identity and Arrow default-pool live/backend observations. Optional values remain distinct from zero. Scalar metadata/alias proofs retain no frames, rows, matrices or pages. |
| Driver commands | Nine source/signature-pinned Psycopg3.3.6 hooks, bounded owned connection admissions and API capabilities, original/prepared execution, internal transactions, declaration/description/fetch/close and both deallocation routes. Exactly one execution link per API. No new SQL or fetch. |
| Evidence buffering | Attempt IDs reserved before dispatch; one joined dispatch/completion/error row per request, including operation, API template hash and existing fetch row count. Pending work remains explicit. Bounded buffering avoids per-fetch fsync; hard-kill prefixes cannot qualify. |
| Existing I/O | Explicit original-operation roles use existing returned inventory/copy metadata. The clone parent references its children; the actual copy owns its bytes. Unknown logical byte counts stay unknown. No extra content scan or file/cache ownership claim. |
| Teardown | Original close/rollback/server stop and final source proof still run if observing them fails. Minimal cleanup lanes invalidate acquisition. Hook and monitoring restoration precede locks. All four signal handlers are exercised locally. |
| Independent replay | Original scientific/integrity/resource reconstruction first, then102-point ordering, exact page/transaction/API/dispatch/role/budget parity and actual binding provenance. Missing, tampered, pending or incomplete evidence cannot qualify. |

The internal host/runtime observer partition is conservative within the unchanged
aggregate caps:3+12CPU seconds,6+24observer-wall seconds,1024+7168reads,
8+56MiBread bytes,2+14MiBraw and32+224role records. Host buffering is flushed
before the runtime owns its writer. Sampler-plus-diagnostic limits remain60CPU
seconds,500000reads and512MiB; the five-second stale-sampler rule is unchanged.
Absolute deadlines reserve cleanup/postflight and clamp the runtime to remaining
wall allowance. No added resource entitlement is created.

## Local evidence and limits

- **155 unchanged baseline regression checks passed.**
- **100 final A1 source checks and 100 sealed checks passed**,
  with stable source fingerprints and correct test-module origins.
- Actual unchanged producer/constructor integration observes the ten selected
  source-line points and the two cursor-close points, below512callbacks. The
  initial isolated constructor proof used91LINE callbacks; this is a mechanism
  count, not a performance result.
- Actual private driver methods execute against synthetic send/result transport.
  Ordinary/prepared execution, declaration/description, SQL/protocol deallocation,
  unknown routes/pipeline blocking and generator yield/send/throw/close/return
  behavior are covered. Metadata-only ledgers reconcile2473pages/pass,
  2472x100+86rows, and9892fetches over four passes. No full native row population
  or database connection is created by those fixtures.
- The real pinned server-cursor iterator also stops after a64-row synthetic partial page with one fetch and no extra exhaustion fetch; its separate source-pinned receipt is retained.
- The actual host and runtime entry paths are exercised with synthetic files,
  processes and transport. The successful runtime reaches all90runtime points;
  host checks cover the12host points. ALRM/TERM/USR1/INT and BaseException paths
  close resources and restore bindings. Observer-failure close/rollback tests
  delegate cleanup; combined observer/transport errors remain represented.
- Replay tests remove each of102required points, alter pages/transactions,
  duplicate commands, leave pending work, omit dispatch evidence or exhaust
  combined budgets. Each invalid case rejects. Descriptive interpretation tests
  cover cursor/constructor/HWM, default-pool and file-charge coincidence rules;
  retained context alone cannot make an informative result.
- Fixtures use at most64source rows x768, bounded literal oracles, or metadata-only
  counts. They establish local semantics/accounting, not native data quality,
  memory feasibility, overhead, physical I/O, causal attribution or savings.

A final source run correctly rejected a stale **simulated** heartbeat: its fixture
refreshed health only at phase changes. The correction models the independent
sampler heartbeat on reads without creating a concurrent Python thread. The
explicit sampler-failure case remains negative. That failed receipt/log and prior
intermediate local passes are preserved; no native gate or margin was relaxed.
A final source review also caught a real validation gap in the provisional
97-check candidate: the synthetic converter published cursor query state earlier
than the real driver, masking parameterized-template validation failures. That
candidate and its provisional documentation are preserved as superseded and were
never released natively. The correction validates exact converted template bytes
with the pinned uncached pure parser, without parameter dumping or cache priming.
New actual PostgresQuery/Transformer and _execute_gen prepared/unprepared checks
prove this route; poisoned cursor state cannot bypass validation. The final
source and sealed suites include these checks.

Earlier local corrections included synthetic transport escaping/cursor ownership,
separating inherited seal metadata during rebuild, aggregate budget accounting
and preserving final proof work when observation fails. These are local readiness
iterations, not spent Torch attempts.

## Seals and preservation

| Item | Verified value |
| --- | --- |
| Manifest SHA256 | `065022eb9428e4a7607b1eafa5784855103e184b174b4b5ac5abd6389827b96a` |
| Archive SHA256 | `d399c84f81f4069b0e63ee539f893f6498ddea1874db02cf1efd779c5bb42e94` |
| Manifest files / regular archive members | 607 / 608 |
| Original frozen native files | 126 byte-identical |
| A0 source/recipe pins | 246 unchanged, with copies in the new seal |
| Earlier evidence files | 3987 unchanged |
| Native handoff | Unreleased; guarded |
| New ANN/exact searches, native DB queries, experiments, jobs, fits, providers, SSH |0 |

The original contract, schedule, resource/stream contracts, eligibility, exposed
cohort, source/settings and identity helper remain byte-identical to M3. The
original producer/constructor/vendor/module files remain bound to their original
manifest. Prior packages, raw returns, bindings, reservations and both resource
verdicts are preserved. The latest stream campaign is also included in the new
native preservation contract for any later separately released artifact.

Local readiness archive: `trials/torch-reviews-startup-attribution-v1/torch-startup-attribution-v1.tar.gz`.
It is not an upload/submit handoff. Source and reproduction instructions:
[isolated A1 harness](../agent/experiments/startup-attribution-v1/README.md).
[Readiness evidence](../trials/torch-reviews-startup-attribution-v1/),
[independent seal/preservation verification](../trials/torch-reviews-startup-attribution-v1/release-verification.json).

## Gates and next step

| Gate | Status / required work | Informs |
| --- | --- | --- |
| A0 | Frozen human/machine/checkpoint/hook design preserved | Prespecified question, invariants and interpretation |
| A1 | Complete, local source/sealed checks only | Instrumentation/accounting is ready for a separate handoff review |
| A2.0 | **Unreleased**. Prepare a separately reviewed release; actual pinned-image library/private-hook/source/Arrow/monitor/proc/cgroup capability must qualify before costly restore | Local Mac reference is compatible with the actual image, or capability-stop |
| A2.1–2.3 | Only after explicit finite release: unchanged identity/zero-search/integrity/lifecycle; all102points, dispatch/page/row/role/budget coverage; cleanup/restoration/locks/fresh replay | Whether complete trustworthy native attribution was acquired |
| A3 | Use only validated new bracket facts.256MiB remains descriptive triage, never an acceptance margin or savings bound | Select one separately frozen remedy design, or close unresolved/no-go |

**Revised critical path:** A0 frozen → A1 locally complete → separate A2 handoff
review/release → actual-image capability before restore → bounded zero-search
acquisition → independent A3 informative/unresolved decision → separate remedy
compatibility/resource qualification → full-workload memory/B2f release review.

The actual-image preflight must match recorded driver method/file hashes,
signatures and actual interpreter/NumPy/Arrow/Psycopg/libpq capability. The local
reference is not an attestation of the image. A mismatch stops without choosing
another hook, dependency upgrade or automatic retry. If later released, the
maximum remains one1h/four-physical-CPU/32GiB allocation, one snapshot/four full
verification scans, original200admissions/ten readers/maxsix live/two servers,
and zero ANN/exact searches.

The resource rule is still peak+2GiBreserve+2GiBworkspace <= finite32GiBcap,
with no positive max/OOM/failure deltas. No file-cache subtraction, early snapshot
release, GC/trim/eviction, cap increase or calibration release follows from A1.
There are no Torch commands for the user to run at this step.

## Sources

The implementation follows the unchanged [A0 design](fannagent-startup-attribution-v1-design-2026-10-28.md),
[checkpoint catalog](../trials/torch-reviews-startup-attribution-v1-design/CHECKPOINTS.json),
[driver-hook catalog](../trials/torch-reviews-startup-attribution-v1-design/DRIVER-HOOKS.json)
and [working-set audit](fannagent-startup-working-set-audit-v1-2026-10-28.md).
Library references and their limits remain recorded in
[A0 primary sources](../trials/torch-reviews-startup-attribution-v1-design/primary-sources.json).
The actual installed private-method reference is sealed as
[DRIVER-REFERENCE.json](../agent/experiments/startup-attribution-v1/DRIVER-REFERENCE.json);
source/signature hashes and actual execution checks supplement those references.
No new literature search or native experiment was required for A1.
