# A1 local readiness: zero-search startup attribution

This implements the immutable A0 `startup-attribution.v1` design in an isolated
harness. It changes no application/vendor code, data, graph, module, policy,
constructor, SQL, cursor size, dtype, scientific gate or resource margin.

A1 is a local implementation/readiness step. **A2/native handoff is unreleased.**
`sa_control.py`, submission/dispatch and both native entry points block a native
launch. No upload/submit commands are issued here. A later release needs its own
reviewed seal; this local readiness artifact stays immutable.

The original producer and constructor execute under local CPython3.12 LINE
monitoring, tool4, with DISABLE and explicit mask/callback/tool restoration.
Nine pinned Psycopg3.3.6 hooks account for existing internal command routes;
actual private methods are tested with synthetic transports. Parameterized templates
are validated with the version-pinned uncached pure parser; cursor query state is
not used as a validation shortcut. Actual PostgresQuery/Transformer conversion
and _execute_gen prepared/unprepared routes are tested, with no duplicate
parameter dumping or priming of the driver query cache. Attempt IDs are
reserved before dispatch, then one joined completion/error record is buffered
per dispatch. Pending IDs remain explicit on failure; a hard-kill prefix may
undercount unflushed work and cannot qualify. Counts describe Python driver
requests, not network packets.

All102 checkpoints, page/row/transaction ledgers, original snapshot retention and
source/integrity work are required for complete acquisition. Final close,
rollback, server stop and protection work must still run if observation fails.
A separate data-only replay rejects missing/tampered checkpoints, dispatches,
pages, ordering, role coverage or combined budgets. The original independent
resource/scientific replay runs first; an informative attribution outcome grants
no resource-margin, calibration or treatment-performance qualification.

The frozen aggregate observer budget is conservatively partitioned internally:
host3CPU/6wall seconds,1024reads/8MiB,2MiBraw,32roles/5000metadata entries;
runtime12CPU/24wall seconds,7168reads/56MiB,14MiBraw,224roles/45000entries.
The host flushes before the container so only one pending writer is active.
No frozen total cap is increased. Sampler-plus-diagnostic totals are independently
checked against the original60CPU-second/500000read/512MiB envelope.

`DRIVER-REFERENCE.json` records the local pinned interpreter/library/private-method
source/signature reference. It is **not an attestation of the Torch image**.
A later A2.0 image preflight must match it (including libpq capability) before any
costly restore, or stop. The local Linux-probe checks use synthetic proc/cgroup
files; no native database or scientific experiment runs in A1.

Local reproduction (from workspace root):

```sh
PYTHONDONTWRITEBYTECODE=1 agent/.venv/bin/python \
  agent/experiments/startup-attribution-v1/run_checks.py \
  --phase source --receipt /private/tmp/startup-attribution-checks.json
```

Fixtures use at most64source rows x768, tiny canonical oracles, or metadata-only
page sizes/counts. Metadata-only full-count ledgers prove accounting logic;
they do not prove native data identity, resource use or attribution results.
The155 unchanged prior harness tests are separately retained as baseline
regression evidence; A1's own source and sealed suites exercise its new paths.
