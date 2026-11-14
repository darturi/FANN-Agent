# Agent-Synthesized Stopping Policies for Filtered ANN Search

This project investigates whether an offline language-model agent can synthesize inexpensive, workload-specific stopping policies for filtered approximate nearest neighbor (ANN) search from a small budget of measured executions. The deployed policy decides when an existing search algorithm has explored enough; the language model runs only during policy development. The intended contribution is a method for acquiring useful policies with limited evidence, supported by a benchmark and harness that measure recall, execution cost, adaptation cost, and generalization together.

The scope is one researcher over approximately fourteen weeks. This brief assesses literature available on September 8, 2026. It proposes experiments rather than reporting completed results. The novelty argument is provisional: adaptive ANN stopping and agent-generated database components already exist, so publication would require a demonstrated advantage beyond combining those ideas.

## Research question and working hypothesis

> Can an offline agent synthesize a compact stopping policy for filtered ANN search that reaches a specified empirical recall target on unseen queries using fewer labeled training executions than strong conventional learning and policy-search methods?

The working hypothesis is that structured feedback about premature stopping and unnecessary continuation can help an agent identify useful combinations of search-progress signals with relatively little training evidence. A successful result would show a better trade-off between adaptation cost and subsequent query performance, rather than merely beating an untuned default.

Three questions make that hypothesis testable:

1. **Evidence efficiency:** At a fixed training-execution budget, does synthesis produce a better latency–recall trade-off than ordinary learning or search over the same policy space?
2. **Mechanism:** Does structured feedback about failures improve synthesis beyond a generic agent receiving aggregate scores and the same underlying traces?
3. **Transfer:** Do the resulting policies remain effective on unseen queries within a workload, including difficult combinations of filter selectivity and vector geometry?

Tree annotations are background experience and impose no implementation requirement. Here, knowledge of data shape means measurable relationships between the query neighborhood, filter membership, and the progress of search.

## The problem in concrete terms

ANN means **approximate nearest neighbor**, not artificial neural network. A vector represents an item such as a document or image. A filtered ANN query might request “the ten closest document embeddings among documents whose category is biology.” Exact search would identify the nearest qualifying vectors under the chosen distance metric. Approximate search aims to recover most of those neighbors at lower cost.

HNSW is a graph-based index that searches through links between vectors. The proposed project fixes one HNSW implementation and changes only its stopping decision. HNSW's graph is a search index; this does not require a property-graph database or a tree-shaped dataset. [^1]

Filter selectivity is the fraction of database items satisfying a predicate. That fraction alone may not describe the difficulty of a query: qualifying vectors might be concentrated near the query or sparse in its neighborhood. Existing work already studies these relationships and their consequences for filtered search. The proposal uses that understanding as motivation, not as a new discovery. [^2]

For example, two predicates might each match 1% of the database. During one query, the search could rapidly encounter close qualifying results; during another, equally close candidates might mostly fail the filter. A useful stopping policy must distinguish these cases without knowing the true nearest neighbors at execution time.

## Novelty and closest prior work

| Prior work | What it already establishes | Implication for this project |
|---|---|---|
| **E2E: Efficient Filtered AKNN Search via Adaptive Termination**, KDD 2026 | Uses early search observations, including filter-valid ratios and distance statistics, with a lightweight learned model to estimate search cost and control termination. | This is the central comparator. Adaptive stopping, filter-aware features, and inexpensive online inference are already established. [^3] |
| **Bespoke-Card**, accepted at AIDB@VLDB 2026 | Agents synthesize workload-specific cardinality-estimation code using validation and structured error feedback. | Executable database specialization and iterative failure feedback are not novel by themselves. [^4] |
| **Query-aware Routing for Filtered Approximate Nearest Neighbors Search**, 2026 preprint | Uses learned predictions to select among filtered ANN methods and configurations. | Query-dependent ANN strategy selection is occupied territory. This proposal fixes the underlying search and studies stopping-policy acquisition. [^5] |
| **LLM-Guided ANN Index Optimization for Human-Object Interaction Retrieval**, 2026 preprint | Studies LLM-guided ANN optimization in a retrieval application. | “An LLM improves ANN” is too broad a novelty claim. Retrieval-task quality must also be distinguished from exact-neighbor recall. [^6] |
| **Revisiting Filtered ANN Benchmarks**, accepted for PVLDB 19(10), 2026 | Introduces an execution-related hardness measure and a generator controlling workload difficulty. | A benchmark varying selectivity or correlation alone is insufficient novelty. Reuse or compare with existing hardness methodology where feasible. [^7] |

