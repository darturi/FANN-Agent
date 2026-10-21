# Master experiment index

Snapshot: October 21, 2026, America/New_York. This is the entry point for the
saved JinyangLiWork experiment history, including unsuccessful runs. Artifact
paths are relative to this document and require the sibling workspace folders;
cloning FANN-Agent alone does not download `trials/`, `harness/` or the raw data.

- [Complete saved-run catalog](RUN_CATALOG.md): individual attempts, failures,
  agent conversations, measurement blocks, analyses and engineering checks.
- [Machine-readable inventory](run-inventory.json): evidence paths, hashes,
  recorded outcomes, reproduction references and journaled experiment IDs.
- [Archive manifest](archive-manifest.json): archive locations, sizes, SHA-256
  hashes and comparisons with existing checksum sidecars.
- [Backup audit](BACKUP_AUDIT.md): verified local integrity, missing artifacts,
  remote-check results and outstanding backup coverage.

The initial inventory contains 292 saved evidence records and 15 experiments
registered inside saved agent journals. Locations include repeated blocks,
analysis directories, packages and synthetic checks; they are not a count of
independent scientific experiments. The 207 discovered archives include source,
runtime, engineering and result archives. Seventeen result tarballs sit directly
under `trials/torch-reviews-results/`; the manifest also covers nested training
packages and archives elsewhere in the scan roots.

## Coverage and interpretation

The catalog enumerates persisted evidence under `trials/`, `agent/runs/`,
`agent-pgvector/verification/`, `harness/results/`, `harness/docs/qualification/`,
`mini-bench/qualification/`, the two research verification roots listed in the
inventory, and `release/`. It excludes dependency installations, vendor/source
copies, private stores, cached artifacts, input/reference corpora and copied
packages inside results. The precise roots and excluded directories are recorded
in JSON. Unit tests are supporting verification, not additional research trials.
Journaled subexperiments are listed under their parent saved run.

The inventory is exhaustive for these discovery rules and this local snapshot.
Remote-only, deleted, unrecorded or differently named runs cannot be certified
complete. The known remote failures below are retained explicitly even when raw
results are absent locally. A directory, finished job or passing mechanical
check does not establish scientific success. Saved status fields can be earlier
than a later report; use the study conclusions below and the linked evidence.
Where no exact historical invocation is recoverable, the catalog says so instead
of constructing a replacement command.

## Study results and artifact map

Each directory link exposes its saved configurations, logs, raw measurements and
supporting artifacts. The catalog enumerates the child attempts and block IDs.
Recipe links describe reproduction; launching a new run is separate from
reading or reanalyzing saved results.

### Earlier harness and local development studies

