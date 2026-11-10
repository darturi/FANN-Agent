"""Frozen composite validator with explicit owned profile; AST checked locally."""

# ruff: noqa: F841 -- preserve the frozen validator AST, including unused artifact.
from copy import deepcopy

from contract import EARLY, FILTERS, digest
from fd_policy_tools import guard, references
from policy import GROUPS, names


def validate(raw, cfg, PROFILE):
    from fannagent.api import validate_policy

    if type(raw) is not dict or set(raw) != {"version", "name", "eligible", "profile", "tree"}:
        raise ValueError("Composite requires exactly version,name,eligible,profile,tree")
    if (
        raw["version"] != "selective-policy.v1"
        or not isinstance(raw["name"], str)
        or not 1 <= len(raw["name"]) <= 160
    ):
        raise ValueError("Invalid version/name")
    eligible = raw["eligible"]
    if (
        type(eligible) is not list
        or not eligible
        or any(type(s) is not str or s not in FILTERS for s in eligible)
        or len(set(eligible)) != len(eligible)
    ):
        raise ValueError("Choose a nonempty subset of actual query predicates")
    allowed = names(cfg, raw["profile"])
    tree = raw["tree"]
    if (
        type(tree) is not dict
        or set(tree) != {"name", "feature_groups", "root"}
        or tree["feature_groups"] != list(GROUPS[raw["profile"]])
    ):
        raise ValueError("Tree fields/groups differ from selected profile")
    artifact = validate_policy(tree, PROFILE)
    if set(references(tree["root"])) - set(allowed):
        raise ValueError("Unqualified runtime feature")

    def depth(n):
        return 0 if isinstance(n, str) else 1 + max(depth(n["then"]), depth(n["else"]))

    if depth(tree["root"]) > 4:
        raise ValueError("Maximum decision depth including guard is four")
    # A canonical outer guard makes unsampled/missing observations continue.
    root = tree["root"]
    if (
        not isinstance(root, dict)
        or root["else"] != "continue"
        or root != guard(root["then"], EARLY)
    ):
        raise ValueError("Use the canonical availability/checkpoint guard")
    owned = deepcopy(raw)
    owned["eligible"] = [s for s in FILTERS if s in eligible]
    identity = digest(
        {
            "version": owned["version"],
            "eligible": owned["eligible"],
            "profile": owned["profile"],
            "root": tree["root"],
            "feature_groups": tree["feature_groups"],
            "runtime_profile": PROFILE.fingerprint,
        }
    )
    return owned, identity
