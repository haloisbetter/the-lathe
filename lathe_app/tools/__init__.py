"""
Lathe App Tool Registry

GET-based read-only tool discovery and invocation.
Tools are pure capability adapters — they do NOT reason, do NOT call models,
and do NOT mutate state.

All tools are discoverable via GET /tools and invoked via GET /tools/<id>.
"""
from lathe_app.tools.registry import ToolSpec, TOOL_REGISTRY, get_tool_spec
from lathe_app.tools.requests import (
    ToolRequest,
    ToolRequestError,
    parse_tool_request,
    validate_tool_request,
    extract_and_validate,
)
from lathe_app.tools.execution import (
    execute_tool,
    execute_tool_from_error,
    build_tool_context_block,
)

__all__ = [
    "ToolSpec",
    "TOOL_REGISTRY",
    "get_tool_spec",
    "ToolRequest",
    "ToolRequestError",
    "parse_tool_request",
    "validate_tool_request",
    "extract_and_validate",
    "execute_tool",
    "execute_tool_from_error",
    "build_tool_context_block",
]
