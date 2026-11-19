# Saved execution and analysis

**The live workflow is retired because it seeds the agent with prior-run
measurements.** The commands below document historical execution and offline
reanalysis only. Read the [methodological correction](METHODOLOGY-ERRATUM.md);
reanalysis cannot convert this run into a clean-start discovery experiment.

Run from the `agent` repository. Native execution used source `d1d4321` and the
sealed continuation kit; later report/documentation edits did not change that
kit. The bound source, prompt, authorization, model conversation and receipts
are retained under:

```text
../trials/fannagent-benchmark-evaluation-v1/reviews-small/torch-live-feedback-v3/
```

Job `23741092` stopped idle before a learned policy was measured. The explicit
continuation authorization permitted only job `23747524`, carrying the original
model ledger and 256 query reservations. Do not replay launch, evaluation or
model requests: delivery identities and permanent submission markers prevent
automatic retries. The staging extraction timeout occurred before submission;
`run-v2/staging-recovery.json` records the checksum-verified recovery.

The continuation kit identities are:

```text
kit.tar.gz: c26eb825bda2b04a6e408602115b8037f695873aa96d71301837aed675066c3e
kit/SHA256SUMS: 1a0ce897fd6ced094c75f1e0d20d05ab138236158a543d7f601b617c000f6fe1
continuation-plan.json: e6cd76092e6b1265549ba325ca4690c06eb25add1328f4a561bb5130e4015965
```

For analysis of the completed, collected run only, choose a fresh output
directory. This verifies returned hashes, frozen identities, schedule and raw
output scores, then performs the fixed 20,000-draw vector-cluster bootstrap.
It makes no model or database requests:

```sh
.venv/bin/python -B experiments/torch-live-feedback-v3/final_report.py \
  --run ../trials/fannagent-benchmark-evaluation-v1/reviews-small/torch-live-feedback-v3/run-v2 \
  --output ../trials/fannagent-benchmark-evaluation-v1/reviews-small/torch-live-feedback-v3/run-v2/reanalysis-v1
```

The original local checks are recorded in `checks/` and `verification.json`:

```sh
.venv/bin/python -B -m pytest experiments/torch-live-feedback-v3/tests -q
.venv/bin/ruff check experiments/torch-live-feedback-v3
```

Fresh native or model experiments require their own explicit resource scope;
these saved commands do not grant another allocation or a new model allowance.
