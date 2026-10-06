"""Private adapters implementing the public services supplied to extensions."""

from .api import AgentError, ExecutionLimits, ExtensionContext, digest


class State:
    def __init__(self, store, name):
        self._store, self._prefix = store, f"extension:{name}:"

    def get(self, key, default=None):
        return self._store.get(self._prefix + key, default)

    def set(self, key, value):
        self._store.set(self._prefix + key, value)


class Secrets:
    def __init__(self, store, name):
        self._store, self._prefix = store, f"extension:{name}:"

    def get(self, key):
        return self._store.secret(self._prefix + key)

    def set(self, key, value):
        self._store.secret(self._prefix + key, value)


class Artifacts:
    def __init__(self, store, state, name):
        self._store, self._state, self._name = store, state, name

    def put(self, kind, value, *, scope="private", limit=None):
        identity = self._store.put(
            f"extension:{self._name}:{kind}", value, scope=scope, limit=limit
        )
        identities = self._state.get("artifact_ids", [])
        if identity not in identities:
            self._state.set("artifact_ids", [*identities, identity])
        return identity

    def read(self, identity):
        if identity not in self._state.get("artifact_ids", []):
            raise AgentError("artifact is outside this extension namespace")
        return self._store.read(identity)


class Journal:
    def __init__(self, state):
        self._state = state

    def record(self, resource):
        rows = list(self.resources())
        if resource not in rows:
            rows.append(resource)
            self._state.set("resource_journal", rows)

    def resources(self):
        return tuple(self._state.get("resource_journal", []))


def context(config, store):
    name = config.backend.name
    private = store.root / "private" / "extensions" / name
    private.mkdir(parents=True, exist_ok=True, mode=0o700)
    state = State(store, name)
    return ExtensionContext(
        name,
        digest(str(store.root)),
        private,
        config.configuration_origin,
        ExecutionLimits(
            config.resources.cpus,
            config.resources.memory_gib,
            config.evidence.max_bytes,
            config.evidence.trace_max_bytes,
            config.query_timeout_seconds,
        ),
        state,
        Secrets(store, name),
        Artifacts(store, state, name),
        Journal(state),
    )
