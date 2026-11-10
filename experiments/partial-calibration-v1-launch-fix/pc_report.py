"""Trusted, offline reconstruction. Raw completion alone never qualifies timing."""

from collections import Counter, defaultdict
from pathlib import Path

from pc_common import (
    CELLS,
    CONTRACT,
    OPERATIONS,
    SQL_CAPS,
    STAGES,
    campaign_identity,
    digest,
    lines,
    parity,
    read,
    safe_file,
    save,
    sha,
    verify,
)
from pc_measure import events, role
from pc_metadata import validate_catalog, validate_packet
from pc_results import equivalent, quality_report
from pc_stats import finite, near, require, score_result, timing, unique


def plan_events(s):
    for n, q in enumerate(s["qualification_query_ids"]):
        for boundary in ("pre", "post"):
            for c in CELLS:
                yield dict(
                    query_id=q,
                    reader=c.split("640")[0] + "-reference",
                    window="qualification",
                    boundary=boundary,
                    fixture=n,
                )
    for n, q in enumerate(s["quality_order"]):
        for boundary in ("pre", "post"):
            for c in CELLS:
                yield dict(
                    query_id=q,
                    reader=c.split("640")[0] + "-reference",
                    window="quality",
                    boundary=boundary,
                    quality_index=n,
                )
    for e in (0, 1):
        for w in s["epoch_window_order"][str(e)]:
            if w in ("primary_pre_plans", "primary_post_plans"):
                for row in s["primary_boundary_plan_order"]:
                    if row["epoch"] == e and row["boundary"] == (
                        "pre" if w == "primary_pre_plans" else "post"
                    ):
                        c, r = row["reader"].rsplit("-", 1)
                        yield dict(
                            query_id=row["query_id"],
                            reader=role(e, c, r),
                            epoch=e,
                            window="bulk",
                            boundary=row["boundary"],
                            inspection_position=row["inspection_position"],
                        )
            elif w == "observer_diagnostic":
                qs = list(
                    dict.fromkeys(r["query_id"] for r in s["diagnostic_bursts"] if r["epoch"] == e)
                )
                for q in qs:
                    for boundary in ("pre", "post"):
                        for row in s["diagnostic_plan_order"]:
                            if (row["epoch"], row["query_id"], row["boundary"]) == (e, q, boundary):
                                r = row["reader"]
                                if not r.endswith("reference"):
                                    c, slot = r.rsplit("-", 1)
                                    r = role(e, c, slot)
                                yield dict(
                                    query_id=q,
                                    reader=r,
                                    epoch=e,
                                    window="diagnostic",
                                    boundary=boundary,
                                    observer_mode="on",
                                    inspection_position=row["inspection_position"],
                                )


def raw_lock(run):
    lock = read(run / "LOCK.json")
    for n, h in lock["files"].items():
        require(sha(safe_file(run, n)) == h, "Raw lock mismatch: " + n)
    exempt = {
        "LOCK.json",
        "job-exit.json",
        "host-exit.json",
        "host-failure.json",
        "protected-source-after.json",
    }
    actual = {str(p.relative_to(run)) for p in run.rglob("*") if p.is_file()}
    require(not actual - set(lock["files"]) - exempt, "Unbound raw file")
    require(lock["complete"], "Native lock incomplete")
    return lock


def process_counters(p):
    s = p["stat"]
    return {
        **{k: s[k] for k in ("minflt", "majflt", "utime", "stime")},
        **p["io"],
        **p["context_switches"],
        **{
            "sched_" + k: v
            for k, v in p.get("schedstat", {}).items()
            if k != "wait_enabled" and v is not None
        },
    }