The candidate contribution is **budgeted synthesis of stopping policies, with trajectory-level failure feedback and independent recall calibration**, evaluated against equally informed alternatives. Each ingredient has precedents; the paper must establish why the method is useful for this particular systems problem.

A defensible eventual claim would be: “Under explicitly measured adaptation budgets, our method produces compact policies that reach the target recall with less training evidence or lower total adaptation cost than competing approaches, and the advantage persists on held-out workloads.” This sentence is a hypothesis to test, not a promised result.

Simply replacing a learned model with an LLM-generated decision tree would likely be too incremental. Likewise, a result against only a conservative fixed budget would leave open whether a small conventional model could achieve the same gain. The initial literature review should follow the early-termination references in E2E, including LAET and DARTH, and search for newer work on program synthesis for search control before finalizing the contribution. [^3]

## Semester scope

| Component | Initial commitment |
|---|---|
| Engine | One instrumentable HNSW implementation, preferably building on a relevant research artifact |
| Search semantics | Fixed graph construction, distance metric, traversal, filter handling, and maximum exploration budget |
| Agent action | Generate a compact continue/stop function from an approved feature interface |
| Filters | One categorical predicate type; use single-label membership, which reduces to equality for single-valued categories |
| Query objective | Top-10 retrieval as the primary setting; illustrative mean recall target of 0.95 |
| Workloads | One dataset for the pilot; aim for two real datasets plus one controlled synthetic family for the final study |
| Deployment | Ordinary executable policy; no per-query language-model call |
| Primary transfer test | Unseen query vectors and query–filter combinations within each workload |

The exact engine and datasets are week-one decisions based on artifact availability and instrumentation effort. The updated E2E paper links a public repository, making it a sensible first inspection target; buildability and compatibility have not been verified for this brief. [^3] PostgreSQL/pgvector integration is a later extension unless suitable search-loop hooks are inexpensive to obtain.

Exclude index construction optimization, traversal synthesis, multiple engines, SQL-plan optimization, mixed predicate languages, and distribution-drift adaptation from the required semester result. Each adds a separate source of complexity. A second recall target or value of k is a sensitivity experiment if the core comparison succeeds.

## Proposed method and harness

### 1. Record comparable search trajectories

Instrument the engine at fixed checkpoints. Each record should contain accumulated distance computations, inexpensive search-state features, and the current qualifying result set. Collect sufficiently long reference trajectories to study earlier stopping, subject to a fixed maximum budget and clearly documented native termination behavior.

Compute exact filtered nearest neighbors separately for labeled queries. This produces recall labels for trajectory prefixes and identifies where additional exploration helped. A long approximate run must not be treated as exact ground truth.

Trajectory replay is valid only for **stopping along the same underlying traversal**. Changing beam width, expansion order, graph structure, or candidate handling can change the trajectory and requires a new execution. Verify that replayed decisions reproduce actual engine results before using replay for policy development. Final latency measurements must execute the deployed policy in the engine, including its feature and decision overhead.

The pilot must also establish that the chosen base traversal can reach the target quality. A stopping policy cannot recover a true neighbor that the base traversal never visits. Record such failures separately from failures caused by premature stopping.

### 2. Define a small policy language

Allow bounded arithmetic, comparisons, and short conditional expressions over a fixed feature interface. Candidate inputs include exploration count, number of qualifying results, observed filter-valid fraction, normalized distance summaries, and recent changes in the best qualifying results. Make any global metadata statistic available to every comparator and account for its construction cost.

These features are starting points, not proposed inventions. Freeze the feature interface after the pilot so policy synthesis can be compared fairly with conventional learners.

Set a code-size or expression-depth limit. Exclude raw query identifiers, stored answer sets, and vector-specific lookup tables. Define behavior for missing values, empty queues, and numerical errors. An invalid policy decision should fall back to continuing the base search, and such fallbacks should be counted.

### 3. Synthesize using structured development feedback

