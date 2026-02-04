"""
OpenWebUI ↔ Lathe Agent Contract

Single source of truth for the payload and response schema.
Zero runtime impact - used for validation and documentation in code.
"""

VALID_INTENTS = ("propose", "think", "context", "rag")

WHY_REQUIRED_KEYS = (
    "goal",
    "context", 
    "evidence",
    "decision",
    "risk_level",
    "options_considered",
    "guardrails",
    "verification_steps",
)

REQUEST_SCHEMA = {
    "intent": {"type": str, "required": True, "enum": VALID_INTENTS},
    "task": {"type": str, "required": True},
    "why": {"type": dict, "required": True, "keys": WHY_REQUIRED_KEYS},
}

RESPONSE_SCHEMA_SUCCESS = {
    "results": {"type": list, "required": True, "description": "Always present, may be empty"},
}

RESPONSE_SCHEMA_REFUSAL = {
    "refusal": {"type": bool, "required": True, "value": True},
    "reason": {"type": str, "required": True},
    "details": {"type": str, "required": True},
    "results": {"type": list, "required": True, "value": []},
}


def validate_request(payload: dict) -> tuple[bool, str]:
    """Validate an incoming request payload. Returns (valid, error_message)."""
    if not isinstance(payload, dict):
        return False, "Payload must be a JSON object"
    
    for field in ("intent", "task", "why"):
        if field not in payload:
            return False, f"Missing required field: {field}"
    
    if payload["intent"] not in VALID_INTENTS:
        return False, f"Invalid intent: {payload['intent']}"
    
    if not isinstance(payload["task"], str):
        return False, "Field 'task' must be a string"
    
    why = payload.get("why")
    if not isinstance(why, dict):
        return False, "Field 'why' must be an object"
    
    for key in WHY_REQUIRED_KEYS:
        if key not in why:
            return False, f"Missing required 'why' field: {key}"
    
    return True, ""


def is_refusal(response: dict) -> bool:
    """Check if a response is a structured refusal."""
    return response.get("refusal") is True


def example_request() -> dict:
    """Return a minimal valid request payload."""
    return {
        "intent": "propose",
        "task": "add input validation to user registration",
        "why": {
            "goal": "Prevent invalid user data",
            "context": "Registration accepts any input",
            "evidence": "Bug report #123",
            "decision": "Add server-side validation",
            "risk_level": "Low",
            "options_considered": ["Client-side only", "Server-side"],
            "guardrails": ["Only modify lathe/**", "No breaking changes"],
            "verification_steps": ["Run tests", "Manual test registration"],
        }
    }


def example_success_response() -> dict:
    """Return an example success response shape."""
    return {
        "proposals": [],
        "assumptions": [],
        "risks": [],
        "results": [],
    }


def example_refusal_response() -> dict:
    """Return an example refusal response shape."""
    return {
        "refusal": True,
        "reason": "Target file outside allowed paths",
        "details": "Attempted to modify docs/README.md",
        "results": [],
    }
