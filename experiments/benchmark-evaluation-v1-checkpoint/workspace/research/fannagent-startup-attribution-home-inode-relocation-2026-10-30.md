# Main A2 home file quota: confirmed shortage and preserving relocation

October 30, 2026, America/New_York. Roadmap D106 / v1.57.

The user's read-only Torch report at 16:40:19 confirms home usage 20,108 files under
the displayed 30k quota. The unchanged parser conservatively treats that limit as
29,000, leaving **8,892 available files: 1,108 below the frozen 10,000 requirement**.
Conservative byte headroom and filesystem bytes/inodes pass. Both main submission
binding and reservation report ABSENT. The previous main attempt stopped before
creating either state file or reaching Slurm; the main allowance remains unspent.
The authentication/device-code transcript is not retained.

## Scope and preservation decision

The main protected-source chain was audited through pc_common, legacy_common,
frozen protected/legacy_protected/prior_protected/preservation and the sealed main
configuration. It reads named historical package/result subtrees and does not
require the three failed C2 compatibility directory trees. Original bundle,
retained database source, all raw results/reservations, passed C2B and current main
package stay in place.

[RELOCATION-FREEZE.json](../trials/torch-reviews-startup-attribution-v1-image-reference/home-quota-relocation-2026-10-30/RELOCATION-FREEZE.json)
precedes the helper. Relocate exactly the package trees belonging to spent failed
jobs 21348020, 21367064 and 21382454 into the current validated `$ARCHIVE` under
`fannagent-a2-spent-compatibility-20261030`. Keep their original home paths as
symlinks. All files and binding contents, permissions, owners/groups and mtimes
are preserved and hash-verified. Their native raw/result/reservation records and
all four spent-allowance decisions remain unchanged.

The reported directory counts 787+790+790 imply an estimated reduction of 2,364 home
inodes after three replacement symlinks, giving about 11,256 conservative available
files before the small helper-upload cost. This is a projection, not a post-move
measurement. Actual archive quota/filesystem capacity and final home headroom must
pass in the helper. No quota threshold, scientific/main limit, code or package
change is made.

## Helper behavior and local qualification

The standalone helper verifies the exact main manifest and parser, absent main
binding/reservation, expected terminal FAILED job records and old submission/
reservation/binding identities. It pins each old capsule's manifest and complete
file inventory; links/devices/unknown content or ownership stop before commit.

It copies each complete tree to private archive staging, verifies full bytes and
metadata, rechecks the source, then commits the archive. An atomic rename keeps an
owned home quarantine until the original path's archive symlink exists. Only the
already verified duplicate in that quarantine is removed, after another archive
and quarantine check. Full preservation records, copy/relocation receipts and a
fresh quota report stay in archive. Partial/unowned copies are preserved for
inspection. Alias failure restores the original; interrupted duplicate cleanup
can resume against the verified full archive. No main job is submitted by the
helper. A fresh bound/reserved main state stops further relocation.

All **21 local tests** pass on tiny owned fixtures, including a mocked complete
Torch command, byte/mode/mtime/binding preservation, idempotence, source/archive
tampering, source/target/extra-file/link rejection, rollback, interrupted rename,
partial-cleanup recovery, main-state races and bad archive quota. AST/Ruff and
transfer/command shell checks pass. These are local filesystem checks; no actual
remote relocation has occurred in this review.

[Release verification](../trials/torch-reviews-startup-attribution-v1-image-reference/home-quota-relocation-2026-10-30/release-verification.json)
binds helper SHA-256 `bc2709837664777662a665adce0a9b4293e4de73eb3ab6c426e7d489bf13afc5`. The original main 619-file seal,
620-member archive and all 68 recipes remain unchanged. All 128+128 qualified native
cases, the final main 128 local cases, strict references/verification and original
1h/4CPU/32GiB zero-search acquisition stay intact.

## Current handoff

[COMMANDS.txt](../trials/torch-reviews-startup-attribution-v1-image-reference/home-quota-relocation-2026-10-30/COMMANDS.txt)
provides Mac helper-only upload with checksum, then Torch verified relocation and
fresh home headroom check. Only successful helper exit allows the shell to invoke
the existing main controller's original submit command, which repeats its full
frozen preflight before reservation/dispatch. No reupload/extraction of the main
package, extra compute entitlement or compatibility resubmission is involved.
Then use the unchanged main status/terminal collection/Mac download commands.

Main A2 remains unlaunched. After actual dispatch its allowance is spent, including
failure; no automatic retry. Collect/download and independently verify its full
capability/identity/coverage/overhead/resource/lifecycle/restoration/cleanup/locks/
trusted replay before A2 closure/A3. Full B2f remains held.

To restore a physical old package directory later, first establish enough home
headroom, copy the verified archived tree to a fresh sibling, verify its stored
fingerprint/metadata, and atomically replace the alias. Preserve the archived
copy and its preservation records. This relocation never authorizes rerunning a
spent compatibility job.

## Mac transfer correction, D107 / v1.58

The first helper upload stopped before SCP because macOS's long temporary
directory plus OpenSSH's control-socket suffix exceeded its Unix socket path
limit. The helper upload and later main result transfer now create private
0700 directories directly under `/private/tmp`, independent of `TMPDIR`.
Their transfer, authentication and verification commands are unchanged.

Offline long-TMPDIR checks cover both upload paths, success, authentication
failure before SCP, suffix length and cleanup. Actual short socket binding is
prohibited by the local execution sandbox, so native SSH remains to be retried
by the user. No remote connection or movement occurred in this correction.
The relocation payload, main source/sealed recipes and archive retain their
previous hashes. Previous release receipts and failed helper bytes are preserved.
See the [correction receipt](../trials/torch-reviews-startup-attribution-v1-image-reference/home-quota-relocation-2026-10-30/socket-path-fix-2026-10-30/verification.json).

Rerun the same Mac upload command from `COMMANDS.txt`, then its Torch continuation
only after `UPLOAD VERIFIED`. Main A2 remains unlaunched.
