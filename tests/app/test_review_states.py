"""
Tests for human review state machine.

Verifies:
- State transitions are explicit
- Execution requires approval
- Refusals cannot be executed
- Invalid transitions are rejected
"""
import pytest

from lathe_app.storage import InMemoryStorage
from lathe_app.review import (
    ReviewManager,
    ReviewState,
    ReviewAction,
)
from lathe_app.artifacts import (
    ArtifactInput,
    ObservabilityTrace,
    RunRecord,
    ProposalArtifact,
    RefusalArtifact,
)
from lathe_app.executor import execute_from_run


def make_proposal_run() -> RunRecord:
    """Create a test run with a proposal."""
    input_data = ArtifactInput(
        intent="propose",
        task="test task",
        why={"goal": "test"},
    )
    output = ProposalArtifact.create(
        input_data=input_data,
        proposals=[{"action": "modify", "target": "test.py"}],
        assumptions=[],
        risks=[],
        results=[],
        model_fingerprint="test",
        observability=ObservabilityTrace.empty(),
    )
    return RunRecord.create(
        input_data=input_data,
        output=output,
        model_used="test-model",
        fallback_triggered=False,
        success=True,
    )


def make_refusal_run() -> RunRecord:
    """Create a test run with a refusal."""
    input_data = ArtifactInput(
        intent="propose",
        task="test task",
        why={"goal": "test"},
    )
    output = RefusalArtifact.create(
        input_data=input_data,
        reason="test refusal",
        details="details",
        observability=ObservabilityTrace.empty(),
    )
    return RunRecord.create(
        input_data=input_data,
        output=output,
        model_used="test-model",
        fallback_triggered=False,
        success=False,
    )


class TestReviewStates:
    """Tests for review state machine."""
    
    def test_initial_state_is_proposed(self):
        storage = InMemoryStorage()
        run = make_proposal_run()
        storage.save_run(run)
        
        manager = ReviewManager(storage)
        state = manager.get_state(run.id)
        
        assert state == ReviewState.PROPOSED
    
    def test_transition_to_reviewed(self):
        storage = InMemoryStorage()
        run = make_proposal_run()
        storage.save_run(run)
        
        manager = ReviewManager(storage)
        result = manager.transition(run.id, ReviewAction.REVIEW)
        
        assert result.success is True
        assert manager.get_state(run.id) == ReviewState.REVIEWED
    
    def test_transition_to_approved(self):
        storage = InMemoryStorage()
        run = make_proposal_run()
        storage.save_run(run)
        
        manager = ReviewManager(storage)
        manager.transition(run.id, ReviewAction.REVIEW)
        result = manager.transition(run.id, ReviewAction.APPROVE)
        
        assert result.success is True
        assert manager.get_state(run.id) == ReviewState.APPROVED
    
    def test_direct_approval_from_proposed(self):
        storage = InMemoryStorage()
        run = make_proposal_run()
        storage.save_run(run)
        
        manager = ReviewManager(storage)
        result = manager.transition(run.id, ReviewAction.APPROVE)
        
        assert result.success is True
        assert manager.get_state(run.id) == ReviewState.APPROVED
    
    def test_transition_to_rejected(self):
        storage = InMemoryStorage()
        run = make_proposal_run()
        storage.save_run(run)
        
        manager = ReviewManager(storage)
        result = manager.transition(run.id, ReviewAction.REJECT)
        
        assert result.success is True
        assert manager.get_state(run.id) == ReviewState.REJECTED
    
    def test_cannot_transition_from_rejected(self):
        storage = InMemoryStorage()
        run = make_proposal_run()
        storage.save_run(run)
        
        manager = ReviewManager(storage)
        manager.transition(run.id, ReviewAction.REJECT)
        
        result = manager.transition(run.id, ReviewAction.APPROVE)
        
        assert result.success is False
        assert "Cannot" in result.error
    
    def test_is_approved(self):
        storage = InMemoryStorage()
        run = make_proposal_run()
        storage.save_run(run)
        
        manager = ReviewManager(storage)
        
        assert manager.is_approved(run.id) is False
        
        manager.transition(run.id, ReviewAction.APPROVE)
        
        assert manager.is_approved(run.id) is True
    
    def test_history_recorded(self):
        storage = InMemoryStorage()
        run = make_proposal_run()
        storage.save_run(run)
        
        manager = ReviewManager(storage)
        manager.transition(run.id, ReviewAction.REVIEW, comment="First look")
        manager.transition(run.id, ReviewAction.APPROVE, comment="LGTM")
        
        review = manager.get_review(run.id)
        
        assert len(review.history) == 2
        assert review.history[0].action == "review"
        assert review.history[0].comment == "First look"
        assert review.history[1].action == "approve"
    
    def test_refusal_has_no_review_state(self):
        storage = InMemoryStorage()
        run = make_refusal_run()
        storage.save_run(run)
        
        manager = ReviewManager(storage)
        
        assert manager.get_review(run.id) is None


class TestExecutionRequiresApproval:
    """Tests that execution requires approval."""
    
    def test_execution_without_approval_rejected(self):
        """Critical: execution MUST refuse unless state == approved."""
        from lathe_app import execute_proposal
        from lathe_app import _default_storage, _default_review
        
        run = make_proposal_run()
        _default_storage.save_run(run)
        
        result = execute_proposal(run.id, dry_run=True)
        
        assert result.status.value == "rejected"
        assert "not approved" in result.error.lower()
    
    def test_execution_after_approval_works(self):
        """Approved proposals can be executed."""
        from lathe_app import execute_proposal, review_run
        from lathe_app import _default_storage
        
        run = make_proposal_run()
        _default_storage.save_run(run)
        
        review_run(run.id, "approve")
        
        result = execute_proposal(run.id, dry_run=True)
        
        assert result.status.value in ("dry_run", "success")
