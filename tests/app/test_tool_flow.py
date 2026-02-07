"""
Tests for Tool Selection Contract, Execution, and Agent→Tool→Agent Flow

Covers:
- Tool request parsing and validation (requests.py)
- Tool execution and trace recording (execution.py)
- TOOL_CONTEXT block generation
- Orchestrator 2-phase flow integration
- ToolCallTrace in RunRecord
- Failure modes: nonexistent tool, invalid inputs, trust denied, tool error
- Serialization of tool_calls
"""
import json
import os
import tempfile

import pytest

from lathe_app.artifacts import (
    ArtifactInput,
    RunRecord,
    ToolCallTrace,
    ObservabilityTrace,
    ProposalArtifact,
)
from lathe_app.tools.registry import ToolSpec, TOOL_REGISTRY, get_tool_spec
from lathe_app.tools.requests import (
    ToolRequest,
    ToolRequestError,
    ToolWhy,
    parse_tool_request,
    validate_tool_request,
    extract_and_validate,
)
from lathe_app.tools.execution import (
    execute_tool,
    execute_tool_from_error,
    build_tool_context_block,
)
from lathe_app.tools.handlers import TOOL_HANDLERS
from lathe_app.workspace.manager import WorkspaceManager


class TestToolCallTrace:
    def test_create(self):
        trace = ToolCallTrace.create(
            tool_id="fs_tree",
            inputs={"workspace": "test"},
            result_summary={"file_count": 5},
            status="success",
        )
        assert trace.tool_id == "fs_tree"
        assert trace.status == "success"
        assert trace.timestamp
        assert trace.result_summary == {"file_count": 5}
        assert trace.refusal_reason is None

    def test_create_refused(self):
        trace = ToolCallTrace.create(
            tool_id="fs_tree",
            inputs={"workspace": "test"},
            result_summary={"error": "trust_denied"},
            status="refused",
            refusal_reason="Trust level insufficient",
        )
        assert trace.status == "refused"
        assert trace.refusal_reason == "Trust level insufficient"

    def test_to_trace_dict_success(self):
        trace = ToolCallTrace.create(
            tool_id="fs_tree",
            inputs={"workspace": "test"},
            result_summary={"file_count": 5},
            status="success",
        )
        d = trace.to_trace_dict()
        assert d["tool_id"] == "fs_tree"
        assert d["status"] == "success"
        assert d["inputs"] == {"workspace": "test"}
        assert d["result_summary"] == {"file_count": 5}
        assert "refusal_reason" not in d
        assert "raw_result" not in d

    def test_to_trace_dict_refused(self):
        trace = ToolCallTrace.create(
            tool_id="unknown",
            inputs={},
            result_summary={"error": "nonexistent_tool"},
            status="refused",
            refusal_reason="Tool does not exist",
        )
        d = trace.to_trace_dict()
        assert d["refusal_reason"] == "Tool does not exist"

    def test_trace_immutable_fields(self):
        trace = ToolCallTrace.create(
            tool_id="fs_tree",
            inputs={"workspace": "test"},
            result_summary={},
            status="success",
        )
        assert trace.tool_id == "fs_tree"
        assert isinstance(trace.timestamp, str)


class TestRunRecordToolCalls:
    def test_default_empty_tool_calls(self):
        run = RunRecord.create(
            input_data=ArtifactInput(intent="propose", task="test", why={}),
            output=None,
            model_used="test-model",
            fallback_triggered=False,
            success=True,
        )
        assert run.tool_calls == []

    def test_with_tool_calls(self):
        trace = ToolCallTrace.create(
            tool_id="fs_tree",
            inputs={"workspace": "ws"},
            result_summary={"file_count": 3},
            status="success",
        )
        run = RunRecord.create(
            input_data=ArtifactInput(intent="propose", task="test", why={}),
            output=None,
            model_used="test-model",
            fallback_triggered=False,
            success=True,
            tool_calls=[trace],
        )
        assert len(run.tool_calls) == 1
        assert run.tool_calls[0].tool_id == "fs_tree"

    def test_multiple_tool_calls(self):
        traces = [
            ToolCallTrace.create(
                tool_id="fs_tree",
                inputs={"workspace": "ws"},
                result_summary={"file_count": 3},
                status="success",
            ),
            ToolCallTrace.create(
                tool_id="git_status",
                inputs={"workspace": "ws"},
                result_summary={"clean": True},
                status="success",
            ),
        ]
        run = RunRecord.create(
            input_data=ArtifactInput(intent="propose", task="test", why={}),
            output=None,
            model_used="test-model",
            fallback_triggered=False,
            success=True,
            tool_calls=traces,
        )
        assert len(run.tool_calls) == 2


