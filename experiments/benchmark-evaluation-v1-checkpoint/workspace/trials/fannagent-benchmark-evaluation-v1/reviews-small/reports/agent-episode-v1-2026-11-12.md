# Fresh agent episode v1: explicit abstention

Outcome: the authorized fresh agent episode ran and completed with an explicit first-round abstention. No new policy was proposed or selected. This is a bounded negative generation result, not a provider/schema failure, not evidence that no useful policy exists, and not a held-out benchmark result.

## Authorization and input boundary

The user explicitly approved the prepared anonymized development features, recall labels, timings and follow-up feedback for Anthropic's Messages API using `claude-sonnet-5-5`, up to three rounds and $15. The approval is recorded with the exact first-request hash. The earlier automatic-review rejection remains in the provenance; after this explicit approval, dispatch succeeded without changing the prepared first payload.

The request contained 3,150 query/filter cases from 450 frozen development groups, all six scalar filters plus unfiltered, causal checkpoint features and saved stop/guarded-parent labels. No review text, query vectors, source query/result IDs, credentials, validation or test cases were in the payload. The five folds are development diagnostics, not independent validation. The guarded native640 parent, common guard and query split remain unchanged.

## Execution and accounting

| Item | Result |
| --- | --- |
| Model | claude-sonnet-5-5 |
| Inference | global, standard-only, between_tools/high |
| Paid requests | 1 |
| Input tokens | 278,319 |
| Output tokens | 457 |
| Charged cost | $0.561208 |
| First-round conservative reservation | $1.030534 |
| Episode ceiling | 3 requests, 9 proposals, $15 |
| Request completion | end_turn |
| Parsed policies | empty list; valid explicit abstention |
| Remaining rounds | not dispatched |

The driver was predeclared to terminate when the model returns an empty policy list. Accordingly, it did not spend the remaining allowance to rescue the result. The saved request matches the approved first payload; response identity, usage, charge calculation, request/response hashes and frozen empty proposal pool were independently checked. There are no uncertain calls or live new-policy timing results. See `../development/agent-episode-v1/episode-verification.json`.

## Interpretation

The model cited the evidence table's size/noise and uncertainty about finding feature thresholds that preserve every query's recall. It returned no candidate for the evaluator to test. The prompt comprised 278,319 input tokens; this is a plausible evidence-presentation/method bottleneck, not an empirical impossibility result for the available signals.

A subsequent data-only diagnostic counted queries with at least one already verified forced stop whose recall is no worse than the guarded parent:

| Condition | Queries with some recall-preserving checkpoint /450 |
| --- | ---: |
| unfiltered | 425 |
| votes743 | 65 |
| votes527 | 136 |
| votes310 | 249 |
| votes192 | 298 |
| votes108 | 350 |
| votes32 | 407 |

There are 1,930 such query/filter cases out of 3,150 (1,505 out of 2,700 scalar-filter cases). These choices use exact outcome labels retrospectively. They are not an executable rule, do not establish that causal features separate safe from unsafe cases, and do not establish deployable latency savings. Cross-phase forced/no-op timings remain only development cost surrogates. No new policy was hand-designed to replace or conceal the agent's abstention.

## Disposition and next research step

Preserve the failed episode, retain the guarded native640 parent, and leave validation/test untouched. The next method revision should address the demonstrated presentation/selection bottleneck: compact filter-specific summaries and focused failure examples, with a bounded local rule-evaluation tool rather than one large raw table. Such a revision must be versioned and distinguished from this episode; unused budget does not turn this recorded abstention into success. Do not relax recall/completeness or select a final policy using only the existing cost proxy.

The current episode is complete. There is no candidate to compile, validate or test from it, so the generic next-step field in the immutable driver summary is superseded by this explicit disposition. No additional provider or ANN/exact calls were used for the post-abstention diagnostic.

## Source artifacts

- `../development/agent-episode-v1/external-payload-approval.json`
- `../development/agent-episode-v1/round-1/request.json`, `response.json`, `settlement.json`, `parsed-proposals.json`
- `../development/agent-episode-v1/episode-summary.json`, `episode-verification.json`, `proposal-pool-freeze.json`
- `../development/agent-episode-v1/post-abstention-opportunity-audit.json`
