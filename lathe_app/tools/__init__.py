"""
Lathe App Tool Registry

GET-based read-only tool discovery and invocation.
Tools are pure capability adapters — they do NOT reason, do NOT call models,
and do NOT mutate state.

All tools are discoverable via GET /tools and invoked via GET /tools/<id>.
"""
from lathe_app.tools.registry import ToolSpec, TOOL_REGISTRY, get_tool_spec

__all__ = [
    "ToolSpec",
    "TOOL_REGISTRY",
    "get_tool_spec",
]
