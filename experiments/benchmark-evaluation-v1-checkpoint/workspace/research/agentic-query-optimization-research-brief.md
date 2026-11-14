# Agentic Query Optimization Using Knowledge of Data Structure

The strongest initial project is a controlled study of whether an LLM agent can turn measured properties of a dataset into useful query execution decisions under a limited experimentation budget. The broad proposition that agents can improve database query execution already has close academic and industry precedents. A defensible contribution therefore needs to establish what information the agent uses, what it contributes beyond ordinary search or learned routing, and whether the resulting improvements survive evaluation on unseen queries and data distributions.

This brief assesses literature available on September 8, 2026, and proposes a scope for one researcher over approximately fourteen weeks. Publication status is identified where verified; a linked preprint is not assumed to be peer reviewed. The proposed methods, schedule, and thresholds below are research design recommendations, not experimental findings. No systems have been reproduced or benchmarked for this brief, and the literature assessment does not establish an exhaustive absence of competing work.

## 1. Research positioning

The connection to tree annotations is strong, but it spans several different optimization problems. *Seeing the Trees for the Forest* demonstrates how structural indexes can accelerate path queries over tree-shaped substructures in property graphs and argues for managing these structures throughout the graph query lifecycle. Its public artifact provides a concrete starting point for a graph-oriented follow-up. [^1][^2]

An agent might contribute at four increasingly ambitious levels:

| Level | What the agent changes | Example | Appropriate role in this project |
|---|---|---|---|
| Plan selection | Choices supported by an existing engine and existing access paths | Join order; exact versus approximate vector scan | Main semester experiment |
| Query rewriting | An equivalent expression of the requested computation | Replacing a traversal with a predicate over existing annotations | Possible graph alternative |
| Physical design | Persistent structures that enable additional execution strategies | Tree labels, indexes, materialized views, partitions | Later extension, with construction and maintenance costs |
| Algorithm or engine synthesis | Executable implementations and data representations | Generating a specialized query kernel | Thesis-scale extension |

This distinction affects the research claim. If annotations are absent, a planner may have no way to express the faster strategy. Supplying knowledge of a tree cannot by itself create an indexed ancestor test. Conversely, allowing the agent to build annotations changes the available plan space and introduces preprocessing, storage, update, and correctness obligations. Comparing that agent only with a default optimizer would conflate several sources of improvement.

The intellectual lineage also predates LLMs. Semantic query optimization uses constraints to justify more efficient equivalent computations. Learned optimizers such as Bao steer existing optimizers from execution feedback, while BayesQO explicitly spends offline time searching for better plans for recurring queries. The proposal should position the agent as a possible mechanism for acquiring and applying knowledge within this lineage. [^3][^4][^5]

The principal research question should be:

> Under equal information access and resource budgets, can an agent use verified properties of data structure to discover execution policies that outperform strong conventional alternatives on unseen queries?

“Data structure” should be operationalized rather than left as an intuitive description. It can mean topological properties, statistical dependencies, or vector geometry. These are related sources of optimization information, but they require different measurements and permit different transformations.

## 2. Closest prior work and its implications

### Agentic specialization and tuning

**Bespoke OLAP — Wehrstein et al., VLDB 2026.** This is a particularly close match to the described 2026 paper: an autonomous pipeline synthesizes workload-specific database engines through performance feedback and validation. It is listed as a regular research paper in the conference program and has a PVLDB proceedings PDF. It establishes substantial overlap with a proposal about generating a custom database for each workload; it does not establish the narrower hypothesis about the value of controlled structural information. Confirmation is still needed that this is the particular paper originally discussed. [^6]

**GenDB — Lao and Trummer, 2026.** The research prototype generates query processing code specialized to data, workloads, and hardware; a separate demonstration paper describes its use for repeated query templates. It is an important reference if the project later permits generated execution code. Its discussion of differential validation and future stronger correctness checks is also relevant: successful execution on a benchmark instance is not a universal semantic guarantee. [^7][^8]

**GPTuner — Lao et al., PVLDB 2024.** The likely intended spelling is GPTuner. It extracts knowledge from database manuals to guide Bayesian optimization of configuration knobs. It is an appropriate precedent for combining language-derived domain knowledge with empirical optimization, but its principal action space is system configuration rather than per-query execution plans. [^9]

### Query optimization and rewriting

**Databricks / UPenn join-order agent — April 2026 industry research report.** The agent submits legal join orders, executes them, and observes runtimes and subplan cardinalities. On a scaled version of JOB, the report gives a 1.288× geometric-mean speedup and a 41% reduction in P90 query latency; the headline comparison uses fifteen tested join orders per query, while a longer exploration discussion uses fifty iterations. These are reported prototype results, not independently reproduced results or universal expectations. The report explicitly raises the possibility of giving agents cardinality probes and tools for testing assumptions about the data. This is direct overlap with both the proposed loop and part of its motivation. [^10]

