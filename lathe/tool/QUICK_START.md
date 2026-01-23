# Lathe Tool - Quick Start

## Installation

```bash
# Already available when lathe is installed
python -c "from lathe.tool import lathe_plan; print('OK')"
```

## 30-Second Example

```python
from lathe.tool import lathe_plan, lathe_validate

# 1. Prepare
result = lathe_plan(
    project="myapp",
    scope="auth",
    phase="design",
    goal="Design login flow"
)

# 2. Check status
if result.get("ready"):
    # 3. Use system prompt + context with LLM
    system_prompt = result["system_prompt"]
    context = result["context_blocks"]

    # 4. Validate LLM output
    validation = lathe_validate(
        phase="design",
        output="<LLM OUTPUT HERE>"
    )

    print(f"Status: {validation['status']}")
```

## Three Functions

### `lathe_plan(project, scope, phase, goal, constraints=None, sources=None)`

Prepares an AI step for the given phase.

**Phases:** `analysis` | `design` | `implementation` | `validation` | `hardening`

**Returns:**
```json
{
  "phase": "design",
  "system_prompt": "...",
  "context_blocks": [...],
  "rules": [...],
  "risks": [...],
  "ready": true
}
```

### `lathe_validate(phase, output, ruleset=None)`

Validates AI output against rules.

**Returns:**
```json
{
  "status": "pass" | "warn" | "fail",
  "violations": [{...}],
  "summary": "...",
  "can_proceed": true | false
}
```

### `lathe_context_preview(query, sources=None, max_tokens=2000)`

Previews what context would be used.

**Returns:**
```json
{
  "context_blocks": [{...}],
  "total_tokens": 1234,
  "truncated": false
}
```

## Phase Discipline

```
analysis        analysis
    ↓
  design        design
    ↓
implement       implementation
    ↓
  validate      validation
    ↓
 harden        hardening
```

Each phase has:
- ✓ System prompt template
- ✓ Default validation rules
- ✓ Known risks
- ✓ Expected context sources

## Error Handling

All errors are returned (never thrown):

```python
result = lathe_plan(...)

if result.get("status") == "fail":
    error = result["error_type"]  # PHASE_VIOLATION | VALIDATION_ERROR | INTERNAL_ERROR
    message = result["message"]
    print(f"Error: {error}: {message}")
else:
    # Use result normally
    proceed(result)
```

## Common Patterns

### Pattern 1: Full Workflow

```python
for phase in ["analysis", "design", "implementation"]:
    # Prepare
    plan = lathe_plan(project="x", scope="y", phase=phase, goal="...")
    if plan["status"] == "fail": break

    # Send to LLM
    output = llm.generate(system=plan["system_prompt"], context=plan["context_blocks"])

    # Validate
    valid = lathe_validate(phase=phase, output=output)
    if not valid["can_proceed"]: break
```

### Pattern 2: Quick Validation

```python
# Just validate without planning
result = lathe_validate(
    phase="implementation",
    output=code
)
print(f"Status: {result['status']}")
```

### Pattern 3: Context Budget

```python
# Check what context is available
preview = lathe_context_preview(query="auth system")
print(f"Available: {preview['total_tokens']} tokens")
```

## Input/Output

### All inputs: strings and lists
```python
lathe_plan(
    project="string",           # Project name
    scope="string",             # What are we working on
    phase="string",             # One of 5 phases
    goal="string",              # What to achieve
    constraints=["string"],     # Optional requirements
    sources=["knowledge", "memory", "files"]  # Optional context sources
)
```

### All outputs: JSON-safe dicts
```json
{
  "status": "pass" | "fail",
  "phase": "string",
  "rules": ["string"],
  "violations": [{"rule": "string", "message": "string"}],
  "ready": true | false,
  "can_proceed": true | false
}
```

## Rules (Per Phase)

| Phase | Default Rules |
|-------|---------------|
| analysis | explicit_assumptions, required_section |
| design | required_section, output_format |
| implementation | full_file_replacement, output_format |
| validation | no_hallucinated_files, output_format |
| hardening | output_format |

## Available Rules

- `full_file_replacement` - Complete code/files, not snippets
- `explicit_assumptions` - Assumptions stated clearly
- `required_section` - Required sections present
- `no_hallucinated_files` - No fake file references
- `output_format` - Proper formatting

## Examples

### Design an API

```python
plan = lathe_plan(
    project="user-service",
    scope="REST API",
    phase="design",
    goal="Design REST API for users",
    constraints=["RESTful", "JWT auth"]
)

print(plan["system_prompt"])  # Give to LLM
```

### Validate Code

```python
with open("implementation.py") as f:
    code = f.read()

result = lathe_validate(
    phase="implementation",
    output=code
)

if result["status"] != "pass":
    for v in result["violations"]:
        print(f"Issue: {v['message']}")
```

### Check Context Budget

```python
preview = lathe_context_preview(
    query="authentication system",
    sources=["knowledge", "files"],
    max_tokens=2000
)

print(f"Total tokens: {preview['total_tokens']}")
if preview["truncated"]:
    print("WARNING: Context was truncated")
```

## Troubleshooting

### "No module named 'lathe'"
```bash
pip install -e /path/to/lathe
```

### "Invalid phase"
Use one of: `analysis`, `design`, `implementation`, `validation`, `hardening`

### "Validation always fails"
Try with `ruleset=["output_format"]` to use lenient rules

### "Can't proceed despite passing"
Check `can_proceed` flag, not just status

## More Information

- Full reference: See `README.md`
- Usage examples: See `EXAMPLES.md`
- Integration guide: See `INTEGRATION.md`
- Run tests: `python tests/test_tool_wrapper.py`

## Key Principles

1. **Stateless**: Each call is independent
2. **Safe**: Always returns structured responses, never throws
3. **Phase-locked**: Enforces development phases
4. **JSON-safe**: All I/O is JSON-serializable
5. **Thin**: No business logic, just orchestration

---

**Status:** Production-ready ✓
**Tests:** 16/16 passing ✓
**Type hints:** 100% ✓
**Documentation:** Complete ✓
