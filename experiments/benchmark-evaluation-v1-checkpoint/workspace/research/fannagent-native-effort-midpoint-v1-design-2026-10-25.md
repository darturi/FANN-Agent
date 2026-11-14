# B1b2: quality-first fixed native effort comparison

Contract: `NEXT-EFFORT-MID-01` / `native-effort-midpoint-v1`, design version1.  
Frozen design date: October25,2026, America/New_York, before any480 outcomes.  
State: prospective documentation only; implementation, local checks, package and native execution have not occurred. The user's current request authorizes the [read-only B1 review](fannagent-effort-interface-review-2026-10-25.md), not execution of this proposed campaign.

## Question and permitted conclusion

Does **one fixed native `ef_search=480`** preserve the original study640 quality reserve across the three existing contexts and save useful **warm persistent-reader full query time**, using the same native execution method for both arms?

480 is the arithmetic midpoint of320/640, chosen prospectively for one bounded information probe. It is not predicted to pass. Do not interpolate recall/latency, assume nested returned sets, tune another value, select a per-context map or fit a router. Effort is fixed for each owned reader's lifetime. There is no online effort envelope or selector.

This is an exposed-development, constant-configuration diagnostic. It does not qualify the public raw-query API, fresh-reader activation, cold buffers, concurrency, deployment, independent confirmation, a query-dependent policy or agent-method improvement. B1b's aggregate `measurement_inconclusive`, P2/P3 closure and retained original execution remain unchanged.

## Immutable inputs and execution boundary

Use B1b's current physical graph, frozen runtime/backend and same600 cases/200 vectors. Implementation must copy or reference them by a new explicit manifest without modifying any old source/package/raw result. Before sealing, pin every source, request, eligibility and input digest, this contract's digest, order schedule and analysis source. Any change to this design must be recorded before a native480 outcome, with an explicit design revision rather than a silent allowance change.

| Identity | Required value / boundary |
| --- | --- |
| Physical index identity | `90f4a709ab3ee7ce40fe7630009b29d5646f6e1e80ceab8c2246cb970d803484` |
| Index file | `base/16384/264013`,1,012,678,656 bytes; SHA `dbc14b0912d7e9ad9cd4ddcf806cac081412e66b1861de7ce3629fd81e23b393` |
| Native module | `e7dcace1f4dfd4ea233256d6cdfc17b3190f3f07cccb6406b479b5ebe8b85811` |
| Runtime profile | `b2974c2c65d40780d207109d9bbd298b2628ea58abde673c0dd479c1a0e52ed3` |
| Feature registry | `fc42b1fb1441518b15123ed30ba2a0d0c96e9c74d4f0727ab9eb391597cdbf37` |
| SIF image | `7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a` |
| Dataset parquet | `06eae31a43ecfd63a647f6fa93a9c00bcb2350ca6fe2f2bcd35d007c13b2e4ee` |
| Source shape |247,286 rows;768 dimensions;cosine;k10;iterative scans off |
| Origin / comparator / candidate | Inspected origin remains320; declared study reference640; candidate480. Upstream boot40 is separate metadata |
| Cohort | Exact existing B1b200 exposed vectors × unfiltered, `m_000000>=32`, `m_000000>=108`; no additions or substitutions |
| Prior package anchor | B1b manifest `35a09d4e2fd71598a023f6479e418d9e8bc90434d764a53564c60a5436b69c1f` |

The origin manifest is privately owned and preserved. Each effective binding differs only in the declared `hnsw.ef_search`; actual settings and target acknowledgement must agree. No index/module rebuild, changed GUC, iterative scan, policy installation, native-direct optimization, new query validator, SQL/transport optimization or pooling dependency may be bundled with480.

Use the inherited frozen native SQL/execution/scoring methods for both arms. The isolated harness may construct single-reader effective bindings for480/640, validate the sealed cohort once with the shared `Snapshot.query`, own those validated requests, check connection/binding identity symmetrically and record time/results. Shared request admission/snapshot creation is recorded outside the warm endpoint. This is the same prevalidated-cohort native boundary for both arms, not caching validation of arbitrary live requests by query ID. The public API and its checks are untouched.

