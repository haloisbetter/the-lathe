"""
Lathe App Layer

The shell around the Lathe kernel.
All state lives here. Lathe remains pure.
"""
from typing import Dict, List, Optional, Any

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
from lathe_app.query import RunQuery, QueryResult
from lathe_app.review import (
    ReviewManager,
    ReviewState,
    ReviewAction,
    ReviewResult,
    ReviewRecord,
)
from lathe_app.fs import FilesystemInspector, TreeResult, GitResult

_default_storage = InMemoryStorage()
_default_orchestrator = Orchestrator(storage=_default_storage)
_default_query = RunQuery(_default_storage)
_default_review = ReviewManager(_default_storage)
_default_fs = FilesystemInspector()


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
        intent: The intent type (propose, think, rag, plan)
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
    - Requires review state == approved
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
    
    if not _default_review.is_approved(run_id):
        state = _default_review.get_state(run_id)
        state_str = state.value if state else "unknown"
        return ExecutionResult.rejected(
            f"Run {run_id} is not approved. Current state: {state_str}. "
            "Use POST /review to approve before execution."
        )
    
    result = execute_from_run(run, dry_run=dry_run)
    
    if result.applied:
        _default_review.mark_executed(run_id)
    
    return result


def list_runs() -> list:
    """List all stored run IDs."""
    return _default_storage.list_runs()


def load_run(run_id: str) -> Optional[RunRecord]:
    """Load a run by ID."""
    return _default_storage.load_run(run_id)


def search_runs(
    *,
    intent: Optional[str] = None,
    outcome: Optional[str] = None,
    file: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = 100,
) -> QueryResult:
    """
    Search runs with optional filters.
    
    Args:
        intent: Filter by intent type (propose, think, rag, plan)
        outcome: Filter by outcome (success, refusal)
        file: Filter by file path touched
        since: Filter by timestamp (ISO format)
        until: Filter by timestamp (ISO format)
        limit: Maximum results
        
    Returns:
        QueryResult with matching runs
    """
    return _default_query.search(
        intent=intent,
        outcome=outcome,
        file=file,
        since=since,
        until=until,
        limit=limit,
    )


def review_run(
    run_id: str,
    action: str,
    *,
    comment: Optional[str] = None,
) -> ReviewResult:
    """
    Perform a review action on a run.
    
    Args:
        run_id: ID of the run to review
        action: Action to take (review, approve, reject)
        comment: Optional comment
        
    Returns:
        ReviewResult with success/failure
    """
    try:
        action_enum = ReviewAction(action)
    except ValueError:
        return ReviewResult(
            success=False,
            run_id=run_id,
            previous_state="unknown",
            new_state="unknown",
            error=f"Invalid action: {action}. Valid: review, approve, reject",
        )
    
    return _default_review.transition(run_id, action_enum, comment=comment)


def get_review_state(run_id: str) -> Optional[Dict[str, Any]]:
    """Get review state for a run."""
    record = _default_review.get_review(run_id)
    return record.to_dict() if record else None


def fs_tree(path: str = ".", max_depth: int = 3) -> TreeResult:
    """Get directory tree (read-only)."""
    return _default_fs.tree(path, max_depth=max_depth)


def fs_status() -> GitResult:
    """Get git status (read-only)."""
    return _default_fs.git_status()


def fs_diff(staged: bool = False) -> GitResult:
    """Get git diff (read-only)."""
    return _default_fs.git_diff(staged=staged)


def fs_run_files(run_id: str) -> List[str]:
    """Get files touched by a run."""
    return _default_query.get_files_touched(run_id)


__all__ = [
    "run_request",
    "execute_proposal",
    "list_runs",
    "load_run",
    "search_runs",
    "review_run",
    "get_review_state",
    "fs_tree",
    "fs_status",
    "fs_diff",
    "fs_run_files",
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
    "RunQuery",
    "QueryResult",
    "ReviewManager",
    "ReviewState",
    "ReviewAction",
    "ReviewResult",
    "FilesystemInspector",
    "TreeResult",
    "GitResult",
]