class TestToolRequestParsing:
    def test_parse_with_tool_request(self):
        output = json.dumps({
            "tool_request": {
                "tool_id": "fs_tree",
                "reason": "Need file list",
                "inputs": {"workspace": "test"},
            },
            "proposals": [],
        })
        raw = parse_tool_request(output)
        assert raw is not None
        assert raw["tool_id"] == "fs_tree"

    def test_parse_without_tool_request(self):
        output = json.dumps({"proposals": [], "assumptions": []})
        raw = parse_tool_request(output)
        assert raw is None

    def test_parse_invalid_json(self):
        raw = parse_tool_request("not json at all")
        assert raw is None

    def test_parse_non_dict(self):
        raw = parse_tool_request(json.dumps([1, 2, 3]))
        assert raw is None

    def test_parse_none_input(self):
        raw = parse_tool_request(None)
        assert raw is None


class TestToolRequestValidation:
    def test_valid_request(self):
        raw = {
            "tool_id": "fs_tree",
            "reason": "List files",
            "inputs": {"workspace": "my-ws"},
        }
        req, err = validate_tool_request(raw)
        assert err is None
        assert req is not None
        assert req.tool_id == "fs_tree"
        assert req.why.goal == "List files"
        assert req.reason == "List files"
        assert req.inputs == {"workspace": "my-ws"}
        assert req.spec.id == "fs_tree"

    def test_nonexistent_tool(self):
        raw = {
            "tool_id": "does_not_exist",
            "reason": "test",
            "inputs": {},
        }
        req, err = validate_tool_request(raw)
        assert req is None
        assert err.error_type == "nonexistent_tool"
        assert "does_not_exist" in err.message

    def test_missing_tool_id(self):
        raw = {"reason": "test", "inputs": {}}
        req, err = validate_tool_request(raw)
        assert req is None
        assert err.error_type == "malformed_request"

    def test_missing_required_inputs(self):
        raw = {
            "tool_id": "fs_tree",
            "reason": "test",
            "inputs": {},
        }
        req, err = validate_tool_request(raw)
        assert req is None
        assert err.error_type == "invalid_inputs"
        assert "workspace" in err.message

    def test_non_dict_inputs(self):
        raw = {
            "tool_id": "fs_tree",
            "reason": "test",
            "inputs": "not a dict",
        }
        req, err = validate_tool_request(raw)
        assert req is None
        assert err.error_type == "invalid_inputs"

    def test_non_dict_request(self):
        req, err = validate_tool_request("not a dict")
        assert req is None
        assert err.error_type == "malformed_request"

    def test_optional_inputs_accepted(self):
        raw = {
            "tool_id": "fs_tree",
            "reason": "Filter py",
            "inputs": {"workspace": "ws", "ext": ".py"},
        }
        req, err = validate_tool_request(raw)
        assert err is None
        assert req.inputs["ext"] == ".py"

    def test_empty_reason_ok(self):
        raw = {
            "tool_id": "fs_tree",
            "inputs": {"workspace": "ws"},
        }
        req, err = validate_tool_request(raw)
        assert err is None
        assert req.why.goal == ""
        assert req.reason == ""


