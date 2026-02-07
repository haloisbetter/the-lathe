"""
Unit tests for LatheClient.

All tests use mocked HTTP — no live server required.
No imports from lathe or lathe_app.
"""
import json
from unittest.mock import patch, MagicMock
import pytest

from lathe_tui.app.client import LatheClient, LatheClientError


@pytest.fixture
def client():
    return LatheClient(base_url="http://test:3001", timeout=5)


def _mock_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    return resp


class TestHealth:
    @patch("lathe_tui.app.client.requests.get")
    def test_health_ok(self, mock_get, client):
        mock_get.return_value = _mock_response(200, {"ok": True, "results": []})
        result = client.health()
        assert result["ok"] is True
        mock_get.assert_called_once_with(
            "http://test:3001/health", params=None, timeout=5
        )

    @patch("lathe_tui.app.client.requests.get")
    def test_health_connection_refused(self, mock_get, client):
        import requests
        mock_get.side_effect = requests.ConnectionError("refused")
        result = client.health()
        assert result["ok"] is False
        assert result["error_type"] == "connection_refused"

    @patch("lathe_tui.app.client.requests.get")
    def test_health_timeout(self, mock_get, client):
        import requests
        mock_get.side_effect = requests.Timeout("timed out")
        result = client.health()
        assert result["ok"] is False
        assert result["error_type"] == "timeout"


class TestRunsList:
    @patch("lathe_tui.app.client.requests.get")
    def test_runs_list_with_params(self, mock_get, client):
        mock_get.return_value = _mock_response(200, {"runs": [{"id": "r1"}], "total": 1})
        result = client.runs_list(params={"limit": 5, "intent": "propose"})
        assert "runs" in result
        call_kwargs = mock_get.call_args
        assert call_kwargs[1]["params"] == {"limit": 5, "intent": "propose"}

    @patch("lathe_tui.app.client.requests.get")
    def test_runs_list_empty(self, mock_get, client):
        mock_get.return_value = _mock_response(200, {"runs": [], "total": 0})
        result = client.runs_list()
        assert result["runs"] == []


class TestRunsGet:
    @patch("lathe_tui.app.client.requests.get")
    def test_get_existing_run(self, mock_get, client):
        run_data = {"id": "run-123", "intent": "propose", "success": True}
        mock_get.return_value = _mock_response(200, run_data)
        result = client.runs_get("run-123")
        assert result["id"] == "run-123"
        mock_get.assert_called_once_with(
            "http://test:3001/runs/run-123", params=None, timeout=5
        )

    @patch("lathe_tui.app.client.requests.get")
    def test_get_missing_run(self, mock_get, client):
        mock_get.return_value = _mock_response(404, {"refusal": True, "reason": "not_found"})
        result = client.runs_get("run-missing")
        assert result["ok"] is False
        assert result["missing_endpoint"] is True


class TestRunStats:
    @patch("lathe_tui.app.client.requests.get")
    def test_stats(self, mock_get, client):
        stats = {"by_intent": {"propose": 5}, "total": 5}
        mock_get.return_value = _mock_response(200, stats)
        result = client.runs_stats()
        assert result["by_intent"]["propose"] == 5


class TestReview:
    @patch("lathe_tui.app.client.requests.get")
    def test_review_get(self, mock_get, client):
        mock_get.return_value = _mock_response(200, {"state": "pending", "results": []})
        result = client.run_review_get("run-123")
        assert result["state"] == "pending"

    @patch("lathe_tui.app.client.requests.post")
    def test_review_submit(self, mock_post, client):
        mock_post.return_value = _mock_response(200, {"state": "approved"})
        result = client.review_submit("run-123", "approve", comment="looks good")
        assert result["state"] == "approved"
        call_args = mock_post.call_args
        body = call_args[1]["json"]
        assert body["run_id"] == "run-123"
        assert body["action"] == "approve"
        assert body["comment"] == "looks good"

    @patch("lathe_tui.app.client.requests.post")
    def test_review_submit_without_comment(self, mock_post, client):
        mock_post.return_value = _mock_response(200, {"state": "rejected"})
        result = client.review_submit("run-456", "reject")
        body = mock_post.call_args[1]["json"]
        assert "comment" not in body


class TestStaleness:
    @patch("lathe_tui.app.client.requests.get")
    def test_staleness_check(self, mock_get, client):
        mock_get.return_value = _mock_response(200, {
            "run_id": "r1",
            "potentially_stale": False,
            "stale_count": 0,
            "fresh_count": 3,
        })
        result = client.run_staleness_get("r1")
        assert result["potentially_stale"] is False


