# B2b exact-top10 catalog serialization correction

Frozen October 26, 2026, before any corrected native measurement. This addendum preserves the [original scientific design](fannagent-exact-topk-v1-design-2026-10-25.md) byte for byte. Its recall, semantic, plan, A/A, economic, cohort, schedule and per-attempt resource limits remain unchanged.

## Trigger and evidence limit

The user reports campaign `reviews-exact-topk-v1-20261026T032153Z.9khasec1`, job `20941363_0`, failed with exit1 after00:06:17 at the initial catalog guard. Reported backend searches0, empty operation counts, providers0 and protected sources unchanged. Raw archive, scheduler accounting and cleanup files have not yet been downloaded or independently verified. This is failed qualification, not valid quality-negative or economic evidence. Preserve its package, binding, reservation, work directory and full resource charge; no repeated v1 submission.

## Deterministic defect and bounded correction

The original catalog query applies `to_jsonb(t)` to a row containing PostgreSQL `oid`. PostgreSQL17.11 [type categorization](https://github.com/postgres/postgres/blob/REL_17_11/src/backend/utils/adt/jsonfuncs.c#L5608-L5705) does not classify `oid` as a JSON numeric type; [jsonb conversion](https://github.com/postgres/postgres/blob/REL_17_11/src/backend/utils/adt/jsonb.c#L764-L772) emits its output as JSON text. The original mock uses integer264013 and the original guard compares against that integer. Correct native JSON contains `"264013"` and necessarily fails that comparison, even for the intended unchanged graph. This source-backed defect explains the reported failure class; it does not prove that no other remote field differs.

Use an exact, type-strict expected JSON text OID `"264013"`; do not coerce arbitrary input or drop the OID check. Keep the SQL unchanged. Keep byte size, opclass, options, validity, structure and immutable physical-file checks. Report individual mismatched fields. Preserve the raw rejected catalog and timer in `catalog-failure.json`, including catalog-stability errors, before propagating failure. Add an explicit `initial_catalog_qualification` progress phase so a catalog error is not shown as restore progress.

The correction has a distinct source directory, protocol version, package, campaign prefix and once-only reservation. Preserve original design and sealed v1 evidence. Pin this addendum plus the original manifest in the new seal. No adopted backend, graph, module, data, policy, endpoint, formatter, decoder, SQL, planner setting, timing schedule or scientific gate changes.

## Recovery order and stop rules

1. Collect the terminal failed v1 campaign using the original controller; download/checksum using its original helper. Verify original submission/package/job/accounting, failure0-search accounting, cleanup and protected-source evidence. If these differ from the reported trigger, stop and investigate; no corrected submission.
2. Complete local correctness, source/old-artifact preservation, source/sealed/package checks for this correction. A local PostgreSQL16 scalar fixture is optional engineering evidence only; sandbox inability to create shared memory is recorded and is not a native qualification pass. No benchmark data or native searches are allowed locally.
3. Only after raw review, release the corrected package commands for one fresh prospective allocation. Its controller requires the original failed campaign and checksum-valid collected archive, pinned v1 manifest/binding, zero-search catalog failure, successful reader/database cleanup, unchanged protected sources, and terminal FAILED scheduler evidence. A missing/changed prerequisite rejects submission before reservation or sbatch. Keep the original allowance consumed; the correction permits at most one additional4CPU/32GiB/two-hour allocation,6,600-second work deadline and40,230 backend attempts. No automatic repeat after another failure.
4. Corrected native catalog/graph/module/plan/semantic qualification must pass before interpreting quality. Acquire1,800 fresh references after30 qualification searches; valid quality failure stops at1,830. Only quality pass unlocks the two existing temporal blocks, all16 A/A interval checks and adjusted economic gates. Verify complete raw and unchanged sealed replay before any next design decision. Original execution remains adopted; no router/adoption/confirmation follows.

## Progress

- [x] Pin the original user-reported failure identity and source-backed type defect.
- [ ] Implement the separate correction and pass local/source/sealed checks.
- [ ] Download and independently verify the original failed archive.
- [ ] Release corrected one-attempt user commands after prerequisites pass.
- [ ] Verify corrected native gates/results and update the roadmap.

The checklist here records the prospective freeze. Track later completion in the permanent roadmap and correction receipt, without editing this frozen addendum.
