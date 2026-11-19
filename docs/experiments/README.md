# Master experiment index

Updated: November 19, 2026, America/New_York. Saved work reviewed through the
completed broader-language oracle comparison on November 19. This is the entry
point for the saved JinyangLiWork experiment history, including unsuccessful runs. Artifact
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

The refreshed inventory contains 1,992 saved evidence records and 15 experiments
registered inside saved agent journals. Locations include definitions, receipts,
repeated blocks, analyses, packages and synthetic checks; they are not a count of
independent scientific experiments. The 444 discovered archives include source,
runtime, engineering and result archives, totaling 23,319,428,678 bytes. All 188
with usable checksum sidecars match; 256 have no usable earlier sidecar. The
October 21 inventory had 292 records and 207 archives. The increased record count
reflects both later work and expanded discovery of Markdown reports, receipts,
freezes and experiment definitions; it is not a count of new launches.

## Current study status — November 19, 2026

The active benchmark study uses raw ANN outputs with **exact search for offline
scoring only**. All six scalar filters plus unfiltered remain in scope. The
450 development / 150 validation / 275 test / 125 historical-exclusion split
remains the recorded split. The separately authorized hindsight studies have now
exposed outcomes for the 275-vector test cohort and the full 1,000-vector
workload, including validation and historical groups. Their fitted-cohort results
measure hypothetical policy capacity; they are not an untouched test of an agent
trained on development data. Earlier completion-guard results and older timing
criteria below retain their original conclusions.

| Stage | Latest recorded disposition | Authoritative evidence |
|---|---|---|
| M0 reader/CPU/search-work attribution | Job 23303080 verified; failed startup job 23074287 retained separately. Broad has a modest allocation-conditional development benefit, without a final performance claim. | [M0 assessment](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/reports/reader-attribution-assessment-23303080.md) |
| M1 runtime, prefix and cost qualification | Job 23376796 verified; all 9,436 reached prefixes labeled, including 1,496 partial prefixes. Runtime qualified; universal additive cost precision does not follow. | [M1 assessment](../../experiments/m1-assessment-v1/REPORT.md) |
| M2/M3 evidence and controller | Complete evidence bound. Both point-cost models fail their fixed precision limits; the separately qualified uncertainty-aware shortlist and bound positive/abstention rehearsals pass. | [M2/M3 report](../../experiments/m2-evidence-cost-v1/REPORT.md), [shortlist report](../../experiments/uncertainty-shortlist-v1/REPORT.md) |
| M4 agent episode and amendments | Initial payload-limit abstention and six-call closed outcome preserved. Dollar-governed continuation formally submits candidates 7/8; eight cumulative Messages calls cost $0.403114 under the original $15 ceiling. Both nominees preserve development recall and have supported uncertain cost estimates; estimated costs are not measured speedups. | [Final M4 assessment](../../experiments/m4-dollar-assessment-v1/REPORT.md), [nominees](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/m4-dollar-budget-v1/assessment-v1/nominees.json) |
| M5 live policy/control comparison | Sealed for one user-submitted development job. Native startup preflight, original-graph qualification and actual timings remain pending. No final policy selected. | [M5 preparation report](../../experiments/m5-policy-qualification-v1/REPORT.md), [freeze](../../experiments/m5-policy-qualification-v1/receipts/M5-freeze.json), [SFTP upload](../../experiments/m5-policy-qualification-v1/SFTP-UPLOAD.txt), [Torch/return commands](../../experiments/m5-policy-qualification-v1/COMMANDS.txt) |
| Live Torch feedback prototype | Local compiler, synthetic PostgreSQL and controller checks pass. No live-feedback allocation or provider episode is recorded; original-graph qualification remains pending. This is separate from M4/M5 and the oracle runs. | [Prototype status and boundaries](../../experiments/torch-live-feedback-v1/README.md), [verification](../../experiments/torch-live-feedback-v1/verification.json) |
| Earlier hindsight oracles | Count-preserving oracle and subsequent three-level v2 comparison completed on both cohorts. All intended-cohort recall gates pass; strict per-condition timing equivalence is not established. Preserve their separate quality gates and allocations. | [Count-preserving oracle](../../experiments/full-workload-oracle-v1/README.md), [three-level comparison](../../experiments/oracle-variants-v1/results/REPORT.md) |
| Broader-language feasible oracle | Completed job 23719580 after preserved cancellation and failed qualification. One ordinary v3 policy per cohort saves a descriptive 64.95% on 1,925 test cases and 68.39% on 7,000 full-workload cases, versus 21.37% / 19.80% for the prior v2 policies rerun alongside it. Zero intended-cohort recall losses; timing controls fail the strict equivalence requirement. | [Verified comparison](../../experiments/broad-oracle-v1/results/REPORT.md), [accounting](../../experiments/broad-oracle-v1/results/accounting.json), [completed resume](../../experiments/broad-oracle-v1/RESUMED.json) |

The returned M5 archive and independent scheduler accounting remain the evidence
gate for the frozen development nominees. The completed oracle diagnostic does
not qualify those nominees or establish agent discovery, unseen-query benefit,
replicated latency benefit, or a certified latency ceiling. Native remains a valid
outcome. The historical three-request episode remains exhausted at $0.725544 and
is separate from the M4 ledger; the oracle studies made no provider calls.

