"""
Validation engine for lathe-validation subsystem.

Core evaluation engine for running validation rules against content.
"""

from typing import List, Dict, Any, Optional
from lathe.validation.rules import ValidationRule
from lathe.shared.models import ValidationResult
from lathe.shared.enums import ValidationLevel


class ValidationEngine:
    """
    Executes validation rules and produces structured results.

    Responsibilities:
    - Run multiple rules against content
    - Aggregate results
    - Determine overall validation level
    - Track pass/fail/warn per rule

    State:
    - Stateless (no internal state between validations)
    """

    def __init__(self, fail_fast: bool = False):
        """
        Initialize validation engine.

        Args:
            fail_fast: Stop validation on first failure if True
        """
        self.fail_fast = fail_fast

    def validate(
        self,
        content: str,
        rules: List[ValidationRule],
    ) -> ValidationResult:
        """
        Validate content against a set of rules.

        Args:
            content: Content to validate
            rules: List of rules to apply

        Returns:
            ValidationResult with detailed results
        """
        rule_results = {}
        passed_rules = []
        failed_rules = []
        warnings = []
        errors = []

        for rule in rules:
            try:
                passed = rule.evaluate(content)

                result = {
                    "passed": passed,
                    "severity": rule.severity.value,
                    "description": rule.description,
                }

                rule_results[rule.rule_id] = result

                if passed:
                    passed_rules.append(rule.rule_id)
                else:
                    if rule.severity == ValidationLevel.FAIL:
                        failed_rules.append(rule.rule_id)
                        errors.append(
                            f"[{rule.name}] {rule.description}"
                        )
                    elif rule.severity == ValidationLevel.WARN:
                        warnings.append(
                            f"[{rule.name}] {rule.description}"
                        )

                # Fail fast if requested
                if self.fail_fast and not passed:
                    break

            except Exception as e:
                # Rule execution error
                errors.append(f"Error in {rule.name}: {str(e)}")
                failed_rules.append(rule.rule_id)

        # Determine overall level
        if failed_rules:
            overall_level = ValidationLevel.FAIL
        elif warnings:
            overall_level = ValidationLevel.WARN
        else:
            overall_level = ValidationLevel.PASS

        return ValidationResult(
            overall_level=overall_level,
            rule_results=rule_results,
            errors=errors,
            warnings=warnings,
            passed_rules=passed_rules,
            failed_rules=failed_rules,
        )

    def validate_with_config(
        self,
        content: str,
        config: Dict[str, Any],
    ) -> ValidationResult:
        """
        Validate content using a configuration dictionary.

        Args:
            content: Content to validate
            config: Configuration with rules specification

        Returns:
            ValidationResult

        Example config:
        {
            "rules": [
                {
                    "type": "full_file_replacement",
                    "severity": "fail",
                    "params": {"min_lines": 5}
                },
                {
                    "type": "explicit_assumptions",
                    "severity": "warn"
                },
            ],
            "fail_fast": False
        }
        """
        # This is a placeholder for rule factory pattern
        # Real implementation would instantiate rules from config
        rules = []
        # TODO: Implement rule factory

        return self.validate(content, rules)

    def get_validation_summary(self, result: ValidationResult) -> str:
        """
        Get human-readable validation summary.

        Args:
            result: Validation result

        Returns:
            Summary string
        """
        summary = f"Validation: {result.overall_level.upper()}\n"
        summary += f"Passed: {len(result.passed_rules)}\n"
        summary += f"Failed: {len(result.failed_rules)}\n"
        summary += f"Warnings: {len(result.warnings)}\n"

        if result.errors:
            summary += "\nErrors:\n"
            for error in result.errors:
                summary += f"  - {error}\n"

        if result.warnings:
            summary += "\nWarnings:\n"
            for warning in result.warnings:
                summary += f"  - {warning}\n"

        return summary


class ValidationStage:
    """
    Represents a validation stage in a pipeline.

    Allows composing multiple validation steps.
    """

    def __init__(
        self,
        stage_name: str,
        rules: List[ValidationRule],
        engine: Optional[ValidationEngine] = None,
    ):
        """
        Initialize validation stage.

        Args:
            stage_name: Name of this stage
            rules: Rules to apply in this stage
            engine: Optional engine (creates new if None)
        """
        self.stage_name = stage_name
        self.rules = rules
        self.engine = engine or ValidationEngine()

    def execute(self, content: str) -> ValidationResult:
        """
        Execute this stage on content.

        Args:
            content: Content to validate

        Returns:
            ValidationResult
        """
        return self.engine.validate(content, self.rules)


class ValidationPipeline:
    """
    Chains multiple validation stages together.

    Executes stages in sequence, optionally stopping on failure.
    """

    def __init__(self, fail_on_stage_failure: bool = True):
        """
        Initialize validation pipeline.

        Args:
            fail_on_stage_failure: Stop pipeline if any stage fails
        """
        self.stages: List[ValidationStage] = []
        self.fail_on_stage_failure = fail_on_stage_failure

    def add_stage(self, stage: ValidationStage) -> "ValidationPipeline":
        """
        Add a validation stage.

        Args:
            stage: Stage to add

        Returns:
            Self for chaining
        """
        self.stages.append(stage)
        return self

    def execute(self, content: str) -> Dict[str, ValidationResult]:
        """
        Execute all stages on content.

        Args:
            content: Content to validate

        Returns:
            Dictionary mapping stage names to results
        """
        results = {}

        for stage in self.stages:
            result = stage.execute(content)
            results[stage.stage_name] = result

            if (
                self.fail_on_stage_failure
                and result.overall_level == ValidationLevel.FAIL
            ):
                break

        return results

    def get_overall_result(
        self,
        stage_results: Dict[str, ValidationResult],
    ) -> ValidationLevel:
        """
        Determine overall validation level across all stages.

        Args:
            stage_results: Results from execute()

        Returns:
            Overall ValidationLevel
        """
        if any(
            r.overall_level == ValidationLevel.FAIL
            for r in stage_results.values()
        ):
            return ValidationLevel.FAIL

        if any(
            r.overall_level == ValidationLevel.WARN
            for r in stage_results.values()
        ):
            return ValidationLevel.WARN

        return ValidationLevel.PASS
