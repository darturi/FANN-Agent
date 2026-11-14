# FANNAgent system audit October 6 2026

FANNAgent has a coherent core and extension architecture, and its tested policy, spending, evidence, and evaluation safeguards are working. The current system has two high-priority defects: the harness UI cannot start after the shared-code extraction, and restored PostgreSQL copies permit unauthenticated superuser access from other Docker containers. Seven additional findings concern connection remapping, resource ownership, recovery, cancellation, and resource limits. Fix these before expanding use beyond controlled disposable datasets or publishing the current release as qualified for broader use.

This audit covers `fannagent` 0.2.0, `fannagent-pgvector` 0.1.0, their public API v1, the packaged native engine patches, build and release artifacts, and the affected `fannbench` 0.4.1 compatibility boundary. It assesses the files present on October 6, 2026. These directories have no Git repository, so the evidence manifest records source and wheel hashes instead of a commit ID. Application source files were left unchanged; new files contain this audit and its evidence.

## Findings by priority

P1 means a current failure that should block the affected release or use with sensitive data. P2 means a reproducible defect or a concrete missing safeguard that should be resolved before broader operational qualification. Reproduction methods distinguish live disposable tests, controlled fault injection, and code analysis.

| Finding | Priority | Consequence | Evidence |
| --- | --- | --- | --- |
| F1 Harness filter wrapper omits required constants | P1 | UI and API initialization fail | 14 failing tests; all pass with an in-memory compatibility shim |
| F2 Restored database accepts unauthenticated superusers | P1 | Other containers can read or modify the full copied cluster | Live peer container connected as `postgres` with superuser privileges |
| F3 Copy DSN retains source routing and authentication constraints | P2 | Supported source connection strings can prevent connection to the copy | DSN reconstruction plus PostgreSQL connection semantics |
| F4 Restore can write into an existing foreign volume | P2 | Journaled creation intent is mistaken for acquired ownership | Fresh Docker volume reproduction and restore-path analysis |
| F5 Preparation retry skips unfinished sidecar creation | P2 | An incomplete preparation can become qualified | Live sidecar failure injection and retry |
| F6 Initialization failures can leak sandbox or session resources | P2 | Failed startup leaves resources open; sandbox crashes lack durable recovery | Controlled failure injection and cleanup-path analysis |
| F7 Profile upgrades prevent cleanup of owned resources | P2 | Ordinary upgrades can strand containers and volumes | Descriptor change injected into a schema-v2 run |
| F8 Sandbox timeout does not cancel host tool work | P2 | Long calibration or labeling can continue after the agent sandbox stops | Broker shutdown reproduction and timeout-path analysis |
| F9 Sandbox output and workspace writes lack host resource bounds | P2 | Agent commands can exhaust host memory or disk | Subprocess capture and writable mount analysis |

## Verified architecture and safeguards

The core owns the study, grouped workload splits, monetary reservations, candidate selection, policy freezing, final-test entitlement, and acceptance checks. Extensions own database configuration, physical copying, native execution, exact truth, compatibility identities, original identifiers, and cleanup. The public SDK is independent of the harness and concrete database clients. Extension callbacks remain trusted code; namespace services are organizational boundaries, not process isolation.

The extension discovery path rejects duplicate names, unsupported API versions, malformed descriptors, mismatched profiles, and unsupported declared capabilities. Runtime policy features and collection groups come from the selected profile. Semantic and native identities are recorded separately. An independently packaged test extension completed the workflow against an unchanged built core wheel, using different features, checkpoints, identifiers, and work units.

The policy validator enforces the bounded tree, runtime-only inputs, numeric types, finite values, int64 literals, depth and node limits, and bounded shape-model payloads. Native qualification confirmed continuation after interpreter failure. Development artifacts and private evaluator artifacts have separate access scopes. Artifact reads verify their hash, size, and regular-file type and reject symlinks; writes use pinned directory descriptors and atomic replacement.

Monetary reservations use transactional SQLite state and conservative maximum charges. Retry attempts receive separate reservations. Timeouts and missing authoritative usage retain possible charges. Bound violations disable further calls, and resume cannot change the stored monetary contract. These are verified accounting controls under the configured provider pricing and token-bound assumptions; no paid provider call was made in this audit.

