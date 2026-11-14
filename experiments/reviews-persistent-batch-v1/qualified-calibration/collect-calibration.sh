#!/bin/bash
set -euo pipefail
umask 077

stage=$(cd -- "$(dirname -- "$0")" && pwd -P)
cd "$stage"
sha256sum -c SHA256SUMS
[[ "$(wc -l < jobs.tsv)" -eq 3 ]]
members=(jobs.tsv confirmation/prior-quality.jsonl)
while IFS=$'\t' read -r job node; do
  [[ "$job" =~ ^[1-9][0-9]*$ && "$node" =~ ^cs[0-9]+$ ]]
  state=$(/opt/slurm/bin/sacct --local -n -P -j "$job" -o JobIDRaw%24,State%32,ExitCode,NodeList%32 |
    awk -F'|' -v id="$job" '$1 == id {state=$2 "|" $3 "|" $4; if (!seen[state]++) print state}')
  if [[ "$state" != "COMPLETED|0:0|$node" ]]; then
    printf 'Job %s is not ready for collection (%s)\n' "$job" "$state" >&2
    exit 1
  fi
  name="votes108-shared-$job.tar.gz"
  (cd "run-$job" && sha256sum -c "$name.sha256")
  test -s "host-$job.tsv"
  members+=("host-$job.tsv" "run-$job/$name" "run-$job/$name.sha256")
done < jobs.tsv
leaf=${stage##*/}
archive="votes108-calibration-${leaf##*.}.tar.gz"
if [[ ! -e "$archive" ]]; then
  COPYFILE_DISABLE=1 tar -czf "$archive.tmp" "${members[@]}"
  mv "$archive.tmp" "$archive"
fi
if [[ ! -e "$archive.sha256" ]]; then
  sha256sum "$archive" > "$archive.sha256.tmp"
  mv "$archive.sha256.tmp" "$archive.sha256"
fi
sha256sum -c "$archive.sha256"
printf 'Run these two commands separately in local SFTP:\n'
printf 'get %s/%s /private/tmp/%s\n' "$stage" "$archive" "$archive"
printf 'get %s/%s.sha256 /private/tmp/%s.sha256\n' "$stage" "$archive" "$archive"
