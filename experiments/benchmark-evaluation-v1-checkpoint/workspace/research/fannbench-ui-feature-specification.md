# FANNBench research UI — feature specification

Version: 1.0  
Date: September 27, 2026  
Status: Proposed implementation specification, grounded in the current harness

## 1. Product purpose

The UI is a local research workbench for understanding FANNBench experiments. It must help a researcher determine whether a stopping policy saves work and time at the intended recall target, identify where it fails, inspect the evidence behind a decision, and prepare reproducible results for discussion and reporting.

The first release reads existing experiment and evidence artifacts. The CLI remains the execution interface. This scope fits the project's current investment in structured results, instrumentation, and reproducible measurement, and limits the engineering work needed before the main research experiment.

The UI must make these questions answerable:

1. Did the experiment complete, and which results are usable?
2. How did latency, recall, correctness, and execution work change between the baseline and treatment?
3. Which queries improved, regressed, or fell below the recall target?
4. What did the engine observe, and what happened when the policy stopped?
5. Which dataset, index, engine build, configuration, policy, and evidence produced the result?

Later releases should answer whether the learned shape model predicts query behavior, improves the policy beyond simpler alternatives, and pays back its acquisition cost.

## 2. Users and working assumptions

| User | Primary need | Successful outcome |
| --- | --- | --- |
| Researcher running the study | Compare experiments and diagnose unexpected behavior | Can move from a result to the responsible queries and recorded evidence without manually joining files |
| Advisor or collaborator | Understand the experimental claim and its limits | Can inspect a portable report containing definitions, provenance, coverage, and representative examples |
| Harness developer | Investigate correctness, instrumentation, and compatibility issues | Can locate the exact failed record or conformance bundle and reproduce its configuration |

Assume one researcher, one local workspace, and desktop browser use. All three existing backends must be recognized when their artifacts are present. The UI must also be useful with one backend, one run, or one standalone evidence artifact.

The source data may be incomplete, generated under an earlier contract, or copied from another machine. Missing information is an expected state. The UI must remain useful without Docker, the original database containers, an internet connection, or access to the original vector dataset.

## 3. Release priorities

**P0 means required for the first usable release. P1 extends research analysis after P0 is reliable. P2 is a separately scoped execution interface.**

| Area | Priority | Required result |
| --- | --- | --- |
| Artifact discovery and validation | P0 | Open runs, studies, policies, and evidence; report unsupported or incomplete inputs |
| Run overview and experiment comparison | P0 | Inspect outcome, coverage, provenance, and supported paired comparisons |
| Query explorer | P0 | Find regressions, recall failures, and invalid responses; inspect individual samples |
| Trace and checkpoint inspection | P0 | Navigate recorded search progress and correctly attach available stop labels |
| Policy inspection | P0 | Understand the actual artifact, feature requirements, and compatibility |
| Correctness and evidence quality | P0 | Distinguish conformance, response correctness, retrieval quality, and evidence availability |
| Study overview | P0 | Inspect split counts, recall target, frozen policy, available aggregate evaluations, and recorded budgets |
| Saved views and export | P0 | Reopen an analysis and export its figures, tables, and provenance |
| Data-shape analysis and learning curves | P1 | Relate structure to policy outcomes and compare methods across evidence budgets |
| Model version analysis | P1 | Explain changes in shape memory and their measured effects |
| Experiment setup and execution | P2 | Validate and launch approved workflows through existing application services |

P0 excludes execution controls, policy editing, agent conversations, vector ingestion, resource deletion, cloud hosting, accounts, and shared editing. These would add operational scope before the analysis workflows are established.

## 4. Navigation and shared interaction rules

The primary navigation consists of **Experiments**, **Studies**, and **Policies**. A run opens an overview with tabs for **Compare**, **Queries**, **Evidence**, and **Artifacts**. Query details open in a dedicated view with a persistent breadcrumb back to the exact filtered table. A policy or study can also be opened directly from a file.

Provide a documented local launch entry point. A proposed command is `fannbench ui --results /path/to/results`; this command does not exist today. It should print the local URL and open the default browser when requested. With no registered sources, the first screen explains the accepted artifacts and provides an Add source action. Closing the browser and reopening the service restores the local catalog and saved views. UI dependencies should be installable separately from ordinary CLI use.

Every analysis view must retain its active context: run or artifact, backend, execution mode or comparison, study split when known, metric definition, selected query group, and sample counts. Filters appear as removable chips. Resetting filters restores the default population and makes the resulting denominator visible.

Tables support search, sort, column selection, pagination or virtualization, and CSV export. Charts support keyboard-accessible selection, tooltips with exact values and units, and an equivalent data table. Selecting a query in a chart opens that query with the same backend, comparison, and population context.

Use a stable color for each execution mode across screens, supplemented by text and symbols. Units belong on axes and columns. Expandable explanations define terms such as recall, policy opportunity, paired effect, route, and censored label in plain language. Raw identifiers and hashes remain available through copy controls and artifact details.

## 5. P0 feature requirements

### F01. Open and index local artifacts

**Purpose:** Make existing experiment output immediately usable without asking the researcher to reorganize it.

Requirements:

- Accept a selected results directory, individual run directory, study manifest, policy artifact, or recognized evidence JSON file. Multiple roots can be registered.
- Discover run directories by validated manifests and artifact contents, rather than assuming filenames alone establish their type.
- Index metadata first. Load measurements and traces on demand. Opening a directory must never start an engine, compute an oracle answer, or consume a study budget.
- List run ID, start time, dataset name, backend set, modes, timing role, completion state, query count, recorded coverage, policy name/hash, and note when available.
- Search by run ID, dataset, note, backend, and policy. Filter by completion state, protocol, artifact compatibility, timing role, and study association.
- Distinguish source status from UI observation: for example, `Manifest says running; last file update 2 hours ago`. A stale manifest alone does not prove that a process is active or failed.
- Present corrupt, partially written, unsupported, and missing files individually. An unreadable trace must not make an otherwise valid run disappear.
- Refresh manually. Optional automatic refresh reads bounded updates and can be paused during benchmarks. A partially written final JSONL line is deferred while the file is changing; malformed complete records are reported.
- Keep index caches and user notes in a separate UI workspace. Source artifacts and study ledgers remain unmodified.

Acceptance: A directory containing a complete run, an incomplete run, an unsupported legacy bundle, and a malformed artifact shows all four with distinct states and actionable explanations.

### F02. Run overview

**Purpose:** Establish what was measured and whether the result can support analysis.

The overview must show:

- Run identity, note, timestamps, status, and benchmark versus development-trace role.
- Dataset name, row count, dimension, dataset/workload hashes, and logical query count.
- Backend/build identities, requested modes, policy identity, feature contract, and selected configuration.
- Planned, recorded, successful, invalid, timeout, error, and missing measurements, with per-backend breakdowns.
- Conformance state for each backend and links to failed queries.
- Per-backend and mode latency, recall, failure rate, and available policy/route counts.
- Latency mean and median; p95/p99 only when the producer's sample thresholds are met. Display a reason when a value is suppressed.
- Visible limitations derived from the artifact: unobserved route, insufficient samples, trace truncation, unknown study membership, or incompatible contract.
- Links to configuration, environment, policy, preparation, logs, diagnostics, and original manifest.

The default view must include all attempted measurements in its coverage and failure reporting. A successful-request latency statistic must name its successful, valid population. Incomplete runs remain inspectable and do not receive a blanket “passed” presentation.

Acceptance: A run with one failed backend shows the successful backend results, the absent measurements, and the failed backend's error without presenting the overall run as complete.

### F03. Compare modes and experiments

**Purpose:** Assess the quality–cost trade-off and separate policy effects from observation and interpreter costs.

Support two comparison workflows:

1. **Within-run mode comparison:** Use recorded pair identities and the harness's paired statistics. Default to native versus candidate policy when available.
2. **Between-run comparison:** Display selected results side by side with a configuration and provenance difference table. Matching query IDs across separate runs does not establish a randomized or paired experiment.

Required views:

- Summary table containing latency, explicitly named recall metric, failures, usable samples/queries, available work counters, and coverage.
- Latency versus recall plot, with each plotted point's aggregation level stated. Clicking a query-level point opens query details.
- Paired latency and recall effects with the exported confidence intervals and independent query count when supplied.
- Query-level change distribution, including both improvements and regressions.
- Whole-workload results as the initial population. A separately labeled matching-route view shows the excluded pair counts and reasons.
- Observation overhead from native to matched no-op. Interpreter overhead is labeled as such only for a verified always-continue control with matching collection groups. An active policy's no-op-to-agent difference includes its changed stopping behavior.
- Configuration diff covering dataset/workload, host, engine build, physical index evidence where available, backend knobs, feature groups, timing protocol, policy, and random seed.

Comparison eligibility:

| State | UI behavior |
| --- | --- |
| Supported paired comparison | Show paired effect and uncertainty with its full inclusion rules |
| Descriptive comparison | Show separate measurements and differences; label changed conditions and omit a controlled policy-effect claim |
| Incompatible metric or artifact contract | Allow artifact inspection; block pooling or a shared numerical effect |
| Insufficient provenance | Show what is available and name the missing evidence needed for stronger comparison |

Expected treatment differences, such as a changed policy, must be distinguished from uncontrolled differences such as a changed dataset or host. Cross-backend results are descriptive unless a separately declared study establishes the intended comparison. Similar backend setting names do not establish equivalent effort or recall.

Acceptance: Selecting two runs from different hosts exposes the host difference before an effect is interpreted. A stock run still supports latency/recall inspection while its route-specific analysis is unavailable.

### F04. Query explorer and sample details

**Purpose:** Find the queries responsible for an aggregate result.

The default table has one row per query for the selected backend and mode or comparison. Available columns include query ID, logical predicate, requested `k`, eligible count, study split, median latency, named recall metric, below-target state, paired change, result count, correctness failures, route, stop reason, policy opportunity, available work, and trace availability.

