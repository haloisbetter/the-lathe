"""
Tests for observability instrumentation.

Verifies:
- trace_id exists in all responses
- Stage order is deterministic
- Fallback events are recorded
- Refusal includes observability block
- Observability never affects control flow
"""
import pytest
import json

from lathe.observability import ObservabilityRecorder, create_recorder
from lathe.pipeline import process_request
from lathe.model_tiers import FALLBACK_MODEL


class TestObservabilityRecorder:
    """Tests for the ObservabilityRecorder class."""
    
    def test_start_generates_trace_id(self):
        recorder = create_recorder(enabled=True)
        trace_id = recorder.start()
        
        assert trace_id != ""
        assert len(trace_id) == 36
    
    def test_disabled_recorder_returns_empty(self):
        recorder = create_recorder(enabled=False)
        recorder.start()
        recorder.record("test_stage")
        
        result = recorder.to_dict()
        assert result == {}
    
    def test_stages_recorded_in_order(self):
        recorder = create_recorder(enabled=True)
        recorder.start()
        recorder.record("stage_1")
        recorder.record("stage_2")
        recorder.record("stage_3")
        
        result = recorder.to_dict()
        stage_names = [s["name"] for s in result["stages"]]
        
        assert stage_names == ["stage_1", "stage_2", "stage_3"]
    
    def test_timestamps_are_monotonic(self):
        recorder = create_recorder(enabled=True)
        recorder.start()
        recorder.record("first")
        recorder.record("second")
        recorder.record("third")
        
        result = recorder.to_dict()
        timestamps = [s["timestamp"] for s in result["stages"]]
        
        assert timestamps == sorted(timestamps)
    
    def test_model_record(self):
        recorder = create_recorder(enabled=True)
        recorder.start()
        recorder.record_model(
            requested="qwen2.5",
            used="deepseek-chat",
            fallback_triggered=True,
            fallback_reason="Model not authorized",
        )
        
        result = recorder.to_dict()
        
        assert result["models"]["requested"] == "qwen2.5"
        assert result["models"]["used"] == "deepseek-chat"
        assert result["models"]["fallback_triggered"] is True
        assert result["models"]["fallback_reason"] == "Model not authorized"
    
    def test_outcome_record_success(self):
        recorder = create_recorder(enabled=True)
        recorder.start()
        recorder.record_outcome(success=True, refusal=False)
        
        result = recorder.to_dict()
        
        assert result["outcome"]["success"] is True
        assert result["outcome"]["refusal"] is False
    
    def test_outcome_record_refusal(self):
        recorder = create_recorder(enabled=True)
        recorder.start()
        recorder.record_outcome(success=False, refusal=True, reason="Invalid input")
        
        result = recorder.to_dict()
        
        assert result["outcome"]["success"] is False
        assert result["outcome"]["refusal"] is True
        assert result["outcome"]["reason"] == "Invalid input"
    
    def test_recorder_never_raises(self):
        recorder = create_recorder(enabled=True)
        recorder.record("before_start")
        recorder.record_model(requested="x", used="y")
        recorder.record_outcome(success=True, refusal=False)
        result = recorder.to_dict()
        
        assert "trace_id" in result


