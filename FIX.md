# OpenWebUI Publishing Fix

## Problem Summary

**Error:** `unable to publish error: no such file or directory`

**Root Cause:** OpenWebUI expects a single `.py` file with an absolute path, not a Python package directory.

## What Was Wrong

### Before (Broken)

```
lathe/
  tool/
    __init__.py      # Package init that imports from wrapper
    wrapper.py       # Contains tool functions
    README.md
```

**Issue:** When attempting to publish in OpenWebUI:
- User pointed to `lathe/tool/` (a directory)
- Or used module path `lathe.tool` (not a file)
- OpenWebUI tried to open this as a file → **ENOENT error**

### Why OpenWebUI Failed

1. **OpenWebUI requires a single .py file** - Not a package, not a module path
2. **Must be an absolute file path** - Not a relative path or module name
3. **Functions must be at module level** - Not inside classes or nested imports
4. **File must be accessible** - Inside OpenWebUI's runtime environment

## What Was Fixed

### After (Fixed)

Created **`lathe_tool.py`** - A standalone, OpenWebUI-compatible tool file:

```
lathe_tool.py        # ← NEW: Single file with all functions
lathe/
  tool/
    __init__.py      # Original package (still works for Python imports)
    wrapper.py       # Original implementation
```

### Key Changes

1. **Created `lathe_tool.py`** in project root
2. **All three functions** defined at module level:
   - `lathe_plan`
   - `lathe_validate`
   - `lathe_context_preview`
3. **Direct imports** from lathe subsystems (no relative imports)
4. **OpenWebUI metadata** added (`__title__`, `__description__`, etc.)

## How to Publish in OpenWebUI

### Step 1: Locate the Tool File

**Absolute path:**
```
/tmp/cc-agent/62910883/project/lathe_tool.py
```

### Step 2: Install Lathe Package

OpenWebUI needs access to the `lathe` package for subsystem imports:

```bash
# In OpenWebUI environment (Docker or local)
pip install -e /tmp/cc-agent/62910883/project
```

### Step 3: Verify Installation

```bash
python3 -c "from lathe_tool import lathe_plan; print('OK')"
```

Expected output: `OK`

### Step 4: Publish in OpenWebUI

#### Option A: Via OpenWebUI Web Interface

1. Go to **Settings** → **Tools**
2. Click **"Add Tool"**
3. Enter tool path: `/tmp/cc-agent/62910883/project/lathe_tool.py`
4. Click **"Import"**

#### Option B: Via OpenWebUI Configuration File

Edit OpenWebUI's tools config:

```yaml
tools:
  - name: lathe
    type: python
    path: /tmp/cc-agent/62910883/project/lathe_tool.py
    description: "AI coding control layer"
```

#### Option C: Copy to OpenWebUI Tools Directory

If OpenWebUI is running in Docker:

```bash
# Copy tool file into container
docker cp /tmp/cc-agent/62910883/project/lathe_tool.py \
  openwebui:/app/backend/tools/lathe_tool.py

# Also install lathe package in container
docker exec openwebui pip install -e /tmp/cc-agent/62910883/project
```

Then in OpenWebUI, use path: `/app/backend/tools/lathe_tool.py`

## Verification Steps

### 1. Test Import in Same Environment as OpenWebUI

```bash
# SSH into OpenWebUI container (if Docker)
docker exec -it openwebui bash

# Or if local, activate same Python environment
source /path/to/openwebui/venv/bin/activate

# Test import
python3 -c "
from lathe_tool import lathe_plan, lathe_validate, lathe_context_preview
print('✓ All functions imported')
"
```

### 2. Test Function Execution

```bash
python3 -c "
from lathe_tool import lathe_plan
result = lathe_plan(
    project='test',
    scope='module',
    phase='analysis',
    goal='Test goal'
)
print('✓ Status:', 'READY' if result.get('ready') else 'FAILED')
print('✓ Phase:', result.get('phase'))
"
```

Expected output:
```
✓ All functions imported
✓ Status: READY
✓ Phase: analysis
```

### 3. Test in OpenWebUI

Once published, test in OpenWebUI chat:

```
User: Call lathe_plan with project="myapp", scope="auth", phase="design", goal="Design login system"
```

OpenWebUI should successfully call the tool and return results.

