# First-Year Guide to the Filtered-ANN Research Brief

This document explains the specialized language used in [*Agent-Synthesized Stopping Policies for Filtered ANN Search*](/Users/danielarturi/Developer/JinyangLiWork/research/filtered-ann-stopping-policy-research-brief.md:1). It assumes the reader has completed, or is taking, a first programming course and may know basic arrays, functions, graphs, and databases. It does not assume prior knowledge of database research, machine learning, vector search, or experimental statistics.

The entries follow the order of the brief. Each group links to the place where the terms first appear. When one definition uses another specialized term, that term appears as its own entry in this guide.

## 1. Opening description

Corresponding passage: [opening paragraphs of the brief](/Users/danielarturi/Developer/JinyangLiWork/research/filtered-ann-stopping-policy-research-brief.md:3).

### Machine learning, model, and training

**Machine learning** is a way of building software in which a program learns patterns from examples instead of receiving every decision rule directly from a programmer.

A **model** is the learned function that maps inputs to predictions or generated output. **Training** is the process of adjusting that model using examples so its output better matches a goal. Training the large language model itself is outside this project; the project uses an already trained model inside an agent.

### Agent, language model, LLM, and offline agent

An **agent** is a program that repeatedly chooses an action, observes the result, and uses that result to choose its next action. In this project, its actions might include writing a candidate stopping rule, running an evaluation, reading which queries failed, and revising the rule.

A **language model** is a machine-learning model trained to predict and generate text. A modern language model can also generate program code and reason about structured feedback. **LLM** means **large language model**, where “large” refers to the model's substantial number of learned numerical settings and large training collection. The proposed agent uses an LLM as the component that proposes and revises policies.

A **neural network** is a machine-learning model made from layers of simple numerical operations whose adjustable values are learned during training. Modern LLMs are very large neural networks.

An **offline agent** does its work before the search system serves real queries. “Offline” does not mean disconnected from the internet. It means outside the time-sensitive path that answers a user's query. The agent may take seconds or minutes while developing a policy; the finished policy should make each live stopping decision quickly without calling the language model.

### Synthesis and an agent-synthesized policy

**Synthesis** means automatically constructing a program or rule that satisfies a goal. It is more specific than asking a model for advice. The output here is executable logic, such as:

```text
if qualifying_results >= 10
   and recent_distance_improvement < 0.01
   and visited_nodes > 200:
       stop
else:
       continue
```

An **agent-synthesized policy** is such a rule produced through the agent's propose–test–revise loop. The research question is whether that loop can create a good rule using relatively few measured examples.

### Workload and workload-specific

A **workload** is the collection or distribution of tasks a system is expected to handle. For a database, it includes the kinds of queries, their frequency, the data they access, and sometimes the hardware on which they run.

**Workload-specific** means designed for that particular collection of queries rather than for every possible use. A policy trained mainly on biology-category searches may exploit patterns that do not exist in a shopping-image workload. Specialization can improve performance, but it can also reduce the ability to handle changed or unfamiliar workloads.

### Stopping policy

A **policy** is a rule that maps the current state to an action. A **stopping policy** observes the state of an ongoing search and returns one of two actions: continue searching or stop and return the current results. Stopping too early saves work but may miss good answers. Stopping too late preserves quality but wastes time.

### Measured execution and execution budget

An **execution** is one actual run of a query or program. A **measured execution** records facts about that run, such as elapsed time, number of distance calculations, intermediate results, and final accuracy.

A **budget** is a fixed limit on a resource. A training-execution budget may allow a method to observe only 100 query runs. Budgeting matters because a method that needs one million examples may be impractical even if its final policy is excellent.

An LLM **token** is a small unit of text processed by the model, often a word or part of a word. Token counts are recorded because model services commonly limit or charge for the amount of text processed.

### Deployment and deployed policy

**Deployment** is putting a developed component into the system that handles test or real-world work. The **deployed policy** is the completed continue/stop function used during query execution. In this proposal, deployment does not include a language-model call for every search.

### Benchmark and harness

A **benchmark** is a standardized set of data, tasks, and measurements used to compare systems fairly. It answers questions such as: Which queries will be run? What counts as the correct result? Which costs and quality measures will be reported?

A **harness** is the surrounding software that runs the experiments. It loads data, invokes each method, records measurements, checks results, and produces comparable output. The benchmark is the experimental specification; the harness is the code that carries it out.

### Recall

**Recall** measures how many of the correct answers a search method found. If the exact top ten results are known and an approximate search returns eight of those ten, its recall is 8/10 = 0.8. It may return ten items in total, but only overlap with the exact answer counts toward recall.

### Execution cost, adaptation cost, and overhead

**Execution cost** is the work needed to answer queries after the policy is deployed. It can be measured in time, distance calculations, CPU work, or money.

**Adaptation cost** is the one-time or occasional work used to create a policy for a workload. It includes collecting training executions, computing correct answers, running the agent, and calibrating the result.

**Overhead** is extra work added by a technique itself. A stopping policy might reduce graph search by 2 milliseconds but spend 1 millisecond computing its features. The net saving is therefore only 1 millisecond.

### Generalization

**Generalization** is the ability of a learned or synthesized rule to work on examples it did not see while being developed. Memorizing the training queries is not enough. A useful policy must make good decisions for new query vectors and filter combinations.

### Novelty, contribution, and provisional claim

In research, **novelty** means that the work adds knowledge or a method that is meaningfully different from prior work. A **contribution** is the specific new result a paper offers, such as a new method, benchmark, measurement, or explanation.

**Provisional** means tentative and subject to change. The brief calls its novelty argument provisional because newer or overlooked research may already cover part of the idea, and experiments may fail to show the expected advantage.

## 2. Research question and hypothesis

Corresponding passage: [research question and working hypothesis](/Users/danielarturi/Developer/JinyangLiWork/research/filtered-ann-stopping-policy-research-brief.md:7).

### Hypothesis and testable question

A **hypothesis** is a proposed explanation or prediction that an experiment can support or contradict. Here, the prediction is that structured failure feedback will help an agent produce effective policies with fewer measured examples.

