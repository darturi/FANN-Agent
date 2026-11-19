"""Retire the seeded acquisition workflow; historical analysis remains available."""

RETIREMENT_REASON = (
    "This v3 live workflow is retired: it initializes the agent with measurements "
    "from prior experiments. It does not satisfy the required clean start. "
    "A replacement that acquires evidence within its own run is not implemented; "
    "new preparation, generation and native dispatch are disabled. "
    "Historical status, collection and offline analysis remain available."
)


def require_live_workflow():
    raise ValueError(RETIREMENT_REASON)
