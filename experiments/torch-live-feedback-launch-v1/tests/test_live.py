import json
import subprocess
import sys
from mailbox import dispatch
from types import SimpleNamespace

import pytest
from analysis import summarize
from client import TorchClient
from controller import LiveTools
from limits import ADMISSION_SECONDS, FILTERS, SCHEMA, Deadline, digest, read, write
from worker import execute, serve, unpack_sources


class Clock:
    def __init__(self):
        self.now = 0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


@pytest.fixture
def empty_policy():
    return {
        "schema": "fannagent.filtered-ann.v2",
        "name": "test",
        "rules": {},
        "rationale": "scripted fixture only",
    }


def make_run(tmp_path, monkeypatch):
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    (tmp_path / "job-id").write_text("123\n")
    run = tmp_path / "run-123"
    run.mkdir()
    (run / "requests").mkdir()
    return run


def test_idle_worker_releases_without_a_client(tmp_path, monkeypatch):
    run = make_run(tmp_path, monkeypatch)
    clock = Clock()
    result = serve(tmp_path, run, Deadline(clock=clock), {}, sleep=clock.sleep, clock=clock)
    assert result["status"] == "stopped_idle"
    assert clock.now == 900
    assert result["completed_batches"] == 0


@pytest.mark.parametrize("kind", ["parent_path", "symlink"])
def test_source_extraction_rejects_paths_and_links_before_writing(tmp_path, kind):
    import io
    import tarfile

    path = tmp_path / "sources.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        member = tarfile.TarInfo("../outside" if kind == "parent_path" else "link")
        if kind == "symlink":
            member.type = tarfile.SYMTYPE
            member.linkname = "../outside"
            archive.addfile(member)
        else:
            member.size = 4
            archive.addfile(member, io.BytesIO(b"test"))
    destination = tmp_path / "output"
    destination.mkdir()
    with pytest.raises(ValueError, match="unsafe source archive"):
        unpack_sources(path, destination)
    assert not (tmp_path / "outside").exists()
    assert not list(destination.iterdir())


def test_admission_closes_even_with_queued_work(tmp_path, monkeypatch):
    run = make_run(tmp_path, monkeypatch)
    clock = Clock()
    deadline = Deadline(clock=clock)
    clock.now = ADMISSION_SECONDS
    queued = run / "requests" / ("a" * 32)
    queued.mkdir()
    (queued / "ready").touch()
    result = serve(tmp_path, run, deadline, {}, sleep=clock.sleep, clock=clock)
    assert result["status"] == "stopped_deadline"
    assert (queued / "ready").is_file()


def test_same_request_is_not_reexecuted_and_conflicts_fail(tmp_path, monkeypatch, empty_policy):
    run = make_run(tmp_path, monkeypatch)
    import time

    write(
        run / "state.json",
        {
            "status": "running",
            "job_id": "123",
            "started_epoch": time.time(),
            "work_seconds": 20400,
            "admission_seconds": 18900,
        },
    )
    payload = {"schema": SCHEMA, "policies": [empty_policy]}
    identity = "a" * 32
    assert dispatch(tmp_path, "submit", identity, payload)["status"] == "registered"
    assert dispatch(tmp_path, "submit", identity, payload)["status"] == "already_registered"
    assert len(list((run / "requests").iterdir())) == 1
    with pytest.raises(ValueError, match="another payload"):
        dispatch(tmp_path, "submit", identity, {"schema": SCHEMA, "policies": [empty_policy] * 2})


def test_mailbox_checks_deadline_without_a_worker_heartbeat(tmp_path, monkeypatch, empty_policy):
    run = make_run(tmp_path, monkeypatch)
    write(
        run / "state.json",
        {
            "status": "running",
            "job_id": "123",
            "started_epoch": 0,
            "work_seconds": 20400,
            "admission_seconds": 18900,
        },
    )
    with pytest.raises(ValueError, match="not accepting"):
        dispatch(tmp_path, "submit", "a" * 32, {"schema": SCHEMA, "policies": [empty_policy]})


def test_worker_stops_after_first_native_failure(tmp_path, monkeypatch, empty_policy):
    run = make_run(tmp_path, monkeypatch)
    for identity in ("a" * 32, "b" * 32):
        folder = run / "requests" / identity
        folder.mkdir()
        payload = {"schema": SCHEMA, "policies": [empty_policy]}
        write(
            folder / "request.json",
            {
                "job_id": "123",
                "request_id": identity,
                "payload": payload,
                "payload_sha256": digest(payload),
            },
        )
        (folder / "ready").touch()
    calls = []

    def fail(command, log, timeout):
        calls.append(command)
        assert timeout <= 20400
        return 1

    clock = Clock()
    result = serve(
        tmp_path,
        run,
        Deadline(clock=clock),
        {"image": "/image", "bundle": "/bundle", "prepared": "/prepared"},
        execute_fn=fail,
        sleep=clock.sleep,
        clock=clock,
    )
    assert result["status"] == "stopped_batch_failure"
    assert len(calls) == 1
    assert (run / "requests" / ("b" * 32) / "ready").exists()
    assert read(run / "requests" / ("a" * 32) / "response.json")["automatic_retry"] is False


