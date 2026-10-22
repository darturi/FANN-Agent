# Annotated real agent run: investigate, revise, export

**One completed provider-backed conversation wrote its own analysis, encountered
a host-rejected policy, revised it, and exported six research proposals.**
It finished with an explicit statement that no policy was accepted.

This walkthrough uses existing records from `pair-0-exploratory` in the
`aggressive-policy-proposals-v2` study. The companion
[curated trace](agent-trace.json) contains selected command excerpts, saved host
assessments, the representative policy, and source hashes. No model request,
database operation, fitting procedure, or scientific analysis was rerun to
prepare these documents.

[Showcase overview](README.md) · [Agent architecture](../agent-design.md)

## Run identity and scope

| Item | Saved record |
|---|---|
| Conversation | `pair-0-exploratory`, exploratory condition, pair 0 |
| Recorded date | October 20, 2026, America/New_York |
| Model identifier | `anthropic/claude-sonnet-5-5`, as recorded in the historical configuration |
| Provider attempts and shell commands | 10 settled attempts; 10 commands |
| Recorded model API cost | $0.530724; infrastructure costs excluded |
| Limits | $1.06 conversation cap, 12 provider attempts, 120 commands, 60 seconds per command |
| Evidence supplied | 300 training query/filter cases, 100 vector groups, 2,397 previously measured stop outcomes, 19 qualified features |
| Terminal status | `completed`, with six exported proposals and `canonical_acceptance_established: false` |
| Archived source identity | Sealed 228-file manifest, SHA-256 `508d624fef85724e52b2424b87c515a9be035ad5534e6f7d5e414b656740bde6` |

This study used a specialized proposal runner that called the core
`BudgetedModel` and offline policy evaluator. It analyzed saved training evidence
inside a command sandbox. It was not a new invocation of the ordinary
`prepare/run/evaluate` workflow, and it did not exercise every mechanism described
in the general architecture document. In particular, the standard guided
experiment journal and deployment workflow are not claimed as events in this run.

The archived package is identified by its sealed source manifest. A single
historical Git commit is not established by the selected records; the current
documentation branch is not presented as that historical source revision.

## Task and working question

The supplied task asked for a portfolio of conservative, intermediate, and
aggressive stopping policies. Structurally valid research proposals could include
known recall losses. Exporting them did not waive the final recall and measured
latency requirements. Confirmation data and serving operations were unavailable.

The startup context described feature types, the outcome schema, and the existing
five vector-group folds. The supplied helper handled typed policy syntax and tool
transport; it supplied no thresholds, fitter, or selection rule. The model then
wrote Python to inspect outcomes, scan thresholds, simulate policies, and fit
staged rules.

An editorial description of the working question is: **can checkpoint-specific
progress features identify useful early stops more selectively than an
unconditional fixed stop?** This summarizes observable actions and submitted
rationales. It is not a reconstructed private thought process or a claim that
this specialized runner registered a formal hypothesis before analysis.

## The ten-step sequence

Each row corresponds to one saved model-selected shell command. The numbered
`steps` in the [trace](agent-trace.json) identify its assistant tool call, command
record, exact excerpts, and editorial annotation.

