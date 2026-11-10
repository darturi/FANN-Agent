#!/usr/bin/env bash
#SBATCH --job-name=fann-a2-prepared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --signal=B:USR1@60
set -euo pipefail
umask 077
test "$#" -eq 6
cc_python="$6"
case "$cc_python" in /*) ;; *) exit 2 ;; esac
test -x "$cc_python"
export PATH="${PATH:-/usr/bin:/bin}"
export SLURM_EXPORT_ENV=ALL PYTHONDONTWRITEBYTECODE=1
exec srun --export=ALL --ntasks=1 --cpus-per-task=2 --hint=nomultithread --cpu-bind=cores \
  --kill-on-bad-exit=1 "$cc_python" "$1/host.py" "$@"
