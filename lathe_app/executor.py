"""
Lathe App Executor Layer

Applies proposals to the filesystem.
Side effects are EXPLICIT, AUDITABLE, and OPT-IN.

ARCHITECTURAL LAW:
"Lathe reasons.
The app decides.
Executors act.
Nothing else is allowed."

WORKSPACE ISOLATION:
Executors act ONLY inside workspaces.
Execution outside workspace root is refused.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import os

from lathe_app.artifacts import (
    ProposalArtifact,
    RefusalArtifact,
    PlanArtifact,
    RunRecord,
)
from lathe_app.workspace.context import WorkspaceContext, get_current_context


class ExecutionStatus(Enum):
    """Outcome of an execution attempt."""
    SUCCESS = "success"
    FAILURE = "failure"
    DRY_RUN = "dry_run"
    REJECTED = "rejected"


@dataclass
class ExecutionResult:
    """
    Result of executing (or attempting to execute) a proposal.
    
    Contains:
    - status: success, failure, dry_run, or rejected
    - diff: what would change (or did change)
    - error: error message if failed
    - applied: whether changes were actually applied
    - workspace_id: the workspace this execution was scoped to
    """
    status: ExecutionStatus
    diff: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    applied: bool = False
    workspace_id: Optional[str] = None
    
    @classmethod
    def success(cls, diff: List[Dict[str, Any]], workspace_id: str = None) -> "ExecutionResult":
        return cls(status=ExecutionStatus.SUCCESS, diff=diff, applied=True, workspace_id=workspace_id)
    
    @classmethod
    def failure(cls, error: str, workspace_id: str = None) -> "ExecutionResult":
        return cls(status=ExecutionStatus.FAILURE, error=error, applied=False, workspace_id=workspace_id)
    
    @classmethod
    def dry_run(cls, diff: List[Dict[str, Any]], workspace_id: str = None) -> "ExecutionResult":
        return cls(status=ExecutionStatus.DRY_RUN, diff=diff, applied=False, workspace_id=workspace_id)
    
    @classmethod
    def rejected(cls, reason: str, workspace_id: str = None) -> "ExecutionResult":
        return cls(status=ExecutionStatus.REJECTED, error=reason, applied=False, workspace_id=workspace_id)


class PatchExecutor:
    """
    Executes proposals by applying patches to the filesystem.
    
    SAFETY GUARANTEES:
    - Accepts ONLY ProposalArtifact
    - Rejects RefusalArtifact (cannot execute a refusal)
    - Rejects PlanArtifact (plans are not executable)
    - Applies patches ONLY when explicitly called
    - Supports dry_run mode (default: True)
    - Never touches Lathe
    - Refuses execution outside workspace root
    
    Side effects are:
    - Explicit: must call execute()
    - Auditable: returns diff of all changes
    - Opt-in: dry_run=True by default
    """
    
    def __init__(self, context: WorkspaceContext = None):
        """
        Initialize executor with optional workspace context.
        
        Args:
            context: Workspace context for isolation. Uses default if None.
        """
        self._context = context or get_current_context()
    
    def validate_artifact(self, artifact: Any) -> Optional[str]:
        """
        Validate that artifact is executable.
        
        Returns None if valid, error message if invalid.
        """
        if isinstance(artifact, RefusalArtifact):
            return "Cannot execute a RefusalArtifact. Refusals are not actionable."
        
        if isinstance(artifact, PlanArtifact):
            return "Cannot execute a PlanArtifact. Plans must be decomposed into proposals first."
        
        if not isinstance(artifact, ProposalArtifact):
            return f"Unknown artifact type: {type(artifact).__name__}. Only ProposalArtifact is executable."
        
        return None
    
    def execute(
        self,
        artifact: ProposalArtifact,
        *,
        dry_run: bool = True,
    ) -> ExecutionResult:
        """
        Execute a proposal.
        
        Args:
            artifact: The ProposalArtifact to execute
            dry_run: If True (default), compute diff but don't apply
            
        Returns:
            ExecutionResult with status and diff
        """
        ws_id = self._context.workspace_id
        
        validation_error = self.validate_artifact(artifact)
        if validation_error:
            return ExecutionResult.rejected(validation_error, workspace_id=ws_id)
        
        try:
            diff = self._compute_diff(artifact)
            
            boundary_error = self._validate_workspace_boundaries(diff)
            if boundary_error:
                return ExecutionResult.rejected(boundary_error, workspace_id=ws_id)
            
            if dry_run:
                return ExecutionResult.dry_run(diff, workspace_id=ws_id)
            
            self._apply_patches(diff)
            return ExecutionResult.success(diff, workspace_id=ws_id)
            
        except Exception as e:
            return ExecutionResult.failure(str(e), workspace_id=ws_id)
    
    def _validate_workspace_boundaries(self, diff: List[Dict[str, Any]]) -> Optional[str]:
        """
        Validate that all targets in diff are within workspace.
        
        Returns error message if any target escapes workspace, None if all valid.
        """
        for patch in diff:
            target = patch.get("target")
            if target and target != "unknown":
                resolved = self._context.resolve_path(target)
                if resolved is None:
                    return f"Execution refused: target '{target}' is outside workspace '{self._context.root_path}'"
        return None
    
    def _compute_diff(self, artifact: ProposalArtifact) -> List[Dict[str, Any]]:
        """
        Compute the diff for a proposal.
        
        Returns list of patch operations.
        """
        diff = []
        
        for proposal in artifact.proposals:
            action = proposal.get("action", "unknown")
            target = proposal.get("target", proposal.get("file", "unknown"))
            
            diff.append({
                "operation": action,
                "target": target,
                "proposal": proposal,
                "status": "pending",
            })
        
        return diff
    
    def _apply_patches(self, diff: List[Dict[str, Any]]) -> None:
        """
        Apply patches to filesystem.
        
        In a real implementation, this would:
        - Write files
        - Create directories
        - Apply code modifications
        
        Currently a placeholder that marks patches as applied.
        """
        for patch in diff:
            patch["status"] = "applied"


def execute_from_run(
    run: RunRecord,
    *,
    dry_run: bool = True,
    context: WorkspaceContext = None,
) -> ExecutionResult:
    """
    Execute a proposal from a RunRecord.
    
    Convenience function that validates and executes.
    
    Args:
        run: The RunRecord containing the artifact
        dry_run: If True (default), don't apply changes
        context: Optional workspace context for isolation
        
    Returns:
        ExecutionResult
    """
    executor = PatchExecutor(context=context)
    ws_id = executor._context.workspace_id
    
    if not run.success:
        return ExecutionResult.rejected(
            f"Cannot execute failed run. Run {run.id} was not successful.",
            workspace_id=ws_id,
        )
    
    artifact = run.output
    
    validation_error = executor.validate_artifact(artifact)
    if validation_error:
        return ExecutionResult.rejected(validation_error, workspace_id=ws_id)
    
    return executor.execute(artifact, dry_run=dry_run)
