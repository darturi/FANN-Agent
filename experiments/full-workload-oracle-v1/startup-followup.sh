#!/bin/bash
set -euo pipefail
umask 077
stage=$(cd -- "$(dirname -- "$0")" && pwd -P)
probe="$stage/.startup-preflight"
mkdir -m700 "$probe"
tar -xzf "$stage/original-package.tar.gz" -C "$probe"
package="$probe/reviews-persistent-batch-native-v1"
source_results=/scratch/dar579/fannagent-benchmark-evaluation-v1/oracle-headroom-20261117-v1/full-workload-oracle-v1/run-23544718/results
image=/home/dar579/torch-reviews-first/images/runtime.sif
for entry in oracle_preflight.py followup_run.py; do
    flags=(--check-only)
    [[ "$entry" != oracle_preflight.py ]] || flags=(--package /patch)
    /share/apps/apptainer/bin/apptainer exec --cleanenv --containall --no-home --pwd /tmp \
        --bind "$package:/patch:ro" --bind "$stage:/qual:ro" \
        --bind "$source_results:/acquisition:ro" \
        --bind "$stage/oracle-module.so:/opt/postgresql/lib/vector.so:ro" \
        --env PYTHONPATH=/patch:/qual:/opt/torch-reviews/vendor --env PYTHONDONTWRITEBYTECODE=1 \
        --env OPENBLAS_NUM_THREADS=1 --env OMP_NUM_THREADS=1 \
        "$image" python -B "/qual/$entry" "${flags[@]}" \
        > "$probe/$entry.json" 2> "$probe/$entry.err"
    cat "$probe/$entry.json"
done
