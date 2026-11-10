# Existing-data precision review and prospective design choice

October 23, 2026. Data only: completed P2a campaign `reviews-prepared-policy-v1-20261023T161756Z.8uq_covr`, verified receipt SHA-256 `5b2449a02ec55ad4c4670e210dbff9ab51ec9b50a9b7c2312306c206826bfdb5`, local `performance.json` SHA-256 `bc622a944ab024b66c8361669bef3bba68dbe6510f99195759628ecc5e8e6236`. No new measurements or confirmation access.

These are the direct P2a-minus-original policy contrasts already reconstructed under the original vector bootstrap. Times are milliseconds; interval width is upper minus lower, not a half-width.

| Arm/regime | Pooled primary gap 95% interval | Largest per-filter primary interval width | Primary point gaps by block 0, 1, 2 |
| --- | --- | ---: | --- |
| Candidate activation | [-0.061361, +0.081151] | 0.284361 | +0.037961, -0.048291, +0.039251 |
| Candidate reuse | [-0.330433, -0.242073] | 0.180911 | -0.275712, -0.296204, -0.286350 |
| Matched continue activation | [-0.047469, +0.104582] | 0.287933 | +0.007600, -0.010061, +0.090420 |
| Matched continue reuse | [-0.346535, -0.229474] | 0.247729 | -0.281431, -0.311258, -0.269275 |
| Routed-native activation | [-0.011311, +0.130068] | 0.274696 | -0.090020, +0.147906, +0.119583 |
| Routed-native reuse | [-0.008029, +0.049266] | 0.101603 | +0.006994, +0.030683, +0.024596 |

The previous three blocks alternated original/P2a order, so each query/semantic arm could not have equal counts in each variant position. Several activation intervals are wider than the full 0.20 ms equivalence band; routed-native activation changes direction across blocks. These facts justify explicit order balance and identical-path controls. They do not prove ordering caused a slowdown, identify server/transport noise, or make the prior failed engineering gate pass.

P2b therefore uses four Williams-balanced variant positions, the same native/policy order within each four-variant comparison, two independently constructed labels of the identical P2b path, and raw schedule/order validation. Every one of the original 200 vectors and all filters is retained. Two A/A labels are also pooled as repeated observations of the P2b treatment within each vector, not as new independent samples. Original and frozen P2a remain concurrent references. The expected admission mechanism is separately verified by constructor call counts.

This is a finite diagnostic/engineering comparison, **not a demonstrated power calculation**. A fourth block and an extra label do not guarantee a particular interval width; query-specific differences, drift and database/cache state can remain. No square-root sample extrapolation treats repeated blocks as independent vectors. The unchanged +0.10 ms / 2% regression limits remain binding. A/A equivalence must be established for every pooled arm/regime/filter; otherwise the result is explicitly `measurement_inconclusive` and no adoption follows. Block/stratum/order results remain visible even when inconvenient. A/A is never used as a numerical correction.

The fixed allowance is four serial 4-CPU/32-GiB/two-hour allocations, 370,884 searches and 33,120 separately counted eviction installations. It is consumed on failure or ambiguity, with no optional extension based on observed precision. New independent data, a normalization rewrite, a transport change, or another follow-up requires a new versioned design and finite allowance. See [the complete contract](DESIGN.md).