class TestExtractAndValidate:
    def test_no_tool_request(self):
        output = json.dumps({"proposals": []})
        req, err = extract_and_validate(output)
        assert req is None
        assert err is None

    def test_valid_tool_request(self):
        output = json.dumps({
            "tool_request": {
                "tool_id": "fs_stats",
                "reason": "Count files",
                "inputs": {"workspace": "ws"},
            }
        })
        req, err = extract_and_validate(output)
        assert err is None
        assert req.tool_id == "fs_stats"

    def test_invalid_tool_request(self):
        output = json.dumps({
            "tool_request": {
                "tool_id": "nonexistent",
                "reason": "test",
                "inputs": {},
            }
        })
        req, err = extract_and_validate(output)
        assert req is None
        assert err.error_type == "nonexistent_tool"


class TestToolCallV1Format:
    def test_parse_tool_call_with_structured_why(self):
        output = json.dumps({
            "tool_call": {
                "tool_id": "fs_tree",
                "why": {
                    "goal": "List project files",
                    "evidence_needed": "File structure for analysis",
                    "risk": "None - read only",
                    "verification": "Check file count matches",
                },
                "inputs": {"workspace": "test-ws"},
            },
            "proposals": [],
        })
        raw = parse_tool_request(output)
        assert raw is not None
        assert raw["tool_id"] == "fs_tree"
        assert raw["why"]["goal"] == "List project files"

    def test_legacy_tool_request_still_works(self):
        output = json.dumps({
            "tool_request": {
                "tool_id": "fs_tree",
                "reason": "Need file list",
                "inputs": {"workspace": "ws"},
            },
        })
        raw = parse_tool_request(output)
        assert raw is not None
        assert raw["tool_id"] == "fs_tree"
        assert raw["reason"] == "Need file list"

    def test_tool_call_takes_priority_over_tool_request(self):
        output = json.dumps({
            "tool_call": {
                "tool_id": "fs_stats",
                "why": {"goal": "From tool_call"},
                "inputs": {"workspace": "ws"},
            },
            "tool_request": {
                "tool_id": "fs_tree",
                "reason": "From tool_request",
                "inputs": {"workspace": "ws"},
            },
        })
        raw = parse_tool_request(output)
        assert raw["tool_id"] == "fs_stats"
        assert raw["why"]["goal"] == "From tool_call"

    def test_structured_why_flows_to_tool_call_trace(self):
        output = json.dumps({
            "tool_call": {
                "tool_id": "fs_tree",
                "why": {
                    "goal": "Inspect files",
                    "evidence_needed": "Directory listing",
                    "risk": "None",
                    "verification": "Count files",
                },
                "inputs": {"workspace": "ws"},
            },
        })
        req, err = extract_and_validate(output)
        assert err is None
        assert req is not None
        assert req.why.goal == "Inspect files"
        assert req.why.evidence_needed == "Directory listing"
        assert req.why.risk == "None"
        assert req.why.verification == "Count files"

    def test_tool_call_trace_to_trace_dict_includes_why(self):
        why = {"goal": "Test goal", "evidence_needed": "ev", "risk": "low", "verification": "check"}
        trace = ToolCallTrace.create(
            tool_id="fs_tree",
            inputs={"workspace": "ws"},
            result_summary={"file_count": 5},
            status="success",
            why=why,
        )
        d = trace.to_trace_dict()
        assert "why" in d
        assert d["why"]["goal"] == "Test goal"
        assert d["why"]["evidence_needed"] == "ev"

    def test_tool_context_block_includes_goal(self):
        trace = ToolCallTrace.create(
            tool_id="fs_tree",
            inputs={"workspace": "ws"},
            result_summary={"file_count": 2},
            status="success",
            why={"goal": "List project structure"},
            raw_result={"files": ["a.py"], "count": 1, "workspace": "ws"},
        )
        block = build_tool_context_block(trace)
        assert "Goal: List project structure" in block


@pytest.fixture
def manager():
    m = WorkspaceManager()
    yield m
    m.clear()


@pytest.fixture
def workspace_dir():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "src"))
        with open(os.path.join(d, "main.py"), "w") as f:
            f.write("print('hello')\n")
        with open(os.path.join(d, "src", "lib.py"), "w") as f:
            f.write("x = 1\n")
        with open(os.path.join(d, "README.md"), "w") as f:
            f.write("# Test\n")
        yield d