| Step | Model-selected action | Recorded observation or consequence |
|---|---|---|
| 1 | Read the evidence guide and tool contract. | The guide specified training-only evidence, retained invalid attempts, receipt-based exports, and a maximum total decision depth of four. |
| 2 | Inspect the corpus schema and syntax helper. | The output counted 100 cases in each of `unfiltered`, `votes32`, and `votes108`. |
| 3 | Inventory features, checkpoints, and existing stop outcomes. | The output listed the 19 qualified features and the available measured checkpoints. |
| 4 | Write a fixed-checkpoint comparison by filter stratum. | The model's own analysis printed different recall damage across strata, including a large loss for early unconditional stopping in `votes108`. |
| 5 | Write local preparation code joining features and outcomes by checkpoint ordinal. | This prepared the model's analysis rows from the saved evidence. Missing outcomes were not newly measured. |
| 6 | Write a feature-threshold scan. | The output listed candidate feature conditions and their estimated tradeoffs at several checkpoints. |
| 7 | Write local policy simulation and import the typed syntax/transport helper. | The model could inspect a composed stopping rule using its own analysis code. This output was not the host's acceptance decision. |
| 8 | Write a staged fitter and use the supplied vector-group folds. | Its printed cross-validation estimates exposed recall losses, including a weaker `votes108` result. These are saved model-written analysis outputs, not a new independent validation performed for this page. |
| 9 | Send six candidate policies to the host's `archive` operation. | Five were structurally valid. The four-stage candidate returned `valid: false` and a receipt; its saved host record identifies a decision-depth violation. |
| 10 | Read the saved failure response, replace the four-stage candidate with a three-stage version, select valid receipts, export six proposals, and call `finish`. | The replacement was valid for research admission. The tool reported six exports and a completed conversation; acceptance remained false. |

All ten shell commands returned exit code zero. A shell exit code did not imply
that every domain-tool request inside it succeeded: step 9 contained the rejected
policy. Retaining the structured tool result made that distinction inspectable.

## The rejection and revision

The rejected policy was `aggr_S8_32_64_128_t008`. Its saved host record contains:

```json
{
  "operation": "archive",
  "valid": false,
  "error": "AgentError: candidate exceeds the study decision depth"
}
```

This is a selected-field excerpt of `result.json` event 5, not a synthetic fixture.
The preceding model observation printed `valid: false` and the receipt. The next
command printed the full saved response, including the error, and constructed
`aggr_S32_64_128_t008` using checkpoints 32, 64, and 128. Its submitted rationale
explicitly stated: “Replaces a 4-stage variant rejected as too deep.”

The host admitted that replacement as structurally valid and retained its
assessment. The model exported valid receipts and excluded the rejected policy.
No additional model turn is inserted into this account between reading the
failure response and executing the correction within command 10.

This sequence demonstrates a concrete interface boundary: the model could propose
a rule and inspect feedback, while the host retained authority over the study's
structural constraints. Structural validity still did not establish recall or
latency acceptance.

## A concrete policy the model produced

One exported proposal, `cons_S32_64_128_t002`, used three checkpoint-specific tests.
The following pseudocode is an editorial translation of its saved policy tree:

```text
If any required feature is unavailable: continue.
At checkpoint 32, stop if frontier_count <= 983.
At checkpoint 64, stop if retained_result_count <= 1415.
At checkpoint 128, stop if completed_expansions >= 417.
Otherwise: continue.
```

The [trace](agent-trace.json) includes the exact original tree under
`representative_policy`, including its availability guard, typed literals,
feature groups, and runtime profile hash. The pseudocode is an explanation of a
historical research proposal, not a configuration change or a deployment recommendation.

The model's freedom lay in choosing the analysis, features, thresholds, checkpoint
combination, and portfolio. The host checked the submitted tree and assessed it
against existing evidence through the project's offline evaluator.

## What the saved host assessments established

This table uses the saved host assessment fields, rather than the model's local
simulator estimates. Values are rounded for presentation; their original numeric
values and record selectors are included in `candidate_assessments` in the trace.

| Exported proposal | Estimated work reduction | Mean training recall change, percentage points | Host training recall check |
|---|---:|---:|---|
| `cons_S128_t002` | 15.64% | −0.100 | Passed |
| `cons_S32_64_128_t002` | 31.00% | −0.100 | Passed |
| `mid_S64_128_t004` | 36.01% | −0.333 | Failed |
| `mid_S32_64_128_t004` | 37.15% | −0.300 | Failed |
| `aggr_S8_32_64_t004` | 31.75% | −0.200 | Failed |
| `aggr_S32_64_128_t008` | 43.47% | −0.533 | Failed |

The training recall check is the saved `aggregate_quality_passed` field, using
grouped evidence and per-filter requirements. It is not a held-out confirmation.
All six assessments reported zero unknown stops on this evidence, with 300 cases
representing 100 vector groups. Repetitions and filter variants do not turn them
into 300 independent vector groups.