| Study / saved runs | Result and limits | Artifact location | Reproduction reference |
|---|---|---|---|
| MoReVec harness baselines, September 21 | Saved all-engine and pgvector benchmark/conformance evidence; retain the recorded versions and settings. | [all engines](../../../harness/results/morevec-all/), [pgvector](../../../harness/results/morevec-pgvector/) | [harness methodology](../../../harness/docs/methodology.md), saved run configurations |
| Instrumentation and teardown checks, September 27 | Four persisted trace/teardown runs; engineering verification. | [runs](../../../harness/results/instrumentation-demo/) | [harness evidence contract](../../../harness/docs/evidence.md) and each run's configuration |
| Reviews qualification and corrected study, September 28 | Qualification plus original/corrected study and prefix-label evidence; do not substitute original records for corrected evidence. | [qualification](../../../harness/results/morevec-reviews-qualification/), [original](../../../harness/results/morevec-reviews-study/), [corrected](../../../harness/results/morevec-reviews-study-corrected/) | [harness README](../../../harness/README.md), saved study manifests |
| Movies small agent and research trials, October 9–11 | Original run interrupted; fresh research run completed without a recommendation after 12 provider calls. | [family](../../../trials/morevec-movies-small/), [research report](../../../trials/morevec-movies-small/research-trial-20261011T024817Z/report.txt), [saved agent state](../../../trials/morevec-movies-small/runs/) | [original instructions](../../../trials/morevec-movies-small/instructions.txt), [research instructions](../../../trials/morevec-movies-small/research-instructions.txt) |
| Movies latency diagnosis, stall fixes and Docker stability | Includes timeouts, interrupted/incomplete comparisons and rejected candidates. Sequential quiet comparison passed its engineering criteria; this did not certify a learned serving policy. | [all attempts](../../../trials/morevec-movies-small/), [accepted sequential comparison](../../../trials/morevec-movies-small/quiet-sequential-20261011T010606Z/report.txt) | [diagnosis recipe](../../../trials/morevec-movies-small/latency-diagnosis-README.txt), [fix recipe](../../../trials/morevec-movies-small/latency-fix-README.txt); per-attempt status retains executed commands |
| Movies offline stopping feasibility, two October 11 analyses | Corrected interpretation of saved labels; oracle work headroom was substantial, but estimated transport/control overhead constrained latency. These are retrospective diagnostics. | [first](../../../trials/morevec-movies-small/stopping-feasibility-20261011T030828Z/), [corrected report](../../../trials/morevec-movies-small/stopping-feasibility-20261011T031244Z/report.txt) | [analysis source](../../../trials/morevec-movies-small/analyze_stopping_feasibility.py), saved summary/identity/query files |
| Reviews workload qualification, October 11 | Includes three failed qualification attempts, a failed oracle preflight and a failed settings screen, followed by passing checks and quiet measurements. | [all qualification attempts](../../../trials/morevec-reviews-qualification/) | [qualification source](../../../trials/morevec-reviews-qualification/qualify_workload.py), [screen source](../../../trials/morevec-reviews-qualification/screen_settings.py), [measurement source](../../../trials/morevec-reviews-qualification/measure_workload.py); saved status/configuration where available |
| Bounded Reviews, two October 12 execution receipts | First execution reached its 12-attempt limit without an accepted policy. Preserve the second receipt separately; terminal completion is not inferred from its presence. | [executions and prepared study](../../../trials/morevec-reviews-bounded/) | [readiness](../../../trials/morevec-reviews-bounded/readiness.txt), [entry point](../../../trials/morevec-reviews-bounded/study_entry.py) |
| Fixed bounded Reviews | Includes a failed unpaid integration check, a later sealed preparation and a model execution ending without a recommendation. The root preparation report predates the execution outcome. | [family](../../../trials/morevec-reviews-fixed-bounded/), [execution report](../../../trials/morevec-reviews-fixed-bounded/execution-20261012T015808Z/report.txt) | [study entry](../../../trials/morevec-reviews-fixed-bounded/study.sh), saved `agent.yaml` and contract |
| Durable bounded Reviews | Includes failed preparation and unpaid checks; completed model execution ended with no recommendation. | [report](../../../trials/morevec-reviews-durable-bounded/report.txt), [all attempts](../../../trials/morevec-reviews-durable-bounded/) | [study entry](../../../trials/morevec-reviews-durable-bounded/study.sh), saved contract/runtime selection |
| Workflow review / durable workflow packaging | Unpaid review, analysis, delivery audits and runtime packages; engineering artifacts, not new successful policy measurements. | [workflow review](../../../trials/morevec-reviews-workflow-review/), [durable workflow](../../../trials/morevec-reviews-durable-workflow/) | [saved-state analysis](../../../trials/morevec-reviews-durable-workflow/analyze_saved.py), package manifests and delivery audits |
| Unpaid Reviews feasibility, two October 12 attempts | Failed first preparation; completed follow-up found no promising rule in the bounded families. | [attempts](../../../trials/morevec-reviews-unpaid-feasibility/), [final report](../../../trials/morevec-reviews-unpaid-feasibility/run-20261012T141648Z/report.txt) | [runner](../../../trials/morevec-reviews-unpaid-feasibility/run_feasibility.py), [reporter](../../../trials/morevec-reviews-unpaid-feasibility/report_results.py), saved plans/configurations |
| Overhead/predictor investigation, four October 13 attempts | Preparation/settings failures and a stopped diagnostic preceded the functional follow-up. No predictor met unchanged recall and latency guards. | [attempts](../../../trials/morevec-reviews-overhead-predictor/), [final report](../../../trials/morevec-reviews-overhead-predictor/run-20261013T143007Z/report.txt) | [investigation runner](../../../trials/morevec-reviews-overhead-predictor/run_investigation.py), [reporter](../../../trials/morevec-reviews-overhead-predictor/report_results.py); per-attempt frozen plans/code |
| Runtime fixes, two October 13 attempts | Initial attempt retained audits without a terminal result; follow-up completed runtime checks and archived a prior report correction. | [attempts](../../../trials/morevec-reviews-runtime-fixes/), [final report](../../../trials/morevec-reviews-runtime-fixes/run-20261013T151714Z/report.txt) | [checks](../../../trials/morevec-reviews-runtime-fixes/run_checks.py), [reporter](../../../trials/morevec-reviews-runtime-fixes/report.py), saved source snapshots |

