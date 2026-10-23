# The stopping oracle: measuring the opportunity

Before asking an agent to learn a stopping rule, I needed a way to ask a simpler
question: **at which tested checkpoints could this search have stopped while
retaining the quality of ordinary native execution?**

The sparse hindsight oracle answers that question using actual stopped database
executions. It provides a diagnostic reference for search headroom and a way to
organize stopping evidence for the agent.

[Architecture](../agent-design.md) · [Evaluation](evaluation.md) · [Data and queries](workload.md)

## Two references with different jobs

| Reference | Question it answers | How it works |
|---|---|---|
| Exact filtered nearest-neighbor reference | Which eligible items should a top-10 query retrieve? | An exhaustive database reference bypasses index scans; result scoring handles the exact-distance tie boundary. |
| Sparse stopping oracle | Which measured early stop preserves this query's native recall? | Execute sampled stops, score their actual returned results, and choose the earliest tested qualifying checkpoint. |

The exact reference measures retrieval quality. The stopping oracle uses those
scores to select a checkpoint retrospectively. Preserving native recall need
not mean achieving 100% recall: the native search is itself approximate.

## Constructing a trustworthy stop label

1. Run ordinary native search and score its results against the exact reference.
2. Capture an always-continue trajectory and verify that tracing retains the
   native results and distances.
3. Select a sparse set of checkpoints from that trajectory. The original
   acquisition uses at most eight tested checkpoints per query, based on powers
   of two and the final checkpoint, thinning the set when needed.
4. Execute a real stopping policy at each selected checkpoint. Check that its
   observed execution prefix matches the reference trajectory through that stop.
5. Record actual work, result completeness, validity, and recall. Among valid
   stops returning all ten results with recall at least the native score, choose
   the earliest checkpoint. If none qualifies, continue search.

```text
qualifying = tested stops where:
    result is valid
    returned_count == 10
    stop_recall >= native_recall

oracle_checkpoint = earliest qualifying checkpoint, or continue
```

Only executed stops receive labels. Untested checkpoints remain unknown; the
procedure does not interpolate recall or assume it improves monotonically.
Because the oracle samples stops, its chosen point is the earliest *tested*
qualifying stop, rather than proof of the globally earliest safe stop.

## How this supports the agent design

The original proposal study supplied **2,397 measured stop outcomes** across
300 training query/filter cases. The agent could join those outcomes to 19
qualified runtime features, inspect differences between filters, and write its
own threshold scans and staged fitting code.

The learner view excluded oracle selections and query vectors. The oracle
remained an evaluator-only control. A deployable tree must choose its action
from features available during the search, without knowing future outcomes or
the answer for that query.

That distinction turns the oracle into an experimental instrument: it helps
separate available stopping opportunity from the agent's ability to express
and discover a useful decision rule. Timing the oracle and continue controls
also helps expose the cost of exercising the policy path.

## Evidence to inspect

The [study evidence](study-evidence.json) preserves the original oracle
definition, checkpoint-acquisition contract, feature list, source-file hashes,
and a query inventory summary. The
[returned-evidence importer](../../src/fannagent/learning/returned.py) constructs
the `oracle-original` arm with per-query policy hashes and checks its measured
checkpoint. The [benchmark reporter](../../src/fannagent/learning/benchmark.py)
marks oracle arms as nondeployable.

The companion [pgvector exact-reference implementation](https://github.com/darturi/FANN-Agent-pgvector/blob/portfolio-v1/src/fannagent_pgvector/backend.py)
shows index-bypass verification and exact-boundary handling. The frozen timing
study's [verification record](../verification/frozen-proposals-timing-v1-runtime-fix-postrun.json)
identifies the original native runtime and measurements.
