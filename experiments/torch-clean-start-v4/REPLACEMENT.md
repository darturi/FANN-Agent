# Declined clean-start replacement

Status: **user declined on November 19, 2026; do not launch**.

The replacement remains unstarted. No authorization or second paid episode was
created. The proposal below is retained as an audit record.

The user requested “one clean-start Opus 5.5 experiment.” That episode started
from a verified empty workspace, then failed before candidate evaluation when
Torch returned `ESTALE` reading an atomically replaced heartbeat file. Its 16
model calls, $1.228968, 518 ANN/exact attempts, 203 observations and closed native
fallback are preserved. There is no learned policy or latency comparison from it.
The closed conversation will not be resumed.

## Repair and qualification

- Source commit: `a1fe405`.
- Native correctness, sandbox isolation and original-graph timing controls passed.
  Clone/empty overall ratios were 0.99954 and 1.00023; all condition-level
  equivalence gates passed under the fixed 4 GiB resident-index configuration.
- Control reads now reopen after bounded `ESTALE` failures. Provider calls,
  native operations and uncertain deliveries are never retried.
- Heartbeats are read once per loop; persistent failures are recorded as worker
  errors instead of deadlines.
- 91 regression checks passed. A cross-node test completed 5,000 control reads
  during atomic replacements, recovering **nine real stale handles** and three
  injected faults. It made zero ANN/exact or provider calls.

## Proposed single replacement

| Item | Bound |
|---|---:|
| Model | `claude-opus-5-5`, adaptive/high |
| Additional paid episodes | 1 |
| Remaining shared model accounting | $13.771032 |
| Remaining ANN/exact attempts, including final comparison | 244,350 |
| Of those reserved for final comparison | 195,000 |
| Proposed new allocation | 4h30m, four CPUs, 16 GiB |
| Worker wall/discovery clocks | 16,000 / 8,800 seconds |

The overall limits remain $15, 300,000 ANN/exact attempts and six cumulative
allocated hours. Already charged: $1.228968, 55,650 queries and 4,891 allocated
seconds. The failed allocation has ended. A new 16,200-second allocation would
bring cumulative allocated time to at most 21,091 seconds, below 21,600.

Prepared UUID: `c3735ec6f1b14fbabfde895c0d9892d4`.
Prepared archive SHA-256:
`30e0b6931b3b53a63f5dea1f679ed57f5d5d9d11bc8a4f966cd0aad831a9577f`.
Its initial evidence journal, policy/scratch directories and model history are
empty. No authorization, worker or model has been started. It contains static
task inputs and generic software only; no failed-episode or qualification
observations, fitted artifacts, thresholds or conversations are imported.

Only after model closure and policy freeze will the two existing feasible
oracles be read and attached for one final comparison on all 1,925 held-out and
7,000 full-workload cases. The same global agent policy is used on both cohorts.
The final report runs in the already pinned Apptainer runtime to supply NumPy,
which is absent from Torch's bare host interpreter; that reporting step performs
no new native queries or model calls.

Raw prepared package and verification receipts:
`trials/fannagent-benchmark-evaluation-v1/reviews-small/torch-clean-start-v4/replacement-prepared-v1/`.
