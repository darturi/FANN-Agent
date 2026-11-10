"""Compact measured-grid matrices; unreachable slots are never imputed."""

import gc
from dataclasses import dataclass

import numpy as np
from common import ROOT, digest, read

GRID = [1, 2, 4, 8, 16, 32, 64, 128]
FILTERS = ["unfiltered", "votes32", "votes108"]


@dataclass
class Data:
    meta: list
    folds: dict
    definitions: dict
    names: dict
    x: dict
    full_x: dict
    slices: list
    reached: np.ndarray
    labels: dict

    def indices(self, groups):
        selected = np.array(
            [i for i, q in enumerate(self.meta) if q["group"] in set(groups)], dtype=int
        )
        if len(selected) != len(set(groups)) * 3:
            raise ValueError("Expected three filter cases per group")
        return selected


def load(pins):
    audit = read(ROOT / "research/fannagent-p3a-evidence-audit-2026-10-24/audit.json")
    defs = audit["feature_definitions"]
    names = {
        "static23": [n for n, d in defs.items() if d["group"] != "progress_filter"],
        "progress34": list(defs),
    }
    # Definitions are serialized by name: use a fixed lexical column order.
    names = {k: sorted(v) for k, v in names.items()}
    if [len(names[k]) for k in ["static23", "progress34"]] != [23, 34]:
        raise ValueError("Qualified information scope changed")
    corpus = read(ROOT / pins["corpus"])
    rows = sorted(corpus["queries"], key=lambda q: (q["group"], FILTERS.index(q["stratum"])))
    if len(rows) != 600 or len(corpus["folds"]) != 200:
        raise ValueError("Wrong independent-group inventory")
    meta = [
        {k: q[k] for k in ["query_id", "group", "stratum", "native_recall", "native_work"]}
        for q in rows
    ]
    x = {p: np.full((600, 8, len(ns)), np.nan) for p, ns in names.items()}
    reached = np.zeros((600, 8), dtype=bool)
    labels = {
        p: {
            k: np.full((600, 9), np.nan)
            for k in ["recall", "valid", "count", "activation", "reuse", "work"]
        }
        for p in names
    }
    full, slices = {p: [] for p in names}, []
    offset = 0
    for i, q in enumerate(rows):
        if q["group"] != q["query_id"].rsplit("-", 1)[0] or q["stratum"] not in FILTERS:
            raise ValueError("Query/group binding changed")
        length = len(q["base_states"])
        slices.append((offset, offset + length))
        offset += length
        if len(q["local_states"]) != length:
            raise ValueError("Profile trajectories differ")
        for p, family in [("static23", "base"), ("progress34", "local")]:
            ns = names[p]
            states = q[family + "_states"]
            if [s["checkpoint_index"] for s in states] != list(range(1, length + 1)):
                raise ValueError("Incomplete full trajectory")
            full[p].extend([[s["features"][n] for n in ns] for s in states])
            for j, cp in enumerate(GRID):
                if cp > length:
                    if str(cp) in q["labels"][family]:
                        raise ValueError("Label for unreachable checkpoint")
                    continue
                if str(cp) not in q["labels"][family]:
                    raise ValueError("Unknown reached stop outcome")
                reached[i, j] = True
                values = [states[cp - 1]["features"][n] for n in ns]
                if any(v is None or not np.isfinite(v) for v in values):
                    raise ValueError("Qualified feature unavailable/nonfinite")
                x[p][i, j] = values
            for j, cp in enumerate([*GRID, None]):
                if cp is not None and not reached[i, j]:
                    continue
                label = q["continue_costs"][family] if cp is None else q["labels"][family][str(cp)]
                for key, source in [
                    ("recall", "recall"),
                    ("valid", "valid"),
                    ("count", "returned_count"),
                    ("activation", "activation_ms_saved"),
                    ("reuse", "reuse_ms_saved"),
                    ("work", "layer0_distances"),
                ]:
                    labels[p][key][i, j] = label[source]
                if cp is None and (
                    label["recall"] != q["native_recall"]
                    or not label["valid"]
                    or label["returned_count"] != 10
                ):
                    raise ValueError("Continue result differs from native")
    if int(reached.sum()) != 4695:
        raise ValueError("Reachable-grid coverage changed")
    full = {p: np.asarray(v, dtype=float) for p, v in full.items()}
    out = Data(meta, corpus["folds"], defs, names, x, full, slices, reached, labels)
    del corpus, rows
    gc.collect()
    return out


def training_data(data, profile, groups):
    selected = data.indices(groups)
    q, j = np.where(data.reached[selected])
    qi = selected[q]
    x = data.x[profile][qi, j]
    label = data.labels[profile]
    native = np.array([data.meta[i]["native_recall"] for i in qi])
    invalid = (label["valid"][qi, j] != 1) | (label["count"][qi, j] != 10)
    loss = np.where(invalid, 1.0, np.maximum(0, native - label["recall"][qi, j]))
    benefit = np.minimum(label["activation"][qi, j], label["reuse"][qi, j])
    weights = 1 / (3 * data.reached[qi].sum(axis=1))
    ids = np.array([data.meta[i]["group"] for i in qi])
    if not np.isfinite(x).all() or not np.isfinite(loss).all() or not np.isfinite(benefit).all():
        raise ValueError("Nonfinite fitting data")
    if np.any(loss < 0) or np.any(loss > 1):
        raise ValueError("Loss outside [0,1]")
    for group in groups:
        if not np.isclose(weights[ids == group].sum(), 1):
            raise ValueError("Vector weights differ")
    return (
        x,
        loss,
        benefit,
        weights,
        ids,
        {
            "training_groups": sorted(groups),
            "groups_sha256": digest(sorted(groups)),
            "reached_rows": len(loss),
            "risk_target_sha256": digest(loss.tolist()),
            "benefit_target_sha256": digest(benefit.tolist()),
            "weights_sha256": digest(weights.tolist()),
        },
    )


def outcomes(data, profile, indices, chosen):
    chosen = np.asarray(chosen, dtype=int)
    if len(chosen) != len(indices) or np.any(chosen < 0) or np.any(chosen > 8):
        raise ValueError("Invalid action indices")
    for i, j in zip(indices, chosen):
        if j != 8 and not data.reached[i, j]:
            raise ValueError("Unmeasured/unreachable selected stop")
    result = []
    for i, j in zip(indices, chosen):
        q = data.meta[i]
        label = data.labels[profile]
        result.append(
            {
                **q,
                "checkpoint": None if j == 8 else GRID[j],
                "policy_recall": float(label["recall"][i, j]),
                "recall_delta": float(label["recall"][i, j] - q["native_recall"]),
                "valid": bool(label["valid"][i, j] == 1 and label["count"][i, j] == 10),
                "returned_count": int(label["count"][i, j]),
                "activation_proxy_ms_saved": float(label["activation"][i, j]),
                "reuse_proxy_ms_saved": float(label["reuse"][i, j]),
                "layer0_distances": float(label["work"][i, j]),
            }
        )
    return result
