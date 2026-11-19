"""Retire the seeded acquisition workflow; historical analysis remains available."""

RETIREMENT_REASON = (
    "This v3 live workflow is retired: it initializes the agent with measurements "
    "from prior experiments. It does not satisfy the required clean start. "
    "This workflow's preparation, generation and native dispatch remain disabled. "
    "Use the separate torch-clean-start-v4 implementation for fresh evidence acquisition; "
    "it has no experiment results yet. "
    "Historical status, collection and offline analysis remain available."
)


def require_live_workflow():
    raise ValueError(RETIREMENT_REASON)
