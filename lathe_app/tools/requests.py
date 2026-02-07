"""
Tool Request Parsing

Extracts and validates tool_request blocks from agent output.
Agents declare tool needs declaratively — they NEVER execute tools.

Rules:
- tool_id MUST exist in GET /tools
- inputs MUST match the tool schema exactly
- If no tool is needed, tool_request MUST be omitted
- The agent MUST NOT assume the tool's output
"""
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from lathe_app.tools.registry import get_tool_spec, ToolSpec


@dataclass
class ToolRequest:
    tool_id: str
    reason: str
    inputs: Dict[str, Any]
    spec: ToolSpec

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "reason": self.reason,
            "inputs": self.inputs,
        }


@dataclass
class ToolRequestError:
    error_type: str  # "nonexistent_tool" | "invalid_inputs" | "malformed_request"
    message: str
    tool_id: Optional[str] = None


def parse_tool_request(agent_output: str) -> Optional[Dict[str, Any]]:
    """Extract tool_request from agent output JSON.

    Returns the raw tool_request dict if present, None otherwise.
    """
    try:
        parsed = json.loads(agent_output)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(parsed, dict):
        return None

    return parsed.get("tool_request")


def validate_tool_request(raw_request: Dict[str, Any]) -> tuple:
    """Validate a raw tool_request dict.

    Returns (ToolRequest, None) on success or (None, ToolRequestError) on failure.
    """
    if not isinstance(raw_request, dict):
        return None, ToolRequestError(
            error_type="malformed_request",
            message="tool_request must be a dict",
        )

    tool_id = raw_request.get("tool_id")
    if not tool_id or not isinstance(tool_id, str):
        return None, ToolRequestError(
            error_type="malformed_request",
            message="tool_request.tool_id is required and must be a string",
        )

    spec = get_tool_spec(tool_id)
    if spec is None:
        return None, ToolRequestError(
            error_type="nonexistent_tool",
            message=f"Tool '{tool_id}' does not exist in the registry",
            tool_id=tool_id,
        )

    reason = raw_request.get("reason", "")
    inputs = raw_request.get("inputs", {})
    if not isinstance(inputs, dict):
        return None, ToolRequestError(
            error_type="invalid_inputs",
            message="tool_request.inputs must be a dict",
            tool_id=tool_id,
        )

    missing_required = []
    for field_name, field_spec in spec.inputs.items():
        if isinstance(field_spec, dict) and field_spec.get("required", False):
            if field_name not in inputs:
                missing_required.append(field_name)

    if missing_required:
        return None, ToolRequestError(
            error_type="invalid_inputs",
            message=f"Missing required inputs: {', '.join(missing_required)}",
            tool_id=tool_id,
        )

    return ToolRequest(
        tool_id=tool_id,
        reason=reason,
        inputs=inputs,
        spec=spec,
    ), None


def extract_and_validate(agent_output: str) -> tuple:
    """Combined parse + validate.

    Returns (ToolRequest, None) if a valid tool_request is found,
    (None, ToolRequestError) if request is present but invalid,
    (None, None) if no tool_request is present.
    """
    raw = parse_tool_request(agent_output)
    if raw is None:
        return None, None
    return validate_tool_request(raw)
