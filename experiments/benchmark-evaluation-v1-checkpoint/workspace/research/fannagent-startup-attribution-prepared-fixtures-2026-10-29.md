# A2 compatibility: verified fixture-preparation deadline and prepared fixtures

October 29, 2026, America/New_York.

**Postrun update:** The prepared-fixture allowance was spent by job 21382454 and
failed at the source deadline after 119 passing cases. The handoff below is now
historical; do not resubmit it. See the [verified third timeout and budget
review](fannagent-startup-attribution-third-compatibility-timeout-2026-10-29.md).
No further capsule or main A2 handoff is currently released.

## Verified native result

Job21367064, campaign
`reviews-startup-attribution-compatibility-v1-fixture-fix-20261029T213607Z.drh59xwh`,
failed at the unchanged300-second source deadline. The host ended at313.689seconds;
Slurm records FAILED/1:0 after00:05:17 with2CPUs/4GiB. No main A2 launched, and the
records report zero real database connections, SQL, PostgreSQL servers, ANN/exact
searches and provider calls. The recorded MaxRSS1,380,080KiB is not a main-workload
resource qualification or evidence to change any memory margin.

The16-member archive checksum is
`6fd2a830378bc21be90378169aa72855cb1caf791cd73320b440a63629169a62`.
All extracted bytes,11 locked file hashes and submission/job/package identity
verify. Native3.12.15 provenance, all three offline constructor dependencies and
separate final capsule/SIF integrity pass. The lock correctly remains incomplete;
source/sealed target receipts, final source guard and candidate manifest are absent.

[Independent returned verification](../trials/torch-reviews-startup-attribution-compatibility-v1-fixture-fix/postrun-audit-2026-10-29/returned-verification.json),
[raw campaign](../trials/torch-reviews-startup-attribution-compatibility-v1-fixture-fix/returned/reviews-startup-attribution-compatibility-v1-fixture-fix-20261029T213607Z.drh59xwh/).

## What changed in the diagnosis

96source cases have pass events, with no error/failure/subtest-error events.
The earlier missing metadata defect is fixed: all replay tests and the four-signal
cleanup case pass. Replay setup itself completes a bounded synthetic runtime and
its full metadata-ledger replay. The separate dedicated full-runtime assertion case
starts but times out during its fixture reseal, before that case's runtime body.
This partial prefix cannot satisfy the frozen128+128 correctness gate.

Four class-setup intervals last37.143,38.001,67.919 and41.451seconds, totaling
184.514seconds. They include full package builds and, for replay, a runtime fixture;
they are not a measurement of hashing alone. The four-signal case takes77.349seconds.
Five periodic stack samples show three full seed-build hash operations, a fixture
write, and a fixture manifest hash. These samples and the event ledger support a
fixture-preparation bottleneck; they are not evidence of an ANN/backend deadlock,
a deterministic stopping failure or a new reference mismatch.

The first fixture correction removed repeated bulk copies but retained five full
seed builds per suite, each with archive/hash work, plus repeated reseal hashing
of immutable hardlinks. Local ~112second suites did not establish native headroom.
The next change addresses that redundant preparation while retaining every test,
all real production code paths and the original deadlines.

[Original source events](../trials/torch-reviews-startup-attribution-compatibility-v1-fixture-fix/returned/reviews-startup-attribution-compatibility-v1-fixture-fix-20261029T213607Z.drh59xwh/run/guard-source.events.jsonl),
[stack/test log](../trials/torch-reviews-startup-attribution-compatibility-v1-fixture-fix/returned/reviews-startup-attribution-compatibility-v1-fixture-fix-20261029T213607Z.drh59xwh/run/checks-source.log).

## Frozen local correction

[PREPARATION-FREEZE.json](../trials/torch-reviews-startup-attribution-compatibility-v1-prepared-fixtures/PREPARATION-FREEZE.json)
precedes implementation. The isolated capsule is
`torch-startup-attribution-compatibility-v1-prepared-fixtures`.

1. Each child calls the actual unmodified synthetic builder once in independently
   owned temporary scratch. Five class setup requests reuse that seed only after
   complete byte fingerprints and real archive/checksum verification. Native,
   unspecified, duplicate/existing targets and changed seed/archive/checksum inputs
   reject. Verify again at the end and restore the builder on every exit.
