# Live Torch feedback with a six-hour allocation

The model/controller runs locally. One Torch batch worker compiles and executes its
new policies, returns actual development recall and paired request timings, and
then waits for the next batch. Compute-node internet and provider credentials on
Torch are unnecessary. This is a new opt-in experiment, not a modification or
continuation of the closed M4 episodes or frozen M5 comparison.

**Status:** 18 local tests pass. The live compilation path built an amd64 module
offline; its C decisions match the existing two diagnostic controls exactly.
The compiled module passed all seven synthetic PostgreSQL conditions, full
quality and balanced request-timing loops (3,024 synthetic attempts). Details are
in `verification.json`. No Torch allocation or paid model call has
been launched. Actual original-graph startup, on-node compilation and live-return
qualification remain pending. This prototype must not be described as a measured
policy benefit or a production-qualified experiment service.

## The usage boundary

The user's selected maximum is **one allocation of six hours**. `submit.sh`
passes `--time=06:00:00` and `--no-requeue` explicitly. It creates a permanent
submission marker before contacting Slurm and never removes an uncertain one.
The worker has no scheduler or extension tool. It refuses an existing run or a
Slurm restart. There are no dependent jobs or automatic replacement allocations.

All job time counts, including setup, builds and waiting for the local agent:

| Boundary | Behavior |
| --- | --- |
| Fifteen idle minutes | Exit if no request arrives, including after a laptop disconnect |
| 5 h 15 min | Stop admitting new batches |
| 5 h 40 min | Stop work, including a running build/container |
| 5 h 55 min | Independent outer process timeout; kill grace is 15 seconds |
| 5 h 59 min | Whole batch-shell timeout, including archiving; kill grace is 15 seconds |
| 6 h | Requested Slurm allocation limit |
| 300,000 native attempts | Episode-wide limit, reserved durably before each query |

