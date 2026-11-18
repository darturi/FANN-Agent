#!/bin/bash
set -euo pipefail
umask 077
stage=$(cd -- "$(dirname -- "$0")" && pwd -P)
probe="$stage/.startup-preflight"
mkdir -m 700 "$probe"
tar -xzf "$stage/original-package.tar.gz" -C "$probe"
package="$probe/reviews-persistent-batch-native-v1"
image=/home/dar579/torch-reviews-first/images/runtime.sif
/share/apps/apptainer/bin/apptainer exec --cleanenv --containall --no-home --pwd /tmp \
    --bind "$package:/patch:ro" --bind "$stage:/qual:ro" \
    --bind "$stage/oracle-module.so:/opt/postgresql/lib/vector.so:ro" \
    --env PYTHONPATH=/patch:/qual:/opt/torch-reviews/vendor --env PYTHONDONTWRITEBYTECODE=1 \
    --env OPENBLAS_NUM_THREADS=1 --env OMP_NUM_THREADS=1 \
    "$image" python -B /qual/oracle_preflight.py --package /patch \
    > "$probe/result.json" 2> "$probe/stderr"
cat "$probe/result.json"
