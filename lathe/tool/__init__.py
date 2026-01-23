"""
Lathe OpenWebUI Tool Wrapper

This module provides the thin OpenWebUI-compatible interface to The Lathe subsystems.
It does NOT contain business logic — only orchestration of existing subsystems.

Exported functions:
- lathe_plan: Prepare AI step with system prompt and context
- lathe_validate: Validate AI output against rules
- lathe_context_preview: Preview context assembly

All functions accept and return JSON-serializable dicts.
"""

from lathe.tool.wrapper import (
    lathe_plan,
    lathe_validate,
    lathe_context_preview,
)

__all__ = [
    "lathe_plan",
    "lathe_validate",
    "lathe_context_preview",
]
