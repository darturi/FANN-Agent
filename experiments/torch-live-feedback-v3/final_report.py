"""Independently reconstruct the frozen agent/oracle comparison after collection."""

# Markdown rows and report paragraphs are kept as literal strings.
# ruff: noqa: E501

import argparse
import json
import math
import shutil
from pathlib import Path

from analysis import summarize
from limits import digest, read, sha, write


def rows(path):
    with path.open() as handle:
        for line in handle:
            yield json.loads(line)


def analyze(run, output, draws=20000):
    submission = read(run / "submission.json")
    job = submission["job_id"]
    returned = run / ("return-" + job)
    accounting = (returned / "accounting.psv").read_text()
    assert accounting.splitlines()[0].split("|")[1:3] == ["COMPLETED", "0:0"]
    root = returned / ("run-" + job)
    assert read(root / "host-exit.json") == {"job_id": job, "exit_code": 0}
    worker = read(root / "state.json")
    assert worker["status"] == "completed_frozen_comparison" and worker["attempts"] <= 300000
    requests = list((root / "requests").iterdir())
    finals = [p for p in requests if read(p / "request.json")["payload"]["mode"] == "final"]
    assert len(finals) == 1
    final = finals[0]
    response = read(final / "response.json")
    assert response["status"] == "final_complete" and response["private_cleanup_verified"]
    for name, expected in response["raw_sha256"].items():
        assert sha(final / "results" / name) == expected, name
    binding = read(final / "batch-binding.json")
    assert response["module_sha256"] == binding["module_sha256"]
    assert sha(final / "compiled-programs.json") == binding["programs_sha256"]
    request = read(final / "request.json")
    freeze = read(run / "final-freeze.json")
    assert request["payload"]["policies"] == [freeze["policy"]]
    assert digest(request["payload"]) == response["payload_sha256"]
    tools = run / "agent-packet/live/tools.json"
    assert sha(tools) == freeze["agent_state_sha256"]
    assert sha(run / "agent-packet/live/disposition.json") == freeze["agent_disposition_sha256"]
    quality = list(rows(final / "results/quality.jsonl"))
    timing = list(rows(final / "results/timing.jsonl"))
    eligible = {int(t): set(v) for t, v in read(run / "kit/source-eligibility.json").items()}
    exact = {r["id"]: r["output"] for r in rows(run / "kit/source-exact-reference.jsonl")}
    native = {r["id"]: r["native"] for r in rows(run / "kit/source-cases.jsonl")}
    roles = read(run / "kit/query-roles.json")

    def score(answer, qid, t):
        assert len(answer) <= min(10, len(eligible[t]))
        assert len({i for i, _ in answer}) == len(answer)
        assert all(
            i in eligible[t] and math.isfinite(d) and -1e-6 <= d <= 2.000001 for i, d in answer
        )
        if not eligible[t]:
            return 1.0
        boundary = max(d for _, d in exact[qid])
        return sum(d <= boundary + 1e-6 for _, d in answer) / min(10, len(eligible[t]))

    expected_outputs = {}
    for r in quality:
        assert r["role"] == roles[r["id"]]
        assert abs(score(r["output"], r["id"], r["filter"]) - r["recall"]) < 1e-12
        assert abs(score(native[r["id"]], r["id"], r["filter"]) - r["native_recall"]) < 1e-12
        assert r["native_count"] == len(native[r["id"]])
        expected_outputs[r["id"], r["family"]] = r["output"]
    families = tuple(binding["arms"])
    assert len(families) == 6 and len(quality) == 7000 * 6 and len(timing) == 7000 * 6 * 4
    # Reconstruct schedule independently of the helper that produced it.
    for r in timing:
        ti = (-1, 743, 527, 310, 192, 108, 32).index(r["filter"])
        assert r["family"] == families[(r["rotation"] + r["reader"] + ti) % 6]
        assert r["request_ns"] > 0
        wanted = expected_outputs[r["id"], r["family"]]
        assert len(wanted) == len(r["output"])
        assert all(
            a[0] == b[0] and abs(a[1] - b[1]) < 2e-6
            for a, b in zip(wanted, r["output"], strict=True)
        )
    cohorts = {}
    test_ids = {r["id"] for r in quality if r["role"] == "test"}
    assert len(test_ids) == 1925
    for name in ("heldout_test", "full_workload"):
        q = quality if name == "full_workload" else [r for r in quality if r["id"] in test_ids]
        t = timing if name == "full_workload" else [r for r in timing if r["id"] in test_ids]
        cohorts[name] = summarize(q, t, families, draws=draws)
        cohorts[name]["scope"] = (
            "fixed development-fitted agent versus separately cohort-fitted hindsight oracles"
        )
        oracle = "oracle_full" if name == "full_workload" else "oracle_test"
        values = cohorts[name]["aggregates"]["all_seven"]
        cohorts[name]["oracle_gap_percentage_points"] = (
            values[oracle]["savings_percent"] - values["agent"]["savings_percent"]
        )
    disposition = read(run / "agent-packet/live/disposition.json")
    report = {
        "schema": "fannagent.agent-v3-oracle-comparison.v1",
        "job_id": job,
        "cohorts": cohorts,
        "agent_disposition": disposition,
        "freeze_reason": freeze["reason"],
        "agent_policy_sha256": digest(freeze["policy"]),
        "native_attempts_charged": worker["attempts"],
        "allocated_seconds": max(int(r.split("|")[4]) for r in accounting.splitlines() if r.strip())
        + worker.get("prior_allocated_seconds", 0),
        "fresh_exact_queries": 0,
        "model_calls": len(disposition["budget"]["calls"]),
        "model_spend_usd": disposition["budget"]["committed_usd"],
        "automatic_retries": 0,
        "test_feedback_returned_to_agent": False,
        "hindsight_fit_for_agent": False,
        "raw_final_response_sha256": sha(final / "response.json"),
        "raw_final_quality_sha256": sha(final / "results/quality.jsonl"),
        "raw_final_timing_sha256": sha(final / "results/timing.jsonl"),
        "limitations": [
            "One allocation; conditional intervals omit adaptive selection and allocation variability.",
            "Oracle fits use their reported cohort; agent discovery sees development only.",
            "Full workload includes development; research design follows prior protected oracle exposure.",
            "Recall failures and failed equivalence controls prevent qualifying a preserving latency win.",
        ],
    }
    output.mkdir(parents=True)
    write(output / "report.json", report)
    write(output / "agent-policy.json", freeze["policy"])
    write(output / "agent-freeze.json", freeze)
    write(output / "agent-disposition.json", disposition)
    shutil.copyfile(returned / "accounting.psv", output / "accounting.psv")
    lines = [
        "# V3 agent versus broad feasible oracle",
        "",
        f"Job {job}; frozen development-only agent outcome: **{disposition['status']}**.",
        "",
        "The saved broad oracle policies were rerun alongside the frozen agent on the same native baseline. All-seven-condition savings use ratios of mean request latency.",
        "",
        "| Cohort | Agent savings | Broad oracle savings | Gap | Agent recall-loss cases | Strict controls |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for name, label in [
        ("heldout_test", "Test subset: 1,925 cases"),
        ("full_workload", "Full workload: 7,000 cases"),
    ]:
        c = cohorts[name]
        oracle = "oracle_test" if name == "heldout_test" else "oracle_full"
        v = c["aggregates"]["all_seven"]
        lines.append(
            f"| {label} | {v['agent']['savings_percent']:.2f}% | {v[oracle]['savings_percent']:.2f}% | {c['oracle_gap_percentage_points']:.2f} pp | {c['quality_loss_cases']['agent']} | {'Pass' if c['all_condition_controls_pass'] else 'Not established'} |"
        )
    lines += [
        "",
        "A recall-loss count above zero means the agent did not preserve native quality on that cohort. Its measured latency is diagnostic. Failed control equivalence makes estimates descriptive, not certified speedups or numerical ceilings.",
        "",
        "The JSON retains native/agent/oracle means, both seven-condition and six-filter aggregates, per-condition results, result-count losses, conditional intervals and control failures.",
        "",
        f"Model requests: {report['model_calls']}; recorded spend ${report['model_spend_usd']} under $15. Charged ANN reservations: {worker['attempts']} / 300,000. Allocated seconds: {report['allocated_seconds']} / 21,600. Zero fresh exact queries and no automatic retries.",
        "",
        "The agent used 450 development groups; the oracle used hindsight on its reported cohort. No final feedback reached the agent. The cohorts overlap, full includes development, and earlier oracle results informed this research design. Bootstrap intervals condition on one allocation and the fixed selected artifacts; they do not include discovery uncertainty.",
        "",
        "Raw returns, model transcripts, offline fitting scripts and sealed inputs remain in the sibling trial directory outside Git.",
    ]
    (output / "REPORT.md").write_text("\n".join(lines) + "\n")
    paths = sorted(p for p in output.iterdir() if p.is_file())
    (output / "SHA256SUMS").write_text("".join(sha(p) + "  " + p.name + "\n" for p in paths))
    print((output / "REPORT.md").read_text())
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--draws", type=int, default=20000)
    a = p.parse_args()
    analyze(a.run, a.output, a.draws)
