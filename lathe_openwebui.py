from typing import Any, Dict, List, Optional
import lathe_tool


class Tools:
    def lathe_plan(
        self,
        project: str,
        scope: str,
        phase: str,
        goal: str,
        constraints: Optional[List[str]] = None,
        sources: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Prepare a phase-locked AI planning step.

        Args:
            project: Project identifier
            scope: Scope of work (e.g., module, component)
            phase: Phase: analysis, design, implementation, validation, hardening
            goal: Goal for this phase
            constraints: Optional list of constraints
            sources: Optional list of source types (knowledge, memory, files)

        Returns:
            Phase plan with system prompt, context blocks, rules, and risks
        """
        return lathe_tool.lathe_plan(
            project=project,
            scope=scope,
            phase=phase,
            goal=goal,
            constraints=constraints,
            sources=sources,
        )

    def lathe_validate(
        self,
        phase: str,
        output: str,
        ruleset: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Validate AI output against Lathe rules.

        Args:
            phase: Phase: analysis, design, implementation, validation, hardening
            output: AI-generated output to validate
            ruleset: Optional list of rule names to apply

        Returns:
            Validation result with status, violations, and proceed decision
        """
        return lathe_tool.lathe_validate(
            phase=phase,
            output=output,
            ruleset=ruleset,
        )

    def lathe_context_preview(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """Preview context that would be injected for a query.

        Args:
            query: Query or identifier for context gathering
            sources: Optional list of source types (knowledge, memory, files)
            max_tokens: Maximum tokens to include in preview

        Returns:
            Context preview with blocks and token estimates
        """
        return lathe_tool.lathe_context_preview(
            query=query,
            sources=sources,
            max_tokens=max_tokens,
        )
