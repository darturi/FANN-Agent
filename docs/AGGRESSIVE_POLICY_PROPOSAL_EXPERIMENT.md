# Aggressive policy proposal experiment v1

Prepared October 20, 2026. **Current status: v1/v2 generation comparisons remain
inconclusive; the separate corrected timing study and held-out confirmation are
complete. The frozen selected policy fails confirmation recall criteria.**
See the [master experiment index](experiments/README.md)
for the full run history, failures, artifacts and reproduction procedures.
The versioned implementation and launch commands are in
[`trials/torch-reviews-aggressive-proposals-v1/README.md`](../../trials/torch-reviews-aggressive-proposals-v1/README.md).
The original implementation verification used synthetic tests, a fake provider
and existing host-only references without model spending or Torch submissions.
The subsequent actual generation outcome is recorded in
[the postrun verification](verification/aggressive-proposals-v1-postrun.json).

The six actual conversations used 71 provider attempts and $2.589112. Five
reached the 12-attempt limit; one hit its 60-second command timeout on attempt
11. None exported a proposal or called `finish`. Two exploratory conversations
archived four distinct structurally valid aggressive intermediates; all four
offline screens reproduce. These are diagnostic intermediates, not completed
portfolios, accepted policies or evidence that either selection condition wins.
The minimum of two complete pairs was not met, so the training packager correctly
refused to create a Torch campaign. No final recall criterion was changed.

The run also exposed usability limitations in the shared interface: corpus
schema discovery consumed several requests, typed constants and guards required
repairs, and tool observations did not expose remaining provider attempts. These
are plausible contributors to censoring, not a measured causal explanation.
The frozen v1 prompts, source, results and ledger remain intact. A follow-up
must separately predeclare common schema guidance, request accounting, completion
instructions and its budget; it cannot resume or relabel these terminated runs.

The user subsequently authorized that corrected follow-up inside the existing
budget. **At the close of v2 generation, two exploratory conversations completed,
four were budget-censored, and no A/B pair completed. Torch measurement was deferred.**
Its [amended protocol](../../trials/torch-reviews-aggressive-proposals-v2/DESIGN.md),
[launch commands](../../trials/torch-reviews-aggressive-proposals-v2/README.md)
and [implementation verification](verification/aggressive-proposals-v2-implementation.json)
are separate from v1. V2 is capped at $6.36 total, $1.06 and 12 attempts per
fresh conversation, with v1+v2 still capped at the original $9. Final recall,
activation/reuse and confirmation gates remain unchanged.

V2 used 56 paid attempts and $3.020092. Its two completed exploratory
conversations exported 12 distinct policies, of which three pass the unchanged
training-replay recall checks; no new latency measurement had been made at that
stage. All 37
valid archived screens reproduce, representing 35 distinct intermediate policies.
The three acceptance-oriented conversations screened recall-passing candidates
before hitting their reservation limit; they did not finish or record abstentions.
Their zero export counts therefore do not establish deliberate withholding.
The [v2 postrun verification](verification/aggressive-proposals-v2-postrun.json)
records this outcome and the preserved diagnostic export inventory.

Every new request required the original fixed $0.606208 maximum-charge
reservation. With a $1.06 conversation cap, another request became unaffordable
once committed spending exceeded $0.453792, even though some of the nominal
12 attempts remained. The finalization guidance should have accounted for this
reservation constraint as well as the request count. The stopped conversations
remain censored and cannot be resumed or relabeled under the v2 protocol. Any
measurement-only follow-up using the already exported portfolio must be declared
separately and retain the original A/B comparison as inconclusive. It need not
make further model calls; it cannot bypass v2's predeclared completion gate.

The user authorized that separate twelve-policy timing study. It is implemented
and packaged as `frozen-proposals-timing-v1`, with
[its own protocol](../../trials/torch-reviews-frozen-proposals-timing-v1/DESIGN.md),
[Torch commands](../../trials/torch-reviews-frozen-proposals-timing-v1/README.md)
and [verification record](verification/frozen-proposals-timing-v1-implementation.json).
All twelve original exports are included in two source-balanced cohorts of six;
no model call, fit or proposal change is introduced. Six allocations retain
115,200 pairs, with the original native comparisons, matched continue controls,
diagnostic controls, recall criteria and activation/reuse gates. Conditional
confirmation requires independent local raw-report reproduction before opening
the original sealed split. V2's summary and closed A/B gate remain unchanged;
the new timing contract explicitly retains the inconclusive A/B comparison.

