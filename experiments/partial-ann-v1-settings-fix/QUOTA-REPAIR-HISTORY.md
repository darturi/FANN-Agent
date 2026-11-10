Historical quota-repair snapshot; current settings correction uses a separate
reservation as specified in SETTINGS-CORRECTION.md and README.md.

# B2d quota display compatibility repair — October 26, 2026

This is a separate packaging revision of partial-ann.v1, not another campaign allowance.
Original package manifest: f11159e1b66d9e9cb0259bec45e136eac9bff7a322233a9ac00a4153267c09a4.
Original archive: b2f7730a24a98ea2a3d29474298064a2500eab8e61911c83130bf705bc97755c.
Captured user submission transcript SHA256: 5a7bab648812345d643064067e1c764e9497c320b92ab82cce31edac76285fed.
Captured readable myquota stdout SHA256: 8550beed2d611ee94a37b2acc59f68576719a89beb85bf9aa5a7cfaa4f27f5c9.

The user's submission stops in resource preflight, before sbatch --test-only,
reservation, binding or actual dispatch. The pasted table reports home 50GB/30k
and scratch 5.00TB/5.00M. The original parser lacks lower-case k. Replaying the
literal pasted table raises Unrecognized quota unit:30k. The remote trace instead
reports unmatched rows; original terminal-control bytes are unavailable in the
paste, so the exact raw row-match difference is unproven. The repair additionally
accepts standard ANSI SGR colour wrappers; other malformed rows still fail closed.

Only file-count unit aliases k/K, m/M, g/G and terminal colour handling change in
the resource guard. Decimal/binary storage interpretation, conservative rounding,
free-space checks, scratch/home requirements, deadlines and search ceilings stay
unchanged. Captured conservative available home space is 26,988,400,000 bytes and
15,013 file slots; scratch 4,784,590,000,000 bytes and 4,850,576 file slots.
These are parser bounds on the pasted snapshot, not a current quota guarantee.
The actual prepared footprint and current quota/statvfs are checked again at
submission and on the compute host.

The packaging alias is torch-partial-ann-v1-quota-fix. The experiment name/version,
campaign prefix, scientific config, inputs, schedules, runtime, data/graph/module,
policies, quality/A/A/economic gates and one-allocation budget remain original.
The controller retains the shared .torch-partial-ann-v1-reservation.json name;
current commands also require the old package to have no submission binding.
Never delete that reservation or any original package. No new allocation is
created by this repair; exactly one user-run allocation remains proposed if no
prior reservation/dispatch exists. No native/index experiment is run locally.

The new source tests retain the original 55 checks and add six captured-format,
case/colour, malformed-output, preflight and insufficient-quota regressions.
Use only the new trial's COMMANDS.txt and transfer.sh for upload/status/collection
and trusted local replay. Preserve the original failed preflight as evidence.
