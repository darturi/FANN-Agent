#!/usr/bin/env bash
set -euo pipefail
bundle=$(cd -- "$(dirname -- "$0")" && pwd -P)
backend=fake
mode=host
destination="$PWD/.fannagent-install"
python_bin=
build_images=0
offline=()
while [ $# -gt 0 ]; do
  case "$1" in
    --backend) backend=$2; shift 2 ;;
    --mode) mode=$2; shift 2 ;;
    --directory) destination=$2; shift 2 ;;
    --python) python_bin=$2; shift 2 ;;
    --build-images) build_images=1; shift ;;
    --offline) offline=(--offline); shift ;;
    --help) echo 'install.sh [--backend fake|pgvector] [--mode host|container] [--directory DIR] [--python PATH] [--build-images] [--offline]'; exit 0 ;;
    *) echo "Unknown installer option: $1" >&2; exit 1 ;;
  esac
done
case "$backend:$mode" in fake:host|fake:container|pgvector:host|pgvector:container) ;; *)
  echo 'Choose backend fake or pgvector and mode host or container.' >&2; exit 1 ;; esac
mkdir -p -- "$destination"
destination=$(cd -- "$destination" && pwd -P)
# Container mode checks and consumes a content-addressed, locally built image.
if [ "$mode" = container ]; then
  docker version --format '{{.Server.Version}}' >/dev/null
  if [ -f "$bundle/images.tar" ]; then
    if command -v sha256sum >/dev/null; then actual=$(sha256sum "$bundle/images.tar")
    else actual=$(shasum -a 256 "$bundle/images.tar"); fi
    expected=$(cat "$bundle/images.tar.sha256")
    [ "${actual%% *}" = "$expected" ] || { echo 'Image archive checksum differs.' >&2; exit 1; }
    docker load --input "$bundle/images.tar" >/dev/null
  fi
  image_file="$bundle/controller-$backend.image"
  [ -f "$image_file" ] || { echo 'Build the controller images with build_release.py --build-controller.' >&2; exit 1; }
  runtime=$(cat "$image_file")
  release=$(cat "$bundle/release-id")
  actual=$(docker image inspect "$runtime" --format '{{index .Config.Labels "io.fannagent.release"}}')
  [ "$actual" = "$release" ] || { echo 'Controller image does not match the release bundle.' >&2; exit 1; }
  docker run --rm --entrypoint python "$runtime" -c 'import fannagent; from fannagent.backends import discover; print(sorted(discover()))'
else
  if [ -z "$python_bin" ]; then
    if command -v uv >/dev/null; then
      export UV_CACHE_DIR="$destination/cache" UV_PYTHON_INSTALL_DIR="$destination/python"
      uv python install "$(cat "$bundle/python-version")" --no-bin "${offline[@]}"
      python_bin=$(uv python find --managed-python "$(cat "$bundle/python-version")")
    else
      for candidate in python3.12 python3.13; do
        if command -v "$candidate" >/dev/null; then python_bin=$(command -v "$candidate"); break; fi
      done
    fi
  fi
  [ -n "$python_bin" ] || { echo 'Install uv or Python 3.12/3.13, or select --mode container.' >&2; exit 1; }
  python_bin=$("$python_bin" -c 'import sys; assert (3,12) <= sys.version_info[:2] < (3,14); print(sys.executable)')
  release=$("$python_bin" "$bundle/verify_bundle.py" "$bundle")
  runtime="$destination/releases/$release-$backend"
  if [ ! -f "$runtime/installed" ]; then
    # Build in its final path: Python entry-point shebangs contain the environment path.
    mkdir -p -- "$runtime"
    "$python_bin" -m venv "$runtime"
    requirements=core-requirements.txt
    [ "$backend" = pgvector ] && requirements=pgvector-requirements.txt
    if command -v uv >/dev/null; then
      uv pip install --python "$runtime/bin/python" --require-hashes \
        "${offline[@]}" -r "$bundle/$requirements"
      uv pip install --python "$runtime/bin/python" --no-deps \
        "${offline[@]}" "$bundle"/wheels/fannagent-*.whl
      if [ "$backend" = pgvector ]; then
        uv pip install --python "$runtime/bin/python" --no-deps \
          "${offline[@]}" "$bundle"/wheels/fannagent_pgvector-*.whl
      fi
    else
      [ ${#offline[@]} = 0 ] || { echo '--offline requires a populated uv cache.' >&2; exit 1; }
      "$runtime/bin/python" -m pip install --require-hashes -r "$bundle/$requirements"
      "$runtime/bin/python" -m pip install --no-deps "$bundle"/wheels/fannagent-*.whl
      if [ "$backend" = pgvector ]; then
        "$runtime/bin/python" -m pip install --no-deps "$bundle"/wheels/fannagent_pgvector-*.whl
      fi
    fi
    "$runtime/bin/fannagent" backends list >/dev/null
    touch "$runtime/installed"
  fi
fi
# Verify the full bundle in container mode too, without host Python.
if [ "$mode" = container ]; then
  docker run --rm --mount "type=bind,source=$bundle,target=/bundle,readonly" \
    --entrypoint python "$runtime" /bundle/verify_bundle.py /bundle >/dev/null
fi
if [ -f "$destination/runtime" ]; then
  old=$(cat "$destination/runtime")
  old_mode=$(cat "$destination/mode")
  if [ "$old" != "$runtime" ] || [ "$old_mode" != "$mode" ]; then
    echo 'Existing installation differs; select a new installation directory.' >&2; exit 1
  fi
fi
if [ "$build_images" = 1 ]; then
  if [ "$mode" = host ]; then
    "$runtime/bin/fannagent-workspace-build"
    [ "$backend" != pgvector ] || "$runtime/bin/fannagent-pgvector-build"
  else
    echo 'Build runtime images with build_release.py --build-runtime-images before container installation.' >&2
    exit 1
  fi
fi
for image in sandbox database; do
  if [ -f "$bundle/$image.image" ]; then cp -- "$bundle/$image.image" "$destination/$image.image"; fi
done
cp -- "$bundle/fannagent-launcher.sh" "$destination/fannagent.tmp"
chmod 755 "$destination/fannagent.tmp"
mv -- "$destination/fannagent.tmp" "$destination/fannagent"
printf '%s\n' "$runtime" > "$destination/runtime.tmp"
printf '%s\n' "$mode" > "$destination/mode.tmp"
mv -- "$destination/runtime.tmp" "$destination/runtime"
mv -- "$destination/mode.tmp" "$destination/mode"
echo "Installed $backend ($mode): $destination/fannagent"
echo 'Run init, doctor, and the simulation before preparing a database study.'
