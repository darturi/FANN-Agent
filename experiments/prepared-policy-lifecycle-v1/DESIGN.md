# Prepared-policy lifecycle v1: frozen P2a contract

Prepared October 23, 2026, after verified [P1 attribution](../../docs/verification/execution-cost-attribution-v1-postrun.json). Experiment ID: NEXT-EXEC-01. This is a separately versioned execution comparison, with no policy fitting, provider calls, confirmation queries, or deployment.

## One conceptual change

The original session passes its privately owned raw tree to the backend on every query. The prepared cache validates, copies and serializes that input before checking for a hit. P2a retains one private prepared-policy handle for the life of an owned session.

Full original composite admission remains in session construction and is charged to activation. The handle is resolved lazily at the original preparation line inside the backend timer: first eligible execution performs original backend preparation; subsequent executions reuse the resulting private prepared object. Native bypass never resolves the handle. Bytecode remains lazy, and installation/acknowledgement remain inside the original backend timer.

`pp_backend._execute_owned` copies the pinned backend execution body, changing only the function name and the policy-preparation expression. A local AST comparison enforces that boundary. The original path calls the original frozen Session/backend; the new wrapper preserves the original operation lock and close-on-error behavior. No database SQL, query normalization, routing predicate, numeric conversion, interpreter, feature getter, policy, profile definition or native module is changed.

The current composite validator's repeated profile fingerprints remain charged. This first revision does not introduce fingerprint memoization or a second query-boundary optimization.

## Ownership and invalidation

- Original complete composite validation owns a copy of the caller's tree. The learner never receives or supplies a prepared handle.
- A handle belongs to one backend, connection and prepared-cache/profile binding. Session queries check backend/connection liveness, cache object/identity and runtime-profile object before execution. A change requires a new session. First resolution also verifies the prepared artifact's runtime profile identity.
- The backend cache still owns its validated artifact snapshot; original limits of 16 entries and 2 MiB remain unchanged. A session retains at most one prepared artifact, independently of whether its cache entry is later evicted. Direct mutation of backend-private profile/cache internals is not a supported profile update; replace the binding for semantic profile changes.
- Clearing entries does not invalidate an already owned artifact on the same binding. Evicting server installation still causes acknowledged reinstallation. Cold measurement explicitly clears entries, evicts installation, and creates a new session, so it cannot reuse a prior session's compiled artifact.
- Closing/replacing the connection, replacing the cache or profile binding, and cross-backend use reject the old session. A failed execution closes the backend and is never replayed as native fallback.
- Compilation, admission and installation costs remain visible. This contract does not redefine activation as an amortized persistent-service objective.

## Frozen inputs and comparison

Use the original selective pilot manifest `082b167507e25009bdb25ea613950cd434ef38608fbcbc6194af19c363d0f6dc`, P1 package manifest `4c2f475664784b1851b1274a5c696bccbc55ee41c659a469c3643eb0ca0109c0`, and verified P1 receipt `16647a2486df6f191a764f4600e17ee2437f01352edc76eb3646490ca3b90378`.

Preserve the same x86 module/image, physical 247,286-row index, `ef_search=640`, `k=10`, 200 exposed development vectors and all 600 query/filter cases. Candidate semantic hash remains `a014a290966444a86614f1e5be1960dad2fb8684044e85e9df82899911062b0d`, with original seed credit. Compare original and owned execution for each unchanged semantic arm:

1. `cons-bypass108` candidate, light19, native bypass on `votes108`.
2. Same mask/profile/conditions, all leaves continue.
3. Host-only routed-native control, empty eligibility mask.

There are six execution arms. Every arm gets its own randomized ordinary-native pair. Within each query, semantic-arm order is deterministically shuffled and rotated across three blocks. Original/owned variants are adjacent; their initial order is hash-selected and alternates by block. Query order uses seed 20261022 plus block. Each arm runs activation, one discarded warmup, then three retained reuse pairs after explicit installation eviction and cache clearing.

The original pair timer and full outer application timer are preserved. Direct new-versus-old contrasts match query, block, regime and repetition and compare the two policy execution times. They do not subtract independently summarized native gaps. All three strata, all blocks, and ordinary-native baselines remain visible.

## Diagnostic pass and native correctness

