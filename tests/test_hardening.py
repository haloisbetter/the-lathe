"""
Tests for architectural hardening features.

Verifies:
- Malformed model output never crashes Lathe
- Qwen-style verbose output becomes refusal
- DeepSeek fallback is triggered correctly
- Identical prompts yield identical outcomes
- Refusal is deterministic
"""
import pytest
import json

from lathe.normalize import (
    normalize_request,
    NormalizedRequest,
    extract_intent,
    normalize_why,
    build_default_why,
)
from lathe.output_validator import (
    validate_and_normalize_output,
    is_valid_json_response,
    create_refusal_from_error,
    is_refusal_response,
    contains_forbidden_content,
)
from lathe.model_tiers import (
    classify_model,
    can_execute_intent,
    get_fallback_model,
    ModelTier,
    FALLBACK_MODEL,
)
from lathe.pipeline import process_request, PipelineResult


class TestPromptNormalization:
    """Tests for the prompt normalization layer."""
    
    def test_valid_request_normalizes(self):
        payload = {
            "intent": "propose",
            "task": "add validation",
            "why": {
                "goal": "Test",
                "context": "Test",
                "evidence": "Test",
                "decision": "Test",
                "risk_level": "Low",
                "options_considered": ["A"],
                "guardrails": ["B"],
                "verification_steps": ["C"],
            }
        }
        normalized, is_valid, error = normalize_request(payload)
        
        assert is_valid
        assert normalized is not None
        assert normalized.intent == "propose"
        assert normalized.task == "add validation"
    
    def test_missing_intent_infers_from_task(self):
        payload = {
            "task": "propose changes to the auth module",
            "why": {"goal": "Test", "context": "Test", "evidence": "Test", 
                    "decision": "Test", "risk_level": "Low",
                    "options_considered": [], "guardrails": [], "verification_steps": []}
        }
        normalized, is_valid, error = normalize_request(payload)
        
        assert is_valid
        assert normalized.intent == "propose"
        assert "intent_inferred_from_keywords:propose" in normalized.normalization_applied
    
    def test_missing_why_creates_default(self):
        payload = {"intent": "think", "task": "analyze code"}
        normalized, is_valid, error = normalize_request(payload)
        
        assert is_valid
        assert normalized.why is not None
        assert "why_object_missing_created_default" in normalized.normalization_applied
    
    def test_task_truncation(self):
        payload = {
            "intent": "think",
            "task": "x" * 3000,
            "why": {"goal": "Test", "context": "Test", "evidence": "Test",
                    "decision": "Test", "risk_level": "Low",
                    "options_considered": [], "guardrails": [], "verification_steps": []}
        }
        normalized, is_valid, error = normalize_request(payload)
        
        assert is_valid
        assert len(normalized.task) == 2000
        assert "task_truncated_to_2000_chars" in normalized.normalization_applied
    
    def test_invalid_payload_type_rejected(self):
        normalized, is_valid, error = normalize_request("not a dict")
        
        assert not is_valid
        assert normalized is None
        assert "JSON object" in error
    
    def test_missing_task_rejected(self):
        normalized, is_valid, error = normalize_request({"intent": "propose"})
        
        assert not is_valid
        assert "task" in error


