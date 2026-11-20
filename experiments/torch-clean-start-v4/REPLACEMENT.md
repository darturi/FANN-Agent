# Approved clean-start replacement

Status: **approved November 19; completed November 20, 2026 with voluntary
abstention**. Job 23800555 ended successfully; the native comparison and cleanup
completed. [Results and accounting](results/comparison-v1/REPORT.md).

The user corrected the earlier decline: “Sorry what I meant to say is do run
replacement.” This supersedes the decline. A fresh empty workspace is authorized
under the bounds below; the failed conversation and observations are not resumed.

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

## Authorized single replacement

| Item | Bound |
|---|---:|
| Model | `claude-opus-5-5`, adaptive/high |
| Additional paid episodes | 1 |
| Remaining shared model accounting | $13.771032 |
| Remaining ANN/exact attempts, including final comparison | 244,350 |
| Of those reserved for final comparison | 195,000 |
| Allocation ceiling | 4h30m, four CPUs, 16 GiB |
| Worker wall/discovery clocks | 16,000 / 8,800 seconds |

The overall limits remain $15, 300,000 ANN/exact attempts and six cumulative
allocated hours. Already charged: $1.228968, 55,650 queries and 4,891 allocated
seconds before replacement. Its allocation consumed 7,328 seconds, bringing
cumulative allocated time to 12,219 seconds, below 21,600. Total queries were
255,134 and model accounting $11.616176. All requests settled.

Prepared UUID: `c3735ec6f1b14fbabfde895c0d9892d4`.
Prepared archive SHA-256:
`30e0b6931b3b53a63f5dea1f679ed57f5d5d9d11bc8a4f966cd0aad831a9577f`.
At preparation its evidence journal, policy/scratch directories and model history
were empty, with no authorization, worker or model started. The approved package
was subsequently bound to job 23800555 and verified empty before model start.
It contained static task inputs and generic software only; no failed-episode or
qualification observations, fitted artifacts, thresholds or conversations were
imported. The authorized initial archive SHA-256 is
`016b1db414aae628704f1aa8e560eef40ebfdb72e8dc8461a3845418ed44b637`.

Only after verified model closure and policy freeze were the two existing feasible
oracles read and attached for one final comparison on all 1,925 held-out and
7,000 full-workload cases. The same global native-outcome artifact was used on
both cohorts. Opus evaluated two unsafe candidates and voluntarily abstained;
no full confirmation was attempted. Operational agent savings are 0%; the unchanged
oracles saved 67.67% / 68.03%. Final timing controls passed, but the full oracle
has three count losses and is not a strict-quality comparator.

The final report ran in the already pinned Apptainer runtime to supply NumPy,
which is absent from Torch's bare host interpreter; that reporting step performs
no new native queries or model calls. The acquisition-helper defect discovered
in this episode was fixed only after model closure; executed source remained
`a1fe405`. The report documents the affected observations and future fix.

Raw prepared package and verification receipts:
`trials/fannagent-benchmark-evaluation-v1/reviews-small/torch-clean-start-v4/replacement-prepared-v1/`.