After the entire unprofiled pass completes, profile 30 vector groups, all three filters, all six arms, using the lowest canonical SHA-256 values of `["prepared-diagnostic-v1", group]`. No adaptive subsampling. Preparation, activation, discarded warmup and reuse have separate groups.

Getter qualification remains the original 921-search procedure. Every case has pinned exact/native/light19 references and an actual route/first-stop proof for all six arms. Native/exact/trace reference identities must reproduce P1 pins. Original/owned IDs, distances, recall, stopped prefix and acknowledgements must agree, including diagnostic outputs. Trace normalization and transport code remain unchanged by the AST-checked backend body.

Diagnostic function counts must show one backend cache `prepare` per original eligible query; owned first activation also prepares once, and owned warmup/reuse prepares zero times. Bypasses and session constructors do not call backend cache preparation. Profiling times never enter latency criteria. There are 72 profile groups per block, 216 total.

Local protocol stubs and simulated timing validate interfaces, ownership, accounting and rejection behavior. They do not establish native qualification or performance; those await this Torch comparison.

## Resource ceiling and finite stopping rule

| Item | Per block | Whole campaign |
| --- | ---: | ---: |
| Serial allocations | 1 | Exactly 3 maximum |
| CPUs / memory / wall limit | 4 / 32 GiB / 2 hours | At most 6 allocated wall-hours, 24 allocated CPU-hours |
| Runtime work deadline | 6,600 seconds | One deadline per block |
| Getter searches | 921 | 2,763 |
| Primary searches including getters | 42,321 | 126,963 |
| Diagnostic searches | 5,400 | 16,200 |
| Total searches | 47,721 | 143,163 |
| Primary retained / discarded warmup pairs | 14,400 / 3,600 | 43,200 / 10,800 |
| Diagnostic retained / discarded warmup pairs | 2,160 / 540 | 6,480 / 1,620 |
| Explicit control eviction installations | 4,140 | 12,420 |
| Provider calls / confirmation queries | 0 / 0 | 0 / 0 |

Search accounting is `921 + 600 × (3 references + 6 proofs + 6 × 5 pairs × 2 executions)` for primary timing, plus `90 × 6 × 5 × 2` diagnostic executions. Eviction installs are separately counted SQL operations, not searches; not every SQL statement is counted.

Only one implementation and this three-block campaign are included. No automatic retuning, additional allocations, reruns or second variant follow a failure. A durable global reservation and per-block dispatch record prevent duplicate/reupload submissions; an ambiguous dispatch stays unknown. Known jobs are serial `afterok` dependencies. Each allocation restores/stops a private database; original studies and prepared inputs stay protected/read-only.

## Prospective engineering criteria

Reconstruct summaries with the original 10,000-resample vector-group bootstrap, seed 20261019. The vector is the independent unit across all filters, blocks and repetitions. Use the upper endpoint of the two-sided 95% interval for the following required criteria; all must pass:

- **Candidate reuse:** direct owned-minus-original primary latency upper bound <= -0.10 ms; mean log latency-ratio upper bound <= `log(0.98)`; outer application gap upper bound <= -0.10 ms. Its primary point saving must be positive in every block.
- **No material regressions:** for every semantic arm, both regimes, overall and every filter, direct primary gap upper bound <= +0.10 ms and mean log ratio upper bound <= `log(1.02)`; outer gap upper bound <= +0.10 ms. These controls prevent a pooled win from hiding a bypass/activation regression.
- **Correctness/mechanism:** complete coverage, preserved identities, exact old/new outputs and stopping behavior, valid original quality criteria, and the diagnostic preparation-call counts above. Invalid/missing/corrupt evidence fails verification rather than being dropped.

The original native recall floor (0.95 per filter), default-relative recall margin (0.005), development reserve (0.0025) and activation/reuse latency checks remain separately reported against ordinary native. An engineering pass does not imply that the frozen candidate now beats native on activation. No final data is opened or candidate selected.

Report `pass` or `revise_or_retain_original` for this P2a engineering gate. Broader G2/M1 economics require review of actual residual costs and operating scope; M2, M3 and canonical acceptance stay unestablished. A failed or inconclusive result consumes this campaign allowance; any follow-up requires a separately declared mechanism/version and finite budget.
