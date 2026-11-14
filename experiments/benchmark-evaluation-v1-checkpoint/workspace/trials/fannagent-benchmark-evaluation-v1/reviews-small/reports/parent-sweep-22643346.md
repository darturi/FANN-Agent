# Verified stronger-parent sweep and next-step recommendation

Date: November 11, 2026. Job 22643346 is a verified bounded negative: no adequate parent on the predeclared grid. Exit 3 is the planned scientific-disposition exit, not a successful stronger-parent qualification and not evidence of a crash. User-provided scheduler output reports 25m24s, exit 3:0, step MaxRSS 6,592,312K, node cs685. The archive checksum and safe extraction checks passed.

## Verification

`runtime-parent-v1/verify_negative_return.py` reconstructs every one of 15,750 ANN observations:450 development groups x 7 conditions x 5 effort settings. All 35 summary cells, recall scores, completion flags, eligible/unique/finite results, native640 continuity on 3,150 requests, and the no-parent selection decision passed. Eligible sets match job 22635567. The kit itself and its prior exact-reference file match their sealed hashes. The negative branch produced four raw files and no success receipt; it never entered the selected-parent stop/continue requalification. Data/import and final index/cleanup checks are supported by the pinned guest's negative branch and its expected exit 3, not by a separate returned success receipt.

Five tiny distance-order inversions occur for the same votes32 query across the five effort settings. Their maximum size is 1.8469e-8, within the protocol's pre-existing 1e-6 numerical tolerance. They are retained in the verifier report. The verifier's extra ordering diagnostic initially used 1e-12; that diagnostic was corrected to the existing protocol tolerance, without changing any recall/completeness criterion or the negative disposition.

| Effort | votes743 recall | Complete votes743 requests /450 | All seven conditions adequate? |
| ---: | ---: | ---: | --- |
|640 |53.4889% |105 |No |
|1,000 |69.2444% |196 |No |
|2,048 |89.4222% |355 |No |
|4,096 |98.1556% |433 |No |
|8,192 |99.7778% |449 |No |

At 8,192 all other conditions have 450/450 complete outputs and mean recall above 95%. votes743 is the only remaining obstacle to the common-parent completeness requirement. Keep the bounded negative; do not silently extend the effort grid, drop this query/filter, or loosen completeness.

## The incomplete query

Identity: `reviews-clean-v0196-votes743`; published source query ID `r216749`; frozen development group source index 196. This predicate has 2,475 eligible corpus rows, so the short result is not caused by having fewer than k eligible records.

| Effort | Returned | Query recall | Observed request time, ms |
| ---: | ---: | ---: | ---: |
|640 |0 |0% |23.19 |
|1,000 |0 |0% |31.22 |
|2,048 |2 |20% |58.36 |
|4,096 |5 |50% |101.39 |
|8,192 |8 |80% |183.97 |

These are individual development measurements on one allocation, not a comparative latency claim. At 8,192 every returned ID belongs to the exact filtered top 10. It misses exact ranks 7 and 9:

- ID 7338, distance 0.5141754448413849.
- ID 33679, distance 0.5161810517311096.

The returned set includes the exact tenth neighbor at distance 0.5171828578223493. Thus this is an incomplete approximate candidate result, not merely omission of a tail tied at the boundary. The stored native640 checkpoint qualifying counts are 0/1/0 at 16/32/64. There is **no 8192 checkpoint trace** in this return: the run stopped after the sweep's negative selection. We cannot infer global neighbor ranks, local selectivity over all 8192 candidates, or precisely which internal graph/heap step omitted those two IDs from these records alone.

## Recommended next step: a common completion guard

Retain all six filters, the same corpus/graph, source IDs, metric, k, and grouped split. Add one explicit deterministic serving rule to both the native parent and every agent arm: if the completed ANN request returns fewer than 10 results, execute exact filtered top 10 on the same immutable dataset/snapshot and replace the partial result. Do not special-case this query or predicate. When fewer than k rows exist, use the protocol's min(k,eligible_count) rule. Keep other integrity failures as failures rather than concealing them behind fallback.

This is a **hybrid parent**, not unmodified native execution and not an agent-generated improvement. Preserve both failed native-only studies. Charge the ANN attempt, short-result check, exact fallback, decoding, and policy work inside complete-request time for both sides. Record fallback frequency, exact cost and resulting output identity. A full result count does not guarantee recall; retain the same independent recall gates and held-out test.

A retrospective development replay using already verified exact references shows why this is a viable next experiment:

| Effort | Requests needing exact fallback /3150 | Fraction | Lowest guarded mean recall across conditions |
| ---: | ---: | ---: | ---: |
|640 |541 |17.17% |96.56% |
|1,000 |354 |11.24% |97.69% |
|2,048 |112 |3.56% |98.49% |
|4,096 |17 |0.54% |99.40% |
|8,192 |1 |0.03% |99.82% |

All five would meet development recall and completeness **in this replay**. This is not a live qualification or measured hybrid latency result. We have not added cross-node exact timings to native timings to fabricate an end-to-end estimate. In particular, do not assume 8,192 is cheapest just because its fallback count is smallest: it pays the largest ANN budget on every query.

Prospectively qualify the guard and measure the complete hybrid request on the same fixed five effort settings, with all 450 development groups/all 7 conditions, and a fixed balanced schedule. Choose one common adequate parent using development serving cost and a frozen tie rule; then pin the parent/module, shared guard and baseline grid before the new agent episode. Requalify stop/continue and exact-fallback output/snapshot behavior. Leave validation/test unopened. This report recommends that experiment; it does not launch it or amend the sealed protocol by itself.

## Why this before another larger ceiling or an iterative rewrite?

An additional ceiling could fix this one development case without providing a completion rule for future hard queries. Preserve the predeclared stopping point instead of extending until the development set passes.

Native iterative scanning is a sound baseline to examine: pgvector documents that post-index filtering can produce short results, and iterative scans continue until enough rows are found or resource limits are reached. [Official pgvector documentation](https://github.com/pgvector/pgvector#iterative-index-scans). However, the retained live stopping path explicitly rejects discarded-candidate continuation (`discarded != NULL` or resumed initialization). Enabling `strict_order` alone is not a qualified integration with that path. Supporting it requires checkpoint/reset, retained-heap, resume and policy-decline parity work; resource exhaustion still needs a defined incomplete-result disposition. It is a larger method/runtime revision than a shared completion guard.

Partial per-filter indexes or dropping the difficult filter would change the established graph/scope. Neither is necessary for the recommended next experiment. Preserve the unmodified-native/iterative baseline distinction in any eventual paper.

## Artifacts

- `../returns/job-22643346/results/negative-verification.json`: full sweep reconstruction and diagnostic limits.
- `../returns/job-22643346/results/incomplete-query-inspection.json`: exact/missing IDs and all five observations.
- `../returns/job-22643346/results/guarded-parent-offline-replay.json`: labeled retrospective guard replay.
- `../runtime-parent-v1/verify_negative_return.py`: reproducible verifier.

No provider calls, new ANN/exact searches, remote jobs, validation outcomes or test outcomes were used in this inspection. The next step is a prospective common-guard experiment, not an agent rerun against an ineligible parent.
