"""Trusted local reconstruction of startup identity and conservative resource margin."""

from collections import Counter
from pathlib import Path

from pc_common import (
    CELLS,
    CONTRACT,
    RESOURCE,
    RESOURCE_DESIGN_SHA,
    RESOURCE_SHA,
    SQL_CAPS,
    campaign_identity,
    digest,
    lines,
    read,
    safe_file,
    save,
    sha,
    verify,
)
from pc_restore import IDENTITY_SHA
from pc_trace import DATA_SQL, SNAPSHOT_SQL, allowed
from sr_memory import membership, resolve_scope


def require(value, message):
    if not value:
        raise ValueError(message)


def memory_result(context, rows, summary, phases, runtime_process):
    require(context["version"] in (1, 2), "Unknown cgroup version")
    resolved = resolve_scope(context["parent_cgroup_text"], context["host_mountinfo"])
    require(all(context[k] == v for k, v in resolved.items()), "Cgroup resolution/context differs")
    require(
        membership(context["sampler_cgroup_text"]) == membership(context["parent_cgroup_text"]),
        "Sampler/parent mapping differs",
    )
    require(context["sampler_cpu"] == context["allocation"]["selected"][3], "Sampler CPU differs")
    r = RESOURCE["resources"]
    d = RESOURCE["decision"]
    require(summary["status"] == "complete" and not summary["error"], "Sampler did not complete")
    require(
        len(rows) == summary["samples"] and 2 <= len(rows) <= r["sampler_samples_max"],
        "Sampler coverage/count differs",
    )
    require(
        summary["raw_bytes"] <= r["sampler_raw_bytes_max"]
        and summary["file_reads"] <= r["sampler_file_reads_max"]
        and summary["bytes_read"] <= r["sampler_read_bytes_max"]
        and summary["cpu_seconds"] <= r["sampler_cpu_seconds_max"],
        "Sampler budget differs",
    )
    reasons = []
    limits = None
    previous = None
    peaks = []
    events = {}
    maximums = {}
    gaps = []
    mapped = False
    component_highs = {}
    phase_samples = {}
    process_highs = {}
    for row in rows:
        phase = phase_samples.setdefault(
            row["phase"], dict(samples=0, largest_sampled_current_bytes=0)
        )
        phase["samples"] += 1
        require(row["start_ns"] <= row["end_ns"], "Memory window invalid")
        if previous is not None:
            require(row["start_ns"] >= previous["end_ns"], "Memory samples overlap/reverse")
            gaps.append((row["start_ns"] - previous["end_ns"]) / 1e9)
            require(
                row["file_reads"] >= previous["file_reads"]
                and row["bytes_read"] >= previous["bytes_read"],
                "Sampler charges reversed",
            )
        scopes = row["scopes"]
        require(
            [s["path"] for s in scopes] == context["ancestors"], "Cgroup scope coverage differs"
        )
        current = {s["path"]: s["limit"] for s in scopes}
        if limits is None:
            limits = current
        require(current == limits, "Memory limits changed")
        require(len(row["processes"]) <= r["processes_max"], "Process cap differs")
        for process in row["processes"]:
            if process.get("VmHWM") is not None:
                key = str(process["pid"]) + ":" + str(process["starttime"])
                process_highs[key] = max(process_highs.get(key, 0), process["VmHWM"])
            if process.get("starttime") == runtime_process["starttime"] and runtime_process[
                "pid"
            ] in (process.get("namespace_pids") or [process["pid"]]):
                mapped = True
        for s in scopes:
            if s["current"] is not None and (
                s["limit"] is not None or s["path"] == context["leaf"]
            ):
                phase["largest_sampled_current_bytes"] = max(
                    phase["largest_sampled_current_bytes"], s["current"]
                )
            values = component_highs.setdefault(s["path"], {})
            for key in [
                "anon",
                "file",
                "kernel",
                "shmem",
                "file_dirty",
                "file_writeback",
                "rss",
                "cache",
                "total_rss",
                "total_cache",
            ]:
                if key in s["stat"]:
                    values[key] = max(values.get(key, 0), s["stat"][key])
            relevant = s["limit"] is not None or s["path"] == context["leaf"]
            if s["limit"] is not None:
                require(type(s["limit"]) is int and s["limit"] > 0, "Invalid finite memory limit")
                if s["peak"] is None:
                    reasons.append("kernel_peak_unavailable")
                else:
                    require(
                        type(s["peak"]) is int and s["peak"] >= s["current"] >= 0,
                        "Invalid charge/peak",
                    )
                    peaks.append(s["peak"])
                    require(s["peak"] >= maximums.get(s["path"], 0), "Memory peak decreased")
                    maximums[s["path"]] = s["peak"]
            if not relevant:
                continue
            ev = s["events"]
            required = (
                {"oom", "oom_kill", "max"} if context["version"] == 2 else {"failcnt", "oom_kill"}
            )
            if not required.issubset(ev):
                reasons.append("event_coverage_incomplete")
            if s["path"] not in events:
                events[s["path"]] = (ev.copy(), ev.copy())
            first, last = events[s["path"]]
            for k in {"oom", "oom_kill", "oom_group_kill", "max", "failcnt"}:
                if k in ev:
                    require(ev[k] >= last.get(k, 0), "Memory event counter decreased")
                    if ev[k] > first.get(k, 0):
                        reasons.append("limit_or_oom_event_delta")
            events[s["path"]] = (first, ev.copy())
        previous = row
    finite = [n for n in limits.values() if n is not None]
    require(bool(finite), "No finite observed memory constraint")
    limit = min([32 * 1024**3, *finite])
    peak = max(peaks) if peaks else None
    if peak is None:
        reasons.append("kernel_peak_unavailable")
    if (
        peak is not None
        and peak + d["reserve_bytes"] + d["unmeasured_workspace_allowance_bytes"] > limit
    ):
        reasons.append("conservative_total_charge_margin_not_demonstrated")
    maxgap = max(gaps, default=0)
    if maxgap > r["sampler_max_gap_seconds"]:
        reasons.append("sampling_gap")
    require(
        phases
        and rows[0]["start_ns"] <= phases[0]["time_ns"]
        and rows[-1]["end_ns"] >= phases[-1]["time_ns"],
        "Memory trace does not bracket runtime",
    )
    for phase in ["epoch0_hold", "epoch1_hold"]:
        if not any(row["phase"] == phase for row in rows):
            reasons.append("reader_hold_not_observed")
    if not mapped:
        reasons.append("host_container_process_mapping_unobserved")
    return dict(
        outcome="startup_resource_margin_pass_scoped"
        if not reasons
        else "startup_complete_resource_margin_inconclusive",
        reasons=sorted(set(reasons)),
        effective_limit_bytes=limit,
        largest_kernel_aggregate_peak_bytes=peak,
        reserve_bytes=d["reserve_bytes"],
        unmeasured_workspace_allowance_bytes=d["unmeasured_workspace_allowance_bytes"],
        max_sampling_gap_seconds=maxgap,
        host_container_process_mapping_observed=mapped,
        cache_subtracted_bytes=0,
        cgroup_version=context["version"],
        limit_visibility="observed host hierarchy only; no invisible ancestor inference",
        sampled_component_highs=component_highs,
        component_highs_scope=(
            "separate sampled maxima; not additive or necessarily simultaneous with aggregate peak"
        ),
        phase_sample_summaries=phase_samples,
        process_high_water_kib=process_highs,
        process_high_water_scope=(
            "per PID/starttime high-water values; never summed as simultaneous job memory"
        ),
        event_deltas={
            p: {
                k: last[k] - first.get(k, 0)
                for k in ["oom", "oom_kill", "oom_group_kill", "max", "failcnt"]
                if k in last
            }
            for p, (first, last) in events.items()
        },
        workload_memory_qualified=False,
        calibration_qualified=False,
    )


