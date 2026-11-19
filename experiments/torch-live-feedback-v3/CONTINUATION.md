# Continuation after the idle stop — completed

Job **23741092** completed with exit 0 after **1,262 allocated seconds**, but
its worker stopped on the old fifteen-minute idle rule while the model was
actively fitting offline. This is an infrastructure-censored run, not an agent
abstention or a measured policy result. No learned policy reached native
evaluation. The model made **24 settled requests costing $1.707958**; there are
no uncertain charges. Qualification used 252 ANN requests / 256 charged slots.
The late host liveness request was rejected before registration and used no ANN
queries. The raw return, transcript, fitting scripts and failed delivery are kept.

The repaired controller sends authenticated activity heartbeats before model
calls and after completed tools. A heartbeat keeps the worker available while
offline fitting is active; it cannot reopen a closed worker, change its start
time, reset its deadlines, increase its query budget or extend its allocation.
If the controller disconnects, the existing fifteen-minute idle expiry remains.
Read-only status checks do not send heartbeats. Tests cover those boundaries.

The prepared continuation proposes **one additional allocation of at most
5 hours 38 minutes**, with four physical CPUs and 48 GiB. Together with the
first job this is at most **5:59:02**, below the original six-hour aggregate
ceiling. All 256 prior ANN reservations remain charged against 300,000. The
same model ledger, conversation, fitting files and tool receipts continue;
**$13.292042 remains under the original $15 ceiling**, with no new allowance.
The first job's outcome is immutable. No provider retry, final-result reselection
or replacement allocation is dispatched automatically.

The v3 language, evidence, compiler/VM, quality criterion, native timing method,
control thresholds, intended cohorts and frozen final comparison are unchanged.
The new worker must qualify before model continuation. Only an audited
administrative stop with fully settled model charges and completed tool
receipts can resume. An abstention, frozen policy or unknown delivery cannot
be reopened by this path. The final agent policy will still be selected on
development only and evaluated once on the test and full workloads.

The initial [protocol](PROTOCOL.md) limited the run to **one allocation**.
Consequently the second allocation requires the user's explicit approval.
`remote.py launch` refuses a continuation without an authorization bound to the
prepared `continuation-plan.json`; it never infers that permission from a retry.
Preparation and tests authorize no new compute or model spending.

The user explicitly answered **“Approve bounded continuation.”** The bound
authorization is saved in `run-v2/continuation-authorization.json` in the sibling
trial directory. Staging exceeded the launcher's local extraction wait, before
any submission. A read-only recovery verified all 214 input checksums and absent
submission markers; readiness then passed. There was no reupload or submission
retry. Job **23747524** is the single approved continuation allocation.

It qualified the native path, resumed the original conversation and ledger, and
measured three model-generated policies on development. The agent froze
`candidate-2` (`fgap-margin-narrow`) after **32 cumulative model calls costing
$2.797810**, with no uncertain charges. The protected final comparison follows
that immutable selection. The [discovery receipt](results/agent-discovery.json)
records the source/review bindings and all three development outcomes; the
first attempt remains separately recorded.

Job 23747524 subsequently completed with exit 0, including the frozen final
comparison and verified private cleanup. The returned archive and all final raw
hashes verify; independent analysis checks scores, frozen identities and the
complete schedule. Both jobs total **6,049 allocated seconds** and **248,800
charged ANN reservations**, with no new exact searches or automatic retries.
The [final report](results/comparison-v1/REPORT.md) records the agent's −0.46% /
−1.78% descriptive savings against the broad oracle's 66.32% / 64.87% on held-out
and full respectively. Both have zero intended-cohort recall losses; strict
timing equivalence is not established.
