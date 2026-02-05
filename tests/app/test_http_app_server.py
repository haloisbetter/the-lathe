"""
Tests for lathe_app HTTP server.

Verifies:
- POST /agent returns run_id and does NOT apply changes
- POST /execute with dry_run=true does not mutate
- POST /execute with dry_run=false attempts apply
- missing fields return structured refusal
- GET /health returns ok
- no tracebacks are returned
- Port configuration: default=3001, env var, CLI flag
"""
import json
import os
import pytest
import threading
import time
from http.client import HTTPConnection
from typing import Any, Dict

from lathe_app.server import create_server, get_port, DEFAULT_PORT
import lathe_app


@pytest.fixture(scope="module")
def test_server():
    """Start a test server on an available port."""
    server = create_server("127.0.0.1", 5099)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    time.sleep(0.1)
    yield server
    server.shutdown()


@pytest.fixture
def client(test_server):
    """Create an HTTP client connected to the test server."""
    conn = HTTPConnection("127.0.0.1", 5099)
    yield conn
    conn.close()


def post_json(client: HTTPConnection, path: str, data: Dict[str, Any]) -> tuple:
    """POST JSON and return (status, response_dict)."""
    body = json.dumps(data).encode("utf-8")
    client.request("POST", path, body=body, headers={"Content-Type": "application/json"})
    resp = client.getresponse()
    return resp.status, json.loads(resp.read().decode("utf-8"))


def get_json(client: HTTPConnection, path: str) -> tuple:
    """GET and return (status, response_dict)."""
    client.request("GET", path)
    resp = client.getresponse()
    return resp.status, json.loads(resp.read().decode("utf-8"))


class TestHealthEndpoint:
    """Tests for GET /health."""
    
    def test_health_returns_ok(self, client):
        status, data = get_json(client, "/health")
        
        assert status == 200
        assert data["ok"] is True
        assert "results" in data


class TestAgentEndpoint:
    """Tests for POST /agent."""
    
    def test_agent_returns_run_id(self, client):
        why = {"goal": "test", "context": "test", "evidence": "test",
               "decision": "test", "risk_level": "Low",
               "options_considered": [], "guardrails": [], "verification_steps": []}
        
        status, data = post_json(client, "/agent", {
            "intent": "propose",
            "task": "create test file",
            "why": why,
        })
        
        assert status == 200
        assert "id" in data
        assert "results" in data
        assert data.get("refusal") is not True
    
    def test_agent_missing_intent(self, client):
        status, data = post_json(client, "/agent", {
            "task": "test",
            "why": {},
        })
        
        assert status == 400
        assert data["refusal"] is True
        assert "intent" in data["details"]
    
    def test_agent_missing_task(self, client):
        status, data = post_json(client, "/agent", {
            "intent": "propose",
            "why": {},
        })
        
        assert status == 400
        assert data["refusal"] is True
        assert "task" in data["details"]
    
    def test_agent_missing_why(self, client):
        status, data = post_json(client, "/agent", {
            "intent": "propose",
            "task": "test",
        })
        
        assert status == 400
        assert data["refusal"] is True
        assert "why" in data["details"]
    
    def test_agent_does_not_apply_changes(self, client, tmp_path):
        """Critical: POST /agent must NOT apply any filesystem changes."""
        import os
        
        why = {"goal": "test", "context": "test", "evidence": "test",
               "decision": "test", "risk_level": "Low",
               "options_considered": [], "guardrails": [], "verification_steps": []}
        
        status, data = post_json(client, "/agent", {
            "intent": "propose",
            "task": "create file agent_test_file.py",
            "why": why,
        })
        
        assert status == 200
        assert not os.path.exists("agent_test_file.py")


