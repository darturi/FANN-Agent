#!/bin/bash
set -euo pipefail
umask 077
stage=$(cd -- "$(dirname -- "$0")" && pwd -P)
cd "$stage"
sha256sum -c SHA256SUMS
[[ "${1:-}" = --check || "${1:-}" = --submit ]]
args=(--account=torch_pr_288_courant --partition=cs --job-name=reviews-full-oracle
      --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=48G --time=06:00:00
      --hint=nomultithread --no-requeue --chdir="$stage"
      --output="$stage/slurm-%j.out" --error="$stage/slurm-%j.err"
      --wrap='exec /opt/slurm/bin/srun --ntasks=1 --cpus-per-task=4 --hint=nomultithread --cpu-bind=cores --kill-on-bad-exit=1 /bin/bash ./run-on-compute.sh')
/opt/slurm/bin/sbatch --test-only "${args[@]}"
if [[ "$1" = --check ]]; then exit 0; fi
bash ./startup-preflight.sh
mkdir .submitted
job=$(/opt/slurm/bin/sbatch --parsable "${args[@]}")
job=${job%%;*}
[[ "$job" =~ ^[1-9][0-9]*$ ]]
printf '%s\n' "$job" > job-id
printf 'Submitted oracle diagnostic %s (one allocation, no automatic replacement)\n' "$job"