### Torch campaigns, agent learning and follow-ups

All Torch names below are exact saved campaign identifiers. Unless otherwise
specified, remote results originated under `/home/dar579/torch-reviews-results/`.
Remote locations are historical provenance; current existence was not verified
because noninteractive SSH authentication failed during the backup audit.

| Campaign / experiment | Result and limits | Results and artifacts | Reproduction reference |
|---|---|---|---|
| Initial Torch launch/release, October 15 | Launcher release failed; three jobs cancelled. No measurement claim. | [failure receipt](../../../trials/torch-reviews-launch-20261015/release-failure.json) | [operations recipe](../../../trials/torch-reviews-operations/README.md); exact campaign/jobs below |
| Original Torch preparation, October 15 | PostgreSQL lifetime ended between contained executions; preparation failed and dependent measurements were cancelled. | [failure receipt](../../../trials/torch-reviews-launch-20261015/preparation-19935115-failure.json) | [original package](../../../trials/torch-reviews-first/README.md), [separate lifecycle correction](../../../trials/torch-reviews-lifecycle-fix/README.md) |
| Lifecycle campaign measurement, observed October 18 | All three blocks failed before paired timing because authoritative exact reference did not bypass indexes. | [failure receipt](../../../trials/torch-reviews-launch-20261015/measurement-19942043-failure.json) | [lifecycle recipe](../../../trials/torch-reviews-lifecycle-fix/README.md), [reference correction](../../../trials/torch-reviews-reference-fix/README.md) |
| `reviews-reference-20261018T234510Z.UA52vD` | Three completed allocations; 10,800 pairs. Control-path overhead dominates tested entry/frontier policies; development evidence only. | [raw campaign](../../../trials/torch-reviews-results/reviews-reference-20261018T234510Z.UA52vD/), [verified report](../../../trials/torch-reviews-results/analysis-reviews-reference-20261018T234510Z.UA52vD/report.txt) | [reference-fix recipe](../../../trials/torch-reviews-reference-fix/README.md) |
| `reviews-ef-sweep-20261019T004327Z.dcFzo0` | Completed ef_search sweep on the same physical index; records recall/overhead tradeoffs and supports subsequent ef=640 work. | [campaign](../../../trials/torch-reviews-results/reviews-ef-sweep-20261019T004327Z.dcFzo0/), [verified report](../../../trials/torch-reviews-results/analysis-reviews-ef-sweep-20261019T004327Z.dcFzo0/report.txt) | [ef-sweep recipe](../../../trials/torch-reviews-ef-sweep/README.md) |
| `reviews-size-sweep-20261019T021505Z.jbrSqB` | Completed four-size nested-subset sweep; one realized index graph per size, descriptive development comparison. | [campaign](../../../trials/torch-reviews-results/reviews-size-sweep-20261019T021505Z.jbrSqB/), [verified report](../../../trials/torch-reviews-results/analysis-reviews-size-sweep-20261019T021505Z.jbrSqB/report.txt) | [size-sweep recipe](../../../trials/torch-reviews-size-sweep/README.md) |
| Queue-statistics optimization qualification | Preserved native correctness/performance evidence for the collector patch; engineering stage preceding the actual crossover. | [report](../../../trials/torch-reviews-queue-optimization/report.txt), [native results](../../../trials/torch-reviews-queue-optimization/native-results.json) | [collector comparison recipe](../../../trials/torch-reviews-collector-ab/README.md); saved qualification logs |
| `reviews-collector-ab-20261019T052849Z.Us5why` | 34,560 raw pairs; optimized numerical variance removes about 78–87% of its prior reported overhead. Percentile controls retain their distinct cost. | [campaign](../../../trials/torch-reviews-results/reviews-collector-ab-20261019T052849Z.Us5why/), [verified report](../../../trials/torch-reviews-results/analysis-reviews-collector-ab-20261019T052849Z.Us5why/report.txt) | [collector recipe](../../../trials/torch-reviews-collector-ab/README.md) |
| `reviews-policy-learning-20261019T145148Z.EJ34ct` learning export | Saved training corpus and fixed/oracle baselines, used by later agent work; export is distinct from agent execution. | [learning export](../../../trials/torch-reviews-results/reviews-policy-learning-20261019T145148Z.EJ34ct-learning/) | [policy-learning recipe](../../../trials/torch-reviews-policy-learning/README.md) |
| Initial agent plus bounded continuation/finalization | Includes authentication failure, request-limit stop and recorded continuation. Agent abstained in all four ef/feature cases. Early audit found a qualified-feature omission and use of an unqualified getter; no latency claim. | [saved run](../../../trials/torch-reviews-results/reviews-policy-learning-20261019T145148Z.EJ34ct-agent/), [verified report](../../../trials/torch-reviews-results/analysis-reviews-policy-learning-20261019T145148Z.EJ34ct/report.txt), adjacent authentication/resume/finalization receipts and logs | [original recipe](../../../trials/torch-reviews-policy-learning/README.md), [finalization recipe](../../../trials/torch-reviews-policy-finalization/README.md) |
| Corrected qualified-feature agent rerun | All four cases again explicitly abstained; 13 additional requests. Offline screening only; no candidate confirmation. | [qualified run/report](../../../trials/torch-reviews-results/reviews-policy-learning-20261019T145148Z.EJ34ct-agent-qualified/), corresponding checksummed archive | [qualified rerun recipe](../../../trials/torch-reviews-policy-qualified/README.md) |
| Offline conventional fits / measured-feedback development | Six original trees, four updated fits and 49 deduplicated unknown first stops; candidate stores and predicate-context preparation retained. | [learning-v1](../../runs/learning-v1/), [learning-v2](../../runs/learning-v2/) | [offline tools](../OFFLINE_LEARNING.md), [revision plan](../POLICY_LEARNING_REVISIONS.md) |
| `reviews-policy-feedback-20261019T175419Z.g5ya3i5n` | 57,600 pairs. All six conventional trees fail recall despite speedups; hindsight oracle remains diagnostic. | [campaign](../../../trials/torch-reviews-results/reviews-policy-feedback-20261019T175419Z.g5ya3i5n/), [verified report](../../../trials/torch-reviews-results/reviews-policy-feedback-20261019T175419Z.g5ya3i5n-analysis/report.txt) | [feedback recipe](../../../trials/torch-reviews-policy-feedback/README.md), saved [verification source](../../../trials/torch-reviews-results/reviews-policy-feedback-20261019T175419Z.g5ya3i5n-analysis/verify.py) |
| Training-stops original package | Superseded package preserved; no separately collected completed campaign discovered. Do not count v2 results twice. | [original package](../../../trials/torch-reviews-training-stops/) | [original recipe](../../../trials/torch-reviews-training-stops/README.md) |
| `reviews-training-stops-v2-20261019T205135Z.lvzjw42d` | 32,400 pairs and 49 new actual stop outcomes. None of four predeclared CART candidates passes recall and latency together. | [campaign](../../../trials/torch-reviews-results/reviews-training-stops-v2-20261019T205135Z.lvzjw42d/), [verified report](../../../trials/torch-reviews-results/reviews-training-stops-v2-20261019T205135Z.lvzjw42d-analysis/report.txt) | [training-stops v2 recipe](../../../trials/torch-reviews-training-stops-v2/README.md) |
| Predicate-context implementation/qualification | Separate feature-profile mechanical verification; later measured in the ablation. | [local qualification](../../../trials/torch-reviews-predicate-context/), [native record](../../../agent-pgvector/verification/predicate-context-v1.json) | [revision plan](../POLICY_LEARNING_REVISIONS.md), ablation recipe below |
| `reviews-predicate-ablation-20261019T235922Z.ilxcioru` | 86,400 pairs, eight fits, 24 arms. Context reduces some recall loss, but no candidate meets all unchanged recall and timing gates. | [campaign](../../../trials/torch-reviews-results/reviews-predicate-ablation-20261019T235922Z.ilxcioru/), [verified report](../../../trials/torch-reviews-results/reviews-predicate-ablation-20261019T235922Z.ilxcioru-analysis/report.txt) | [ablation recipe](../../../trials/torch-reviews-predicate-ablation-v1/README.md) |
| `reviews-insertion-bypass-20261020T064451Z.ycqo7_i_` | 104,400 pairs, 29 arms; none qualifies in activation or reuse. Full raw and feedback archives retained. | [campaign](../../../trials/torch-reviews-results/reviews-insertion-bypass-20261020T064451Z.ycqo7_i_/), [verified report](../../../trials/torch-reviews-results/reviews-insertion-bypass-20261020T064451Z.ycqo7_i_-analysis/report.txt) | [insertion/bypass recipe](../../../trials/torch-reviews-insertion-bypass-v1/README.md) |
| `reviews-dispatch-overhead-20261020T152408Z.rhheoeyj` | Feedback/summary consistency verified; raw measurements unavailable locally. Two arms pass pooled reuse log-ratio/recall gates, but activation does not qualify; arithmetic latency deltas remain positive. | [feedback](../../../trials/torch-reviews-results/reviews-dispatch-overhead-20261020T152408Z.rhheoeyj-feedback/), [report and limitations](../../../trials/torch-reviews-results/reviews-dispatch-overhead-20261020T152408Z.rhheoeyj-analysis/report.txt) | [dispatch recipe](../../../trials/torch-reviews-dispatch-overhead-v1/README.md); full independent raw reanalysis requires missing full archive |
| Aggressive proposals v1, six conversations | All censored: five request-limit stops and one command timeout. No exports/completed A/B pairs; diagnostic intermediates do not establish a selection effect. | [conversations/summary](../../../trials/torch-reviews-results/aggressive-policy-proposals-v1/), [audit](../../../trials/torch-reviews-results/aggressive-policy-proposals-v1-analysis/audit.json) | [v1 recipe](../../../trials/torch-reviews-aggressive-proposals-v1/README.md), [offline audit source](../../../trials/analyze_aggressive_proposals_v1.py) |
| Aggressive proposals v2, six conversations | Two exploratory conversations complete and export 12 policies; four conversations budget-censored. Zero complete A/B pairs; A/B comparison inconclusive. | [conversations/summary](../../../trials/torch-reviews-results/aggressive-policy-proposals-v2/), [audit/export inventory](../../../trials/torch-reviews-results/aggressive-policy-proposals-v2-analysis/) | [v2 recipe](../../../trials/torch-reviews-aggressive-proposals-v2/README.md), [offline audit source](../../../trials/analyze_aggressive_proposals_v2.py) |
| Frozen proposal timing v1, both original cohorts | Both block-0 jobs fail at 234 backend calls because the frozen backend lacks `runtime_profile`; dependent arrays cancelled. No qualification result. | [original package](../../../trials/torch-reviews-results/frozen-proposals-timing-v1/), [failure/correction receipt](../../../trials/torch-reviews-frozen-proposals-timing-v1-runtime-fix/runtime-repair.json); raw remote failure files not downloaded | [original timing recipe](../../../trials/torch-reviews-frozen-proposals-timing-v1/README.md); preserve failure and use separately named correction |
| `reviews-frozen-proposals-timing-v1-runtime-fix-training-20261021T044854Z.l3c__b58` | All six blocks independently reproduced: 115,200 retained pairs, 100 vector groups. Two qualifiers; prespecified selection is `cons_S32_64_128_t002`: 12.690% activation and 13.545% reuse savings. Worst recall lower bound exactly meets −0.5 pp. Training feasibility only; confirmation unmeasured and A/B inconclusive. | [raw campaign](../../../trials/torch-reviews-results/reviews-frozen-proposals-timing-v1-runtime-fix-training-20261021T044854Z.l3c__b58/), [independent report](../../../trials/torch-reviews-results/reviews-frozen-proposals-timing-v1-runtime-fix-training-20261021T044854Z.l3c__b58-analysis/report.txt), [postrun record](../verification/frozen-proposals-timing-v1-runtime-fix-postrun.json) | [corrected recipe](../../../trials/torch-reviews-frozen-proposals-timing-v1-runtime-fix/README.md), exact saved-result reanalysis command below |