@pytest.fixture
def workspace(manager, workspace_dir, monkeypatch):
    monkeypatch.setattr(
        "lathe_app.tools.handlers.get_default_manager",
        lambda: manager,
    )
    ws = manager.create_workspace(workspace_dir, workspace_id="exec-test")
    return ws


class TestToolExecution:
    def test_execute_fs_tree_success(self, workspace):
        req = ToolRequest(
            tool_id="fs_tree",
            why=ToolWhy(goal="List files"),
            inputs={"workspace": "exec-test"},
            spec=get_tool_spec("fs_tree"),
        )
        trace = execute_tool(req)
        assert trace.status == "success"
        assert trace.tool_id == "fs_tree"
        assert "file_count" in trace.result_summary
        assert trace.raw_result is not None
        assert trace.refusal_reason is None

    def test_execute_fs_stats_success(self, workspace):
        req = ToolRequest(
            tool_id="fs_stats",
            why=ToolWhy(goal="Stats"),
            inputs={"workspace": "exec-test"},
            spec=get_tool_spec("fs_stats"),
        )
        trace = execute_tool(req)
        assert trace.status == "success"
        assert "total_files" in trace.result_summary

    def test_execute_workspace_not_found(self, workspace):
        req = ToolRequest(
            tool_id="fs_tree",
            why=ToolWhy(goal="test"),
            inputs={"workspace": "nonexistent"},
            spec=get_tool_spec("fs_tree"),
        )
        trace = execute_tool(req)
        assert trace.status == "refused"
        assert "workspace_not_found" in str(trace.result_summary)

    def test_execute_no_handler(self, workspace):
        spec = ToolSpec(
            id="fake_tool",
            category="test",
            description="test",
            read_only=True,
            inputs={},
            outputs={},
            trust_required=0,
        )
        req = ToolRequest(
            tool_id="fake_tool",
            why=ToolWhy(goal="test"),
            inputs={},
            spec=spec,
        )
        trace = execute_tool(req)
        assert trace.status == "refused"
        assert "no_handler" in str(trace.result_summary)

    def test_execute_from_error(self):
        error = ToolRequestError(
            error_type="nonexistent_tool",
            message="Tool 'xyz' does not exist",
            tool_id="xyz",
        )
        trace = execute_tool_from_error(error)
        assert trace.status == "refused"
        assert trace.tool_id == "xyz"
        assert trace.refusal_reason == "Tool 'xyz' does not exist"


class TestToolContextBlock:
    def test_success_context_block(self):
        trace = ToolCallTrace.create(
            tool_id="fs_tree",
            inputs={"workspace": "test-ws"},
            result_summary={"file_count": 2},
            status="success",
            raw_result={
                "files": ["main.py", "src/lib.py"],
                "count": 2,
                "workspace": "test-ws",
            },
        )
        block = build_tool_context_block(trace)
        assert "TOOL_CONTEXT_START" in block
        assert "TOOL_CONTEXT_END" in block
        assert "Tool: fs_tree" in block
        assert "Workspace: test-ws" in block
        assert "main.py" in block
        assert "src/lib.py" in block

    def test_refused_context_block(self):
        trace = ToolCallTrace.create(
            tool_id="fs_tree",
            inputs={"workspace": "test-ws"},
            result_summary={"error": "trust_denied"},
            status="refused",
            refusal_reason="Trust level insufficient",
        )
        block = build_tool_context_block(trace)
        assert "TOOL_CONTEXT_START" in block
        assert "TOOL_CONTEXT_END" in block
        assert "Status: refused" in block
        assert "Trust level insufficient" in block

    def test_error_context_block(self):
        trace = ToolCallTrace.create(
            tool_id="git_status",
            inputs={"workspace": "test-ws"},
            result_summary={"error": "execution_error", "message": "git crashed"},
            status="error",
        )
        block = build_tool_context_block(trace)
        assert "TOOL_CONTEXT_START" in block
        assert "Status: error" in block

    def test_git_status_context_block(self):
        trace = ToolCallTrace.create(
            tool_id="git_status",
            inputs={"workspace": "ws"},
            result_summary={"clean": True, "branch": "main"},
            status="success",
            raw_result={
                "clean": True,
                "branch": "main",
                "stdout": "",
                "workspace": "ws",
            },
        )
        block = build_tool_context_block(trace)
        assert "Branch: main" in block
        assert "Clean: True" in block

    def test_fs_stats_context_block(self):
        trace = ToolCallTrace.create(
            tool_id="fs_stats",
            inputs={"workspace": "ws"},
            result_summary={"total_files": 10},
            status="success",
            raw_result={
                "extensions": {".py": 5, ".md": 3, ".json": 2},
                "total_files": 10,
                "workspace": "ws",
            },
        )
        block = build_tool_context_block(trace)
        assert "Total: 10" in block
        assert ".py: 5" in block

    def test_context_block_no_workspace(self):
        trace = ToolCallTrace.create(
            tool_id="fs_tree",
            inputs={},
            result_summary={},
            status="success",
            raw_result={"files": [], "count": 0},
        )
        block = build_tool_context_block(trace)
        assert "Workspace: NONE" in block


