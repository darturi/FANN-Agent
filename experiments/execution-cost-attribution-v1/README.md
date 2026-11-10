# Execution cost attribution v1

First experiment in the [performance research roadmap](../../../research/fannagent-performance-research-roadmap-2026-10-22.md), implementing P1's measurement protocol. It diagnoses the unchanged selective execution path. It does not optimize production code, fit a policy, call a model, consume confirmation data, or authorize deployment.

The latest selective pilot found that even routed-native execution paid approximately 1.247 ms preparation plus 0.152 ms routing during activation. This experiment identifies the Python functions and call paths behind those measured categories before a separate P2 implementation changes their lifecycle.

## What runs

Reuse the pilot's exact x86 `vector.so`, image, prepared physical index, qualified core/adapter, `ef_search=640`, `k=10`, and 200 previously exposed development vectors / 600 query-filter cases. The package includes the sealed pilot inputs, not a fresh copy of the current source checkouts. No engine compilation or index rebuild is required.

Three fixed arms each receive their own paired ordinary-native reference:

1. Earlier `cons-bypass108` candidate, credited seed, semantic hash `a014a290966444a86614f1e5be1960dad2fb8684044e85e9df82899911062b0d`.
2. Same mask/profile/tree conditions with all leaves continuing.
3. Host-owned routed-native control with an empty eligibility mask.

Each block has two separate passes:

- **Primary timing:** all 600 cases; original unmodified `Session`, pair timer, and call path; activation, one discarded warmup, three retained reuse pairs. No profiler is active.
- **Diagnostic profiling:** 60 deterministically hash-selected development vectors, all three filters, 180 cases. After primary timing is finished, profile session preparation and query execution with `cProfile`. Keep activation, discarded warmup, and reuse phases separately. Verify outputs against the primary same-query proofs. These timings are perturbed diagnostics and never enter primary performance statistics.

Record function counts, exclusive self time, inclusive cumulative time, and profiled wall time by block/arm/filter/phase. Function argument values are not recorded. Nested cumulative times must not be added together. Full application timers, ANN timers, preparation, and routing remain visible. No overhead is subtracted from candidate latency.

## Resource ceiling

| Item | Per allocation | Entire campaign |
| --- | ---: | ---: |
| Serial allocations | 1 | 3 |
| CPUs / memory / Slurm wall limit | 4 / 32 GiB / 2 hours | At most 6 allocated hours, plus queue time |
| Runtime work deadline | 6,600 seconds | One deadline per allocation |
| Getter qualification searches | 921 | 2,763 |
| Primary backend/reference searches | 22,521 including getter qualification | 67,563 |
| Diagnostic backend searches | 5,400 | 16,200 |
| Total backend/reference searches | 27,921 | 83,763 |
| Primary retained pairs / discarded warmup pairs | 7,200 / 1,800 | 21,600 / 5,400 |
| Diagnostic retained pairs / discarded warmup pairs | 2,160 / 540 | 6,480 / 1,620 |
| Explicit control policy installations | 2,340 | 7,020 |
| Provider calls / confirmation queries | 0 / 0 | 0 / 0 |

Control installations are SQL work, counted separately from backend/reference searches. The study does not claim to count every SQL statement. Repetitions are clustered within independent vectors, including all filter variants and blocks.

The three blocks are submitted with serial `afterok` dependencies. The controller checks source preservation, image, binary, prepared index, and getter qualification before timing. Private database copies use the existing Unix-socket/SCRAM restore procedure and are stopped on exit. Original databases, package sources, ledgers, result campaigns, and confirmation entitlements are not modified.

## Local preparation and checks

From the workspace root on the Mac:

```bash
cd /Users/danielarturi/Developer/JinyangLiWork
PYTHONDONTWRITEBYTECODE=1 agent/.venv/bin/python \
  agent/experiments/execution-cost-attribution-v1/test_experiment.py
PYTHONDONTWRITEBYTECODE=1 agent/.venv/bin/python \
  agent/experiments/execution-cost-attribution-v1/experiment.py package
```

The first command runs interface, integrity, accounting, profiler separation, and scheduler simulations only. It makes no provider/database/Slurm requests. Fake timing values are not scientific results or native qualification. The second command verifies preserved local source data and creates the sealed upload, checksum, and exact transfer/run commands. Repeating `package` recovers an existing verified package; it does not overwrite one.

Output directory:

```text
/Users/danielarturi/Developer/JinyangLiWork/trials/torch-reviews-execution-cost-attribution-v1/
```

Use its `COMMANDS.txt` as the exact runbook. Do not use the closed selective episode's `study.py resume` or submission commands.

## Run on Torch

The actual measurements need the Torch x86 environment. Mac tests cannot establish the measured preparation/routing costs on that environment. The package uses the previously measured native module; it does not need the local ARM Docker qualification fixture.

**1. Mac: upload the sealed archive.**