class TestPipelineObservability:
    """Tests for observability integration in pipeline."""
    
    def dummy_agent_fn(self, normalized, model_id):
        """Dummy agent that returns valid response."""
        return json.dumps({
            "proposals": [],
            "results": [],
            "model_fingerprint": model_id,
        })
    
    def failing_agent_fn(self, normalized, model_id):
        """Agent that returns invalid output."""
        return "This is not valid JSON"
    
    def test_success_response_has_observability(self):
        payload = {
            "intent": "think",
            "task": "analyze code",
            "why": {"goal": "Test", "context": "Test", "evidence": "Test",
                    "decision": "Test", "risk_level": "Low",
                    "options_considered": [], "guardrails": [], "verification_steps": []}
        }
        
        result = process_request(
            payload, "deepseek-chat", self.dummy_agent_fn,
            require_fingerprint=True, enable_observability=True
        )
        
        assert "_observability" in result.response
        obs = result.response["_observability"]
        
        assert "trace_id" in obs
        assert len(obs["trace_id"]) == 36
    
    def test_refusal_response_has_observability(self):
        payload = {"invalid": "payload"}
        
        result = process_request(
            payload, "deepseek-chat", self.dummy_agent_fn,
            require_fingerprint=True, enable_observability=True
        )
        
        assert result.response.get("refusal") is True
        assert "_observability" in result.response
        
        obs = result.response["_observability"]
        assert obs["outcome"]["refusal"] is True
    
    def test_stage_order_is_deterministic(self):
        payload = {
            "intent": "think",
            "task": "analyze code",
            "why": {"goal": "Test", "context": "Test", "evidence": "Test",
                    "decision": "Test", "risk_level": "Low",
                    "options_considered": [], "guardrails": [], "verification_steps": []}
        }
        
        result1 = process_request(
            payload, "deepseek-chat", self.dummy_agent_fn,
            require_fingerprint=True, enable_observability=True
        )
        result2 = process_request(
            payload, "deepseek-chat", self.dummy_agent_fn,
            require_fingerprint=True, enable_observability=True
        )
        
        stages1 = [s["name"] for s in result1.response["_observability"]["stages"]]
        stages2 = [s["name"] for s in result2.response["_observability"]["stages"]]
        
        assert stages1 == stages2
    
    def test_fallback_recorded_in_observability(self):
        payload = {
            "intent": "propose",
            "task": "add feature",
            "why": {"goal": "Test", "context": "Test", "evidence": "Test",
                    "decision": "Test", "risk_level": "Low",
                    "options_considered": [], "guardrails": [], "verification_steps": []}
        }
        
        result = process_request(
            payload, "qwen2.5", self.dummy_agent_fn,
            require_fingerprint=True, enable_observability=True
        )
        
        assert result.fallback_triggered is True
        
        obs = result.response["_observability"]
        assert obs["models"]["fallback_triggered"] is True
        assert obs["models"]["requested"] == "qwen2.5"
        assert obs["models"]["used"] == FALLBACK_MODEL
    
    def test_observability_disabled(self):
        payload = {
            "intent": "think",
            "task": "analyze code",
            "why": {"goal": "Test", "context": "Test", "evidence": "Test",
                    "decision": "Test", "risk_level": "Low",
                    "options_considered": [], "guardrails": [], "verification_steps": []}
        }
        
        result = process_request(
            payload, "deepseek-chat", self.dummy_agent_fn,
            require_fingerprint=True, enable_observability=False
        )
        
        assert "_observability" not in result.response or result.response.get("_observability") == {}
    
    def test_observability_does_not_affect_response_content(self):
        payload = {
            "intent": "think",
            "task": "analyze code",
            "why": {"goal": "Test", "context": "Test", "evidence": "Test",
                    "decision": "Test", "risk_level": "Low",
                    "options_considered": [], "guardrails": [], "verification_steps": []}
        }
        
        result_with = process_request(
            payload, "deepseek-chat", self.dummy_agent_fn,
            require_fingerprint=True, enable_observability=True
        )
        result_without = process_request(
            payload, "deepseek-chat", self.dummy_agent_fn,
            require_fingerprint=True, enable_observability=False
        )
        
        resp_with = {k: v for k, v in result_with.response.items() if k != "_observability"}
        resp_without = {k: v for k, v in result_without.response.items() if k != "_observability"}
        
        assert resp_with == resp_without
    
    def test_pipeline_stages_recorded(self):
        payload = {
            "intent": "think",
            "task": "analyze code",
            "why": {"goal": "Test", "context": "Test", "evidence": "Test",
                    "decision": "Test", "risk_level": "Low",
                    "options_considered": [], "guardrails": [], "verification_steps": []}
        }
        
        result = process_request(
            payload, "deepseek-chat", self.dummy_agent_fn,
            require_fingerprint=True, enable_observability=True
        )
        
        obs = result.response["_observability"]
        stage_names = [s["name"] for s in obs["stages"]]
        
        assert "pipeline_start" in stage_names
        assert "normalize_input" in stage_names
        assert "normalize_success" in stage_names
        assert "classify_model" in stage_names
        assert "execute_model" in stage_names
        assert "execute_complete" in stage_names
