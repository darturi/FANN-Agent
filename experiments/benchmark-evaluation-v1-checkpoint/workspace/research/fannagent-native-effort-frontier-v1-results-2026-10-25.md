# B1b native-effort frontier: verified results

Reviewed October 25, 2026, America/New_York. Campaign
`reviews-native-effort-v1-20261025T014743Z.p_kspq5v`; user-run Torch jobs
`20845494` and `20845495`.

**No context or regime qualifies for B1c. Retain original execution.** Native
conformance passes and the lower effort substantially improves reuse latency,
but every filter context fails the recall reserve and the forced640 wrapper
fails its overhead limit. Activation A/A precision also fails. The frozen
aggregate verdict remains **`measurement_inconclusive`**; it is not rewritten
as a passing or uniformly well-measured negative experiment.

The [postrun receipt](../agent/docs/verification/native-effort-frontier-v1-postrun.json),
[fresh sealed replay](../trials/torch-reviews-native-effort-frontier-v1/analysis-review/reviews-native-effort-v1-20261025T014743Z.p_kspq5v/performance.json),
[verification/reconciliation](../trials/torch-reviews-native-effort-frontier-v1/analysis-review/reviews-native-effort-v1-20261025T014743Z.p_kspq5v/verification.json)
and [descriptive analysis](../trials/torch-reviews-native-effort-frontier-v1/analysis-review/reviews-native-effort-v1-20261025T014743Z.p_kspq5v/descriptive-analysis.json)
preserve the complete evidence. No new experiment, fitting, DB call, provider
request or Torch submission was needed to recover or analyze this return.

## Download error and narrowly scoped recovery

The download/checksum succeeded. The original ingestion then stopped at
`result/campaign` because the remote reporter used `Path('/results').name`,
while the Mac reporter used the extracted campaign directory's full name.
The sealed collector explicitly mounts the bound campaign at `/results`.
This is a reporting/ingestion bug, not a failed Torch campaign.

Recovery verifies the downloaded archive checksum and all 40 extracted files
against its original archive members, the sealed 146-file package, submission
campaign/path, both dispatch/job completion identities, all 26 locked raw files,
source preservation, native/index/module identities and the full raw protocol.
It then executes the unchanged sealed analyzer into a fresh `analysis-review`
directory. The first partial `analysis-local` attempt remains preserved.

Only the copied remote report's top-level campaign label is reconciled from
`results` to the proven submission identity. All other discrete fields and gate
decisions match exactly. Three floating values differ by at most
`4.336808689942018e-19`, below the original `1e-12` tolerance. Raw reports,
measurements, gates and sealed package are unchanged. The receipt explicitly
records **statistical/gate parity after proven metadata reconciliation**, not
literal parity of the unmodified report documents.

The [data-only recovery helper](../agent/experiments/native-effort-frontier-v1/recover_campaign_identity.py)
has four passing regression checks plus lint/format checks. Arbitrary campaign
aliases, changed package/job identities, altered gates, extra fields and other
result differences still reject. Future reporters should take a verified
campaign identity from their submission record rather than infer it from a
container mount name. No measurement or quality threshold was relaxed.

## Completion and conformance

| Item | Verified result |
| --- | --- |
| Allocations / searches | 2 / 139,272, exactly the allowance |
| Independent exposed vectors / filter cases | 200 / 600; reused development data |
| Retained executions / discarded warmups | 76,800 / 19,200 |
| Native conditioning calls | 38,400, separately recorded |
| Exact/native/effort/source reference searches | 4,800 |
| Native qualification searches | 72 |
| Reader admissions | 28,832 |
| Block work durations | 2,264.237 / 2,080.211 seconds, each below 6,600 |
| Provider calls / fits / confirmation queries | 0 / 0 / 0 |
| Current index / module | Original90f4 graph and e7dc module preserved |

Settings/HNSW plans, alternating320/640 isolation, forced640 versus original640
outputs, source320 versus wrapped320 outputs, exact-transaction independence,
SQL rollback and explicit new-session recovery all pass. All timed results
match their actual effort reference, and both blocks reproduce the same query
outcomes. Every effort320 result is complete/valid top10; completeness alone
does not establish the required recall.

All 324 prior code/source hashes, 29 consulted prior inputs and 128 historical
raw/saved outputs still match the B1a preservation inventory. The frozen
[B1b contract](../agent/experiments/native-effort-frontier-v1/DESIGN.md) and
original execution remain intact.

## Measured latency

These are arithmetic mean **full outer** latencies in B1b's declared warm
shared-index/snapshot scope. Activation includes a fresh reader admission;
wrapped activation charges both readers. Reuse follows one discarded warmup.
The confidence analysis clusters every repetition, label, filter and block by
the same 200 vectors. SQL-only timing is secondary. This changed admission
scope does not support cross-campaign percentage claims against P2a/P2b/P2c.