See the [November 17–19 oracle log](#oracle-studies-and-broader-policy-language--november-1719-2026),
the [November 5–16 log additions](#experiment-log-update--november-516-2026),
and the [benchmark roadmap](../../../research/fannagent-benchmark-evaluation-roadmap-2026-11-10.md)
for the longer narrative. Read dated later assessments when an older preparation
paragraph or roadmap header still describes a pending stage.

## Coverage and interpretation

The catalog enumerates persisted evidence under `trials/`, `agent/experiments/`,
`agent/runs/`, `agent/docs/verification/`,
`agent-pgvector/verification/`, `harness/results/`, `harness/docs/qualification/`,
`mini-bench/qualification/`, `research/`, and `release/`. It excludes dependency
installations, copied workspace/vendor/frozen/snapshot source trees, private
stores, caches and input/reference corpora. Case-insensitive report/status/receipt
markers and named verification/review/freeze metadata discover evidence. Flat
report, freeze and receipt collections, research documents and agent verification
receipts receive individual file records. Raw JSONL/CSV/log paths are linked
without reanalysis. The exact rules, roots and excluded directories are recorded
in JSON. Unit tests are supporting verification, not additional research trials;
an experiment definition or sealed kit does not establish execution. Journaled
subexperiments are listed under their parent saved run.

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
during this documentation refresh. The October 21 backup audit's failed
noninteractive SSH check remains historical; later oracle collection is recorded
separately below and does not recertify current remote retention.

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
| `reviews-frozen-proposals-timing-v1-runtime-fix-training-20261021T044854Z.l3c__b58` | All six blocks independently reproduced: 115,200 retained pairs, 100 vector groups. Two qualifiers; prespecified selection is `cons_S32_64_128_t002`: 12.690% activation and 13.545% reuse savings. Worst recall lower bound exactly meets −0.5 pp. Training feasibility only; subsequent confirmation is recorded below. A/B inconclusive. | [raw campaign](../../../trials/torch-reviews-results/reviews-frozen-proposals-timing-v1-runtime-fix-training-20261021T044854Z.l3c__b58/), [independent report](../../../trials/torch-reviews-results/reviews-frozen-proposals-timing-v1-runtime-fix-training-20261021T044854Z.l3c__b58-analysis/report.txt), [postrun record](../verification/frozen-proposals-timing-v1-runtime-fix-postrun.json) | [corrected recipe](../../../trials/torch-reviews-frozen-proposals-timing-v1-runtime-fix/README.md), exact saved-result reanalysis command below |
| `reviews-frozen-proposals-timing-v1-runtime-fix-confirmation-20261021T160807Z.n5yrz2mk` | All three blocks independently reproduced: 29,160 retained pairs, 60 held-out vector groups / 180 cases. Frozen `cons_S32_64_128_t002` saves 11.673% activation and 12.377% reuse, but fails recall overall, votes32 and votes108. Overall recall 99.500% to 98.944%; lower 95% delta bound −1.056 pp versus required ≥−0.500 pp. No qualifying candidate or fallback; A/B inconclusive. | [raw campaign](../../../trials/torch-reviews-results/reviews-frozen-proposals-timing-v1-runtime-fix-confirmation-20261021T160807Z.n5yrz2mk/), [independent report](../../../trials/torch-reviews-results/reviews-frozen-proposals-timing-v1-runtime-fix-confirmation-20261021T160807Z.n5yrz2mk-analysis/report.txt), [postrun record](../verification/frozen-proposals-timing-v1-runtime-fix-confirmation-postrun.json) | [corrected recipe](../../../trials/torch-reviews-frozen-proposals-timing-v1-runtime-fix/README.md), saved [diagnostic audit](../../../trials/torch-reviews-results/reviews-frozen-proposals-timing-v1-runtime-fix-confirmation-20261021T160807Z.n5yrz2mk-analysis/diagnostics.py) after sealed-source `run.sh analyze --campaign` |
| `reviews-four-condition-training-v1-20261022T032823Z.qx3frkhp` | Five allocations and nested fits independently reproduced: 46,800 retained timing pairs, 100 learning vectors, 4,698 acquired stop outcomes, zero model/confirmation calls. All 20 outer-fold policies continue after every inner candidate fails the development recall reserve. Native recall preserved; all four procedures add latency and none qualifies. Sparse hindsight oracle saves 59.581% activation / 59.834% reuse with zero recall loss. Final criteria unchanged; original generation A/B inconclusive. | [raw campaign](../../../trials/torch-reviews-results/reviews-four-condition-training-v1-20261022T032823Z.qx3frkhp/), [independent report](../../../trials/torch-reviews-results/reviews-four-condition-training-v1-20261022T032823Z.qx3frkhp-analysis/report.txt), [postrun record](../verification/four-condition-training-v1-postrun.json) | [protocol](../../experiments/four-condition-training-v1/README.md), sealed local `report.py`, [diagnostics](../../../trials/torch-reviews-results/reviews-four-condition-training-v1-20261022T032823Z.qx3frkhp-analysis/diagnostics.py) |
| `offline-first-stop-fitter-v1-20261022` | Offline comparison of CART and whole-query first-stop tree search on existing 100 learning vectors. Original CART exactly reproduced; 320 new fits / 2,922,482 candidate scores; 16 tests and shared-interpreter audit pass. Positive proxies increase from 51/80 to 63/80 assessments, but both methods fail the development reserve in every assessment and continue in all 20 outer folds. No new model/backend calls; latency of new policies unmeasured. Final recall unchanged; original generation A/B inconclusive. | [results](../../../trials/torch-reviews-results/offline-first-stop-fitter-v1-20261022/), [report](../../../trials/torch-reviews-results/offline-first-stop-fitter-v1-20261022/report.txt), [postrun record](../verification/offline-first-stop-fitter-v1-postrun.json) | [protocol and reproduction command](../../experiments/offline-first-stop-fitter-v1/README.md), [saved-policy audit](../../../trials/torch-reviews-results/offline-first-stop-fitter-v1-20261022/validation/check_results.py) |
| `reviews-feature-data-ablation-v1-20261022T154122Z.duo0d70y` | Four initial allocations and all 16 fits independently reproduced: 200 development vectors, 9,390 stop proofs, 21,180 retained acquisition pairs, 77,172 backend searches, zero model calls. Static-160/risk1280 preserves all calibration recalls but has an unfavorable activation proxy; the other 15 candidates fail votes108. No joint pass; no common evaluation or timing allocation runs. Final criteria unchanged; original generation A/B inconclusive. | [raw campaign](../../../trials/torch-reviews-results/reviews-feature-data-ablation-v1-20261022T154122Z.duo0d70y/), [local interpretation](../../../trials/torch-reviews-results/reviews-feature-data-ablation-v1-20261022T154122Z.duo0d70y-analysis/interpretation.txt), [postrun record](../verification/feature-data-ablation-v1-postrun.json) | [protocol](../../experiments/feature-data-ablation-v1/README.md), [local raw reconstruction](../../../trials/torch-reviews-results/reviews-feature-data-ablation-v1-20261022T154122Z.duo0d70y-analysis/reproduce.py), [diagnostics](../../../trials/torch-reviews-results/reviews-feature-data-ablation-v1-20261022T154122Z.duo0d70y-analysis/diagnostics.py) |

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

### Archived October 21 campaign reanalysis

The following is the historical October 21 recipe, rather than the latest study.
Refreshing this index did not execute it or reopen confirmation data:

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
The selected-policy confirmation has failed and consumed the original split.
The completed [four-condition training study](../../experiments/four-condition-training-v1/README.md)
used zero further model calls and excluded that confirmation from training.
All four procedures abstain from stopping and fail latency qualification.
Its results do not select a deployable policy; any later optimized policy
requires fresh independent confirmation.

## Selective agent with measured feedback

The separately versioned [selective-agent-v1](../../experiments/selective-agent-v1/README.md)
implements one fresh agent episode with a $10 independent budget, up to three
initial selective policies, one measured-feedback response, at most one revision,
and gated one-shot confirmation on the 60 previously unexecuted development
vectors. All three query types remain in evaluation, including real native
bypasses. Final recall and activation/reuse gates remain unchanged. The original
generation A/B remains inconclusive with zero complete pairs. See its
[commands](../../experiments/selective-agent-v1/COMMANDS.txt); implementation,
validation, model spending and launch state are recorded separately in the
selective-agent-v1 verification receipt.

## Execution cost attribution v1

The [first performance-roadmap experiment](../../experiments/execution-cost-attribution-v1/README.md)
was implemented and packaged with [its frozen design](../../experiments/execution-cost-attribution-v1/DESIGN.md)
and [implementation verification](../verification/execution-cost-attribution-v1-implementation.json).
It reuses the sealed selective pilot's policy, adapter/core, x86 module and physical
index. Three serial allocations first measure unprofiled native/candidate/continue/
routed-native controls, then separately profile preparation and query execution on
60 development vectors. The ceiling is 83,763 backend/reference searches, zero
provider calls and zero confirmation queries. Sixteen local simulation/integrity
tests and lint passed before dispatch; that state remains preserved in the
implementation receipt.

The user subsequently completed campaign
`reviews-execution-cost-v1-20261023T044408Z.a08qpwdi`, created October 23, 2026
at 04:44:08 UTC (00:44:08 America/New_York), using jobs 20686461–20686463.
All three blocks and exactly 83,763 searches completed. The
[postrun receipt](../verification/execution-cost-attribution-v1-postrun.json)
records passing sealed local verification and remote/local numerical parity.
The frozen candidate is 22.799% slower on activation and 6.347% faster on reuse;
routed-native is 22.898% and 2.105% slower respectively. Diagnostic profiles and
frozen source identify repeated profile identity construction, pre-cache
validation/copying/serialization, and query normalization. Server/transport wait
remains unresolved by Python profiling. G1 passes as an attribution gate; the
next bounded proposal is owned prepared-policy state, with prospective cost
limits and full qualification/measurement still required.

See the [detailed interpretation](../../../research/fannagent-execution-cost-attribution-v1-results-2026-10-23.md)
and [updated roadmap](../../../research/fannagent-performance-research-roadmap-2026-10-22.md).
The receipt links the complete raw campaign, recomputed reports and identities;
the experiment runbook documents local data-only reproduction. Provider calls
and confirmation queries remain zero. No candidate selection, execution
optimization, independent confirmation or serving acceptance occurred; the
earlier selective episode remains closed with abstention. Do not resubmit this
completed campaign.

## Prepared-policy lifecycle v1 (P2a)

[NEXT-EXEC-01](../../experiments/prepared-policy-lifecycle-v1/README.md)
implements one experimental session-owned prepared-policy handle, following the
verified attribution above. The original complete composite admission remains
charged; the first backend preparation resolves lazily at the original timed
expression, followed by handle reuse. Bypass, SQL, query normalization, native
module and policies remain unchanged. A local AST comparison constrains the
copied backend execution body to its single preparation-expression change.

At the October 23, 2026 pre-dispatch snapshot, 31 local correctness/simulation/integrity checks passed,
including real query/numeric rejection and deterministic protocol-stub execution
of both original/new SQL bodies. Lint/format, module/shell syntax, package and
archive verification also pass. These are local checks, not native timing or
target-architecture qualification. The
[implementation receipt](../verification/prepared-policy-lifecycle-v1-implementation.json)
records source/package/archive identities and zero remote execution at that snapshot.

The [frozen contract](../../experiments/prepared-policy-lifecycle-v1/DESIGN.md)
compares original and owned execution for each of the same three policy/control
arms. Its cap is three serial four-CPU/32-GiB/two-hour allocations, 143,163
searches and 12,420 separately counted eviction installs. All 200 exposed
development vectors / 600 cases remain, followed by separately profiled timing
on 30 vectors. Candidate reuse must establish at least 0.10 ms and 2% saving
against original execution, with predeclared activation/control/filter and
outer-time protections. This engineering decision is separate from policy
confirmation and canonical acceptance.

The user completed that single declared comparison on Torch. Campaign
`reviews-prepared-policy-v1-20261023T161756Z.8uq_covr` completed all three serial
jobs (`20736459`, `20736460`, `20736461`), consuming 143,163 searches and 12,420
separately counted eviction installs. Recorded internal elapsed time totals
5,188.18 seconds (86.47 minutes); this is not a Slurm billing record. No model
call, confirmation query, policy selection or canonical acceptance occurred.
The archive checksum, protected inputs, all 42 raw-file hashes, strict output
and stopping parity, and locally recomputed report passed verification.

Candidate reuse improved directly over original policy execution by 0.286 ms
(5.171%; 95% gap interval −0.330 to −0.242 ms), with a saving in every block.
Matched-continue reuse improved by 4.192%. Overall candidate activation showed
no clear improvement. The complete engineering gate **failed** because several
activation/control/filter confidence bounds exceeded the frozen nonregression
margins, including a routed-native reuse outer-time bound. The recorded verdict
is `revise_or_retain_original`; the original adopted execution remains the
baseline. These findings do not authorize another campaign or production adoption.

The [postrun receipt](../verification/prepared-policy-lifecycle-v1-postrun.json)
and [results analysis](../../../research/fannagent-prepared-policy-lifecycle-v1-results-2026-10-23.md)
record the evidence and limitations. The
[roadmap](../../../research/fannagent-performance-research-roadmap-2026-10-22.md)
closes `NEXT-EXEC-01` and proposes `NEXT-ADMIT-01`: isolate repeated admission
profile-identity work, with prospective A/A controls and per-filter precision
planning before any new implementation or run. Production sources and sealed
campaigns remain unchanged; the original
[run commands](../../../trials/torch-reviews-prepared-policy-lifecycle-v1/COMMANDS.txt)
are retained as historical instructions, not a request to resubmit.

## Admission profile identity v1 (P2b)

[NEXT-ADMIT-01](../../experiments/admission-profile-identity-v1/README.md)
implements one privately owned immutable semantic runtime-profile identity per
session admission. Deep copy, the single original fingerprint, binding checks
and all original policy validation remain charged to activation. The copied
composite validator changes only its explicit profile binding, checked by AST;
P2b inherits the frozen P2a query body and lazy handle. Original/P2a session and
backend reference files, policies, SQL, normalization, native module and index
remain unchanged.

As of October 23, 2026, **45 local correctness/simulation/integrity checks pass**,
including a complete four-block simulated driver/report, ownership/mutation and
numeric/depth/feature rejection, cold accounting, lifecycle invalidation, actual
Python SQL-body protocol stubs, close-on-error behavior, balanced ordering,
physical-order verification and A/A decision boundaries. Lint/format, Python and
Bash/zsh syntax, sealed package/archive integrity and a mock authentication
failure check also pass. These do not establish native qualification or speed.
The [implementation receipt](../verification/admission-profile-identity-v1-implementation.json)
records source/package/archive identities and zero native execution at the pre-dispatch snapshot.

The [frozen contract](../../experiments/admission-profile-identity-v1/DESIGN.md)
compares original, frozen P2a and two independently constructed identical P2b
labels for each unchanged candidate, matched-continue and routed-native arm.
Four Williams-balanced serial blocks retain all 200 exposed vectors/600 cases,
with a separate 30-vector diagnostic pass. The
[precision review](../../experiments/admission-profile-identity-v1/PRECISION.md)
uses P2a's existing data and makes no power guarantee. A/A primary/outer/log-ratio
intervals must fit the declared equivalence bands in every pooled
arm/regime/filter/overall cell. Failed equivalence produces
`measurement_inconclusive`; A/A differences never correct treatment gaps.
Incremental activation versus P2a, combined reuse versus original, every
nonregression bound and original quality requirements remain binding.

The frozen cap was **four serial 4-CPU/32-GiB/two-hour allocations**, 370,884
searches and 33,120 separately counted eviction installations. All four jobs
(`20753185`, `20753186`, `20753187`, `20753188`) completed in campaign
`reviews-admission-profile-v1-20261023T193304Z.a2mfz4a0`. The earlier
[user-pasted status](../verification/admission-profile-identity-v1-torch-status.json)
is preserved as a historical snapshot. The completed archive has now passed
checksum/member validation, all 56 locked raw-file hashes and a fresh sealed
local reconstruction; all output/stop/identity/mechanism checks pass. The
[postrun receipt](../verification/admission-profile-identity-v1-postrun.json)
records actual consumption, complete direct comparisons and the frozen verdict.

Candidate activation is **2.109% faster than concurrent original execution and
2.102% faster than P2a** (approximately 0.202 ms); reuse is **4.054% faster than
original**, with no established extra reuse benefit versus P2a. Constructor
preparation falls from P2a's 1.477747 to 1.280951 ms. Outputs, recall and actual
stopping behavior match across versions. All 144 nonregression endpoints pass.

The engineering verdict is nevertheless **`measurement_inconclusive`**. Six
activation/filter A/A cells fail eleven absolute equivalence endpoints, although
all overall/reuse A/A cells and relative A/A bounds pass. The incremental
activation relative-saving lower bound is 1.943%, below the required 2%.
Preserve both failures; do not adopt, adjust margins, correct by A/A subtraction
or rerun this consumed allowance. The
[detailed analysis](../../../research/fannagent-admission-profile-identity-v1-results-2026-10-23.md)
explains the positive signal and limits. A
[descriptive audit](../../../research/fannagent-admission-profile-identity-v1-order-audit-2026-10-23.json)
of existing rows finds order-associated activation variation and a profile-copy
tradeoff; neither identifies a causal correction or qualifies a future gain.

Original execution remains the adopted baseline. The
[roadmap](../../../research/fannagent-performance-research-roadmap-2026-10-22.md)
proposes at most one separately declared activation timing calibration
(`NEXT-CAL-01`) before further optimization, or an explicit retain-original
redirect to bounded P3 if calibration is unjustified/inconclusive. No new budget,
implementation or run is assigned. No provider call, confirmation query, policy
selection, production adoption or deployment occurred.

The [exact commands](../../../trials/torch-reviews-admission-profile-identity-v1/COMMANDS.txt)
and [Mac transfer helper](../../../trials/torch-reviews-admission-profile-identity-v1/transfer.sh)
remain historical instructions for this completed campaign; do not resubmit.

## Activation timing calibration v1 (P2c)

[NEXT-CAL-01](../../experiments/activation-timing-calibration-v1/README.md)
implements the separately declared calibration following P2b. Policies and four
execution/validation reference files remain byte-identical, as does the frozen
P2b engineering gate logic. Ten cells cover identical original/P2a/P2b paths for
all three semantic arms, plus plain native, with twenty A/B labels.

Each fresh slot resets policy state and runs exactly two recorded ordinary-native
conditioning calls before constructing its measured session. Full admission,
snapshot/copy/hash, lazy preparation, compilation, installation and first
execution remain timed. The endpoint explicitly assumes conditioned shared
query/index state; it is not a cold-index/novel-query/fresh-connection result or a
retroactive P2b qualification. Conditioning/reset costs are separately reported
and resource-counted. Adjacent A/B then B/A rounds (ABBA/BAAB) are complemented
across two serial blocks, with all 200 exposed vectors/600 cases retained.

The [contract](../../experiments/activation-timing-calibration-v1/DESIGN.md)
requires all native/original/P2a/P2b A/A cells, both regimes, every filter and
overall to meet the original ±0.10 ms / ±log(1.02) bounds: 80 cells/240 endpoints.
Direct contrasts reuse the exact frozen P2b engineering gate in this new scope,
without native-gap or A/A subtraction. No profiler, changed policy, outlier
exclusion or threshold relaxation is introduced. Both gates passing would still
require operating-scope/lifecycle review before adoption.

**44 local correctness/simulation/integrity checks pass**, including the full
two-block driver/replay, phase/order/cold-charge tampering rejection, original
numeric/depth/ownership/invalidation behavior, real Python SQL-body stubs,
mandatory native/original controls, vector clustering, scheduler uncertainty
and safe ingestion. The same checks pass on the sealed package. Lint/format,
Python/Bash/zsh syntax, all 600-case crossover checks, archive integrity and mock
authentication-failure handling also pass. These are not native performance
measurements. The [implementation receipt](../verification/activation-timing-calibration-v1-implementation.json)
records pins, checks and zero native execution.

**Verified October 24, 2026:** campaign
`reviews-activation-calibration-v1-20261024T025706Z.c8557262` completes jobs
`20778104` and `20778105`. Actual use equals the finite two-block search ceiling:
**592,242 searches**, including **96,000 conditioning executions**, 192,000
retained pairs, 48,000 discarded warmup pairs and 48,000 separate eviction
installations. Provider/confirmation calls remain zero. Both blocks finish
within deadline; the campaign allowance is consumed.

The [postrun receipt](../verification/activation-timing-calibration-v1-postrun.json)
records checksum verification, all 41 archive members matching extraction,
26 locked raw hashes, protected inputs/runtime/index identities, output/actual
stop parity, phase/order/conditioning coverage and full admission charges.
Fresh sealed reconstruction matches the earlier local analysis exactly; five
remote floating values differ by at most 3.47e-18, below 1e-12. The compact timing
and calibration reports reproduce byte-for-byte. Returned code was not executed.

**Calibration passes:** all 80 native/original/P2a/P2b A/A cells and 240 interval
checks meet the fixed primary/outer ±0.10 ms and relative ±log(1.02) bounds.
All 144 practical nonregression checks and development quality protections also
pass. This is a result in the declared conditioned scope; P2b's old
`measurement_inconclusive` verdict remains unchanged.

Concurrent candidate P2b activation saves **2.205% versus original** and
**1.884% versus P2a**. Reuse saves **4.711% versus original**, with no established
additional benefit versus P2a (gap +0.005202 ms, interval [-0.005152, +0.015782]).
The unchanged engineering gate is **`revise_or_retain_original`**: incremental
activation's relative lower saving bound is **1.751%, below 2%**. Absolute and
outer activation saving lower bounds exceed 0.10 ms. A/A precision is now
adequate for the declared margins, but the practical improvement target fails.

The [detailed analysis](../../../research/fannagent-activation-timing-calibration-v1-results-2026-10-24.md)
and [full reconstructed data](../../../trials/torch-reviews-activation-timing-calibration-v1/analysis-review/reviews-activation-calibration-v1-20261024T025706Z.c8557262/performance.json)
retain every filter/block/control interval, order diagnostic and resource cost.
P2b constructor preparation remains 1.392070 ms; its activation is still
36.876–37.036% slower than its own ordinary-native reference. Reuse is
8.298–8.300% faster than native. Conditioning outer time totals 563.091 seconds,
and reset/conditioning/bookkeeping wall time totals 651.629 seconds; these
overlap and are excluded from the explicitly conditioned service endpoint.
They do not establish a cold-index or per-request deployment gain.

**Decision:** retain original execution and close the finite P2 sequence without
optimized-path qualification. G2's branch decision is complete; M1/M2/M3 remain
unestablished. Next is **P3a / NEXT-INFO-01**, an offline contract and inventory
of existing permitted development trajectories, qualified decision-time
features, actual-stop outcomes, missing coverage, vector exposure and original
execution-cost identities. A coverage gate must precede fitting or a separately
contracted targeted acquisition. No Torch command is needed now; no extra block,
retuned conditioning, threshold change or automatic P2d optimization follows.

The [exact commands](../../../trials/torch-reviews-activation-timing-calibration-v1/COMMANDS.txt)
and [Mac transfer helper](../../../trials/torch-reviews-activation-timing-calibration-v1/transfer.sh)
remain historical run artifacts. Preserve bindings/reservations and do not
resubmit P2b or P2c. The
[roadmap](../../../research/fannagent-performance-research-roadmap-2026-10-22.md)
records completed gates and the revised P3a coverage-first critical path.

## Existing stopping evidence audit (P3a)

**NEXT-INFO-01, completed October 24, 2026:** the
[frozen data-only contract](../../../research/fannagent-p3a-evidence-audit-2026-10-24/contract.json)
audits the existing 200 exposed development vectors / 600 cases and their
overlapping older 100-vector subset. No fitting, policy search/simulation,
database/provider calls, Torch jobs or protected query-value access occurs.
Original execution and every earlier P2 verdict remain unchanged.

The [audit receipt](../verification/p3a-evidence-audit-v1.json) and
[complete saved-data audit](../../../research/fannagent-p3a-evidence-audit-2026-10-24/audit.json)
record 620 source/input files verified before/after, sealed identities, exact
stop/output/feature-prefix joins and reconstructed acquisition labels/cost
proxies. The older source uses a different binary/profile/registry: matching
outcomes on its 100-vector subset do not license timing pooling. Four audit
decoder assumptions were corrected with versions/logs preserved; the receipt
also records that cumulative compliance with the self-imposed local I/O ceiling
is not established. No scientific inputs or thresholds changed.

**Restricted coverage gate passes:** static23 and progress34 each have all
**4,695 reachable actual stopping outcomes** on ordinal checkpoints
1/2/4/8/16/32/64/128, plus 600 measured continue outcomes. All required qualified
features are available there; all 9,390 stop proofs and corresponding profile
outputs agree. Per profile, 105 nominal grid positions were not reached before
search ended; 30 measured early votes108 stops return incomplete top-10 and
remain explicit negative outcomes. The
[coverage matrix](../../../research/fannagent-p3a-evidence-audit-2026-10-24/coverage.csv)
preserves every filter/stage denominator.

**Remaining scopes need separate evidence if pursued:** current-binary Light19
has 1,074 directly executed stop cells out of 4,695, leaving 3,621 without direct
proofs and no complete compatible fixed-stop cost matrix. Each static/progress
profile has 90,411 observed off-grid states without actual stop outcomes.
Acquisition costs are fixed-stop proxies; any newly fitted policy's full
composite-session latency remains unmeasured. These gaps do not block the
supported static23/progress34 grid comparison.

The [feature diagnostics](../../../research/fannagent-p3a-evidence-audit-2026-10-24/feature-diagnostics.json)
find identical Light19 votes32/votes108 traces for all 200 vectors, despite
359 paired grid states with differing complete-recall-preservation labels.
Static23/progress34 expose the actual validated predicate threshold. Static
probe statistics remain constant in all 600 cases; qualified progress
observations change across checkpoints in all 600, with causal receipts
reconstructed. Predictive usefulness remains untested.

**Next: prepare P3b / NEXT-MODEL-01**, a finite matched-information
flexible-versus-shallow development modeling contract on static23/progress34 and
the measured grid. Preserve vector-group folds, invalid outcomes, complete
first-stop evaluation and prior exposure; no model has been fitted by this audit.
No targeted Torch acquisition is needed first, and no user command is needed
now. Final G3 family selection and M1/M2/M3 remain unestablished. The
[detailed P3a report](../../../research/fannagent-p3a-evidence-audit-2026-10-24.md)
and [roadmap](../../../research/fannagent-performance-research-roadmap-2026-10-22.md)
record the scoped decision and conditional acquisition branches.

## P3b — grouped stopping-model comparison (October 24, 2026)

**Complete; negative for the frozen procedures.** `NEXT-MODEL-01`, local run
`p3b-20261024-local-v1`, compares depth-three utility regression with a bounded
64-tree Extra Trees ensemble on the previously exposed 200 vectors / 600 cases,
within qualified static23/progress34 profiles and the measured eight-checkpoint
grid. The [contract](../../experiments/grouped-stop-modeling-v1/contract.json)
was frozen before fitting (SHA-256 `d50ccf6a7b41e7b7af79541c6b0f55cd87ef20acb4842636fb0da63125f1b5c7`).
Five outer and four inner vector-group folds separate fitting, pruning and
selection from held-out outcomes. No new native/database/provider/Torch or
protected-query/confirmation access occurs; production code is unchanged.

All twenty calibrated outer selections choose measured profile continue.
All 225 positive-proxy inner candidates fail recall; all 305 recall-passing
candidates have nonpositive proxies. The predeclared risk320/threshold0 ensemble
diagnostic stops 268 static / 216 progress cases, but both fail unfiltered
recall (lower 95% bounds −1.15 / −1.25 percentage points). Fixed-stop costs are
development proxies, not new learned-policy latency. The zero calibrated
flexible-minus-shallow contrast reflects identical continue actions, not a
capacity-equivalence result. Nothing is adopted; original execution and all
prior P2 verdicts remain unchanged.

Fourteen correctness checks passed, consuming twelve synthetic fits across
three test processes. The scientific run used 340/360 estimator fits, 235.661 s,
0.997 GiB peak RSS and 0.783 GiB metered reads, within its one-thread local cap.
The [postrun receipt](../verification/grouped-stop-modeling-v1-postrun.json)
binds sources, isolated dependencies, 99 input pins and 803 hashed output
artifacts. A [data-only independent replay](../../../trials/torch-reviews-grouped-stop-modeling-v1/runs/p3b-20261024-local-v1/verification-replay.json)
reconstructs all 560 inner assessments and 4,800 outer cases with zero refits;
reports match within 1e−12. The initial zero-fit bytecode-cache guard failure is
preserved with original sources/logs in the [preflight repair record](../../../trials/torch-reviews-grouped-stop-modeling-v1/preflight-repair.json).

The [results report](../../../research/fannagent-p3b-grouped-modeling-v1-results-2026-10-24.md),
[descriptive analysis](../../../research/fannagent-p3b-grouped-modeling-2026-10-24/analysis.json)
and [roadmap v1.11](../../../research/fannagent-performance-research-roadmap-2026-10-22.md)
record **G3 revise** and the proposed **P3c/NEXT-RISK-01**: one prospectively
bounded risk-separated objective comparison at fixed feature/action/capacity
scope. P3c is not implemented or run; a new frozen finite contract is required.
No Torch command is needed now. No family, independent confirmation, M1/M2/M3
or canonical serving acceptance is established. This entry supersedes the P3a
entry's historical “next P3b” status without altering its audit conclusions.

## P3c — risk-separated stopping-model comparison (October 24, 2026)

**Complete; no qualifying joint result.** `NEXT-RISK-01`, local run
`p3c-20261024-local-v1`, freezes risk-only tree partitions and separate savings
means within those same fitting leaves. P3b's features, tree counts/depths,
group support, five outer/four inner folds and measured checkpoints stay
matched. The [contract](../../experiments/risk-separated-stop-modeling-v1/contract.json)
SHA-256 is `92928bbca0ca8c1b0a4ac6962d3fe95aa083b96c14e9b49b4ea050c657ae99ae`.

Four of twenty ensemble cells select gates. Static/progress calibrated stops
are236/90 out of 600, with activation proxies −0.603150/−1.371480 ms. Static also
fails votes108's development recall reserve; progress passes recall but loses
both cost proxies. Shallow methods always continue. The fixed diagnostic
reduces P3b's observed11/10 loss cases to 1/1 and passes recall, but activation
proxies remain negative. These are exposed-development fixed-stop proxies,
not new serving timings or proof that original execution improved.

Sixteen checks use six synthetic fits. The scientific run uses exactly100 fits,
3,250 individual trees,102.377 s, 0.993 GiB RSS and 0.839 GiB metered reads.
The [postrun receipt](../verification/risk-separated-stop-modeling-v1-postrun.json)
binds 919 prior input/artifact files, ten source files and 323 core outputs. An
[independent data-only replay](../../../trials/torch-reviews-risk-separated-stop-modeling-v1/runs/p3c-20261024-local-v1/verification-replay.json)
reconstructs248,851 fitting-leaf risk/benefit values, all 980 inner candidates,
4,800 outer cases, baseline/control reports and paired contrasts within 1e−12,
without fitting. All scientific and verification runs pass; no prior evidence,
production code/environment or protected query values are modified/accessed.
There are zero new native/DB/provider/Torch/confirmation calls.

The [results report](../../../research/fannagent-p3c-risk-separated-modeling-v1-results-2026-10-24.md),
[analysis](../../../research/fannagent-p3c-risk-separated-modeling-2026-10-24/analysis.json)
and [roadmap v1.12](../../../research/fannagent-performance-research-roadmap-2026-10-22.md)
close P3c and bounded G3 negatively for these procedures. Original execution
remains adopted; no universal information ceiling or M1/M2/M3 claim follows.
Next recommended scope: **B1a/NEXT-SCOPE-01**, a read-only fixed-index
query-dependent search-effort feasibility/design audit before any experiment.
B1a is proposed, not implemented or run. No user/Torch commands are needed now.
This entry supersedes the P3b entry's historical “next P3c” status; prior results
and their failed/inconclusive gates remain unchanged.

## B1a — fixed-index search-effort feasibility audit (October 24, 2026)

**Complete; scoped engine feasibility passes.** `NEXT-SCOPE-01` is a read-only
source/API/query-input/timing/identity review. The pinned engine supports
query-time `hnsw.ef_search` without requiring an index rebuild. The current
strict query API has no effort field and the policy language supports only
stop/continue; a versioned experimental native-effort interface is needed.
Parsing actual predicates and `k` is available before ANN, but the600 exposed
cases provide only three contexts, not within-filter vector-difficulty labels.
Selector/validation/session/setting cost is unmeasured and must be charged.

The historical four-effort sweep uses index 6076/file hash `8c15a172…`; P3 uses
index 90f4/file hash `dbc14b09…`. Historical full-size320 uses the current graph
but an older runtime/profile. The old/current group inventories also differ.
These scopes cannot be spliced into a current multi-effort training/cost matrix;
ef 640 stopping prefixes are not ef 320 interventions. The historical sweep's
122 input hashes and six saved analysis-output hashes match the saved inventory.
No prior confidence intervals were recomputed or router selected.

The [audit report](../../../research/fannagent-b1a-search-effort-audit-2026-10-24.md),
[findings](../../../research/fannagent-b1a-search-effort-audit-2026-10-24/audit.json),
[source/input inventory](../../../research/fannagent-b1a-search-effort-audit-2026-10-24/input-and-source-inventory.json)
and [receipt](../verification/b1a-search-effort-audit-v1.json) record 324 unchanged
code/source files, scoped GB1 pass and zero code changes/tests/fits/simulations,
new native/DB/provider/Torch or protected-query access. Original execution,
P2/P3 verdicts and all milestone/acceptance boundaries remain unchanged.

Next: **B1b/NEXT-EFFORT-01**, freeze and prepare a native 320/640 interface and
matched current-index frontier with original 640 quality reference, full-path
original/wrapper and identical-path controls, setting-isolation qualification
and a finite resource contract. No router fitting before that gate. At most
eight predicate-context maps are a later conditional baseline. B1b is not
implemented or run; no user/Torch commands are needed now. The
[roadmap v1.13](../../../research/fannagent-performance-research-roadmap-2026-10-22.md)
supersedes P3c's historical “next B1a” status.

## B1b — native-effort frontier v1 (October24,2026)

**Implemented, locally verified and sealed; awaiting the user's Torch run.**
`NEXT-EFFORT-01` compares original study640, wrapped forced640, wrapped
forced320 and the separately identified source320 path on the current physical
index/module. The versioned experimental envelope and two immutable reader
bindings preserve the original API, SQL/execution method and all prior code.
No stopping policy, router fit, rebuild, provider or protected query is involved.

The [prospective contract](../../experiments/native-effort-frontier-v1/DESIGN.md)
freezes full outer activation/reuse costs (including both wrapped readers),
actual setting/plan/isolation/rollback qualification, exact truth and unchanged
640 quality reference, complementary ABBA/BAAB controls,64 A/A interval tests
and per-context/regime recall/overhead/net-benefit gates. Two serial allocations,
each4CPUs/32GiB/2hours, have a139,272-search total ceiling. Reuse-only support
cannot qualify activation or deployment; no supported frontier means explicit
inconclusive/negative closure, not automatic extra collection.

Seventeen source and seventeen sealed-package local tests pass, including complete
600-case mock acquisition, two-block raw serialization/replay and rejection of a
rehashed altered timer. Lint/format, shell syntax, package/checksum and all147
archive members pass. All324 previous code/source hashes,29 consulted prior
inputs and128 historical raw/saved outputs match. These are correctness checks;
no new native/DB/provider/Torch experiment or learned model ran.

The [receipt](../verification/native-effort-frontier-v1-implementation.json),
[implementation guide](../../experiments/native-effort-frontier-v1/README.md),
[sealed manifest](../../../trials/torch-reviews-native-effort-frontier-v1/torch-native-effort-frontier-v1/manifest.json)
and [commands](../../../trials/torch-reviews-native-effort-frontier-v1/COMMANDS.txt)
record the package and next actions. The Mac transfer helper uses interactive
MFA and a completed binding file before JSON parsing. The user uploads/submits
once, monitors, collects and downloads for trusted local data-only replay.
Bindings/reservations persist after failures; do not resubmit automatically.

[Roadmap v1.14](../../../research/fannagent-performance-research-roadmap-2026-10-22.md)
marks G0-B1b local readiness passed and GB1b native/control/frontier unassessed.
Original execution, all P2/P3 findings and M1/M2/M3 remain unchanged. B1c awaits
verified frontier evidence and a separate grouped-routing contract. This entry
supersedes B1a's historical “B1b not implemented/no commands” status.

## B1b — completed native-effort comparison and recovered ingest (October 25, 2026)

**Complete and locally verified; no qualifying context or regime.** The user
completed jobs `20845494`/`20845495`, campaign
`reviews-native-effort-v1-20261025T014743Z.p_kspq5v`, with exactly139,272 searches
on the unchanged physical index/module. Native setting/plan/isolation/error
qualification, complete top10 outputs, exact/native references and source
preservation all pass. There are200 exposed vectors/600 cases,76,800 retained
executions,19,200 warmups and38,400 conditioning calls; zero providers/fits or
confirmation queries.

Download and checksum passed. The original ingest rejected only the campaign
name: the remote container reported `results`, while the Mac used the full
extracted campaign name. The separate
[recovery helper](../../experiments/native-effort-frontier-v1/recover_campaign_identity.py)
verifies all40 archive/extracted files,146 sealed package files, submission/job
identity,26 locked raw files and a fresh unchanged sealed analyzer. Its proof
permits exactly one copied campaign-label reconciliation; every other discrete
and gate value matches, with three floating differences no larger than4.34e−19
under the original1e−12 tolerance. Raw data, sealed code and the failed first
local output are preserved. Four recovery tests plus lint/format pass.

Reuse A/A passes32/32 intervals; activation passes2/32. Wrapped320 reuse is
40.540% faster (5.519471→3.281898ms), but recall falls99.0333%→98.2333%, and
every context fails the−0.25pp development reserve. Forced640 reuse adds0.206ms
and fails overhead protection in every context. Preserve the frozen aggregate
`measurement_inconclusive` verdict while recording these independent reuse
quality/control failures. Original execution remains adopted; B1c stays deferred.

The [postrun receipt](../verification/native-effort-frontier-v1-postrun.json),
[results report](../../../research/fannagent-native-effort-frontier-v1-results-2026-10-25.md),
[fresh replay](../../../trials/torch-reviews-native-effort-frontier-v1/analysis-review/reviews-native-effort-v1-20261025T014743Z.p_kspq5v/performance.json),
[identity/recovery verification](../../../trials/torch-reviews-native-effort-frontier-v1/analysis-review/reviews-native-effort-v1-20261025T014743Z.p_kspq5v/verification.json)
and [roadmap v1.15](../../../research/fannagent-performance-research-roadmap-2026-10-22.md)
record the result and next proposed read-only effort/interface revision review.
No user commands, rerun, extra effort/block, router fit or protected-data access
are needed or automatically authorized. This entry supersedes the earlier B1b
preparation/awaiting-Torch status. The naming error did not change the evidence.

## B1-review — completed source/evidence audit and B1b2 design (October25,2026)

**Read-only review complete; fixed480 comparison is design-only.**
`NEXT-EFFORT-REVIEW-01` audits the existing B1b admission, vector validation,
ownership and timer boundaries. The custom eager two-reader session performs
34 explicit startup SQL calls versus17 for an ordinary reader. The same matched
forced640 reuse gap is0.206235ms, comprising0.081905ms inside the SQL timer and
0.124329ms outside it; these are broad categories, not isolated function costs.
All685 inventoried existing files remain preserved, including146 sealed B1b
files,40 returned files and prior324 code/source,29 inputs and128 historical
outputs. No execution code, test, native/DB/provider/Torch experiment, fit,
policy simulation or protected-query-value access occurred in this review.

The [completed review](../../../research/fannagent-effort-interface-review-2026-10-25.md),
[audit](../../../research/fannagent-effort-interface-review-2026-10-25/audit.json),
[receipt](../verification/effort-interface-review-v1.json) and
[roadmap v1.16](../../../research/fannagent-performance-research-roadmap-2026-10-22.md)
recommend **B1b2 / NEXT-EFFORT-MID-01**, one fixed480 versus study640 comparison
on ordinary native readers, retaining the same physical index/module and
exposed200 vectors/600 cases.480 is an unmeasured midpoint probe, not a predicted
qualifier. The [prospective contract](../../../research/fannagent-native-effort-midpoint-v1-design-2026-10-25.md)
requires implementation/local checks/seal first, native conformance and a fresh
quality screen. Stop by1,830 searches for failed quality; only a pass unlocks
two temporal warm blocks, fresh16-interval A/A and0.10ms/2% benefit gates.
Proposed ceiling: one4CPU/32GiB/two-hour allocation and59,430 searches total;
zero providers/fits/new vectors/protected values/confirmation.

Warm persistent-reader results cannot qualify activation or deployment. Startup,
first-use, conditioning, audit and cleanup stay charged separately. No new
validator, native-direct path, pooling dependency, router or effort ladder is
included. B1b's aggregate `measurement_inconclusive` and all prior verdicts remain
unchanged; original execution retained, B1c deferred, M1/M2/M3 unestablished.
Next is isolated implementation/local readiness and exact sealed commands.
No B1b2 package exists and no user/Torch commands are needed now. This entry
supersedes only the prior “next read-only review” action.

## B1b2 — fixed native480 midpoint comparison (October25,2026)

**Implemented, locally verified and sealed; awaiting the user's single Torch job.**
`NEXT-EFFORT-MID-01` preserves the [frozen design](../../../research/fannagent-native-effort-midpoint-v1-design-2026-10-25.md),
original native methods/scorer, physical index/module and same200 exposed vectors/600 cases.
One private fixed-effort reader per arm replaces B1b's dynamic two-reader question;
there is no new public API, stopping policy, router, validator/direct-native optimization,
provider or protected-data access. Startup/shared admission/first-use/conditioning/audit/cleanup
remain separately charged; primary timing is warm full outer execution only.

Thirty conformance searches and1,800 fresh exact/640/480 references come first.
Failed quality closes normally at1,830 searches and creates no timing workload.
Only passing quality permits two complementary temporal blocks inside one4CPU/32GiB/two-hour
allocation (6,600-second work deadline), with a59,430-search total ceiling,14 reader
admissions/five live readers and fresh16-interval A/A/0.10ms/2% benefit gates.
Warm-only support cannot establish activation, serving acceptance or M1/M2/M3.

Twenty-two source and twenty-two sealed local correctness checks pass: complete600-case
fake acquisition/raw replay, early quality stop, stale/immutable ownership, preserved inherited
native methods, strict query admission, guard/error recovery, rehashed timer/coverage tamper,
provider import rejection and quality-negative collect/archive/checksum/replay.
Submission-derived identity gives identical reports through a `/results` alias; unrelated
metadata/scientific parity differences still fail. All tests use fake connections/results and
synthetic clocks. No native/DB/provider/Torch experiment or scientific fit ran.

The package contains150 manifest files/151 archive members; every member's bytes,
lint/format and shell syntax pass. Manifest `b7ad5be746bfa26bcaf5fbd381b0523c518f3872bb8011d8d00331b399c34bc1`;
archive `fbd7ac0654bb9ff99f6add7011127caf01c008cd08fb142abe56783ea94e6185` (14,831,467 bytes).
All691 prior source/evidence hashes match; previous packages, returns, verdicts and the user's
preexisting proposal edits are preserved.

See the [guide](../../experiments/native-effort-midpoint-v1/README.md),
[receipt](../verification/native-effort-midpoint-v1-implementation.json),
[manifest](../../../trials/torch-reviews-native-effort-midpoint-v1/torch-native-effort-midpoint-v1/manifest.json),
[local check records](../../../trials/torch-reviews-native-effort-midpoint-v1/local-checks/),
[exact commands](../../../trials/torch-reviews-native-effort-midpoint-v1/COMMANDS.txt)
and [roadmap v1.17](../../../research/fannagent-performance-research-roadmap-2026-10-22.md).
Next: Mac upload; once-only Torch submit; status/collect; Mac download and sealed data-only replay.
A quality-negative run is still collected. Preserve failed/unknown reservations; do not resubmit.
This entry supersedes the earlier design-only/no-commands status, without altering B1b's
aggregate measurement-inconclusive/no-qualifier verdict. Original execution retained, B1c deferred.

## B1b2 — completed midpoint quality screen (October25,2026)

**Complete and verified; `closed_negative_quality`.** Campaign
`reviews-native-midpoint-v1-20261025T172357Z.ybpfkkki`, job 20898557/task 0,
ran 30 conformance+1,800 reference searches and correctly stopped at 1,830.
Native conformance and all 95% absolute mean-recall floors pass. The frozen−0.25 pp
relative development reserve fails overall, votes32 and votes108: lower 95% bounds
−0.3333,−0.3500 and −0.6500 pp, shortfalls0.0833,0.1000 and 0.4000 pp.
Unfiltered passes at −0.1500 pp lower bound. The looser−0.50 pp diagnostic also
fails votes108 by 0.15 pp and cannot replace development/confirmation gates.

No temporal timing blocks, retained executions, conditioning or warmups ran;
A/A and benefit are **not assessed**, and no 480 speed improvement is established.
Eleven extra missed true neighbors versus 640 occur across 11 cases/nine vectors;
seven are votes108. Matching all 600 query/exact/640 outputs and current index/module
identities allows descriptive comparison with prior 320:480 recovers 37 true neighbors,
+0.6167 pp recall overall, but still fails the 640-relative contract.

All 24 returned members/15 locked raw files and 150 sealed package files/151 package
archive members verify. Fresh unchanged sealed replay is byte-identical to remote
and download-helper reports. Independent saved-ID arithmetic matches all 1,200 current
recalls; all 888 inventoried immutable files, including691 prior files/12 implementation
sources, remain preserved. The previously recorded outer transport-helper recovery is
explicitly reconciled; sealed/scientific code is unchanged. This review ran no new
experiment, fit, DB/native/Torch/provider call or protected-query access.

See the [result report](../../../research/fannagent-native-effort-midpoint-v1-results-2026-10-25.md),
[post-run receipt](../verification/native-effort-midpoint-v1-postrun.json),
[fresh verification](../../../trials/torch-reviews-native-effort-midpoint-v1/analysis-review/reviews-native-midpoint-v1-20261025T172357Z.ybpfkkki/verification.json)
and [roadmap v1.18](../../../research/fannagent-performance-research-roadmap-2026-10-22.md).
Original execution retained; B1b's aggregate measurement-inconclusive and all prior
verdicts remain unchanged; B1c deferred; M1/M2/M3 unestablished. Proposed next:
**B2a/NEXT-PLAN-SCOPE-01**, read-only plan/filter/index and identity/input-cost feasibility
review before any new finite comparison. No automatic560/600 ladder, subset router,
extra block, margin change or protected entitlement. **No user/Torch commands now.**
This entry supersedes the preceding awaiting-Torch status, not the frozen contract.

## B2a — completed plan/filter/index scope audit (October25,2026)

**Complete; GB2a passes scoped source feasibility, GO for a B2b design only.**
`NEXT-PLAN-SCOPE-01` reads existing source/plans/settings/identities and exposed
request metadata. The user named the already completed B1a; the stated assumption
was to handle this next read-only B2a. Original B1a and prior verdicts are preserved.

The loaded exact-reference path removes LIMIT, disables index scans and fetches
all eligible rows for authoritative truth/ties. It is not an exact top10 execution
benchmark. Native SQL retains LIMIT and can run on a separately bound exact
non-ANN plan while retaining current data/HNSW graph/module. This is technically
feasible but has no actual top10 correctness/control/economics qualification yet.
Saved480/640 plans establish HNSW plus executor filtering for six fixtures; their
estimated costs/rows are not actual latency or exact selectivity. The recipe
contains no scalar-index DDL, while saved selected-index metadata does not certify
a full current catalog; that remains a future native qualification requirement.

Partial/partitioned targets require new physical/backend scope. ACORN-1 expands
neighbors during search but documents an unpruned graph variant; the current
pruned graph is not proven compatible. The threshold feature is not predicate-aware
traversal. Offline eligible counts and evaluator/query IDs are not free router inputs.

All 349 source/code files and 907 immutable paths verify; zero code changes, tests,
fits, simulations, experiments, DB/native/Torch/provider calls or protected query
values. See the [audit report](../../../research/fannagent-b2a-plan-scope-audit-2026-10-25.md),
[machine findings](../../../research/fannagent-b2a-plan-scope-audit-2026-10-25/audit.json),
[preservation receipt](../verification/b2a-plan-scope-audit-v1.json)
and [roadmap v1.19](../../../research/fannagent-performance-research-roadmap-2026-10-22.md).

Next recommendation: **B2b/NEXT-EXACT-TOPK-01**, freeze one finite fixed exact-top10
versus unchanged native640 comparison before isolated implementation/check/seal.
Proposed ceiling only: one 4CPU/32GiB/two-hour allocation, 6,600-second work deadline,
<=50,000 backend attempts, same 200 exposed vectors/600 cases; zero fits/providers/
new or reserved vectors/confirmation. Exact schedule and gates are not frozen and
no budget/package/experiment is assigned by this audit. Native plan/semantic/quality,
fresh A/A and full-outer warm economics precede any routing design. No activation
or adoption qualification; original retained, B1c deferred, prior findings unchanged.
**No user/Torch commands now.** This supersedes the proposed-B2a next action only.

## B2b — exact-top10 versus native640 prepared (October25,2026)

**Frozen, implemented, locally checked and sealed; awaiting one user Torch job.**
`NEXT-EXACT-TOPK-01` preserves current data, graph, module, native statement/formatter/
execution/decoder and exhaustive full truth. Exact10 differs only by an owned effective
planner binding: seqscan on, index/index-only/bitmap off, with effort640 in both cells.
No router, index rebuild, JIT/parallel tuning, new transport/validator or protected query.

Thirty native qualifications plus1,800 fresh exact/native640/exact10 references come
before timing. Actual catalog, current/cached plans, exact tie-aware semantics and
native640/truth identity must qualify; semantic failures abort without a scientific
quality verdict. Complete valid quality failure stops at1,830. Only a pass opens two
temporal warm blocks within one4CPU/32GiB/two-hour job and6,600-second work deadline.
Maximum40,230 searches:19,200 retained,9,600 warmups,9,600 conditioning plus1,830
qualification/reference;14 admissions/5 live. Metadata SQL<=40,000,12,012 complete
plan packets and four stable catalog/statistics snapshots; phase costs stay visible.

All16 native/exact A/A intervals must meet unchanged equivalence bounds. Any of the
four prespecified reports called promising must meet.10ms/2% adjusted confidence-bound
savings and both-block direction, with Bonferroni over eight economic endpoints.
This is only a warm development frontier diagnostic; no selected route, activation,
adoption, independent confirmation or M1/M2/M3 follows. Original execution and all
prior findings remain unchanged; B1c deferred.

33 source and33 sealed local checks pass, including full600-case/two-block raw replay,
exact semantic stop/tie equivalence, injected quality stop, catalog/index/cache/tuning
rejection, rehashed primary/diagnostic timers, negative collection/archive/parity,
terminal failed-job collection and uncertain-dispatch refusal. All use fake readers,
results and synthetic clocks. An initial duplicate-catalog rejection defect was fixed;
the original failed-check log is preserved separately. No native experiment ran.

Package153 files/archive154 members,14,841,564 bytes. Manifest
`0124abaa1c472f19e0f778c633f7a4c1cc42f69430f83964a4a14cb90a56f55e`;
archive `01c6d272ac5de658e72c7c8e0bd5c2038a44fa5b5181d83039bf16c79f47b65d`.
Four staged transfer mocks and all912 prior immutable hashes pass; scientific source,
old packages/raw evidence/receipts and preexisting user proposal edits remain preserved.

See the [frozen design](../../../research/fannagent-exact-topk-v1-design-2026-10-25.md),
[guide](../../experiments/exact-topk-v1/README.md),
[receipt](../verification/exact-topk-v1-implementation.json),
[manifest](../../../trials/torch-reviews-exact-topk-v1/torch-exact-topk-v1/manifest.json),
[local check records](../../../trials/torch-reviews-exact-topk-v1/local-checks/)
and [exact commands](../../../trials/torch-reviews-exact-topk-v1/COMMANDS.txt).
Next: Mac upload until UPLOAD VERIFIED; once-only Torch checksum/extract/submit;
status/collect; Mac checksum/download/sealed data-only replay. Failed raw campaigns
remain collectable; preserve unknown/failed bindings, never resubmit automatically.
This supersedes only B2a's next-design action; native/quality/A/A/cost remain unassessed.

### B2b original preflight failure and separate catalog correction — October26,2026

User reports original campaign`reviews-exact-topk-v1-20261026T032153Z.9khasec1`,
job20941363_0 FAILED1:0 after6m17s, initial catalog guard, backend searches0,
empty operation counts and protected sources unchanged. Raw/accounting/cleanup are
not yet independently verified. No recall, timing or A/A result exists.

PostgreSQL17.11 serializes `oid` as JSON text; the original integer mock and check
reject the correct graph ID. A separate correction expects exact text`"264013"`,
retains all graph checks/SQL/scientific gates, saves rejected raw catalog details,
and identifies the initial catalog progress phase. Original source, sealed package,
archive, design, receipt and failed allowance remain unchanged.

The new source/sealed suites each pass43 checks; package155 files/156 archive members,
14,855,087 bytes; manifest6b2bb0f4a2797f01b70edcf256c518fe20f5cc00598d755ada04f216c9c6f842;
archiveb15b0b4b43708dbd891ae0b11a380591bdf2b192b731010398ba3fb7be75f95b.
All1,095 prior immutable hashes,127 frozen files and unchanged scientific constants
pass. A temporary PG16 scalar fixture could not initialize under sandbox shared-memory
restrictions and ran no SQL; no native/ANN/Torch experiment occurred.

**Current next action:** use the [collection-only commands](../../../trials/torch-reviews-exact-topk-v1-catalog-fix/RECOVER-FAILED-V1.txt).
Codex must verify original failed archive/submission/job/zero-search/cleanup/protected
and scheduler evidence before releasing corrected commands. The correction's controller
rejects missing or changed recovery prerequisites before reservation/sbatch. No old-v1
resubmission or automatic new allowance.

See [failure status](../verification/exact-topk-v1-torch-failure-2026-10-26.json),
[diagnosis](../../../research/fannagent-exact-topk-v1-catalog-failure-2026-10-26.md),
[frozen addendum](../../../research/fannagent-exact-topk-v1-catalog-fix-design-2026-10-26.md),
[correction guide](../../experiments/exact-topk-v1-catalog-fix/README.md),
[receipt](../verification/exact-topk-v1-catalog-fix-implementation.json),
[sealed manifest](../../../trials/torch-reviews-exact-topk-v1-catalog-fix/torch-exact-topk-v1-catalog-fix/manifest.json)
and [local check records](../../../trials/torch-reviews-exact-topk-v1-catalog-fix/local-checks/).
Earlier B2b readiness is historical. Corrected native/semantic/quality/A/A/economic
gates remain unassessed, and original execution remains adopted.

### B2b original failed raw verified; corrected handoff released — October26,2026

Original failed campaign`reviews-exact-topk-v1-20261026T032153Z.9khasec1` is now
independently verified:19 regular archive members/153,662 bytes, checksum
6773f88b361e01c5ed6fb7b4f15ba687329636bf62c1c18dff7fc5224312c25c;
submission/job20941363_0/FAILED1:0/zero-search failure match. One reader closed and
private DB stopped; captured protected reports are byte-identical across19 groups
and1,621 entries. Runtime/prepared/snapshot/origin/effective identities pass.

No quality, timing or A/A evidence exists. The old rejected full catalog is absent;
other actual catalog-field differences cannot be reconstructed. Original helper
validated the remote binding during download; binding bytes are not archived and
are rechecked by the corrected controller.6m17s remains the prior user's status
figure; downloaded scheduler accounting has no elapsed column.

R2/R3 are complete: the unchanged155-file/156-member correction seal is released
through [RUN-CORRECTED.txt](../../../trials/torch-reviews-exact-topk-v1-catalog-fix/RUN-CORRECTED.txt).
Previous43 source/43 sealed checks remain applicable;1,307 old inputs/artifacts,
both packages, original raw, frozen designs and historical receipts are unchanged.
This release supersedes only the earlier HOLD, not the original failed allowance.
No scientific code or package change and no new experiment/submission occurred.

Next: user corrected Mac upload and once-only Torch submit, then actual native
catalog/plan/semantic qualification, valid quality stop/go, conditional A/A/economics
and independently verified corrected return. Original execution stays adopted.

See [verification](../../../trials/torch-reviews-exact-topk-v1-catalog-fix/failed-v1-verification-2026-10-26/verification.json),
[verification source](../../../trials/torch-reviews-exact-topk-v1-catalog-fix/failed-v1-verification-2026-10-26/verify_return.py),
[completion/release receipt](../verification/exact-topk-v1-failure-postrun.json)
and [interpretation/limits](../../../research/fannagent-exact-topk-v1-failure-verification-2026-10-26.md).

### Corrected B2b deadline stop reported — October26,2026

User reports campaign`reviews-exact-topk-v1-catalog-fix-20261026T050859Z.jrmkwhuy`,
job20949301_0 FAILED1:0 after1:52:22, `Work deadline exhausted` during block1.
Application deadline is6,600s/110minutes within the two-hour allocation; SSH loss
was separate.26,247 budgeted attempts and12,208/19,200 retained observations are
reported. Entering timing indicates initial qualification/quality prefix pass in
source control flow; raw qualification, quality, terminal coverage and cleanup are
not yet independently verified. Full final audits and two-block A/A/economics did
not complete. No full performance or quality-negative verdict exists.

Both attempts remain consumed. Preserve data/packages/bindings/reservations and
use [collection-only commands](../../../trials/torch-reviews-exact-topk-v1-catalog-fix/deadline-stop-2026-10-26/COLLECT-ONLY.txt).
Expected failed/incomplete ingest preserves partial data. Codex then verifies the
archive, accounting, cleanup, prefix quality, journal coverage and actual phase
costs before deciding any separately frozen resource/design revision. No retry,
retrospective deadline extension, partial resume or subset acceptance.

See [status record](../verification/exact-topk-v1-catalog-fix-deadline-status-2026-10-26.json)
and [interpretation/next audit](../../../trials/torch-reviews-exact-topk-v1-catalog-fix/deadline-stop-2026-10-26/INTERPRETATION.md).
This status update changes no source/package/policy/gates and runs no experiment;
all1,315 prior inputs/artifacts remain preserved. Earlier corrected submit commands
are historical and must not be repeated for this spent campaign.

### Corrected B2b partial raw verified; no repeat recommended — October26,2026

Campaign`reviews-exact-topk-v1-catalog-fix-20261026T050859Z.jrmkwhuy`, job20949301_0,
is now independently verified:30 archive members/2,219,553 bytes, checksum
6856a060b01166ac53ba3993caf9affe3e5d49892dbbc5536eca35e7b102ceaf;
26,247 counted attempts,14 readers/five live, successful cleanup and identical captured
protected hashes across20 groups/1,622 entries.1,352 prior files remain unchanged.

Qualification and all600 fresh quality references pass unchanged sealed replay:
exact10 recall100% versus native64099.0333%; original floors/reserve pass. Every
recorded result/timer/order validates:6,104 complete slots/12,208 retained, one extra
conditioning call and8,520 valid plan packets. Block0 covers600 cases, block1 the
first163 plus the next conditioning call. Full final metadata/LOCK/charges/block1
boundary and final native integrity are missing; full A/A/economics remain unassessed.

Descriptive complete block0 exact535.980ms versus native9.552ms,56.11x; even votes108
is28.47x slower. Exact is faster in0/763 complete case/block instances and consumes
93.66% of the observed warm window. All recorded plan diagnostics total19.76seconds.
No partial subset was promoted to complete gates or a formal performance verdict.

**Disposition:** finite campaign closes incomplete_budget_exhausted; retain original
and both spent allowances, do not repeat/extend exact10. Recommend planned read-only
B2c/NEXT-ANN-ALTERNATIVES-01 compatibility/mechanism/cost review of indexed/filter-aware
ANN alternatives before any new implementation or allocation. No user/Torch command.

See [machine-readable analysis](../../../trials/torch-reviews-exact-topk-v1-catalog-fix/partial-review-2026-10-26/analysis.json),
[data-only source](../../../trials/torch-reviews-exact-topk-v1-catalog-fix/partial-review-2026-10-26/analyze_partial.py),
[completion receipt](../verification/exact-topk-v1-catalog-fix-partial-postrun.json)
and [results/next-step report](../../../research/fannagent-exact-topk-v1-catalog-fix-partial-results-2026-10-26.md).
This review replays the saved quality bootstrap once without new experiments/fits,
changes to scientific code/seals, native/database/provider/Torch or protected access.

## B2c read-only alternatives review; B2d design only — October26,2026

**B2c / NEXT-ANN-ALTERNATIVES-01 complete: scoped design GO.** Select exactly one
partial cosine HNSW for actual total_votes>=108, preserving full table/global IDs,
original full graph and module. Current public inspection rejects partial targets;
C binding is not a planner hint. A separate experimental validator and two private
copies prevent baseline plan contamination; candidate-only redundant fixed predicate
and actual fresh/cached-plan checks remain prospective native gates.

The [review](../../../research/fannagent-b2c-ann-alternatives-audit-2026-10-26.md),
[machine audit](../../../research/fannagent-b2c-ann-alternatives-audit-2026-10-26/audit.json),
[inventory](../../../research/fannagent-b2c-ann-alternatives-audit-2026-10-26/input-and-source-inventory.json)
and [receipt](../verification/b2c-ann-alternatives-audit-v1.json) preserve349 source
and1,364 prior-file hashes, all earlier verdicts and old scientific packages.
No code/tests/experiments/bootstrap/fit/index build/native/DB/Torch/provider or
protected-query access occurred.

[B2d / NEXT-PARTIAL-ANN-01 design](../../../research/fannagent-partial-ann-v1-design-2026-10-26.md)
is frozen, **not implemented, checked, sealed or run**:200 exposed >=108 cases,
24-vector early cost screen,16,802 maximum searches, unchanged quality margins,
four one-context A/A intervals, conservative economic bounds and complete final
integrity. Proposed one3h4CPU32GiB allowance is not allocated. Next is isolated
local implementation/checks/seal; no user commands now. Original execution stays
adopted, B1c deferred, and B2b's finite incomplete/no-repeat outcome unchanged.

## B2d partial ANN implementation ready for Torch — October26,2026

**NEXT-PARTIAL-ANN-01 / partial-ann.v1 local readiness passes:**55 source and
55 sealed-copy synthetic checks. One new >=108 partial cosine HNSW, two private
copies, preserved full table/original graph/module and unchanged native640.
Public validation/adopted code and all earlier experiments remain unchanged.
Native support, actual build/recall/A/A/economics/final integrity remain unassessed.

The [completion report](../../../research/fannagent-partial-ann-v1-implementation-2026-10-26.md),
[prospective addendum](../../../research/fannagent-partial-ann-v1-implementation-addendum-2026-10-26.md),
[source](../../experiments/partial-ann-v1/),
[source checks](../../../trials/torch-reviews-partial-ann-v1/local-checks-source.json),
[sealed checks](../../../trials/torch-reviews-partial-ann-v1/local-checks-sealed.json),
[final manifest](../../../trials/torch-reviews-partial-ann-v1/torch-partial-ann-v1/manifest.json)
and [receipt](../verification/partial-ann-v1-implementation.json) record readiness
and349 source/1,370 prior-file preservation. Internal review seal1 is retained as
superseded after metadata cleanup; it was never uploaded/submitted. Scientific
design and gates unchanged.

[Exact user commands](../../../trials/torch-reviews-partial-ann-v1/COMMANDS.txt):
Mac upload with remote checksum proof, then once-only Torch submission/status/
collection and Mac download. One3h4CPU32GiB job,202/802/16,802 search stops/cap,
site quota/memory/native preflight, full quality and four scoped A/A intervals.
No actual index build/native experiment/SSH/Torch call/allocation/provider/fit or
protected evaluation occurred locally. Retain original; B1c deferred. No retry,
resume, subset rescue or adoption from local mock results.

## B2d quota preflight repaired before any allocation — October26,2026

The user's attempted submission verified the original bundle, then stopped in
site myquota parsing before reservation, binding or Slurm dispatch. No allocation
was consumed. The table's lowercase30k is unsupported by the original parser.
A separate compatible source/package adds file-unit aliases and standard SGR
colour handling, preserving conservative capacity checks and fail-closed behavior.

**Current readiness:**61 source/61 sealed synthetic checks pass;162 manifested
files/163 regular archive members. Scientific config, runtime, policies, cohort,
schedule, measurement/controller/replay and gates are byte-identical. The repair
shares the original reservation and grants no extra allocation. All1,733 prior
immutable source/package/raw/receipt files remain unchanged.

Use only the [new commands](../../../trials/torch-reviews-partial-ann-v1-quota-fix/COMMANDS.txt)
and [transfer helper](../../../trials/torch-reviews-partial-ann-v1-quota-fix/transfer.sh).
Preserve the old package and failed preflight output. Corrected upload → guarded
once-only submit → current resource/native/preview/quality/A/A/economic/final gates
→ collect/download → independent replay. Native results remain unassessed;
original execution retained and B1c deferred.

See [repair report](../../../research/fannagent-partial-ann-v1-quota-fix-2026-10-26.md),
[isolated source](../../experiments/partial-ann-v1-quota-fix/),
[local/package records](../../../trials/torch-reviews-partial-ann-v1-quota-fix/)
and [receipt](../verification/partial-ann-v1-quota-fix.json).
No native/index/DB/provider/Torch call, model fit, protected query or new job was
run by Codex for this repair. Earlier readiness receipts stay historical.

## B2d submitted job failed initial environment guard — October26,2026

**Current action is collection only.** User reports campaign
reviews-partial-ann-v1-20261027T000432Z.9haq3pyt, actual job21043219_0,
FAILED1:0/4minutes. Quota preflight passed; the allowance is consumed. Runtime
reports0 searches/0 readers and the inherited JIT/parallel/work_mem/cache guard
failure. No partial-index build, quality, A/A or performance result; final
integrity is false. Host protected sources are reported unchanged, not yet
independently verified. Retain the shared reservation and all packages/raw.

Source applies reader environment expectations to the first admin catalog before
reader configuration; the exact differing field awaits saved raw. The later
memory guard has a related admin work_mem assumption. Do not waive checks or
rerun from this message. Codex next verifies archive/catalog/accounting/cleanup/
protected identities and decides a separately scoped correction if warranted.

Use [collection-only commands](../../../trials/torch-reviews-partial-ann-v1-quota-fix/native-failure-2026-10-26/COLLECT-ONLY.txt):
Torch collect, then the quota-fix Mac download helper. Failed/incomplete raw
preserved is expected. See [source interpretation](../../../trials/torch-reviews-partial-ann-v1-quota-fix/native-failure-2026-10-26/INTERPRETATION.md)
and [status receipt](../verification/partial-ann-v1-quota-fix-native-failure-2026-10-26.json).
All1,928 prior immutable files remain unchanged; no code/seal/test/new experiment
or job by Codex. Earlier quota-fix submit instructions are historical now.

## B2d failed raw verified; separate settings correction ready — October26,2026

Failed job21043219_0 now independently verifies:21 archive members/163,151bytes,
checksum60ae88ccf64c9f23e15af96d304c1b63f326f8ee52f01a2374ac02a289a20a82,
8 incomplete-lock hashes,0 searches/readers,6 SQL records, shutdown/cleanup and
23 protected groups/1,672 entries unchanged. Exact guard mismatch is admin
work_mem4096 versus reader16384; other guarded settings and structural catalog
checks pass. No quality/A/A/economic result; final integrity remains false.

The [frozen correction](../../../research/fannagent-partial-ann-v1-settings-fix-design-2026-10-26.md)
uses explicit role/phase guards, retains reader16MiB, bounds memory by that value,
and inspects build memory/workers as numeric bytes/int. It changes no query
policy, scientific margin/cohort/schedule/timer or adopted/prior code. Old failed
package/raw/archive/binding/spent reservation must verify before any corrected
submission/host execution. The original allowance remains spent.

**75 source/75 sealed synthetic checks pass**,169 manifested files/170 archive
members, scientific/frozen/member scope proof and1,960 prior immutable hashes pass.
One separate3h4CPU32GiB/16,802-search corrected allowance is proposed; none launched.
Use [current exact commands](../../../trials/torch-reviews-partial-ann-v1-settings-fix/COMMANDS.txt)
and [new transfer helper](../../../trials/torch-reviews-partial-ann-v1-settings-fix/transfer.sh).
All corrected native/quality/A/A/economic/final gates remain pending. Preserve
both reservations; no automatic retry/resume or performance inference from mocks.

See [failed analysis](../../../trials/torch-reviews-partial-ann-v1-quota-fix/failure-review-2026-10-26/analysis.json),
[postrun receipt](../verification/partial-ann-v1-quota-fix-failure-postrun.json),
[correction report](../../../research/fannagent-partial-ann-v1-settings-fix-2026-10-26.md),
[isolated source](../../experiments/partial-ann-v1-settings-fix/),
[local/package checks](../../../trials/torch-reviews-partial-ann-v1-settings-fix/)
and [readiness receipt](../verification/partial-ann-v1-settings-fix-implementation.json).

## Corrected B2d completed by status; exact-campaign collection recovery — October26,2026

User reports job21048213_0 COMPLETED0:0/17:17, all16,802 searches/two blocks,
quality_pass true and final integrity true. Full returned raw/A/A/economics remain
unverified independently. Actual campaign is
reviews-partial-ann-v1-20261027T005510Z.q6rgxprs: controller hardcodes old prefix,
while reporter/transfer expect the new prefix.75 mocks generated expected names
and missed actual controller naming. No scientific result changes or new run.

Use [current collection-only commands](../../../trials/torch-reviews-partial-ann-v1-settings-fix/collection-recovery-2026-10-26/COMMANDS.txt):
small helper upload on Mac, checksum/extract/raw collect on Torch, then new helper
Mac download. Eight synthetic checks pass; exact campaign/job/package/lock/
scheduler/cleanup/protection guards precede archiving and safe data-only ingest.
No experiment report or scientific code executes in collection. Existing package,
source, raw, labels, reservations and2,166 prior immutable files are preserved.

See [status](../../../trials/torch-reviews-partial-ann-v1-settings-fix/collection-recovery-2026-10-26/status.json),
[interpretation](../../../trials/torch-reviews-partial-ann-v1-settings-fix/collection-recovery-2026-10-26/INTERPRETATION.md)
and [receipt](../verification/partial-ann-v1-settings-fix-completion-status-2026-10-26.json).
Independent raw verification/proven exact-name reconciliation and trusted A/A/
economic replay follow download. Original status command is safe; old collect/
download commands are superseded for this campaign. No new allocation.

## B2d complete raw verified; A/A defeats speed qualification — October26,2026

**Frozen outcome: measurement_inconclusive.** Job21048213_0/campaign
reviews-partial-ann-v1-20261027T005510Z.q6rgxprs verifies37 archive members,
checksum0bb845dea4a0f1668a8dc46ebe93ba25f6c0ead65a629606de628bf4219ae055,
16,802 attempts/6,400 retained/3,200 slots/5,700 plans, all settings/data/original+
partial graph/module/final identities and cleanup/protection (24 groups/1,678 entries).
Exact-name reconciliation is limited to proven package/job/dispatch/counts; raw,
labels, scientific code and seals remain unchanged. Two fresh sealed replays
agree exactly. Remote economic JSON was not generated; no remote/local parity claim.

Recall98.60%→99.85%,+1.25pp,[+.65,+1.90]pp95%; floors/reserve pass. Mean outer
query time7.304522→6.030911ms (17.44% lower), conservative upper gap−1.080889ms/
ratio.876162 and both block directions pass nominal endpoints. **All four A/A
intervals fail**: identical partial replicas differ1.163ms/17.59%, close to the
1.274ms treatment gap.93.67% of partial A/A gap is in SQL; label positions exactly
balance. Cause remains unresolved; no qualified speed/adoption/amortization result.

Retain original execution/B1c deferred and both consumed allowances. Recommend
B2e/NEXT-PARTIAL-CONTROLS-01 read-only replica/session/source timing mechanism
audit before any separately frozen calibration proposal. No new Torch commands,
experiments, fitting, raw/package/scientific code change or protected access.
All2,219 prior immutable files remain unchanged.

See [results/next step](../../../research/fannagent-partial-ann-v1-settings-fix-results-2026-10-26.md),
[performance replay](../../../trials/torch-reviews-partial-ann-v1-settings-fix/postrun-review-2026-10-26/replay-1/performance.json),
[verification](../../../trials/torch-reviews-partial-ann-v1-settings-fix/postrun-review-2026-10-26/replay-1/verification.json),
[fresh parity](../../../trials/torch-reviews-partial-ann-v1-settings-fix/postrun-review-2026-10-26/parity.json),
[descriptive audit](../../../trials/torch-reviews-partial-ann-v1-settings-fix/postrun-review-2026-10-26/descriptive.json)
and [postrun receipt](../verification/partial-ann-v1-settings-fix-postrun.json).

## B2e replica/session audit complete; calibration design justified — October26,2026

**NEXT-PARTIAL-CONTROLS-01 / GB2e: GO to one separately frozen instrumented A/A
calibration design.** B2d remains measurement_inconclusive; original retained,
B1c deferred. No causal fix or performance qualification is established.

All saved traces/source reviewed.800 corresponding a/b plan packets per cell
match exactly, including parameters/preparation/custom counters; all captured
generic counts are0. Recorded boundary GUCs/admission bindings match. A/b are
separate connections to the same server/graph within cell, with fixed
label→connection/creation-order mapping. Observer planning traffic is symmetric
in count but uses fixed order and advances custom-plan counters.

Retained2 is faster after one discarded warmup across all readers; partial-a
mean falls.953ms versus.312ms for partial-b. Partial gap persists at retained2
(.843ms), for193/200 query averages and every block/temporal-quarter summary.
Last-conditioned cell aliases within-round position. Physical backend PIDs,
CPU placement/migrations and per-search CPU/wait/cache attribution are missing.
The SQL-labelled timer includes protocol/fetch/decode, not pure server time.

**Next: B2f/NEXT-PARTIAL-CALIBRATION-01 design only**, first proving fixed-graph
restoration and required telemetry feasibility, then freezing connection epochs,
independent order/warmup/observer controls, physical-backend diagnostics, exact
finite charges/stops and unchanged margins. Proposed ceiling≤1 calibration
allocation/3h4CPU32GiB/16,802 combined attempts, zero authorized now. Implementation,
local checks and native calibration require separate requests. No unchanged
repeat, pooled label cancellation or automatic treatment run.

Read-only descriptive analysis only; no code/raw/seal changes, tests, bootstrap,
experiments, fitting, native/DB/Torch/SSH/provider calls or protected values.
All2,235 prior pinned inputs preserved. No user commands now.

See [B2e report and phased handoff](../../../research/fannagent-b2e-replica-session-audit-2026-10-26.md),
[descriptive/source evidence](../../../trials/torch-reviews-partial-ann-v1-settings-fix/b2e-audit-2026-10-26/analysis.json),
[scope/input pins](../../../trials/torch-reviews-partial-ann-v1-settings-fix/b2e-audit-2026-10-26/)
and [completion receipt](../verification/b2e-replica-session-audit-v1.json).

## B2f instrumented A/A calibration design frozen — October26,2026

**NEXT-PARTIAL-CALIBRATION-01 / partial-calibration.v1: design frozen only.**
Exact B2d full/partial graphs, complete data/module/image/query identities and
quality/A/A/future economic margins remain unchanged. B2d stays
measurement_inconclusive; original retained/B1c deferred. No code or experiment.

The fixed contract uses two fresh formal connection epochs with reversed
creation order/crossed labels, physical backend PID/starttime/server identities,
allocation-local core placement and cell CPU crossover. Primary bursts have
two main conditioners,four on-reader warmups andthree retained repeats, with
independent conditioner/order balance. Bulk plan checks bound primary windows;
an eight-vector paired observer diagnostic cannot select or rescue a result.

Full cap16,242 searches:10 conformance+600 fresh quality+80 priming+14,400 primary
+1,152 diagnostic. Remaining560 below the16,802 envelope cannot be spent.
10 reader admissions/max6 live,4,200 plan packets,13,500 observer SQL and all
startup/truth/telemetry/time/storage/memory caps frozen. One proposed3h4CPU32GiB
allocation, zero allocated. **All56** physical A/A,half-epoch andretained-stability
intervals must pass unchanged margins; no treatment speed verdict in calibration.

Next prerequisite: user runs only the read-only path/PID-file/three-graph-hash/
space inventory in design§12. Exact stopped whole-cluster copies must remain
available; no graph transplant/rebuild or old-source startup. Actual four-core
and mandatory proc/PID/affinity capabilities remain future native gates.
Separate implementation/local readiness/seal and one-job handoff come later.

Only Markdown/JSON design/order/arithmetic artifacts created. No code/raw/seal
edits,tests,experiments,simulations,bootstrap,fits,native/DB/Torch/SSH/provider
calls orprotected values. All2,241 prior pinned files preserved.

See [frozen design and exact read-only user commands](../../../research/fannagent-partial-calibration-v1-design-2026-10-26.md),
[contract](../../../trials/torch-reviews-partial-ann-v1-settings-fix/b2f-design-2026-10-26/contract.json),
[explicit order](../../../trials/torch-reviews-partial-ann-v1-settings-fix/b2f-design-2026-10-26/schedule.json),
[count/balance accounting](../../../trials/torch-reviews-partial-ann-v1-settings-fix/b2f-design-2026-10-26/plan-accounting.json)
and [freeze receipt](../verification/partial-calibration-v1-design-freeze.json).

## B2f preliminary retained-source inventory passes — October27,2026

The user returned the requested read-only Torch output from torch-login-a-0.
Both exact retained pgdata paths and PG_VERSION/pg_control files are listed;
checksums/df/myquota were reached without the postmaster.pid stop branch.
Allthree reported graph hashes match partial-calibration.v1: full graph in
both copies dbc14b09…e23b393; partial b0300f40…8606700.

Disposition: **preliminary_user_reported_source_inventory_pass**. This is a
comparison of user-pasted terminal evidence, not an independent remote read or
complete clean-cluster/copy verification. Conservative quota lower headroom:
home26.3407GB/14,567 files; scratch4.778TB/4,846,599 files. Complete scratch
qualification still needs current source footprints and filesystem inode checks.

Frozen design/contract/schedule remain byte-for-byte unchanged. No graph rebuild
or replacement is justified. Next is separately requested implementation/local
correctness/preservation/seal; full clean whole-cluster/resource/data/module/
graph/core/PID/mandatory telemetry gates remain future. No more user commands now.
B2d stays measurement_inconclusive; original retained/B1c deferred.

Only evidence/assessment/receipt and tracking documents changed; no code/tests/
experiments/bootstrap/fits/native/DB/SSH/Torch/provider calls by Codex. All2,249
prior pinned files preserved.

See [user transcript](../../../trials/torch-reviews-partial-ann-v1-settings-fix/b2f-source-inventory-2026-10-27/user-output.txt),
[review](../../../trials/torch-reviews-partial-ann-v1-settings-fix/b2f-source-inventory-2026-10-27/review.md),
[structured assessment](../../../trials/torch-reviews-partial-ann-v1-settings-fix/b2f-source-inventory-2026-10-27/assessment.json)
and [receipt](../verification/partial-calibration-v1-source-inventory-2026-10-27.json).

## B2f implementation checked and sealed — October27,2026

**NEXT-PARTIAL-CALIBRATION-01 / partial-calibration.v1:
implementation_checked_sealed_native_pending.** The user authorized the next
implementation/local-check/seal steps after the preliminary source inventory.
A new isolated experimental package implements the byte-identical frozen design,
contract and schedule with unchanged graphs/data/module/policies/margins.

Source and sealed suites each pass78 synthetic correctness checks, including full
mocked acquisition and independent reconstruction plus failure/identity/ownership/
namespace/affinity/archive/budget guards. Lint/format/AST/shell checks and complete
archive-member byte parity pass. All2,255 prior pinned files remain unchanged.
No PostgreSQL/native ANN experiment, Torch submission, assistant SSH/provider
request, new fit or protected query was run. Synthetic checks do not establish
native performance, restoration compatibility or telemetry availability.

The user can now upload and submit one3h4CPU32GiB job, bounded at16,242 search
attempts/4,200 plan packets. Native stopped-cluster, full data/catalog/graph/module,
resource/core/mandatory-telemetry gates precede measurement; final preservation
and cleanup plus independent all56-interval analysis remain required. Failed raw
is collectible without a retry. Calibration cannot qualify treatment speedup or
adoption; B2d stays measurement_inconclusive/original retained/B1c deferred.

See [implementation report](../../../research/fannagent-partial-calibration-v1-implementation-2026-10-27.md),
[receipt](../verification/partial-calibration-v1-implementation.json),
[isolated source](../../experiments/partial-calibration-v1/README.md),
[exact commands](../../../trials/torch-reviews-partial-calibration-v1/COMMANDS.txt)
and [release evidence](../../../trials/torch-reviews-partial-calibration-v1/).

## B2f pre-Python failure verified; isolated launch correction — October27,2026

Original `reviews-partial-calibration-v1-20261027T155119Z.6rd0lmkp`,
job21111616_0, failed after4s with2:0. All6 archive members/checksum and exact
submission/seal/scheduler/log identities verify. srun could not exec bare python3;
no Python wrapper/runtime started and no native search ran. The allocation is
spent; no calibration/quality/A/A/native-capability verdict exists.

New isolated `partial-calibration.v1.launch-fix` records/passes the resolved
absolute host interpreter and establishes SLURM_EXPORT_ENV=ALL/srun --export=ALL.
It records host launch identity and guards the original failed package/raw/
binding/reservation.88 source+88 sealed synthetic checks pass, including the
actual shell launcher under a synthetic restricted export/PATH boundary, full
mocked acquisition/reconstruction and existing negative guards. Static/shell/
archive/scientific byte parity and all2,500 prior/captured-failure pins pass.
All native measurement code, frozen design/order, data/graphs/module/policies/
margins and per-job ceilings remain unchanged. Actual native N0–N4 stay pending.

The clearly labelled corrected handoff proposes **one additional**3h4CPU32GiB
job/16,242-search cap; the old attempt stays spent. Preparation/upload launches
nothing. User execution of the new submit command requests the new allocation;
no automatic repeat, binding deletion or graph replacement is authorized.
B2d remains measurement_inconclusive/original retained/B1c deferred.

See [verified failure](../../../trials/torch-reviews-partial-calibration-v1-launch-fix/failed-archive-verification.json),
[correction and Slurm sources](../../../research/fannagent-partial-calibration-v1-launch-fix-2026-10-27.md),
[implementation receipt](../verification/partial-calibration-v1-launch-fix-implementation.json),
[exact corrected commands](../../../trials/torch-reviews-partial-calibration-v1-launch-fix/COMMANDS.txt)
and [release evidence](../../../trials/torch-reviews-partial-calibration-v1-launch-fix/).

## B2f identity sidecar omission verified; restoration correction — October27,2026

The launcher worked in job21129331_0, but startup failed after8m34s before any
reader admission/search. Its32-member archive/raw locks and exact identities
verify. Both retained source cells contain the pinned957-byte identity file;
clone omitted it outside pgdata, and the actual frozen constructor required it.
Source-before/source-after inventories match across2,587 files; whole-copy proofs,
initial catalogs, protected inputs and both working-server shutdowns verify.
Final measurement integrity and all calibration gates remain unqualified.

New isolated partial-calibration.v1.metadata-fix privately copies only the exact
pinned source identity, checks copy/final provenance and keeps both prior
seals/raw/bindings/reservations protected.101 source+101 sealed synthetic checks
pass, including the actual frozen constructor/binding/snapshot/native/exact
methods through the full16,242-call fixture and trusted reconstruction. Only DB
responses are synthetic in that added integration;40 fixture rows do not prove
native/full-size performance or memory. Existing protocol/launcher/negative
guards pass; static/shell/archive/scientific parity and2,781 prior pins pass.
Timed query/scoring/schedule/analysis/margins/data/graphs/module remain unchanged.

Both prior allocations (4s and8m34s) stay spent. The clearly labelled corrected
handoff proposes one additional3h4CPU32GiB/16,242-search job; preparation/upload
submits nothing, and no automatic repeat follows. Native N0–N4 remain pending;
B2d inconclusive/original retained/B1c deferred. Codex ran no native experiment,
Torch submission, SSH/provider request, fit or protected query.

See [verified failure](../../../trials/torch-reviews-partial-calibration-v1-metadata-fix/failed-archive-verification.json),
[restoration correction](../../../research/fannagent-partial-calibration-v1-metadata-fix-2026-10-27.md),
[implementation receipt](../verification/partial-calibration-v1-metadata-fix-implementation.json),
[exact corrected commands](../../../trials/torch-reviews-partial-calibration-v1-metadata-fix/COMMANDS.txt)
and [release checks](../../../trials/torch-reviews-partial-calibration-v1-metadata-fix/).

## B2f third startup failure and release hold — October27,2026

The metadata-corrected job21159802_0 failed1:0/10m44s before any search. Its30-file
archive7e383c42…6ba21e, failed lock, source/copy/catalog/protected identities and
clean shutdown verify. Two readers were admitted; no quality/A/A/performance
result exists. Three prior jobs are now spent, all0 searches.

The guard hashed field_map plus IDs/votes against a pinned IDs/votes-only record.
Earlier integration skipped that startup control flow. Isolated identity-fix
source preserves the eligibility schema and checks field/dataset identities
separately. New tests invoke pc_runtime.main through full startup/acquisition/
final checks/cleanup with synthetic OS/DB interfaces and actual frozen readers;
negative lifecycle and full247,286-ID/vote schema tests are included. Exact checks
and3,065 prior-file preservation are in the receipt.

**Release held:** no production package/transfer/new submission is released.
MaxRSS33534232K versus32GiB requires accounting/resource review; no OOM cause is
established. Only read-only Slurm configuration is requested. Frozen scientific
files/caps/margins remain unchanged; B2d stays inconclusive/original retained.

See [verified third failure](../../../trials/torch-reviews-partial-calibration-v1-identity-fix/failed-archive-verification.json),
[release audit and next gates](../../../research/fannagent-partial-calibration-v1-release-audit-2026-10-27.md),
[check/audit receipt](../verification/partial-calibration-v1-identity-fix-implementation.json)
and [local evidence](../../../trials/torch-reviews-partial-calibration-v1-identity-fix/).

## B2f accounting review — October27,2026

The user supplied the requested controller fields: jobacct_gather/cgroup,
JobAcctGatherParams=(null), proctrack/cgroup and task/cgroup+affinity. The request
is complete. With cgroup/v2 this permits file cache in MaxRSS; the transcript
identifies neither compute cgroup version, effective limits nor cache/anonymous
shares. The explicit schema-guard failure remains the recorded cause; no OOM or
full-run32GiB feasibility is established.

Release stays held. Next recommended work is a separate startup-only resource
qualification design: full-size unchanged snapshot/admission and both reader
creation orders, memory-limit/component/event observations and source/cleanup
proof, with0 ANN/exact searches. The outline proposes at most one4CPU32GiB/1hour
job; no implementation, handoff or allocation is released. Freeze exact caps and
resource decision rules first. No user commands are needed now.

[Accounting review and next gates](../../../research/fannagent-partial-calibration-v1-accounting-review-2026-10-27.md),
[review receipt](../verification/partial-calibration-v1-accounting-review-2026-10-27.json),
[current hold/evidence](../../../trials/torch-reviews-partial-calibration-v1-identity-fix/accounting-review-2026-10-27/).
This update changes no code and reruns no tests/experiments;119 prior passing
checks and3,115 prior pinned files are retained.

## Startup-only resource qualification v1 — October 27, 2026

NEXT-STARTUP-RESOURCE-01/startup-resource.v1 is frozen before implementation and
locally checked/sealed for one additional one-hour, four-CPU, 32 GiB user job. Zero ANN/exact
searches: method/operation/SQL guards; actual full-size snapshot/data/admission
SQL and ten-reader lifecycle only. A separate bounded host sampler records actual
v1/v2/ancestor limits/peaks/components/events/PID memory through cleanup. No cache
subtraction or scientific quality/A/A/performance result. Full calibration stays
held pending independent resource evidence and later review.

Actual launcher/host/runtime/frozen-startup synthetic fixtures, historical failure
regressions, zero-search/observer/cleanup/transport/archive negatives and trusted
complete resource replay pass. Source and sealed package each pass 117 tests.
Exact final source/sealed/static/archive identities
and 3,123 prior-file preservation are recorded in the receipt. Codex ran no native
DB/ANN/Torch experiment, provider, fit, real SSH or protected query.

[Pre-code frozen design](../../../research/fannagent-startup-resource-v1-design-2026-10-27.md),
[implementation and limits](../../../research/fannagent-startup-resource-v1-implementation-2026-10-27.md),
[release receipt](../verification/startup-resource-v1-implementation.json),
[exact once-only commands](../../../trials/torch-reviews-startup-resource-v1/COMMANDS.txt),
[checks/preservation](../../../trials/torch-reviews-startup-resource-v1/).

User upload/single submit/status/terminal collect/download is next. All three
failed calibration packages/raw/bindings/reservations remain spent/protected.
No automatic retry, full-calibration launch, graph rebuild or resource increase.

## Startup-only resource return — October 28, 2026

User job `21171789_0` completes `0:0` in 13m28s. The 46-member archive and
independent fresh sealed reconstruction verify zero ANN/exact searches, ten
admissions, both epochs, final integrity and clean shutdown. Verdict:
`startup_complete_resource_margin_inconclusive`. Job peak equals its 32 GiB limit;
the frozen 2+2 GiB allowances are unmet, and 592 max events occur during snapshot
loading. OOM/kill deltas are zero. Full calibration stays held.

The trace records both anonymous memory and file-cache charge; neither components
nor per-process highs are subtracted or added to qualify the gate. Read-only
source inspection identifies overlapping Python vector rows, NumPy matrix and
full JSON text/bytes as candidates for a memory compatibility audit. No individual
savings or unconstrained demand is established.

[Verified report](../../../research/fannagent-startup-resource-v1-postrun-2026-10-28.md),
[postrun receipt](../verification/startup-resource-v1-postrun.json),
[archive/metrics/fresh replay/preservation](../../../trials/torch-reviews-startup-resource-v1/postrun-audit-2026-10-28/).
All 3,442 preserved inputs remain unchanged. No new implementation, tests,
experiment, searches, provider/remote calls or job. Next is
NEXT-STARTUP-MEMORY-01 read-only snapshot-memory/identity compatibility audit and
prospective design. No Torch commands are needed now; preserve all spent evidence.

## Snapshot-memory compatibility audit/design — October 28, 2026

NEXT-STARTUP-MEMORY-01 M0/M1 are complete: read-only review of 116 source files,
137 references and the existing startup trace selects per-row original canonical
hashing with exact identity framing. Ten readers share one snapshot; original rows
have real consumers and remain alongside the NumPy matrix. The default snapshot
cursor buffers results on the client; verification scans already use named
server cursors. Those paths and validation stay unchanged in the first remedy.

[Audit and decision](../../../research/fannagent-startup-memory-audit-v1-2026-10-28.md),
[frozen prospective design](../../../research/fannagent-startup-identity-stream-v1-design-2026-10-28.md),
[machine contract/source/trace/freeze evidence](../../../trials/torch-reviews-startup-memory-audit-v1/),
[audit receipt](../verification/startup-memory-audit-v1.json).

Design feasibility only; exact byte/identity, bounded buffer and scoped binding/
restoration checks are specified before code. No implementation, tests, new
measurement, experiment, provider/remote/native job or cap/margin change occurred.
All 3,456 preserved inputs are unchanged. M2 isolated implementation/local
qualification is next on separate request. No Torch commands or M3 native release;
full B2f stays held and the original resource result remains inconclusive.

## Identity-streaming local readiness and resource handoff — October 28, 2026

NEXT-STARTUP-MEMORY-01 M2 is complete. The new isolated
`startup-resource.stream.v1` harness hashes original canonical fields/rows in
bounded pieces with exact framing, temporarily scoping only the snapshot-module
digest during the initial actual construction. Finally restoration precedes
validation/publication/admission. Original rows/NumPy/cursor/SQL/constructor,
data/graphs/native module/policies and all scientific/resource margins remain.

Source and sealed suites each pass **155/155** bounded offline/synthetic checks,
including actual frozen constructor/acquisition/cleanup, a handled POSIX signal,
byte/hash/consumer/error/deadline/restoration and trusted replay tamper rejection.
Static/source/seal/archive checks and 116 source pins pass; all **3,468** prior
inputs remain unchanged. Initial local failures and fixes are preserved. These
checks establish local compatibility; full-size native memory/CPU savings and
resource margin remain unmeasured. Codex executes no native DB/search/provider/
fit/real SSH/Torch job.

[Implementation report](../../../research/fannagent-startup-identity-stream-v1-implementation-2026-10-28.md),
[release receipt](../verification/startup-resource-stream-v1-implementation.json),
[check/preservation evidence](../../../trials/torch-reviews-startup-resource-stream-v1/),
[independent archive/release verification](../../../trials/torch-reviews-startup-resource-stream-v1/release-verification.json),
[exact once-only Mac/Torch commands](../../../trials/torch-reviews-startup-resource-stream-v1/COMMANDS.txt).

Next is one user-executed **M3 startup-only** resource qualification: one hour,
four CPUs, 32 GiB, zero ANN/exact searches, unchanged lifecycle/observer/sampler/
cleanup caps and peak+2+2 GiB/no-limit-event gate. Terminal collect/download and
trusted independent stream/resource analysis are required. All three failed
calibration attempts and original resource job remain spent; no automatic retry,
resource increase or cache subtraction. Full B2f stays held, including after a
startup-only pass until separate query-workload memory and release review.

## Identity-stream resource return — October 28, 2026

User job `21224521_0` completes `0:0` in 11m55s. All 48 raw members and the 346-file
seal verify; fresh trusted replay exactly matches preserved download-time
analysis. Native identity streaming reproduces the exact original snapshot hash
for 247,286 rows, one invocation/restored binding,64 KiB maximum pending bytes,
both reader epochs, zero searches, final integrity and clean shutdown.

Verdict: **startup_complete_resource_margin_inconclusive**. Runtime-process RSS
high-water is descriptively15.030→11.323 GiB (−3.707 GiB/24.66%), but job peak
remains 32 GiB at 32 GiB limit, with 259 max/zero OOM deltas. The28 GiB/no-event gate
is unchanged and unmet; lower process RSS is insufficient. Counter brackets show
pressure strictly before hashing and within finalization, with 76 and 68 events
crossing load/hash and hold/finalization boundaries respectively. Preserve that
attribution uncertainty. No search-speed/recall/A/A claim follows.

[Verified report](../../../research/fannagent-startup-resource-stream-v1-postrun-2026-10-28.md),
[postrun receipt](../verification/startup-resource-stream-v1-postrun.json),
[archive/replay/metrics/phase attribution/preservation](../../../trials/torch-reviews-startup-resource-stream-v1/postrun-audit-2026-10-28/).
All 3,947 preserved inputs remain unchanged. Codex changes no implementation and
runs no new tests/experiment/native DB/search/provider/fit/SSH/Torch job.

M3 is complete/closed-inconclusive; all three failed calibration attempts and both
resource jobs are spent. Do not rerun earlier submit commands. Next is
NEXT-STARTUP-MEMORY-02 read-only loading/retained-representation/verification I/O
working-set audit, then a separate design GO/no-GO. No new allocation or commands;
full B2f calibration remains held.

## Snapshot working-set audit — October 28, 2026

NEXT-STARTUP-MEMORY-02 W0–W2 are complete, read-only. The actual producer builds
original rows plus a matrix; ten readers share one snapshot, and reader close
leaves snapshot roots live through final verification. Verification already uses
named-cursor/512-record Arrow batches without read threads. Its four transaction
brackets total 333.775 seconds / 56.60% of streaming runtime, whereas logged execute
intervals sum 0.034982 seconds; iteration/fetch/decode/bit comparison is outside the
execute timer. Source/per-allocation and per-file attribution remain unresolved.

The 171 startup +56 observer counts mean 227 charged API-level statements, not all
SQL/protocol activity. Raw driver fetch/close/transaction handling bypasses the
wrapper counter/API allowlist. Pinned default code implies 9,892 fetches across four
passes conditionally; that is not a measured wire count. Future design must
preserve old API semantics and add an explicit finite driver-command ledger.

[Audit and recommendation](../../../research/fannagent-startup-working-set-audit-v1-2026-10-28.md),
[audit receipt](../verification/startup-working-set-audit-v1.json),
[source/trace/accounting/primary-reference/preservation evidence](../../../trials/torch-reviews-startup-working-set-audit-v1/).
All 246 source/recipe pins, including earlier 116, and 3,961 prior inputs remain
unchanged. No code, tests, new measurements, native DB/search/provider/fit/SSH or
Torch job. Dataset/query vectors are not decoded by this audit.

No-go for a blind cursor-only, batch-only or close/GC-only correction. Next is
NEXT-STARTUP-ATTRIBUTION-01 A0: separately freeze bounded zero-search lifetime/I/O
observations, command/row/file-role ledgers and semantic/overhead/futility gates.
No implementation or allocation is released. Both resource jobs and three failed
calibration attempts remain spent; full B2f stays held. No Torch commands now.

## Attribution diagnostic design freeze — October 28, 2026

NEXT-STARTUP-ATTRIBUTION-01 A0 is frozen before implementation. The prospective
startup-attribution.v1 design specifies102 required/max128 memory checkpoints,
original-code local CPython monitoring and scoped cursor-close/harness seams,
nine pinned driver-hook roles, exact page/row and separate API/dispatch/protocol
ledgers. Original producer/constructor/rows/matrix/identity, SQL/transactions,
four verification scans and all science/data/graphs/module/policies stay fixed.

The proposed later scope is at most one1h4CPU32GiB job with zero ANN/exact searches;
no allocation is released. Added observation is bounded15 CPU/30 observer-wall
seconds,64 MiB reads/8,192 operations and16 MiB raw, within original combined
sampler caps. Dispatch/request envelope13,000 includes64 reserved cleanup; no
additional fetch/SQL or hidden packet-count claim. Monitoring callbacks/masks
clear before tool release; every driver binding restores before locks. Absolute
remaining-wall clamps preserve original cleanup reserves.

[Human frozen design](../../../research/fannagent-startup-attribution-v1-design-2026-10-28.md),
[machine contract/catalogs/source/reference/freeze evidence](../../../trials/torch-reviews-startup-attribution-v1-design/),
[A0 receipt](../verification/startup-attribution-v1-design.json).
All246 source/recipe and3,974 prior inputs remain unchanged. No implementation,
test, runtime capability probe, new experiment/measurement/native DB/search/
provider/fit/SSH/Torch job or vector decoding occurs in A0.

Next is separately requested A1 implementation and actual original-code/monitor/
driver/generator/signal/cleanup/source/seal local readiness. A2 remains unreleased.
Informative attribution requires a new prespecified bracket distinction; known
retention/capped peak or fetch reconciliation alone is insufficient. Complete
nondiscriminating evidence closes unresolved. Resource/scientific gates remain
separate; full B2f held, original retained/B1c deferred. No Torch commands now.

## Startup attribution A1 — local readiness complete, A2 unreleased

October 29, 2026. The isolated `startup-attribution.v1` harness implements the frozen
A0 instrumentation and passes155 unchanged baseline regressions plus
100source/100sealed correctness checks. Actual original-code monitoring,
private-driver/generator/host/runtime/signal/cleanup and negative independent
replay paths are exercised with bounded synthetic files/transports/counts.
3,987prior evidence files and246 A0 source pins remain unchanged. Original
contracts/cohort/helper/vendor/module/scientific boundaries remain intact.

The stale simulated-heartbeat failure and correction are preserved. The native
five-second gate is unchanged. Local metadata-only9892fetch accounting is not a
native observation or performance/resource result.

[Report](../../../research/fannagent-startup-attribution-v1-implementation-2026-10-29.md),
[verification receipt](../verification/startup-attribution-v1-implementation.json),
[harness](../../experiments/startup-attribution-v1/README.md),
[sealed/local evidence](../../../trials/torch-reviews-startup-attribution-v1/).

Next: separate A2 handoff/release review, actual-image capability before restore,
then only the bounded zero-search diagnostic and independent A3 decision.
The A1 controller/native entry guards remain closed. No Torch command or job is
released. Both resource verdicts remain margin-inconclusive; full B2f held.

## A2 release review / source-only image inventory — October 29, 2026

A2 acquisition is **not complete or released**. The release review catches A1's
strict local Python3.12.7 reference versus saved image-build config/header3.12.15
before dispatch. Actual SIF capability inventory is required before a separate
compatibility decision. No dependency/reference/gate change or Torch job.
A0/A1 and both margin-inconclusive resource results stay unchanged; full B2f held.

The isolated source-only inventory has29source/29sealed checks,99 byte-identical
A1 references,108manifest/109regular archive members and5,318 preserved prior
files. It contains no datasets, DB/graph binaries or scheduler entry point.
One user image invocation:15CPU/30interpreter-wall seconds,2GiB virtual address
space,60s wrapper timeout+5s kill grace; zero DB connections/SQL/snapshot/search.
The exclusive binding preserves failure prefixes and prevents rerunning.

Manifest `5f8bbb0dfa50b5346d00e4b60f5a7f3e6757bd48de3f0abe2073a3b882b554ce`;
archive `ccfab40dcd5325e9391f0ffdf76f3e8d73a7e2a343bcae8eed0d35ea6ac76fcb`.
[Review](../../../research/fannagent-startup-attribution-v1-release-review-2026-10-29.md),
[receipt](../verification/startup-attribution-v1-release-review.json),
[harness](../../experiments/startup-attribution-image-preflight-v1/README.md),
[handoff verification](../../../trials/torch-reviews-startup-attribution-v1-release/handoff-verification.json),
[exact image-only commands](../../../trials/torch-reviews-startup-attribution-v1-release/COMMANDS.txt).

Next: user Mac upload → one Torch login image inventory → Mac download, then
independent compatibility review. Even a matching inventory leaves allocation
proc/cgroup, native accounting/resource/cleanup/replay gates pending. No automatic
version substitution, retry or allocation submission.

## A2.0a image inventory verified — October 29, 2026

`startup-attribution-image-preflight-v1.QANl63cj` completed successfully: exit0,
empty stderr,5.627513442s, zero SQL/connections/snapshot/search/providers and no
Slurm allocation. Exact four-file/three-payload checksums,108-file manifest,
109-member archive,99 A1 references and fresh trusted sealed data-only replay
verify.5,519 earlier source/evidence files are preserved. No new execution,
experiment, code/reference/dependency change or test suite during analysis.

The sole provenance mismatch is CPython3.12.15 actual versus3.12.7 in A1's local
reference. A0 already requires3.12.15: the harness captured the Mac version into
its native expectation. NumPy/Arrow/Psycopg/libpq, all9 hooks and the query parser
match exactly. Original source/line mappings and4 literal monitoring callbacks
pass; original producer/constructor and full wrapper/signal/cleanup paths were
not executed by this inventory. Zero import-time Arrow pool bytes do not qualify
workload memory. The one inventory is complete; do not repeat it.

Decision: GO isolated strict image-reference correction and actual3.12.15
compatibility readiness, then reviewed finite native handoff. A2 acquisition,
A3 and full B2f remain held; original resource verdicts and all gates unchanged.
No new commands are required now.

[Postrun report](../../../research/fannagent-startup-attribution-image-preflight-v1-postrun-2026-10-29.md),
[receipt](../verification/startup-attribution-image-preflight-v1-postrun.json),
[raw inventory](../../../trials/torch-reviews-startup-attribution-v1-release/returned/startup-attribution-image-preflight-v1.QANl63cj/),
[independent verification](../../../trials/torch-reviews-startup-attribution-v1-release/postrun-audit-2026-10-29/inventory-verification.json),
[correction boundary](../../../trials/torch-reviews-startup-attribution-v1-release/postrun-audit-2026-10-29/compatibility-decision.json).

## A2 exact-reference correction and native compatibility handoff — October 29, 2026

The separate main harness now uses strict verified3.12.15 image provenance and
retains the historical3.12.7 local reference. Pre-restore original source/AST/line/
local-mask proof and conditional finite native controller are implemented.
128normal/128guarded local tests pass; source/vendor/126 original native files and
5,531 prior inputs are unchanged. No main production artifact/handoff yet.

The local exact-build linux/amd64 attempt emitted QEMU target SIGSEGV and no
Python receipt. Its owned container was stopped/removed (OOMKilled=false;
exit137 follows the stop). It cannot establish target readiness. No second local
emulated attempt or dependency change was made.

Only one native zero-DB correctness job is now prepared:15m/2physicalCPUs/4GiB,
128source+128sealed synthetic-candidate checks in the unchanged SIF;0SQL/real DB/
server/ANN/exact/provider/fit.23source/23sealed local capsule checks, actual mocked
host/guest success/failure, exact guards/controller/terminal collection and archive
verification pass.693-file manifest/694regular archive members;20,332,368-byte
archive. The main A2 acquisition and full B2f remain held pending native results
and C3's final main production seal/release review.

Manifest `fb850640e4fe71c0a05ce6439b97586232701bbfaacfa08b348c927fb5844439`;
archive `987c1611a354aca2080218e7ba40cc7fd086801e4004681ed66ad9f30b07f0e2`.
[Report](../../../research/fannagent-startup-attribution-image-reference-correction-2026-10-29.md),
[receipt](../verification/startup-attribution-image-reference-correction.json),
[corrected main harness](../../experiments/startup-attribution-v1-image-reference/README.md),
[native compatibility harness](../../experiments/startup-attribution-compatibility-v1/README.md),
[independent release verification](../../../trials/torch-reviews-startup-attribution-compatibility-v1/release-verification.json),
[exact compatibility commands](../../../trials/torch-reviews-startup-attribution-compatibility-v1/COMMANDS.txt).

Next user step: Mac upload → one Torch compatibility submit/status/terminal collect
using cc_control.py → Mac download. That controller checks the compatibility job;
it is not the completed image inventory or the future main diagnostic. No job was
submitted during this implementation. Preserve failures; no automatic retry.

## A2 compatibility fixture correction — October 29, 2026

Job21348020 failed after a ReplayTests setup error and300-second source deadline.
The13-file/eight-lock return verifies; native provenance matches. Retained scratch
output and actual-constructor regressions identify omitted inputs/local-identity.json.
The preceding handoff entry and its commands are historical; its allowance is spent.

The isolated correction includes exact constructor metadata, optimizes only ephemeral
synthetic fixture clones with seed/mutable-file checks, and records immediate fail-fast
errors, per-test progress, restored guards and separate final host integrity.
33source/33sealed and128source/128packaged-fixture main local checks pass. Original
main code/recipe, references, graphs/module/data/policies and margins stay unchanged.
One distinct15m2CPU4GiB zero-DB compatibility correction is prepared; main A2/C3/full
B2f remain held pending complete native128+128 proof and independent review.

[Diagnosis and gates](../../../research/fannagent-startup-attribution-compatibility-fixture-fix-2026-10-29.md),
[failed-return verification](../../../trials/torch-reviews-startup-attribution-compatibility-v1/postrun-audit-2026-10-29/returned-verification.json),
[corrected harness](../../experiments/startup-attribution-compatibility-v1-fixture-fix/README.md),
[release verification](../../../trials/torch-reviews-startup-attribution-compatibility-v1-fixture-fix/release-verification.json),
[exact corrected commands](../../../trials/torch-reviews-startup-attribution-compatibility-v1-fixture-fix/COMMANDS.txt).

## A2 compatibility prepared fixtures — October 29, 2026

Historical pre-run entry: job 21382454 has now spent this allowance and failed.
See the postrun entry below; these commands are not a retry authorization.

Second native correctness job21367064 failed at its300-second source deadline.
The16-file/11-lock archive verifies.96cases passed with zero error events; metadata,
native provenance and final capsule/image integrity pass. Events/stacks locate
fixture preparation/hash/write work. Full target receipts are absent; the earlier
fixture-fix handoff and reservation are now spent historical evidence.

A separately frozen capsule retains all128+128 original cases and deadlines. Each
child invokes the actual builder once and fully verifies the shared seed/archive
before four reuses; immutable hardlink manifests reuse only proved identical bytes,
re-hashing all mutable fields.43source/43sealed plus128source/128packaged cases pass
through final guards; actual original-helper manifest parity passes. A local async
watchdog cancellation stall was caught/preserved/stopped before release; synchronous
fixture-stage diagnostics now complete. No main source/science/margin change.

One distinct15m2CPU4GiB zero-DB native qualification is prepared. Both old allowances
are spent; no automatic retry or main A2/full B2f release. Native headroom remains
unqualified despite local~63–64second suites.

[Failure analysis and gates](../../../research/fannagent-startup-attribution-prepared-fixtures-2026-10-29.md),
[verified native failure](../../../trials/torch-reviews-startup-attribution-compatibility-v1-fixture-fix/postrun-audit-2026-10-29/returned-verification.json),
[prepared harness](../../experiments/startup-attribution-compatibility-v1-prepared-fixtures/README.md),
[release verification](../../../trials/torch-reviews-startup-attribution-compatibility-v1-prepared-fixtures/release-verification.json),
[exact commands](../../../trials/torch-reviews-startup-attribution-compatibility-v1-prepared-fixtures/COMMANDS.txt).

## A2 compatibility third timeout verified — October 29, 2026

Prepared-fixture job **21382454** timed out at the 300-second source limit after
119 passing cases and no recorded errors. The full synthetic runtime/checkpoint
case now passes. Test 120 is incomplete; eight cases had not started, and final
child/source/sealed qualification proofs remain absent. Main A2 did not launch.

The 16-file return, all 11 locked hashes, exact native provenance/dependencies and
separate final capsule/SIF integrity verify. Completed fixture stages total
143.703 seconds. Original runtime verification still reads a roughly 299-MB
historical package; hardlinks do not remove that work. Local suite times did not
establish native headroom. There is no new recorded functional failure to justify
another speculative fixture change.

All three compatibility allowances are spent. **No current run command or new
capsule is released.** Next is C2B: freeze/review a native-informed, finite time
budget for all 128+128 cases and final proofs, then implement/check only the
isolated compatibility time/accounting changes. A 20-minute sizing option is
documented for review, not frozen or authorized for dispatch. Main A2's separate
1h/4CPU/32GiB zero-search design and all scientific margins remain unchanged.

[Analysis and next-step gates](../../../research/fannagent-startup-attribution-third-compatibility-timeout-2026-10-29.md),
[independent return verification](../../../trials/torch-reviews-startup-attribution-compatibility-v1-prepared-fixtures/postrun-audit-2026-10-29/returned-verification.json),
[decision receipt](../verification/startup-attribution-compatibility-prepared-fixtures-postrun.json),
[roadmap](../../../research/fannagent-performance-research-roadmap-2026-10-22.md).

## Main A2 startup attribution — completed October 30, 2026

Campaign `reviews-startup-attribution-v1-image-reference-20261030T213446Z.cmd7zvbo`,
job **21459623_0**, completed **0:0 in 14m16s**, using the original four CPUs and
32 GiB allocation. The 52-member return, 32 guest/45 host locks, unchanged main
seal and fresh trusted replay all verify. The replay matches all three existing
analysis files exactly, preserves all 128+128 native checks and reconstructs all
102 checkpoints, four full verification scans and zero ANN/exact searches.

Outcome: **attribution_complete_informative**. The prespecified row-decode bracket
adds 7.478 GiB RSS; matrix construction adds 0.709 GiB. These descriptive brackets
do not establish causal savings. The separate resource verdict remains
**startup_complete_resource_margin_inconclusive**: aggregate peak32 GiB,
780 memory-limit events, no OOM kills. Full B2f stays held. Main and all four
compatibility allowances are spent; next is A3 remedy contract review before code,
not another native run.

[Interpretation](../../../research/fannagent-startup-attribution-main-A2-postrun-2026-10-30.md),
[raw return](../../../trials/torch-reviews-startup-attribution-v1-image-reference/returned/reviews-startup-attribution-v1-image-reference-20261030T213446Z.cmd7zvbo/),
[independent audit](../../../trials/torch-reviews-startup-attribution-v1-image-reference/postrun-audit-2026-10-30/returned-verification.json),
[closure receipt](../verification/startup-attribution-main-A2-postrun.json).

## A3 exact-vector remedy decision — October 30, 2026

A3 selects one isolated decoded-vector representation: immutable binary64 payloads
plus exact original integer categories/values, with one-row canonical identity
and bounded ordinary-JSON sample adapters. The contract was frozen before code.
All33 guarded <=64x768 original-consumer local checks pass;756 tracked A2 files
and existing128+128 native receipts remain byte-identical. Initial fixture errors
and earlier positive logs are preserved. No SQL, ANN/exact search, connection,
subprocess or native job occurred in guarded checks.

A3's decision is complete; production producer/boundary integration, exact-target
source+sealed correctness and native resource qualification are separate and
pending. Internal vector type/mutability changes explicitly; universal list/API
equivalence and memory/savings are not claimed. No Torch commands or allowance
are released; main A2 and all four compatibility jobs remain spent, full B2f held.

[Decision](../../../research/fannagent-startup-exact-vector-A3-decision-2026-10-30.md),
[freeze](../../../trials/torch-reviews-startup-exact-vector-v1/A3-FREEZE.json),
[offline receipt](../../../trials/torch-reviews-startup-exact-vector-v1/local-checks.json),
[code](../../experiments/startup-exact-vector-v1/README.md),
[closure receipt](../verification/startup-exact-vector-A3-decision.json).

## A3 integrated startup — distinct target correctness ready, October 30, 2026

The isolated one-row packed producer, original constructor/eligibility/admission,
rollback/shared-cache handling and receipt-gated resource context pass56 source+
56 sealed local cases. All128+128 original A2 cases and65+65 capsule/controller/
deadline/publication checks pass. The774-file/775-member archive, exact source/
seal/member hashes and789 preserved old files independently verify.

One new25m2CPU4GiB correctness job is released through E342, with private scratch
extraction and zero real DB/SQL/search/server/provider. Native3.12.15 remains
pending; all old jobs are spent. No resource acquisition, savings claim or B2f
release follows. Source/receipt/library/guard/seed/final-integrity verification
must independently pass after native terminal collection/download.

[Implementation/review](../../../research/fannagent-startup-exact-vector-integration-qualification-2026-10-30.md),
[local release audit](../../../trials/torch-reviews-startup-exact-vector-compatibility-v1/release-verification.json),
[historical correctness commands — now spent](../../../trials/torch-reviews-startup-exact-vector-compatibility-v1/COMMANDS.txt),
[decision](../verification/startup-exact-vector-integration-qualification.json).

## A3 native correctness — independently complete October 31, 2026

Campaign `reviews-startup-exact-vector-compatibility-v1-20261031T014056Z.3twju78d`,
job **21470341**, completed **0:0 in 11m44s** on the unchanged exact image and
CPython **3.12.15**. Independent verification reconstructs all **368 cases**:
128 source + 128 sealed original A2 cases and 56 source + 56 sealed A3 cases,
with no errors, failures, skips, missing or duplicate cases. All 33 returned
members, 28 run locks, module/code provenance, guards, fixture builds/seeds,
finite deadlines, final capsule/SIF integrity and cleanup verify. The original
789 tracked files and 68 main recipes remain unchanged.

The authentic four-receipt packet passes the unchanged local native gate in a
metadata-only rehearsal; its temporary hypothetical release is deleted. No
returned code executes, native-size arrays are allocated or DB/SQL/ANN/exact
searches occur in the audit. Native correctness is qualified; native memory,
causal savings, workload, quality and performance remain unqualified.

The correctness allowance is **spent; do not resubmit E342**. All previous
allowances remain spent. Next is a separate startup-resource protocol/harness
freeze, integration and local release review under the unchanged 32 GiB limit
and 2 GiB reserve + 2 GiB workspace rule. No resource command or full B2f release
is issued by this result. Earlier pending entries describe their dated state.

[Interpretation](../../../research/fannagent-startup-exact-vector-native-correctness-postrun-2026-10-31.md),
[independent audit](../../../trials/torch-reviews-startup-exact-vector-compatibility-v1/postrun-audit-2026-10-31/returned-verification.json),
[authentic proof packet](../../../trials/torch-reviews-startup-exact-vector-compatibility-v1/postrun-audit-2026-10-31/qualified-receipts/),
[closure receipt](../verification/startup-exact-vector-native-correctness-postrun.json).

## A3 startup-memory harness — locally qualified, October 31, 2026

The distinct `torch-startup-exact-vector-resource-v1` harness passes all **100
source + 100 sealed** cases. The production seal has **983 manifest files / 984
regular archive members**; full source/member/hash, authentic native proof and
1,956 prior-file preservation checks pass. Original 68 main recipes, five
qualified A3 files and all 128+128 / 56+56 native correctness receipts remain
unchanged.

Actual owned-reader startup exposed frozen metadata at the qualified producer
boundary. A separately frozen <=16-KiB metadata view preserves exact canonical
bytes and immutable state, restoring the getter before the producer connection.
Full local runtime/host/controller and independent replay/tamper checks cover this
new wrapper; prior native receipts are not claimed to cover it. Earlier packaging
and local disk failures are retained. Temporary test clones alone share large
read-only files; production/database copies remain independent.

**One new 1h/4CPU/32GiB zero-search resource handoff is ready and unlaunched.**
Original scans, ten-reader/max-six lifetimes, orders/holds, cleanup, strict target
references and aggregate peak +2 GiB reserve +2 GiB workspace/no-positive-limit
rule remain unchanged. All earlier allowances are spent. Offline transfer checks
use SSH/SCP stubs; no native job or actual SSH/SQL/search runs here. Actual memory,
workload, quality, A/A, performance, savings and full B2f remain unqualified.

[Readiness and findings](../../../research/fannagent-startup-exact-vector-resource-readiness-2026-10-31.md),
[freeze](../../../trials/torch-reviews-startup-exact-vector-resource-v1/RESOURCE-FREEZE.json),
[metadata amendment](../../../trials/torch-reviews-startup-exact-vector-resource-v1/RESOURCE-AMENDMENT-1.json),
[release audit](../../../trials/torch-reviews-startup-exact-vector-resource-v1/release-verification.json),
[current Mac/Torch commands](../../../trials/torch-reviews-startup-exact-vector-resource-v1/COMMANDS.txt),
[decision](../verification/startup-exact-vector-resource-readiness.json).

## A3 resource login path correction — October 31, 2026

The initial resource login verified 7,297 files and then failed because the
inherited protection helper searched for the old exact package beside the
embedded reference. The failure occurred before scheduler testing or reservation
creation. **The resource allowance remains unspent for this attempt.**

The separate correction verifies the complete preserved main home package and
spent binding before invoking unchanged original protection in its original
home/sibling context; caller import paths restore on exceptions. No historical
checks, old source, limits or scientific inputs change. All **110 source + 110
sealed** cases pass, retaining all original 100 IDs; original 128+128/56+56 proofs,
initial artifact and **3,035 prior files** are unchanged. The new seal contains
984 manifest files / 985 regular archive members.

Use the corrected commands below for the **same** unspent one-hour/4CPU/32GiB
zero-search allowance and fixed reservation. Separate transfer/extraction paths
preserve the first artifact; the checked continuation stops for any existing
resource reservation/binding. No actual SSH, SQL, job or search ran here; native
memory and full B2f remain unqualified. The previous E352 handoff is superseded.

[Cause and correction](../../../research/fannagent-startup-exact-vector-resource-path-fix-2026-10-31.md),
[freeze](../../../trials/torch-reviews-startup-exact-vector-resource-v1-path-fix/PATH-FIX-FREEZE.json),
[release audit](../../../trials/torch-reviews-startup-exact-vector-resource-v1-path-fix/release-verification.json),
[current short commands](../../../trials/torch-reviews-startup-exact-vector-resource-v1-path-fix/NEXT-COMMANDS.txt),
[decision](../verification/startup-exact-vector-resource-path-fix.json).

## A3 resource job21542975 — terminal failure reported October31,2026

Campaign `reviews-startup-exact-vector-resource-v1-20261031T203754Z.0lyxk3k2`,
array task **21542975_0**, is reported **FAILED1:0 after16m35s**. Runtime status
reports both epochs,200 admissions/zero executions,ten readers/maxsix,one
snapshot/four data scans and final integrity complete, with zero searches.
Memory sampler loss/finalization and guest cleanup failed, so native memory
qualification is not established. Detailed cause/source/coverage/integrity
verification requires the full downloaded raw; RSS fragments imply no margin or
OOM verdict.

The resource allowance is **spent; no resubmission or new capsule is released**.
Current commands collect every terminal failure file, then download/checksum and
ingest as data. All prior source/seals/proofs/limits stay unchanged; full B2f held.

[Reported assessment](../../../trials/torch-reviews-startup-exact-vector-resource-v1-path-fix/reported-failure-2026-10-31/assessment.json),
[current collection/download commands](../../../trials/torch-reviews-startup-exact-vector-resource-v1-path-fix/reported-failure-2026-10-31/COMMANDS.txt),
[decision](../verification/startup-exact-vector-resource-reported-failure.json).

## A3 resource job 21542975 — independent failed-return audit, October 31, 2026

The downloaded 56-member return and all 49 host/34 guest lock bindings verify.
Both completion flags remain false. Exact provenance, both epochs, 200 admission-only
requests, ten readers/max six, one snapshot/four data scans, retained roots, final
scientific identities and zero searches reconcile. Retained source (2,587 files)
and protected historical inventories match before/after; all 3,035 prior local
files and 128+128/56+56 native case proofs remain unchanged.

The recorded finite-ancestor aggregate peak is **28.700241 GiB**. Adding the frozen
2 GiB reserve and 2 GiB workspace gives **32.700241 GiB**, above the unchanged32GiB
cap. The sampler also fails on missing live-process RSS counters; cleanup lacks
working-copy clean-shutdown certification. A sampler-only correction is insufficient.
The generic cleanup deadline text is emitted before the actual600-second stage
or global deadline and does not justify extending time. Zero recorded relevant
OOM/max-event deltas do not cover the missing final observation period.

Close failed/unqualified; the allowance is spent. Next is offline total-charge,
sampler-lifecycle and shutdown design review, with a prospective freeze before
any correction. No retry, new capsule, Torch command or full B2f release.

[Independent audit](../../../trials/torch-reviews-startup-exact-vector-resource-v1-path-fix/postrun-audit-2026-10-31/returned-verification.json),
[failure analysis](../../../trials/torch-reviews-startup-exact-vector-resource-v1-path-fix/postrun-audit-2026-10-31/REPORT.md),
[decision](../verification/startup-exact-vector-resource-postrun.json).

## A3 offline memory/lifecycle review and correction — October 31, 2026

The review preserves the failed native resource verdict: recorded aggregate
28.700241GiB +2GiB reserve +2GiB workspace exceeds32GiB. File and anonymous
components both matter; no causal saving or justified single storage patch is
established. Main/producer/memory-decision code, limits, scans and root lifetime
remain unchanged. Memory qualification stays held.

A pre-code freeze and separate replay/cooperative-cancellation amendments precede isolated sampling and
cancellation/shutdown corrections. PID/starttime bracketing and bounded exit
re-observation retain fail-closed live-counter checks and durable diagnostics.
Ordinary cancellation records a request and the next existing budget check rejects
further ordinary work before driver execution; the handler cannot interrupt
cleanup entry. Cancellation remains failed; original deadlines
and all shutdown certification requirements remain. Strict replay rejects missing,
nonzero or mistyped cancellation evidence and observer-loss requests after relocking.

**142 source +142 independent code-snapshot checks** pass, preserving all110
inherited cases/test files,128+128/56+56 native proofs,five A3 files and5,163prior
files. Code snapshots are offline checks, not sealed native qualification. Native
CLI/production capsule build are disabled. Zero SQL/search/job actions; no Torch
command, new capsule/entitlement, spent-allowance retry or full B2f release.

Next: separate source-backed memory remedy design, frozen before implementation.

[Review and correction report](../../../trials/torch-reviews-startup-exact-vector-resource-offline-review-v1/REPORT.md),
[freeze](../../../trials/torch-reviews-startup-exact-vector-resource-offline-review-v1/OFFLINE-FREEZE.json),
[verification](../../../trials/torch-reviews-startup-exact-vector-resource-offline-review-v1/offline-verification.json),
[decision](../verification/startup-exact-vector-resource-offline-review.json).

## A3 exact adaptive memory-component design — October 31, 2026

The pre-code64-row probe confirms overlapping per-vector float32 conversion
buffers in the unchanged Snapshot constructor. One prospectively frozen codec
retains3072-byte codewords only if decoding reproduces every original binary64
bit; otherwise it keeps the original6144-byte payload. Integer categories/values,
signed zero, canonical identity and float32 matrix bits remain exact. Three-slot
headers do not grow; compact constructor input views avoid separate row data.
The required mutable matrix remains independent of immutable row payloads.

**94 source +94 code-snapshot cases** pass: all56original A3 cases unchanged plus38
new exactness/consumer/ownership/allocation/reference cases. The5,445prior files,
128+128 main/56+56 native proofs and142+142 lifecycle artifacts are unchanged.
The initial wrong-system-NumPy pin is preserved with failed receipts; a frozen
amendment pins the existing approved2.5.3reference before correction, with no
wildcard/dependency/limit change. Real SQL/search/DB/network/process/job actions
remain zero.

This is a <=64-row component/consumer fixture, with no producer integration or
native release. Native compactability, formatter CPU cost, exact-image correctness
and total charge remain unqualified. Maximum payload-only arithmetic exceeds the
known deficit by only7.4MiB if every row compacts; that is no margin verdict.
Next: separately frozen production integration/source/release/retention/target
proof design. No native capsule/command/entitlement or spent-allowance repeat.

[Design/report](../../../trials/torch-reviews-startup-exact-vector-memory-remedy-v1/REPORT.md),
[freeze](../../../trials/torch-reviews-startup-exact-vector-memory-remedy-v1/MEMORY-FREEZE.json),
[verification](../../../trials/torch-reviews-startup-exact-vector-memory-remedy-v1/verification.json),
[decision](../verification/startup-exact-vector-memory-remedy.json).

## A3 adaptive startup integration — November 1, 2026

A prospectively frozen isolated harness integrates the exact adaptive codec with
startup and the corrected lifecycle. The original ordered SQL/client cursor,
Snapshot constructor, validation and atomic shared-cache publication are kept;
request admission is identical. Compact/raw64 payloads preserve binary64 bits,
integer categories, canonical identity and float32 matrix bits. Retention and
replay bind new source/target/origin/count/payload/matrix proofs while preserving
all existing strict checks and the unchanged limits and memory decision.

**272 source +272 code-snapshot cases** pass, including all236preserved cases and
36new producer/runtime/failure/tampering tests. All5,526prior files and original
main128+128/A3 56+56native proofs remain unchanged. Exact SIF/OCI data inspection
reconciles ten selected source/ELF files, formatter and full driver references.
Local3.12.7 is explicitly rejected as target3.12.15; target code was not executed.

This completes offline integration/reference checking. Full-size CPU cost,
compactability, exact-image runtime behavior, native shutdown and aggregate
headroom remain unqualified. Native builders/entries/release remain disabled;
synthetic replay cannot qualify the correction. No Torch launch, new capsule,
command, reservation, entitlement, spent-allowance reuse or B2f release.
Next: separate exact-image correctness and CPU-budget review.

[Report](../../../trials/torch-reviews-startup-exact-vector-startup-integration-v1/REPORT.md),
[freeze](../../../trials/torch-reviews-startup-exact-vector-startup-integration-v1/STARTUP-FREEZE.json),
[target references](../../../trials/torch-reviews-startup-exact-vector-startup-integration-v1/TARGET-REFERENCE.json),
[verification](../../../trials/torch-reviews-startup-exact-vector-startup-integration-v1/verification.json),
[decision](../verification/startup-exact-vector-startup-integration.json).

## A3 exact-image correctness and CPU review — November 1, 2026

The separately frozen review runs the exact cached image with read-only inputs,
no network, unchanged4CPU/32GiB maxima and finite deadlines. Its full source
attempt faults while importing PyArrow under amd64 emulation on this ARM Mac,
before test collection finishes. Standalone import diagnostics reproduce that
failure; Python3.12.15,NumPy2.5.3andpsycopg3.3.6import successfully. The failed
attempt/explicit termination and all diagnostic logs are preserved. No production
code, dependency, allocator/SIMD setting or strict reference was changed.

A further frozen kernel-only scope passes **32source+32snapshot cases** using the
real codec, original canonical/frame encoder and NumPy matrix bits. It does not
import/stub PyArrow or replace Snapshot/full-suite qualification. All original
272+272local cases and5,697prior files remain unchanged; four local review guard
cases also pass. CPU profiling confirms substantial serial decoder work; Mac
projections omit native overhead and emulated timings cannot certify Torch's
600-second stage. Full target correctness, native CPU/memory and B2f remain held.

Next: separately freeze a compatible non-emulatedx86_64exact-image execution
path for the complete correctness suite and full startup-stage CPU/wall review.
No Torch job, native capsule/command, reservation, new entitlement or reuse of any
spent allowance is released here.

[Report](../../../trials/torch-reviews-startup-exact-vector-exact-image-review-v1/REPORT.md),
[freeze](../../../trials/torch-reviews-startup-exact-vector-exact-image-review-v1/REVIEW-FREEZE.json),
[CPU review](../../../trials/torch-reviews-startup-exact-vector-exact-image-review-v1/CPU-BUDGET-REVIEW.json),
[verification](../../../trials/torch-reviews-startup-exact-vector-exact-image-review-v1/verification.json),
[decision](../verification/startup-exact-vector-exact-image-review.json).

## A3 non-emulated x86_64 qualification preparation — November 1, 2026

A prospective freeze prepares one distinct, unlaunched1h/4physicalCPU/32GiB
correctness and bounded CPU qualification. New campaign/reservation paths and
both durable/in-memory dispatch guards keep every older allowance closed.
Native proof requires x86 ELF/vendor evidence, no emulation, four distinct physical
cores, full exact image/private-driver references, source/sealed cases and strict
final source/image/cleanup/timing/lock/scheduler evidence. Original main/A3 source,
all tests/limits/scans/root lifetimes and aggregate memory rule remain unchanged.

Local**128+128main/276+276A3/39+39controller cases**, all60CPU samples and the
1,602-file/member archive pass.5,757prior files and original native proofs remain
unchanged. The failed bytecode inventory check is preserved; qualification child
setup is corrected and a fresh complete mirror passes without relaxing checks.
The exact transfer/command script is tested offline with local stubs and short
SSH sockets; no actual SSH/upload/job/search or spent-allowance reuse occurred.

Use only the new command file. One explicit submit is allowed after upload/login
verification; repeat status/terminal collection, never submit. Native target and
CPU measurements remain pending. Bounded CPU projections cannot release full
startup CPU, memory, resource or B2f qualification.

[Freeze](../../../trials/torch-reviews-startup-adaptive-x86-qualification-v1/QUALIFICATION-FREEZE.json),
[release verification](../../../trials/torch-reviews-startup-adaptive-x86-qualification-v1/release-verification.json),
[commands](../../../trials/torch-reviews-startup-adaptive-x86-qualification-v1/COMMANDS.txt),
[report](../../../trials/torch-reviews-startup-adaptive-x86-qualification-v1/REPORT.md),
[decision](../verification/startup-adaptive-x86-qualification.json).

## A3 native x86 qualification failed; allowance closed — November 1, 2026

User-run **21595967** failed at the A3 source suite's frozen 600-second cap,
22m46s overall. Both unchanged main suites pass **128/128**. A3 records 165
passes and one interrupted case, with 110 source cases, all 276 sealed cases
and the CPU probe unstarted. No assertion failure is recorded before the alarm.
The partial result cannot qualify full adaptive target correctness or CPU.

All 38 return members and extracted bytes, 24 guest/33 host lock hashes/coverage,
exact native hardware/reference, source/image preservation and cleanup verify.
Both failed locks remain `complete:false`; the unchanged strict analyzer rejects
the allocation. All 5,757 prior files, 1,602 capsule files and original sources,
tests, limits and aggregate memory rule remain unchanged; searches/real SQL and
provider calls remain zero. This allowance and all older allowances are spent.

The traces show continued progress through costly resource fixtures/replay, but
do not separate hashing, filesystem wait and other work. Next is offline fixture
construction/verification/I/O feasibility and design under unchanged caps. Freeze
any justified correction before implementation. No Torch command, retry, new
allowance, memory/resource or B2f release is issued. The earlier preparation
record and command file are historical; do not repeat their submit command.

[Report](../../../trials/torch-reviews-startup-adaptive-x86-qualification-v1/postrun-audit-2026-11-01/REPORT.md),
[verification](../../../trials/torch-reviews-startup-adaptive-x86-qualification-v1/postrun-audit-2026-11-01/verification.json),
[timings](../../../trials/torch-reviews-startup-adaptive-x86-qualification-v1/postrun-audit-2026-11-01/case-timing.json),
[decision](../verification/startup-adaptive-x86-qualification-postrun.json).

## Offline A3 fixture-cost review and path correction — November 1, 2026

A complete guarded 276-case profile identifies substantial full verification,
hashing and path work. The original path checker eagerly constructs absolute
ancestors above its root that it immediately discards. A separate prospective
freeze precedes a standalone offline wrapper that avoids those objects while
retaining every fresh path resolution/symlink observation and full digest.
Original main/A3 source, tests, fixtures, whole verifiers and limits are unchanged.

**128+128 main, 276+276 A3 and 26+26 helper cases pass.** Each A3 run keeps all
292,688 original hashes, 341,707 fresh resolutions, 975,641 symlink observations
and identical verifier/build/copy/reseal work. All 7,490 prior files verify.
Profiled local path time is 57.879→44.197 seconds; these diagnostic observations
do not establish a native speed factor or fit under the 600-second cap.

Next: separate complete-budget native feasibility/storage and verification-cost
design. Exact native target, CPU/memory/resource and B2f remain held. Every
allowance, including 21595967, remains spent. Zero searches/real SQL/providers;
no native job, capsule, command or retry is released.

[Review freeze](../../../trials/torch-reviews-startup-adaptive-fixture-cost-v1/REVIEW-FREEZE.json),
[correction freeze](../../../trials/torch-reviews-startup-adaptive-fixture-cost-v1/CORRECTION-FREEZE.json),
[report](../../../trials/torch-reviews-startup-adaptive-fixture-cost-v1/REPORT.md),
[verification](../../../trials/torch-reviews-startup-adaptive-fixture-cost-v1/verification.json),
[decision](../verification/startup-adaptive-fixture-cost.json).

## A3 native budget/storage review; local replay held — November 1, 2026

The fixed time caps close, including startup inside the existing240s host
preflight. A prospectively frozen offline prototype stages exact archive data,
keeps every original check/path/read-only destination and rejects incomplete
storage/quota records. Its conditional6.87GiB/22,498-entry capacity envelope fits
the existing8GiB/30,000guards; actual target capacity, speed, memory and failure
retention remain unproved. No native host/controller or original source is changed.

**35+35new unit checks pass; all1,602archive members and10,076prior files verify.**
The real Mac has about4GiBfree and the unchanged8GiBguard stops staging before
output creation. Full real staging and a new128+128/276+276integrated replay have
not run; all previous passing cases/proofs remain preserved. Initial unit errors
and exact source are retained; synthetic unit capacity never qualifies the real
admission. No limit is lowered and no prior artifact is deleted.

Next requires at least8GiBreal local headroom and full staging/replay, followed
by any separately justified native handoff with real capacity/timing/retention
proofs. All allowances remain spent; no Torch job, search, provider call, native
capsule/command, reuse or full B2f release.

[Review freeze](../../../trials/torch-reviews-startup-adaptive-budget-storage-v1/REVIEW-FREEZE.json),
[correction freeze](../../../trials/torch-reviews-startup-adaptive-budget-storage-v1/CORRECTION-FREEZE.json),
[report](../../../trials/torch-reviews-startup-adaptive-budget-storage-v1/REPORT.md),
[verification](../../../trials/torch-reviews-startup-adaptive-budget-storage-v1/verification.json),
[decision](../verification/startup-adaptive-budget-storage.json).

## A3 Mac capacity recovered; full local replay next — November 1, 2026

Twenty-two byte-identical frozen inputs now use independent copy-on-write
clones. Every prior path/byte and existing hardlink group remains; all173,943
protected full hashes and54 candidate metadata/creation-time proofs pass.
Available space is10.40GiB, above unchanged8GiB staging admission and the
prospective10GiB cleanup target. Verified payload backup/recovery, initial
preparation failures and the previous roadmap/index are retained. No old test
proof is relabelled and no science/code/guard changes.

Full exact-archive local staging and integrated replay are next and have not
run. Native qualification and every spent allowance remain closed. No Torch,
ANN/exact search, provider call, native command/capsule or allowance reuse.

[Plan](../../../trials/torch-reviews-a3-mac-space-preservation-v1/SPACE-PLAN.json),
[report](../../../trials/torch-reviews-a3-mac-space-preservation-v1/REPORT.md),
[verification](../../../trials/torch-reviews-a3-mac-space-preservation-v1/verification.json),
[decision](../verification/a3-mac-space-preservation.json).

## A3 full local staging and integrated replay pass — November 1, 2026

The unchanged exact archive stages and verifies all1,602 files, with three
original semantic checks and final source/stage/view preservation. Full local
reference/origins, all128+128 main/276+276 A3/35+35 storage/26+26 path-helper
cases and60 CPU samples pass. Original verification work, serial fixture
lifetimes and every limit remain intact; all185,133 prior files verify unchanged.

Three local setup failures are retained: unsupported Darwin VM hook,
shell interpreter missing psycopg, then a parent PermissionError after all main
and A3 source cases pass. Prospectively frozen supervisor-only
corrections use observed owned-process RSS and the existing full-reference
project environment, with owned-PID/exit proof and telemetry outside the tool
sandbox. No dependency or original implementation/test changes.

Local staging/replay is complete. Native target, CPU, quota/storage, aggregate
memory/shutdown/resource, binding/controller and failure-retention gates remain
held. No Torch, search, real SQL/provider call, native capsule/command or spent
allowance reuse.

[Execution freeze](../../../trials/torch-reviews-startup-adaptive-budget-storage-v1/full-local-replay-20261101-v4/EXECUTION-FREEZE.json),
[report](../../../trials/torch-reviews-startup-adaptive-budget-storage-v1/full-local-replay-20261101-v4/REPORT.md),
[verification](../../../trials/torch-reviews-startup-adaptive-budget-storage-v1/full-local-replay-20261101-v4/verification.json),
[decision](../verification/startup-adaptive-full-local-replay.json).

## A3 offline native harness integration verified — November 1, 2026

The frozen separate host/guest/controller core and disabled target adapters pass
81+81 new checks, all39+39 original controller/35+35 storage/26+26 path helpers,
128+128 main/276+276 A3 cases and60 CPU samples. Complete references/IDs/origins,
fresh verification work, fixture lifetimes and all limits remain unchanged.
All189,345 prior files verify;17 exact COW replacements preserve paths/bytes/metadata.

Direct persistent raw output plus bounded lossless failed-work capture restores
all1,000 files/597MB in a real fixture proof with under2MiB of diagnostics. The
original32MiB/256-file return and startup/guest/cleanup/post/outer budgets hold
locally. Initial failed checks and exact source snapshots remain preserved.

Native entry/dispatch stays closed: no scheduler, grant, Torch/search/provider,
native handoff or allowance reuse. Real native authority, target/runtime/CPU,
storage/persistence/retention and aggregate-memory/resource gates remain held.

[Design](../../../trials/torch-reviews-startup-native-harness-integration-v1/DESIGN-FREEZE.json),
[report](../../../trials/torch-reviews-startup-native-harness-integration-v1/REPORT.md),
[verification](../../../trials/torch-reviews-startup-native-harness-integration-v1/verification.json),
[decision](../verification/startup-native-harness-integration.json).

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

## A3 offline native release review complete; handoff HOLD — November 2, 2026

D128 / roadmap v1.80. Independent source/trace review freezes and corrects five
bounded lifecycle/admission gaps in a separate closed candidate: observed ready
arrival, independent original signals, publication inside original endpoints,
required whole-group ownership control and complete frozen binding/admission.
All1,280 local checks and60 CPU samples pass, including every original test plus
55+55 release regressions. Full staging, exact references, strict hashes/paths,
publication-inclusive completion, parent-observed exit and195,784 prior files /
27,123,306,137 bytes verify. The unchanged real597MB recovery proof rehashes in
full without another data copy. D127 source/evidence remain intact.

Native qualification handoff stays HOLD: no concrete qualified authority/group
or live admission/return backend and no fresh authorization/allowance. A future
job must validate its live native facts under unchanged limits and produce the
complete exact-target/CPU results. Downstream resource/B2f additionally needs
aggregate memory/events/shutdown/source/return qualification. No Torch, native
capsule/command release, search, new grant or spent-allowance reuse occurred.

[Review freeze](../../../trials/torch-reviews-startup-native-release-review-v1/REVIEW-FREEZE.json),
[correction freeze](../../../trials/torch-reviews-startup-native-release-review-v1/CORRECTION-FREEZE.json),
[findings](../../../trials/torch-reviews-startup-native-release-review-v1/release-findings.json),
[verification](../../../trials/torch-reviews-startup-native-release-review-v1/verification.json),
[report](../../../trials/torch-reviews-startup-native-release-review-v1/REPORT.md),
[decision](../verification/startup-native-release-review.json).

## A3 offline authority/ownership backend verified — November 2, 2026

D129 / roadmap v1.81. A separate frozen backend implements strict independent
permission/site anchors, durable single-use claims, a Linux PID-descriptor
subreaper guardian, blocked-before-exec registration and one combined read
ledger. It proves shutdown through direct status, kernel ECHILD, terminal pipe
proof and independent guardian exit. Authority/observer loss holds qualification
while only registered descriptors retain bounded cleanup capability.

All 642 fresh checks pass:68+68 models,17+17 real local Linux cases,136+136 old
integration,39+39 controller,35+35 storage and26+26 path. All D128 source/tests
are byte-identical;200,143 prior files /28,833,842,186 bytes verify unchanged.
The existing128+128 main/276+276 A3/60 CPU proof is freshly reconciled without
science re-execution or new full staging. Earlier candidates/failures are kept.

Production roots remain empty. Actual site-attestation acquisition/provisioning,
host/guest adapter wiring and cross-process handoff are pending; native release
and target/CPU/memory/resource/B2f remain HOLD. No Torch/SSH, searches, SQL/provider
calls, new grant, capsule/command release or spent-allowance reuse occurred.

[Design](../../../trials/torch-reviews-startup-native-authority-ownership-v1/DESIGN-FREEZE.json),
[final pin](../../../trials/torch-reviews-startup-native-authority-ownership-v1/IMPLEMENTATION-PIN.json),
[verification](../../../trials/torch-reviews-startup-native-authority-ownership-v1/verification.json),
[report](../../../trials/torch-reviews-startup-native-authority-ownership-v1/REPORT.md),
[decision](../verification/startup-native-authority-ownership.json).

## A3 offline native integration and pending package verified — November 2, 2026

D130 / roadmap v1.82. Frozen host/guest integration, nested ownership, bounded shared read accounting and a separately PLAN-bound stable-site login adapter pass1,656 checks plus60 CPU measurements. Both full main128+128 and A3276+276 suites are rerun with strict unchanged references/verification/limits. All205,032 protected files/30,662,112,708 bytes verify unchanged; old43 backend files are byte-identical. Earlier failures/replays and every test are retained.

The exact1,768-file package and standalone installer/CLI are verified. Mac upload and zero-allocation Torch installation/site-check commands are ready. No Torch/SSH execution, searches, SQL/provider calls, fresh approval or spent-allowance reuse occurred. Review actual site/account output and obtain distinct explicit authorization before one new qualification allocation. Native target/CPU/resource/B2f remain HOLD.

[Report](../../../trials/torch-reviews-startup-native-integrated-release-v1/REPORT.md),
[final verification](../../../trials/torch-reviews-startup-native-integrated-release-v1/final/completion-checks.json),
[package](../../../trials/torch-reviews-startup-native-integrated-release-v1/final/package-verification.json),
[Torch read-only command](../../../trials/torch-reviews-startup-native-integrated-release-v1/final/TORCH-SITE-CHECK.txt),
[decision](../verification/startup-native-integrated-release.json).

## A3 installed-site compatibility verified — November 2, 2026

D131 / roadmap v1.83. Live metadata isolates the failed ancestor to unwritable UID1001/GID1001 /opt/slurm, with root-owned clients/bin/other ancestors. A prospectively frozen, exact prefix policy applies before login and allocated-host admission. All71 scientific integration files, tests, references, strict verification and limits remain unchanged.722 fresh checks,211,278 prior hashes/32,907,014,918 bytes and fresh reconciliation of the full old128+128 main/276+276 A3/60 CPU proof pass. No new scientific replay or large staging is performed.

The replacement immutable package and read-only installation/site/account command are ready. Actual authenticated output and current project associations are pending; torch.env still says users and is not edited. No Torch/SSH execution, searches, new grant or spent-allowance reuse occurred. A distinct new authorization remains required before any future allocation. Native target/CPU/resource/B2f stay HOLD.

[Design](../../../trials/torch-reviews-startup-native-site-compatibility-v1/DESIGN-FREEZE.json),
[report](../../../trials/torch-reviews-startup-native-site-compatibility-v1/REPORT.md),
[verification](../../../trials/torch-reviews-startup-native-site-compatibility-v1/verification.json),
[read-only Torch command](../../../trials/torch-reviews-startup-native-site-compatibility-v1/TORCH-SITE-CHECK.txt),
[decision](../verification/startup-native-site-compatibility.json).

## A3 live site/project readiness reviewed — November 3, 2026

D132 / roadmap v1.84. The user-run exact package installation and actual Torch/auth-munge/site-policy output review passes. The intended project association exists, cs is UP with no displayed conflicting restriction, and the unchanged conservative quota parser passes. The remaining users environment setting is handled by a per-invocation project override; torch.env and every package/source/test/limit stay unchanged.

The exact conditional approval-and-submit block is prepared and locally exercised with stubs. It would explicitly authorize ONE distinct new1hour/4physicalCPU/32GiB zero-search/no-retry allocation and submit once. It has not run: no new approval, allowance, remote command or job is issued by the assistant. Every previous allowance remains spent. Actual native correctness/CPU/storage/deadline/cleanup/return qualification remains prospective, with memory/resource/B2f later.

[Review](../../../trials/torch-reviews-startup-native-site-compatibility-v1/site-readiness-review-2026-11-03/review.json),
[conditional commands](../../../trials/torch-reviews-startup-native-site-compatibility-v1/site-readiness-review-2026-11-03/TORCH-APPROVE-AND-SUBMIT-PENDING.txt),
[decision](../verification/startup-native-site-readiness.json).

## A3 native qualification job21756110 submitted — November 3, 2026

D133 / roadmap v1.85. The user explicitly records the distinct new1hour/4physicalCPU/32GiB zero-search/no-retry allowance and submits job21756110. PLAN/manifest/account match the verified619d4288ca7a candidate. The allowance is committed and cannot be reused; every older spent allowance remains closed. No code/package/test/reference/limit change accompanies dispatch.

Queue/running/terminal state and native scientific/CPU/resource outcome remain pending. Submission alone confers no qualification verdict. The assistant ran no remote command and performs no retry. Next is read-only status, then collection under the original caps after terminal accounting.

[Submission](../../../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/submission-return.json),
[review](../../../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/review.json),
[status command](../../../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/TORCH-STATUS.txt),
[decision](../verification/startup-native-qualification-submitted.json).

## A3 job21756110 failed preflight; allowance closed — November 3, 2026

D134 / roadmap v1.86. User status records FAILED1:0/38s with ValueError Outside the frozen site-prefix scope and native qualification false. This distinct allowance is spent and cannot be approved/submitted again. Actual rejected allocated-node path/role remains unknown until the full scheduler traceback/raw is collected. The preflight batch427216K MaxRSS is not a scientific memory verdict.

Source/package/trust guards/tests/strict scientific verification/limits are unchanged. Exact terminal collection/traceback and a strictly pinned DTN download helper are prepared; four download fixture checks pass, with no actual remote action or new allocation. Preserve all evidence and freeze any justified correction only after independent raw review. Native target/CPU/resource/B2f remain unqualified.

[Failure](../../../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/failure-review-2026-11-03/reported-terminal.json),
[review](../../../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/failure-review-2026-11-03/review.json),
[collect/traceback command](../../../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/failure-review-2026-11-03/TORCH-COLLECT-AND-TRACEBACK.txt),
[decision](../verification/startup-native-qualification-preflight-failure.json).

## A3 allocated SLURM_CONF failure isolated — November 3, 2026

D135 / roadmap v1.87. The original scheduler traceback identifies configuration environment validation as the gate that failed in21756110. Slurm and recorded Apptainer executable validation completed; the first Slurm probe and scientific phases were not launched. The actual SLURM_CONF value/resolved path and rejected metadata are not logged in the trace. Remote terminal collection succeeds; local full return download/verification is pending.

No code/package/guard/test/strict verification/limit change or new allowance/retry occurs. Download the collected raw before freezing any justified correction; every spent allowance remains closed and native results remain unqualified.

[Finding](../../../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/failure-review-2026-11-03/slurm-conf-trace-review/finding.json),
[download helper](../../../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/failure-review-2026-11-03/download-return-21756110.sh),
[decision](../verification/startup-native-slurm-conf-failure-review.json).

## A3 complete failed21756110return reviewed — November 3, 2026

D136 / roadmap v1.88. The complete return independently verifies:9files/16,283bytes; every member inspected without extraction/execution. Approval, plan, account, dispatch and FAILED1:0/38seconds reconcile. The exact SLURM_CONF validation gate failed before first Slurm probe/science, but the allocated variable value/resolved path/rejected metadata are absent. No specific trust-policy correction is justified.

A checked login-only metadata/accounting command preserves the existing policy and bounded queries, filters unrelated environment values and requests no allocation. Stored submission/current login evidence cannot alone establish historical runtime injection or compute-node metadata. All71scientific files, site source/package pins,128+128main/276+276A3 tests, strict verification, limits and prior evidence remain unchanged. No scientific tests rerun for this evidence review, no assistant remote command, no retry, no new allowance; native results remain unqualified.

[Review](../../../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/failure-review-2026-11-03/raw-return-review/README.md),
[diagnostic](../../../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/failure-review-2026-11-03/raw-return-review/TORCH-CONFIG-METADATA.txt),
[decision](../verification/startup-native-return-21756110-review.json).

## A3 configuration metadata unavailable; site evidence request ready — November 3, 2026

D137 / roadmap v1.89. The user-run login-only diagnostic succeeds:21756110FAILED1:0 on cs624, current login SLURM_CONF unset, stored environment NONE. The original launcher does not set/source SLURM_CONF; allocated value/path/component metadata remain unknown. No exact new trust exception or environment bypass is justified.

A local unsent request to NYU HPC asks for existing site/log path/link/UID/GID/mode/ACL/provenance evidence, distinguishes historical/current layout and explicitly requests no resubmission or diagnostic allocation. No assistant message is sent. Complete original packet/source/evidence pins verify unchanged; all71scientific files,128+128main/276+276A3 tests, strict verification, limits and prior evidence remain preserved. Native qualification remains incomplete, and all allowances stay spent/closed.

[Finding](../../../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/failure-review-2026-11-03/metadata-unavailable-review/finding.json),
[unsent request](../../../trials/torch-reviews-startup-native-site-compatibility-v1/submission-21756110/failure-review-2026-11-03/metadata-unavailable-review/NYU-HPC-REQUEST.txt),
[decision](../verification/startup-native-configuration-metadata-unavailable.json).

## A3 alternate client-configuration design frozen — November 3, 2026

D138 / roadmap v1.90. Independent matching Slurm25.05.4 source review supports an alternate prospective route: controller-exported snapshot from the working trusted login client, full dependency review, new PLAN pin, immutable Linux sealed input for our bounded scheduler queries. Future runs can conditionally avoid dependence on the unknown21756110cache path. Historical support remains optional.

No export, adapter, scheduler command or scientific test ran. Export permissions/completeness, serialized syntax, plugins/Includes/AuthInfo/relative auxiliary closure, exact-version sealed-input compatibility and compute-node portability remain gates. Existing arbitrary-path root/loader checks, controller/auth/job/kernel authority and original strict scientific verification remain required. All71scientific source files and site/evidence pins verify unchanged; all128+128main/276+276A3 tests, limits and prior artifacts preserved. No fresh grant or retry; native qualification remains incomplete.

[Freeze](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/DESIGN-FREEZE.json),
[independent review](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/REVIEW.txt),
[decision](../verification/startup-native-pinned-client-configuration-design.json).

## A3 login-only configuration capture command ready — November 3, 2026

D139 / roadmap v1.91. A separate capture helper is implemented after its capture freeze.32source+32independent snapshot checks pass, including real local fixture-process file-size/output/deadline/group cleanup and exact original packet/reference verification. Torch identity/RPCs are mocked; no native Slurm, Torch export/job or scientific work occurs locally. Existing34site/evidence pins,71scientific files, all128+128main/276+276A3 tests, strict verification, limits and prior full replay/60CPU proof remain unchanged.

The checked block performs original verification/quota/client/anchor checks and one export to a fresh private path, retains bounded logs/SHA receipt and holds any unsafe/incomplete/changed output without retry. It does not load/admit the configuration. User-run login capture is next; syntax/dependency/portable sealed-input validation and native qualification remain open. All spent allowances stay closed; no new grant or retry.

[Capture command](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/capture-v1/TORCH-CAPTURE.txt),
[verification](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/capture-v1/verification.json),
[decision](../verification/startup-native-client-configuration-capture-ready.json).

## A3 current configuration capture reported; exact download ready — November 3, 2026

D140 / roadmap v1.92. User reports successful login-only capture:16,647bytes/config SHA ba998cfda785eee87ef65023a8fe2caf4f7c3734665eb15af5b76d5a2b603ea6 and manifest0ef4872fd4a60229dd5545d764bebc85998d036347d5555ba1be6ed9d2c9f6f2, expected client/controller/auth and zero allocations/searches. Actual10file raw is not yet local. A pinned-key Mac download helper passes14local adversarial/mocked transfer cases; no real transfer or assistant remote command occurs. No remote packaging/export retry is needed.

Full content/manifest/receipt/command/quota verification and actual directive/dependency/portable sealed-input review remain required. Original capture/science/admission code, all128+128main/276+276A3 tests, strict verification, limits and prior evidence remain preserved. Config/native admission remains false and all spent allowances stay closed; no new grant/job.

[Receipt](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/capture-return-9rki9gow/reported-receipt.json),
[Mac download](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/capture-return-9rki9gow/download-return.sh),
[decision](../verification/startup-native-configuration-capture-reported.json).

## A3 actual snapshot reviewed; scoped use frozen — November 3, 2026

D141 / roadmap v1.93. All10capturefiles/40,601bytes verify independently. The16,647byte snapshot has192active records/noInclude,130recognized top-level keys under native case-insensitive spelling,374defined nodes and55partitions with valid node references. Matching-tag source review covers19files and preserves retrieval/schema-review prechecks. No native parser or deployed library equivalence is claimed.

Retain captured bytes unchanged. Ordinary MUNGE client auth under the existing environment filter does not need daemon JWT alternatives, so no private JWT keys are requested. Several client plugin initializers and relative auxiliary inputs still require installed dependency evidence. A shorter exported InteractiveStepOptions value precludes general Slurm equivalence; the frozen future capability is read-only queries only, with opaque sealed bytes, verified dependencies and all original trust/auth/job/kernel guards.

No adapter/config admission, Torch command/job, new grant or spent retry occurs. Original capture/download/site/science pins,71scientific files and full exact packet/semantic references verify unchanged. All128+128main/276+276A3 tests, strict verification, limits and previous evidence remain preserved. Next is isolated locally verified compatibility/dependency harness work, followed by login-only validation.

[Review](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/snapshot-review-v1/REVIEW.txt),
[use freeze](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/snapshot-review-v1/CONFIGURATION-USE-FREEZE.json),
[decision](../verification/startup-native-captured-configuration-review.json).

## A3 read-only configuration compatibility harness locally verified — November 4, 2026

D142 / roadmap v1.94.326final checks pass across independent source/snapshot macOS and ARM Linux runs, including real memfd seals/FD lifetime/inheritance, mutation denial, bounded subprocess output/deadlines/group cleanup, metadata/ELF/path races and closed native replay. Exact manifest/PLAN/inventory/Python hashes are verified before importing original packet code; actual original packet and adversarial import-boundary checks pass. Static ELF/plugin candidates do not claim installed runtime dependency closure; no private JWT key is read. Original configuration bytes,71scientific files, full packet/semantic references,128+128main/276+276A3 tests, strict verification, limits and prior evidence verify unchanged.

No Torch command, Slurm client, job, search, scientific SQL or provider call ran. All spent allowances including21756110remain closed. Native closure table is empty; configuration/dependency/native qualification flags remain false. Next is preparation of login-only installed dependency inspection, review of that evidence, then a separately frozen exact native read-only closure. No qualification grant is issued.

[Freeze](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/compatibility-v1/HARNESS-FREEZE.json),
[verification](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/compatibility-v1/verification.json),
[report](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/compatibility-v1/REPORT.txt),
[decision](../verification/startup-native-client-configuration-compatibility.json).

## A3 login-only dependency inspection commands ready — November 4, 2026

D143 / roadmap v1.95.29source+29independent snapshot checks pass for the pinned-key Mac upload and exact Torch login bootstrap. Payload35749bytes/SHA b8725d26973a2cf7eeee3f0012c77ec4f7cbec251fa548a551d3e79fb2e1a793 is unchanged; original326harness checks,128+128main/276+276A3 tests, strict packet/reference verification, limits and evidence remain preserved. No real network/SSH/scp/Slurm/job/search occurred during checks. An initial source guard included its own log; that held precheck and input-list correction are preserved.

Upload one pinned inspector into a fresh private directory, then run the isolated/no-bytecode login block. It checks bytes/permissions/generation before compilation and forces inspect. Original login/package/quota/capture/dependency bounds remain active. No scheduler client, loader, ldd, JWT private key, replay or allocation is invoked. Return the final JSON/evidence for installed dependency review. All spent allowances remain closed and native admission stays false.

[Mac upload](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-command-v1/upload-from-mac.sh),
[Torch inspection](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-command-v1/TORCH-INSPECT.txt),
[verification](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-command-v1/verification.json),
[decision](../verification/startup-native-login-dependency-command-ready.json).

## A3 upload session failure; direct SFTP replacement ready — November 4, 2026

D144 / roadmap v1.96. The user upload fails before scp at the remote shell mkdir session. Its held receipt/code remain evidence. A frozen transport-only correction uses one direct SFTP connection with interactive MFA enabled, no master/mux or remote shell, identical strict DTN key and unchanged payload/Torch inspection block. Fresh-directory and batch abort checks preserve any existing destination.

14source+14snapshot checks pass, including real local SFTP bytes/permissions/abort, actual installed-client option order via local fake transport/ssh -G, and real owned-child TERM cleanup. All29+29command/326harness proofs,128+128main/276+276A3 tests, packet/references, strict verification, limits and prior evidence remain preserved. No actual network/Torch/job/search occurs here and all spent grants remain closed. Replacement user upload is next; native gates remain held.

[Replacement Mac uploader](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-command-v1/sftp-upload-correction-v1/upload-from-mac.sh),
[verification](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-command-v1/sftp-upload-correction-v1/verification.json),
[decision](../verification/startup-native-dependency-sftp-transport-correction.json).

## A3 login verification timeout; strict one-pass correction ready — November 4, 2026

D145 / roadmap v1.97. User inspection passes its pinned bootstrap and first full semantic verifier, then times out120seconds during the quota wrapper's repeated full verification before metadata starts. A frozen separate correction retains one complete exact original semantic verifier/default core and compiles the exact quota tail without only its redundant three-statement verification prefix. Original code/functions/strict criteria/quota parser and minima,30squota bound,120shelper deadline and all scientific limits remain unchanged; no cache or false semantic option is used.

424local checks pass across source/snapshot Mac/ARM Linux and transport/bootstrap, preserving all prior74functional/15kernel IDs. An actual exact-target package check records one full verifier/core and original quota output with only myquota/statvfs mocked; native runtime is unqualified. New payload39512bytes/SHA9b8870a49526dbd5309b34815202f0be74687822857eac47ce73659b21d06b7f uses a fresh remote directory and NEW pinned login block. Strict direct SFTP is retained. All old128+128main/276+276A3 tests, strict references/limits, CPU60proof and evidence remain preserved; no actual network/Torch/job/search or grant reuse occurs. User upload/login-only collection is next and all native gates stay held.

[Review](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/verification-cost-correction-v1/REPORT.txt),
[Mac upload](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/verification-cost-correction-v1/upload-from-mac.sh),
[new Torch block](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/verification-cost-correction-v1/TORCH-INSPECT.txt),
[decision](../verification/startup-native-login-verification-cost-correction.json).

## A3 login-only dependency capture reported complete; download ready — November 4, 2026

D146 / roadmap v1.98. User reports completed metadata capture at a3-client-config-dependencies.xgzm0ve9: one full strict verifier56.006s, quota2.070s, all allocation/search counters0 and configuration/dependency/native flags false. Actual four-file raw is not local yet; native/scientific qualification remains held.

Exact bounded Mac retrieval passes27source+27snapshot checks, including real local SFTP valid/oversize behavior and unchanged parent limits. It uses two strict direct-SFTP MFA connections to enforce control/inspection file ceilings, fixed four names and manifest/hash/JSON/proof/quota verification; no remote shell, new inspection, job or retry. Executable quota parser is pinned in code after a frozen pre-release hardening. All prior424checks,128+128main/276+276A3 tests, strict verification, limits and evidence remain preserved. No actual network/Torch action occurs locally; every spent allowance stays closed.

[Download](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-return-xgzm0ve9/download-from-mac.sh),
[verification](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-return-xgzm0ve9/verification.json),
[decision](../verification/startup-native-dependency-inspection-reported.json).

## A3 actual dependency capture reviewed; RPATH metadata correction ready — November 4, 2026

D147 / roadmap v1.99. All4returned files/73,986bytes verify.18ELF objects and34captured components reconcile without conflicting generations; forty duplicate lexical candidate paths are captured symlink aliases. Both client pins match. Each client requires libslurmfull.so in /opt/slurm/lib64/slurm, listed by the captured directory but omitted from the fixed candidate roots, so its identity/transitives are not yet captured. Captured libslurm.so.43 is not substituted.

Freeze then append only that observed PLUGIN_DIR to a separate inspector's fixed roots. All other AST/functions, ownership/environment/strict one-pass verification/quota rules,120second and original limits remain unchanged.436local source/snapshot Mac/ARM Linux/transport/bootstrap checks pass, retaining all85functional/15kernel IDs. All128+128main/276+276A3 tests,71scientific files, prior evidence and spent closures remain preserved. No actual network/Torch/job/search occurs. New strict upload/login-only capture is ready; runtime loader/plugin/auxiliary/MUNGE/parser/native qualification gates remain held.

[Review](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-review-xgzm0ve9-v1/REPORT.txt),
[verification](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-review-xgzm0ve9-v1/verification.json),
[new Mac upload](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-review-xgzm0ve9-v1/upload-from-mac.sh),
[new Torch block](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/dependency-review-xgzm0ve9-v1/TORCH-INSPECT.txt),
[decision](../verification/startup-native-dependency-capture-review.json).

## Experiment log update — November 5–16, 2026

Reconciled November 17, America/New_York, from saved reports, deployment/outcome
freezes, returned evidence and current handoff files. Dates below are recorded
work dates. This refresh read metadata and hashed local archives; it did not
launch experiments, call a provider, access Torch or inspect protected outcomes.
The detailed catalog also indexes intervening engineering receipts and failed
preparations that do not warrant a separate scientific result row here.

### A3 and persistent-reader studies — November 5–10

| Study / question | Recorded outcome and limits | Source, evidence and reproduction |
|---|---|---|
| A3 installed configuration, loader/plugin/peer/NSS and native integration | Later login-only evidence and local compatibility work reached a packaged readiness bridge. The November 8 submission attempt failed the strict `/etc/passwd` digest guard on `torch-login-b-2` before reservation or dispatch: no new job, ANN/exact searches or native qualification. The timebox expired; the failed approval/attempt remains closed. Local or login checks do not qualify native x86 execution, startup headroom or B2f. | [Integration report](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/native-config-integration-v1/REPORT.txt), [held submission](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/native-config-integration-v1/submission-hold-2026-11-08.json), [saved engineering evidence](../../../trials/torch-reviews-startup-native-pinned-client-config-v1/) |
| November 8 retained-path policy decision | Abstain from independent-confirmation nomination: the selective seed's reuse gain did not repay activation; partial-index timing controls failed; A3 remained held. Preserve this decision under its original contract, separately from the later clean benchmark restart. | [Decision memo](../../../research/fannagent-policy-evaluation-decision-memo-2026-11-08.md), [activation review](../../../research/fannagent-retained-path-activation-review-2026-11-08.md) |
| Controlled Reviews batch and persistent-reader development | The separately authorized proposal `seed-revised-128-gate418` cost $0.125714. Preserve earlier admission, compute-tool and guest-path failures (jobs 22372968/22376684), memory-gated development, calibration and reader diagnostics as distinct attempts. Original recall/timing controls and frozen data apply to each version; later successes do not replace failed launches. | [Study design](../../../research/fannagent-controlled-reviews-batch-study-design-2026-11-08.md), [source/recorded handoffs](../../experiments/reviews-persistent-batch-v1/README.md), [proposal evidence](../../../trials/reviews-persistent-batch-proposal-v1/episode/), [native attempts](../../../trials/reviews-persistent-batch-native-v1/) |
| Shared lookup and timing attribution, jobs 22563225 / 22574550 / 22574554 / 22574556 / 22601306 | On the 60-query shared-lookup comparison, mean request times were 22.26 ms agent, 27.77 ms native and 25.67 ms baseline, with 99% mean recall. Original identical-path controls failed, so the means are descriptive. Three calibration allocations reused cs604, not three independent machines. Attribution localized variation to backend execution/CPU without validating the policy's speed or uniquely identifying the cause. These exposed queries cannot become a fresh test. | [Shared verification](../../../trials/reviews-persistent-batch-native-v1/confirmation-shared-v1/job-22563225/verification.json), [calibration verification](../../../trials/reviews-persistent-batch-native-v1/confirmation-calibration-v1/campaign-Wxv353/verification.json), [attribution verification](../../../trials/reviews-persistent-batch-native-v1/confirmation-attribution-v1/job-22601306/verification.json), [source/frozen recipes](../../experiments/reviews-persistent-batch-v1/README.md) |

### Clean restart and guarded-to-unguarded transition — November 10–13

| Date / run | Question and recorded outcome | Source, evidence and reproduction |
|---|---|---|
| November 10, clean restart | Reservation review recovers 150 protected validation and 275 protected test groups; 450 groups are development and 125 historical groups excluded. The earlier 25/100 provisional plan is superseded and preserved. Local recorded-history evidence does not certify unrecorded access. | [Reservation review](../../../trials/fannagent-benchmark-evaluation-v1/inventory/reservation-review.md), [split seal](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/freeze/split-freeze.json), [restart plan](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/protocol/restart-plan.md) |
| November 11, job 22635567 | Native640 runtime semantics qualify on 3,150 development cases and 7,940 forced outputs; scientific adequacy fails at votes743/527/310. No generation episode runs at this stage. | [Report](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/reports/native640-qualification-22635567.md), [raw return](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/returns/job-22635567/), [original runtime commands](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/COMMANDS.txt) |
| November 11, job 22643346 | Prespecified stronger-parent sweep has no adequate complete parent: 15,750 observations reconstruct; one votes743 case still returns 8/10 at ef8192. Exit 3 is the declared negative outcome. No grid expansion or inferred traversal cause. | [Report](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/reports/parent-sweep-22643346.md), [raw return](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/returns/job-22643346/), [parent plan](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/protocol/parent-requalification-plan-v1.json), [commands](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/PARENT-COMMANDS.txt) |
| November 12, job 22684501 | The then-authorized common exact completion guard qualifies all seven conditions. Guarded native640 is selected at 18.8723 ms equal-scalar serving mean; 203,286 attempts verify. This hybrid development result is historical and does not qualify the later raw-output objective. | [Report](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/reports/guard-qualification-22684501.md), [raw return](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/returns/job-22684501/), [guard amendment](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/protocol/completion-guard-amendment-v1.md), [commands](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/GUARD-COMMANDS.txt) |
| November 12, original generation and compact continuation | First request explicitly abstains with an empty policy pool. The authorized two-request continuation yields three replay-eligible final programs; original parser rejection and separate envelope recovery are preserved. Three requests total $0.725544 exhaust this historical allowance. Surrogate costs do not establish actual speed or select a final policy. | [Initial episode](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/reports/agent-episode-v1-2026-11-12.md), [continuation](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/reports/agent-compact-continuation-2026-11-12.md), [frozen eligible programs](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/development/agent-episode-v2-compact/eligible-policies.json) |
| November 13, job 22928562 | Compiled guarded policies reproduce all 9,450 policy cases and zero development recall losses; 50,400 timings and 81,456 attempts verify. Broad's 3.19% nominal gain is below the 5% target, with reader-control limitations. Development nominee only. | [Report](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/reports/agent-policy-qualification-22928562.md), [raw return](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/returns/job-22928562/), [deployment amendment](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/protocol/agent-policy-qualification-amendment-v1.md), [commands](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/AGENT-COMMANDS.txt) |
| November 13, unguarded redesign and job 23045686 | User-directed removal of serving exact completion: short outputs remain misses, absolute 95% recall becomes diagnostic, zero per-case loss versus actual raw native640 remains the preservation gate. All 150,570 attempts verify. Conservative's nominal 8.01% gain cannot be attributed to stopping because always-continue is 6.54% faster and reader controls fail. Old policies are guarded-label transfer ablations, not fresh unguarded discoveries. | [Revised protocol](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/protocol/study-protocol-unguarded-v1.md), [report](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/reports/unguarded-development-23045686.md), [raw return](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/returns/job-23045686/), [commands](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/UNGUARDED-COMMANDS.txt) |

### Protocol v2, M0–M3 — November 13–16

The [protocol revamp](../../../research/fannagent-agent-protocol-revamp-2026-11-13.md)
separates runtime engineering, raw-recall preservation, graph work and attributable
complete-request latency. Source/evidence checkpoints preceded the revamp and M1.
The [local v2 implementation](../../experiments/filtered-ann-protocol-v2/README.md)
has a causal DSL/compiler, observation masks, partial/zero stops, matched controls
and bounded typed tools. Its synthetic checks were readiness evidence; the native
qualifications below remain separate experiments.

| Date / stage | Recorded outcome and limits | Source, evidence and reproduction |
|---|---|---|
| November 15, M0 job 23074287 | Clean-import namespace collision stops startup before restore/search. Failed archive is collected and contains no measurements. A separate schedule-module rename and native preflights repair deployment without changing the scientific schedule or policies. | [Repair](../../experiments/reader-attribution-startup-fix-v1/README.md), [failed return](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/returns/job-23074287/), [deployment freeze](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/freeze/reader-attribution-startup-fix-v1.json) |
| November 16, M0 job 23303080 | Verified COMPLETED/0:0; 630,000 measured requests and 684,950 attempts. Every policy preserves raw-native recall. Broad saves 3.77% equal-scalar latency and 5.30% vector-score work; the conditional speed interval is 3.01–4.59%, with 82.47% of scalar millisecond savings from votes32. The old always-continue advantage does not reproduce. One allocation, no final 5% practical pass, no unique attribution of the old anomaly. | [Assessment](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/reports/reader-attribution-assessment-23303080.md), [raw return](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/returns/job-23303080/), [outcome freeze](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/freeze/reader-attribution-assessment-v1.json), [repaired commands](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/ATTRIBUTION-STARTUP-FIX-COMMANDS.txt) |
| November 16, M1 job 23376796 | Verified COMPLETED/0:0; 781,200 measured requests and 984,396 attempts. All 9,436 prefixes now have actual labels: 7,940 full, 1,496 partial, including 95 zero-output prefixes. Native bridge, compatible stops, work and reader/CPU schedules verify. Historical Broad transfer saves 5.55% on v2, conditional interval 4.58–6.57%; no final practical-bound pass. Packaged analysis's fold-key error is retained; a separate integer-key export repair produces the bound evidence without rerunning Torch or changing sealed source. | [Assessment](../../experiments/m1-assessment-v1/REPORT.md), [raw return](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/returns/job-23376796/), [outcome freeze](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/freeze/m1-assessment-v1.json), [M1 source/recipe](../../experiments/m1-runtime-qualification-v1/README.md) |
| November 16, M2/M3 initial qualification | All 3,150 development cases and 9,436 prefix labels bind to compact evidence. Both predeclared point-cost models fail fixed precision limits; preserve signed/noisy estimates and all filters. Actual-bound M3 passes quality/work, quota, tamper and explicit abstention paths, but cannot authorize cost ranking under the failed model contract. Scripted positive fixtures remain engineering checks. | [Report](../../experiments/m2-evidence-cost-v1/REPORT.md), [outcome freeze](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/freeze/protocol-v2-M2-M3-v1.json), [saved evidence/rehearsals](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/evidence-m2-v1/) |
| November 16, uncertainty-aware selection and M3 | Separately frozen adaptation reuses the signed proxy without refitting; deployment envelope is ±3.5364 native percentage points and the conditional regret bound is at most one point. Outer engineering checks and actual-bound positive/abstention rehearsals pass. This empirical envelope is not a future-query/allocation confidence interval, and precise point ranking stays failed. Initial local context-cap failure and feedback-only repair remain preserved. | [Report/contract](../../experiments/uncertainty-shortlist-v1/REPORT.md), [outcome freeze](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/freeze/uncertainty-shortlist-v1.json), [saved rehearsals](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/uncertainty-shortlist-v1/) |

### M4 generation and M5 preparation — November 16

The M4 evidence uses raw outputs, all six filters plus unfiltered, and development
data only. It is a separately authorized episode from the historical three-call
episode above. Each amendment preserves the original transcript, charges,
candidate records, freezes and closed outcomes.

| Version / stage | Recorded outcome and limits | Source, evidence and reproduction |
|---|---|---|
| Original M4 packet and execution | After explicit approval, two successful Messages calls cost $0.038798. A legal tool sequence would exceed the host's 50,000-byte payload/headroom bound by 574 bytes; the host stops before request 3. Zero policies/nominees; terminal capacity abstention, not model-context or budget exhaustion. | [Packet](../../experiments/m4-provider-episode-v1/APPROVAL.md), [assessment](../../experiments/m4-episode-assessment-v1/REPORT.md), [outcome freeze](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/freeze/m4-episode-v1-outcome.json) |
| Context amendment and approved continuation | A frozen 8 MiB wire limit plus exact input token counts replaces the operational byte heuristic. Four additional Messages calls complete: six cumulative calls/$0.244308. Six policies have loss counts 8/4/1/1/1/0. Candidate 6 is zero-loss but needs an unsupported unfiltered observation mask; no candidate meets both quality and cost support. No formal final submission before the call cap, so no M5 nominee. Preserve that closed outcome. | [Amendment](../../experiments/m4-context-amendment-v1/APPROVAL.md), [assessment](../../experiments/m4-continuation-assessment-v1/REPORT.md), [outcome freeze](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/freeze/m4-continuation-outcome-v1.json) |
| Dollar-budget amendment and final continuation | User changes the cumulative contract to the original $15 ceiling without a Messages-count limit; scientific tool/candidate limits and all prior spend remain. Two more calls yield voluntary formal submission of candidates 7/8: eight cumulative calls/$0.403114. Both preserve every development case and use supported observation masks, stopping 135/41 and 102/22 unfiltered/votes32 cases. Other filters continue natively. Proxy intervals include native; conditional shortlist eligibility is not an actual speedup or held-out result. | [Active runner/contract](../../experiments/m4-dollar-budget-v1/README.md), [assessment](../../experiments/m4-dollar-assessment-v1/REPORT.md), [outcome freeze](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/freeze/m4-dollar-outcome-v1.json), [formal nominees](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/m4-dollar-budget-v1/assessment-v1/nominees.json) |
| M5 sealed, pending original-graph execution | Candidates 7/8, native640, their two matched continue-only controls and an empty-policy diagnostic are frozen unchanged. Local compiler, PostgreSQL fixture, return-verifier, CPU-analysis and loader checks pass; local failures are retained in readiness. No M5 job/result is recorded. Full native startup preflight and one user-submitted development allocation precede qualification/timing. | [Preparation report](../../experiments/m5-policy-qualification-v1/REPORT.md), [protocol](../../experiments/m5-policy-qualification-v1/PROTOCOL.md), [freeze](../../experiments/m5-policy-qualification-v1/receipts/M5-freeze.json), [readiness](../../experiments/m5-policy-qualification-v1/receipts/local-readiness.json) |

M5 archive identity: `m5-policy-qualification-v1.tar.gz`, 8,248,804 bytes,
SHA-256 `3c4a0bd267d743e7abff9790beff7a7af510bc350cf079dda1c45d24e984b3b1`.
The frozen plan reserves 214,396 attempts under 225,000, including 151,200
uninstrumented complete-request timings and separate work counters, on four
physical CPUs / 48 GiB / six hours. Exact scoring has 6,300 offline calls and
zero serving exact calls. The current [SFTP upload supplement](../../experiments/m5-policy-qualification-v1/SFTP-UPLOAD.txt)
supersedes only the original SCP upload block; the sealed archive is unchanged.
Use the [submission/status/return commands](../../experiments/m5-policy-qualification-v1/COMMANDS.txt)
and the sealed verifier/analyzer for the returned result. Local fixture times
and replay checks are not M5 original-graph measurements.

Disposition recorded on November 16: two formal development nominees, no final
selected policy, no demonstrated held-out or replicated latency benefit, and no
validation/test outcome access. The next record should identify the actual M5 job, scheduler
result, returned hashes, complete quality/timing/work reconstruction and its
scientific disposition, including a negative or inconclusive outcome if needed.
The separately authorized oracle studies below subsequently exposed outcomes;
they do not change the recorded M4/M5 disposition.

## Oracle studies and broader policy language — November 17–19, 2026

Reconciled November 19, America/New_York, from committed reports, frozen policy
artifacts, scheduler accounting and collected raw returns. The question was how
much latency could hypothetically be saved with hindsight on both the frozen
275-vector test subset (1,925 query/filter cases) and all 1,000 benchmark vectors
(7,000 cases). The cohorts overlap. Each includes six scalar filters plus
unfiltered on the original 247,286-row cosine graph, k=10, native ef=640 and
iterative scans off. Exact references are offline scoring inputs only.

### Definitions, deployment and exposure

| Variant | Hindsight freedom | Runtime policy requirement |
|---|---|---|
| `oracle_ideal` | Choose the earliest safe reached checkpoint independently for each case. | Evaluator-only choice table, with routing outside the request timer and no policy feature/VM cost. |
| `oracle_constrained` | Choose independently per case from checkpoints 16/32/64 or native continuation. | Same action menu as v2; still a free hindsight lookup rather than one causal agent policy. |
| `oracle_feasible`, narrow v2 | Fit one complete policy on the reported cohort's outcomes. | Ordinary `fannagent.filtered-ann.v2` artifact: at most three ascending clauses per filter, four AND comparisons per clause, and four causal features. |
| `oracle_feasible`, broad v3 | Fit one complete policy on the reported cohort's outcomes. | Ordinary `fannagent.broad-stop.v3` artifact, submitted through the agent adapter and executed by its trusted compiler/VM. |

There is **one fixed feasible policy per cohort**, with seven filter-specific
programs inside each artifact. All queries in a filter share that program. The
full-workload policy is applied to all 7,000 cases; the separate test-fitted policy
is applied to all 1,925 test cases. Neither selects a policy by query ID. Both are
frozen before timing. The agent can hypothetically emit these exact accepted
artifacts; this does not demonstrate that an autonomous agent discovers them
from its usual feedback or that they generalize.

The opt-in [v3 interface](../../experiments/filtered-ann-protocol-v3/README.md)
replaces the old rule shape with typed Boolean/arithmetic expression graphs,
checkpoint schedules from 1 to 4,096, thirteen causal features and bounded
query-local registers. The public [validator](../../src/fannagent/api/broad_policy.py)
and [compiler](../../experiments/filtered-ann-protocol-v3/fannproto3/compiler.py)
limit source to 8 MiB, expression nodes to 131,072, depth to 64, tables to 4 MiB,
registers to 32 and fuel to 16 million per query; these fits use two million.
Runtime inputs exclude query IDs, truth labels and future observations, and the
VM has no I/O or index mutation. Faults or fuel exhaustion continue natively.
The fitted trees can distinguish and memorize finite-cohort causal observations
through fine thresholds. Broader savings reflect expanded expressions, features
and checkpoints together, rather than an isolated change in rule syntax.

The original count-preserving oracle required both native Recall@10 and result
count. The later three-level and broad comparisons use the actual agent gate:
zero per-case native Recall@10 losses, with short outputs scored as misses and
count reductions reported separately. Hindsight exposure of the test and full
workloads is authorized for this diagnostic. No oracle labels were added to the
ordinary agent feedback service, and these cohorts must not be described as an
untouched confirmatory test after fitting on their outcomes.

### Earlier oracle runs and retained amendments

Dates below use America/New_York; the first source submission was November 17
at 21:31 (November 18 at 02:31 UTC). Saved source, amendments and reproduction
commands are in [full-workload-oracle-v1](../../experiments/full-workload-oracle-v1/README.md)
and [oracle-variants-v1](../../experiments/oracle-variants-v1/README.md).

| Date / exact job | Question and recorded outcome | Saved evidence |
|---|---|---|
| November 17–18, 23544718 | Initial count-preserving acquisition: all 7,000 exact references and 4,256 complete choices acquired. Deliberately interrupted before primary timing to replace expensive durable per-query bookkeeping; scheduler FAILED is retained. | [Source return](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/full-workload-oracle-v1/return-23544718/), [submission](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/full-workload-oracle-v1/submission.json) |
| November 18, 23558871 | Frozen bookkeeping follow-up completes the remaining 2,744 choices and 23,225 fresh validation queries. Deliberately stopped before primary timing when eight repetitions would exceed the remaining aggregate budget; FAILED and all charges retained. | [Follow-up return](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/full-workload-oracle-v1/return-23558871/), [amendment](../../experiments/full-workload-oracle-v1/FOLLOWUP-PROTOCOL.md) |
| November 18, 23567950 | Uniform four-repetition schedule completes 112,000 timing records and all 7,000 frozen choices verify. No native recall or result-count losses. Strict all-condition timing controls remain inconclusive. | [Final return/report](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/full-workload-oracle-v1/return-23567950/results/), [timing amendment](../../experiments/full-workload-oracle-v1/BALANCED-PROTOCOL.md), [commands](../../experiments/full-workload-oracle-v1/COMMANDS.txt) |
| November 18, 23604734 | Three-level comparison captures complete actual prefix evidence; COMPLETED/0:0 in 1,809 seconds. | [Capture return](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/oracle-variants-v1/return-23604734/) |
| November 18, 23610319 | Three-level comparison completes 56,000 quality requests and 448,000 primary timings; COMPLETED/0:0 in 7,601 seconds. Both feasible artifacts pass the unchanged v2 compiler and intended-cohort recall gate. | [Timing return](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/oracle-variants-v1/return-23610319/), [committed report](../../experiments/oracle-variants-v1/results/REPORT.md), [commands](../../experiments/oracle-variants-v1/COMMANDS.md) |

The count-preserving study measured 65.28% test and 66.06% full-workload savings,
with 18,716 total allocated seconds and 493,388 charged reservations across all
three jobs. The later recall-only v2 comparison measured ideal/constrained/feasible
savings of 67.52% / 54.67% / 27.20% on test and 68.25% / 55.12% / 17.98% on full.
Its two jobs consumed 9,410 allocated seconds, 557,403 actual ANN requests and
558,080 charged reservations. Neither study established strict timing-control
equivalence. These are separate historical measurements; the comparison below
reruns the same narrow policies alongside the broader policies on a fresh shared
allocation. All consumed time, failures and earlier estimates remain recorded.

### Broad v3 capture, pause, failure and completed comparison

The existing work was committed as `795db05` before implementation, as requested.
`b32d618` checkpoints the implementation and frozen fits at the user-requested
pause; `75c5752` records the resumed comparison, canonical-projection repair and
carried costs; `7ee2df1` records the verified final results. The original engine,
v2 policies and historical reports remain preserved. The experiment's
[protocol](../../experiments/broad-oracle-v1/PROTOCOL.md),
[reproduction commands](../../experiments/broad-oracle-v1/COMMANDS.md),
[pause](../../experiments/broad-oracle-v1/PAUSED.json) and
[completed resume](../../experiments/broad-oracle-v1/RESUMED.json) bind this sequence.

| Date / exact job | Question and recorded outcome | Saved evidence |
|---|---|---|
| November 18, 23644126 | Capture the expanded causal interface on the original graph. COMPLETED/0:0, 1,683 allocated seconds; 7,000 cases and 1,104,761 checkpoint frames captured, with native outputs and complete prefix chains verified. | [Capture return/accounting](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/broad-oracle-v1/return-23644126/), [source verification](../../experiments/broad-oracle-v1/results/source-verification.json) |
| November 18, 23648495 | First timing allocation cancelled at the user's explicit pause, before any experiment ANN request or reservation. Root elapsed 120 seconds; conservative charge 122 includes cleanup. No final timing result. | [Cancellation and remote raw location](../../experiments/broad-oracle-v1/paused-checkpoint/benchmark-cancellation.json), [saved accounting](../../experiments/broad-oracle-v1/results/prior-cancelled-accounting.json) |
| November 19, 23716630 | Explicitly resumed frozen comparison fails independent canonical-frontier validation before quality/timing. FAILED/1:0; root elapsed 205 seconds, conservative charge 207. Entire 1,024-query window charged; actual failed-stage queries unknown within 1–1,024. | [Failed raw return/accounting](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/broad-oracle-v1/return-23716630/), [retained failure charge](../../experiments/broad-oracle-v1/results/prior-failed-accounting.json) |
| November 19, 23719580 | Corrected validation applies the existing native cosine projection. COMPLETED/0:0 in 5,771 allocated seconds. All checkpoint frontier/work and prefix checks, 84,000 quality checks and 336,000 timings independently reconstruct. | [Final raw return/accounting](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/broad-oracle-v1/return-23719580/), [qualification](../../experiments/broad-oracle-v1/results/frontier-qualification.json), [final report](../../experiments/broad-oracle-v1/results/REPORT.md) |

The failed check compared raw canonical cosine values with the native collector's
already-clipped [0,2] values. The separate reference correction applies that
existing projection, requires agreement within 1e-12 after projection and permits
boundary corrections no larger than 1e-6. All 1,104,761 frames pass; 196 boundary
roundoff events have maximum magnitude 1.1920928955078125e-7. The native module,
frozen policies and primary timing method did not change. See the
[projection fixture](../../experiments/broad-oracle-v1/results/frontier-projection-fixture.json)
and [qualification evidence](../../experiments/broad-oracle-v1/results/frontier-qualification.json).
The failed run is retained rather than treated as an absent attempt.

### Fresh latency comparison and quality

Savings below are ratios of mean complete-request latency, equally weighted over
all seven conditions, from one balanced allocation and shared native baseline.
Each of twelve families has four measurements per case, one on each reader,
with mirrored ordering. Feature collection and VM execution are inside the
primary timer; ideal/constrained choice routing is outside it and reported
separately. No outliers or samples were removed.

| Oracle | Test subset: 1,925 cases | Full workload: 7,000 cases |
|---|---:|---:|
| `oracle_ideal` | 65.89% | 67.48% |
| `oracle_constrained` | 53.28% | 55.00% |
| `oracle_feasible`, narrow v2 | 21.37% | 19.80% |
| `oracle_feasible`, broad v3 | 64.95% | 68.39% |

| Broad v3 summary | Test subset | Full workload |
|---|---:|---:|
| Native mean request latency | 11.647 ms | 11.933 ms |
| Broad feasible mean request latency | 4.083 ms | 3.772 ms |
| Saving, conditional 95% interval | 63.01–66.84% | 67.34–69.41% |
| Gain over narrow feasible | 43.57 pp | 48.60 pp |
| Stops | 1,923 | 6,996 |
| Matches ideal stop | 1,924 / 1,925 | 6,994 / 7,000 |
| Per-case native Recall@10 losses | 0 | 0 |
| Returned-result-count reductions | 0 | 3 |

All four variants have zero intended-cohort native recall losses. On full, ideal,
constrained, narrow and broad have 3 / 2 / 0 / 3 result-count reductions; test has
none. The seven stop mismatches across the overlapping cohorts delay checkpoint
1 to 16. Their first permitted observations, including collection fuel charge,
are identical to unsafe peers in the same fitted cohort; the current causal
interface cannot distinguish them safely at checkpoint 1. The
[collision proof](../../experiments/broad-oracle-v1/results/first-checkpoint-collisions.json)
retains the evidence. Outside the test fitting cohort, the test-fitted policies
lose recall on 147 narrow and 2,353 broad cases out of 5,075. This transfer
diagnostic prevents interpreting fitted-cohort preservation as generalization.

For the six filtered conditions alone, ideal / constrained / narrow / broad
savings are 61.62% / 48.21% / 14.28% / 60.56% on test and
63.49% / 50.21% / 13.43% / 64.69% on full. Per-condition values and both aggregate
definitions are retained in [report.json](../../experiments/broad-oracle-v1/results/report.json).

**Strict timing-control equivalence is not established in either cohort.** The
90% intervals for every condition's native-clone and empty-language controls must
all lie within ±2%; this requirement failed. These savings are descriptive
hindsight estimates, not certified numerical ceilings. The broad full-workload
policy's apparent 0.91-point lead over ideal reflects unresolved timing bias and
does not show that it beats the ideal oracle. The 20,000 fixed-seed vector-cluster
bootstrap draws condition on frozen fitted policies and one allocation, omitting
fitting uncertainty and variability across allocations. Best-found feasible
policies and earliest-safe work stops do not prove a mathematical wall-clock
optimum. No comparison was repeated to obtain favorable controls.

### Accounting, artifacts and reproduction

The broad study's recorded aggregate charge is 7,783 allocated seconds, including
the cancelled and failed allocations, under 21,600 seconds. Four physical CPUs
and 48 GiB were requested per allocation. Completed stages issued 463,192 known
ANN requests; the failed stage adds 1–1,024 unknown requests, giving physical-count
bounds of 463,193–464,216. All 464,896 reservations remain charged under the
two-million cap, including unused and failed-stage windows. There were zero
provider calls, fresh exact queries or automatic retries, one explicit user
resume and one supervised validation revision. SSH was closed after collection;
the completion record reports no active benchmark jobs. See
[accounting.json](../../experiments/broad-oracle-v1/results/accounting.json) for
source hashes, resource counts and raw evidence identities.

The committed [result directory](../../experiments/broad-oracle-v1/results/)
contains the numerical report and plots, both ordinary policy JSON artifacts,
fit/compiler certificates, agent submission receipt, source and frontier
qualification, timing plan, resource accounting and `SHA256SUMS`. The
[full policy](../../experiments/broad-oracle-v1/results/oracle_feasible-broad-full_workload.json)
and [test policy](../../experiments/broad-oracle-v1/results/oracle_feasible-broad-heldout_test.json)
are the artifacts the agent could hypothetically produce. Raw returns, failed
logs, frozen kits and fitting inputs remain outside Git in the
[trial directory](../../../trials/fannagent-benchmark-evaluation-v1/reviews-small/broad-oracle-v1/).
Use the [saved commands](../../experiments/broad-oracle-v1/COMMANDS.md) with the
final `benchmark-kit-v3` to reproduce verification/analysis; launching fresh
measurements is a separate operation.

This log update refreshed only the local inventory and archive SHA-256 values.
It ran no experiments and contacted no remote service. All 188 usable archive
sidecars match; 256 other archives have newly observed inventory hashes without
an earlier usable sidecar. Raw archives are not included in the documentation
commit, and independent backup coverage was not verified; see the
[backup audit](BACKUP_AUDIT.md).