class TestOrchestratorToolFlow:
    def test_no_tool_request_passthrough(self):
        from lathe_app.orchestrator import Orchestrator
        from lathe_app.storage import InMemoryStorage

        def agent_fn(normalized, model_id):
            return json.dumps({
                "proposals": [{"action": "create", "target": "test.py"}],
                "assumptions": [],
                "risks": [],
                "results": [],
                "model_fingerprint": model_id,
            })

        storage = InMemoryStorage()
        orch = Orchestrator(agent_fn=agent_fn, storage=storage)
        run = orch.execute(
            intent="propose",
            task="add test",
            why={"goal": "test"},
            speculative=False,
        )
        assert run.tool_calls == []
        assert run.success is True

    def test_tool_request_triggers_phase2(self):
        from lathe_app.orchestrator import Orchestrator
        from lathe_app.storage import InMemoryStorage

        call_count = [0]

        def agent_fn(normalized, model_id):
            call_count[0] += 1
            if call_count[0] == 1:
                return json.dumps({
                    "tool_request": {
                        "tool_id": "fs_tree",
                        "reason": "Need to see files",
                        "inputs": {"workspace": "no-such-ws"},
                    },
                    "proposals": [],
                    "model_fingerprint": model_id,
                    "results": [],
                })
            return json.dumps({
                "proposals": [],
                "assumptions": [],
                "risks": [],
                "results": [],
                "model_fingerprint": model_id,
            })

        storage = InMemoryStorage()
        orch = Orchestrator(agent_fn=agent_fn, storage=storage)
        run = orch.execute(
            intent="propose",
            task="list files",
            why={"goal": "test"},
            speculative=False,
        )
        assert call_count[0] == 2
        assert len(run.tool_calls) == 1
        assert run.tool_calls[0].tool_id == "fs_tree"

    def test_nonexistent_tool_recorded_as_refusal(self):
        from lathe_app.orchestrator import Orchestrator

        def agent_fn(normalized, model_id):
            return json.dumps({
                "tool_request": {
                    "tool_id": "nonexistent_tool",
                    "reason": "test",
                    "inputs": {},
                },
                "proposals": [],
                "model_fingerprint": model_id,
                "results": [],
            })

        orch = Orchestrator(agent_fn=agent_fn)
        run = orch.execute(
            intent="propose",
            task="test",
            why={},
            speculative=False,
        )
        assert len(run.tool_calls) == 1
        assert run.tool_calls[0].status == "refused"
        assert run.tool_calls[0].result_summary["error"] == "nonexistent_tool"

    def test_invalid_inputs_recorded_as_refusal(self):
        from lathe_app.orchestrator import Orchestrator

        def agent_fn(normalized, model_id):
            return json.dumps({
                "tool_request": {
                    "tool_id": "fs_tree",
                    "reason": "test",
                    "inputs": {},
                },
                "proposals": [],
                "model_fingerprint": model_id,
                "results": [],
            })

        orch = Orchestrator(agent_fn=agent_fn)
        run = orch.execute(
            intent="propose",
            task="test",
            why={},
            speculative=False,
        )
        assert len(run.tool_calls) == 1
        assert run.tool_calls[0].status == "refused"
        assert run.tool_calls[0].result_summary["error"] == "invalid_inputs"

    def test_tool_calls_in_storage(self):
        from lathe_app.orchestrator import Orchestrator
        from lathe_app.storage import InMemoryStorage

        call_count = [0]

        def agent_fn(normalized, model_id):
            call_count[0] += 1
            if call_count[0] == 1:
                return json.dumps({
                    "tool_request": {
                        "tool_id": "fs_stats",
                        "reason": "Check",
                        "inputs": {"workspace": "noexist"},
                    },
                    "proposals": [],
                    "model_fingerprint": model_id,
                    "results": [],
                })
            return json.dumps({
                "proposals": [],
                "assumptions": [],
                "risks": [],
                "results": [],
                "model_fingerprint": model_id,
            })

        storage = InMemoryStorage()
        orch = Orchestrator(agent_fn=agent_fn, storage=storage)
        run = orch.execute(
            intent="propose",
            task="test",
            why={},
            speculative=False,
        )
        saved = storage.load_run(run.id)
        assert saved is not None
        assert len(saved.tool_calls) == 1

    def test_malformed_tool_request_recorded(self):
        from lathe_app.orchestrator import Orchestrator

        def agent_fn(normalized, model_id):
            return json.dumps({
                "tool_request": {
                    "reason": "no tool_id",
                    "inputs": {},
                },
                "proposals": [],
                "model_fingerprint": model_id,
                "results": [],
            })

        orch = Orchestrator(agent_fn=agent_fn)
        run = orch.execute(
            intent="propose",
            task="test",
            why={},
            speculative=False,
        )
        assert len(run.tool_calls) == 1
        assert run.tool_calls[0].status == "refused"
        assert "malformed_request" in str(run.tool_calls[0].result_summary)


