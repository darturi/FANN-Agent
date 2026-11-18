#!/bin/bash
set -euo pipefail
umask 077
stage=$(cd -- "$(dirname -- "$0")" && pwd -P)
cd "$stage"
sha256sum -c SHA256SUMS
[[ "${1:-}" = --check || "${1:-}" = --submit ]]
limit=$(python3 -c 'import json;p=json.load(open("followup-plan.json"));assert p["source_elapsed_seconds"]+p["wall_limit_seconds"]<=21600;print(p["wall_limit_seconds"]//60)')
args=(--account=torch_pr_288_courant --partition=cs --job-name=reviews-oracle-followup
      --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=48G --time="$limit"
      --hint=nomultithread --no-requeue --chdir="$stage"
      --output="$stage/slurm-%j.out" --error="$stage/slurm-%j.err"
      --wrap='exec /opt/slurm/bin/srun --ntasks=1 --cpus-per-task=4 --hint=nomultithread --cpu-bind=cores --kill-on-bad-exit=1 /bin/bash ./run-followup.sh')
/opt/slurm/bin/sbatch --test-only "${args[@]}"
[[ "$1" = --submit ]] || exit 0
bash startup-followup.sh
mkdir .submitted
job=$(/opt/slurm/bin/sbatch --parsable "${args[@]}")
job=${job%%;*}
[[ "$job" =~ ^[1-9][0-9]*$ ]]
printf '%s\n' "$job" > job-id
printf 'Submitted bounded oracle followup %s\n' "$job"
