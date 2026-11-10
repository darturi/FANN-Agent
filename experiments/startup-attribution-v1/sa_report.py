"""Independent data-only replay. Scientific/resource proof is still reconstructed first."""

from collections import Counter
from pathlib import Path

from pc_common import digest, lines, read, save, sha
from sa_driver import CAPS
from sa_observe import CATALOG


def need(value, why):
    if not value:
        raise ValueError("Attribution replay: " + why)


def replay(host, runtime, sampler, driver, synthetic=False):
    """No returned code is executed; summaries alone never establish the ledger."""
    all_points, summaries, commands, roles = {}, [], [], []
    for scope, rows in (("host", host), ("runtime", runtime)):
        points = [r for r in rows if r["kind"] == "checkpoint"]
        expected = {k for k, v in CATALOG.items() if v == scope}
        need(
            {p["id"] for p in points} == expected and len(points) == len(expected),
            "checkpoint coverage",
        )
        previous = -1
        for n, p in enumerate(points):
            need(
                p["seq"] == n and previous <= p["start_ns"] <= p["end_ns"],
                "checkpoint sequence/window",
            )
            need(p["end_ns"] - p["start_ns"] <= 10**9, "checkpoint overhead")
            previous = p["end_ns"]
            if not synthetic:
                s = p["sample"]
                need(set(s["scopes"]) == {"job", "step_user", "task"}, "three memory scopes")
                need(
                    s["pid"] > 0
                    and s["starttime"] > 0
                    and s["process"]["rss"]
                    and s["process"]["hwm"],
                    "process coverage",
                )
                for v in s["scopes"].values():
                    need(
                        v["peak"] is not None
                        and v["current"] is not None
                        and v["component_coverage"] == "anon_file_kernel",
                        "memory component coverage",
                    )
                if scope == "runtime":
                    need(
                        s["arrow"] is not None
                        and s["arrow"]["live_bytes"] >= 0
                        and s["arrow"]["backend"],
                        "pool coverage",
                    )
            all_points[p["id"]] = p
        summary = [r for r in rows if r["kind"] == "summary"]
        need(len(summary) == 1 and rows[-1] == summary[0], "one final summary")
        s = summary[0]
        need(s["complete"] and not s["invalid"], "incomplete observer")
        need(
            s["cpu_seconds"] <= 15
            and s["wall_seconds"] <= 30
            and s["line_callbacks"] <= 512
            and s["callbacks"] <= 65536
            and s["file_reads"] <= 8192
            and s["read_bytes"] <= 64 * 1024**2,
            "observer ceilings",
        )
        summaries.append(s)
        commands.extend(r for r in rows if r["kind"] == "command")
        roles.extend(r for r in rows if r["kind"] == "role")
    need(len(all_points) == 102, "102 checkpoints")
    need(
        sum(s["cpu_seconds"] for s in summaries) <= 15
        and sum(s["wall_seconds"] for s in summaries) <= 30
        and sum(s["file_reads"] for s in summaries) <= 8192
        and sum(s["read_bytes"] for s in summaries) <= 64 * 1024**2,
        "aggregate added-observer ceilings",
    )

    # Preserve nested clone ordering; catalog order is not execution order.
    def before(a, b):
        need(all_points[a]["end_ns"] <= all_points[b]["start_ns"], a + " precedes " + b)

    for name in all_points:
        if name.endswith(".before"):
            before(name, name[:-7] + ".after")
    snapshot = [k for k in CATALOG if k.startswith("S")]
    for a, b in zip(snapshot, snapshot[1:]):
        before(a, b)
    for cell in ("native640", "partial640"):
        for part in ("source", "destination"):
            before(
                "R03.clone." + cell + ".before",
                "R04.clone_inventory." + cell + "." + part + ".before",
            )
            before(
                "R04.clone_inventory." + cell + "." + part + ".after",
                "R03.clone." + cell + ".after",
            )
    for phase in ("initial", "final"):
        for cell in ("native640", "partial640"):
            stem = "V." + phase + "." + cell
            order = (
                [stem + ".before"]
                + [stem + ".fetch_return." + str(i) for i in (1, 1237, 2473)]
                + [stem + ".after"]
            )
            for a, b in zip(order, order[1:]):
                before(a, b)
            if phase == "final":
                before("R08.final_reader_close.after", stem + ".before")
    for epoch in (0, 1):
        stem = "E" + str(epoch)
        order = [
            stem + "." + s for s in ("creation_before", "hold_begin", "hold_end", "closed_after")
        ]
        for a, b in zip(order, order[1:]):
            before(a, b)
        need(
            all_points[stem + ".hold_end"]["start_ns"] - all_points[stem + ".hold_begin"]["end_ns"]
            >= 5 * 10**9,
            "original hold duration",
        )
    need(len(commands) <= 13000, "command envelope")
    counts, api_links, passes = Counter(), Counter(), {}
    for ordinal, row in enumerate(commands, 1):
        need(
            row["event"] == "dispatch" and row["id"] == ordinal and row["error"] is None,
            "completed unique command ids",
        )
        need(row["reserved_ns"] <= row["start_ns"] <= row["end_ns"], "dispatch interval")
        family = row["family"]
        need(family in CAPS, "unknown family")
        if family == "transaction_control":
            need(row["operation"] in ("BEGIN", "COMMIT"), "unexpected transaction outcome")
        if family == "verification_fetch":
            need(row["operation"] == "FETCH", "fetch operation")
        if family == "verification_close":
            need(row["operation"] == "CLOSE", "close operation")
        counts[family] += 1
        need(counts[family] <= CAPS[family], "family envelope")
        if family == "api_execution":
            api_links[row["api"]] += 1
        if family == "verification_fetch":
            need(
                row["pass_id"]
                in {
                    f"V.{p}.{c}" for p in ("initial", "final") for c in ("native640", "partial640")
                },
                "fetch pass",
            )
            passes.setdefault(row["pass_id"], []).append(row["rows"])
    need(api_links and set(api_links.values()) == {1}, "one execution per API")
    need(set(api_links) == set(range(1, driver["api_attempts"] + 1)), "all API capability ids")
    need(driver["bindings_restored"], "driver bindings not restored")
    for pass_name in {
        f"V.{p}.{c}" for p in ("initial", "final") for c in ("native640", "partial640")
    }:
        seq = [r for r in commands if r["pass_id"] == pass_name]
        need(
            seq[0]["operation"] == "BEGIN"
            and seq[-1]["operation"] == "COMMIT"
            and sum(r["operation"] == "BEGIN" for r in seq) == 1
            and sum(r["operation"] == "COMMIT" for r in seq) == 1,
            "one original transaction per pass",
        )
    need(
        len(passes) == 4 and all(v == [100] * 2472 + [86] for v in passes.values()),
        "exact fetch/page ledger",
    )
    need(
        counts["verification_fetch"] == 9892
        and counts["verification_close"] == 4
        and counts["portal_describe"] == 4
        and counts["transaction_control"] == 8,
        "success driver counts",
    )
    need(
        driver["pending"] == 0
        and driver["admissions"] == 12
        and driver["attempts"] == len(commands)
        and dict(counts) == driver["counts"],
        "driver summary parity",
    )
    required_roles = set(
        read(Path(__file__).parent / "ATTRIBUTION-DESIGN.json")["io_roles"]["categories"]
    )
    need(required_roles.issubset({r["role"] for r in roles}), "operation role coverage")
    need(len(roles) <= 256 and sum(r["entries"] for r in roles) <= 50000, "role/metadata caps")
    need(
        sum(s["cpu_seconds"] for s in summaries) + sampler["cpu_seconds"] <= 60, "combined CPU cap"
    )
    need(
        sum(s["file_reads"] for s in summaries) + sampler["file_reads"] <= 500000,
        "combined read cap",
    )
    need(
        sum(s["read_bytes"] for s in summaries) + sampler["bytes_read"] <= 512 * 1024**2,
        "combined byte cap",
    )
    informative, brackets = interpret(all_points) if not synthetic else ([], [])
    return dict(
        outcome="attribution_complete_informative"
        if informative
        else "attribution_complete_unresolved",
        informative_brackets=informative,
        bracket_observations=brackets,
        checkpoints=102,
        dispatches=len(commands),
        fetches=9892,
        synthetic_fixture=synthetic,
        causal_savings_claim=False,
        full_calibration_released=False,
    )


