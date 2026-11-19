#!/bin/bash
set -euo pipefail
umask 077
stage=$(cd -- "$(dirname -- "$0")" && pwd -P)
cd "$stage"
sha256sum -c SHA256SUMS
args=(--account=torch_pr_288_courant --partition=cs --job-name=reviews-live-v3
      --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=48G --time=06:00:00
      --hint=nomultithread --no-requeue --chdir="$stage"
      --output="$stage/slurm-%j.out" --error="$stage/slurm-%j.err"
      --wrap='exec /usr/bin/timeout --signal=TERM --kill-after=15s 21540s /bin/bash ./job.sh')
if [ "${1:---check}" = --check ]; then
    /opt/slurm/bin/sbatch --test-only "${args[@]}"
    exit
fi
if [ "$#" -ne 1 ] || [ "$1" != --submit ]; then
    echo 'Use --check (no allocation) or --submit (one six-hour allocation).' >&2
    exit 2
fi
test -x /usr/bin/timeout
test -x /share/apps/apptainer/bin/apptainer
python3 -c 'import sys; assert sys.version_info >= (3, 9), "Host Python 3.9+ required"'
# Keep this marker even when submission returns an uncertain error. Never auto-resubmit.
mkdir .submitted
/opt/slurm/bin/sbatch --parsable "${args[@]}" > .submitted/sbatch-response.txt
job=$(cat .submitted/sbatch-response.txt)
job=${job%%;*}
[[ "$job" =~ ^[1-9][0-9]*$ ]]
printf '%s\n' "$job" > job-id
printf 'Submitted job %s; six-hour allocation, no automatic replacement.\n' "$job"