- Predicate and query metadata appear only when a matching workload artifact is available. A copied results directory must still work when original absolute paths no longer exist.
- Support filters for below-target recall, invalid responses, timeouts, slow queries, largest regressions, route, stop reason, and policy application. Descriptor-based filters appear only for verified attached development evidence.
- Distinguish queries from repeated measurements. Expanding a query exposes pass, sequence, pair ID, exact latency, recall, returned count, correctness state, and recorded telemetry for each sample.
- Let the user choose a sample; do not silently choose an unusually favorable execution as representative.
- Show returned IDs and recorded distances/scores only where present, with logical source IDs or metadata available through a separately verified dataset attachment.
- Show recorded correctness causes: duplicates, unknown IDs, predicate violations, short results, score/acknowledgement failures, and policy fallback/error where available.
- For empty eligible sets, show recall as undefined and evaluate the empty response according to the harness contract.

Acceptance: A below-target filter reports the number of queries with defined recall, the number with unknown recall, and the selected recall rule. Expanding a row preserves access to every recorded sample, including failures.

### F05. Trace and checkpoint viewer

**Purpose:** Explain search progress using evidence from a specific execution.

The header identifies backend, query, execution nonce, mode, route, index/build/registry hashes, feature groups, and capture completeness. The default horizontal axis is recorded cumulative layer-zero distance computations. Event order and checkpoint index are alternative views. A wall-time axis is available only if the source records the required timestamps.

Required interactions and panels:

- Select a checkpoint by clicking a plot, choosing a row, or using previous/next controls.
- Show checkpoint target, actual work, overshoot, component, sequence, observation watermark, and recorded decision.
- Plot selected available features such as qualifying result count, filter-hit observations, distance summaries, frontier size, and work. Offer meaningful presets and a registry-backed feature picker.
- Keep frontier, native retained-result heap, and observational best-`k` populations separately named. Keep component-local statistics separate from request-wide totals.
- Show lifecycle events and component boundaries, including exact work, HNSW work, fallback, final merge, and completion where recorded.
- Mark the observed stopping event and distinguish work at stopping from work performed during finalization or other components.
- Overlay actual prefix-stop labels only after verifying reference nonce and the available query/build/registry identities. Attach a label to the reference trajectory only when the artifact declares a matching prefix and a reference checkpoint label.
- Render sampled recall labels as measured points. Do not invent recall at unlabeled checkpoints or interpolate a continuous true-recall curve.
- Label the earliest success as **earliest tested checkpoint reaching target**. If none succeeded, retain the censored state; it does not prove that no successful checkpoint exists.
- Put divergent stop executions in a separate list with their measured results. Their observations cannot be attached as labels to the reference curve.
- Show truncation, recovered terminal telemetry, unavailable features, and missing artifacts at the affected panel. A recovered terminal count does not establish a complete trace.

Native measurements may have no feature trace. Their missing work values must not become zero or be copied from a no-op execution. A separate diagnostic execution is identified as separate evidence.

Acceptance: The existing ACORN label fixture displays two actual stop labels. The truncation fixture shows incomplete capture and cannot generate complete membership fractions or reference-prefix claims.

### F06. Policy and feature inspector

**Purpose:** Make the deployed policy inspectable and connect its inputs to the available evidence.

- Show name, content hash, schema, feature profile and registry hash, engine allow-list, feature groups, checkpoint interval, interpreter/numeric contract, and training/migration provenance.
- Render the bounded policy tree as readable conditions and continue/stop leaves. Provide the original JSON and a copy action.
- Show node count, depth, requested feature groups, and shape-model size. Use the harness validator for validity and current execution compatibility; opening the UI must not execute the policy against an engine.
- Provide feature definitions including units, population, scope, runtime versus development stage, availability, and route qualification.
- Display attached shape memory as structured JSON or a generic table in P0. Arbitrary fields do not imply a known model type or measured predictive quality.
- From a compatible recorded checkpoint, optionally highlight the decision path using a version-matched bounded interpreter with the recorded inputs. Label this as local re-evaluation. This enhancement requires a validated interpreter for that artifact version; it is not required for P0. If inputs are incomplete or contracts differ, show the recorded decision without inventing its branch path.
- Flag disagreement between recorded and locally re-evaluated decisions as a diagnostic requiring investigation.
- Compare two policy artifacts structurally and show exactly which fields or conditions changed. Display linked evaluations only when provenance supports the association.

Acceptance: An older policy remains readable with its original feature meanings and an explicit compatibility state. A feature unavailable at a checkpoint stays unavailable, and recorded fallback outcomes remain visible.

### F07. Correctness and evidence quality

**Purpose:** Keep distinct reasons for trusting or rejecting a result visible.

Provide four separate status groups:

1. **Input and exact conformance:** filter eligibility, exact-vector membership/order/distance checks, backend route proof, and tolerances.
2. **Response correctness:** per-sample validity, IDs, predicates, counts, acknowledgements, and runtime failures.
3. **Retrieval quality:** recall definition, below-target results, and empty-filter handling.
4. **Evidence quality:** server observation versus adapter assertion/unobserved state, trace completeness, identity matches, and membership audit coverage.

The conformance table links each failure to the original reproduction bundle. The artifact browser supports structured viewing and download of the logical query, oracle candidates, native result, comparison, and route evidence already present. Native plans retain their backend-specific structure and are labeled as timed-request evidence or separate diagnostic execution according to their source.

