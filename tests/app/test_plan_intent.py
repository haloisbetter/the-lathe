"""
Tests for plan as a first-class intent.

Verifies:
- intent=plan produces PlanArtifact
- Plans are NOT executable
- Plans have structured steps
"""
import pytest

from lathe_app.artifacts import (
    ArtifactInput,
    ObservabilityTrace,
    RunRecord,
    PlanArtifact,
)
from lathe_app.executor import PatchExecutor, ExecutionStatus


def make_plan_artifact() -> PlanArtifact:
    """Create a test PlanArtifact."""
    input_data = ArtifactInput(
        intent="plan",
        task="plan authentication",
        why={"goal": "add auth"},
    )
    return PlanArtifact.create(
        input_data=input_data,
        steps=[
            {"step": 1, "description": "Design auth schema"},
            {"step": 2, "description": "Implement login"},
            {"step": 3, "description": "Add session management"},
        ],
        dependencies=["database", "crypto"],
        results=[],
        model_fingerprint="test",
        observability=ObservabilityTrace.empty(),
    )


class TestPlanArtifact:
    """Tests for PlanArtifact."""
    
    def test_plan_has_steps(self):
        plan = make_plan_artifact()
        
        assert len(plan.steps) == 3
        assert plan.steps[0]["step"] == 1
    
    def test_plan_has_dependencies(self):
        plan = make_plan_artifact()
        
        assert "database" in plan.dependencies
    
    def test_plan_has_intent(self):
        plan = make_plan_artifact()
        
        assert plan.input.intent == "plan"
    
    def test_plan_has_timestamp(self):
        plan = make_plan_artifact()
        
        assert plan.timestamp is not None
        assert "T" in plan.timestamp


class TestPlanNotExecutable:
    """Tests that plans cannot be executed."""
    
    def test_executor_rejects_plan(self):
        executor = PatchExecutor()
        plan = make_plan_artifact()
        
        error = executor.validate_artifact(plan)
        
        assert error is not None
        assert "PlanArtifact" in error
        assert "decomposed" in error
    
    def test_execute_plan_returns_rejected(self):
        executor = PatchExecutor()
        plan = make_plan_artifact()
        
        result = executor.execute(plan, dry_run=True)
        
        assert result.status == ExecutionStatus.REJECTED


class TestPlanIntentFlow:
    """Tests for plan intent through orchestrator."""
    
    def test_run_request_with_plan_intent(self):
        from lathe_app import run_request
        
        why = {"goal": "test", "context": "test", "evidence": "test",
               "decision": "test", "risk_level": "Low",
               "options_considered": [], "guardrails": [], "verification_steps": []}
        
        run = run_request(
            intent="plan",
            task="plan a feature",
            why=why,
        )
        
        assert run.input.intent == "plan"
        assert run.success is True
        assert isinstance(run.output, PlanArtifact)
