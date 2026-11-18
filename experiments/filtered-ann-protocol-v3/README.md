# Portable broad stopping programs

V3 removes the former three-clause/four-comparison/16-32-64 rule shape.
The public format and reference implementation are in
`src/fannagent/api/broad_policy.py`. `fannproto3.compiler` emits immutable data
for the trusted native VM. `fannproto3.tools.BroadPolicyTools` is the agent
submission interface; `toolspec` provides its tool and research instructions.

An agent can generate a policy directly or use offline scripts to produce a
JSON file. Call `evaluate_broad_candidates` with `policies` or `policy_paths`.
The latter resolves files inside the private workspace, enforces the source
budget, validates types and compiles through the same trusted path as inline
submission. The host injects its evaluator, evidence access and resource
allowance. Successful candidates receive content hashes and registry artifacts.
There is no evaluator-only policy syntax or query-ID dispatch mechanism.
The v2 controller remains available for reproduction; v3 is a separate opt-in
interface and does not silently alter prior experiments.

A policy declares schema, name, rationale, per-query fuel, register count and
per-filter programs. Each program declares sorted checkpoints, a Boolean root
expression and simultaneous numeric register updates. Expressions use JSON
arrays such as `["le", ["feature", "frontier_gap"], 0.02]`,
`["if", condition, then_expression, else_expression]`, or
`["add", ["state", 0], 1]`. See the public validator for all operators.
Programs cannot read IDs, splits, outcomes or future state. Missing values,
floating point faults and query-budget fallback have deterministic semantics.

Operational limits bound deployment memory and execution, rather than the
researcher's fitting method: 8 MiB source, 131,072 expression nodes, depth 64,
four MiB compiled tables, 32 registers and 16 million maximum fuel units.
Checkpoint indices range from 1 to 4096. Costs include feature collection.
Only checkpoint-required features are collected; prior-frame dependencies
refer to the preceding *declared* checkpoint. Policies reset for each query.

The implementation and measured oracle comparison are under
`experiments/broad-oracle-v1`; its protocol defines qualification and timing.
