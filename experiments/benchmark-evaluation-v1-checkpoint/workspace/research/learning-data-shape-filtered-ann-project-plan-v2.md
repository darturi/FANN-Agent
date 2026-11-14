# Learning Data Shape from Query Executions for Structure-Aware Filtered ANN Search

## Project-planning brief — Version 2

This project investigates whether an offline language-model agent can learn a compact, reusable description of workload-relevant data structure from a limited stream of database query executions, and whether that learned structure improves later query execution decisions. The first controlled application is stopping in filtered approximate nearest-neighbor (ANN) search: the search algorithm and traversal remain fixed, while a small generated policy decides when enough of the search graph has been explored.

The conceptual contribution is broader than stopping. The project separates **learning how the data behaves** from **using that knowledge to control a query**. The required semester experiment keeps the control action deliberately narrow so that the value of learned structural knowledge can be isolated and evaluated rigorously.

The scope is one researcher over approximately fourteen weeks. This plan incorporates literature assessed in the September 8, 2026 research briefs; it does not claim a new exhaustive literature search. It proposes experiments rather than reporting results, and all novelty claims remain hypotheses until the closest systems and released artifacts have been reproduced or compared appropriately.

## 1. Central research idea

Database optimization traditionally uses schema information, statistics, constraints, and execution feedback to choose efficient ways to answer queries. Some properties are explicit and exact, such as keys or a verified tree-shaped subgraph. Others are empirical regularities, such as correlations, clusters, skew, or relationships between a query's local neighborhood and a metadata filter.

The motivating idea is that repeated query executions reveal information about these regularities. An agent may be able to turn a small number of observations into a persistent and inspectable model of **data shape**, then compile that model into inexpensive execution logic for future queries.

For the semester study, the central question is:

> Can an offline agent acquire a compact model of workload-relevant data shape from a bounded stream of filtered-ANN query executions, and can that model improve stopping decisions on unseen queries at a fixed empirical recall target?

The intended pipeline is:

```text
query executions and a bounded set of exact labels
                         ↓
          agent acquires structural knowledge
                         ↓
        compact, inspectable shape model
                         ↓
          agent synthesizes a stop policy
                         ↓
     ordinary executable code for future queries
```

The language model runs during development or periodic batch adaptation, not on the latency-critical path of each deployed query.

## 2. Connection to structural query optimization

The project grows from the same general principle as exploiting tree-shaped substructures in property graphs: useful regularity in the data can justify a more efficient execution strategy. Tree annotations can turn some path traversals into indexed tests, provided that the tree property is valid and the required annotations and access paths exist. [^1][^2]

This project studies a statistical rather than exact version of that principle. In filtered ANN, a category may be globally rare but locally dense around some query regions, or globally common but locally sparse. Those relationships can predict how quickly an approximate search will find good qualifying results. Unlike a verified tree invariant, an observed filter–geometry relationship normally cannot justify an exact semantic rewrite. It can inform a calibrated decision under an empirical accuracy objective.

This distinction matters:

- **Exact structural constraints** can establish that a transformation preserves query semantics within a declared scope.
- **Statistical structural regularities** can predict cost or quality but may fail on individual queries.
- **An available execution mechanism** is still required. Knowledge that a subgraph is a tree does not create a tree-label index, and knowledge that a filtered-ANN query is easy does not help unless the engine exposes a safe way to stop or select a strategy.

The work therefore belongs in the lineage of semantic query optimization and learned or feedback-driven optimization, while asking a narrower question about how an agent acquires and operationalizes structural knowledge. [^3]

## 3. Concrete problem setting

ANN means **approximate nearest neighbor**, not artificial neural network. Each stored item has a vector, such as a document embedding, and metadata, such as a category. A filtered query might ask for the ten vectors closest to a query vector among items whose category is `biology`.

Exact search computes the true nearest qualifying items but can be expensive. HNSW instead navigates a layered proximity graph and usually examines only a fraction of the database. The HNSW graph is an index derived from vector similarity; it is not the application-level property graph used to represent a social network. [^4]

