# Verification Tests

Lightweight test suite for verifying Lathe subsystem architecture and interfaces.

## Quick Start

```bash
python3 tests/verify_subsystems.py
```

## What Gets Tested

### Import Independence
- Each subsystem can be imported independently
- No cross-subsystem imports
- Shared models can be imported

### Interface Verification
- PromptRegistry methods exist
- ContextBuilder methods exist
- ValidationEngine methods exist

### Functional Tests
- Prompts can be registered and retrieved
- Context can be assembled from sources
- Validation can be run and returns results

### Architecture Compliance
- No imports of `lathe.context` in prompts/
- No imports of `lathe.prompts` in context/
- No imports of `lathe.validation` anywhere inappropriately
- No database/file I/O imports

### Statelessness
- PromptRegistry instances are independent
- ContextBuilder produces different outputs for different inputs
- No caching or global state

### Enums and Models
- All required enums exist
- All required data models exist
- All extension features work (pipeline, rules, etc.)

## Test Results

All tests should pass with output like:

```
IMPORT TESTS
------------------------------------------------------------
✓ Import prompts subsystem
✓ Import context subsystem
✓ Import validation subsystem
✓ Import shared models
✓ Import shared enums

... (more tests) ...

============================================================
VERIFICATION SUMMARY
============================================================
Passed: 22
Failed: 0
Total:  22
============================================================
```

## Files

- `verify_subsystems.py` - Main verification script (no external dependencies, works with stdlib only)
- `test_subsystem_verification.py` - Pytest-compatible tests (optional, requires pytest)

## Running with pytest

If pytest is available:

```bash
python3 -m pytest tests/test_subsystem_verification.py -v
```

## Architecture Validated

```
prompts/          context/          validation/
  │                 │                  │
  └─────────────────┴──────────────────┘
                     │
                 shared/
```

Verification confirms:
- ✓ No direct imports between subsystems
- ✓ All communication via shared/ models
- ✓ Stateless operation
- ✓ Clean interfaces
- ✓ Proper data contracts

## Troubleshooting

If tests fail, check:

1. **Python version** - Requires Python 3.6+
2. **Module path** - Run from project root
3. **Working directory** - Should be project root

## Test Details

See `VERIFICATION.md` in project root for detailed test results and compliance matrix.
