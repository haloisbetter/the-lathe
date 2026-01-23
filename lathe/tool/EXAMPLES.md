# Lathe Tool Wrapper - Usage Examples

This document provides practical examples of how to use the Lathe OpenWebUI tool wrapper.

## Basic Setup

```python
from lathe.tool import lathe_plan, lathe_validate, lathe_context_preview
```

## Example 1: Full AI-Assisted Design Workflow

Complete workflow from planning through validation:

```python
# Step 1: Get ready for design phase
plan_result = lathe_plan(
    project="user-auth-service",
    scope="authentication module",
    phase="design",
    goal="Design OAuth2-based authentication flow",
    constraints=[
        "OAuth2 required",
        "HIPAA compliant",
        "Support multi-tenant",
        "Rate limiting needed"
    ],
    sources=["knowledge", "memory"]
)

if plan_result.get("ready"):
    print(f"Phase: {plan_result['phase']}")
    print(f"System Prompt:\n{plan_result['system_prompt']}\n")
    print(f"Rules to follow: {plan_result['rules']}")
    print(f"Risks to watch: {plan_result['risks']}")

    # Pass system_prompt and context_blocks to LLM
    ai_output = call_llm(
        system_prompt=plan_result['system_prompt'],
        context=plan_result['context_blocks']
    )

    # Step 2: Validate AI output
    validation_result = lathe_validate(
        phase="design",
        output=ai_output,
        ruleset=["required_section", "output_format"]
    )

    if validation_result.get("can_proceed"):
        print(f"✓ Design validation passed")
    else:
        print(f"✗ Validation failed:")
        for violation in validation_result['violations']:
            print(f"  - {violation['rule']}: {violation['message']}")
else:
    print(f"Error: {plan_result['error_type']}: {plan_result['message']}")
```

## Example 2: Analysis Phase

Discover requirements and identify unknowns:

```python
# Request analysis phase preparation
analysis_plan = lathe_plan(
    project="payment-processing",
    scope="payment gateway integration",
    phase="analysis",
    goal="Analyze payment flow requirements",
    constraints=["PCI-DSS compliant", "Support Stripe + Square"],
    sources=["knowledge"]
)

print("Analysis Phase Ready:")
print(f"System Prompt: {analysis_plan['system_prompt']}")
print(f"Rules: {analysis_plan['rules']}")
# Output should contain assumptions and risks
```

## Example 3: Implementation Phase with Full File Validation

Generate and validate complete code:

```python
# Prepare implementation phase
impl_plan = lathe_plan(
    project="api-service",
    scope="rate limiter middleware",
    phase="implementation",
    goal="Implement token bucket rate limiter",
    constraints=["Python 3.10+", "No external dependencies"],
    sources=["knowledge", "files"]
)

# Get AI to generate code
ai_code = """
def rate_limiter(max_requests: int, window_seconds: int):
    '''Token bucket rate limiter implementation.'''
    import time

    bucket = max_requests
    last_refill = time.time()

    def check_limit():
        nonlocal bucket, last_refill
        now = time.time()

        # Refill tokens
        elapsed = now - last_refill
        refill = (elapsed / window_seconds) * max_requests
        bucket = min(max_requests, bucket + refill)
        last_refill = now

        if bucket >= 1:
            bucket -= 1
            return True
        return False

    return check_limit

# Tests...
"""

# Validate with strict rules for implementation
validation = lathe_validate(
    phase="implementation",
    output=ai_code,
    ruleset=["full_file_replacement", "output_format"]
)

if validation['status'] == 'pass':
    print("✓ Implementation ready for deployment")
else:
    print(f"✗ Issues found: {validation['summary']}")
    for v in validation['violations']:
        print(f"  {v['rule']}: {v['message']}")
```

## Example 4: Validation Phase

Test comprehensively before hardening:

```python
# Validation phase focuses on testing
validation_plan = lathe_plan(
    project="api-service",
    scope="rate limiter middleware",
    phase="validation",
    goal="Write comprehensive test suite",
    constraints=["100% coverage", "Edge cases required"],
    sources=["knowledge"]
)

# Get test code from AI
test_code = """
import pytest
from limiter import rate_limiter

def test_rate_limiter_allows_requests():
    check = rate_limiter(max_requests=10, window_seconds=60)
    for _ in range(10):
        assert check() is True
    assert check() is False

def test_refill_tokens():
    check = rate_limiter(max_requests=5, window_seconds=1)
    # Use up tokens
    for _ in range(5):
        check()
    # Wait for refill
    time.sleep(1.1)
    assert check() is True

# More tests...
"""

# Validate test output
validation = lathe_validate(
    phase="validation",
    output=test_code
)

if not validation['violations']:
    print("✓ Test suite validated")
```

## Example 5: Context Preview for Token Budgeting

Check what context will be available:

```python
# Preview context before full planning
preview = lathe_context_preview(
    query="authentication implementation",
    sources=["knowledge", "files"],
    max_tokens=2000
)

print(f"Total tokens available: {preview['total_tokens']}")
print(f"Truncated: {preview['truncated']}")

for block in preview['context_blocks']:
    print(f"\n{block['source'].upper()} ({block['size_tokens']} tokens):")
    print(block['preview'][:100] + "...")
```

## Example 6: Error Handling

Gracefully handle errors:

