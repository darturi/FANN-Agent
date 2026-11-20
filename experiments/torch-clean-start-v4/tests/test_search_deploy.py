import copy
import struct

import pytest
from fannclean.controller import REPORT_KEYS, Controller, Workspace
from fannclean.core import FILTERS, read, write
from fannclean.deploy import package, software_tree, verify_package, verify_running_code
from fannclean.fit import fit
from fannclean.postgres import check_plan, membership, verify_vm
from fannclean.search import stopping_review, structure
from test_core_engine import SyntheticBackend, policy, request
from test_model_worker import StubClient

from fannagent.api.broad_policy import FEATURES, Executable, compile_graph, start, validate


def test_generic_fitters_learn_only_supplied_run_evidence_and_emit_normal_v3():
    records = []
    for t in FILTERS:
        for i in range(40):
            safe = 10 <= i < 30
            records.append(
                {
                    "run_id": "own",
                    "request_id": "executed",
                    "query_ordinal": i + 1,
                    "checkpoint": 4,
                    "filter": t,
                    "group": f"g{i}",
                    "features": {"checkpoint": 4, "qualifying_count": i},
                    "label": {"safe": safe, "count_preserving": True},
                    "observation_schedule": [4],
                }
            )
    structures = set()
    for method in ("threshold", "linear", "tree"):
        answer = fit(
            records,
            run_id="own",
            method=method,
            features=["qualifying_count"],
            checkpoints=[4],
            min_leaf=2,
            depth=4,
        )
        artifact = validate(answer["policy"])
        assert not {"handle", "group", "label", "request_id"} & artifact.keys()
        structures.add(structure(artifact))
        assert all(r["groups"] == 40 for r in answer["validation"])
        if method == "tree":
            graph = compile_graph(artifact)
            vm = Executable(graph)
            decisions = [
                vm.step("unfiltered", 4, {"checkpoint": 4, "qualifying_count": i}, start(graph))
                for i in range(40)
            ]
            assert decisions == [10 <= i < 30 for i in range(40)]
    assert len(structures) >= 2
    with pytest.raises(ValueError, match="only this run"):
        fit(records, run_id="old", method="tree", features=["qualifying_count"], checkpoints=[4])
    with pytest.raises(ValueError, match="identical observation"):
        fit(
            records,
            run_id="own",
            method="tree",
            features=["previous_qualifying_count"],
            checkpoints=[2, 4],
        )
    with pytest.raises(ValueError, match="positive"):
        fit(
            records,
            run_id="own",
            method="tree",
            features=["qualifying_count"],
            checkpoints=[4],
            costs={"qualifying_count": 0},
        )


def test_threshold_tweaks_and_more_checkpoints_do_not_satisfy_structural_diversity():
    root = ["gt", ["feature", "qualifying_count"], 5]
    a, b = policy(root=root), policy(root=["gt", ["feature", "qualifying_count"], 99], cp=8)
    assert structure(a) == structure(b)
    dispatched = policy(
        root=[
            "if",
            ["eq", ["feature", "checkpoint"], 4],
            root,
            ["if", ["eq", ["feature", "checkpoint"], 8], root, False],
        ]
    )
    assert structure(dispatched) == structure(a)
    tree = policy(root=["and", root, ["lt", ["feature", "qualifying_count"], 10]])
    assert structure(tree) != structure(a)


def test_stopping_rejects_premature_or_unconfirmed_selection_and_allows_resource_exit(stage):
    from fannclean.core import Limits

    state = {"rounds": [], "candidates": {}}
    report = {k: "Evidence-based substantive explanation" for k in REPORT_KEYS}
    resources = {
        "discovery_queries_remaining": 10000,
        "minimum_action_queries": 28,
        "discovery_seconds_remaining": 2000,
    }
    with pytest.raises(ValueError, match="prematurely"):
        stopping_review(state, Limits(), None, report, resources)
    assert (
        stopping_review(
            state, Limits(), None, report, {**resources, "discovery_queries_remaining": 0}
        )["status"]
        == "abstained"
    )
    with pytest.raises(ValueError, match="freeze requires"):
        stopping_review(state, Limits(), "c1", report, {**resources, "model_exhausted": True})
    with pytest.raises(ValueError, match="substantive"):
        stopping_review(state, Limits(), None, {}, resources)