def test_provisional_native_result_is_not_delivered_before_cleanup(
    tmp_path, monkeypatch, empty_policy
):
    run = make_run(tmp_path, monkeypatch)
    identity = "a" * 32
    batch = run / "requests" / identity
    batch.mkdir()
    payload = {"schema": SCHEMA, "policies": [empty_policy]}
    write(
        batch / "request.json",
        {
            "job_id": "123",
            "request_id": identity,
            "payload": payload,
            "payload_sha256": digest(payload),
        },
    )
    (batch / "ready").touch()
    calls = []

    def finish(command, log, timeout):
        calls.append(command)
        if len(calls) == 2:
            write(
                batch / "native-response.json",
                {"status": "measured", "request_id": identity, "private_cleanup_verified": True},
            )
            assert dispatch(tmp_path, "result", identity)["status"] == "pending"
            (batch / "work/.torch-owned").write_text("123\n")
            (batch / "results").mkdir()
            write(batch / "attempts.json", {"total": 10})
        return 0

    clock = Clock()
    state = serve(
        tmp_path,
        run,
        Deadline(clock=clock),
        {"image": "/image", "bundle": "/bundle", "prepared": "/prepared"},
        execute_fn=finish,
        sleep=clock.sleep,
        clock=clock,
    )
    assert state["status"] == "stopped_idle"
    assert state["attempts"] == 10
    assert not (batch / "work").exists()
    assert dispatch(tmp_path, "result", identity)["status"] == "measured"


def test_subprocess_timeout_terminates_the_worker_process(tmp_path):
    with pytest.raises(subprocess.TimeoutExpired):
        execute(
            [sys.executable, "-c", "import time; print('started',flush=True); time.sleep(30)"],
            tmp_path / "log",
            1,
        )
    assert "started" in (tmp_path / "log").read_text()


def test_client_persists_uncertain_identity_and_does_not_retry(tmp_path, empty_policy):
    calls = []

    def lost(*args, **kwargs):
        calls.append(args)
        raise subprocess.TimeoutExpired("ssh", 30)

    client = TorchClient("torch", "/scratch/live", tmp_path, invoke=lost)
    with pytest.raises(subprocess.TimeoutExpired):
        client.evaluate([empty_policy], identity="a" * 32)
    assert read(tmp_path / (("a" * 32) + ".json"))["status"] == "delivery_not_confirmed"
    with pytest.raises(ValueError, match="already exists"):
        client.evaluate([empty_policy], identity="a" * 32)
    assert len(calls) == 1


def test_client_rejects_other_candidate_receipt(tmp_path, empty_policy):
    results = iter([{"status": "registered"}, {"status": "measured", "request_id": "b" * 32}])

    def invoke(*args, **kwargs):
        return SimpleNamespace(returncode=0, stdout=json.dumps(next(results)))

    client = TorchClient("torch", "/scratch/live", tmp_path, invoke=invoke)
    with pytest.raises(ValueError, match="another request"):
        client.evaluate([empty_policy], identity="a" * 32)


def fixture_measurements():
    families = ("native640", "candidate1", "matched1", "empty")
    quality, timing = [], []
    for group in range(3):
        for t in FILTERS:
            condition = "unfiltered" if t < 0 else "votes" + str(t)
            qid = f"q-{group}-{condition}"
            quality.append(
                {
                    "filter": t,
                    "results": {
                        name: {"recall": 0.9, "checkpoint": 16 if name == "candidate1" else 0}
                        for name in families
                    },
                }
            )
            for name in families:
                for _ in range(8):
                    timing.append(
                        {
                            "id": qid,
                            "filter": t,
                            "family": name,
                            "request_ns": 90 if name == "candidate1" else 100,
                        }
                    )
    return families, quality, timing


def test_measured_screen_preserves_all_filters_and_matched_pairing():
    families, quality, timing = fixture_measurements()
    result = summarize(quality, timing, families, draws=100)
    assert result["latency"]["candidate1"]["scalar_ratio_to_native"] == 0.9
    assert result["latency"]["candidate1"]["scalar_ratio_to_matched"] == 0.9
    assert set(result["latency"]["candidate1"]["per_filter_ratio_to_native"]) == {
        str(t) for t in FILTERS
    }
    assert result["performance_claim"] is False
    with pytest.raises(ValueError, match="incomplete balanced"):
        summarize(quality, timing[:-1], families, draws=100)


def test_live_controller_two_rounds_without_cost_estimation(tmp_path, empty_policy):
    families, quality, timing = fixture_measurements()
    result = {"status": "measured", "feedback": summarize(quality, timing, families, draws=100)}
    calls = []

    class Client:
        def evaluate(self, policies, *, identity):
            calls.append(identity)
            return result

    tools = LiveTools(None, Client(), tmp_path / "controller.json")
    answer = tools.call("first", "evaluate_candidates", {"policies": [empty_policy]})
    assert tools.call("first", "evaluate_candidates", {"policies": [empty_policy]}) == answer
    assert len(calls) == 1
    assert tools.eligible("candidate-1")
    final = tools.call(
        "second", "submit_or_abstain", {"candidate_ids": ["candidate-1"], "abstain": False}
    )
    assert final["status"] == "development_nominees_frozen"
    assert "cost_estimate" not in read(tmp_path / "controller.json")["registry"]["candidate-1"]


