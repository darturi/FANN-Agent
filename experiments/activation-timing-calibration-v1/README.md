# P2c activation timing calibration v1

NEXT-CAL-01 implements fixed native conditioning and adjacent AB/BA crossover controls for the original, P2a, P2b and plain-native execution paths. Policies and four P2a/P2b execution/validation sources remain byte-identical. Read [DESIGN.md](DESIGN.md) before interpreting the measurement scope.

This measures fresh-session activation with an explicitly conditioned shared index/query path. Two ordinary-native executions precede each fresh constructor; all conditioning is recorded and resource-counted. Full admission, lazy preparation, compilation, installation and first execution stay charged. It does not measure a cold index or retrospectively qualify the inconclusive P2b campaign.

Local checks from the workspace root:

```bash
PYTHONDONTWRITEBYTECODE=1 agent/.venv/bin/python -m unittest discover \
  -s agent/experiments/activation-timing-calibration-v1 -p test_experiment.py -v
agent/.venv/bin/ruff check agent/experiments/activation-timing-calibration-v1
agent/.venv/bin/ruff format --check agent/experiments/activation-timing-calibration-v1
```

The local tests simulate the entire two-block driver and trusted replay on saved inputs, plus malformed/tampered raw evidence and timing phases. They exercise original numeric/tree/depth rejection, private ownership, lazy compilation, connection/cache/profile invalidation, actual Python SQL-body protocol stubs and failure closure. They do not run native DB searches or establish speed.

The builder seals and verifies a separate package without dispatch:

```bash
PYTHONDONTWRITEBYTECODE=1 agent/.venv/bin/python \
  agent/experiments/activation-timing-calibration-v1/experiment.py package
```

Output directory: `trials/torch-reviews-activation-timing-calibration-v1/`. It contains the sealed package/archive/checksum, exact `COMMANDS.txt`, and `transfer.sh upload|download`. Mac transfer authenticates interactively over SSH, transfers binding JSON as a completed file and checks its manifest/campaign identity before download/ingestion. No authentication output is piped into JSON parsing.

On Mac use `bash .../transfer.sh upload`. On Torch verify/extract the new `torch-activation-timing-calibration-v1` package once, source the existing `torch-reviews-first/torch.env`, set the existing Slurm account and run the new `pp_control.py submit` once. Successful submission prints **two** serial job IDs, job name `fann-calibration-v1`. Each requests 4 CPUs/32 GiB/3 hours; work deadline 10,200 seconds. Total cap: 592,242 searches, including 96,000 conditioning executions, plus 48,000 separately counted eviction installations. No GPU, provider call or confirmation query.

Use `pp_control.py status` after submission, including after a fresh login. If both jobs finish, run `pp_control.py collect`; then `transfer.sh download` on Mac verifies the archive and independently reconstructs `report.txt`, `calibration.md` and `performance.json` using sealed local code. No returned code is executed. If a known job fails, collect preserves failed raw evidence once jobs have left the queue; unknown dispatch requires inspection.

Do not repeat submit, delete reservations/bindings, re-extract over a partial package, add blocks or rerun P2b. The old P2b verdict stays `measurement_inconclusive`. New calibration requires all native/original/P2a/P2b A/A cells, both regimes and all filters to fit the unchanged absolute/relative bands. Engineering criteria use the frozen P2b gate logic in this newly declared scope. No A/A correction, dropped observations or threshold change. Failure/inconclusiveness consumes this single allowance and leads to an explicit retain-original/P3 decision, not automatic retries. Both gates passing still requires operating-scope and lifecycle review before any adoption.
