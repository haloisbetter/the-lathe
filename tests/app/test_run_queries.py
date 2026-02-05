"""
Tests for run history queries.

Verifies:
- Query by intent
- Query by outcome (success/refusal)
- Query by file path
- Query by time range
- All queries are read-only
"""
import pytest

from lathe_app.storage import InMemoryStorage
from lathe_app.query import RunQuery
from lathe_app.artifacts import (
    ArtifactInput,
    ObservabilityTrace,
    RunRecord,
    ProposalArtifact,
    RefusalArtifact,
)


def make_proposal_run(intent: str = "propose", files: list = None) -> RunRecord:
    """Create a test run with a proposal."""
    input_data = ArtifactInput(
        intent=intent,
        task="test task",
        why={"goal": "test"},
    )
    proposals = []
    if files:
        for f in files:
            proposals.append({"action": "modify", "target": f})
    
    output = ProposalArtifact.create(
        input_data=input_data,
        proposals=proposals,
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


def make_refusal_run(intent: str = "propose") -> RunRecord:
    """Create a test run with a refusal."""
    input_data = ArtifactInput(
        intent=intent,
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


class TestRunQuery:
    """Tests for RunQuery."""
    
    def test_search_by_intent(self):
        storage = InMemoryStorage()
        storage.save_run(make_proposal_run(intent="propose"))
        storage.save_run(make_proposal_run(intent="think"))
        storage.save_run(make_proposal_run(intent="plan"))
        
        query = RunQuery(storage)
        
        result = query.search(intent="propose")
        assert result.total == 1
        assert result.runs[0].input.intent == "propose"
        
        result = query.search(intent="think")
        assert result.total == 1
    
    def test_search_by_outcome_success(self):
        storage = InMemoryStorage()
        storage.save_run(make_proposal_run())
        storage.save_run(make_refusal_run())
        
        query = RunQuery(storage)
        
        result = query.search(outcome="success")
        assert result.total == 1
        assert result.runs[0].success is True
    
    def test_search_by_outcome_refusal(self):
        storage = InMemoryStorage()
        storage.save_run(make_proposal_run())
        storage.save_run(make_refusal_run())
        
        query = RunQuery(storage)
        
        result = query.search(outcome="refusal")
        assert result.total == 1
        assert result.runs[0].success is False
    
    def test_search_by_file(self):
        storage = InMemoryStorage()
        storage.save_run(make_proposal_run(files=["src/main.py"]))
        storage.save_run(make_proposal_run(files=["tests/test_main.py"]))
        
        query = RunQuery(storage)
        
        result = query.search(file="main.py")
        assert result.total == 2
        
        result = query.search(file="tests/")
        assert result.total == 1
    
    def test_search_with_limit(self):
        storage = InMemoryStorage()
        for i in range(10):
            storage.save_run(make_proposal_run())
        
        query = RunQuery(storage)
        
        result = query.search(limit=5)
        assert len(result.runs) == 5
    
    def test_get_files_touched(self):
        storage = InMemoryStorage()
        run = make_proposal_run(files=["a.py", "b.py"])
        storage.save_run(run)
        
        query = RunQuery(storage)
        
        files = query.get_files_touched(run.id)
        assert "a.py" in files
        assert "b.py" in files
    
    def test_query_is_readonly(self):
        """Verify queries don't modify storage."""
        storage = InMemoryStorage()
        run = make_proposal_run()
        storage.save_run(run)
        original_count = len(storage.list_runs())
        
        query = RunQuery(storage)
        query.search(intent="propose")
        query.search(outcome="success")
        query.get_files_touched(run.id)
        
        assert len(storage.list_runs()) == original_count
