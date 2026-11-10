# B2f identity correction — release held

This is isolated, locally checked experimental source. **No production package,
transfer helper, upload command or fourth submission is released.**
`experiment.build(testing=False)` rejects production builds. Temporary test
packages are explicitly synthetic and cannot submit.

Three prior allocations failed before searches. They remain spent and immutable:
21111616_0 (launch), 21129331_0 (omitted identity sidecar), and 21159802_0
(eligibility schema mismatch). See IDENTITY-CORRECTION.md and the permanent audit:
`research/fannagent-partial-calibration-v1-release-audit-2026-10-27.md`.

`pc_snapshot.py` hashes only the pinned source_ids/votes eligibility schema.
It separately checks the exact logical field mapping and frozen dataset identity.
Both the actual runtime and actual-backend integration fixtures call its complete
snapshot/request-admission boundary. Returned complete evidence must include
snapshot-qualified.json and the trusted analyzer verifies it independently.

The entry-point fixture calls pc_runtime.main itself through startup, two epochs,
final integrity and cleanup, using the actual frozen backend with synthetic
PostgreSQL/OS responses. It checks startup/cleanup failure paths too. A separate
schema regression reads all 247,286 pinned IDs/votes without dataset vectors.
None of these checks is a native experiment, memory qualification or performance
measurement. Prior frozen code, data, graphs, module, schedule, quality/timing
margins and resource ceilings are unchanged.

Run the offline source checks:

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/danielarturi/Developer/JinyangLiWork/agent/.venv/bin/python \
  /Users/danielarturi/Developer/JinyangLiWork/agent/experiments/partial-calibration-v1-identity-fix/run_checks.py \
  --phase source --receipt /private/tmp/b2f-identity-local-checks.json
```

The remaining release gate is an explicit memory/resource review and the final
release audit. The latest MaxRSS33534232K does not prove anonymous memory usage,
remaining capacity or an OOM cause. Frozen limits will not be silently increased.
Only the read-only configuration command in the audit is requested from Torch.
