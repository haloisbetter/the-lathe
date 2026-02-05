"""
Tests for storage layer.

Verifies:
- Runs persist correctly
- Load/save/list/delete work
- NullStorage discards everything
"""
import pytest

from lathe_app.storage import InMemoryStorage, NullStorage
from lathe_app.artifacts import (
    ArtifactInput,
    ObservabilityTrace,
    RunRecord,
    ProposalArtifact,
)


def make_test_run(run_id: str = None) -> RunRecord:
    """Create a test RunRecord."""
    input_data = ArtifactInput(
        intent="propose",
        task="test task",
        why={"goal": "test"},
    )
    output = ProposalArtifact.create(
        input_data=input_data,
        proposals=[],
        assumptions=[],
        risks=[],
        results=[],
        model_fingerprint="test",
        observability=ObservabilityTrace.empty(),
    )
    run = RunRecord.create(
        input_data=input_data,
        output=output,
        model_used="test-model",
        fallback_triggered=False,
        success=True,
    )
    if run_id:
        run.id = run_id
    return run


class TestInMemoryStorage:
    """Tests for InMemoryStorage."""
    
    def test_save_and_load(self):
        storage = InMemoryStorage()
        run = make_test_run()
        
        storage.save_run(run)
        loaded = storage.load_run(run.id)
        
        assert loaded is not None
        assert loaded.id == run.id
    
    def test_load_missing_returns_none(self):
        storage = InMemoryStorage()
        
        loaded = storage.load_run("nonexistent-id")
        
        assert loaded is None
    
    def test_list_runs(self):
        storage = InMemoryStorage()
        run1 = make_test_run("run-1")
        run2 = make_test_run("run-2")
        
        storage.save_run(run1)
        storage.save_run(run2)
        
        run_ids = storage.list_runs()
        
        assert "run-1" in run_ids
        assert "run-2" in run_ids
        assert len(run_ids) == 2
    
    def test_delete_run(self):
        storage = InMemoryStorage()
        run = make_test_run("to-delete")
        storage.save_run(run)
        
        result = storage.delete_run("to-delete")
        
        assert result is True
        assert storage.load_run("to-delete") is None
    
    def test_delete_missing_returns_false(self):
        storage = InMemoryStorage()
        
        result = storage.delete_run("nonexistent")
        
        assert result is False
    
    def test_clear(self):
        storage = InMemoryStorage()
        storage.save_run(make_test_run("run-1"))
        storage.save_run(make_test_run("run-2"))
        
        storage.clear()
        
        assert storage.list_runs() == []


class TestNullStorage:
    """Tests for NullStorage."""
    
    def test_save_does_nothing(self):
        storage = NullStorage()
        run = make_test_run()
        
        storage.save_run(run)
        
        assert storage.load_run(run.id) is None
    
    def test_list_returns_empty(self):
        storage = NullStorage()
        
        assert storage.list_runs() == []
    
    def test_delete_returns_false(self):
        storage = NullStorage()
        
        assert storage.delete_run("any-id") is False
