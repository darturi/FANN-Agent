# M4 stopped at the host payload limit before policy generation

The approved frozen episode ran on `claude-sonnet-5-5` and terminated with an explicit bounded
abstention after two Messages requests. **No candidate policy was submitted or nominated.**
Actual settled usage cost **$0.038798**. There were no retries, uncertain charges, third request,
new SQL searches, serving exact-search calls or validation/test access.

This is a host protocol capacity failure on a valid tool sequence. It is not evidence that the
model failed to discover a robust policy: the episode ended before any policy could be evaluated.
The preparation rehearsal did not cover this allowed exploration sequence.

## What happened

Execution used the user-approved package from commit `ee1ad72`, package SHA-256
`1338109962e544a4f6e969b2ec33993139248ddfd1b13df67c8300fb9d025660`.
The explicit approval quote and exact package/contract hashes are retained in `authorization.json`.
Fresh authenticated model metadata and official pricing GETs matched the approved terms before
dispatch. The first request exactly matches the approved 14,472-byte payload.

| Request | Input tokens | Output tokens | Actual cost | Model actions |
| --- | ---: | ---: | ---: | --- |
| 1 | 5,797 | 47 | $0.012064 | `inspect_workload` |
| 2 | 11,637 | 346 | $0.026734 | Three `explain_cases` calls, six cases each |
| Total | 17,434 | 393 | **$0.038798** | Four valid tools; zero candidate submissions |

Both responses were HTTP200, the pinned model, global inference and standard service, with no
cache usage or thinking output tokens. Charges settled from the reported usage at $2/million
input and $10/million output. The ledger retains both $2.06 initial reservations and their smaller
actual settlements. All paid calls, transport attempts, response identities and durable records
reconcile. No request or charge was reserved for the blocked third round.

The initial orientation advised against redundant full inspection, but `inspect_workload` remained
a permitted tool. The host returned a 14,703-byte tool-result block. The next response validly
requested six examples in each of these categories:

- Preserving partial prefixes for `votes527`.
- Lossy prefixes for `unfiltered`.
- Qualified full prefixes for `unfiltered`.

The host prepared all 18 examples from the bound development evidence. Their three tool-result
blocks occupied 3,705, 4,247 and 4,239 bytes. The resulting next request would be **42,382 bytes**.
Adding the frozen **8,192-byte headroom** yields **50,574 bytes**, which exceeds the **50,000-byte
operational limit by 574 bytes**. The guard stopped before transport and reservation. Those
18 examples were never sent to Anthropic; actual egress was the approved initial orientation
and the aggregate workload inspection feedback.

The runner preserved the exact transcript and registry, recorded
`bounded_M4_abstention_local_contract_limit`, and issued no rescue request, as the frozen contract
requires. Its generic disposition field mentions M5, but **M5 is ineligible with no nominees**;
the verified assessment supplies the correct next step.

## What this establishes

The real provider path, approval/source binding, charge settlement, bounded tools, durable records
and pre-transport context stop worked. The remaining operational byte ceiling was too small for
one valid sequence that the host advertised. It was an application limit, not exhaustion of the
model's 1M-token context or the $15 budget. Signed thinking did not cause this failure.

The earlier no-network rehearsal exercised known candidate evaluation and nomination, rather
than the full range of unseeded evidence exploration. Its pass did not establish that all permitted
tool-feedback sequences fit the request limit. This preparation gap needs a local capacity check.

All six predicates (`total_votes >= 743,527,310,192,108,32`) and unfiltered remain in the fixed
450-group development evidence and initial payload. Exact truth remains offline recall scoring
only; short serving outputs and their recall penalties are unchanged. No policy quality,
latency benefit, robustness, validation selection or final test conclusion follows from this run.

## Recommended next step

Prepare a versioned amendment that makes feedback/context capacity consistent with the permitted
tool protocol. The full-model financial reservation is already safe at $2.06/request; the legacy
50,000-byte heuristic should not be treated as the financial token bound. Use compact,
nonduplicated workload views and explicit cumulative feedback capacity, then qualify the observed
sequence and worst permitted tool batches locally, including room for subsequent candidate
evaluation and final submission. Do not rely on a prompt asking the model to avoid a legal tool.

Keep this episode terminal and intact. Any explicitly approved continuation should retain this
transcript, two consumed requests and $0.038798 against the original cumulative six-request/$15
cap: at most four further requests, not a reset to six. Present the concrete amended contract and
local qualification before seeking that approval. No continuation is run by this assessment.
M5 development measurements become appropriate only after eligible actual policies exist.

## Reproducibility

Run `audit.py` from the existing `agent` virtual environment against a fresh audit destination.
It performs no network or database search and opens campaign state read-only. It verifies all
32 frozen source hashes and 65 preparation-artifact hashes, the actual approval, both wire
requests/responses, every charge and all ten durable artifact contents. It recomputes all four
tool answers from the same bound evidence and reconstructs the full transcript and blocked
request size. It freezes the live artifact hashes and result once.

Full records are under
`trials/fannagent-benchmark-evaluation-v1/reviews-small/m4-episode-v1/` in the workspace:
`live-episode/`, `authorization.json`, `assessment-v1/receipt.json` and `assessment.log`.
The study outcome freeze is `freeze/m4-episode-v1-outcome.json`. Compact outcome and approval
copies are retained in this directory's `receipts/`. The original proposal, pending specification,
source files and prior M0/M1/M2/M3 evidence remain unchanged.
