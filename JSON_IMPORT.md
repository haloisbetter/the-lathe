# OpenWebUI JSON Import Guide: Lathe Tool

**Complete guide to importing the Lathe tool into OpenWebUI using JSON definition**

---

## Quick Start (3 Steps)

### Step 1: Install the Lathe Package

```bash
# Option A: Install from project directory
cd /tmp/cc-agent/62910883/project
pip install -e .

# Option B: Copy to stable location (production)
mkdir -p /opt/lathe
cp -r lathe /opt/lathe/
cp lathe_tool.py /opt/lathe/
export PYTHONPATH="/opt/lathe:$PYTHONPATH"
```

### Step 2: Update JSON Path (if needed)

Edit `lathe_tool.json` and update the `path` field:

```json
{
  "path": "/opt/lathe/lathe_tool.py"
}
```

**Important:** Use the absolute path where you installed the tool file.

### Step 3: Import into OpenWebUI

**Method A: Admin UI**
1. Open OpenWebUI Admin Panel: http://localhost:8080/admin
2. Navigate to: **Tools** → **Import Tool**
3. Click **Upload JSON**
4. Select `lathe_tool.json`
5. Click **Import**

**Method B: API Import**
```bash
curl -X POST http://localhost:8080/api/v1/tools/import \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d @lathe_tool.json
```

**Method C: File System (Docker)**
```bash
# If running OpenWebUI in Docker
docker cp lathe_tool.json openwebui:/app/tools/
docker exec openwebui python -c "from tools import import_tool; import_tool('lathe_tool.json')"
```

---

## Understanding the JSON Structure

### Required Fields

```json
{
  "name": "lathe",              // Tool identifier (used in @lathe)
  "version": "1.0.0",           // Tool version
  "type": "python",             // Language type
  "module": "lathe_tool",       // Python module name (without .py)
  "path": "/path/to/lathe_tool.py",  // ABSOLUTE path to tool file
  "functions": [...]            // Function definitions
}
```

### Function Definition Schema

Each function must specify:
- **name**: Function name (must match Python function)
- **description**: What the function does
- **parameters**: JSON Schema for inputs
- **returns**: JSON Schema for outputs

Example:
```json
{
  "name": "lathe_plan",
  "description": "Prepare a phase-locked AI development step",
  "parameters": {
    "type": "object",
    "properties": {
      "project": {
        "type": "string",
        "description": "Project name"
      }
    },
    "required": ["project"]
  },
  "returns": {
    "type": "object",
    "description": "Plan with system prompt and context"
  }
}
```

---

## Installation Paths

### Development (Temporary)

**Current Path:**
```
/tmp/cc-agent/62910883/project/lathe_tool.py
```

**JSON Configuration:**
```json
{
  "path": "/tmp/cc-agent/62910883/project/lathe_tool.py"
}
```

**Pros:** Works immediately
**Cons:** Lost on reboot, unsuitable for production

### Production (Recommended)

**Option 1: System-wide Install**
```bash
# Install package
pip install -e /path/to/lathe-project

# Tool file location (after install)
# Usually: /usr/local/lib/python3.x/site-packages/lathe_tool.py
# Or use absolute path: /opt/lathe/lathe_tool.py
```

**JSON Configuration:**
```json
{
  "path": "/opt/lathe/lathe_tool.py"
}
```

**Option 2: User Install**
```bash
# Install for current user
pip install --user -e /path/to/lathe-project

# Tool file location
# Usually: ~/.local/lib/python3.x/site-packages/lathe_tool.py
```

**JSON Configuration:**
```json
{
  "path": "/home/username/.local/lib/python3.x/site-packages/lathe_tool.py"
}
```

**Option 3: Docker Volume Mount**
```bash
# Mount tool directory into container
docker run -v /opt/lathe:/app/tools/lathe openwebui
```

**JSON Configuration:**
```json
{
  "path": "/app/tools/lathe/lathe_tool.py"
}
```

---

## Verification

### Pre-Import Checks

**Check 1: Tool file exists**
```bash
ls -l /path/to/lathe_tool.py
```
Expected: File exists and is readable

**Check 2: Python can import**
```bash
python3 -c "from lathe_tool import lathe_plan; print('✓ OK')"
```
Expected: No errors

**Check 3: JSON is valid**
```bash
python3 -c "import json; json.load(open('lathe_tool.json')); print('✓ Valid JSON')"
```
Expected: ✓ Valid JSON

**Check 4: Functions work**
```bash
python3 << 'EOF'
from lathe_tool import lathe_plan
result = lathe_plan(project="test", scope="demo", phase="analysis", goal="verify")
assert result.get("phase") == "analysis"
print("✓ Functions work")
EOF
```
Expected: ✓ Functions work

**Check 5: Full verification**
```bash
python3 verify_lathe.py
```
Expected: ✅ ALL CHECKS PASSED

### Post-Import Checks

