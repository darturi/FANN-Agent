from __future__ import annotations

import json

import numpy as np

from .api.primitives.filters import evaluate_filter
from .config import WorkloadConfig
from .errors import AgentError
from .snapshot import Snapshot
from .store import digest


def generate(snapshot: Snapshot, config: WorkloadConfig) -> list[dict]:
    rng = np.random.default_rng(config.seed)
    rows = snapshot.rows
    result = []
    anchors = rng.permutation(len(rows))
    for i in range(config.count):
        anchor = int(anchors[i % len(anchors)])
        vector = snapshot.data.vectors[anchor].astype(np.float64)
        vector += rng.normal(size=len(vector)) * 0.05 / np.sqrt(len(vector))
        vector = (vector / np.linalg.norm(vector)).astype(np.float32)
        predicate = None
        if snapshot.fields:
            field = snapshot.fields[i % len(snapshot.fields)]
            name, kind = field["name"], field["type"]
            values = [r["metadata"].get(name) for r in rows]
            known = [v for v in values if v is not None]
            if field.get("nullable") and i % 13 == 0:
                predicate = {"field": name, "op": "is_null"}
            elif known:
                if kind in {"float", "integer"}:
                    value = np.quantile(known, [0.01, 0.1, 0.5, 0.9][i % 4])
                    value = int(value) if kind == "integer" else float(value)
                    predicate = {"field": name, "op": "lte", "value": value}
                else:
                    predicate = {
                        "field": name,
                        "op": "eq",
                        "value": known[int(rng.integers(len(known)))],
                    }
        query = snapshot.query(
            {"id": f"generated-{i}", "vector": vector.tolist(), "k": config.k, "filter": predicate}
        )
        result.append({"query": query, "anchor": rows[anchor]["source_id"]})
    return result


def create_workload(snapshot: Snapshot, config: WorkloadConfig) -> dict:
    if config.queries:
        raw = [json.loads(line) for line in config.queries.read_text().splitlines() if line.strip()]
        items = [{"query": snapshot.query(q), "anchor": None} for q in raw]
        origin = "supplied"
    else:
        items, origin = generate(snapshot, config), "synthetic"
    if len({q["query"]["id"] for q in items}) != len(items):
        raise AgentError("workload query identifiers must be unique")
    parent = list(range(len(items)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    vectors = np.asarray([q["query"]["vector"] for q in items], dtype=np.float64)
    for i in range(len(items)):
        for j in range(i):
            same_anchor = (
                items[i]["anchor"] is not None and items[i]["anchor"] == items[j]["anchor"]
            )
            if same_anchor or np.linalg.norm(vectors[i] - vectors[j]) <= 1e-3:
                parent[root(i)] = root(j)
    groups = sorted({root(i) for i in range(len(items))})
    np.random.default_rng(config.seed).shuffle(groups)
    if len(groups) < 5:
        raise AgentError("workload needs at least five independent vector groups")
    first, second = max(1, int(0.6 * len(groups))), max(2, int(0.8 * len(groups)))
    assignments = {
        g: "development" if i < first else "calibration" if i < second else "test"
        for i, g in enumerate(groups)
    }
    for i, item in enumerate(items):
        item["group"] = str(root(i))
        item["split"] = assignments[root(i)]
    selectivities = [
        float(evaluate_filter(i["query"]["filter"], snapshot.data.metadata).mean())
        for i in items
        if i["query"].get("filter")
    ]
    requested = [0.01, 0.1, 0.5, 0.9]
    gaps = [
        target
        for target in requested
        if not selectivities or min(abs(value - target) for value in selectivities) > 0.025
    ]
    return {
        "schema_version": 1,
        "items": items,
        "seed": config.seed,
        "origin": origin,
        "dataset_hash": snapshot.identity,
        "claims": "supplied workload" if origin == "supplied" else "synthetic workload only",
        "workload_hash": digest(items),
        "predicate_coverage": {
            "filtered_queries": len(selectivities),
            "observed_selectivities": sorted(set(selectivities)),
            "uncovered_requested_selectivities": gaps,
        },
    }
