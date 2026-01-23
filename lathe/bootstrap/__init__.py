"""
Bootstrap module for The Lathe.

Contains temporary executor implementations that delegate task execution
to external agents (like OpenHands).

IMPORTANT: This module is temporary and designed to be replaced.
The dependency on external agents must be removable.

Responsibilities:
- External agent integration
- Task translation to agent format
- Result parsing from agents

Does NOT contain:
- Core orchestration logic
- Storage
- Configuration
"""

from .openhands import OpenHandsExecutor

__all__ = ["OpenHandsExecutor"]
