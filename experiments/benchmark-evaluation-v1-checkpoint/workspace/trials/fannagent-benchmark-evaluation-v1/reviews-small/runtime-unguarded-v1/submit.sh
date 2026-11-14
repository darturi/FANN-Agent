#!/bin/bash
set -euo pipefail
umask 077
stage=$(cd -- "$(dirname -- "$0")" && pwd -P)
cd "$stage"
sha256sum -c SHA256SUMS
test -x /share/apps/apptainer/bin/apptainer
test -r /home/dar579/torch-reviews-first/images/runtime.sif
test -r /scratch/dar579/torch-reviews/torch-reviews-size-sweep.ihFoep/prepared/size-247286/base/backup_manifest
args=(--account=torch_pr_288_courant --partition=cs --job-name=reviews-raw-qual
      --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=48G --time=08:00:00
      --hint=nomultithread --no-requeue --chdir="$stage"
      --output="$stage/slurm-%j.out" --error="$stage/slurm-%j.err"
      --wrap='exec /opt/slurm/bin/srun --ntasks=1 --cpus-per-task=4 --hint=nomultithread --cpu-bind=cores --kill-on-bad-exit=1 /bin/bash ./run-on-compute.sh')
/opt/slurm/bin/sbatch --test-only "${args[@]}"
mkdir .submitted
job=$(/opt/slurm/bin/sbatch --parsable "${args[@]}")
job=${job%%;*}
[[ "$job" =~ ^[1-9][0-9]*$ ]]
printf '%s\n' "$job" > job-id
printf 'Submitted development-only qualification job %s\n' "$job"
printf 'Status: /opt/slurm/bin/sacct --local -j %s -o JobIDRaw,State,ExitCode,Elapsed,MaxRSS\n' "$job"
printf 'Progress: tail -n 10 %s/slurm-%s.out\n' "$stage" "$job"
printf 'Return: %s/run-%s/qualification-%s.tar.gz\n' "$stage" "$job" "$job"
