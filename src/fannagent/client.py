from pathlib import Path

from .api import require_capabilities
from .controller import open_run
from .errors import AgentError
from .study import Study


def open_session(run: str | Path):
    """Install once on a connection to the explicitly selected evaluated copy."""
    config, store, backend = open_run(Path(run))
    if store.get("cleaned") or not store.get("prepared", {}).get("qualified"):
        backend.close()
        raise AgentError("policy session requires a live qualified copy")
    require_capabilities(backend, serving=True)
    deployed = store.get("deployment")
    if deployed:
        if backend.compatibility() != deployed["compatibility"]:
            backend.close()
            raise AgentError("deployed policy compatibility changed")
        policy = backend.validate_policy(deployed["policy"])
        if policy.policy_hash != deployed["policy_hash"]:
            backend.close()
            raise AgentError("deployed policy hash changed")
        return backend.open_policy_session(policy)
    report = store.get("report")
    if not report or store.read(report)["status"] != "accepted":
        backend.close()
        raise AgentError("policy session requires an accepted final evaluation")
    try:
        return backend.open_policy_session(Study(config, store, backend).frozen_policy())
    except BaseException:
        backend.close()
        raise