A question is **testable** when its terms can be measured and competing outcomes are possible. “Can AI optimize search?” is vague. “At 500 labeled executions, which method achieves the lowest latency while meeting a recall target on held-out queries?” specifies a comparison that data can answer.

### Compact policy

A **compact policy** is deliberately small, for example a short decision tree or bounded expression. Small policies are fast to run, easier to inspect, and harder to use as hidden storage for memorized answers. Compactness must be defined by a limit such as maximum tree depth, expression count, or code length.

### Empirical recall target

**Empirical** means based on observed experiments. An **empirical recall target** such as 0.95 means the method is tuned to achieve that measured recall on a specified sample. It is not a mathematical promise that every future query will achieve 0.95 recall.

### Labeled training execution

A **label** is the correct answer or target value attached to a training example. For a search trajectory, a label may state the recall at each checkpoint or the first checkpoint that reaches the target. Producing the label requires knowing the exact nearest qualifying neighbors, which can be expensive.

A **labeled training execution** is a recorded query run paired with this correctness information. An unlabeled run has search-state observations but lacks the exact answer needed to judge them.

### Conventional learning and policy search

**Conventional learning** refers here to established machine-learning algorithms, such as gradient-boosted decision trees, trained from numerical features and labeled examples. It provides a strong non-agent comparison.

**Policy search** is any procedure that explores possible policies and scores them. It could systematically list small expressions, use an evolutionary algorithm that repeatedly modifies a population of candidate policies, use Bayesian optimization that builds a probability-based model to choose promising candidates, or use an agent. Comparing multiple search procedures over the same policy language helps determine whether improvement comes from the agent or simply from the available policy choices.

### Structured feedback, aggregate score, and search-progress signal

**Structured feedback** reports detailed, organized information about a failure. For example: “The policy stopped after 220 visits with recall 0.7; recall reached 0.9 after 40 more visits; the local valid-result ratio was falling.” This tells the agent what went wrong and where.

An **aggregate score** combines many outcomes into one or a few numbers, such as mean latency and mean recall. It is easier to process but hides the individual failure cases.

A **search-progress signal** is any value available while the search is running that may indicate whether more work is useful. Examples include the number of visited nodes, the number of valid results found, and whether the best distances have recently improved.

### Evidence efficiency

**Evidence efficiency** asks how much useful performance a method obtains from a given amount of training evidence. Method A is more evidence-efficient than method B if A learns a similarly good policy from 100 labeled query runs while B needs 1,000. This is separate from the final speed of the deployed policy.

### Latency–recall trade-off

**Latency** is the elapsed time between issuing a query and receiving its answer. A **trade-off** occurs when improving one goal tends to hurt another. Searching longer usually raises recall but also raises latency. A latency–recall trade-off describes the set of quality and speed combinations a method can achieve.

A fair comparison either fixes recall and compares latency, or shows a curve across several operating points. Comparing one method at 0.95 recall with another at 0.80 recall would mix speed and quality.

### Policy space

The **policy space** is the set of policies a method is allowed to choose from. If policies may contain at most four `if` conditions over six features, every legal combination belongs to the policy space. Equal policy spaces help isolate the quality of the search method; otherwise, one method might win merely because it was allowed more expressive programs.

### Mechanism

In an experiment, a **mechanism** is the part of a method believed to cause its advantage. The proposed mechanism is structured trajectory-level feedback. Removing that feedback while keeping the agent, data, and tools constant tests whether the feedback is actually responsible.

### Trace and trajectory

A **trace** is a recorded sequence of states or events from one program execution. A **search trajectory** is the ordered path of states created as a search runs: which nodes were visited, what candidates were queued, and how the result set changed.

The two words are nearly interchangeable in the brief. “Trajectory” emphasizes the changing state of the search; “trace” emphasizes the stored record used by the experiment.

### Transfer and unseen query

**Transfer** measures whether a method remains useful outside the exact examples used to create it. An **unseen query** is one excluded from training and calibration. Within-workload transfer tests new queries drawn from a similar source. A harder transfer test might use completely unseen filter values or a changed data distribution.

### Filter selectivity and vector geometry

**Filter selectivity** is the fraction of database items that pass a filter. If 500 of 100,000 documents have category `biology`, the selectivity is 500/100,000 = 0.005, or 0.5%.

**Vector geometry** describes the spatial relationships among vectors: which are close, which form clusters, and where empty or dense regions occur. Two filters with the same selectivity can have different search difficulty because their matching vectors occupy different parts of the vector space.

### Tree annotation, implementation requirement, and data shape

An **annotation** is extra information stored with a data item to make later operations easier. A tree annotation might record each node's position or ancestry. An **implementation requirement** is something the system must actually build or support.

The brief says tree annotations are not an implementation requirement. **Data shape** is used more generally to mean measurable structure in the data, especially how filter membership is distributed around a query in vector space.

### Query neighborhood and filter membership

A query's **neighborhood** is the set of vectors close to its vector according to the distance function. **Filter membership** is whether an item passes the query's metadata condition. Their relationship matters: a rare category that is locally common near a query may be easier to find than its overall frequency suggests.

## 3. The filtered-ANN problem

Corresponding passage: [the problem in concrete terms](/Users/danielarturi/Developer/JinyangLiWork/research/filtered-ann-stopping-policy-research-brief.md:21).

### Vector and embedding

A **vector** is an ordered list of numbers, such as `[0.2, -0.7, 1.1]`. A distance function can compare two vectors. In search systems, a vector often represents the content of an item.

An **embedding** is a vector created by a model so that related items tend to have nearby vectors. A document-embedding model might place two papers about databases close together even if they use different wording. The embedding is a numerical representation, not the original document.

### Nearest neighbor, k-nearest neighbors, ANN, and AKNN

A vector's **nearest neighbor** is the stored vector with the smallest distance from it. The **k-nearest neighbors** are the k closest stored vectors; for `k = 10`, the query asks for ten items.

**Approximate nearest neighbor (ANN)** search returns neighbors that are expected to be close to the query but may miss some of the exact closest items. It avoids the cost of comparing the query with every stored vector. Some papers use **AKNN**, “approximate k-nearest neighbor,” to emphasize that multiple neighbors are returned. In this brief, ANN and AKNN refer to the same general problem family.

