"""
Tests for artifact models.

Verifies artifacts are plain data objects with required fields.
"""
import pytest

from lathe_app.artifacts import (
    ArtifactInput,
    ObservabilityTrace,
    RefusalArtifact,
    ProposalArtifact,
    PlanArtifact,
    RunRecord,
)


class TestArtifactInput:
    """Tests for ArtifactInput."""
    
    def test_create_input(self):
        input_data = ArtifactInput(
            intent="propose",
            task="add feature",
            why={"goal": "test"},
            model_requested="deepseek-chat",
        )
        
        assert input_data.intent == "propose"
        assert input_data.task == "add feature"
        assert input_data.why == {"goal": "test"}
        assert input_data.model_requested == "deepseek-chat"


class TestObservabilityTrace:
    """Tests for ObservabilityTrace."""
    
    def test_from_dict(self):
        data = {
            "trace_id": "abc-123",
            "stages": [{"name": "start"}],
            "models": {"used": "deepseek"},
            "outcome": {"success": True},
        }
        
        trace = ObservabilityTrace.from_dict(data)
        
        assert trace.trace_id == "abc-123"
        assert len(trace.stages) == 1
        assert trace.models["used"] == "deepseek"
        assert trace.outcome["success"] is True
    
    def test_empty_trace(self):
        trace = ObservabilityTrace.empty()
        
        assert trace.trace_id == ""
        assert trace.stages == []
        assert trace.models == {}
        assert trace.outcome == {}


class TestRefusalArtifact:
    """Tests for RefusalArtifact."""
    
    def test_create_refusal(self):
        input_data = ArtifactInput(
            intent="propose",
            task="bad task",
            why={},
        )
        obs = ObservabilityTrace.empty()
        
        refusal = RefusalArtifact.create(
            input_data=input_data,
            reason="Invalid input",
            details="Task is malformed",
            observability=obs,
        )
        
        assert refusal.id is not None
        assert len(refusal.id) == 36
        assert refusal.timestamp is not None
        assert refusal.reason == "Invalid input"
        assert refusal.details == "Task is malformed"
        assert refusal.input == input_data


class TestProposalArtifact:
    """Tests for ProposalArtifact."""
    
    def test_create_proposal(self):
        input_data = ArtifactInput(
            intent="propose",
            task="add auth",
            why={"goal": "security"},
        )
        obs = ObservabilityTrace.empty()
        
        proposal = ProposalArtifact.create(
            input_data=input_data,
            proposals=[{"action": "add login"}],
            assumptions=["user exists"],
            risks=["session hijack"],
            results=[],
            model_fingerprint="deepseek-v3",
            observability=obs,
        )
        
        assert proposal.id is not None
        assert proposal.proposals == [{"action": "add login"}]
        assert proposal.assumptions == ["user exists"]
        assert proposal.risks == ["session hijack"]
        assert proposal.model_fingerprint == "deepseek-v3"


class TestPlanArtifact:
    """Tests for PlanArtifact."""
    
    def test_create_plan(self):
        input_data = ArtifactInput(
            intent="plan",
            task="build system",
            why={"goal": "automation"},
        )
        obs = ObservabilityTrace.empty()
        
        plan = PlanArtifact.create(
            input_data=input_data,
            steps=[{"step": 1, "action": "design"}],
            dependencies=["numpy"],
            results=[],
            model_fingerprint="gpt-4",
            observability=obs,
        )
        
        assert plan.id is not None
        assert plan.steps == [{"step": 1, "action": "design"}]
        assert plan.dependencies == ["numpy"]


class TestRunRecord:
    """Tests for RunRecord."""
    
    def test_create_run_record(self):
        input_data = ArtifactInput(
            intent="propose",
            task="task",
            why={},
        )
        output = RefusalArtifact.create(
            input_data=input_data,
            reason="test",
            details="test",
            observability=ObservabilityTrace.empty(),
        )
        
        record = RunRecord.create(
            input_data=input_data,
            output=output,
            model_used="deepseek-chat",
            fallback_triggered=False,
            success=False,
        )
        
        assert record.id is not None
        assert record.model_used == "deepseek-chat"
        assert record.fallback_triggered is False
        assert record.success is False
        assert isinstance(record.output, RefusalArtifact)
