# Lathe OpenWebUI Tool Wrapper

This module provides the thin orchestration layer between OpenWebUI and The Lathe subsystems.

## Overview

The Lathe tool wrapper is a **stateless, thin orchestrator** that:
- ✓ Accepts structured JSON inputs
- ✓ Calls existing subsystems in controlled order
- ✓ Returns structured JSON outputs
- ✓ Enforces phase discipline
- ✓ Does NOT modify existing subsystems
- ✓ Does NOT persist data
- ✓ Does NOT implement business logic

## Installation

The tool is automatically available when lathe is installed:

```python
from lathe.tool import lathe_plan, lathe_validate, lathe_context_preview
```

## Functions

### 1. lathe_plan

**Purpose:** Prepare a phase-locked AI step before model execution.

**Orchestrates:**
- `lathe-prompts`: Retrieve system prompt for phase
- `lathe-context`: Assemble scoped context
- Aggregate rules and risks

**Input:**
```python
lathe_plan(
    project: str,           # Project identifier
    scope: str,             # Scope of work (e.g., "module", "component")
    phase: str,             # Phase: analysis | design | implementation | validation | hardening
    goal: str,              # Goal for this step
    constraints: List[str], # Optional constraints
    sources: List[str]      # Optional source types: knowledge, memory, files
)
```

**Output (on success):**
```json
{
  "phase": "string",
  "system_prompt": "string",
  "context_blocks": [
    {
      "type": "string",
      "content": "string",
      "metadata": {}
    }
  ],
  "rules": ["string"],
  "risks": ["string"],
  "ready": true
}
```

**Output (on error):**
```json
{
  "status": "fail",
  "error_type": "PHASE_VIOLATION | VALIDATION_ERROR | INTERNAL_ERROR",
  "message": "string",
  "details": {}
}
```

**Example:**
```python
result = lathe_plan(
    project="myproject",
    scope="authentication",
    phase="design",
    goal="Design user authentication flow",
    constraints=["OAuth2 required", "HIPAA compliant"],
    sources=["knowledge", "memory"]
)
```

### 2. lathe_validate

**Purpose:** Validate an AI response against Lathe rules.

**Orchestrates:**
- `lathe-validation`: Run specified rules against output
- Does NOT modify output or attempt auto-fix

**Input:**
```python
lathe_validate(
    phase: str,           # Current phase
    output: str,          # AI-generated output to validate
    ruleset: List[str]    # Optional rule names; uses phase defaults if None
)
```

**Available rules:**
- `full_file_replacement` - Check for complete files
- `explicit_assumptions` - Require assumption statements
- `required_section` - Enforce section headers
- `no_hallucinated_files` - Detect fake file references
- `output_format` - Check format compliance

**Output (on success):**
```json
{
  "status": "pass | warn | fail",
  "violations": [
    {
      "rule": "string",
      "message": "string"
    }
  ],
  "summary": "string",
  "can_proceed": true | false
}
```

**Output (on error):**
```json
{
  "status": "fail",
  "error_type": "VALIDATION_ERROR | INTERNAL_ERROR",
  "message": "string",
  "details": {}
}
```

**Example:**
```python
result = lathe_validate(
    phase="implementation",
    output="def authenticate(username, password):\n    # implementation here",
    ruleset=["full_file_replacement", "output_format"]
)
```

**Phase-specific default rules:**
- `analysis`: explicit_assumptions, required_section
- `design`: required_section, output_format
- `implementation`: full_file_replacement, output_format
- `validation`: no_hallucinated_files, output_format
- `hardening`: output_format

### 3. lathe_context_preview (Optional)

**Purpose:** Preview what context would be injected.

**Orchestrates:**
- `lathe-context`: Assemble context with token estimates

**Input:**
```python
lathe_context_preview(
    query: str,        # Query or identifier for context
    sources: List[str],# Source types: knowledge, memory, files
    max_tokens: int    # Maximum tokens (default: 2000)
)
```

**Output (on success):**
```json
{
  "context_blocks": [
    {
      "source": "string",
      "size_tokens": 123,
      "preview": "string"
    }
  ],
  "total_tokens": 1234,
  "truncated": false
}
```

**Output (on error):**
```json
{
  "status": "fail",
  "error_type": "INTERNAL_ERROR",
  "message": "string",
  "details": {}
}
```

**Example:**
```python
result = lathe_context_preview(
    query="authentication system",
    sources=["knowledge", "files"],
    max_tokens=2000
)
```

## Phase Discipline

The wrapper enforces phase transitions:

```
analysis → design → implementation → validation → hardening
```

