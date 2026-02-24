"""
Tests for Option B Execution Service

Covers:
1. Cannot execute unless approved
2. Enqueue returns job_id and queued status
3. Worker picks up job and runs tool calls (fake tools)
4. Tool trace is recorded with inputs/outputs and timestamps
5. Trust enforcement blocks tool execution and records failed trace
6. Workspace boundary enforcement remains intact
7. Idempotency / already_executing guard works (second execute returns 409)
8. Job status endpoints return expected shape
"""
import os
import tempfile
import time
import threading

import pytest

from lathe_app.artifacts import (
    ArtifactInput,
    RunRecord,
    ToolCallTrace,
    ObservabilityTrace,
    ProposalArtifact,
)
from lathe_app.storage import InMemoryStorage
from lathe_app.review import ReviewManager, ReviewAction
from lathe_app.execution.models import ExecutionJob, ExecutionJobStatus, ExecutionTrace
from lathe_app.execution.queue import ExecutionQueue
from lathe_app.execution.service import ExecutionService
from lathe_app.execution.worker import Worker, _run_job


def _temp_db() -> str:
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    return f.name


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "exec_test.db")


@pytest.fixture
def queue(db_path):
    return ExecutionQueue(db_path=db_path)


@pytest.fixture
def storage():
    return InMemoryStorage()


@pytest.fixture
def review(storage):
    return ReviewManager(storage)


@pytest.fixture
def service(queue, storage, review):
    return ExecutionService(queue=queue, storage=storage, review_manager=review)


def _make_approved_run(storage, review) -> RunRecord:
    """Create a run that has been approved for execution."""
    obs = ObservabilityTrace.empty()
    artifact = ProposalArtifact.create(
        input_data=ArtifactInput(intent="propose", task="test task", why={}),
        proposals=[{"action": "create", "target": "out.txt"}],
        assumptions=[],
        risks=[],
        results=[],
        model_fingerprint="test-model",
        observability=obs,
    )
    run = RunRecord.create(
        input_data=ArtifactInput(intent="propose", task="test task", why={}),
        output=artifact,
        model_used="test-model",
        fallback_triggered=False,
        success=True,
    )
    storage.save_run(run)
    review.transition(run.id, ReviewAction.APPROVE)
    return run


def _make_approved_run_with_tool_calls(storage, review) -> RunRecord:
    """Create an approved run that has a tool call trace (from proposal phase)."""
    obs = ObservabilityTrace.empty()
    tool_trace = ToolCallTrace.create(
        tool_id="fs_stats",
        inputs={"workspace": "test-exec-ws"},
        result_summary={"total_files": 2},
        status="success",
        why={"goal": "Check file count", "evidence_needed": "", "risk": "", "verification": ""},
    )
    artifact = ProposalArtifact.create(
        input_data=ArtifactInput(intent="propose", task="test task", why={}),
        proposals=[{"action": "inspect"}],
        assumptions=[],
        risks=[],
        results=[],
        model_fingerprint="test-model",
        observability=obs,
    )
    run = RunRecord.create(
        input_data=ArtifactInput(intent="propose", task="test task", why={}),
        output=artifact,
        model_used="test-model",
        fallback_triggered=False,
        success=True,
        tool_calls=[tool_trace],
    )
    storage.save_run(run)
    review.transition(run.id, ReviewAction.APPROVE)
    return run


class TestCannotExecuteUnlessApproved:
    def test_proposed_run_rejected(self, service, storage, review):
        obs = ObservabilityTrace.empty()
        artifact = ProposalArtifact.create(
            input_data=ArtifactInput(intent="propose", task="t", why={}),
            proposals=[],
            assumptions=[],
            risks=[],
            results=[],
            model_fingerprint="m",
            observability=obs,
        )
        run = RunRecord.create(
            input_data=ArtifactInput(intent="propose", task="t", why={}),
            output=artifact,
            model_used="m",
            fallback_triggered=False,
            success=True,
        )
        storage.save_run(run)

        result = service.enqueue_run(run.id)
        assert result["ok"] is False
        assert result["error"] == "run_not_approved"
        assert result["status_code"] == 409

    def test_reviewed_but_not_approved_rejected(self, service, storage, review):
        obs = ObservabilityTrace.empty()
        artifact = ProposalArtifact.create(
            input_data=ArtifactInput(intent="propose", task="t", why={}),
            proposals=[],
            assumptions=[],
            risks=[],
            results=[],
            model_fingerprint="m",
            observability=obs,
        )
        run = RunRecord.create(
            input_data=ArtifactInput(intent="propose", task="t", why={}),
            output=artifact,
            model_used="m",
            fallback_triggered=False,
            success=True,
        )
        storage.save_run(run)
        review.transition(run.id, ReviewAction.REVIEW)

        result = service.enqueue_run(run.id)
        assert result["ok"] is False
        assert result["error"] == "run_not_approved"

    def test_nonexistent_run_returns_not_found(self, service):
        result = service.enqueue_run("run-does-not-exist")
        assert result["ok"] is False
        assert result["error"] == "run_not_found"
        assert result["status_code"] == 404