### Filtered ANN query and qualifying item

A **filtered ANN query** adds a condition to vector similarity. It asks for close vectors only among items satisfying a rule, such as `category = biology` or `year >= 2024`.

A **qualifying item** is an item that passes that rule. An item can be extremely close in vector space and still be ineligible because it fails the filter.

### Exact search and approximate search

**Exact search** returns the true closest qualifying items according to the specified distance and tie rules. A simple exact method compares the query with every qualifying vector and sorts the results.

**Approximate search** reduces work by exploring only part of the data. It is faster at large scale but can miss a true nearest neighbor. Exact search is used to create ground truth for evaluating the approximate method.

### Distance metric

A **distance metric** is a formula for measuring how far apart two vectors are. Euclidean distance measures straight-line distance. Cosine distance compares direction. The chosen formula defines what “nearest” means, so it must remain fixed during a fair experiment.

### Index and graph-based index

An **index** is an extra data structure that helps locate results without scanning every item. A book's index maps topics to pages; a database index maps search values to records.

A **graph-based index** represents stored vectors as nodes connected by edges, usually linking nearby vectors. Search starts at one or more entry nodes and follows promising edges toward the query. The graph is built for search speed and may not represent relationships from the original application.

### HNSW

**HNSW** stands for **Hierarchical Navigable Small World**. It is a popular graph-based ANN index. “Hierarchical” means it has multiple graph layers. Upper, sparse layers allow large jumps across the dataset; lower, denser layers refine the search near promising vectors. “Small world” refers to graphs in which short paths often connect distant regions.

HNSW search maintains a set of promising candidates and explores their neighbors. Parameters control how widely it searches. More exploration often improves recall at the cost of more time.

### Property-graph database

A **property graph** stores entities as nodes and relationships as edges, with named properties attached to both. A social graph might use person nodes, `FOLLOWS` edges, and properties such as `name` or `date`.

A **property-graph database** is a database designed to store and query this model. HNSW also uses a graph internally, but that does not make it a property-graph database. Its edges exist to navigate vector space rather than to represent application relationships.

### Predicate

A **predicate** is a condition that evaluates to true or false. `category = "biology"` is true for biology documents and false for others. A filter is made from one or more predicates.

### Candidate

A **candidate** is an item the search algorithm is considering as a possible result or as a promising next place to explore. Different implementations use “candidate” for slightly different internal collections, so the project must define it according to the chosen engine.

## 4. Prior work and research positioning

Corresponding passage: [novelty and closest prior work](/Users/danielarturi/Developer/JinyangLiWork/research/filtered-ann-stopping-policy-research-brief.md:31).

### Prior work and comparator

**Prior work** is research completed before the current project. A literature review identifies what is already known and where an unanswered question remains.

A **comparator** is a method against which the proposed method is experimentally compared. The strongest relevant prior method is usually more informative than a basic default.

### Adaptive termination and online inference

**Termination** is the end of an algorithm's execution. **Adaptive termination** uses the state of each individual query to decide when to stop instead of applying the same fixed limit to all queries.

**Inference** is using a trained model to make a prediction. **Online inference** happens while serving a query. “Lightweight online inference” means the prediction is inexpensive enough to make during search without erasing the saved time.

### Feature and filter-aware feature

A **feature** is an input value given to a learned model or policy. The number of explored nodes is one feature; the fraction of explored nodes passing the filter is another.

A **filter-aware feature** directly contains information about the filter or the observed behavior of matching items. A distance-only feature knows how close candidates are but not whether they pass the filter.

### Cardinality estimation

**Cardinality** means the number of items in a set. A database **cardinality estimator** predicts how many rows a query operation will produce. Query optimizers use this prediction to choose among execution plans. Bespoke-Card is related because it synthesizes workload-specific estimator code, although it tackles a different database decision.

### Validation and iterative failure feedback

**Validation** checks a candidate method against data reserved for development decisions. It helps choose among candidate policies without using the final test results.

**Iterative failure feedback** means repeatedly showing a system its mistakes so it can revise its output. “Iterative” indicates a loop rather than a single generation step.

### Query-aware routing

**Routing** selects which of several available methods should handle a request. **Query-aware routing** makes that selection separately for each query using information about the query. It differs from the proposed stopping work: routing selects an algorithm or configuration, while a stopping policy controls when one fixed search should end.

### Configuration

A **configuration** is a collection of settings that control a system's behavior. For HNSW, settings can affect graph construction or search effort. Comparing configurations is different from generating a stopping rule inside a fixed configuration.

### Retrieval application and retrieval quality

**Retrieval** means finding relevant stored items in response to a request. A **retrieval application** could be document search, image search, or the document-finding stage of a question-answering system.

**Retrieval-task quality** is an application-level score, such as whether returned images are useful. It is not necessarily the same as exact-neighbor recall. A system could retrieve semantically useful items while missing some vectors defined as exact nearest neighbors.

**Human–object interaction retrieval**, which appears in the title of one cited paper, searches for examples of a person performing an action with an object, such as a person riding a bicycle. It is the application studied by that paper rather than a required part of this proposal.

### Hardness measure, correlation, and methodology

A **hardness measure** assigns a numerical difficulty value to a query or workload. A useful measure should relate consistently to observed execution cost or quality.

**Correlation** means that two quantities tend to change together. If harder queries usually take longer, hardness and latency are positively correlated. Correlation describes an observed relationship; by itself it does not prove that one variable causes the other.

A **methodology** is a documented way to design and perform a study. Reusing an existing benchmark methodology can make experiments more comparable with earlier research.

### Calibration

**Calibration** adjusts a completed method to meet a desired operating point. For example, after a policy has been created, a separate group of queries can be used to choose how high its confidence must be before stopping. Calibration changes a limited setting; it should not become another unrestricted policy-development phase.

### Held-out workload

**Held-out** data is deliberately hidden from training. A held-out workload or query set is used later to measure generalization. If the agent has inspected its answers, it is no longer truly held out.

### Decision tree, incremental result, and program synthesis

A **decision tree** makes a prediction by following a sequence of yes/no tests. For example, it might first ask whether ten valid results have been found, then whether recent improvement is small.

