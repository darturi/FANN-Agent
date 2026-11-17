# Amended M4 continuation awaiting approval

The context fix is qualified and the exact continuation is prepared. **No further paid Messages
request or development-data transfer has occurred.** The original two-request terminal episode
is preserved. This proposal continues its transcript and debt rather than starting a fresh budget.

| Contract | Value |
| --- | --- |
| Model / Messages endpoint | `claude-sonnet-5-5`, `https://api.anthropic.com/v1/messages` |
| Remaining paid requests | **At most four**, with the prior two retained toward six total |
| Original total ceiling | **$15**, zero overrun allowance and no retries |
| Already spent | **$0.038798**, retained with both original charge identities |
| Four further maximum reservations | **$8.24**, at $2.06 each |
| Maximum resulting cumulative commitment | **$8.278798**, below the original $15 ceiling |
| Output limit | 6,000 total tokens/request, including thinking/progress |
| Rates / inference | $2/million input, $10/million output; global, standard-only, between-tools thinking, high effort |
| Remaining domain tools / submissions | Eight tools; nine policy submissions, at most three/batch |
| Case / M5 bounds | At most 12 cases/explanation; at most three qualified M5 nominees |

The first continuation request is **42,382 bytes**, SHA-256
`016421c73832218fad8d71326df976e813f7ac8b943ac5e65e601f108ee6db3d`.
It is the exact request previously blocked by the old byte limit. No history is summarized or
deleted. The system prompt, initial instruction, five tools, inference parameters, evidence,
runtime policy language, recall scoring and uncertainty-aware selector remain unchanged.
The 18 locally prepared case examples are included as the outstanding tool responses.

## Context amendment

The old 50,000-byte operational cap is replaced with an **8MiB wire cap**, including the same
8,192-byte headroom. This is separate from the financial input bound and the model's token limit.
Financial reservations still use the entire 1,000,000-token input ceiling plus 6,000 output tokens.

Before each paid call, make at most one **free** POST to Anthropic's
`https://api.anthropic.com/v1/messages/count_tokens`, at most **four** for the continuation.
It receives the same model/system/tools/messages/thinking/output configuration, with signed
blocks unchanged. Reject estimates above **900,000 input tokens before reserving money**.
With 6,000 output tokens this leaves 94,000 tokens below the documented 1M context ceiling.
Token counting is an estimate; it does not replace the conservative full-model financial bound.
Count failures or changed terms stop the run without retry or paid dispatch.

Wire capacity is bounded independently: at most512KiB per accepted assistant message and per
returned feedback block, with eight remaining feedback slots. Cached tool IDs and malformed
final text consume feedback slots too, so idempotency cannot bypass the wire bound. These are
envelope checks; no tool answer or signed block is silently truncated. Oversized provider output
halts for audit with its charge reservation retained. Normal distinct tool calls keep the same
original twelve-tool cumulative quota.

Across the three assistant responses that can precede the last paid call, all eight remaining
feedback envelopes, prior transcript, wrapper margin and headroom, the structural wire bound is
**5,818,766 bytes**, below8,388,608. This certificate is conditional on the declared envelope and
feedback-slot caps; the separate token preflight protects model context. It is not a promise
about arbitrary oversized provider responses, discovery success or policy performance.

Official references: [token counting](https://platform.claude.com/docs/en/build-with-claude/token-counting),
[context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows),
[count API](https://platform.claude.com/docs/en/api/messages/count_tokens).
The API version remains2023-06-01. One free synthetic-only count request verified this version,
model and field combination; it contained no study data. No development count request has run.
Model/prices are checked again before actual continuation dispatch.

## Qualification and study scope

All **106 tests** pass, including migration without resetting charges, four additional ordinal
limits, count failure before reservation, exact count/request matching, signed-block continuity,
cached-ID feedback accounting, context envelope stops and approval tampering.

No-network qualification starts from the actual prior transcript and both real settled charges.
Four scripted rounds use all eight remaining tools and all nine candidate slots, including invalid,
duplicate, unsafe and unsupported programs, full nine-program comparisons and final submission.
The largest outgoing request is176,071bytes. All49 category/filter combinations are checked at
the twelve-case maximum. A separate all-filter unsafe fixture produces21 counterexamples/program
and repeats nine-program comparisons five times; its largest tool result is84,561bytes.
Full-size synthetic assistant/feedback envelopes also fit the structural bound. Known policies
and unsafe fixtures are qualification inputs only; none is supplied as a seed to the real model.

The original terminal Store, raw requests/responses, source packet and outcome remain unchanged.
Actual dispatch will fork the verified snapshot, retain the original charge IDs, transcript and
four tool receipts, and clear only the documented terminal/contract in that fork. The core
controller enforces six cumulative Messages requests and the same $15 ledger contract.

All450 exposed development groups, **all six scalar filters** (`743,527,310,192,108,32`) plus
unfiltered remain fixed. Exact truth is used only in offline recall scoring. Short serving results
retain their missing-neighbor penalties. Validation/test remain untouched and unavailable.
No arbitrary file, SQL, shell, network or hidden optimizer tool is given to the model.

## Review and authorization

Full artifacts live at
`trials/fannagent-benchmark-evaluation-v1/reviews-small/m4-context-amendment-v1/` in the workspace:

- `prepared/first-request.preview.json`: exact readable continuation request.
- `prepared/continuation-contract.json`, `bound-gates.json`: amended limits and unchanged evidence.
- `qualification-v1/receipt.json`, `feedback-extremes-v1/receipt.json`, `local-tests.xml`: qualification.
- `synthetic-count-endpoint-check/`: static synthetic request, HTTP200 and compatibility receipt.
- `package-freeze.json`: frozen source and artifact hashes to which approval must bind.

Approve **up to four further Messages requests and four free token-count checks**, using this
frozen amendment and permitted anonymized development feedback, with both prior requests and
$0.038798 charged against the original six-request/$15 cap. The original approval does not enable
this changed context contract or new count endpoint. No usable amendment authorization exists yet.
M5 remains a later development-only measurement step for actual eligible policies. No Torch
command is needed for this preparation or continuation.
