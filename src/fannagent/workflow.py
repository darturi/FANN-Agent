"""Development-only orientation and advisory pacing for fresh research conversations."""

from __future__ import annotations

TOOL_GUIDANCE = """Development tool usage:
Every fannagent-tool command takes one JSON object and prints an envelope:
{"ok":true,"result":VALUE}, or {"ok":false,"error":...,"error_info":...} with exit code 1.
Check success before interpreting result. Artifact files contain VALUE directly, with no envelope.
The startup development catalog is already at the supplied /workspace/artifacts/HASH.json path.
It contains all development items as {query: OBJECT, group: VECTOR_GROUP}; no held-out queries.
queries {"offset":0,"limit":20} returns a LIST of query objects, not the full workload.
Default limit is 20, maximum 100; offset paginates. Adjacent filter variants can share one vector.
Use catalog groups to spread cheap checks across independent vectors and filter variants.
Do not print vectors or whole traces into the conversation. Summarize IDs, groups and measurements.
sample returns DATA ROWS, not workload queries; prefer the prepared development catalog.
count, descriptors, probe, audit and labels all require {"query": QUERY_OBJECT}.
probe and audit optionally accept "policy": POLICY_OBJECT. labels is per query, not a bulk command.
screen takes {"query":QUERY_OBJECT,"policy":POLICY_OBJECT} and returns modes native, policy,
and continue with complete latency/recall summaries. It uses no trace, one warmup and three
paired repetitions; this is cheap screening, never statistical acceptance. probe uses tracing
and observation execution, so its timings are not an ordinary native comparison.
development_evaluate and validate require {"policy": POLICY_OBJECT}.
calibrate takes {"policy": POLICY_OBJECT,"checkpoint":true}; submit takes {"policy": POLICY_OBJECT}.
validate checks policy structure and features only; it performs no recall/latency evaluation.
development_evaluate measures the FULL development split with the configured statistical gates.
Small probe sweeps and work savings do not establish recall noninferiority or latency gains.
artifact takes {"hash":"HASH"}. For local analysis, read the referenced development JSON file.
Example after registering an investigation (substitute the startup catalog path):
  import json, subprocess
  items = json.load(open(CATALOG_PATH))["items"]
  q = items[0]["query"]
  reply = json.loads(subprocess.run(["fannagent-tool", "labels", json.dumps({"query":q})],
                                   capture_output=True, text=True, check=True).stdout)
  assert reply["ok"]
  print(reply["result"])  # artifact hash; read it locally and summarize
Budget time for experiment transitions as well as measurements. Finish the investigation,
start a candidate_evaluation plan, evaluate the exact policy on development, and conclude.
If supported, start a calibration plan, calibrate with checkpoint:true, conclude using its event,
then submit the SAME accepted policy. Rejected/inconclusive evidence permits abstention.
For a twelve-attempt study, finish orientation and screening in the first three attempts.
Use one checked Bash action to finish screening, start candidate_evaluation, run the full
evaluation and record its conclusion. Aim to complete full development by attempt six.
Screen actual complete latency against native execution and an always-continue control;
work reduction alone can hide policy overhead. Spread checks across independent catalog groups.
Multiple sequential broker calls and local analysis may share one Bash action. Check every
operation's success; do not hide failures with pipes or run measurements in the background.
Full evaluations can exceed an hour. The broker and shell allow three hours; wait for the result.
Evaluation results include evaluation_job_id and evaluation_report_artifact. The latter is the
complete durable report, even if the response omits large per-query details. Retrieve it locally
or with artifact. evaluation_status {"job_id":"ID"} retrieves durable status and the completed
response without measuring again. A timeout includes the request's job ID; preserve it and
retrieve status after the original worker finishes. Do not replay an evaluation or start another
measurement while its outcome is uncertain. A still-running record after interruption is not
evidence of completion and never grants replay or final-test permission.
"""


def workflow_plan(turn_limit):
    """Targets reserve four turns for calibration, its record, and submission/corrections."""
    return {
        "advisory": True,
        "model_turn_limit": turn_limit,
        "screening_by_turn": min(3, turn_limit),
        "full_development_evaluation_by_turn": min(turn_limit, max(1, min(6, turn_limit - 6))),
        "calibration_by_turn": min(turn_limit, max(1, min(8, turn_limit - 4))),
        "reserve_turns": min(4, turn_limit),
        "instruction": (
            "Keep orientation and cheap development screening short. Move to full development "
            "evaluation, calibration and conclusion within the allocation, or abstain if no "
            "candidate is defensible. These targets never waive acceptance or experiment gates."
        ),
    }


def workflow_notice(tools, turn_limit, completed_turns):
    """Only public stage aggregates; never expose calibration queries, rows or evidence refs."""
    events = tools.experiments.events()
    successful = [e for e in events if e["state"] == "success"]
    development = [e for e in successful if e["operation"] == "development_evaluate"]
    calibration = [e for e in successful if e["operation"] == "calibrate"]
    budget = tools.budget.summary()
    remaining = max(0, turn_limit - completed_turns)
    if not development:
        next_step = (
            "Conclude cheap screening and run full development_evaluate under a registered "
            "candidate_evaluation plan on a defensible candidate, or exit 0."
        )
        if completed_turns >= 3:
            next_step = (
                "Screening allocation is used. In the next checked Bash action, finish screening, "
                "register candidate_evaluation, run full development_evaluate and conclude, "
                "or exit 0 if no candidate is defensible. Reserve remaining attempts for the "
                "calibration and submission sequence; another small probe sweep "
                "is not a full result."
            )
    elif not calibration:
        next_step = (
            "Use the full development result to select or reject the candidate. If supported, "
            "finish its experiment, start calibration and calibrate with checkpoint:true. "
            "If unsupported and no evidence-backed revision fits, exit 0."
        )
    elif tools.study.checkpoint_policy_hash():
        next_step = (
            "Conclude the accepted calibration experiment, then submit the exact accepted "
            "policy while it remains eligible. Do not spend the last turns on more probes."
        )
    else:
        next_step = (
            "Calibration produced no accepted checkpoint. Reject unsupported candidates; "
            "only revise with development evidence and sufficient remaining allocation, or exit 0."
        )
    return {
        "model_turns_completed": completed_turns,
        "model_turns_remaining": remaining,
        "model_turn_limit": turn_limit,
        "charged_provider_attempts": len(budget["calls"]),
        "committed_usd": budget["committed_usd"],
        "ceiling_usd": budget["ceiling_usd"],
        "successful_development_operations": len(development),
        "successful_calibration_operations": len(calibration),
        "active_experiment": tools.study.store.get("research_active_experiment"),
        "checkpoint_policy_hash": tools.study.checkpoint_policy_hash(),
        "reserve_warning": remaining <= 6,
        "next_step": next_step,
        "advisory": True,
    }
