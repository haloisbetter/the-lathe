"""
Lathe App Layer

The shell around the Lathe kernel.
All state lives here. Lathe remains pure.
"""
from typing import Optional

from lathe_app.orchestrator import Orchestrator
from lathe_app.artifacts import (
    RunRecord,
    PlanArtifact,
    ProposalArtifact,
    RefusalArtifact,
)
from lathe_app.storage import Storage, InMemoryStorage, NullStorage
from lathe_app.executor import (
    PatchExecutor,
    ExecutionResult,
    ExecutionStatus,
    execute_from_run,
)

_default_storage = InMemoryStorage()
_default_orchestrator = Orchestrator(storage=_default_storage)


def run_request(
    intent: str,
    task: str,
    why: dict,
    *,
    model: str = None,
) -> RunRecord:
    """
    Execute a request through Lathe and return a structured RunRecord.
    
    This is the main entry point for the app layer.
    Lathe is called but never stores state.
    
    Args:
        intent: The intent type (propose, think, rag, etc.)
        task: The task description
        why: The WHY record (goal, context, evidence, etc.)
        model: Optional model override
        
    Returns:
        RunRecord containing the full execution trace and artifacts.
        
    NOTE: Proposals are NOT auto-applied.
    Call execute_proposal() to apply changes.
    """
    return _default_orchestrator.execute(
        intent=intent,
        task=task,
        why=why,
        model=model,
    )


def execute_proposal(
    run_id: str,
    *,
    dry_run: bool = True,
) -> ExecutionResult:
    """
    Execute a proposal from a stored run.
    
    SAFETY GUARANTEES:
    - Accepts ONLY ProposalArtifact
    - Rejects RefusalArtifact (cannot execute a refusal)
    - Rejects PlanArtifact (plans must be decomposed first)
    - dry_run=True by default (no filesystem changes)
    
    Args:
        run_id: ID of the run to execute
        dry_run: If True (default), compute diff but don't apply
        
    Returns:
        ExecutionResult with status, diff, and error (if any)
    """
    run = _default_storage.load_run(run_id)
    
    if run is None:
        return ExecutionResult.rejected(f"Run not found: {run_id}")
    
    return execute_from_run(run, dry_run=dry_run)


def list_runs() -> list:
    """List all stored run IDs."""
    return _default_storage.list_runs()


def load_run(run_id: str) -> Optional[RunRecord]:
    """Load a run by ID."""
    return _default_storage.load_run(run_id)


__all__ = [
    "run_request",
    "execute_proposal",
    "list_runs",
    "load_run",
    "Orchestrator",
    "RunRecord",
    "PlanArtifact",
    "ProposalArtifact",
    "RefusalArtifact",
    "Storage",
    "InMemoryStorage",
    "NullStorage",
    "PatchExecutor",
    "ExecutionResult",
    "ExecutionStatus",
]
