"""Fixed qualification, expense preview, scoped quality and complementary blocks."""

import hashlib
import math
import random
import statistics
import time

from pa_common import CELLS, CRITERIA, SEED, context, digest, inventory, read, save
from pa_interface import audit, freeze
from pa_stats import score_result
from pa_trace import category


def ordered(items):
    out = list(items)
    random.Random(SEED).shuffle(out)
    return out


def schedule(qid, block):
    cells = CELLS.copy()
    random.Random(int(digest([SEED, "cells", qid]), 16)).shuffle(cells)
    if block:
        cells.reverse()
    for pos, cell in enumerate(cells):
        flip = bool(int(digest([SEED, "labels", qid, cell]), 16) % 2) ^ bool(block)
        first = ["b", "a"] if flip else ["a", "b"]
        for round_ in range(2):
            for within, label in enumerate(first if round_ == 0 else first[::-1]):
                yield dict(
                    cell=cell, cell_position=pos, round=round_, label=label, within_round=within
                )


def order_manifest(items):
    inventory(items)
    ids = [i["query"]["id"] for i in ordered(items)]
    preview = sorted(
        ids,
        key=lambda x: (
            hashlib.sha256(("partial-ann.v1/preview/20261026/" + x).encode()).hexdigest(),
            x,
        ),
    )[:24]
    return dict(
        seed=SEED,
        quality_order=ids,
        preview_order=preview,
        timing_order={"0": ids, "1": ids[::-1]},
        slots={str(b): {q: list(schedule(q, b)) for q in ids} for b in (0, 1)},
    )


def truth_record(t):
    return dict(
        truth_strict=sorted(t.strictly_better),
        truth_ties=sorted(t.boundary_ties),
        truth_k=t.effective_k,
    )


def record_result(result, truth, q, eligibility):
    if getattr(result, "evidence", None) or any(
        (getattr(result, "metadata", None) or {}).get(k)
        for k in ("policy_applied", "policy_fallback", "policy_runtime_error")
    ):
        raise RuntimeError("Unexpected policy/trace result")
    ids = list(result.ids)
    distances = list(result.distances)
    strict = set(truth["truth_strict"])
    ties = set(truth["truth_ties"])
    k = truth["truth_k"]
    votes = eligibility["votes"]
    if len(ids) != 10 or any(type(i) is not int or not 0 <= i < len(votes) for i in ids):
        raise RuntimeError("Invalid result IDs/length")
    violations = sum(votes[i] is None or votes[i] < 108 for i in set(ids))
    duplicates = len(ids) - len(set(ids))
    recall = (len(set(ids) & strict) + min(k - len(strict), len(set(ids) & ties))) / k
    r = dict(
        ids=ids,
        distances=distances,
        recall=recall,
        valid=not violations and not duplicates,
        returned_count=len(ids),
        duplicate_count=duplicates,
        predicate_violation_count=violations,
    )
    score_result(r, truth, q, eligibility)
    if not r["valid"]:
        raise RuntimeError("Invalid native output is an acquisition failure")
    return r


def equivalent(value, expected):
    if (
        not value["valid"]
        or not expected["valid"]
        or value["recall"] != expected["recall"]
        or dict(zip(value["ids"], value["distances"]))
        != dict(zip(expected["ids"], expected["distances"]))
    ):
        raise RuntimeError("Repeated native ID-distance mapping changed")


def admit(snapshot, items):
    inventory(items)
    out = []
    mapping = snapshot.field_map
    if mapping.get("m_000000") != "total_votes":
        raise RuntimeError("Logical metadata mapping differs")
    for i in items:
        q = snapshot.query(i["query"])
        context(q)
        if q != i["query"]:
            raise RuntimeError("Validated query semantics differ")
        out.append(dict(group=i["group"], query=freeze(q)))
    return out


def call(reader, q, truth, budget, operation, eligibility, emit, **meta):
    start = time.perf_counter_ns()
    value = None
    reserved = budget.calls
    try:
        r = reader.native(q, budget, operation)
        end = time.perf_counter_ns()
        value = record_result(r, truth, q, eligibility)
        if not math.isfinite(r.latency_ms) or r.latency_ms < 0:
            raise RuntimeError("Invalid SQL timer")
        row = dict(
            operation=operation,
            query_id=q["id"],
            group=q["id"].rsplit("-", 1)[0],
            reader=reader.identity,
            cell=reader.mode,
            stage=budget.stage,
            start_ns=start,
            end_ns=end,
            outer_ms=(end - start) / 1e6,
            sql_ms=r.latency_ms,
            result=value,
            **meta,
        )
        emit("searches", row)
        return row
    except BaseException as e:
        if budget.calls > reserved:
            emit(
                "searches",
                dict(
                    operation=operation,
                    query_id=q["id"],
                    reader=reader.identity,
                    cell=reader.mode,
                    stage=budget.stage,
                    start_ns=start,
                    end_ns=time.perf_counter_ns(),
                    error=dict(type=type(e).__name__, message=str(e)),
                    **meta,
                ),
            )
        raise


