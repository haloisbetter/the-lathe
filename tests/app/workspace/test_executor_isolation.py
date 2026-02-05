"""Tests for executor workspace isolation."""
import os
import pytest
import tempfile
from lathe_app.executor import PatchExecutor, ExecutionStatus
from lathe_app.artifacts import ArtifactInput, ProposalArtifact, ObservabilityTrace
from lathe_app.workspace.context import WorkspaceContext


def make_proposal(targets: list) -> ProposalArtifact:
    """Create a proposal with given targets."""
    input_data = ArtifactInput(
        intent="propose",
        task="test task",
        why={"test": True},
    )
    return ProposalArtifact.create(
        input_data=input_data,
        proposals=[{"action": "create", "target": t} for t in targets],
        assumptions=[],
        risks=[],
        results=[],
        model_fingerprint="test-model",
        observability=ObservabilityTrace.empty(),
    )


class TestExecutorWorkspaceIsolation:
    """Tests for executor workspace isolation."""
    
    def test_execution_inside_workspace(self):
        """Test execution succeeds for targets inside workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = WorkspaceContext(workspace_id="test", root_path=tmpdir)
            executor = PatchExecutor(context=ctx)
            
            proposal = make_proposal([
                "src/main.py",
                "tests/test_main.py",
            ])
            
            result = executor.execute(proposal, dry_run=True)
            
            assert result.status == ExecutionStatus.DRY_RUN
            assert result.workspace_id == "test"
    
    def test_execution_outside_workspace_rejected(self):
        """Test execution refused for targets outside workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = WorkspaceContext(workspace_id="test", root_path=tmpdir)
            executor = PatchExecutor(context=ctx)
            
            proposal = make_proposal(["/etc/passwd"])
            
            result = executor.execute(proposal, dry_run=True)
            
            assert result.status == ExecutionStatus.REJECTED
            assert "outside workspace" in result.error
            assert result.workspace_id == "test"
    
    def test_execution_traversal_rejected(self):
        """Test execution refused for path traversal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = WorkspaceContext(workspace_id="test", root_path=tmpdir)
            executor = PatchExecutor(context=ctx)
            
            proposal = make_proposal(["../escape.txt"])
            
            result = executor.execute(proposal, dry_run=True)
            
            assert result.status == ExecutionStatus.REJECTED
            assert "outside workspace" in result.error
    
    def test_workspace_id_in_result(self):
        """Test workspace ID is recorded in result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = WorkspaceContext(workspace_id="my-ws", root_path=tmpdir)
            executor = PatchExecutor(context=ctx)
            
            proposal = make_proposal(["file.py"])
            result = executor.execute(proposal, dry_run=True)
            
            assert result.workspace_id == "my-ws"
    
    def test_mixed_targets_rejected(self):
        """Test mixed inside/outside targets are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = WorkspaceContext(workspace_id="test", root_path=tmpdir)
            executor = PatchExecutor(context=ctx)
            
            proposal = make_proposal([
                "valid/file.py",
                "/etc/shadow",
            ])
            
            result = executor.execute(proposal, dry_run=True)
            
            assert result.status == ExecutionStatus.REJECTED
    
    def test_unknown_target_allowed(self):
        """Test unknown target is not rejected (graceful degradation)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = WorkspaceContext(workspace_id="test", root_path=tmpdir)
            executor = PatchExecutor(context=ctx)
            
            proposal = make_proposal(["unknown"])
            proposal.proposals[0]["target"] = "unknown"
            
            result = executor.execute(proposal, dry_run=True)
            
            assert result.status == ExecutionStatus.DRY_RUN


class TestBackwardCompatibility:
    """Tests for backward compatibility without workspace."""
    
    def test_executor_without_context(self):
        """Test executor works without explicit context."""
        executor = PatchExecutor()
        
        proposal = make_proposal(["file.py"])
        result = executor.execute(proposal, dry_run=True)
        
        assert result.status == ExecutionStatus.DRY_RUN
        assert result.workspace_id is not None
    
    def test_default_context_used(self):
        """Test default context is used when none provided."""
        executor = PatchExecutor()
        
        assert executor._context is not None
        assert executor._context.workspace_id is not None