Work reduction is an offline estimate. Every assessment marked activation and
reuse latency as `unmeasured`, with zero timing pairs. **None of these exports
established final acceptance.** The model's local estimates and the host's
assessments remain distinct records; this page does not recompute or reconcile
their numerical differences.

## Budget visibility and explicit completion

Before request 10, the host supplied these saved values:

| Budget field | Value |
|---|---:|
| Attempts already used | 9 of 12 |
| Committed model charges | $0.449836 |
| Remaining conversation budget | $0.610164 |
| Maximum next-request reservation | $0.606208 |
| Reservation fits | `true` |

The final request executed the replacement, exports, and finish. The saved ledger
then contained ten settled attempts and $0.530724 in committed model charges.
The budget limit is a model API accounting scope under the recorded pricing and
token-bound assumptions; it does not include infrastructure or establish current
provider pricing.

The model's submitted finish reason included:

> None is accepted: no latency measured including activation

The complete tool-submitted conclusion is preserved under `finish` in the trace.
It also identified weak recall estimates, the invalid policy, and the absence of
confirmation data. The host recorded `completed` because the model finished the
research conversation. That status did not mean an accepted stopping policy.

## What this run demonstrates

| Engineering capability | Observable evidence in this run |
|---|---|
| A usable domain interface | The model read the schema and tool guide, generated typed policies, and used receipt-based operations. |
| Model-directed investigation | The assistant tool calls contain the Python preparation, threshold scanning, simulation, and fitting code it chose to write. |
| Host validation and feedback | An invalid policy was retained with a precise error; a subsequent command replaced it with a valid shape. |
| Persistent evidence | Commands, assessments, failed attempts, selections, and the final reason were saved separately. |
| Visible limits | Host status messages exposed budget and request headroom before dispatch. |
| Separation of research and acceptance | Structurally valid failing proposals could be exported, while every export retained an explicit false acceptance flag. |

This conversation does not establish general optimization benefit, production
readiness, or superiority of one agent-selection strategy. Across the six v2
conversations, two exploratory conversations completed and four conversations
were budget-censored. There were zero complete A/B pairs, so the study comparison
remained inconclusive. The existing
[postrun summary](../verification/aggressive-proposals-v2-postrun.json) records
that broader outcome. The separate frozen-policy confirmation linked from the
showcase overview is a later campaign, not an event in this conversation.

## Provenance and omissions

The curated trace stores each original source's workspace-relative name, byte
count, and SHA-256. `source_ref` entries use a source ID and zero-based JSON Pointer;
status-message projections additionally identify the JSON embedded in a string.
`copied_fields` are selected original fields, and `exact_excerpt` strings are
contiguous original text. Step annotations and the pseudocode are editorial.

During preparation, the original commands were matched to the saved assistant
tool arguments, the saved system prompt was matched to the study contract, and
all 228 package files matched the archived manifest. These are read-only
consistency checks, not fresh tests of the agent or independent scientific reanalysis.

An existing serializer issue caused export records to carry the target candidate's
receipt in place of the export envelope receipt. The existing audit reports six
recovered collisions for this conversation. The trace preserves the candidate
receipts and uses event sequence plus record location to identify each export;
it does not invent replacement receipts or modify the originals.

There are seven archive attempts, six export events, and one finish event in the
selected result: fourteen tool events, rather than fourteen independent policies.

Private model reasoning fields, thinking blocks, provider metadata, raw response
artifacts, query vectors, source identifiers, query-level outcomes, and full
generated scripts are omitted. Exact command excerpts and short tool-submitted
scientific rationales provide evidence without publishing those materials.

Original paths in the trace are provenance identifiers, not broken links into a
reader's filesystem. The curated trace can be read from this repository on its
own; full raw records remain external. Hashes identify the bytes checked locally
and do not independently authenticate omitted records or supply a full replay bundle.
