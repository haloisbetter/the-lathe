"""
Lathe App Executor Layer

Applies proposals to the filesystem.
Side effects are EXPLICIT, AUDITABLE, and OPT-IN.

ARCHITECTURAL LAW:
"Lathe reasons.
The app decides.
Executors act.
Nothing else is allowed."
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

from lathe_app.artifacts import (
    ProposalArtifact,
    RefusalArtifact,
    PlanArtifact,
    RunRecord,
)


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
    """
    status: ExecutionStatus
    diff: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    applied: bool = False
    
    @classmethod
    def success(cls, diff: List[Dict[str, Any]]) -> "ExecutionResult":
        return cls(status=ExecutionStatus.SUCCESS, diff=diff, applied=True)
    
    @classmethod
    def failure(cls, error: str) -> "ExecutionResult":
        return cls(status=ExecutionStatus.FAILURE, error=error, applied=False)
    
    @classmethod
    def dry_run(cls, diff: List[Dict[str, Any]]) -> "ExecutionResult":
        return cls(status=ExecutionStatus.DRY_RUN, diff=diff, applied=False)
    
    @classmethod
    def rejected(cls, reason: str) -> "ExecutionResult":
        return cls(status=ExecutionStatus.REJECTED, error=reason, applied=False)


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
    
    Side effects are:
    - Explicit: must call execute()
    - Auditable: returns diff of all changes
    - Opt-in: dry_run=True by default
    """
    
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
        validation_error = self.validate_artifact(artifact)
        if validation_error:
            return ExecutionResult.rejected(validation_error)
        
        try:
            diff = self._compute_diff(artifact)
            
            if dry_run:
                return ExecutionResult.dry_run(diff)
            
            self._apply_patches(diff)
            return ExecutionResult.success(diff)
            
        except Exception as e:
            return ExecutionResult.failure(str(e))
    
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
) -> ExecutionResult:
    """
    Execute a proposal from a RunRecord.
    
    Convenience function that validates and executes.
    
    Args:
        run: The RunRecord containing the artifact
        dry_run: If True (default), don't apply changes
        
    Returns:
        ExecutionResult
    """
    executor = PatchExecutor()
    
    if not run.success:
        return ExecutionResult.rejected(
            f"Cannot execute failed run. Run {run.id} was not successful."
        )
    
    artifact = run.output
    
    validation_error = executor.validate_artifact(artifact)
    if validation_error:
        return ExecutionResult.rejected(validation_error)
    
    return executor.execute(artifact, dry_run=dry_run)
