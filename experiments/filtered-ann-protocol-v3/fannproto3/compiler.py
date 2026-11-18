"""Compile the public broad-policy format to immutable native VM tables."""

import hashlib

from fannagent.api.broad_policy import DECIDE, FEATURES, compile_graph, validate


def compile_programs(bindings):
    if not 1 <= len(bindings) <= 20:
        raise ValueError("one to twenty broad program bindings required")
    nodes, steps, updates, programs, arms = [], [], [], [], set()
    manifest = []
    for binding in bindings:
        sizes_before = (len(nodes), len(steps), len(updates), len(programs))
        if set(binding) != {"arm", "policy", "force_continue"}:
            raise ValueError("invalid broad binding")
        arm = binding["arm"]
        if type(arm) is not int or not 60 <= arm <= 89 or arm in arms:
            raise ValueError("broad arm must be unique in 60..89")
        if type(binding["force_continue"]) is not bool:
            raise ValueError("force_continue must be Boolean")
        arms.add(arm)
        policy = validate(binding["policy"])
        graph = compile_graph(policy)
        base = len(nodes)
        for code in graph["nodes"]:
            code = list(code)
            if code[0] >= 4:
                code[1:4] = [n + base if n >= 0 else -1 for n in code[1:4]]
            nodes.append(code)
        for name, program in graph["programs"].items():
            point_map = program["steps"]
            if not any(s["mask"] & DECIDE for s in point_map.values()):
                continue
            start = len(steps)
            previous = 0
            for cp in range(program["checkpoints"][-1] + 1):
                point = point_map.get(cp)
                if point is None:
                    steps.append((0, -1, 0, 0, previous))
                    continue
                first_update = len(updates)
                for slot, root in sorted(point["updates"].items(), key=lambda kv: int(kv[0])):
                    updates.append((int(slot), root + base))
                steps.append(
                    (
                        point["mask"],
                        point["root"] + base,
                        first_update,
                        len(updates) - first_update,
                        previous,
                    )
                )
                previous = cp
            programs.append(
                (
                    arm,
                    -1 if name == "unfiltered" else int(name[5:]),
                    start,
                    program["checkpoints"][-1],
                    policy["fuel"],
                    policy["state_slots"],
                    int(binding["force_continue"]),
                )
            )
        sizes_after = (len(nodes), len(steps), len(updates), len(programs))
        storage = sum(
            (b - a) * size
            for a, b, size in zip(sizes_before, sizes_after, (32, 24, 8, 32), strict=True)
        )
        if storage > 4 * 1024 * 1024:
            raise ValueError("compiled policy exceeds four MiB deployment budget")
        manifest.append(
            {
                **binding,
                "policy_hash": graph["policy_hash"],
                "plans": graph["programs"],
                "table_bytes_upper_bound": storage,
            }
        )
    out = [
        "/* Trusted v3 compiler output: data only; no evaluator fields. */",
        "static const V3Node v3Nodes[] = {",
    ]
    for op, a, b, c, value in nodes or [(1, -1, -1, -1, 0.0)]:
        out.append(f" {{{op},{a},{b},{c},{float(value).hex()}}},")
    out += ["};", "static const V3Update v3Updates[] = {"]
    out += [f" {{{a},{b}}}," for a, b in updates or [(-1, -1)]]
    out += ["};", "static const V3Step v3Steps[] = {"]
    out += [" {" + ",".join(map(str, s)) + "}," for s in steps or [(0, -1, 0, 0, 0)]]
    out += ["};", "static const V3Program v3Programs[] = {"]
    out += [" {" + ",".join(map(str, p)) + "}," for p in programs or [(-1, 0, 0, 0, 0, 0, 0)]]
    out += [
        "};",
        "static bool V3ArmDeclared(int arm) { return "
        + " || ".join("arm==" + str(a) for a in sorted(arms))
        + "; }",
    ]
    code = "\n".join(out) + "\n"
    return code, {
        "schema": "fannagent.broad-compiler.v3",
        "bindings": manifest,
        "source_sha256": hashlib.sha256(code.encode()).hexdigest(),
        "features": FEATURES,
        "nodes": len(nodes),
        "programs": len(programs),
        "table_bytes_upper_bound": len(nodes) * 32 + len(steps) * 24 + len(updates) * 8,
        "compiler_semantics": "float64; short circuit; query-local bounded state",
    }
