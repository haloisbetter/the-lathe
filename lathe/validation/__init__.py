"""
lathe-validation: Validate AI outputs against Lathe rules.

This subsystem provides:
- Validation rule definitions
- Rule evaluation engine
- Structured validation results
- Support for multiple severity levels (pass, warn, fail)

DOES NOT provide:
- Code execution or parsing
- Persistence or caching
- Orchestration logic
- UI or reporting
"""

from lathe.validation.engine import ValidationEngine
from lathe.validation.rules import ValidationRule as BaseValidationRule

__all__ = [
    "ValidationEngine",
    "BaseValidationRule",
]
