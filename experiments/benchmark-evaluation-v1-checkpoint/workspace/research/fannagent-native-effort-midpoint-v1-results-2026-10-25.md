# B1b2: verified fixed 480 versus 640 results

Date: October 25, 2026, America/New_York.  
Experiment: `NEXT-EFFORT-MID-01`; campaign `reviews-native-midpoint-v1-20261025T172357Z.ybpfkkki`; Torch job `20898557`, task 0.  
Verdict: **complete, `closed_negative_quality`; retain original execution.** B1c stays deferred. This closes the one frozen midpoint probe, not every possible effort/plan/index design.

## Decision and scope

The fixed 480 candidate passed native conformance and all absolute mean-recall floors, but failed the **−0.25 percentage-point development recall reserve** overall and for both filtered groups. The quality-first stop worked: exactly 1,830 searches ran; no temporal timing blocks, A/A controls or benefit estimates were acquired. The job's successful exit means a valid completed negative experiment, not a qualifying candidate. No speed improvement, activation qualification, agent-method improvement or M1/M2/M3 acceptance is established.

This review reads the completed return and runs unchanged sealed saved-data analysis only. It changes no source, policy, frozen contract, threshold or previous verdict and launches no experiment, database/native call, Torch job, fit, provider request or protected-query access.

## Verification

The [post-run receipt](../agent/docs/verification/native-effort-midpoint-v1-postrun.json) and [verification](../trials/torch-reviews-native-effort-midpoint-v1/analysis-review/reviews-native-midpoint-v1-20261025T172357Z.ybpfkkki/verification.json) record:

- Download SHA256 **`f32a9f23b543999150a82651ee0cf5320cba30ae8c460f47fcd89edc72f27c04`**, 329,356 bytes; checksum filename matches. All 24 unique safe regular archive members match the exact extracted member set and bytes.
- Sealed package: 150 manifest files and 151 archive members verified. Manifest `b7ad5be746bfa26bcaf5fbd381b0523c518f3872bb8011d8d00331b399c34bc1`; package archive `fbd7ac0654bb9ff99f6add7011127caf01c008cd08fb142abe56783ea94e6185`. All 12 implementation source hashes still match the preparation receipt.
- Fresh unchanged sealed analysis validates all 15 locked raw files, case/order/settings/qualification/count identities and reconstructs quality from saved results. Performance JSON and report are **byte-identical** to both the remote reports and the download helper's local reports; no parity repair or tolerance change was needed. The existing strict float tolerance remains 1e−12.
- Independent arithmetic recomputes 1,200 current recalls from returned IDs and strict/tied exact truth, plus 600 prior 320 outcomes. All 600 current exact truths/native 640 outputs match B1b; query inventory bytes, dataset/physical index and runtime image/module/profile/registry match. Comparison with 320 below is descriptive quality only.
- All 888 inventoried immutable source/evidence/input files remain unchanged, including 691 prior preparation-preservation files. The one documented earlier transport-helper update is accounted for explicitly: the outer unsealed `transfer.sh` changed from `9df5c8c8…c874c0d` to `8f8e3dd5…c475b83` during upload recovery; its original bytes and separate recovery receipt remain preserved. It changed no sealed package or scientific code. No new helper change occurred in this review.

Current index identity is `90f4a709ab3ee7ce40fe7630009b29d5646f6e1e80ceab8c2246cb970d803484`; physical file `base/16384/264013`, 1,012,678,656 bytes, SHA `dbc14b0912d7e9ad9cd4ddcf806cac081412e66b1861de7ce3629fd81e23b393`. Native module SHA `e7dcace1f4dfd4ea233256d6cdfc17b3190f3f07cccb6406b479b5ebe8b85811`; runtime profile `b2974c2c65d40780d207109d9bbd298b2628ea58abde673c0dd479c1a0e52ed3`. Index/module checks after execution and protected-source preservation pass. Reader cleanup and database shutdown complete.

## Which recall gates failed, and by how much

The frozen criterion is **lower 95% bound of mean(recall480−recall640) ≥−0.25 pp**, overall **and** in every filter. Intervals use the frozen 10,000-resample seed 20261019 bootstrap, grouped by 200 vectors; each vector's three filters stay together for the overall interval. There are 600 cases, not 600 independent vectors. These are pointwise development intervals on already exposed data, not simultaneous bounds or independent confirmation.

| Stratum | 640 mean recall | 480 mean recall | Observed 480−640 |95% interval, pp | Development reserve | Lower-bound shortfall, pp |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| Overall |99.0333% |98.8500% |−0.1833 pp |[−0.3333,−0.0667] | **Fail** | **0.0833** |
| Unfiltered |99.3500% |99.3000% |−0.0500 pp |[−0.1500,0.0000] | Pass |0;0.1000 pp headroom |
| `votes32` (`m_000000≥32`) |99.1500% |99.0000% |−0.1500 pp |[−0.3500,0.0000] | **Fail** | **0.1000** |
| `votes108` (`m_000000≥108`) |98.6000% |98.2500% |−0.3500 pp |[−0.6500,−0.1000] | **Fail** | **0.4000** |

