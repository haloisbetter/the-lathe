"""
OpenWebUI Tool: Lathe AI Control Layer

This is a standalone OpenWebUI-compatible tool file.
It provides three functions for phase-locked AI development:
- lathe_plan: Prepare a phase-locked AI step
- lathe_validate: Validate AI output against rules
- lathe_context_preview: Preview context assembly

All functions are stateless and return JSON-serializable dicts.
"""

from typing import Any, Dict, List, Optional
import json

from lathe.prompts import PromptRegistry, Prompt
from lathe.context import ContextBuilder
from lathe.validation import ValidationEngine
from lathe.shared.enums import PromptScope, ContextSourceType, ValidationLevel
from lathe.shared.models import ContextSource, ContextOutput, ValidationResult
from lathe.validation.rules import (
    FullFileReplacementRule,
    ExplicitAssumptionsRule,
    RequiredSectionRule,
    NoHallucinatedFilesRule,
    OutputFormatRule,
)


def _error_response(
    error_type: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a structured error response.

    Args:
        error_type: Error category (PHASE_VIOLATION, VALIDATION_ERROR, INTERNAL_ERROR)
        message: Human-readable error message
        details: Optional additional error details

    Returns:
        Structured error dict
    """
    return {
        "status": "fail",
        "error_type": error_type,
        "message": message,
        "details": details or {},
    }


def lathe_plan(
    project: str,
    scope: str,
    phase: str,
    goal: str,
    constraints: Optional[List[str]] = None,
    sources: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Prepare a phase-locked AI step before model execution.

    Orchestrates:
    1. PromptRegistry to retrieve system prompt for phase
    2. ContextBuilder to assemble scoped context
    3. Aggregates rules and risks for the phase

    Does NOT generate AI output or advance phase.

    Args:
        project: Project identifier
        scope: Scope of work (e.g., "module", "component")
        phase: Phase name (analysis, design, implementation, validation, hardening)
        goal: Goal for this step
        constraints: Optional list of constraints
        sources: Optional list of source types (knowledge, memory, files)

    Returns:
        {
            "phase": str,
            "system_prompt": str,
            "context_blocks": [{"type": str, "content": str, "metadata": dict}],
            "rules": [str],
            "risks": [str],
            "ready": bool
        }
        OR error response
    """
    try:
        # Validate phase
        valid_phases = ["analysis", "design", "implementation", "validation", "hardening"]
        if phase not in valid_phases:
            return _error_response(
                "PHASE_VIOLATION",
                f"Invalid phase: {phase}. Must be one of: {valid_phases}",
            )

        # Map phase to prompt scope
        phase_to_scope = {
            "analysis": PromptScope.TASK,
            "design": PromptScope.TASK,
            "implementation": PromptScope.PROJECT,
            "validation": PromptScope.PROJECT,
            "hardening": PromptScope.GLOBAL,
        }
        prompt_scope = phase_to_scope.get(phase, PromptScope.TASK)

        # Get system prompt from registry
        registry = PromptRegistry()
        prompt_id = f"{project}_{phase}"

        # Create a system prompt if not registered
        # (In production, these would be pre-loaded from configuration)
        system_prompt_content = f"""You are operating in {phase.upper()} phase.

Project: {project}
Scope: {scope}
Goal: {goal}

Constraints:
{chr(10).join(f"- {c}" for c in (constraints or ["None"]))}

Apply phase-specific discipline and rules.
Do not exceed phase boundaries.
Return structured output."""

        system_prompt = Prompt(
            id=prompt_id,
            name=f"System Prompt: {project} - {phase}",
            content=system_prompt_content,
            version="1.0",
        )

        registry.register(system_prompt, scope=prompt_scope)
        retrieved_prompt = registry.get_prompt(prompt_id)

        if not retrieved_prompt:
            return _error_response(
                "INTERNAL_ERROR",
                f"Could not register or retrieve prompt: {prompt_id}",
            )

        # Build context from sources
        source_type_map = {
            "knowledge": ContextSourceType.KNOWLEDGE,
            "memory": ContextSourceType.MEMORY,
            "files": ContextSourceType.FILE,
        }

        context_sources: List[ContextSource] = []
        for source_name in (sources or ["knowledge"]):
            source_type = source_type_map.get(source_name)
            if source_type:
                # Create minimal context sources
                context_sources.append(
                    ContextSource(
                        type=source_type,
                        identifier=f"{source_name}_{phase}",
                        content=f"Context from {source_name}",
                        priority=75 if source_type == ContextSourceType.KNOWLEDGE else 50,
                        metadata={"phase": phase, "source": source_name},
                    )
                )

        context_builder = ContextBuilder(max_content_length=8000)
        context_output = context_builder.build(context_sources)

        # Define rules for this phase
        phase_rules = {
            "analysis": [
                "Document assumptions explicitly",
                "List all unknowns",
                "Identify risks early",
            ],
            "design": [
                "Provide architecture diagram",
                "List design trade-offs",
                "Define interfaces clearly",
            ],
            "implementation": [
                "Include full implementations",
                "Add error handling",
                "Write clear comments",
            ],
            "validation": [
                "Run all tests",
                "Check edge cases",
                "Verify error paths",
            ],
            "hardening": [
                "Add security checks",
                "Optimize performance",
                "Add monitoring/observability",
            ],
        }

        phase_risks = {
            "analysis": [
                "Incomplete understanding",
                "Missing edge cases",
                "Wrong assumptions",
            ],
            "design": [
                "Over-engineering",
                "Unclear interfaces",
                "Performance issues",
            ],
            "implementation": [
                "Off-by-one errors",
                "Missing error cases",
                "Performance degradation",
            ],
            "validation": [
                "Test gaps",
                "Integration issues",
                "Environment differences",
            ],
            "hardening": [
                "Regression bugs",
                "Performance impact",
                "Compatibility issues",
            ],
        }

        # Format context blocks
        context_blocks = [
            {
                "type": "system_prompt",
                "content": retrieved_prompt.content,
                "metadata": {
                    "prompt_id": prompt_id,
                    "phase": phase,
                    "scope": prompt_scope.value,
                },
            },
            {
                "type": "assembled_context",
                "content": context_output.assembled_content,
                "metadata": {
                    "sources_used": context_output.sources_used,
                    "total_tokens_estimated": context_output.total_tokens_estimated,
                },
            },
        ]

        return {
            "phase": phase,
            "system_prompt": retrieved_prompt.content,
            "context_blocks": context_blocks,
            "rules": phase_rules.get(phase, []),
            "risks": phase_risks.get(phase, []),
            "ready": True,
        }

    except Exception as e:
        return _error_response(
            "INTERNAL_ERROR",
            f"Error in lathe_plan: {str(e)}",
            {"exception": type(e).__name__},
        )


def lathe_validate(
    phase: str,
    output: str,
    ruleset: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Validate an AI response against Lathe rules.

    Orchestrates ValidationEngine to run specified rules against output.
    Does NOT modify output or attempt auto-fix.

    Args:
        phase: Current phase (analysis, design, implementation, validation, hardening)
        output: AI-generated output to validate
        ruleset: List of rule names to apply (if None, uses phase-appropriate rules)

    Returns:
        {
            "status": "pass" | "warn" | "fail",
            "violations": [{"rule": str, "message": str}],
            "summary": str,
            "can_proceed": bool
        }
        OR error response
    """
    try:
        # Validate phase
        valid_phases = ["analysis", "design", "implementation", "validation", "hardening"]
        if phase not in valid_phases:
            return _error_response(
                "PHASE_VIOLATION",
                f"Invalid phase: {phase}. Must be one of: {valid_phases}",
            )

        # Map ruleset names to rule instances
        rule_name_to_class = {
            "full_file_replacement": FullFileReplacementRule,
            "explicit_assumptions": ExplicitAssumptionsRule,
            "required_section": RequiredSectionRule,
            "no_hallucinated_files": NoHallucinatedFilesRule,
            "output_format": OutputFormatRule,
        }

        # Default rules per phase
        default_rules_per_phase = {
            "analysis": ["explicit_assumptions", "required_section"],
            "design": ["required_section", "output_format"],
            "implementation": ["full_file_replacement", "output_format"],
            "validation": ["no_hallucinated_files", "output_format"],
            "hardening": ["output_format"],
        }

        # Use provided ruleset or phase defaults
        active_ruleset = ruleset or default_rules_per_phase.get(phase, [])

        # Instantiate rules
        rules = []
        for rule_name in active_ruleset:
            rule_class = rule_name_to_class.get(rule_name)
            if rule_class:
                # Instantiate with appropriate severity for phase
                severity = (
                    ValidationLevel.FAIL
                    if phase in ["validation", "implementation"]
                    else ValidationLevel.WARN
                )
                try:
                    # Special handling for rules with required arguments
                    if rule_name == "required_section":
                        # Default sections based on phase
                        sections = {
                            "analysis": ["Findings", "Risks", "Next Steps"],
                            "design": ["Architecture", "Components", "Trade-offs"],
                            "implementation": ["Code", "Tests", "Documentation"],
                            "validation": ["Results", "Coverage", "Issues"],
                            "hardening": ["Security", "Performance", "Monitoring"],
                        }
                        rule = rule_class(
                            required_sections=sections.get(phase, ["Summary"]),
                            severity=severity
                        )
                    else:
                        rule = rule_class(severity=severity)
                    rules.append(rule)
                except TypeError as e:
                    # Rule might have different arguments, skip with warning
                    pass

        # Run validation
        engine = ValidationEngine(fail_fast=False)
        validation_result = engine.validate(output, rules)

        # Map validation level to status
        status = validation_result.overall_level.value

        # Extract violations
        violations = []
        for error in validation_result.errors:
            violations.append({
                "rule": "error",
                "message": error,
            })
        for warning in validation_result.warnings:
            violations.append({
                "rule": "warning",
                "message": warning,
            })

        # Determine if we can proceed
        can_proceed = status in ["pass", "warn"]

        # Build summary
        summary = f"Validation {status}: {len(validation_result.passed_rules)} passed, {len(validation_result.failed_rules)} failed"
        if validation_result.warnings:
            summary += f", {len(validation_result.warnings)} warnings"

        return {
            "status": status,
            "violations": violations,
            "summary": summary,
            "can_proceed": can_proceed,
        }

    except Exception as e:
        return _error_response(
            "VALIDATION_ERROR",
            f"Error during validation: {str(e)}",
            {"exception": type(e).__name__},
        )


def lathe_context_preview(
    query: str,
    sources: Optional[List[str]] = None,
    max_tokens: int = 2000,
) -> Dict[str, Any]:
    """
    Preview what context would be injected.

    Assembles context from specified sources and returns preview with token estimates.
    Useful for understanding context budget before full planning.

    Args:
        query: Query or identifier for context gathering
        sources: List of source types (knowledge, memory, files)
        max_tokens: Maximum tokens to include in preview

    Returns:
        {
            "context_blocks": [
                {"source": str, "size_tokens": int, "preview": str}
            ],
            "total_tokens": int,
            "truncated": bool
        }
        OR error response
    """
    try:
        # Map source names to types
        source_type_map = {
            "knowledge": ContextSourceType.KNOWLEDGE,
            "memory": ContextSourceType.MEMORY,
            "files": ContextSourceType.FILE,
        }

        # Build context sources
        context_sources: List[ContextSource] = []
        for source_name in (sources or ["knowledge"]):
            source_type = source_type_map.get(source_name)
            if source_type:
                # Create minimal context source with preview content
                preview_content = f"[{source_name.upper()} SOURCE]\nQuery: {query}\n\nContent from {source_name} would appear here."
                context_sources.append(
                    ContextSource(
                        type=source_type,
                        identifier=f"{source_name}_{query}",
                        content=preview_content,
                        priority=75 if source_type == ContextSourceType.KNOWLEDGE else 50,
                        metadata={"query": query, "source": source_name},
                    )
                )

        # Estimate max content length from token budget
        # Rough estimate: 1 token ≈ 4 characters
        max_content_length = max_tokens * 4

        # Build context
        context_builder = ContextBuilder(max_content_length=max_content_length)
        context_output = context_builder.build(context_sources)

        # Format context blocks for preview
        context_blocks = []
        total_estimated_tokens = 0

        for source_id in context_output.sources_used:
            # Find the source to get its content length
            for source in context_sources:
                if source.identifier == source_id:
                    estimated_tokens = len(source.content) // 4
                    total_estimated_tokens += estimated_tokens

                    context_blocks.append({
                        "source": source.type.value,
                        "size_tokens": estimated_tokens,
                        "preview": source.content[:200] + ("..." if len(source.content) > 200 else ""),
                    })
                    break

        truncated = total_estimated_tokens > max_tokens

        return {
            "context_blocks": context_blocks,
            "total_tokens": total_estimated_tokens,
            "truncated": truncated,
        }

    except Exception as e:
        return _error_response(
            "INTERNAL_ERROR",
            f"Error in lathe_context_preview: {str(e)}",
            {"exception": type(e).__name__},
        )


# OpenWebUI tool metadata
__title__ = "Lathe"
__description__ = "AI coding control layer with phase-locked development"
__version__ = "1.0.0"
__author__ = "Lathe Project"
