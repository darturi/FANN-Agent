# P2b admission profile identity v1

NEXT-ADMIT-01 tests one immutable semantic runtime-profile identity per session admission. It preserves full original policy validation and P2a's lazy prepared handle/query path. Both deep copy and fingerprint remain charged to activation. See [DESIGN.md](DESIGN.md) and the [existing-data precision review](PRECISION.md).

The sealed comparison has four execution labels for each unchanged candidate, matched-continue and routed-native arm: original, frozen P2a, P2b A and identical-path P2b B. Four Williams-balanced serial blocks retain all 200 exposed vectors/600 cases and separate unprofiled timing from a 30-vector diagnostic pass. No provider calls, policy selection, confirmation queries or production changes.

Run the local checks from the workspace root:

```bash
PYTHONDONTWRITEBYTECODE=1 agent/.venv/bin/python -m unittest discover \
  -s agent/experiments/admission-profile-identity-v1 -p test_experiment.py -v
agent/.venv/bin/ruff check agent/experiments/admission-profile-identity-v1
agent/.venv/bin/ruff format --check agent/experiments/admission-profile-identity-v1
```

These use protocol stubs and saved inputs, not native performance measurements. They exercise original numeric/type/depth/feature rejection, caller/profile ownership, cold accounting, lazy compilation, cache/connection/profile invalidation, actual Python SQL-body paths, error closure, balanced scheduling, full simulated driver/report coverage, A/A equivalence gates and safe data ingestion. Native qualification and speed await Torch.

The host-side builder seals a new package; it never dispatches jobs:

```bash
PYTHONDONTWRITEBYTECODE=1 agent/.venv/bin/python \
  agent/experiments/admission-profile-identity-v1/experiment.py package
```

Output: `trials/torch-reviews-admission-profile-identity-v1/`. Use its `COMMANDS.txt` for the exact Mac/Torch paths. The generated `transfer.sh upload` and `transfer.sh download` helpers verify checksums and avoid piping SSH device-authentication output into JSON parsing. Authenticate at the prompt on your own machine. Failed authentication stops before ingestion.

On Torch, verify/extract the new package once, source the existing `torch-reviews-first/torch.env`, set the Slurm account, then call the new package's `pp_control.py submit` once. Four serial jobs each request 4 CPUs/32 GiB/2 hours, with a 6,600-second work deadline. Maximum campaign work is 370,884 searches plus 33,120 separately counted eviction installations. The package uses the existing prepared index/module/image; do not rebuild them or edit policies.

After submission, use `pp_control.py status`. After all four jobs finish, use `pp_control.py collect`, then the Mac transfer helper's `download` action to download the exact bound archive, verify it and independently reconstruct the analysis with sealed local code. Returned Python/shell code is never executed. Remote/local numerical tolerance remains 1e-12; discrete outcomes must match exactly.

Do not rerun `submit`, delete binding/reservation files, or re-extract over an existing package. An ambiguous/failed submission is retained for diagnosis. Serial `afterok` dependencies prevent later measurements after a failed block. `collect` preserves failure data when all known jobs have left the queue; unknown dispatch requires status inspection. The four-block allowance is finite; no extra block or automatic tuning follows failure.

A/A intervals must fit the declared equivalence band, not merely include zero. Failed A/A yields `measurement_inconclusive`; passed A/A with failed engineering criteria yields `revise_or_retain_original`; only all requirements produce `pass`. None establishes policy confirmation, M1/M2/M3 or serving acceptance. Original execution remains the adopted baseline until measured review says otherwise.