Shortfall is `max(0,−0.25−lower_bound_pp)`; it is distinct from the observed mean loss. Overall and votes32 point losses are smaller than 0.25 pp, but their lower confidence bounds do not exclude losses beyond the reserve. Failing noninferiority does not prove the population loss exceeds the margin. Votes32's interval includes zero; votes108 shows the largest observed loss, and its interval lies below zero.

**All eight absolute native-floor checks pass**: both efforts exceed 95% mean recall overall and per filter. The weakest 480 stratum is votes108 at 98.25%, 3.25 pp above the absolute floor. All 1,200 native outputs are valid complete sets of 10 results with no duplicates or predicate violations. These absolute/completeness checks do not replace relative quality protection.

The looser **−0.50 pp final-margin diagnostic** passes overall, unfiltered and votes32, but **fails votes108 by 0.15 pp**: its lower bound is −0.65 pp. This margin was diagnostic only; it cannot substitute for the development reserve or independent confirmation. The unfiltered pass cannot rescue the global fixed 480 contract or authorize a post-hoc 480/640 router.

## Case-level diagnosis and prior 320 comparison

[Saved descriptive arithmetic](../trials/torch-reviews-native-effort-midpoint-v1/analysis-review/reviews-native-midpoint-v1-20261025T172357Z.ybpfkkki/descriptive.json) preserves exact counts without new bootstrapping or selection.

| Stratum | Truth hits 640 / 480 | Cases lower / equal / higher at 480 | Net missing true neighbors versus 640 | Prior 320 mean recall | 480 gain over prior 320 |
| --- | --- | --- | ---: | ---: | ---: |
| Overall |5,942 /5,931 of 6,000 |11 /589 /0 |11 |98.2333% |+0.6167 pp |
| Unfiltered |1,987 /1,986 of 2,000 |1 /199 /0 |1 |98.9500% |+0.3500 pp |
| votes32 |1,983 /1,980 of 2,000 |3 /197 /0 |3 |98.6000% |+0.4000 pp |
| votes108 |1,972 /1,965 of 2,000 |7 /193 /0 |7 |97.1500% |+1.1000 pp |

The 11 losses are one neighbor each across 11 cases belonging to **nine vectors**. Ordered IDs and ID sets differ in exactly those 11 cases; 589 cases match 640. Seven of 11 extra misses occur in votes108. Relative to prior 320, 480 recovers **37 true neighbors in 36 improved cases**, with no lower-recall case observed on this cohort. This establishes an observed quality improvement over 320 under matched identities, while the 480 versus 640 gate still fails. It predicts neither 560/600 quality nor an unmeasured speed/recall curve; the old multi-effort sweep remains a different-index study.

## Charges, controls and performance interpretation

| Item | Actual verified consumption |
| --- | --- |
| Allocations |1; job 20898557/task 0 |
| Native qualification |30 searches: 6 exact, 12 at 640, 12 at 480 |
| Quality references |1,800 searches: 600 exact, 600 at 640, 600 at 480 |
| Total backend searches | **1,830**; 57,600 conditional timing searches never authorized by the quality gate |
| Readers |10 admissions; all closed |
| Temporal timing blocks / retained executions / warmups / conditioning |0 /0 /0 /0 |
| A/A intervals | **0 of 16 acquired; not assessed**, not a control failure |
| Benefit comparison | Not assessed; `comparison=null`, no qualified latency estimate |
| Work clock |859.376026 seconds; separate from the user-reported Slurm allocation elapsed 16m13s |
| Restore/import and cleanup |160.431023 s and 1.187523 s; recorded phase charges, not candidate savings |
| Provider calls / fits / control installations / confirmation queries |0 /0 /0 /0 |
| New vectors / protected-query values |0 /0 |

The fresh replay checks exact search/operation and non-search accounting, including 170 explicit reader-startup SQL calls and 12,120 inherited exact non-search calls. Phase categories overlap and must not be summed into a new wall-time estimate. Quality-reference/qualification timers and work elapsed are acquisition diagnostics: they lack the balanced repeated workload and fresh A/A needed for a warm benefit claim. B1b's earlier 40.540% reuse saving at 320 does not transfer to 480. B1b activation A/A failures are unchanged, and 480's simpler admission economics remain unmeasured.

## Next step and decision gates

Close B1b2 as a valid finite negative quality result; keep the original 640 study execution. B1b's aggregate remains `measurement_inconclusive`, B1c stays deferred, and the finite P2/P3 closures remain intact. No automatic retry, additional temporal block, threshold relaxation, 560/600 ladder, subset rescue, fit or protected entitlement follows. This is no universal ceiling on native-effort optimization.

