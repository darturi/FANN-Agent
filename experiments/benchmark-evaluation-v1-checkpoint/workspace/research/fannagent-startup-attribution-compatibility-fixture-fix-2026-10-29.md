# A2 native compatibility failure and fixture correction

Date: October 29, 2026, America/New_York.

## Outcome and evidence

Compatibility job `21348020` failed; main A2 never launched. The downloaded archive
has13 unique regular files and SHA-256
`f694e12e1cd91f3caa5d3da8c51595e4eb595c11c84f5c8b0ba498021359f623`.
Its extracted bytes, submission/package/job identity and all eight locked files
verify. The lock correctly says incomplete. Native Python3.12.15, libraries,
private hooks and query-parser fingerprints match the corrected image reference.
This is not complete target correctness: source/sealed target receipts, terminal
guard proof and candidate manifest are missing. The old host attempted final
source/image checks but did not publish a separate positive integrity receipt.

The source log shows86 completed successes (85 single-line successes plus one
multi-line argparse-negative success), then `ReplayTests.setUpClass ... ERROR`.
The suite continued into the four-signal runtime test and hit its300-second cap
at301.027 seconds. The host ended at313.835 seconds; Slurm says FAILED/1:0 and
00:05:17. The recorded MaxRSS is2,294,136KiB against4GiB. No resource or speedup
qualification follows. The controller's earlier21348019 message was its
`sbatch --test-only` check; the recorded dispatched job is21348020.

[Archive/lock verification](../trials/torch-reviews-startup-attribution-compatibility-v1/postrun-audit-2026-10-29/returned-verification.json)
and [original source-suite log](../trials/torch-reviews-startup-attribution-compatibility-v1/returned/reviews-startup-attribution-compatibility-v1-20261029T172935Z.e69x0afy/run/checks-source.log).

## Diagnosis

The user's subsequent read-only scratch output records three synthetic runtime
failures with FileNotFoundError for
`trials/torch-reviews-first/inputs/local-identity.json`. Each runtime body lasted
approximately0.93–0.98 seconds. Their phase timestamps were23.502 and25.325 seconds
apart. These are retained user-pasted diagnostics, separate from the verified
archive. Their synthetic observer SQL/full-scan counters describe test doubles,
not real database work.

The actual frozen `TorchBackend.__init__` reads that metadata record. The old
capsule included only runner.py and manifest.json from the first bundle. Local
checks used the ambient workspace and therefore missed this dependency. This is
a packaging defect, not evidence of a changed Python/private-hook reference.
A direct local negative regression now reproduces that exact missing-file error;
the actual constructor succeeds using the corrected packaged bundle.

The source suite also builds five full seeds (~299MB each). Each runtime fixture
then copied and resealed another full seed. Existing timestamps establish a large
preparation interval outside the ~one-second failing runtime; they do not isolate
individual copy, hash or compression costs. A larger timeout alone would neither
repair the missing input nor expose the first traceback. Standard unittest deferred
the setup traceback until its final summary, which the timeout prevented.

[Retained diagnostics and diagnosis](../trials/torch-reviews-startup-attribution-compatibility-v1/postrun-audit-2026-10-29/retained-diagnostics-and-diagnosis.json),
[actual constructor](../trials/torch-reviews-first/runner.py),
[original fixture](../agent/experiments/startup-attribution-v1-image-reference/sa_fixtures.py)
and [package builder](../agent/experiments/startup-attribution-compatibility-v1/package.py).

## Isolated correction

The [correction freeze](../trials/torch-reviews-startup-attribution-compatibility-v1-fixture-fix/FIX-FREEZE.json)
preceded implementation. The new capsule is
`torch-startup-attribution-compatibility-v1-fixture-fix`. It preserves the failed
package, source, raw, binding and reservation. The main A2 recipe, historical and
native references, A0/A1, graph/module/data/policies and all scientific margins
remain unchanged.

1. Include the exact1,666-byte original local-identity.json alongside runner.py
   and manifest.json. Hash-pin and verify all three before suite execution. The
   frozen constructor consumes settings/binding metadata from the historical
   record and obtains index identity from its private work record; this record
   does not replace native environment provenance.
2. Optimize only ephemeral synthetic runtime_fixture clones: hardlink immutable
   temporary seed files, separately copy manifest/config/eligibility/queries,
   reject symlinks/native seeds/link failures, and fingerprint the seed before
   and after each fixture, including exceptions. Production copy paths are not
   patched. Ten clones avoid repeated bulk writes; no native speedup is inferred.
3. Print errors/failures immediately, fail fast, retain per-test events and
   bounded periodic stack traces. Publish the restored guard receipt even after
   an unexpected Python exception. Emit a separate final host-integrity result.
4. Validate the actual constructor through the isolated packaged bundle path,
   reproduce missing metadata, exercise clone isolation/restoration/tamper/flag/
   symlink failures and setup fail-fast behavior, and run the unchanged128 main
   checks through both source and packaged fixture paths.

[Corrected implementation](../agent/experiments/startup-attribution-compatibility-v1-fixture-fix/README.md),
[clone helper](../agent/experiments/startup-attribution-compatibility-v1-fixture-fix/fixture_io.py)
and [guard/result runner](../agent/experiments/startup-attribution-compatibility-v1-fixture-fix/check_child.py).

## Bounds, decision gates and next action

The correction declares a distinct one-allocation allowance with the same limits:
15minutes, two physical CPUs,4GiB; source300s, candidate90s, sealed300s, guest720s
and unchanged startup/cleanup reserves. Real SQL/database/server/search/provider/
fit counts remain zero. The old allowance is spent and is never reset. There is
no automatic retry, main A2 dispatch or full B2f release.

- Local release gate:33 source and33 sealed compatibility checks,128 guarded
  source main checks and128 packaged-fixture main checks; exact seals, dependency,
  guard/seed-restoration and prior-input preservation verification must all pass.
- Native gate: all128 source plus128 sealed checks under unchanged SIF3.12.15,
  exact recipe/provenance, dependency hashes, zero guard denials, restored
  bindings, unchanged seeds, successful exits and locked final integrity proof.
  A partial prefix cannot qualify.
- C3 gate: independently ingest/review the native return, then separately seal
  and review the production main A2 package before its1h/4CPU/32GiB zero-search
  diagnostic can launch. A3 interpretation and any remedy/full B2f remain later.

The revised critical path is **verified failed C2 → dependency/copy/reporting
correction and local packaged-path qualification → one bounded native correction
qualification → C3 main seal/release → main A2 → A3 diagnosis**.

Final local checks, identities and preservation results are recorded in the
[release verification](../trials/torch-reviews-startup-attribution-compatibility-v1-fixture-fix/release-verification.json).
Use the [exact commands](../trials/torch-reviews-startup-attribution-compatibility-v1-fixture-fix/COMMANDS.txt)
for Mac upload, Torch submit/status/terminal collect and Mac download. This launches
only the compatibility correction. Native results remain unqualified until returned
and independently verified. No Torch job or real search was run by Codex here.
