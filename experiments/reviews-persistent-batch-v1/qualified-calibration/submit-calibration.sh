#!/bin/bash
set -euo pipefail
umask 077

stage=$(cd -- "$(dirname -- "$0")" && pwd -P)
cd "$stage"
sha256sum -c SHA256SUMS
test -r /home/dar579/torch-reviews-first/images/runtime.sif
test -r /scratch/dar579/torch-reviews/torch-reviews-size-sweep.ihFoep/prepared/size-247286/base/backup_manifest

/opt/slurm/bin/scontrol -o show node > nodes-before.txt
python3 ./choose_nodes.py nodes-before.txt > planned-nodes.txt
nodes=()
while IFS= read -r node; do nodes+=("$node"); done < planned-nodes.txt
[[ "${#nodes[@]}" == 3 ]]
printf 'Planned nodes %s %s %s\n' "${nodes[@]}"
args=(
  --account=torch_pr_288_courant --partition=cs
  --job-name=votes108-cal --nodes=1 --ntasks=1
  --cpus-per-task=4 --mem=32G --time=02:00:00
  --hint=nomultithread --no-requeue --chdir="$stage"
  --output="$stage/slurm-%j.out" --error="$stage/slurm-%j.err"
  --wrap='exec /opt/slurm/bin/srun --ntasks=1 --cpus-per-task=4 --hint=nomultithread --cpu-bind=cores --kill-on-bad-exit=1 /bin/bash ./run-calibration.sh'
)
for node in "${nodes[@]}"; do
  /opt/slurm/bin/sbatch --test-only "${args[@]}" --nodelist="$node"
done

reservation=/home/dar579/torch-reviews-results/.votes108-timing-calibration-22563225
if ! (set -o noclobber; printf '%s\n' "$stage" > "$reservation"); then
  printf 'Calibration already reserved or cannot be reserved: %s\n' "$reservation" >&2
  exit 1
fi
touch jobs.tsv
previous=
for node in "${nodes[@]}"; do
  deps=(--nodelist="$node")
  if [[ -n "$previous" ]]; then
    deps+=(--dependency="afterany:$previous")
  fi
  job=$(/opt/slurm/bin/sbatch --parsable "${args[@]}" "${deps[@]}")
  job=${job%%;*}
  [[ "$job" =~ ^[1-9][0-9]*$ ]]
  printf '%s\t%s\n' "$job" "$node" >> jobs.tsv
  printf 'Submitted job %s on %s\n' "$job" "$node"
  previous=$job
done
jobs=$(cut -f1 jobs.tsv | paste -sd ',' -)
printf 'Stage %s\n' "$stage"
printf 'Status: /opt/slurm/bin/sacct --local -j %s -o JobIDRaw,State,ExitCode,Elapsed,NodeList\n' "$jobs"
printf 'After all three complete: /bin/bash %s/collect-calibration.sh\n' "$stage"
