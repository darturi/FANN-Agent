# Reader-attribution v1 startup repair

Torch job23074287 failed after9seconds with exit1 at `load_stage()`:
`ValueError: Use a clean process`. The diagnostic's top-level experiment import loaded its
schedule as `design`, a reserved root belonging to the pinned inherited package. The guard
correctly rejected the foreign module before restore or exact/ANN queries. This is an invalid
startup allocation, not a negative performance observation. The failed archive must be collected;
its independent verification remains pending.

The repair renames only the diagnostic schedule module to `reader_attribution_design` and changes
its three consumers' imports. The schedule module's bytes are identical. The executable entrypoint,
serving function, both search modules, original package, queries, policy thresholds, graph, scoring,
analysis logic, phase counts and resource limits are unchanged. The frozen loader and its checks
are unmodified. The original archive/freeze and remote run directory are preserved.

The new `submit.sh` requires `startup-preflight.sh` before sbatch. It extracts the pinned package
into a private `.startup-preflight` directory, mounts inputs read-only and checks both phase
environments using Torch's native runtime image. The checks exercise actual entrypoint imports,
the frozen loader, backend/PyArrow imports, runner identity, phase module pins and private startup
adapter. They execute no database query and make no provider call. A failure preserves its
stdout/stderr and stops before Slurm submission. No automatic retry or requeue is added.

Local checks reproduce the original exception and pass the corrected frozen loader in both phase
environments. Six regression checks establish namespace-only executable changes, identical role/
CPU/order assignments, original artifact preservation and mandatory native preflight. A full-size
fabricated-return check exercises all630,000 timing rows,14,000 warmups and15,750 work rows,
including corrupted CPU/module rejection and paired analysis. These fixtures are not new
performance results.

The full local backend import crashed in PyArrow under Mac x86 QEMU, with and without the
launcher's one-thread math-library limits. The logs are retained; those containers were stopped.
Only the loader portion is locally qualified. **Full backend readiness is pending the native
Torch preflight**, which does not use the local `--loader-only` testing option. No Slurm job or
provider request is submitted by Codex. All six filters remain; exact search is offline scoring
only, and validation/test outcomes remain unopened.

`build_repair.py` creates a fresh kit from the original hash-verified kit. After local checks,
`seal_repair.py` pins the delta/readiness receipts and creates the deployment archive and a new
deployment freeze. It never overwrites the old study freeze. Output kit:
`trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/reader-attribution-v1-startup-fix.tar.gz`.
The deployment remains the same bounded diagnostic, with684,950 planned attempts and unchanged
four-CPU/48GiB/eight-hour limits. This is one manual corrected submission, not a search for a
favorable allocation.

Run local regression checks from the workspace root:

```bash
agent/.venv/bin/python -B agent/experiments/reader-attribution-startup-fix-v1/test_repair.py
```

Use the workspace's `kits/ATTRIBUTION-STARTUP-FIX-COMMANDS.txt` to collect the failed return,
upload the corrected archive, run the mandatory native preflights and submit once. If either
preflight or the new job fails, retain all files and report the output before another attempt.
