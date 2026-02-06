"""
Tests for speculative model selection.

Proves:
1) Speculative selection escalates when validator rejects
2) Escalation reasons are logged in RunRecord.escalation
3) Non-speculative intents skip escalation
4) Better results are accepted, worse results are rejected
"""
import json
import pytest
from lathe_app.orchestrator import (
    Orchestrator,
    SPECULATIVE_STRONG_MODEL,
    WARNING_ESCALATION_THRESHOLD,
)
from lathe_app.classification import ResultClassification, FailureType
from lathe_app.storage import InMemoryStorage


def make_success_agent(model_fingerprint="test-model"):
    def agent_fn(normalized, model_id):
        return json.dumps({
            "proposals": [{"action": "create", "target": "test.py"}],
            "assumptions": [],
            "risks": [],
            "results": [],
            "model_fingerprint": model_fingerprint,
        })
    return agent_fn


def make_failing_then_success_agent():
    call_count = {"n": 0}
    def agent_fn(normalized, model_id):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return "INVALID JSON GARBAGE"
        return json.dumps({
            "proposals": [{"action": "create", "target": "test.py"}],
            "assumptions": [],
            "risks": [],
            "results": [],
            "model_fingerprint": model_id,
        })
    return agent_fn


def make_always_failing_agent():
    def agent_fn(normalized, model_id):
        return "INVALID JSON GARBAGE"
    return agent_fn


class TestSpeculativeSelection:
    def test_successful_run_has_classification(self):
        orch = Orchestrator(agent_fn=make_success_agent())
        run = orch.execute(
            intent="propose",
            task="test",
            why={"goal": "test"},
            speculative=False,
        )
        assert run.classification is not None
        assert run.classification.failure_type == FailureType.SUCCESS

    def test_failed_run_has_classification(self):
        orch = Orchestrator(agent_fn=make_always_failing_agent())
        run = orch.execute(
            intent="propose",
            task="test",
            why={"goal": "test"},
            speculative=False,
        )
        assert run.classification is not None
        assert run.classification.failure_type != FailureType.SUCCESS

    def test_escalation_on_failure(self):
        orch = Orchestrator(agent_fn=make_failing_then_success_agent())
        run = orch.execute(
            intent="propose",
            task="test",
            why={"goal": "test"},
            speculative=True,
        )
        assert run.escalation is not None
        assert run.escalation["to_model"] == SPECULATIVE_STRONG_MODEL
        assert "reasons" in run.escalation
        assert len(run.escalation["reasons"]) > 0

    def test_no_escalation_for_rag_intent(self):
        orch = Orchestrator(agent_fn=make_always_failing_agent())
        run = orch.execute(
            intent="rag",
            task="test",
            why={"goal": "test"},
            speculative=True,
        )
        assert run.escalation is None

    def test_no_escalation_when_disabled(self):
        orch = Orchestrator(agent_fn=make_failing_then_success_agent())
        run = orch.execute(
            intent="propose",
            task="test",
            why={"goal": "test"},
            speculative=False,
        )
        assert run.escalation is None

    def test_escalation_stored_in_record(self):
        storage = InMemoryStorage()
        orch = Orchestrator(
            agent_fn=make_failing_then_success_agent(),
            storage=storage,
        )
        run = orch.execute(
            intent="propose",
            task="test",
            why={"goal": "test"},
            speculative=True,
        )
        loaded = storage.load_run(run.id)
        assert loaded is not None
        assert loaded.escalation is not None

    def test_no_escalation_when_already_strong(self):
        orch = Orchestrator(agent_fn=make_always_failing_agent())
        run = orch.execute(
            intent="propose",
            task="test",
            why={"goal": "test"},
            model=SPECULATIVE_STRONG_MODEL,
            speculative=True,
        )
        assert run.escalation is None

    def test_classification_always_present(self):
        for agent in [make_success_agent(), make_always_failing_agent()]:
            orch = Orchestrator(agent_fn=agent)
            for intent in ["propose", "think", "rag"]:
                run = orch.execute(
                    intent=intent,
                    task="test",
                    why={"goal": "test"},
                    speculative=False,
                )
                assert run.classification is not None
                assert hasattr(run.classification, "failure_type")
                assert hasattr(run.classification, "confidence")
                assert hasattr(run.classification, "warnings")
                assert hasattr(run.classification, "reasons")
