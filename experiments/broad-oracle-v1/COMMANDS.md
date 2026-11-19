# Reproduction

Run from the `agent` repository. Keep the prior experiment inputs immutable.
All outputs below go to new directories under
`../trials/fannagent-benchmark-evaluation-v1/reviews-small/broad-oracle-v1`.

1. Read `PROTOCOL.md`; run the v3 tests and the existing v2 protocol tests.
2. Prepare a capture binding: arm 80, forced continuation, all 13 declared
   features, schedule 1..4096 and normal maximum fuel. Build it with
   `build_runtime.py --bindings PATH --output NEW_RUNTIME`.
3. Compile with the pinned `fannagent/torch-reviews-first:20261013` image:
   `make -j2 OPTFLAGS= PG_CONFIG=/opt/postgresql/bin/pg_config` in `engine`.
   This task's final capture runtime is `capture-runtime-v3`.
4. `prepare_capture.py` seals the acquisition kit. `remote.py launch capture`
   verifies and uploads it, performs a native startup preflight and submits
   exactly one bounded Slurm job. `remote.py monitor capture` reads progress;
   `remote.py collect capture` verifies scheduler/host status and raw hashes.
   Configure a verified authenticated SSH master before using this transport.
5. `fit_broad.py --capture RETURN/results --output NEW_FIT` independently checks
   known actual prefix features, fits each cohort, replays compiled semantics
   and submits both JSON artifacts through the normal agent adapter. It requires
   NumPy. Record the actual capture allocation's `ElapsedRaw` from accounting.
6. `prepare_benchmark.py --capture RETURN/results --fit FIT --elapsed SECONDS
   --phase build` creates a separate engine retaining every old v2 oracle.
   Compile it using the pinned image. Run the same command with `--phase seal`
   to freeze the shared comparison, including carried resource reservations.
7. Launch, monitor and collect the benchmark with `remote.py`. Do not silently
   requeue or repeat an allocation. Fixes require new explicit sealed revisions
   and must retain consumed time/search reservations and failed evidence.
8. `broad_analyse.py --results RETURN/results --kit benchmark-kit-v1` verifies
   all output, audit, schedule and accounting records before calculating
   statistics. `finalize.py --capture CAPTURE/results --results RETURN/results
   --fit FIT` publishes compact artifacts and a comparison plot. The latter
   requires Matplotlib. Set `MPLCONFIGDIR` to a writable temporary directory.

The implementation deliberately uses only the standard library in the frozen
native runtime helpers. `broad_contract.py` is a byte-for-byte copy of the public
core with a neutral module name: the frozen backend disallows importing the
researcher's `fannagent` package before loading its own pinned dependencies.
Fitting occurs offline with the public package and actual agent submission
adapter; this neutral native import does not change the language or compiler.

The completed run is job `23719580`, sealed in `benchmark-kit-v3`. Its explicit
resume used `prepare_resume.py`, then a supervised canonical-projection repair
used `prepare_repair.py`; `launch_resume.py --revision v3` verifies and hard-links
unchanged input bytes from the earlier remote stage and overlays only changed
control files. It submits once. All prior time and the failed reservation window
remain charged. `remote.py collect_failed` preserves failed evidence separately.

For monitoring or collecting this revision, set `FANNAGENT_SSH_CONTROL_PATH` to
an authenticated master and pass `--record benchmark-v3-submission.json` to
`remote.py`. For reporting, use the v3 kit with `broad_analyse.py --kit ...` and
`finalize.py --kit ...`. Preserve the failed control results; do not repeat a
comparison to obtain favorable equivalence tests. Both the seven-condition and
six-filter aggregates are exported in `results/report.json`.
