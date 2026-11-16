# M1 original-graph v2 runtime, prefix-label and serving-cost qualification

Prepared November16,2026 after verified M0 job23303080. This is one development-only allocation,
with four physical CPUs,48GiB and an eight-hour hard limit. The exact workload is984,396 ANN/exact
attempts under a1,000,000 global ceiling. No automatic retry/requeue. Preserve failed/partial
returns. No new model request, policy selection, validation or test is authorized by this kit.

## Fixed inputs and semantics

Use all450 frozen exposed development vectors and all six scalar predicates plus unfiltered,
the original247,286-row full graph,768-dimensional cosine vectors, k10 and ef_search640 with
iterative_scan off. Keep the existing split, graph/data hashes, source-ID mapping, frozen exact
truth tolerance and zero serving-exact calls. Absolute95% recall is diagnostic only. A short
answer remains short; missing neighbors reduce recall. Empty eligible populations score one
only for empty output. Exact sequential queries are offline scoring only; their connections
must close before approximate qualification/timing. No serving guard or exact repair exists.

The runtime profile remains `filtered-ann-partial-checkpoints/v2`, with predicate/checkpoint masks
derived by the compiler. Rules see qualifying count, tenth distance, frontier gap and top-ten
turnover only. Missing values make their comparisons false. A predicate with no rule has no
observation pass. Turnover needs current and preceding scheduled top tens (32 before64), not
the last checkpoint that happened to be collected. Stops return actual0..10 SQL results.
The prototype C implementation is unchanged; this kit expands its compiled qualification pool.
Old arms retain their semantics. Historical rules are transfer/engineering ablations, not fresh
agent output. Researcher fixed-prefix and feature probes may lose recall: record those losses,
never suppress their rows, but require correct first-stop/features/actual-output/scoring behavior.

## Pool and qualification

Twenty-one v2 bindings: three unchanged historical transfer policies and their matched continue
controls; count-stop16/32/64; empty/native bypass; turnover64 dependency, count-based partial
condition and distance-only probes; all-checkpoint count/ranked/turnover/decision-only/four-compare
continue probes; and bare unconditional stop16/32/64. Include native640 and four legacy arms
(continue and the three policies), for26 quality/work families. No fitting or new thresholds.

On the timing module, independently compute3,150 fresh offline exact references; qualify native
before and after role changes for every query; capture the canonical observations; force each
reached prefix using its actual causal budget; and qualify every compiled/legacy family. Compare
native/canonical/legacy/transfer outputs and observations with the frozen development evidence.
Reconstruct actual labels for all9,436 reached prefixes, including1,496 partial prefixes missing
from the current library. Never infer those outputs/recalls from count or distance features.

V2 audit frames check every requested mask, nullable value, first decision and dependency state
against the canonical capture. No-observation paths have no heap passes. Native after changing
roles must agree with native before. Audit/trace is disabled for all serving-cost measurements.
Timing validation/logging and setup happen outside the request timer.

## Resource-feasible reader/CPU timing design

There are six prospectively fixed blocks of families, each containing its own native anchor:

1. Native, legacy Conservative, v2 Conservative, matched Conservative, empty bypass.
2. Native, legacy Moderate, v2 Moderate, matched Moderate, empty bypass.
3. Native, legacy Broad, v2 Broad, matched Broad, empty bypass.
4. Native, decision-only continue, count continue, ranked continue, turnover continue,
   four-comparison continue.
5. Native, count-stop16, bare-stop16, count-stop32, bare-stop32.
6. Native, count-stop64, bare-stop64, legacy continue, empty bypass.

For each condition/block open four persistent reader PIDs, pinned one per allocated physical
CPU. Maximum live readers plus keeper is five, below the qualified32-connection setting.
For K families rotate `family[(reader+rotation)%K]` through K rotations, then reverse the
rotations in a second cycle. Every actual PID runs every role twice; every query/role sees each
CPU once per cycle, giving eight observations per query/role/block. A rotation can omit families;
balance is over the complete fixed crossover, not within one rotation.

Hash vector-group IDs with seed `reviews-protocol-v2-M1-20261116`, block and rotation to order
queries; reverse the matched order in cycle two. Use four-reader Williams base[0,1,3,2], rotate
by query position/rotation/filter/block, and reverse matched rows in cycle two. Record PID,
singleton affinity before/after rotations, CPU, order and predecessor. Use ten fixed development
warmups per reader/rotation, mirrored reader order. New read-only transactions import the
keeper snapshot between roles. Measure bind/open/warmup/close and membership-map setup separately.

The31 family appearances across blocks give781,200 measured full requests and17,360 warmups.
Compare each family to its SAME-block native and applicable matched continue control, paired by
vector/filter/PID/cycle. Repeated native/empty anchors remain identified by block; do not silently
pool their costs or subtract cross-block/historical gaps to manufacture a result. Report all six
scalar filters with equal weight; unfiltered is secondary. No unfavorable filter/reader is dropped.

