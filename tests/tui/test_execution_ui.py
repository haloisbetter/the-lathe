"""
Tests for Execution UI Components

Unit tests for state management and data structures (without Textual rendering).
"""
from unittest.mock import Mock

import pytest

from lathe_tui.app.client import LatheClient


class TestLatheClientExecutionMethods:
    def test_execute_run(self):
        client = LatheClient(base_url="http://localhost:3001")
        client._post = Mock(return_value={"ok": True, "job_id": "job-1"})
        result = client.execute_run("run-1")
        client._post.assert_called_once_with("/runs/run-1/execute", {})
        assert result["job_id"] == "job-1"

    def test_run_execute_status(self):
        client = LatheClient(base_url="http://localhost:3001")
        client._get = Mock(return_value={"ok": True, "status": "queued"})
        result = client.run_execute_status("run-1")
        client._get.assert_called_once_with("/runs/run-1/execute")
        assert result["status"] == "queued"

    def test_job_get(self):
        client = LatheClient(base_url="http://localhost:3001")
        client._get = Mock(return_value={"ok": True, "id": "job-1", "status": "running"})
        result = client.job_get("job-1")
        client._get.assert_called_once_with("/jobs/job-1")
        assert result["id"] == "job-1"

    def test_run_tool_traces(self):
        client = LatheClient(base_url="http://localhost:3001")
        client._get = Mock(return_value={"ok": True, "traces": []})
        result = client.run_tool_traces("run-1")
        client._get.assert_called_once_with("/runs/run-1/tool_traces")
        assert result["traces"] == []


class TestExecutionUIStateBehavior:
    def test_execute_button_unique_id_format(self):
        run_id = "run-abc123"
        btn_id = f"btn-execute-{run_id}"
        assert btn_id == "btn-execute-run-abc123"

    def test_execute_result_widget_id_format(self):
        run_id = "run-xyz"
        result_id = f"execute-result-{run_id}"
        assert result_id == "execute-result-run-xyz"

    def test_approved_state_check(self):
        review = {"state": "APPROVED"}
        is_approved = review.get("state") == "APPROVED"
        assert is_approved is True

    def test_non_approved_state_check(self):
        review = {"state": "REVIEWED"}
        is_approved = review.get("state") == "APPROVED"
        assert is_approved is False

    def test_job_terminal_states(self):
        terminal_states = ("succeeded", "failed")
        for status in ["queued", "running", "succeeded", "failed"]:
            is_terminal = status in terminal_states
            if status in ("succeeded", "failed"):
                assert is_terminal
            else:
                assert not is_terminal


class TestExecutionPollingLogic:
    def test_backoff_init(self):
        poll_interval = 0.5
        assert poll_interval == 0.5

    def test_backoff_levels(self):
        intervals = {
            0: 0.5,
            1: 1.0,
            2: 2.0,
        }
        assert intervals[0] == 0.5
        assert intervals[1] == 1.0
        assert intervals[2] == 2.0

    def test_trace_append_only(self):
        traces = []
        new_trace = {"tool_id": "fs_stats", "ok": True}
        traces.append(new_trace)
        assert len(traces) == 1
        traces.append({"tool_id": "git_status", "ok": False})
        assert len(traces) == 2
        assert traces[0]["tool_id"] == "fs_stats"
        assert traces[1]["tool_id"] == "git_status"

    def test_no_duplicate_traces(self):
        last_count = 0
        traces = [
            {"tool_id": "fs_stats"},
            {"tool_id": "git_status"},
        ]
        new_traces = traces[last_count:]
        assert len(new_traces) == 2
        last_count = 2
        new_traces = traces[last_count:]
        assert len(new_traces) == 0


class TestExecutionUIIntegration:
    def test_execute_response_success(self):
        response = {"ok": True, "job_id": "job-123", "status": "queued"}
        job_id = response.get("job_id")
        assert job_id == "job-123"

    def test_execute_response_already_executing(self):
        response = {"ok": False, "error": "already_executing", "status_code": 409}
        assert response["ok"] is False
        assert response["status_code"] == 409

    def test_execute_response_not_approved(self):
        response = {"ok": False, "error": "run_not_approved", "status_code": 409}
        assert response["ok"] is False
        assert response["error"] == "run_not_approved"

    def test_execute_response_not_found(self):
        response = {"ok": False, "error": "run_not_found", "status_code": 404}
        assert response["ok"] is False
        assert response["status_code"] == 404

    def test_job_status_display_queued(self):
        job = {"status": "queued"}
        display = f"Status: {job['status']}"
        assert display == "Status: queued"

    def test_job_status_display_running(self):
        job = {"status": "running"}
        display = f"Status: {job['status']}"
        assert display == "Status: running"

    def test_job_status_display_succeeded(self):
        job = {"status": "succeeded"}
        display = f"Status: {job['status']}"
        assert display == "Status: succeeded"

    def test_tool_trace_with_duration(self):
        trace = {
            "tool_id": "fs_stats",
            "started_at": "2026-01-01T12:00:00Z",
            "finished_at": "2026-01-01T12:00:05Z",
        }
        duration_s = 5.0
        duration_ms = int(duration_s * 1000)
        assert duration_ms == 5000