Membership audits show checked coverage, visited/frontier populations, complete versus incomplete reconstruction, missing identities, mismatches, and tuple pass/fail observations. Engine-specific populations remain explicit; PostgreSQL tuple multiplicity must not be presented as a simple graph-node fraction.

Acceptance: A conformance pass cannot hide a later invalid measured response. A correct low-recall result is shown as below target without being mislabeled as a predicate or identity error.

### F08. Study overview and evidence budgets

**Purpose:** Explain the study protocol and the evidence used to produce a policy.

- Open a study manifest and show dataset/workload identities, seed, target recall, split counts, registry, declared budgets, frozen policy hash, and associated artifacts.
- Show recorded ledger consumption for distinct labeled queries, engine executions, oracle distances, wall time, audit predicate evaluations, audit storage, and checkpoint labels. Keep checkpoint labels distinct from independent labeled queries.
- Distinguish a persisted current ledger from an older artifact's ledger snapshot. Display source and freshness. Never sum cumulative snapshots as if they were separate costs.
- Show remaining budget only when the manifest and ledger association is verified. Missing consumption is unknown.
- Show development, calibration, and final-test evaluations using the detail level the producer authorizes. Current calibration/test artifacts provide aggregates; their query table and trace drill-down remain unavailable.
- A frozen policy alone does not authorize exposing hidden test evidence. The UI consumes approved evaluation output and cannot use filesystem discovery to bypass the study service's split restrictions.
- Study-aware APIs and exports enforce the same restrictions as the screen. An unknown split must be labeled unknown; it cannot be relabeled development based on a folder name.
- Display final-test consumption from the ledger separately from successful completion of an evaluation artifact. A consumed test attempt with missing output is a distinct condition.
- Viewing already authorized artifacts must not call live evidence acquisition or modify budget accounting. Evidence exposure to an agent remains the responsibility of the study workflow.

Acceptance: Opening a calibration evaluation displays aggregates and an explanation of its available detail. No query data is exposed through hidden routes, downloads, saved views, or an alternate table export.

### F09. Saved analyses and portable exports

**Purpose:** Make an analysis reproducible and easy to discuss with an advisor.

- Save selection, filters, columns, chart settings, metric definitions, source content hashes, and UI/analysis version as a small view document outside source directories.
- Restore a view and verify its sources. If a source changed, show the difference and require an explicit refresh before replacing the saved result.
- Export the current table as CSV and chart as SVG/PNG with title, units, cohort, sample counts, metric definition, and source identity.
- Produce a self-contained HTML report with selected figures/tables, experiment description, configuration differences, validity and coverage information, policy identity, and provenance appendix. Provide a print layout suitable for a PDF through the browser.
- Include all active filters and exclusions in the report. A report made from a partial run carries that status visibly.
- Generate local deep links to a run, query, sample, or checkpoint. A copied link works only in a workspace containing the required artifacts; the HTML report is the portable review format.
- Reports include only selected permitted content. Raw vectors, full datasets, local absolute paths, and environment details beyond the research provenance are excluded by default, with an export preview listing included files/sections.
- Separate researcher annotations from measured observations and generated explanations. Notes can be saved without altering the experiment manifest.

Acceptance: Another person can open the HTML report offline and identify the comparison, quality metric, included population, missing evidence, and exact policy/build identities without access to the UI service.

## 6. Scientific and numerical rules

These requirements apply to every screen, filter, derived metric, and export.

| Topic | Required behavior |
| --- | --- |
| Canonical versus tie-aware recall | Name the metric explicitly. Benchmark summaries currently use `recall`; study evaluations use tie-aware recall. Do not merge them into a generic “recall” value without a stated definition. |
| Recall target | Use the associated study's target when available. For an independent run, allow an explicitly labeled exploratory target; do not imply it was predeclared. |
| Recall denominator | Follow `min(k, eligible_count)` and the producer's tie policy. Empty eligible sets have undefined recall and separate correctness semantics. |
| Below-target query fraction | In an exploratory run view, use the arithmetic mean of the selected recall metric over valid, defined samples for each query, then count query means below the displayed target. Also expose sample-level violations and undefined/invalid coverage. Label this as a UI-derived descriptive metric; use a declared study rule if it supplies a different definition. |
| Latency population | Use successful, valid, evaluated measurements. Show failures and exclusions beside the statistic. Never fabricate a latency for a timeout. |
| Repetitions and weighting | Label sample-weighted versus query-weighted results. The existing backend summary and query-grouped paired effects have different aggregation rules and must not look interchangeable. |
| Pairing | Scope pair IDs to their run and backend; the textual IDs may repeat in another run. Reject duplicate members for a pair/mode rather than silently choosing one. |
| Paired delta | Treatment minus baseline. Negative latency delta means faster; positive recall delta means higher recall. Show recall deltas in percentage points when formatted as percentages. |
| Relative latency | Label the actual estimator. The harness's mean of query-level relative changes is not the ratio of two displayed aggregate means. |
| Confidence intervals | Preserve the exported grouped bootstrap method, seed, and query count. Query repetitions and checkpoint labels are not independent queries. A one-query degenerate interval must not be described as strong evidence. |
| New filtered statistics | Recompute through a versioned analysis service using shared harness semantics. Counts and exclusions must follow the filter. Never reuse an unfiltered confidence interval for a subset. |
| Tail latency | Honor saved protocol thresholds and statuses; defaults are 100 successful samples for p95 and 1,000 for p99. Reapply the threshold after filtering. |
| Missing values | Distinguish unavailable, unsupported, not recorded, invalid, not evaluated, and insufficient samples. Display real zero as zero. |
| Route evidence | Only source-qualified route observations support route-specific interpretation. Keep stock unobserved routes visible as unknown. |
| Policy status | Distinguish policy requested, opportunity available, interpreter invoked, stop chosen, fallback, and runtime error. An evaluated policy may continue until native completion. |
| Timing role | Keep development traces, membership audits, separate native diagnostics, and benchmark timing explicitly identified. Trace/audit results do not automatically establish production latency. |
| Work counters | Preserve counter definitions, phase, component, units, and availability. Sum only disjoint populations with compatible definitions. Fewer distance computations do not by themselves prove lower wall time. |
| Overhead | Feature/interpreter nanoseconds and client latency milliseconds measure different scopes. Display units and scopes; avoid subtracting unrelated counters to invent server time. Trace-export time is outside the measured request. |
| Quality judgments | There is no automatic single “best backend” or “best policy” ranking. Display the target, coverage, correctness, and trade-offs underlying any selection. |
| IDs and large integers | Preserve canonical signed-64-bit IDs losslessly. Serialize IDs to the browser as strings or another lossless representation. Large counters must not be rounded by JavaScript number conversion. |