The difficulty of a filtered query depends on more than global filter selectivity. Consider two filters that each match 1% of the database:

- Qualifying items for one filter may cluster near the query, so useful results appear quickly.
- Qualifying items for the other may be sparse around the query, so much more exploration is required.

The first project fixes graph construction, distance metric, expansion order, candidate handling, and filter semantics. At declared checkpoints, the deployed policy chooses only:

```text
continue the existing traversal
or
stop and return the current best qualifying results
```

Although this is a binary action, it is made repeatedly from a rich state. It can allocate different amounts of search work to different queries while preserving a tractable experimental design.

## 4. Research questions and hypotheses

### RQ1 — Structural acquisition

Can an agent infer compact structural summaries from a limited sequence of query traces and labeled executions that predict properties of unseen queries?

Candidate prediction targets include local filter prevalence, search hardness, the amount of exploration needed to reach a recall target, and the likelihood that further exploration will improve the current result set.

**H1:** Learned structural summaries will predict held-out query behavior more accurately than global selectivity and other simple workload-wide summaries alone.

### RQ2 — Downstream optimization value

Does conditioning a stopping policy on accumulated structural knowledge improve its latency–recall trade-off on unseen queries?

**H2:** At a fixed empirical recall target, a policy with access to learned shape memory will require less search work than a policy synthesized from only the current query trajectory.

### RQ3 — Agent contribution

Does an agent acquire or use structural knowledge more effectively under small evidence budgets than strong conventional methods given the same information?

**H3:** At some practically relevant evidence budgets, the agent-based method will reach a better held-out trade-off between structural prediction, adaptation cost, and query performance than direct policy search or conventional learning.

This is the most uncertain hypothesis. If a compact conventional model matches the agent, the project must report that result rather than weaken the baselines.

### RQ4 — Transfer and limitations

Which learned regularities transfer to unseen query vectors and query–filter combinations, and in which structural regimes do they fail?

The required transfer test is within a fixed workload snapshot. Transfer to new datasets, distribution drift, unseen filter values, and different engines are harder extensions and should be reported separately if attempted.

## 5. Novelty and closest prior work

The proposal does not claim that data correlations, adaptive search termination, agent-generated database components, or query-dependent ANN routing are individually new.

| Prior direction | What it already establishes | Consequence for this project |
|---|---|---|
| Semantic query optimization and tree-aware graph processing | Verified constraints and structural indexes can enable faster equivalent execution | The structural motivation has a substantial pre-LLM lineage; the contribution must concern acquisition and operational use, not the observation that structure matters [^1][^3] |
| E2E adaptive termination | Early filter-valid ratios and distance statistics can drive inexpensive learned stopping | Adaptive filtered-ANN stopping and filter-aware features are already established; E2E is a central comparator [^8] |
| Bespoke-Card and related agentic specialization | Agents can synthesize workload-specific database code using evaluation and structured feedback | Agent generation plus iterative feedback is not sufficient novelty by itself [^9] |
| Query-aware filtered-ANN routing | Conventional learned models can use selectivity, geometry, and predicate information to choose query-dependent strategies | A strong non-agent learner with equal information is required [^10] |
| Filtered-ANN benchmark and hardness work | Filter–geometry relationships and controlled workload difficulty are already studied | Neither measuring alignment nor building a structural generator is the primary contribution [^5][^7] |

The candidate contribution is the explicit, controlled separation of:

1. Acquiring a bounded and persistent structural model from query experience.
2. Evaluating that model independently on held-out structural predictions.
3. Compiling the model into a cheap execution policy.
4. Measuring whether the explicit structural-acquisition stage improves downstream decisions under equal evidence and computation budgets.

A defensible positive claim would be:

> Under explicitly measured adaptation budgets, an agent-acquired shape model predicts held-out filtered-search behavior and enables compact stopping policies that meet the target recall with less execution work or less labeled evidence than strong equally informed alternatives.