The allocation requests four physical CPUs and 48 GiB, no GPU. Six elapsed hours
at four CPUs is at most 24 requested CPU-hours; this is not a statement about site
charging multipliers. Queue waiting is outside allocation runtime. Slurm documents
a site-configured termination grace/possible over-time policy, so an absolute
to-the-second infrastructure guarantee is not claimed. The earlier independent
timeouts leave headroom inside the requested limit. See [Slurm sbatch](https://slurm.schedmd.com/sbatch.html).

The local agent depends on a working connection to obtain the next result. Its
failure cannot extend the worker's independent clocks. A request interrupted in
delivery is audited by identity, not repeated. Unknown outcomes remain unknown.

## What the agent gets

`evaluate_candidates` accepts at most three validated v2 DSL policies per batch.
Only the compiler emits C. The immutable image, graph, development query files,
compiler sources and inherited M5 measurement helpers are pinned in the kit.
Each batch builds a new module and starts a fresh private database copy; loaded
libraries are never overwritten beneath running readers. A successful stopped
copy is verified before releasing its owned work directory. Failed work is retained.

Every candidate and matched continue control is checked on all 450 development
groups / 3,150 cases, including all six filters plus unfiltered. The inherited M5
checks recapture all 9,436 reached prefixes, including 1,496 partial prefixes,
check masked observations and first decisions, bridge native outputs and compare
actual answers against the qualified raw native reference. Any recall regression
rejects the batch before timing; failure details remain available for revision.
Saved verified exact references are scoring inputs only. Approximate serving has
no exact access, fallback or completion repair.

Timing uses the same hash-selected **64 development groups across all seven
conditions** on every round. It retains M5's four-reader/CPU role crossover, both
cycles, eight observations per query/family, matched controls and empty-policy
diagnostic. Audit/work instrumentation is off. Complete request time includes SQL
construction, execution, fetch and result decoding. Compilation, connection,
membership setup, warmups and waiting are outside that request timer and remain
part of total development cost. This prototype does not acquire work counters.

The feedback contains actual ratios to same-batch native and matched controls,
per-filter ratios, quality loss cases, stop counts and a paired group bootstrap
interval. These are adaptive screens on one allocation, **not** a guarantee about
future queries or uncertainty after selection. The controller never uses the old
latency estimator to rank candidates. A nominee requires zero development losses,
upper 95% ratio bounds below one against native and its matched control, and an
empty/native 90% interval inside [0.98, 1.02], retaining M5's screening rules. The
practical 5% reduction target is reported separately. Otherwise
the agent can revise within time/money or abstain. Independent frozen evaluation
is still required. Validation/test are never staged or exposed.

The host loop uses the existing durable `Budget` ledger and a reviewed provider
contract. There is no fixed model-request or total-candidate quota; dollars,
context capacity, native attempts and the one worker's deadlines bound the run.
The prepared packet proposes a separate $15 ceiling; preparation authorizes no
new spending and resets no previous charges. Unknown charges stop without retry.

## Preparing and launching

Run local commands from the workspace root with the existing agent environment:

```sh
agent/.venv/bin/python -B -m pytest agent/experiments/torch-live-feedback-v1/tests -q
agent/.venv/bin/ruff check agent/experiments/torch-live-feedback-v1
agent/.venv/bin/python -B agent/experiments/torch-live-feedback-v1/package.py \
  --output trials/fannagent-benchmark-evaluation-v1/reviews-small/torch-live-feedback-v1/kit
```

The kit inherits the verified site's account, `cs` partition, image and prepared
graph paths from M5. Torch's host Python must be 3.9+. The local authoring commands
use the existing Python 3.12 environment. Build tools and dependencies
must already exist in the pinned container; no network installer runs. On-node
availability is a pending qualification, not an assumed successful experiment.

Upload the kit archive and its checksum through your existing trusted route,
verify the checksum and extract into a **fresh** scratch directory. The SSH client
must already be authenticated through the site's normal MFA route, using a trusted
multiplexed connection if needed; these tools never disable host-key checking or
set up tunnels. `client.py` uses `BatchMode=yes` and stops if authentication expires.
Use `--ssh-control-path` with an authenticated control socket when the site's MFA
prevents fresh noninteractive SSH sessions. The concrete commands are in
`COMMANDS.txt`; an SSH connection is not a compute allocation.

On Torch, inside the extracted kit:

```sh
bash submit.sh --check      # Slurm test-only; does not allocate
bash submit.sh --submit     # Exactly one six-hour allocation
```

Check the recorded numeric `job-id` using `squeue`/`sacct`. Once running, inspect
the worker from the Mac, substituting the actual extracted stage path:

```sh
agent/.venv/bin/python -B agent/experiments/torch-live-feedback-v1/client.py \
  --host torch --stage /scratch/dar579/ACTUAL_KIT_DIRECTORY --output /tmp/live-receipts status
```

Before paying for a new model episode, prepare and review its exact first prompt,
tool definitions, provider destination, proposed cap and source/evidence bindings:

```sh
agent/.venv/bin/python -B agent/experiments/torch-live-feedback-v1/run_agent.py prepare \
  --host torch --stage /scratch/dar579/ACTUAL_KIT_DIRECTORY \
  --kit trials/fannagent-benchmark-evaluation-v1/reviews-small/torch-live-feedback-v1/kit \
  --output trials/fannagent-benchmark-evaluation-v1/reviews-small/torch-live-feedback-v1/agent-packet
```

After actual matched authorization, `run_agent.py run --output PACKET --approval
APPROVAL_JSON` rechecks the established provider's current official model/rates
before requesting generation. It sends only anonymous development examples,
model-authored rules and live development feedback to the existing Anthropic
provider. Never write an authorization record from a test or pending specification.

The first qualification uses `diagnostic-policies.json`, containing the same two
historical M5 nominees as researcher controls. It runs **inside the same six-hour
allocation**, counts toward its attempt/time budgets, and is not a new agent
discovery. The model runner requires its successful native result before paid
dispatch. Startup qualification establishes runtime and measurement completeness;
it does not establish timing precision or a policy win. No preliminary or
replacement allocation is submitted automatically.

## Recovery

If SSH fails after a request was sent, preserve its locally saved request ID and
use `client.py ... result --identity ID`. The result operation cannot create work.
Never repeat `evaluate`, delete `.submitted`, requeue, or reset elapsed time to
recover an unknown outcome. All raw records remain on scratch independently of
the client; completed jobs also attempt a checksummed return archive. Obtain final
`sacct` status before treating an entire job return as complete. Failed or partial
jobs are retained; they do not automatically receive a replacement allocation.

Native feedback qualification should confirm dynamic compilation, full quality,
schedule completeness and independently reconstructed measurements on Torch.
Local scripted tests establish the controller and usage boundaries, not native
availability, timing precision, or a useful-policy result.