## Separate work and native bridge

After the timing restore is stopped and index integrity verified, restore another private copy
of the same graph. Use a separately compiled observer module: existing M0 counter hooks only,
no graph/search/stop changes. Fresh3,150 offline exact references precede81,900 instrumented
requests (26 families per query). Their times are audit data, never primary serving costs.

Read counters and direct-kernel start/end CPU samples outside each search. Reuse one pinned
backend per condition across isolated role transactions. Outputs/first stops/recall must match
the uninstrumented quality cache. Native graph counters must match verified M0 native records.
All continue-only variants must have identical measured graph-work counts to native; compatible
legacy/v2 policies and count/bare forced prefixes must have the same graph counts. Feature-pass
counts must match compiled masks; native, empty and decision-only paths must have zero heap
feature/membership work. Instrumentation times cannot be substituted for primary timings.

## Ledger and time bounds

| Phase/category | Attempts |
| --- | ---: |
| Timing offline references | 3,150 |
| Canonical captures | 3,150 |
| Actual forced-prefix captures | 9,436 |
| Native before/after role changes | 6,300 |
| Other quality families | 78,750 |
| Warmups | 17,360 |
| Primary measured requests | 781,200 |
| **Timing phase total** | **899,346** |
| Work offline references | 3,150 |
| Separate work requests | 81,900 |
| **Work phase total** | **85,050** |
| **Overall** | **984,396** |

Timing cap920,000, work cap90,000 and combined cap1,000,000. Timing watchdog6h15m, work watchdog
1h15m leave30minutes for staging/compression within Slurm8h. SQL setup/metadata/EXPLAIN/audit
control calls are not ANN/exact search attempts and are kept outside serving timers. Both phases
verify original inputs, prepared graph, private restore/index integrity, cleanup and cgroup
memory events. Delete only the first stopped, integrity-verified, owned private restore to make
room for the second; retain all failure artifacts.

## Analysis, evidence and dispositions

The return verifier must reconstruct every identity, label, audit frame, schedule/order, reader/
CPU assignment, actual output, timer component, native work bridge and attempt. Raw-file hashes,
module/profile/source/plan pins and user-provided independent sacct COMPLETED0:0 are additional
gates. A failure is retained, not automatically replaced or mislabeled as successful qualification.

For complete serving costs use20,000 exposed-vector group bootstrap draws, seed20261116, retaining
paired filter/block/reader/cycle/family observations. Report per-filter, CPU/reader and cycle
behavior and same-block native/matched-control contrasts. This is one allocation, not final
allocation-level or held-out inference. Timing improvement is not required for a valid negative
qualification/cost result. No policy is promoted or selected by M1.

Physical-CPU summaries follow the recorded CPU assignment across all six scalar filters; reader
slot summaries are separate because slot-to-CPU mapping changes by filter/block. Deployment v2
adds these explicit physical-CPU summaries before dispatch. The undispatched v1 seal is preserved;
runtime modules, programs, workload, statistical method and resource ceilings are unchanged.

The feature calibration block reports paired COMPLETE-plan differences: decision minus native,
count minus decision, ranked minus count, turnover minus ranked, and four-comparison minus
turnover. These include code/availability/short-circuit/cache effects. Keep negative/noisy
differences and their uncertainty. They are not isolated pure-operation timings or an automatic
additive model. The actual compiled request costs and prefix library support subsequent M2 cost
binding; they do not prove an unmeasured new program's latency. M2 must explicitly validate any
surrogate and its uncertainty before generation. Later M5 must measure actual finalists.

Export anonymous development groups (ascending source-index ordinals)/folds, raw-native labels,
complete full-precision causal
observations and ACTUAL prefix labels. No query IDs/folds/truth/costs become runtime features.
The export remains cost-unqualified until M2 binds the model; no hidden optimizer or automatic
provider call is included. Preserve native/legacy/engineering/agent credit separately. Validation
and test remain unopened. Any post-freeze code/design amendment needs a new sealed version.

## Startup and delivery

Require full native frozen-package/backend/runner/module preflight under BOTH modules before
sbatch. Local Mac x86 emulation may exercise loader-only checks separately; that option is never
used by the Torch submission script. The previous reserved-module collision is prevented by
unique `m1_*` names and no general-agent/provider import before the pinned loader.

The kit includes archive/checksum, immutable input/engine source pins, local semantic/CPU smoke
and verifier/corruption receipts, native preflight, one-shot submission and failure-preserving
return scripts, independent verifier/analysis and upload/progress/download commands. It does
not require another model authorization to execute this qualification, and does not itself
authorize the later proposed six-request/$15 agent episode.