Create the common snapshot through the initial640 reference reader; give subsequent readers that same immutable snapshot. Do not create an extra origin320 search arm. Source320 remains provenance, and new performance claims are limited to480 versus the study640 reference. Historical6076-graph results supply neither truth nor cost labels.

## Phase0: implementation and local readiness

Implement an isolated harness and package only after the next implementation request. Do not edit adopted code or the sealed B1b implementation. G0-B1b2 requires:

1. Strict effort/type/context/cohort/identity admission, immutable origin/effective views, identical native method identity and complete timing boundaries.
2. Synthetic/fake-reader checks for settings isolation, closed/stale/replaced connection rejection, SQL error/rollback, explicit new-reader recovery, invalid/missing output rejection, deterministic schedule, early quality stop and all resource counters.
3. Small mock raw round-trip plus a full600-case/two-block mock schedule proving the counts below; raw tampering and incomplete/censored runs must fail verification.
4. Data-only ingest that uses the campaign identity from the verified submission/binding, not the basename of a container mount. A different mount path must not alter scientific parity; unrelated metadata/scientific differences must still be rejected.
5. Exact package/archive manifests, local correctness/lint/format/shell checks, declared input/protected-source preservation and an implementation receipt. No native qualification follows from mocks.
6. User-facing upload, once-only submission, status, collect and checksum/download commands only after the package exists. Preserve uncertain/failed reservations; no automatic resubmission.

Before native execution, seal query/order seed **20261025**, bootstrap seed **20261019**,10,000 vector-bootstrap resamples, exact tie-aware scorer, criteria, guards and raw schema. No result-dependent changes or additional seed trials.

## Phase1: native conformance, maximum30 searches

Use one existing fixture per context. Perform the following ten searches for each fixture, charging every attempt, including a failed search if one occurs:

1. Exact reference through the initial640 reader, using the unchanged transaction-local exact path.
2. Ordinary native640 on that reader.
3. Ordinary native480 on a newly admitted480 reader.
4. Native640 again to check reader-setting isolation after480.
5. Native480 again to check determinism/isolation after640.
6. Native480 through an explicitly new reader after the prior480 reader experiences an injected non-search SQL transaction error, rollback and close; reject the old handle without issuing a search.
7. Exact reference through640 again; truth and session settings must be unchanged.
8. Native640 after that exact transaction; output/settings must match the earlier640 result.
9. Native640 through a freshly created temporary640 reader; compare with the initial640 result and close the temporary reader afterward. The initial reference reader remains available.
10. Native480 on the fresh post-error480 reader; verify unchanged output/settings.

For step9, create one temporary640 reader per fixture, execute its one search, then close it. For step6, there are two480 admissions per fixture; close both after use except the final fixture's post-error reader, which supplies Phase2's480 references. These operations require nine temporary/480 reader admissions across the three fixtures, plus the initial640 reader. There is no hidden search retry. Injected non-search error statements are separately recorded (three total), not ANN/exact searches.

Verify actual `pg_settings` including boot/reset/source/unit metadata, target/index identity, native HNSW plans, ordinary autocommit execution, no policy/trace installation, exact-plan index bypass, exact/native independence and finite valid complete results. Verify the index/module before restore use and after the campaign, and effective settings/connection identity at each phase boundary. Record SQL/administrative/audit operations separately; they are not free latency or omitted resource work. Native qualification or integrity failure stops as invalid/incomplete, not as negative evidence about480 quality.

## Phase2: quality screen before repeated timing, maximum1,800 searches

For each of600 cases collect a **fresh exact reference, native640 and native480** result:600×3=1,800 searches. Exact results use the unchanged full eligible-set/tie-aware scorer. Retain compact truth/outputs/proofs, not600 duplicate full eligible-ID sets in memory. Use sealed snapshot eligibility metadata to validate predicates; do not change scoring semantics or infer exact truth from ANN results. Quality collection order is sealed before execution and cannot depend on earlier outcomes.

