# Offline policy learning tools

The experimental `fannagent learning` commands prepare and assess stopping policies from saved training evidence. They use the existing bounded policy validator and interpreter, keep unmeasured outcomes unknown, and save reproducible candidate receipts. The commands make no model or database requests and have no serving or deployment authority.

These tools implement the evidence import, scoring and development interface in the [revision plan](POLICY_LEARNING_REVISIONS.md). Completed Torch packages and existing acceptance code remain fixed.

The [verification record](verification/offline-learning-v1.json) records the 193 passing non-integration tests and exact replay of the six existing trees over 300 training queries each. A local smoke run is saved under `runs/learning-v1/` (ignored by Git). Its fitted candidate still has unmeasured stops and no timing qualification.

The [returned-feedback verification record](verification/offline-learning-v2.json) records 211 passing tests and the complete Stage 2/3 offline pass. Artifacts under `runs/learning-v2/` include the verified evidence, benchmark comparisons, ten archived candidates, four new baseline fits, the ablation study and a deduplicated plan for 49 additional query/checkpoint measurements. One fit always continues; the other three require 49, 32 and 11 outcomes respectively. None establishes a new latency benefit or qualifies for confirmation.

## Import existing training evidence

Run from the core agent checkout or an environment containing the revised core and its pgvector extension. The source package is read as data; its Python and shell files are never executed. Backend discovery reads the extension descriptor and runtime profile without creating a backend or connecting to PostgreSQL.

```sh
mkdir -p runs/learning-v1
fannagent learning import-torch ../trials/torch-reviews-policy-feedback \
  --backend pgvector --output runs/learning-v1/corpus.json
fannagent learning inspect runs/learning-v1/corpus.json
```

Use a fresh output filename. The importer verifies the package manifest, original learning receipt, declared training inventory, qualified feature columns, source candidate hashes and binding to the supplied runtime profile. It rejects confirmation records, extra feature columns, broken trajectories, duplicate labels and mismatched work counters. Query vectors and oracle selections are excluded from the normalized evidence.

The original native prefix proof may cover fields omitted from the sanitized export. The corpus retains that source proof and its artifact identity. Importing does not claim to repeat native verification by hashing fewer features.

The first adapter supports the pinned `ef_search=640` lightweight training package. The returned-data adapter below performs separate raw-result, receipt and scorer checks before incorporating additional labels or timings. Existing Torch acquisition, import and collection scripts are unchanged.

## Import returned feedback and check scorer parity

Keep the extracted campaign, its full archive and its four-file feedback archive together under their original names. Supply the independent local verification record containing the source checksums previously matched to Torch. The importer verifies those archive hashes and compares every archive member with the extracted files. It never extracts files or executes the campaign's scripts.

```sh
mkdir -p runs/learning-v2
fannagent learning import-feedback ../trials/torch-reviews-policy-feedback \
  ../trials/torch-reviews-results/reviews-policy-feedback-20261019T175419Z.g5ya3i5n \
  --verification ../trials/torch-reviews-results/reviews-policy-feedback-20261019T175419Z.g5ya3i5n-analysis/verification.json \
  --output runs/learning-v2/returned-verified.json

fannagent learning parity runs/learning-v2/returned-verified.json \
  ../trials/torch-reviews-results/reviews-policy-feedback-20261019T175419Z.g5ya3i5n \
  --output runs/learning-v2/parity.json
fannagent learning benchmark runs/learning-v2/returned-verified.json \
  --output runs/learning-v2/benchmark-report.json
```

The new `fannagent.learning.returned-feedback.v1` envelope contains the normalized corpus and benchmark records. Stage 1 corpus parsing and evidence hashes retain their original format. The importer preserves original outcomes, recomputes new-label prefix proofs, checks actual first stops through the shared interpreter, verifies result-based recall and continue controls, and requires exact arm/query/block/repetition coverage. It retains native runtime identities, qualified getters, allocation identifiers, warmup counts and the original spending receipt. Raw result IDs, distances and query vectors are excluded from the normalized evidence.

Scorer parity compares every saved block and pooled summary, including per-filter intervals and candidate feasibility decisions. Structure and discrete values must agree exactly; floating results allow absolute roundoff of at most `1e-12`. The seeded bootstrap samples independent vectors across all filters, repetitions and allocations. Pooled and per-block reports remain separate. This is reproduction of the declared empirical criterion, not a new statistical acceptance claim.

The 16 arms retain their distinct identities. Matched continue controls are linked to their candidates. The retrospective oracle retains per-query policy hashes and cannot become a deployable global policy. `benchmark` reports candidate-versus-native measurements and separate matched-control contrasts; subtracting a control cost never establishes deployed savings.

## Fit and evaluate a candidate

```sh
fannagent learning fit runs/learning-v1/corpus.json \
  --depth 2 --minimum-leaf-groups 8 --risk-weight 20 --folds 5 \
  --output runs/learning-v1/fit.json
fannagent learning evaluate runs/learning-v1/corpus.json runs/learning-v1/fit.json \
  --output runs/learning-v1/assessment.json
```

`fit` is a deterministic conventional tree baseline. It trains only on measured stopping outcomes and keeps every filter variant of a vector in the same validation fold. Its conservative proposal target is preservation of native recall on individual measured stops. That proposal target does not replace the study's aggregate recall tolerance. Fold diagnostics are descriptive development feedback; additional labels and independent confirmation are still needed.

The evaluator validates a candidate once, then executes the existing interpreter at each checkpoint until its first stop. It requires the corpus feature groups, native-qualified inputs and declared decision-depth limit. A fitted artifact must match the corpus evidence hash. A plain bounded policy object is also accepted.

