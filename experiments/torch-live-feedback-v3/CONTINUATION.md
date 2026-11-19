# Continuation after the idle stop — pending approval

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