## Container Visibility (Docker)

If OpenWebUI runs in Docker, ensure the tool file is accessible:

### Option 1: Volume Mount

Add to `docker-compose.yml`:

```yaml
services:
  openwebui:
    volumes:
      - /tmp/cc-agent/62910883/project:/workspace/lathe:ro
```

Then use path: `/workspace/lathe/lathe_tool.py`

### Option 2: Build into Image

Add to `Dockerfile`:

```dockerfile
COPY /tmp/cc-agent/62910883/project/lathe_tool.py /app/tools/lathe_tool.py
RUN pip install -e /tmp/cc-agent/62910883/project
```

Then use path: `/app/tools/lathe_tool.py`

### Option 3: Copy at Runtime

```bash
docker cp /tmp/cc-agent/62910883/project/lathe_tool.py \
  openwebui:/app/tools/lathe_tool.py

docker exec openwebui pip install -e /tmp/cc-agent/62910883/project
```

## Common Issues & Solutions

### Issue 1: "No module named 'lathe'"

**Cause:** Lathe package not installed in OpenWebUI environment

**Solution:**
```bash
pip install -e /tmp/cc-agent/62910883/project
```

### Issue 2: "Permission denied"

**Cause:** File permissions incorrect

**Solution:**
```bash
chmod 644 /tmp/cc-agent/62910883/project/lathe_tool.py
```

### Issue 3: "Invalid Python file"

**Cause:** Wrong path or file format

**Solution:**
- Verify path is absolute: `/tmp/cc-agent/62910883/project/lathe_tool.py`
- Verify file ends with `.py`
- Verify file contains valid Python code

### Issue 4: "Functions not found"

**Cause:** Functions not at module level

**Solution:**
- Verify functions are defined at top level (not inside classes)
- Check with: `python3 -c "import lathe_tool; print(dir(lathe_tool))"`

## Path Reference

### Correct Paths to Use in OpenWebUI

**Local installation:**
```
/tmp/cc-agent/62910883/project/lathe_tool.py
```

**Docker with volume mount:**
```
/workspace/lathe/lathe_tool.py
```

**Docker with copy:**
```
/app/tools/lathe_tool.py
```

### INCORRECT Paths (Will Fail)

❌ `lathe.tool` - Module path, not file path
❌ `lathe/tool/` - Directory, not file
❌ `lathe/tool/__init__.py` - Package init, not tool file
❌ `./lathe_tool.py` - Relative path, needs absolute
❌ `lathe_tool` - Missing .py extension

## Summary

### What Changed
- ✅ Created single-file tool: `lathe_tool.py`
- ✅ All functions at module level
- ✅ Direct imports from lathe subsystems
- ✅ OpenWebUI metadata included

### What Didn't Change
- ✅ Original `lathe/tool/` package still works for Python imports
- ✅ No subsystem code modified
- ✅ All tests still pass
- ✅ API remains identical

### How to Publish
1. Install lathe package: `pip install -e /tmp/cc-agent/62910883/project`
2. Use absolute path: `/tmp/cc-agent/62910883/project/lathe_tool.py`
3. Verify in OpenWebUI environment before publishing

### Success Criteria
- ✅ No "file not found" errors
- ✅ Tool appears in OpenWebUI tools list
- ✅ Functions callable from chat
- ✅ Returns JSON-formatted responses

## Next Steps

1. **Verify installation:**
   ```bash
   python3 -c "from lathe_tool import lathe_plan; print('OK')"
   ```

2. **Publish in OpenWebUI** using absolute path

3. **Test in chat:**
   ```
   Call lathe_plan with project="test", scope="module", phase="analysis", goal="test"
   ```

4. **Check logs** if issues persist:
   ```bash
   docker logs openwebui | grep lathe
   ```

## File Location Map

```
Project Root: /tmp/cc-agent/62910883/project/

NEW FILES:
  lathe_tool.py              ← Use this for OpenWebUI

EXISTING FILES (unchanged):
  lathe/
    tool/
      __init__.py            ← Python package import
      wrapper.py             ← Implementation
      README.md              ← Documentation
```

## Complete Tool Path

**Copy this exact path for OpenWebUI:**

```
/tmp/cc-agent/62910883/project/lathe_tool.py
```