**OBELISK — Pan et al., PVLDB 19(7), 2026.** This is an especially important academic comparator. It combines Bayesian optimization, feedback-aware language-model reasoning, and evaluation admission controls to search cost-scaling knobs that steer TiDB's optimizer. It already addresses iterative reasoning, empirical feedback, and economical evaluation. A new project cannot claim that combination alone as its contribution. Its engine-specific controls also mean that a PostgreSQL adaptation would need to be labeled an adaptation, rather than an exact reproduction. [^11]

**BayesQO — Tao et al., SIGMOD 2025.** It searches execution plans offline using a learned representation and Bayesian optimization. It supplies a strong alternative explanation for agent gains: a system might improve because it receives additional executions and time. Its evaluation also studies drift and transfer, so neither feature is automatically novel. For a relational-plan project, it is an important baseline or methodological comparator. [^5]

**LLMOpt — Yao et al., 2025 preprint.** It uses LLMs for candidate-plan generation and selection. It establishes overlap with asking a language model to produce or rank plans, even without a richer tool-using agent. [^12]

**LLM-R² — Li et al., 2024; R-Bot — Sun et al., PVLDB 2025; QUITE — Song et al., preprint first posted in 2025.** These cover LLM-guided rewrite-rule selection, retrieved rewrite evidence, and feedback-driven agentic rewriting beyond predefined rules. QUITE's repository explicitly distinguishes equality of results on a benchmark instance from semantic equivalence and documents a known divergence. A graph rewrite project should account for the same distinction. [^13][^14][^15][^16]

### ANN tuning, planning, and benchmarks

| Work | Existing contribution | Consequence for a new proposal |
|---|---|---|
| VDTuner, Yang et al., 2024 | Multi-objective Bayesian optimization of vector-system configurations, balancing speed and recall | ANN autotuning is an established baseline category. [^17] |
| LLM-Guided ANN Index Optimization, Esmat et al., June 2026 preprint | History-conditioned agent optimizing a coupled retrieval pipeline, with ANN parameters, reranking choices, and metadata prefiltering | “Use an LLM agent to tune ANN” is already occupied, including some filtering decisions. [^18] |
| ACORN, Patel et al., SIGMOD 2024 | A predicate-agnostic index and traversal approach for hybrid vector/structured search | Data/filter interactions already motivate specialized algorithms. [^19] |
| PathFinder, Wu and Tang, November 2025 preprint | Cost-based optimization over attribute-specific ANN indexes for conjunctions and disjunctions | Optimizer-based filtered ANN plan selection is also prior work. [^20] |
| Amanbayev et al., February 2026 preprint | MoReVec dataset, Global-Local Selectivity metric, and evaluation of FAISS, Milvus, and pgvector | Measuring filter–vector correlation and demonstrating pgvector planning weaknesses are not sufficient new contributions. [^21] |
| Query-aware Routing, Xiong and Zhang, June 2026 preprint | Lightweight models predict candidate-method recall and support query-dependent routing; final features include selectivity, intrinsic dimensionality, and predicate type | A new routing method must face a conventional learned router with comparable information. [^22] |
| Iff et al., July 2025; Shi et al., September 2025 preprints | Filtered ANN datasets, taxonomies, and systematic benchmark comparisons | Extend existing benchmark infrastructure instead of assuming the area lacks benchmarks. [^23][^24] |

The ANN-agent preprint deserves scrutiny rather than uncritical adoption. It reports larger gains on its strongly coupled task and near-convergence on simpler controls. Its broad claim about conventional optimizers being unable to navigate coupled parameters should be treated as a claim about the tested setup, not as evidence of a general impossibility. The proposal needs a controlled comparison against suitably configured optimizers. [^18]

Across this literature, the most defensible prospective contribution is the **combination of controlled data interventions, measured information acquisition costs, and agent/non-agent comparisons**. This remains a candidate research gap. Before submission, the closest papers' experiments and released artifacts should be checked against the final protocol, and citation searches should be refreshed.

## 3. What ANN means here

ANN means **approximate nearest neighbor**, not artificial neural network. A record has a vector of numbers, often an embedding produced by another model. Given a query vector, nearest-neighbor search finds records with the smallest distance under a specified metric. Exact search obtains the true nearest neighbors; approximate search may miss some in exchange for lower cost. The embedding model and distance function define the retrieval task and should remain fixed in this project. [^25]

For example: find the ten documents most similar to a query, among documents whose category is “databases.” That combines a vector-distance ordering with an ordinary metadata predicate. There are several execution strategies: identify eligible records and compute exact distances; search a larger vector candidate set and apply the filter; or incorporate filtering into index traversal. Their behavior depends on how many records qualify and where those records lie relative to the query. [^26]