```bash
(
  set -euo pipefail
  cd /Users/danielarturi/Developer/JinyangLiWork/trials/torch-reviews-execution-cost-attribution-v1
  shasum -a 256 -c torch-execution-cost-attribution-v1.tar.gz.sha256
  scp -o HostKeyAlias=dtn.torch.hpc.nyu.edu -o HostKeyAlgorithms=ssh-ed25519 \
    -o StrictHostKeyChecking=yes -o UpdateHostKeys=no \
    torch-execution-cost-attribution-v1.tar.gz \
    torch-execution-cost-attribution-v1.tar.gz.sha256 \
    dar579@dtn012.hpc.nyu.edu:/home/dar579/
)
```

Use your existing interactive Torch login/authentication flow. This experiment does not change SSH host keys or install credentials.

**2. Torch login terminal: verify, extract, and submit once.**

```bash
(
  set -euo pipefail
  cd /home/dar579
  sha256sum -c torch-execution-cost-attribution-v1.tar.gz.sha256
  test ! -e torch-execution-cost-attribution-v1
  tar -xzf torch-execution-cost-attribution-v1.tar.gz
  source /home/dar579/torch-reviews-first/torch.env
  export TORCH_SLURM_ACCOUNT=torch_pr_288_courant
  PYTHONDONTWRITEBYTECODE=1 python3 \
    /home/dar579/torch-execution-cost-attribution-v1/ec_control.py submit \
    /home/dar579/torch-reviews-first /home/dar579/torch-reviews-results
)
```

Submission uses the environment's scratch/results roots and existing Apptainer binary. It requires the original pilot package at `/home/dar579/torch-selective-agent-v1-pilot-20261022T192817Z-66ed81d6`, the completed pilot under `/home/dar579/torch-reviews-results`, and the existing prepared index at `/scratch/dar579/torch-reviews/torch-reviews-size-sweep.ihFoep/prepared/size-247286`.

If an input is missing or changed, submission fails. Inspect/recover the preserved resource; do not rebuild the index and call it an identical replay. The account above is the recorded previous account; if access has changed, set the currently authorized account before submission rather than changing the protocol or guessing one.

**3. Torch: check status, including after a fresh login.**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  /home/dar579/torch-execution-cost-attribution-v1/ec_control.py status
```

This prints the bound campaign, per-block progress/failures, job IDs, `sacct`, and `squeue`. No prior shell variable is required. Do not run the submit command again.

**4. Torch: after all three blocks finish, analyze and collect.**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  /home/dar579/torch-execution-cost-attribution-v1/ec_control.py collect
```

The controller analyzes successful raw results with the sealed code and prints the archive/checksum paths. Collection does not allocate another Slurm job or call a model. If known jobs have all left the queue but a block failed or a dependency was cancelled, it archives the partial data with a failure summary and makes no performance claim.

**5. Mac: use the complete download/ingest block in the generated `COMMANDS.txt`.**

That block reads the durable campaign binding through your authenticated transfer host, downloads the exact archive/checksum, verifies them, extracts regular files as data, and recomputes reports with the trusted local package. Returned Python and shell files are never executed. Remote/local discrete results must match exactly; floating summaries permit at most `1e-12` absolute roundoff.

## Outputs and interpretation

Independent local analysis is written to:

```text
trials/torch-reviews-execution-cost-attribution-v1/analysis-local/<bound-campaign>/
  report.txt          # unprofiled paired latency and quality, cost components
  attribution.md      # top exclusive-cost functions by block/arm/filter/phase
  performance.json    # full per-filter, pooled, block, raw-hash, and profile data
  verification.json   # remote/local parity and preserved study boundaries
```

Start with `report.txt`, then inspect `attribution.md` for preparation and routed-native groups in all three blocks. Use `performance.json` for complete function lists and confidence intervals. A large function's cumulative duration includes children; exclusive time is the useful starting point for assigning cost without double counting.

The first decision is whether preparation/routing cost is concentrated in repeated validation, object ownership/copying, hashing/serialization, query normalization, or database-side/transport work. Map each candidate operation to its required lifetime and invalidation rules. Then propose one separately versioned P2 change and remeasure it with the same frozen policy. This experiment makes no optimization or serving acceptance claim, even if a development arm passes the old numerical checks.

## Recovery and preservation

- A package binding and a global protocol reservation prevent duplicate submissions, including accidental reuploads. An ambiguous `sbatch` result remains recorded as unknown; no automatic retry occurs.
- If submission fails or a dependency is cancelled, retain the package, reservation, and campaign. Use `status` and inspect `blocks/*/failure.json`, `host-failure.json`, and `logs/`. Do not delete bindings or clear reservations to force a rerun.
- A failed or incomplete campaign cannot yield a verified performance result. A separately declared mechanical repair/version is needed if execution cannot be recovered without repeating measurements.
- Download and local extraction preserve existing outputs. After inspecting an interrupted extraction, use `experiment.py analyze --campaign /absolute/path/to/existing/campaign`. If an analysis directory is partial or already populated, add `--output /absolute/path/to/a/fresh/analysis-directory`. Existing analysis is never overwritten.
- No confirmation inventory is opened, no old model episode is resumed, and no package or result is published externally by these scripts.

See [DESIGN.md](DESIGN.md) for the question, phase separation, rejection conditions, and decision gate.
