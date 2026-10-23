# Portfolio snapshot validation

Prepared October 22, 2026. The candidate retains the committed runtime and
learning tools inherited by the branch now named `public-facing`. The only runtime-source
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

The [hosted run for the final release commit `6918fba`](https://github.com/darturi/FANN-Agent/actions/runs/39830411124)
passed both Python versions: ordinary tests, lint, SDK typing, distribution builds,
and the installed-wheel no-key demo. The initial workflow was rejected before any
job ran because temporary runner configuration was referenced at the job level;
initialization now occurs in a runner step. No application behavior was changed.

That exact commit is published as `portfolio-v1`. The wheel includes the MIT
license and upstream attribution notice. This completion record was added on the
documentation branch after publication; the release tag remains unchanged.

## Public source checks

Both repositories' `portfolio-v1` tags are publicly accessible. The final
unauthenticated HTTPS check resolved all 57 reading-path links, including source,
evidence, notices, companion source, and CI. A fresh unauthenticated core tag clone
resolved to the exact commit tested above. The README commands also passed from
a fresh public clone of that commit, with three completed experiments, simulated
acceptance, zero model charges/calls, and a report retained after cleanup.

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

The selected source is published at the [`portfolio-v1` tag](https://github.com/darturi/FANN-Agent/tree/portfolio-v1).
`main` and the active research worktree remain separate from publication work.

## Portfolio narrative update — October 23, 2026

The `public-facing` narrative now foregrounds the author's experimental
approach and agent design: architecture decisions, the stopping oracle,
evaluation methodology, workload, and the connection from an agent export to
measured database latency reductions. The original `portfolio-v1` tag and its
release checks above describe the earlier frozen publication.

Verification for this documentation update checked 133 local reading-path links,
Markdown fences and JSON examples, ten original source-file hashes, both query
inventory hashes, and the selected policy's lineage. The projected inventories
contain 300 training and 180 held-out cases in 100 and 60 disjoint vector groups;
all three filter variants of each group use the same vector. The original
training corpus contains 2,397 stop labels and 19 qualified features.

The results tables were formatted directly from the original verification JSON.
Absolute timings, percentage reductions, recall values, per-filter reductions,
and candidate-specific timing-pair counts were checked against those records.
The original policy tree in the curated agent trace matches the frozen timing
candidate's fields, and its policy hash matches both measurement stages.

Runtime source, tests, dependency files, original verification records, and the
curated agent trace are unchanged. No model call, database execution, fitting,
or scientific reanalysis was performed. The runtime release suite was not rerun
for this documentation-only revision.

## Documentation and installation sync — October 23, 2026

Selected documentation updates were copied from `main` at `894e59d` into
`public-facing`: complete source-clone instructions in the local demo, a clear
distinction between the public source installation and locally assembled bundles,
direct source/test links in the engineering summary, and contribution wording.
The public-facing narrative, research results, and evidence remain unchanged.

Both installation guides and the contribution page match the source commit.
The first-run shell blocks match `main` exactly. Verification resolved 166 local
reading-path links, syntax-checked six shell blocks, parsed JSON examples, and
checked Markdown fences and whitespace. Official PyPI package-record endpoints
returned HTTP 404 for both `fannagent` and `fannagent-pgvector` on this date.

All writes were restricted to five documentation files in the public-facing
checkout. No command ran in the development checkout or experiment directories;
no environment was installed or rebuilt. Runtime source, tests, dependencies,
experiment files, recorded results, evidence, `main`, and the development branch
were not changed. The runtime suite and database/model workflows were not rerun.
