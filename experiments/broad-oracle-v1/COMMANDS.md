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
