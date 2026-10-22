# Portfolio snapshot validation

Prepared October 22, 2026. The candidate retains the committed runtime and
learning tools inherited by `docs/application-ready`. The only runtime-source
edit in the publication pass wraps one overlong controller condition; its parsed
syntax tree matches the original. Prompts, policies, datasets, statistical gates,
test implementations, and original research artifacts were not changed.

## Local checks

Verification used a temporary clone and a new locked environment on macOS ARM64,
Python 3.12.7, and uv 0.11.14. No test outputs were written to the research checkout.

| Check | Observed result |
|---|---|
| Ordinary core tests | 209 passed in the sandbox; the two socket tests were blocked by its socket-binding restriction and both passed when rerun with local socket permission. One integration test was deselected. |
| Ruff, `src tests` | Passed after the formatting-only line wrap |
| Public SDK typing | Passed for 17 source files |
| Source distribution and wheel | Built successfully |
| Generated fake-config lifecycle | Initialization, doctor, preparation, interruption, resume, evaluation, experiment inspection, reporting, status, and cleanup passed from outside the checkout |
| Installed-wheel lifecycle | Passed in a new runtime-only environment outside the checkout; packaged fake template and MIT license were present |
| Packaged attribution | A subsequent isolated rebuild includes both `LICENSE` and `NOTICE.md` under the wheel's license directory |
| Demo acceptance | `accepted`, `valid: true`, `simulated: true`; three completed experiments |
| Model ledger in the demo | Zero committed model charges, empty call list |
| Existing real-run documentation | 23 source hashes, 31 field projections, 37 exact excerpts, and ten assistant/action matches were checked during its preparation |
| History credential screen | 216 reachable historical blobs, 2,527,881 bytes; no matches for the provider/GitHub/AWS key, private-key, or credential-bearing PostgreSQL URL patterns checked |

The history check is rule-based screening, not a guarantee that every possible
secret format is detectable. Historical reports retain local/HPC provenance paths
and external workspace links; those are not inputs required by the demo. The
portfolio entry points and curated trace use repository-contained evidence.

## Continuous integration

The [CI workflow](../../.github/workflows/ci.yml) checks Python 3.12 and 3.13 on
Linux. It installs the frozen dependency lock, runs ordinary tests, lint and SDK
typing, builds both distributions, installs the wheel into a separate environment,
and verifies the no-key lifecycle outside the checkout. Actions are pinned to
verified upstream release commits and have read-only repository permission.

The [hosted run for `2a38258`](https://github.com/darturi/FANN-Agent/actions/runs/39829430205)
passed both Python versions: ordinary tests, lint, SDK typing, distribution builds,
and the installed-wheel no-key demo. The initial workflow was rejected before any
job ran because temporary runner configuration was referenced at the job level;
initialization now occurs in a runner step. No application behavior was changed.

This validation document and the notice filename were finalized after that run.
The final source is checked again by the same workflow before the core portfolio
tag is published. GitHub attaches those checks to the selected commit.

## Public source checks

The core portfolio branch and the companion's `portfolio-v1` tag are publicly
accessible. An unauthenticated HTTPS check resolved all 54 distinct documents,
source references, evidence files, and companion links in the primary reading path.
The final core tag is checked separately during publication.

Fresh public sibling clones also completed the companion's frozen source install
and backend discovery: core `0.2.0` and pgvector extension `0.1.0`, with `fake` and
`pgvector` registered. That check made no database or provider calls. The companion
tag points to `05e5450`, which retains runtime source from `09590fd` and adds only
its README and MIT license. No new native qualification is claimed.

## Qualification boundaries

The scripted demo verifies a synthetic lifecycle, not database performance or
model-directed discovery. The [annotated real run](agent-run.md) documents existing
provider-backed behavior using a specialized offline proposal runner. The
[results summary](../results.md) reports existing timing studies and their failed
held-out recall gate.

This release does not rerun paid models, native database fixtures, Torch jobs,
physical restore, production deployment, or broad engine/hardware qualification.
The separate pgvector source retains its earlier qualification records and limits.
Public package-registry or image publication is outside this portfolio snapshot.

The selected source is intended to be linked through the `portfolio-v1` tag.
`main` and the active research worktree remain separate from publication work.
