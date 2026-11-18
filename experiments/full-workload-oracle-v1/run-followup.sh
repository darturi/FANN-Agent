#!/bin/bash
set -euo pipefail
umask 077
stage=$(cd -- "$(dirname -- "$0")" && pwd -P)
cd "$stage"
sha256sum -c SHA256SUMS
job=${SLURM_JOB_ID:?Run inside Slurm}
run="$stage/run-$job"
mkdir -m700 "$run" "$run/results" "$run/work"
finish() {
    status=$?
    trap - EXIT
    printf '{"exit_code":%d,"job_id":"%s"}\n' "$status" "$job" > "$run/results/host-exit.json"
    tar -czf "$run/oracle-followup-$job.tar.gz" -C "$run" results
    (cd "$run" && sha256sum "oracle-followup-$job.tar.gz" > "oracle-followup-$job.tar.gz.sha256")
    exit "$status"
}
trap finish EXIT
bundle=/home/dar579/torch-reviews-first
prepared=/scratch/dar579/torch-reviews/torch-reviews-size-sweep.ihFoep/prepared/size-247286
source_results=/scratch/dar579/fannagent-benchmark-evaluation-v1/oracle-headroom-20261117-v1/full-workload-oracle-v1/run-23544718/results
image="$bundle/images/runtime.sif"
tar -xzf original-package.tar.gz -C "$run"
package="$run/reviews-persistent-batch-native-v1"
seconds=$(python3 -c 'import json;print(json.load(open("followup-plan.json"))["wall_limit_seconds"]-90)')
timeout --signal=TERM --kill-after=15s "${seconds}s" \
    /share/apps/apptainer/bin/apptainer exec --cleanenv --containall --no-home --pwd /run \
    --bind "$package:/patch:ro" --bind "$stage:/qual:ro" \
    --bind "$stage/oracle-module.so:/opt/postgresql/lib/vector.so:ro" \
    --bind "$source_results:/acquisition:ro" --bind "$bundle:/bundle:ro" --bind "$prepared:/prepared:ro" \
    --bind "$run/work:/run:rw" --bind "$run/results:/results:rw" \
    --env PYTHONPATH=/patch:/qual:/opt/torch-reviews/vendor --env PYTHONDONTWRITEBYTECODE=1 \
    --env TMPDIR=/tmp --env OPENBLAS_NUM_THREADS=1 --env OMP_NUM_THREADS=1 --env "SLURM_JOB_ID=$job" \
    "$image" python -B /qual/followup_run.py \
    --package /patch --bundle /bundle --prepared /prepared --work /run --output /results
