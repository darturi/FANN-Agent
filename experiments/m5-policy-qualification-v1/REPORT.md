# M5 preparation outcome — November16

The development-only Torch kit is sealed and ready for user upload/submission.
No Torch allocation or provider request was made while preparing it. The original
graph M5 qualification and live timings remain pending.

## Frozen deployment

Archive: `trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/m5-policy-qualification-v1.tar.gz`
relative to the workspace;8,248,804 bytes. SHA256:
`3c4a0bd267d743e7abff9790beff7a7af510bc350cf079dda1c45d24e984b3b1`.
The [freeze receipt](receipts/M5-freeze.json) binds the modules, plan, protocol,
nominees, source graph/split and local readiness. Use [SFTP-UPLOAD.txt](SFTP-UPLOAD.txt)
for Mac upload; this transport-only supplement supersedes the original SCP upload
block. [COMMANDS.txt](COMMANDS.txt) provides Torch submission/progress and
return-download commands. The sealed archive and its checksum are unchanged.

One job: four physical CPUs,48GiB,six-hour wall limit. Expected214,396 searches
under225,000 total reserved attempts. Compare native640, candidate7, candidate8,
their exact matched continue-only controls, and an empty-policy diagnostic.
All six scalar filters plus unfiltered remain represented in every phase.
Four pinned persistent reader PIDs cross all six roles twice, yielding151,200
timed requests. Work counters run under a separate module/private graph copy.
See [PROTOCOL.md](PROTOCOL.md) and [the machine-readable plan](receipts/M5-plan.json).

Both compiled nominee policies exactly match M4 submission. Bound M1 labels
reproduce candidate7's135/41 unfiltered/votes32 stops and candidate8's102/22,
with zero per-case recall losses across3,150 cases. These are replay checks,
not new M5 original-graph results. Torch must reproduce them before timing.

## Local verification

- Nine design/source/scope tests pass, including complete role/CPU/query cells,
  mirrored order, unchanged M1 engine sources except compiled pool, mandatory
  native startup checks, and one approximate request for a short output.
- Generated C and independent Python decisions agree on3,990 boundary/null/partial
  cases. Matched force-continue and compiler feature masks are checked.
- Actual synthetic PostgreSQL runs exercised production qualification and timing
  loops (1,344 timed and1,344 warmup requests), separate work loops (168 requests),
  and zero-result nullable-feature continuation on every filtered condition.
  These fixtures use8d vectors and ef8192; they are engineering checks, never
  original-graph latency evidence. The Torch run uses frozen768d/ef640.
- The independent return verifier reconstructed3,220 fixture attempts and rejected
  eight re-signed corruptions: CPU assignment, request order, missing prefix,
  work CPU, timed output, unneeded feature work, instrumented primary module,
  and extra attempt. Production scope rejects fixture results.
- Forty-eight independent raw CPU aggregations match analysis means/ratios.
  Paired group bootstrap analysis executes, including per-filter intervals.
- Both clean frozen-package loader-only checks pass under local amd64 emulation.
  Full native backend startup remains mandatory on Torch before sbatch.
- Python lint/format and all shell syntax checks pass. Failed initial local
  module-mount and inherited zero-fixture checks are retained and explained in
  [local readiness](receipts/local-readiness.json); neither was a study run.

Exact search runs only in offline scoring sessions, with6,300 planned calls and
zero serving exact calls. It never completes or repairs ANN outputs. Missing
neighbors remain recall misses. No validation/test outcomes or vectors were
opened; no additional model call, threshold fitting or automatic retry is added.

## Return gate and interpretation

Verify archive checksum, complete raw inventory,3,150-case quality/prefix bridges,
reader/CPU schedule, all timing rows and214,396 attempts; obtain independent sacct
COMPLETED/0:0. Analyse direct paired candidate/native and candidate/matched costs,
each filter, CPU/cycle behavior, and separate graph-work savings. Empty/native
equivalence is a diagnostic, not a correction to candidate time. One allocation
can supply a development signal; it cannot establish allocation-level robustness
or held-out benefit. Native remains admissible. If credible benefit is absent,
retain a negative/inconclusive outcome rather than add generation or use held-out
queries to search for a winner.
