"""
Shared enumerations for Lathe subsystems.

These enums are used across prompts, context, and validation subsystems.
"""

from enum import Enum


class ValidationLevel(str, Enum):
    """Severity level for validation results."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class ContextSourceType(str, Enum):
    """Types of context sources that can be assembled."""

    KNOWLEDGE = "knowledge"
    MEMORY = "memory"
    FILE = "file"
    METADATA = "metadata"
    CUSTOM = "custom"


class PromptScope(str, Enum):
    """Scope or domain of a prompt."""

    GLOBAL = "global"
    PROJECT = "project"
    TASK = "task"
    CUSTOM = "custom"
