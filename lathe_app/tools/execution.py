"""
Tool Execution

Executes validated tool requests and produces ToolCallTrace records.
Generates TOOL_CONTEXT blocks for agent Phase 2 injection.

Execution Authority:
- ONLY the app layer executes tools
- Tools execute AFTER agent output
- Tools are subject to workspace boundaries and trust gating

FAILURE MODES:
- Nonexistent tool → refusal (handled by requests.py)
- Invalid inputs → refusal (handled by requests.py)
- Insufficient trust → refusal (recorded in trace)
- Tool failure → recorded failure + error context
- NO retries, NO silent fallback, NO alternative tool substitution
"""
from typing import Any, Dict, List, Optional

from lathe_app.artifacts import ToolCallTrace
from lathe_app.tools.registry import get_tool_spec
from lathe_app.tools.handlers import TOOL_HANDLERS
from lathe_app.tools.requests import ToolRequest, ToolRequestError


def _map_inputs_to_handler(tool_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Map schema input keys to handler parameter names.

    The ToolSpec schema uses ``workspace`` but handlers expect ``workspace_id``.
    This mapping bridges the contract without changing either side.
    """
    mapped = dict(inputs)
    if "workspace" in mapped and "workspace_id" not in mapped:
        mapped["workspace_id"] = mapped.pop("workspace")
    return mapped


def _why_dict(request: ToolRequest) -> Optional[Dict[str, str]]:
    """Extract structured why dict from request, if present."""
    return request.why.to_dict()


def execute_tool(request: ToolRequest) -> ToolCallTrace:
    """Execute a validated tool request and return an immutable trace.

    The handler is looked up from TOOL_HANDLERS by tool_id.
    Trust and workspace boundary checks are delegated to the handler.
    """
    why = _why_dict(request)

    handler = TOOL_HANDLERS.get(request.tool_id)
    if handler is None:
        return ToolCallTrace.create(
            tool_id=request.tool_id,
            inputs=request.inputs,
            result_summary={"error": "no_handler"},
            status="refused",
            why=why,
            refusal_reason=f"No handler registered for tool '{request.tool_id}'",
        )

    mapped_inputs = _map_inputs_to_handler(request.tool_id, request.inputs)

    try:
        raw_result = handler(**mapped_inputs)
    except Exception as exc:
        return ToolCallTrace.create(
            tool_id=request.tool_id,
            inputs=request.inputs,
            result_summary={"error": "execution_error", "message": str(exc)},
            status="error",
            why=why,
            raw_result=None,
        )

    if not isinstance(raw_result, dict):
        raw_result = {"result": raw_result}

    if raw_result.get("error") == "trust_denied":
        return ToolCallTrace.create(
            tool_id=request.tool_id,
            inputs=request.inputs,
            result_summary={"error": "trust_denied"},
            status="refused",
            why=why,
            raw_result=raw_result,
            refusal_reason=raw_result.get("message", "Trust level insufficient"),
        )

    if raw_result.get("error") == "workspace_not_found":
        return ToolCallTrace.create(
            tool_id=request.tool_id,
            inputs=request.inputs,
            result_summary={"error": "workspace_not_found"},
            status="refused",
            why=why,
            raw_result=raw_result,
            refusal_reason=raw_result.get("message", "Workspace not found"),
        )

    if "error" in raw_result:
        return ToolCallTrace.create(
            tool_id=request.tool_id,
            inputs=request.inputs,
            result_summary={"error": raw_result["error"]},
            status="error",
            why=why,
            raw_result=raw_result,
        )

    summary = _build_summary(request.tool_id, raw_result)

    return ToolCallTrace.create(
        tool_id=request.tool_id,
        inputs=request.inputs,
        result_summary=summary,
        status="success",
        why=why,
        raw_result=raw_result,
    )


def execute_tool_from_error(error: ToolRequestError) -> ToolCallTrace:
    """Create a refusal trace from a ToolRequestError."""
    return ToolCallTrace.create(
        tool_id=error.tool_id or "unknown",
        inputs={},
        result_summary={"error": error.error_type},
        status="refused",
        refusal_reason=error.message,
    )


def _build_summary(tool_id: str, raw_result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract a compact summary from raw tool output."""
    if tool_id == "fs_tree":
        return {
            "file_count": raw_result.get("count", 0),
            "workspace": raw_result.get("workspace"),
        }
    elif tool_id == "fs_stats":
        return {
            "total_files": raw_result.get("total_files", 0),
            "workspace": raw_result.get("workspace"),
        }
    elif tool_id == "git_status":
        return {
            "clean": raw_result.get("clean"),
            "branch": raw_result.get("branch"),
            "workspace": raw_result.get("workspace"),
        }
    else:
        keys = list(raw_result.keys())[:5]
        return {k: raw_result[k] for k in keys if k != "error"}


def build_tool_context_block(trace: ToolCallTrace) -> str:
    """Generate the TOOL_CONTEXT_START/END block for agent Phase 2 injection.

    Rules:
    - Agent may reference ONLY what appears inside this block
    - Context Echo validation still applies
    - Tool context is isolated from prompt history
    """
    lines = ["TOOL_CONTEXT_START"]
    lines.append(f"Tool: {trace.tool_id}")

    workspace = trace.inputs.get("workspace", "NONE")
    lines.append(f"Workspace: {workspace}")

    if trace.why:
        goal = trace.why.get("goal", "")
        if goal:
            lines.append(f"Goal: {goal}")

    if trace.status == "success" and trace.raw_result:
        lines.append("Result:")
        _format_result(trace.tool_id, trace.raw_result, lines)
    elif trace.status == "refused":
        lines.append(f"Status: refused")
        lines.append(f"Reason: {trace.refusal_reason or 'unknown'}")
    elif trace.status == "error":
        lines.append(f"Status: error")
        msg = trace.result_summary.get("message", "unknown error")
        lines.append(f"Error: {msg}")

    lines.append("TOOL_CONTEXT_END")
    return "\n".join(lines)


def _format_result(tool_id: str, raw: Dict[str, Any], lines: List[str]) -> None:
    """Format raw tool result into human-readable lines."""
    if tool_id == "fs_tree":
        for f in raw.get("files", []):
            lines.append(f"- {f}")
    elif tool_id == "fs_stats":
        for ext, count in raw.get("extensions", {}).items():
            lines.append(f"- {ext}: {count}")
        lines.append(f"Total: {raw.get('total_files', 0)}")
    elif tool_id == "git_status":
        lines.append(f"Branch: {raw.get('branch', 'unknown')}")
        lines.append(f"Clean: {raw.get('clean', 'unknown')}")
        stdout = raw.get("stdout", "")
        if stdout:
            for line in stdout.split("\n"):
                lines.append(f"  {line}")
    else:
        import json as _json
        lines.append(_json.dumps(raw, indent=2, default=str))
