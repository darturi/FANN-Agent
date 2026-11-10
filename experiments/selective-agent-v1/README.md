# Selective agent with one measured feedback round

This is one engineering episode, not a replacement A/B experiment. The original
generation A/B remains inconclusive with zero complete pairs. Canonical serving
acceptance remains false. The previous confirmation sample stays consumed.

The goal is an agent-produced composite policy that measurably lowers latency
while preserving recall. It chooses a mask over actual predicates, one of the
19/23/34-feature profiles, and one guarded stop/continue tree. A native branch
issues ordinary SQL before unnecessary tree compilation, installation or feature
collection. A continue leaf still pays policy costs. All three filters remain
in all reports, including genuine native bypasses and their measured overhead.
Other k values also default to native; this study's learned scope is k=10.

## Fixed final gates

- Valid complete top-10, native mean recall >=.95 in every filter.
- Lower 95% policy-minus-native recall bound >=-.005 (0.5 percentage points loss)
  overall AND in unfiltered/votes32/votes108.
- Upper 95% mean log latency-ratio bound <0 in activation AND reuse, overall.
- Vector-group bootstrap, 10,000 resamples, seed 20261019. Repetitions, filters and
  allocations remain in their vector cluster; they are not independent vectors.
- Development admission to confirmation reserves -.0025, requires complete actual
  timing and at least one policy stop. This does not tighten the final gate.

## Data and provenance

The independently verified feature/data campaign supplies 200 development vectors
and 600 cases, including the former 40-vector calibration sample. Five balanced
hash-ordered group folds are descriptive checks on exposed development data.
The 60 unexecuted evaluation vectors become this new protocol's single-candidate
confirmation entitlement. Their values are not read into an agent view or a
development package. Another 37 vectors remain reserved. Canonical workloads
are never executed. Seeds are explicitly credited: an earlier agent export and
the conventional S160/risk1280 tree. Reuse is not an independent discovery.

The trusted first-stop beam growth is copied from the audited study. Profile/mask
input mapping is explicit. Static/progress fitting uses its measured fixed-stop
proxies; light19 fitting uses normalized physical-work savings because matching
cost measurements do not exist across all 200 vectors. Zero bypass utility is a
ranking convention only. Routing cost and fitted-policy latency are unknown until
actual timing. Poor proxies/known recall losses do not block pilot admission.

## Agent and stage transitions

`prepare` creates one fresh bound episode with a separate ledger. `propose` allows
at most eight provider attempts and three semantic exports, ending only at the
agent's explicit `pause`. Package and run the pilot, download its archive, and
`ingest` with trusted local code. `resume` is the same episode's only feedback
response, at most four attempts. The agent explicitly selects an unchanged export,
exports one sole revision, or abstains, and calls `finish`.

A revision receives its own actual development measurements. No second feedback
round or host replacement is allowed. The confirmation package can be built only
for that final selection after a verified development pass. Its complete artifact,
runtime and provenance are frozen. Torch reserves the 60-vector entitlement before
dispatch; it cannot be reused after failure. There are no model calls afterward.

## Measurement and limits

Reuse exactly the existing physical index, pinned image and verified x86 module;
no engine or dataset rebuild. `ef_search=640`, `k=10`. Each stage has three serial
four-CPU/32-GiB/two-hour allocations, a 6600-second work deadline and <=70k
backend/reference searches per allocation. No phase can be reuploaded to evade a
stage reservation. Exactly three initial, up to three revision and up to three
confirmation allocations; maximum nine and 299,529 searches.

The actual module is `modules/vector.so`, pinned by `module_sha256` to the
verified e7dcace1… build. The inherited `original_module_sha256` field identifies
historical preservation evidence, not the binary executed by this study.

| Stage | Maximum arms | Searches/block | Retained pairs/block | Warmup pairs/block |
|---|---:|---:|---:|---:|
| Pilot | 8 | 56,721 | 19,200 | 4,800 |
| Revision | 4 | 30,321 | 9,600 | 2,400 |
| Confirmation | 3 | 12,801 | 4,860 | 540 |

Development arms are agent candidates, same-mask/profile/conditions matched
continue controls, routed-native control and a lightweight sparse hindsight
oracle. Confirmation omits the oracle. Each case/arm/block retains one activation
pair, discards one warmup pair and retains three reuse pairs (eight in
confirmation). Pair order and arm order are predeclared/randomized. Getter
qualification is 921 searches per allocation, using development fixtures only.
Control SQL/installation counts are separate from backend/reference searches.

Cold means absent policy preparation/installation, not cold database buffers.
All newly introduced validation, owned artifact preparation and query routing
are charged exactly once in addition to the frozen ANN timer. Compilation,
installation and feature work remain inside that ANN timer. Outer call time is
also retained. No overhead is subtracted. Bypass has null policy activation,
work and checkpoint counts. Trace requests preserve native routing. Errors fail
the study rather than invoking a successful fallback.

Provider calls are Mac-only, standard global Anthropic Sonnet 5.5, after unpaid
official pricing and authenticated model-availability checks. Hard cap $10 new
spending, $6 phase A/$4 phase B, eight/four attempts, no retries. Each request is
reserved before sending; failed/uncertain charges remain committed. Original
ledgers and caps stay immutable. Sandbox: no network, no credentials, read-only
evidence, private workspace, 2 CPUs/4 GiB, 120 commands and 3600 active seconds
across both phases. Torch wait time does not count toward active analysis.

## Mac commands

Use the existing Python runtime:

```bash
cd /Users/danielarturi/Developer/JinyangLiWork
agent/.venv/bin/python agent/experiments/selective-agent-v1/study.py prepare
agent/.venv/bin/python agent/experiments/selective-agent-v1/study.py preflight
agent/.venv/bin/python agent/experiments/selective-agent-v1/study.py propose
agent/.venv/bin/python agent/experiments/selective-agent-v1/study.py package --stage pilot
```

The last command prints the frozen package, archive, checksum and stage-specific
`COMMANDS.txt` with exact Mac upload/download and Torch submit/status/collect
commands. It uses the existing verified DTN transfer options and durable campaign
bindings; no shell variable from an earlier login is required.

After downloading and ingesting pilot results using that generated command file:

```bash
agent/.venv/bin/python agent/experiments/selective-agent-v1/study.py resume
agent/.venv/bin/python agent/experiments/selective-agent-v1/study.py status
# Only if the agent made a revision:
agent/.venv/bin/python agent/experiments/selective-agent-v1/study.py package --stage revision
# After the selected primary has a verified development pass:
agent/.venv/bin/python agent/experiments/selective-agent-v1/study.py package --stage confirmation
```

Supplying `--run /absolute/run/path` selects the exact episode; omitting it uses
the durable binding. Each run retains an immutable local controller/core snapshot;
commands delegate to it through the Torch wait. A censored/interrupted episode
does not silently restart. The existing mini-swe-agent local environment is loaded
for its configured Anthropic credential. Otherwise set ANTHROPIC_API_KEY only in
the Mac process; never include credentials in
commands, files submitted to Torch, or results. Native validation is required
before any paid call. Unit/fake-provider/native fixture tests make zero paid
calls and do not create scientific candidates. Synthetic packages cannot submit.

Every returned archive is checksum checked and safely extracted as data only.
Collection recomputes coverage, first-stop proofs, exact recall arithmetic,
counts, timing components and bootstrap gates. The Mac uses the original sealed
local package and never executes returned code. Reports retain failures and
abstentions; no automatic new labels, extra model calls or deployment follows.
