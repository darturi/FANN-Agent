# FANNAgent: engineering an experimental research agent

FANNAgent connects an LLM's investigation to a real vector-search experimental
system. Daniel Aarao Reis Arturi designed the project-specific agent infrastructure,
tooling, evaluation workflow, and pgvector integration.

The working question is concrete: **can the agent discover when search can stop
earlier, then express that decision as a small executable policy?** One policy
from the recorded conversation subsequently reduced mean query latency by
12.69% including activation and 13.54% on reuse on the 300-case training workload,
with mean Recall@10 changing from 99.00% to 98.90%.

## A reading path

| Topic | Engineering decisions to look for |
|---|---|
| [Architecture](../agent-design.md) | Where the model has freedom, where the host has authority, and how tools, state, budgets, and recovery fit together |
| [Oracle](oracle.md) | How actual stopped executions reveal search headroom and produce evidence the agent can analyze |
| [Evaluation](evaluation.md) | How candidate freeze, matched controls, paired execution, and grouped statistics distinguish promising ideas from measured effects |
| [Data and queries](workload.md) | What was searched, what the filters mean, how vector groups are split, and which information reaches the model |
| [Agent run](agent-run.md) | Agent-written analysis, policy construction, correction after validation feedback, and source attribution |
| [Measured policy performance](../results.md) | The exported policy, native-versus-policy timings, and associated recall changes |

## The method behind the system

The project follows a sequence of explicit experimental questions:

1. **Is there headroom?** Observe native execution and test real early stops.
2. **Can the agent use the evidence?** Give it qualified features and a bounded
   tool interface, then preserve its analysis and proposals.
3. **Does the complete policy save time?** Measure native and policy executions
   with activation and runtime overhead included.
4. **Does the behavior carry to different queries?** Freeze one selection before
   opening the separate held-out groups and assess quality alongside latency.

The recorded model study used a specialized proposal runner around the core
budgeted model adapter and offline evaluator. The general architecture also
supports a brokered interactive study workflow. The [run walkthrough](agent-run.md)
identifies the path actually exercised by the recorded conversation.

The [contributions page](../CONTRIBUTIONS.md) identifies Daniel's engineering and
credits mini-swe-agent, LiteLLM, PostgreSQL, pgvector, and the data sources.

## Inspect or run it

- [Curated agent trace](agent-trace.json): selected original commands, assessments,
  policy tree, receipts, and source hashes.
- [Study evidence](study-evidence.json): workload, oracle definition, candidate
  lineage, and timing-contract projections checked against the saved packages.
- [Local simulation](local-demo.md): a free scripted lifecycle using the synthetic
  backend, with no API key or database required.
- [Validation](validation.md): release checks and documentation verification.

The simulation illustrates the lifecycle with predetermined actions. The real
run and database measurements are recorded research evidence. Full database
reproduction requires the original external index, campaign archives, and runtime.
