# Methodological correction: seeded agent initialization

Recorded November 19, 2026, following the user's explicit requirement that the
agent must start without information from prior experimental runs.

**The v3 agent run does not satisfy the intended clean-start discovery experiment.
Claims about autonomous discovery from that starting condition are withdrawn.**
Jobs 23741092 and 23747524 initialized the agent with an exported development
dataset assembled from earlier oracle measurement archives. It contained
142,258 measured prefix outcomes, 499,121 captured feature frames, native recall,
result counts and work measurements for 450 development vectors / 3,150 cases.
These were inherited empirical inputs, not evidence acquired by this agent run.
Selecting only development rows did not satisfy the required starting condition.
The implementation made that experimental-design assumption without establishing
that inherited evidence was allowed.

The measured latencies, outputs, model transcript, source snapshots and resource
accounting remain preserved. They describe a seeded-development run and may be
audited as such. The prior agent/oracle gap, search behavior and model choice do
not establish clean-start agent performance or a limitation of independent
discovery. The earlier explicitly hindsight-fitted oracle studies retain their
separate stated scope. This correction does not invent a replacement result.

The current v3 workflow is retired. Preparation, continuation, model generation,
qualification dispatch, launch and final-evaluation dispatch fail before doing
work. Historical read-only status, collection and offline analysis remain
available. A compliant replacement has not yet been implemented or run. The
Opus configuration remains a future preference; changing the model does not
correct this initialization defect.

The starting condition for future agent discovery must exclude prior-run
observations, prefix labels, performance summaries, fitted policies, learned
thresholds and previous agent conversations or scratch files. Empirical
information exposed to the agent must be acquired through that experiment's
own permitted actions and charged to its budget, with an auditable provenance.
Generic software interfaces and static task/workload inputs are distinct from
prior empirical results. The exact replacement workflow must document that
boundary before execution.

The committed comparison artifacts and their original `SHA256SUMS` are left
unchanged. This erratum supersedes their interpretation for clean-start
discovery. Subsequent offline report generation must carry the same correction.
