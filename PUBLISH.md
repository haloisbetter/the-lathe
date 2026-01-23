# Publishing The Lathe in OpenWebUI

## Overview

**The Lathe** is a phase-locked AI development control layer that enforces disciplined workflow through 4 development phases: Analysis → Design → Implementation → Validation.

The tool is published as a **single standalone Python file** (`lathe_tool.py`) that can be deployed anywhere.

---

## Installation

### 1. Install The Lathe Package

```bash
# Clone or download the repository
cd the-lathe

# Install in development mode (editable)
pip install -e .

# Or install from wheel/source
pip install .
```

**Verify installation:**
```bash
python3 -c "from lathe_tool import lathe_plan, lathe_validate; print('✓ Lathe installed')"
```

### 2. Locate lathe_tool.py

After installation, `lathe_tool.py` is at:

**Option A: Repository Root** (recommended for development)
```
/path/to/the-lathe/lathe_tool.py
```

**Option B: After pip install** (system-wide)
```bash
# Find the exact path
python3 -c "import site; print(site.getsitepackages()[0])"
# Result: /usr/local/lib/python3.11/site-packages/

# The file is in:
# /usr/local/lib/python3.11/site-packages/the-lathe/lathe_tool.py
```

**Option C: Permanent Installation Path**
```
/opt/lathe/lathe_tool.py    # Linux/Mac (requires setup)
~/lathe/lathe_tool.py        # User home directory
```

---

## Publishing in OpenWebUI

### Prerequisites

1. **OpenWebUI running** (local or remote)
2. **Python 3.11+** installed and in PATH
3. **The Lathe installed**: `pip install -e /path/to/the-lathe`

### Step 1: Get lathe_tool.py Path

**Find the absolute path:**
```bash
python3 -c "import os; print(os.path.abspath('lathe_tool.py'))"
```

**Example output:**
```
/home/user/the-lathe/lathe_tool.py
```

### Step 2: Open OpenWebUI Admin Panel

1. Navigate to: `http://localhost:8081` (or your OpenWebUI URL)
2. Log in with admin credentials
3. Go to **Admin Panel** → **Tools**
4. Click **Add New Tool** or **Import Tool**

### Step 3: Add Custom Tool

**Select:** `Custom Python Tool`

**Enter:**
- **Tool Name:** `lathe` (or `Lathe`)
- **Tool Path:** `/home/user/the-lathe/lathe_tool.py`
- **Tool ID:** `lathe` (lowercase)

**Configuration:**
```yaml
name: lathe
type: python
path: /home/user/the-lathe/lathe_tool.py
functions:
  - lathe_plan
  - lathe_validate
  - lathe_context_preview
```

### Step 4: Configure Tool Functions

OpenWebUI will automatically detect:
- `lathe_plan(project, scope, phase, goal, constraints=None, sources=None)`
- `lathe_validate(phase, output, ruleset=None)`
- `lathe_context_preview(project, scope, max_tokens=8000, source_types=None)`

**Enable all functions** (default: all enabled)

### Step 5: Verify Installation

1. **In OpenWebUI**, use the tool in a conversation:
   ```
   @lathe plan: project=myapp scope=auth phase=analysis goal=discover_auth_needs
   ```

2. **Expected response:**
   ```json
   {
     "phase": "analysis",
     "system_prompt": "You are operating in ANALYSIS phase...",
     "rules": ["no_code_output", "explicit_assumptions", ...],
     "can_proceed": true,
     "ready": true
   }
   ```

---

## System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.11 | 3.12+ |
| RAM | 256 MB | 512 MB |
| Disk | 10 MB | 50 MB |
| Network | None | None (stateless) |

---

## File Locations Reference

### Standard Locations

**Linux/Mac:**
```
/home/user/the-lathe/lathe_tool.py
/opt/lathe/lathe_tool.py
~/.local/lib/python3.11/site-packages/lathe/tool/wrapper.py (internal)
```

**Windows:**
```
C:\Users\User\the-lathe\lathe_tool.py
C:\Python311\Lib\site-packages\lathe\tool\wrapper.py (internal)
```

### After Installation

```
pip show the-lathe
# Shows:
# Location: /usr/local/lib/python3.11/site-packages
#
# Tool file at:
# /usr/local/lib/python3.11/site-packages/../the-lathe/lathe_tool.py
```

