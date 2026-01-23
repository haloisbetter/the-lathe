"""
lathe-context: Assemble and scope context for AI interactions.

This subsystem provides:
- Context assembly from multiple sources
- Source prioritization and filtering
- Context output generation
- Prevention of context flooding

DOES NOT provide:
- Knowledge storage or vector databases
- Prompt logic or execution
- Validation logic
- Persistence
"""

from lathe.context.builder import ContextBuilder
from lathe.context.sources import SourceFilter

__all__ = [
    "ContextBuilder",
    "SourceFilter",
]