Two index families are sufficient background for a pilot. **HNSW** organizes vectors into a layered proximity graph and navigates toward nearby records; its graph is an index structure, not a property graph expressing application relationships. **IVF** groups vectors into regions and searches selected regions. Construction settings determine properties of the index, whereas search-time settings determine how much of it a query explores. Faiss provides runtime parameter autotuning, which is another useful conventional baseline if that library becomes the experimental backend. [^27][^28]

The essential quality metric is recall relative to exact ground truth. Let F(q) be the eligible set for query q, let G(q) be its exact nearest min(k, |F(q)|) neighbors, and let A(q) be the returned records. For nonempty F(q):

    recall@k(q) = |A(q) ∩ G(q)| / min(k, |F(q)|)

A query with no eligible records should return an empty answer and be scored separately, rather than dividing by zero. All returned records must satisfy the filter. Define tie handling in advance, using a distance-tolerant or otherwise consistent ground-truth convention. Returning k records does not establish high recall, and ordering the returned records exactly does not establish that they are the true nearest k.

A reasonable primary objective is latency subject to a prespecified recall requirement, such as mean recall@10 of at least 0.95 **within each declared evaluation stratum**. Also report the distribution of per-query recall and the fraction below the target. This is an empirical quality criterion on held-out queries, not a guarantee for every future query. Varying the target should be a later sensitivity test; lowering recall cannot count as a speed improvement at the original target.

The structural analogy to trees is the existence of exploitable regularity. The difference is that a verified tree invariant can justify an exact transformation, whereas observed vector clustering usually predicts performance or accuracy statistically. Uncertain geometry can guide a choice without changing the requested filter or similarity metric.

## 4. Choosing a system

SQL is a query language, PostgreSQL is a database engine, property graphs are a data model, and ANN is a retrieval problem. These choices overlap: PostgreSQL with pgvector provides SQL access to ANN, and graph data can also be represented in relational tables.

| Starting point | Main advantage | Main difficulty | Assessment for one semester |
|---|---|---|---|
| PostgreSQL relational plans | Mature instrumentation and a familiar exact-query objective | Very crowded prior work; plan enforcement and fair optimizer baselines need care | Strong fallback if ANN setup fails |
| A graph engine from the tree-annotation artifact | Best continuity with prior expertise and existing examples | Changes to annotations mix plan selection with physical design; engine controls may be limited | Strong alternative if structural rewrite discovery is the real objective |
| PostgreSQL + pgvector | Combines SQL familiarity with ANN interest and observable execution plans | Recall-aware evaluation and faithful access-path control | Recommended feasibility pilot |
| Standalone Faiss / specialized vector engine | Direct control of ANN algorithms and parameters | May become algorithm/configuration tuning rather than database plan optimization | Appropriate if index research becomes the central question |

PostgreSQL exposes explicit join-order controls, and pg_hint_plan adds optimizer hints, but these are mechanisms to verify experimentally rather than assumptions that arbitrary plans can be forced. PostgreSQL also supports multivariate statistics; any relational baseline should include fresh statistics and an enhanced-statistics condition, since ordinary correlation information is not exclusive to agents. [^29][^30][^31]

pgvector supports exact search and approximate HNSW/IVFFlat indexes. Its documentation describes filtering after approximate index scanning and iterative scans that continue searching until enough results are found or limits are reached. Therefore, an ANN pilot must compare against a sensibly configured iterative-search baseline, not just a weak default that returns too few results. It also must verify the actual execution plan for every proposed action. [^32]

**Recommendation:** spend two weeks validating a PostgreSQL + pgvector problem instance. Commit only if several data/query regimes show reproducible differences among feasible strategies at the same recall target, and those differences are not already captured almost completely by a simple selectivity rule. If this fails, move to one relational or graph task by week three. Do not run all three as full experiments during the semester.

This is an engineering and research-scoping judgment, not a claim that pgvector is the strongest vector database. Conclusions from it must remain bounded to the measured engine, versions, workloads, and action space. VBASE is useful background on the broader problem of integrating vector similarity with relational query execution. [^33]

## 5. Proposed benchmark

The benchmark should define **optimization episodes**, not merely a list of queries. An episode contains a dataset snapshot, a development workload, legal observations and actions, a budget, and a withheld evaluation workload. An optimizer uses the development workload to choose a reusable policy. The evaluator then freezes that policy and tests it on queries the optimizer has not executed.

For the first ANN version, use one controlled synthetic family and one real embedding dataset with metadata. MoReVec and the public filtered-ANN artifacts are candidates to inspect for access, licensing, scale, and reproducibility; their suitability has not yet been tested. Use existing embeddings rather than adding embedding-model training to the project. [^21][^23][^24]

### Controlled structural interventions

Construct paired datasets or workloads with similar simple summaries but different relationships that may affect execution:

| Domain | Hold approximately fixed | Change deliberately | What the comparison investigates |
|---|---|---|---|
| Filtered ANN | Vectors, total rows, label frequencies, query templates | Assign qualifying labels inside, outside, or independently of vector clusters | Whether local filter relationships matter beyond global selectivity |
| Relational joins | Schema, row counts, selected column marginals | Join-key overlap, conditional skew, cross-table dependencies | Whether additional dependency information improves plan selection |
| Tree substructures | Node counts and query families | Depth, fanout, balance; later introduce violating cross-edges | Whether structural information or annotations remain useful and valid |

For ANN, fixing the vectors while changing labels separates filter relationships from geometry changes. Generate label assignments from a declared cluster-based mechanism, with query vectors sampled independently; avoid constructing every case around the eventual test query. Global selectivity is the fraction that qualifies, so a smaller fraction means a more restrictive filter. Local qualifying frequency measures how prevalent eligible records are near a query. The GLS literature already studies their relationship; use or adapt that definition explicitly rather than claiming a new metric. [^21]

A practical first design uses three selectivity levels and three alignment regimes at one scale, with at least three independent data seeds. Add one real dataset and two scales only after the measurement pipeline works. Exact sizes should follow memory and timing measurements; the initial aim is interpretable variation, not a large leaderboard. Report regimes where the default already performs well and where no alternative helps.

The pilot should measure whether interventions actually change the best feasible strategy. This is not guaranteed: correlation might change recall while leaving raw latency nearly unchanged, which can still change the effort required to meet a recall target. If the portfolio has no useful variation, changing the prompt is unlikely to rescue the experiment.

### Information conditions

Separate four kinds of access:

1. **Standard context:** schema, available indexes, documented controls, engine statistics, and an initial plan.
2. **Additional structural summaries:** measured correlations, selected density summaries, or verified graph properties, with extraction costs recorded.
3. **Active inspection:** an optimizer can request bounded samples, selectivity estimates, or other declared probes and pays for them.
4. **Evaluator-only diagnostic information:** expensive exact properties or exhaustive candidate results used to estimate attainable performance. These are never exposed in the practical condition.

An agent receiving execution feedback is already receiving some information about the data. The first condition is consequently a “standard-context” or “runtime-feedback” condition, not a truly data-blind agent. Audit actual tool inputs and outputs to prevent forbidden summaries from appearing indirectly.

Use the same feature values for non-LLM comparators. Test whether numerical summaries suffice before attributing value to natural-language descriptions. Include a small diagnostic with uninformative names or misleading stale summaries; avoid treating altered semantic names as the only contamination defense. Newly generated data, withheld templates, and explicit splits matter more.

### Correctness and evaluation separation

Maintain separate development, validation, and final test query sets. Tune prompts and thresholds only on development/validation data, freeze them before the final run, and split by query family or distribution where feasible. Shared knowledge of the dataset is legitimate in an instance-specialization task; access to the final queries' answers or measured candidate rankings is not. A zero-shot transfer experiment should also freeze the policy before it sees the new dataset; an adaptation experiment can reveal a new development set under a fresh budget. Report these separately.

For SQL/graph variants, prefer a constrained family of transformations with explicit preconditions. Result comparison must preserve duplicates, NULL behavior, aggregates, and required ordering. Tests on one snapshot support instance correctness, not equivalence under all future states. A discovered tree property used to eliminate traversal must be verified in its declared scope and invalidated or maintained after changes.

## 6. Minimal agent harness

Use one agent with structured tool calls. Multiple specialist agents, model fine-tuning, and unrestricted code generation are not required to test the initial hypothesis. The benchmark specifies the task and scoring independently; the harness is one interchangeable policy for solving it.

| Component | Responsibility | Minimal implementation |
|---|---|---|
| Episode specification | Fix inputs, legal actions, observations, and budgets | Versioned JSON/YAML manifest |
| Data generator/loader | Build reproducible snapshots and splits | Seeded generators and existing dataset importers |
| Database adapter | Execute approved actions and inspect actual plans | PostgreSQL client with plan capture and timeouts |
| Profiler | Produce declared features and charge their costs | Small set of bounded sampling/statistics routines |
| Agent loop | Choose a probe, experiment, or final policy | Structured model responses and bounded history |
| Validator/evaluator | Check plan execution, filter validity, recall, and latency | Exact ground truth plus independent timed executions |
| Policy recorder | Save a reusable decision artifact | Small decision table or bounded decision-tree representation |
| Experiment ledger | Make costs and failures reproducible | Append-only records of actions, results, versions, and seeds |

The workflow is:

    dataset + development queries + budget
                      ↓
             inspect available evidence
                      ↓
        select a probe or candidate policy
                      ↓
         validate → execute → record feedback
                      ↺
                 freeze policy
                      ↓
       independent evaluation on held-out queries

Use a fixed index inventory for the main experiment: for example, a metadata B-tree and a global HNSW index on the same data snapshot. Candidate actions can select metadata filtering followed by exact distance ranking, or HNSW search with several approved effort/iteration settings. Keep ordinary planner execution as an action and baseline. The adapter should canonicalize candidates and inspect their plans so that nominally different actions mapping to the same physical plan are not mistaken for exploration.