def interpret(points):
    """Frozen descriptive triage only; no allocation ownership or savings inference."""
    threshold = 256 * 1024**2
    findings, observations = [], []

    def rss(sample, field="rss"):
        value, unit = sample["process"][field].split()
        need(unit == "kB" and int(value) >= 0, "RSS/HWM units")
        return int(value) * 1024

    def bracket(a, b, family):
        x, y = points[a]["sample"], points[b]["sample"]
        process_delta = rss(y) - rss(x)
        peak_delta = rss(y, "hwm") - rss(x, "hwm")
        anon_delta = y["scopes"]["task"]["stat"]["anon"] - x["scopes"]["task"]["stat"]["anon"]
        file_delta = y["scopes"]["job"]["stat"]["file"] - x["scopes"]["job"]["stat"]["file"]
        row = dict(
            before=a,
            after=b,
            family=family,
            process_rss_delta_bytes=process_delta,
            process_hwm_delta_bytes=peak_delta,
            task_anon_delta_bytes=anon_delta,
            job_file_delta_bytes=file_delta,
            hwm_limitation="unchanged peak may mask a transient" if peak_delta == 0 else None,
        )
        observations.append(row)
        return row

    pairs = [
        ("S01.execute_before", "S02.result_received", "cursor_execute"),
        ("S02.result_received", "S03.decoded_before_close", "cursor_decode"),
        ("S03.decoded_before_close", "S04.cursor_closed", "cursor_close"),
        ("S05a.matrix_before", "S06.matrix_ready", "matrix"),
        ("S06.matrix_ready", "S07.finite_complete", "finite"),
        ("S07.finite_complete", "S08.norm_complete", "norm"),
    ]
    for a, b, family in pairs:
        row = bracket(a, b, family)
        if (
            max(
                abs(row["process_rss_delta_bytes"]),
                row["process_hwm_delta_bytes"],
                abs(row["task_anon_delta_bytes"]),
            )
            >= threshold
        ):
            findings.append(family + "_descriptive_bracket")
    for phase in ("initial", "final"):
        for cell in ("native640", "partial640"):
            stem = "V." + phase + "." + cell
            names = (
                [stem + ".before"]
                + [stem + ".fetch_return." + str(n) for n in (1, 1237, 2473)]
                + [stem + ".after"]
            )
            pool = [points[n]["sample"]["arrow"]["live_bytes"] for n in names]
            if max(pool) - min(pool) >= threshold:
                findings.append(stem + "_default_pool_variation")
            observations.append(
                dict(
                    family="verification_pool",
                    pass_id=stem,
                    sampled_pool_range_bytes=max(pool) - min(pool),
                )
            )
    # Use only before/after original I/O roles, not retained-context epoch controls.
    for name in points:
        if name.endswith(".before") and name.startswith(
            ("R01.", "R02.", "R04.", "R05.", "R06.", "V.", "R10.", "R12.", "R13.")
        ):
            after = name[:-7] + ".after"
            row = bracket(name, after, "file_charge_context")
            if (
                abs(row["job_file_delta_bytes"]) >= threshold
                and abs(row["process_rss_delta_bytes"]) < threshold
                and abs(row["task_anon_delta_bytes"]) < threshold
            ):
                findings.append(name + "_file_charge_coincidence_no_ownership_claim")
    return findings, observations


