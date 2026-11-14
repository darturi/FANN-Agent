# Runtime qualification status

Protocol: finalized and sealed in `../freeze/protocol-freeze-v2.json`. Original frozen split unchanged. Scientific execution choices are in `../protocol/study-protocol.md` and `config.json`.

## Completed locally

- Staged an isolated copy of the pinned original engine; historical engine, database and results remain untouched.
- Replaced the votes108-only lookup attachment with predicate-scoped immutable lookup files for unfiltered and all six published thresholds. Each attachment checks relation/index identity, row/eligible counts, snapshot constraints and file ownership/mode.
- Added local-map reference binding across those predicates, retained checkpoint/forced-stop/continue logic at 16/32/64, and made causal turnover available to the policy-rule compilation path.
- Compiled the Linux x86_64 module offline in the cached research image. Module SHA256: `2383b3faa99d199c631d3f3787e7ef1ebe067af982f5cba850d3de7208337da8`.
- Ran real PostgreSQL on a synthetic 8-dimensional fixture under local amd64 emulation. All seven predicates exercised all three checkpoints and passed shared/local/native output parity, forced-stop parity, live no-stop parity, and rejection of mismatched map headers. This is synthetic smoke evidence, not the retained graph or benchmark latency evidence.
- Eight focused Python checks passed for all-filter parameter routing, wrong predicates/fields/operators, exact ties, partial native outputs, invalid/duplicate/nonfinite outputs and the pre-dispatch search cap. Shell/Python syntax and final capsule hashes passed.
- Verified the inherited restore package's paths and all serialized query vectors: its 200 groups are within the frozen 450 development groups. The new qualification input contains exactly 3,150 requests, covering 450 development groups and all seven conditions. No validation/test query values are shipped.

## Pending target check

The inherited full restore loader was attempted locally but QEMU terminated with SIGSEGV while loading the emulated amd64 Python dependency stack. Its log is retained in `checks/legacy-loader.log`. This did not execute ANN/exact searches on the frozen dataset and is not counted as a passing bootstrap test. The native Torch job will check the actual loader/restore and fail before qualification if it cannot load. The all-filter module smoke is independently passed as described above.

Direct Torch SSH failed strict host-key verification; no trust entry was changed. The user will execute the prepared commands in their working Torch session. See `../kits/COMMANDS.txt`.

The active payload is `../kits/development-runtime-v2.tar.gz` with a checksum sidecar. Version1 is a preserved, undispatched local draft; version2 adds complete input/restore integrity checks, persistent per-family readers, partial native-output reporting, eligibility-return evidence and local return reconstruction. The protocol choices did not change between those packaging drafts.

## Native development run

One private restore on the original graph; 4 physical CPUs, 48 GiB, 3 hours, at most 40,000 search attempts; zero providers/validation/test queries. Verify base image/runner/input/backup/index identities and read-only mounts. Build seven maps once under a keeper lock. For all 3,150 requests compare native versus shared capture, execute actual forced stops, compare live stop decisions and output identities, and verify no-stop continuation. Compare local/shared features on ten development groups per condition. Preserve exact references and query-level outcomes, incompleteness, features, collection cost, live request cost, plans, map lifecycles and machine/resource metadata. Verify data/index again and stop the database before reporting success.

Low-recall or incomplete native results at selective predicates are retained as scientific findings; they do not become a hidden filter exclusion. They fail policy-quality eligibility under the study protocol, while runtime parity can still qualify if the adapter reproduces that behavior correctly.

## Completion gate

Do not mark original-graph runtime qualification complete until the Slurm job is confirmed COMPLETED/0:0, its checksummed return is collected, and `verify_return.py` reconstructs all 3,150 records locally. The runtime gate remains pending. No agent proposal calls have run; provider usage reconciliation also remains required before dispatch under the finalized procedure.