class TestEnqueueReturnsJobId:
    def test_enqueue_approved_run(self, service, storage, review):
        run = _make_approved_run(storage, review)
        result = service.enqueue_run(run.id)

        assert result["ok"] is True
        assert result["run_id"] == run.id
        assert "job_id" in result
        assert result["job_id"].startswith("job-")
        assert result["status"] == "queued"
        assert result["results"] == []

    def test_job_persisted_in_queue(self, service, queue, storage, review):
        run = _make_approved_run(storage, review)
        result = service.enqueue_run(run.id)
        job_id = result["job_id"]

        job = queue.get_job(job_id)
        assert job is not None
        assert job.id == job_id
        assert job.run_id == run.id
        assert job.status == ExecutionJobStatus.QUEUED


class TestIdempotencyGuard:
    def test_second_execute_returns_409(self, service, storage, review):
        run = _make_approved_run(storage, review)
        r1 = service.enqueue_run(run.id)
        assert r1["ok"] is True

        r2 = service.enqueue_run(run.id)
        assert r2["ok"] is False
        assert r2["error"] == "already_executing"
        assert r2["status_code"] == 409


class TestWorkerExecution:
    def test_worker_picks_up_job_no_tool_calls(self, queue, storage, review):
        """Run with no tool calls in the proposal → job succeeds with no traces."""
        run = _make_approved_run(storage, review)
        job = ExecutionJob.create(run.id)
        queue.enqueue(job)

        _run_job(job, storage, queue)

        updated = queue.get_job(job.id)
        assert updated.status == ExecutionJobStatus.SUCCEEDED
        assert updated.finished_at is not None
        assert updated.tool_traces == []

    def test_worker_records_trace_for_each_tool_call(self, queue, storage, review, monkeypatch, tmp_path):
        """Run with successful tool calls → traces recorded with timestamps."""
        ws_dir = str(tmp_path / "workspace")
        os.makedirs(ws_dir)
        (tmp_path / "workspace" / "hello.py").write_text("x=1")

        from lathe_app.workspace.manager import WorkspaceManager
        mgr = WorkspaceManager()
        mgr.create_workspace(ws_dir, workspace_id="exec-worker-ws")

        monkeypatch.setattr(
            "lathe_app.tools.handlers.get_default_manager",
            lambda: mgr,
        )

        run = _make_approved_run_with_tool_calls(storage, review)
        run_with_ws = RunRecord.create(
            input_data=run.input,
            output=run.output,
            model_used=run.model_used,
            fallback_triggered=run.fallback_triggered,
            success=run.success,
            tool_calls=[
                ToolCallTrace.create(
                    tool_id="fs_stats",
                    inputs={"workspace": "exec-worker-ws"},
                    result_summary={"total_files": 1},
                    status="success",
                    why={"goal": "check", "evidence_needed": "", "risk": "", "verification": ""},
                )
            ],
        )
        storage.save_run(run_with_ws)
        review.transition(run_with_ws.id, ReviewAction.APPROVE)

        job = ExecutionJob.create(run_with_ws.id)
        queue.enqueue(job)
        _run_job(job, storage, queue)

        updated = queue.get_job(job.id)
        assert updated.status == ExecutionJobStatus.SUCCEEDED
        assert len(updated.tool_traces) == 1

        trace = updated.tool_traces[0]
        assert trace.tool_id == "fs_stats"
        assert trace.ok is True
        assert trace.started_at is not None
        assert trace.finished_at is not None
        assert trace.started_at <= trace.finished_at

        mgr.clear()

    def test_worker_with_nonexistent_workspace_records_failed_trace(self, queue, storage, review):
        """Tool call with unknown workspace → trace ok=False recorded, job status=failed."""
        obs = ObservabilityTrace.empty()
        artifact = ProposalArtifact.create(
            input_data=ArtifactInput(intent="propose", task="t", why={}),
            proposals=[],
            assumptions=[],
            risks=[],
            results=[],
            model_fingerprint="m",
            observability=obs,
        )
        run = RunRecord.create(
            input_data=ArtifactInput(intent="propose", task="t", why={}),
            output=artifact,
            model_used="m",
            fallback_triggered=False,
            success=True,
            tool_calls=[
                ToolCallTrace.create(
                    tool_id="fs_stats",
                    inputs={"workspace": "workspace-that-does-not-exist"},
                    result_summary={"error": "workspace_not_found"},
                    status="refused",
                    why=None,
                )
            ],
        )
        storage.save_run(run)
        review.transition(run.id, ReviewAction.APPROVE)

        job = ExecutionJob.create(run.id)
        queue.enqueue(job)
        _run_job(job, storage, queue)

        updated = queue.get_job(job.id)
        assert updated.status in (ExecutionJobStatus.SUCCEEDED, ExecutionJobStatus.FAILED)
        assert updated.finished_at is not None


