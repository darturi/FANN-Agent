#!/bin/bash
set -euo pipefail
umask 077

stage=$(cd -- "$(dirname -- "$0")" && pwd -P)
cd "$stage"
sha256sum -c SHA256SUMS
test -r /home/dar579/torch-reviews-first/images/runtime.sif
test -r /scratch/dar579/torch-reviews/torch-reviews-size-sweep.ihFoep/prepared/size-247286/base/backup_manifest
args=(
  --account=torch_pr_288_courant --partition=cs
  --job-name=votes108-shared --nodes=1 --ntasks=1
  --cpus-per-task=4 --mem=32G --time=02:00:00
  --hint=nomultithread --no-requeue --chdir="$stage"
  --output="$stage/slurm-%j.out" --error="$stage/slurm-%j.err"
  --wrap='exec /opt/slurm/bin/srun --ntasks=1 --cpus-per-task=4 --hint=nomultithread --cpu-bind=cores --kill-on-bad-exit=1 /bin/bash ./run-on-compute.sh'
)
/opt/slurm/bin/sbatch --test-only "${args[@]}"

ledger=/home/dar579/torch-reviews-results
test -d "$ledger"
reservation="$ledger/.votes108-shared-rerun-22560903.json"
if ! (set -o noclobber; printf '{"status":"reserved_before_dispatch","campaign":"%s","prior_job":"22560903"}\n' "$stage" > "$reservation"); then
  printf 'Shared rerun reservation already exists or cannot be written: %s\n' "$reservation" >&2
  exit 1
fi
job=$(/opt/slurm/bin/sbatch --parsable "${args[@]}")
job=${job%%;*}
[[ "$job" =~ ^[1-9][0-9]*$ ]]
printf '%s\n' "$job" > "$stage/job-id"
archive="votes108-shared-${job}.tar.gz"
printf 'Job %s\nStage %s\n' "$job" "$stage"
printf 'Status: /opt/slurm/bin/sacct --local -j %s -o JobIDRaw,State,ExitCode,Elapsed\n' "$job"
printf 'After COMPLETED 0:0, paste into local SFTP:\n'
printf 'get %s/run-%s/%s /private/tmp/%s\n' "$stage" "$job" "$archive" "$archive"
printf 'get %s/run-%s/%s.sha256 /private/tmp/%s.sha256\n' "$stage" "$job" "$archive" "$archive"
