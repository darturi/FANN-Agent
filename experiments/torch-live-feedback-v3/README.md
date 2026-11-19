# V3 agent with live Torch feedback

This is the new broad-language controller. Historical v1/v2 controllers and
sealed experiment inputs remain available for reproduction. The model can use
isolated offline Python fitting scripts, submit normal v3 JSON artifacts, get
actual development quality/latency feedback, and freeze one candidate or abstain.

Read [PROTOCOL.md](PROTOCOL.md) for the exposure boundary, exploratory-versus-
qualified freeze, timing controls and resource accounting. The language is
`fannagent.broad-stop.v3`; it is the same trusted compiler/VM used for the broad
`oracle_feasible`. No oracle program or protected outcome enters the agent's
workspace. Discovery uses 450 development groups. Frozen evaluation reports both
the 275-group test subset and all 1,000 vectors, alongside the saved full- and
test-fitted broad oracles on one shared baseline.

Future fresh preparations now default to **Claude Opus 5.5**, adaptive thinking,
high effort and a 6,000-token total output limit, through
[model-profile.json](model-profile.json). The model-specific preflight checks
Opus access, supported inference settings, the one-million-token input bound,
and current $4 / $20 per-million input/output rates before any future generation.
The API version is bound in each review. Model settings and rates are included
in the review's source hashes; a resume retains its original model, inference
settings and ledger rather than silently changing an existing spending contract.
The [configuration verification](checks/opus-config-verification.json) used
unpaid metadata/document GETs and local tests, with zero new generations or
Torch jobs. The completed measurements below used **Sonnet 5.5**. This model
selection does not change the search prompt, quality gates or stopping logic.

The initial protocol allowed one six-hour allocation, 300,000 charged ANN
reservations and a $15 model ledger. After the idle-stopped first attempt, the
user explicitly approved one [bounded continuation](CONTINUATION.md), carrying
all spend, queries and allocated time. Both jobs stay under six aggregate hours.
Native queries reserve durable windows before execution, with 225,000 attempts
reserved for final comparison. No automatic retry or requeue occurs. The model
and credentials stay local; Torch runs trusted compilation and ANN evaluation.

From the `agent` repository:

```sh
.venv/bin/python -B -m pytest experiments/torch-live-feedback-v3/tests -q
.venv/bin/ruff check experiments/torch-live-feedback-v3
.venv/bin/python -B experiments/torch-live-feedback-v3/prepare.py \
  --output ../trials/fannagent-benchmark-evaluation-v1/reviews-small/torch-live-feedback-v3/run-v1
```

Prepare once into a fresh directory. `prepare.py` verifies the old oracle source
binding, packages native inputs and creates a separately mounted development
workspace. It makes no provider call and submits no job. Native deployment uses
`remote.py launch`, then read-only `status`, then `qualify` inside that allocation.
`run_agent.py prepare` seals the prompt, tools, model configuration, evidence,
workspace and source identities. The run requires an authorization record bound
to that review; the user's explicit experiment request supplies its provenance.
The runner freshly verifies official provider model/rates before generation.

After the model loop terminates, `remote.py final` freezes the selected artifact
and submits exactly one final comparison. Abstention or no submission maps to
native continuation, with no researcher fallback. Final quality failures are
retained and do not trigger a new search. No protected result is returned to the
model. `remote.py collect` requires terminal scheduler accounting and verifies
the returned archive. Read-only request recovery uses the identity in the local
client receipt; never rerun a delivery whose outcome is unknown.

The experiment completed on November 19, 2026. Job **23741092** qualified the native path, then
stopped at the old fifteen-minute idle limit while the model was fitting offline.
No learned policy reached native evaluation in that attempt. Its 24 model calls,
$1.707958, 1,262 allocated seconds and 256 reservations remain recorded in the
[first-attempt report](results/REPORT.md). The heartbeat/resume repair has 31
passing controller/language tests.

Approved continuation **23747524** completed with exit 0. The same agent made
32 cumulative model calls costing **$2.797810**, measured three development
candidates, and selected `candidate-2` (`fgap-margin-narrow`). It stopped with
budget remaining. This single frozen policy uses frontier-gap thresholds at
checkpoint 64 for votes108 and checkpoint 32 for votes32, continuing natively
otherwise. It stopped on 145 / 3,150 development cases, 105 / 1,925 held-out
cases and 351 / 7,000 full-workload cases. It had zero recall or result-count
losses on both final cohorts.

| Cohort | Agent savings | Broad `oracle_feasible` savings | Gap |
|---|---:|---:|---:|
| Held-out: 1,925 cases | −0.46% | 66.32% | 66.77 pp |
| Full: 7,000 cases | −1.78% | 64.87% | 66.66 pp |

Negative savings indicate higher measured latency. Strict per-condition control
equivalence failed for both cohorts; these estimates are descriptive. The
agent's held-out conditional 95% savings interval includes zero. The oracle has
zero intended-cohort recall losses; the full oracle has three result-count
reductions, recorded separately. The agent used development only, while each
oracle was hindsight-fitted to its reported cohort. This episode does not
exhaust the v3 language or establish an agent discovery limit.

Both allocations used **6,049 seconds / 21,600** and **248,800 / 300,000** charged
ANN reservations, with zero fresh exact searches and no automatic retries.
The final comparison contains 42,000 quality records and 168,000 timing records.
See the [verified report](results/comparison-v1/REPORT.md),
[discovery receipt](results/agent-discovery.json), and
[independent return audit](checks/continuation-postrun.json), with
[saved commands](COMMANDS.md). Large workspaces, transcripts, native returns
and sealed inputs remain outside Git under the sibling trial directory.