This is a hypothesis, not a promised result. Simply asking an LLM to summarize traces and then generate a decision tree would be too incremental unless the evaluation isolates a measurable benefit from explicit structural acquisition.

## 6. The two generated artifacts

The project must keep structural acquisition and query control distinguishable. The agent produces two separately inspectable artifacts.

### 5.1 Shape model

The **shape model** is a bounded representation of persistent, workload-level knowledge inferred from development executions. It must not be an unconstrained natural-language memory whose contents cannot be reproduced or scored.

Candidate fields include:

- Global prevalence of each allowed filter value.
- Filter-valid fractions by declared query region, distance bucket, or search checkpoint.
- Curves describing how quickly qualifying candidates appear as exploration increases.
- Rates at which the best qualifying distances improve.
- Relationships between early observations and eventual search difficulty.
- Evidence counts and uncertainty estimates for every stored summary.

The exact representation is a pilot decision. Plausible forms include a small table, bounded decision rules, piecewise numerical profiles, or a short program over a fixed summary interface. Raw query identifiers, full vectors, stored ground-truth answer sets, and query-specific lookup tables are prohibited.

Every stored claim must have:

1. A defined computation or interpretation.
2. A declared evidence source.
3. A construction and maintenance cost.
4. A way to evaluate it on held-out queries.

Natural-language explanations may accompany the artifact, but evaluation must depend on the executable or numerical representation.

### 5.2 Stopping policy

The **stopping policy** is an ordinary, inexpensive function evaluated at fixed checkpoints. It receives approved current-query features plus permitted values from the shape model and returns `continue` or `stop`.

Candidate current-query features include:

- Accumulated distance computations or expansions.
- Number of qualifying results found.
- Observed filter-valid fraction.
- Normalized distance summaries.
- Recent changes in the current best qualifying results.
- Queue or frontier summaries exposed cheaply by the engine.

The policy language should allow bounded arithmetic, comparisons, and short conditional expressions. Set a code-size or expression-depth limit. Define safe behavior for missing values, empty queues, numerical errors, and invalid generated code. Invalid decisions fall back to continuing the base search and must be counted.

## 7. What the agent observes

Information access must be divided into explicit categories so that the experiment does not accidentally give one method more knowledge than another.

### Passive execution evidence

These observations can be collected during ordinary instrumented approximate queries without computing exact answers:

- Query and filter descriptors allowed by the protocol.
- Search-state features at checkpoints.
- Latency and distance-computation counts.
- Filter matches encountered during traversal.
- Changes in the approximate result set.

Passive observations may reveal patterns in the data, but they do not reveal true recall.

### Labeled development evidence

For a bounded subset of development queries, compute exact filtered nearest neighbors and collect sufficiently long reference trajectories. This reveals recall at each prefix and supports diagnostics such as premature stopping and unnecessary continuation.

Every labeled query, exact computation, reference trajectory, and ground-truth-derived diagnostic must be charged to the evidence and computation budgets.

### Evaluator-only information

Final-test answers, exhaustive candidate comparisons, and any oracle structural summaries remain hidden from all methods until evaluation. Oracle summaries may be used in a separately labeled diagnostic condition to estimate the maximum possible value of structural information.

### Shared-information rule

All agent and non-agent comparators receive the same raw observations or the same derived summaries in the comparison being claimed. If the agent chooses additional probes, that becomes a separate active-acquisition experiment and every probe must be charged.

## 8. Learning as queries are conducted

The required experiment simulates cumulative learning using ordered development batches rather than deploying an unconstrained online language model.

1. Predeclare and order a development stream.
2. Expose the first batch of passive traces and the allowed labeled subset.
3. Let each method update its shape model and stopping policy within a fixed budget.
4. Evaluate interim versions on a validation set to produce learning curves.
5. Repeat at geometrically spaced evidence budgets.
6. Freeze the final representation, code, and calibration procedure.
7. Run once on the untouched final test set.

