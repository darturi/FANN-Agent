#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
  upload|download) probe_action="$1" ;;
  *) echo 'Usage: bash transfer.sh upload|download' >&2; exit 2 ;;
esac
cd '@OUTPUT@'
probe_socketdir="$(mktemp -d -t fann-image-ssh)"
probe_binding="$probe_socketdir/binding.json"
probe_options=(
  -o HostKeyAlias=dtn.torch.hpc.nyu.edu -o HostKeyAlgorithms=ssh-ed25519
  -o StrictHostKeyChecking=yes -o UpdateHostKeys=no -o PubkeyAuthentication=no
  -o ControlMaster=auto -o ControlPersist=600 -o "ControlPath=$probe_socketdir/connection"
)
probe_cleanup() {
  ssh "${probe_options[@]}" -O exit dar579@dtn012.hpc.nyu.edu >/dev/null 2>&1 || true
  rm -f "$probe_binding" "$probe_socketdir/connection"
  rmdir "$probe_socketdir" 2>/dev/null || true
}
trap probe_cleanup EXIT
if test "$probe_action" = upload; then
  PYTHONDONTWRITEBYTECODE=1 '@PYTHON@' '@PACKAGE@/inspect_image.py' verify
  printf '%s\n' '@ARCHIVE_SHA@  @NAME@.tar.gz' | shasum -a 256 -c -
fi
printf '%s\n' 'Authenticate with Torch DTN; file transfer follows. No job will be submitted.'
if ! ssh -t "${probe_options[@]}" dar579@dtn012.hpc.nyu.edu true; then
  echo 'Authentication failed before transfer. No job submitted.' >&2
  exit 1
fi
if test "$probe_action" = upload; then
  scp "${probe_options[@]}" '@NAME@.tar.gz' '@NAME@.tar.gz.sha256' dar579@dtn012.hpc.nyu.edu:/home/dar579/
  ssh "${probe_options[@]}" dar579@dtn012.hpc.nyu.edu 'set -e
cd /home/dar579
printf "%s\n" "@ARCHIVE_SHA@  @NAME@.tar.gz" | sha256sum -c -'
  echo 'UPLOAD VERIFIED. Image-only inventory capsule is in /home/dar579/. No job submitted.'
else
  scp "${probe_options[@]}" dar579@dtn012.hpc.nyu.edu:/home/dar579/torch-reviews-results/.startup-attribution-image-preflight-v1-binding.json "$probe_binding"
  probe_run="$( '@PYTHON@' - "$probe_binding" <<'PYBIND'
import json,re,sys
v=json.load(open(sys.argv[1]))
if v['capsule_manifest_sha256']!='@MANIFEST@':
    raise SystemExit('Inventory binding belongs to another capsule')
p=v['directory']
if not re.fullmatch(r'/home/dar579/torch-reviews-results/startup-attribution-image-preflight-v1[.][A-Za-z0-9]{8}',p):
    raise SystemExit('Unexpected inventory result path')
print(p)
PYBIND
  )"
  probe_local='@OUTPUT@/returned/'"${probe_run##*/}"
  mkdir -p '@OUTPUT@/returned'
  mkdir "$probe_local"
  for probe_file in image-capability.json stderr.log exit-code.txt SHA256SUMS; do
    scp "${probe_options[@]}" "dar579@dtn012.hpc.nyu.edu:${probe_run}/$probe_file" "$probe_local/"
  done
  ( cd "$probe_local"; shasum -a 256 -c SHA256SUMS )
  PYTHONDONTWRITEBYTECODE=1 '@PYTHON@' '@PACKAGE@/experiment.py' check-return --directory "$probe_local"
  echo 'Inventory evidence downloaded. A2 native handoff remains held for compatibility review.'
fi
