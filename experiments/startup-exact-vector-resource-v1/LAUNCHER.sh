#!/usr/bin/env bash
#SBATCH --job-name=fann-startup-exact-vector-v1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --signal=B:USR1@120
set -euo pipefail
umask 077
if test "$#" -ne 8; then
  printf '%s\n' 'Launcher requires seven job arguments and absolute host Python.' >&2
  exit 2
fi
sr_host_python="$8"
case "$sr_host_python" in
  /*) ;;
  *) printf '%s\n' 'Absolute host Python required; no PATH fallback.' >&2; exit 2 ;;
esac
if ! test -f "$sr_host_python" || ! test -x "$sr_host_python"; then
  printf 'Host Python unavailable: %s\n' "$sr_host_python" >&2
  exit 2
fi
export PATH="${PATH:-/usr/bin:/bin}"
export PYTHONDONTWRITEBYTECODE=1
export SLURM_EXPORT_ENV=ALL
printf 'A3 exact-vector startup-memory qualification: zero searches; Python=%s\n' "$sr_host_python"
exec srun --export=ALL --ntasks=1 --cpus-per-task=4 --hint=nomultithread --cpu-bind=cores \
  --kill-on-bad-exit=1 "$sr_host_python" "$1/pc_job.py" "$@"