def telemetry(rows, searches, identities, placement, complete):
    alloc = next(r for r in placement if r["kind"] == "allocation")
    selected = alloc["selected"]
    require(len(selected) == len(set(selected)) == 4, "Invalid CPU selection")
    topology = {r["cpu"]: (r["socket"], r["core"]) for r in alloc["topology"]}
    require(
        len({topology[c] for c in selected}) == 4 and set(selected) <= set(alloc["allowed"]),
        "SMT/outside-allocation core",
    )
    require(len(rows) <= 5500, "Telemetry cap")
    grouped = defaultdict(list)
    previous = {}
    total = 0
    for r in sorted(rows, key=lambda x: x["start_ns"]):
        finite(r["outer_ms"])
        near(r["outer_ms"], (r["end_ns"] - r["start_ns"]) / 1e6)
        total += r["outer_ms"] / 1000
        identity = r["identity"]
        key = identity["reader"]
        original = identities[key]
        require(
            all(
                identity[k] == original[k]
                for k in ("pid", "starttime", "postmaster", "server", "socket", "cell")
            ),
            "Physical mapping drift",
        )
        expected = selected[
            int(CONTRACT["cpu_policy"]["epoch" + str(identity["epoch"])][identity["cell"]][1])
        ]
        require(identity["cpu"] == expected, "Epoch CPU crossover differs")
        for kind, cpu in [("backend", expected), ("client", selected[0])]:
            p = r[kind]
            s = p["stat"]
            require(
                p["affinity"] == [cpu]
                and __import__("pc_proc").cpu_list(p["allowed_cpus"]) == {cpu}
                and p["status_pid"] == s["pid"]
                and p["status_ppid"] == s["ppid"],
                "Affinity/namespace raw mismatch",
            )
            if kind == "backend":
                require(p["threads"] == 1, "Unexpected backend threads")
            require(
                s["processor"] == cpu and s["state"] not in ("Z", "X"), "Last CPU/alive mismatch"
            )
            if kind == "backend":
                require(
                    s["pid"] == original["pid"]
                    and s["ppid"] == original["postmaster"]
                    and s["starttime"] == original["starttime"],
                    "PID/server replacement",
                )
            keyp = (s["pid"], s["starttime"])
            counts = process_counters(p)
            require(
                all(
                    type(v) is int and v >= previous.get(keyp, {}).get(k, 0)
                    for k, v in counts.items()
                ),
                "Counter delta invalid",
            )
            previous[keyp] = counts
            if "schedstat" in p:
                require(
                    (p["schedstat"]["runqueue_ns"] is not None)
                    == alloc["scheduler_wait_accounting_enabled"],
                    "Unavailable scheduler wait inferred zero",
                )
        grouped[
            (
                r["identity"]["reader"],
                r.get("query_id"),
                r.get("observer_mode"),
                r.get("repetition"),
            )
        ].append(r)
    require(total <= 60, "Telemetry time cap")
    primary = [r for r in searches if r["operation"] in ("warmup", "measurement")]
    bursts = defaultdict(list)
    for r in primary:
        bursts[r["reader"], r["query_id"]].append(r)
    for (reader, q), ss in bursts.items():
        pair = grouped[reader, q, None, None]
        require(
            len(pair) == 2 and {p["boundary"] for p in pair} == {"burst_pre", "burst_post"},
            "Missing/duplicate primary bracketing",
        )
        pre = next(p for p in pair if p["boundary"] == "burst_pre")
        post = next(p for p in pair if p["boundary"] == "burst_post")
        require(
            len(ss) == 7
            and pre["end_ns"] <= min(r["start_ns"] for r in ss)
            and post["start_ns"] >= max(r["end_ns"] for r in ss),
            "Burst bracketing/window differs",
        )
    diag = [
        r for r in searches if r["operation"] in ("diagnostic_warmup", "diagnostic_measurement")
    ]
    for r in diag:
        pair = grouped[r["reader"], r["query_id"], r["observer_mode"], r["repetition"]]
        require(len(pair) == 2, "Missing/duplicate diagnostic bracketing")
        pre = next(p for p in pair if p["boundary"] == "query_pre")
        post = next(p for p in pair if p["boundary"] == "query_post")
        require(
            pre["end_ns"] <= r["start_ns"] <= r["end_ns"] <= post["start_ns"],
            "Diagnostic bracketing differs",
        )
    if complete:
        require(len(bursts) == 1600 and len(diag) == 896, "Telemetry coverage differs")
    return dict(
        bundles=len(rows),
        sample_seconds=total,
        primary_bursts=len(bursts),
        diagnostic_calls=len(diag),
    )


