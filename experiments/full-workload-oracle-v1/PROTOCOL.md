# Full-workload and held-out hindsight stopping oracle

The user explicitly requested both the frozen 275-vector held-out test split
(1,925 cases) and the complete 1,000-vector workload (7,000 cases), including all
six filters and the unfiltered condition. One acquisition over the complete
workload supplies two separately reported cohorts. The held-out cohort is a
subset, not an independent replication of the full-workload result.

Use the preserved 247,286-row, 768-dimensional cosine HNSW graph, k=10,
ef_search=640, iterative scanning off, and its actual raw outputs. Exact search
is solely an offline scoring reference. Missing neighbors remain misses.

For every query/filter case, capture the native trajectory and actually execute
every reached checkpoint in increasing ordinal order until a valid answer
preserves both native Recall@10 and native result count. Ordinary full native
answers therefore require ten results; native short answers require at least
their original count. If no checkpoint qualifies, continue native search. Verify
every measured prefix against its canonical trajectory. Do not infer monotonic
recall, skip earlier checkpoints, interpolate labels, or change recall targets.
The native checkpoint recurrence tests after an expanded neighborhood reaches
the next multiple-of-64 layer-0 distance target; it can overshoot. This is an
exhaustive oracle over those existing boundaries, not arbitrary instruction
boundaries. A 4,096-checkpoint or 2,000,000-attempt ceiling fails closed and leaves
an incomplete result rather than silently returning a sparse oracle.

Freeze choices before timing. Replay them using a minimal copied native module:
arm10 counts checkpoints and stops at the chosen ordinal, with no feature
collection, classifier, exact lookup or answer replacement. Arm11 counts through
the same ordinal and continues. Also measure raw native and the existing empty
program. A zero target continues normally. The oracle's per-query choice is set
outside the primary request timer: its prediction is hypothetical and free.
Record that routing time separately. Actual acquisition and setup costs are not
serving savings. Preserve source/module identities and qualify all replayed
answers against executed stopped outputs before timing.

Measure SQL construction, dispatch, execution, fetch and result decoding on four
persistent readers. Each reader runs each family in four cyclic rotations and
their reverse, using mirrored group and within-query reader orders. Every case
has eight observations per family across four reader/CPU roles and two cycles:
224,000 total timed requests and 2,240 warmups. Warmups use the same scheduled
cohort but never select or alter oracle decisions. Record setup, binding, PID,
CPU affinity, cycle, rotation, predecessor order, all outputs and timings.
No outlier deletion, timing-minimum selection or automatic rerun is allowed.

Report native/oracle mean milliseconds, percent reduction, stop fraction, recall,
result completeness and checkpoint distribution for the full workload and the
held-out subset. Report each of seven conditions, equal weighting across six
scalar filters, and equal weighting across all seven. Use paired vector-group
bootstrap intervals retaining all filter/reader/cycle/family pairings; intervals
are conditional on one allocation. Report reader/CPU/cycle consistency and
empty/native controls, including 90% ratio intervals against the existing
[0.98,1.02] diagnostic band. A failed control makes affected performance contrasts
inconclusive; it does not justify deleting rows or automatically repeating work.

This is a measured, optimistic hindsight reference for checkpoint stopping under
native quality, not a mathematical upper bound over other algorithms, indexes,
quality objectives, or noisy per-query latency minima. The earliest qualifying
checkpoint minimizes the stopping ordinal, not necessarily measured wall time.
No deployability or learned-policy success claim follows.

This explicitly authorized diagnostic exposes test and validation outcomes.
Keep all oracle labels and selections in this evaluator-only experiment and
record the exposure before the first query. Never feed them to the agent or
treat a policy tuned after exposure as an untouched confirmatory test. Existing
splits, policies, reports and selection records remain immutable.

One separate Torch allocation, four physical CPUs, 48GiB, at most six hours,
no automatic retry or requeue, no provider calls. Independent attempt
reservation precedes every query. Preserve failed/partial results. Verify the
runtime image, source capsule, graph before/after, module, all raw hashes,
schedule and scheduler completion locally before accepting the result.