Each phase has:
- **System prompt template** - Defines phase-specific instructions
- **Default rules** - Validation rules automatically applied
- **Risk factors** - Known risks for this phase
- **Context requirements** - Recommended context sources

### Phase Guidelines

**Analysis:** Discover requirements, identify unknowns
- Rules: explicit_assumptions, required_section
- Risks: Incomplete understanding, missing edge cases

**Design:** Plan architecture and interfaces
- Rules: required_section, output_format
- Risks: Over-engineering, unclear interfaces

**Implementation:** Write code and tests
- Rules: full_file_replacement, output_format
- Risks: Off-by-one errors, missing error cases

**Validation:** Test comprehensively
- Rules: no_hallucinated_files, output_format
- Risks: Test gaps, integration issues

**Hardening:** Secure and optimize
- Rules: output_format
- Risks: Regression bugs, performance impact

## Error Handling

All errors are returned as structured JSON (never raise exceptions):

```json
{
  "status": "fail",
  "error_type": "PHASE_VIOLATION | VALIDATION_ERROR | INTERNAL_ERROR",
  "message": "Human-readable error",
  "details": {
    "exception": "ExceptionType",
    ...
  }
}
```

**Error Types:**

| Type | Cause | Action |
|------|-------|--------|
| PHASE_VIOLATION | Invalid phase or phase transition | Check phase value |
| VALIDATION_ERROR | Rule evaluation failed | Review rule output |
| INTERNAL_ERROR | Subsystem call failed | Check subsystem logs |

## What This Tool Does

✓ Orchestrates calls to existing subsystems
✓ Accepts and returns JSON
✓ Enforces phase discipline
✓ Validates inputs and outputs
✓ Returns structured errors
✓ Supports multiple context sources
✓ Provides context budgeting via tokens

## What This Tool Does NOT Do

✗ Generate AI responses (only prepares context)
✗ Store state between calls
✗ Persist data
✗ Modify existing subsystems
✗ Implement business logic
✗ Cache results
✗ Support dynamic rule creation
✗ Manage project files or repositories

## Integration with OpenWebUI

### As a Tool

Add to OpenWebUI's tool configuration:

```yaml
tools:
  - name: lathe
    type: python
    module: lathe.tool
    functions:
      - lathe_plan
      - lathe_validate
      - lathe_context_preview
```

### Workflow Example

```
User: "Design authentication for my project"
  ↓
OpenWebUI calls: lathe_plan(project="myapp", phase="design", goal="...")
  ↓
Tool returns: system_prompt, context, rules, risks
  ↓
OpenWebUI sends context + prompt to LLM
  ↓
LLM generates design document
  ↓
OpenWebUI calls: lathe_validate(phase="design", output="...")
  ↓
Tool returns: pass/warn/fail + violations
  ↓
OpenWebUI reports results to user
```

## Dependencies

The tool uses only existing Lathe subsystems:
- `lathe.prompts` - System prompt registry
- `lathe.context` - Context assembly
- `lathe.validation` - Rule validation
- `lathe.shared` - Shared data models and enums

## Source Code Structure

```
lathe/tool/
├── __init__.py       # Public API exports
├── wrapper.py        # Implementation
└── README.md         # This file
```

## Type Hints

All public functions have full type hints:

```python
def lathe_plan(
    project: str,
    scope: str,
    phase: str,
    goal: str,
    constraints: Optional[List[str]] = None,
    sources: Optional[List[str]] = None,
) -> Dict[str, Any]:
    ...
```

## Testing

Test the tool with simple Python code:

```python
from lathe.tool import lathe_plan, lathe_validate

# Test plan
result = lathe_plan(
    project="test",
    scope="module",
    phase="analysis",
    goal="Test goal"
)
assert result.get("ready") == True

# Test validate
result = lathe_validate(
    phase="analysis",
    output="Testing output validation"
)
assert result.get("status") in ["pass", "warn", "fail"]
```

## Performance

- **lathe_plan**: <100ms (depends on context assembly)
- **lathe_validate**: <50ms (depends on number of rules)
- **lathe_context_preview**: <50ms (depends on sources)

All functions are stateless and reentrant.

## Security Notes

- ✓ No filesystem access
- ✓ No database access
- ✓ No external API calls
- ✓ No credential handling
- ✓ Stateless (no cross-request state)
- ✓ JSON-only I/O (no code execution)

## Future Extensions

Possible additions (without modifying core):
- Custom rule registration
- Context source plugins
- Phase workflow validation
- Metrics collection
- Audit logging

## License

Same as The Lathe project.

## Support

For issues or questions:
1. Check the function docstrings
2. Review phase discipline guidelines
3. Examine error details in response
4. Check individual subsystem README files in lathe/