### Failure identities with incomplete local raw evidence

| Campaign | Job identity and outcome | Evidence |
|---|---|---|
| `reviews-20261015T141436Z.rf2vvnwf` | Build 19933958, prepare 19933968, measure 19933970; cancelled after launcher release failed. | [receipt](../../../trials/torch-reviews-launch-20261015/release-failure.json) |
| `reviews-20261015T142227Z.Vo0iYp` | Prepare 19935115 failed; dependent measure 19935117 cancelled. Initial campaign receipt's pending fields are superseded by failure evidence. | [launch](../../../trials/torch-reviews-launch-20261015/campaign-19935108.json), [failure](../../../trials/torch-reviews-launch-20261015/preparation-19935115-failure.json) |
| `reviews-lifecycle-20261015T151142Z.ccXL4N` | 19942043_0, _1, _2 failed exact-reference validation before paired timing. | [receipt](../../../trials/torch-reviews-launch-20261015/measurement-19942043-failure.json) |
| `reviews-frozen-timing-v1-training-c0-20261021T003548Z.yk9crum4` | 20479670_0 failed; 20479673_[1-2%1] cancelled. | [reported cohort failures](../../../trials/torch-reviews-frozen-proposals-timing-v1-runtime-fix/runtime-repair.json) |
| `reviews-frozen-timing-v1-training-c1-20261021T003751Z.gnq7yl2t` | 20479956_0 failed; 20479958_[1-2%1] cancelled. | [reported cohort failures](../../../trials/torch-reviews-frozen-proposals-timing-v1-runtime-fix/runtime-repair.json) |

