# lathe-prompts

**Central registry for system prompts with versioning support.**

## Responsibilities

This subsystem provides:
- **Prompt registration**: Store prompts with metadata
- **Lookup and retrieval**: Find prompts by ID, scope, or version
- **Versioning**: In-memory version tracking (no persistence)
- **Validation**: Ensure prompts meet structure requirements
- **Organization**: Scope prompts by domain (global, project, task, custom)
- **Variable substitution**: Replace placeholders in prompt content

## Non-Responsibilities

This subsystem does NOT:
- Persist prompts to database or filesystem
- Execute prompts or invoke AI models
- Render UI or provide web interfaces
- Select context for prompts
- Validate prompt outputs
- Handle orchestration

## Public Interface

### `PromptRegistry`

Central in-memory registry for prompts.

**Methods:**
- `register(prompt, scope, description, tags) -> PromptMetadata`: Register a new prompt
- `get_prompt(prompt_id, version) -> Prompt | None`: Retrieve a specific prompt
- `get_metadata(prompt_id) -> PromptMetadata | None`: Get prompt metadata
- `list_prompts(scope) -> List[PromptMetadata]`: List all prompts (optionally filtered)
- `list_versions(prompt_id) -> List[str]`: Get all versions of a prompt
- `delete_prompt(prompt_id, version) -> bool`: Delete a prompt or version
- `count_prompts() -> int`: Get total prompt count

### `Prompt`

Data model for a system prompt.

**Fields:**
- `id`: Unique identifier
- `name`: Human-readable name
- `content`: The actual prompt text
- `version`: Version identifier
- `description`: Optional description
- `metadata`: Arbitrary metadata dict
- `variables`: Placeholders for substitution

**Methods:**
- `validate() -> bool`: Check if prompt is valid
- `substitute_variables(values) -> str`: Replace variables in content

## Data Contracts

### Input: Prompt
```python
Prompt(
    id="prompt_1",
    name="Code Review",
    content="Review this code: {code}",
    version="1.0",
    variables={"code": ""}
)
```

### Output: PromptMetadata
```python
PromptMetadata(
    id="prompt_1",
    scope=PromptScope.GLOBAL,
    name="Code Review",
    version="1.0",
    created_at=datetime.now(),
    updated_at=datetime.now()
)
```

## Usage Example

```python
from lathe.prompts import PromptRegistry, Prompt
from lathe.shared.enums import PromptScope

# Create registry
registry = PromptRegistry()

# Create and register a prompt
prompt = Prompt(
    id="review_code",
    name="Code Review Assistant",
    content="Review the following code for best practices: {code}",
    version="1.0"
)

metadata = registry.register(
    prompt,
    scope=PromptScope.TASK,
    description="Reviews code submissions"
)

# Retrieve prompt
retrieved = registry.get_prompt("review_code")

# Substitute variables
filled = retrieved.substitute_variables({"code": "def foo(): pass"})

# List all versions
versions = registry.list_versions("review_code")
```

## State Model

- **In-memory only**: All data stored in RAM, cleared on restart
- **No persistence adapters**: Direct API, no database layer
- **Singleton pattern encouraged**: One registry instance per application

## Future Extension Points

1. **Persistence Adapter**: Add a `storage` module with database backends
2. **Prompt Templates**: Add template rendering (Jinja2, etc.)
3. **Validation Rules**: Add advanced validation (schema, content checks)
4. **Import/Export**: Add YAML/JSON serialization
5. **Access Control**: Add permission checks per scope

## Design Decisions

1. **In-memory first**: Simplicity and speed for scaffolding
2. **No orchestration**: Clients decide when to use prompts
3. **Simple versioning**: String-based, not semantic versioning enforced
4. **Scope-based organization**: Aligns with Lathe task hierarchy
5. **Explicit validation**: Prompts must pass validation before registration

## Example Prompts (Placeholder)

```python
# Code analysis
"Analyze this code for performance issues: {code}"

# Documentation
"Generate documentation for this function: {function_name}"

# Testing
"Write unit tests for this code: {code}"

# Refactoring
"Suggest refactoring improvements: {code}"
```
