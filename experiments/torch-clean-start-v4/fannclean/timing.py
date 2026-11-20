"""Native-bracketed, randomized repeated blocks; retain every sample and control."""

import random
from collections import defaultdict

import numpy as np

from .core import digest


def measure(cases, families, execute, seed, blocks=2):
    if blocks < 2 or blocks > 6:
        raise ValueError("two to six predeclared independent timing blocks required")
    records = []
    declarations = defaultdict(set)
    for case in cases:
        for family in families(case):
            declarations[family].add(case["handle"])
    declaration_hashes = {f: digest(sorted(h)) for f, h in declarations.items()}
    for block in range(blocks):
        rng = random.Random(seed + 104729 * block)
        order = list(cases)
        rng.shuffle(order)
        warmups = {}
        for case in order:
            for arm in ["native", *families(case)]:
                warmups.setdefault((case["filter"], arm), case)
        warmup_order = list(warmups.items())
        rng.shuffle(warmup_order)
        for (_, arm), case in warmup_order:
            sample = execute(case, arm, block % 4)
            records.append(
                {
                    "phase": "warmup",
                    "block": block,
                    "family": arm,
                    "handle": case["handle"],
                    "filter": case["filter"],
                    "request_ns": sample["request_ns"],
                    "query_ordinal": sample["query_ordinal"],
                }
            )
        for case in order:
            arms = list(families(case))
            rng.shuffle(arms)
            # Same reader for the whole bracket. Reader/core effects cannot rank arms.
            reader = block % 4
            # Warm this exact query's buffer working set before BOTH baseline
            # measurements. Otherwise the first baseline can price cache misses
            # that no subsequent arm pays, producing fake savings for no-ops.
            warm = execute(case, "native", reader)
            before = execute(case, "native", reader)
            within = [(arm, execute(case, arm, reader)) for arm in arms]
            after = execute(case, "native", reader)
            baseline = (before["request_ns"] + after["request_ns"]) / 2
            for arm, result in within:
                records.append(
                    {
                        "phase": "sample",
                        "handle": case["handle"],
                        "group": case["group"],
                        "filter": case["filter"],
                        "role": case["role"],
                        "block": block,
                        "reader": reader,
                        "family": arm,
                        "request_ns": result["request_ns"],
                        "native_ns": baseline,
                        "native_before_ns": before["request_ns"],
                        "native_after_ns": after["request_ns"],
                        "query_ordinal": result["query_ordinal"],
                        "native_before_ordinal": before["query_ordinal"],
                        "case_warmup_ns": warm["request_ns"],
                        "case_warmup_ordinal": warm["query_ordinal"],
                        "native_after_ordinal": after["query_ordinal"],
                        "declared_blocks": blocks,
                        "declared_handles_sha256": declaration_hashes[arm],
                    }
                )
    return records


def summarize(records, draws=10000, tolerance=0.02, seed=0):
    """Resample vector groups and measurement blocks together for paired ratios."""
    records = [r for r in records if r.get("phase", "sample") == "sample"]
    result = {
        "families": {},
        "controls_pass": False,
        "interpretation": (
            "Conditional on this allocation; resamples groups and blocks. All samples retained."
        ),
    }
    if not records:
        return result
    expected_blocks = set(range(records[0]["declared_blocks"]))
    expected_filters = {r["filter"] for r in records}
    if any(r["declared_blocks"] != len(expected_blocks) for r in records):
        raise ValueError("inconsistent timing declaration")
    for family in {r["family"] for r in records}:
        chosen = [r for r in records if r["family"] == family]
        keys = {(r["handle"], r["block"]) for r in chosen}
        handles = {r["handle"] for r in chosen}
        expected_hash = digest(sorted(handles))
        if any(r["declared_handles_sha256"] != expected_hash for r in chosen):
            raise ValueError("incomplete declared timing panel")
        if len(keys) != len(chosen) or keys != {(h, b) for h in handles for b in expected_blocks}:
            raise ValueError("incomplete or duplicate timing block; do not rank partial returns")
        filters_by_group = defaultdict(set)
        for r in chosen:
            filters_by_group[r["group"]].add(r["filter"])
        if any(v != expected_filters for v in filters_by_group.values()):
            raise ValueError("incomplete filter coverage")
    for family in sorted({r["family"] for r in records}):
        selected = [r for r in records if r["family"] == family]
        scopes = {"all": selected}
        scopes.update(
            {
                str(t): [r for r in selected if r["filter"] == t]
                for t in {r["filter"] for r in selected}
            }
        )
        estimates = {}
        for name, rows in scopes.items():
            groups, blocks = sorted({r["group"] for r in rows}), sorted({r["block"] for r in rows})
            if len(groups) < 2 or len(blocks) < 2:
                estimates[name] = {"status": "insufficient_clusters"}
                continue
            values = np.empty((len(groups), len(blocks), 2))
            cells = defaultdict(list)
            for r in rows:
                cells[r["group"], r["block"]].append(r)
            for gi, group in enumerate(groups):
                for bi, block in enumerate(blocks):
                    cell = cells[group, block]
                    if not cell:
                        raise ValueError("incomplete timing block; do not rank partial returns")
                    values[gi, bi] = [
                        np.mean([r["request_ns"] for r in cell]),
                        np.mean([r["native_ns"] for r in cell]),
                    ]
            rng = np.random.default_rng(seed)
            ratios = []
            for offset in range(0, draws, 128):
                count = min(128, draws - offset)
                gs = rng.integers(0, len(groups), (count, len(groups)))
                bs = rng.integers(0, len(blocks), (count, len(blocks)))
                sampled = values[gs[:, :, None], bs[:, None, :]].mean(axis=(1, 2))
                ratios.extend((sampled[:, 0] / sampled[:, 1]).tolist())
            ratio = float(values[:, :, 0].mean() / values[:, :, 1].mean())
            estimates[name] = {
                "status": "estimated",
                "ratio": ratio,
                "savings_percent": 100 * (1 - ratio),
                "ci95": np.quantile(ratios, [0.025, 0.975]).tolist(),
                "ci90": np.quantile(ratios, [0.05, 0.95]).tolist(),
                "groups": len(groups),
                "blocks": len(blocks),
            }
        result["families"][family] = estimates
    controls = [v for f in ("clone", "empty") for v in result["families"].get(f, {}).values()]
    result["controls_pass"] = (
        all(f in result["families"] for f in ("clone", "empty"))
        and bool(controls)
        and all(
            v.get("status") == "estimated"
            and v["ci90"][0] >= 1 - tolerance
            and v["ci90"][1] <= 1 + tolerance
            for v in controls
        )
    )
    # Matched continuation is paired to the candidate using the identical query/block cells.
    for family in list(result["families"]):
        if not family.startswith("candidate:"):
            continue
        matched = "matched:" + family.split(":", 1)[1]
        by_key = {(r["handle"], r["block"]): r for r in records if r["family"] == matched}
        paired = [
            {**r, "family": "paired", "native_ns": by_key[r["handle"], r["block"]]["request_ns"]}
            for r in records
            if r["family"] == family
        ]
        # No candidate prefix in recursive call, hence no recursive pairing.
        result["families"][family]["matched"] = summarize(paired, draws, tolerance, seed)[
            "families"
        ]["paired"]["all"]
    return result