Retrieve remote failure logs/status/accounting into a new local evidence directory
when authenticated access is available. Keep these failed runs separate from the
replacement successes. Current raw availability and exact replay of these failures
remain unverified.

### Engineering and synthetic verification

[Research audit](../../../research/agent-audit-2026-10-06/),
[literature-guidance verification](../../../research/verification/agent-literature-guidance-2026-10-09/),
[native profile verification](../../../agent-pgvector/verification/),
[harness qualification](../../../harness/docs/qualification/),
[mini-bench qualification](../../../mini-bench/qualification/REPORT.md) and
[release acceptance fixtures](../../../release/) retain additional checks,
including host/container simulations, lock recovery and installation failures.
Their individual discovered records are in the catalog. These establish local
contracts and readiness rather than new production performance claims.

## Reproduction procedures

### Inspect and verify saved results

Read the linked report and verification record first. The archive manifest pins
the current bytes; `matches` means the digest agrees with an existing sidecar.
`no usable sidecar` means a new inventory digest was calculated without an older
checksum to compare, not that the archive has been historically authenticated.

Check an archive with its existing sidecar from the directory containing both:

```sh
cd /Users/danielarturi/Developer/JinyangLiWork/trials/torch-reviews-results
shasum -a 256 -c reviews-frozen-proposals-timing-v1-runtime-fix-training-20261021T044854Z.l3c__b58.tar.gz.sha256
```

