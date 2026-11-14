# Three compiled agent policies: job22928562 verified

All three compiled programs pass full original-graph development qualification. The archive, sealed kit/module/guard/split/program identities, exact references, live checkpoint features, first-stop/continue decisions, final eligibility/completeness/recall, every timing and warmup output, global execution order, timer components and attempt ledger reconstruct successfully. Slurm completion is independently recorded from the user's pasted sacct output: COMPLETED0:0,49m08s, step MaxRSS6,706,152KiB. Actual node cs640, Intel Xeon Platinum8592+, four physical cores and48GiB limit. Graph/data identity matches the prior qualified parent; snapshot, cleanup and integrity gates pass.

No validation/test outcomes were opened. All450 vector groups and all six scalar predicates plus unfiltered are retained. There were no provider calls or policy edits. This is one development allocation, not a confirmatory result.

## Coverage and accounting

- 3,150 query/filter qualification rows, comprising9,450 compiled-policy cases and3,150 native cases.
- 50,400 complete serving-time records:450 groups x7 conditions x4 families x2 A/B labels x2 epochs.
- 1,120 separately recorded warmups.
- All four families return complete unique eligible finite results on every case. All three candidates have zero individual recall losses; their mean recall equals the guarded parent in every condition. Minimum mean recall is.965556 at votes310, above.95.

| Phase | ANN | Capture | Reference exact | Completion exact | Total attempts |
| --- | ---: | ---: | ---: | ---: | ---: |
| Quality | 12,600 | 3,150 | 3,150 | 2,164 | 21,064 |
| Timings | 50,400 | 0 | 0 | 8,656 | 59,056 |
| Warmups | 1,120 | 0 | 0 | 216 | 1,336 |
| Total | 64,120 | 3,150 | 3,150 | 11,036 | 81,456 |

This is below the sealed160,000-attempt ceiling. No omitted or duplicate case/epoch/label is accepted. Query attempts include serving exact fallbacks as well as qualification references. Map build totaled1.557s; reader open/attach13.968s; warmups47.838s; close0.228s, separately from complete-request costs. Heavy truth checking and logging are outside request timers as declared.

## Candidate assessment

The primary development endpoint equally weights the six scalar-filter arithmetic means; unfiltered is a separate control.

| Family | Scalar mean ms | Ratio to native | Observed reduction | Stops /3,150 | Recall losses |
| --- | ---: | ---: | ---: | ---: | ---: |
| native | 19.274893 | 1.000000 | 0.00% | 0 | 0 |
| conservative_a | 19.251483 | 0.998786 | 0.12% | 141 | 0 |
| moderate_b_fixed | 19.153754 | 0.993715 | 0.63% | 238 | 0 |
| broad_c_fixed | 18.659077 | 0.968051 | 3.19% | 357 | 0 |

`broad_c_fixed` is the unique development leader under the prespecified1% tie rule; neither alternative is within1% of its mean. All three remain quality-eligible members of the frozen pool. This designation does not select a final validated policy or authorize holdout access.

| Condition | Mean recall (all families) | Native ms | Broad ms | Broad stops /450 | Exact completions per450 (every family) |
| --- | ---: | ---: | ---: | ---: | ---: |
| unfiltered | 0.996444 | 15.450 | 13.281 | 72 | 0 |
| votes743 | 0.992222 | 30.424 | 30.422 | 0 | 345 |
| votes527 | 0.975333 | 28.153 | 28.088 | 7 | 172 |
| votes310 | 0.965556 | 17.442 | 17.359 | 13 | 23 |
| votes192 | 0.979333 | 13.439 | 13.194 | 28 | 1 |
| votes108 | 0.989111 | 12.965 | 12.378 | 56 | 0 |
| votes32 | 0.993778 | 13.225 | 10.513 | 181 | 0 |

The broad policy's largest scalar improvement is votes32 (20.50%); votes108 is4.53% lower. votes743/527 contribute little observed benefit and retain345/172 exact completions per450. Every family retains541 completion fallbacks across the3,150 qualification cases: the agent has not removed the sparse-filter completion cost. Unfiltered improves14.03% descriptively but is not included in the equal-six-filter primary endpoint. Conservative/moderate scalar gains are near zero; feature/no-stop overhead is paid on the conditions where they continue.

## Timing controls and limits

Broad's A/B point ratios are1.02167 at votes108 and1.04156 at votes32, outside[.98,1.02]. Preserve these discrepancies; do not subtract them from treatment effects, choose only a favorable reader or discard those conditions. Most condition/family A/B intervals are too wide to establish equivalence in this allocation.

A supplementary20,000-draw bootstrap (seed20261110) resamples the450 vector groups jointly across every predicate/family/label/epoch. Its broad scalar ratio95% interval is[.95799,.97775]. Broad's A/B90% intervals are[.9906,1.0536] for votes108 and[1.0037,1.0814] for votes32. These conditional-on-one-allocation diagnostics do not implement the final five-allocation hierarchical design and are not confirmatory equivalence or benefit tests. Full per-condition intervals, components and controls are in `development-assessment.json`.

The observed broad reduction is3.19%, below the5% practical target. Neither this point estimate nor the conditional interval establishes the study's adjusted upper-ratio<=.95 success criterion. The one-allocation development result supports a modest candidate signal and a completed runtime qualification, not a headline success or universal recall guarantee. The unsuccessful exploratory model programs and initial abstention remain preserved separately.

## Recommended next step

Retain broad_c_fixed as the development nominee, keep all three unchanged quality-eligible programs in the frozen agent pool, and prepare the single bounded validation selection batch under the existing four-mirrored-epoch design. First complete/pin the required comparator pool and executable schedule; this job only measured native640 and the three new programs, not all seven final comparator families. Preserve the existing quality, equal-filter selection/tie and timing-control rules. Do not open validation until that complete pool and selection procedure are sealed, and leave test untouched until final comparison freeze.

Validation should be treated as an honest bounded decision that can end negative or inconclusive. Do not add model requests, tune thresholds using holdouts, drop sparse filters, relax the5% target or keep rerunning valid development allocations until controls look favorable. There is no need to silently repair or replace this scientifically valid allocation. Any separate diagnostic run would need an explicit fixed prevalidation purpose and versioned plan; it is not recommended as an open-ended prerequisite. This recommendation does not execute validation or authorize a new provider request (the original three-request allowance is exhausted).

## Evidence

`../returns/job-22928562/results/`: raw `quality.jsonl`, `timing.jsonl`, `warmup.jsonl`, execution plans, membership/setup receipts, `receipt.json`, `host-exit.json`; independent `local-verification.json`, `scheduler-reported.json`, `development-assessment.json`. Verification code: `../runtime-agent-v1/verify_return.py`; supplemental assessment: `../runtime-agent-v1/assess_development_return.py`. The original archive and checksum remain unchanged. Machine-readable disposition: `../freeze/agent-development-assessment-v1.json`.
