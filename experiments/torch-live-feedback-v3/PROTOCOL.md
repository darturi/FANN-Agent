# V3 agent discovery and frozen oracle comparison

The user requested migration of the agent controller to the broad v3 language,
an actual agent experiment, and comparison with the broad `oracle_feasible`.
The prior controller and sealed historical experiments remain unchanged. This
new controller defaults exclusively to ordinary `fannagent.broad-stop.v3` JSON.

Discovery uses all 450 development vectors / 3,150 filter cases, actual recorded
prefix labels, and all thirteen captured causal features. Development evidence
is anonymized before the agent sees it. The agent receives no oracle policies,
oracle fitter, protected outcomes, source query IDs, vectors or neighbor IDs.
The host has already seen the earlier oracle results; this is an agent transfer
evaluation after that research history, not a wholly untouched study design.

The agent may author Python discovery/fitting scripts in a local, pinned
container with NumPy and the standard library. Only the development workspace
is mounted; no network, credentials, oracle artifacts or host filesystem are
available. Each execution has 240 seconds, one CPU and 2 GiB. The research
process emits JSON; only the trusted compiler/VM runs policy logic in the
database. Language/resource bounds are exactly v3's existing bounds. Native
feature collection and VM work stay inside the serving timer.

One fresh $15 model ledger uses the established Anthropic Sonnet 5.5 model and
existing local credential route, after current official metadata/rate checks.
Anonymous development observations and measurements may be returned to that
provider. There is no fixed total request/candidate quota. There is no automatic
provider retry. Unknown charges stop for audit. The user's instruction to run
this experiment supplies authorization; its exact text is bound in the prepared
receipt rather than borrowing any old episode's authorization or charges.

Compute is one allocation, four physical CPUs, 48 GiB and at most six hours,
including builds, waiting and research during the allocation. Preserve the
existing idle/work/outer timeouts and no-requeue behavior. All ANN queries are
durably reserved in 32-query windows under 300,000 attempts, including unused
windows. Reserve 225,000 attempts for the final comparison before admitting
development batches. A batch is refused if its conservative worst case cannot
fit. Development admission ends at three allocated hours, reserving the later
part of the same allocation for the frozen comparison. All failed, cancelled,
refused and incomplete attempts remain recorded.
There are zero fresh exact searches. Exact references are offline scoring only.

An unpaid qualification batch first compiles a causal continue-only diagnostic
and checks one development query per condition. Discovery may submit up to three
policies per batch. Full development quality, compiled decisions and feature/
state/fuel audits are checked against reference replay; selected prefixes are
independently executed when no frozen output is known. Any candidate recall
loss rejects the batch before development timing. A fixed hash-selected
32-vector screen across all seven conditions bounds adaptive timing cost.
Candidate/matched continuation/native/empty families use four readers, with
every family measured once on every reader per case. All samples are retained.

The agent permanently freezes one measured zero-development-loss policy, or
abstains. A descriptive candidate may be frozen when controls fail, but strict
qualification is recorded separately: zero development loss, upper 95% ratio
below one against native and matched continuation, and every condition's empty
control 90% interval inside [0.98,1.02]. This explicit exploratory freeze does
not relax the old qualification criteria or declare a policy win. If the agent
abstains or finishes without submission, native continuation is the final agent
outcome; no researcher chooses a replacement after seeing protected results.

The host then evaluates that single frozen policy on both the 1,925-case test
subset and all 7,000 cases. No final feedback returns to the agent and there is
no revision after exposure. Six shared-baseline families are native, frozen
agent, saved broad full-fitted oracle, saved broad test-fitted oracle, empty v3
and native clone. Each has four timings per case, one on every reader, using
six rotations with mirrored query/reader order. This is 168,000 primary timings.
Full quality checks and actual compiled audits precede timing. A transfer recall
failure is retained and timed for diagnosis, never promoted as a preserving
policy. Oracle-test quality is required only on its intended test cohort.

Report all seven conditions and six filtered conditions, per-case native recall
losses, result-count reductions, means, savings and oracle gaps on each cohort.
Use 20,000 fixed-seed vector-cluster bootstrap draws for the final report, with
paired conditions/families retained. Strict control equivalence requires every
condition's empty and native-clone 90% intervals inside ±2%. Failed equivalence
makes latency descriptive. The intervals omit adaptive policy selection and
between-allocation variability; the full cohort also contains development data.
Oracle results remain hindsight fits on each reported cohort, while the agent
uses development outcomes only. The resulting gap combines discovery and transfer.
