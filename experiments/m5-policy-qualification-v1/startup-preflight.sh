#!/bin/bash
set -euo pipefail
umask 077
stage=$(cd -- "$(dirname -- "$0")" && pwd -P)
probe="$stage/.startup-preflight"
mkdir -m 700 "$probe"
tar -xzf "$stage/original-package.tar.gz" -C "$probe"
package="$probe/reviews-persistent-batch-native-v1"
image=/home/dar579/torch-reviews-first/images/runtime.sif
printf '%s  %s\n' b596c69bbab0bb49d720df02b820e5a9f2c1652a47e67b6b327f16f8769663bc "$package/manifest.json" | sha256sum -c -
printf '%s  %s\n' 7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a "$image" | sha256sum -c -
for phase in timing work; do
    if /share/apps/apptainer/bin/apptainer exec --cleanenv --containall --no-home --pwd /tmp \
        --bind "$package:/patch:ro" --bind "$stage:/qual:ro" \
        --bind "$stage/$phase-module.so:/opt/postgresql/lib/vector.so:ro" \
        --env PYTHONPATH=/patch:/qual:/opt/torch-reviews/vendor \
        --env PYTHONDONTWRITEBYTECODE=1 --env TMPDIR=/tmp \
        --env OPENBLAS_NUM_THREADS=1 --env OMP_NUM_THREADS=1 \
        "$image" python -B /qual/m5_preflight.py --package /patch --phase "$phase" \
        > "$probe/$phase.json" 2> "$probe/$phase.err"; then
        cat "$probe/$phase.json"
    else
        status=$?
        cat "$probe/$phase.err" >&2
        printf 'Startup preflight failed for %s (exit %s); no Slurm job submitted. Preserve %s\n' "$phase" "$status" "$probe" >&2
        exit "$status"
    fi
done
printf 'NATIVE_STARTUP_PREFLIGHT_PASSED_NO_QUERIES\n'
