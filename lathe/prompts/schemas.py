"""
Prompt schema definitions for lathe-prompts subsystem.

Defines the structure and validation rules for prompts.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class Prompt:
    """
    A system prompt with metadata and content.

    Attributes:
        id: Unique identifier
        name: Human-readable name
        content: The actual prompt text
        version: Version identifier (e.g., "1.0", "1.1")
        description: Optional description of the prompt's purpose
        metadata: Additional structured metadata
        variables: Placeholders that can be substituted (e.g., {project_name})
    """

    id: str
    name: str
    content: str
    version: str
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, str] = field(default_factory=dict)

    def validate(self) -> bool:
        """
        Validate prompt structure.

        Returns:
            True if valid, False otherwise.

        Checks:
        - id and name are non-empty
        - content is non-empty
        - version follows semantic versioning
        """
        if not self.id or not self.name:
            return False
        if not self.content or not self.content.strip():
            return False
        # Basic version format check (e.g., "1.0", "2.1.3")
        if not self.version or not any(c.isdigit() for c in self.version):
            return False
        return True

    def substitute_variables(self, values: Dict[str, str]) -> str:
        """
        Substitute variables in prompt content.

        Args:
            values: Dictionary mapping variable names to values

        Returns:
            Content with variables substituted
        """
        result = self.content
        for var_name, var_value in values.items():
            result = result.replace(f"{{{var_name}}}", var_value)
        return result
