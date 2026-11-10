# B1b native-effort frontier v1

`NEXT-EFFORT-01`: isolated experimental native320/640 interface, original640
and source-setting comparators, identical-path controls and a current-index
frontier. [DESIGN.md](DESIGN.md) is the prospective contract. No production
API/runtime/module change, stopping policy, routing fit or provider call.

Local correctness checks use mocks/synthetic durations only:

```sh
cd /Users/danielarturi/Developer/JinyangLiWork
PYTHONDONTWRITEBYTECODE=1 agent/.venv/bin/python -m unittest discover \
  -s agent/experiments/native-effort-frontier-v1 -p test_experiment.py -v
agent/.venv/bin/ruff check agent/experiments/native-effort-frontier-v1
agent/.venv/bin/ruff format --check agent/experiments/native-effort-frontier-v1
PYTHONDONTWRITEBYTECODE=1 agent/.venv/bin/python \
  agent/experiments/native-effort-frontier-v1/experiment.py package
```

The package command verifies prior sources/results, derives read-only eligibility
metadata from the pinned dataset and seals a new package. It does not dispatch.
Generated output: `trials/torch-reviews-native-effort-frontier-v1/`, including
archive/checksum, `COMMANDS.txt` and MFA-aware `transfer.sh`. Run:

```sh
bash /Users/danielarturi/Developer/JinyangLiWork/trials/torch-reviews-native-effort-frontier-v1/transfer.sh upload
```

Then paste the **Torch login** block from `COMMANDS.txt`. It verifies/extracts
once, loads the existing environment, selects account`torch_pr_288_courant` and
submits both serial allocations through `ef_control.py`. Do not run it again
after a successful or uncertain submission. Each allocation uses4CPUs/32GiB/
2hours; total ceiling139,272 searches. The current prepared index is restored
privately; no rebuild or shared source writes. The first native qualification
failure stops its block, and the dependent second block will not execute.

After submission these commands work following a fresh login:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 /home/dar579/torch-native-effort-frontier-v1/ef_control.py status
PYTHONDONTWRITEBYTECODE=1 python3 /home/dar579/torch-native-effort-frontier-v1/ef_control.py collect
```

Run `collect` after both jobs finish. It reconstructs the report or preserves a
failed campaign and prints the archive path. On the Mac:

```sh
bash /Users/danielarturi/Developer/JinyangLiWork/trials/torch-reviews-native-effort-frontier-v1/transfer.sh download
```

The helper authenticates interactively, transfers the binding as a file, checks
package/campaign identity, downloads archive/checksum and runs sealed local
data-only replay. Never pipe an interactive MFA SSH response into a JSON parser.
No returned Python/shell is executed. Do not delete bindings/reservations or
resubmit after a failure; retain the error/raw campaign for diagnosis.

Native correctness, timing precision, recall and net performance are **pending
Torch**. A frontier can justify only a scoped B1c design, not a selected router,
independent confirmation, original-path replacement or milestone claim.

The undispatched first preflight package is preserved under
`trials/torch-reviews-native-effort-frontier-v1-preflight-01/`. Final review removed
a thin reporting wrapper from the plain baseline's query timer and added a
regression check before the final seal. Its old package/receipt are superseded;
use only the current runbook/archive above. No native job or scientific run used
the preflight package, and no gate margin, cohort or search budget changed.

## Completed return and local naming-error recovery (October 25, 2026)

Campaign `reviews-native-effort-v1-20261025T014743Z.p_kspq5v` completed both
allocations and139,272 searches. The original ingest stopped at `result/campaign`:
the remote reporter used its `/results` mount name and the local reporter used
the canonical extracted name. Download/checksum and measurements were intact.

The separate [data-only recovery helper](recover_campaign_identity.py) verifies
the checksum, archive/extracted data, pinned sealed package, submission/job
identity and full unchanged raw analyzer. It permits only that proven campaign
metadata reconciliation, followed by original strict parity for every other
field. It never edits the sealed package, raw results, criteria or gate verdict.
Four regression checks cover narrow recovery and rejection of unrelated changes.

The recovery and full fresh replay are already complete. No further user/Torch
commands or redownload are needed. Reproduction uses a fresh output directory:

```sh
cd /Users/danielarturi/Developer/JinyangLiWork
PYTHONDONTWRITEBYTECODE=1 agent/.venv/bin/python \
  agent/experiments/native-effort-frontier-v1/recover_campaign_identity.py \
  --archive trials/torch-reviews-native-effort-frontier-v1/reviews-native-effort-v1-20261025T014743Z.p_kspq5v.tar.gz \
  --output /tmp/b1b-replay-fresh-output
```

The [postrun receipt](../../docs/verification/native-effort-frontier-v1-postrun.json)
and [results report](../../../research/fannagent-native-effort-frontier-v1-results-2026-10-25.md)
record passing native conformance/reuse A/A, failed recall and forced640 wrapper
overhead, and failed activation A/A. Formal aggregate verdict:
`measurement_inconclusive`; no context qualifies and B1c stays deferred. Preserve
original execution. This completed status supersedes the pre-dispatch recipe
above; do not resubmit or repeat the campaign.
