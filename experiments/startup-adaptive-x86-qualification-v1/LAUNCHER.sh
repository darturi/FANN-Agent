#!/usr/bin/env bash
#SBATCH --job-name=fann-a3-x86-qual
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --signal=B:USR1@120
set -euo pipefail
umask 077
test "$#" -eq 6
qx_python="$6"
case "$qx_python" in /*) ;; *) exit 2 ;; esac
test -x "$qx_python"
export PATH="${PATH:-/usr/bin:/bin}"
export SLURM_EXPORT_ENV=ALL PYTHONDONTWRITEBYTECODE=1
exec srun --export=ALL --ntasks=1 --cpus-per-task=4 --hint=nomultithread --cpu-bind=cores \
 --kill-on-bad-exit=1 "$qx_python" "$1/host.py" "$@"
