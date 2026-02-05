"""
Lathe App Review Layer

Human review state machine for proposals.

States:
- proposed: Initial state after creation
- reviewed: Human has looked at it
- approved: Human has approved for execution
- rejected: Human has rejected
- executed: Successfully executed

Rules:
- execute_proposal() MUST refuse unless state == approved
- State transitions are explicit and auditable
- No automatic transitions
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from lathe_app.artifacts import RunRecord, ProposalArtifact
from lathe_app.storage import Storage


class ReviewState(Enum):
    """Review states for proposals."""
    PROPOSED = "proposed"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


class ReviewAction(Enum):
    """Actions that can be taken on a proposal."""
    REVIEW = "review"
    APPROVE = "approve"
    REJECT = "reject"
    EXECUTE = "execute"


VALID_TRANSITIONS = {
    ReviewState.PROPOSED: {ReviewAction.REVIEW, ReviewAction.APPROVE, ReviewAction.REJECT},
    ReviewState.REVIEWED: {ReviewAction.APPROVE, ReviewAction.REJECT},
    ReviewState.APPROVED: {ReviewAction.EXECUTE, ReviewAction.REJECT},
    ReviewState.REJECTED: set(),
    ReviewState.EXECUTED: set(),
}


@dataclass
class ReviewEntry:
    """A single review action entry."""
    timestamp: str
    action: str
    from_state: str
    to_state: str
    comment: Optional[str] = None


@dataclass
class ReviewRecord:
    """Complete review history for a run."""
    run_id: str
    state: ReviewState
    history: List[ReviewEntry]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "state": self.state.value,
            "history": [
                {
                    "timestamp": e.timestamp,
                    "action": e.action,
                    "from_state": e.from_state,
                    "to_state": e.to_state,
                    "comment": e.comment,
                }
                for e in self.history
            ],
        }


@dataclass
class ReviewResult:
    """Result of a review action."""
    success: bool
    run_id: str
    previous_state: str
    new_state: str
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "run_id": self.run_id,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "error": self.error,
            "results": [],
        }


class ReviewManager:
    """
    Manages review states for proposals.
    
    State machine enforcing human review before execution.
    """
    
    def __init__(self, storage: Storage):
        self._storage = storage
        self._reviews: Dict[str, ReviewRecord] = {}
    
    def get_review(self, run_id: str) -> Optional[ReviewRecord]:
        """Get review record for a run."""
        if run_id not in self._reviews:
            run = self._storage.load_run(run_id)
            if run is None:
                return None
            
            if not run.success:
                return None
            
            if not isinstance(run.output, ProposalArtifact):
                return None
            
            self._reviews[run_id] = ReviewRecord(
                run_id=run_id,
                state=ReviewState.PROPOSED,
                history=[],
            )
        
        return self._reviews.get(run_id)
    
    def get_state(self, run_id: str) -> Optional[ReviewState]:
        """Get current review state for a run."""
        review = self.get_review(run_id)
        return review.state if review else None
    
    def transition(
        self,
        run_id: str,
        action: ReviewAction,
        *,
        comment: Optional[str] = None,
    ) -> ReviewResult:
        """
        Attempt a state transition.
        
        Args:
            run_id: ID of the run to review
            action: The action to take (review, approve, reject, execute)
            comment: Optional comment for the transition
            
        Returns:
            ReviewResult with success/failure and state info
        """
        review = self.get_review(run_id)
        
        if review is None:
            return ReviewResult(
                success=False,
                run_id=run_id,
                previous_state="unknown",
                new_state="unknown",
                error=f"Run {run_id} not found or not a proposal",
            )
        
        current_state = review.state
        valid_actions = VALID_TRANSITIONS.get(current_state, set())
        
        if action not in valid_actions:
            return ReviewResult(
                success=False,
                run_id=run_id,
                previous_state=current_state.value,
                new_state=current_state.value,
                error=f"Cannot {action.value} from state {current_state.value}. "
                      f"Valid actions: {[a.value for a in valid_actions]}",
            )
        
        new_state = self._apply_action(current_state, action)
        
        entry = ReviewEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action.value,
            from_state=current_state.value,
            to_state=new_state.value,
            comment=comment,
        )
        review.history.append(entry)
        review.state = new_state
        
        return ReviewResult(
            success=True,
            run_id=run_id,
            previous_state=current_state.value,
            new_state=new_state.value,
        )
    
    def _apply_action(self, state: ReviewState, action: ReviewAction) -> ReviewState:
        """Compute new state after action."""
        if action == ReviewAction.REVIEW:
            return ReviewState.REVIEWED
        if action == ReviewAction.APPROVE:
            return ReviewState.APPROVED
        if action == ReviewAction.REJECT:
            return ReviewState.REJECTED
        if action == ReviewAction.EXECUTE:
            return ReviewState.EXECUTED
        return state
    
    def is_approved(self, run_id: str) -> bool:
        """Check if a run is approved for execution."""
        state = self.get_state(run_id)
        return state == ReviewState.APPROVED
    
    def mark_executed(self, run_id: str) -> None:
        """Mark a run as executed after successful execution."""
        self.transition(run_id, ReviewAction.EXECUTE)