This protocol captures the idea that the system accumulates knowledge from query experience while preserving clean evaluation boundaries. It avoids the engineering and statistical complications of asynchronous production updates, delayed feedback, and a policy changing during final measurement.

The number and size of batches should follow pilot costs. Multiple checkpoints from one query are correlated observations and do not count as independent queries.

## 9. Proposed implementation and experimental workflow

### Phase 1 — Validate the engine and opportunity

Select one instrumentable HNSW implementation, preferably one used by a close adaptive-termination artifact. Verify buildability, deterministic settings where possible, fixed checkpoint instrumentation, and the ability to execute generated stopping logic with measurable overhead.

The pilot must establish both:

- The base traversal can reach the target recall under the maximum budget.
- Meaningful variation exists in when different queries first reach that target.

A stopping policy cannot recover a true neighbor that the fixed traversal never visits. Base-search failures must be recorded separately from premature stopping.

### Phase 2 — Build exact ground truth and trace capture

For every labeled query, compute exact filtered nearest neighbors independently. A long approximate search is not exact ground truth.

Instrument sufficiently long reference trajectories at fixed checkpoints. Each checkpoint records approved search features and the current qualifying result set. Validate that replaying a stopping decision along a recorded fixed trajectory reproduces actual engine results.

Trajectory replay is valid only for stopping along the same traversal. Changing beam width, expansion order, graph structure, or candidate handling requires new execution.

### Phase 3 — Define the bounded shape representation

Use pilot data to choose a small representation that can express local-versus-global filter relationships without memorizing queries. Freeze the representation and its permitted input functions before the main comparison.

Evaluate candidate summaries on simple prediction tasks before synthesizing policies. This establishes whether the representation contains useful structural information independently of downstream stopping performance.

### Phase 4 — Acquire shape models

At each evidence budget, the agent receives the current development evidence, a bounded shape-model language, and evaluation tools. It proposes or revises the shape model and receives structured feedback about incorrect, unsupported, or unhelpful summaries.

Feedback may include:

- A predicted easy query that was actually hard.
- A claimed local density pattern that failed on held-out development evidence.
- A summary supported by too few independent queries.
- A structural distinction that did not improve prediction beyond a simpler statistic.

Retain the generated artifacts, prompts, feedback, model identifiers, seeds, token counts, and evaluation ledger.

### Phase 5 — Synthesize policies using the shape model

Given the frozen shape representation available at that evidence budget, the agent generates a bounded stopping policy. Development feedback distinguishes:

- **Premature stopping:** The policy stops below the recall target even though later points on the same trajectory improve the answer.
- **Unnecessary continuation:** The policy continues substantially beyond a point that already meets the target.

Compare this two-stage process with direct policy synthesis from the same underlying evidence. This ablation tests whether explicitly acquiring persistent structural knowledge adds value beyond giving the agent more text or more iterations.

### Phase 6 — Calibrate

After code selection, freeze the shape model and policy. Use a separate calibration split to set a conservativeness parameter. Design the parameter family so that increasing conservativeness can only delay stopping along the fixed trajectory.

Predeclare the calibration objective and apply a comparable calibration procedure to competing methods. Calibration supports an empirical quality target; it does not guarantee recall for every future query or arbitrary distribution shift.

### Phase 7 — Deploy and test

Run the frozen policy on untouched test queries in the actual engine. Measure wall-clock latency, distance computations, feature and shape-lookup overhead, policy-evaluation overhead, and recall. Replay is a development accelerator, not a substitute for final deployed measurements.

## 10. Benchmark and workload design

### Real workloads

Start with public embeddings paired with meaningful metadata. Existing filtered-ANN benchmark studies provide candidate datasets and harnesses, but suitability, licensing, scale, predicate support, and artifact compatibility must be confirmed during the pilot. [^5][^6]

Aim for one real dataset in the feasibility phase and a second only after the full pipeline works.

### Controlled structural family

Use a synthetic or semi-synthetic workload family that holds vectors and global label counts fixed while varying how qualifying labels align with vector neighborhoods:

