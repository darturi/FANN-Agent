# FANNAgent local installation bundle

For a public first-run installation, use the [source-install simulation](../README.md#simulation).
The instructions below require a separately assembled local release bundle;
there is no downloadable public bundle or published PyPI package for this snapshot.
The [bundle builder](build_release.py) assembles the local release artifacts.

This bundle installs FANNAgent for simulation or pgvector studies. Configuration,
run state, model charges, policies and evaluation entitlements stay in your workspace.
Installation never prepares a database or calls a paid model.

## Install

For host operation, provide `uv` (which provisions the private pinned Python runtime)
or Python 3.12/3.13. Docker Engine 28+ is needed for pgvector and paid-model sandboxes.
Container operation needs a shell and a local Docker daemon. Remote daemons and
Windows are outside this release's installation contract.

```sh
bash /path/to/bundle/install.sh --backend fake --mode host --directory "$PWD/.fannagent-install"
# Or use the packaged controller image and no host Python:
bash /path/to/bundle/install.sh --backend pgvector --mode container --directory "$PWD/.fannagent-install"
```

Host installation uses locked dependency versions and hashes. With a populated uv
cache, use `--offline`. `--python /absolute/path/to/python` selects an existing runtime.
Use a new installation directory for a different release, backend or mode.
Repeating the same installation preserves configuration and run data.

Container images are referenced by local immutable image IDs and checked against
the release identity. If `images.tar` is supplied, the installer verifies its checksum
and loads it. Otherwise the images must already be in the local daemon. The bundle
contains a manifest and per-artifact checksums; verify it using `verify_bundle.py`.

## First run

```sh
./.fannagent-install/fannagent init --backend fake --output fake.yaml
./.fannagent-install/fannagent doctor fake.yaml
./.fannagent-install/fannagent prepare fake.yaml --run runs/demo
./.fannagent-install/fannagent run fake.yaml --run runs/demo --steps 2
./.fannagent-install/fannagent resume --run runs/demo
./.fannagent-install/fannagent evaluate --run runs/demo
./.fannagent-install/fannagent report --run runs/demo
./.fannagent-install/fannagent clean --run runs/demo
```

Simulation needs no provider credentials and makes no database performance claim.
For a database study, generate a pgvector configuration, edit the target fields,
and set `FANNAGENT_DATABASE_URL` plus either a supplied physical backup or
`FANNAGENT_REPLICATION_URL`. Run `doctor CONFIG --check-source` before preparation.
It checks the source read-only; preparation also verifies backup integrity, Docker
storage, index identity and copy security.

Container source credentials must address the database from the controller;
replication credentials must address it from a separate backup helper. For a source
on the Docker host, use `host.docker.internal` instead of controller loopback.
Credentials are forwarded by environment-variable name. Set `FANNAGENT_ENV_FILE`
to a private Docker-format environment file, or set `FANNAGENT_ENV_NAMES` to additional
variable names, one per line. Never put credential values into CLI arguments.

The launcher mounts the current physical directory at the same absolute path, so
run identity survives subsequent invocations. Keep configs, runs and query files
within that workspace. For outside input directories, set `FANNAGENT_INPUT_DIRS`
to their absolute paths, one per line; these mounts are read-only. Docker Desktop
must permit file sharing for those paths. Additional writable run roots and remote
Docker hosts are unsupported. Locking requires local filesystems supporting SQLite
and atomic hard links; network filesystems are unsupported. A container cannot
prove that a host process has died, so reclaim an abandoned host operation by
running the next command from that host installation. Controller crashes are
recovered using Docker container liveness. An interrupted lock metadata update
fails closed and requires checking the recorded guard owner before removal.

The controller has Docker daemon access and is trusted. The model sandbox has no
Docker socket or network and only sees its development workspace. The agent creates
and journals the database, relay and per-run networks; cleanup retains artifacts and
backups. A Compose template is supplied for advanced use; the launcher handles the
normal UID, socket, mounts, credentials and signal setup.

Native qualification of each assembled controller bundle is a separate gate. Run
`qualify_container.py --bundle /path/to/bundle --workspace /path/to/repository-parent`
with the disposable fixture image available and at least 1 GiB free in Docker's
storage. The secure database image has earlier ARM64 fixture qualification recorded
in `agent-pgvector/QUALIFICATION.md`; this does not qualify new controller routing.
Native AMD64 and broader deployment/data profiles need separate qualification.
Paid-provider smoke testing is also a separate gate; a configured spending contract
does not verify provider behavior. Consult the release's validation record for the
gates actually exercised.

## Build a bundle from source

From the repository parent containing `agent/` and `agent-pgvector/`, with the
development environment, uv and hatchling available:

```sh
agent/.venv/bin/python -m fannagent.build_workspace
agent/.venv/bin/python agent/packaging/build_release.py \
  --output release/fannagent-local --build-controller --save-images
```

Build the secure database image beforehand with `fannagent-pgvector-build`, or use
`--build-runtime-images` to rebuild both runtime images. The controller bases are
pinned by digest, and dependencies come from the distribution lockfiles. Each
distribution remains independently installable; the bundle does not require the harness.
