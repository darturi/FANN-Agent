"""Investigate a measured bad stop and screen a revised policy on other queries."""

from collections import defaultdict

from .comparison import check_portfolio
from .core import digest, write


def bad_stop(row):
    return (
        row["checkpoint"] > 0
        and not row["fault"]
        and not row["exhausted"]
        and (row["recall"] + 1e-12 < row["native_recall"] or row["count"] < row["native_count"])
    )


def candidate_measurements(candidate):
    yield candidate["screen_result"], candidate["screen_family"]
    if candidate.get("confirmation"):
        yield candidate["confirmation"], "candidate:0"


def investigate(controller, args):
    candidate_id, handle = args["candidate_id"], args["handle"]
    candidate = controller.state["candidates"][candidate_id]
    points, features = args["later_checkpoints"], args["features"]
    check_portfolio(points, features)
    failing = None
    for measurement, family in candidate_measurements(candidate):
        rows = [row for row in measurement["quality"] if row["family"] == family]
        failing = next((row for row in rows if row["handle"] == handle and bad_stop(row)), None)
        if failing:
            break
    if failing is None:
        raise ValueError(
            "choose a development handle with a measured failed stop for this candidate"
        )
    point = failing["checkpoint"]
    if points[0] <= point:
        raise ValueError("every later checkpoint must follow the measured failed stop")
    peers = sorted(
        (
            row
            for row in rows
            if row["filter"] == failing["filter"]
            and row["group"] != failing["group"]
            and row["checkpoint"] > 0
            and not row["fault"]
            and not row["exhausted"]
            and not bad_stop(row)
        ),
        key=lambda row: (abs(row["checkpoint"] - point), row["handle"]),
    )[:2]
    selected = [failing, *peers]
    result = controller.remote(
        {
            "kind": "acquire",
            "handles": [row["handle"] for row in selected],
            "checkpoints": [point, *points],
            "features": features,
        }
    )
    relative = f"evidence/{result['request_id']}/stop-investigation.json"
    audit = {
        "candidate_id": candidate_id,
        "failed_stop": failing,
        "successful_peers": peers,
        "requested_checkpoints": [point, *points],
        "observations": result["evidence"],
    }
    write(controller.root / "agent" / relative, audit)
    receipt = {
        "candidate_id": candidate_id,
        "handle": handle,
        "groups": [row["group"] for row in selected],
        "source_request_id": failing["request_id"],
        "request_id": result["request_id"],
        "later_prefixes_measured": sum(
            row["handle"] == handle and row["checkpoint"] > point for row in result["evidence"]
        ),
        "artifact": relative,
    }
    if any(row["handle"] == handle and row["checkpoint"] == point for row in result["evidence"]):
        controller.state["investigations"].append(receipt)
    return {
        **receipt,
        "prefix_scores": [
            {
                "handle": row["handle"],
                "checkpoint": row["checkpoint"],
                "recall": row["label"]["recall"],
                "native_recall": row["native_recall"],
                "count": row["label"]["result_count"],
                "native_count": row["native_count"],
            }
            for row in result["evidence"]
        ],
    }


def revision_panel(controller, parent_id):
    investigations = [
        row for row in controller.state["investigations"] if row["candidate_id"] == parent_id
    ]
    if not investigations:
        raise ValueError("investigate a measured failed stop from the parent first")
    parent = controller.state["candidates"][parent_id]
    excluded = {r["group"] for r in parent["screen_result"]["quality"]}
    excluded.update(group for row in investigations for group in row["groups"])
    eligible = defaultdict(list)
    for item in controller.development.values():
        if item["group"] not in excluded:
            eligible[item["group"]].append(item["handle"])
    seen = set(controller.state["measured_groups"])
    seed = controller.comparison["seed"]
    chosen = sorted(eligible, key=lambda group: (group in seen, digest([seed, group])))[
        : controller.comparison["screen_groups"]
    ]
    if len(chosen) < 2:
        raise ValueError("too few development groups outside the parent screen and investigation")
    return (
        [handle for group in chosen for handle in sorted(eligible[group])],
        sum(group not in seen for group in chosen),
        [row["request_id"] for row in investigations],
    )


def review_abstention(state, disposition):
    needs_revision = (
        disposition["status"] == "abstained"
        and not disposition["resource_exit"]
        and not state["revisions"]
    )
    if needs_revision and any(
        row["family"] == family and bad_stop(row)
        for candidate in state["candidates"].values()
        for result, family in candidate_measurements(candidate)
        for row in result["quality"]
    ):
        raise ValueError(
            "A measured failure remains to learn from. Call investigate_stop, then "
            "evaluate_revision with a changed policy before voluntary abstention."
        )
    disposition["targeted_investigations"] = len(state["investigations"])
    disposition["evaluated_revisions"] = len(state["revisions"])