def exact(reader, q, budget, operation, emit):
    start = time.perf_counter_ns()
    reserved = budget.calls
    try:
        t = reader.exact(q, budget, operation)
        end = time.perf_counter_ns()
        value = truth_record(t)
        emit(
            "searches",
            dict(
                operation=operation,
                query_id=q["id"],
                reader=reader.identity,
                cell=reader.mode,
                stage=budget.stage,
                start_ns=start,
                end_ns=end,
                outer_ms=(end - start) / 1e6,
                truth=value,
            ),
        )
        return value
    except BaseException as e:
        if budget.calls > reserved:
            emit(
                "searches",
                dict(
                    operation=operation,
                    query_id=q["id"],
                    reader=reader.identity,
                    stage=budget.stage,
                    start_ns=start,
                    end_ns=time.perf_counter_ns(),
                    error=dict(type=type(e).__name__, message=str(e)),
                ),
            )
        raise


def rollback(reader):
    with category("observer"):
        try:
            with reader.connection.transaction():
                reader.connection.execute("SELECT 1/0", prepare=False)
        except Exception as e:
            if getattr(e, "sqlstate", None) != "22012":
                raise
        else:
            raise RuntimeError("Expected failed transaction missing")
        if reader.connection.execute("SELECT 1", prepare=False).fetchone()[0] != 1:
            raise RuntimeError("Rollback failed")
    reader.close()


def qualify(factory, reference, items, pins, eligibility, budget, emit):
    q = items[0]["query"]
    pin = pins[q["id"]]
    t = exact(reference, q, budget, "qualification_exact", emit)
    if t != {k: pin[k] for k in t}:
        raise RuntimeError("Pinned fixture truth differs")
    old = factory.create("partial640", "qualification-partial-old")
    baseline = call(reference, q, t, budget, "qualification_native640", eligibility, emit, step=1)[
        "result"
    ]
    equivalent(baseline, pin["original640"])
    candidate = call(old, q, t, budget, "qualification_partial640", eligibility, emit, step=2)[
        "result"
    ]
    for step, r in [(3, reference), (4, old)]:
        v = call(r, q, t, budget, "qualification_" + r.mode, eligibility, emit, step=step)["result"]
        equivalent(v, baseline if r.mode == "native640" else candidate)
    plans = {"before": {r.mode: factory.observer.plan(r, q) for r in [reference, old]}}
    settings = {"before": {r.mode: audit(r) for r in [reference, old]}}
    rollback(old)
    before = budget.calls
    try:
        old.native(q, budget, "qualification_partial640")
    except RuntimeError:
        pass
    else:
        raise RuntimeError("Closed reader accepted")
    if budget.calls != before:
        raise RuntimeError("Closed handle consumed search")
    rollback(reference)
    before = budget.calls
    try:
        reference.native(q, budget, "qualification_native640")
    except RuntimeError:
        pass
    else:
        raise RuntimeError("Closed baseline accepted")
    if budget.calls != before:
        raise RuntimeError("Closed baseline consumed search")
    reference = factory.create("native640", "native-reference")
    candidate_reader = factory.create("partial640", "partial-reference")
    equivalent(
        call(candidate_reader, q, t, budget, "qualification_partial640", eligibility, emit, step=5)[
            "result"
        ],
        candidate,
    )
    if exact(reference, q, budget, "qualification_exact", emit) != t:
        raise RuntimeError("Truth changed after rollback")
    equivalent(
        call(reference, q, t, budget, "qualification_native640", eligibility, emit, step=6)[
            "result"
        ],
        baseline,
    )
    equivalent(
        call(reference, q, t, budget, "qualification_native640", eligibility, emit, step=7)[
            "result"
        ],
        baseline,
    )
    equivalent(
        call(candidate_reader, q, t, budget, "qualification_partial640", eligibility, emit, step=8)[
            "result"
        ],
        candidate,
    )
    plans["after"] = {r.mode: factory.observer.plan(r, q) for r in [reference, candidate_reader]}
    settings["after"] = {r.mode: audit(r) for r in [reference, candidate_reader]}
    return (
        dict(
            status="passed",
            query_id=q["id"],
            truth=t,
            plans=plans,
            settings=settings,
            rollback_both_cells=True,
            closed_handles_rejected=True,
            explicit_recovery=True,
        ),
        reference,
        candidate_reader,
    )