```python
from lathe.tool import lathe_plan

result = lathe_plan(
    project="test",
    scope="test",
    phase="unknown_phase",  # Invalid!
    goal="test"
)

if result.get("status") == "fail":
    error_type = result.get("error_type")
    message = result.get("message")

    if error_type == "PHASE_VIOLATION":
        print(f"Invalid phase: {message}")
    elif error_type == "VALIDATION_ERROR":
        print(f"Validation failed: {message}")
    elif error_type == "INTERNAL_ERROR":
        print(f"Internal error: {message}")
else:
    # Success
    proceed_with_phase(result)
```

## Example 7: Custom Ruleset

Apply specific rules for your needs:

```python
# Strict validation for critical code
strict_validation = lathe_validate(
    phase="implementation",
    output=ai_code,
    ruleset=[
        "full_file_replacement",      # Complete implementations
        "output_format",               # Proper formatting
        "no_hallucinated_files",       # No fake file references
    ]
)

# Lenient validation for documentation
doc_validation = lathe_validate(
    phase="analysis",
    output=ai_output,
    ruleset=["explicit_assumptions"]  # Just require assumptions stated
)
```

## Example 8: Multi-Phase Workflow

End-to-end project workflow:

```python
phases_workflow = [
    ("analysis", "Understand requirements"),
    ("design", "Design architecture"),
    ("implementation", "Write code"),
    ("validation", "Test thoroughly"),
    ("hardening", "Secure and optimize"),
]

for phase, goal in phases_workflow:
    print(f"\n{'='*60}")
    print(f"PHASE: {phase.upper()}")
    print(f"{'='*60}")

    # Step 1: Get phase plan
    plan = lathe_plan(
        project="myproject",
        scope="core-module",
        phase=phase,
        goal=goal,
        sources=["knowledge", "memory"]
    )

    if plan.get("status") == "fail":
        print(f"Error: {plan['message']}")
        break

    print(f"Rules: {plan['rules']}")
    print(f"Risks: {plan['risks']}")

    # Step 2: Run with LLM (pseudo-code)
    ai_output = llm_service.generate(
        system_prompt=plan['system_prompt'],
        context=plan['context_blocks'],
        user_request=goal
    )

    # Step 3: Validate output
    validation = lathe_validate(
        phase=phase,
        output=ai_output
    )

    if validation['can_proceed']:
        print(f"✓ Phase {phase} validated, proceeding...")
        save_output(phase, ai_output)
    else:
        print(f"✗ Phase {phase} failed validation:")
        for v in validation['violations']:
            print(f"  {v['message']}")
        break
```

## Example 9: Integration with OpenWebUI

How OpenWebUI would call the tool:

```yaml
# In OpenWebUI tool configuration
tools:
  lathe:
    type: python
    module: lathe.tool
    functions:
      - name: lathe_plan
        description: Prepare AI step for specific phase
        parameters:
          project:
            type: string
            description: Project identifier
          phase:
            type: string
            enum: [analysis, design, implementation, validation, hardening]
          goal:
            type: string
          sources:
            type: array
            items:
              type: string
              enum: [knowledge, memory, files]

      - name: lathe_validate
        description: Validate AI output against rules
        parameters:
          phase:
            type: string
            enum: [analysis, design, implementation, validation, hardening]
          output:
            type: string
          ruleset:
            type: array
            items:
              type: string

      - name: lathe_context_preview
        description: Preview context that would be assembled
        parameters:
          query:
            type: string
          sources:
            type: array
            items:
              type: string
          max_tokens:
            type: integer
```

## Example 10: JSON-based API Usage

Use the tool from external systems:

```python
import json
from lathe.tool import lathe_plan, lathe_validate

# Input as JSON
plan_request = {
    "project": "api",
    "scope": "users",
    "phase": "design",
    "goal": "Design user management API",
    "constraints": ["RESTful", "JWT auth"],
    "sources": ["knowledge"]
}

# Call tool
result = lathe_plan(**plan_request)

# Output as JSON
print(json.dumps(result, indent=2, default=str))

# Validate output
validation_request = {
    "phase": "design",
    "output": "...",
    "ruleset": ["output_format"]
}

validation = lathe_validate(**validation_request)
print(json.dumps(validation, indent=2))
```

## Key Patterns

### Pattern 1: Safe Phase Transitions
Always check `ready` flag before proceeding to next phase.

### Pattern 2: Error Checking
Always check for `status == "fail"` before using result.

### Pattern 3: Token Budget Awareness
Use `lathe_context_preview` to understand available context budget.

### Pattern 4: Progressive Validation
Start with lenient rules (WARN) and increase to strict (FAIL) as you progress.

### Pattern 5: Stateless Calls
Each function call is independent - no session or state management needed.

## Common Mistakes

❌ Don't: Call functions without checking for error responses
```python
# WRONG
system_prompt = lathe_plan(...)['system_prompt']  # May crash if error
```

✓ Do: Always check status first
```python
# RIGHT
result = lathe_plan(...)
if result.get('status') != 'fail':
    system_prompt = result['system_prompt']
```

❌ Don't: Assume phase must advance linearly
```python
# Can repeat phases or go back
lathe_plan(phase="design")
lathe_plan(phase="design")  # OK to repeat
lathe_plan(phase="analysis")  # OK to go back
```

✓ Do: Track phase state at application level
```python
current_phase = "analysis"
# Application decides when to advance
current_phase = "design"
```

## Performance Tips

1. **Reuse PromptRegistry**: Multiple lathe_plan calls create new registries (stateless by design)
2. **Preview first**: Use lathe_context_preview to understand token usage
3. **Batch validation**: Validate multiple outputs in sequence, not parallel
4. **Error recovery**: Use WARN severity for recoverable issues, FAIL for blockers