Workload grouping keeps synthetic anchor families and near-duplicate supplied vectors together. Development tools reject protected vectors and protected synthetic anchors. Calibration exposes selected aggregates. Frozen policies bind dataset, copy, workload, evaluation configuration, and backend compatibility. Final-test entitlement is consumed transactionally before measurement; interrupted final tests cannot silently replay. Evaluation retains failed pairs, checks duplicate and predicate violations, handles boundary ties, and bootstraps independent groups rather than treating repetitions as independent queries.

Pgvector qualification exercised physical index preservation, both backup methods, source-role search defaults, authoritative SQL without index plans, real stops, ordered checkpoint evidence, truncation, original signed bigint identifiers, quoted fields, null metadata, HOT visibility, duplicate vectors, aborts, timeouts, reuse, non-HNSW paths, snapshot invalidation, marked fallback, and repeated cleanup. These results qualify the exercised ARM64 fixture and data profile. They do not establish a latency improvement or production cutover qualification.

## Detailed findings

### F1 P1 Harness UI cannot start

[The compatibility wrapper](/Users/danielarturi/Developer/JinyangLiWork/harness/src/fannbench/filters.py:1) forwards `validate_filter` and `evaluate_filter` but omits `BOOLEANS`, `COMPARISONS`, and `NULL_TESTS`. [The UI API imports those names](/Users/danielarturi/Developer/JinyangLiWork/harness/src/fannbench/ui/general_api.py:24). `create_app()` therefore raises `ImportError` during workflow API installation.

The complete non-integration harness suite selected 211 tests: 196 passed, 14 failed, and one skipped. All 14 failures were caused by this missing import. Assigning the three existing shared constants to the wrapper in memory, without editing source, produced 210 passes and one skip. The built 0.4.1 wheel matches this source, so the regression is present in that artifact as well.

Re-export the existing constants and preserve the wrapper's previous import surface. Require the full harness suite and a built-wheel `create_app()` smoke test in the extraction release gate. The recorded 76 targeted regression passes were insufficient to detect this application initialization failure.

Evidence: [baseline failures](/Users/danielarturi/Developer/JinyangLiWork/research/agent-audit-2026-10-06/harness-tests.log), [controlled shim verification](/Users/danielarturi/Developer/JinyangLiWork/research/agent-audit-2026-10-06/harness-shim-verification.log).

### F2 P1 Restored copies expose the copied cluster

[Restore writes a trust authentication rule](/Users/danielarturi/Developer/JinyangLiWork/agent-pgvector/src/fannagent_pgvector/backend.py:528) allowing every IPv4 address to connect as any database user. The database container uses the default Docker bridge and `listen_addresses=*`. Publishing its host port on `127.0.0.1` does not prevent access through its container address.

A separate disposable container connected to the restored fixture without a password. `SELECT current_user,rolsuper ...` returned `postgres|t`. This is access to the full physical cluster copy, including unrelated databases restored with it. The agent shell's separate `--network=none` setting does not secure this database container.

Use copy-specific authentication and restrict network access to the required callers. Contain outbound connections from the restored cluster as well; copied configuration and database objects need explicit treatment before restoring real clusters. Acceptance criteria should include refusal of an unauthenticated peer connection, access only through the intended authenticated route, and inspection of copied background connection mechanisms.

Evidence: [live observations](/Users/danielarturi/Developer/JinyangLiWork/research/agent-audit-2026-10-06/native-audit-observations.json), reproduced by [native audit driver](/Users/danielarturi/Developer/JinyangLiWork/research/agent-audit-2026-10-06/native_audit.py).

### F3 P2 Copy connections retain source constraints

