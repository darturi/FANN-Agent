# Native A2 compatibility checks: zero database work

This is a separately bounded correctness job required before the main A2 release.
The corrected main harness passes128 local source checks. The local linux/amd64
Docker attempt emitted QEMU SIGSEGV and produced no Python test receipt. Its
owned container was stopped/removed; OOMKilled=false. It is not a target pass.

One15-minute/two-physical-CPU/4GiB Slurm allocation runs the unchanged SIF on native
Torch hardware. It checks the corrected main source and a sealed synthetic
candidate,128 tests each. All work is synthetic: <=64x768 original constructor
rows or metadata-only counts, mocked transport/resources. No real DB connection,
SQL, PostgreSQL server, ANN/exact search, fit or provider is permitted. Main A2 and
full B2f remain unreleased. Correctness is not native memory/quality/performance.

The image and capsule are hash-verified. Workspace/source/A1 files are mounted
read-only; private scratch holds only fake fixture files and candidate copies.
The old M3 test-path alias points to A1's byte-identical original native files.
No retained/prepared database or other results root is mounted into the image.
Only controlled original launcher shell fixtures may spawn from a test child.
Connection class/module APIs and Python network audit events are blocked; guard
bindings restore and each child exits before publishing a pass. Tests may replace
the blocked module connect with their existing fake transport, never a real DB.

Finite limits and the exact main recipe are frozen in COMPATIBILITY-CONTRACT.json.
Host startup90s, guest720s (source300/seal90/sealed300/cleanup30), host cleanup60s
and30s outer margin fit the900s allocation; all waits clamp to remaining reserve.
Each suite must pass exactly128 tests under3.12.15 with complete source/recipe/
provenance hashes and zero guard denials. Missing/failed/pending evidence holds
release; there is no automatic retry or allowance reuse. A partial/failing return
remains collectable after terminal scheduler status.

The package includes immutable prior source data as hash/copy inputs for existing
integrity tests. It performs no full snapshot scan or native query; dataset files
are not substitute measured outcomes. A1's original/local3.12.7 reference and all
old seals are preserved. Successful source/sealed candidate checks inform a later
local production package/release review; this job cannot submit the main A2 job.

Generated COMMANDS.txt separates Mac upload/download from Torch submit/status/
terminal collect. cc_control.py status checks this compatibility job. It is not
the completed direct image inventory and is not the future main A2 diagnostic.