An **incremental** research result makes only a small advance over existing work. Incremental work can be useful, but a competitive publication usually needs a clearly important new capability, result, or understanding.

**Program synthesis** is the automated construction of a program from a specification, examples, or feedback. It is the wider research area containing the proposed generation of stopping-policy code.

### LAET, DARTH, E2E, and Bespoke-Card

These are names of prior systems, not general technical terms. **LAET** and **DARTH** are earlier methods for learned early termination in unfiltered ANN search and are cited by E2E. **E2E** is the closest published comparator because it applies learned adaptive termination to filtered ANN search. **Bespoke-Card** is a related agentic system that synthesizes database cardinality estimators. The brief recommends reading their papers rather than assuming the acronyms describe standard components.

## 5. Semester scope and system boundaries

Corresponding passage: [semester scope](/Users/danielarturi/Developer/JinyangLiWork/research/filtered-ann-stopping-policy-research-brief.md:47).

### Engine and instrumentable implementation

The **engine** is the software that actually stores the index and executes searches. An **implementation** is concrete program code for an algorithm.

An implementation is **instrumentable** if the researcher can add or expose measurements inside it. This project needs access to the search loop so it can record checkpoints and invoke the stopping policy. A service that exposes only `search(query)` and final results may be difficult to instrument.

### Research artifact

A **research artifact** is code, data, scripts, or configuration released with a paper. An artifact can help reproduce a method, but public availability does not guarantee that it builds on the researcher's machine or supports the needed modification.

### Search semantics

**Semantics** describe what an operation means. **Search semantics** include how distance is calculated, how filters are applied, which results are valid, and what occurs when fewer than k items qualify. Fixing them ensures that methods solve the same problem.

### Graph construction, traversal, and exploration budget

**Graph construction** is the process that builds the HNSW nodes, layers, and links before queries run.

**Traversal** is the sequence of graph nodes visited during a search. A method that changes traversal might explore an entirely different part of the graph.

An **exploration budget** limits how much of the graph a query may examine, for example a maximum number of node expansions or distance computations.

### Feature interface

An **interface** defines how software components communicate. The **feature interface** lists the values a policy is allowed to read, their types, and when they are updated. Fixing this interface gives competing policy-generation methods the same information.

### Categorical predicate, label membership, and equality

A **categorical value** belongs to a named group rather than a continuous numerical scale. Examples are `biology`, `database`, and `graphics`.

A **categorical predicate** tests such a group. **Label membership** asks whether an item's set of labels contains a requested label. **Equality** asks whether two values or sets are exactly the same. For an item with only one category, membership in that one-value set and equality with the category produce the same answer.

### Top-k retrieval and mean recall

**Top-k retrieval** requests the best k results according to a score or distance. “Top-10” fixes `k = 10`.

**Mean recall** adds the recall values for all evaluated queries and divides by the number of queries. A mean can hide poor individual cases, which is why the brief also asks for the recall distribution and failure counts.

### Dataset, pilot, and synthetic family

A **dataset** is an organized collection of data used in an experiment.

A **pilot** is a small preliminary experiment used to test feasibility and expose design problems before the full study.

**Synthetic data** is generated according to chosen rules rather than collected directly from the world. A **controlled synthetic family** is a set of generated datasets or workloads in which specific properties vary in known ways. It helps test cause and effect more clearly than a real dataset whose properties all change together.

### Repository, buildability, and compatibility

A code **repository** is a version-controlled collection of source files and history, commonly hosted on GitHub.

**Buildability** means the code can be compiled or installed successfully with available dependencies. **Compatibility** means it works with the required operating system, libraries, data, and desired changes.

### PostgreSQL, pgvector, integration, and search-loop hook

**PostgreSQL** is an open-source relational database system. **pgvector** is a PostgreSQL extension that adds vector storage, distance operations, and vector indexes.

**Integration** means connecting a new component to an existing system. A **hook** is an intentionally exposed point where external or experimental logic can observe or affect execution. A search-loop hook would let the policy run at checkpoints inside ANN traversal.

### Index-construction optimization and traversal synthesis

**Index-construction optimization** chooses or changes how the search index is built. It might change HNSW links or construction parameters. This affects storage and every later query.

**Traversal synthesis** generates the logic that decides which graph node to visit next. It is a larger action space than stopping alone because it changes the trajectory itself.

### SQL-plan optimization

**SQL** is a language for querying relational databases. A **query execution plan** is the sequence of operations selected to answer a SQL query, such as scanning a table, using an index, and joining rows. **SQL-plan optimization** searches for an efficient plan. The brief excludes it because it is a separate problem from stopping an ANN graph search.

### Mixed predicate language

A **predicate language** is the set of filter expressions a system supports. A mixed language might include equality, ranges, set membership, `AND`, and `OR`. Supporting only one categorical predicate removes many semantic and experimental complications.

### Distribution drift

A data **distribution** describes how often values and relationships occur. **Distribution drift** means that this pattern changes after training. For example, new categories might appear or qualifying documents might move to different regions of vector space. A policy developed before the change may no longer be well calibrated.

### Sensitivity experiment

A **sensitivity experiment** changes one design choice, such as k or the recall target, to see whether the main conclusion depends heavily on it. It tests robustness but is secondary to establishing the main result.

## 6. Recording and replaying search

Corresponding passage: [record comparable search trajectories](/Users/danielarturi/Developer/JinyangLiWork/research/filtered-ann-stopping-policy-research-brief.md:64).

### Instrumentation and checkpoint

**Instrumentation** is extra code added to observe a running program. It can count operations, record internal states, and measure time.

A **checkpoint** is a predefined moment during search at which the system records state and may ask the policy whether to continue. Checkpoints might occur every 20 node expansions. Very frequent checkpoints offer finer control but add more decision overhead.

### Distance computation and search-state feature

A **distance computation** applies the chosen distance formula to the query vector and one stored vector. It is a useful machine-independent count of important search work, although it does not capture every source of elapsed time.

A **search-state feature** is a numerical summary of the search at a checkpoint. It must be available then, rather than calculated using future search events or exact answers.

### Result set and native termination

A **result set** is the collection of items currently ready to return.