[The DSN construction](/Users/danielarturi/Developer/JinyangLiWork/agent-pgvector/src/fannagent_pgvector/backend.py:563) copies every parsed source parameter and overrides only `host`, `port`, `sslmode`, database, and user. A source `hostaddr` remains in the new DSN. PostgreSQL uses `hostaddr` for the network address when both parameters are present, so replacing `host` alone does not redirect that connection to loopback. Source authentication constraints such as `require_auth=scram-sha-256` also survive, while the copy currently uses trust authentication. [PostgreSQL 17 connection documentation](https://www.postgresql.org/docs/17/libpq-connect.html#LIBPQ-PARAMKEYWORDS).

The reproduction yielded `host=127.0.0.1` alongside `hostaddr=192.0.2.20` and retained `require_auth=scram-sha-256`. This is a construction test using a documentation address, not a connection to an external server.

Construct the copy DSN from an explicit allowlist and its own endpoint and credentials. Test source DSNs with `hostaddr`, multiple hosts, service settings, required authentication, and channel binding. Verify that both administration and query connections reach the selected copy regardless of source routing parameters.

Evidence: [connection reconstruction](/Users/danielarturi/Developer/JinyangLiWork/research/agent-audit-2026-10-06/core-audit-observations.json).

### F4 P2 Creation does not establish volume ownership

[Preparation creates a deterministic named volume and immediately mounts it for writing](/Users/danielarturi/Developer/JinyangLiWork/agent-pgvector/src/fannagent_pgvector/backend.py:516). There is no ownership check between creation and copying. Docker returns an existing volume for `volume create`; it does not replace its existing ownership labels. An empty foreign volume therefore passes `test -z`, receives the backup, and is subsequently chowned. Cleanup's label check occurs after this mutation.

A newly created audit volume labelled `io.fannagent.run=foreign` retained that label after the same creation pattern requested `claimed`. The restore path's emptiness check then permitted writing a synthetic marker into it. Only this newly created audit volume was used, and it was removed afterward.

Reject foreign existing resources before mounting or writing them. Verify ownership after creation to handle races, and distinguish journaled creation intent from verified external ownership. Test empty and nonempty foreign volumes and confirm that neither receives a write, permission change, or deletion.

Evidence: [volume observations](/Users/danielarturi/Developer/JinyangLiWork/research/agent-audit-2026-10-06/volume-audit-observations.json), [reproduction](/Users/danielarturi/Developer/JinyangLiWork/research/agent-audit-2026-10-06/volume_audit.py).

### F5 P2 Retry can qualify incomplete preparation

[The recovery branch](/Users/danielarturi/Developer/JinyangLiWork/agent-pgvector/src/fannagent_pgvector/backend.py:370) reconnects, optionally qualifies, and returns whenever extension preparation state exists. That state is persisted before [sidecar creation and its manifest](/Users/danielarturi/Developer/JinyangLiWork/agent-pgvector/src/fannagent_pgvector/backend.py:625). An interruption between those phases bypasses sidecar creation on retry.

Injecting failure into `Snapshot.save()` on a fresh physical restore, then calling preparation again, produced `qualified=true` with no sidecar manifest. Native searches still worked, because snapshots were rebuilt from SQL. The defect concerns incomplete preparation artifacts and provenance, rather than demonstrated query corruption.

Persist preparation phases and resume each unfinished phase. Qualification should require the sidecar file, its hash and manifest, and consistent dataset identity. Inject failure before and after each sidecar write, move, manifest commit, qualification commit, and core preparation commit; every successful retry should produce the complete artifact set.

Evidence: [native observations](/Users/danielarturi/Developer/JinyangLiWork/research/agent-audit-2026-10-06/native-audit-observations.json).

### F6 P2 Setup failures escape resource cleanup

[Exploration creates the sandbox before entering the cleanup try block](/Users/danielarturi/Developer/JinyangLiWork/agent/src/fannagent/controller.py:140). Trajectory loading and agent initialization can fail after creation. A deliberately malformed saved trajectory raised `KeyError`; the injected environment recorded creation and no close. An unreadable or hash-invalid saved artifact reaches the same unprotected setup region.

Sandbox containers also have only the generic `io.fannagent.sandbox=true` label, and their identities are not recorded in durable run ownership state. A killed controller therefore leaves no normal run-specific cleanup path for its sandbox. [The deployed session branch](/Users/danielarturi/Developer/JinyangLiWork/agent/src/fannagent/client.py:17) similarly lacks exception-wide cleanup: an injected compatibility exception left its backend unclosed. [Deployment opens its target before entering its try block](/Users/danielarturi/Developer/JinyangLiWork/agent/src/fannagent/cli.py:131), so target initialization failure can leave the source backend open.

Register cleanup immediately after acquiring each resource, using context managers or an `ExitStack`. Journal sandbox identity before creation with labels tied to its run, and include it in verified cleanup. Test malformed or missing trajectories, backend compatibility exceptions, target initialization failures, and process termination after sandbox creation.

Evidence: [setup and session observations](/Users/danielarturi/Developer/JinyangLiWork/research/agent-audit-2026-10-06/core-audit-observations.json), [core reproduction](/Users/danielarturi/Developer/JinyangLiWork/research/agent-audit-2026-10-06/core_audit.py).

### F7 P2 Extension upgrades can strand resources

[The common run opener rejects changed runtime or native identities](/Users/danielarturi/Developer/JinyangLiWork/agent/src/fannagent/controller.py:77), and `clean` uses that opener before accessing the resource journal. The execution compatibility guard therefore prevents cleanup even though removing labelled owned resources does not require a compatible runtime policy.

Changing the fake extension descriptor's checkpoint interval for an existing schema-v2 run caused `clean` to fail with `extension runtime profile changed; use a new run`, before invoking backend cleanup. The same guard applies to pgvector resources.

Give schema-v2 cleanup a path that validates the installed cleanup contract and resource ownership without requiring the old execution profile. Retain strict compatibility checks for exploration, evaluation, deployment, and serving. Test cleanup after both semantic and native profile changes with source credentials absent. This does not require enabling unsupported legacy-run operations or migrating old ledgers.

Evidence: [upgrade cleanup refusal](/Users/danielarturi/Developer/JinyangLiWork/research/agent-audit-2026-10-06/core-audit-observations.json).

### F8 P2 Tool work survives sandbox timeout

[Shell execution has a 180-second timeout](/Users/danielarturi/Developer/JinyangLiWork/agent/src/fannagent/environment.py:97), while the tool client waits for up to 3,600 seconds. Calibration and real-stop labeling run synchronously on the host broker thread. [Broker shutdown sets a flag and joins that thread](/Users/danielarturi/Developer/JinyangLiWork/agent/src/fannagent/broker.py:257); it does not cancel an active tool operation.

A controlled slow tool remained active after broker shutdown was requested, and shutdown remained blocked until the tool was explicitly released. Consequently, when a legitimate long calibration exceeds the shell timeout, the sandbox stops while its host-side database work can continue. The per-query SQL timeout limits individual statements, not the full labeling or measurement operation. No live operation was allowed to run for 180 seconds merely to demonstrate this mismatch.

Propagate operation deadlines and cancellation into study loops, descriptor computation, and active database calls. Align shell, client, and broker timeout behavior, or expose long work as explicit jobs with bounded polling and cancellation. Test cancellation during labels, calibration, and final evaluation, preserving partial progress and the one-shot test entitlement.

Evidence: [broker shutdown observations](/Users/danielarturi/Developer/JinyangLiWork/research/agent-audit-2026-10-06/core-audit-observations.json).

### F9 P2 Host disk and output capture are unbounded

[The sandbox receives a writable host workspace bind mount](/Users/danielarturi/Developer/JinyangLiWork/agent/src/fannagent/environment.py:70). Arbitrary files written there bypass the artifact database's evidence quota. The 256 MiB tmpfs bounds `/tmp`, not `/workspace`. The database sidecar is also written directly rather than charged as artifact bytes.

[Subprocess execution captures all stdout and stderr](/Users/danielarturi/Developer/JinyangLiWork/agent/src/fannagent/environment.py:98) before trimming the returned output to 64,000 characters. Docker's sandbox memory limit does not bound the host Python process's captured output. A verbose or runaway command can therefore consume substantial host memory or disk within an otherwise limited container. This finding follows directly from the resource paths; the audit did not fill the user's disk or induce an out-of-memory failure.

Drain process output into a bounded buffer, and use bounded scratch storage or enforce a workspace quota. Account for direct sidecars and broker files separately from registered JSON artifacts. Add host analysis admission checks or worker limits for the in-memory profile. Verify these controls with modest disposable quotas and output bursts, without stressing the host.

## Verification results

| Check | Result | Practical scope |
| --- | --- | --- |
| Core non-integration suite | 32 passed | Study, accounting, SDK, artifacts, serving and deployment using simulations |
| Pgvector non-integration suite | 8 passed | Preconditions, namespace, journal, cleanup and import boundaries |
| Core and pgvector Ruff checks | Passed | Existing source and tests |
| Public SDK mypy | Passed across 17 files | Published SDK typing boundary |
| Sandbox integration | 1 passed | Container broker access and exclusion of private paths and Docker socket |
| Fresh ARM64 native qualification | 18 passed | Supplied and streamed-WAL backups, six fresh restores, direct native and SDK scenarios |
| Full harness non-integration suite | 196 passed, 14 failed, 1 skipped | Current source; failures are F1 |
| Harness with in-memory constant exports | 210 passed, 1 skipped | Confirms F1 accounts for every baseline failure; source remains unchanged |
| Installed-wheel acceptance | Passed in three fresh environments | Core alone, core plus pgvector, core plus independent extension; cached dependencies only |
| Wheel and source comparisons | No differing included source files | Core 0.2.0, pgvector 0.1.0 and harness 0.4.1 |
| Audit fixture cleanup | Confirmed | Audit qualification source/copies, sandboxes and marker volume removed; evidence and backups retained |

The fresh native results are [recorded here](/Users/danielarturi/Developer/JinyangLiWork/agent-pgvector/.qualification/be74b1d039/results.json). The first supplied restore included the F5 failure injection before retrying; its subsequent native scenarios passed despite the absent sidecar, exposing a qualification coverage gap. Installed-wheel acceptance ran from outside the repository and preserved the existing frozen policy after installing the unrelated extension. [Wheel acceptance log](/Users/danielarturi/Developer/JinyangLiWork/research/agent-audit-2026-10-06/wheel-acceptance.log).

## Release and operational limits

ARM64 qualification is real but limited to the disposable fixtures and normalized cosine float32, bigint, single selected relation/index, in-memory profile. AMD64 qualification, actual paid-model provider behavior, public package/image publication, broader data and engine coverage, production traffic cutover, writes, replication, and HA remain open gates. Native probe and session qualification does not establish an accepted native performance policy or a successful paid-model optimization study.

The engine recipe pins upstream commits, patch hashes, and its PostgreSQL base image. The workspace Dockerfile uses a floating Python image and unpinned NumPy/PyArrow installation; engine package installation also resolves apt packages during build. The current artifact hashes establish identity, while repeated builds are not guaranteed to produce identical bytes. The local wheels were verified; they remain unpublished.

No dependency vulnerability scanner was installed, and this audit makes no CVE clearance claim. Resolved direct and important transitive versions are recorded in the evidence manifest. Before publication, run a dependency and image vulnerability scan, preserve package license metadata and notices, and connect the full unit, integration, wheel, and UI smoke checks to a repeatable release gate. No CI configuration is present in the audited package directories.

Evidence exhaustion also deserves a failure-path check: final entitlement is consumed before measurement, but its fallback report is written through the same quota-limited artifact store. A full quota can prevent saving the terminal report. Preserve small terminal status and failure information outside the exhausted evidence allocation without restoring test entitlement. This is a code-analysis follow-up rather than a separately reproduced priority finding.

## Remediation order

1. Restore the harness compatibility exports and verify application initialization from the built wheel.
2. Secure and contain the copied database, then repair copy DSN construction and verify ownership before volume mutation.
3. Make preparation phase-complete, journal sandbox ownership, and close resources on every initialization failure.
4. Permit safe schema-v2 cleanup across profile upgrades, propagate tool cancellation, and enforce host output and storage bounds.
5. Repeat the affected native failure scenarios, full harness suite, installed-wheel checks, and provider/architecture release gates. Publish only the scope that those checks actually qualify.

The core policy and evaluation design can be retained. The necessary changes concentrate on the compatibility wrapper and operational boundaries around otherwise well-tested algorithms.

## Reproduction evidence

[Evidence manifest](/Users/danielarturi/Developer/JinyangLiWork/research/agent-audit-2026-10-06/manifest.json) contains source identities, wheel hashes, dependency versions, and result references. [Core reproductions](/Users/danielarturi/Developer/JinyangLiWork/research/agent-audit-2026-10-06/core_audit.py) use controlled doubles and temporary runs without provider calls. [Native reproductions](/Users/danielarturi/Developer/JinyangLiWork/research/agent-audit-2026-10-06/native_audit.py) run the existing disposable qualification fixture and inject one sidecar failure. [Volume reproduction](/Users/danielarturi/Developer/JinyangLiWork/research/agent-audit-2026-10-06/volume_audit.py) uses a new audit-labelled volume with a synthetic marker.

The native driver requires the locally built ARM64 stock fixture and qualified instrumented image. It creates only fresh labelled sources and copies, and retains backup/evidence artifacts under the extension qualification directory. The audit neither connected to user databases nor made paid model calls.
