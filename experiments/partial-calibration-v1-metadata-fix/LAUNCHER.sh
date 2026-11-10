#!/usr/bin/env bash
#SBATCH --job-name=fann-partial-cal-meta-fix
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=03:00:00
#SBATCH --signal=B:USR1@120
set -euo pipefail
umask 077
if test "$#" -ne 8; then
  printf '%s\n' 'Launcher requires seven job arguments and the absolute host Python path.' >&2
  exit 2
fi
pc_host_python="$8"
case "$pc_host_python" in
  /*) ;;
  *) printf '%s\n' 'Host Python path must be absolute; no PATH fallback.' >&2; exit 2 ;;
esac
if ! test -f "$pc_host_python" || ! test -x "$pc_host_python"; then
  printf 'Host Python unavailable on compute node: %s\n' "$pc_host_python" >&2
  exit 2
fi
export PATH="${PATH:-/usr/bin:/bin}"
export PYTHONDONTWRITEBYTECODE=1
export SLURM_EXPORT_ENV=ALL
printf 'B2f launch-fix: absolute host Python=%s; srun export=ALL\n' "$pc_host_python"
exec srun --export=ALL --ntasks=1 --cpus-per-task=4 --hint=nomultithread --cpu-bind=cores \
  --kill-on-bad-exit=1 "$pc_host_python" "$1/pc_job.py" "$@"
