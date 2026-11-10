"""Vector-clustered first-stop assessment; fixed-stop proxies are not latency."""

from collections import Counter

import numpy as np
from data import FILTERS


class Bootstrap:
    def __init__(self, groups, samples=10000):
        self.groups = sorted(groups)
        rng = np.random.default_rng(20261019)
        ix = rng.integers(0, len(self.groups), size=(samples, len(self.groups)))
        counts = np.zeros((samples, len(self.groups)))
        np.add.at(counts, (np.arange(samples)[:, None], ix), 1 / len(self.groups))
        self.weights = counts

    def ci(self, values):
        return np.quantile(self.weights @ np.asarray(values), [0.025, 0.975], axis=0)


def assess(rows, bootstrap, *, all_metrics=True):
    expected = {(g, f) for g in bootstrap.groups for f in FILTERS}
    if {(r["group"], r["stratum"]) for r in rows} != expected or len(rows) != len(expected):
        raise ValueError("Incomplete/duplicate first-stop group/filter coverage")
    reports = {}
    keys = ["recall_delta", "activation_proxy_ms_saved", "reuse_proxy_ms_saved"]
    for f in ["overall", *FILTERS]:
        selected = [r for r in rows if f == "overall" or r["stratum"] == f]
        by_group = {g: [r for r in selected if r["group"] == g] for g in bootstrap.groups}
        use = keys if all_metrics else keys[:1]
        values = np.array(
            [[np.mean([r[k] for r in by_group[g]]) for k in use] for g in bootstrap.groups]
        )
        ci = bootstrap.ci(values)
        mean = values.mean(axis=0)
        native = float(np.mean([r["native_recall"] for r in selected]))
        valid = all(r["valid"] and r["returned_count"] == 10 for r in selected)
        report = {
            "independent_vectors": len(by_group),
            "query_filter_cases": len(selected),
            "native_recall": native,
            "policy_recall": float(np.mean([r["policy_recall"] for r in selected])),
            "all_valid_complete_top10": valid,
            "recall_delta": float(mean[0]),
            "recall_delta_ci95": ci[:, 0].tolist(),
            "development_recall_pass": bool(valid and native >= 0.95 and ci[0, 0] >= -0.0025),
            "original_tolerance_recall_replay_pass": bool(
                valid and native >= 0.95 and ci[0, 0] >= -0.005
            ),
            "stopped_cases": sum(r["checkpoint"] is not None for r in selected),
            "incomplete_cases": sum(not r["valid"] for r in selected),
            "recall_loss_cases": sum(r["recall_delta"] < -1e-12 for r in selected),
            "activation_proxy_ms_saved": float(np.mean([r[keys[1]] for r in selected])),
            "reuse_proxy_ms_saved": float(np.mean([r[keys[2]] for r in selected])),
        }
        if all_metrics:
            report["activation_proxy_ms_saved_ci95"] = ci[:, 1].tolist()
            report["reuse_proxy_ms_saved_ci95"] = ci[:, 2].tolist()
        reports[f] = report
    overall = reports.pop("overall")
    recall_pass = overall["development_recall_pass"] and all(
        v["development_recall_pass"] for v in reports.values()
    )
    utility = min(overall["activation_proxy_ms_saved"], overall["reuse_proxy_ms_saved"])
    return {
        "overall": overall,
        "per_filter": reports,
        "utility_proxy_ms": utility,
        "development_signal": bool(recall_pass and utility > 0 and overall["stopped_cases"] > 0),
        "development_recall_pass": bool(recall_pass),
        "original_tolerance_recall_replay_pass": bool(
            overall["original_tolerance_recall_replay_pass"]
            and all(v["original_tolerance_recall_replay_pass"] for v in reports.values())
        ),
        "first_stop_histogram": dict(
            sorted(
                Counter(
                    str(r["checkpoint"]) if r["checkpoint"] is not None else "continue"
                    for r in rows
                ).items()
            )
        ),
        "actual_new_policy_latency": "unmeasured",
        "canonical_acceptance": False,
    }


def paired(left, right, bootstrap):
    index = {(r["group"], r["stratum"]): r for r in right}
    rows = []
    for r in left:
        ref = index[(r["group"], r["stratum"])]
        rows.append(
            {
                **r,
                "policy_recall": r["policy_recall"] - ref["policy_recall"],
                "recall_delta": r["recall_delta"] - ref["recall_delta"],
                "activation_proxy_ms_saved": r["activation_proxy_ms_saved"]
                - ref["activation_proxy_ms_saved"],
                "reuse_proxy_ms_saved": r["reuse_proxy_ms_saved"] - ref["reuse_proxy_ms_saved"],
            }
        )
    result = {}
    for f in ["overall", *FILTERS]:
        selected = [r for r in rows if f == "overall" or r["stratum"] == f]
        values = np.array(
            [
                [
                    np.mean([r[k] for r in selected if r["group"] == g])
                    for k in ["recall_delta", "activation_proxy_ms_saved", "reuse_proxy_ms_saved"]
                ]
                for g in bootstrap.groups
            ]
        )
        result[f] = {
            "independent_vectors": len(bootstrap.groups),
            "recall_delta_difference": float(values[:, 0].mean()),
            "recall_delta_difference_ci95": bootstrap.ci(values)[:, 0].tolist(),
            "activation_proxy_saving_difference_ms": float(values[:, 1].mean()),
            "activation_proxy_saving_difference_ci95": bootstrap.ci(values)[:, 1].tolist(),
            "reuse_proxy_saving_difference_ms": float(values[:, 2].mean()),
            "reuse_proxy_saving_difference_ci95": bootstrap.ci(values)[:, 2].tolist(),
            "scope": "Paired fixed-stop development proxies; not actual policy latency.",
        }
    return result
