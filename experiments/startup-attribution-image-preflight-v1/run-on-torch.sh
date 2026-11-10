#!/usr/bin/env bash
set -euo pipefail
umask 077
probe_package="$(cd -- "$(dirname -- "$0")" && pwd -P)"
probe_results=/home/dar579/torch-reviews-results
probe_binding="$probe_results/.startup-attribution-image-preflight-v1-binding.json"
probe_image=/home/dar579/torch-reviews-first/images/runtime.sif
probe_apptainer=/share/apps/apptainer/bin/apptainer
probe_python="$(command -v python3)"
test -d "$probe_results"
test -x "$probe_apptainer"
test ! -e "$probe_binding"
PYTHONDONTWRITEBYTECODE=1 "$probe_python" "$probe_package/inspect_image.py" verify
printf '%s  %s\n' '7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a' "$probe_image" | sha256sum -c -
probe_manifest="$(sha256sum "$probe_package/manifest.json")"
probe_manifest="${probe_manifest%% *}"
probe_output="$(mktemp -d "$probe_results/startup-attribution-image-preflight-v1.XXXXXXXX")"
# One data-only invocation; binding survives failure and is never overwritten.
( set -C; printf '{"directory":"%s","capsule_manifest_sha256":"%s"}\n' "$probe_output" "$probe_manifest" > "$probe_binding" )
probe_code=0
( ulimit -f 256
  exec timeout --signal=TERM --kill-after=5s 60s \
  "$probe_apptainer" exec --cleanenv --containall --no-home --pwd /tmp \
  --bind "$probe_package:/inspect:ro" \
  --env "PYTHONPATH=/inspect/reference:/inspect/reference/frozen:/inspect/reference/frozen/vendor:/opt/torch-reviews/vendor" \
  --env PYTHONDONTWRITEBYTECODE=1 --env OPENBLAS_NUM_THREADS=1 --env OMP_NUM_THREADS=1 \
  --env 'SA_VERIFIED_IMAGE_SHA256=7cbaab49d5ed4772176df0c4fe0f64f0482ec972fb48d2af598b1b6c97857d9a' \
  "$probe_image" python /inspect/inspect_image.py inspect ) \
  > "$probe_output/image-capability.json" 2> "$probe_output/stderr.log" || probe_code="$?"
printf '%s\n' "$probe_code" > "$probe_output/exit-code.txt"
( cd "$probe_output"; sha256sum image-capability.json stderr.log exit-code.txt > SHA256SUMS )
printf 'Image inventory exit code: %s\nResults: %s\n' "$probe_code" "$probe_output"
printf '%s\n' 'No Slurm job submitted. A2 native handoff stays held. Download these results.'