Do not assume pgvector exposes every inline-filtering algorithm from the literature. The first portfolio should contain only methods that can actually be executed and verified in the selected engine. IVFFlat, partial indexes, partitions, and index construction tuning are extensions after the basic experiment. Enforcing an exact path may require a vetted query template or scoped planner settings; inspect the resulting plan and exact result behavior rather than trusting the requested setting.

Start with roughly 8–16 genuinely distinct configurations or strategies. An agent can experiment on selected development query batches and emit a bounded rule that maps inexpensive query features to a candidate. The same representation should be available to a non-LLM learner. Charge feature extraction at deployment: a “cheap router” is not cheap if computing its inputs requires a near-complete search.

Keep exact test neighbors and full performance tables inside the evaluator. Development-set recall can be returned by the experiment tool. Record a brief explicit hypothesis and evidence reference when useful, but evaluate behavior through interventions and ablations; self-reported explanations are not proof of what caused a choice.

## 7. Baselines, measurements, and falsifiable hypotheses

The primary comparison is against the strongest affordable alternative, with engine defaults retained as context.

| Baseline / ablation | Question answered |
|---|---|
| Default optimizer with fixed inventory | Is there an observable engine-level opportunity? |
| Recommended iterative-search configuration, validated for recall | Do gains persist beyond an obvious configuration repair? |
| Best static configuration selected on development data | Is adaptation useful at all? |
| Selectivity rule and small learned router using the same features | Does the LLM add value beyond ordinary feature-based decisions? |
| Random search and a conventional sequential optimizer | Are gains merely the result of more experiments? |
| Agent with standard context versus additional summaries | What is the incremental value of structural information? |
| Agent with fixed summaries versus active probes | Does selecting what to inspect justify its cost? |
| Single-response LLM versus iterative agent, if affordable | Does interaction add value? |
| Best feasible candidate in the measured portfolio | How much attainable headroom remains? |

The last item is a diagnostic reference, not a deployable oracle and not the globally optimal execution plan. Its exhaustive evaluation cost should be reported separately and its results hidden from all practical methods. In a very small portfolio, exhaustive search may itself be an excellent practical baseline. If so, that is evidence against adding an agent for this particular problem.

For ANN, VDTuner and the recent query-aware router are relevant comparator designs, but implementing their entire original environments may exceed the semester. First compare conventional search and learned routing within exactly the same portfolio. Clearly label adaptations and do not claim to have beaten the published systems based on a simplified implementation. If relational optimization becomes the main track, prioritize Bao-style steering and an offline-search comparator inspired by BayesQO, with an explicit account of differences from the original systems. [^4][^5][^17][^22]

Three primary hypotheses are sufficient:

**H1 — Information helps.** At a fixed experimental budget, providing measured structural features improves the agent's held-out feasible performance relative to standard context. Test the same information increment on non-LLM methods to determine whether it benefits the agent specifically or all optimizers.

**H2 — Acquisition is worthwhile.** An agent that chooses a limited number of structural probes reaches a target quality/latency level at lower total adaptation cost than a fixed profiling pipeline or conventional search. It may fail because the summaries are too expensive or straightforward to select.

**H3 — Policies generalize.** A policy learned on development queries retains an advantage on held-out queries and a declared distribution shift. Separate frozen transfer from adaptation with new measurements. Failure would limit the result to specialization of the measured instance or workload.

Equalize both **information** and **resources**. Report candidate-evaluation counts, actual database time, elapsed adaptation time, feature/probe costs, model tokens, monetary model cost, and CPU/GPU resources where applicable. Use at least one wall-clock budget comparison as well as an evaluation-count comparison. Timed-out plans consume their elapsed budget and remain failures or censored observations, rather than disappearing from the dataset.

Final metrics should include latency among recall-feasible policies, fraction of strata meeting recall, per-query recall distribution, P50/P95 latency, regression frequency, worst observed slowdown, and improvement as a function of adaptation cost. Use consistent concurrency and hardware. Randomize candidate order, separate profiling from final timing, specify cache conditions, and rerun frozen winners independently to reduce selection of lucky measurements. Several data seeds and repeated agent runs are needed; use intervals clustered at the dataset/episode level rather than treating correlated query repetitions as independent experiments.

For recurring workloads, account for amortization:

    total_baseline(N) = N × mean_baseline_execution_cost
    total_agent(N) = adaptation_cost
                     + N × (mean_policy_execution_cost + routing_cost)

The break-even repetition count is adaptation_cost divided by the positive per-execution saving. Use consistent units, reporting time and money separately unless an explicit conversion model is given. Construction and maintenance costs enter adaptation or lifecycle cost when new indexes or annotations are permitted. A faster plan that will not repay its discovery cost before workload change can be an interesting search result without being a useful deployment policy.

