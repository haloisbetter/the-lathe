"""
Prompt Normalization Layer

Converts ANY incoming user prompt (raw, messy, verbose, malformed)
into a canonical internal structure BEFORE it reaches any model.

This layer is:
- Deterministic
- Stateless
- Independent of model behavior
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union
from lathe.openwebui_contract import VALID_INTENTS, WHY_REQUIRED_KEYS


@dataclass
class NormalizedRequest:
    """Canonical internal structure for all requests."""
    intent: str
    task: str
    why: dict
    constraints: List[str] = field(default_factory=list)
    response_contract: str = "standard"
    raw_input: Optional[str] = None
    normalization_applied: List[str] = field(default_factory=list)


def extract_intent(raw: str) -> Tuple[str, List[str]]:
    """Extract intent from raw input. Returns (intent, normalizations_applied)."""
    normalizations = []
    lower = raw.lower().strip()
    
    if any(kw in lower for kw in ["propose", "patch", "change", "modify", "edit", "fix", "add"]):
        normalizations.append("intent_inferred_from_keywords:propose")
        return "propose", normalizations
    elif any(kw in lower for kw in ["think", "reason", "explain", "analyze", "understand"]):
        normalizations.append("intent_inferred_from_keywords:think")
        return "think", normalizations
    elif any(kw in lower for kw in ["context", "show", "read", "view", "lines"]):
        normalizations.append("intent_inferred_from_keywords:context")
        return "context", normalizations
    elif any(kw in lower for kw in ["search", "find", "rag", "look"]):
        normalizations.append("intent_inferred_from_keywords:rag")
        return "rag", normalizations
    
    normalizations.append("intent_defaulted_to_think")
    return "think", normalizations


def extract_constraints(why: dict, task: str) -> List[str]:
    """Derive implicit constraints from why and task."""
    constraints = []
    
    guardrails = why.get("guardrails", [])
    if isinstance(guardrails, list):
        constraints.extend(guardrails)
    
    risk = why.get("risk_level", "").lower()
    if risk in ("high", "critical"):
        constraints.append("HIGH_RISK_REQUIRES_CONFIRMATION")
    
    if "test" in task.lower():
        constraints.append("TEST_MODIFICATION_ALLOWED")
    
    if any(kw in task.lower() for kw in ["delete", "remove", "drop"]):
        constraints.append("DESTRUCTIVE_OPERATION")
    
    return constraints


def build_default_why(task: str) -> dict:
    """Build a minimal valid WHY object for missing/incomplete inputs."""
    return {
        "goal": f"Complete task: {task[:100]}",
        "context": "No context provided",
        "evidence": "None",
        "decision": "Proceed with caution",
        "risk_level": "Unknown",
        "options_considered": ["Default approach"],
        "guardrails": ["Standard safety checks"],
        "verification_steps": ["Manual review required"],
    }


def normalize_why(why_input) -> Tuple[dict, List[str]]:
    """Normalize a WHY object, filling in missing fields. Returns (why, normalizations)."""
    normalizations = []
    
    if why_input is None:
        normalizations.append("why_object_missing_created_default")
        return build_default_why("unknown task"), normalizations
    
    if not isinstance(why_input, dict):
        normalizations.append("why_object_invalid_type_created_default")
        return build_default_why("unknown task"), normalizations
    
    why = dict(why_input)
    
    for key in WHY_REQUIRED_KEYS:
        if key not in why or why[key] is None:
            normalizations.append(f"why_field_missing:{key}")
            if key == "options_considered":
                why[key] = ["Default option"]
            elif key == "guardrails":
                why[key] = ["Standard safety"]
            elif key == "verification_steps":
                why[key] = ["Manual review"]
            else:
                why[key] = "Not provided"
    
    return why, normalizations


def normalize_request(payload: dict) -> Tuple[Optional[NormalizedRequest], bool, str]:
    """
    Normalize an incoming request to canonical form.
    
    Returns:
        (NormalizedRequest or None, is_valid, error_message)
    
    The model must NEVER see raw user input.
    Only normalized, structured input is allowed downstream.
    """
    normalizations = []
    
    if not isinstance(payload, dict):
        return None, False, "Payload must be a JSON object"
    
    intent = payload.get("intent")
    task = payload.get("task", "")
    why = payload.get("why")
    
    if not intent:
        if task:
            intent, intent_norms = extract_intent(task)
            normalizations.extend(intent_norms)
        else:
            return None, False, "Missing required field: intent or task"
    elif intent not in VALID_INTENTS:
        return None, False, f"Invalid intent: {intent}"
    
    if not task:
        return None, False, "Missing required field: task"
    
    if not isinstance(task, str):
        task = str(task)
        normalizations.append("task_coerced_to_string")
    
    task = task.strip()
    if len(task) > 2000:
        task = task[:2000]
        normalizations.append("task_truncated_to_2000_chars")
    
    why, why_norms = normalize_why(why)
    normalizations.extend(why_norms)
    
    constraints = extract_constraints(why, task)
    
    normalized = NormalizedRequest(
        intent=intent,
        task=task,
        why=why,
        constraints=constraints,
        response_contract="standard",
        raw_input=None,
        normalization_applied=normalizations,
    )
    
    return normalized, True, ""


def to_canonical_dict(normalized: NormalizedRequest) -> dict:
    """Convert NormalizedRequest to dict for downstream processing."""
    return {
        "intent": normalized.intent,
        "task": normalized.task,
        "why": normalized.why,
        "constraints": normalized.constraints,
        "response_contract": normalized.response_contract,
        "_normalization_applied": normalized.normalization_applied,
    }