def analyze(campaign, package, output):
    campaign, package, output = map(Path, (campaign, package, output))
    verify(package)
    name = campaign_identity(campaign, package)
    run = campaign / "run"
    raw_lock(run)
    launch = read(run / "host-launch.json")
    sub = read(campaign / "submission.json")
    require(
        launch["host_python"] == sub["host_python"]
        and Path(launch["host_python"]).is_absolute()
        and launch["step_export"] == "ALL"
        and launch["python_no_bytecode"] == "1",
        "Host launch/interpreter identity differs",
    )
    require(
        sum(p.stat().st_size for p in run.rglob("*") if p.is_file()) <= 1024**3,
        "Whole evidence cap",
    )
    status = read(run / "status.json")
    sub = read(campaign / "submission.json")
    host = read(run / "host-exit.json")
    require(
        status["status"] == "complete" and status["final_integrity_verified"],
        "Missing completion/final proof",
    )
    require(
        host["exit_code"] == 0
        and host["protected_sources_unchanged"]
        and host["provider_calls"] == 0,
        "Host/protection failure",
    )
    require(
        host["array_job_id"] == sub["jobs"]["block-0"]
        and host["array_task_id"] == "0"
        and host["job_id"] in {sub["jobs"]["block-0"], sub["jobs"]["block-0"] + "_0"},
        "Slurm identity differs",
    )
    scheduler = read(campaign / "scheduler-evidence.json")
    valid_ids = {sub["jobs"]["block-0"], sub["jobs"]["block-0"] + "_0"}
    require(
        any(
            len(p := line.split("|")) >= 3
            and p[0] in valid_ids
            and p[1] == "COMPLETED"
            and p[2] == "0:0"
            for line in scheduler["sacct_stdout"].splitlines()
        ),
        "Scheduler success missing",
    )
    require(read(run / "job-exit.json")["exit_code"] == 0, "Runtime exit failure")
    for k in ("provider_calls", "new_fits", "confirmation_queries"):
        require(status[k] == 0, "Prohibited activity")
    require(
        read(run / "protected-source-before.json")
        == read(run / "protected-source-after.json")
        == read(campaign / "protected-source-before.json"),
        "Protected source proof differs",
    )
    source = read(run / "source-before.json")
    require(source == read(run / "source-after.json"), "Retained source changed")
    for c, ctrl in read(run / "source-control.json").items():
        require(
            c in CELLS and ctrl["fields"]["Database cluster state"] == "shut down", "Unclean source"
        )
    require(set(read(run / "source-control.json")) == set(CELLS), "Source control coverage")
    for c, copy in read(run / "copies.json").items():
        files = {
            n[len(c + "/pgdata/") :]: v
            for n, v in source["files"].items()
            if n.startswith(c + "/pgdata/")
        }
        inv = dict(
            files=files, bytes=sum(v["bytes"] for v in files.values()), file_count=len(files)
        )
        require(
            copy["pgdata_inventory_sha256"] == digest(inv) and copy["independent_inodes"],
            "Whole-copy proof differs",
        )
    require(read(run / "runtime-identity.json") == CONTRACT["runtime"], "Runtime identity differs")
    final = read(run / "final-integrity.json")
    require(final["module_sha256"] == CONTRACT["runtime"]["module_sha256"], "Final module")
    for c in CELLS:
        proof = final["copies"][c]
        require(
            proof["data_bits_verified"]
            and proof["rows"] == 247286
            and proof["original_graph_files"] == CONTRACT["graphs"]["native640"]
            and proof["partial_graph_files"]
            == (CONTRACT["graphs"]["partial640"]["partial"] if c == "partial640" else {}),
            "Final data/graphs",
        )
    stopped = read(run / "stopped-copies.json")
    require(
        stopped["graphs_match"] and set(stopped["controls"]) == set(CELLS),
        "Stopped-copy final graph coverage",
    )
    require(
        all(
            v["fields"]["Database cluster state"] == "shut down"
            for v in stopped["controls"].values()
        ),
        "Final copies unclean",
    )
    cleanup = read(run / "cleanup.json")
    require(
        cleanup == dict(errors=[], all_readers_closed=True, databases_stopped=True),
        "Cleanup incomplete",
    )
    from pc_settings import memory_proof

    mem = read(run / "memory-preflight.json")
    require(
        mem == memory_proof(mem["servers"]) and mem["conservative_bound_bytes"] == 15300820992,
        "Memory configured bound",
    )
    for resources in [
        read(campaign / "resource-preflight-login.json"),
        read(run / "resource-preflight.json"),
    ]:
        require(
            resources["graph_hashes_match"]
            and resources["source"] == CONTRACT["retained_source_work"],
            "Resource/source identity",
        )
        for fs, q in resources["quota"].items():
            if fs in ("/home", "/scratch"):
                require(
                    min(q["filesystem_free_bytes"], q["space_available_lower"])
                    >= q["required_bytes"]
                    and min(q["filesystem_free_inodes"], q["inodes_available_lower"])
                    >= q["required_inodes"],
                    "Resource floor failed",
                )
    catalog_expected = read(package / "b2d-catalogs.json")
    cats = lines(run / "catalogs.jsonl")
    require(len(cats) == 4, "Catalog coverage")
    for c in CELLS:
        cc = [r for r in cats if r["copy"] == c]
        require({r["phase"] for r in cc} == {"before_build", "final"}, "Catalog boundaries")
        for r in cc:
            require(
                r["session_user"] == "torch_owner"
                and r["value"] == catalog_expected[c]
                and r["sha256"] == digest(r["value"]),
                "Complete catalog/statistics identity",
            )
            validate_catalog(r["value"], c == "partial640", "torch_owner")
    s = read(package / "SCHEDULE.json")
    queries = {i["query"]["id"]: i["query"] for i in lines(package / "queries.jsonl")}
    pins = read(package / "baseline-results.json")
    old = unique(lines(package / "b2d-references.jsonl"), lambda r: r["query_id"])
    elig = read(package / "eligibility.json")
    refs = lines(run / "references.jsonl")
    require([r["query_id"] for r in refs] == s["quality_order"], "Fresh reference order")
    for r in refs:
        qid = r["query_id"]
        truth = {k: r[k] for k in ("truth_strict", "truth_ties", "truth_k")}
        require(truth == {k: pins[qid][k] for k in truth}, "Exact truth identity")
        for c, v in r["outcomes"].items():
            score_result(v, truth, queries[qid], elig)
            equivalent(v, old[qid]["outcomes"][c])
    quality = quality_report(refs)
    parity(quality, read(run / "quality.json"))
    complete = quality["pass"]
    expected = list(events(s))
    expected = expected if complete else expected[:610]
    rows = lines(run / "searches.jsonl")
    require(len(rows) == len(expected), "Search count differs")
    counter = Counter()
    prev = 0
    for r, (op, qid, reader, meta) in zip(rows, expected):
        require(
            (r["operation"], r["query_id"], r["reader"]) == (op, qid, reader) and "error" not in r,
            "Search order/identity/error",
        )
        require(all(r.get(k) == v for k, v in meta.items()), "Search prospective metadata")
        finite(r["outer_ms"], True)
        near(r["outer_ms"], (r["end_ns"] - r["start_ns"]) / 1e6)
        require(r["start_ns"] >= prev, "Overlapping/reordered calls")
        prev = r["end_ns"]
        counter[op] += 1
        truth = {k: pins[qid][k] for k in ("truth_strict", "truth_ties", "truth_k")}
        if op.endswith("exact"):
            require(r["truth"] == truth, "Exact truth parity")
        else:
            score_result(r["result"], truth, queries[qid], elig)
            equivalent(r["result"], old[qid]["outcomes"][r["cell"]])
            finite(r["sql_ms"])
    require(
        dict(counter) == status["operations"]
        and sum(counter.values()) == status["backend_searches"] == status["search_sql"],
        "Search accounting",
    )
    if complete:
        require(dict(counter) == OPERATIONS, "Operation reservations differ")
    admissions = lines(run / "admissions.jsonl")
    identities = unique(lines(run / "identities.jsonl"), lambda r: r["reader"])
    order = ["native-reference", "partial-reference"] + (
        [role(e, *v.rsplit("-", 1)) for e in (0, 1) for v in s["epoch_creation_order"][str(e)]]
        if complete
        else []
    )
    require(
        [a["reader"] for a in admissions] == order and list(identities) == order,
        "Admission order/coverage",
    )
    require(len({r["pid"] for r in identities.values()}) == len(order), "PID reuse")
    require(
        status["reader_connections"] == len(order)
        and status["maximum_live_readers"] == (6 if complete else 2),
        "Reader caps",
    )
    for a in admissions:
        c = a["mode"]
        origin = a["origin"]
        effective = a["effective"]
        require(origin["index"] == CONTRACT["targets"][c]["index"], "Admitted index target differs")
        require(
            effective == __import__("pc_common").effective(origin, c),
            "Admitted effective binding differs",
        )
        require(effective["settings"] == CONTRACT["settings"], "Admitted GUCs differ")
    for r in rows:
        if "result" in r:
            i = identities[r["reader"]]
            p = r["physical"]
            require(p["epoch"] == r.get("epoch", 0), "Search physical epoch mismatch")
            require(
                all(
                    p[k] == i[k]
                    for k in (
                        "reader",
                        "cell",
                        "pid",
                        "starttime",
                        "postmaster",
                        "server",
                        "socket",
                    )
                ),
                "Search backend mapping differs",
            )
    plans = lines(run / "plans.jsonl")
    pe = list(plan_events(s))
    pe = pe if complete else pe[:808]
    require(len(plans) == len(pe) == status["plan_packets"], "Plan coverage")
    paired = defaultdict(dict)
    for p, e in zip(plans, pe):
        require(all(p.get(k) == v for k, v in e.items()), "Plan order/boundary differs")
        packet = p["packet"]
        require(packet["mode"] == identities[p["reader"]]["cell"], "Plan target/reader mismatch")
        validate_packet(packet, queries[p["query_id"]], packet["mode"])
        require(
            packet["driver"]["psycopg"] == "3.3.6"
            and all(c["generic_plans"] == 0 for c in packet["cached"]),
            "Generic/driver regime changed",
        )
        if p["window"] == "bulk":
            *_, slot = p["reader"].split("-")
            paired[p["epoch"], p["boundary"], p["query_id"], packet["mode"]][slot] = {
                k: v for k, v in packet.items() if k != "charge"
            }
    require(
        all(set(v) == {"r0", "r1"} and v["r0"] == v["r1"] for v in paired.values()),
        "Physical replica plan divergence",
    )
    sql = lines(run / "sql.jsonl")
    charges = Counter(r["category"] for r in sql if "category" in r)
    require(
        dict(charges) == status["sql"]
        and all(charges[k] <= v for k, v in SQL_CAPS.items())
        and not set(charges) - set(SQL_CAPS),
        "SQL ceiling/accounting",
    )
    require(not any(r.get("error") for r in sql), "SQL acquisition error")
    # No observer SQL or proc sample inside any primary seven-call interval.
    burst = defaultdict(list)
    for r in rows:
        if r["operation"] in ("warmup", "measurement"):
            burst[r["reader"], r["query_id"]].append(r)
    telemetry_rows = lines(run / "telemetry.jsonl")
    intervals = sorted(
        (min(r["start_ns"] for r in rr), max(r["end_ns"] for r in rr)) for rr in burst.values()
    )
    import bisect

    ends = [b for a, b in intervals]
    for r in [*sql, *telemetry_rows]:
        a = r.get("start_ns", r.get("time_ns"))
        b = r.get("end_ns", a)
        j = bisect.bisect_right(ends, a)
        if j < len(intervals):
            require(b <= intervals[j][0], "Observer I/O entered primary burst")
    tele = telemetry(telemetry_rows, rows, identities, lines(run / "placement.jsonl"), complete)
    tc = status["telemetry"]
    require(
        tc["bundles"] == tele["bundles"]
        and tc["proc_reads"] <= 44000
        and tc["affinity_operations"] <= 11200
        and tc["telemetry_seconds"] <= 60,
        "Telemetry ceilings",
    )
    require(tc["telemetry_seconds"] + 1e-9 >= tele["sample_seconds"], "Telemetry cost undercount")
    checkpoints = read(run / "charges-checkpoint.json")
    require(checkpoints["searches"] == len(rows), "Final checkpoint")
    for st in checkpoints["stages"]:
        require(st["end"] - st["start"] <= STAGES[st["name"]], "Stage cap changed")
    require(status["elapsed_seconds"] <= 10200, "Work deadline")
    require(
        status["result"]
        == dict(
            outcome="complete_calibration_acquisition" if complete else "closed_negative_quality",
            completed_epochs=2 if complete else 0,
            quality_pass=complete,
        ),
        "Terminal acquisition outcome",
    )
    gates = timing([r for r in rows if r["operation"] == "measurement"]) if complete else None
    outcome = (
        ("calibration_qualified_scoped" if gates["all_pass"] else "calibration_inconclusive")
        if gates
        else "closed_negative_quality"
    )
    descript = (
        {
            c: sum(
                r["outer_ms"] for r in rows if r["operation"] == "measurement" and r["cell"] == c
            )
            / 2400
            for c in CELLS
        }
        if complete
        else None
    )
    orientation = {}
    diagnostic = {}
    if complete:
        for e in (0, 1):
            for c in CELLS:
                sign = 1 if e == 0 else -1
                orientation[f"{e}/{c}"] = dict(
                    contrast="later-created minus earlier-created",
                    physical_contrast="r1-r0" if e == 0 else "r0-r1",
                    gap_ms=sign * gates["intervals"][f"aa/{e}/{c}/gap"]["mean"],
                )
                mode = {}
                for m in ("off", "on"):
                    rr = [
                        r
                        for r in rows
                        if r["operation"] == "diagnostic_measurement"
                        and r["epoch"] == e
                        and r["cell"] == c
                        and r["observer_mode"] == m
                    ]
                    require(len(rr) == 48, "Diagnostic retained coverage")
                    mode[m] = sum(r["outer_ms"] for r in rr) / len(rr)
                diagnostic[f"{e}/{c}"] = dict(
                    outer_ms=mode,
                    paired_on_minus_off_ms=mode["on"] - mode["off"],
                    independent_vectors=8,
                    descriptive_only=True,
                    primary_rescue_allowed=False,
                )
    result = dict(
        campaign=name,
        outcome=outcome,
        quality=quality,
        timing=gates,
        telemetry=tele,
        descriptive_outer_ms=descript,
        creation_order_orientation=orientation,
        observer_diagnostic=diagnostic,
        provider_calls=0,
        new_fits=0,
        confirmation_queries=0,
        treatment_speed_qualified=False,
        adoption_authorized=False,
        b2d_status="measurement_inconclusive",
        original_execution_retained=True,
    )
    output.mkdir(parents=True, exist_ok=False)
    save(output / "analysis.json", result)
    save(
        output / "verification.json",
        dict(
            status="passed",
            raw_lock_verified=True,
            package_manifest_sha256=sha(package / "manifest.json"),
            raw_data_only=True,
            strict_discrete_parity=True,
            float_tolerance=1e-12,
        ),
    )
    (output / "report.txt").write_text(
        outcome
        + "\n"
        + (
            "Timing intervals passed: " + str(gates["passed_intervals"]) + "/56\n"
            if gates
            else "Quality gate failed; no formal timing verdict.\n"
        )
        + "No treatment speedup or adoption verdict. B2d remains inconclusive.\n"
    )
    return result