- **Locally clustered:** Qualifying items concentrate near relevant query regions.
- **Approximately independent:** Filter membership is largely independent of vector geometry.
- **Locally sparse or anti-aligned:** Qualifying items are uncommon near relevant query regions despite the same global selectivity.

Use multiple selectivity levels and independent data seeds. Do not construct each dataset around the eventual test queries. Measure realized local relationships and actual execution hardness rather than assuming the generator produced the intended difficulty.

This controlled family tests whether a method learns structure beyond global selectivity. Existing work already studies filter–geometry relationships and hardness, so neither the relationship nor the generator alone is the claimed contribution. [^5][^7]

### Data splits

Partition data access into:

- **Development stream:** Used to acquire shape models and synthesize code.
- **Validation set:** Used for candidate comparison, feedback, and learning curves.
- **Calibration set:** Used only to set the declared conservativeness parameter.
- **Final test set:** Used once after all representations, prompts, thresholds, and analyses are frozen.

Group near-duplicate queries where necessary to prevent leakage. The primary test uses unseen query vectors and unseen query–filter combinations within each workload. Holding out entire filter values is a distinct harder experiment.

## 11. Quality and structural evaluation

### Retrieval quality

For query `q`, let `S(q)` be all stored items eligible under the filter, `G(q)` the exact nearest `min(k, |S(q)|)` eligible items, and `R(q)` the returned set. For nonempty `S(q)`:

`recall(q) = |R(q) ∩ G(q)| / min(k, |S(q)|)`

Specify deterministic distance-tie handling and filter semantics. Report empty eligible sets separately and verify that every returned item satisfies the filter.

Use top-10 retrieval as the primary setting and predeclare an operating point, initially mean recall of 0.95 unless the pilot justifies a different target. Also report per-query recall, the fraction below a declared threshold, short result sets, and results within structural and hardness strata.

### Structural-model quality

The shape model must be evaluated independently of query latency. Depending on its final representation, report:

- Error in predicting local filter prevalence or search work required.
- Calibration of predicted difficulty or improvement probability.
- Performance by selectivity and alignment regime.
- Stability across development samples and agent runs.
- Complexity, size, lookup cost, and unsupported or invalid claims.
- Transfer to unseen queries and query–filter combinations.

Do not declare the model successful merely because the final policy is fast. A policy can improve for reasons unrelated to its stated structural representation.

## 12. Required baselines and ablations

| Method | What it tests |
|---|---|
| Native stopping rule and calibrated fixed budgets | Whether any adaptive method beats credible engine behavior rather than a weak default |
| Simple hand-written policy | Whether inexpensive engineering explains the gain |
| Global-selectivity or simple-summary model | Whether local structural learning adds information beyond basic statistics |
| Same-feature conventional learner | Whether an ordinary model can map current-query features directly to stopping decisions |
| Conventional learner with the same shape representation | Whether any benefit comes from the representation rather than agent reasoning |
| E2E or the closest faithful adaptive-termination method | Comparison with established learned stopping using early search observations [^8] |
| Direct synthesis agent without persistent shape memory | Whether the explicit structural-acquisition stage adds value |
| Agent with bounded shape memory | Proposed complete method |
| Conventional search over the same policy language | Whether synthesis outperforms ordinary search within the same representation |
| Oracle structural summaries, diagnostic only | Upper bound on the possible value of the selected structural information |

All applicable methods receive equal raw information or equal derived summaries, the same labeled-query budgets, comparable calibration, and declared hyperparameter or agent-call budgets.

The minimum mechanism ablation is:

```text
same agent + same raw evidence + same policy language
without explicit shape memory
versus
with explicit bounded shape memory
```

If this ablation shows no benefit, the project cannot claim that explicit structural acquisition is the mechanism behind any improvement.

## 13. Measurements and accounting

Report five categories of outcomes.

### Structural acquisition

- Held-out prediction errors and calibration.
- Number of supported structural distinctions found.
- Shape-model size, complexity, and evaluation cost.
- Stability across repeated runs and evidence samples.