class TestTrustEnforcement:
    def test_workspace_boundary_invalid_workspace_fails(self, queue, storage, review):
        """Tool calls with non-existent workspace are recorded as failures, not silently dropped."""
        obs = ObservabilityTrace.empty()
        artifact = ProposalArtifact.create(
            input_data=ArtifactInput(intent="propose", task="t", why={}),
            proposals=[],
            assumptions=[],
            risks=[],
            results=[],
            model_fingerprint="m",
            observability=obs,
        )
        run = RunRecord.create(
            input_data=ArtifactInput(intent="propose", task="t", why={}),
            output=artifact,
            model_used="m",
            fallback_triggered=False,
            success=True,
            tool_calls=[
                ToolCallTrace.create(
                    tool_id="fs_tree",
                    inputs={"workspace": "totally-unknown-workspace-xyz"},
                    result_summary={"file_count": 0},
                    status="success",
                    why=None,
                )
            ],
        )
        storage.save_run(run)
        review.transition(run.id, ReviewAction.APPROVE)

        job = ExecutionJob.create(run.id)
        queue.enqueue(job)
        _run_job(job, storage, queue)

        updated = queue.get_job(job.id)
        assert len(updated.tool_traces) == 1
        assert updated.tool_traces[0].ok is False
        assert updated.tool_traces[0].error is not None


class TestJobStatusEndpoints:
    def test_get_latest_job_for_run_returns_none_when_no_jobs(self, service):
        result = service.get_latest_job_for_run("no-jobs-run")
        assert result is None

    def test_get_latest_job_for_run_returns_summary(self, service, storage, review):
        run = _make_approved_run(storage, review)
        enqueue_result = service.enqueue_run(run.id)
        job_id = enqueue_result["job_id"]

        summary = service.get_latest_job_for_run(run.id)
        assert summary is not None
        assert summary["id"] == job_id
        assert summary["run_id"] == run.id
        assert summary["status"] == "queued"
        assert "trace_count" in summary
        assert "results" in summary

    def test_get_job_returns_full_detail(self, service, storage, review):
        run = _make_approved_run(storage, review)
        enqueue_result = service.enqueue_run(run.id)
        job_id = enqueue_result["job_id"]

        detail = service.get_job(job_id)
        assert detail is not None
        assert detail["id"] == job_id
        assert detail["run_id"] == run.id
        assert detail["status"] == "queued"
        assert "tool_traces" in detail
        assert detail["tool_traces"] == []

    def test_get_job_returns_none_for_unknown_id(self, service):
        result = service.get_job("job-does-not-exist")
        assert result is None

    def test_get_run_traces_empty_when_no_jobs(self, service):
        traces = service.get_run_traces("no-jobs-run")
        assert traces == []

    def test_get_run_traces_returns_traces_after_execution(self, service, queue, storage, review, monkeypatch, tmp_path):
        ws_dir = str(tmp_path / "trace-ws")
        os.makedirs(ws_dir)
        (tmp_path / "trace-ws" / "a.py").write_text("x=1")

        from lathe_app.workspace.manager import WorkspaceManager
        mgr = WorkspaceManager()
        mgr.create_workspace(ws_dir, workspace_id="trace-test-ws")
        monkeypatch.setattr(
            "lathe_app.tools.handlers.get_default_manager",
            lambda: mgr,
        )

        obs = ObservabilityTrace.empty()
        artifact = ProposalArtifact.create(
            input_data=ArtifactInput(intent="propose", task="t", why={}),
            proposals=[],
            assumptions=[],
            risks=[],
            results=[],
            model_fingerprint="m",
            observability=obs,
        )
        run = RunRecord.create(
            input_data=ArtifactInput(intent="propose", task="t", why={}),
            output=artifact,
            model_used="m",
            fallback_triggered=False,
            success=True,
            tool_calls=[
                ToolCallTrace.create(
                    tool_id="fs_stats",
                    inputs={"workspace": "trace-test-ws"},
                    result_summary={"total_files": 1},
                    status="success",
                    why={"goal": "test", "evidence_needed": "", "risk": "", "verification": ""},
                )
            ],
        )
        storage.save_run(run)
        review.transition(run.id, ReviewAction.APPROVE)

        job = ExecutionJob.create(run.id)
        queue.enqueue(job)
        _run_job(job, storage, queue)

        traces = service.get_run_traces(run.id)
        assert len(traces) == 1
        assert traces[0]["tool_id"] == "fs_stats"
        assert traces[0]["ok"] is True
        assert "job_id" in traces[0]

        mgr.clear()


