# Admission profile identity v1: frozen P2b contract

Prepared October 23, 2026, after the verified [P2a result](../../../research/fannagent-prepared-policy-lifecycle-v1-results-2026-10-23.md). Experiment ID: **NEXT-ADMIT-01**. One implementation and one four-block Torch campaign. No provider calls, policy fitting/selection, confirmation queries, native module change or deployment.

## Hypothesis and one mechanism

P2a reduced repeated-query preparation but left session admission at 1.539285 ms and four semantic runtime-profile fingerprint calculations per constructor. P2b tests whether one privately owned, immutable admission-profile identity can reduce this cost without weakening validation or creating a query-path regression.

Each P2b session, under the existing backend operation lock, deep-copies the frozen runtime profile and computes its original semantic fingerprint **once**. It retains only that string, a read-only mapping of privately copied frozen feature definitions, and a frozen set of collection groups. No mutable profile is memoized; no identity is shared across sessions. The copy, hash, binding checks and full policy admission remain inside `preparation_ms` and are charged to activation and outer application time. This experiment does not amortize cold setup or assume a persistent-service objective.

The complete frozen composite validator is copied as `pb_policy.validate`, changing only its explicit profile parameter in place of the global import; an AST comparison enforces this. The original `validate_policy` still performs original node/type/numeric/size/group/runtime-profile checks. Feature qualification, maximum depth, canonical guard, copying, eligible-mask canonicalization and semantic policy identity remain unchanged. Repeated reads of `profile.fingerprint` now read one immutable string. The new admission rejects an unexpected backend profile binding or a cache identity that differs from the captured semantics.

P2b inherits P2a's query method and uses its lazy private prepared-policy handle without modification. The original query normalization, route, backend timing boundary, compilation/install acknowledgement and error closure remain unchanged. Both the P2a session and backend-body reference files are byte-identical to the sealed P2a package. The frozen original execution remains a separate reference.

Caller mutation cannot change the captured identity, feature definitions, or owned policy. Connection/cache/profile binding replacement, cross-backend use, server eviction and failed execution retain P2a's lifetime rules. Direct mutation of backend-private cache/profile internals is not a supported profile update; replace the binding and create a fresh session. No global monkey patch, shared cached property or modification to the installed core/adapter is used.

## Frozen inputs and twelve arms

Retain the original 200 exposed development vectors, all 600 cases, all three filters, `ef_search=640`, `k=10`, the physical 247,286-row index and the same x86 native module/image. Candidate semantic hash remains `a014a290966444a86614f1e5be1960dad2fb8684044e85e9df82899911062b0d` with its earlier seed credit. There are three unchanged semantic arms:

1. Candidate `cons-bypass108`, light19, native bypass on `votes108`.
2. Its matched all-continue tree with identical profile/mask/conditions.
3. Host routed-native control with an empty eligibility mask.

For each semantic arm run four execution labels:

| Label | Execution |
| --- | --- |
| `original` | Exact frozen original Session/backend |
| `owned` | Exact frozen P2a session and backend body |
| `admission-a` | New P2b admission, unchanged inherited P2a query path |
| `admission-b` | Same P2b factory/class, separately constructed state; A/A replicate |

Both A/A labels use identical code, policies, cold charges and native pairing. Each starts a fresh session after explicit server installation eviction and cache clearing. No prepared artifact is transferred between labels. Every label has its own ordinary-native measurement pair. Zero provider calls and zero protected confirmation vectors are available to this campaign.

## Schedule, precision and analysis unit

The [existing-data precision review](PRECISION.md) uses only the completed P2a data. It finds wide activation/filter bounds and control variation; it does not establish a causal ordering effect or guarantee the next campaign's precision.

Within each query and semantic arm, use four Williams rows: `[0,1,3,2]` plus block number modulo four, after a fixed query/semantic hash permutation of variant labels. Across four blocks each label occupies each position once, and every directed predecessor pair occurs once. Semantic-arm order is hash-selected and rotated modulo three; four blocks do not perfectly balance semantic positions, and raw positions remain reported. All twelve arms for a query are contiguous. Query order uses seed `20261022 + block`.

Native/policy order inside each pair is hash-selected from query, semantic arm, block and repetition, and is identical across the four variants. Each arm has one activation pair, one discarded warmup pair and three retained reuse pairs. There are no adaptive repetitions. The raw rows record the full schedule and position; the trusted verifier checks both metadata and physical query/arm/repetition order.

After the entire primary pass, profile the same previously fixed 30-vector subset, all three filters, all twelve arms and four phases (constructor, activation, discarded warmup, reuse). Profiling never enters latency estimates. Each block has 144 profile groups; the campaign has 576. P2b constructors must call original `RuntimeProfile.fingerprint` once and snapshot `capture` once; original/P2a constructors must still call fingerprint four times. Original eligible queries prepare once each; P2a/P2b prepare only on first activation, never on reuse or bypass.

Use the original 10,000-resample vector-cluster bootstrap, seed 20261019. All filters, blocks, repetitions and A/A labels from a vector stay in the same cluster. There are **200 independent vectors**, not 400 A/A vectors or 800 block-vectors. Do not use independent-row intervals. The intervals are pointwise; all declared endpoint requirements must pass (an intersection decision), with no favorable subset selection. They do not provide an omnibus simultaneous confidence region or a cross-workload generalization claim.

## Direct comparisons and prospective gates

Report all four contrast families, every semantic arm, both regimes, overall and per filter, pooled and by block:

- `p2a_vs_original`: P2a policy time minus original policy time; historical mechanism replication, no reopening of P2a's failed gate.
- `p2b_vs_p2a`: mean of the two fresh P2b labels minus the same-query P2a time; incremental admission effect.
- `p2b_vs_original`: mean P2b minus original; combined execution effect.
- `aa_b_vs_a`: P2b B minus P2b A; identical-path measurement diagnostic.

The bootstrap groups both P2b labels by vector; pooling them does not create independent samples. Individual label-versus-native reports and schedule fields remain visible. Direct contrasts compare policy execution times, never a subtraction of independently summarized native gaps. A/A is never subtracted from treatment gaps, never used to relax margins, and never used to filter blocks.

All of the following are mandatory:

1. **Identity/correctness/mechanism:** all inputs and runtime/index identities, getter/reference/output/actual-stop/prefix/acknowledgement checks pass. Old/new IDs, distances, recall and stopping outputs match exactly, including diagnostics. All call-count requirements above pass. Missing/corrupt evidence fails verification.
2. **A/A equivalence:** for every semantic arm, regime, filter and overall, the complete two-sided 95% primary and outer gap intervals are contained in `[-0.10,+0.10]` ms. The complete mean log-ratio interval is contained in `[-log(1.02),+log(1.02)]`. Including zero is insufficient. Block-level A/A intervals are reported for diagnosis; equivalence is required on the pooled vector-cluster estimates.
3. **Incremental activation benefit:** candidate `p2b_vs_p2a` activation has primary and outer gap upper endpoints <= `-0.10` ms, mean log-ratio upper endpoint <= `log(0.98)`, and a negative primary point gap in every block.
4. **Retained combined reuse benefit:** candidate `p2b_vs_original` reuse meets the same `0.10` ms/2% primary and `0.10` ms outer requirements and saves time in every block.
5. **No material regression:** for `p2b_vs_p2a` and `p2b_vs_original`, every semantic arm, both regimes, every filter and overall must have primary gap upper endpoint <= `+0.10` ms, log-ratio upper endpoint <= `log(1.02)`, and outer gap upper endpoint <= `+0.10` ms.
6. **Original quality criteria:** every ordinary-native report remains valid, native recall >= 0.95 per filter and the development-relative recall lower bound >= -0.0025. The original default-relative margin 0.005 and activation/reuse latency criteria remain separately reported; an engineering pass does not establish activation superiority over native.

Verdicts: `measurement_inconclusive` if A/A equivalence is not established (retain all engineering failures too); otherwise `revise_or_retain_original` if any engineering/quality criterion fails; otherwise `pass`. A failed/inconclusive result consumes this allowance. No repeat-until-pass, added blocks, threshold adjustment, policy change or second implementation is authorized by the contract. G2/M1 still require measured residual-cost/operating-scope review; M2, M3 and canonical acceptance remain unestablished.

## Resource ceiling and finite stopping rule

| Item | Per block | Whole campaign |
| --- | ---: | ---: |
| Serial allocations | 1 | Exactly 4 maximum |
| CPUs / memory / wall limit | 4 / 32 GiB / 2 hours | <= 8 allocated wall-hours; 32 allocated CPU-hours |
| Runtime work deadline | 6,600 seconds | One deadline per block |
| Getter searches | 921 | 3,684 |
| Primary searches including getters | 81,921 | 327,684 |
| Diagnostic searches | 10,800 | 43,200 |
| Total backend/reference searches | 92,721 | **370,884** |
| Primary retained / discarded warmup pairs | 28,800 / 7,200 | 115,200 / 28,800 |
| Diagnostic retained / discarded warmup pairs | 4,320 / 1,080 | 17,280 / 4,320 |
| Separately counted eviction installations | 8,280 | 33,120 |
| Provider calls / confirmation queries | 0 / 0 | 0 / 0 |

Primary accounting: `921 + 600 × (3 references + 12 proofs + 12 × 5 pairs × 2 executions)`. Diagnostics: `90 × 12 × 5 × 2`. Evictions: `(600+90) × 12`. Other SQL statements are not all counted. Four blocks were chosen for complete variant-order balance, not from an estimated power guarantee. P2a internal time suggests roughly twice its per-block work, but this is not a runtime commitment. If the fixed deadline or resource limit is reached, preserve the failure; do not enlarge the allowance after seeing results.

Submission uses four serial `afterok` jobs, a durable package binding, and a globally unique protocol reservation. An unknown dispatch remains unknown and is not retried. Every allocation restores/stops a private database; original pilot/P1/P2a raw data and inputs are protected. Local tests simulate these interfaces; native qualification and all performance claims await the declared Torch campaign. Data-only ingestion rejects links/path traversal/nonregular files, over 10,000 members, over 256 MiB per file, or over 2 GiB total; the larger finite return ceiling covers the additional blocks/arms.

## Source identities

| Source | SHA-256 |
| --- | --- |
| Frozen selective pilot manifest | `082b167507e25009bdb25ea613950cd434ef38608fbcbc6194af19c363d0f6dc` |
| P1 manifest | `4c2f475664784b1851b1274a5c696bccbc55ee41c659a469c3643eb0ca0109c0` |
| P1 postrun receipt | `16647a2486df6f191a764f4600e17ee2437f01352edc76eb3646490ca3b90378` |
| P2a manifest | `c4c00e12a08963751ab20aed3f195ed3af2a515be40c0bdd619ce57209bca60c` |
| P2a postrun receipt | `5b2449a02ec55ad4c4670e210dbff9ab51ec9b50a9b7c2312306c206826bfdb5` |

The new package manifest pins every new source, contract, precision review and original frozen input. The implementation receipt records its archive and local checks. Original receipts and sealed packages are preserved.