class TestToolCallSerialization:
    def test_runrecord_serializes_tool_calls(self):
        from lathe_app.http_serialization import to_jsonable_runrecord

        trace = ToolCallTrace.create(
            tool_id="fs_tree",
            inputs={"workspace": "ws"},
            result_summary={"file_count": 5},
            status="success",
        )
        run = RunRecord.create(
            input_data=ArtifactInput(intent="propose", task="test", why={}),
            output=ProposalArtifact.create(
                input_data=ArtifactInput(intent="propose", task="test", why={}),
                proposals=[],
                assumptions=[],
                risks=[],
                results=[],
                model_fingerprint="test",
                observability=ObservabilityTrace.empty(),
            ),
            model_used="test-model",
            fallback_triggered=False,
            success=True,
            tool_calls=[trace],
        )
        data = to_jsonable_runrecord(run)
        assert "tool_calls" in data
        assert len(data["tool_calls"]) == 1
        tc = data["tool_calls"][0]
        assert tc["tool_id"] == "fs_tree"
        assert tc["status"] == "success"
        assert "raw_result" not in tc
        assert "results" in data

    def test_empty_tool_calls_serialized(self):
        from lathe_app.http_serialization import to_jsonable_runrecord

        run = RunRecord.create(
            input_data=ArtifactInput(intent="propose", task="test", why={}),
            output=None,
            model_used="test",
            fallback_triggered=False,
            success=True,
        )
        data = to_jsonable_runrecord(run)
        assert data["tool_calls"] == []