def test_controller_compact_feedback_contains_counterexamples_and_own_raw_files(stage, cases):
    from fannclean.engine import Engine

    class Client(StubClient):
        actions = 0

        def action(self, payload):
            self.actions += 1
            return Engine(stage, SyntheticBackend).process(f"{self.actions:032x}", payload)

    write(stage / "deployment.json", {"research_image": "sha256:" + "a" * 64})
    client = Client(stage)
    controller = Controller(stage, client)
    assert "error" in controller.call("p0", "evaluate", {"policy_paths": [], "handles": []})
    assert "error" in controller.call("p1", "plan_search", {"plan": "x" * 90, "prior": "forbidden"})
    assert controller.call(
        "p2",
        "plan_search",
        {
            "plan": "Acquire all filters, compare threshold and tree models; "
            "validate grouped recall and measure collector costs before confirmation."
        },
    )["registered"]
    write(stage / "agent/policies/bad.json", policy("lossy", cp=2))
    args = {"policy_paths": ["policies/bad.json"], "handles": request("acquire", cases)["handles"]}
    feedback = controller.call("e1", "evaluate", args)
    assert feedback["quality_failure_cases"] == 14
    assert len(feedback["counterexamples"]) == 8
    directory = stage / "agent" / feedback["complete_feedback_directory"]
    assert len(read(directory / "quality.json")["records"]) == 14
    assert read(directory / "samples.json")["records"]
    assert controller.call("e1", "evaluate", args) == feedback
    assert client.actions == 1
    with pytest.raises(ValueError, match="conflicting"):
        controller.call("e1", "evaluate", {**args, "blocks": 3})
    with pytest.raises(ValueError, match="fresh controller"):
        Controller(stage, client)


def test_controller_acquires_explores_confirms_and_freezes_single_policy(stage, cases):
    from fannclean.engine import Engine

    class Client(StubClient):
        actions = 0

        def action(self, payload):
            self.actions += 1
            return Engine(stage, SyntheticBackend).process(f"{self.actions:032x}", payload)

    write(stage / "deployment.json", {"research_image": "sha256:" + "a" * 64})
    controller = Controller(stage, Client(stage))
    assert controller.call(
        "plan",
        "plan_search",
        {
            "plan": "Acquire all conditions, compare expressions using own observations, "
            "measure collector cost and confirm every development case."
        },
    )["registered"]
    acquisition = request("acquire", cases)
    acquisition.pop("kind")
    assert controller.call("collect", "acquire", acquisition)["records_added"] == 28
    root = ["gt", ["feature", "qualifying_count"], 1]
    write(stage / "agent/policies/threshold.json", policy(root=root))
    write(
        stage / "agent/policies/interval.json",
        policy(root=["and", root, ["lt", ["feature", "qualifying_count"], 100]]),
    )
    assert "candidate_ids" in controller.call(
        "screen",
        "evaluate",
        {
            "policy_paths": ["policies/threshold.json", "policies/interval.json"],
            "handles": acquisition["handles"],
        },
    )
    assert controller.call("confirm", "confirm", {"candidate_id": "c1"})["full_quality"]
    report = {k: "Explanation grounded in this run's evidence" for k in REPORT_KEYS}
    answer = controller.call("finish", "finish", {"candidate_id": "c1", "report": report})
    assert answer["status"] == "policy_frozen"
    assert read(stage / "host/freeze.json")["policy"] == policy(root=root)
    assert not (stage / "private/comparison.json").exists()
    with pytest.raises(ValueError, match="ended"):
        controller.call("after_finish", "inspect_state", {})


def minimal_engine(root):
    source = root / "source"
    (source / "src").mkdir(parents=True)
    (source / "src/hnswutils.c").write_text('#include "broad_runtime.inc"\n')
    (source / "src/fannbench.c").write_text(
        "if (arm < 0 || (arm > 11 && !FannbenchV2ArmDeclared(arm) "
        "&& !FannbenchV3ArmDeclared(arm))) fail();\n"
    )
    for name in ("compiled_study_policies.inc", "compiled_v2.inc", "compiled_v3.inc"):
        (source / "src" / name).write_text("PRIOR_FITTED_COEFFICIENT_DO_NOT_COPY")
    (source / "old-labels.jsonl").write_text("PRIOR_EMPIRICAL_DATA_DO_NOT_COPY")
    return source


