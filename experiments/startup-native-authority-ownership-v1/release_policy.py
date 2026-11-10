"""Offline release classification. No scheduler, authority issuer, or grant exists."""

import math

SPENT = frozenset({"21459623", "21470341", "21542975", "21595967"})
QUALIFICATION_MISSING = (
    "fresh explicit authorization and unspent allowance",
    "qualified allocation/binding/owned-group backend",
    "authoritative job-private disk mount/device/quota/ownership evidence",
    "persistent return quota and bounded durable-return evidence",
    "qualified native host/guest publication and independent exit observation",
)
DOWNSTREAM_MISSING = (
    "complete exact-image non-emulated x86_64 main128+128 and A3276+276 outcomes",
    "complete native CPU120/180 screen with all60 samples",
    "continuous aggregate memory ancestry/limits/peaks/events and unchanged4GiB margin",
    "complete native shutdown, source preservation and bounded raw return",
)


def completed(exit_observation, result):
    """Artifacts alone cannot establish completion; observer authority is external.

    This numerical consistency check does not authenticate its input. Current
    review supplies no native observer authority and always returns HOLD below.
    """
    keys = ("started", "publication_started", "finished", "post_started", "post_deadline")
    if not isinstance(result, dict) or not isinstance(exit_observation, dict):
        return False
    if any(type(result.get(k)) not in (int, float) or not math.isfinite(result[k]) for k in keys):
        return False
    exit_time = exit_observation.get("observed_finished")
    return (
        result.get("status") == "pass"
        and type(exit_observation.get("exit_code")) is int
        and exit_observation["exit_code"] == 0
        and type(exit_time) in (int, float)
        and math.isfinite(exit_time)
        and 0
        <= result["started"]
        <= result["post_started"]
        <= result["publication_started"]
        <= result["finished"]
        <= exit_time
        < result["post_deadline"]
        <= min(result["post_started"] + 240, result["started"] + 3480)
    )


def review(evidence):
    """Current closed review cannot be promoted by self-asserted records."""
    if not isinstance(evidence, dict):
        raise ValueError("Review evidence dictionary required")
    return {
        "status": "HOLD",
        "qualification_handoff": {"status": "HOLD", "missing": list(QUALIFICATION_MISSING)},
        "resource_and_B2f": {"status": "HOLD", "missing": list(DOWNSTREAM_MISSING)},
        "local_completion_consistent": completed(
            evidence.get("exit_observation"), evidence.get("host_result")
        ),
        "native_authority_implemented": False,
        "native_release": False,
        "fresh_allowance_issued": False,
        "spent_allowances_reused": False,
        "Torch_jobs": 0,
        "ANN_searches": 0,
        "exact_searches": 0,
    }
