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


class RequireMultipleDesignOptionsRule(ValidationRule):
    """
    Rule: Design phase must present multiple design options.

    Enforces design thinking discipline - consider alternatives.
    Warns if only one approach is presented.
    """

    def __init__(
        self,
        severity: ValidationLevel = ValidationLevel.WARN,
        min_options: int = 2,
    ):
        super().__init__(
            rule_id="require_multiple_design_options",
            name="Multiple Design Options",
            severity=severity,
            description=f"Design should present at least {min_options} different approaches",
            metadata={"min_options": min_options},
        )
        self.min_options = min_options

        # Keywords that indicate design options
        self.option_markers = [
            "Option 1",
            "Option 2",
            "Option 3",
            "Approach 1",
            "Approach 2",
            "Approach 3",
            "Alternative 1",
            "Alternative 2",
            "Design A",
            "Design B",
            "Solution 1",
            "Solution 2",
            "Strategy 1",
            "Strategy 2",
        ]

    def evaluate(self, content: str) -> bool:
        """
        Check if design presents multiple options.

        Args:
            content: Design content to check

        Returns:
            True if multiple options found
        """
        # Count how many option markers appear
        option_count = 0
        for marker in self.option_markers:
            if marker in content:
                option_count += 1

        # Count explicit mentions of "options" or "alternatives"
        if "option" in content.lower() and "another" in content.lower():
            option_count = max(option_count, 2)
        if "alternative" in content.lower() and ("however" in content.lower() or "versus" in content.lower()):
            option_count = max(option_count, 2)

        return option_count >= self.min_options


class RequireTradeoffsRule(ValidationRule):
    """
    Rule: Design phase must discuss tradeoffs.

    Enforces consideration of design implications.
    Warns if tradeoff analysis is missing.
    """

    def __init__(
        self,
        severity: ValidationLevel = ValidationLevel.WARN,
    ):
        super().__init__(
            rule_id="require_tradeoffs",
            name="Tradeoff Analysis",
            severity=severity,
            description="Design should discuss tradeoffs and implications of each option",
            metadata={},
        )

        # Keywords indicating tradeoff discussion
        self.tradeoff_markers = [
            "tradeoff",
            "trade-off",
            "trade off",
            "pros and cons",
            "advantages and disadvantages",
            "benefits and drawbacks",
            "strength",
            "weakness",
            "complexity",
            "performance",
            "scalability",
            "maintainability",
            "cost",
            "risk",
            "vs.",
            "versus",
            "however",
            "on the other hand",
        ]

    def evaluate(self, content: str) -> bool:
        """
        Check if design discusses tradeoffs.

        Args:
            content: Design content to check

        Returns:
            True if tradeoff discussion found
        """
        content_lower = content.lower()

        # Count tradeoff markers
        marker_count = 0
        for marker in self.tradeoff_markers:
            if marker in content_lower:
                marker_count += 1

        # Need at least 3 different tradeoff indicators
        return marker_count >= 3


class AllowDiagramsRule(ValidationRule):
    """
    Rule: Design phase can include diagrams.

    Allows ASCII art, Mermaid diagrams, and architecture descriptions.
    Specifically designed for design phase where diagrams are expected.
    """

    def __init__(
        self,
        severity: ValidationLevel = ValidationLevel.WARN,
    ):
        super().__init__(
            rule_id="allow_diagrams",
            name="Diagram Support",
            severity=severity,
            description="Design can include ASCII art and Mermaid diagrams",
            metadata={},
        )

        # Markers indicating diagram presence
        self.diagram_markers = [
            "```ascii",
            "```mermaid",
            "┌─",
            "├─",
            "└─",
            "│",
            "graph ",
            "flowchart ",
            "diagram",
            "architecture",
            "sequence",
            "component",
            "deployment",
        ]

    def evaluate(self, content: str) -> bool:
        """
        Check if design includes architectural descriptions/diagrams.

        Args:
            content: Design content to check

        Returns:
            True if diagrams or architecture descriptions found
        """
        content_lower = content.lower()

        # Count diagram indicators
        diagram_count = 0
        for marker in self.diagram_markers:
            if marker in content_lower:
                diagram_count += 1

        # At least one diagram indicator is good
        # This is permissive - just checking that architecture is described
        return diagram_count >= 1


