"""
Tests to freeze the /agent HTTP contract for OpenWebUI integration.
Uses only Python standard library.
"""
import pytest
import json
import threading
import time
import urllib.request
import urllib.error
import socketserver
from lathe.server import LatheHandler

def get_ephemeral_server():
    """Start server on ephemeral port and return (server, port)."""
    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True
    
    server = ReusableTCPServer(("127.0.0.1", 0), LatheHandler)
    port = server.server_address[1]
    return server, port

def make_request(port, payload):
    """Make a POST request to the agent endpoint."""
    url = f"http://127.0.0.1:{port}/agent"
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url, 
        data=data, 
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8')) if e.read() else {}

@pytest.fixture
def agent_server():
    """Fixture to start and stop the agent server."""
    server, port = get_ephemeral_server()
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    time.sleep(0.1)  # Give server time to start
    yield port
    server.shutdown()

def test_valid_propose_request(agent_server):
    """Valid propose request returns 200 and structured response."""
    payload = {
        "intent": "propose",
        "task": "add tests",
        "why": {
            "goal": "Test contract",
            "context": "Testing",
            "evidence": "None",
            "decision": "Test",
            "risk_level": "Low",
            "options_considered": ["Option"],
            "guardrails": ["Guard"],
            "verification_steps": ["Verify"]
        }
    }
    status, body = make_request(agent_server, payload)
    
    assert status == 200
    assert isinstance(body, dict)
    # Must have either proposals OR refusal (refusal is valid)
    assert ("proposals" in body) or ("refusal" in body)
    # Must not contain traceback
    assert "Traceback" not in json.dumps(body)

def test_valid_think_request(agent_server):
    """Valid think request returns 200 and structured response."""
    payload = {
        "intent": "think",
        "task": "analyze code",
        "why": {
            "goal": "Test contract",
            "context": "Testing",
            "evidence": "None",
            "decision": "Test",
            "risk_level": "Low",
            "options_considered": ["Option"],
            "guardrails": ["Guard"],
            "verification_steps": ["Verify"]
        }
    }
    status, body = make_request(agent_server, payload)
    
    assert status == 200
    assert isinstance(body, dict)
    # Think returns proposed_plan or refusal
    assert ("proposed_plan" in body) or ("refusal" in body)
    assert "Traceback" not in json.dumps(body)

def test_valid_rag_request(agent_server):
    """Valid rag request returns 200 and structured response."""
    payload = {
        "intent": "rag",
        "task": "search",
        "why": {
            "goal": "Test contract",
            "context": "Testing",
            "evidence": "None",
            "decision": "Test",
            "risk_level": "Low",
            "options_considered": ["Option"],
            "guardrails": ["Guard"],
            "verification_steps": ["Verify"]
        }
    }
    status, body = make_request(agent_server, payload)
    
    assert status == 200
    assert isinstance(body, dict)
    # RAG returns conceptual/actionable or refusal
    assert (("conceptual" in body) and ("actionable" in body)) or ("refusal" in body)
    assert "Traceback" not in json.dumps(body)

def test_missing_fields_returns_structured_refusal(agent_server):
    """Missing required fields return structured refusal, not traceback."""
    payload = {"intent": "propose"}  # Missing task and why
    status, body = make_request(agent_server, payload)
    
    assert status == 200  # Refusal is a successful outcome
    assert "refusal" in body
    assert "Missing required fields" in body["refusal"]
    assert "Traceback" not in json.dumps(body)

def test_invalid_why_returns_structured_refusal(agent_server):
    """Invalid why object returns structured refusal."""
    payload = {
        "intent": "propose",
        "task": "test",
        "why": {"incomplete": "object"}  # Invalid structure
    }
    status, body = make_request(agent_server, payload)
    
    assert status == 200
    assert "refusal" in body
    assert "Invalid 'why' object" in body["refusal"]
    assert "Traceback" not in json.dumps(body)

def test_unknown_intent_returns_structured_refusal(agent_server):
    """Unknown intent returns structured refusal."""
    payload = {
        "intent": "unknown_intent",
        "task": "test",
        "why": {
            "goal": "Test",
            "context": "Testing",
            "evidence": "None",
            "decision": "Test",
            "risk_level": "Low",
            "options_considered": ["Option"],
            "guardrails": ["Guard"],
            "verification_steps": ["Verify"]
        }
    }
    status, body = make_request(agent_server, payload)
    
    assert status == 200
    assert "refusal" in body
    assert "Unknown intent" in body["refusal"]
    assert "Traceback" not in json.dumps(body)
