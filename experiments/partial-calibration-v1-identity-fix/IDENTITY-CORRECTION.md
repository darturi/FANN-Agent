# Startup identity guard correction and release hold

The third B2f attempt (21159802_0) created two readers and loaded the snapshot,
then raised `Snapshot eligibility changed` before any search. Its checksum,
30 archive members, raw lock, source/copy/catalog/protection and cleanup verify.

The runtime hashed `{field_map, source_ids, votes}`, whereas the immutable
eligibility.json contains only `{source_ids, votes}`. This comparison necessarily
fails for unchanged values. JSON encoding itself matches. The fix preserves the
frozen file and validates its exact two-key schema. It separately requires
`{"m_000000": "total_votes"}` and the existing experiment.snapshot_identity.
The latter restores an explicit guard present in B2d but omitted in B2f.

The prior integration tests called acquisition directly. They exercised the real
snapshot method but bypassed the runtime's startup comparison. The new entry-point
fixture invokes main itself through startup/acquisition/final checks/cleanup.
Database replies, proc/affinity, OS paths and resource boundaries remain synthetic;
full-data bit validation and real processes are not simulated as native proof.
A separate full-size ID/vote-only fixture reproduces the exact schema failure.
Changed IDs/votes, mapping, dataset identity and added keys fail closed.

Actual frozen reader construction, role admission, binding, snapshot, native and
exact query methods are retained. Full successful fixture counts are 16,242
attempts/4,200 plans/10 admissions/two epochs. Startup identity/catalog/server
failures preserve failed raw/source inventories and close readers/servers. A
cleanup failure cannot qualify. Existing strict acquisition/replay/budget/PID/
affinity/archive tests remain. Measured SQL/timers/scoring/schedule/gates and all
scientific/native frozen files stay unchanged.

The scheduler reports MaxRSS33534232K under a32GiB request. Its attribution is
unresolved; no OOM is recorded. Frozen snapshot loading keeps Python vectors,
NumPy vectors and constructs a full canonical JSON string/bytes for identity.
That is a plausible startup peak, not a measured attribution. The old configured
14.25GiB estimate is not a demonstrated full-process/job upper bound.

**Production packaging is blocked.** No fourth native job, transfer helper or
submit command is released. The read-only Slurm accounting configuration and an
explicit resource feasibility decision are needed before a new release. Any
necessary cap/design amendment must be separate and prospective; no margin,
graph, source, prior reservation or consumed allowance may change.