The first submitted timing campaign failed in both block-0 allocations on
October 21, 2026, at 234 backend calls per cohort. The shared-interpreter helper
read an instance `runtime_profile` attribute absent from the frozen Torch
backend. The dependent arrays were cancelled. The local fake backend had added
that attribute and therefore missed the interface mismatch. This mechanical
failure provides no timing or recall qualification result.

A separately named
[runtime correction](../../trials/torch-reviews-frozen-proposals-timing-v1-runtime-fix/README.md)
passes the runner's module-level frozen profile explicitly to prediction in
qualification and raw analysis. The original upload, source, submission bindings
and failed campaigns remain preserved. Its
[verification record](verification/frozen-proposals-timing-v1-runtime-fix.json)
records interface regression checks against the preserved original runner and
backend. Packaging requires byte-identical candidates, spending receipt,
generation contract and A/B summary, and an unchanged scientific protocol except
implementation identity and correction provenance. Final recall criteria,
allocation limits, timing boundaries and the inconclusive A/B result remain
unchanged. No further model calls are permitted.

The replacement timing campaign completed on October 21, 2026. Independent local
raw reanalysis reproduced all six blocks, 115,200 retained pairs, 28,800 discarded
warmups and 28,800 native causal-prefix proofs across the original 100 vector
groups. All final criteria remain unchanged. Two policies pass both training
regimes: `cons_S32_64_128_t002` saves 12.690% including activation and 13.545% on
reuse; `tol0.0005` saves 3.555% and 4.190%. The prespecified selection rule chooses
the former. Nine proposals fail recall; `cons_S128_t002` passes recall but lacks
a reliable primary-clock latency improvement. The
[postrun verification](verification/frozen-proposals-timing-v1-runtime-fix-postrun.json)
records the independently reproduced result and analysis artifacts.

The selected policy's overall recall changes from 99.0% to 98.9%; its worst
per-filter recall confidence lower bound, for votes108, is exactly -0.5 percentage
points and passes the original inclusive cutoff. Its selected identity is
frozen. At training close this was training feasibility only; no confirmation query was opened,
no new model call or fit was made, and canonical serving acceptance remains
unestablished. The A/B comparison stays inconclusive with zero complete pairs.
This made the policy eligible for the originally prescribed one-policy held-out
confirmation, without retuning or a fallback candidate after its result.

The user subsequently authorized packaging that confirmation for the exact
`cons_S32_64_128_t002` selection. The
[confirmation-package verification](verification/frozen-proposals-timing-v1-runtime-fix-confirmation-package.json)
records the completed upload and checksum. Packaging independently reproduced
both raw training cohort reports and selection before reading the original
confirmation inventory. The upload contains one selected policy and five
diagnostic controls, 180 cases in 60 disjoint vector groups, three serial blocks
and 29,160 retained pairs. It preserves the original timing contract, recall
criteria and inconclusive A/B result. No model call, fit, query execution or
Torch submission occurred during packaging. The held-out query inventory was
packaged with explicit authorization; its outcomes were unmeasured at that stage.

The user-submitted confirmation campaign
`reviews-frozen-proposals-timing-v1-runtime-fix-confirmation-20261021T160807Z.n5yrz2mk`
completed all three allocations on October 21. Independent local raw reanalysis
reproduces 29,160 retained pairs from 180 query/filter cases in 60 held-out vector
groups. The unchanged `cons_S32_64_128_t002` is faster in both timing regimes:
9.865925 to 8.714277 ms including activation (11.673% saved) and 7.590645 to
6.651142 ms on reuse (12.377% saved). Both latency confidence-bound gates pass.
Recall fails overall and in votes32 and votes108. Overall native recall is
99.500%, policy recall 98.944%, and the recall-delta lower 95% bound is -1.056
percentage points; the permitted bound remains at least -0.500 pp. Per-filter
lower bounds are -0.500 pp unfiltered (passes inclusively), -0.833 pp votes32
and -2.167 pp votes108. All complete-result and minimum-native-recall checks pass.
The [confirmation postrun verification](verification/frozen-proposals-timing-v1-runtime-fix-confirmation-postrun.json)
records exact results, source identities, raw reproduction and analysis files.

