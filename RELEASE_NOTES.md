# Unreleased

Add a local release bundle, repeatable host installer, Docker controller launcher,
packaged `init` templates and extension-owned `doctor` checks. Package the sandbox
tool client and pin sandbox dependencies. Preserve run paths across launch modes,
route container connections through the owned authenticated relay, and replace
PID-only leases with atomic filesystem ownership records. Journal sandboxes for
recovery after controller termination and close them on initialization failures.
Docker Desktop's socket ownership and lack of cross-kernel advisory locks are
handled explicitly. Existing study configurations, budgets and policy profiles remain compatible.

Supply compact prepared-backend context automatically before the first model call, with development artifact references for full inspection and feature definitions. Add the optional inspection `startup_summary` dictionary for extensions. Save initialization before model execution and start fresh scripted runs with `probe`. Resume preserves existing messages, counters, and older scripted action indices. Extension API v1, configuration/run schema v2, and policy fingerprints require no migration.

Normalize absent optional shell exception metadata for mini-swe-agent's observation formatter so provider-backed probes can complete.

Add actionable, bounded validation feedback across model tool calls, shell syntax, CLI/broker arguments, and query/filter/policy inputs. Validate all model actions before execution, track invalid requests on the host even when shell output is suppressed, and stop after three consecutive invalid turns. Persist recovery across resume, retain billing for malformed responses, and preserve accepted-policy completion and candidate checkpoint behavior. Broker responses retain `ok`, `result`, and string `error`, with additive `error_info`; brokers also accept raw CLI `argv` alongside the existing request form. Existing configuration/run schemas and extension API v1 remain supported.

# 0.2.0

Separate the reusable core and public extension API v1 from database integrations. Add descriptor discovery, typed data/runtime profiles, canonical bounded policy envelopes, namespaced host services, schema-v2 configuration/runs and read-only legacy inspection. Keep spending and evaluator controls in the core. Shared neutral algorithms now support the harness's compatibility wrappers. Pgvector is delivered separately at 0.1.0. Existing operational runs require the pinned legacy environment.
