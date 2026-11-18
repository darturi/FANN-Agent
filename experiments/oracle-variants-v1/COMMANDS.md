# Reproduction entry points

Run from `/Users/danielarturi/Developer/JinyangLiWork`. These are evaluator-only
hindsight diagnostics; do not feed their labels or policies into an ordinary
protected agent qualification run.

1. `prepare_capture.py` seals the original graph/module and existing exact
   references. The submitted revision was `capture-kit-v2`, job 23604734.
2. `verify_capture.py --results <capture-results> --kit <capture-kit-v2>` checks
   raw hashes, all cases and legal actions, prefix proofs, scores and budgets.
3. Run `dsl_fit.py --cases <capture-results>/cases.jsonl --output <fits> \
   --seconds-per-filter 180 --cohort full_workload` and the same command with
   `--cohort heldout_test`. System Python 3.12 with SciPy 1.16.3 is required.
   Set `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`. Each fit manifest freezes the
   fitter, validator, compiler and cases before optimization. Do not edit them
   while a fit is running.
4. `build_runtime.py --policies <fits> --output <fresh-runtime>` invokes the
   unchanged agent validator/compiler. It checks that only `compiled_v2.inc`
   differs from the qualified oracle engine. Compile that runtime in the pinned
   `fannagent/torch-reviews-first:20261013` amd64 image with `make -j2 OPTFLAGS=
   PG_CONFIG=/opt/postgresql/bin/pg_config`.
5. `prepare_benchmark.py --capture <capture-results> --runtime <fresh-runtime> \
   --fit <fits> --elapsed <capture-sacct-ElapsedRaw> --revision v1` checks fit
   bindings and seals the benchmark archive. The capture allocated 1,809 seconds.
   Inspect the timing protocol and generated shell scripts before submitting.
6. On Torch, verify the archive hash, extract into a fresh directory and use
   `bash submit-benchmark.sh --check`, then `--submit`. The latter runs the real
   backend startup preflight before its single non-requeued Slurm submission.
7. `monitor_benchmark.py` reads the active job using the authenticated SSH master.
   Collect the completed archive, its checksum, Slurm output and `sacct` records.
8. Put the sealed kit on `PYTHONPATH` and run its `variants_analyse.py --results
   <results> --kit <kit>`. It independently verifies all raw records before
   bootstrapping either cohort. This must pass before publishing any numbers.
9. `finalize.py --results <results> --kit <kit> --fit <fits> --output <fresh-output>
   --accounting <capture-accounting.psv> <benchmark-accounting.psv>` exports the
   ordinary feasible policies separately from hindsight lookup artifacts.
   `plot_report.py --folder <fresh-output>` renders the PNG/SVG figure.

`test_dsl_fit.py` compares the optimizer against exhaustive enumeration on a
small nonmonotonic/nullable case. `smoke_capture.py` and `smoke_benchmark.py` run
actual PostgreSQL fixture acquisition, compiled decisions, feature masks,
answers and timing. Fixture latencies are never benchmark results. The fixture
database must persist between capture and recompilation; its Unix socket needs
container storage rather than a macOS bind mount.

Raw inputs, source acquisition, fit progress, solver certificates, build logs,
failed fixture attempts and final measurements are retained under
`trials/fannagent-benchmark-evaluation-v1/reviews-small/oracle-variants-v1`.
Never overwrite a sealed kit or a returned raw file.