Nine of 180 cases across seven vectors lose recall, with no gains: eight lose
one top-10 match and one loses two. These outcomes repeat identically across
blocks and timing repetitions. This is a failed recall confirmation despite
repeatable latency improvement. No candidate qualifies, no serving acceptance
is established, and this study ends without retuning or a fallback on the
consumed split. Future optimized candidates require fresh independent
confirmation. The A/B comparison remains inconclusive with zero complete pairs.
There were zero new model calls or fits, and all 169 original financial charges
and the original scientific ledger state remain unchanged.

No model requests, fitting, policy replay, database measurements, builds, tests,
Torch submissions or confirmation queries were performed to prepare this design.
The source state was committed before this document was added. Exact revisions
and local evidence hashes are recorded in
[the checkpoint manifest](verification/aggressive-proposals-v1-inputs.json).

## Question and competing explanations

The working hypothesis is that the agent withholds informative aggressive
policies because it tries to certify a successful final policy during proposal
selection. The conventional six-tree experiment instead admitted provisional
policies with known or unknown recall failures for training measurement. This
difference could explain the output gap without a representational limitation.

Competing explanations are insufficient model/tool budget, difficulty fitting
from the supplied evidence, and inadequate runtime information. The experiment
tests the proposal-selection explanation first. Producing an aggressive tree,
beating native latency, and passing final recall are three separate outcomes.
Abstention after testing candidates must not be reported as no candidates tested.

This is an exploratory reproduction on already studied development data. It
cannot retroactively make those data an independent test or establish that
all possible stopping policies are infeasible.

## Fixed evidence, representation and execution

Use the original **2,397 actual stop labels**, 100 learning vector groups and
300 query/filter cases at `ef_search=640`, with `k=10`. The three strata are
unfiltered, `votes32` and `votes108`. Use the original lightweight view underlying
the six trees in the discussion, rather than the later 3,933-label corpus.
This holds the learning opportunity fixed. The saved normalized corpus has
zero timing pairs; its source-hash metadata must be removed from the learner
view so it cannot point to hidden candidate artifacts.

Both arms receive exactly the same 19 qualified features, numeric semantics,
availability rules, data ordering, five vector-group folds, training-only
baseline summaries, tool documentation and policy limits. `predicate_leaf_count`
is included. The actual predicate threshold, full queue statistics, vectors,
query identities as runtime features and unqualified getters are excluded.
Group and stratum identifiers may support offline diagnostics, never decisions
inside the deployed tree. Filter variants of a vector stay in the same fold.
Use the original fold rule: the integer value of SHA-256 over the UTF-8 string
`20261019/` followed by the group ID, modulo five. Record the complete assignment
in the sealed learner view; do not substitute the newer fitter's fold ordering.

The policy language permits at most four decision levels including availability
guards, subject to the existing validator's expression/node limits. A missing
required feature must continue. Both arms may write their own fitting scripts
using the same pinned Python/NumPy environment. Neither sees the six existing
tree artifacts, their fitting implementation, their measured results, the later
feedback corpus, other agent transcripts or the other arm's outputs. The host
retains these as comparison/provenance artifacts outside the sandbox.

The learner gets a read-only sanitized corpus, interpreter-backed `inspect`,
`validate`, `screen` and `archive`, plus a writable private analysis directory.
Use an explicitly versioned **proposal export**, separate from the old submission
and freeze operations. Its admission checks are identical in both arms: legal
syntax, depth, qualified features and artifact integrity. It accepts a structurally
valid research proposal despite known recall loss, unknown outcomes or poor work
estimates. Those properties remain visible in feedback. Neither arm may call
serving submission or freeze a policy during proposal generation.

Primary measurements use the original optimized lightweight x86 library and
frozen feedback-study query driver, ordinary-native comparator and existing
247,286-row by 768-dimensional physical Reviews index. Verify their exact
identities from the original receipt before execution. **Do not substitute the
new dispatch path, predicate-context profile, index rebuild or feature patch.**
Changing execution together with the prompt would confound this experiment.

