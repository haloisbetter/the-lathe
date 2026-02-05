"""
Output Contract Enforcement

Lathe treats model output as UNTRUSTED INPUT.

This module validates that model responses match EXACTLY one of:
- success schema
- refusal schema

Any deviation becomes a structured refusal.
NO exceptions. NO crashes.
"""
import json
import re
from typing import Tuple, Optional

SUCCESS_REQUIRED_KEYS = {"results"}
SUCCESS_OPTIONAL_KEYS = {"proposals", "assumptions", "risks", "proposed_plan", 
                          "evidence_references", "conceptual", "actionable",
                          "context", "lines", "path", "start_line", "end_line"}

REFUSAL_REQUIRED_KEYS = {"refusal", "reason", "details", "results"}

MODEL_FINGERPRINT_PATTERN = re.compile(r"MODEL_FINGERPRINT=([a-zA-Z0-9_\-:.]+)")


def extract_fingerprint(response: dict) -> Optional[str]:
    """Extract MODEL_FINGERPRINT from response if present."""
    fp = response.get("model_fingerprint")
    if fp:
        return str(fp)
    
    for key, value in response.items():
        if isinstance(value, str):
            match = MODEL_FINGERPRINT_PATTERN.search(value)
            if match:
                return match.group(1)
    
    return None


def is_valid_json_response(raw: str, strict: bool = True) -> Tuple[bool, Optional[dict], str]:
    """
    Check if raw response is valid JSON.
    Returns (is_valid, parsed_dict, error_message).
    
    In strict mode (default):
    - No markdown code blocks allowed
    - No prose prefix/suffix allowed
    - Must be pure JSON only
    """
    if not isinstance(raw, str):
        if isinstance(raw, dict):
            return True, raw, ""
        return False, None, "Response is not a string or dict"
    
    raw = raw.strip()
    
    if strict:
        has_forbidden, msg = contains_forbidden_content(raw)
        if has_forbidden:
            return False, None, f"Forbidden content detected: {msg}"
        
        if raw.startswith("```"):
            return False, None, "Markdown code blocks not allowed in strict mode"
        
        if not raw.startswith("{"):
            return False, None, "Response must start with JSON object (no prose prefix allowed)"
        
        if not raw.endswith("}"):
            return False, None, "Response must end with JSON object (no prose suffix allowed)"
    
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return False, None, "JSON must be an object, not array or primitive"
        return True, parsed, ""
    except json.JSONDecodeError as e:
        return False, None, f"Invalid JSON: {str(e)}"


def is_refusal_response(response: dict) -> bool:
    """Check if response matches refusal schema."""
    return response.get("refusal") is True


def validate_success_response(response: dict, require_fingerprint: bool = True) -> Tuple[bool, str]:
    """Validate response matches success schema."""
    if "results" not in response:
        return False, "Missing required key: results"
    
    if not isinstance(response.get("results"), list):
        return False, "Field 'results' must be a list"
    
    if require_fingerprint:
        fp = response.get("model_fingerprint")
        if not fp:
            return False, "Missing required model_fingerprint"
        if not isinstance(fp, str) or len(fp) < 3:
            return False, "Malformed model_fingerprint (must be string, min 3 chars)"
    
    allowed_keys = SUCCESS_REQUIRED_KEYS | SUCCESS_OPTIONAL_KEYS | {"model_fingerprint", "_normalization_applied"}
    extra_keys = set(response.keys()) - allowed_keys
    
    if extra_keys:
        return False, f"Unexpected keys in response: {extra_keys}"
    
    return True, ""


def validate_refusal_response(response: dict) -> Tuple[bool, str]:
    """Validate response matches refusal schema."""
    for key in REFUSAL_REQUIRED_KEYS:
        if key not in response:
            return False, f"Refusal missing required key: {key}"
    
    if response.get("refusal") is not True:
        return False, "Refusal field must be exactly True"
    
    if not isinstance(response.get("reason"), str):
        return False, "Refusal reason must be a string"
    
    if not isinstance(response.get("results"), list):
        return False, "Refusal results must be a list"
    
    return True, ""


def create_refusal_from_error(reason: str, details: str = "") -> dict:
    """Create a structured refusal response from an error condition."""
    return {
        "refusal": True,
        "reason": reason,
        "details": details,
        "results": [],
    }


def validate_and_normalize_output(
    raw_response, 
    source_model: str = "unknown",
    require_fingerprint: bool = True,
    strict_json: bool = True,
) -> dict:
    """
    Validate model output and normalize to contract.
    
    If validation fails, returns a structured refusal.
    NEVER crashes. NEVER returns invalid data.
    
    Args:
        raw_response: Raw model output
        source_model: Model identifier for logging
        require_fingerprint: If True, missing fingerprint = validation failure
        strict_json: If True, no prose/markdown allowed around JSON
    """
    is_valid, parsed, error = is_valid_json_response(raw_response, strict=strict_json)
    
    if not is_valid or parsed is None:
        return create_refusal_from_error(
            reason="Model output validation failed",
            details=f"Source: {source_model}. Error: {error}"
        )
    
    fingerprint = extract_fingerprint(parsed)
    
    if is_refusal_response(parsed):
        valid, err = validate_refusal_response(parsed)
        if valid:
            return parsed
        else:
            return create_refusal_from_error(
                reason="Malformed refusal from model",
                details=f"Source: {source_model}. Error: {err}"
            )
    
    valid, err = validate_success_response(parsed, require_fingerprint=require_fingerprint)
    if valid:
        if "results" not in parsed:
            parsed["results"] = []
        return parsed
    else:
        return create_refusal_from_error(
            reason="Model output does not match success schema",
            details=f"Source: {source_model}. Error: {err}"
        )


def contains_forbidden_content(raw: str) -> Tuple[bool, str]:
    """Check if response contains forbidden patterns."""
    if not isinstance(raw, str):
        return False, ""
    
    forbidden_patterns = [
        (r"<html", "HTML content detected"),
        (r"<script", "Script tag detected"),
        (r"Traceback \(most recent", "Python traceback detected"),
        (r"^\s*def\s+\w+\s*\(", "Raw function definition detected"),
        (r"^\s*class\s+\w+", "Raw class definition detected"),
    ]
    
    for pattern, message in forbidden_patterns:
        if re.search(pattern, raw, re.IGNORECASE | re.MULTILINE):
            return True, message
    
    return False, ""
