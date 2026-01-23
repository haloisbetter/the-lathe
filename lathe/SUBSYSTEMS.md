# Lathe Subsystems Architecture

**Three independent subsystems for AI-assisted code generation.**

## Overview

```
lathe/
├── shared/                 # Shared data contracts (schemas, enums)
│   ├── __init__.py
│   ├── enums.py           # ValidationLevel, ContextSourceType, PromptScope
│   ├── models.py          # PromptMetadata, ContextSource, ValidationResult
│   └── README.md
│
├── prompts/               # Central prompt registry
│   ├── __init__.py
│   ├── schemas.py         # Prompt model and validation
│   ├── registry.py        # PromptRegistry interface
│   └── README.md
│
├── context/               # Context assembly
│   ├── __init__.py
│   ├── sources.py         # SourceFilter, SourcePrioritizer
│   ├── builder.py         # ContextBuilder interface
│   └── README.md
│
├── validation/            # Output validation
│   ├── __init__.py
│   ├── rules.py           # ValidationRule implementations
│   ├── engine.py          # ValidationEngine, Pipeline
│   └── README.md
│
└── SUBSYSTEMS.md          # This file
```

## Subsystem Independence

**Explicit Dependency Model:**

```
prompts/          context/          validation/
     │                 │                  │
     └─────────────────┴──────────────────┘
                       │
                   shared/
```

- **No cross-subsystem imports** (prompts ↔ context ↔ validation)
- **All communication via shared/ contracts**
- **Each subsystem is independently testable**
- **Orchestration handled externally (future lathe-core)**

## Subsystem Contracts

### lathe-prompts

**Input:** None (registry initialized empty)

**Output:**
- `PromptMetadata`: Prompt identifier, scope, version, timestamps
- `Prompt`: Full prompt with content, variables, validation

**Public Interface:**
```python
registry = PromptRegistry()
metadata = registry.register(prompt, scope, description, tags)
prompt = registry.get_prompt(prompt_id, version=None)
prompts = registry.list_prompts(scope=PromptScope.TASK)
versions = registry.list_versions(prompt_id)
```

### lathe-context

**Input:**
- `List[ContextSource]`: Candidate context from any source
- `List[SourceFilter]`: Filtering criteria
- String sort method: "priority" | "recency" | None

**Output:**
- `ContextOutput`: Assembled content, sources used, token estimate, metadata

**Public Interface:**
```python
builder = ContextBuilder(max_content_length=50000)
output = builder.build(sources, filters=None, sort_by="priority")
stats = builder.get_source_stats(sources)
truncated = builder.truncate_content(content, max_length=1000)
```

### lathe-validation

**Input:**
- String content to validate
- `List[ValidationRule]`: Rules to apply

**Output:**
- `ValidationResult`: Overall level (pass/warn/fail), per-rule results, errors/warnings

**Public Interface:**
```python
engine = ValidationEngine(fail_fast=False)
result = engine.validate(content, rules)
summary = engine.get_validation_summary(result)

# Pipeline API
pipeline = ValidationPipeline(fail_on_stage_failure=True)
pipeline.add_stage(stage1).add_stage(stage2)
results = pipeline.execute(content)
overall = pipeline.get_overall_result(results)
```

## Data Flow (Future Orchestration)

A typical Lathe workflow *could* look like:

```
1. prompts/ → Get system prompt
2. context/ → Assemble context from sources
3. [AI invocation - external]
4. validation/ → Check AI output
5. [Action - external]
```

But this orchestration is **NOT defined in these subsystems**.
It will be in future `lathe-core`.

## Stateless Design

All subsystems are **stateless by default:**

- **No database access** (data passed in, results returned)
- **No file I/O** (no persistence layer)
- **No caching** (each call is independent)
- **Deterministic** (same inputs → same outputs)

Persistence adapters can be added **later without rewriting subsystem logic**.

## Shared Models Glossary

| Model | Subsystem | Role |
|-------|-----------|------|
| `PromptMetadata` | prompts | Metadata about a registered prompt |
| `Prompt` | prompts | Full prompt with content |
| `ContextSource` | context | Single context candidate |
| `ContextOutput` | context | Assembled context ready for AI |
| `ValidationRule` | validation | Definition of a validation rule |
| `ValidationResult` | validation | Results of validation |