For an aggregate-only artifact, metrics absent from that aggregate remain unavailable. The UI cannot infer a recall distribution, below-target fraction, paired confidence interval, or per-query behavior from a mean alone.

## 7. Data integration and provenance

### 7.1 Source mapping

| Existing source | UI use | Important limit |
| --- | --- | --- |
| `manifest.json` | Run identity, configuration, host, build, timing role, policy, status | Not every historical manifest includes every current field |
| `summary.json` and summary/paired CSVs | Published summaries, paired effects, coverage | CSV and JSON are alternate encodings of the same result, not additional observations |
| `measurements.jsonl` | Evaluated samples, correctness, recalls, IDs, telemetry, trace links | Needs a schema-compatible validated reader |
| `measurements.parquet` | Efficient reading and filtering of evaluated samples | Must match the authoritative evaluated records; do not double-count |
| `raw-measurements.jsonl` | Transport results and interrupted-run diagnosis | Correctness evaluation may not have happened; raw success is insufficient for a valid analyzed sample |
| `conformance.json`, `conformance-failures/` | Exact/filter qualification and reproduction details | Qualifies the recorded workload/backend; does not prove all measured responses valid |
| `preparation.json` | Import/reuse, storage, physical field mapping, index/resource details | Storage measures retain their original scope and units |
| Normalized trace envelope and raw trace JSONL | Event and checkpoint inspection | Normalized meaning depends on the recorded protocol/registry; partial capture stays partial |
| Diagnostic artifacts | Native plan/profile inspection | Often a separate execution; retain that distinction |
| Policy JSON, embedded policy, registry | Tree, features, provenance, compatibility | Shape memory is currently an arbitrary bounded object |
| Study manifest and ledger | Splits, target, declared and consumed budgets, frozen policy | Ledger snapshots are cumulative; association and freshness must be known |
| Development descriptor artifacts | Selectivity, geometry, hardness, cohort analysis | Development-only and already charged evidence; viewing does not recompute it |
| Prefix labels and membership audits | Measured stop outcomes, reconstructed populations | Joining requires identity and coverage checks |
| Evaluation and overhead artifacts | Approved aggregates and available development rows | Some current artifacts lack complete run/study/host identity |
| Original workload and dataset, optionally attached | Logical predicates, IDs, metadata | Verify identities before joining; do not load all vectors for ordinary result browsing |

Raw transport records are preserved as recorded evidence. Evaluated records supply per-sample correctness and quality. Saved summaries supply published aggregate results. When alternate encodings or a recomputation disagree, display a data-consistency issue with both sources; do not silently overwrite a source or select the more favorable result.

### 7.2 Identity and attachment rules

Use opaque content-derived artifact IDs internally. A filename, query ID, policy name, or nearby directory alone is insufficient to join evidence.

Verify the identities supplied by each artifact: dataset/workload or query hash, study identity, backend, physical index/build, policy, protocol, registry, feature set, and execution/reference nonce as applicable. Do not substitute an index configuration hash for a physical index generation identity without explicitly documenting what the source proves.

An imported standalone artifact may be inspected with an incomplete association. Its relationships are marked unverified, and analyses requiring those relationships remain unavailable. User notes or manual grouping do not upgrade scientific provenance. For missing optional workload files, offer attachment and identity validation; retain the existing results if attachment fails.

Artifacts from earlier contracts retain their original meaning through explicit adapters. The compatibility catalog distinguishes full current analysis, legacy inspection, unsupported, and invalid. Merely changing a schema-version number never constitutes migration.

### 7.3 Required analysis boundary

Place artifact reading, validation, grouping, statistics, compatibility checks, and export assembly in a Python analysis layer that can be tested without a browser. The frontend consumes bounded view models and renders interaction. Reuse the existing evaluator, statistics, and policy logic where their contracts apply.