Preserve the original archive; extract only into a new directory after checking
member paths. Never execute a downloaded result's bundled Python code merely
because it is present. Use the preserved local implementation and pinned runtime
named in the study recipe. For database-backed agent histories, the original
installation can inspect registered experiments without model/database searches:

```sh
fannagent experiments --run /absolute/path/to/saved/run
fannagent experiments --run /absolute/path/to/saved/run --experiment-id RECORDED_ID
```

The inventory reads SQLite in read-only mode and lists each discovered registered
experiment ID; it does not dump configuration, credentials or provider responses.

### Independently reanalyze the latest completed campaign

The following is the archived recipe, provided for future reproduction. Creating
this index did not execute it or reopen confirmation data:

```sh
cd /Users/danielarturi/Developer/JinyangLiWork
bash trials/torch-reviews-frozen-proposals-timing-v1-runtime-fix/run.sh analyze \
  --campaign trials/torch-reviews-results/reviews-frozen-proposals-timing-v1-runtime-fix-training-20261021T044854Z.l3c__b58
```

It verifies the frozen local source, all six blocks, reports and selection from
saved raw results, without new model or database calls. The independent analysis
directory additionally contains `diagnostics.py`, `raw-reproduction.log`,
`overview.json`, `report.txt` and `verification.json`; the committed postrun record
pins all five hashes. Older study recipes link their original report/collection
code and verification receipts. Some early analyses lack a standalone exact
reanalysis command; retain that gap rather than implying identical rerun support.

