# Lathe Tool Integration Guide

How to integrate the Lathe tool wrapper with OpenWebUI and other platforms.

## OpenWebUI Integration

### 1. Register the Tool

Add to OpenWebUI's tool manifest:

```json
{
  "tools": [
    {
      "name": "lathe",
      "type": "python_function",
      "module": "lathe.tool",
      "description": "Lathe AI control layer for phase-locked development",
      "functions": [
        {
          "name": "lathe_plan",
          "description": "Prepare a phase-locked AI step",
          "parameters": {
            "type": "object",
            "properties": {
              "project": {
                "type": "string",
                "description": "Project identifier"
              },
              "scope": {
                "type": "string",
                "description": "Work scope (module, component, etc.)"
              },
              "phase": {
                "type": "string",
                "enum": ["analysis", "design", "implementation", "validation", "hardening"],
                "description": "Current development phase"
              },
              "goal": {
                "type": "string",
                "description": "Goal for this phase"
              },
              "constraints": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional constraints"
              },
              "sources": {
                "type": "array",
                "items": {
                  "type": "string",
                  "enum": ["knowledge", "memory", "files"]
                },
                "description": "Context sources to assemble"
              }
            },
            "required": ["project", "scope", "phase", "goal"]
          }
        },
        {
          "name": "lathe_validate",
          "description": "Validate AI output against rules",
          "parameters": {
            "type": "object",
            "properties": {
              "phase": {
                "type": "string",
                "enum": ["analysis", "design", "implementation", "validation", "hardening"]
              },
              "output": {
                "type": "string",
                "description": "AI output to validate"
              },
              "ruleset": {
                "type": "array",
                "items": {
                  "type": "string",
                  "enum": [
                    "full_file_replacement",
                    "explicit_assumptions",
                    "required_section",
                    "no_hallucinated_files",
                    "output_format"
                  ]
                },
                "description": "Rules to apply (defaults if not specified)"
              }
            },
            "required": ["phase", "output"]
          }
        },
        {
          "name": "lathe_context_preview",
          "description": "Preview context assembly",
          "parameters": {
            "type": "object",
            "properties": {
              "query": {
                "type": "string"
              },
              "sources": {
                "type": "array",
                "items": {
                  "type": "string",
                  "enum": ["knowledge", "memory", "files"]
                }
              },
              "max_tokens": {
                "type": "integer",
                "default": 2000
              }
            },
            "required": ["query"]
          }
        }
      ]
    }
  ]
}
```

### 2. Configure Python Environment

```bash
# Install lathe package
pip install -e /path/to/lathe

# Verify installation
python -c "from lathe.tool import lathe_plan; print('OK')"
```

### 3. Use in OpenWebUI Workflows

#### Example: Design Workflow

```
User: "Design a REST API for user management"

OpenWebUI Workflow:
1. Call lathe_plan(project="api", scope="users", phase="design", goal="...")
   → Returns system prompt + context + rules
2. Send to LLM with system prompt + context
   → LLM generates design
3. Call lathe_validate(phase="design", output=<llm response>)
   → Returns validation result
4. If valid: Save design
   If invalid: Show violations to user
```

#### Example: Multi-Phase Workflow

```
1. Analysis Phase
   - lathe_plan(phase="analysis")
   - LLM analyzes requirements
   - lathe_validate(phase="analysis")

2. Design Phase
   - lathe_plan(phase="design")
   - LLM designs solution
   - lathe_validate(phase="design")

3. Implementation Phase
   - lathe_plan(phase="implementation")
   - LLM writes code
   - lathe_validate(phase="implementation")

4. Validation Phase
   - lathe_plan(phase="validation")
   - LLM writes tests
   - lathe_validate(phase="validation")

5. Hardening Phase
   - lathe_plan(phase="hardening")
   - LLM optimizes/secures
   - lathe_validate(phase="hardening")
```

## REST API Wrapper

Expose the tool as a REST API:

```python
# api_server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from lathe.tool import lathe_plan, lathe_validate, lathe_context_preview

app = FastAPI(title="Lathe Tool API")

class PlanRequest(BaseModel):
    project: str
    scope: str
    phase: str
    goal: str
    constraints: Optional[List[str]] = None
    sources: Optional[List[str]] = None

class ValidateRequest(BaseModel):
    phase: str
    output: str
    ruleset: Optional[List[str]] = None

class ContextPreviewRequest(BaseModel):
    query: str
    sources: Optional[List[str]] = None
    max_tokens: int = 2000

@app.post("/plan")
async def plan(request: PlanRequest):
    """Plan a phase."""
    result = lathe_plan(
        project=request.project,
        scope=request.scope,
        phase=request.phase,
        goal=request.goal,
        constraints=request.constraints,
        sources=request.sources,
    )
    if result.get("status") == "fail":
        raise HTTPException(status_code=400, detail=result)
    return result

@app.post("/validate")
async def validate(request: ValidateRequest):
    """Validate output."""
    result = lathe_validate(
        phase=request.phase,
        output=request.output,
        ruleset=request.ruleset,
    )
    return result

@app.post("/context-preview")
async def context_preview(request: ContextPreviewRequest):
    """Preview context."""
    result = lathe_context_preview(
        query=request.query,
        sources=request.sources,
        max_tokens=request.max_tokens,
    )
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Usage:

```bash
# Start API
python api_server.py

# Call from client
curl -X POST http://localhost:8000/plan \
  -H "Content-Type: application/json" \
  -d '{
    "project": "myapp",
    "scope": "auth",
    "phase": "design",
    "goal": "Design auth flow"
  }'
```

## CLI Wrapper

Create a command-line interface:

```python
# cli.py
import click
import json
from lathe.tool import lathe_plan, lathe_validate, lathe_context_preview

@click.group()
def cli():
    """Lathe CLI tool."""
    pass

@cli.command()
@click.option('--project', required=True)
@click.option('--scope', required=True)
@click.option('--phase', required=True)
@click.option('--goal', required=True)
@click.option('--constraints', multiple=True)
@click.option('--sources', multiple=True)
def plan(project, scope, phase, goal, constraints, sources):
    """Prepare a phase."""
    result = lathe_plan(
        project=project,
        scope=scope,
        phase=phase,
        goal=goal,
        constraints=list(constraints) if constraints else None,
        sources=list(sources) if sources else None,
    )
    print(json.dumps(result, indent=2, default=str))

@cli.command()
@click.option('--phase', required=True)
@click.option('--output', required=True)
@click.option('--ruleset', multiple=True)
def validate(phase, output, ruleset):
    """Validate output."""
    result = lathe_validate(
        phase=phase,
        output=output,
        ruleset=list(ruleset) if ruleset else None,
    )
    print(json.dumps(result, indent=2, default=str))

@cli.command()
@click.option('--query', required=True)
@click.option('--sources', multiple=True)
@click.option('--max-tokens', type=int, default=2000)
def preview(query, sources, max_tokens):
    """Preview context."""
    result = lathe_context_preview(
        query=query,
        sources=list(sources) if sources else None,
        max_tokens=max_tokens,
    )
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    cli()
```

Usage:

```bash
# Prepare a phase
python cli.py plan \
  --project myapp \
  --scope auth \
  --phase design \
  --goal "Design auth flow" \
  --sources knowledge \
  --sources memory

# Validate output
python cli.py validate \
  --phase design \
  --output "$(cat output.txt)" \
  --ruleset output_format

# Preview context
python cli.py preview \
  --query "authentication" \
  --sources knowledge \
  --max-tokens 2000
```

## IDE Plugin

Embed in IDE using Language Server Protocol (LSP):

```python
# lsp_server.py
from pygls.server import LanguageLanguageServer
from lsprotocol.types import TEXT_DOCUMENT_DID_OPEN
from lathe.tool import lathe_plan

server = LanguageLanguageServer("Lathe", "v0.1.0")

@server.feature(TEXT_DOCUMENT_DID_OPEN)
def on_file_open(ls, params):
    """When file opens, check current phase."""
    # Extract project/phase from file path or config
    result = lathe_plan(
        project="ide",
        scope="current_file",
        phase="implementation",
        goal="Code assistance"
    )
    # Show results in IDE UI
    pass
