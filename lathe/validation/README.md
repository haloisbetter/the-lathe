# lathe-validation

**Validate AI outputs against Lathe rules.**

## Responsibilities

This subsystem provides:
- **Rule definitions**: Full-file replacement, assumptions, sections, formats
- **Validation engine**: Execute rules and aggregate results
- **Severity levels**: Pass, Warn, Fail with clear semantics
- **Pipeline support**: Chain multiple validation stages
- **Structured results**: Detailed pass/fail per rule with diagnostics

## Non-Responsibilities

This subsystem does NOT:
- Execute code or parse ASTs
- Persist validation results
- Generate fixes or suggestions
- Handle UI or reporting
- Make orchestration decisions

## Public Interface

### `ValidationEngine`

Core engine for validating content against rules.

**Methods:**
- `validate(content, rules) -> ValidationResult`: Run all rules, return results
- `validate_with_config(content, config) -> ValidationResult`: Validate using config dict
- `get_validation_summary(result) -> str`: Human-readable summary

**Constructor:**
```python
ValidationEngine(fail_fast=False)  # Stop on first failure if True
```

### `ValidationRule` (Abstract Base)

Base class for all validation rules.

**Subclasses:**
- `FullFileReplacementRule`: Ensure complete files, not snippets
- `ExplicitAssumptionsRule`: Require assumption statements
- `RequiredSectionRule`: Enforce section headers
- `NoHallucinatedFilesRule`: Detect unrealistic file references
- `OutputFormatRule`: Check format compliance

**Methods:**
- `evaluate(content) -> bool`: Return True if passes

### `ValidationStage`

Represents a single validation stage.

**Constructor:**
```python
ValidationStage(stage_name, rules, engine=None)
```

**Methods:**
- `execute(content) -> ValidationResult`

### `ValidationPipeline`

Chain multiple validation stages.

**Methods:**
- `add_stage(stage) -> ValidationPipeline`: Add stage (chainable)
- `execute(content) -> Dict[str, ValidationResult]`: Run all stages
- `get_overall_result(stage_results) -> ValidationLevel`: Overall pass/warn/fail

## Data Contracts

### Input: Content String + List[ValidationRule]
```python
content = "def process(): return True"
rules = [
    FullFileReplacementRule(severity=ValidationLevel.FAIL, min_lines=1),
    ExplicitAssumptionsRule(severity=ValidationLevel.WARN),
]
```

### Output: ValidationResult
```python
ValidationResult(
    overall_level=ValidationLevel.PASS,
    rule_results={
        "full_file_replacement": {
            "passed": True,
            "severity": "fail",
            "description": "..."
        },
        "explicit_assumptions": {
            "passed": False,
            "severity": "warn",
            "description": "..."
        }
    },
    errors=[],
    warnings=["[Explicit Assumptions] Output should state assumptions clearly"],
    passed_rules=["full_file_replacement"],
    failed_rules=["explicit_assumptions"]
)
```

## Usage Example

```python
from lathe.validation import ValidationEngine
from lathe.validation.rules import (
    FullFileReplacementRule,
    ExplicitAssumptionsRule,
    RequiredSectionRule
)
from lathe.shared.enums import ValidationLevel

# Create engine
engine = ValidationEngine(fail_fast=False)

# Define rules
rules = [
    FullFileReplacementRule(severity=ValidationLevel.FAIL, min_lines=5),
    ExplicitAssumptionsRule(severity=ValidationLevel.WARN),
    RequiredSectionRule(
        required_sections=["# Usage", "# Examples"],
        severity=ValidationLevel.WARN
    ),
]

# Validate content
content = """
def my_function():
    # ASSUME: Python 3.8+
    return True

# Usage
# Examples
"""

result = engine.validate(content, rules)

# Check results
if result.overall_level == ValidationLevel.PASS:
    print("All validations passed!")
elif result.overall_level == ValidationLevel.WARN:
    print("Warnings detected:")
    for w in result.warnings:
        print(f"  - {w}")
else:
    print("Validation failed:")
    for e in result.errors:
        print(f"  - {e}")

# Get summary
print(engine.get_validation_summary(result))
```

## Validation Stages

### Stage 1: Structure Validation
- Full file replacement check
- Required sections check
- Format validation

### Stage 2: Content Validation
- Explicit assumptions check
- No hallucinated files check
- Content quality checks

### Stage 3: Semantic Validation (Future)
- Code correctness checks
- Documentation completeness
- Example validity

## Pipeline Example

```python
from lathe.validation.engine import ValidationStage, ValidationPipeline

# Create stages
stage1 = ValidationStage(
    "structure",
    [FullFileReplacementRule(severity=ValidationLevel.FAIL)]
)

stage2 = ValidationStage(
    "content",
    [
        ExplicitAssumptionsRule(),
        NoHallucinatedFilesRule(),
    ]
)

# Create pipeline
pipeline = ValidationPipeline(fail_on_stage_failure=True)
pipeline.add_stage(stage1).add_stage(stage2)

# Execute
results = pipeline.execute(content)

# Check overall result
overall = pipeline.get_overall_result(results)
```

## Severity Levels

- **PASS**: Rule passed, no issues
- **WARN**: Rule failed but is advisory (continue with caution)
- **FAIL**: Rule failed critically (should block or require review)

## Rule Severity Defaults

| Rule | Default Severity | Rationale |
|------|------------------|-----------|
| FullFileReplacementRule | FAIL | Critical for correctness |
| ExplicitAssumptionsRule | WARN | Important but not blocking |
| RequiredSectionRule | WARN | Structure guidance |
| NoHallucinatedFilesRule | WARN | Helpful but may have false positives |
| OutputFormatRule | WARN | Format guidance |

## Design Decisions

1. **Rule-based architecture**: Composable, extensible rules
2. **Explicit severity levels**: Pass/Warn/Fail with clear semantics
3. **No automatic fixes**: Validation reports problems, doesn't fix them
4. **Stateless engine**: No side effects or internal state
5. **Pipeline support**: Composable validation stages
6. **Exception handling**: Errors are captured, don't crash engine

## Future Extension Points

1. **Custom Rule Factories**: Load rules from config
2. **Rule Scoring**: Weight rules differently in scoring
3. **Auto-fix Suggestions**: Recommend fixes for failed rules
4. **Rule Dependencies**: Some rules only run if others pass
5. **Async Rules**: Support async rule evaluation
6. **Rule Metadata**: Rich metadata about rule constraints
7. **Statistical Validation**: Learn rules from examples

## Example Rule Definitions (Placeholder)

```python
# Code must have docstrings
"All functions must have docstrings"

# Output must reference input
"Output should reference the provided input"

# Assumptions must be listed
"Explicit assumptions section required"

# File paths must be realistic
"File paths should match project structure"

# Examples must be complete
"Examples should be executable/complete"
```
