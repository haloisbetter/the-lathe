"""
Context builder interface for lathe-context subsystem.

Assembles context from multiple sources with prioritization and filtering.
"""

import hashlib
from typing import List, Optional, Tuple
from lathe.shared.models import ContextSource, ContextOutput
from lathe.context.sources import SourceFilter, SourcePrioritizer


def get_file_context_from_lines(path_part: str, all_lines: List[str], start: int, end: int, max_lines: int = 500) -> dict:
    """
    Assembles context from a list of strings (lines).
    No file I/O occurs here.
    """
    if start < 1:
        start = 1

    if end - start + 1 > max_lines:
        end = start + max_lines - 1

    lines_to_return = []
    actual_end = min(end, len(all_lines))
    content_to_hash = ""

    for i in range(start - 1, actual_end):
        line_content = all_lines[i]
        lines_to_return.append((i + 1, line_content.rstrip()))
        content_to_hash += line_content

    content_hash = hashlib.sha256(content_to_hash.encode("utf-8")).hexdigest()

    return {
        "path": path_part,
        "lines": lines_to_return,
        "hash": content_hash
    }


class ContextBuilder:
    """
    Builds assembled context from multiple sources.

    Responsibilities:
    - Accept candidate sources
    - Apply filtering and prioritization rules
    - Prevent context flooding
    - Produce structured ContextOutput

    State:
    - Stateless (no internal state between calls)
    """

    def __init__(self, max_content_length: Optional[int] = None):
        """
        Initialize context builder.

        Args:
            max_content_length: Maximum total content length (None = unlimited)
        """
        self.max_content_length = max_content_length
        self._token_estimate_ratio = 0.25  # Rough estimate: 1 token per 4 chars

    def build(
        self,
        sources: List[ContextSource],
        filters: Optional[List[SourceFilter]] = None,
        sort_by: str = "priority",
        separator: str = "\n---\n",
    ) -> ContextOutput:
        """
        Build assembled context from sources.

        Args:
            sources: List of candidate sources
            filters: Optional list of filters (all must match)
            sort_by: How to sort ("priority", "recency", or None)
            separator: Separator string between sources

        Returns:
            ContextOutput with assembled content
        """
        # Apply all filters
        filtered = sources
        if filters:
            for filter_obj in filters:
                filtered = [s for s in filtered if filter_obj.matches(s)]

        # Sort sources
        if sort_by == "priority":
            filtered = SourcePrioritizer.sort_by_priority(filtered)
        elif sort_by == "recency":
            filtered = SourcePrioritizer.sort_by_recency(filtered)

        # Assemble content with length limit
        assembled_parts = []
        total_length = 0
        sources_used = []

        for source in filtered:
            content_to_add = source.content
            total_length_after = total_length + len(content_to_add) + len(separator)

            # Check length limit
            if (
                self.max_content_length
                and total_length_after > self.max_content_length
            ):
                # Skip this source to avoid exceeding limit
                continue

            assembled_parts.append(content_to_add)
            sources_used.append(source.identifier)
            total_length = total_length_after

        # Join all parts
        assembled_content = separator.join(assembled_parts)

        # Estimate tokens
        estimated_tokens = int(total_length * self._token_estimate_ratio)

        return ContextOutput(
            assembled_content=assembled_content,
            sources_used=sources_used,
            total_tokens_estimated=estimated_tokens,
            metadata={
                "filter_count": len(filters) if filters else 0,
                "sources_considered": len(sources),
                "sources_included": len(sources_used),
                "sort_method": sort_by,
                "content_length": total_length,
            },
        )

    def get_source_stats(self, sources: List[ContextSource]) -> dict:
        """
        Get statistics about a set of sources.

        Args:
            sources: List of sources

        Returns:
            Dictionary with statistics
        """
        if not sources:
            return {
                "count": 0,
                "total_length": 0,
                "avg_priority": 0,
                "types": {},
            }

        total_length = sum(len(s.content) for s in sources)
        avg_priority = sum(s.priority for s in sources) / len(sources)

        type_counts = {}
        for source in sources:
            type_name = source.type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        return {
            "count": len(sources),
            "total_length": total_length,
            "avg_priority": avg_priority,
            "types": type_counts,
            "avg_content_length": total_length // len(sources),
        }

    def truncate_content(
        self,
        content: str,
        max_length: int,
        preserve_words: bool = True,
    ) -> str:
        """
        Truncate content to max length.

        Args:
            content: Content to truncate
            max_length: Maximum length
            preserve_words: If True, truncate at word boundary

        Returns:
            Truncated content
        """
        if len(content) <= max_length:
            return content

        if not preserve_words:
            return content[:max_length]

        # Truncate at word boundary
        truncated = content[:max_length]
        last_space = truncated.rfind(" ")

        if last_space > 0:
            truncated = truncated[:last_space]

        return truncated.strip() + "..."