The agent receives the search semantics, approved policy language, training traces, and an evaluation tool. It proposes a policy, evaluates it on development evidence, and revises it within a fixed budget.

Feedback distinguishes two failures:

- **Premature stopping:** The policy stops at a prefix with inadequate recall, although further exploration on the same trajectory would improve it. Show the state at stopping and the subsequent improvement.
- **Unnecessary continuation:** The policy continues well beyond a prefix already achieving the target. Show which signals remained misleading and the avoidable work on that trajectory.

Ground-truth-derived explanations are available only during development and must be charged to the labeled-evidence budget. A diagnostic “earliest prefix reaching the target” is an oracle for that particular trajectory, not an achievable online feature or a globally optimal search algorithm.

Retain candidate policies and choose among them using development data. Compare structured feedback with aggregate-score feedback under the same evidence and agent-call budgets. This isolates the value of the proposed feedback design.

### 4. Freeze and calibrate

After code selection, freeze the policy. Use a separate calibration split to set a conservativeness parameter, such as the threshold of a stopping score. Design the parameter family so a more conservative setting permits stopping only at a subset of the checkpoints allowed by a less conservative setting. With fixed traversal and a best-k result heap, this should delay stopping; verify that property in the implementation.

Choose the calibration objective and threshold-selection procedure in advance. Do not revise code after inspecting calibration outcomes; a further development round requires an explicitly accounted new split or protocol. Use the same quality-selection procedure for competing methods where applicable.

Calibration supports an empirical quality objective. It does not establish a recall guarantee for every future query or under arbitrary distribution changes.

### 5. Deploy and measure

Run the frozen, calibrated policy on untouched test queries. Measure actual query latency, quality, and policy overhead. Preserve the exact generated artifact, prompts, model identifier, seeds, budget ledger, and engine revision so the synthesis procedure and resulting policy can be inspected independently.

## Benchmark and experimental controls

### Workload construction

Start with public embeddings paired with meaningful metadata. Existing filtered-ANN benchmark work provides candidate resources, including transformer-based document embeddings with attributes. Dataset suitability, licensing, scale, and predicate support need to be checked during the pilot. A documented subset is acceptable if hardware constraints require one. [^8]

Use a controlled synthetic family to vary global filter selectivity and the spatial distribution of qualifying points independently. Hold label counts fixed when testing the effect of alignment. Include cases where qualifying items cluster near query neighborhoods, are approximately independent of geometry, or are sparse near them. Treat generated labels as synthetic even when the underlying vectors are real.

Also measure actual execution difficulty. Selectivity and geometric alignment are explanatory variables, not universally reliable substitutes for hardness. Existing hardness-controlled benchmarking provides a relevant comparison and possible generator to reuse. [^7]

### Splits and leakage prevention

Partition queries into development, calibration, and final test sets before experimentation. Group related queries where necessary so near-duplicate vectors do not leak across splits. Test unseen vectors and query–filter combinations first. Holding out entire filter values is a distinct, harder transfer experiment and should be reported separately.

Use two evaluation modes only if time permits:

- **Required: shared evidence.** All methods receive identical labeled query traces at each training-budget level. This isolates how well each method uses evidence.
- **Optional: active acquisition.** Methods choose which additional queries to execute from an unlabeled pool. Charge every label-producing inspection, including queries used to discover counterexamples. Compare with random and uncertainty-based acquisition before attributing benefits to the agent.

Do not claim active data-selection benefits from experiments using a fully labeled pool that was freely inspected. Multiple checkpoints from one query are correlated observations, not independent training queries.

### Quality definition

For query q, let S(q) be its eligible items, G(q) the exact nearest min(k, |S(q)|) items, and R(q) the returned set. For nonempty S(q), define:

`recall(q) = |R(q) ∩ G(q)| / min(k, |S(q)|)`

Specify deterministic distance-tie handling and filter semantics. Report empty eligible sets separately rather than dividing by zero. Check that every returned item satisfies the filter.

A primary target of mean recall 0.95 is an experimental operating point. It does not mean every query achieves 0.95; with k=10 and ten eligible items, per-query recall changes in increments of 0.1. Report the distribution of recall, the fraction below the chosen per-query threshold, and results within predeclared selectivity and hardness groups. Fix any additional group-level acceptance criteria before final testing.