## 8. Semester plan and decision gates

The following is a planning estimate for one researcher; it should be adjusted to the actual academic calendar and hardware access.

| Weeks | Work | Concrete deliverable / decision |
|---|---|---|
| 1–2 | Read the closest papers; learn filtered ANN; install a pinned PostgreSQL/pgvector environment; compare a few exact/ANN paths | Short feasibility memo with measured recall/latency and a confirmed legal action space |
| 3–4 | Freeze the problem; implement controlled data variants, query splits, ground truth, and timing | Benchmark v0 plus a scoped proposal draft |
| 5–6 | Implement default, static, selectivity, random-search, and small learned baselines | Evidence of remaining headroom and a decision on whether an agent experiment is justified |
| 7–8 | Add the single-agent harness and fixed-information conditions | Complete optimization episodes with cost accounting |
| 9–10 | Run primary comparisons and ablations; add active probing only if stable | Results for H1 and, if feasible, H2 |
| 11–12 | Evaluate one real dataset and one held-out shift; verify failures and frozen winners | Generalization and limitations analysis |
| 13–14 | Analyze results, package artifacts, and write | Research report, reproducible benchmark release, and thesis-extension decision |

**Gate at week two:** can the adapter reliably exercise distinct strategies, and does there appear to be a meaningful quality-constrained performance difference? If not, change the engine/action scope or select the relational/graph alternative immediately.

**Gate at week six:** does a simple rule or inexpensive exhaustive sweep already capture nearly all headroom? If yes, either write a careful negative result or move to a justified richer task while preserving time for evaluation. Do not expand the search space merely to manufacture an advantage for the agent.

**Minimum successful semester outcome:** a reproducible benchmark with controlled structural variation, strong baselines, one agent evaluated under equal budgets, and an evidence-based answer about where the agent helps or fails. A universally superior optimizer, several database backends, or a new ANN index is not required. Publication potential depends on the strength and breadth of the resulting evidence, not on the existence of a harness alone.

For a pilot, plan around a stable CPU machine with sufficient RAM and SSD space; use existing embeddings and hosted model inference if available. As an illustration, one million 768-dimensional float32 vectors alone occupy about 3.1 GB before index, metadata, and database overhead. A 32–64 GB machine is a plausible planning target for moderate experiments, not a verified requirement. Begin smaller and measure memory. Dedicated GPUs are optional for this scope, while reproducible access to otherwise idle hardware is valuable.

## 9. Draft proposal language

**Working title:** *Evaluating Agentic Query Optimization Under Controlled Data-Structure Variation*

**Draft abstract.** Database execution decisions depend on properties of the underlying data that may be only partially represented in optimizer statistics. Recent systems demonstrate that language-model agents can specialize database implementations, rewrite queries, and search execution plans. However, improvements from these systems can reflect additional experimentation, richer observations, or a broader action space, making the contribution of data-structure knowledge difficult to isolate. This project proposes a benchmark and agent harness for measuring that contribution under controlled conditions. The initial study will target filtered nearest-neighbor queries in PostgreSQL with pgvector, comparing execution policies over a fixed set of access paths. Paired datasets will vary the relationship between metadata predicates and vector neighborhoods while controlling simpler statistics. An agent and conventional alternatives will receive matched information and experimentation budgets, and their policies will be evaluated on held-out queries at a fixed empirical recall requirement. The study will measure execution performance, information acquisition costs, adaptation efficiency, and sensitivity to distribution change. Its intended contribution is a reproducible account of when agentic reasoning provides useful optimization beyond existing statistical and search methods.

The scope should remain conditional on the pilot. If the graph direction is selected instead, replace filtered-neighbor queries with a small family of tree queries and fix an inventory of precomputed annotations. First evaluate whether the agent can select valid structural rewrites on unseen tree shapes. Letting it discover or construct new annotations would be a separate subsequent experiment.

A thesis extension could address automatic feature/probe discovery, guarded synthesis of new access paths, maintenance under updates, or transfer across engines. Each expands a specific limitation of the semester study. The most important discussion with the supervisor is whether the desired long-term result is an optimizer that **chooses known strategies** or a system that **invents new specializations**; the benchmark should eventually distinguish those capabilities.

## 10. Reading order

Start with the Databricks report and OBELISK to establish the closest agentic planning overlap. Then read Bespoke OLAP and GPTuner to separate engine synthesis from system tuning. For ANN, read the filtered-vector-search tutorial, the relevant pgvector documentation, and the MoReVec/GLS study before attempting to reproduce a tuning system. Follow with the query-aware routing paper and ANN-agent preprint, focusing on features, information access, evaluation costs, and split definitions. BayesQO and the JOB paper supply useful background on offline search and optimizer evaluation. [^5][^6][^9][^10][^11][^18][^21][^22][^26][^32][^34]