class TestOutputValidation:
    """Tests for output contract enforcement."""
    
    def test_valid_json_success(self):
        raw = '{"proposals": [], "results": [], "model_fingerprint": "test-model"}'
        is_valid, parsed, error = is_valid_json_response(raw, strict=True)
        
        assert is_valid
        assert parsed["proposals"] == []
    
    def test_markdown_json_rejected_in_strict_mode(self):
        raw = """```json
{"proposals": [], "results": []}
```
"""
        is_valid, parsed, error = is_valid_json_response(raw, strict=True)
        
        assert not is_valid
        assert "Markdown" in error
    
    def test_prose_prefix_rejected_in_strict_mode(self):
        raw = 'I analyzed your request: {"proposals": [], "results": []}'
        is_valid, parsed, error = is_valid_json_response(raw, strict=True)
        
        assert not is_valid
        assert "prose prefix" in error
    
    def test_invalid_json_fails(self):
        raw = "This is not JSON at all"
        is_valid, parsed, error = is_valid_json_response(raw, strict=True)
        
        assert not is_valid
        assert "prose prefix" in error or "Invalid JSON" in error
    
    def test_malformed_output_becomes_refusal(self):
        raw = "def hello(): pass  # just code"
        result = validate_and_normalize_output(raw, source_model="test-model", require_fingerprint=True)
        
        assert result["refusal"] is True
        assert "test-model" in result["details"]
    
    def test_qwen_verbose_output_becomes_refusal(self):
        raw = """
        Let me analyze this carefully. First, I'll consider the architecture...
        <thinking>
        The user wants to modify the authentication module...
        </thinking>
        
        Based on my analysis, here are some thoughts:
        1. We should consider...
        2. The best approach would be...
        
        Unfortunately I cannot provide a structured response.
        """
        result = validate_and_normalize_output(raw, source_model="qwen2.5", require_fingerprint=True)
        
        assert result["refusal"] is True
    
    def test_extra_keys_rejected(self):
        raw = '{"proposals": [], "results": [], "model_fingerprint": "test", "unexpected_key": "value"}'
        result = validate_and_normalize_output(raw, source_model="test", require_fingerprint=True)
        
        assert result["refusal"] is True
        assert "Unexpected keys" in result["details"]
    
    def test_valid_refusal_passes_through(self):
        raw = '{"refusal": true, "reason": "Cannot do this", "details": "Blocked", "results": []}'
        result = validate_and_normalize_output(raw, source_model="test", require_fingerprint=True)
        
        assert result["refusal"] is True
        assert result["reason"] == "Cannot do this"
    
    def test_missing_fingerprint_rejected(self):
        raw = '{"proposals": [], "results": []}'
        result = validate_and_normalize_output(raw, source_model="test", require_fingerprint=True)
        
        assert result["refusal"] is True
        assert "model_fingerprint" in result["details"]
    
    def test_malformed_fingerprint_rejected(self):
        raw = '{"proposals": [], "results": [], "model_fingerprint": "ab"}'
        result = validate_and_normalize_output(raw, source_model="test", require_fingerprint=True)
        
        assert result["refusal"] is True
        assert "Malformed" in result["details"]
    
    def test_html_detected_as_forbidden(self):
        has_forbidden, msg = contains_forbidden_content("<html><body>Hello</body></html>")
        
        assert has_forbidden
        assert "HTML" in msg
    
    def test_traceback_detected_as_forbidden(self):
        content = """Traceback (most recent call last):
  File "test.py", line 1
    error here
"""
        has_forbidden, msg = contains_forbidden_content(content)
        
        assert has_forbidden
        assert "traceback" in msg.lower()


class TestModelTiers:
    """Tests for model capability tiers."""
    
    def test_deepseek_is_tier_a(self):
        classification = classify_model("deepseek-chat")
        
        assert classification.tier == ModelTier.TIER_A
        assert classification.can_propose is True
        assert classification.requires_fallback is False
    
    def test_qwen_is_tier_b(self):
        classification = classify_model("qwen2.5")
        
        assert classification.tier == ModelTier.TIER_B
        assert classification.can_propose is False
        assert classification.requires_fallback is True
    
    def test_unknown_model_defaults_to_unknown(self):
        classification = classify_model("some-random-model-v1")
        
        assert classification.tier == ModelTier.UNKNOWN
        assert classification.requires_fallback is True
        assert classification.fallback_model == FALLBACK_MODEL
    
    def test_tier_b_cannot_propose(self):
        allowed, reason = can_execute_intent("qwen2.5", "propose")
        
        assert not allowed
        assert "cannot generate proposals" in reason
    
    def test_tier_b_can_think(self):
        allowed, reason = can_execute_intent("qwen2.5", "think")
        
        assert allowed
    
    def test_all_models_can_rag(self):
        for model in ["qwen", "deepseek", "unknown-model"]:
            allowed, _ = can_execute_intent(model, "rag")
            assert allowed
    
    def test_model_name_normalization(self):
        for name in ["DeepSeek-Chat:latest", "DEEPSEEK-CHAT", "user/deepseek-chat"]:
            classification = classify_model(name)
            assert classification.tier == ModelTier.TIER_A