### Query execution

- Mean, median, and p95 wall-clock latency.
- Distance computations or node expansions.
- Feature-maintenance, shape-lookup, and policy-evaluation overhead.

### Retrieval quality

- Mean recall and query-level recall distribution.
- Fraction of queries below the declared target.
- Results within selectivity, alignment, and hardness groups.
- Short result sets, invalid-policy fallbacks, and base-search failures.

### Adaptation cost

- Distinct passive and labeled queries.
- Exact-ground-truth and trajectory-generation cost.
- Agent calls, tokens, time, and monetary cost.
- Conventional training and hyperparameter-search cost.
- Calibration evidence.

### Generalization and amortization

- Performance on unseen queries and query–filter combinations.
- Separate results for every dataset and harder transfer condition.
- Break-even query count: additional adaptation cost divided by average deployed savings, using consistent units.

Fewer distance computations do not by themselves establish lower latency or total cost.

## 14. Semester scope

### Required commitment

| Component | Required scope |
|---|---|
| Engine | One instrumentable HNSW implementation |
| Search semantics | Fixed construction, traversal, filtering, and maximum exploration budget |
| Predicate language | One categorical single-label membership predicate |
| Query objective | Top-10 filtered retrieval at one primary empirical recall target |
| Learned artifact | One bounded, inspectable shape representation |
| Agent action | Generate a compact continue/stop policy using approved features and shape memory |
| Workloads | One real pilot dataset; target one additional real dataset plus one controlled family |
| Adaptation | Ordered offline or batch development, not an LLM call per deployed query |
| Transfer | Unseen queries and query–filter combinations within each workload |

### Explicitly excluded from the required result

- Changing HNSW expansion order or candidate handling.
- Synthesizing a new traversal algorithm.
- Index construction or physical-design optimization.
- Multiple database engines.
- SQL plan optimization or graph-query rewriting.
- Mixed predicate languages.
- Continuous production adaptation or distribution-drift recovery.
- Automatic discovery of new runtime features or arbitrary probes.

These exclusions preserve the ability to replay trajectories, calibrate recall, compare methods on shared evidence, and attribute gains to structural acquisition.

### Stretch goal

Only after the required end-to-end experiment works, allow the shape model to select among a tiny predeclared menu of two or three initial search budgets or strategies. Each strategy must have complete logged or re-executed evidence and its own fair baselines. Failure to complete the stretch goal does not weaken the core result.

### Thesis extensions

Longer-term work may study active acquisition of informative executions, online drift adaptation, traversal control, index or access-path selection, automatic physical design, graph structural-invariant discovery, guarded query rewriting, and transfer across engines. These extensions test whether the acquired shape model can support broader decisions; they are not bundled into the semester implementation.

## 15. Milestones and decision gates

| Weeks | Work and concrete output | Decision gate |
|---|---|---|
| 1–2 | Recheck closest literature and artifacts; select engine and pilot dataset; specify trace and evidence interfaces | Proceed only if instrumentation and a credible adaptive-stopping baseline fit the semester |
| 3–4 | Implement exact ground truth, trajectory capture, replay validation, native/fixed/hand-written baselines | Confirm that the base traversal reaches target quality and that stopping opportunities vary meaningfully across queries |
| 5–6 | Measure structural regimes; define and freeze bounded shape representation; implement simple structural predictors | Confirm that selected summaries predict held-out behavior beyond global selectivity; simplify or reconsider the representation if not |
| 7–8 | Implement agent shape acquisition, direct-synthesis ablation, and conventional same-information learners | Determine whether the explicit shape stage adds a measurable signal under controlled budgets |
| 9–10 | Add policy synthesis, structured feedback, calibration, and end-to-end deployed execution | Confirm that structural prediction translates into latency–recall value rather than only descriptive accuracy |
| 11–12 | Run controlled structural family and second real dataset if feasible; freeze protocol and final artifacts | Assess repeatability and identify where structural knowledge helps or fails |
| 13–14 | Execute final test once; complete ablations, cost analysis, artifact packaging, and paper-style report | State only the claim supported by held-out results and decide whether broader query actions are justified |

