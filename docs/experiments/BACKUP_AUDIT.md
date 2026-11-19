# Experiment archive backup audit

Local archive integrity refreshed November 19, 2026, America/New_York, alongside
the experiment index and run catalog. **No independent backup was verified by
this refresh.** The destination, remote and cloud checks below were performed
October 21 and were not repeated; their results are historical observations,
not current destination status. Hashing created no independent backup and changed
no backup configuration. Experiment packaging and transfers are recorded separately
in the [experiment log](README.md).

## Verified local holdings

[archive-manifest.json](archive-manifest.json) now lists 454 archives, totaling
23,516,496,150 bytes, under the inventory's expanded, pruned workspace roots. These include
source/runtime/engineering archives as well as experiment results. Every file
was streamed through SHA-256 on November 19. All 192 archives with usable existing
checksum sidecars match; none mismatched. The remaining 262 have inventory hashes but no
usable sidecar for an independent earlier comparison. A checksum on the same
disk protects identity checking, not recovery after disk loss.

The historical October 21 full timing archive remains present with manifest hash
`f205d2c2b7a234539e3d3f0431de50c51a517d303bafc72650f4f706c2ed8ebe`.
The October 21 audit also checked five independent-analysis files against the
[postrun verification](../verification/frozen-proposals-timing-v1-runtime-fix-postrun.json).

The refreshed manifest retains the eight downloaded benchmark returns through
M1 job 23376796 and the sealed, unexecuted M5 kit. The kit matches its frozen
SHA-256 `3c4a0bd267d743e7abff9790beff7a7af510bc350cf079dda1c45d24e984b3b1`.
It also includes count-preserving oracle returns 23544718 / 23558871 / 23567950,
three-level oracle returns 23604734 / 23610319, and broad-language oracle returns
23644126 / 23716630 / 23719580, with their source and runtime packages. Failed
returns remain included. The cancelled broad job 23648495 has saved accounting
and remote-path metadata rather than a completed local measurement archive.
These are local integrity checks of collected artifacts; remote retention was
not rechecked during this documentation task.
The later v3 agent snapshot includes the verified idle-stopped return for job
23741092 and its prepared continuation kit. No learned-policy result exists for
that job; the sealed continuation is pending approval. The archive identity check
does not back up the model transcript, mutable fitting workspace or raw return to
an independent destination.
Archive integrity does not establish a successful experiment, destination
retention, or a restore test. See the [current index](README.md) for outcomes.

## Historical backup checks and evidence — October 21

| Destination / mechanism | Read-only check | Observed result | Meaning |
|---|---|---|---|
| Time Machine destination | `tmutil destinationinfo` | `No destinations configured.` | No configured Time Machine destination was found. |
| Local Time Machine snapshots | `tmutil listlocalsnapshots /` | Header only; no snapshot entries. | No local Time Machine snapshot was enumerated. Local snapshots would still share the physical disk. |
| Time Machine exclusion | `tmutil isexcluded /Users/danielarturi/Developer/JinyangLiWork/trials` | `[Included]` | The directory is eligible; this does not mean it has been backed up. |
| Mounted volumes | `/Volumes` inventory | Only `Macintosh HD`. | No mounted external backup destination observed. |
| Torch home results | SSH with `BatchMode=yes`, zero password prompts, strict host checking; attempted read-only archive listing | `Permission denied (gssapi-keyex,gssapi-with-mic,password,keyboard-interactive).` | Current remote archive existence and hashes remain unverified; interactive NYU authentication is needed. No trust/auth settings were changed. |
| Google Drive, both connected personal and school accounts | Drive metadata search for `torch-reviews`, `reviews-frozen`, or exact folder name `JinyangLiWork` | No matching items returned. | No backup located by these searches. This is not a proof that no other cloud copy exists. |
| Google Drive desktop | CloudStorage directory inventory | Google Drive mount exists; the workspace is under `~/Developer/`. | Installation/mount presence does not demonstrate synchronization of these archives. |
| GitHub source repository | `git ls-remote origin HEAD refs/heads/main refs/heads/feat/measured-policy-feedback` | HEAD/main: `4d1b896662659400956090ca25e9ead3faebaeb0`; feature branch not returned. | Remote main is the October 13 source state, older than the latest results/docs. No push was performed as part of this documentation task. |

The workspace root and `trials/` are outside the `agent` Git repository. Committing
the index, verification receipts and documentation does not include the raw
archives. The current documentation commit is local until explicitly pushed.
The saved `backup_source.py` scripts and database backup references preserve
experimental source databases; their names do not establish a backup of all
experiment archives.

## Historical backup gaps to recheck

These October 21 findings remain recorded for follow-up. The November 19
documentation refresh does not recertify remote availability or backup coverage.

- **Dispatch-overhead full results:** only
  `reviews-dispatch-overhead-20261020T152408Z.rhheoeyj-feedback.tar.gz` is local.
  Its [verification record](../../../trials/torch-reviews-results/reviews-dispatch-overhead-20261020T152408Z.rhheoeyj-analysis/verification.json)
  explicitly limits the audit to feedback/summary consistency because raw
  measurements are unavailable locally. Retrieve the full campaign archive and
  checksum after authenticating to Torch; preserve the current feedback archive.
- **Failed frozen-timing cohorts:** the two failed campaigns and their cancelled
  arrays are recorded in [runtime-repair.json](../../../trials/torch-reviews-frozen-proposals-timing-v1-runtime-fix/runtime-repair.json).
  That receipt states the evidence came from pasted status output; the remote
  raw failure artifacts were not downloaded. Their retention is unverified.
- **Older Torch launch failures:** local structured receipts preserve job IDs,
  failure causes and partial accounting. A complete local raw archive was not
  discovered for each failed campaign.
- **Local-only early trials and analyses:** no independently verified backup was
  found for the Movies/local Reviews histories, agent SQLite journals, corrected
  analyses, candidate stores, package dependencies or database/index assets.
  Some are not represented by a standalone result tarball.
- **Reconstruction dependencies:** the prepared Torch database/index, Apptainer
  image, qualified native module and pinned local runtimes must also be preserved
  to support full reruns; result archives cannot replace them.

## How to complete backup verification

After normal NYU authentication, enumerate the historical
`/home/dar579/torch-reviews-results/` archives and compare remote SHA-256 values
with the committed manifest. Record destination, object/path, size, hash and
verification timestamp for each match. Home and scratch paths should be checked
separately; an old download receipt is not a current retention check.

For durable recovery, copy the raw archives, early run directories/journals,
analysis scripts/results, source packages and required runtime/data assets to an
independent destination with a known retention policy. Verify the destination
bytes against this manifest and perform a restore check into a fresh directory.
Keep credentials and private configuration out of documentation and public Git.
Update this audit with the observed result. Creating or configuring that backup
is outstanding work; this task only checked existing coverage.