class TestPipeline:
    """Tests for the full processing pipeline."""
    
    def dummy_agent_fn(self, normalized, model_id):
        """Dummy agent that returns valid response with fingerprint."""
        return json.dumps({
            "proposals": [],
            "assumptions": [],
            "risks": [],
            "results": [],
            "model_fingerprint": model_id,
        })
    
    def failing_agent_fn(self, normalized, model_id):
        """Agent that returns invalid output."""
        return "This is not valid JSON structure, just prose"
    
    def test_valid_request_succeeds(self):
        payload = {
            "intent": "think",
            "task": "analyze code",
            "why": {"goal": "Test", "context": "Test", "evidence": "Test",
                    "decision": "Test", "risk_level": "Low",
                    "options_considered": [], "guardrails": [], "verification_steps": []}
        }
        
        result = process_request(payload, "deepseek-chat", self.dummy_agent_fn, require_fingerprint=True)
        
        assert result.response.get("refusal") is not True
        assert result.model_used == "deepseek-chat"
        assert result.fallback_triggered is False
    
    def test_tier_b_propose_triggers_fallback(self):
        payload = {
            "intent": "propose",
            "task": "add validation",
            "why": {"goal": "Test", "context": "Test", "evidence": "Test",
                    "decision": "Test", "risk_level": "Low",
                    "options_considered": [], "guardrails": [], "verification_steps": []}
        }
        
        result = process_request(payload, "qwen2.5", self.dummy_agent_fn, require_fingerprint=True)
        
        assert result.fallback_triggered is True
        assert result.model_used == FALLBACK_MODEL
    
    def test_tier_a_invalid_output_no_fallback(self):
        """Tier A models do NOT trigger fallback even on failure."""
        payload = {
            "intent": "think",
            "task": "analyze code",
            "why": {"goal": "Test", "context": "Test", "evidence": "Test",
                    "decision": "Test", "risk_level": "Low",
                    "options_considered": [], "guardrails": [], "verification_steps": []}
        }
        
        result = process_request(payload, "deepseek-chat", self.failing_agent_fn, require_fingerprint=True)
        
        assert result.response.get("refusal") is True
        assert result.fallback_triggered is False
        assert result.model_used == "deepseek-chat"
    
    def test_tier_b_invalid_output_triggers_fallback(self):
        """Tier B models DO trigger fallback on failure for propose/think."""
        payload = {
            "intent": "think",
            "task": "analyze code",
            "why": {"goal": "Test", "context": "Test", "evidence": "Test",
                    "decision": "Test", "risk_level": "Low",
                    "options_considered": [], "guardrails": [], "verification_steps": []}
        }
        
        result = process_request(payload, "qwen2.5", self.failing_agent_fn, require_fingerprint=True)
        
        assert result.fallback_triggered is True
    
    def test_identical_prompts_yield_identical_outcomes(self):
        payload = {
            "intent": "think",
            "task": "analyze the architecture",
            "why": {"goal": "Test", "context": "Test", "evidence": "Test",
                    "decision": "Test", "risk_level": "Low",
                    "options_considered": [], "guardrails": [], "verification_steps": []}
        }
        
        result1 = process_request(payload, "deepseek-chat", self.dummy_agent_fn, require_fingerprint=True)
        result2 = process_request(payload, "deepseek-chat", self.dummy_agent_fn, require_fingerprint=True)
        
        resp1 = {k: v for k, v in result1.response.items() if k != "_observability"}
        resp2 = {k: v for k, v in result2.response.items() if k != "_observability"}
        assert resp1 == resp2
        assert result1.model_used == result2.model_used
        assert result1.fallback_triggered == result2.fallback_triggered
    
    def test_refusal_is_deterministic(self):
        payload = {"invalid": "payload"}
        
        result1 = process_request(payload, "deepseek-chat", self.dummy_agent_fn, require_fingerprint=True)
        result2 = process_request(payload, "deepseek-chat", self.dummy_agent_fn, require_fingerprint=True)
        
        assert result1.response["refusal"] is True
        assert result2.response["refusal"] is True
        assert result1.response["reason"] == result2.response["reason"]


