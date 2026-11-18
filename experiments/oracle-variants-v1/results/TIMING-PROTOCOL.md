# Oracle variant timing protocol

All choices and both complete feasible policies are frozen before timing. The
7,000-case acquisition is independently verified against the original canonical
prefix hashes, exact references and native outputs. The feasible policies are
fitted separately using all outcomes of their reported cohorts. The test policy
is also run on the rest of the workload; any transfer failures are retained and
excluded only from its explicitly test-cohort quality claim.

Eight persistent readers are pinned across four physical CPUs. Requests execute
serially. Eight rotations put every family on every reader once, yielding eight
measurements per case and family (448,000 timed searches). The family inventory
is native ef640, ideal hindsight, legal-action hindsight, full-workload feasible,
test-cohort feasible, each feasible policy forced to continue, and an empty
compiled policy. There are 56,000 fresh pre-timing quality searches and 4,480
warmups. Audit collection is disabled in all primary timing readers.

Query vector order is hash-seeded, with four vector orders mirrored in the
second half. Reader order varies with query position, filter and rotation and
is also mirrored. All case/family/reader cells, PIDs, CPU affinity, actual output
and construction/SQL timer components are retained. No answer is completed
using exact search. No noisy latency observation selects a hindsight stop.

Ideal and constrained per-case lookup RPCs occur outside the primary request
timer; their cost is separately retained. Feasible feature collection and rule
execution occur inside the actual compiled serving request. Full and test
policies are constant family bindings: neither query identity nor cohort role
is supplied to the compiled policy. Reference observations are used outside
the request only to audit native execution.

Report ratio of mean request latencies, equally weighted across six filtered
conditions as the primary summary and across all seven conditions separately.
Also report each condition. Bootstrap 20,000 samples of query vectors, retaining
all conditions, readers and paired families within each vector; seed 20261118.
Intervals are conditional on this allocation and the fixed hindsight policies.
They exclude allocation variability and policy-selection uncertainty.

The empty/native 90% interval must lie entirely in [0.98, 1.02] in every
condition to pass the timing-control diagnostic. Otherwise retain all results
as descriptive estimates and explicitly report inconclusive/outside-band
controls. No outlier removal, repeated allocation to obtain passing controls,
automatic retry, or requeue is permitted.

The new capture and timing comparison together have a six-hour allocated-time
cap, four physical CPUs and 48 GiB per allocation, and two million cumulative
reserved searches. Capture reservations, including unused slots, carry into the
timing ledger. Previously completed historical experiments are separate and
remain immutable. Actual allocation accounting is reported after completion.

These are measured hindsight headroom estimates. Earliest safe checkpoints do
not prove minimum wall time. Feasible search maximizes captured layer-0 work
saved within the unchanged DSL, using a bounded MILP with explicit incumbent
and dual bounds. A best-found feasible policy demonstrates attainability by
the agent's language; it does not certify the maximum latency savings in that
language or demonstrate that an agent can discover or generalize the policy.
