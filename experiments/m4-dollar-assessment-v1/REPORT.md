# Dollar-governed M4: two submitted development nominees

The resumed agent explicitly submitted **candidate7 and candidate8**, and both satisfy the frozen
development quality and cost-support gates. Each preserves raw native640 recall on all3,150
query/filter cases from450 exposed development groups. Both are formally frozen for M5
development measurement. **No actual latency improvement or held-out robustness is established.**

The agent used two further Messages calls and two free token-count checks. Cumulative spending,
including all six earlier calls, is **$0.403114 across eight Messages calls**, within the original
$15 ceiling. The agent ended through a valid explicit submission with research resources and
money remaining. No request-count cap caused termination.

## Policies and qualification

Both policies decide only at checkpoint64, using frontier gap and tenth distance. They contain
rules for unfiltered and `votes32`; the other five scalar filters continue natively and all their
cases stay in the primary all-six-filter evaluation.

| Formal nominee | Conditions at checkpoint64 | Unfiltered stops /450 | `votes32` stops /450 | Recall-loss cases /3150 |
| --- | --- | ---: | ---: | ---: |
| candidate7, `u_v32_gap_td_noturn` | gap>=0.10 and tenth_distance<=0.34 | 135 | 41 | **0** |
| candidate8, `u_v32_gap_td_noturn_strict` | gap>=0.12 and tenth_distance<=0.33 | 102 | 22 | **0** |

Neither policy uses turnover. The compiler derives zero observation at16/32 and rank/count plus
decision mask11 at64 for those two conditions; other predicates have zero observation masks.
These masks are all covered by qualified cost evidence. Missing feature values make comparisons
false, so partial results retain native continuation rather than being repaired by exact search.

Candidate7 makes the same stop/continue decisions as the prior candidate6 on this development
corpus, while removing its checkpoint32 observation dependency and turnover feature. That resolves
candidate6's cost-support obstacle through a new policy chosen by the agent, without a host
threshold rewrite or relaxed gate. This equivalence is observed on development only.

The first six policies and their outcomes remain unchanged. All eight loss counts independently
reproduce as8/4/1/1/1/0/0/0. Candidate6 remains excluded for unsupported cost estimation; candidates
1–5 remain excluded for quality. The deterministic interval selector admits7/8, retains both and
reports conditional regret bound0 within its engineering interval-box assumptions. It makes no
claim that actual future measurement noise or costs lie inside those envelopes.

## Cost guidance is not measured speed

| Nominee | Primary surrogate/native ratio | Engineering interval |
| --- | ---: | --- |
| candidate7 | 0.99530 | [0.95994,1.03067] |
| candidate8 | 0.99850 | [0.96313,1.03386] |

The point centers correspond to roughly0.47% and0.15% primary cost reductions, and both intervals
include native's ratio1. These are conditional surrogate values, not measured speedups. The
point-model precision failure remains preserved. Stronger unfiltered proxy gains do not replace
the primary all-six-scalar objective. Actual observation overhead and matched-control timing may
still favor native. Zero losses on exposed development do not establish unseen-query safety.

## Provider and dollar ledger

| Cumulative call | Action | Input tokens | Output tokens including thinking | Actual settled cost |
| --- | --- | ---: | ---: | ---: |
| 7 | Evaluate the two new policies | 34,476 | 647 | $0.075422 |
| 8 | Explicitly submit both policies | 39,252 | 488 | $0.083384 |
| This continuation | Two Messages and two free count checks | 73,728 | 1,135 | **$0.158806** |
| Entire episode | Eight Messages calls | 184,587 | 3,394 | **$0.403114** |

All four new POSTs returned HTTP200. Count estimates matched actual input usage exactly. Usage
stayed within the pinned model, global/standard service, zero-cache and6000-total-output contract.
All eight ledger entries are settled with zero uncertainty or retry. Prior charge identities,
six candidate records and full signed history remain intact. Fresh model/rate GETs passed.

Both calls used the research request profile; the second voluntarily called `submit_or_abstain`.
The funded closing-only fallback was available but not needed. The final state contains eight
candidate submissions and ten cumulative tools, below the nine/twelve scientific limits. Remaining
money is$14.596886; the budget is a ceiling, not a spending target.

Execution used commit`f85f9d6`, package SHA-256
`081dd13927c0621afc17259a78b5380b161ebb1b0c346fecb465fe3c4e328af7`, and the explicit resume
instruction stored separately in `execution-authorization.json`. The prior configuration approval,
six-call closed outcome, source packets and all protected outcomes remain unchanged.

## Independent audit and frozen export

`audit.py` verifies the package/approval and all50 durable artifacts, eight charges, two new
count/message pairs, every new tool answer and exact signed transcript. It validates and regenerates
C source/manifests for all eight policies, replays them, and uses the separate first-satisfied-clause scorer
to check25,200 policy/query/filter scores. Quality/cost/work feedback and the exact deterministic
submission certificate reproduce. The two new rule objects exactly match the provider's parsed
proposals; no policy repair, fit or source substitution occurs. Native-module execution remains M5 work.

The audit freezes the formally submitted canonical policies in `assessment-v1/nominees.json`
under the study's `m4-dollar-budget-v1/` directory. Its SHA-256 is
`48bf2eca1a66950a68701cd89cd646daa499f9243223a6b9301ea7f2d9befef1`.
The receipt SHA-256 is
`87328f79ec8cd0354bc03111951763bda48863dde5bfae246f034ef3a6b36948`, referenced by
`freeze/m4-dollar-outcome-v1.json`. Compact copies live in this directory's `receipts/`.
The initial standalone audit import rejection is retained in `assessment-import-rejected.log`;
no provider request or benchmark search was repeated for that repair.

## Next step

Prepare M5 to qualify and time these exact two policies on frozen development, with native and
matched continue-only controls, counterbalanced execution/reader roles, CPU placement and work
counters. Retain all six scalar conditions and the unfiltered control. Measure complete request
cost and actual recall before choosing a winner; native remains a valid outcome. The current
surrogate centers suggest modest primary opportunity, so no positive performance conclusion is
prespecified.

This task freezes the nominees and audit; no Torch kit or job is launched. Full validation-selection
and test comparison pools are later protocol gates. **Validation/test remain untouched. Exact
truth remains offline scoring only, with no serving completion guard.**
