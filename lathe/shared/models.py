"""
Shared data models for Lathe subsystems.

These models define explicit data contracts between subsystems.
Subsystems communicate through these models only.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

from lathe.shared.enums import (
    ValidationLevel,
    ContextSourceType,
    PromptScope,
)


@dataclass
class PromptMetadata:
    """
    Metadata for a prompt in the registry.

    Attributes:
        id: Unique identifier for the prompt
        scope: Scope or domain (global, project, task, custom)
        name: Human-readable name
        version: Version identifier
        created_at: Creation timestamp
        updated_at: Last update timestamp
        description: Optional description
        tags: Optional list of tags for organization
    """

    id: str
    scope: PromptScope
    name: str
    version: str
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class ContextSource:
    """
    Represents a single context source.

    Attributes:
        type: Type of source (knowledge, memory, file, metadata, custom)
        identifier: Unique identifier within its source type
        content: Actual content of the source
        priority: Priority for ranking (0-100, higher = more important)
        metadata: Additional metadata about the source
    """

    type: ContextSourceType
    identifier: str
    content: str
    priority: int = 50
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextOutput:
    """
    Assembled context ready for AI interaction.

    This is the output contract of lathe-context subsystem.

    Attributes:
        assembled_content: Final assembled context string
        sources_used: List of source identifiers that were included
        total_tokens_estimated: Rough token count estimate
        metadata: Context assembly metadata
    """

    assembled_content: str
    sources_used: List[str]
    total_tokens_estimated: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationRule:
    """
    Defines a single validation rule.

    Attributes:
        rule_id: Unique identifier for the rule
        name: Human-readable rule name
        severity: Validation level (pass, warn, fail)
        description: What the rule checks
    """

    rule_id: str
    name: str
    severity: ValidationLevel
    description: str


@dataclass
class ValidationResult:
    """
    Result of validation against a set of rules.

    This is the output contract of lathe-validation subsystem.

    Attributes:
        overall_level: Overall validation result (pass, warn, fail)
        rule_results: Detailed results per rule
        errors: List of error messages if validation failed
        warnings: List of warning messages
        passed_rules: List of rule IDs that passed
        failed_rules: List of rule IDs that failed
    """

    overall_level: ValidationLevel
    rule_results: Dict[str, Dict[str, Any]]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    passed_rules: List[str] = field(default_factory=list)
    failed_rules: List[str] = field(default_factory=list)