The analysis layer must provide these capabilities; endpoint names are an implementation choice:

| Capability | Request | Response |
| --- | --- | --- |
| Catalog | Registered roots and filters | Paginated run/artifact metadata and validation status |
| Run detail | Opaque run ID | Overview, coverage, provenance, supported analyses |
| Comparison | Sources, modes, scope, filters, metric | Compatibility decision, metrics, effects, intervals, exclusions |
| Query search | Run/comparison and filters | Paginated query rows, totals, denominator definitions |
| Sample detail | Run/backend/query/sample identity | Recorded measurement and authorized attachments |
| Trace slice | Trace ID, component, checkpoint/event range | Bounded events/features, completeness, authorized labels |
| Policy detail | Artifact hash and optional compatible checkpoint | Validated tree, registry, provenance, optional local branch evaluation |
| Study detail | Study ID | Authorized aggregate/detail availability, manifest, ledger sources |
| Export | Saved view and chosen sections | Report/CSV/figure plus source and analysis metadata |

Every response includes source identity, applied filters, aggregation/metric definition, availability, and warnings relevant to that view. Query APIs enforce known study split restrictions before returning data. File references exposed to the frontend are approved artifact IDs, not unrestricted filesystem paths.

### 7.4 Backend work required before P0

The repository already supplies much of the evidence, but the following changes are prerequisites or explicit limits:

| Gap observed in the current source | Required action |
| --- | --- |
| `schema.py` declares evidence measurements as schema 6, while `Measurement` and `read_measurements()` accept 4/5 | Align the model, writer, and reader under explicit version adapters; validate representative v6 output before connecting the UI. Do not simply relax all validation. |
| Studies, normalized traces, evaluations, audits, and overhead outputs have different envelopes and incomplete shared identity fields | Add typed readers and a capability result for each artifact kind. Add versioned provenance at generation time for future artifacts. Existing artifacts with insufficient evidence remain inspectable but cannot acquire invented relationships. |
| Study evaluations return per-query rows only for development | Preserve the restriction. Add any newly required calibration/test statistic inside the authorized evaluator as an aggregate, rather than exporting hidden rows to the UI. |
| Existing study aggregates omit recall distributions, target failure fractions, and uncertainty | P0 reports these as unavailable for those artifacts. Add explicit aggregate fields before requiring those panels for studies. |
| Query predicates and source metadata may live only at external workload/dataset paths | Add verified optional attachment support; a future portable result package should include a small query-description snapshot under the study's exposure rules. |
| Progress callbacks are strings and the run manifest gives coarse status | P0 shows observed file/status information only. Structured progress, process liveness, and cancellation are prerequisites for P2. |
| Shape models and training provenance are generic dictionaries; no standard acquisition history is present | P0 provides generic inspection. Typed model summaries and method/budget histories are required for P1 charts. |
| The Python policy evaluator is documented and typed for policy v1, while current engine policies use v2 | Before enabling optional local branch re-evaluation, establish v2 feature typing and interpreter parity against versioned engine/golden fixtures. P0 can show the validated tree and recorded decisions without re-evaluating them. |
| Some policy/trace/overhead associations cannot establish the full matched experimental conditions | Show unverified/descriptive status. Extend producer provenance before enabling a controlled-effect label. |

These are specification dependencies, not claims that they have been implemented by this document.

## 8. P1 research analysis

### F10. Data-shape and query-group explorer

Join approved development descriptors with query outcomes. Show global versus local filter prevalence, available alignment/hardness measures, and their association with work, recall, or latency changes. Support scatter plots, distributions, and tables grouped by explicitly defined ranges.

Selecting a range or points creates a visible exploratory query group usable in Compare and Queries. Show group definition, independent query count, missing descriptor count, and within-group outcome distributions. A group discovered through inspection remains labeled exploratory; it is not silently treated as a predeclared hypothesis. Correlation views do not assert causation.

Add learned model predictions versus observed outcomes only when a typed prediction artifact supplies the target, split, predicted value/uncertainty, observed value, and provenance. Keep exact oracle descriptors distinct from runtime policy inputs.

Acceptance: The researcher can inspect whether policies fail more often for locally sparse filters, and export the cohort definition and observed evidence supporting that finding.

### F11. Learning curves and method comparison

Compare methods at matched evidence budgets, including native/fixed controls where applicable, a conventional learner, direct policy synthesis, and synthesis with shape memory when those results exist.

- Plot structural prediction error, recall, below-target fraction, latency, and work against independent labeled-query budget or another explicitly selected cost.
- Show repeated seeds/study instances individually and summarize them only under a stated aggregation and uncertainty rule.
- Track passive evidence, labels, oracle work, agent calls/tokens, training/search time, calibration, and monetary cost as separate quantities when recorded.
- Keep method identity, information available, policy language, calibration procedure, dataset, split, and target visible so the shape-memory ablation can be assessed.
- Provide adaptation break-even only with consistent cost units and a positive measured deployed saving: `(candidate adaptation cost − baseline adaptation cost) / (baseline per-query cost − candidate per-query cost)`. Show uncertainty and undefined cases; heterogeneous wall/CPU/monetary costs cannot be combined without an explicit model.

