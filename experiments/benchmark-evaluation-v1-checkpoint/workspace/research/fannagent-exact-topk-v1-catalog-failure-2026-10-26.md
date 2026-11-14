# B2b initial catalog failure and prospective correction

The user reports job `20941363_0` in campaign `reviews-exact-topk-v1-20261026T032153Z.9khasec1` failed at the first catalog check, with zero backend searches and no operation entries. The reported elapsed allocation is6m17s, exit1:0 and protected sources unchanged. This is **failed qualification**, with no recall, latency or A/A evidence. The SSH session timeout is independent of Slurm execution. This record is based on pasted status; raw accounting and cleanup have not yet been independently verified. The generic host failure and stale restore progress do not identify another scientific failure.

## Confirmed harness defect; limits of the diagnosis

The catalog SQL selects `c.oid` into a composite passed to `to_jsonb(t)`. PostgreSQL17.11 [json_categorize_type](https://github.com/postgres/postgres/blob/REL_17_11/src/backend/utils/adt/jsonfuncs.c#L5608-L5705) handles built-in `oid` through its ordinary output category, and [datum_to_jsonb_internal](https://github.com/postgres/postgres/blob/REL_17_11/src/backend/utils/adt/jsonb.c#L764-L772) emits that category as JSON text. Thus the correct graph ID arrives as `"264013"`. The original validator demands Python integer264013; its mock fixture also uses an integer. A source-backed regression supplies the correct text representation, reproduces the original rejection and passes the corrected strict representation check. This defect is established without a benchmark; it does not independently establish every actual remote catalog field.

The old observer validates before storing the catalog and saves `metadata.json` only on a successful measurement exit. The raw rejected row is therefore expected to be absent from this failure archive. We cannot retrospectively reconstruct it from a generic error. The corrected observer preserves rejected raw values, hashes, phase, timer, prior accepted hash and field-specific errors. The native SQL, graph identity, byte checks and scientific thresholds are unchanged.

A temporary PostgreSQL16 scalar-only fixture was attempted; initialization failed under the filesystem sandbox's shared-memory restrictions before any SQL ran. Temporary directories were removed. That failure is recorded separately and is neither native qualification nor experimental evidence. No existing database or vector dataset was accessed, and no new ANN/native/Torch experiment ran.

## Separate correction and unchanged scientific scope

The [frozen correction addendum](fannagent-exact-topk-v1-catalog-fix-design-2026-10-26.md) pins a new source/package/version/campaign/reservation and preserves the [original design](fannagent-exact-topk-v1-design-2026-10-25.md). Original source, seal, archive, receipt and failed allowance are retained. This correction changes the expected JSON type, diagnostics, progress label, provenance and recovery prerequisites. Reader implementation, quality computation, statistics, report and host/container launcher are byte-identical; settings, native query, data/module/graph,200 exposed vectors/600 cases, quality reserve,16 A/A intervals, eight economic endpoints and attempt limits remain unchanged.

The corrected controller checks the pinned original manifest/binding/campaign/job, zero-search failure, stopped database/closed readers, protected evidence, terminal FAILED scheduler record and checksum-valid collected archive before any new reservation or sbatch. Missing or changed prerequisites stop submission. One separately declared corrected allocation is prospective, not a reset or hidden repeat of the original allowance. No corrected run is submitted or authorized automatically by a passing local mock.

## Critical path and user handoff

1. **User now:** [collect and download the failed original archive](../trials/torch-reviews-exact-topk-v1-catalog-fix/RECOVER-FAILED-V1.txt) using the original controller/helper.
2. **Codex:** verify archive/submission/job/accounting/cleanup/protected evidence; reconcile any mismatch. The expected ingest output preserves a failed/incomplete campaign and gives no performance verdict.
3. **After verification:** release separately corrected sealed package instructions. Do not delete a reservation or resubmit original v1. Actual catalog/semantic/plan qualification is still required.
4. Only native qualification and complete valid quality pass unlock two temporal blocks/A/A/cost analysis. Verify unchanged sealed raw replay before a scoped next decision. Original execution remains adopted; no router, deployment, protected-query consumption or performance conclusion follows.

Track source/sealed check outcomes, package hashes, preservation and pending raw/native gates in the [correction receipt](../agent/docs/verification/exact-topk-v1-catalog-fix-implementation.json), [local checks](../trials/torch-reviews-exact-topk-v1-catalog-fix/local-checks/), [user-reported failure record](../agent/docs/verification/exact-topk-v1-torch-failure-2026-10-26.json) and [permanent roadmap](fannagent-performance-research-roadmap-2026-10-22.md).
