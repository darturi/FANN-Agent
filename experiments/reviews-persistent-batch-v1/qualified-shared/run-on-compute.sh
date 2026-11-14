#!/bin/bash
set -euo pipefail
umask 077

stage=$(cd -- "$(dirname -- "$0")" && pwd -P)
cd "$stage"
sha256sum -c SHA256SUMS
job=${SLURM_JOB_ID:?Run inside a Slurm allocation}
[[ "$job" =~ ^[1-9][0-9]*$ ]]
run="$stage/run-$job"
mkdir -m 700 -- "$run"
mkdir -m 700 -- "$run/work" "$run/results"
tar -xzf "$stage/original-package.tar.gz" -C "$run"
package="$run/reviews-persistent-batch-native-v1"
bundle=/home/dar579/torch-reviews-first
prepared=/scratch/dar579/torch-reviews/torch-reviews-size-sweep.ihFoep/prepared/size-247286
image="$bundle/images/runtime.sif"
image_sha=7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a
package_sha=b596c69bbab0bb49d720df02b820e5a9f2c1652a47e67b6b327f16f8769663bc
printf '%s  %s\n' "$image_sha" "$image" "$package_sha" "$package/manifest.json" | sha256sum -c -
read -r module_sha _ < <(sha256sum "$stage/vector.so")
read -r parity_sha _ < <(sha256sum "$stage/confirmation/qualification.jsonl")

/share/apps/apptainer/bin/apptainer exec --cleanenv --containall --no-home --pwd /run \
    --bind "$package:/patch:ro" \
    --bind "$stage/confirmation:/confirm:ro" \
    --bind "$stage/vector.so:/opt/postgresql/lib/vector.so:ro" \
    --bind "$bundle:/bundle:ro" \
    --bind "$prepared:/prepared:ro" \
    --bind "$run/work:/run:rw" \
    --bind "$run/results:/results:rw" \
    --env PYTHONPATH=/patch:/confirm:/opt/torch-reviews/vendor \
    --env PYTHONDONTWRITEBYTECODE=1 --env TMPDIR=/tmp \
    --env OPENBLAS_NUM_THREADS=1 --env OMP_NUM_THREADS=1 \
    --env "SLURM_JOB_ID=$job" --env "TORCH_IMAGE_SHA256=$image_sha" \
    "$image" python -B /confirm/shared_guest.py \
    --package /patch --package-sha "$package_sha" \
    --bundle /bundle --prepared /prepared --work /run --output /results \
    --module-sha "$module_sha" --qualification-sha "$parity_sha"

archive="votes108-shared-${job}.tar.gz"
tar -czf "$run/$archive" -C "$run" \
    results/shared-receipt.json results/lookup.json results/quality.jsonl \
    results/timing.jsonl results/eligible.json
(cd "$run" && sha256sum "$archive" > "$archive.sha256")
printf 'Return archive %s/%s\n' "$run" "$archive"
