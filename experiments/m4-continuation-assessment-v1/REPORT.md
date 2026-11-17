# M4 completed: one zero-loss development policy, no qualified nominee

The approved continuation completed all four additional Messages requests and four free
token-count checks. The combined episode used **six Messages requests and $0.244308**,
including the original two requests/$0.038798. All charges settled; there were no retries,
uncertain calls, context failures or provider errors.

The agent proposed six valid policies. **Candidate6 was the only policy with zero raw-native
recall losses across all3,150 development query/filter cases.** It lacks qualified cost support
for an unfiltered observation path and cannot enter the frozen shortlist. The last response
evaluated three new candidates instead of making a final submission. The request limit therefore
closed the episode as explicit bounded abstention with **no M5 nominees**. A read-only diagnostic
of the frozen selector also admits no candidate, so the missing final submission did not conceal
an otherwise eligible shortlist. No candidate was exported as a finalist or promoted to Torch.

## Provider, context and accounting verification

Execution used commit`23ba475` and approved package SHA-256
`d51f61d67b503a6ede42729f3f6ddd9913fbfd093e1fe93c8542b83215a43234`.
The explicit user approval and package binding are retained. Fresh model/rate GETs matched the
frozen terms. The continuation fork retained both original charge IDs, settlements, exact
transcript and four completed tool receipts. The original terminal episode is unchanged.

| Cumulative request | Input tokens | Output tokens, including thinking | Settled cost | Action |
| --- | ---: | ---: | ---: | --- |
| 3 | 17,172 | 698 | $0.041324 | Evaluate candidates1–3 |
| 4 | 24,056 | 183 | $0.049942 | Invalid case request: `filter="group 399"` |
| 5 | 24,268 | 117 | $0.049706 | Twelve `votes32` lossy-prefix examples |
| 6 | 27,929 | 868 | $0.064538 | Evaluate candidates4–6 |
| Continuation | **93,425** | **1,866** | **$0.205510** | Four Messages calls |
| Whole episode | **110,859** | **2,259** | **$0.244308** | Six Messages calls |

All eight continuation POSTs returned HTTP200. Each token count exactly matched the following
Messages input usage. Standard/global inference and zero cache usage match the charge contract;
thinking output was included in usage. Complete signed thinking blocks and tool feedback pass
unchanged through the reconstructed transcript. The wire sizes were42,382/58,947/60,918/69,571
bytes, safely below the amended8MiB bound. The context amendment worked.

One `explain_cases` request supplied an anonymous group handle in the filter field. The host
returned the bounded validation error without reading another scope. That consumed one tool
and one paid turn. The episode ended at eight cumulative tools/feedback slots and six of nine
candidate submissions. Remaining money or unused candidate slots do not extend the consumed
six-request allowance. No seventh paid request or fifth development count check was made.

## All six policy results

Losses below count query/filter cases whose recall fell below that same case's raw native640
recall. The other five scalar filters continue natively when a policy has no rule for them;
all their450 cases remain in evaluation and in the all-six-filter objective.

| Candidate | Agent name | Unfiltered early stops | `votes32` early stops | Recall-loss cases | Cost support |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | `turnover0_gap64` | 311 | 185 | 8: six unfiltered, two votes32 | Unsupported |
| 2 | `turnover0_gap32_64` | 238 | 117 | 4: three unfiltered, one votes32 | Supported; fails quality |
| 3 | `turnover0_only64` | 106 | 0 | 1 unfiltered | Unsupported |
| 4 | `u_turn0_gap_td` | 199 | 0 | 1 unfiltered | Unsupported |
| 5 | `u_v32_turn0_gap_td` | 199 | 77 | 1 unfiltered | Unsupported |
| 6 | `u_v32_gap_high` | **135** | **41** | **0** | **Unsupported** |

Candidate6 stops at checkpoint64 for unfiltered and `votes32` when top-ten turnover is zero,
frontier gap is at least0.10 and tenth distance is at most0.34. The remaining five scalar
conditions retain native execution. Its stop counts are30% of unfiltered cases and9.11% of
`votes32` cases, or41/2700=1.52% of all scalar query/filter cases. These are stopping frequencies,
not measured latency savings.

Turnover at64 requires collecting the preceding scheduled top ten at32. The compiler correctly
requests rank/count observation mask3 at32 without a decision there. That path is runtime-valid,
but the cost evidence's supported unfiltered masks at32 are`[0,8,9,11,15]`: mask3 is absent.
The corresponding `votes32` path is supported. The cost evaluator reports the unfiltered
missing support rather than inventing its price. The only cost-supported candidate, candidate2,
has four recall regressions and fails the strict per-case quality rule.

## Conclusions and next steps

This run establishes that the repaired provider/context/accounting path works and that this
bounded agent episode discovered one zero-loss development rule. It does **not** establish
held-out robustness, actual speedup or success under the full frozen nomination contract.
All folds are exposed development diagnostics. A finite zero-loss replay is not a general safety
guarantee, and stopping on a small subset does not guarantee useful total latency improvement.

Keep the episode closed and preserve its negative/inconclusive nomination outcome. Do not
retroactively relax cost support, fit a replacement threshold, export the intermediate rule as a
winner, or spend unused money as if extra requests were authorized. Validation/test stay unopened.

Before another provider episode, improve the local interface prospectively: enumerate legal
filter values; permit bounded lookup of reported development counterexamples via a typed handle;
show measured cost-mask support; and show remaining request/tool slots with a reserved final
submission step. The invalid group-as-filter request and unclosed final batch are concrete
usability/closure shortcomings. These changes require a versioned rehearsal and future episode
contract, not edits to this completed transcript.

For candidate6, the narrow empirical next step would be a **prospectively frozen development-only
qualification of the missing unfiltered checkpoint32 observation-only path**, preserving the
agent's rule and all six scalar filters. That is more targeted than another generation round.
If it justifies expanding cost support, reconsider eligibility under that new contract and then
measure actual policy/matched controls. This would be a separate amended experiment, not a
retroactive success or M5 nomination from the completed M4 episode. No such Torch job or kit is
created here.

## Audit and provenance

`audit.py` opens the campaign read-only, rehashes all durable artifacts and verifies the original
and amended frozen packages. It reconciles both inherited ledger rows and all four new rows,
four count/message payload pairs, provider metadata, every tool answer and exact signed history.
Each policy is validated, recompiled and replayed. A separate first-satisfied-clause implementation
independently scores18,900 policy/query/filter cases and checks all per-filter and fold totals.
Cost/work feedback is recomputed from the same bound evidence. No SQL search or exact serving
call is used. The selector diagnostic does not submit or nominate a policy.

Full records live under
`trials/fannagent-benchmark-evaluation-v1/reviews-small/m4-context-amendment-v1/`:
`live-continuation/`, `authorization.json`, `assessment-v1/receipt.json` and `assessment.log`.
The study outcome is `freeze/m4-continuation-outcome-v1.json`. Compact receipt/approval copies
are in `receipts/`. Two rejected local audit preflights and source versions are retained in
`assessment-preflight-rejected/`; the final audit correctly identifies only the unfiltered path
as missing support. All actual provider records and policies remain unchanged.

All450 development groups and six scalar filters plus unfiltered remain fixed. Exact truth is
used only in the existing offline recall labels, with raw short-output penalties and no serving
completion guard. **Validation/test remain untouched.**
