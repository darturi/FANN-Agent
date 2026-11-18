# Prospective uniform timing reduction

The source acquisition has frozen all 7,000 choices. Jobs 23544718 and 23558871
were stopped through their cleanup handlers before any primary timing or warmup.
All raw archives, failed scheduler states, and handoff records are retained.

Fresh validation request throughput on the second allocation showed that the
original eight-repetition schedule would exceed the remaining six-hour aggregate
allocation budget. Before any primary latency observations, reduce every case
and family uniformly to four repetitions: one complete cycle of four reader and
CPU rotations, with the original seeded query and reader orders for that cycle.
All seven conditions and both requested cohorts remain. There is no case,
checkpoint, family, or measured-latency-based selection. The four families are
native, hindsight oracle, matched continue, and empty control.

The new allocation measures 112,000 requests and 1,120 warmups. It restores the
same graph and uses the same binary, query, timer and free-choice boundary.
Every warmup and timed answer must match the frozen source output. This covers
every case and family on the fresh graph. No separate additional 28,000-query
qualification pass is performed. No exact serving calls or new exact references.

Statistics use the same vector-group bootstrap and control criteria. The cycle
axis has length one; allocation variability remains unmeasured. Four repetitions
provide less precision and drift protection than the original two mirrored
cycles. Failed or inconclusive controls still make the estimates descriptive.

The two earlier allocations used 13,194 + 4,055 = 17,249 seconds. The final
allocation is limited to 4,200 seconds (four CPUs, 48GiB); the aggregate maximum
is 21,449 seconds, below six hours. No retry or requeue of the timing allocation.
The complete earlier reserved high-water mark is carried forward, including all
unused slots and unobserved interrupted operations. Fresh reservations still
precede execution and the cumulative cap remains two million.

The operational validation timings are retained as operational evidence only;
they do not select checkpoints or enter the primary latency estimates. The
held-out outcomes remain exposed for this evaluator-only diagnostic.