```

## GitHub Actions Integration

Validate code in CI/CD:

```yaml
# .github/workflows/validate.yml
name: Lathe Validation

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'

      - name: Install Lathe
        run: pip install -e .

      - name: Run Lathe validation
        run: |
          python -c "
          from lathe.tool import lathe_validate

          # Read generated code
          with open('output.py') as f:
            code = f.read()

          # Validate
          result = lathe_validate(
            phase='implementation',
            output=code,
            ruleset=['full_file_replacement', 'output_format']
          )

          # Exit with error if failed
          if result['status'] == 'fail':
            print('Validation failed:')
            for v in result['violations']:
              print(f'  {v}')
            exit(1)
          "
```

## Jupyter Notebook Integration

Use in notebooks:

```python
# notebook.ipynb
from lathe.tool import lathe_plan, lathe_validate
import json
from IPython.display import JSON, Markdown

# Prepare phase
result = lathe_plan(
    project="analysis",
    scope="data",
    phase="analysis",
    goal="Analyze user dataset"
)

# Display system prompt
display(Markdown(f"## System Prompt\n\n{result['system_prompt']}"))

# Display rules
display(Markdown(f"## Rules\n\n" + "\n".join(f"- {r}" for r in result['rules'])))

# Get AI output (simulated)
ai_analysis = "..."

# Validate
validation = lathe_validate(
    phase="analysis",
    output=ai_analysis
)

display(JSON(validation))
```

## Error Handling Patterns

### Pattern 1: Graceful Degradation

```python
try:
    result = lathe_plan(...)
    if result.get("status") == "fail":
        # Use defaults
        system_prompt = "You are a helpful assistant."
        context_blocks = []
    else:
        system_prompt = result['system_prompt']
        context_blocks = result['context_blocks']
except Exception as e:
    # Fallback
    system_prompt = "You are a helpful assistant."
    context_blocks = []
```

### Pattern 2: Logging

```python
import logging
logger = logging.getLogger("lathe")

result = lathe_plan(...)
if result.get("status") == "fail":
    logger.error(f"lathe_plan failed: {result['message']}")
    logger.debug(f"Details: {result['details']}")
else:
    logger.info(f"Phase prepared: {result['phase']}")
```

### Pattern 3: Metrics

```python
import time

start = time.time()
result = lathe_plan(...)
elapsed = time.time() - start

metrics.record("lathe.plan.latency", elapsed)
metrics.record("lathe.plan.status", result.get("status"))
```

## Performance Optimization

### Caching System Prompts

```python
# Cache to avoid re-generating
prompt_cache = {}

def get_system_prompt(project, phase):
    key = f"{project}:{phase}"
    if key not in prompt_cache:
        result = lathe_plan(project=project, phase=phase, goal="")
        prompt_cache[key] = result['system_prompt']
    return prompt_cache[key]
```

### Parallel Validation

```python
import concurrent.futures

outputs = [output1, output2, output3]

with concurrent.futures.ThreadPoolExecutor() as executor:
    validations = list(executor.map(
        lambda o: lathe_validate(phase="design", output=o),
        outputs
    ))
```

## Troubleshooting

### Issue: "No module named 'lathe.tool'"

**Solution:** Ensure package is installed
```bash
pip install -e /path/to/lathe
python -c "from lathe.tool import lathe_plan"
```

### Issue: Rule instantiation errors

**Solution:** Check rule requirements in wrapper
```python
# Verify rules exist
from lathe.validation.rules import FullFileReplacementRule
r = FullFileReplacementRule()  # Should work
```

### Issue: Validation always fails

**Solution:** Verify phase matches ruleset
```python
# Use appropriate ruleset for phase
result = lathe_validate(
    phase="design",
    output=output,
    ruleset=["required_section", "output_format"]  # Design rules
)
```

## Support

- See `README.md` for function reference
- See `EXAMPLES.md` for usage patterns
- See subsystem READMEs for detailed behavior
