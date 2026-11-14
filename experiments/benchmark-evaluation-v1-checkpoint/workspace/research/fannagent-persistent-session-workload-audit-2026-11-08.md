# FANNAgent persistent session workload audit

November 8, 2026

**The saved Reviews evidence supports a controlled batch benchmark. It does not establish persistent reuse in the intended workload.** The study design is held pending evidence of how many distinct requests actually share one policy activation and reader binding. [Policy evaluation decision](fannagent-policy-evaluation-decision-memo-2026-11-08.md) · [Roadmap and P8](fannagent-performance-research-roadmap-2026-10-22.md#p8--independently-confirm-a-selected-policy-and-assess-transfer)

## Saved workload and execution evidence

| Evidence | What it establishes |
| --- | --- |
| Sealed selective pilot development inventory | 600 query cases, with 200 distinct vectors under each of three conditions. The rows contain query, group and role fields. They carry no request order, arrival time or policy-session boundary from an application. |
| Selective pilot timing and frozen execution | 14,400 timed policy sessions across eight arms and three blocks. Each session has one activation pair, one discarded warmup pair and three retained reuse pairs, all on the same query. The loop evicts installed policy state and clears the preparation cache before the next timed session. |
| Mini-bench Reviews sweep and MoReVec workflow | The saved sweep schedules 600 queries and the mini-bench runner uses one connection with a seeded shuffle per pass. This is a deliberately constructed benchmark schedule. MoReVec groups are used for sampling and split assignment. |
| FANNAgent application session API | The client opens a session on an evaluated copy, checks acceptance or deployment compatibility, and can install once on a connection. The API establishes feasibility of reuse. |

The development inventory hash matched its sealed manifest. All six retained and warmup timing files matched their block locks and the pinned pilot report. The counted **43,200 retained reuse pairs** came from one distinct query per timed policy session. I found no saved Reviews application trace or intended batch manifest with request order and the lifetime of the installed policy. A physical connection used across a benchmark pass does not establish that lifetime. [Pilot execution loop](../agent/experiments/selective-agent-v1/execution.py#L90) · [Pilot verification](../agent/docs/verification/selective-agent-v1-pilot-postrun.json) · [Reviews sweep plan](../mini-bench/results/reviews-hnsw/sweep/sweep-plan.json) · [Mini-bench runner contract](../mini-bench/README.md#measure-and-compare) · [MoReVec workflow](../harness/docs/morevec-workflow.md) · [Application session API](../agent/src/fannagent/client.py#L8)

## Evidence needed to reopen

A saved development-only trace of representative sessions, or a manifest for an actual intended batch job, would resolve the gate. It should record an opaque activation or session ID, request order, a query fingerprint, filter stratum and `k`, and when a reader reconnect, policy change or reset requires another activation. Include short sessions and all three filter strata. Vectors and search outcomes are unnecessary for this workload check. Compare the resulting distinct-query counts and predicate mix with the rough six-query break-even from the repeated-query pilot before freezing a design. [Pilot timing report](../trials/torch-reviews-selective-agent-v1/runs/20261022T192817Z-66ed81d6/measurements/pilot/report.txt)

Any subsequent study keeps complete valid top-10 results, native mean recall of at least 95% in each filter, and the same lower 95% policy-minus-native recall bounds overall and per filter. The development reserve stays at −0.25 percentage points and the independent gate at −0.50. Session timing would be a separate prospective objective with setup and first use charged. A3 stays on hold and Torch stayed idle. No new searches, fits or provider calls ran. Holdout query files and results were left unopened, and confirmation entitlements stayed untouched. [Selective evaluation contract](../agent/experiments/selective-agent-v1/README.md#fixed-final-gates)
