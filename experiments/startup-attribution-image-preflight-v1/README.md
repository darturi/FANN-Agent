# A2 image compatibility inventory

The A2 finite release review found a mismatch before dispatch. A1's unchanged
`DRIVER-REFERENCE.json` records local CPython 3.12.7; the saved pinned image's
configuration and Python header specify 3.12.15. The image inventory below is
needed before a separate compatibility decision. A2's native diagnostic and full
B2f remain held. The A0/A1 scientific/resource contracts and all earlier evidence
remain unchanged.

This capsule copies only source/reference files from the sealed A1 artifact. It
contains no query vectors, development evidence, database files or graph/module
binaries. It cannot submit a Slurm job, start a server, connect to a database,
execute SQL, call the snapshot producer/constructor, or run ANN/exact searches.

The image-only invocation imports its existing NumPy, Arrow, Psycopg and libpq,
reads the nine original driver hook definitions and uncached parser identity,
checks the original producer/constructor source/AST/line mapping without calling
them, and runs the two literal CPython monitoring selfchecks. It records all
reference differences without modifying the reference. Connections and child
processes are blocked during inspection; bindings are restored in `finally`.

The unchanged SIF is SHA256-verified before invocation. The capsule is mounted
read-only at `/inspect` with no data, retained-source, prepared-DB or output bind.
Host stdout/stderr capture stays outside the capsule in one fresh private results
directory. A durable binding prevents repeat invocation. The script writes no
image/package files. It does not use an allocation or inspect job cgroups.

Limits: one invocation; 15 CPU seconds, 30 interpreter wall seconds, 2 GiB virtual
address space, no core dump, 128 KiB JSON report, 128 source reads of at most
64 KiB each and at most 4 MiB total. An outer 60-second timeout plus a five-second
kill grace also bounds image startup. Package/image checksum time precedes that
runtime envelope. The small capsule is at most 16 MiB /256 files. This is an
image inventory, not the A0 startup acquisition or a resource-margin result.

`inventory_complete_reference_mismatch` is a successful inventory that **holds**
release. A matching inventory would still leave the allocation's proc/cgroup,
overhead, source/lifecycle/cleanup and full acquisition/replay gates pending.
Missing capabilities and incomplete reports also hold release. No fallback,
dependency upgrade, automatic rerun or native submission follows from inspection.

Exact upload, Torch invocation and download commands are in the generated
`COMMANDS.txt` beside the sealed capsule. The transfer helper authenticates before
copying, validates remote/local checksums and binding identity, and runs only
data-only local JSON verification on returned evidence.

Local checks execute tiny monitoring literals and inspect the original source
definitions against the installed local libraries. They run no native image,
database, experiment or search, and do not attest the actual SIF runtime.