class RequireExplicitFilenameRule(ValidationRule):
    """
    Rule: Implementation must explicitly state filename(s).

    Prevents ambiguous implementations - must declare which files are being modified.
    """

    def __init__(
        self,
        severity: ValidationLevel = ValidationLevel.FAIL,
    ):
        super().__init__(
            rule_id="require_explicit_filename",
            name="Explicit Filename",
            severity=severity,
            description="Implementation must explicitly state filename(s) being modified",
            metadata={},
        )

        # Filename indicators
        self.filename_markers = [
            "filename:",
            "file:",
            "path:",
            "src/",
            "lib/",
            "components/",
            "utils/",
            "services/",
            "pages/",
            "api/",
            "database/",
            ".ts",
            ".tsx",
            ".js",
            ".jsx",
            ".py",
            ".sql",
            ".json",
            ".yml",
            ".yaml",
            ".env",
            ".md",
            "create file",
            "create new file",
            "new file",
            "this file",
            "this is the file",
        ]

    def evaluate(self, content: str) -> bool:
        """
        Check if implementation explicitly states filename(s).

        Args:
            content: Implementation content to check

        Returns:
            True if filenames found
        """
        content_lower = content.lower()

        # Count filename markers
        filename_count = 0
        for marker in self.filename_markers:
            if marker in content_lower:
                filename_count += 1

        # Need at least one clear filename indicator
        return filename_count >= 1


class RequireFullFileReplacementRule(ValidationRule):
    """
    Rule: Implementation must provide full file content.

    Prevents partial snippets or "assume this exists" patterns.
    Enforces complete, determinstic output.
    """

    def __init__(
        self,
        severity: ValidationLevel = ValidationLevel.FAIL,
    ):
        super().__init__(
            rule_id="require_full_file_replacement",
            name="Full File Replacement",
            severity=severity,
            description="Implementation must provide complete file content, not snippets",
            metadata={},
        )

        # Markers indicating partial/incomplete content
        self.partial_indicators = [
            "you can use this",
            "you might use this",
            "you could add",
            "you could also add",
            "... rest of",
            "[rest of",
            "// rest of",
            "# rest of",
            "and so on",
            "et cetera",
            "etc.",
            "[omitted",
            "[abbreviated",
            "[truncated",
            "unchanged",
            "no changes needed",
            "assume this exists",
            "assume the file",
            "assuming",
            "leave as is",
            "keep this",
            "don't change",
        ]

        # Markers indicating completeness
        self.complete_indicators = [
            "full file replacement",
            "complete file",
            "entire file",
            "full content",
            "complete content",
            "this is the complete",
            "here is the full",
        ]

    def evaluate(self, content: str) -> bool:
        """
        Check if implementation provides complete file content.

        Args:
            content: Implementation content to check

        Returns:
            True if complete content found
        """
        content_lower = content.lower()

        # Count partial indicators
        partial_count = 0
        for indicator in self.partial_indicators:
            if indicator in content_lower:
                partial_count += 1

        # Count complete indicators
        complete_count = 0
        for indicator in self.complete_indicators:
            if indicator in content_lower:
                complete_count += 1

        # If explicitly marked complete, pass
        if complete_count > 0:
            return True

        # If partial indicators present, fail
        if partial_count > 0:
            return False

        # Check if content looks complete (has opening and closing markers)
        # Files typically have opening structure (import, function, class, etc.)
        # and ending structure (closing braces, EOF, etc.)
        has_opening = any(
            marker in content_lower
            for marker in ["import", "def ", "class ", "function", "export", "const ", "let ", "var "]
        )
        has_closing = any(
            marker in content_lower
            for marker in ["return", "}", "```", "\n\n", "end of file"]
        )

        # Without explicit markers, check structure heuristics
        # If has opening but no partial indicators, likely complete
        return has_opening or len(content) > 100


class ForbidMultipleImplementationsRule(ValidationRule):
    """
    Rule: Implementation must NOT present multiple alternatives.

    Prevents ambiguous "pick one" scenarios.
    Forces commitment to single, clear implementation.
    """

    def __init__(
        self,
        severity: ValidationLevel = ValidationLevel.FAIL,
    ):
        super().__init__(
            rule_id="forbid_multiple_implementations",
            name="No Multiple Alternatives",
            severity=severity,
            description="Implementation must present single approach, not alternatives",
            metadata={},
        )

        # Markers indicating multiple options/alternatives
        self.alternative_markers = [
            "option 1",
            "option 2",
            "option 3",
            "approach 1",
            "approach 2",
            "alternative 1",
            "alternative 2",
            "variant 1",
            "variant 2",
            "solution a",
            "solution b",
            "method 1",
            "method 2",
            "implementation 1",
            "implementation 2",
            "you could do",
            "you could also",
            "another way",
            "another option",
            "one approach",
            "another approach",
            "or you could",
            "alternatively",
        ]

    def evaluate(self, content: str) -> bool:
        """
        Check if implementation presents single approach.

        Args:
            content: Implementation content to check

        Returns:
            True if single implementation (no alternatives)
        """
        content_lower = content.lower()

        # Count alternative markers
        alternative_count = 0
        for marker in self.alternative_markers:
            if marker in content_lower:
                alternative_count += 1

        # Should have NO alternative markers in implementation
        return alternative_count == 0