2. Keep immutable hardlinked runtime-fixture files and four separately copied
   mutable files. Fingerprint the complete seed before and after every fixture.
   For its reseal, require exact inventory/no symlinks and the same immutable
   inodes, reuse the hashes just computed for those identical bytes, and recompute
   every mutable content hash. Reject detached/new files. The main runtime's
   production verification still performs its original hashing; it is not cached.
3. Keep all128 original source and128 sealed cases, original assertions and strict
   provenance. The separate guest candidate still runs the original unpatched
   builder. The full job therefore performs three actual full builds instead of11.
   Each suite must prove5requests/1build/4reuses/6full seed/archive verifications,
   restored builder,10clones/10reseals/10unchanged-seed proofs and restored guards.
4. Keep real constructor dependency regression, immediate fail-fast errors and
   per-test events. New synchronous fixture-stage events expose seed build/hash,
   clone, reseal and final verification boundaries without a background watchdog.

The original main A2 recipe, A0/A1, references, scientific workload, graphs/module,
policies, production copies/verification and margins remain byte-identical.

[Helper source](../agent/experiments/startup-attribution-compatibility-v1-prepared-fixtures/fixture_io.py),
[checker](../agent/experiments/startup-attribution-compatibility-v1-prepared-fixtures/check_child.py),
[implementation scope](../agent/experiments/startup-attribution-compatibility-v1-prepared-fixtures/README.md).

## Local finalization issue caught before release

An initial local candidate passed128 packaged cases but did not complete its final
guard receipt. A one-second stack sample of owned Mac CPython3.12.7 PID4478 shows
the main thread waiting in faulthandler watchdog cancellation while its watchdog
is in traceback/dump_frame code. This establishes the observed cancellation stall,
not a general Python bug or the cause of the separate native deadline. The owned
process was stopped, and its unqualified candidate/logs/sample were preserved.

[PREPARATION-AMENDMENT-1.json](../trials/torch-reviews-startup-attribution-compatibility-v1-prepared-fixtures/PREPARATION-AMENDMENT-1.json)
records the correction before implementation. Remove asynchronous dump/cancel
threads; retain fatal-error faulthandler and synchronous test/fixture-stage events.
Do not claim a native3.12.15 watchdog failure from the Mac observation. Rerun the
checks through final guard publication, with a240-second local outer timeout.

[Preserved local review candidate](../trials/torch-reviews-startup-attribution-compatibility-v1-prepared-fixtures/review-candidates/async-watchdog-stall/).

## Decision gates and revised critical path

- Local gate:43source and43sealed compatibility checks, plus128guarded original
  source and128packaged-fixture cases through complete guard/final seed proofs.
  Separately compare the optimized manifest byte for byte with the actual unchanged
  original reseal helper on a bounded fixture. Verify archives, strict dependencies,
  stage events and preservation of both earlier failed capsules/raw.
- Native gate: one distinct qualification allowance, maximum15minutes/2physical
  CPUs/4GiB; source300s, candidate90s, sealed300s, guest720s and unchanged reserves.
  Require all128+128 cases and exact identities/dependencies/build/clone/reseal/
  restoration/exit/locked final integrity proofs. Zero real DB/SQL/server/search/
  provider/fit. Both previous compatibility allowances remain spent; no automatic
  retry or old reservation reuse. Local timing is not a native headroom guarantee.
- Main gate: only after independent native ingestion/review may C3 prepare/review
  a production main A2 seal. Its1h/4CPU/32GiB zero-search acquisition, A3 diagnosis,
  any remedy and any full B2f release stay separate and held.

**Critical path:** verified second C2 failure → prepared-fixture design and local
complete-guard qualification → one native128+128 qualification → independent review
→ C3 main production seal/release → main A2 → A3 interpretation.

[Final local release verification](../trials/torch-reviews-startup-attribution-compatibility-v1-prepared-fixtures/release-verification.json),
[actual original-helper equivalence](../trials/torch-reviews-startup-attribution-compatibility-v1-prepared-fixtures/actual-reseal-equivalence.json),
[exact commands](../trials/torch-reviews-startup-attribution-compatibility-v1-prepared-fixtures/COMMANDS.txt).
