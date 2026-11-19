import json
import mailbox

import pytest
import worker
from controller import LiveTools
from limits import Deadline, read, sha, write


class Clock:
    now = 0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


@pytest.mark.parametrize("live", [False, True])
def test_heartbeat_prevents_idle_but_cannot_extend_deadline(tmp_path, monkeypatch, live):
    clock = Clock()
    stage = tmp_path / "stage"
    run = tmp_path / "run"
    stage.mkdir()
    (run / "requests").mkdir(parents=True)
    monkeypatch.setenv("SLURM_JOB_ID", "123")
    monkeypatch.setattr(worker, "IDLE_SECONDS", 3)
    monkeypatch.setattr(worker.time, "time", lambda: clock.now)
    deadline = Deadline(clock=clock, work_seconds=10, admission_seconds=10)

    def sleep(seconds):
        if live:
            write(run / "controller-heartbeat.json", {"job_id": "123", "epoch": clock.now})
        clock.sleep(seconds)

    result = worker.serve(stage, run, deadline, {"prior_attempts": 256}, sleep=sleep, clock=clock)
    assert result["attempts"] == 256
    assert result["status"] == ("stopped_deadline" if live else "stopped_idle")
    assert clock.now <= 10


def test_status_is_read_only_and_closed_worker_cannot_be_revived(tmp_path, monkeypatch):
    (tmp_path / "job-id").write_text("123\n")
    run = tmp_path / "run-123"
    run.mkdir()
    state = {
        "job_id": "123",
        "started_epoch": 0,
        "work_seconds": 600,
        "admission_seconds": 500,
        "status": "running",
    }
    write(run / "state.json", state)
    monkeypatch.setattr(mailbox.time, "time", lambda: 100)
    mailbox.dispatch(tmp_path, "status")
    assert not (run / "controller-heartbeat.json").exists()
    assert mailbox.dispatch(tmp_path, "heartbeat")["status"] == "controller_active"
    prior = sha(run / "controller-heartbeat.json")
    state["status"] = "stopped_idle"
    write(run / "state.json", state)
    with pytest.raises(ValueError, match="closed"):
        mailbox.dispatch(tmp_path, "heartbeat")
    assert sha(run / "controller-heartbeat.json") == prior


def test_administrative_resume_preserves_prior_receipts_and_closed_state(tmp_path):
    previous = tmp_path / "prior.json"
    prior = {
        "schema": "fannagent.live-controller.v3",
        "registry": {},
        "terminal": "worker_stopped_or_admission_closed",
        "performance_claim": False,
        "receipts": {"old-tool": {"status": "complete", "signature": "old", "answer": {}}},
    }
    write(previous, prior)
    digest = sha(previous)
    tools = LiveTools.resume(
        {}, None, tmp_path / "new.json", previous, tmp_path / "workspace", "image-id"
    )
    assert tools.state["terminal"] is None
    assert tools.state["receipts"] == prior["receipts"]
    assert sha(previous) == digest
    assert read(previous)["terminal"] == "worker_stopped_or_admission_closed"
    assert tools.state["administrative_resumes"][0]["previous_state_sha256"] == digest


@pytest.mark.parametrize(
    "terminal,receipt",
    [
        ("abstained", "complete"),
        ("development_candidate_frozen", "complete"),
        ("worker_stopped_or_admission_closed", "reserved"),
    ],
)
def test_resume_rejects_final_decisions_and_uncertain_deliveries(tmp_path, terminal, receipt):
    path = tmp_path / "prior.json"
    path.write_text(json.dumps({"terminal": terminal, "receipts": {"x": {"status": receipt}}}))
    with pytest.raises(ValueError):
        LiveTools.resume({}, None, tmp_path / "new.json", path, tmp_path / "workspace", "image-id")


@pytest.mark.parametrize(
    "grant",
    [None, {"status": "authorized", "plan_sha256": "wrong", "user_approval_record": "fixture"}],
)
def test_continuation_cannot_upload_or_launch_without_matching_approval(
    tmp_path, monkeypatch, grant
):
    import remote

    write(tmp_path / "continuation-plan.json", {"status": "pending"})
    if grant:
        write(tmp_path / "continuation-authorization.json", grant)
    monkeypatch.setattr(remote, "WORK", tmp_path)

    def forbidden(*args, **kwargs):
        pytest.fail("remote operation before matching approval")

    monkeypatch.setattr(remote, "ssh", forbidden)
    with pytest.raises(ValueError, match="approval"):
        remote.launch()
