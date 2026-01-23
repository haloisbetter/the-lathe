# Integration Example: Three Subsystems Working Together

This document demonstrates how the three independent subsystems work together in a complete workflow.

## The Workflow

```
User Request
    ↓
[1] lathe-prompts  → Get system prompt
    ↓
[2] lathe-context  → Assemble context
    ↓
[3] AI Invocation (External)
    ↓
[4] lathe-validation → Validate output
    ↓
Result/Action
```

## Step 1: lathe-prompts - Get System Prompt

```python
from lathe.prompts import PromptRegistry, Prompt
from lathe.shared.enums import PromptScope

# Initialize registry
registry = PromptRegistry()

# Create some prompts
code_review_prompt = Prompt(
    id="code_review_v1",
    name="Code Review Assistant",
    content="""Review the following code for:
1. Performance issues
2. Security vulnerabilities
3. Code style violations

Code to review:
{code}""",
    version="1.0",
    variables={"code": ""}
)

documentation_prompt = Prompt(
    id="doc_generator_v1",
    name="Documentation Generator",
    content="""Generate comprehensive documentation for:

{code}

Include:
- Function signatures
- Parameter descriptions
- Return value descriptions
- Usage examples""",
    version="1.0",
    variables={"code": ""}
)

# Register prompts
registry.register(code_review_prompt, scope=PromptScope.TASK)
registry.register(documentation_prompt, scope=PromptScope.TASK)

# Retrieve when needed
selected_prompt = registry.get_prompt("code_review_v1")
print(f"Selected: {selected_prompt.name}")
```

## Step 2: lathe-context - Assemble Context

```python
from lathe.context import ContextBuilder, SourceFilter
from lathe.shared.models import ContextSource
from lathe.shared.enums import ContextSourceType

# Create builder
builder = ContextBuilder(max_content_length=10000)

# Create context sources
sources = [
    ContextSource(
        type=ContextSourceType.FILE,
        identifier="main.py",
        content="""def process_data(items):
    result = []
    for item in items:
        result.append(item * 2)
    return result""",
        priority=95,
        metadata={"file_path": "main.py", "lines": 5}
    ),
    ContextSource(
        type=ContextSourceType.KNOWLEDGE,
        identifier="python_best_practices",
        content="""Python best practices:
- Use list comprehensions instead of loops
- Type hints for clarity
- Follow PEP 8 style guide""",
        priority=70,
        metadata={"category": "python"}
    ),
    ContextSource(
        type=ContextSourceType.MEMORY,
        identifier="previous_feedback",
        content="User prefers functional style over imperative",
        priority=60,
        metadata={"from_interaction": 3}
    ),
]

# Apply filters
filters = [
    SourceFilter(min_priority=50),  # Only important sources
    SourceFilter(content_min_length=10),  # Only substantial content
]

# Build context
context_output = builder.build(
    sources,
    filters=filters,
    sort_by="priority",
    separator="\n---\n"
)

print(f"Assembled context from {len(context_output.sources_used)} sources")
print(f"Estimated tokens: {context_output.total_tokens_estimated}")
print(f"Content preview: {context_output.assembled_content[:200]}...")
```

## Step 3: Combine for AI

```python
# Fill in the prompt with context
filled_prompt = selected_prompt.substitute_variables(
    {"code": context_output.assembled_content}
)

# This is what goes to the AI model
print("=== FULL PROMPT FOR AI ===")
print(filled_prompt)
# Output:
# Review the following code for:
# 1. Performance issues
# 2. Security vulnerabilities
# 3. Code style violations
#
# Code to review:
# def process_data(items):
#     result = []
#     for item in items:
#         result.append(item * 2)
#     return result
# ---
# Python best practices:
# - Use list comprehensions instead of loops
# - ...
```

## Step 4: lathe-validation - Validate AI Output

```python
from lathe.validation import ValidationEngine
from lathe.validation.rules import (
    FullFileReplacementRule,
    ExplicitAssumptionsRule,
    RequiredSectionRule,
)
from lathe.shared.enums import ValidationLevel

# Simulate AI response
ai_response = """
# Code Review

ASSUME: Code is intended to run on Python 3.8+

## Performance Issues

1. The loop can be replaced with a list comprehension:
```python
def process_data(items):
    return [item * 2 for item in items]