## Baselines, ablations, and measurements

| Comparator | Purpose |
|---|---|
| Calibrated fixed exploration budgets and the native stopping rule | Establish the benefit of adapting to individual queries and avoid relying on a deliberately weak default |
| A simple hand-written stopping rule | Test whether inexpensive engineering explains the gains |
| A same-feature gradient-boosted tree model | Test evidence efficiency against a strong conventional learner, using the same query traces and calibration resources |
| E2E | Compare with the closest published method; reproduce its design faithfully where feasible and explicitly label any engine or feature adaptation |
| Conventional search over the same bounded policy language | Separate the benefits of the policy representation from those of language-model synthesis |
| Generic synthesis agent with the same tools and evidence | Isolate the contribution of structured trajectory feedback |

Use a small, declared hyperparameter-search budget for conventional learners and count it. Do not assume a published method requires its largest reported training set: run learning curves over the same available evidence budgets. The same-feature learner and a faithful E2E comparison serve different purposes and should not be silently conflated.

The minimum ablation removes structured failure feedback while preserving evidence access. If time permits, remove filter-aware features and vary policy complexity to test whether gains depend on workload structure or merely on a larger hypothesis space.

Report:

- **Execution:** mean, median, and p95 wall-clock latency; distance computations; policy evaluation and feature-maintenance overhead.
- **Quality:** mean and per-group recall, query-level recall distribution, short result sets, and invalid-policy fallbacks.
- **Adaptation:** distinct labeled queries, trajectory-generation work, exact-ground-truth cost, calibration labels, training/search time, agent tokens, and monetary cost.
- **Stability:** repeated synthesis runs and training-query samples, with paired comparisons and uncertainty intervals over appropriate independent units.
- **Generalization:** within-workload held-out performance, separate results for each dataset, and any explicitly designated harder transfer setting.

Use geometrically spaced evidence budgets selected after measuring pilot costs. Count all development and calibration evidence; allocating most labels to calibration while claiming very little training data would misrepresent adaptation cost. Report the label budget and total computational budget separately, since query lengths and exact-search costs differ.

For repeated-query use, estimate an amortization point: extra adaptation cost divided by average per-query execution savings, using consistent time or monetary units. If savings are absent, there is no positive break-even point. Fewer distance computations alone do not establish lower latency or lower total cost.

## Milestones and decision gates

| Weeks | Work and concrete output | Decision |
|---|---|---|
| 1–2 | Read closest methods; inspect artifacts; select engine and one dataset; document scope and comparison protocol | Proceed only if search-loop instrumentation and a credible closest baseline fit the semester |
| 3–4 | Implement exact ground truth, trace capture, replay validation, and fixed/hand-written baselines; measure earliest useful stopping prefixes | Establish that useful early-stopping opportunities remain under a base traversal that reaches the quality target |
| 5–6 | Implement conventional learner and shared-evidence learning curves; finalize features, budget levels, and quality criteria | Continue synthesis if there is a plausible gap in evidence efficiency or adaptation cost; avoid tuning against final test data |
| 7–9 | Implement bounded synthesis and structured feedback; compare with generic synthesis and conventional policy search | Determine whether the proposed mechanism contributes beyond the representation and available labels |
| 10–11 | Freeze protocol; evaluate second dataset and controlled workload family; calibrate and run held-out comparisons | Assess repeatability and identify the conditions where policies help or fail |
| 12–14 | Complete key ablations, actual runtime measurements, cost analysis, artifact packaging, and paper-style write-up | Formulate the claim supported by results and decide whether a larger project is justified |

If instrumentation consumes the first month, narrow the engine integration before expanding the benchmark. If a small conventional learner matches the agent across budgets, do not move to weaker baselines. Analyze why synthesis fails to add value and decide with the supervisor whether a rigorous comparative study is a worthwhile semester endpoint. Such a result can guide later work, but publication is not assured.

## Expected contribution and extension path

The semester should produce a reproducible harness, a documented workload suite, generated policy artifacts, and a comparative study of policy acquisition under limited evidence. The strongest paper would connect an identifiable synthesis mechanism to measurable savings, explain where those savings arise, and show that recall failures and adaptation costs do not erase them.

