# Open development exploration within the cumulative dollar ceiling

The November 17 user amendment removes cumulative candidate-submission and
domain-tool-call caps. Model requests, token-count checks, candidate evaluations,
comparisons and inspections have no count ceiling. The same **$15 cumulative API
ceiling** includes the eight prior settled calls costing **$0.403114**, leaving
**$14.596886**. Every prior candidate, failure, tool receipt and exact conversation
is retained. Spending the full allowance is explicitly not an objective; the agent
may submit or abstain voluntarily whenever more investigation is unlikely to help.

This is a versioned continuation of the completed dollar-governed episode. The
completed M4 outcome, candidates 7/8, sealed M5 kit and all earlier source packages
remain immutable. The new runner uses a copy of the complete eight-call history.
Configuration and scripted qualification make no paid call, token-count request,
database search or holdout access. Future inference is a separate runner invocation.

## Controller and selection

`exploration_controller.py` versions the dispatch path while inheriting the settled
provider-accounting/round implementation. Tool and submission counters remain for
audit; neither can trigger exhaustion or closing. Invalid/duplicate/revised programs
remain recorded. `compare_candidates` accepts any nonempty registered-ID list that
fits the existing payload envelopes. A large comparison returns a bounded error
with a retained full artifact so the agent can request smaller views.

`selection.py` removes the nine-record admission limit without changing the quality,
cost-support, scalar-stop, canonical-deduplication, uncertainty or tie-breaking
rules. It checks lower-bound prefixes plus one possible upper-bound anchor, giving
the same exact certificate as exhaustive <=3-subset enumeration without cubic
growth in the registry size. Randomized comparisons against the frozen selector,
larger exhaustive pools and a 2,048-policy case verify this generalization.

These existing restrictions remain:

- At most three programs per evaluation batch and three live-measurement nominees.
  These are batch and downstream measurement limits, not cumulative search caps.
  More than three ambiguous eligible programs can still require uncertainty
  abstention; extra search never silently relaxes that certificate.
- Unchanged causal DSL, feature profile, compiler, full-development first-stop
  replay, complete prefix evidence and zero per-case raw-native recall loss.
- Unchanged cost-support requirements and one-native-percentage-point conditional
  shortlist regret limit. Estimates never establish measured latency improvement.
- All 450 development groups and all six scalar filters plus unfiltered retained.
  Exact truth is offline scoring only; validation/test and arbitrary SQL/files/
  shell/network remain outside the agent's tool interface.
- Existing 6,000 total output-token, 900,000 counted-input-token, 8 MiB request,
  512 KiB feedback, case-example and rule-complexity envelopes.
- One maximum-charge reservation before each paid call; funding for a closing call
  is preserved. Below two maxima, only submission/abstention is exposed. Three
  consecutive invalid final replies also enter closing. Uncertain delivery,
  provider/context failures and contract changes stop without automatic retry.

There is no new minimum number of candidates or tools, no target spend, no automatic
retry and no automatic generation after a live or protected evaluation result.

## Configuration and execution

From `agent/`, configuration was prepared and tested with:

```sh
.venv/bin/python -B experiments/m4-open-exploration-v1/configure.py prepare
.venv/bin/python -B -m pytest experiments/m4-open-exploration-v1/tests -q
.venv/bin/python -B experiments/m4-open-exploration-v1/qualify.py
.venv/bin/python -B experiments/m4-open-exploration-v1/configure.py seal
```

The sealed receipt records exact source/package identities and the real ledger
bridge. The active pointer is the study's `reports/active-provider-configuration.json`;
compact receipts are committed here. Full saved state remains under
`trials/fannagent-benchmark-evaluation-v1/reviews-small/m4-open-exploration-v1/`.

Verification: 16 focused tests and 115 historical regression tests pass, with
lint/format checks passing. The regression suites run in separate processes to
isolate their historical same-named `qualify` modules. The real-bound scripted
rehearsal carries forward all eight real charges and completes 22 additional
scripted responses, 20 cumulative candidate submissions, 32 tools and a 20-ID
comparison before voluntary submission. Its new candidates duplicate an existing
rule or are intentionally malformed; it establishes controller behavior, not
discovery or speed. An initial rehearsal's overly strict duplicate-ID assertion
is preserved under `qualification-rejected-alias-assertion/`; canonical rule hashes
verify the same nominees when lexicographic duplicate aliases change above nine.

`exploration_run.py` is the paid execution entry point. It loads the bound inherited
provider authorization, rechecks current model/rates, and creates a new versioned
execution directory. Importing, preparing, testing and sealing never invokes it.