def test_continue_control_gap_cannot_manufacture_a_winner(tmp_path):
    families, quality, timing = fixture_measurements()
    for row in timing:
        if row["family"] == "empty":
            row["request_ns"] = 80
    tools = LiveTools(None, None, tmp_path / "controller.json")
    tools.state["registry"]["candidate-1"] = {
        "status": "measured",
        "remote_family": "candidate1",
        "result": {"feedback": summarize(quality, timing, families, draws=100)},
    }
    assert not tools.eligible("candidate-1")


def test_unapproved_paid_run_stops_before_preflight_or_credentials(tmp_path):
    from run_agent import run

    write(tmp_path / "review.json", {"status": "prepared"})
    write(tmp_path / "approval.json", {"status": "pending"})
    with pytest.raises(ValueError, match="approval does not match"):
        run(tmp_path, tmp_path / "approval.json")
    assert not (tmp_path / "live").exists()


def test_model_loop_uses_dollars_and_live_worker_instead_of_request_ceiling(tmp_path):
    from decimal import Decimal

    from run_agent import Budget, ModelConfig, Store, drive

    class Client:
        def call(self, operation):
            assert operation == "status"
            return {"status": "running", "accepting_requests": True}

    class Evidence:
        def summary(self):
            return {"per_filter": {}}

    class Provider:
        ordinal = 0

        def count(self, request):
            self.ordinal += 1

        def __call__(self, request):
            closing = self.ordinal == 17
            return {
                "model": "scripted",
                "usage": {"input_tokens": 100, "output_tokens": 20},
                "content": [
                    {
                        "type": "tool_use",
                        "id": f"tool-{self.ordinal}",
                        "name": "submit_or_abstain" if closing else "inspect_workload",
                        "input": {"candidate_ids": [], "abstain": True} if closing else {},
                    }
                ],
            }

    model = ModelConfig(
        model="scripted",
        ceiling_usd=Decimal("15"),
        allowance_usd=Decimal("0"),
        input_usd_per_million=Decimal("2"),
        output_usd_per_million=Decimal("10"),
        input_token_bound=1000000,
        output_token_limit=6000,
        bound_verified=True,
    )
    store = Store(tmp_path / "store", create=True)
    tools = LiveTools(Evidence(), Client(), tmp_path / "tools.json")
    provider = Provider()
    result = drive(tools, store, Budget(store, model), {"messages": []}, provider)
    assert result["status"] == "abstained"
    assert provider.ordinal == 17
    assert len(result["budget"]["calls"]) == 17
    assert not result["budget"]["uncertain_calls"]


def test_model_dispatch_stops_when_the_torch_worker_stops(tmp_path):
    from decimal import Decimal

    from run_agent import Budget, ModelConfig, Store, drive

    class Client:
        def call(self, operation):
            return {"status": "stopped_idle", "accepting_requests": False}

    class Provider:
        def count(self, request):
            pytest.fail("stopped allocation must not cause another provider request")

    store = Store(tmp_path / "store", create=True)
    model = ModelConfig(model="scripted", ceiling_usd=Decimal("15"), allowance_usd=Decimal("0"))
    tools = LiveTools(None, Client(), tmp_path / "tools.json")
    result = drive(tools, store, Budget(store, model), {"messages": []}, Provider())
    assert result["status"] == "worker_stopped_or_admission_closed"
    assert not result["budget"]["calls"]


def test_uncertain_provider_delivery_keeps_its_charge_and_never_retries(tmp_path):
    from decimal import Decimal

    from run_agent import Budget, ModelConfig, Store, drive

    class Client:
        def call(self, operation):
            return {"status": "running", "accepting_requests": True}

    class Provider:
        calls = 0

        def count(self, request):
            pass

        def __call__(self, request):
            self.calls += 1
            raise OSError("delivery outcome unknown")

    store = Store(tmp_path / "store", create=True)
    model = ModelConfig(
        model="scripted",
        ceiling_usd=Decimal("15"),
        allowance_usd=Decimal("0"),
        input_usd_per_million=Decimal("2"),
        output_usd_per_million=Decimal("10"),
        input_token_bound=1000000,
        output_token_limit=6000,
        bound_verified=True,
    )
    budget = Budget(store, model)
    tools = LiveTools(None, Client(), tmp_path / "tools.json")
    provider = Provider()
    with pytest.raises(OSError, match="unknown"):
        drive(tools, store, budget, {"messages": []}, provider)
    assert provider.calls == 1
    assert budget.summary()["uncertain_calls"] == 1
    assert Decimal(budget.summary()["committed_usd"]) == Decimal("2.06")
