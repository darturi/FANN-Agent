# Data and queries: what the agent studied

The measured case study uses the **Reviews workload from MoReVec**, a physical
pgvector HNSW index of **247,286 review vectors with 768 dimensions**, and top-10
queries under three metadata-filter conditions. This is the database workload
behind the policy results; the free local simulation uses a synthetic backend.

[Architecture](../agent-design.md) · [Oracle](oracle.md) · [Evaluation](evaluation.md)

## The database workload

| Property | Recorded setting |
|---|---|
| Indexed rows | 247,286 |
| Vector dimensions | 768 |
| Search engine | PostgreSQL with the instrumented native pgvector integration |
| Index | HNSW, `m=16`, `ef_construction=64` |
| Distance | Cosine |
| Search effort | `hnsw.ef_search=640` |
| Requested neighbors | `k=10` |
| Metadata used for these filters | `total_votes`, represented as portable field `m_000000` |
| Execution setting | x86-64 Torch HPC jobs using the existing physical Reviews index and frozen native runtime |

The experiment reuses that physical index across policy/control comparisons.
It does not rebuild a different graph for each candidate.

## Three query conditions per vector

| Stratum | Predicate | Purpose in the experiment |
|---|---|---|
| `unfiltered` | No filter | Observe vector search without a metadata restriction. |
| `votes32` | `total_votes >= 32` | Add a metadata constraint to the same vector query. |
| `votes108` | `total_votes >= 108` | Tighten that constraint and observe a different quality/work tradeoff. |

One query vector appears in all three conditions. For example, training vector
`reviews-bounded-v0778` supplies `-unfiltered`, `-votes32`, and `-votes108` cases.
The portable representation of its `votes32` predicate is:

```json
{"field": "m_000000", "op": "gte", "value": 32}
```

The same 768-dimensional query vector and `k=10` accompany that predicate.
The [study evidence](study-evidence.json) includes selected query metadata and
inventory hashes, with vectors omitted.

## Split by vector, then apply the filters

| Role | Independent vector groups | Query/filter cases | Use |
|---|---:|---:|---|
| Training | 100 | 300 | Agent analysis, policy generation, offline screening, and subsequent frozen-candidate timing |
| Held-out confirmation | 60 | 180 | One unchanged policy, selected before these queries are opened |

Training and held-out inventories have disjoint group and query identifiers.
All three variants of a vector stay together. The proposal study's five
cross-validation folds are also assigned by vector group: SHA-256 of
`20261019/` followed by the group ID, interpreted as an integer modulo five.

Repeated timing passes improve measurement precision; they do not create new
independent query vectors. The data supplied to the proposal agent are training
evidence, so its own cross-validation estimates remain development feedback.

## What information the agent receives

The recorded proposal run receives **2,397 actual stopped-execution outcomes**
and **19 qualified runtime features** for the 300 training cases at
`ef_search=640`. Features include checkpoint ordinal, completed expansions,
distance-evaluation counts, frontier size, retained-result count, minimum
frontier distance, and predicate-leaf count.

The model can analyze query identifiers, query-group labels, and filter labels
offline. A policy tree can use only its declared, qualified runtime features;
query identities cannot become runtime inputs. Query vectors, hindsight-oracle
selections, and held-out records are excluded from the learner view. The original
profile also excludes the numeric predicate threshold as a runtime input.
Missing required features cause search to continue.

This gives the agent a constrained learning problem: infer useful stopping
conditions from observed search state and measured outcomes, then express them
in the policy language. The [real-run walkthrough](agent-run.md) shows the model
writing its own analysis and fitting code within that interface.

## Provenance and availability

The [study evidence](study-evidence.json) records the source-package paths and
SHA-256 identities used to check these descriptions, the complete qualified
feature list, split counts, and candidate lineage. The original
[training](../verification/frozen-proposals-timing-v1-runtime-fix-postrun.json) and
[held-out](../verification/frozen-proposals-timing-v1-runtime-fix-confirmation-postrun.json)
verification records identify the measured archives and runtime contract.

The full review vectors, physical database/index, raw campaign archives, and
original runtime images remain external research assets. They are not bundled
with this repository. Data access follows the original dataset's terms; this
portfolio supplies documentation, curated evidence, and the source code.