If instrumentation consumes the first month, reduce workload breadth before changing the action space. If simple statistics capture nearly all structural variation, do not make the shape model more elaborate merely to create room for the agent. If a conventional learner matches the agent, analyze the result as evidence about the limits of agent-based acquisition.

## 16. Main risks and mitigations

### Risk: “Data shape” remains vague

**Mitigation:** Define a bounded representation, concrete prediction targets, evidence provenance, and independent held-out evaluation before the main agent comparison.

### Risk: The agent merely restates supplied features

**Mitigation:** Compare against global summaries, direct current-query models, and conventional models with the same shape representation. Test whether the learned artifact supports predictions not directly provided in its input.

### Risk: The shape model memorizes queries

**Mitigation:** Exclude identifiers and vector-specific lookup tables, bound model size, group related queries across splits, and test unseen query–filter combinations.

### Risk: Better stopping comes from lower recall

**Mitigation:** Calibrate all methods to the same prespecified empirical target, report the entire recall distribution, and measure failures within declared groups.

### Risk: The base search cannot reach the target

**Mitigation:** Establish maximum-budget reachability during the pilot and report base-search failures separately.

### Risk: The agent appears better only because it receives more evidence or search time

**Mitigation:** Enforce shared information, labeled-query, computation, and adaptation budgets. Preserve complete ledgers.

### Risk: Learning during the final query stream causes leakage

**Mitigation:** Use cumulative development batches and validation learning curves, then freeze everything before the final test.

### Risk: The project becomes a general autonomous optimizer

**Mitigation:** Keep continue/stop as the only required control action. Place routing, traversal, indexing, rewriting, and online drift in explicitly gated extensions.

## 17. Expected contribution and acceptable outcomes

The semester should produce:

1. An instrumented filtered-ANN harness with exact ground truth and replay validation.
2. A documented controlled workload family for filter–geometry structure.
3. A bounded, inspectable shape-model representation.
4. Agent-generated shape models and stopping policies at multiple evidence budgets.
5. Strong same-information baselines and mechanism ablations.
6. A held-out evaluation of structural prediction, query performance, adaptation cost, and transfer.

The strongest positive result would show that explicit agent-acquired shape memory predicts unseen query behavior and produces stopping policies that meet the recall target with less execution work or less labeled adaptation evidence than strong alternatives.

Several negative results would still be scientifically informative:

- Structural summaries predict hardness but do not improve stopping.
- Shape memory helps, but a conventional model acquires it just as efficiently.
- Current-query features make persistent workload knowledge unnecessary.
- The chosen structural regimes have little effect under a well-tuned base engine.
- Agent costs exceed any plausible amortized execution savings.

The report must distinguish these outcomes rather than treating any generated policy as evidence for the central hypothesis.

## 18. Proposal-ready abstract

Filtered approximate nearest-neighbor search combines vector similarity with metadata predicates, and its cost depends not only on filter selectivity but also on how qualifying items are distributed around query neighborhoods. This project asks whether an offline language-model agent can acquire a compact, reusable model of such workload-relevant data shape from a bounded stream of query executions and use it to improve future query control. We propose a two-stage method in which an agent first constructs an inspectable shape model from passive search traces and a limited number of exact labeled executions, then synthesizes a small stopping policy conditioned on that model. The deployed policy executes without language-model calls and controls only whether a fixed HNSW traversal should continue or stop. This restricted action space permits trajectory replay, independent recall calibration, and controlled comparisons against native stopping, hand-written rules, existing adaptive termination, conventional learners, direct policy synthesis, and policy search under equal information and adaptation budgets. Evaluation will separately measure the shape model's ability to predict held-out query behavior and its downstream effect on latency, recall, overhead, evidence cost, and transfer across real and controlled filter–geometry regimes. The goal is to determine whether explicit agent-acquired structural knowledge provides value beyond current-query signals and ordinary learning, while establishing a feasible foundation for later work on broader query-planning and physical-design decisions.

