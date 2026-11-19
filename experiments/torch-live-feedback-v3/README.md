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

The run is capped at one six-hour allocation, 300,000 charged ANN reservations
and a new $15 model ledger. Native queries reserve durable windows before
execution. The final comparison receives a 225,000-attempt reservation before
development admission. No automatic retry or requeue occurs. The model and
credentials stay local; Torch runs only trusted compilation and ANN evaluation.

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

The experiment is implemented and locally tested; measured results and final
execution status will be recorded after collection. Large workspace, transcripts,
native returns and sealed inputs live outside Git under the trial directory.
