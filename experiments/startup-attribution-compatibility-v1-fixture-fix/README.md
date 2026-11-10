# Native A2 compatibility: fixture dependency correction

This isolated capsule corrects failed compatibility job21348020. Its source suite
reported a ReplayTests setup error, continued into signal fixtures and hit the
300-second source deadline. The sealed suite and main A2 never launched.

Retained runtime diagnostics identify a missing offline constructor input:
`inputs/local-identity.json`. The old capsule copied only runner.py/manifest.json;
the Mac tests could read the omitted file from the ambient workspace. This capsule
carries all three exact, hash-pinned files. A positive regression calls the actual
frozen constructor through the packaged bundle path; a negative regression
reproduces FileNotFoundError without the metadata. The original runner only consumes
settings and binding metadata from that historical identity record; it obtains the
native index identity from the private synthetic work record.

Only offline runtime_fixture copies are optimized. Each ephemeral synthetic seed is
fingerprinted, immutable fixture files are hardlinked within temporary scratch, and
manifest/config/query/eligibility files receive separate copies. Seed bytes must
match after each fixture, including failures. Symlinks and native seeds reject;
link failures reject without a silent copy fallback. Production restoration,
reader/snapshot operations and the original main source recipe remain unchanged.

The child reports tracebacks immediately, stops on first test error/failure and
writes per-test events. Bounded periodic stack traces help diagnose timeouts.
The guard receipt is published on unexpected Python errors, and the host records
final capsule/image integrity separately from the primary failure.

Limits remain one15-minute allocation, two physical CPUs,4GiB. Source and sealed
suites retain300 seconds each, candidate build90 seconds, guest720 seconds, and
host startup/cleanup reserves. There are128 actual original-source checks in each
native suite. All transports/proc/resource inputs are synthetic. There are no real
DB connections, SQL, PostgreSQL servers, ANN/exact searches, providers or fits.

The old package, binding, reservation and failed raw are preserved. This correction
has a distinct name/reservation and one separately declared bounded allowance.
There is no retry of either reservation, automatic relaunch or main A2 launch.
A complete native source/sealed pass with exact recipe/provenance, restored guards,
seed integrity, locked raw and host final integrity is still required before C3
can prepare the main A2 production seal. Local checks do not establish native
runtime success or production resource qualification.

Run commands are generated into the output COMMANDS.txt after local readiness and
sealing. Upload/download run on the Mac; submit/status/terminal collect run on Torch.
