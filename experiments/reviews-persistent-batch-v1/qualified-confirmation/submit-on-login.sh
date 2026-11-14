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
  --job-name=votes108-confirm --nodes=1 --ntasks=1
  --cpus-per-task=4 --mem=32G --time=02:00:00
  --hint=nomultithread --no-requeue --chdir="$stage"
  --output="$stage/slurm-%j.out" --error="$stage/slurm-%j.err"
  --wrap='exec /opt/slurm/bin/srun --ntasks=1 --cpus-per-task=4 --hint=nomultithread --cpu-bind=cores --kill-on-bad-exit=1 /bin/bash ./run-on-compute.sh'
)
/opt/slurm/bin/sbatch --test-only "${args[@]}"

source_sha=278f37e328586c5e3237e3003026664d950da82b29f7926f18b73c9033c2bd6d
ledger=/home/dar579/torch-reviews-results
test -d "$ledger"
reservation="$ledger/.selective-confirmation-$source_sha.json"
if ! (set -o noclobber; printf '{"status":"consumed_before_dispatch","campaign":"%s","candidate":"votes108-frontier-fold0-round3"}\n' "$stage" > "$reservation"); then
  printf 'Confirmation reservation already exists or cannot be written: %s\n' "$reservation" >&2
  exit 1
fi
job=$(/opt/slurm/bin/sbatch --parsable "${args[@]}")
job=${job%%;*}
[[ "$job" =~ ^[1-9][0-9]*$ ]]
printf '%s\n' "$job" > "$stage/job-id"
archive="votes108-confirmation-${job}.tar.gz"
printf 'Job %s\nStage %s\n' "$job" "$stage"
printf 'Status: /opt/slurm/bin/sacct --local -j %s -o JobIDRaw,State,ExitCode,Elapsed\n' "$job"
printf 'After COMPLETED 0:0, paste into local SFTP:\n'
printf 'get %s/run-%s/%s /private/tmp/%s\n' "$stage" "$job" "$archive" "$archive"
printf 'get %s/run-%s/%s.sha256 /private/tmp/%s.sha256\n' "$stage" "$job" "$archive" "$archive"
