"""Frozen two-epoch acquisition; no adaptive regimes or treatment benefit test."""

from collections import defaultdict

from pc_common import CELLS, lines, read, save
from pc_results import call, equivalent, exact, quality_report


def role(epoch, cell, slot):
    return f"e{epoch}-{cell}-{slot}"


def events(schedule):
    """Independent immutable search-order specification used by the data verifier."""
    main = {c: c.split("640")[0] + "-reference" for c in CELLS}
    for n, qid in enumerate(schedule["qualification_query_ids"]):
        yield ("qualification_exact", qid, main["native640"], {})
        for rep in range(2):
            for cell in CELLS if (n + rep) % 2 == 0 else CELLS[::-1]:
                yield (
                    "qualification_" + cell,
                    qid,
                    main[cell],
                    dict(fixture=n, fixture_repetition=rep),
                )
    for n, qid in enumerate(schedule["quality_order"]):
        yield ("reference_exact", qid, main["native640"], {})
        for cell in CELLS if n % 2 == 0 else CELLS[::-1]:
            yield ("reference_" + cell, qid, main[cell], dict(quality_index=n))
    for e in (0, 1):
        for name in schedule["epoch_creation_order"][str(e)]:
            cell, slot = name.rsplit("-", 1)
            for n in range(10):
                yield (
                    "priming",
                    schedule["primary_order"][0],
                    role(e, cell, slot),
                    dict(epoch=e, priming_index=n),
                )
        for window in schedule["epoch_window_order"][str(e)]:
            if window not in {"primary", "observer_diagnostic"}:
                continue
            rows = schedule["primary_bursts" if window == "primary" else "diagnostic_bursts"]
            for row in (r for r in rows if r["epoch"] == e):
                primary_order = (
                    schedule["primary_order"] if e == 0 else schedule["primary_order"][::-1]
                )
                meta = dict(
                    epoch=e,
                    window="primary" if window == "primary" else "diagnostic",
                    cell_position=row["cell_position"],
                    physical_slot=row["reader"],
                    within_cell_position=row["within_cell_position"],
                    query_position=primary_order.index(row["query_id"]),
                )
                if window == "primary":
                    meta["label"] = row["label"]
                else:
                    meta.update(
                        observer_mode=row["observer_mode"], mode_position=row["mode_position"]
                    )
                for pos, cell in enumerate(row["conditioning_order"]):
                    yield (
                        "conditioning" if window == "primary" else "diagnostic_conditioning",
                        row["query_id"],
                        main[cell],
                        dict(
                            epoch=e,
                            window=meta["window"],
                            slot_cell=row["cell"],
                            slot_reader=role(e, row["cell"], row["reader"]),
                            conditioning_position=pos,
                            observer_mode=row.get("observer_mode"),
                        ),
                    )
                for rep in range(7):
                    op = "warmup" if rep < 4 else "measurement"
                    if window != "primary":
                        op = "diagnostic_" + op
                    yield (
                        op,
                        row["query_id"],
                        role(e, row["cell"], row["reader"]),
                        dict(
                            **meta,
                            repetition=rep - 3 if rep >= 4 else rep - 4,
                            retained=rep >= 4,
                        ),
                    )


def plan(observer, reader, q, **meta):
    observer.tags = meta
    try:
        packet = observer.plan(reader, q, must_be_cached=meta.get("cached", False))
        if packet["driver"]["psycopg"] != "3.3.6" or any(
            c["generic_plans"] for c in packet["cached"]
        ):
            raise RuntimeError("Unexpected preparation driver/generic plan")
        return packet
    finally:
        observer.tags = {}


def bulk(factory, arms, items, schedule, observer, epoch, boundary):
    observed = defaultdict(dict)
    for spec in schedule["primary_boundary_plan_order"]:
        if (spec["epoch"], spec["boundary"]) != (epoch, boundary):
            continue
        cell, slot = spec["reader"].rsplit("-", 1)
        packet = plan(
            observer,
            arms[cell, slot],
            items[spec["query_id"]]["query"],
            epoch=epoch,
            window="bulk",
            boundary=boundary,
            inspection_position=spec["inspection_position"],
            cached=True,
        )
        observed[spec["query_id"], cell][slot] = {k: v for k, v in packet.items() if k != "charge"}
    if len(observed) != 400 or any(
        set(v) != {"r0", "r1"} or v["r0"] != v["r1"] for v in observed.values()
    ):
        raise RuntimeError("Physical replica plans/parameters/cache counters differ")


