# FANNAgent controlled Reviews batch workload

November 8, 2026

This benchmark asks whether one policy activation can pay for itself over **ten sequential queries with ten distinct vectors** on the retained Reviews index. Ten requests is a fixed design choice for this controlled benchmark. It gives each of the three filters three or four requests per session and yields 20 groups of disjoint vectors for timing analysis. The earlier audit did not establish an application session length. [Workload audit](fannagent-persistent-session-workload-audit-2026-11-08.md)

## Inputs and order

Use only the sealed selective pilot development inventory. It contains 200 exposed vectors and 600 `k=10` cases, with unfiltered, `votes32`, and `votes108` variants for each vector. The native reference is the original full-graph path at `ef_search=640`. The session manifest records development query IDs and hashes. It omits vector values and outcomes. [Development coverage audit](fannagent-p3a-evidence-audit-2026-10-24.md) · [Session manifest](fannagent-controlled-reviews-batch-manifest-2026-11-08.json)

Order the source vector-group IDs by SHA-256 of the UTF-8 string `reviews-persistent-batch.v1:20261019:<group_id>`, breaking ties by group ID. Split into 20 consecutive groups of ten vectors. For each group, use the same ten-vector order in three sessions. In session rotation `r = 0, 1, 2`, assign the request at zero-based position `i` to filter `(i + r) mod 3` in the order unfiltered, `votes32`, `votes108`. Emit groups in hash order and rotations in numeric order. Each vector appears once per session and once under every filter across its three sessions. Each filter appears at every request position once per group. Keep the three sessions together for any later session-timing uncertainty analysis. Keep a vector's three filter results together for the existing recall analysis.

The request fingerprint is SHA-256 over the query object without `id`, encoded as sorted, compact ASCII JSON. The vector fingerprint is SHA-256 over its little-endian binary32 components. The manifest binds the source file and package manifest by SHA-256.

## Session boundary and accounting

Start one fresh bound reader and one logical policy session per batch. Run the ten requests serially on that reader in manifest order. Charge admission once and charge policy installation on the first eligible request, even if the batch opens with a native bypass. Preserve the installation across later requests and close the reader after the tenth. A future native comparison uses the same ordered requests and reader lifecycle on a separate reader. Account for reader acquisition, all query work and close within the session endpoint. Report first-request and first-eligible latency separately. A reset, failure or policy change inside a batch invalidates it under the prospective protocol and retains its charges. [Frozen selective session behavior](../agent/experiments/selective-agent-v1/execution.py#L19)

## Dry run acceptance

Verify exact development coverage, unique vectors within each session, all three filter variants per vector, per-position filter balance, contiguous request order, and balanced reader open and close counts. Model the existing `cons-bypass108` seed only as a credited routing comparator. Route from the actual predicate and `k`. Check that `votes108` never installs the policy and that the first eligible request installs exactly once per session. The dry run reads saved inputs and makes no backend, search, fit or provider calls.

A later development study would preserve valid complete top-10, at least 95% native mean recall per filter, and the −0.25 percentage-point development recall reserve overall and per filter. Independent confirmation keeps the −0.50 percentage-point lower-bound gate under a valid separately reconciled entitlement. This workload definition releases no run. A3 stays on hold and the holdouts are excluded. [Selective evaluation contract](../agent/experiments/selective-agent-v1/README.md#fixed-final-gates)
