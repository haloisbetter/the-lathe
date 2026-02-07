"""
Tool Request Parsing

Extracts and validates tool_call blocks from agent output.
Agents declare tool needs declaratively — they NEVER execute tools.

Supports two formats:
- tool_call (v1 contract): structured why with goal/evidence_needed/risk/verification
- tool_request (legacy): simple reason string

Rules:
- tool_id MUST exist in GET /tools
- inputs MUST match the tool schema exactly
- If no tool is needed, tool_call MUST be omitted
- The agent MUST NOT assume the tool's output
"""
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from lathe_app.tools.registry import get_tool_spec, ToolSpec


@dataclass
class ToolWhy:
    """Structured justification for a tool call (v1 contract)."""
    goal: str = ""
    evidence_needed: str = ""
    risk: str = ""
    verification: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "goal": self.goal,
            "evidence_needed": self.evidence_needed,
            "risk": self.risk,
            "verification": self.verification,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolWhy":
        if not isinstance(data, dict):
            return cls()
        return cls(
            goal=str(data.get("goal", "")),
            evidence_needed=str(data.get("evidence_needed", "")),
            risk=str(data.get("risk", "")),
            verification=str(data.get("verification", "")),
        )

    @classmethod
    def from_reason(cls, reason: str) -> "ToolWhy":
        """Create from a legacy reason string (backward compat)."""
        return cls(goal=reason)

    @property
    def reason(self) -> str:
        """Legacy accessor — returns goal as the plain reason string."""
        return self.goal


@dataclass
class ToolRequest:
    tool_id: str
    why: ToolWhy
    inputs: Dict[str, Any]
    spec: ToolSpec

    @property
    def reason(self) -> str:
        """Legacy accessor for backward compatibility."""
        return self.why.reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "why": self.why.to_dict(),
            "inputs": self.inputs,
        }


@dataclass
class ToolRequestError:
    error_type: str  # "nonexistent_tool" | "invalid_inputs" | "malformed_request"
    message: str
    tool_id: Optional[str] = None


def parse_tool_request(agent_output: str) -> Optional[Dict[str, Any]]:
    """Extract tool_call or tool_request from agent output JSON.

    Checks for ``tool_call`` first (v1 contract), falls back to
    ``tool_request`` (legacy format).  Returns the raw dict if present,
    None otherwise.
    """
    try:
        parsed = json.loads(agent_output)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(parsed, dict):
        return None

    raw = parsed.get("tool_call")
    if raw is not None:
        return raw

    return parsed.get("tool_request")


def validate_tool_request(raw_request: Dict[str, Any]) -> tuple:
    """Validate a raw tool_call/tool_request dict.

    Returns (ToolRequest, None) on success or (None, ToolRequestError) on failure.
    """
    if not isinstance(raw_request, dict):
        return None, ToolRequestError(
            error_type="malformed_request",
            message="tool_call must be a dict",
        )

    tool_id = raw_request.get("tool_id")
    if not tool_id or not isinstance(tool_id, str):
        return None, ToolRequestError(
            error_type="malformed_request",
            message="tool_call.tool_id is required and must be a string",
        )

    spec = get_tool_spec(tool_id)
    if spec is None:
        return None, ToolRequestError(
            error_type="nonexistent_tool",
            message=f"Tool '{tool_id}' does not exist in the registry",
            tool_id=tool_id,
        )

    why = _parse_why(raw_request)

    inputs = raw_request.get("inputs", {})
    if not isinstance(inputs, dict):
        return None, ToolRequestError(
            error_type="invalid_inputs",
            message="tool_call.inputs must be a dict",
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
        why=why,
        inputs=inputs,
        spec=spec,
    ), None


def _parse_why(raw_request: Dict[str, Any]) -> ToolWhy:
    """Extract why/reason from raw request (supports both formats)."""
    why_raw = raw_request.get("why")
    if isinstance(why_raw, dict):
        return ToolWhy.from_dict(why_raw)

    reason = raw_request.get("reason", "")
    return ToolWhy.from_reason(str(reason))


def extract_and_validate(agent_output: str) -> tuple:
    """Combined parse + validate.

    Returns (ToolRequest, None) if a valid tool_call is found,
    (None, ToolRequestError) if request is present but invalid,
    (None, None) if no tool_call is present.
    """
    raw = parse_tool_request(agent_output)
    if raw is None:
        return None, None
    return validate_tool_request(raw)