def analyze(campaign, package, output):
    import sr_report

    # Original independent identity/integrity/resource proof and host/guest locks first.
    resource = sr_report.analyze(campaign, package, Path(output) / "resource")
    run = Path(campaign) / "run"
    capability = read(run / "instrument-capability.json")
    need(
        capability["driver"] == read(Path(package) / "DRIVER-REFERENCE.json"),
        "actual library provenance",
    )
    need(capability["added_preflight_cpu_seconds"] <= 1, "preflight CPU")
    need(
        len(capability["bindings"]) == 9
        and all(
            b["binding_active"]
            and b["original_link_intact"]
            and b["wrapper_source_sha256"] == sha(Path(package) / "sa_driver.py")
            for b in capability["bindings"]
        ),
        "actual binding provenance",
    )
    api = [r for r in lines(run / "sql.jsonl") if "statement" in r]
    lower = [
        r for r in lines(run / "attribution-runtime.jsonl") if r.get("family") == "api_execution"
    ]
    need(len(api) == len(lower), "API/lower dispatch count parity")
    for ordinal, (a, b) in enumerate(zip(api, lower, strict=True), 1):
        need(
            b["api"] == ordinal and b["statement_sha256"] == digest(a["statement"]),
            "API template linking",
        )
    result = replay(
        lines(run / "attribution-host.jsonl"),
        lines(run / "attribution-runtime.jsonl"),
        read(run / "memory-summary.json"),
        read(run / "driver-summary.json"),
    )
    result["resource_verdict"] = resource["outcome"]
    save(Path(output) / "attribution.json", result)
    return result