def acquire(
    factory,
    main,
    budget,
    package,
    out,
    items,
    observer,
    proc,
    journal,
    notify,
    stage,
    context_snapshot,
):
    schedule = read(package / "SCHEDULE.json")
    pins = read(package / "baseline-results.json")
    oldrefs = {r["query_id"]: r for r in lines(package / "b2d-references.jsonl")}
    eligibility = read(package / "eligibility.json")
    byid = {r["query"]["id"]: r for r in items}

    def search(reader, qid, op, truth, **meta):
        row = call(
            reader,
            byid[qid]["query"],
            truth,
            budget,
            op,
            eligibility,
            journal.emit,
            physical=reader.physical.copy(),
            **meta,
        )
        expected = oldrefs[qid]["outcomes"][reader.mode]
        equivalent(row["result"], expected)
        return row

    for n, qid in enumerate(schedule["qualification_query_ids"]):
        q = byid[qid]["query"]
        for cell in CELLS:
            plan(observer, main[cell], q, window="qualification", boundary="pre", fixture=n)
        truth = exact(main["native640"], q, budget, "qualification_exact", journal.emit)
        if truth != {k: pins[qid][k] for k in truth}:
            raise RuntimeError("Fixture truth changed")
        for rep in range(2):
            for cell in CELLS if (n + rep) % 2 == 0 else CELLS[::-1]:
                search(
                    main[cell],
                    qid,
                    "qualification_" + cell,
                    truth,
                    fixture=n,
                    fixture_repetition=rep,
                )
        for cell in CELLS:
            plan(observer, main[cell], q, window="qualification", boundary="post", fixture=n)
    refs = {}
    for n, qid in enumerate(schedule["quality_order"]):
        q = byid[qid]["query"]
        for cell in CELLS:
            plan(observer, main[cell], q, window="quality", boundary="pre", quality_index=n)
        truth = exact(main["native640"], q, budget, "reference_exact", journal.emit)
        if truth != {k: pins[qid][k] for k in truth}:
            raise RuntimeError("Fresh truth changed")
        outcomes = {
            c: search(main[c], qid, "reference_" + c, truth, quality_index=n)["result"]
            for c in (CELLS if n % 2 == 0 else CELLS[::-1])
        }
        row = dict(query_id=qid, group=byid[qid]["group"], **truth, outcomes=outcomes)
        refs[qid] = row
        journal.emit("references", row)
        for cell in CELLS:
            plan(observer, main[cell], q, window="quality", boundary="post", quality_index=n)
        if (n + 1) % 10 == 0:
            notify("fresh_quality", cases=n + 1)
    quality = quality_report(list(refs.values()))
    save(out / "quality.json", quality)
    journal.checkpoint()
    if not quality["pass"]:
        return dict(outcome="closed_negative_quality", completed_epochs=0, quality_pass=False)

    def burst(spec, arms, diagnostic=False):
        e, qid = spec["epoch"], spec["query_id"]
        primary_order = schedule["primary_order"] if e == 0 else schedule["primary_order"][::-1]
        meta = dict(
            epoch=e,
            window="diagnostic" if diagnostic else "primary",
            cell_position=spec["cell_position"],
            physical_slot=spec["reader"],
            within_cell_position=spec["within_cell_position"],
            query_position=primary_order.index(qid),
        )
        if diagnostic:
            meta.update(observer_mode=spec["observer_mode"], mode_position=spec["mode_position"])
        else:
            meta["label"] = spec["label"]
        reader = arms[spec["cell"], spec["reader"]]
        for pos, c in enumerate(spec["conditioning_order"]):
            search(
                main[c],
                qid,
                "diagnostic_conditioning" if diagnostic else "conditioning",
                refs[qid],
                epoch=e,
                window=meta["window"],
                slot_cell=spec["cell"],
                slot_reader=reader.identity,
                conditioning_position=pos,
                observer_mode=spec.get("observer_mode"),
            )
        if not diagnostic:
            proc.sample(reader, "burst_pre", query_id=qid, **meta)
        journal.hold = not diagnostic
        try:
            for rep in range(7):
                rm = dict(meta, repetition=rep - 3 if rep >= 4 else rep - 4, retained=rep >= 4)
                op = "warmup" if rep < 4 else "measurement"
                if diagnostic:
                    op = "diagnostic_" + op
                    proc.sample(reader, "query_pre", query_id=qid, **rm)
                search(reader, qid, op, refs[qid], **rm)
                if diagnostic:
                    proc.sample(reader, "query_post", query_id=qid, **rm)
        finally:
            journal.hold = False
            try:
                if not diagnostic:
                    proc.sample(reader, "burst_post", query_id=qid, **meta)
            finally:
                journal.flush_buffer()

    for e in (0, 1):
        stage("epoch" + str(e))
        for r in main.values():
            proc.repin(r, e)
        arms = {}
        for name in schedule["epoch_creation_order"][str(e)]:
            cell, slot = name.rsplit("-", 1)
            r = factory.create(cell, role(e, cell, slot))
            proc.bind(r, factory.works[cell], e)
            arms[cell, slot] = r
            qid = schedule["primary_order"][0]
            for n in range(10):
                search(r, qid, "priming", refs[qid], epoch=e, priming_index=n)
        allreaders = [*main.values(), *arms.values()]
        context_snapshot("epoch_start", e, allreaders)
        for window in schedule["epoch_window_order"][str(e)]:
            if window == "priming":
                continue
            if window in {"primary_pre_plans", "primary_post_plans"}:
                bulk(
                    factory,
                    arms,
                    byid,
                    schedule,
                    observer,
                    e,
                    "pre" if window == "primary_pre_plans" else "post",
                )
            elif window == "primary":
                for n, spec in enumerate(s for s in schedule["primary_bursts"] if s["epoch"] == e):
                    burst(spec, arms)
                    if (n + 1) % 40 == 0:
                        notify("primary", epoch=e, bursts=n + 1)
            elif window == "observer_diagnostic":
                runs = defaultdict(list)
                for spec in schedule["diagnostic_bursts"]:
                    if spec["epoch"] == e:
                        runs[spec["query_id"], spec["observer_mode"]].append(spec)
                mapping = {
                    **{c.split("640")[0] + "-reference": r for c, r in main.items()},
                    **{c + "-" + slot: r for (c, slot), r in arms.items()},
                }
                for (qid, mode), specs in runs.items():
                    if mode == "on":
                        for p in schedule["diagnostic_plan_order"]:
                            if (p["epoch"], p["query_id"], p["boundary"]) == (e, qid, "pre"):
                                plan(
                                    observer,
                                    mapping[p["reader"]],
                                    byid[qid]["query"],
                                    epoch=e,
                                    window="diagnostic",
                                    boundary="pre",
                                    cached=True,
                                    observer_mode="on",
                                    inspection_position=p["inspection_position"],
                                )
                    for spec in specs:
                        burst(spec, arms, True)
                    if mode == "on":
                        for p in schedule["diagnostic_plan_order"]:
                            if (p["epoch"], p["query_id"], p["boundary"]) == (e, qid, "post"):
                                plan(
                                    observer,
                                    mapping[p["reader"]],
                                    byid[qid]["query"],
                                    epoch=e,
                                    window="diagnostic",
                                    boundary="post",
                                    cached=True,
                                    observer_mode="on",
                                    inspection_position=p["inspection_position"],
                                )
        context_snapshot("epoch_end", e, allreaders)
        for r in arms.values():
            r.close()
        journal.checkpoint()
    return dict(outcome="complete_calibration_acquisition", completed_epochs=2, quality_pass=True)