| Path | Activation ms | Reuse ms | Reuse change versus original640 |
| --- | ---: | ---: | ---: |
| Unwrapped original640 study reference | 83.302736 | 5.519471 | Reference |
| Wrapped forced640 | 138.306258 | 5.725706 | 3.736% slower |
| Wrapped forced320 | 134.792358 | 3.281898 | 40.540% faster |
| Unwrapped inspected-source320 | 78.152103 | 3.098796 | 43.857% faster |

Wrapped320 reuse saves **2.237574 ms**, with 95% interval
**[2.180726, 2.292328] ms**, and saves time in both blocks and every filter.
All three contexts meet the declared reuse net-benefit thresholds. This is a
real latency tradeoff in this development scope, not a qualifying policy gain.

The forced640 overhead control adds **0.206235 ms** during reuse, interval
**[0.190779, 0.221789] ms**. Its mean log-ratio interval
`[0.033684, 0.039005]` exceeds `log(1.02)`. Every context fails the overhead
limit. The gap includes both SQL and work outside its timer; these categories
do not establish a function-level cause without separate attribution.

Wrapped320 activation adds **51.489622 ms**, interval
`[48.071350, 55.218889]`, with a 61.810% arithmetic point slowdown. Forced640
also adds substantial activation cost. These descriptive activation contrasts
cannot qualify a benefit or calibrated comparison because activation A/A
precision fails. Expensive two-reader admission is charged visibly rather than
treated as free; no serving amortization or cold-index claim follows.

## Recall and controls

Recall differences below are **percentage points**, not relative percentages.
Intervals are the original pointwise vector bootstrap intervals.

| Filter | Original640 recall | Effort320 recall | Difference, pp | 95% difference interval, pp |
| --- | ---: | ---: | ---: | --- |
| Overall | 99.0333% | 98.2333% | −0.8000 | [−1.0833, −0.5333] |
| Unfiltered | 99.3500% | 98.9500% | −0.4000 | [−0.7000, −0.1500] |
| votes32 | 99.1500% | 98.6000% | −0.5500 | [−0.9000, −0.2500] |
| votes108 | 98.6000% | 97.1500% | −1.4500 | [−2.0000, −0.9500] |

All three context lower bounds fail the **−0.25 pp development reserve**.
The overall interval is also wholly worse than the **−0.50 pp final margin**,
which remains diagnostic here and is not independent confirmation. The high
absolute recall and complete top10 results do not waive the relative objective.
There are 46 lower-recall cases—8 unfiltered,11 votes32,27 votes108—and no
higher-recall cases among the600. These are cases, not46 independent vectors.

| A/A regime | Interval checks passed | Decision |
| --- | ---: | --- |
| Activation | 2 / 32 | Measurement inconclusive |
| Reuse | 32 / 32 | Scoped precision passes |

Activation equivalence requires whole intervals inside ±0.10ms and
±log(1.02); intervals merely including zero are insufficient. Thirty failed
intervals do not mean thirty proven biases. Reuse precision passes, so its
quality/control failures cannot be dismissed as an activation precision issue.
No A/A correction or native-gap subtraction is used.

## Roadmap decision and next step

B1b's finite campaign is complete and verified. Preserve its exact formal
aggregate `measurement_inconclusive` verdict, record the independently failing
reuse quality/overhead checks, and retain original640 execution. No context or
regime supports B1c under this contract.

A three-context map that selects320 for a whole context inherits that context's
failing quality bound; choosing640 everywhere introduces no effort reduction.
This dependency argument does not fit, select or simulate a router. There is no
justification to spend B1c's effort on the present two-level context family.

Do not rerun activation calibration for this unchanged design: better precision
would not repair its deterministic recall outcomes or its passing-precision
reuse overhead failure. The allowance is consumed. Further efforts, blocks,
quality margins, features or confirmation access require a new contract.

Next proposed work is a **read-only effort/interface revision review**: assess
whether an intermediate-effort question and a simpler admission/validation
design justify a separately bounded comparison. Intermediate recall/latency
cannot be interpolated from320/640, and a new interface needs fresh conformance
and actual costs. There is no prescribed new effort value or authorized new
measurement in this result. Broader filtering/plan/index alternatives stay
conditional; this result does not establish a universal native-effort ceiling.

No user commands are needed now. The download was sufficient; verification and
analysis have been recovered locally. M1/M2/M3 and canonical acceptance remain
unestablished. See [roadmap v1.15](fannagent-performance-research-roadmap-2026-10-22.md).
