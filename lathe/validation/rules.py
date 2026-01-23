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


class NoCodeOutputRule(ValidationRule):
    """
    Rule: Output must not contain code blocks or code snippets.

    Enforces ANALYSIS phase discipline - no code, no implementations, no commands.
    Designed for analysis phase where only prose, findings, and risks are allowed.
    """

    def __init__(
        self,
        severity: ValidationLevel = ValidationLevel.FAIL,
        allow_technical_terms: bool = True,
    ):
        super().__init__(
            rule_id="no_code_output",
            name="No Code Output",
            severity=severity,
            description="Output must not contain code blocks, snippets, file paths, or commands",
            metadata={"allow_technical_terms": allow_technical_terms},
        )
        self.allow_technical_terms = allow_technical_terms

        # Code block patterns
        self.code_block_markers = [
            "```",  # Fenced code blocks
            "~~~",  # Alternative fenced blocks
        ]

        # Programming keywords (common across languages)
        self.code_keywords = [
            "def ",
            "class ",
            "import ",
            "from ",
            "function ",
            "const ",
            "let ",
            "var ",
            "public ",
            "private ",
            "protected ",
            "void ",
            "int ",
            "string ",
            "boolean ",
            "async ",
            "await ",
            "return ",
            "if (",
            "for (",
            "while (",
            "switch (",
        ]

        # Shell command patterns
        self.command_patterns = [
            "\n$ ",
            "\n# ",
            "\n> ",
            "bash\n",
            "sh\n",
            "python\n",
            "node\n",
            "npm ",
            "pip install",
            "apt-get",
            "docker run",
            "git clone",
        ]

        # File path patterns (more strict)
        self.file_path_indicators = [
            "/src/",
            "/lib/",
            "/bin/",
            "/usr/",
            "/etc/",
            "/home/",
            "/app/",
            ".py:",
            ".js:",
            ".ts:",
            ".java:",
            ".cpp:",
            ".go:",
            ".rs:",
            "file://",
        ]

    def evaluate(self, content: str) -> bool:
        """
        Check if content contains code blocks, snippets, or commands.

        Args:
            content: Content to check

        Returns:
            True if NO code detected (passes), False if code found (fails)
        """
        # Check for fenced code blocks
        for marker in self.code_block_markers:
            if marker in content:
                return False

        # Check for inline code with context (avoid false positives)
        # Only flag if there are multiple backticks or code-like content
        if content.count("`") >= 4:  # At least 2 inline code snippets
            return False

        # Check for programming keywords
        content_lower = content.lower()
        for keyword in self.code_keywords:
            if keyword in content_lower:
                # Additional check: ensure it's not just technical discussion
                if self.allow_technical_terms:
                    # Allow keywords in quotes or as references
                    if f'"{keyword.strip()}"' in content_lower or f"'{keyword.strip()}'" in content_lower:
                        continue
                return False

        # Check for shell commands
        for pattern in self.command_patterns:
            if pattern in content:
                return False

        # Check for file paths
        for indicator in self.file_path_indicators:
            if indicator in content:
                return False

        # If no code indicators found, passes
        return True