**Native termination behavior** is the stopping rule already built into the chosen HNSW implementation. The experiment must document it because the new policy may be unable to continue after the engine's own rule has ended the search.

### Ground truth and recall label

**Ground truth** is the trusted correct answer used for evaluation. Here it is obtained by exact filtered search, not by an especially long approximate run.

A **recall label** is the recall computed by comparing the approximate result at a checkpoint with ground truth. It is permitted during policy development but unavailable to a real online stopping decision.

### Prefix

A **prefix** is the first part of a sequence. A trajectory prefix ending at checkpoint 12 contains checkpoints 1 through 12. Replaying different stopping choices on stored prefixes can avoid rerunning an unchanged traversal.

### Trajectory replay and counterfactual decision

**Trajectory replay** applies a proposed stopping rule to a previously recorded trajectory. It finds the first recorded checkpoint at which that rule would stop.

A **counterfactual** asks what would have happened under a different choice. Replay can answer “What if we had stopped earlier on this identical traversal?” It cannot reliably answer “What if we had changed the beam width?” because that change may alter which nodes are visited next.

### Beam width, expansion order, and candidate handling

The **beam width** limits how many promising search possibilities are retained or explored. A wider beam usually explores more alternatives.

**Expansion** means taking a selected graph node and examining its neighbors. **Expansion order** is the order in which those selected nodes are processed.

**Candidate handling** covers how possible results or future nodes are inserted, removed, filtered, and prioritized. Changing any of these can change later states, invalidating replay from an old trajectory.

### Base traversal and base-search failure

The **base traversal** is the fixed underlying search procedure on top of which stopping is studied. A **base-search failure** occurs when that traversal never visits enough correct neighbors within its maximum budget. Continuing longer within the available trajectory cannot fix a result that was never encountered.

## 7. Policy language and safety boundaries

Corresponding passage: [define a small policy language](/Users/danielarturi/Developer/JinyangLiWork/research/filtered-ann-stopping-policy-research-brief.md:76).

### Policy language and bounded arithmetic

A **policy language** defines the legal building blocks for generated policies. It is similar to a very small programming language.

**Bounded arithmetic** means the policy may use a limited set of numerical operations, with limits on expression size or value behavior. The boundary keeps policies fast, comparable, and easier to validate.

A policy's **representation** is the form in which it is encoded, such as a decision tree, a short expression, or program source code. Holding the representation constant helps determine whether one search procedure is better at finding a policy within that form.

### Conditional expression

A **conditional expression** chooses a result based on a Boolean test, such as `stop if count >= 10; otherwise continue`. Conditions let a policy react differently to easy and hard searches.

### Normalization and distance summary

**Normalization** converts values to a common or more stable scale. For example, a distance can be divided by the first observed distance. This can make a feature less dependent on a dataset's raw numerical range.

A **distance summary** compresses many observed distances into a few values such as minimum, mean, maximum, or recent improvement. The full sequence may be too large for a compact policy.

### Metadata and global metadata statistic

**Metadata** is structured information about an item besides its main vector or content, such as category, year, or author.

A **global metadata statistic** summarizes the whole dataset, for example the total fraction of items labeled `biology`. “Global” distinguishes it from the fraction observed in the query's local search neighborhood.

### Code-size limit and expression depth

A **code-size limit** restricts how much generated logic a policy may contain. **Expression depth** measures how deeply operations or conditions are nested. Limits reduce execution cost and make it harder to memorize cases through a giant generated program.

### Query identifier and lookup table

A **query identifier** is a unique name or number assigned to a query. Allowing policies to read it could enable a rule such as “for query 317, stop at step 240,” which memorizes the experiment instead of generalizing.

A **lookup table** maps keys directly to stored answers. Vector-specific or query-specific lookup tables are excluded for the same reason.

### Missing value, empty queue, numerical error, and fallback

A **missing value** occurs when a feature cannot be computed. An **empty queue** means no candidate remains to explore. A **numerical error** includes invalid operations such as division by zero or a non-finite result.

A **fallback** is safe default behavior used when normal processing fails. Continuing the base search prevents an invalid generated policy from silently forcing a low-quality answer. Counting fallbacks reveals whether a policy only appears successful because errors are hidden.

## 8. Development feedback

Corresponding passage: [synthesize using structured development feedback](/Users/danielarturi/Developer/JinyangLiWork/research/filtered-ann-stopping-policy-research-brief.md:84).

### Development evidence

**Development evidence** is the data used while creating and selecting policies. It may influence design choices. It must remain separate from the final test data to avoid an overly optimistic evaluation.

### Premature stopping and unnecessary continuation

**Premature stopping** occurs when the policy stops before the current traversal has found enough of the correct results. It harms recall.

**Unnecessary continuation** occurs when the policy keeps searching after the target quality has already been reached and later work does not improve the needed answer. It wastes resources.

These categories identify opposite errors. A useful policy must balance them rather than eliminating one by always stopping or always continuing.

### Ground-truth-derived explanation and evidence accounting

A **ground-truth-derived explanation** uses knowledge of the exact answer to describe why a candidate policy was wrong. Real deployed policies cannot access that answer, but the development process may use it as **supervised feedback**: feedback based on examples paired with known correct answers.

**Evidence accounting** records every labeled query or answer inspection used to improve a method. Without it, a method could claim to learn from 100 examples while secretly examining thousands to find its best counterexamples.

### Diagnostic and oracle

A **diagnostic** is a measurement used to understand system behavior rather than an input available during normal execution.

An **oracle** is an imaginary or offline component with access to information the real system does not have. The earliest trajectory prefix that reaches target recall is an oracle stopping point because finding it requires exact answers and future trajectory states. It provides an upper-bound reference for that recorded trajectory, not a deployable policy.

### Globally optimal

A solution is **globally optimal** if no legal alternative solution is better under the objective. The earliest good prefix on one fixed trajectory is not globally optimal across all search algorithms because a different traversal might find the correct items sooner.

### Agent-call budget

An **agent call** is one request to the language model or agent system. Its budget limits calls, tokens, elapsed time, or money. Equal agent-call budgets are needed when comparing two agent feedback designs.

## 9. Freezing and calibration

