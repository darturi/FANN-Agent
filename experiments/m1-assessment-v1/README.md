# M1 return assessment

Verified original-graph development job **23376796** is assessed in [REPORT.md](REPORT.md).
The original deployment, input freezes and failed packaged export log remain unchanged.

From the `agent` repository, run the sealed verifier first, then the packaged analysis. Its
original cost-library output is valid; its original export fails on zero-padded source IDs.
Preserve that log. The independent `assess.py` reproduces timing/counter/quality/ledger totals
and bootstrap intervals, checks native startup/scheduler evidence and exports the intended
anonymous prefix bundle with only the fold lookup normalized. It requires a fresh export path.

```bash
.venv/bin/python -B experiments/m1-assessment-v1/assess.py \
  --results ../trials/fannagent-benchmark-evaluation-v1/reviews-small/returns/job-23376796/results \
  --kit ../trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/m1-runtime-qualification-v2
```

The full immutable raw return and larger derived files stay under the study workspace.
Compact receipts bind the external artifacts. The bundle retains cost-unqualified status;
M2 cost guidance and M3 rehearsal remain before any newly authorized provider episode.
No new database search, provider call or validation/test outcome access is part of this assessment.
