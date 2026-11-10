"""Fixed conditioning, fresh activations, adjacent identical-path AB/BA controls."""

import random
import sys
import time

from pp_common import CANDIDATE, CELLS, CONDITIONING_CALLS, COUNTS, digest, lines, read, save


class NativeSession:
    """Identical plain-native control; wrapper construction/overhead stay charged."""

    def __init__(self, backend, raw, cfg):
        started = time.perf_counter_ns()
        self.backend, self.raw = backend, raw
        self.identity = digest(["plain-native-calibration-v1"])
        self.preparation_ms = (time.perf_counter_ns() - started) / 1e6

    def query(self, q, budget, *, trace=False):
        from execution import native_execute

        started = time.perf_counter_ns()
        result = native_execute(self.backend, budget, q)
        ann_ms = result.latency_ms
        routing_ms = max(0.0, (time.perf_counter_ns() - started) / 1e6 - ann_ms)
        result.metadata.update(
            native_bypass=True,
            requested_composite_hash=self.identity,
            policy_ann_ms=ann_ms,
            routing_ms=routing_ms,
        )
        result.latency_ms += routing_ms
        return result


def policies(package):
    from policy import compose, matched

    raw = read(package / "candidate.json")[CANDIDATE]["policy"]
    native = compose("native-route-control", "continue")
    native["eligible"] = []
    return {
        "candidate": raw,
        "matched-continue": matched(raw),
        "routed-native": native,
        "native": native,
    }


def make_session(arm, backend, raw, cfg):
    from execution import session as original
    from pb_session import session as admission
    from pp_session import session as owned

    variant = arm.split("/")[0].rsplit("-", 1)[0]
    return {"original": original, "owned": owned, "admission": admission, "native": NativeSession}[
        variant
    ](backend, raw, cfg)


def cell_order(qid, block):
    result = CELLS.copy()
    random.Random(int(digest(["calibration-cells-v1", qid]), 16)).shuffle(result)
    return result[::-1] if block % 2 else result


def schedule(qid, block):
    cells = cell_order(qid, block)
    for position, cell in enumerate(cells):
        variant, semantic = cell.split("/")
        initial = (int(digest(["calibration-labels-v1", qid, cell]), 16) + block) % 2
        for round_index in range(2):
            labels = ["a", "b"] if (initial + round_index) % 2 == 0 else ["b", "a"]
            for slot_index, label in enumerate(labels):
                yield {
                    "cell": cell,
                    "cell_position": position,
                    "cell_order_sha256": digest(cells),
                    "round": round_index,
                    "label": label,
                    "label_order": labels,
                    "slot_position": round_index * 2 + slot_index,
                    "arm": variant + "-" + label + "/" + semantic,
                }


def pair_rng(qid, cell, block, round_index, rep):
    return random.Random(
        int(digest(["calibration-pair-v1", qid, cell, block, round_index, rep]), 16)
    )


def proof_key(arm):
    variant, semantic = arm.split("/")
    return variant.rsplit("-", 1)[0] + "/" + semantic


def assert_output(row, proof):
    if (row["policy_ids"], row["policy_distances"]) != (
        proof["policy_ids"],
        proof["policy_distances"],
    ):
        raise RuntimeError("Timed result differs from actual first-stop proof")


