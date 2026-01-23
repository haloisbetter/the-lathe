"""
lathe-prompts: Central registry for system prompts.

This subsystem provides:
- Prompt registration and lookup
- Prompt versioning (in-memory)
- Prompt validation against schema
- Scoped prompt organization

DOES NOT provide:
- Persistence
- Model execution
- UI
- Context selection
"""

from lathe.prompts.registry import PromptRegistry
from lathe.prompts.schemas import Prompt

__all__ = [
    "PromptRegistry",
    "Prompt",
]