Corresponding passage: [freeze and calibrate](/Users/danielarturi/Developer/JinyangLiWork/research/filtered-ann-stopping-policy-research-brief.md:97).

### Freeze

To **freeze** a policy means to stop changing its code before using later data. If the researcher edits it after seeing calibration or test failures, those data have become part of development and can no longer provide an independent evaluation.

### Data split: development, calibration, and test

A **split** is a non-overlapping portion of the available examples assigned a specific purpose.

- The **development split** is used to create features, policies, and code.
- The **calibration split** is used after policy selection to set a limited threshold or operating point.
- The **test split** is used once for the final unbiased measurement.

Keeping these roles separate reduces the chance of tailoring a method to the examples on which it is reported.

### Conservativeness parameter and threshold

A **parameter** is a value controlling a method's behavior. A **conservativeness parameter** makes stopping more cautious or aggressive.

A **threshold** is a cutoff used in a decision. If a policy outputs a “safe to stop” score from 0 to 1, it might stop only when the score is at least 0.9. Raising the threshold should make stopping less frequent if the policy family is designed monotonically.

### Parameter family, subset, and monotonic behavior

A **parameter family** is the collection of policies produced by varying one parameter while holding the code fixed.

A **subset** contains only elements also found in another set. Requiring conservative stopping checkpoints to be a subset of aggressive ones means a conservative setting cannot introduce a new earlier stop.

**Monotonic behavior** means changing a parameter in one direction changes the behavior in a consistent direction. Here, more conservativeness should never make a query stop earlier.

### Best-k result heap

A **heap** is a data structure that efficiently finds or removes the smallest or largest priority value. A **best-k result heap** maintains the k best qualifying items seen so far, usually with the worst of those k easy to access. As more nodes are visited on a fixed trajectory, the heap can replace a current result with a closer one.

### Objective, protocol, and recall guarantee

An **objective** is the quantity or rule a procedure tries to optimize, such as minimum latency subject to mean recall of at least 0.95.

An experimental **protocol** is the full predeclared procedure: data splits, budgets, stopping rules, measurements, and selection criteria. A fixed protocol limits accidental cherry-picking.

A **recall guarantee** would be a justified promise that recall satisfies a bound under stated conditions. Calibration on a finite sample provides evidence, not a universal guarantee for arbitrary future queries.

## 10. Deployment and reproducibility

Corresponding passage: [deploy and measure](/Users/danielarturi/Developer/JinyangLiWork/research/filtered-ann-stopping-policy-research-brief.md:105).

### Untouched test query

An **untouched test query** is one whose trace, label, and result have not influenced the policy, feature design, threshold, or experimental choices. Looking at test failures and then revising the method makes the test set part of development.

### Artifact, prompt, model identifier, seed, ledger, and revision

The generated **artifact** is the exact executable policy and related files produced by the experiment.

A **prompt** is the instruction and context sent to a language model. The **model identifier** records the exact model or version used.

A random **seed** is the initial value given to a pseudorandom generator. Recording it helps repeat data sampling and randomized algorithms.

A budget **ledger** is a detailed record of resources spent, such as labeled executions, agent calls, tokens, runtime, and cost.

An engine **revision** identifies the exact version of the search-engine source code, often with a version-control commit hash. These records support **reproducibility**, meaning another researcher can repeat the procedure and check whether it produces similar results.

## 11. Benchmark construction and experimental controls

Corresponding passages: [workload construction](/Users/danielarturi/Developer/JinyangLiWork/research/filtered-ann-stopping-policy-research-brief.md:109) and [splits and leakage prevention](/Users/danielarturi/Developer/JinyangLiWork/research/filtered-ann-stopping-policy-research-brief.md:119).

### Transformer-based embedding

A **transformer** is a neural-network architecture widely used for language and other sequence data. A **transformer-based document embedding** is a vector produced by such a model to summarize a document's meaning. The proposed project consumes these vectors; it does not need to train the transformer.

### Licensing, scale, and hardware constraint

A dataset's **license** states how it may be used, modified, and shared. **Scale** describes its size, such as number of vectors and dimensions.

A **hardware constraint** is a limit imposed by available memory, storage, CPUs, or GPUs. Using a documented subset can make an experiment feasible, but the subset must preserve relevant difficulty and be disclosed.

### Spatial distribution, cluster, independence, and alignment

A **spatial distribution** describes where points lie in vector space.

A **cluster** is a region containing many points close to one another. If qualifying points cluster around a query, filtered search may be easy even when few database items qualify overall.

Two properties are statistically **independent** when knowing one provides no information about the other. Approximate independence between labels and vector geometry means nearby points are neither especially likely nor unlikely to share a label.

**Alignment** here describes how global filter frequency agrees with local frequency near queries. Strong misalignment occurs when a category is common overall but rare near a particular query, or rare overall but concentrated near it.

### Explanatory variable and substitute measure

An **explanatory variable** is a measured property used to understand changes in an outcome. Selectivity may help explain query time.

A **substitute measure**, or proxy, is an easier-to-measure value used in place of the value of real interest. The brief warns that selectivity should not automatically replace direct measurement of execution difficulty.

### Partition and leakage

To **partition** data means to divide it into non-overlapping groups.

**Data leakage** occurs when information from evaluation examples reaches the training or design process. Near-duplicate vectors on both sides of a split can cause leakage because the supposedly new test query is almost the same as one already observed.

### Query–filter combination and held-out filter value

A **query–filter combination** pairs a query vector with its metadata condition. The same vector combined with a different filter is a different search problem.

A **held-out filter value** is a category never used during policy development. Testing it measures a stronger form of transfer than using a familiar category with new query vectors.

### Shared evidence

In the **shared-evidence** experiment, all methods receive the same labeled query traces at every budget. This controls the information available and asks which method uses it most effectively.

### Active acquisition and unlabeled pool

**Active acquisition**, also called active learning in some settings, allows a method to choose which example should be labeled next. The **unlabeled pool** is the set of possible training queries whose exact answers have not yet been computed.

This setting tests both selection and learning. It must count every label inspected, including unsuccessful searches for informative examples.

### Counterexample, random acquisition, and uncertainty-based acquisition

