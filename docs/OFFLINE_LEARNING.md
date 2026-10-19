# Offline policy learning tools

The experimental `fannagent learning` commands prepare and assess stopping policies from saved training evidence. They use the existing bounded policy validator and interpreter, keep unmeasured outcomes unknown, and save reproducible candidate receipts. The commands make no model or database requests and have no serving or deployment authority.

This implements the first stage of the [revision plan](POLICY_LEARNING_REVISIONS.md). The running Torch feedback package and existing acceptance code remain fixed.

The [verification record](verification/offline-learning-v1.json) records the 193 passing non-integration tests and exact replay of the six existing trees over 300 training queries each. A local smoke run is saved under `runs/learning-v1/` (ignored by Git). Its fitted candidate still has unmeasured stops and no timing qualification.

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

The first adapter supports the pinned `ef_search=640` lightweight training package. The returned feedback archive needs the separate Stage 2 raw-result and receipt verification before its additional labels or timings are normalized. Existing Torch acquisition, import and collection scripts are unchanged.

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

Training feasibility requires valid complete results, recall noninferiority overall and per filter, the declared native recall floor per filter, and measured overall latency improvement. A per-query recall loss is retained as a diagnostic and is not an unconditional aggregate rejection. Replay work savings alone never establish timing feasibility. Timing normalization from the running batch is deferred until its raw results and receipts can be verified.

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