### Repeat measurements or model generation

Use the original package README, manifest, scientific contract, source revisions,
runtime/image identities, dataset/index identity, split provenance and budget
receipt. The Torch recipes include upload, one-time submission, status and
collection commands. Full repeats require the original prepared database/index,
qualified x86 binary, Apptainer image and pinned Python dependencies on Torch.
Source and result archives alone do not prove those external dependencies can
currently be restored. Local historical recipes likewise require their preserved
Docker/runtime/source resources. Do not replace those with a newly built index
and label the result an identical replay.

Maintain vector-group clustering, unchanged recall gates, timer boundaries and
activation/reuse distinctions. Do not resume terminated/censored v1/v2
conversations, overwrite failed campaigns, or treat a diagnostic oracle as a
deployable candidate. Fresh paid generation needs its applicable budget and a
fresh declared run; stochastic model outputs are not guaranteed byte-identical.
Latest held-out confirmation is a separate future experiment, not a step needed
to inspect this index.

## Updating the record

For every new launch, add a row here with exact run ID, date/time zone, question,
protocol/source identity, result or failure, local/remote artifacts, reproduction
recipe and limitations. Record aborted preparation, cancellation, censored agent
runs, negative findings and supersession explicitly. Add collection/verification
and backup receipts when available. Preserve prior status and evidence.

Regenerate the detailed local inventory and archive hashes from the workspace:

```sh
cd /Users/danielarturi/Developer/JinyangLiWork
python3 agent/docs/experiments/build_catalog.py --hash-archives
```

This stdlib-only documentation helper imports no experiment modules, runs no
models/measurements and contacts no service. It reads the documented roots and
writes only `RUN_CATALOG.md`, `run-inventory.json` and, with the flag,
`archive-manifest.json` beside itself. Review the generated diff, update the
curated conclusions and backup audit, and commit the documentation. Copy/archive
verification must be recorded separately from hash integrity; the index is not
a backup of the linked raw files.