## Paired agent conditions

Run three independent replicate pairs, six fresh model conversations total.
Use the original model configuration (`anthropic/claude-sonnet-5-5`), identical
sampling/context settings, tool bounds and resource caps. Replicate IDs are
host bookkeeping, not an assumption that the provider supports seeded sampling.
Randomize A/B launch order within each pair using a predeclared host seed,
`20261020`. No shared conversation or transfer of outputs is permitted.

Each conversation has six final proposal slots and identical feedback. Record
every intermediate validated candidate, its screen and its eventual selection
or rejection reason; observing only the final shortlist would hide the mechanism.
Arm A may leave slots empty. Arm B may honestly abstain if it cannot construct a
valid policy; the host must not manufacture an active candidate to fill a slot.

**A: acceptance-oriented selection.** Ask for up to six candidates the agent
believes can satisfy the unchanged aggregate/per-filter recall criterion and
repay policy overhead. It may reject candidates using its offline evidence and
work-cost forecasts, and may submit an abstention. Structural proposal export
remains permissive; conservatism is the selection instruction, not a hidden
server-side recall filter.

**B: exploratory selection.** Ask for up to six distinct candidates spanning
aggressive, intermediate and conservative stopping behavior. Known recall loss,
unknown first-stop outcomes and an unfavorable latency proxy do not disqualify
a training proposal. The agent must describe those limitations and prioritize
informative tradeoffs. Final recall and latency acceptance are identical to A.

Shared task text, supplied verbatim to both arms:

> Develop compact stopping policies for the supplied Reviews training workload.
> The final target is valid complete top-10 results, native recall at least 0.95
> in each stratum, and a 95% vector-cluster lower bound for policy-minus-native
> recall of at least -0.005 overall and in every stratum. A final candidate must
> also demonstrate measured latency improvement including policy activation.
> These criteria do not certify an unmeasured proposal. Keep safe, failing,
> unknown and continued cases separate; never infer recall at an unmeasured stop.
> Use all qualified features as an eligible pool and vector-grouped validation.
> Save every screened policy and its rationale. Export at most six distinct
> research proposals or explain abstention. No confirmation data is available.

A-only selection text:

> Select proposals only when your offline evidence supports the final recall
> objective and your work-cost analysis supports a plausible net latency gain.
> Leave a slot empty when you cannot justify a candidate. Explain which evidence
> or predicted cost caused each rejection. Offline support remains provisional.

B-only selection text:

> Select an informative portfolio, including early-stopping policies that may
> lose recall. Do not require a proposal to pass recall or predicted latency
> before exporting it for training measurement. Include aggressive, intermediate
> and conservative tradeoffs when you can construct them. Report known failures
> and unknowns explicitly. A failed research proposal cannot become an accepted
> policy; final recall and latency criteria remain exactly as stated above.

The entire prompts, corpus view and environment must be hashed before any model
request. Do not add the investigator's expectation of an A/B winner to either
prompt or show the conventional fitter's thresholds.

## Budget and stopping rules

The original durable $15 campaign ledger remains authoritative. The last saved
receipt has $3.174666 committed, including its uncertain reservation, leaving
$11.825334. Do not reset that history or release uncertainty to fund this study.

Reserve a **maximum $9 total** for six conversations, with a hard **$1.50 cap
and 12 provider attempts per conversation**. All requests, failures and uncertain
charges count. Dispatch requires both the per-conversation and original-ledger
balances to cover the conservative complete-request reservation. There are no
automatic retries or transfers of unused money from A to B. Existing reservations
are not six new allowances. Recheck the live ledger and model/pricing contract
before a future launch; if the full $9 cannot be reserved, stop before either arm
runs and amend the design instead of reducing one arm's budget.

These are spending caps, not a promise that all 12 requests fit: a large request
can exhaust a conversation's reservation headroom sooner. Archive the current
candidate inventory after requests 6 and 12, or at earlier termination, without
injecting a new instruction at request 6. Record input/output tokens, costs,
request sizes, tool CPU time, actual tool operations and termination reason.
Use equal local analysis limits of two CPU cores, 4 GiB, 60 minutes per
conversation, at most 120 sandbox commands and a 60-second timeout per command.
Host-managed file reads and non-executing archive collection do not add model
requests. Do not resume a terminated run just because it produced no candidate.