Require all600 results in each native arm to be valid, finite, unique, predicate-correct and complete top10. Require each arm's mean recall>=0.95 in every filter. Require the **lower pointwise95% bound on mean recall480−recall640>=−0.0025** overall and separately in each filter. Cluster the three filters of each vector together; use the frozen10,000-resample vector bootstrap. The −0.005 final margin is diagnostic only, never a substitute for the development reserve or independent confirmation.

If any complete-data quality gate fails, stop the finite probe as `closed_negative_quality`, with at most **30+1,800=1,830 searches**. No timed phase, per-context rescue, additional effort, new sample or threshold relaxation follows. Missing/invalid data or aborted acquisition is invalid/incomplete, not an evaluable quality loss. Repetitions do not add independent quality observations.

## Phase3: conditional warm comparison

Start only if Phases1–2 pass. Create four private native benchmark readers:640-A,640-B,480-A,480-B. Each owns exactly one immutable binding and is initialized once, before timing. These are A/A experimental replicas; each measured arm uses one reader. Keep the initial640 reference reader for conditioning. Close the Phase2 candidate reader before the four benchmark readers open. At most five readers are live; maximum campaign reader admissions are **14** (initial1 + qualification9 + benchmark4). Do not reconnect/retry transparently or replace a benchmark reader mid-run; connection loss aborts the campaign.

There are **two complementary temporal blocks inside one allocation/private database**. They are not independent machines or allocations. Use the sealed200-vector/600-case order and reversed cell order in block1. For each query and cell, execute two rounds with adjacent label pairs **ABBA or BAAB**, chosen by sealed hash of query/cell/seed; block1 complements block0. This gives two cells × two rounds × two labels = eight slots per case per block. All workloads execute serially; no concurrent timing or exploratory requests.

Each slot contains:

1. Two native640 conditioning searches on the separate reference reader.
2. One discarded warmup on the designated benchmark reader.
3. Three retained ordinary native searches on that reader.

Before and after each native call, symmetric lightweight ownership guards reject closed, replaced or mismatched connection/binding identity. Include those guards inside the outer query timer for **both** arms. Record no successful result after an error. Actual settings/plan audits occur outside the primary timed calls at declared boundaries and are separately timed/logged. No session-setting SQL, effort selector, dynamic Pool or additional per-query validator is inserted inside one arm only.

Primary endpoint is **full outer warm query latency**, including inherited statement/vector/context construction, guarded native execution, transport, decoding and output construction. Raw timestamps and SQL-only diagnostics are also saved. Common snapshot/request admission, each reader's initialization/first-use warmup, conditioning, audits and all cleanup are separately charged and reported. No control-gap subtraction, SQL-only substitution, free startup or assumed deployment amortization is allowed. There is no qualified activation endpoint in this campaign.

| Resource category | Per block | Campaign if quality passes |
| --- | ---: | ---: |
| Retained warm executions |600×8×3=14,400 |28,800 |
| Discarded warmups |600×8=4,800 |9,600 |
| Conditioning640 |600×8×2=9,600 |19,200 |
| Timed-phase searches |28,800 |57,600 |
| Native conformance | — |30 |
| Fresh quality/exact references | — |1,800 |
| **Maximum searches** | — |**59,430** |

A search budget reservation precedes every exact/native attempt. Non-search setup, setting/plan/eligibility/audit SQL, injected errors, source verification, restore, analysis and cleanup are logged separately and charged to the same wall/memory allocation. No auxiliary native profiling pass or unbudgeted warmup is permitted. If implementation cannot meet these bounds, revise the design openly before sealing or stop; do not silently increase allowances.

## Phase4: analysis and gates

Use the existing tie-aware quality definition and pointwise vector-bootstrap method, frozen seeds/resample count and no post-hoc trimming. Cluster all filters, labels, repetitions, rounds and temporal blocks of a vector together. There are200 independent vectors, not28,800 independent samples. Report each filter, overall, each block, arithmetic means and intervals. Exposed/adapted development data provide neither independent confirmation nor a joint95% familywise guarantee.

