# Prepared-policy lifecycle v1

P2a / NEXT-EXEC-01 implements the next step in the [performance roadmap](../../../research/fannagent-performance-research-roadmap-2026-10-22.md), following [verified cost attribution](../../../research/fannagent-execution-cost-attribution-v1-results-2026-10-23.md). Production checkouts and the sealed earlier experiments remain unchanged. The revision lives entirely in this separate experiment.

The owned session retains a private prepared-policy handle. Original composite validation remains charged to session admission; backend preparation happens lazily inside the original backend timer on first eligible execution, then the session reuses that private artifact. Bypass does not resolve it. Compilation, installation, query normalization, actual-predicate routing, connection checks, acknowledgements and error closure remain charged/preserved. An AST check ensures the copied backend execution body changes only its preparation expression. See [DESIGN.md](DESIGN.md) for ownership, invalidation, timing, resource ceilings and the prospective engineering gate.

## Comparison

Original and owned execution each run the same candidate, matched-continue and routed-native control, with separate paired ordinary-native baselines. All 200 development vectors / 600 cases remain; there is no fitting or confirmation. Three serial allocations run unprofiled timing, then a separate 30-vector profiling pass. The cap is 143,163 backend/reference searches, 12,420 separately counted control eviction installs, and zero provider calls/confirmation queries. Each allocation requests four CPUs, 32 GiB and two hours.

The direct comparison must establish at least 0.10 ms and 2% candidate reuse savings using the declared bounds; activation/control/filter regressions must remain within 0.10 ms and 2%, with outer application time also checked. Old/new output identity and first-stop behavior are mandatory. This engineering gate does not confirm or deploy a policy.

## Local checks and package

From the Mac workspace root:

```bash
cd /Users/danielarturi/Developer/JinyangLiWork
PYTHONDONTWRITEBYTECODE=1 agent/.venv/bin/python \
  agent/experiments/prepared-policy-lifecycle-v1/test_experiment.py
agent/.venv/bin/ruff check agent/experiments/prepared-policy-lifecycle-v1
PYTHONDONTWRITEBYTECODE=1 agent/.venv/bin/python \
  agent/experiments/prepared-policy-lifecycle-v1/experiment.py package
```

Tests use frozen Python interfaces, real policy/query validators, deterministic SQL protocol stubs and saved development subsets. They contact no database, scheduler or model. Simulated timing is not performance evidence. Packaging verifies prior identities/raw results and seals the exact code/data; it never overwrites an existing package. Output:

```text
trials/torch-reviews-prepared-policy-lifecycle-v1/
  torch-prepared-policy-lifecycle-v1/
  torch-prepared-policy-lifecycle-v1.tar.gz
  torch-prepared-policy-lifecycle-v1.tar.gz.sha256
  COMMANDS.txt
```

## Run on Torch

**1. In a terminal on the Mac, upload the sealed package.**

```bash
(
  set -euo pipefail
  cd /Users/danielarturi/Developer/JinyangLiWork/trials/torch-reviews-prepared-policy-lifecycle-v1
  shasum -a 256 -c torch-prepared-policy-lifecycle-v1.tar.gz.sha256
  scp -o HostKeyAlias=dtn.torch.hpc.nyu.edu -o HostKeyAlgorithms=ssh-ed25519 \
    -o StrictHostKeyChecking=yes -o UpdateHostKeys=no \
    torch-prepared-policy-lifecycle-v1.tar.gz \
    torch-prepared-policy-lifecycle-v1.tar.gz.sha256 \
    dar579@dtn012.hpc.nyu.edu:/home/dar579/
)
```

Use the existing interactive Torch authentication flow.

**2. In the Torch login terminal, verify, extract once and submit.**

```bash
(
  set -euo pipefail
  cd /home/dar579
  sha256sum -c torch-prepared-policy-lifecycle-v1.tar.gz.sha256
  test ! -e torch-prepared-policy-lifecycle-v1
  tar -xzf torch-prepared-policy-lifecycle-v1.tar.gz
  source /home/dar579/torch-reviews-first/torch.env
  export TORCH_SLURM_ACCOUNT=torch_pr_288_courant
  PYTHONDONTWRITEBYTECODE=1 python3 \
    /home/dar579/torch-prepared-policy-lifecycle-v1/pp_control.py submit \
    /home/dar579/torch-reviews-first /home/dar579/torch-reviews-results
)
```

This uses the original runtime image, prepared index, pilot package and completed P1 results already on Torch. The recorded account is the previously authorized one; if its access has changed, use the currently authorized account. Missing or altered inputs fail preflight. Do not rebuild the index and call it an identical comparison. The command submits exactly three serial Slurm jobs, not compute on the login node.

**3. Check progress, including after a fresh login.**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  /home/dar579/torch-prepared-policy-lifecycle-v1/pp_control.py status
```

**4. After all three jobs finish, collect the existing run.**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  /home/dar579/torch-prepared-policy-lifecycle-v1/pp_control.py collect
```

Collection verifies/reports completed blocks in the existing container and prints the exact archive/checksum location. It creates no allocation or provider request. If known jobs have left the queue but a block failed, collection preserves partial results with a failure summary and makes no performance claim.

**5. On the Mac, run the complete download/ingest block in the generated `COMMANDS.txt`.**

That block reads the durable submission binding, downloads its exact archive/checksum, verifies the transfer and independently recomputes results from regular files as data. Returned Python/shell files are never executed. Numerical parity uses exact discrete values and `1e-12` absolute floating tolerance. The same local script also supports `analyze --campaign /absolute/path/to/extracted/campaign --output /absolute/path/to/fresh/analysis` for recovery without redownloading or rerunning Torch measurements.

## Read the results and recover safely

Local output is under `trials/torch-reviews-prepared-policy-lifecycle-v1/analysis-local/<campaign>/`: `report.txt`, `performance.json`, `attribution.md` and `verification.json`.

Start with direct **owned versus original policy execution**, then inspect each variant versus its own ordinary-native reference. `performance.json` includes all filter/block reports, primary/outer intervals, diagnostic preparation-call checks, and the prespecified engineering verdict. Diagnostic timings are perturbed and never qualify speed. A verified negative gate is a valid result.

Submit once. The package binding and global protocol reservation prevent duplicates, including reuploads. Do not remove bindings/reservations, resubmit an unknown dispatch, rerun completed measurements, or resume the closed selective/P1 campaigns. Preserve failures and inspect `status`, `blocks/*/failure.json`, `host-failure.json` and `logs/`. A separately declared mechanical repair/version is needed if recovery would repeat measurements. No result or package is published externally by these scripts.