## 19. Initial reading order

Read the tree-substructure work and semantic query-optimization reference to anchor the structural motivation. Then read HNSW for the fixed search model, the filtered-vector-search and filter–geometry studies for the meaning of data shape, E2E for the closest adaptive-stopping method, and Bespoke-Card for agentic synthesis under structured feedback. Inspect released benchmark and engine artifacts before fixing implementation details.

For each close system, record: information available to the optimizer; persistent learned representation; legal actions; feedback; adaptation cost; correctness or recall objective; workload split; and whether structural acquisition is evaluated separately from downstream performance.

## Sources

[^1]: Daniel Aarao Reis Arturi, Christoph Köhnen, George Fletcher, Bettina Kemme, and Stefanie Scherzinger. [Seeing the Trees for the Forest: Leveraging Tree-Shaped Substructures in Property Graphs](https://arxiv.org/abs/2603.12476). Preprint, March 12, 2026.

[^2]: Authors' artifact. [Trees in Graphs: Benchmarking Tree Queries in Property Graphs](https://github.com/sdbs-uni-p/trees-in-graphs). Repository, 2026; inspected September 8, 2026.

[^3]: Pongtawat Chippimolchai, Kiyoshi Akama, and Vilas Wuwongse. [Semantic Query Optimization: Correctness and Control](https://www.fujipress.jp/jaciii/jc/jacii001000030270/). *Journal of Advanced Computational Intelligence and Intelligent Informatics* 10(3), 2006.

[^4]: Yu. A. Malkov and D. A. Yashunin. [Efficient and Robust Approximate Nearest Neighbor Search Using Hierarchical Navigable Small World Graphs](https://arxiv.org/abs/1603.09320). Initial preprint, 2016; subsequently published in IEEE TPAMI.

[^5]: Abylay Amanbayev, Brian Tsan, Tri Dang, and Florin Rusu. [Filtered Approximate Nearest Neighbor Search in Vector Databases: System Design and Performance Analysis](https://arxiv.org/abs/2602.11443). Preprint, February 11, 2026. [Benchmark artifact](https://github.com/aabylay/ANN-benchmark-HQ).

[^6]: Patrick Iff, Paul Bruegger, Marcin Chrapek, Maciej Besta, and Torsten Hoefler. [Benchmarking Filtered Approximate Nearest Neighbor Search Algorithms on Transformer-based Embedding Vectors](https://arxiv.org/abs/2507.21989). Preprint first posted July 29, 2025; updated April 1, 2026.

[^7]: Mintaek Lim, Dogeun Kim, Minwoo Kim, and Jaeyoung Do. [Revisiting Filtered ANN Benchmarks: A Hardness-Controlled Benchmark Generator for Realistic Evaluation](https://arxiv.org/abs/2606.14193). June 2026; the record states acceptance in PVLDB volume 19, issue 10, and presentation at VLDB 2026.

[^8]: Wenxuan Xia, Mingyu Yang, Wentao Li, and Wei Wang. [E2E: Efficient Filtered AKNN Search via Adaptive Termination](https://arxiv.org/abs/2602.06721v2). KDD 2026; updated May 28, 2026. [Repository linked by the paper](https://github.com/gegeji/E2E). Artifact execution remains to be verified.

[^9]: Johannes Wehrstein, Anton Winter, Timo Eckmann, and Carsten Binnig. [Bespoke-Card: Why Tune When You Can Generate? Synthesizing Workload-Specific Cardinality Estimators](https://arxiv.org/abs/2606.09361v2). Updated July 13, 2026; the record states acceptance at AIDB@VLDB 2026.

[^10]: Qianqian Xiong and Mengxuan Zhang. [Query-aware Routing for Filtered Approximate Nearest Neighbors Search](https://arxiv.org/abs/2606.19898). Preprint, June 18, 2026.
