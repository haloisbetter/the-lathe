# lathe-context

**Assemble and scope context for AI interactions.**

## Responsibilities

This subsystem provides:
- **Context assembly**: Combine multiple sources into coherent context
- **Source filtering**: Apply rules to include/exclude sources
- **Prioritization**: Rank sources by importance, recency, or custom criteria
- **Content limitation**: Prevent context flooding and token limit violations
- **Statistics**: Analyze source characteristics and context metrics

## Non-Responsibilities

This subsystem does NOT:
- Store or retrieve context from databases
- Manage knowledge bases or vector embeddings
- Execute validation rules
- Execute prompts or invoke AI models
- Handle persistence or caching
- Select which prompt to use

## Public Interface

### `ContextBuilder`

Main interface for assembling context.

**Methods:**
- `build(sources, filters, sort_by, separator) -> ContextOutput`: Assemble context
- `get_source_stats(sources) -> dict`: Get statistics about sources
- `truncate_content(content, max_length, preserve_words) -> str`: Truncate text safely

**Constructor:**
```python
ContextBuilder(max_content_length=50000)  # Optional limit
```

### `SourceFilter`

Filtering criteria for sources.

**Fields:**
- `source_type`: Filter by type (knowledge, memory, file, metadata, custom)
- `min_priority`: Minimum priority threshold (0-100)
- `max_sources`: Maximum number of sources to include
- `content_min_length`: Minimum content length
- `custom_filter`: Custom callable filter

**Methods:**
- `matches(source) -> bool`: Check if source matches criteria

### `SourcePrioritizer`

Static utility for source ranking.

**Static Methods:**
- `sort_by_priority(sources) -> List[ContextSource]`: Sort by priority (high first)
- `sort_by_recency(sources) -> List[ContextSource]`: Sort by creation date
- `scale_priorities(sources, min, max) -> List[ContextSource]`: Rescale priorities

## Data Contracts

### Input: List[ContextSource]
```python
sources = [
    ContextSource(
        type=ContextSourceType.FILE,
        identifier="main.py",
        content="def process(): ...",
        priority=90
    ),
    ContextSource(
        type=ContextSourceType.KNOWLEDGE,
        identifier="best_practices",
        content="Always use type hints",
        priority=70
    ),
]
```

### Output: ContextOutput
```python
ContextOutput(
    assembled_content="def process(): ...\n---\nAlways use type hints",
    sources_used=["main.py", "best_practices"],
    total_tokens_estimated=24,
    metadata={
        "sources_considered": 2,
        "sources_included": 2,
        "sort_method": "priority",
        "content_length": 96,
    }
)
```

## Usage Example

```python
from lathe.context import ContextBuilder, SourceFilter
from lathe.shared.models import ContextSource
from lathe.shared.enums import ContextSourceType

# Create builder
builder = ContextBuilder(max_content_length=10000)

# Create sources
sources = [
    ContextSource(
        type=ContextSourceType.FILE,
        identifier="utils.py",
        content="Helper functions...",
        priority=80
    ),
    ContextSource(
        type=ContextSourceType.MEMORY,
        identifier="recent_context",
        content="User previously asked about...",
        priority=60
    ),
]

# Apply filters
filters = [
    SourceFilter(min_priority=50),  # Only high-priority sources
    SourceFilter(content_min_length=10),  # Only substantial content
]

# Build context
output = builder.build(sources, filters=filters, sort_by="priority")

# Output has assembled content ready for AI
print(output.assembled_content)
print(f"Used {len(output.sources_used)} sources")
print(f"Est. tokens: {output.total_tokens_estimated}")
```

## State Model

- **Stateless builder**: No internal state between `build()` calls
- **Immutable sources**: Doesn't modify input sources
- **Explicit outputs**: All decisions visible in metadata

## Context Assembly Rules

1. **Filtering**: All filters must match (AND logic)
2. **Sorting**: Sources ordered before assembly
3. **Length limits**: Sources truncated or skipped if over limit
4. **Separator**: Configurable separator between sources
5. **Token estimation**: Rough estimate (1 token ≈ 4 characters)

## Source Priority Ranges

Suggested priority conventions:
- **90-100**: Critical context (current task, critical errors)
- **70-89**: High value (recent interactions, relevant files)
- **50-69**: Medium value (related context, documentation)
- **30-49**: Low value (background info, old context)
- **0-29**: Minimal value (archived, minimal relevance)

## Future Extension Points

1. **Semantic Reranking**: Add embeddings-based relevance scoring
2. **Caching**: Cache frequently used source combinations
3. **Compression**: Compress context while preserving semantics
4. **Deduplication**: Remove duplicate or near-duplicate sources
5. **Metadata-based Filtering**: Filter by custom metadata fields
6. **Time-based Decay**: Reduce priority of old sources over time

## Design Decisions

1. **Stateless by default**: Caller manages source lifecycle
2. **No persistence**: No database or cache assumptions
3. **Explicit filtering**: All filters applied (no silent drops)
4. **Token estimation**: Approximate, fast calculation
5. **Configurable order**: Sort method is optional parameter
6. **Separator-based**: Simple, debuggable assembly

## Example Context Assembly Flow

```
Input: 10 candidate sources
  ↓
Apply filters: min_priority=50 (→ 6 sources)
  ↓
Sort by priority (→ highest first)
  ↓
Accumulate until max_length exceeded (→ 5 sources)
  ↓
Join with separator: "\n---\n"
  ↓
Output: ContextOutput with 5 sources, token estimate
```
