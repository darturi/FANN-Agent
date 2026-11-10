# B2f launcher correction

October 27, 2026. `partial-calibration.v1.launch-fix` is an infrastructure revision
of the unchanged `partial-calibration.v1` scientific contract.

The verified original campaign is
`reviews-partial-calibration-v1-20261027T155119Z.6rd0lmkp`, job `21111616_0`.
Its six-file archive SHA256 is
`1385637e3657038dba52140fce58260dc74484bcb40847ace9a9714f372fb543`.
Slurm records FAILED/2:0. The task log records `execve(): python3: No such file
or directory`; no Python host-wrapper/runtime evidence exists. The calibration
program never started, so this attempt made zero native searches and supplies
no quality, A/A, timing, restoration or native-capability evidence. The allocation
was nevertheless spent. Preserve its package, archive, raw, binding and reservation.

The submitted batch script combined `sbatch --export=NONE` with bare `python3`
in an srun step. The immediate cause is the failed executable lookup; the
inherited restricted export is the identified launcher defect. We did not sample
the failed step's PATH, so its exact environment contents are not inferred.

The correction records the resolved absolute submitting interpreter in
submission.json, passes it as the eighth batch argument, checks that it exists
on the compute node, and invokes that exact executable. Both SLURM_EXPORT_ENV=ALL
and srun --export=ALL explicitly establish the step export behavior. The new
host-launch.json records interpreter/version/export identity for trusted local
verification. Native Python remains inside the identical pinned image with
unchanged --cleanenv and explicit runtime variables.

The new shell regression executes the actual batch script against a synthetic
srun with restricted inherited export and a PATH containing no python3. It
reproduces the original failure and verifies corrected execution, all argument
boundaries (including spaces), no-bytecode export, and rejection of relative,
missing or absent interpreter arguments. This is a local launcher correctness
check; it does not contact Slurm or prove compute-node compatibility.

The frozen design, contract, schedule, full acquisition/timer/scoring/analysis
code, native module, graphs, data, margins and all per-job ceilings remain
unchanged. Only infrastructure/version/provenance and verification support
change. The corrected package/campaign/reservation have separate names; both
old seal and failed raw/binding/reservation must verify before dispatch.

No automatic retry or allocation reset is introduced. The proposed corrected
handoff is **one additional** job, 3 hours/4 CPUs/32 GiB, at most16,242 searches.
This is separate from the spent four-second original attempt. The user requests
that new allocation by executing the explicitly labelled corrected submit
command. No native job is submitted by preparation or upload, and no further
repeat follows a failure. Original B2d stays measurement_inconclusive; original
execution retained, B1c deferred, no speed/adoption qualification.

Primary sources:

- [Slurm sbatch environment export](https://slurm.schedmd.com/sbatch.html#OPT_export):
  NONE requires absolute executable paths; the documentation recommends ALL for
  step export to avoid inheriting NONE.
- [Slurm srun executable resolution](https://slurm.schedmd.com/srun.html#SECTION_EXECUTABLE-PATH-RESOLUTION)
  and [step export](https://slurm.schedmd.com/srun.html#OPT_export):
  absolute paths and explicit export are supported at the step boundary.
