"""
Prompt registry interface for lathe-prompts subsystem.

Provides in-memory registration, lookup, and versioning of prompts.
"""

from typing import Dict, List, Optional
from lathe.prompts.schemas import Prompt
from lathe.shared.enums import PromptScope
from lathe.shared.models import PromptMetadata
from datetime import datetime


class PromptRegistry:
    """
    In-memory registry for system prompts.

    Provides:
    - Register and store prompts
    - Lookup prompts by ID or scope
    - Version tracking
    - Prompt metadata retrieval

    State:
    - In-memory only (no persistence)
    - Cleared on instantiation
    """

    def __init__(self):
        """Initialize empty registry."""
        # Structure: {prompt_id: {version: Prompt}}
        self._prompts: Dict[str, Dict[str, Prompt]] = {}
        # Structure: {prompt_id: PromptMetadata}
        self._metadata: Dict[str, PromptMetadata] = {}

    def register(
        self,
        prompt: Prompt,
        scope: PromptScope = PromptScope.GLOBAL,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> PromptMetadata:
        """
        Register a prompt in the registry.

        Args:
            prompt: Prompt to register
            scope: Scope (global, project, task, custom)
            description: Optional description
            tags: Optional list of tags

        Returns:
            PromptMetadata for the registered prompt

        Raises:
            ValueError: If prompt validation fails
        """
        if not prompt.validate():
            raise ValueError(f"Invalid prompt: {prompt.id}")

        # Store prompt by version
        if prompt.id not in self._prompts:
            self._prompts[prompt.id] = {}

        self._prompts[prompt.id][prompt.version] = prompt

        # Update metadata
        metadata = PromptMetadata(
            id=prompt.id,
            scope=scope,
            name=prompt.name,
            version=prompt.version,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            description=description,
            tags=tags or [],
        )
        self._metadata[prompt.id] = metadata

        return metadata

    def get_prompt(
        self,
        prompt_id: str,
        version: Optional[str] = None,
    ) -> Optional[Prompt]:
        """
        Retrieve a prompt by ID and optional version.

        Args:
            prompt_id: ID of prompt to retrieve
            version: Specific version (if None, returns latest)

        Returns:
            Prompt if found, None otherwise
        """
        if prompt_id not in self._prompts:
            return None

        versions = self._prompts[prompt_id]
        if not versions:
            return None

        if version:
            return versions.get(version)

        # Return latest version (last in dict, assuming insertion order)
        return list(versions.values())[-1]

    def get_metadata(self, prompt_id: str) -> Optional[PromptMetadata]:
        """
        Retrieve metadata for a prompt.

        Args:
            prompt_id: ID of prompt

        Returns:
            PromptMetadata if found, None otherwise
        """
        return self._metadata.get(prompt_id)

    def list_prompts(self, scope: Optional[PromptScope] = None) -> List[PromptMetadata]:
        """
        List all registered prompts, optionally filtered by scope.

        Args:
            scope: Optional scope to filter by

        Returns:
            List of PromptMetadata
        """
        results = list(self._metadata.values())
        if scope:
            results = [m for m in results if m.scope == scope]
        return results

    def list_versions(self, prompt_id: str) -> List[str]:
        """
        List all versions of a prompt.

        Args:
            prompt_id: ID of prompt

        Returns:
            List of version strings, empty if prompt not found
        """
        if prompt_id not in self._prompts:
            return []
        return list(self._prompts[prompt_id].keys())

    def delete_prompt(self, prompt_id: str, version: Optional[str] = None) -> bool:
        """
        Delete a prompt or specific version.

        Args:
            prompt_id: ID of prompt
            version: Specific version to delete (if None, delete all versions)

        Returns:
            True if deleted, False if not found
        """
        if prompt_id not in self._prompts:
            return False

        if version:
            if version in self._prompts[prompt_id]:
                del self._prompts[prompt_id][version]
                # If no versions left, clean up
                if not self._prompts[prompt_id]:
                    del self._prompts[prompt_id]
                    if prompt_id in self._metadata:
                        del self._metadata[prompt_id]
                return True
        else:
            del self._prompts[prompt_id]
            if prompt_id in self._metadata:
                del self._metadata[prompt_id]
            return True

        return False

    def count_prompts(self) -> int:
        """Return total number of unique prompts registered."""
        return len(self._prompts)