def preview_decision(rows):
    if len(rows) != 24 or len({r["query_id"] for r in rows}) != 24:
        raise ValueError("Incomplete preview")
    ratios = [r["partial640_ms"] / r["native640_ms"] for r in rows]
    gaps = [r["partial640_ms"] - r["native640_ms"] for r in rows]
    result = dict(
        pairs=24,
        median_ratio=statistics.median(ratios),
        mean_gap_ms=statistics.mean(gaps),
        slower_pairs=sum(g > 0 for g in gaps),
    )
    result["stop"] = (
        result["median_ratio"] >= 2
        and result["mean_gap_ms"] >= 0.10
        and result["slower_pairs"] >= 20
    )
    result["positive_acceptance"] = False
    return result


def quality_report(refs):
    import numpy as np

    if len(refs) != 200 or len({r["group"] for r in refs}) != 200:
        raise ValueError("Incomplete quality inventory")
    for r in refs:
        if set(r["outcomes"]) != set(CELLS) or not all(
            v["valid"] and v["returned_count"] == 10 for v in r["outcomes"].values()
        ):
            raise ValueError("Invalid reference output")
    values = np.asarray(
        [
            r["outcomes"]["partial640"]["recall"] - r["outcomes"]["native640"]["recall"]
            for r in sorted(refs, key=lambda r: r["group"])
        ]
    )
    rng = np.random.default_rng(CRITERIA["bootstrap_seed"])
    boot = np.empty(CRITERIA["bootstrap_samples"])
    for i in range(0, len(boot), 128):
        count = min(128, len(boot) - i)
        boot[i : i + count] = values[rng.integers(0, 200, size=(count, 200))].mean(axis=1)
    ci = np.quantile(boot, [0.025, 0.975]).tolist()
    means = {c: float(np.mean([r["outcomes"][c]["recall"] for r in refs])) for c in CELLS}
    checks = dict(
        both_native_floors=all(v >= 0.95 for v in means.values()),
        development_reserve=ci[0] >= -0.0025,
    )
    return dict(
        context="votes108",
        cases=200,
        independent_vectors=200,
        mean_recall=means,
        recall_delta=float(values.mean()),
        recall_delta_ci95=ci,
        checks=checks,
        **{"pass": all(checks.values())},
        final_margin_diagnostic_only=ci[0] >= -0.005,
        independent_confirmation=False,
    )