Prerequisite: A versioned method/evaluation history must identify method, budget checkpoint, study/dataset, seed, model and policy hashes, information access, measurement protocol, and cost sources. Current ledger snapshots alone do not define a learning curve.

Acceptance: A shape-memory comparison can be traced to two methods with the same declared evidence allowance, and any missing fairness metadata is visible.

### F12. Shape-model evolution

Show model versions, supported structural claims, evidence counts, uncertainty when supplied, changed conditions/tables, and linked prediction/policy outcomes. Let a researcher select a claimed regularity and inspect the development evidence permitted by the study.

Generated natural-language explanations are labeled as explanations. The executable/numerical model and measured evaluations establish the result. No UI-generated narrative is presented as an independently validated discovery.

Prerequisite: Freeze a typed shape-model and evidence-reference contract before building specialized visualizations. Until then, the P0 structured inspector is the complete supported behavior.

## 9. P2 experiment execution

Add execution only after analysis use demonstrates a recurring need to replace CLI steps.

The execution workflow should support selecting canonical input files, backend, configuration, modes, policy, study, and output location; validating those selections; previewing the resolved configuration and exact CLI equivalent; and then launching the existing application service.

Required operational capabilities:

- Non-mutating preflight for environment, resources, compatibility, policy validity, and input identities before expensive work.
- Structured progress for validation, oracle preparation, import/index, conformance, warmup, measurement, offline evaluation, export, and completion.
- Correct ownership, locking, and concurrent-operation restrictions for shared database resources.
- Persistent job identity and reconnection after the UI closes; distinguish UI disconnection from engine completion/failure.
- Cancellation semantics that retain partial artifacts, stop the owned work safely, and record what completed. Cancellation must never imply a statistical result that was not produced.
- A new run for changed parameters. Existing experiment artifacts remain immutable.
- Explicit study freeze and final-test actions through the same split/budget enforcement used by the CLI. Test consumption is visible before initiating it.
- Separate resource inspection and exact-target cleanup with the existing dry-run behavior if cleanup is later included.

A P2 release requires an independently reviewable operational specification. P0/P1 must not depend on job execution being present.

## 10. Quality requirements

### Local operation and data handling

Serve the UI on loopback by default. Opening, filtering, and exporting existing artifacts works offline. Send no experiments, queries, vectors, telemetry, or usage analytics to external services by default.

Read only user-registered roots and validated attachments. Resolve paths and symlinks before allowing access. Treat filenames, notes, native errors, predicates, and policy text as data; escape them in the UI and generated HTML. Do not execute embedded scripts, policy source strings, shell commands, or arbitrary HTML from an artifact. Browser-facing access must not expose a generic local-file reader to other websites.

Source artifact checksums before and after a viewer session must match. UI preferences, notes, cache files, exports, and saved views use separate storage. Deleting an entry from the catalog removes its UI registration, not its experiment directory.

### Responsiveness and scale

The following are initial acceptance targets to measure on a recorded local reference machine with at least 8 CPU cores, 16 GiB RAM, and SSD storage. They are design targets rather than observed performance claims.

- Show useful catalog metadata for 100 run manifests within 5 seconds of opening a root.
- Display an already indexed run overview within 2 seconds.
- Filter/sort an indexed workload of 10,000 queries backed by up to 1 million measurements within 2 seconds, with feedback for slower work.
- Open the first usable view of a 64 MiB trace within 3 seconds using bounded loading; navigate loaded checkpoints within 200 ms.
- Paginate event/sample tables and load individual trace components as needed. Rendering must not create one browser element per trace event.
- Keep ordinary result browsing independent of full vector-dataset loading. Perform heavy parsing/aggregation off the browser's interaction thread and report cancellable progress for long indexing/export operations.
- Define performance measurements with the exact fixture size, hardware, browser, and cold/warm cache state. Larger inputs degrade with progress and bounded pages rather than freezing or crashing.

### Accessibility and legibility

All workflows must work by keyboard with visible focus. Charts have textual summaries and accessible data tables. Do not use color alone for modes, failures, or selection. Support browser zoom to 200%, clear contrast, reduced motion, and horizontal scrolling for dense scientific tables.

Desktop is the primary layout. At narrow widths, prioritize overview and reading exported reports; retain access to full tables through controlled scrolling. A dedicated mobile editing/analysis interface is outside the initial scope.

### Predictable application states

Each major screen has explicit loading, empty, partial, unavailable, incompatible, invalid, and failed states as applicable. Explanations name the missing input or failed condition and the next useful action. Avoid a generic blank chart for all failure modes.

Examples: `No trace captured for this sample`, `Recall labels available at 2 of 8 checkpoints`, `Per-query rows withheld by the study evaluator`, `Registry differs from this comparison`, and `Missing original workload; predicate text unavailable`.

## 11. Acceptance and validation plan

Use deterministic saved artifacts for UI verification. Repeatedly starting databases is unnecessary for reader, rendering, and interaction checks. Use live engine testing only when a producer or execution change requires it.

