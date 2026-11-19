# Broad policy language and feasible hindsight oracles

This implements the broader deployable language and compares independently
hindsight-fitted policies for the 1,925-case test cohort and 7,000-case full
workload. Existing work was committed as `795db05` first. The old experiment
inputs, policies, engine and reports remain immutable.

`src/fannagent/api/broad_policy.py` defines typed causal expressions, checkpoint
schedules, arithmetic/Boolean operators and query-local registers. The v3
agent interface in `experiments/filtered-ann-protocol-v3` accepts ordinary JSON
artifacts from offline scripts or inline submissions. Its trusted compiler
produces only data tables for `runtime/broad_runtime.inc`; generated agent code
does not run inside PostgreSQL. Fixed source/table/stack/state/fuel budgets
replace the former three-rule/four-comparison shape.

The experiment first captures and qualifies causal observations on the exact
original graph, reusing actual executed-prefix labels. `fit_broad.py` emits
normal v3 policy artifacts. It prefers compact balanced frontier-distance
threshold trees; mixed feature-value groups use richer pure-leaf trees. These
models can memorize finite-cohort causal observations under hindsight. The
experiment tests representational capacity and deployment cost, not autonomous
discovery, ordinary held-out performance or generalization.

The fresh 12-family comparison measures native, ideal, constrained, both prior
narrow feasible policies, both broader feasible policies, broader matched
continuation controls, empty v2/v3 and a native clone. Four readers and twelve
balanced rotations give every family four measurements per case, one on every
reader. All actual quality outputs and compiled audits are checked before
timing. A separate canonical pass verifies frontier/work at every captured
checkpoint. Feature/VM costs remain inside each serving request's timer.

Read [PROTOCOL.md](PROTOCOL.md) for scope, gates, resource budgets and control
interpretation, [COMMANDS.md](COMMANDS.md) for reproduction, and
[results/REPORT.md](results/REPORT.md) for the verified numerical comparison.
The broader feasible policies measured 64.95% held-out and 68.39% full-workload
latency savings, versus 21.37% and 19.80% for the same prior narrow policies in
the fresh comparison. Timing controls did not establish ±2% equivalence, so the
reported values are descriptive hindsight estimates. Both intended-cohort
native recall gates passed; full-workload result count declined in three cases.
The prior pause and explicit resume remain in [PAUSED.json](PAUSED.json) and
[RESUMED.json](RESUMED.json). Failed qualification and its complete reservation/
time charge are retained. The corrected comparison applies the existing native
cosine projection; frozen policies and the primary timing method were unchanged.
Large raw returns and sealed kits remain outside Git under
`trials/fannagent-benchmark-evaluation-v1/reviews-small/broad-oracle-v1`.
