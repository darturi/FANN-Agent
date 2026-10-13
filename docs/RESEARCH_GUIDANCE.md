# Research guidance and experiment records

FANNAgent can supply a cited primer and require short, testable hypotheses before offline
measurements. The model still chooses its queries, analyses, experiments, and stopping rules.
The host records what actually ran and connects the resulting evidence to the model's conclusions.

## Configuration and sources

Use `research: {mode: guided}` in a fresh schema-v2 configuration. `fannagent init` and the shipped
examples select this mode. Configurations without `research` preserve the original `baseline`
behavior. `protocol_only` enables experiment accountability without literature guidance, supporting
a separate comparison of the primer's contribution. Modes are immutable within a run.

The packaged primer separates findings from project rules. Its literature principles are:

- `E2E_QUERY_EFFORT`: query-dependent search effort motivates adaptive stopping.
- `E2E_FILTER_SIGNALS`: early filter observations can complement distance signals.
- `GLS_LOCAL_ALIGNMENT`: global and local predicate selectivity can differ around a query.

The E2E principles cite [version 2, Sections 3 and 4](https://arxiv.org/html/2602.06721v2).
The GLS principle cites [the MoReVec paper version 1, Section 4](https://arxiv.org/html/2602.11443v1).
The primer records authors, versions, source sections, verification dates, and limits of application.
It also explains the project's rules about exact references, runtime features, complete latency,
missing observations, and workload splits. It is not an implementation of E2E's predictor.

Suggestions refer to the selected backend's runtime feature groups and require inspection of their
availability and costs. Offline GLS, reconstructed filter membership, and actual stopping labels
are diagnostic evidence; they do not become deployed policy inputs.

Guided startup persists the primer snapshot and hash, system prompt hash, mode, and research
protocol version before the first provider request. The development guidance artifact is referenced
in startup context. Resume retains the saved conversation and snapshot, including after a package
update. An unsupported protocol or an insufficient verified input bound fails before model spending.

Fresh conversations also receive a development-only query catalog, its query and independent
vector-group counts, pagination details, runtime feature names by permitted collection group,
and concrete tool argument/response guidance. The catalog contains query objects and group IDs;
it excludes held-out queries and source anchors. Read the catalog in Python and print summaries,
rather than filling the conversation with vectors. `queries {}` still returns the first 20 queries;
its maximum page size is 100. Adjacent filter variants may share a vector.

For a 12-turn study, the advisory workflow targets full development evaluation by turn 6 and
calibration by turn 8, reserving turns for experiment conclusions, submission and corrections.
Use the first three turns for orientation and cheap screening. `screen` compares ordinary native
execution, the actual candidate, and an always-continue policy with the same collection groups,
without tracing, on a permitted development query. One warmup and three paired repetitions per
mode give a preliminary latency and recall comparison. This is screening evidence, not statistical
acceptance. Traced `probe` timings and work savings alone do not establish production latency benefit.
Each subsequent request receives current turn, charge and stage counts. These reminders do not
force a candidate or waive any acceptance requirement. A defensible path is: brief investigation,
conclude it, register candidate evaluation, run `development_evaluate`, conclude, register
calibration, call `calibrate` with `checkpoint: true`, conclude and submit the exact accepted policy.
Sequential operations can share a Bash action, with every response checked. Abstain when evidence
does not support a candidate. `validate` checks structure only and does not replace evaluation.

The broker waits up to three hours for a tool response. The shell action deadline is 11040 seconds,
including the 180-second syntax allowance and response overhead. Development evaluation and
calibration save a durable receipt before starting and periodically record aggregate progress.
Retrieve `evaluation_status {"job_id":"..."}` to inspect a receipt and obtain its saved result;
use `artifact` with `evaluation_report_artifact` for the full development report. Calibration
receipts expose only approved aggregates. The broker processes calls serially, so a tool status
request waits behind an active evaluation; the host can inspect durable progress with a read-only
store while it runs. A completed request with the same identity returns its saved response.
A timeout stops the sandbox; ambiguous measurements must not be replayed automatically. Retrieval
does not consume another evaluation or repeat measurements. Per-query timeouts, measurement passes,
statistical gates, spending and held-out protections are unchanged. Existing saved conversations
retain their original prompt and workflow protocol; use a fresh run to apply this orientation.

## Starting an experiment

In `guided` and `protocol_only`, first call `fannagent-tool experiment` with `action: start` and a
plan. All string fields are nonempty and limited to 512 characters; `client_key` uses at most 80
letters, numbers, underscores, or hyphens. The plan has a 6 KiB serialized bound.

```json
{
  "action": "start",
  "plan": {
    "client_key": "local-filter-check",
    "purpose": "investigation",
    "hypothesis": "Locally sparse filter matches may require later stopping despite similar global selectivity.",
    "why_now": "Test whether global selectivity hides differences relevant to the current rule.",
    "basis": {
      "kind": "literature",
      "principle_ids": ["GLS_LOCAL_ALIGNMENT", "E2E_FILTER_SIGNALS"],
      "evidence_refs": []
    },
    "comparison": "Compare permitted queries with similar global match fractions and different local fractions.",
    "measurements": "Inspect descriptors, actual stopping labels, and recall relative to ordinary execution.",
    "expected_observation": "Locally sparse cases show later recall improvements.",
    "challenging_observation": "Local sparsity does not distinguish late improvements.",
    "decision_if_supported": "Investigate an available runtime filter or progress signal alongside result count.",
    "decision_if_challenged": "Abandon this explanation and investigate another signal."
  }
}
```

Purpose is `investigation`, `candidate_evaluation`, or `calibration`. Basis is `literature`,
`measurement`, or `exploratory`. A literature basis needs a registered literature finding;
project rules alone do not count as a literature citation. A measurement basis
needs permitted development artifact hashes. Exploratory ideas need no invented citation.
`protocol_only` does not have literature principle IDs.

Only one experiment is open at a time. Its measurements attach automatically and may span many
turns. Repeating an identical plan under the same client key returns the original record; changing
the plan under that key is rejected. Plans are short scientific justifications rather than requests
for private chain-of-thought.

## Measurement and conclusion

The protocol requires an open plan for `count`, `descriptors`, `probe`, `screen`, `audit`, `labels`,
`development_evaluate`, and `calibrate`. `inspect`, `queries`, `sample`, `artifact`, and local policy
`validate` remain available for orientation. Python analysis remains available in the sandbox.

The host saves a pending operation before execution, then its outcome, query/policy identity,
bounded observation, and evidence references. Guided tool results include `experiment_event_id`.
Use that ID or a recorded development artifact hash when concluding. Calibration records contain
only existing public aggregates, with private rows, labels, and checkpoint records withheld.

```json
{
  "action": "finish",
  "client_key": "local-filter-check",
  "conclusion": {
    "assessment": "challenged",
    "observations": "The recorded cases did not show the predicted relationship.",
    "evidence_refs": ["$latest"],
    "decision": "Investigate another available signal instead of adding a local-sparsity assumption."
  }
}
```

Assessment is `supported`, `challenged`, or `inconclusive`. `$latest` resolves to the latest operation
in the experiment. Conclusions have a 4 KiB serialized bound and at most 32 references. The host
checks their references and preserves the model's interpretation separately from measurements.
It does not establish the scientific soundness of a conclusion. Python-derived claims should name
the permitted evidence they use and be distinguished from host measurements.

Finish an experiment with accepted calibration for the exact candidate before `submit`. The study's
existing calibration and freeze checks remain authoritative. A later rejected calibration still
makes that candidate ineligible. Malformed plans and references use the existing correction feedback
and invalid-turn limit; paid model attempts remain charged.

## Resume and inspection

```sh
fannagent experiments --run runs/demo
fannagent experiments --run runs/demo --experiment-id EXPERIMENT_ID --limit 20
fannagent status --run runs/demo
fannagent report --run runs/demo
```

The experiment command and status use read-only state. Report adds guidance and journal provenance
alongside existing scientific results. Lists and event pages are limited to 48 KiB and 100 entries;
`next_offset` identifies the next page, selected with `--offset`. The agent's experiment tool also
supports `action: get` with an experiment ID or client
key, and `action: list` with offset/limit.

Step-limit interruption leaves the experiment open for resume. Operations interrupted before a
durable result are marked unknown on recovery and are not replayed automatically. Budget exhaustion
marks an open experiment interrupted and can still freeze an eligible designated checkpoint using
cached calibration. It requires no model-written conclusion, new experiment, or provider call.
Abstention and invalid-turn termination preserve their existing outcomes.

Bounded SQLite records retain journal failures if artifact capacity is exhausted. A plan must be
durable before admitting measurements. The journal limits protocol runs to 1,024 experiments and
10,000 measured operations; baseline recording is observational and adds no execution cap.

## Evaluating the revision

The three modes separate original behavior, explicit planning, and literature guidance. Compare
fresh runs with matched model settings, backend state, workloads/splits, and declared budgets.
Count the extra planning tokens and actual labeled-query acquisition; equal dollar ceilings do not
imply equal numbers of experiments. A common evidence cap requires a comparison runner that enforces
it, since the controller's budget remains monetary.

Repeated aggregate calibration is still part of current candidate selection. Recorded rounds do
not make calibration a one-use procedure or establish a future-query quality guarantee. Independent
final testing retains its existing entitlement and acceptance criteria. A behavior smoke test can
establish that the protocol works; multiple comparative synthesis runs are needed to assess whether
it improves evidence efficiency or policy quality.