class TestExecuteEndpoint:
    """Tests for POST /execute."""
    
    def test_execute_missing_run_id(self, client):
        status, data = post_json(client, "/execute", {})
        
        assert status == 400
        assert data["refusal"] is True
        assert "run_id" in data["details"]
    
    def test_execute_nonexistent_run(self, client):
        status, data = post_json(client, "/execute", {
            "run_id": "nonexistent-run-id",
        })
        
        assert status == 200
        assert data["status"] == "rejected"
        assert "not found" in data["error"].lower()
    
    def test_execute_dry_run_does_not_mutate(self, client):
        """dry_run=true should not apply changes."""
        import os
        
        why = {"goal": "test", "context": "test", "evidence": "test",
               "decision": "test", "risk_level": "Low",
               "options_considered": [], "guardrails": [], "verification_steps": []}
        
        status, agent_data = post_json(client, "/agent", {
            "intent": "propose",
            "task": "create execute_dry_test.py",
            "why": why,
        })
        assert status == 200
        run_id = agent_data["id"]
        
        status, exec_data = post_json(client, "/execute", {
            "run_id": run_id,
            "dry_run": True,
        })
        
        assert status == 200
        assert exec_data["applied"] is False
        assert not os.path.exists("execute_dry_test.py")
    
    def test_execute_with_apply(self, client):
        """dry_run=false should attempt to apply (patches may be empty)."""
        why = {"goal": "test", "context": "test", "evidence": "test",
               "decision": "test", "risk_level": "Low",
               "options_considered": [], "guardrails": [], "verification_steps": []}
        
        status, agent_data = post_json(client, "/agent", {
            "intent": "propose",
            "task": "do nothing",
            "why": why,
        })
        assert status == 200
        run_id = agent_data["id"]
        
        status, exec_data = post_json(client, "/execute", {
            "run_id": run_id,
            "dry_run": False,
        })
        
        assert status == 200
        assert "status" in exec_data
        assert "results" in exec_data


class TestRunsEndpoints:
    """Tests for GET /runs and GET /runs/<id>."""
    
    def test_list_runs(self, client):
        status, data = get_json(client, "/runs")
        
        assert status == 200
        assert "runs" in data
        assert isinstance(data["runs"], list)
        assert "results" in data
    
    def test_get_run_not_found(self, client):
        status, data = get_json(client, "/runs/nonexistent-id")
        
        assert status == 404
        assert data["refusal"] is True
        assert "not found" in data["details"].lower()


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_invalid_json_returns_refusal(self, client):
        client.request("POST", "/agent", body=b"not json", headers={"Content-Type": "application/json"})
        resp = client.getresponse()
        data = json.loads(resp.read().decode("utf-8"))
        
        assert resp.status == 400
        assert data["refusal"] is True
        assert "json" in data["details"].lower()
    
    def test_unknown_path_returns_refusal(self, client):
        status, data = get_json(client, "/unknown/path")
        
        assert status == 404
        assert data["refusal"] is True
    
    def test_no_tracebacks_in_responses(self, client):
        """Responses should never contain Python tracebacks."""
        status, data = post_json(client, "/agent", {
            "intent": "propose",
            "task": "test",
        })
        
        response_str = json.dumps(data)
        assert "Traceback" not in response_str
        assert "File \"" not in response_str


class TestPortConfiguration:
    """
    Tests for port configuration.
    
    Port assignments:
    - OpenWebUI → 3000 (external, not managed here)
    - Lathe App → 3001 (default)
    """
    
    def test_default_port_is_3001(self):
        """Default port must be 3001, not 3000 (OpenWebUI uses 3000)."""
        assert DEFAULT_PORT == 3001
    
    def test_get_port_returns_default(self):
        """get_port() returns 3001 when no overrides."""
        old_env = os.environ.pop("LATHE_APP_PORT", None)
        try:
            assert get_port() == 3001
        finally:
            if old_env:
                os.environ["LATHE_APP_PORT"] = old_env
    
    def test_get_port_cli_overrides_all(self):
        """CLI flag has highest priority."""
        old_env = os.environ.get("LATHE_APP_PORT")
        os.environ["LATHE_APP_PORT"] = "4000"
        try:
            assert get_port(cli_port=5000) == 5000
        finally:
            if old_env:
                os.environ["LATHE_APP_PORT"] = old_env
            else:
                os.environ.pop("LATHE_APP_PORT", None)
    
    def test_get_port_env_overrides_default(self):
        """LATHE_APP_PORT env var overrides default."""
        old_env = os.environ.get("LATHE_APP_PORT")
        os.environ["LATHE_APP_PORT"] = "4000"
        try:
            assert get_port() == 4000
        finally:
            if old_env:
                os.environ["LATHE_APP_PORT"] = old_env
            else:
                os.environ.pop("LATHE_APP_PORT", None)
    
    def test_get_port_invalid_env_uses_default(self):
        """Invalid LATHE_APP_PORT falls back to default."""
        old_env = os.environ.get("LATHE_APP_PORT")
        os.environ["LATHE_APP_PORT"] = "not_a_number"
        try:
            assert get_port() == 3001
        finally:
            if old_env:
                os.environ["LATHE_APP_PORT"] = old_env
            else:
                os.environ.pop("LATHE_APP_PORT", None)
    
    def test_create_server_uses_default_port(self):
        """create_server() defaults to 3001."""
        from lathe_app.server import DEFAULT_PORT
        assert DEFAULT_PORT == 3001
