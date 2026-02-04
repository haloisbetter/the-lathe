import json

def get_why_schema():
    return {
        "goal": str,
        "context": str,
        "evidence": str,
        "options_considered": list,
        "decision": str,
        "risk_level": str,
        "guardrails": list,
        "verification_steps": list
    }

def validate_why_record(record):
    schema = get_why_schema()
    for field, field_type in schema.items():
        if field not in record:
            raise ValueError(f"Missing required field: {field}")
        if not isinstance(record[field], field_type):
            raise TypeError(f"Field {field} must be of type {field_type.__name__}")
    return True

def get_why_example():
    example = {
        "goal": "Normalize CLI structure",
        "context": "The project needs a stable CLI for future tool integration.",
        "evidence": "Existing main.py uses manual sys.argv parsing which is fragile.",
        "options_considered": ["Manual parsing", "Argparse", "Click"],
        "decision": "Use Argparse for zero-dependency standard library compliance.",
        "risk_level": "Low",
        "guardrails": ["Maintain existing command compatibility"],
        "verification_steps": ["Run all tests", "Manually verify each CLI command"]
    }
    return json.dumps(example, indent=2)
