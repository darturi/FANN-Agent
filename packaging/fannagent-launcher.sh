#!/usr/bin/env bash
set -euo pipefail
install_root=$(cd -- "$(dirname -- "$0")" && pwd -P)
mode=$(cat "$install_root/mode")
runtime=$(cat "$install_root/runtime")
export MSWEA_SILENT_STARTUP=1 LITELLM_LOCAL_MODEL_COST_MAP=True
if [ -f "$install_root/sandbox.image" ]; then
  export FANNAGENT_WORKSPACE_IMAGE=$(cat "$install_root/sandbox.image")
fi
if [ -f "$install_root/database.image" ]; then
  export FANNAGENT_PGVECTOR_IMAGE=$(cat "$install_root/database.image")
fi
if [ "$mode" = host ]; then
  exec "$runtime/bin/fannagent" "$@"
fi
workspace=$(pwd -P)
endpoint=${DOCKER_HOST:-$(docker context inspect --format '{{.Endpoints.docker.Host}}')}
case "$endpoint" in unix://*) socket=${endpoint#unix://} ;; *)
  echo 'The container launcher requires a local Unix Docker socket.' >&2; exit 1 ;; esac
if [ ! -S "$socket" ]; then echo 'Start the local Docker daemon.' >&2; exit 1; fi
# Docker Desktop exposes the socket with daemon-side ownership, which can differ
# from the host stat result. Probe the actual bind mount without opening the socket.
socket_gid=$(docker run --rm --read-only --cap-drop ALL \
  --mount "type=bind,source=$socket,target=/var/run/docker.sock,readonly" \
  --entrypoint stat "$runtime" -c %g /var/run/docker.sock)
[[ "$socket_gid" =~ ^[0-9]+$ ]] || { echo 'Cannot determine Docker socket group.' >&2; exit 1; }
name=fannagent-controller-$(od -An -N8 -tx1 /dev/urandom | tr -d ' \n')
args=(run --rm --init --name "$name" --label io.fannagent.controller=1
  --read-only --cap-drop ALL --security-opt no-new-privileges
  --user "$(id -u):$(id -g)" --group-add "$socket_gid" --tmpfs /tmp:rw,size=256m
  --mount "type=bind,source=$workspace,target=$workspace"
  --mount "type=bind,source=$socket,target=/var/run/docker.sock"
  -w "$workspace" -e "FANNAGENT_CONTROLLER=$name" -e HOME=/tmp
  --add-host host.docker.internal:host-gateway)
# Explicitly allow additional input directories; bind them at the same absolute path.
while IFS= read -r input || [ -n "$input" ]; do
  [ -z "$input" ] && continue
  [ -d "$input" ] || { echo "Input mount directory missing: $input" >&2; exit 1; }
  input=$(cd -- "$input" && pwd -P)
  args+=(--mount "type=bind,source=$input,target=$input,readonly")
done <<< "${FANNAGENT_INPUT_DIRS:-}"
if [ -n "${FANNAGENT_ENV_FILE:-}" ]; then args+=(--env-file "$FANNAGENT_ENV_FILE"); fi
for key in FANNAGENT_DATABASE_URL FANNAGENT_REPLICATION_URL OPENAI_API_KEY ANTHROPIC_API_KEY \
  AZURE_API_KEY AZURE_API_BASE AZURE_API_VERSION OPENAI_API_BASE FANNAGENT_WORKSPACE_IMAGE \
  FANNAGENT_PGVECTOR_IMAGE; do
  if [ -n "${!key:-}" ]; then args+=(-e "$key"); fi
done
while IFS= read -r key || [ -n "$key" ]; do
  [ -z "$key" ] && continue
  [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || { echo 'Invalid credential variable name.' >&2; exit 1; }
  args+=(-e "$key")
done <<< "${FANNAGENT_ENV_NAMES:-}"
stop_controller() { docker stop --time 10 "$name" >/dev/null 2>&1 || true; }
trap 'stop_controller; exit 130' INT
trap 'stop_controller; exit 143' TERM
docker "${args[@]}" "$runtime" "$@" &
child=$!
set +e
wait "$child"
result=$?
set -e
trap - INT TERM
exit "$result"
