"""
Source definitions and filtering for lathe-context subsystem.

Defines types of context sources and filtering rules.
"""

from dataclasses import dataclass
from typing import Optional, Callable
from lathe.shared.enums import ContextSourceType
from lathe.shared.models import ContextSource


@dataclass
class SourceFilter:
    """
    Filtering rules for context sources.

    Attributes:
        source_type: Filter by source type (None = all types)
        min_priority: Minimum priority threshold (0-100)
        max_sources: Maximum number of sources to include
        content_min_length: Minimum content length in characters
        custom_filter: Optional callable for custom filtering
    """

    source_type: Optional[ContextSourceType] = None
    min_priority: int = 0
    max_sources: Optional[int] = None
    content_min_length: int = 0
    custom_filter: Optional[Callable[[ContextSource], bool]] = None

    def matches(self, source: ContextSource) -> bool:
        """
        Check if a source matches all filter criteria.

        Args:
            source: Source to check

        Returns:
            True if source matches all criteria
        """
        # Type filter
        if self.source_type and source.type != self.source_type:
            return False

        # Priority filter
        if source.priority < self.min_priority:
            return False

        # Content length filter
        if len(source.content) < self.content_min_length:
            return False

        # Custom filter
        if self.custom_filter and not self.custom_filter(source):
            return False

        return True


class SourcePrioritizer:
    """
    Prioritizes context sources based on ranking rules.

    Provides methods to sort and rank sources by priority,
    recency, relevance, or custom criteria.
    """

    @staticmethod
    def sort_by_priority(sources: list[ContextSource]) -> list[ContextSource]:
        """
        Sort sources by priority (highest first).

        Args:
            sources: List of sources to sort

        Returns:
            Sorted list (highest priority first)
        """
        return sorted(sources, key=lambda s: s.priority, reverse=True)

    @staticmethod
    def sort_by_recency(sources: list[ContextSource]) -> list[ContextSource]:
        """
        Sort sources by recency.

        Requires 'created_at' in source metadata.

        Args:
            sources: List of sources to sort

        Returns:
            Sorted list (most recent first)
        """
        return sorted(
            sources,
            key=lambda s: s.metadata.get("created_at", ""),
            reverse=True,
        )

    @staticmethod
    def scale_priorities(
        sources: list[ContextSource],
        min_priority: int = 0,
        max_priority: int = 100,
    ) -> list[ContextSource]:
        """
        Rescale priorities to a given range.

        Args:
            sources: List of sources
            min_priority: New minimum priority
            max_priority: New maximum priority

        Returns:
            List of sources with rescaled priorities
        """
        if not sources:
            return sources

        current_priorities = [s.priority for s in sources]
        current_min = min(current_priorities)
        current_max = max(current_priorities)

        if current_min == current_max:
            # All same priority, set to middle
            for s in sources:
                s.priority = (min_priority + max_priority) // 2
            return sources

        # Linear rescaling
        for source in sources:
            normalized = (source.priority - current_min) / (current_max - current_min)
            source.priority = int(
                min_priority + normalized * (max_priority - min_priority)
            )

        return sources
