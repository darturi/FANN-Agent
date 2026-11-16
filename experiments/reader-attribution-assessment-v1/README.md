# Verified development attribution return: job23303080

The downloaded return passes the sealed diagnostic. See [REPORT.md](REPORT.md) for findings,
verification counts, conditional uncertainty and the next stages of protocol v2. All six scalar
filters plus unfiltered remain included; validation/test outcomes remain unopened. This records
a valid diagnostic, not final policy promotion. No new Torch job or provider call was made.

The original clean-import failure23074287 is also checksum-verified and retained without any
measurement files. Both native startup preflights for the corrected deployment exercised the full
backend import successfully. The independent scheduler completion gate is preserved from the
user's pasted sacct output in `receipts/scheduler-status.txt`.

The sealed verifier checks all630,000 timings,14,000 warmups,1,400 assignments,15,750 quality
results,15,750 separately instrumented work queries and6,300 offline exact references. It checks
every record's schedule, reader PID, declared CPU, output and timer/attempt accounting, as well as
all phase raw-file hashes, module/source pins and graph/scope gates. Exact search is scoring only.

`assess.py` independently reconstructs the450x7x20x2x5 timing tensor, confirms full cell/CPU/role
coverage, reproduces both frozen summaries' means, checks all query-level native/continue work
counters, raw recall losses and first-stop inventories, and produces descriptive filter summaries.
It reads only the development-only return and sealed kit. This supplemental analysis does not
fit or alter policy thresholds or change the prespecified bootstrap. No outliers/filters are removed.

From the shared workspace root:

```bash
agent/.venv/bin/python -B trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/reader-attribution-v1-startup-fix/verify_return.py --results trials/fannagent-benchmark-evaluation-v1/reviews-small/returns/job-23303080/results --kit trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/reader-attribution-v1-startup-fix
agent/.venv/bin/python -B trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/reader-attribution-v1-startup-fix/analyse.py --results trials/fannagent-benchmark-evaluation-v1/reviews-small/returns/job-23303080/results
agent/.venv/bin/python -B agent/experiments/reader-attribution-assessment-v1/assess.py --results trials/fannagent-benchmark-evaluation-v1/reviews-small/returns/job-23303080/results --kit trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/reader-attribution-v1-startup-fix
```

`receipts/assessment.json` binds the report, code, downloaded archives/logs/preflights, frozen
verifier/analysis and raw phase receipts by SHA256. Large raw records remain under the workspace
paths in that manifest. The protected-study split and original deployment freezes are unmodified.
`receipts/generation-gates.json` closes M0 while retaining the M1/M2 prerequisites. Calling the
controller's generation preflight with those real gates and the current real evidence correctly
stops at **M1 original-graph qualification pending**. It does not authorize a new paid episode.

The outcome supports a modest role/work benefit for Broad within one allocation; the earlier
always-continue advantage did not reproduce. The specific cause of the earlier allocation's
control anomaly remains unidentified. Conditional group confidence is not cross-allocation or
held-out confidence. The next task is to seal the bounded M1 runtime/prefix/cost qualification,
including all reached prefixes and the1,496 missing partial labels, before fresh generation.