For each close paper, record: optimization unit; data and query access; legal actions; feedback; adaptation/training cost; correctness or recall criterion; workload split; published artifact; and which proposed hypothesis it already tests. This comparison should accompany the eventual formal proposal and be updated after the feasibility experiments.

## Sources

[^1]: Daniel Aarao Reis Arturi, Christoph Köhnen, George Fletcher, Bettina Kemme, and Stefanie Scherzinger. [Seeing the Trees for the Forest: Leveraging Tree-Shaped Substructures in Property Graphs](https://arxiv.org/abs/2603.12476). Preprint, March 12, 2026.

[^2]: Authors' artifact. [Trees in Graphs: Benchmarking Tree Queries in Property Graphs](https://github.com/sdbs-uni-p/trees-in-graphs). Repository, 2026; inspected September 8, 2026.

[^3]: Pongtawat Chippimolchai, Kiyoshi Akama, and Vilas Wuwongse. [Semantic Query Optimization: Correctness and Control](https://www.fujipress.jp/jaciii/jc/jacii001000030270/). Journal of Advanced Computational Intelligence and Intelligent Informatics 10(3), 2006.

[^4]: Ryan Marcus et al. [Bao: Making Learned Query Optimization Practical](https://people.csail.mit.edu/tatbul/publications/bao_sigmod21.pdf). SIGMOD 2021.

[^5]: Jeffrey Tao et al. [Learned Offline Query Planning via Bayesian Optimization](https://www.speculative.tech/publications/sigmod25-bayesqo.pdf). SIGMOD / Proceedings of the ACM on Management of Data 3(3), Article 179, June 2025.

[^6]: Johannes Wehrstein, Timo Eckmann, Matthias Jasny, and Carsten Binnig. [Bespoke OLAP: Synthesizing Workload-Specific One-size-fits-one Database Engines](https://www.vldb.org/pvldb/vol19/p3759-wehrstein.pdf). PVLDB volume 19, 2026. [Revised preprint](https://arxiv.org/abs/2603.02001), July 23, 2026; [VLDB conference program](https://vldb.org/2026/program.html).

[^7]: Jiale Lao and Immanuel Trummer. [GenDB: The Next Generation of Query Processing — Synthesized, Not Engineered](https://arxiv.org/abs/2603.02081). Preprint, March 2, 2026. [Author implementation](https://github.com/SolidLao/GenDB).

[^8]: Jiale Lao and Immanuel Trummer. [Demonstrating GenDB: Instance-Optimized and Customized Query Processing Code Generation via LLM Agents](https://arxiv.org/abs/2607.20630). July 22, 2026; separate demonstration paper.

[^9]: Jiale Lao et al. [GPTuner: A Manual-Reading Database Tuning System via GPT-Guided Bayesian Optimization](https://vldb.org/pvldb/vol17/p1939-tang.pdf). PVLDB 17(8):1939–1952, 2024. [Author implementation](https://github.com/SolidLao/GPTuner).

[^10]: Eric Liang, Ryan Marcus, Sid Taneja, and Yuhao Zhang. [Are LLM agents good at join order optimization?](https://www.databricks.com/blog/are-llm-agents-good-join-order-optimization). Databricks research blog, April 22, 2026. Related author analysis: [How Do LLM Agents Think Through SQL Join Orders?](https://ucbskyadrs.github.io/blog/databricks/), April 23, 2026.

[^11]: Zhicheng Pan et al. [OBELISK: Efficient Offline Query Planning with Bayesian Optimization-Informed Language Model Reasoning](https://www.vldb.org/pvldb/vol19/p1674-pan.pdf). PVLDB 19(7):1674–1687, 2026. DOI: 10.14778/3801059.3801077. Artifact linked by paper: [obelisk-offlineqo](https://github.com/DaSECandyLab/obelisk-offlineqo).

[^12]: Zhiming Yao et al. [A Query Optimization Method Utilizing Large Language Models](https://arxiv.org/abs/2503.06902). LLMOpt preprint, March 2025.

[^13]: Zhaodonghui Li, Haitao Yuan, Huiming Wang, Gao Cong, and Lidong Bing. [LLM-R2: A Large Language Model Enhanced Rule-based Rewrite System for Boosting Query Efficiency](https://arxiv.org/abs/2404.12872). 2024. [Author repository identifying VLDB 2024 work](https://github.com/DAMO-NLP-SG/LLM-R2).

[^14]: Zhaoyan Sun et al. [R-Bot: An LLM-based Query Rewrite System](https://www.vldb.org/pvldb/vol18/p5031-li.pdf). PVLDB 18(12):5031–5044, 2025.

[^15]: Yuyang Song et al. [QUITE: A Query Rewrite System Beyond Rules with LLM Agents](https://arxiv.org/abs/2506.07675). Preprint first posted June 9, 2025; no final venue assumed here.

[^16]: QUITE authors. [Implementation and equivalence definition](https://github.com/Yuyang-Song/QUITE). Repository inspected September 8, 2026.

[^17]: Tiannuo Yang et al. [VDTuner: Automated Performance Tuning for Vector Data Management Systems](https://arxiv.org/abs/2404.10413). 2024. [Author implementation](https://github.com/tiannuo-yang/VDTuner).

[^18]: Shahrzad Esmat, Chaunté W. Lacewell, Sameh Gobriel, Nilesh Jain, and Ali Jannesari. [LLM-Guided ANN Index Optimization for Human-Object Interaction Retrieval](https://arxiv.org/abs/2606.05489). Preprint, June 3, 2026; full-text sections 3–6 used for scope and limitations.

[^19]: Liana Patel, Peter Kraft, Carlos Guestrin, and Matei Zaharia. [ACORN: Performant and Predicate-Agnostic Search Over Vector Embeddings and Structured Data](https://arxiv.org/abs/2403.04871). SIGMOD 2024; DOI: 10.1145/3654923.

[^20]: Tianming Wu and Dixin Tang. [PathFinder: Efficiently Supporting Conjunctions and Disjunctions for Filtered Approximate Nearest Neighbor Search](https://arxiv.org/abs/2511.00995). Preprint, November 2, 2025.

[^21]: Abylay Amanbayev, Brian Tsan, Tri Dang, and Florin Rusu. [Filtered Approximate Nearest Neighbor Search in Vector Databases: System Design and Performance Analysis](https://arxiv.org/abs/2602.11443). Preprint, February 11, 2026. [Benchmark artifact](https://github.com/aabylay/ANN-benchmark-HQ).

[^22]: Qianqian Xiong and Mengxuan Zhang. [Query-aware Routing for Filtered Approximate Nearest Neighbors Search](https://arxiv.org/abs/2606.19898). Preprint, June 18, 2026; full-text sections 3–4 used for feature and routing design.

[^23]: Patrick Iff, Paul Bruegger, Marcin Chrapek, Maciej Besta, and Torsten Hoefler. [Benchmarking Filtered Approximate Nearest Neighbor Search Algorithms on Transformer-based Embedding Vectors](https://arxiv.org/abs/2507.21989). Preprint first posted July 29, 2025.

[^24]: Jiayang Shi, Yuzheng Cai, and Weiguo Zheng. [Filtered Approximate Nearest Neighbor Search: A Unified Benchmark and Systematic Experimental Study](https://arxiv.org/abs/2509.07789). Preprint first posted September 9, 2025.

[^25]: Martin Aumüller, Erik Bernhardsson, and Alexander Faithfull. [ANN-Benchmarks: A Benchmarking Tool for Approximate Nearest Neighbor Algorithms](https://arxiv.org/abs/1807.05614). 2018 full-version preprint of the SISAP 2017 paper.

[^26]: Yannis Papakonstantinou, Anastasia Ailamaki, Yannis Chronis, Helena Caminal, and Fatma Ozcan. [Filtered Vector Search: State-of-the-art and Research Opportunities](https://research.google/pubs/filtered-vector-search-state-of-the-art-and-research-opportunities/). Tutorial, 2025.

[^27]: Yu. A. Malkov and D. A. Yashunin. [Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs](https://arxiv.org/abs/1603.09320). Preprint first posted 2016.

[^28]: Faiss maintainers. [Index IO, cloning and hyper parameter tuning](https://github.com/facebookresearch/faiss/wiki/Index-IO%2C-cloning-and-hyper-parameter-tuning). Official documentation; inspected September 8, 2026.

[^29]: PostgreSQL Global Development Group. [Controlling the Planner with Explicit JOIN Clauses](https://www.postgresql.org/docs/current/explicit-joins.html). PostgreSQL documentation; inspected September 8, 2026.

[^30]: pg_hint_plan maintainers. [pg_hint_plan](https://github.com/ossc-db/pg_hint_plan). Official repository; inspected September 8, 2026.

[^31]: PostgreSQL Global Development Group. [Statistics Used by the Planner](https://www.postgresql.org/docs/current/planner-stats.html). PostgreSQL documentation; inspected September 8, 2026.

[^32]: pgvector maintainers. [pgvector documentation](https://github.com/pgvector/pgvector). Sections on indexing, filtering, and iterative index scans; inspected September 8, 2026. Pin an actual release for experiments rather than relying on a moving branch.

[^33]: Qianxi Zhang et al. [VBASE: Unifying Online Vector Similarity Search and Relational Queries via Relaxed Monotonicity](https://www.usenix.org/conference/osdi23/presentation/zhang-qianxi). OSDI 2023.

[^34]: Viktor Leis et al. [How Good Are Query Optimizers, Really?](https://vldb.org/pvldb/vol9/p204-leis.pdf). PVLDB 9(3):204–215, 2015. Useful retrospective: [Still Asking: How Good Are Query Optimizers, Really?](https://www.vldb.org/pvldb/vol18/p5531-viktor.pdf), 2025.