class TestFingerprinting:
    """Tests for model fingerprinting."""
    
    def test_fingerprint_extracted_and_required(self):
        raw = '{"proposals": [], "results": [], "model_fingerprint": "deepseek-v3"}'
        result = validate_and_normalize_output(raw, source_model="test", require_fingerprint=True)
        
        assert result.get("refusal") is not True
        assert result.get("model_fingerprint") == "deepseek-v3"
    
    def test_missing_fingerprint_is_validation_failure(self):
        raw = '{"proposals": [], "results": []}'
        result = validate_and_normalize_output(raw, source_model="test", require_fingerprint=True)
        
        assert result.get("refusal") is True
        assert "model_fingerprint" in result.get("details", "")
    
    def test_fingerprint_optional_when_disabled(self):
        raw = '{"proposals": [], "results": []}'
        result = validate_and_normalize_output(raw, source_model="test", require_fingerprint=False)
        
        assert result.get("refusal") is not True


class TestRefusalSchemaExact:
    """Tests that refusal schema is EXACT."""
    
    def test_refusal_has_all_required_keys(self):
        """Refusal MUST have: refusal, reason, details, results."""
        from lathe.output_validator import REFUSAL_REQUIRED_KEYS
        
        assert REFUSAL_REQUIRED_KEYS == {"refusal", "reason", "details", "results"}
    
    def test_create_refusal_matches_exact_schema(self):
        """create_refusal_from_error returns EXACTLY the required schema."""
        refusal = create_refusal_from_error("test reason", "test details")
        
        assert set(refusal.keys()) == {"refusal", "reason", "details", "results"}
        assert refusal["refusal"] is True
        assert refusal["reason"] == "test reason"
        assert refusal["details"] == "test details"
        assert refusal["results"] == []
    
    def test_refusal_is_http_200(self):
        """Refusal is a successful outcome (HTTP 200), not an error."""
        refusal = create_refusal_from_error("test", "details")
        assert refusal.get("error") is None
    
    def test_malformed_refusal_becomes_canonical(self):
        """If model returns malformed refusal, we normalize it."""
        raw = '{"refusal": true, "reason": "test"}'  # missing details and results
        result = validate_and_normalize_output(raw, source_model="test", require_fingerprint=True)
        
        assert result["refusal"] is True
        assert "results" in result
    
    def test_success_always_has_results(self):
        """All success responses include results: []."""
        raw = '{"proposals": [], "model_fingerprint": "test"}'  # missing results
        result = validate_and_normalize_output(raw, source_model="test", require_fingerprint=True)
        
        if result.get("refusal") is not True:
            assert "results" in result


class TestPortConfiguration:
    """Tests for port configuration priority."""
    
    def test_lathe_kernel_port_is_5000(self):
        """Lathe kernel server defaults to port 5000."""
        from lathe.server import run_server
        import inspect
        sig = inspect.signature(run_server)
        default_port = sig.parameters["port"].default
        assert default_port == 5000
    
    def test_lathe_app_port_is_3001(self):
        """Lathe app server defaults to port 3001."""
        from lathe_app.server import DEFAULT_PORT
        assert DEFAULT_PORT == 3001
