"""
Model Capability Tiers

Explicit model classification enforced in code.
No prompt instructions allowed as enforcement.

Tier A — Agent-Safe
- Allowed to generate proposals
- Allowed to drive Lathe decisions

Tier B — Advisory Only
- Allowed to explain, summarize, brainstorm
- NEVER allowed to generate proposals or tool output
"""
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum


class ModelTier(Enum):
    TIER_A = "agent_safe"
    TIER_B = "advisory_only"
    UNKNOWN = "unknown"


TIER_A_MODELS = frozenset({
    "deepseek-coder",
    "deepseek-chat",
    "deepseek-v3",
    "deepseek-r1",
    "deepseek",
    "gpt-4",
    "gpt-4-turbo",
    "gpt-4o",
    "gpt-4o-mini",
    "claude-3-opus",
    "claude-3-sonnet",
    "claude-3-haiku",
    "claude-3.5-sonnet",
    "claude-3.5-haiku",
    "claude-sonnet-4",
    "claude-opus-4",
    "gemini-pro",
    "gemini-1.5-pro",
    "gemini-2.0-flash",
    "codellama-70b",
    "llama-3.1-70b",
    "llama-3.1-405b",
})

TIER_B_MODELS = frozenset({
    "qwen",
    "qwen2",
    "qwen2.5",
    "qwen-turbo",
    "mistral",
    "mistral-7b",
    "mixtral",
    "phi-2",
    "phi-3",
    "llama-3.1-8b",
    "gemma",
    "gemma-2",
    "orca",
    "vicuna",
    "wizardlm",
})

FALLBACK_MODEL = "deepseek-chat"


@dataclass
class ModelClassification:
    """Result of model classification."""
    model_id: str
    tier: ModelTier
    can_propose: bool
    can_think: bool
    requires_fallback: bool
    fallback_model: Optional[str]


def normalize_model_name(model_id: str) -> str:
    """Normalize model name for comparison."""
    if not model_id:
        return ""
    
    normalized = model_id.lower().strip()
    
    for suffix in [":latest", ":instruct", ":chat", "-instruct", "-chat"]:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
    
    parts = normalized.split("/")
    if len(parts) > 1:
        normalized = parts[-1]
    
    return normalized


def classify_model(model_id: str) -> ModelClassification:
    """
    Classify a model into capability tiers.
    
    This classification is code-enforced.
    No prompt instructions allowed as enforcement.
    """
    if not model_id:
        return ModelClassification(
            model_id="unknown",
            tier=ModelTier.UNKNOWN,
            can_propose=False,
            can_think=True,
            requires_fallback=True,
            fallback_model=FALLBACK_MODEL,
        )
    
    normalized = normalize_model_name(model_id)
    
    for tier_a_model in TIER_A_MODELS:
        if tier_a_model in normalized or normalized in tier_a_model:
            return ModelClassification(
                model_id=model_id,
                tier=ModelTier.TIER_A,
                can_propose=True,
                can_think=True,
                requires_fallback=False,
                fallback_model=None,
            )
    
    for tier_b_model in TIER_B_MODELS:
        if tier_b_model in normalized or normalized in tier_b_model:
            return ModelClassification(
                model_id=model_id,
                tier=ModelTier.TIER_B,
                can_propose=False,
                can_think=True,
                requires_fallback=True,
                fallback_model=FALLBACK_MODEL,
            )
    
    return ModelClassification(
        model_id=model_id,
        tier=ModelTier.UNKNOWN,
        can_propose=False,
        can_think=True,
        requires_fallback=True,
        fallback_model=FALLBACK_MODEL,
    )


def can_execute_intent(model_id: str, intent: str) -> Tuple[bool, str]:
    """
    Check if a model can execute a given intent.
    
    Returns (allowed, reason).
    """
    classification = classify_model(model_id)
    
    if intent == "propose":
        if classification.can_propose:
            return True, ""
        else:
            return False, f"Model {model_id} (Tier {classification.tier.value}) cannot generate proposals"
    
    if intent == "think":
        if classification.can_think:
            return True, ""
        else:
            return False, f"Model {model_id} cannot perform reasoning"
    
    if intent in ("context", "rag"):
        return True, ""
    
    return False, f"Unknown intent: {intent}"


def get_fallback_model(model_id: str) -> Optional[str]:
    """Get the fallback model for a given model."""
    classification = classify_model(model_id)
    return classification.fallback_model if classification.requires_fallback else None