**Check 1: Tool appears in OpenWebUI**
- Go to: Settings → Tools
- Look for: "Lathe" in tool list
- Status: Should be "Active" or "Enabled"

**Check 2: Test in chat**
```
@lathe lathe_plan project=myapp scope=auth phase=analysis goal=test
```
Expected: JSON response with system_prompt and context

**Check 3: Check OpenWebUI logs**
```bash
# Docker
docker logs openwebui | grep lathe

# Systemd
journalctl -u openwebui | grep lathe
```
Expected: No import errors

---

## Common Issues & Fixes

### Issue 1: "File not found"

**Symptom:**
```
Error: Cannot import tool: /path/to/lathe_tool.py not found
```

**Cause:** Path in JSON doesn't match actual file location

**Fix:**
```bash
# Find actual path
python3 -c "import os; print(os.path.abspath('lathe_tool.py'))"

# Update lathe_tool.json with this path
```

### Issue 2: "Module import failed"

**Symptom:**
```
Error: Cannot import module 'lathe_tool'
ImportError: No module named 'lathe'
```

**Cause:** Lathe package not installed or not in PYTHONPATH

**Fix:**
```bash
# Install package
pip install -e /path/to/lathe-project

# Or set PYTHONPATH
export PYTHONPATH="/path/to/lathe-project:$PYTHONPATH"

# For OpenWebUI in Docker, add to environment
docker run -e PYTHONPATH="/app/tools:$PYTHONPATH" openwebui
```

### Issue 3: "Function not found"

**Symptom:**
```
Error: Function 'lathe_plan' not found in module
```

**Cause:** Function name in JSON doesn't match Python function

**Fix:**
```bash
# Verify function names
python3 -c "from lathe_tool import *; print(dir())"

# Update JSON to match exact names
```

### Issue 4: "Invalid JSON"

**Symptom:**
```
Error: Cannot parse tool definition: Invalid JSON
```

**Cause:** Syntax error in JSON file

**Fix:**
```bash
# Validate JSON
python3 -c "import json; json.load(open('lathe_tool.json'))"

# Or use jq
jq . lathe_tool.json
```

### Issue 5: "Tool works locally but fails in OpenWebUI"

**Symptom:**
Tool imports successfully via Python but fails when called from OpenWebUI

**Cause:** Different Python environment or missing dependencies

**Fix:**
```bash
# Check OpenWebUI Python version
docker exec openwebui python3 --version

# Check installed packages
docker exec openwebui pip list | grep -i lathe

# Install dependencies in OpenWebUI environment
docker exec openwebui pip install -e /app/tools/lathe-project
```

### Issue 6: "Permission denied"

**Symptom:**
```
Error: Permission denied: /path/to/lathe_tool.py
```

**Cause:** File not readable by OpenWebUI user

**Fix:**
```bash
# Make file readable
chmod 644 /path/to/lathe_tool.py

# For directory
chmod 755 /path/to/directory
```

---

## JSON vs Direct Python Import

### JSON Import (Recommended)

**Pros:**
- ✅ Declarative: Schema visible in JSON
- ✅ Portable: Works across OpenWebUI instances
- ✅ Versioned: Tool definition can be version controlled
- ✅ Validated: OpenWebUI validates schema on import
- ✅ Documented: Parameters documented in JSON

**Cons:**
- ⚠️ Requires absolute path
- ⚠️ Must keep JSON and Python in sync

**Use when:**
- Publishing tool to multiple OpenWebUI instances
- Need explicit schema documentation
- Want version control for tool definitions

### Direct Python Import

**Pros:**
- ✅ Simple: Just point to .py file
- ✅ No JSON maintenance

**Cons:**
- ⚠️ No schema validation
- ⚠️ No parameter documentation in UI
- ⚠️ Less portable

**Use when:**
- Quick local testing
- Single OpenWebUI instance
- Don't need schema documentation

---

## Updating the Tool

### Update Python Code

```bash
# Edit lathe_tool.py
vim lathe_tool.py

# Verify changes
python3 verify_lathe.py
```

### Update JSON Definition

If you add/modify functions:

1. Update `lathe_tool.json`:
   - Add new function definition
   - Update parameter schemas
   - Increment version

2. Re-import in OpenWebUI:
   ```bash
   # Re-import updated JSON
   curl -X POST http://localhost:8080/api/v1/tools/import \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -d @lathe_tool.json
   ```

3. Restart OpenWebUI (if needed):
   ```bash
   docker restart openwebui
   ```

---

## Production Deployment Checklist

### Pre-Deployment

- [ ] Tool file installed in stable location (not /tmp)
- [ ] All dependencies installed in production environment
- [ ] JSON path updated to production path
- [ ] All verification checks pass
- [ ] Tool tested in staging environment

### Deployment

- [ ] Copy tool file to production path
- [ ] Install dependencies: `pip install -e .`
- [ ] Update JSON with production path
- [ ] Import JSON into production OpenWebUI
- [ ] Verify tool appears in tool list
- [ ] Test all 3 functions in production

