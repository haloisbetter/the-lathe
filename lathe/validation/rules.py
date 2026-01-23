"""
Validation rule definitions for lathe-validation subsystem.

Defines rule interfaces and common rule implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from lathe.shared.enums import ValidationLevel


@dataclass
class ValidationRule(ABC):
    """
    Abstract base class for validation rules.

    Subclasses must implement the `evaluate` method.
    """

    rule_id: str
    name: str
    severity: ValidationLevel
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @abstractmethod
    def evaluate(self, content: str) -> bool:
        """
        Evaluate if content passes this rule.

        Args:
            content: Content to validate

        Returns:
            True if passes, False if fails
        """
        pass


class FullFileReplacementRule(ValidationRule):
    """
    Rule: Output must provide complete file replacement.

    Checks that the output contains a full file (not partial snippets).
    """

    def __init__(
        self,
        severity: ValidationLevel = ValidationLevel.FAIL,
        min_lines: int = 1,
    ):
        super().__init__(
            rule_id="full_file_replacement",
            name="Full File Replacement",
            severity=severity,
            description="Output must contain complete file, not partial snippets",
            metadata={"min_lines": min_lines},
        )
        self.min_lines = min_lines

    def evaluate(self, content: str) -> bool:
        """
        Check if content appears to be a complete file.

        Args:
            content: Content to check

        Returns:
            True if appears to be complete file
        """
        lines = content.strip().split("\n")
        return len(lines) >= self.min_lines


class ExplicitAssumptionsRule(ValidationRule):
    """
    Rule: Output must state explicit assumptions.

    Checks that output contains assumption markers.
    """

    def __init__(
        self,
        severity: ValidationLevel = ValidationLevel.WARN,
        markers: Optional[list[str]] = None,
    ):
        if markers is None:
            markers = ["ASSUME", "assume", "NOTE:", "note:", "Assumption:"]

        super().__init__(
            rule_id="explicit_assumptions",
            name="Explicit Assumptions",
            severity=severity,
            description="Output should state assumptions clearly",
            metadata={"markers": markers},
        )
        self.markers = markers

    def evaluate(self, content: str) -> bool:
        """
        Check if content contains assumption markers.

        Args:
            content: Content to check

        Returns:
            True if assumptions are stated
        """
        return any(marker in content for marker in self.markers)


class RequiredSectionRule(ValidationRule):
    """
    Rule: Output must contain required section headers.

    Checks that output includes expected section headers.
    """

    def __init__(
        self,
        required_sections: list[str],
        severity: ValidationLevel = ValidationLevel.WARN,
    ):
        super().__init__(
            rule_id="required_sections",
            name="Required Sections",
            severity=severity,
            description=f"Output must contain sections: {', '.join(required_sections)}",
            metadata={"required_sections": required_sections},
        )
        self.required_sections = required_sections

    def evaluate(self, content: str) -> bool:
        """
        Check if all required sections are present.

        Args:
            content: Content to check

        Returns:
            True if all sections found
        """
        for section in self.required_sections:
            if section not in content:
                return False
        return True


class NoHallucinatedFilesRule(ValidationRule):
    """
    Rule: Output should not reference non-existent files.

    Checks that file references are realistic/expected.
    """

    def __init__(
        self,
        severity: ValidationLevel = ValidationLevel.WARN,
        allowed_extensions: Optional[list[str]] = None,
    ):
        if allowed_extensions is None:
            allowed_extensions = [
                ".py",
                ".js",
                ".ts",
                ".json",
                ".yaml",
                ".md",
                ".txt",
            ]

        super().__init__(
            rule_id="no_hallucinated_files",
            name="No Hallucinated Files",
            severity=severity,
            description="Output should not reference files that don't exist",
            metadata={"allowed_extensions": allowed_extensions},
        )
        self.allowed_extensions = allowed_extensions

    def evaluate(self, content: str) -> bool:
        """
        Check for suspicious file references.

        This is a placeholder implementation.

        Args:
            content: Content to check

        Returns:
            True if no obvious hallucinations detected
        """
        # Placeholder: In real implementation, check against actual filesystem
        # or project manifest
        return True


class OutputFormatRule(ValidationRule):
    """
    Rule: Output must follow expected format.

    Checks for specific format requirements.
    """

    def __init__(
        self,
        format_type: str = "code",
        severity: ValidationLevel = ValidationLevel.WARN,
    ):
        super().__init__(
            rule_id="output_format",
            name="Output Format",
            severity=severity,
            description=f"Output must be in {format_type} format",
            metadata={"format_type": format_type},
        )
        self.format_type = format_type

    def evaluate(self, content: str) -> bool:
        """
        Check if content follows expected format.

        Args:
            content: Content to check

        Returns:
            True if format is acceptable
        """
        # Placeholder: Format validation depends on format_type
        return bool(content.strip())
