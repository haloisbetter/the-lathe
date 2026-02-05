"""
Tests for the orchestrator.

Verifies:
- Refusals produce RefusalArtifact
- Successful propose produces ProposalArtifact
- Lathe behavior is unchanged
- Orchestrator contains all state, Lathe contains none
"""
import pytest
import json

from lathe_app import run_request, Orchestrator
from lathe_app.artifacts import (
    RunRecord,
    RefusalArtifact,
    ProposalArtifact,
    PlanArtifact,
)
from lathe.model_tiers import FALLBACK_MODEL


def valid_agent_fn(normalized, model_id: str) -> str:
    """Agent that returns valid JSON."""
    return json.dumps({
        "proposals": [{"action": "test"}],
        "assumptions": ["test assumption"],
        "risks": ["test risk"],
        "results": [],
        "model_fingerprint": model_id,
    })


def refusing_agent_fn(normalized, model_id: str) -> str:
    """Agent that returns a refusal."""
    return json.dumps({
        "refusal": True,
        "reason": "Cannot comply",
        "details": "Policy violation",
        "results": [],
    })


def malformed_agent_fn(normalized, model_id: str) -> str:
    """Agent that returns malformed output."""
    return "This is not JSON"


class TestOrchestrator:
    """Tests for Orchestrator class."""
    
    def test_successful_propose_returns_proposal_artifact(self):
        orch = Orchestrator(agent_fn=valid_agent_fn)
        
        result = orch.execute(
            intent="propose",
            task="add validation",
            why={"goal": "test", "context": "test", "evidence": "test",
                 "decision": "test", "risk_level": "Low",
                 "options_considered": [], "guardrails": [], "verification_steps": []},
            model="deepseek-chat",
        )
        
        assert isinstance(result, RunRecord)
        assert result.success is True
        assert isinstance(result.output, ProposalArtifact)
        assert result.output.proposals == [{"action": "test"}]
        assert result.output.assumptions == ["test assumption"]
        assert result.output.model_fingerprint == "deepseek-chat"
    
    def test_refusal_produces_refusal_artifact(self):
        orch = Orchestrator(agent_fn=refusing_agent_fn)
        
        result = orch.execute(
            intent="think",
            task="analyze code",
            why={"goal": "test", "context": "test", "evidence": "test",
                 "decision": "test", "risk_level": "Low",
                 "options_considered": [], "guardrails": [], "verification_steps": []},
            model="deepseek-chat",
        )
        
        assert isinstance(result, RunRecord)
        assert result.success is False
        assert isinstance(result.output, RefusalArtifact)
        assert result.output.reason == "Cannot comply"
        assert result.output.details == "Policy violation"
    
    def test_malformed_output_produces_refusal(self):
        orch = Orchestrator(agent_fn=malformed_agent_fn)
        
        result = orch.execute(
            intent="think",
            task="analyze code",
            why={"goal": "test", "context": "test", "evidence": "test",
                 "decision": "test", "risk_level": "Low",
                 "options_considered": [], "guardrails": [], "verification_steps": []},
            model="deepseek-chat",
        )
        
        assert isinstance(result, RunRecord)
        assert result.success is False
        assert isinstance(result.output, RefusalArtifact)
        assert "validation failed" in result.output.reason.lower()
    
    def test_invalid_input_produces_refusal(self):
        orch = Orchestrator(agent_fn=valid_agent_fn)
        
        result = orch.execute(
            intent="propose",
            task="",
            why={},
        )
        
        assert isinstance(result, RunRecord)
        assert result.success is False
        assert isinstance(result.output, RefusalArtifact)
    
    def test_observability_attached_to_artifact(self):
        orch = Orchestrator(agent_fn=valid_agent_fn)
        
        result = orch.execute(
            intent="propose",
            task="add feature",
            why={"goal": "test", "context": "test", "evidence": "test",
                 "decision": "test", "risk_level": "Low",
                 "options_considered": [], "guardrails": [], "verification_steps": []},
            model="deepseek-chat",
        )
        
        assert result.output.observability is not None
        assert result.output.observability.trace_id != ""
        assert len(result.output.observability.stages) > 0
    
    def test_fallback_recorded(self):
        orch = Orchestrator(agent_fn=valid_agent_fn)
        
        result = orch.execute(
            intent="propose",
            task="add feature",
            why={"goal": "test", "context": "test", "evidence": "test",
                 "decision": "test", "risk_level": "Low",
                 "options_considered": [], "guardrails": [], "verification_steps": []},
            model="qwen2.5",
        )
        
        assert result.fallback_triggered is True
        assert result.model_used == FALLBACK_MODEL
    
    def test_orchestrator_is_stateless(self):
        orch = Orchestrator(agent_fn=valid_agent_fn)
        
        result1 = orch.execute(
            intent="propose",
            task="first task",
            why={"goal": "test", "context": "test", "evidence": "test",
                 "decision": "test", "risk_level": "Low",
                 "options_considered": [], "guardrails": [], "verification_steps": []},
            model="deepseek-chat",
        )
        
        result2 = orch.execute(
            intent="propose",
            task="second task",
            why={"goal": "test", "context": "test", "evidence": "test",
                 "decision": "test", "risk_level": "Low",
                 "options_considered": [], "guardrails": [], "verification_steps": []},
            model="deepseek-chat",
        )
        
        assert result1.id != result2.id
        assert result1.output.id != result2.output.id
        
        assert not hasattr(orch, '_runs')
        assert not hasattr(orch, '_history')
        assert not hasattr(orch, '_state')


class TestRunRequest:
    """Tests for the run_request convenience function."""
    
    def test_run_request_returns_run_record(self):
        result = run_request(
            intent="think",
            task="analyze architecture",
            why={"goal": "test", "context": "test", "evidence": "test",
                 "decision": "test", "risk_level": "Low",
                 "options_considered": [], "guardrails": [], "verification_steps": []},
        )
        
        assert isinstance(result, RunRecord)
        assert result.input.intent == "think"
        assert result.input.task == "analyze architecture"


class TestLatheUnchanged:
    """Tests verifying Lathe core behavior is unchanged."""
    
    def test_lathe_pipeline_still_works_directly(self):
        from lathe.pipeline import process_request
        
        def agent_fn(normalized, model_id):
            return json.dumps({
                "proposals": [],
                "results": [],
                "model_fingerprint": model_id,
            })
        
        result = process_request(
            payload={
                "intent": "think",
                "task": "test",
                "why": {"goal": "test", "context": "test", "evidence": "test",
                        "decision": "test", "risk_level": "Low",
                        "options_considered": [], "guardrails": [], "verification_steps": []},
            },
            model_id="deepseek-chat",
            agent_fn=agent_fn,
        )
        
        assert result.response.get("refusal") is not True
    
    def test_lathe_pipeline_is_stateless(self):
        """Verify Lathe pipeline doesn't accumulate state between calls."""
        from lathe.pipeline import process_request
        
        def agent_fn(normalized, model_id):
            return json.dumps({
                "proposals": [],
                "results": [],
                "model_fingerprint": model_id,
            })
        
        why = {"goal": "test", "context": "test", "evidence": "test",
               "decision": "test", "risk_level": "Low",
               "options_considered": [], "guardrails": [], "verification_steps": []}
        
        for i in range(5):
            result = process_request(
                payload={"intent": "think", "task": f"task {i}", "why": why},
                model_id="deepseek-chat",
                agent_fn=agent_fn,
            )
            assert result.response.get("refusal") is not True