A **counterexample** is an example showing that a proposed rule fails. A query where a policy stops early at low recall is a counterexample to that policy.

**Random acquisition** selects the next query at random. It is a simple baseline.

**Uncertainty-based acquisition** selects examples about which a learned model is least confident. It is a common active-learning baseline. An agent should beat such alternatives before its data-selection ability is credited.

### Correlated observations and independent units

Two observations are **correlated** when they tend to resemble or influence one another. Checkpoints from the same query share the same vector, filter, and traversal, so treating them as hundreds of independent queries exaggerates the amount of evidence.

An **independent unit** is the level at which observations can reasonably be treated as separate, often a query or a repeated training run. Statistical uncertainty should be calculated over suitable independent units.

## 12. Quality definition and notation

Corresponding passage: [quality definition](/Users/danielarturi/Developer/JinyangLiWork/research/filtered-ann-stopping-policy-research-brief.md:130).

### q, S(q), G(q), and R(q)

The symbol **q** names one query.

**S(q)** is the set of all stored items eligible under q's filter. Parentheses indicate that the set depends on the query.

**G(q)** is the ground-truth set: the exact nearest eligible items for q, up to k items.

**R(q)** is the set returned by the approximate search. Recall measures how much R(q) overlaps G(q).

### Set size, minimum, and intersection

Vertical bars around a set, such as **|S(q)|**, mean the number of elements in the set.

**min(k, |S(q)|)** means whichever number is smaller: requested result count k or number of eligible items. If only six items pass the filter and k is ten, the correct result can contain only six items.

The symbol **∩** means set intersection: the items appearing in both sets. Therefore `|R(q) ∩ G(q)|` counts returned items that are also exact correct results.

### Deterministic behavior and distance tie

A procedure is **deterministic** if the same inputs and state always produce the same output. A **distance tie** occurs when two items have exactly the same distance from the query. A deterministic tie rule, such as sorting tied items by identifier, makes ground truth and repeated experiments consistent.

### Operating point and per-query threshold

An **operating point** is one chosen balance of quality and cost, often selected by a parameter. Targeting mean recall 0.95 defines such a point.

A **per-query threshold** is a quality cutoff applied separately to each query. Mean recall can be high even if a minority of queries perform badly, so reporting the fraction below a per-query threshold exposes the tail of failures.

### Distribution, predeclared group, and acceptance criterion

A recall **distribution** reports how recall values are spread, rather than reducing them to one average. It might be shown with percentiles, counts, or a plot.

A **predeclared group** is a category chosen before final results are inspected, such as low-, medium-, and high-selectivity queries. Predeclaration discourages selecting only groups that make a method look good.

An **acceptance criterion** is a rule decided in advance for considering an outcome successful, such as “mean recall is at least 0.95 in every predeclared hardness group.”

## 13. Baselines, ablations, and models

Corresponding passage: [baselines, ablations, and measurements](/Users/danielarturi/Developer/JinyangLiWork/research/filtered-ann-stopping-policy-research-brief.md:140).

### Baseline

A **baseline** is a reference method used to interpret a new method's performance. Strong baselines test plausible simpler explanations. If a hand-written rule or standard learner performs equally well, an agent may not be needed.

### Fixed exploration budget and native stopping rule

A **fixed exploration budget** gives every query the same maximum amount of search work. It is simple but cannot spend less on easy queries and more on hard ones.

The **native stopping rule** is the chosen engine's existing rule. Both are necessary references, but neither alone represents the strongest adaptive alternative.

### Gradient-boosted tree

A **decision tree** divides examples using a sequence of feature tests. A **gradient-boosted tree model** combines many small decision trees. Trees are added one after another, with each new tree focusing on errors made by the current collection. These models often perform well on spreadsheet-like numerical features and modest datasets.

A **same-feature** model receives exactly the features available to the synthesized policy. This controls whether one method wins because it sees more information.

### Faithful reproduction and adaptation

A **faithful reproduction** implements a prior method as closely as possible using its paper and released artifact. An **adaptation** changes it to work with a different engine, dataset, or interface. Adaptations may be necessary, but they should be documented because they can affect performance.

### Hyperparameter and hyperparameter search

A **hyperparameter** is a setting chosen outside the normal fitting process, such as tree depth or learning rate. **Hyperparameter search** evaluates multiple settings to find a good one. It consumes development data and compute, so its budget must be counted for fairness.

### Learning curve

A **learning curve** plots performance against the amount of training evidence. It can show that one method learns faster at small budgets even if both converge later, or that a claimed low-data advantage disappears after proper tuning.

### Conflation

To **conflate** two things is to treat them as if they were the same when they answer different questions. A same-feature boosted tree tests whether an ordinary learner can use the available evidence. A faithful E2E reproduction tests performance against the closest published system. One comparison should not silently stand in for the other.

### Ablation

An **ablation study** removes or changes one component of a method while leaving the rest as constant as possible. If removing structured feedback eliminates the advantage, that supports the claim that the feedback mechanism matters.

### Hypothesis space and policy complexity

A **hypothesis space** is the complete set of functions a learning method may choose. For this project, it closely matches the policy space.

**Policy complexity** measures how elaborate a policy is, such as number of conditions or tree depth. A larger space may fit training data better but can increase runtime and overfitting.

### Overfitting

**Overfitting** occurs when a method learns details of its development examples that do not hold for new data. It achieves excellent training results but poor generalization. Compact policies, separate splits, and held-out tests all help reveal or reduce overfitting.

## 14. Reported measurements

Corresponding passage: [measurement list and budget accounting](/Users/danielarturi/Developer/JinyangLiWork/research/filtered-ann-stopping-policy-research-brief.md:155).

### Mean, median, and p95

The **mean** is the sum of values divided by their count. The **median** is the middle value after sorting. The **95th percentile**, written **p95**, is a value at or below which roughly 95% of observations fall.

Latency is often uneven: most queries may be quick while a few are very slow. Mean, median, and p95 together show typical behavior, overall cost, and slow-tail behavior.

### Wall-clock latency

**Wall-clock latency** is elapsed real time, like measuring with a stopwatch. It includes relevant system costs that an operation count may miss, such as memory access and policy evaluation. Reliable measurements require a controlled environment and repeated runs.

