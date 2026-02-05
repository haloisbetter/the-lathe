"""
Lathe Processing Pipeline

Integrates:
- Prompt normalization
- Model tier enforcement
- Output validation
- Automatic fallback

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


def process_request(
    payload: dict,
    model_id: str,
    agent_fn,
    allow_fallback: bool = True,
    require_fingerprint: bool = True,
) -> PipelineResult:
    """
    Process an agent request through the full pipeline.
    
    Steps:
    1. Normalize input
    2. Check model tier
    3. Execute with model
    4. Validate output
    5. Fallback if needed (only for propose/think with non-Tier-A models)
    
    Returns PipelineResult with response and metadata.
    """
    normalized, is_valid, error = normalize_request(payload)
    
    if not is_valid or normalized is None:
        return PipelineResult(
            response=create_refusal_from_error(
                reason="Input normalization failed",
                details=error
            ),
            model_used="none",
            fallback_triggered=False,
            normalization_applied=[],
            fingerprint=None,
        )
    
    classification = classify_model(model_id)
    is_tier_a = classification.tier == ModelTier.TIER_A
    intent_allows_fallback = normalized.intent in ("propose", "think")
    
    allowed, tier_reason = can_execute_intent(model_id, normalized.intent)
    
    if not allowed:
        if allow_fallback and intent_allows_fallback and not is_tier_a:
            fallback_model = get_fallback_model(model_id) or FALLBACK_MODEL
            log_fallback_event(model_id, fallback_model, tier_reason)
            
            response, success = execute_with_model(
                normalized, fallback_model, agent_fn, require_fingerprint
            )
            
            return PipelineResult(
                response=response,
                model_used=fallback_model,
                fallback_triggered=True,
                normalization_applied=normalized.normalization_applied,
                fingerprint=response.get("model_fingerprint"),
            )
        else:
            return PipelineResult(
                response=create_refusal_from_error(
                    reason="Model not authorized for intent",
                    details=tier_reason
                ),
                model_used=model_id,
                fallback_triggered=False,
                normalization_applied=normalized.normalization_applied,
                fingerprint=None,
            )
    
    response, success = execute_with_model(
        normalized, model_id, agent_fn, require_fingerprint
    )
    
    if not success and allow_fallback and intent_allows_fallback and not is_tier_a:
        fallback_model = get_fallback_model(model_id) or FALLBACK_MODEL
        
        if fallback_model != model_id:
            log_fallback_event(model_id, fallback_model, "Primary model failed validation")
            
            fallback_response, fallback_success = execute_with_model(
                normalized, fallback_model, agent_fn, require_fingerprint
            )
            
            return PipelineResult(
                response=fallback_response,
                model_used=fallback_model,
                fallback_triggered=True,
                normalization_applied=normalized.normalization_applied,
                fingerprint=fallback_response.get("model_fingerprint"),
            )
    
    return PipelineResult(
        response=response,
        model_used=model_id,
        fallback_triggered=False,
        normalization_applied=normalized.normalization_applied,
        fingerprint=response.get("model_fingerprint"),
    )
