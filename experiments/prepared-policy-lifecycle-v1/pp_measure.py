"""Original/owned paired execution, then separate diagnostic-only profiles."""

import random
import sys

from pp_common import CANDIDATE, COUNTS, digest, lines, read, save
from pp_profile import ProfiledSession, Profiles


def arms(package):
    from policy import compose, matched

    raw = read(package / "candidate.json")[CANDIDATE]["policy"]
    native = compose("native-route-control", "continue")
    native["eligible"] = []
    semantic = [
        ("candidate", raw, "candidate"),
        ("matched-continue", matched(raw), "matched"),
        ("routed-native", native, "native-control"),
    ]
    return [
        (variant + "/" + name, raw, kind)
        for name, raw, kind in semantic
        for variant in ("original", "owned")
    ]


def make_session(arm, backend, raw, cfg):
    from execution import session as original
    from pp_session import session as owned

    return (owned if arm.startswith("owned/") else original)(backend, raw, cfg)


def ordered_arms(package, query_id, block):
    result = arms(package)
    semantic = ["candidate", "matched-continue", "routed-native"]
    random.Random(int(digest(["prepared-arms-v1", query_id]), 16)).shuffle(semantic)
    offset = block % len(semantic)
    semantic = semantic[offset:] + semantic[:offset]
    ordered = []
    for name in semantic:
        pair = [r for r in result if r[0].endswith("/" + name)]
        reverse = (int(digest(["variant-order-v1", query_id, name]), 16) + block) % 2
        ordered.extend(pair[::-1] if reverse else pair)
    return ordered


def assert_output(row, proof):
    if (row["policy_ids"], row["policy_distances"]) != (
        proof["policy_ids"],
        proof["policy_distances"],
    ):
        raise RuntimeError("Timed result differs from same-query first-stop proof")


def active(backend, raw, repetition, bypass):
    if not bypass:
        installed = backend._installed == backend.validate_policy(raw["tree"]).policy_hash
        if installed != (repetition > 0):
            raise RuntimeError("Activation/reuse state differs")


