# M5: frozen development nominee qualification and serving timing

Prepared 2026-11-16 from pre-M5 commit `bdbcab4`. This is one prospective
development allocation. It does not select a final policy or open a held-out split.

## Inputs and scope

Use only the frozen 450 development vector groups, 3,150 query/filter cases,
768-dimensional cosine graph with 247,286 rows, k=10, ef_search=640,
iterative_scan=off. Split digest:
`d48d341f3252e24c7eadf5b13e81b66063b25a0dff2d6b6ddd72cb4af418eec0`.
All six scalar thresholds (743, 527, 310, 192, 108, 32) and unfiltered queries
remain in quality, timing and work measurements. No validation/test inputs or
outcomes are staged. Corpus votes/IDs are used for eligibility verification.

The M4 submitted-nominee digest is
`48bf2eca1a66950a68701cd89cd646daa499f9243223a6b9301ea7f2d9befef1`.
Candidate7 and candidate8 are compiled without changing their rules. Both test
frontier_gap and tenth_distance at checkpoint64 on unfiltered/votes32 only:
candidate7 uses gap>=0.10 and distance<=0.34; candidate8 uses gap>=0.12 and
distance<=0.33. Other conditions continue without collecting policy features.
No turnover dependency or checkpoint16/32 observation is introduced.

The qualified M1 runtime profile is unchanged. Copies of its timing and observer
engines differ from their M1 sources only in `src/compiled_v2.inc`. Build with
the pinned amd64 image and `OPTFLAGS=`; retain its PG_CONFIG. The existing
separate observer hooks are unchanged. Preserve all earlier sealed inputs.

## Six comparison families

One timing group, in frozen rotation order:
native640, candidate7, candidate8, matched7, matched8, empty.

Native uses the normal engine path. Each matched control has the candidate's
identical policy, masks and Boolean evaluations, with only the compiler's
force-continue flag set. Empty is an attached v2 program with no rules or
observations. Its purpose is to diagnose dispatch/process effects separately.
Matched controls are researcher comparators, not agent submissions.

## Scoring and quality gate

Exact searches run in dedicated offline sessions, with sequential-scan plans
saved and exact readers closed before any approximate measurement. Fresh truth
must match frozen development references. Repeat this independently under each
module. These 6,300 exact queries never enter serving, output completion or
primary timing. Approximate requests have no fallback, completion guard or
exact repair. A short output is scored normally, with missing neighbors counted
as misses. Keep native's raw recall, including low-recall cases; there is no
absolute 95% recall eligibility floor.

Before timing, qualify all 18,900 family/case results. Bridge native output
before and after role changes to verified M1. Recapture canonical observations
and force all 9,436 reached prefixes (including 1,496 partials) to their actual
0..10 outputs; compare outputs and recall to M1. Validate each compiled audit
frame, nullable feature, mask, first decision and actual prefix output against
the independent Python evaluator. Continue/empty outputs must equal native.
Candidate stop inventories must reproduce bound evidence: candidate7 stops on
135 unfiltered and 41 votes32 cases; candidate8 on 102 and 22, respectively;
all other conditions have zero stops. Require zero per-case recall losses
against raw native for both candidates and controls. Write complete quality
rows and gate counts before rejecting. A failed gate cannot authorize a retry,
threshold repair, extra generation, timing promotion or held-out access.

## Counterbalanced full-request timing

Use the uninstrumented module only. Four persistent reader PIDs per filter
remain pinned one each to the four allocated physical cores. Six cyclic role
rotations followed by the reversed six rotations give each PID every family
twice. Each query/family has eight timed observations: four readers by two
cycles. Rotate the reader-to-CPU mapping by filter. Save assignments, CPU masks,
PIDs, role/block/cycle/rotation and predecessor/order for independent rebuilding.

Within each rotation use the frozen hashed vector-group order, reversed in
cycle2. Interleave each query's four readers with mirrored Williams orders.
Warm each reader on the first ten ordered cases after binding a role.
SQL construction plus execution, fetch and output decoding are the primary
request timer. Audit and work counters are disabled. Validation/serialization
of the record occurs outside that timer. Save all timings, including unfavorable
ones; no trimming, timeout omission or outlier deletion. Graph data are restored
privately and verified before/after. Setup, membership map construction,
connection, binding, warmup and transaction lifecycle costs are saved separately.
This measures repeated warm serving, not cold start or concurrent throughput.

## Separate work phase

After timing succeeds, stop and verify its private graph and release only its
owned stopped copy. Restore a second private copy with the observer module.
Score fresh offline truth, then run all six families on all 3,150 cases.
Record vector calls, lower/upper neighbor scores, queue pops, adjacencies,
feature passes and membership probes. Kernel start/end CPU and backend PID
must match the pinned reader. Validate output/checkpoint/recall parity to timing
qualification. Native graph counters must match verified M0, and every
continue-only control must have identical graph work to native. Feature-pass
counts must match requested audit masks. Instrumented durations never enter
the latency comparison; work savings cannot stand in for a latency gain.

## Ledger and resource ceilings

| Operation | Timing module | Work module |
|---|---:|---:|
| Offline exact references | 3,150 | 3,150 |
| Canonical captures | 3,150 | 0 |
| Actual forced prefixes | 9,436 | 0 |
| Native before/after bridges | 6,300 | 0 |
| Other-family quality | 15,750 | 0 |
| Warmup approximate | 3,360 | 0 |
| Timed approximate | 151,200 | 0 |
| Instrumented approximate | 0 | 18,900 |
| Total | 192,346 | 22,050 |

Total214,396. Reserve attempts before each query, including failures; timing cap
200,000, work cap25,000, combined cap225,000. No automatic retries/requeue.
Four physical CPUs, 48GiB, six-hour wall limit; timing watchdog15,300 seconds,
work watchdog4,500 seconds, leaving 30 minutes for outer staging/archive costs.
One allocation only. Full native startup/backend import checks under both
modules must pass before sbatch; loader-only emulation is local readiness only.
Failure archives preserve partial records and host exit status. Independently
obtain sacct COMPLETED/0:0 before accepting a successful return.

## Analysis and next-stage interpretation

Primary: equal-weight mean complete-request latency over the six scalar filters.
Unfiltered is secondary, reported alongside every individual filter. Compute
candidate/native and candidate/its-matched-control ratios directly from paired
data. Report paired 95% intervals, per-filter means/ratios, reader, physical CPU
and cycle consistency, stop counts, quality and graph-work changes. Never
subtract an unmatched control gap or silently average away a filter regression.

Use 20,000 exposed-vector-group bootstrap draws (seed20261116), preserving all
filter/reader/cycle/family pairings. These intervals are conditional on this one
allocation and reused development groups. They do not quantify allocation
variability, selection effects or held-out generalization. Empty/native is a
prospective diagnostic: a paired 90% interval wholly within [0.98,1.02] supports
equivalence within2%; otherwise mark the diagnostic inconclusive/outside band,
retain all rows and do not automatically repeat. It is not proof of correctness
or an adjustment to candidate times.

Only a candidate with preserved quality, upper95% ratio bounds below1 against
both native and its matched control, and the empty/native diagnostic satisfied
gets an automated label of a development signal for independent confirmation.
This descriptive screening label is not a multiple-comparison-adjusted or final
performance claim. Otherwise report that a credible net development benefit
was not established. Native remains admissible; no forced winner. Candidate7's
and candidate8's proxy gains were below0.5%, so inconclusive or negative live
results are plausible. Review per-filter and CPU/cycle behavior and qualify the
independent allocation procedure before any separately authorized held-out step.
Do not run additional model requests or change thresholds in M5.
