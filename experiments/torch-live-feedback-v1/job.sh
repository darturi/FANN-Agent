#!/bin/bash
set -euo pipefail
umask 077
stage=$(cd -- "$(dirname -- "$0")" && pwd -P)
cd "$stage"
job=${SLURM_JOB_ID:?Run through submit.sh inside Slurm}
[[ "$job" =~ ^[1-9][0-9]*$ ]]
test "${SLURM_RESTART_COUNT:-0}" = 0
test ! -e "run-$job"
sha256sum -c SHA256SUMS
finish() {
    status=$?
    trap - EXIT
    if [ -d "run-$job" ]; then
        printf '{"job_id":"%s","exit_code":%d}\n' "$job" "$status" > "run-$job/host-exit.json"
        # Raw records are already durable on scratch. Exclude private databases and build trees.
        tar --exclude='*/work' --exclude='*/engine' --exclude='*/original' \
            -czf "return-$job.tar.gz" "run-$job"
        sha256sum "return-$job.tar.gz" > "return-$job.tar.gz.sha256"
    fi
    exit "$status"
}
trap finish EXIT
# Includes waiting, hashing, builds and all container children. Does not depend on a client heartbeat.
/usr/bin/timeout --signal=TERM --kill-after=15s 21300s \
    /opt/slurm/bin/srun --ntasks=1 --cpus-per-task=4 --hint=nomultithread \
    --cpu-bind=cores --kill-on-bad-exit=1 python3 -B worker.py --stage "$stage"