Recommend **B2a / `NEXT-PLAN-SCOPE-01`: a read-only query-plan/filter/index feasibility audit**, before another experiment. This is a proposed next phase, not a completed audit or performance prediction.

1. **Establish actual mechanics and inputs.** Inspect existing SQL/native source, saved plans/settings and scalar/ANN-index metadata; separate filter placement, exact-reference execution and supported controls. Record unknowns when local saved metadata is insufficient; run no database query. Identify legal pre-query inputs and their costs; query IDs, evaluator strata and offline eligible-row counts are not free routing features.
2. **Compare distinct intervention classes.** Build a feasibility matrix for predicate-first exact versus ANN plan selection, scalar/partial/partitioned index alternatives and predicate-aware traversal. Separate changes compatible with the current physical graph/module from those requiring new indexes, binaries, datasets or acceptance scopes. Preserve cosine/top10/filter/tie semantics and full lifecycle accounting.
3. **Apply a source/evidence gate (`GB2a`).** Require an actual supported mechanism, explicit changed identities, plausible workload relevance, qualified decision inputs and costs, exact parity/quality controls, finite prospective resources and no hidden evaluator data. Recommend one newly frozen comparison only if justified; otherwise document no-go or the specific missing metadata. This review assigns no measurement budget or source-change permission.
4. **Only after a new design:** isolated implementation/local checks → native qualification → complete quality/control/benefit comparison → independent saved-data verification. Router fitting, operating-scope adoption and confirmation remain separate later gates.

Why this branch: the frozen 480 probe is exhausted, with failures concentrated in filtering; that motivates investigating different mechanisms, not proving filtering caused the misses. Official [pgvector 0.8.6 filtering guidance](https://github.com/pgvector/pgvector/blob/v0.8.6/README.md#filtering) lists exact filter indexes, partial indexes and partitioning as workload-dependent alternatives. Its [iterative-scan guidance](https://github.com/pgvector/pgvector/blob/v0.8.6/README.md#iterative-index-scans) addresses too few filtered results; all current outputs already contain 10, so it is not an established recall repair here. Eligibility is broad: 123,692 of 247,286 rows for votes32 and 49,498 for votes108 (about 50% and 20%); exact-plan savings cannot be assumed. [ACORN v1](https://arxiv.org/abs/2403.04871v1) provides a distinct predicate-subgraph traversal/index design to assess for compatibility, with no transferable local performance guarantee.

**Revised critical path:** verified B1b2 negative closure → proposed B2a source/identity/input audit → GB2a go/no-go → only if justified, a new finite prospective contract → implementation/qualification/measurement/replay → scoped family decision before routing or adoption. **No user or Torch commands are needed now.** The [roadmap](fannagent-performance-research-roadmap-2026-10-22.md) tracks this branch and preserves the previous gates.

## Evidence and reproduction

- [Frozen premeasurement design](fannagent-native-effort-midpoint-v1-design-2026-10-25.md) and [implementation receipt](../agent/docs/verification/native-effort-midpoint-v1-implementation.json) remain unchanged historical records.
- [Returned campaign](../trials/torch-reviews-native-effort-midpoint-v1/returned/reviews-native-midpoint-v1-20261025T172357Z.ybpfkkki/), including raw `run/references.jsonl`, quality, qualification, lock, charges and status.
- [Fresh sealed performance](../trials/torch-reviews-native-effort-midpoint-v1/analysis-review/reviews-native-midpoint-v1-20261025T172357Z.ybpfkkki/replay/performance.json), [report](../trials/torch-reviews-native-effort-midpoint-v1/analysis-review/reviews-native-midpoint-v1-20261025T172357Z.ybpfkkki/replay/report.txt) and [parity receipt](../trials/torch-reviews-native-effort-midpoint-v1/analysis-review/reviews-native-midpoint-v1-20261025T172357Z.ybpfkkki/replay/verification.json).
- [Input inventory](../trials/torch-reviews-native-effort-midpoint-v1/analysis-review/reviews-native-midpoint-v1-20261025T172357Z.ybpfkkki/input-inventory.json), [archive/preservation proof](../trials/torch-reviews-native-effort-midpoint-v1/analysis-review/reviews-native-midpoint-v1-20261025T172357Z.ybpfkkki/archive-preservation.json), [descriptive arithmetic](../trials/torch-reviews-native-effort-midpoint-v1/analysis-review/reviews-native-midpoint-v1-20261025T172357Z.ybpfkkki/descriptive.json) and [documentation checks](../trials/torch-reviews-native-effort-midpoint-v1/analysis-review/reviews-native-midpoint-v1-20261025T172357Z.ybpfkkki/documentation-checks.json).

To reproduce only the saved-data analysis, invoke the **unchanged local sealed** `experiment.py analyze --campaign <returned campaign> --output <new review directory>` with `PYTHONDONTWRITEBYTECODE=1` and the existing agent virtualenv. Read no downloaded executable and do not rerun `submit`. Exact paths and the command actually used are recorded in the post-run receipt.