Assessments distinguish measured native-preserving stops, measured recall losses, invalid results, runtime errors, continued queries and unknown stops. Unmeasured stops produce explicit measurement requests. Earliest measured native-preserving checkpoints provide retrospective work comparisons, not latency estimates or proven optima. Without `--output`, evaluation prints a bounded feedback summary; the full file contains every decision and measurement request.

`inspect` also identifies identical allowed feature states with conflicting measured native-preservation labels. This is a useful information diagnostic; it does not prove that the aggregate quality objective is unattainable.

## Keep measured timing distinct from replay

The versioned corpus can represent already verified native/policy timing pairs and a predeclared schedule. The timing assessor requires full query, block and repetition coverage. It reports cold activation separately from reused execution, clusters uncertainty by vector across repetitions and filter variants, and retains block summaries. Incomplete coverage cannot yield a feasibility decision.

Training feasibility requires valid complete results, recall noninferiority overall and per filter, the declared native recall floor per filter, and measured overall latency improvement. A per-query recall loss is retained as a diagnostic and is not an unconditional aggregate rejection. Replay work savings alone never establish timing feasibility. Returned measurements retain the frozen reported latency boundary, including activation in the cold regime; the latency criterion uses the upper confidence bound on the mean log latency ratio.

Every report states that canonical acceptance has not been established. These tools consume no calibration, confirmation or final-test entitlement and do not change `fannagent evaluate` or deployment behavior.

## Archive and recover candidates

```sh
fannagent learning archive runs/learning-v1/corpus.json runs/learning-v1/fit.json \
  --archive runs/learning-v1/candidates
fannagent learning candidates --archive runs/learning-v1/candidates
fannagent learning show RECEIPT_HASH --archive runs/learning-v1/candidates
```

The archive uses the existing content-addressed artifact store in a separate directory. It retains the corpus, policy, fitting configuration and assessment before publishing an immutable receipt. Repeating the same request recovers the same receipt. Interrupted publication leaves no visible partial candidate; retrying reuses already durable artifacts.

The archive refuses an ordinary study directory, preserves every other run's spending state and never selects an accepted serving policy. Read-only commands verify saved artifact hashes. Fitting metadata is limited to 8 KiB and archive artifacts to 512 MiB. Existing output files are preserved rather than overwritten.

The same commands are available through `python -m fannagent.learning`, which imports neither model-provider modules nor concrete database clients for evaluation, fitting or archive inspection. Model-driven learning remains a later explicit stage under the original campaign ledger.

## Use the measured-feedback-v2 learning interface

`learning qualify CORPUS POLICY` reports aggregate training quality and measured timing qualification. Its `learning_qualification` record distinguishes missing outcomes, invalid executions, quality failure, readiness for timing measurements and measured feasibility. Trace-verified stopping labels support replay and fitting. Complete measured policy executions can establish quality even when the corresponding reusable checkpoint label has not yet been acquired; reports keep that distinction explicit. Invalid results and runtime errors remain hard failures.

`LearningTools` exposes `inspect`, `validate`, `screen`, `archive` and `freeze` through both a request object and the existing `FileBroker` `(operation, args)` interface. For example, save `{"operation":"screen","policy":POLICY_OBJECT}` in a JSON file, then run:

```sh
fannagent learning tool runs/learning-v2/returned-verified.json request.json \
  --archive runs/learning-v2/candidates
```

Screen feedback bounds examples, preserves unknown outcomes, includes actual timing reports when available, and references the evidence and policy hashes. Archived assessments retain the aggregate gate, every measured failure and all measurement requests. Freezing requires valid aggregate quality and measured latency gains in both activation and reuse regimes. It records an immutable selection for later confirmation; it neither consumes confirmation nor establishes serving acceptance. Retry recovers the same selection, and a different candidate requires a separate study archive.

The old trial's zero-loss submission rule and candidate locks remain unchanged. This interface is the new study version. It can serve an offline learner through the existing broker, but these commands do not launch a model round. Future model work must use the original durable ledger, including its prior charges and uncertain reservations; a new evidence version or archive does not create a new budget. Grouped cross-validation over adaptively acquired training labels is development feedback, not independent confirmation.

## Prepare the separate predicate-context-v1 ablation

```sh
fannagent learning prepare-ablation runs/learning-v2/returned-verified.json \
  ../trials/torch-reviews-policy-feedback \
  --output runs/learning-v2/predicate-context-v1
```

Preparation publishes `study.json`, `query-context.json` and a planned runtime profile in a fresh directory. The context extractor reads the actual portable predicate, rather than deriving inputs from query IDs or filter names. Version 1 supports `m_000000 >= nonnegative_integer`, with `query_predicate_threshold=0` for an unfiltered query distinguished by the existing `predicate_leaf_count=0`. It rejects unsupported predicate shapes instead of inventing context.

The baseline and context arms share evidence, vector-group folds, fitting settings, policy depth, quality objective and spending contract. The planned context arm has a different profile hash and collection group. Its feature is explicitly unqualified; the preparation artifact is not a feedback corpus and cannot be passed to the fitter as qualified native evidence. Existing timings do not apply to the new profile.

Before running the context arm, implement and qualify its native getter, verify numeric branches and causal prefixes, check native equivalence, and measure collection cost under both profiles. Give every competing learner the same context and acquire actual outcomes at any new first stops. The manifest retains these requirements and the original activation/reuse protocol. No confirmation or model calls occur during preparation.

Account for predicate extraction and binding as well as checkpoint reads. Additional context setup must not disappear outside the measured comparison. Keep the frozen reported latency primary and retain an end-to-end measurement covering any additional setup before claiming a deployed benefit.