---

## Verification Commands

### 1. Verify Package Installation

```bash
python3 -c "import lathe; print(f'✓ Lathe {lathe.__version__ if hasattr(lathe, \"__version__\") else \"installed\"}')"
```

### 2. Verify Tool File Exists

```bash
python3 -c "import os; path=os.path.abspath('lathe_tool.py'); print(f'✓ Tool at: {path}' if os.path.exists(path) else '✗ Tool not found')"
```

### 3. Verify All Functions Export

```bash
python3 << 'EOF'
from lathe_tool import lathe_plan, lathe_validate, lathe_context_preview
print("✓ lathe_plan")
print("✓ lathe_validate")
print("✓ lathe_context_preview")
print("\n✓ All functions available for OpenWebUI")
EOF
```

### 4. Test Tool Directly

```bash
python3 << 'EOF'
from lathe_tool import lathe_plan

result = lathe_plan(
    project="test",
    scope="demo",
    phase="analysis",
    goal="Test Lathe installation"
)

if result.get("phase") == "analysis":
    print("✓ Lathe tool working correctly")
    print(f"✓ Phase: {result['phase']}")
    print(f"✓ Rules loaded: {len(result['rules'])} rules")
else:
    print("✗ Tool returned unexpected result")
    print(result)
EOF
```

### 5. Full Verification Script

**Save as `verify_lathe.py`:**

```python
#!/usr/bin/env python3
"""Verify Lathe is properly installed and ready for OpenWebUI."""

import sys
import os

def verify_installation():
    print("Verifying Lathe Installation")
    print("=" * 50)

    # Check 1: Package import
    try:
        import lathe
        print("✓ Package 'lathe' imports successfully")
    except ImportError as e:
        print(f"✗ Package import failed: {e}")
        return False

    # Check 2: Tool functions
    try:
        from lathe_tool import lathe_plan, lathe_validate, lathe_context_preview
        print("✓ All tool functions available")
    except ImportError as e:
        print(f"✗ Tool functions not available: {e}")
        return False

    # Check 3: Tool file
    try:
        tool_path = os.path.abspath("lathe_tool.py")
        if os.path.exists(tool_path):
            print(f"✓ Tool file exists: {tool_path}")
        else:
            print(f"✗ Tool file not found at {tool_path}")
            return False
    except Exception as e:
        print(f"✗ Tool file check failed: {e}")
        return False

    # Check 4: Basic functionality
    try:
        result = lathe_plan(
            project="verify",
            scope="test",
            phase="analysis",
            goal="Verify installation"
        )
        if result.get("phase") == "analysis":
            print("✓ Tool functions work correctly")
        else:
            print("✗ Tool functions returned unexpected result")
            return False
    except Exception as e:
        print(f"✗ Tool function test failed: {e}")
        return False

    # Check 5: Validation rules
    try:
        result = lathe_validate(
            phase="validation",
            output="VALIDATION TEST\n- [ ] Test case\nRollback: revert code"
        )
        if result.get("status"):
            print(f"✓ Validation working (status: {result['status']})")
        else:
            print("✗ Validation returned unexpected result")
            return False
    except Exception as e:
        print(f"✗ Validation test failed: {e}")
        return False

    print("\n" + "=" * 50)
    print("✅ All checks passed! Lathe is ready for OpenWebUI.")
    print("\nNext step: Configure in OpenWebUI Admin Panel")
    print(f"Tool path: {os.path.abspath('lathe_tool.py')}")
    return True

if __name__ == "__main__":
    success = verify_installation()
    sys.exit(0 if success else 1)
```

**Run verification:**
```bash
python3 verify_lathe.py
```

---

## Troubleshooting

### Problem: "lathe_tool not found"

**Solution:**
```bash
# Make sure you're in the project directory
cd /path/to/the-lathe

# Install the package
pip install -e .

# Verify
python3 -c "from lathe_tool import lathe_plan; print('OK')"
```

### Problem: "ImportError: No module named 'lathe'"

**Solution:**
```bash
# Reinstall with dependencies
pip install -e . --force-reinstall

# Or install with dev dependencies
pip install -e ".[dev]"
```