This budget curve is descriptive, not a randomized test of additional spending.
A cost-, context- or request-censored pair cannot establish that conservatism,
rather than budget, explains its difference. Report it as censored. If fewer
than two complete pairs remain, the prompt comparison is inconclusive and the
Torch measurement stage is deferred. A higher-budget or fitter-assisted arm
would require a separate, predeclared follow-up rather than an adaptive extension.

Arm A is a controlled reconstruction of acceptance-oriented selection, not an
exact rerun of the earlier four-case agent study. This experiment gives both arms
the same updated tools and one focused case. A difference identifies an effect
inside this matched protocol; it does not prove the cause of every historical
abstention or separate every aspect of framing from selection instructions.

## Outcomes and interpretation before new measurements

Semantic deduplication uses the canonical decision root, collection groups and
runtime profile, excluding names. Always-continue trees do not count as active.
An intermediate candidate is archived when first presented to validation/screening;
an unrecorded private draft cannot support a claim about its screening outcome.

Record per run: distinct valid intermediate and exported policies, abstentions,
known-failing/unknown first-stop coverage, stop fraction, work reduction, policy
complexity, rejected-candidate reasons and time/cost to first active proposal.
For a fixed manipulation check, define an aggressive exported policy as one that
stops on at least 25% of the 300 trajectories and reduces mean predicted
layer-zero distance work by at least 20%, counting continuation as native work.
This is a work diagnostic, never a latency or recall qualification.

The proposal-selection hypothesis receives **descriptive support** if B exports
an aggressive policy in at least two complete pairs while paired A does not,
under the same caps. Stronger mechanism evidence is A internally screening and
rejecting comparable active candidates that B exports. With only three pairs,
do not claim a statistically established model-level effect. Mandating a broader
portfolio can mechanically change output counts; counts alone do not establish
learning quality, useful information or agent superiority.

If both arms produce aggressive proposals, the earlier abstention was not a
reliable indication of a persistent inability to propose. If neither does and
runs finish uncensored, investigate fitting/tool understanding next. If both
are censored, the budget explanation remains open. Successful export followed
by failed recall supports exploration ability, not a successful optimizer.

The six saved conventional trees are a **host-only positive reference** for
representability and previously observed tradeoffs. Replay their frozen artifacts
later under the same measurement schedule; do not refit them with later labels.
Do not call them agent discoveries. A future arm exposing the fitter to the
agent would test tool orchestration rather than independent policy discovery.

## Frozen training measurement stage

Only after all complete conversations terminate, freeze their proposal artifacts,
source attribution and the entire measurement schedule. The model stage never
sees results from this new measurement stage. There is no within-study refit,
threshold tuning or proposal replacement after measurements begin. New first
stops may remain unknown during offline selection; actual complete policy
executions provide their recall outcomes without interpolating checkpoint labels.

Measure every structurally valid, unique exported proposal, including policies
predicted to lose recall. Up to 36 agent slots plus six conventional references
give at most 42 candidate artifacts; shared artifacts execute once and retain
all source attributions. Add a matched-continue control for each candidate.
Common controls are lightweight continue, fixed-4,096, fixed-8,192 and the
original sparse hindsight oracle. The oracle stays evaluator-only.

Use at most six cohorts of seven candidates, their seven matched controls and
the four common controls: **18 arms per cohort**. Freeze a source-balanced
assignment by hash before timing; do not group one prompt condition entirely
before the other. Shared controls repeat in each cohort. Their observations
remain cohort-specific rather than being borrowed across nodes or time.

Each cohort has three serial Torch allocations with the original index restored
and checked. Each arm/query/block retains one activation-inclusive pair, one
discarded warmup pair and three reused pairs. Randomize paired execution order;
balance/rotate arm order across allocations using the frozen schedule. Retain
all results, outer application clocks and outliers. Activation includes policy
preparation/installation and first execution on warm data; reuse includes all
normal validation, serialization, feature collection, inference and decoding.
Keep the frozen native timing boundary and report the common outer clock too.
Do not subtract estimated overhead or replace the primary clock after results.