Potential thesis extensions include active acquisition of informative executions, adaptation after workload drift, additional predicate types, transfer between search implementations, or policies that change traversal rather than only stop it. These should follow evidence from the fixed-traversal study; they are not required to make its initial question meaningful.

### Proposal-ready abstract

Filtered approximate nearest neighbor search combines vector similarity with metadata predicates. Its execution cost varies across queries, motivating policies that stop search once sufficient result quality has been reached. Existing learned termination methods demonstrate the value of search-state signals, while recent agentic systems synthesize workload-specific database components. This project asks whether offline agent synthesis can acquire effective filtered-ANN stopping policies from limited execution evidence. We propose a bounded policy language, a development loop using trajectory-level feedback about premature stopping and unnecessary continuation, and a separate calibration stage for empirical recall control. Generated policies execute without language-model calls during query processing. A benchmark and harness will compare synthesis against fixed policies, conventional learners, existing adaptive termination, and policy-search baselines under explicit evidence and computational budgets. Evaluation will measure latency, recall distributions, adaptation cost, and transfer to unseen queries across real and controlled workloads. The goal is to determine whether agent synthesis offers a reproducible advantage in the cost of acquiring useful search policies, and to characterize the conditions under which that advantage holds.

## Sources and initial reading order

Read HNSW for the search model, E2E for the closest technical overlap, and Bespoke-Card for agentic synthesis. Then read the two benchmark studies to finalize workloads and difficulty controls. Publication status below reflects the linked records checked for this brief.

[^1]: Yu. A. Malkov and D. A. Yashunin. [Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs](https://arxiv.org/abs/1603.09320). Initial preprint, 2016; subsequently published in IEEE TPAMI. Background on the fixed search algorithm.

[^2]: Abylay Amanbayev, Brian Tsan, Tri Dang, and Florin Rusu. [Filtered Approximate Nearest Neighbor Search in Vector Databases: System Design and Performance Analysis](https://arxiv.org/abs/2602.11443). 2026 preprint. Relevant to filter–geometry relationships and system-dependent behavior.

[^3]: Wenxuan Xia, Mingyu Yang, Wentao Li, and Wei Wang. [E2E: Efficient Filtered AKNN Search via Adaptive Termination](https://arxiv.org/abs/2602.06721v2). KDD 2026; updated May 28, 2026. The earlier preprint title was *Filtered Approximate Nearest Neighbor Search Cost Estimation*. [Full text](https://arxiv.org/html/2602.06721v2); [repository linked by the paper](https://github.com/gegeji/E2E). Artifact execution remains to be verified.

[^4]: Johannes Wehrstein, Anton Winter, Timo Eckmann, and Carsten Binnig. [Bespoke-Card: Why Tune When You Can Generate? Synthesizing Workload-Specific Cardinality Estimators](https://arxiv.org/abs/2606.09361v2). Updated July 13, 2026; the record states acceptance at AIDB@VLDB 2026, a workshop rather than the main PVLDB research track.

[^5]: Qianqian Xiong and Mengxuan Zhang. [Query-aware Routing for Filtered Approximate Nearest Neighbors Search](https://arxiv.org/abs/2606.19898). June 2026 preprint.

[^6]: Shahrzad Esmat, Chaunte W. Lacewell, Sameh Gobriel, Nilesh Jain, and Ali Jannesari. [LLM-Guided ANN Index Optimization for Human-Object Interaction Retrieval](https://arxiv.org/abs/2606.05489). June 2026 preprint.

[^7]: Mintaek Lim, Dogeun Kim, Minwoo Kim, and Jaeyoung Do. [Revisiting Filtered ANN Benchmarks: A Hardness-Controlled Benchmark Generator for Realistic Evaluation](https://arxiv.org/abs/2606.14193). June 2026; the record states acceptance in PVLDB volume 19, issue 10, and presentation at VLDB 2026.

[^8]: Patrick Iff, Paul Bruegger, Marcin Chrapek, David Kochergin, Maciej Besta, and Torsten Hoefler. [Benchmarking Filtered Approximate Nearest Neighbor Search Algorithms on Transformer-based Embedding Vectors](https://arxiv.org/abs/2507.21989v3). Initial preprint, July 2025; updated April 1, 2026. Candidate benchmark and dataset reference; final dataset selection requires artifact inspection.