| Scenario | Pass condition |
| --- | --- |
| Complete current evidence run | Overview matches saved evaluated records, summaries, pair coverage, and provenance |
| Stock run with no route observations | Latency/recall remain usable; route and policy-opportunity analysis remain unavailable |
| Incomplete run or timeout | Missing measurements and failures are visible; successful latency does not absorb a fabricated timeout duration |
| Small sample | Tail statistics remain suppressed and uncertainty is not overstated |
| Empty eligible set | Recall is undefined, with correct empty-response behavior |
| Duplicate/unknown/predicate-invalid IDs | Invalid sample remains inspectable and is excluded from valid-latency populations |
| Same textual pair ID in two runs | Runs are never accidentally paired or deduplicated together |
| Missing or mismatched artifact identity | Inspection works where possible; unsupported joins and controlled-effect claims are blocked |
| Canonical versus tie-aware recall | Definition and selected target remain explicit across tables, plots, and exports |
| Matched and divergent prefix labels | Only valid matched labels attach to the reference curve; censored and standalone results retain their meaning |
| Truncated trace and recovered terminal | Missing coverage remains visible; reconstructed completeness is not invented |
| Multi-component Lucene trace | Component-local and request-wide quantities stay distinct; one component's stop does not imply request completion |
| PostgreSQL membership audit | Tuple outcomes, graph identities, checked coverage, and reconstructed fractions retain their separate populations |
| No-op and active/always-continue policies | Observation, interpreter, and net policy comparisons receive the correct interpretation |
| Calibration/test artifact | Authorized aggregate-only behavior holds in screens, APIs, saved views, and exports |
| Legacy artifact | Original semantics are retained; incompatible versions do not pool silently |
| Changed source or inconsistent encoding | Cached results invalidate or show a consistency issue; stale results are not represented as current |
| Large 64-bit canonical ID | It survives load, selection, copy, join, and export exactly |
| Offline portable report | Report opens independently and includes metric definitions, filtering, counts, limitations, and provenance |
| Viewer immutability | Checksums of source artifacts and study ledger remain unchanged |

Minimum researcher walkthroughs:

1. Open a run, identify its largest query regression, select the responsible sample, inspect available evidence, and return to the same filtered table.
2. Compare native and policy results, inspect recall failures alongside latency, and export a report with the exact population and provenance.
3. Open a prefix-label artifact, distinguish tested success from censored or divergent results, and inspect the linked checkpoint when present.
4. Open a study and explain its target, recorded budget usage, frozen policy, and available final evaluation without exposing withheld query evidence.

P0 is accepted only when these walkthroughs work with current saved artifacts and the relevant edge cases above. Numeric reconciliation, provenance, and access rules take precedence over decorative completeness.

## 12. Delivery sequence and completion criteria

### Increment A: Trustworthy experiment reader

Resolve current schema incompatibilities, implement typed artifact adapters and the catalog, and deliver Run overview plus an Artifacts view. Validate copied, missing, partial, and legacy inputs. Completion: a researcher can understand a run and its validity without opening JSON manually.

### Increment B: Comparison and query investigation

Add paired comparison, compatibility differences, filters, query/sample details, and saved analysis state. Completion: the researcher can explain an aggregate change by inspecting the underlying queries, with numerical agreement against the harness output.

### Increment C: Evidence and study review

Add trace/checkpoint inspection, policy tree, prefix labels, audit/conformance details, study aggregates/budgets, and portable reports. Completion: all P0 walkthroughs and access/identity cases pass.

### Increment D: Research-specific analysis

Use the first complete policy experiment to settle the typed model and method-history contracts, then implement the P1 plots that answer recurring research questions. Completion: the shape-memory ablation and evidence-efficiency claims can be inspected with their supporting data.

Evaluate value by observing whether the researcher can answer the core questions through these workflows with fewer manual file joins and fewer ambiguous comparisons. Do not use the number of screens or charts as the success criterion. Revisit execution controls only after actual usage identifies a persistent operational bottleneck.

## 13. Source references

This specification describes proposed UI behavior. Existing capabilities and gaps were checked against these local sources on September 27, 2026:

- [Research plan and evaluation requirements](learning-data-shape-filtered-ann-project-plan-v2.md)
- [Harness overview and outputs](../harness/README.md)
- [Measurement methodology](../harness/docs/methodology.md)
- [Instrumentation, study evidence, and live qualification](../harness/docs/evidence.md)
- [Canonical artifact formats](../harness/docs/formats.md)
- [Schema constants](../harness/src/fannbench/schema.py), [measurement models](../harness/src/fannbench/models.py), and [result readers/writers](../harness/src/fannbench/results.py)
- [Run creation and trace export](../harness/src/fannbench/runner.py)
- [Aggregation and paired statistics](../harness/src/fannbench/statistics.py)
- [Study manifests, ledgers, prefix labels, and evaluator restrictions](../harness/src/fannbench/evidence/study.py)
- [Membership audit semantics](../harness/src/fannbench/evidence/audit.py)
- [Policy artifact validation](../harness/src/fannbench/policy/models.py)
- [CLI artifact production](../harness/src/fannbench/cli.py)

When documentation and executable contracts differ, implementation must resolve the discrepancy explicitly and retain representative versioned fixtures. The current schema-6 reader mismatch is one such prerequisite.
