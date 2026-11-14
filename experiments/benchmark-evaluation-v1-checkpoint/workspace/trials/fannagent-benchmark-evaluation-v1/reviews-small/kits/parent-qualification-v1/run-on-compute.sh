#!/bin/bash
set -euo pipefail
umask 077
stage=$(cd -- "$(dirname -- "$0")" && pwd -P)
cd "$stage"
sha256sum -c SHA256SUMS
job=${SLURM_JOB_ID:?Run inside a Slurm allocation}
[[ "$job" =~ ^[1-9][0-9]*$ ]]
run="$stage/run-$job"
mkdir -m 700 "$run"
mkdir -m 700 "$run/work" "$run/results"
finish() {
    status=$?
    trap - EXIT
    printf '{"exit_code":%d,"job_id":"%s"}\n' "$status" "$job" > "$run/results/host-exit.json"
    tar -czf "$run/qualification-$job.tar.gz" -C "$run" results
    (cd "$run" && sha256sum "qualification-$job.tar.gz" > "qualification-$job.tar.gz.sha256")
    printf 'Return: %s/qualification-%s.tar.gz\n' "$run" "$job"
    exit "$status"
}
trap finish EXIT
bundle=/home/dar579/torch-reviews-first
prepared=/scratch/dar579/torch-reviews/torch-reviews-size-sweep.ihFoep/prepared/size-247286
image="$bundle/images/runtime.sif"
printf '%s  %s\n' 7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a "$image" | sha256sum -c -
tar -xzf original-package.tar.gz -C "$run"
package="$run/reviews-persistent-batch-native-v1"
printf '%s  %s\n' b596c69bbab0bb49d720df02b820e5a9f2c1652a47e67b6b327f16f8769663bc "$package/manifest.json" | sha256sum -c -
/share/apps/apptainer/bin/apptainer exec --cleanenv --containall --no-home --pwd /run \
    --bind "$package:/patch:ro" --bind "$stage:/qual:ro" \
    --bind "$stage/vector.so:/opt/postgresql/lib/vector.so:ro" \
    --bind "$bundle:/bundle:ro" --bind "$prepared:/prepared:ro" \
    --bind "$run/work:/run:rw" --bind "$run/results:/results:rw" \
    --env PYTHONPATH=/patch:/qual:/opt/torch-reviews/vendor \
    --env PYTHONDONTWRITEBYTECODE=1 --env TMPDIR=/tmp \
    --env OPENBLAS_NUM_THREADS=1 --env OMP_NUM_THREADS=1 --env "SLURM_JOB_ID=$job" \
    "$image" python -B /qual/qualify.py --package /patch --bundle /bundle \
    --prepared /prepared --work /run --output /results