### Post-Deployment

- [ ] Monitor OpenWebUI logs for errors
- [ ] Test tool in actual conversations
- [ ] Document tool usage for team
- [ ] Set up monitoring/alerts for tool failures

---

## Tool File Requirements (Reference)

For a Python file to work as an OpenWebUI tool, it must:

### 1. Be a Single .py File
- ✅ `lathe_tool.py` (single file)
- ❌ `lathe/` (package directory)

### 2. Export Functions at Top Level
```python
def lathe_plan(...): ...      # ✅ Top-level function
def lathe_validate(...): ...  # ✅ Top-level function

class Helper:                  # ❌ Not directly callable
    def method(...): ...       # ❌ Not top-level
```

### 3. Accept JSON-Serializable Parameters
```python
# ✅ Good
def func(name: str, count: int, items: List[str]) -> Dict[str, Any]:
    ...

# ❌ Bad (custom objects)
def func(config: CustomConfig) -> MyResult:
    ...
```

### 4. Return JSON-Serializable Results
```python
# ✅ Good
return {"status": "ok", "data": [1, 2, 3]}

# ❌ Bad (custom object)
return MyCustomClass(data=[1, 2, 3])
```

### 5. Not Crash on Import
```python
# ❌ Bad (runs code on import)
result = expensive_computation()

# ✅ Good (code in functions only)
def compute():
    return expensive_computation()
```

### 6. Have Module Metadata (Optional but Recommended)
```python
__version__ = "1.0.0"
__title__ = "Tool Name"
__description__ = "Tool description"
__author__ = "Author Name"
```

---

## Troubleshooting Workflow

If import fails, follow this workflow:

```
1. Verify file exists
   └─→ ls -l /path/to/lathe_tool.py
       └─→ FAIL: Fix path in JSON
       └─→ PASS: Continue

2. Verify Python can import
   └─→ python3 -c "from lathe_tool import lathe_plan"
       └─→ FAIL: Install package (pip install -e .)
       └─→ PASS: Continue

3. Verify JSON is valid
   └─→ python3 -c "import json; json.load(open('lathe_tool.json'))"
       └─→ FAIL: Fix JSON syntax
       └─→ PASS: Continue

4. Verify functions work
   └─→ python3 verify_lathe.py
       └─→ FAIL: Fix tool code
       └─→ PASS: Continue

5. Import into OpenWebUI
   └─→ Check logs for errors
       └─→ FAIL: See "Common Issues" above
       └─→ PASS: Done! ✅
```

---

## API Reference (Quick)

### lathe_plan()

**Purpose:** Prepare AI step with system prompt and context

**Usage:**
```python
from lathe_tool import lathe_plan

result = lathe_plan(
    project="myapp",
    scope="auth",
    phase="analysis",
    goal="Identify authentication requirements"
)
```

**Returns:** Dict with `phase`, `system_prompt`, `context_blocks`, `total_tokens`

### lathe_validate()

**Purpose:** Validate AI output against phase rules

**Usage:**
```python
from lathe_tool import lathe_validate

result = lathe_validate(
    phase="design",
    output="# Architecture\n\n..."
)
```

**Returns:** Dict with `status`, `violations`, `summary`, `can_proceed`

### lathe_context_preview()

**Purpose:** Preview context assembly and token estimates

**Usage:**
```python
from lathe_tool import lathe_context_preview

result = lathe_context_preview(
    query="authentication",
    sources=["knowledge", "files"]
)
```

**Returns:** Dict with `context_blocks`, `total_tokens`, `truncated`

---

## Support

### Getting Help

**Verification Issues:**
```bash
python3 verify_lathe.py
```

**Check Tool Status:**
```bash
# List all functions
python3 -c "from lathe_tool import *; print([x for x in dir() if not x.startswith('_')])"
```

**OpenWebUI Logs:**
```bash
# Docker
docker logs openwebui 2>&1 | grep -i "lathe\|error"

# System
journalctl -u openwebui -n 100 | grep -i "lathe\|error"
```

### Quick Reference

| File | Purpose |
|------|---------|
| `lathe_tool.py` | Canonical tool file (Python) |
| `lathe_tool.json` | Tool definition (OpenWebUI import) |
| `verify_lathe.py` | Verification script |
| `JSON_IMPORT.md` | This guide |
| `PUBLISH_FIX.md` | Publishing troubleshooting |

### Next Steps

1. ✅ Verify tool works: `python3 verify_lathe.py`
2. ✅ Update JSON path: Edit `lathe_tool.json`
3. ✅ Import to OpenWebUI: Admin Panel → Tools → Import
4. ✅ Test in chat: `@lathe lathe_plan ...`
5. ✅ Deploy to production: Follow checklist above

---

**Status:** Tool is JSON-import ready ✅
**Tool File:** `lathe_tool.py`
**JSON Definition:** `lathe_tool.json`
**Documentation:** Complete
