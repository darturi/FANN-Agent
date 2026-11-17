# M4 episode awaiting approval

Prepared November 16, 2026. **No generation has run and no development payload has left the
workspace.** This is a new authorization; the historical three-request episode is exhausted
at $0.725544 and contributes no unused requests to this episode.

The proposal sends the frozen compact development payload and permitted tool feedback to
Anthropic's first-party Messages API. The model chooses fresh hypotheses and thresholds within
the qualified causal policy language. The host evaluates them on existing offline development
evidence and applies the qualified uncertainty-aware shortlist rule. Any nominees still need
actual M5 program and matched-control measurements before a speed claim or final selection.

| Term | Frozen value |
| --- | --- |
| Provider / endpoint | Anthropic, `https://api.anthropic.com/v1/messages` |
| Model | `claude-sonnet-5-5`, pinned model ID |
| API version | `2023-06-01` |
| Inference | Global; standard-only service; `between_tools` thinking; high effort |
| New episode limit | **At most six Messages requests and $15 total**, zero overrun allowance |
| Output limit | 6,000 total tokens per request, including thinking/progress |
| Verified prices | $2 per million input tokens; $10 per million output tokens |
| Financial reservation | 1,000,000 input tokens plus 6,000 output tokens = **$2.06 per request** |
| Six maximum reservations | **$12.36**; actual reported usage is settled at the verified rates |
| Retries / alternate models | None; malformed replies consume requests; uncertain delivery stops dispatch |
| Domain tools / policy submissions | At most 12 tools, nine submissions including invalid/duplicate/repair slots, three policies per batch |
| Explanation / shortlist bounds | At most 12 anonymized cases per explanation and three M5 nominees |
| Operational request bound | Canonical request bytes plus 8,192 headroom at most 50,000; this is separate from the financial token bound |

Account availability was verified by an authenticated Models GET, returning this active model,
its 1,000,000-token input ceiling and the requested thinking/effort capabilities. Public official
documentation verifies rates and standard pricing across the full context window. This did not
test paid generation. Availability and terms are checked again before dispatch; changed terms
stop the episode. Client tools have no server-tool charges; caching, batch and fast modes are
outside this contract.

Official references: [Sonnet 5.5](https://platform.claude.com/docs/en/models/sonnet-5-5/overview),
[pricing](https://platform.claude.com/docs/en/about-claude/pricing),
[thinking continuity](https://platform.claude.com/docs/en/build-with-claude/thinking),
[pinned model IDs](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions).
The GET response and downloaded document bytes are retained with SHA-256 hashes.

## Data and feedback covered by this approval

The initial request is **14,472 bytes**, SHA-256
`e0f69f12b2b6c27b6de6ae25ce345b0f5cf45cf0a079f74745f701e8912a68b8`.
It contains the frozen system prompt, five typed client-tool definitions, policy primer and
compact per-filter development orientation. It supplies no prior policy as a seed.

The scope is the same 450 exposed development groups, **all six predicates**
`total_votes >= 743, 527, 310, 192, 108, 32`, and the unfiltered control. The complete bound
evidence remains local. Follow-up responses can contain anonymized development case handles,
prefix observations/features, raw-native and candidate recall labels, per-filter/fold quality
results, bounded counterexamples, measured-prefix work summaries and explicitly uncertain
cost guidance. Tool feedback comes only from that bound evidence. The five tools are
`inspect_workload`, `explain_cases`, `evaluate_candidates`, `compare_candidates` and
`submit_or_abstain`; the model has no arbitrary shell, SQL, file or network access.

Evidence identity:
`5b025e2b11662f20bf68986bee06851727a353c6e991ba75da62a06116dce07d`.
Source query IDs, vectors, exact neighbor lists and credentials are excluded. Exact search is
used only for offline recall scoring. Serving returns raw short outputs without exact repair.
**Validation/test stay untouched and unavailable to the episode.**

## Review the exact packet

The data packet lives at
`trials/fannagent-benchmark-evaluation-v1/reviews-small/m4-episode-v1/` relative to the workspace:

- `prepared/first-request.preview.json`: readable view of the exact canonical first request.
- `prepared/system-prompt.md`, `tools.json`, `initial-user-message.json`: individual payload parts.
- `prepared/development-summary.json`: compact per-filter evidence orientation.
- `prepared/episode-contract.json`, `execution-contract.json`, `model-config.json`: scope and limits.
- `provider/preflight.json`, `model-api-response.json`, official Markdown files: availability/rate evidence.
- `no-network-rehearsal/receipt.json`, `local-tests.xml`: preparation qualification.
- `package-freeze.json`: frozen source/artifact hashes; the approval must match its exact hash.

All 85 local tests pass. A separate two-response no-network rehearsal uses the actual bound
evidence and prepared prompt/tools, with a scripted model ID and fictional usage. It verifies
unchanged signed-progress continuity, bounded feedback, deterministic diagnostic nomination,
pending-approval blocking before credentials/transport/reservation and $15 accounting. Its
fixture policies are not new agent discoveries.

If capacity ends before a valid final submission, record abstention and retain the complete
registry. There is no extra rescue request or opportunistic promotion of intermediate results.
No new Torch submission is needed for M4 preparation or generation.

## Approval requested

Approve sending this frozen anonymized development payload and the permitted follow-up feedback
to Anthropic's Messages API using `claude-sonnet-5-5`, for a **new episode of at most six requests
and $15 total**, under the limits above. Approval enables only this episode. The pending
specification is not dispatchable; no usable authorization file is created before your reply.
