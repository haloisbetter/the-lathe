"""
Tests for executor layer.

Verifies:
- Proposals do not auto-apply
- Refusals cannot be executed
- Execution requires explicit invocation
- Dry-run does not mutate
"""
import pytest

from lathe_app.executor import (
    PatchExecutor,
    ExecutionResult,
    ExecutionStatus,
    execute_from_run,
)
from lathe_app.artifacts import (
    ArtifactInput,
    ObservabilityTrace,
    RunRecord,
    ProposalArtifact,
    RefusalArtifact,
    PlanArtifact,
)


def make_input():
    return ArtifactInput(
        intent="propose",
        task="test task",
        why={"goal": "test"},
    )


def make_proposal_artifact():
    return ProposalArtifact.create(
        input_data=make_input(),
        proposals=[{"action": "create_file", "target": "test.py"}],
        assumptions=["test"],
        risks=["test"],
        results=[],
        model_fingerprint="test-model",
        observability=ObservabilityTrace.empty(),
    )


def make_refusal_artifact():
    return RefusalArtifact.create(
        input_data=make_input(),
        reason="Cannot comply",
        details="Policy violation",
        observability=ObservabilityTrace.empty(),
    )


def make_plan_artifact():
    return PlanArtifact.create(
        input_data=ArtifactInput(intent="plan", task="test", why={}),
        steps=[{"step": 1}],
        dependencies=[],
        results=[],
        model_fingerprint="test",
        observability=ObservabilityTrace.empty(),
    )


class TestPatchExecutor:
    """Tests for PatchExecutor."""
    
    def test_validate_proposal_passes(self):
        executor = PatchExecutor()
        artifact = make_proposal_artifact()
        
        error = executor.validate_artifact(artifact)
        
        assert error is None
    
    def test_validate_refusal_fails(self):
        executor = PatchExecutor()
        artifact = make_refusal_artifact()
        
        error = executor.validate_artifact(artifact)
        
        assert error is not None
        assert "RefusalArtifact" in error
        assert "not actionable" in error
    
    def test_validate_plan_fails(self):
        executor = PatchExecutor()
        artifact = make_plan_artifact()
        
        error = executor.validate_artifact(artifact)
        
        assert error is not None
        assert "PlanArtifact" in error
        assert "decomposed" in error
    
    def test_dry_run_does_not_apply(self):
        executor = PatchExecutor()
        artifact = make_proposal_artifact()
        
        result = executor.execute(artifact, dry_run=True)
        
        assert result.status == ExecutionStatus.DRY_RUN
        assert result.applied is False
        assert len(result.diff) > 0
        for patch in result.diff:
            assert patch["status"] == "pending"
    
    def test_execute_applies_patches(self):
        executor = PatchExecutor()
        artifact = make_proposal_artifact()
        
        result = executor.execute(artifact, dry_run=False)
        
        assert result.status == ExecutionStatus.SUCCESS
        assert result.applied is True
        for patch in result.diff:
            assert patch["status"] == "applied"
    
    def test_execute_refusal_rejected(self):
        executor = PatchExecutor()
        artifact = make_refusal_artifact()
        
        result = executor.execute(artifact, dry_run=True)
        
        assert result.status == ExecutionStatus.REJECTED
        assert "RefusalArtifact" in result.error
    
    def test_execute_plan_rejected(self):
        executor = PatchExecutor()
        artifact = make_plan_artifact()
        
        result = executor.execute(artifact, dry_run=True)
        
        assert result.status == ExecutionStatus.REJECTED
        assert "PlanArtifact" in result.error


class TestExecuteFromRun:
    """Tests for execute_from_run function."""
    
    def test_execute_successful_run(self):
        run = RunRecord.create(
            input_data=make_input(),
            output=make_proposal_artifact(),
            model_used="test",
            fallback_triggered=False,
            success=True,
        )
        
        result = execute_from_run(run, dry_run=True)
        
        assert result.status == ExecutionStatus.DRY_RUN
    
    def test_execute_failed_run_rejected(self):
        run = RunRecord.create(
            input_data=make_input(),
            output=make_refusal_artifact(),
            model_used="test",
            fallback_triggered=False,
            success=False,
        )
        
        result = execute_from_run(run, dry_run=True)
        
        assert result.status == ExecutionStatus.REJECTED
        assert "not successful" in result.error


class TestExecutionResult:
    """Tests for ExecutionResult factory methods."""
    
    def test_success_result(self):
        result = ExecutionResult.success(diff=[{"op": "create"}])
        
        assert result.status == ExecutionStatus.SUCCESS
        assert result.applied is True
        assert len(result.diff) == 1
    
    def test_failure_result(self):
        result = ExecutionResult.failure("Something broke")
        
        assert result.status == ExecutionStatus.FAILURE
        assert result.applied is False
        assert result.error == "Something broke"
    
    def test_dry_run_result(self):
        result = ExecutionResult.dry_run(diff=[{"op": "modify"}])
        
        assert result.status == ExecutionStatus.DRY_RUN
        assert result.applied is False
    
    def test_rejected_result(self):
        result = ExecutionResult.rejected("Not allowed")
        
        assert result.status == ExecutionStatus.REJECTED
        assert result.error == "Not allowed"


class TestProposalsDoNotAutoApply:
    """Critical test: proposals must never auto-apply."""
    
    def test_orchestrator_does_not_execute(self):
        """Verify that running a request does NOT apply changes."""
        from lathe_app import run_request
        
        why = {"goal": "test", "context": "test", "evidence": "test",
               "decision": "test", "risk_level": "Low",
               "options_considered": [], "guardrails": [], "verification_steps": []}
        
        result = run_request(
            intent="propose",
            task="create file test.py",
            why=why,
        )
        
        assert isinstance(result, RunRecord)
        
        import os
        assert not os.path.exists("test.py"), "File should NOT have been created!"
