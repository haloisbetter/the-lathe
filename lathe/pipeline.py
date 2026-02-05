"""
Lathe Processing Pipeline

Integrates:
- Prompt normalization
- Model tier enforcement
- Output validation
- Automatic fallback
- Observability (passive instrumentation)

This is the single entry point for processing agent requests.
"""
import logging
from typing import Tuple, Optional
from dataclasses import dataclass

from lathe.normalize import normalize_request, to_canonical_dict, NormalizedRequest
from lathe.output_validator import (
    validate_and_normalize_output,
    create_refusal_from_error,
)
from lathe.model_tiers import (
    classify_model,
    can_execute_intent,
    get_fallback_model,
    ModelTier,
    FALLBACK_MODEL,
)
from lathe.observability import ObservabilityRecorder, create_recorder

logger = logging.getLogger("lathe.pipeline")


@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    response: dict
    model_used: str
    fallback_triggered: bool
    normalization_applied: list
    fingerprint: Optional[str]


def log_fallback_event(original_model: str, fallback_model: str, reason: str):
    """Log a fallback event for auditing."""
    logger.warning(
        f"FALLBACK_TRIGGERED: {original_model} -> {fallback_model}. Reason: {reason}"
    )


def execute_with_model(
    normalized: NormalizedRequest,
    model_id: str,
    agent_fn,
    require_fingerprint: bool = True,
) -> Tuple[dict, bool]:
    """
    Execute a request with a specific model.
    
    Returns (response, success).
    """
    try:
        response = agent_fn(normalized, model_id)
        
        validated = validate_and_normalize_output(
            response, 
            source_model=model_id,
            require_fingerprint=require_fingerprint,
            strict_json=True,
        )
        
        if validated.get("refusal") is True:
            return validated, False
        
        return validated, True
        
    except Exception as e:
        return create_refusal_from_error(
            reason="Execution failed",
            details=f"Model: {model_id}. Error: {str(e)}"
        ), False


def _attach_observability(response: dict, recorder: ObservabilityRecorder) -> dict:
    """Attach observability data to response. Never modifies decision logic."""
    try:
        obs_data = recorder.to_dict()
        if obs_data:
            response["_observability"] = obs_data
    except Exception:
        pass
    return response


def process_request(
    payload: dict,
    model_id: str,
    agent_fn,
    allow_fallback: bool = True,
    require_fingerprint: bool = True,
    enable_observability: bool = True,
) -> PipelineResult:
    """
    Process an agent request through the full pipeline.
    
    Steps:
    1. Normalize input
    2. Check model tier
    3. Execute with model
    4. Validate output
    5. Fallback if needed (only for propose/think with non-Tier-A models)
    
    Observability is passive instrumentation that never affects control flow.
    
    Returns PipelineResult with response and metadata.
    """
    recorder = create_recorder(enabled=enable_observability)
    recorder.start()
    recorder.record("pipeline_start", {"model_requested": model_id})
    
    recorder.record("normalize_input")
    normalized, is_valid, error = normalize_request(payload)
    
    if not is_valid or normalized is None:
        recorder.record("normalize_failed", {"error": error})
        recorder.record_model(requested=model_id, used="none")
        recorder.record_outcome(success=False, refusal=True, reason="Input normalization failed")
        
        response = create_refusal_from_error(
            reason="Input normalization failed",
            details=error
        )
        return PipelineResult(
            response=_attach_observability(response, recorder),
            model_used="none",
            fallback_triggered=False,
            normalization_applied=[],
            fingerprint=None,
        )
    
    recorder.record("normalize_success", {"intent": normalized.intent})
    
    recorder.record("classify_model")
    classification = classify_model(model_id)
    is_tier_a = classification.tier == ModelTier.TIER_A
    intent_allows_fallback = normalized.intent in ("propose", "think")
    
    recorder.record("check_authorization")
    allowed, tier_reason = can_execute_intent(model_id, normalized.intent)
    
    if not allowed:
        recorder.record("authorization_denied", {"reason": tier_reason})
        
        if allow_fallback and intent_allows_fallback and not is_tier_a:
            fallback_model = get_fallback_model(model_id) or FALLBACK_MODEL
            log_fallback_event(model_id, fallback_model, tier_reason)
            recorder.record("fallback_triggered", {"reason": tier_reason})
            
            recorder.record("execute_model", {"model": fallback_model})
            response, success = execute_with_model(
                normalized, fallback_model, agent_fn, require_fingerprint
            )
            recorder.record("execute_complete", {"success": success})
            
            recorder.record_model(
                requested=model_id,
                used=fallback_model,
                fallback_triggered=True,
                fallback_reason=tier_reason,
            )
            recorder.record_outcome(
                success=success,
                refusal=response.get("refusal") is True,
                reason=response.get("reason") if response.get("refusal") else None,
            )
            
            return PipelineResult(
                response=_attach_observability(response, recorder),
                model_used=fallback_model,
                fallback_triggered=True,
                normalization_applied=normalized.normalization_applied,
                fingerprint=response.get("model_fingerprint"),
            )
        else:
            recorder.record_model(requested=model_id, used=model_id)
            recorder.record_outcome(success=False, refusal=True, reason="Model not authorized")
            
            response = create_refusal_from_error(
                reason="Model not authorized for intent",
                details=tier_reason
            )
            return PipelineResult(
                response=_attach_observability(response, recorder),
                model_used=model_id,
                fallback_triggered=False,
                normalization_applied=normalized.normalization_applied,
                fingerprint=None,
            )
    
    recorder.record("authorization_granted")
    recorder.record("execute_model", {"model": model_id})
    response, success = execute_with_model(
        normalized, model_id, agent_fn, require_fingerprint
    )
    recorder.record("execute_complete", {"success": success})
    
    if not success and allow_fallback and intent_allows_fallback and not is_tier_a:
        fallback_model = get_fallback_model(model_id) or FALLBACK_MODEL
        
        if fallback_model != model_id:
            log_fallback_event(model_id, fallback_model, "Primary model failed validation")
            recorder.record("fallback_triggered", {"reason": "Primary model failed validation"})
            
            recorder.record("execute_model", {"model": fallback_model})
            fallback_response, fallback_success = execute_with_model(
                normalized, fallback_model, agent_fn, require_fingerprint
            )
            recorder.record("execute_complete", {"success": fallback_success})
            
            recorder.record_model(
                requested=model_id,
                used=fallback_model,
                fallback_triggered=True,
                fallback_reason="Primary model failed validation",
            )
            recorder.record_outcome(
                success=fallback_success,
                refusal=fallback_response.get("refusal") is True,
                reason=fallback_response.get("reason") if fallback_response.get("refusal") else None,
            )
            
            return PipelineResult(
                response=_attach_observability(fallback_response, recorder),
                model_used=fallback_model,
                fallback_triggered=True,
                normalization_applied=normalized.normalization_applied,
                fingerprint=fallback_response.get("model_fingerprint"),
            )
    
    recorder.record_model(requested=model_id, used=model_id, fallback_triggered=False)
    recorder.record_outcome(
        success=success,
        refusal=response.get("refusal") is True,
        reason=response.get("reason") if response.get("refusal") else None,
    )
    
    return PipelineResult(
        response=_attach_observability(response, recorder),
        model_used=model_id,
        fallback_triggered=False,
        normalization_applied=normalized.normalization_applied,
        fingerprint=response.get("model_fingerprint"),
    )
