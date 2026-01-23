"""
The Lathe - Core Bootstrap Module

This package provides the core bootstrap for an AI coding platform.
It handles configuration loading, startup, lifecycle, and orchestration.

Responsibility Boundaries:
- Configuration management
- Logging and observability
- Task orchestration (WHAT to build)
- Storage and persistence
- CLI interface

Does NOT contain:
- AI reasoning logic
- Business rules for task generation
- Direct network calls (abstracted through executors)
"""

__version__ = "0.1.0"