### Problem: "OpenWebUI can't find the tool file"

**Solution:**
1. Use **absolute path** (not relative):
   ```
   /home/user/the-lathe/lathe_tool.py    ✓ Correct
   ./lathe_tool.py                        ✗ Wrong
   ~/the-lathe/lathe_tool.py              ✗ Tilde may not expand
   ```

2. Check file permissions:
   ```bash
   ls -l /path/to/lathe_tool.py
   chmod 644 /path/to/lathe_tool.py
   ```

3. Verify Python can run it:
   ```bash
   python3 /path/to/lathe_tool.py
   ```

### Problem: "Tool returns blank results"

**Solution:**
```bash
# Test the tool directly
python3 << 'EOF'
from lathe_tool import lathe_plan
import json

result = lathe_plan(
    project="test",
    scope="demo",
    phase="analysis",
    goal="Test"
)
print(json.dumps(result, indent=2))
EOF
```

If empty or error, check:
1. Python version: `python3 --version` (need 3.11+)
2. Package installed: `pip show the-lathe`
3. Module imports: `python3 -c "from lathe.prompts import PromptRegistry"`

---

## Advanced: Manual Setup (Without Package)

If you need to use `lathe_tool.py` without installing the package:

### 1. Copy lathe_tool.py

```bash
cp /path/to/the-lathe/lathe_tool.py /opt/lathe/lathe_tool.py
```

### 2. Set Python Path

In OpenWebUI environment setup:
```bash
export PYTHONPATH="/path/to/the-lathe:$PYTHONPATH"
```

### 3. Use Absolute Path in OpenWebUI

```
/opt/lathe/lathe_tool.py
```

### 4. Verify

```bash
PYTHONPATH="/path/to/the-lathe" python3 /opt/lathe/lathe_tool.py
```

---

## OpenWebUI Tool Configuration Example

**In OpenWebUI Admin → Tools:**

```yaml
Tool Name: Lathe
Tool ID: lathe
Type: Python File
Path: /home/user/the-lathe/lathe_tool.py

Description: |
  Phase-locked AI development control layer.
  Enforces disciplined workflow through analysis, design,
  implementation, and validation phases with automatic
  rule validation and risk assessment.

Functions:
  - lathe_plan: Prepare phase-locked AI step
  - lathe_validate: Validate output against phase rules
  - lathe_context_preview: Preview context assembly

Enabled: Yes
```

---

## Security Notes

### Safe by Design

- **Stateless:** No persistent state or side effects
- **Read-only:** Does not modify files or system
- **Isolated:** Each call is independent
- **Sandboxed:** No network access or external calls
- **No secrets:** Does not require API keys or credentials

### Best Practices

1. **Use absolute paths only** (no relative or tilde paths)
2. **Keep Python updated** (3.11+)
3. **Verify package installation** before publishing
4. **Test tool locally** before OpenWebUI deployment
5. **Monitor tool execution** in OpenWebUI logs

---

## Version Information

| Component | Version | Status |
|-----------|---------|--------|
| The Lathe | 1.0.0 | Stable |
| Python | 3.11+ | Required |
| OpenWebUI | Any | Compatible |
| Phases | 4 (+ 1 planned) | Complete |

---

## Support

For issues:

1. **Verify installation:** Run `verify_lathe.py`
2. **Check logs:** OpenWebUI admin panel → Logs
3. **Test directly:** `python3 -c "from lathe_tool import lathe_plan; print(lathe_plan(...))"`
4. **Check permissions:** `ls -la /path/to/lathe_tool.py`

---

## One-Liner Publishing Commands

**For experienced users:**

```bash
# Install + verify + get path
pip install -e . && python3 verify_lathe.py && python3 -c "import os; print(f'Use in OpenWebUI: {os.path.abspath(\"lathe_tool.py\")}')"
```

---

## Summary

1. **Install:** `pip install -e .`
2. **Verify:** Run `verify_lathe.py`
3. **Get path:** `python3 -c "import os; print(os.path.abspath('lathe_tool.py'))"`
4. **Publish:** Add that path in OpenWebUI Admin → Tools
5. **Use:** Reference in conversations with `@lathe`

The Lathe is now **permanent, stable, and ready for production deployment in OpenWebUI**.
