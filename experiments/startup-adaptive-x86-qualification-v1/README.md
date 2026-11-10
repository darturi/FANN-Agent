# A3 adaptive non-emulated x86_64 qualification

This capsule prepares one fresh correctness and bounded CPU qualification job.
All older allowances, bindings and jobs remain spent. Preparation does not launch
Torch. The unique reservation is `.torch-startup-adaptive-x86-qualification-v1-reservation.json`.
Ambiguous, rejected or failed dispatch retains that reservation and cannot retry.

The prospective design is `QUALIFICATION-FREEZE.json`, SHA256
`8da59a6cb15fabe303ec34babc884b168399f7d42e5964eb51e87962b93a20aa`.
Original production/main/A3 files, every existing test, strict image/library/hook
references, native resource guards, scan counts and memory decision remain intact.
The capsule ships original data once and binds its byte-identical frozen aliases
read-only. Owned local mirrors use verified hardlinks for those same aliases.
No dependency, allocator/SIMD or interpreter-version workaround is permitted.

One job uses the original 1h, four distinct physical CPUs, 32GiB maxima, 3000s guest
runtime including a full 600s cleanup reserve, 240s host pre/post and 120s outer
margin. Complete guest caps total2940s, leaving60s for bookkeeping:

| Phase | Seconds |
| --- | ---: |
| Exact native preflight |30|
| Main source, all128cases |420|
| Original main candidate build and exact A3 code snapshot |90|
| Main sealed, all128cases |420|
| A3 source, all272+4cases |600|
| A3 sealed, all272+4cases |600|
| Bounded producer CPU probe |180wall /120CPU|
| Final cleanup and publication |600|

Native guards require x86_64 Linux, x86 ELF machine62, genuine Intel/AMD CPU
information, no QEMU/Rosetta evidence, four distinct physical-core pairs pinned,
and complete exact CPython3.12.15/NumPy2.5.3/PyArrow22/driver provenance. The original
SIF is hashed before and after. Sources, capsule and image remain read-only;
only owned scratch/results are writable. No database, provider or search is used.

Every original128+128 main case and272+272 A3 case runs; four frozen review guard
cases augment each A3 phase to276. Immediate per-case events, original fixture
seed/hash/reseal/binding proofs, source/origin maps, cleanup, host/guest timing,
locks and terminal scheduler evidence are required. All return ingestion is
bounded and data-only. Returned code is never executed.

The CPU probe uses the unchanged real producer/constructor/identity, five fixed
compact/fallback profiles,16/64rows and three repeats. It can qualify non-emulated
bounded CPU measurements and report a prespecified projection screen against the
unchanged600s stage. Synthetic projections cannot qualify full native startup CPU,
compactability or aggregate memory. Full startup/resource/B2f release remains held.

Use the external `COMMANDS.txt` only after local release verification passes.
Upload and login verification do not dispatch a job; only the single explicit
`cc_control.py submit` does. Repeat status/collect as documented, never submit.