Maximum retained coverage is 18 x 300 x 3 x 4 = **64,800 pairs per cohort**,
or **388,800 pairs across six cohorts**. An allocation uses 54,000 timed/warmup
backend calls before exact references and qualification. Limit the full allocation
to 70,000 counted backend/reference/qualification calls and 6,600 measurement
seconds, with four CPUs, 32 GiB and a two-hour job limit. Control SQL is counted
separately. Require a static complete-call accounting check before submission;
never silently drop checks or candidates to fit the cap. Incomplete coverage
cannot produce a feasibility decision.

Native qualification must exercise actual stop decisions, availability branches,
causal-prefix equivalence and result integrity for every candidate. Native and
matched-continue results must agree. Failed qualification is a reported mechanical
failure, not a successful recall tradeoff. Restore private copies, preserve
previous campaigns and retain all failure artifacts. Torch makes zero model calls.

Report activation and reused savings in milliseconds and as
100 x (paired native mean - policy mean) / paired native mean, alongside overall
and per-filter recall changes, completeness, uncertainty and cost. Bootstrap
10,000 times at the independent vector-group level, retaining all related
filters, repetitions and allocations together, with the existing seed 20261019.
Report allocation/cohort variation separately; repeated timings do not increase
the number of independent vectors. Latency-recall frontiers and policy/source
attribution are training descriptions, not multiplicity-corrected discoveries.

## Unchanged final gate and independent confirmation

**Permissive proposal admission does not alter any final criterion:**

1. Complete, valid top-10 results under the existing tie-aware reference scorer.
2. Native mean recall at least 0.95 in each filter stratum.
3. The lower 95% vector-cluster confidence bound of policy-minus-native recall
   is at least **-0.005 overall and in every stratum**. A point estimate inside
   0.5 percentage points alone is insufficient. No individual-filter omission,
   zero-loss proposal rule, proxy label or aggregate-only substitute is allowed.
4. The upper 95% confidence bound of mean log(policy/native latency) is below
   zero including activation. Report reuse separately and require it to pass
   as well before this study recommends a candidate for later confirmation.

Among training candidates passing every requirement, choose **one primary
candidate** by greatest activation-inclusive percentage saving, then fewer
decision nodes, then lexical semantic hash. Freeze its identity, evidence,
profile and evaluator before opening the original **60 untouched confirmation
vector groups / 180 queries**. If none passes, stop with no promotion and leave
confirmation sealed. Training results remain adaptive even for frozen proposals.

Confirmation uses three allocations, the same driver and all four unchanged
criteria. Its six arms are the single candidate, its matched continue and the
four common controls. Retain one activation pair and eight reused pairs after
one discarded warmup pair, yielding 6 x 180 x 3 x 9 = **29,160 retained pairs**.
The selected candidate is the sole primary policy comparison; other controls
are diagnostic. Failed confirmation permits no retuning or second candidate
on that same split. No canonical calibration, final test or serving acceptance
is consumed or changed by this development experiment.

## Implementation contract and verification before launch

This document is not a launcher. The implementation supplies the paired runner, identical permissive
proposal-export broker, sanitized evidence builder, sealed transcripts, shared
ledger/subbudget accounting and separate measurement package in a new versioned
trial. Old manifests, locks, uploader limits and paid receipts remain unchanged.
An explicit new request contract must account for all appended attempts; do not
relabel extended receipts to pass the original 24-attempt uploader.

Before model execution, verify prompt/evidence equality outside the declared
selection text, sandbox exclusion of host-only artifacts, candidate provenance,
immutable inputs, per-call budget reservations and interrupted-run recovery.
Before Torch execution, verify exact driver/library/index identity, policy
interpreter/native parity, causal prefixes, complete call accounting, scheduling,
report reproduction and failure retention. Synthetic control-plane and packaging
checks are recorded with the implementation. Actual new policy/native execution
is qualified inside its Torch allocation before measurements. Historical
qualification records do not qualify a new runner automatically.

This design alone authorizes no additional spending, submission or opening of
confirmation. Historical authorized executions are recorded above; the latest
training timing study and held-out confirmation are complete. Confirmation
failed the unchanged recall criteria and permits no policy promotion.
