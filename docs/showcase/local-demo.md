# Local simulation

This demo uses the synthetic backend and the scripted model. It creates a new
temporary run and makes no provider or database call. Docker and a GPU are not
required. The initial dependency installation needs network access.

## Source installation

From a clone of the `portfolio-v1` snapshot, run:

```sh
uv sync --frozen --python 3.12
demo_dir="$(mktemp -d)"
export MSWEA_GLOBAL_CONFIG_DIR="$demo_dir/mini-config"
export MSWEA_SILENT_STARTUP=1
export LITELLM_LOCAL_MODEL_COST_MAP=True

uv run --frozen fannagent init --backend fake --output "$demo_dir/fake.yaml"
uv run --frozen fannagent doctor "$demo_dir/fake.yaml"
uv run --frozen fannagent prepare "$demo_dir/fake.yaml" --run "$demo_dir/run"
uv run --frozen fannagent run "$demo_dir/fake.yaml" --run "$demo_dir/run" --steps 2
uv run --frozen fannagent resume --run "$demo_dir/run"
uv run --frozen fannagent evaluate --run "$demo_dir/run"
uv run --frozen fannagent experiments --run "$demo_dir/run"
uv run --frozen fannagent report --run "$demo_dir/run"
uv run --frozen fannagent status --run "$demo_dir/run"
uv run --frozen fannagent clean --run "$demo_dir/run"
```

`init` generates a configuration with `backend.name: fake` and `model.model:
scripted`. Keep that configuration for this example. Initialization refuses to
overwrite an existing configuration.

## Expected observations

| Command | Relevant output |
|---|---|
| `doctor` | `ready: true` |
| `run --steps 2` | `status: interrupted` |
| `resume` | `status: frozen` |
| `evaluate` | `status: accepted`, `valid: true`, `simulated: true` |
| `experiments` / `status` | Three completed experiments, no open experiment |
| `status` | `budget.committed_usd: "0"`, `budget.calls: []` |
| `report` | A path to `run/REPORT.md` and the simulated result |

Hashes, generated IDs, temporary paths, and elapsed times can vary. The accepted
result is for the scripted synthetic example. It does not demonstrate model
discovery or a database speedup. See the [annotated real run](agent-run.md) for
existing provider-backed behavior.

Cleanup removes owned operational resources and retains state and the report.
Generated files are under `$demo_dir`, including the mini-swe-agent configuration.
The demo does not need `trials/`, other repositories, source databases, local
installation bundles, or archived images.

## Installed-wheel check

The [CI workflow](../../.github/workflows/ci.yml) builds the source distribution
and wheel, exports locked dependency constraints, installs the wheel into a new
environment, and runs this lifecycle outside the checkout. That checks discovery
and packaged assets without relying on an editable import or a sibling backend.
See [validation](validation.md) for observed results and qualification limits.