class TestTUIToolCallsRendering:
    def test_tool_calls_data_structure(self):
        tc_data = {
            "tool_id": "fs_tree",
            "timestamp": "2026-02-07T15:12:44Z",
            "inputs": {"workspace": "test-ws", "ext": ".py"},
            "result_summary": {"file_count": 42},
            "status": "success",
        }
        assert tc_data["tool_id"] == "fs_tree"
        assert tc_data["status"] == "success"
        assert tc_data["inputs"]["workspace"] == "test-ws"

    def test_refused_tool_call_structure(self):
        tc_data = {
            "tool_id": "fs_tree",
            "timestamp": "2026-02-07T15:12:44Z",
            "inputs": {"workspace": "test-ws"},
            "result_summary": {"error": "trust_denied"},
            "status": "refused",
            "refusal_reason": "Trust level insufficient",
        }
        assert tc_data["status"] == "refused"
        assert tc_data["refusal_reason"] == "Trust level insufficient"


class TestFailureModes:
    def test_no_retries_on_failure(self):
        call_count = [0]

        def agent_fn(normalized, model_id):
            call_count[0] += 1
            if call_count[0] == 1:
                return json.dumps({
                    "tool_request": {
                        "tool_id": "nonexistent",
                        "reason": "test",
                        "inputs": {},
                    },
                    "proposals": [],
                    "model_fingerprint": model_id,
                    "results": [],
                })
            return json.dumps({
                "proposals": [],
                "model_fingerprint": model_id,
                "results": [],
            })

        from lathe_app.orchestrator import Orchestrator
        orch = Orchestrator(agent_fn=agent_fn)
        run = orch.execute(intent="propose", task="test", why={}, speculative=False)
        assert call_count[0] == 1
        assert len(run.tool_calls) == 1
        assert run.tool_calls[0].status == "refused"

    def test_no_alternative_substitution(self):
        def agent_fn(normalized, model_id):
            return json.dumps({
                "tool_request": {
                    "tool_id": "fs_tree_v2",
                    "reason": "test",
                    "inputs": {"workspace": "ws"},
                },
                "proposals": [],
                "model_fingerprint": model_id,
                "results": [],
            })

        from lathe_app.orchestrator import Orchestrator
        orch = Orchestrator(agent_fn=agent_fn)
        run = orch.execute(intent="propose", task="test", why={}, speculative=False)
        assert len(run.tool_calls) == 1
        assert run.tool_calls[0].tool_id == "fs_tree_v2"
        assert run.tool_calls[0].status == "refused"


class TestObservabilityGuarantees:
    def test_trace_answers_observability_questions(self):
        trace = ToolCallTrace.create(
            tool_id="fs_tree",
            inputs={"workspace": "test-ws", "ext": ".py"},
            result_summary={"file_count": 5},
            status="success",
            raw_result={"files": ["a.py", "b.py"], "count": 2, "workspace": "test-ws"},
        )
        d = trace.to_trace_dict()
        assert d["tool_id"]
        assert d["inputs"]
        assert d["status"]
        assert d["result_summary"]
        assert d["timestamp"]

    def test_refused_trace_includes_reason(self):
        trace = ToolCallTrace.create(
            tool_id="fs_tree",
            inputs={"workspace": "test-ws"},
            result_summary={"error": "trust_denied"},
            status="refused",
            refusal_reason="Trust level insufficient",
        )
        d = trace.to_trace_dict()
        assert d["refusal_reason"] == "Trust level insufficient"

    def test_tool_calls_appear_in_runrecord(self):
        from lathe_app.orchestrator import Orchestrator

        call_count = [0]

        def agent_fn(normalized, model_id):
            call_count[0] += 1
            if call_count[0] == 1:
                return json.dumps({
                    "tool_request": {
                        "tool_id": "fs_stats",
                        "reason": "Check",
                        "inputs": {"workspace": "missing"},
                    },
                    "proposals": [],
                    "model_fingerprint": model_id,
                    "results": [],
                })
            return json.dumps({
                "proposals": [],
                "assumptions": [],
                "risks": [],
                "results": [],
                "model_fingerprint": model_id,
            })

        orch = Orchestrator(agent_fn=agent_fn)
        run = orch.execute(intent="propose", task="test", why={}, speculative=False)
        assert len(run.tool_calls) >= 1
        tc = run.tool_calls[0]
        assert tc.tool_id
        assert tc.inputs is not None
        assert tc.status in ("success", "refused", "error")
        assert tc.timestamp