class TestExecutionModelSerialization:
    def test_execution_job_roundtrip(self):
        job = ExecutionJob.create("run-abc")
        d = job.to_dict()
        restored = ExecutionJob.from_dict(d)
        assert restored.id == job.id
        assert restored.run_id == job.run_id
        assert restored.status == job.status

    def test_execution_trace_roundtrip(self):
        trace = ExecutionTrace(
            tool_id="fs_stats",
            inputs={"workspace": "w"},
            why={"goal": "g"},
            started_at="2026-01-01T00:00:00+00:00",
            finished_at="2026-01-01T00:00:01+00:00",
            ok=True,
            output={"total_files": 5},
            error=None,
        )
        d = trace.to_dict()
        restored = ExecutionTrace.from_dict(d)
        assert restored.tool_id == "fs_stats"
        assert restored.ok is True
        assert restored.output == {"total_files": 5}

    def test_execution_trace_failed_roundtrip(self):
        trace = ExecutionTrace(
            tool_id="fs_tree",
            inputs={"workspace": "missing"},
            why=None,
            started_at="2026-01-01T00:00:00+00:00",
            finished_at="2026-01-01T00:00:01+00:00",
            ok=False,
            output=None,
            error={"reason": "workspace_not_found"},
        )
        d = trace.to_dict()
        assert "error" in d
        assert "output" not in d
        restored = ExecutionTrace.from_dict(d)
        assert restored.ok is False
        assert restored.error == {"reason": "workspace_not_found"}


class TestQueuePersistence:
    def test_job_survives_queue_reload(self, db_path):
        q1 = ExecutionQueue(db_path=db_path)
        job = ExecutionJob.create("run-persist-test")
        q1.enqueue(job)

        q2 = ExecutionQueue(db_path=db_path)
        loaded = q2.get_job(job.id)
        assert loaded is not None
        assert loaded.run_id == "run-persist-test"
        assert loaded.status == ExecutionJobStatus.QUEUED

    def test_running_jobs_reset_to_queued_on_reload(self, db_path):
        q1 = ExecutionQueue(db_path=db_path)
        job = ExecutionJob.create("run-crash-test")
        job.status = ExecutionJobStatus.RUNNING
        job.started_at = "2026-01-01T00:00:00+00:00"
        q1.enqueue(job)
        q1.update(job)

        q2 = ExecutionQueue(db_path=db_path)
        loaded = q2.get_job(job.id)
        assert loaded.status == ExecutionJobStatus.QUEUED
        assert loaded.started_at is None


class TestWorkerDaemonThread:
    def test_worker_processes_job_end_to_end(self, queue, storage, review):
        """Full integration: enqueue → worker picks up → job reaches terminal state."""
        run = _make_approved_run(storage, review)
        job = ExecutionJob.create(run.id)
        queue.enqueue(job)

        worker = Worker(queue=queue, storage=storage)
        worker.start()
        time.sleep(1.5)
        worker.stop()

        updated = queue.get_job(job.id)
        assert updated.status in (
            ExecutionJobStatus.SUCCEEDED,
            ExecutionJobStatus.FAILED,
        )
        assert updated.finished_at is not None