def locked(root, name, complete=True):
    lock = read(root / name)
    require(lock["complete"] is complete, "Missing required completion lock: " + name)
    for n, h in lock["files"].items():
        require(sha(safe_file(root, n)) == h, "Raw lock differs: " + n)
    return lock


def analyze(campaign, package, output):
    campaign, package, output = map(Path, (campaign, package, output))
    cfg = verify(package)
    campaign_identity(campaign, package)
    run = campaign / "run"
    hostlock = locked(run, "HOST-LOCK.json")
    locked(run, "LOCK.json")
    require(
        set(hostlock["files"])
        == {
            str(p.relative_to(run))
            for p in run.rglob("*")
            if p.is_file() and p.name != "HOST-LOCK.json"
        },
        "Unlocked host evidence",
    )
    status = read(run / "status.json")
    host = read(run / "host-exit.json")
    sub = read(campaign / "submission.json")
    require(
        status["status"] == "complete" and status["final_integrity_verified"],
        "Incomplete startup/final proof",
    )
    require(host["exit_code"] == 0 and host["protected_sources_unchanged"], "Host/source failure")
    require(
        host["array_job_id"] == sub["jobs"]["block-0"] and host["array_task_id"] == "0",
        "Job identity differs",
    )
    scheduler = read(campaign / "scheduler-evidence.json")
    require(
        any(
            s.split("|")[:3] == [sub["jobs"]["block-0"] + "_0", "COMPLETED", "0:0"]
            for s in scheduler["sacct_stdout"].splitlines()
        ),
        "Successful terminal scheduler record missing",
    )
    launch = read(run / "host-launch.json")
    require(
        launch["host_python"] == sub["host_python"]
        and Path(launch["host_python"]).is_absolute()
        and launch["step_export"] == "ALL",
        "Host interpreter/export differs",
    )
    require(
        all(
            status[k] == 0
            for k in [
                "backend_searches",
                "search_sql",
                "prohibited_sql_attempts",
                "plan_packets",
                "provider_calls",
                "new_fits",
                "confirmation_queries",
            ]
        ),
        "Zero-search/prohibited scope differs",
    )
    require(
        not status["operations"] and status["full_scans"] == {"snapshot": 1, "data": 4},
        "Scan/search accounting differs",
    )
    checkpoint = read(run / "charges-checkpoint.json")
    stages = checkpoint["stages"]
    require(
        [p["name"] for p in stages]
        == ["restore_identity", "snapshot_admission", "epoch0", "epoch1", "final_cleanup"],
        "Stage coverage/order differs",
    )
    require(
        status["elapsed_seconds"] <= 3000 and checkpoint["elapsed_seconds"] <= 3000,
        "Runtime work envelope exceeded",
    )
    for i, row in enumerate(stages):
        require(
            0
            < row["end"] - row["start"]
            <= RESOURCE["resources"]["stage_seconds"][row["name"]] + 1e-6,
            "Stage cap differs",
        )
        if i:
            require(row["start"] <= stages[i - 1]["end"], "Stage deadline overrun")
    require(
        status["reader_connections"] == 10
        and status["maximum_live_readers"] == 6
        and status["result"]["completed_epochs"] == 2,
        "Reader/epoch coverage differs",
    )
    require(
        read(run / "admitted-requests.json") == dict(count=200, executed=0),
        "Requests were not admission only",
    )
    proof = read(run / "snapshot-qualified.json")
    require(
        proof
        == dict(
            eligibility_sha256=sha(package / "eligibility.json"),
            snapshot_identity=cfg["snapshot_identity"],
            field_map={"m_000000": "total_votes"},
            rows=247286,
        ),
        "Snapshot identity proof differs",
    )
    from si_verify import validate as validate_stream

    require(
        all(
            (run / n).stat().st_size <= 65536
            for n in ("identity-stream.json", "identity-preflight.json")
        ),
        "Identity summary cap",
    )
    stream = validate_stream(
        read(run / "identity-stream.json"),
        read(run / "identity-preflight.json"),
        package,
        cfg["snapshot_identity"],
        lines(run / "phases.jsonl"),
    )
    sql = lines(run / "sql.jsonl")
    counts = Counter()
    scans = Counter()
    for row in sql:
        if "statement" not in row:
            continue
        allowed(row["statement"], row["parameters"])
        require(
            row["statement_sha256"] == digest(row["statement"]) and row["error"] is None,
            "SQL error/identity differs",
        )
        counts[row["category"]] += 1
        if row["statement"] == SNAPSHOT_SQL:
            scans["snapshot"] += 1
        if row["statement"] == DATA_SQL:
            scans["data"] += 1
    require(
        dict(counts) == status["sql"] and scans == status["full_scans"],
        "Independent SQL counts differ",
    )
    require(all(counts[k] <= v for k, v in SQL_CAPS.items()), "SQL budget exceeded")
    lifecycle = lines(run / "lifecycle.jsonl")
    live = set()
    opens = []
    closes = []
    peak = 0
    for row in lifecycle:
        key = row["reader"]
        if row["kind"] == "open":
            require(key not in live and key not in opens, "Duplicate reader")
            live.add(key)
            opens.append(key)
        else:
            require(row["kind"] == "close" and key in live, "Invalid reader close")
            live.remove(key)
            closes.append(key)
        peak = max(peak, len(live))
    expected = [c.split("640")[0] + "-reference" for c in CELLS] + [
        "e" + str(e) + "-" + name
        for e in (0, 1)
        for name in RESOURCE["epoch_creation_order"][str(e)]
    ]
    require(
        opens == expected and not live and len(closes) == 10 and peak == 6,
        "Reader order/lifetime differs",
    )
    admissions = lines(run / "admissions.jsonl")
    identities = lines(run / "identities.jsonl")
    contexts = lines(run / "reader-context.jsonl")
    require(
        [r["reader"] for r in contexts] == expected
        and all(r["extra"] == ["auto", "on"] for r in contexts),
        "Reader session context differs",
    )
    require([a["reader"] for a in admissions] == expected, "Admission identity/order differs")
    require([a["reader"] for a in identities] == expected, "Physical reader identity/order differs")
    allocation = next(p for p in lines(run / "placement.jsonl") if p["kind"] == "allocation")
    require(
        len(allocation["selected"]) == 4 and len(set(allocation["selected"])) == 4,
        "Four selected cores missing",
    )
    cores = {r["cpu"]: (r["socket"], r["core"]) for r in allocation["topology"]}
    require(len({cores[c] for c in allocation["selected"]}) == 4, "Four physical cores missing")
    require(
        len({(r["pid"], r["starttime"]) for r in identities}) == 10,
        "Physical reader process reused",
    )
    from pc_common import effective

    for row, physical in zip(admissions, identities):
        cell = row["mode"]
        epoch = physical["epoch"]
        cpu_key = CONTRACT["cpu_policy"]["epoch" + str(epoch)][cell]
        require(
            row["origin"]["settings"] == cfg["source_settings"]
            and row["origin"]["index"] == CONTRACT["targets"][cell]["index"]
            and row["effective"] == effective(row["origin"], cell),
            "Reader target/settings changed",
        )
        require(
            physical["cpu"] == allocation["selected"][int(cpu_key[1])] and physical["cell"] == cell,
            "Reader CPU/cell differs",
        )
    copies = read(run / "copies.json")
    require(set(copies) == set(CELLS), "Whole copy coverage differs")
    source = read(run / "source-before.json")
    require(source == read(run / "source-after.json"), "Retained source changed")
    require(
        read(run / "protected-source-before.json")
        == read(run / "protected-source-after.json")
        == read(campaign / "protected-source-before.json"),
        "Protected dependencies changed",
    )
    for c, copy in read(run / "copies.json").items():
        files = {
            n[len(c + "/pgdata/") :]: v
            for n, v in source["files"].items()
            if n.startswith(c + "/pgdata/")
        }
        require(
            copy["independent_inodes"]
            and copy["database_identity_sha256"] == IDENTITY_SHA
            and copy["pgdata_inventory_sha256"]
            == digest(
                dict(
                    files=files,
                    bytes=sum(v["bytes"] for v in files.values()),
                    file_count=len(files),
                )
            ),
            "Independent whole copy/sidecar proof differs",
        )
    final = read(run / "final-integrity.json")
    require(final["module_sha256"] == CONTRACT["runtime"]["module_sha256"], "Final module changed")
    for c in CELLS:
        v = final["copies"][c]
        require(
            v["data_bits_verified"]
            and v["rows"] == 247286
            and v["original_graph_files"] == CONTRACT["graphs"]["native640"]
            and v["partial_graph_files"]
            == (CONTRACT["graphs"]["partial640"]["partial"] if c == "partial640" else {}),
            "Final data/graph identity differs",
        )
    require(
        read(run / "cleanup.json")
        == dict(errors=[], all_readers_closed=True, databases_stopped=True),
        "Cleanup failed",
    )
    stopped = read(run / "stopped-copies.json")
    require(
        stopped["graphs_match"]
        and all(
            v["fields"]["Database cluster state"] == "shut down"
            for v in stopped["controls"].values()
        ),
        "Working clusters not verified stopped",
    )
    expected_catalogs = read(package / "b2d-catalogs.json")
    cats = lines(run / "catalogs.jsonl")
    require(
        len(cats) == 4
        and {(r["copy"], r["phase"]) for r in cats}
        == {(c, p) for c in CELLS for p in ["before_build", "final"]},
        "Catalog coverage differs",
    )
    require(
        all(
            r["value"] == expected_catalogs[r["copy"]] and r["session_user"] == "torch_owner"
            for r in cats
        ),
        "Catalog identities differ",
    )
    require(
        sum(p.stat().st_size for p in run.rglob("*") if p.is_file())
        <= RESOURCE["resources"]["raw_bytes_max"],
        "Whole raw-size cap",
    )
    require(
        read(run / "memory-context.json")["allocation"]["selected"] == allocation["selected"],
        "Host/container selected cores differ",
    )
    memory = memory_result(
        read(run / "memory-context.json"),
        lines(run / "memory.jsonl"),
        read(run / "memory-summary.json"),
        lines(run / "phases.jsonl"),
        read(run / "runtime-process.json"),
    )
    result = dict(
        protocol="startup-resource.stream.v1",
        resource_contract_sha256=RESOURCE_SHA,
        design_sha256=RESOURCE_DESIGN_SHA,
        campaign=campaign.name,
        searches=0,
        ANN_searches=0,
        exact_searches=0,
        memory=memory,
        outcome=memory["outcome"],
        startup_completed=True,
        identity_stream=stream,
        reader_admissions=10,
        scoped_only=True,
        calibration_qualified=False,
        treatment_speed_qualified=False,
    )
    output.mkdir(parents=True, exist_ok=False)
    save(output / "resource.json", result)
    (output / "report.txt").write_text(
        result["outcome"]
        + "\nZero ANN/exact searches; ten admissions; startup-only scope.\n"
        + str(memory)
        + "\n"
    )
    return result
