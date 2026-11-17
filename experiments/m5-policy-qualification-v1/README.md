# M5 Torch kit

Qualifies and measures frozen agent candidates7/8, native640, their two matched
continue-only controls, and an empty-policy diagnostic. All six filters plus
unfiltered remain included. Exact search is offline scoring only. Validation/test
are untouched. See [PROTOCOL.md](PROTOCOL.md) for the prospective design.

Kit: `trials/fannagent-benchmark-evaluation-v1/reviews-small/kits/m5-policy-qualification-v1.tar.gz`
relative to the workspace. Upload/submit/status/return commands are in
[COMMANDS.txt](COMMANDS.txt). User submits one job; no retry or provider request.
Resources: four physical CPUs,48GiB,six-hour ceiling;214,396 planned attempts.

Build and seal locally using Python3.12+ with the repository's dependencies:

1. `PYTHONPATH=src .venv/bin/python -B experiments/m5-policy-qualification-v1/build_runtime.py`
2. Build copied `engine`/`observer-engine` in pinned Docker image
   `sha256:ea7083a544d105d589ac1a3915b7ab8425fe1e867f2afc3ceaf99f0a9a48967f`
   with `make OPTFLAGS= PG_CONFIG=/opt/postgresql/bin/pg_config`; save separate
   timing/work modules. Engines differ from qualified M1 only in compiled pool.
3. Stage with `package_kit.py`, execute the tests, actual PostgreSQL fixture
   timing/work/zero-output smokes, independent return-verifier mutation checks,
   physical-CPU analysis check and both loader-only checks. These synthetic
   checks are engineering readiness, never study performance evidence.
4. `seal_kit.py` requires the resulting successful receipts and freezes hashes.

On return, checksum and safely extract the archive into a fresh return directory.
Use Python3.12+ and PYTHONPATH pointing to the sealed kit to run `m5_verify.py`
then `m5_analyse.py`. Preserve errors and obtain independent final sacct output.
The verifier reconstructs the exact schedules and ledger, not just summary flags.
The analysis retains native as a valid outcome and makes no held-out claim.
