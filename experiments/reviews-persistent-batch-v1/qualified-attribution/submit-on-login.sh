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
  --job-name=votes108-attribution --nodelist=cs604 --nodes=1 --ntasks=1
  --cpus-per-task=4 --mem=32G --time=00:30:00
  --hint=nomultithread --no-requeue --chdir="$stage"
  --output="$stage/slurm-%j.out" --error="$stage/slurm-%j.err"
  --wrap='exec /opt/slurm/bin/srun --ntasks=1 --cpus-per-task=4 --hint=nomultithread --cpu-bind=cores --kill-on-bad-exit=1 /bin/bash ./run-calibration.sh'
)
/opt/slurm/bin/sbatch --test-only "${args[@]}"

ledger=/home/dar579/torch-reviews-results/.votes108-attribution-22582763
if ! (set -o noclobber; printf '%s\n' "$stage" > "$ledger"); then
  printf 'Attribution test already reserved or cannot be reserved: %s\n' "$ledger" >&2
  exit 1
fi
job=$(/opt/slurm/bin/sbatch --parsable "${args[@]}")
job=${job%%;*}
[[ "$job" =~ ^[1-9][0-9]*$ ]]
printf '%s\n' "$job" > job-id
archive="votes108-attribution-${job}.tar.gz"
printf 'Job %s\nStage %s\n' "$job" "$stage"
printf 'Status: /opt/slurm/bin/sacct --local -j %s -o JobIDRaw,State,ExitCode,Elapsed,NodeList\n' "$job"
printf 'After COMPLETED 0:0, run these separately in local SFTP:\n'
printf 'get %s/run-%s/%s /private/tmp/%s\n' "$stage" "$job" "$archive" "$archive"
printf 'get %s/run-%s/%s.sha256 /private/tmp/%s.sha256\n' "$stage" "$job" "$archive" "$archive"
