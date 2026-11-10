"""Request admission only; no search or scoring entry points in this module."""

from pc_common import context, inventory
from pc_interface import freeze


def admit(snapshot, items):
    inventory(items)
    if snapshot.field_map != {"m_000000": "total_votes"}:
        raise RuntimeError("Logical metadata mapping differs")
    admitted = []
    for row in items:
        query = snapshot.query(row["query"])
        context(query)
        if query != row["query"]:
            raise RuntimeError("Validated request semantics differ")
        admitted.append(dict(group=row["group"], query=freeze(query)))
    return admitted