def test_packaging_neutralizes_prior_compiled_tables_and_copies_no_empirical_files(
    tmp_path, input_cases
):
    source = minimal_engine(tmp_path)
    target = tmp_path / "software"
    software_tree(source, target)
    text = "\n".join(p.read_text() for p in target.rglob("*") if p.is_file())
    assert "PRIOR_" not in text
    assert "arm != 10" in text
    assert not (target / "old-labels.jsonl").exists()
    snapshot = tmp_path / "static-db"
    snapshot.mkdir()
    (snapshot / "PG_VERSION").write_text("17\n")
    image = tmp_path / "runtime.sif"
    image.write_bytes(b"synthetic static image; never executed")
    root = tmp_path / "package"
    task = package(
        root,
        input_cases,
        source,
        snapshot,
        image,
        "sha256:" + "a" * 64,
        database_user="fixture_admin",
    )
    assert read(root / "private/backend.json")["database_user"] == "fixture_admin"
    assert task["queries"]
    verify_package(root)
    verify_running_code(root)
    assert not (root / "host").exists()
    assert not (root / "private/query-ledger.json").exists()
    assert not (root / "private/comparison.json").exists()
    software_tree(root / "private/engine", tmp_path / "twice-neutralized")
    assert sorted(p.name for p in (root / "agent/api").iterdir()) == ["broad_contract.py", "fit.py"]
    assert not (root / "agent/evidence/observations.jsonl").read_bytes()
    (root / "private/engine/src/compiled_v2.inc").write_text("tampered")
    with pytest.raises(ValueError, match="sealed"):
        verify_package(root)


def test_research_sandbox_disallows_unpinned_images_and_policy_escape(stage, monkeypatch):
    from fannclean.core import Limits

    with pytest.raises(ValueError, match="pinned"):
        Workspace(stage / "agent", "python:latest", Limits())
    workspace = Workspace(stage / "agent", "sha256:" + "a" * 64, Limits())
    with pytest.raises(ValueError, match="policies"):
        workspace.policy("task.json")
    captured = []

    def invoke(args, **kw):
        captured.append((args, kw))
        return type("Result", (), {"returncode": 0, "stdout": "fixture", "stderr": ""})()

    monkeypatch.setattr("fannclean.controller.subprocess.run", invoke)
    assert workspace.execute("print('unit fixture')", timeout=20)["exit_code"] == 0
    args, kw = captured[0]
    assert args[args.index("--network") + 1] == "none"
    assert "--read-only" in args and "--cap-drop" in args
    assert all(str(stage / "private") not in x and "ANTHROPIC_API_KEY" not in x for x in args)
    assert kw["timeout"] == 20
    assert sum(x.endswith(",readonly") for x in args) == 3


def test_runtime_parity_rejects_mutated_audit_and_verifies_fuel():
    artifact = policy(root=["gt", ["feature", "qualifying_count"], 1])
    graph = compile_graph(artifact)
    state, vm = start(graph), Executable(graph)
    values = {f: None for f in FEATURES}
    values.update(checkpoint=4, qualifying_count=2)
    assert vm.step("unfiltered", 4, values, state, collection_units=7)
    frame = {
        "checkpoint": 4,
        "mask": graph["programs"]["unfiltered"]["steps"][4]["mask"],
        "count_units": 7,
        "values": [values[f] for f in FEATURES],
        "decision": True,
        "remaining": state.remaining,
        "state": state.registers,
        "fault": False,
        "exhausted": False,
    }
    audit = {"frames": [frame]}
    verify_vm(artifact, False, -1, audit, 4)
    compiled = (graph, vm)
    verify_vm(artifact, False, -1, audit, 4, compiled)
    verify_vm(artifact, False, -1, audit, 4, compiled)  # new query-local state every call
    corrupt = copy.deepcopy(audit)
    corrupt["frames"][0]["remaining"] -= 1
    with pytest.raises(ValueError, match="decision, state or fuel"):
        verify_vm(artifact, False, -1, corrupt, 4)
    with pytest.raises(ValueError, match="continued after"):
        verify_vm(artifact, False, -1, {"frames": [frame, frame]}, 4)


def test_plans_and_fresh_membership_format_are_validated(tmp_path):
    ann = [
        {
            "Plan": {
                "Node Type": "Limit",
                "Plans": [
                    {
                        "Node Type": "Index Scan",
                        "Relation Name": "reviews",
                        "Index Name": "reviews_hnsw",
                    }
                ],
            }
        }
    ]
    exact = [
        {
            "Plan": {
                "Node Type": "Sort",
                "Plans": [{"Node Type": "Seq Scan", "Relation Name": "reviews"}],
            }
        }
    ]
    check_plan(ann, False)
    check_plan(exact, True)
    with pytest.raises(ValueError, match="sequential"):
        check_plan(ann, True)
    with pytest.raises(ValueError, match="HNSW"):
        check_plan(exact, False)
    path = tmp_path / "membership.bin"
    membership(path, 111, 222, [("(0,1)", 1000, 11), ("(0,2)", 1, 12)], 108)
    assert struct.unpack("<8sIIII", path.read_bytes()[:24]) == (b"V108MAP1", 111, 222, 2, 1)
    assert path.read_bytes()[24] == 0b0111
    assert path.stat().st_mode & 0o777 == 0o400