```

This is more Pythonic and slightly faster.

## Security
No security issues detected.

## Style
- Add type hints for clarity
- Function could use docstring

## Examples
process_data([1, 2, 3]) → [2, 4, 6]
"""

# Create validation engine
engine = ValidationEngine(fail_fast=False)

# Define validation rules
rules = [
    FullFileReplacementRule(
        severity=ValidationLevel.FAIL,
        min_lines=3
    ),
    ExplicitAssumptionsRule(
        severity=ValidationLevel.WARN
    ),
    RequiredSectionRule(
        required_sections=["# Code Review", "## Performance"],
        severity=ValidationLevel.WARN
    ),
]

# Validate output
validation_result = engine.validate(ai_response, rules)

# Check results
print("=== VALIDATION RESULTS ===")
print(engine.get_validation_summary(validation_result))
# Output:
# Validation: PASS
# Passed: 3
# Failed: 0
# Warnings: 0
#
# Overall: All validations passed!

if validation_result.overall_level == ValidationLevel.PASS:
    print("✓ Output is valid, safe to use")
elif validation_result.overall_level == ValidationLevel.WARN:
    print("⚠ Output has warnings, review before use")
    for warning in validation_result.warnings:
        print(f"  {warning}")
else:
    print("✗ Output failed validation, do not use")
    for error in validation_result.errors:
        print(f"  {error}")
```

## Step 5: Pipeline Pattern

```python
from lathe.validation.engine import ValidationStage, ValidationPipeline

# Create validation stages
stage1_structure = ValidationStage(
    "structure",
    rules=[
        FullFileReplacementRule(severity=ValidationLevel.FAIL),
    ]
)

stage2_content = ValidationStage(
    "content",
    rules=[
        ExplicitAssumptionsRule(severity=ValidationLevel.WARN),
        RequiredSectionRule(["# Code Review"], severity=ValidationLevel.WARN),
    ]
)

# Create pipeline
pipeline = ValidationPipeline(fail_on_stage_failure=False)
pipeline.add_stage(stage1_structure).add_stage(stage2_content)

# Execute pipeline
stage_results = pipeline.execute(ai_response)

# Get overall result
overall = pipeline.get_overall_result(stage_results)
print(f"Overall validation: {overall.upper()}")

# Inspect individual stages
for stage_name, result in stage_results.items():
    print(f"\n{stage_name}:")
    print(f"  Level: {result.overall_level.upper()}")
    print(f"  Passed: {len(result.passed_rules)}")
    print(f"  Failed: {len(result.failed_rules)}")
```

## Complete End-to-End Example

```python
def complete_workflow():
    """Demonstrate all three subsystems working together."""

    # Step 1: Get prompt
    from lathe.prompts import PromptRegistry
    registry = PromptRegistry()
    prompt = Prompt(
        id="review", name="Review", content="Review: {code}", version="1.0"
    )
    registry.register(prompt)

    # Step 2: Assemble context
    from lathe.context import ContextBuilder
    builder = ContextBuilder()
    source = ContextSource(
        type=ContextSourceType.FILE,
        identifier="app.py",
        content="def hello(): pass",
        priority=100
    )
    context = builder.build([source])

    # Step 3: Validate (simulated AI output)
    from lathe.validation import ValidationEngine
    engine = ValidationEngine()
    rule = FullFileReplacementRule()
    result = engine.validate("def hello():\n    return 'world'", [rule])

    print(f"Prompt: {registry.get_prompt('review').name}")
    print(f"Context: {len(context.sources_used)} sources")
    print(f"Validation: {result.overall_level.upper()}")

    return {
        "prompt": registry.get_prompt("review"),
        "context": context,
        "validation": result,
    }

# Run workflow
output = complete_workflow()
```

## Key Properties Demonstrated

### 1. Independence
- Each subsystem can be tested separately
- No subsystem knows about the others
- Easy to replace implementations

### 2. Explicit Contracts
- Subsystems communicate via shared models
- Clear input/output specifications
- Type-safe interfaces

### 3. Statelessness
- No internal caching or databases
- Deterministic behavior
- Same inputs → same outputs

### 4. Composability
- Validation pipeline chains rules
- Context builder chains filters
- Future orchestrator chains subsystems

### 5. Extensibility
- Add new prompt scopes without changing registry
- Add new validation rules without changing engine
- Add new source types without changing builder

## Future: lathe-core Orchestration

Once all subsystems are stable, `lathe-core` will orchestrate them:

```python
from lathe.core import LatheWorkflow

workflow = LatheWorkflow()
result = workflow.execute(
    task_description="Review this code",
    code_snippet="def foo(): pass",
    prompt_id="code_review_v1",
    context_sources=sources,
    validation_rules=rules,
)

print(result.status)  # PASS, WARN, FAIL
print(result.output)  # AI response
print(result.validation)  # ValidationResult
```

But until then, each subsystem remains **independent, testable, and ready to use**.