def measure(backend, frozen, budget, package, out, block, notify):
    if sys.getprofile() is not None:
        raise RuntimeError("An active profiler would contaminate primary timing")
    from execution import install_eviction, native_execute, pair, prefix, session
    from fd_execution import qualify
    from fd_policy_tools import predict
    from legacy_execution import write
    from policy import compose, names, route, states

    cfg = read(package / "experiment.json")
    source = package / "frozen"
    source_cfg = read(source / "experiment.json")
    items = lines(source / "inputs/queries.jsonl")
    evidence = {
        q["query_id"]: q for q in read(source / "inputs/development-evidence.json")["queries"]
    }
    getters = qualify(backend, budget, lines(source / "inputs/qualification.jsonl"), source_cfg)
    save(out / "qualified-features.json", getters)
    random.Random(cfg["seed"] + block).shuffle(items)
    rng = random.Random(cfg["seed"] + block)
    truths, references, proof_map = {}, {}, {}
    retained = 0
    with (
        (out / "pairs.jsonl").open("x") as pairs,
        (out / "warmups.jsonl").open("x") as warms,
        (out / "proofs.jsonl").open("x") as proofs,
        (out / "references.jsonl").open("x") as refs,
    ):
        for index, item in enumerate(items):
            q = item["query"]
            qid = q["id"]
            budget.reserve("exact_reference")
            truth = backend.exact_reference(q)
            truths[qid] = truth
            native = native_execute(backend, budget, q)
            score = frozen.score(truth, native)
            if not score["valid"] or len(native.ids) != 10:
                raise RuntimeError("Invalid native reference")
            traced = session(backend, compose("profile-reference", "continue"), source_cfg).query(
                q, budget, trace=True
            )
            observed = prefix(traced, names(source_cfg, "light19"))
            if (traced.ids, traced.distances) != (native.ids, native.distances):
                raise RuntimeError("Continue trace differs from native")
            if (
                observed != states(evidence[qid], "light19", source_cfg)
                or score["recall"] != evidence[qid]["native_recall"]
            ):
                raise RuntimeError("Frozen development trajectory/native quality changed")
            ref = {
                "query_id": qid,
                "group": item["group"],
                "states": observed,
                "native_ids": native.ids,
                "native_distances": native.distances,
                "native_recall": score["recall"],
                "truth_strict": sorted(truth.strictly_better),
                "truth_ties": sorted(truth.boundary_ties),
                "truth_k": truth.effective_k,
            }
            references[qid] = ref
            write(refs, ref)
            for arm, raw, kind in ordered_arms(package, qid, block):
                s = make_session(arm, backend, raw, source_cfg)
                bypass = route(q) not in raw["eligible"]
                result = s.query(q, budget, trace=True)
                cp = None if bypass else predict(raw["tree"], observed, backend.runtime_profile)
                if not bypass:
                    if prefix(result, names(source_cfg, "light19")) != (
                        observed if cp is None else observed[:cp]
                    ):
                        raise RuntimeError("Actual stop prefix differs")
                    if (result.metadata["stop_reason"] == "policy_stop") != (cp is not None):
                        raise RuntimeError("Actual stop acknowledgement differs")
                if (bypass or cp is None) and (result.ids, result.distances) != (
                    native.ids,
                    native.distances,
                ):
                    raise RuntimeError("Native/continue result differs")
                proof = {
                    "query_id": qid,
                    "arm": arm,
                    "checkpoint": cp,
                    "native_bypass": bypass,
                    "composite_hash": s.identity,
                    "policy_ids": result.ids,
                    "policy_distances": result.distances,
                    "prefix_sha256": None
                    if bypass
                    else digest(prefix(result, names(source_cfg, "light19"))),
                }
                proof_map[(qid, arm)] = proof
                write(proofs, proof)
                install_eviction(backend, budget)
                backend._policies.clear()
                s = make_session(arm, backend, raw, source_cfg)
                for repetition in range(5):
                    active(backend, raw, repetition, bypass)
                    row = pair(
                        frozen,
                        backend,
                        budget,
                        q,
                        truth,
                        s,
                        rng,
                        {
                            "block": block,
                            "arm": arm,
                            "kind": kind,
                            "pass": "primary",
                            "regime": "activation-cold" if repetition == 0 else "reused-warm",
                            "repetition": 0 if repetition == 0 else repetition - 2,
                        },
                        repetition == 0,
                    )
                    assert_output(row, proof)
                    write(warms if repetition == 1 else pairs, row)
                    retained += repetition != 1
            notify(
                "unprofiled_measurement", query=index + 1, total=len(items), searches=budget.calls
            )
    if budget.calls != COUNTS["main_searches"] or retained != COUNTS["retained_pairs_per_block"]:
        raise RuntimeError("Primary schedule accounting differs")
    profiles = Profiles()
    diagnostic = [i for i in items if i["group"] in cfg["diagnostic_groups"]]
    diag_retained = 0
    with (
        (out / "diagnostic-pairs.jsonl").open("x") as pairs,
        (out / "diagnostic-warmups.jsonl").open("x") as warms,
    ):
        for index, item in enumerate(diagnostic):
            q = item["query"]
            qid = q["id"]
            stratum = route(q)
            for arm, raw, kind in ordered_arms(package, qid, block):
                install_eviction(backend, budget)
                backend._policies.clear()
                s = profiles.call(
                    arm + "/" + stratum + "/prepare", make_session, arm, backend, raw, source_cfg
                )
                wrapped = ProfiledSession(s, profiles, arm, stratum)
                bypass = route(q) not in raw["eligible"]
                for repetition in range(5):
                    wrapped.phase = (
                        "activation"
                        if repetition == 0
                        else "warmup"
                        if repetition == 1
                        else "reuse"
                    )
                    active(backend, raw, repetition, bypass)
                    row = pair(
                        frozen,
                        backend,
                        budget,
                        q,
                        truths[qid],
                        wrapped,
                        rng,
                        {
                            "block": block,
                            "arm": arm,
                            "kind": kind,
                            "pass": "diagnostic",
                            "regime": "activation-cold" if repetition == 0 else "reused-warm",
                            "repetition": 0 if repetition == 0 else repetition - 2,
                        },
                        repetition == 0,
                    )
                    assert_output(row, proof_map[(qid, arm)])
                    write(warms if repetition == 1 else pairs, row)
                    diag_retained += repetition != 1
            notify(
                "diagnostic_profiling",
                query=index + 1,
                total=len(diagnostic),
                searches=budget.calls,
            )
    if (
        budget.calls != COUNTS["searches_per_block"]
        or diag_retained != COUNTS["diagnostic_pairs_per_block"]
    ):
        raise RuntimeError("Diagnostic accounting differs")
    if budget.control_installations != COUNTS["control_evictions_per_block"]:
        raise RuntimeError("Control SQL accounting differs")
    save(out / "profiles.json", profiles.serialize())
    return {"retained_pairs": retained, "diagnostic_pairs": diag_retained}