### Feature-maintenance cost

**Feature maintenance** is the work required to update policy inputs as search proceeds. For example, maintaining a running mean distance adds arithmetic at every visited node. This cost is part of the deployed method.

### Stability and repeated synthesis run

**Stability** describes how consistent results are when randomness, training samples, or agent outputs change. A **repeated synthesis run** starts the policy-generation procedure again, often with a different random seed. One unusually successful generated policy is weak evidence if most runs fail.

### Paired comparison

A **paired comparison** evaluates two methods on the same units, such as the same queries and random seeds. Comparing their within-query differences removes some noise caused by certain queries being inherently harder.

### Uncertainty interval

An **uncertainty interval** is a range showing the precision of an estimated result. A narrow interval around a latency difference gives stronger evidence about its size than a single average alone. The exact statistical method must respect the experiment's independent units.

### Geometrically spaced budgets

**Geometrically spaced** values increase by a constant factor rather than a constant amount. Example budgets are 50, 100, 200, 400, and 800. This covers a wide range with relatively few experimental points.

### Computational budget

A **computational budget** limits processing resources such as CPU time, GPU time, or distance calculations. It differs from a label budget: two methods may receive the same number of labeled queries but spend very different amounts of computation searching policies.

### Amortization point and break-even point

**Amortization** spreads a one-time cost over repeated uses. Suppose policy development costs 10 hours and the policy saves 1 second per query. It needs 36,000 queries to save 10 hours in total.

That query count is the **break-even point**: after it, cumulative execution savings exceed the adaptation cost. The calculation must use compatible units and include all material costs.

## 15. Milestones, decision gates, and expected output

Corresponding passages: [milestones and decision gates](/Users/danielarturi/Developer/JinyangLiWork/research/filtered-ann-stopping-policy-research-brief.md:167) and [expected contribution](/Users/danielarturi/Developer/JinyangLiWork/research/filtered-ann-stopping-policy-research-brief.md:180).

### Milestone and decision gate

A **milestone** is a planned, concrete project result expected by a certain time, such as a working trace recorder.

A **decision gate** is a point at which evidence determines whether to continue, narrow, or change direction. For example, if the base search has no useful early-stopping opportunity, building an agent for that setup is unlikely to answer the research question.

### Feasibility and credible baseline

**Feasibility** asks whether the planned work can be completed with the available time, software access, data, and hardware.

A **credible baseline** is a relevant and competently implemented comparison that knowledgeable readers would take seriously. Beating a deliberately poor method does not establish value.

### Replay validation

**Replay validation** checks that a policy decision simulated on a stored trajectory produces the same result as running that policy inside the real engine. This catches mismatches in checkpoint timing or state reconstruction.

### Repeatability and artifact packaging

**Repeatability** means obtaining consistent results when the same team repeats the experiment under the same conditions.

**Artifact packaging** organizes the code, data instructions, configurations, and scripts required to run the study. Good packaging lets reviewers inspect policies and reproduce figures without reconstructing undocumented steps.

### Workload suite and comparative study

A **workload suite** is a documented collection of multiple workloads used together for evaluation.

A **comparative study** evaluates multiple methods under a shared protocol and analyzes their differences. It can be valuable even when the proposed method does not win, provided the comparison is rigorous and reveals something useful.

### Active acquisition, workload drift, and cross-engine transfer

These appear as possible thesis extensions. **Active acquisition** was defined above as choosing which evidence to label. **Workload drift** is distribution drift specifically in incoming queries or data.

**Cross-engine transfer** asks whether a policy or synthesis procedure developed for one search engine works with another. Different engines expose different states and implement graph traversal differently, so such transfer is not automatic.

## 16. Publication and citation vocabulary

Corresponding passage: [sources and reading order](/Users/danielarturi/Developer/JinyangLiWork/research/filtered-ann-stopping-policy-research-brief.md:190).

### Preprint

A **preprint** is a paper made publicly available before, or independently of, final publication. It can contain valuable recent work, but its claims may not yet have passed formal peer review and later versions may change.

### Peer review, conference, workshop, and proceedings

**Peer review** is evaluation by other researchers in the field before acceptance at a venue.

A research **conference** publishes accepted papers and hosts presentations. A **workshop** is usually a smaller, more focused event, often connected to a conference. Acceptance standards, paper lengths, and research maturity can differ between the main conference and its workshops.

**Proceedings** are the published collection of papers accepted by a conference or workshop.

### KDD, VLDB, PVLDB, AIDB, and IEEE TPAMI

These names identify publication venues:

- **KDD** is the ACM conference on Knowledge Discovery and Data Mining.
- **VLDB** is a major database research conference associated with the Very Large Data Bases community.
- **PVLDB** is the *Proceedings of the VLDB Endowment*, a journal-style publication whose papers are presented at VLDB.
- **AIDB** is a workshop focused on artificial intelligence and databases, held with VLDB in the cited year.
- **IEEE TPAMI** is *IEEE Transactions on Pattern Analysis and Machine Intelligence*, a peer-reviewed journal.

Venue names help identify where a paper appeared, but the usefulness of a result still depends on its methods, assumptions, and evidence.

## 17. A compact reading map

The central system idea can be read as a short chain:

1. A filtered ANN query asks for the closest vectors that also pass a metadata predicate.
2. HNSW explores a graph and gradually improves its current top-k qualifying results.
3. A stopping policy uses only current search-state features to decide whether more exploration is worth its cost.
4. An offline agent synthesizes a compact policy from labeled search trajectories and structured examples of stopping too soon or continuing too long.
5. A separate calibration split chooses how conservative the frozen policy should be.
6. Untouched test queries measure recall, latency, generalization, and policy overhead.
7. Strong baselines with the same evidence determine whether the agent adds value beyond established learning and search methods.
8. The full adaptation ledger determines whether any online savings justify the cost of creating the specialized policy.

This sequence is also the logic of the proposed research contribution: the project is not merely asking whether a generated rule can stop search early. It asks whether the agent can acquire a useful and generalizable rule more efficiently than credible alternatives under a fair accounting of evidence and computation.