def measure(factory, reference, budget, package, out, items, notify, emit, checkpoint):
    pins = read(package / "baseline-results.json")
    eligibility = read(package / "eligibility.json")
    order = read(package / "order.json")
    byid = {i["query"]["id"]: i for i in items}
    budget.enter("qualification_preview")
    notify("native_qualification")
    q, reference, partial = qualify(factory, reference, items, pins, eligibility, budget, emit)
    save(out / "qualification.json", q)
    checkpoint()
    main = {"native640": reference, "partial640": partial}
    preview = []
    for n, qid in enumerate(order["preview_order"]):
        q = byid[qid]["query"]
        truth = pins[qid]
        retained = {c: [] for c in CELLS}
        for r in main.values():
            factory.observer.plan(r, q)
        for c in CELLS if n % 2 == 0 else CELLS[::-1]:
            call(
                main[c],
                q,
                truth,
                budget,
                "preview_conditioning",
                eligibility,
                emit,
                preview_index=n,
                part="conditioning",
            )
        for c in CELLS:
            call(
                main[c],
                q,
                truth,
                budget,
                "preview_warmup",
                eligibility,
                emit,
                preview_index=n,
                part="warmup",
            )
        for position, c in enumerate(
            ["native640", "partial640", "partial640", "native640"]
            if n % 2 == 0
            else ["partial640", "native640", "native640", "partial640"]
        ):
            row = call(
                main[c],
                q,
                truth,
                budget,
                "preview_measurement",
                eligibility,
                emit,
                preview_index=n,
                part="retained",
                preview_position=position,
            )
            retained[c].append(row["outer_ms"])
        for r in main.values():
            factory.observer.plan(r, q)
        preview.append(
            dict(query_id=qid, **{c + "_ms": statistics.mean(retained[c]) for c in CELLS})
        )
        notify("cost_preview", cases=n + 1)
    futility = preview_decision(preview)
    save(out / "preview.json", dict(pairs=preview, decision=futility))
    checkpoint()
    if futility["stop"]:
        return dict(outcome="closed_cost_futility", quality_pass=None, completed_temporal_blocks=0)
    budget.enter("quality")
    refs = {}
    for n, qid in enumerate(order["quality_order"]):
        item = byid[qid]
        q = item["query"]
        for r in main.values():
            factory.observer.plan(r, q)
        truth = exact(reference, q, budget, "reference_exact", emit)
        if truth != {k: pins[qid][k] for k in truth}:
            raise RuntimeError("Fresh full truth differs from pinned evidence")
        outcomes = {
            c: call(
                main[c], q, truth, budget, "reference_" + c, eligibility, emit, quality_index=n
            )["result"]
            for c in CELLS
        }
        equivalent(outcomes["native640"], pins[qid]["original640"])
        for r in main.values():
            factory.observer.plan(r, q)
        row = dict(query_id=qid, group=item["group"], **truth, outcomes=outcomes)
        emit("references", row)
        refs[qid] = row
        notify("quality_references", cases=n + 1)
    quality = quality_report(list(refs.values()))
    save(out / "quality.json", quality)
    save(out / "quality-settings.json", {c: audit(r) for c, r in main.items()})
    checkpoint()
    if not quality["pass"]:
        return dict(
            outcome="closed_negative_quality", quality_pass=False, completed_temporal_blocks=0
        )
    arms = {(c, label): factory.create(c, c + "-" + label) for c in CELLS for label in ["a", "b"]}
    budget.enter("formal")
    allreaders = [*main.values(), *arms.values()]
    for block in range(2):
        blockstart = time.perf_counter_ns()
        before = {r.identity: audit(r) for r in allreaders}
        for n, qid in enumerate(order["timing_order"][str(block)]):
            q = byid[qid]["query"]
            ref = refs[qid]
            for r in allreaders:
                factory.observer.plan(r, q)
            for slot, meta in enumerate(schedule(qid, block)):
                common = dict(
                    query_id=qid, group=byid[qid]["group"], block=block, slot_index=slot, **meta
                )
                start = time.perf_counter_ns()
                for pos, c in enumerate(CELLS if (n * 8 + slot) % 2 == 0 else CELLS[::-1]):
                    row = call(
                        main[c],
                        q,
                        ref,
                        budget,
                        "conditioning",
                        eligibility,
                        emit,
                        block=block,
                        slot_index=slot,
                        slot_cell=meta["cell"],
                        conditioning_position=pos,
                    )
                    equivalent(row["result"], ref["outcomes"][c])
                condend = time.perf_counter_ns()
                reader = arms[(meta["cell"], meta["label"])]
                for rep in range(3):
                    row = call(
                        reader,
                        q,
                        ref,
                        budget,
                        "warmup" if rep == 0 else "measurement",
                        eligibility,
                        emit,
                        block=block,
                        slot_index=slot,
                        round=meta["round"],
                        label=meta["label"],
                        repetition=rep,
                        regime="reuse",
                        retained=rep != 0,
                    )
                    equivalent(row["result"], ref["outcomes"][reader.mode])
                emit(
                    "slots",
                    dict(
                        **common,
                        start_ns=start,
                        conditioning_end_ns=condend,
                        end_ns=time.perf_counter_ns(),
                        reader=reader.identity,
                    ),
                )
            for r in allreaders:
                factory.observer.plan(r, q, must_be_cached=True)
            notify("warm_measurement", temporal_block=block, cases=n + 1)
        for c, r in main.items():
            factory.observer.catalog(
                r.connection, c, "after_block_" + str(block), candidate=c == "partial640"
            )
        save(
            out / f"warm-boundary-{block}.json",
            dict(
                block=block,
                start_ns=blockstart,
                end_ns=time.perf_counter_ns(),
                before=before,
                after={r.identity: audit(r) for r in allreaders},
            ),
        )
        checkpoint()
    return dict(outcome="complete_measurement", quality_pass=True, completed_temporal_blocks=2)