1. **Integrity/conformance first:** exact cohort/count/order/timestamp identities, settings/module/index and deterministic per-case effort outputs must reproduce. Every timed output must match its freshly measured same-effort reference. Verify protected source before/after, complete raw coverage and no retries. Preserve aborted/censored runs.
2. **Quality remains mandatory:** Phase2's completeness, floors and overall/per-filter reserve must pass. Do not use a timing or later control result to overturn a failed early quality screen.
3. **Fresh warm A/A precision:** for each of two cells and four strata (overall plus three filters), form A/B paired outer-gap and mean log-ratio95% intervals. All **16 intervals** must fit wholly inside **±0.10ms** and **±log(1.02)** respectively. Including zero is insufficient. Old B1b reuse precision does not qualify this new reader lifetime/order design. Failure gives `measurement_inconclusive`; no correction or extra blocks.
4. **Benefit:** match480/640 by query, block, round and retained repetition, average A/B labels symmetrically, then require the upper95% confidence bounds on the mean480−640 outer gap and mean log(480/640) to be<=−0.10ms and<=log(0.98), respectively, **overall and in every filter**. Arithmetic savings must have the correct direction in both temporal blocks, overall/per filter. No separately estimated control subtraction or cross-campaign P2/B1b percentage comparison.
5. **Verdict:** valid quality failure → `closed_negative_quality`; valid adequately controlled benefit failure → `closed_negative_economics`; control failure → `measurement_inconclusive`; all pass → `promising_warm_fixed_configuration`. Native/integrity/censoring failure → invalid/incomplete. Publish exactly what happened, including unused budget.

No B1c, production adoption, protected query access, additional fit, confirmation job or M1/M2/M3 follows automatically. A positive result requires operating-scope/lifecycle and entitlement review before an independent evaluation. A negative/inconclusive result closes this finite probe; consider plan/filter/index alternatives or an explicitly justified new contract. Do not proceed automatically to560,600, another seed, a subset router or another allocation.

## Resource ceiling, execution and return

Propose **one Torch allocation,4 CPUs,32GiB,2 hours; work deadline6,600 seconds; database max_connections16**. There are two temporal blocks, not two submissions. Budget exhaustion or deadline stops and preserves the incomplete return. There are zero provider calls, scientific fits, new development vectors, protected query values and confirmation queries. The separate60-vector confirmation entitlement and37 reserved vectors remain untouched.

Collection must archive raw reference/qualification/slot/execution/conditioning/setup/cleanup logs, runtime/index identities, phase counters, failure and submission/Slurm provenance, locked file hashes and remote analysis. Local data-only verification must check archive checksum/membership, exact package/submission/job identities, raw schedule/coverage and unchanged analysis parity at the original1e−12 floating tolerance. Derive canonical campaign identity from proven submission metadata; do not normalize arbitrary scientific fields to make reports agree.

No package or commands exist for this proposal yet. The next implementation stage must produce them and pass G0-B1b2; the user then runs only the sealed commands. The current review requires no Torch command.

## Tracking and sources

- [x] Design question/value/boundary, identities, resources and stop rules specified before480 outcomes.
- [ ] Isolated implementation and local correctness checks; exact package/order/input hashes and commands sealed.
- [ ] Native conformance and complete quality gate.
- [ ] Conditional warm A/A/benefit measurement, within one allocation and59,430-search ceiling.
- [ ] Verified archive/raw replay, preserved source and scoped result/roadmap update.

Project basis: [B1b result](fannagent-native-effort-frontier-v1-results-2026-10-25.md), [review and static/timer audit](fannagent-effort-interface-review-2026-10-25.md), [B1b frozen contract](../agent/experiments/native-effort-frontier-v1/DESIGN.md), [roadmap](fannagent-performance-research-roadmap-2026-10-22.md). Primary mechanism sources: [pgvector0.8.6](https://github.com/pgvector/pgvector/blob/v0.8.6/README.md), [pinned GUC definitions](https://raw.githubusercontent.com/pgvector/pgvector/8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c/src/hnsw.c), [pinned HNSW scan](https://raw.githubusercontent.com/pgvector/pgvector/8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c/src/hnswscan.c), [PostgreSQL17 SET](https://www.postgresql.org/docs/17/sql-set.html). These justify the mechanism and isolation requirements; none establishes480's quality, speed or future acceptance.