class TestWorkspace:
    @patch("lathe_tui.app.client.requests.get")
    def test_workspace_list(self, mock_get, client):
        mock_get.return_value = _mock_response(200, {
            "workspaces": [{"name": "proj"}],
            "count": 1,
        })
        result = client.workspace_list()
        assert len(result["workspaces"]) == 1

    @patch("lathe_tui.app.client.requests.get")
    def test_workspace_stats(self, mock_get, client):
        mock_get.return_value = _mock_response(200, {"workspace_count": 2})
        result = client.workspace_stats()
        assert result["workspace_count"] == 2


class TestFsEndpoints:
    @patch("lathe_tui.app.client.requests.get")
    def test_fs_tree(self, mock_get, client):
        mock_get.return_value = _mock_response(200, {"tree": {"name": ".", "children": []}})
        result = client.fs_tree(path="/tmp", max_depth=2)
        params = mock_get.call_args[1]["params"]
        assert params["path"] == "/tmp"
        assert params["max_depth"] == 2

    @patch("lathe_tui.app.client.requests.get")
    def test_fs_run_files(self, mock_get, client):
        mock_get.return_value = _mock_response(200, {"run_id": "r1", "files": ["a.py"]})
        result = client.fs_run_files("r1")
        assert result["files"] == ["a.py"]


class TestHealthSummary:
    @patch("lathe_tui.app.client.requests.get")
    def test_health_summary(self, mock_get, client):
        mock_get.return_value = _mock_response(200, {
            "success_rate": 0.95,
            "total_runs": 20,
            "recent_errors": [],
        })
        result = client.health_summary()
        assert result["success_rate"] == 0.95


class TestErrorHandling:
    @patch("lathe_tui.app.client.requests.get")
    def test_generic_exception(self, mock_get, client):
        mock_get.side_effect = RuntimeError("kaboom")
        result = client.health()
        assert result["ok"] is False
        assert result["error_type"] == "request_error"
        assert "kaboom" in result["message"]

    @patch("lathe_tui.app.client.requests.post")
    def test_post_connection_refused(self, mock_post, client):
        import requests
        mock_post.side_effect = requests.ConnectionError("refused")
        result = client.review_submit("r1", "approve")
        assert result["ok"] is False
        assert result["error_type"] == "connection_refused"

    @patch("lathe_tui.app.client.requests.post")
    def test_post_404(self, mock_post, client):
        mock_post.return_value = _mock_response(404, {})
        result = client.review_submit("r1", "approve")
        assert result["missing_endpoint"] is True


class TestClientConfig:
    def test_default_url(self):
        c = LatheClient()
        assert c.base_url == "http://127.0.0.1:3001"

    def test_custom_url(self):
        c = LatheClient(base_url="http://custom:9999/")
        assert c.base_url == "http://custom:9999"

    def test_custom_timeout(self):
        c = LatheClient(timeout=30)
        assert c.timeout == 30


class TestClientErrorModel:
    def test_error_to_dict(self):
        err = LatheClientError("connection_refused", "nope")
        d = err.to_dict()
        assert d["ok"] is False
        assert d["error_type"] == "connection_refused"
        assert d["message"] == "nope"


class TestNoLatheImports:
    def test_client_has_no_lathe_imports(self):
        import lathe_tui.app.client as mod
        source = open(mod.__file__).read()
        assert "import lathe." not in source
        assert "import lathe_app" not in source
        assert "from lathe." not in source
        assert "from lathe_app" not in source

    def test_tui_has_no_lathe_imports(self):
        import lathe_tui.app.tui as mod
        source = open(mod.__file__).read()
        assert "import lathe." not in source
        assert "import lathe_app" not in source
        assert "from lathe." not in source
        assert "from lathe_app" not in source

    def test_replay_has_no_lathe_imports(self):
        import lathe_tui.app.replay as mod
        source = open(mod.__file__).read()
        assert "import lathe." not in source
        assert "import lathe_app" not in source
        assert "from lathe." not in source
        assert "from lathe_app" not in source

    def test_console_has_no_lathe_imports(self):
        import lathe_tui.app.console as mod
        source = open(mod.__file__).read()
        assert "import lathe." not in source
        assert "import lathe_app" not in source
        assert "from lathe." not in source
        assert "from lathe_app" not in source

    def test_smoke_has_no_lathe_imports(self):
        import lathe_tui.tools.smoke as mod
        source = open(mod.__file__).read()
        assert "import lathe." not in source
        assert "import lathe_app" not in source
        assert "from lathe." not in source
        assert "from lathe_app" not in source
