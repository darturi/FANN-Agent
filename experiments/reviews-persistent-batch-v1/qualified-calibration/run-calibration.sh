#!/bin/bash
set -euo pipefail
umask 077

stage=$(cd -- "$(dirname -- "$0")" && pwd -P)
cd "$stage"
job=${SLURM_JOB_ID:?Run inside a Slurm allocation}
node=${SLURMD_NODENAME:-${SLURM_JOB_NODELIST:?Missing Slurm node name}}
[[ "$job" =~ ^[1-9][0-9]*$ && "$node" =~ ^cs[0-9]+$ ]]
(
  set -o noclobber
  {
    printf 'job_id\t%s\nnode\t%s\nkernel\t%s\n' "$job" "$node" "$(uname -r)"
    awk -F: '
      /^$/ {exit}
      $1 ~ /^(vendor_id|cpu family|model|model name|stepping|microcode)[[:space:]]*$/ {
        sub(/[[:space:]]+$/, "", $1)
        sub(/^[[:space:]]+/, "", $2)
        print $1 "\t" $2
      }' /proc/cpuinfo
  } > "$stage/host-$job.tsv"
)
exec /bin/bash ./run-on-compute.sh