def measure(backend, frozen, budget, package, out, block, notify):
    if sys.getprofile() is not None:
        raise RuntimeError("Profiler active during calibration")
    from execution import install_eviction, native_execute, pair, prefix, session
    from fd_execution import qualify
    from fd_policy_tools import predict
    from legacy_execution import write
    from policy import compose, names, route, states

    cfg = read(package / "frozen/experiment.json")
    protocol = read(package / "experiment.json")
    items = lines(package / "frozen/inputs/queries.jsonl")
    evidence = {
        q["query_id"]: q
        for q in read(package / "frozen/inputs/development-evidence.json")["queries"]
    }
    save(
        out / "qualified-features.json",
        qualify(backend, budget, lines(package / "frozen/inputs/qualification.jsonl"), cfg),
    )
    random.Random(protocol["seed"] + block).shuffle(items)
    raw_policies = policies(package)
    retained = warmup_count = slots_count = conditioning_count = 0
    with (
        (out / "references.jsonl").open("x") as refs,
        (out / "proofs.jsonl").open("x") as proofs,
        (out / "pairs.jsonl").open("x") as pairs,
        (out / "warmups.jsonl").open("x") as warmups,
        (out / "conditioning.jsonl").open("x") as conditioners,
        (out / "slots.jsonl").open("x") as slots,
    ):
        for index, item in enumerate(items):
            q = item["query"]
            qid = q["id"]
            budget.reserve("exact_reference")
            truth = backend.exact_reference(q)
            native = native_execute(backend, budget, q)
            score = frozen.score(truth, native)
            if not score["valid"] or len(native.ids) != 10:
                raise RuntimeError("Invalid ordinary-native reference")
            traced = session(backend, compose("profile-reference", "continue"), cfg).query(
                q, budget, trace=True
            )
            observed = prefix(traced, names(cfg, "light19"))
            if (
                (traced.ids, traced.distances) != (native.ids, native.distances)
                or observed != states(evidence[qid], "light19", cfg)
                or score["recall"] != evidence[qid]["native_recall"]
            ):
                raise RuntimeError("Pinned native/trajectory reference differs")
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
            write(refs, ref)
            proof_map = {}
            tree_hashes = {}
            for cell in CELLS:
                variant, semantic = cell.split("/")
                raw = raw_policies[semantic]
                s = make_session(variant + "-a/" + semantic, backend, raw, cfg)
                bypass = variant == "native" or route(q) not in raw["eligible"]
                if variant == "native":
                    result = native
                    cp = None
                else:
                    result = s.query(q, budget, trace=True)
                    cp = None if bypass else predict(raw["tree"], observed, backend.runtime_profile)
                    if not bypass:
                        if prefix(result, names(cfg, "light19")) != (
                            observed if cp is None else observed[:cp]
                        ):
                            raise RuntimeError("Actual first-stop prefix differs")
                        if (result.metadata["stop_reason"] == "policy_stop") != (cp is not None):
                            raise RuntimeError("Actual first-stop acknowledgement differs")
                        tree_hashes[cell] = backend.validate_policy(raw["tree"]).policy_hash
                if (bypass or cp is None) and (result.ids, result.distances) != (
                    native.ids,
                    native.distances,
                ):
                    raise RuntimeError("Native/continue result differs")
                proof = {
                    "query_id": qid,
                    "cell": cell,
                    "checkpoint": cp,
                    "native_bypass": bypass,
                    "composite_hash": s.identity,
                    "policy_ids": result.ids,
                    "policy_distances": result.distances,
                    "prefix_sha256": None
                    if bypass
                    else digest(prefix(result, names(cfg, "light19"))),
                }
                proof_map[cell] = proof
                write(proofs, proof)
            for meta in schedule(qid, block):
                cell = meta["cell"]
                raw = raw_policies[cell.split("/")[1]]
                proof = proof_map[cell]
                bypass = proof["native_bypass"]
                started = time.perf_counter_ns()
                install_eviction(backend, budget)
                backend._policies.clear()
                installed = backend._installed
                for conditioner in range(CONDITIONING_CALLS):
                    t0 = time.perf_counter_ns()
                    result = native_execute(backend, budget, q)
                    t1 = time.perf_counter_ns()
                    if (result.ids, result.distances) != (
                        ref["native_ids"],
                        ref["native_distances"],
                    ):
                        raise RuntimeError("Conditioning changed native output")
                    write(
                        conditioners,
                        {
                            **meta,
                            "block": block,
                            "query_id": qid,
                            "conditioner": conditioner,
                            "latency_ms": result.latency_ms,
                            "outer_ms": (t1 - t0) / 1e6,
                            "started_ns": t0,
                            "finished_ns": t1,
                            "output_sha256": digest([result.ids, result.distances]),
                        },
                    )
                    conditioning_count += 1
                conditioned = time.perf_counter_ns()
                if backend._policies.entries or backend._installed != installed:
                    raise RuntimeError("Native conditioning prepared/installed a policy")
                constructor_started = time.perf_counter_ns()
                s = make_session(meta["arm"], backend, raw, cfg)
                constructor_finished = time.perf_counter_ns()
                if (
                    backend._policies.entries
                    or backend._installed != installed
                    or s.identity != proof["composite_hash"]
                ):
                    raise RuntimeError("Constructor warmed policy state or changed identity")
                first_preparation = s.preparation_ms
                for rep in range(5):
                    if not bypass and (backend._installed == tree_hashes[cell]) != (rep > 0):
                        raise RuntimeError("Fresh activation/reuse installation state differs")
                    pair_started = time.perf_counter_ns()
                    row = pair(
                        frozen,
                        backend,
                        budget,
                        q,
                        truth,
                        s,
                        pair_rng(qid, cell, block, meta["round"], rep),
                        {
                            **meta,
                            "block": block,
                            "pass": "primary",
                            "kind": "candidate" if cell.endswith("/candidate") else "control",
                            "regime": "activation-cold" if rep == 0 else "reused-warm",
                            "repetition": 0 if rep == 0 else rep - 2,
                        },
                        rep == 0,
                    )
                    row.update(
                        pair_started_ns=pair_started, pair_finished_ns=time.perf_counter_ns()
                    )
                    assert_output(row, proof)
                    write(warmups if rep == 1 else pairs, row)
                    retained += rep != 1
                    warmup_count += rep == 1
                write(
                    slots,
                    {
                        **meta,
                        "block": block,
                        "query_id": qid,
                        "started_ns": started,
                        "conditioned_ns": conditioned,
                        "constructor_started_ns": constructor_started,
                        "constructor_finished_ns": constructor_finished,
                        "finished_ns": time.perf_counter_ns(),
                        "preparation_ms": first_preparation,
                        "conditioning_calls": CONDITIONING_CALLS,
                        "cache_empty_after_conditioning": True,
                        "cache_empty_after_constructor": True,
                        "installation_unchanged_until_first_pair": True,
                    },
                )
                slots_count += 1
            notify(
                "conditioned_activation_crossover",
                query=index + 1,
                total=len(items),
                searches=budget.calls,
            )
    if (
        budget.calls != COUNTS["searches_per_block"]
        or retained != COUNTS["retained_pairs_per_block"]
        or warmup_count != COUNTS["warmups_per_block"]
        or slots_count != COUNTS["slots_per_block"]
        or conditioning_count != COUNTS["conditioning_searches_per_block"]
        or budget.control_installations != COUNTS["control_evictions_per_block"]
    ):
        raise RuntimeError("Calibration schedule accounting differs")
    return {
        "retained_pairs": retained,
        "warmup_pairs": warmup_count,
        "conditioning_searches": conditioning_count,
        "slots": slots_count,
        "diagnostic_pairs": 0,
    }
