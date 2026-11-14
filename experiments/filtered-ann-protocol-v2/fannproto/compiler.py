"""Emit deterministic masks and null-safe C decisions; no policy fitting."""

from fannagent.store import digest

from .policy import PROFILE, observation_plan, rule_hash, validate


def compile_programs(programs):
    """programs: [{arm,policy,force_continue}]; arm20..59 is versioned v2 only."""
    if not 1 <= len(programs) <= 40:
        raise ValueError("one..40 bounded program bindings")
    arms = set()
    lines = ["/* Deterministic v2 DSL compiler. No labels/IDs/timings are runtime inputs. */"]
    bindings = []
    for entry in programs:
        if (
            set(entry) != {"arm", "policy", "force_continue"}
            or type(entry["arm"]) is not int
            or not 20 <= entry["arm"] <= 59
            or entry["arm"] in arms
            or type(entry["force_continue"]) is not bool
        ):
            raise ValueError("invalid arm binding")
        arms.add(entry["arm"])
        p = validate(entry["policy"])
        bindings.append(
            {**entry, "rule_hash": rule_hash(p), "observation_plan": observation_plan(p)}
        )
    lines += [
        "static bool V2ArmDeclared(int arm) { return "
        + " || ".join("arm == " + str(a) for a in sorted(arms))
        + "; }",
        "static int V2Mask(int arm, int filter, int cp) {",
    ]
    for e in bindings:
        for f, points in e["observation_plan"].items():
            t = -1 if f == "unfiltered" else int(f[5:])
            for cp, mask in points.items():
                if mask:
                    lines.append(
                        f" if (arm == {e['arm']} && filter == {t} && cp == {cp}) return {mask};"
                    )
    lines += [
        " return 0;",
        "}",
        "static bool V2ForceContinue(int arm) { return "
        + (
            " || ".join("arm == " + str(e["arm"]) for e in bindings if e["force_continue"])
            or "false"
        )
        + "; }",
        "static bool V2Decision(int arm,int filter,int cp,int count,d"
        "ouble tenth,double gap,int turnover,bool full,bool hasgap,bo"
        "ol hasturn) {",
    ]
    names = {
        "qualifying_count": "count",
        "tenth_distance": "tenth",
        "frontier_gap": "gap",
        "top10_new_since_previous": "turnover",
    }
    availability = {
        "tenth_distance": "full",
        "frontier_gap": "hasgap",
        "top10_new_since_previous": "hasturn",
    }
    for e in bindings:
        for f, clauses in e["policy"]["rules"].items():
            t = -1 if f == "unfiltered" else int(f[5:])
            for c in clauses:
                tests = [f"arm == {e['arm']}", f"filter == {t}", f"cp == {c['cp']}"]
                for feature, op, value in c["conditions"]:
                    if feature in availability:
                        tests.append(availability[feature])
                    tests.append(
                        f"{names[feature]} {op} "
                        + (str(value) if type(value) is int else float(value).hex())
                    )
                lines.append(" if (" + " && ".join(tests) + ") return true;")
    lines += [" return false;", "}"]
    source = "\n".join(lines) + "\n"
    manifest = {
        "schema": "filtered-ann-compiler.v2",
        "profile": PROFILE.describe(),
        "bindings": bindings,
        "source_hash": __import__("hashlib").sha256(source.encode()).hexdigest(),
        "partial_stops": True,
        "exact_serving_calls": 0,
        "mask_semantics": "previous scheduled checkpoint dependency; predicate with no "
        "clause has zero observation mask",
    }
    manifest["artifact_hash"] = digest(manifest)
    return source, manifest