| Enum | Values | Usage |
|------|--------|-------|
| `ValidationLevel` | PASS, WARN, FAIL | Validation severity |
| `ContextSourceType` | KNOWLEDGE, MEMORY, FILE, METADATA, CUSTOM | Source classification |
| `PromptScope` | GLOBAL, PROJECT, TASK, CUSTOM | Prompt organization |

## Error Handling

Each subsystem handles errors internally:

**prompts/**
- `ValueError`: Invalid prompt during registration

**context/**
- Gracefully handles missing metadata
- Skips sources on length overflow
- Returns empty output if all sources filtered

**validation/**
- Catches rule execution errors
- Reports errors in ValidationResult
- Continues with remaining rules

## Testing Strategy

Each subsystem can be tested independently:

```python
# Test prompts
def test_prompt_registry():
    registry = PromptRegistry()
    prompt = Prompt(...)
    registry.register(prompt)
    assert registry.get_prompt(prompt.id) is not None

# Test context
def test_context_builder():
    builder = ContextBuilder()
    sources = [ContextSource(...)]
    output = builder.build(sources)
    assert len(output.sources_used) > 0

# Test validation
def test_validation_engine():
    engine = ValidationEngine()
    rule = FullFileReplacementRule()
    result = engine.validate("def foo(): pass", [rule])
    assert result.overall_level == ValidationLevel.PASS
```

## Extension Points

### 1. Add Persistence Later
```
lathe/
├── shared/
│   └── persistence/      # NEW: Adapter layer
│       ├── base.py       # Abstract adapters
│       ├── supabase.py   # Supabase implementation
│       └── sqlite.py     # SQLite implementation
```

### 2. Add New Subsystem
- Define new models in `shared/`
- Create new subsystem folder
- Import only from `shared/`
- Document in SUBSYSTEMS.md

### 3. Add Orchestration (lathe-core)
```
lathe/
├── core/                 # NEW: Orchestration logic
│   ├── pipeline.py       # Coordinate subsystems
│   ├── workflow.py       # Define execution patterns
│   └── __init__.py
```

## Design Principles (Locked)

1. **Independence**: Subsystems do not import each other
2. **Statelessness**: No hidden state or side effects
3. **Explicit contracts**: All I/O via shared models
4. **Determinism**: Same inputs always produce same outputs
5. **Simplicity**: No premature abstraction
6. **Testability**: Each subsystem independently testable

## Quick Start

### Import subsystems:
```python
from lathe.prompts import PromptRegistry
from lathe.context import ContextBuilder
from lathe.validation import ValidationEngine
from lathe.shared.enums import ValidationLevel, ContextSourceType, PromptScope
from lathe.shared.models import ContextSource, PromptMetadata
```

### Use subsystems:
```python
# Prompts
registry = PromptRegistry()
prompt = Prompt(id="test", name="Test", content="Test", version="1.0")
registry.register(prompt)

# Context
builder = ContextBuilder()
sources = [ContextSource(type=ContextSourceType.FILE, identifier="x", content="y")]
output = builder.build(sources)

# Validation
engine = ValidationEngine()
result = engine.validate("code", rules=[])
```

## Next Steps (Future Work)

1. **Implement lathe-core**: Orchestration logic
2. **Add persistence adapters**: Database layer
3. **Expand rules library**: More validation rules
4. **Implement prompt templates**: Template rendering
5. **Add performance optimizations**: Caching, indexing
6. **Integrate with OpenWebUI**: Tool wrapper layer

## Files Summary

| File | Lines | Purpose |
|------|-------|---------|
| shared/__init__.py | 30 | Public exports |
| shared/enums.py | 35 | Shared enumerations |
| shared/models.py | 150 | Shared data models |
| shared/README.md | 70 | Shared module docs |
| prompts/__init__.py | 20 | Public exports |
| prompts/schemas.py | 80 | Prompt model |
| prompts/registry.py | 200 | Registry implementation |
| prompts/README.md | 200 | Prompts subsystem docs |
| context/__init__.py | 20 | Public exports |
| context/sources.py | 130 | Filtering and prioritization |
| context/builder.py | 180 | Builder implementation |
| context/README.md | 200 | Context subsystem docs |
| validation/__init__.py | 20 | Public exports |
| validation/rules.py | 200 | Rule definitions |
| validation/engine.py | 250 | Engine and pipeline |
| validation/README.md | 250 | Validation subsystem docs |
| **TOTAL** | ~2000 | Well-organized scaffolding |
