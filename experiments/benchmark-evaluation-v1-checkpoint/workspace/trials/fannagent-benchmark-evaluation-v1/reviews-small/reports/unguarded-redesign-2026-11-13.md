# Redesign: actual approximate answers, exact search only for scoring

The user authorized removal of the completion guard from both native and agent serving. The primary question is now relative recall preservation and unguarded response latency. Exact sequential search remains an offline evaluator; it does not complete, replace or otherwise influence a query's answer. All six scalar predicates, the unfiltered control,450/150/275/125 grouped split, original graph/data/metric,k=10 and policy feature/checkpoint semantics remain unchanged. Validation/test outcomes are unopened.

## Scientific changes

A native answer with seven correct top-ten neighbors has recall.7 even though only seven results are returned. The denominator is min(10,eligible_count), not returned_count; missing results count as misses. Short valid outputs are ordinary scientific outcomes. Duplicate, ineligible, oversized, nonfinite or malformed answers remain integrity errors.

The zero-observed-query-recall-loss requirement remains relative to ACTUAL unguarded native640. The95% absolute recall floor is now a reported application-quality diagnostic, not an eligibility gate on native/agent and not a prerequisite that triggers repair. Both relative preservation and absolute recall must be reported. Preserving53% recall does not mean meeting a95%-quality application target. The5% practical latency target, independent timing controls, grouped inference and one bounded validation selection remain unchanged.

The earlier guarded studies remain valid hybrid-system results and are preserved. Their18.87ms/19.27ms baselines and3.19% agent effect cannot be transferred into an unguarded latency claim or repaired by subtracting fallback time. Fresh complete unguarded measurements are required. Historical/fixed/turnover comparators still need unguarded qualification before the full validation pool is sealed. Native iterative scanning remains outside this fixed non-iterative stopping intervention; no claim of superiority to every production configuration is warranted.

## Saved-output rescore

The pre-fallback outputs from job22928562 were independently scored against its verified exact references. All three unchanged policies still have zero query-level losses relative to raw native640 and identical per-condition mean recall to that raw reference. Every family has541 short answers among3,150 cases. These are scored, not repaired or rejected.

| Condition | Raw mean recall, native and each policy | Short answers /450 |
| --- | ---: | ---: |
| Unfiltered |99.6444% |0 |
| votes743 |53.4889% |345 |
| votes527 |78.9778% |172 |
| votes310 |94.8222% |23 |
| votes192 |97.8889% |1 |
| votes108 |98.9111% |0 |
| votes32 |99.3778% |0 |

This is a quality rescore only, with no new ANN/provider call or latency inference. The policies were generated using guarded-development labels and remain unchanged: this is a labeled transfer evaluation, not a fresh unguarded-trained agent episode. The original3-request allowance is exhausted at$0.725544. No additional provider access is authorized or needed for the redesign.

## New Torch experiment

The revised source/runtime is `../runtime-unguarded-v1/`; authoritative full protocol/config are `../protocol/study-protocol-unguarded-v1.md` and `../protocol/config-unguarded-v1.json`. The unchanged x86_64 module and programs are pinned to job22928562. No C/graph/algorithm recompilation is necessary to remove the Python serving guard.

The next fixed development job measures nine families: native effort40/80/160/320/640, always-continue policy640 and conservative/moderate/broad compiled policies. Lower-effort native settings expose the recall/latency frontier instead of requiring all settings to meet95%. Matched-quality native selection requires zero individual recall loss against raw640, then lowest equal-six-filter mean; within1% choose higher effort. The agent uses the existing mean/complexity/hash tie rules. Keep all grid points and failed relative-quality outcomes.

Execution phases:

1. Recompute3,150 exact references under sequential plans on the actual imported representation; log evaluation cost separately and close all exact readers.
2. Capture development checkpoint features and qualify28,350 family outputs (including9,450 compiled policy cases), native/noop parity, expected raw outputs and first-stop decisions. No exact-serving connection is available; low recall and short answers do not fail runtime qualification.
3. Time113,400 real unguarded requests and2,520 warmups across two mirrored epochs and18 A/B reader labels. The serving function accepts only one ANN connection/query, dispatches one approximate SQL query, returns its actual output, and times construction/feature/rule/search/continuation/fetch/decode. It cannot access exact labels, an exact connection or a fallback rule. Heavy evaluation and logging are outside request time.
4. Verify immutable data/index, exported snapshot, eligibility, settings, resources and cleanup. Return verifier reconstructs every quality/timing/warmup record, exact references, full execution order, timer components, partial-output scores and exact attempt ledger. Slurm COMPLETED0:0 is a separate gate.

Fixed resources:4 physical CPUs/48GiB/8-hour ceiling/160,000-attempt cap. Planned attempts are exactly150,570:144,270 ANN requests,3,150 captures and3,150 offline exact references. There are zero serving exact calls. The private copied PostgreSQL cluster raises max_connections16->32 to support18 A/B readers plus keeper; all other startup settings remain inherited and no original database or pinned source is modified. No node pinning or automatic resubmission is included.

## Local readiness

Ten serving/scoring/startup-contract checks pass, including7/10=.7, empty/partial answers, wrong-neighbor scoring, duplicate/ineligible/nonfinite rejection, SQL failure propagation, timer components, cap-before-dispatch and one-query/no-exact serving capability. Synthetic real PostgreSQL smoke passes seven conditions, native/noop/three compiled-policy semantics, short answers returned unchanged, separate exact reference scoring and18 concurrent reader capacity using the same private startup helper. The first capacity smoke failed because pg_ctl was not on that container's PATH; the helper now uses the explicit qualified binary path, and both logs are retained. Full-size synthetic verifier checks use fabricated timers and explicitly do not establish runtime latency.

The sealed kit and upload/submission/progress/collection instructions are `../kits/unguarded-development-v1.tar.gz` and `../kits/UNGUARDED-COMMANDS.txt`. The new original-graph timing gate remains pending a user-run Torch return. There is no promotion of the old broad nominee into a final unguarded policy before this experiment.
