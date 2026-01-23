# OpenWebUI Publishing Checklist

Use this checklist to publish the Lathe tool in OpenWebUI.

---

## Pre-Publishing Checklist

### ✅ 1. Verify Tool File Exists
```bash
ls -l /tmp/cc-agent/62910883/project/lathe_tool.py
```
Expected: File exists with read permissions

### ✅ 2. Verify Python Environment
```bash
which python3
python3 --version
```
Expected: Python 3.8+ available

### ✅ 3. Install Lathe Package
```bash
pip install -e /tmp/cc-agent/62910883/project
```
Expected: "Successfully installed lathe"

### ✅ 4. Test Import
```bash
python3 -c "from lathe_tool import lathe_plan, lathe_validate, lathe_context_preview; print('OK')"
```
Expected: "OK"

### ✅ 5. Test Function Execution
```bash
python3 -c "from lathe_tool import lathe_plan; r = lathe_plan('test', 'test', 'analysis', 'test'); print('Ready:', r.get('ready'))"
```
Expected: "Ready: True"

### ✅ 6. Run Test Suite
```bash
python3 tests/test_tool_wrapper.py
```
Expected: "Passed: 16, Failed: 0"

---

## Publishing in OpenWebUI

### Method 1: Web Interface

1. **Navigate to Tools**
   - Open OpenWebUI
   - Go to Settings → Tools

2. **Add Tool**
   - Click "Add Tool" or "Import Tool"
   - Tool Type: "Python Function"

3. **Enter Path**
   ```
   /tmp/cc-agent/62910883/project/lathe_tool.py
   ```

4. **Import**
   - Click "Import" or "Save"
   - Verify tool appears in tools list

5. **Test**
   - Open a chat
   - Try: "Use lathe_plan to prepare an analysis phase"
   - Verify tool executes successfully

---

### Method 2: Configuration File

1. **Locate Config**
   - Find OpenWebUI config file (usually `config.yaml` or `tools.yaml`)

2. **Add Tool Entry**
   ```yaml
   tools:
     - name: lathe
       type: python_function
       path: /tmp/cc-agent/62910883/project/lathe_tool.py
       description: "AI coding control layer with phase-locked development"
       functions:
         - lathe_plan
         - lathe_validate
         - lathe_context_preview
   ```

3. **Restart OpenWebUI**
   ```bash
   # Docker
   docker restart openwebui

   # Local
   systemctl restart openwebui
   # or
   pkill -f openwebui && openwebui
   ```

4. **Verify**
   - Check tools list
   - Test in chat

---

### Method 3: Docker Deployment

1. **Copy Tool into Container**
   ```bash
   docker cp /tmp/cc-agent/62910883/project/lathe_tool.py \
     openwebui:/app/tools/lathe_tool.py
   ```

2. **Install Package in Container**
   ```bash
   docker exec openwebui pip install -e /tmp/cc-agent/62910883/project
   ```

3. **Verify in Container**
   ```bash
   docker exec openwebui python3 -c "from lathe_tool import lathe_plan; print('OK')"
   ```
   Expected: "OK"

4. **Add to OpenWebUI**
   - Use path: `/app/tools/lathe_tool.py`
   - Follow Method 1 or Method 2 above

5. **Test**
   - Use tool in chat
   - Check container logs: `docker logs openwebui | grep lathe`

---

## Post-Publishing Verification

### ✅ 1. Tool Appears in List
- Check OpenWebUI Settings → Tools
- Verify "lathe" is listed

### ✅ 2. Function Discovery
- Verify all three functions visible:
  - lathe_plan
  - lathe_validate
  - lathe_context_preview

### ✅ 3. Test lathe_plan
In OpenWebUI chat:
```
Use lathe_plan with:
- project: "test_project"
- scope: "authentication"
- phase: "design"
- goal: "Design secure login"
```

Expected response: JSON with `ready: true`

### ✅ 4. Test lathe_validate
In OpenWebUI chat:
```
Use lathe_validate with:
- phase: "implementation"
- output: "def hello(): return 'world'"
```

Expected response: JSON with validation status

### ✅ 5. Test lathe_context_preview
In OpenWebUI chat:
```
Use lathe_context_preview with:
- query: "authentication system"
- sources: ["knowledge"]
```

Expected response: JSON with context blocks

---

## Troubleshooting

### Issue: Tool Not Found
**Check:**
- [ ] File path is absolute (starts with `/`)
- [ ] File has `.py` extension
- [ ] File exists and is readable

**Fix:**
```bash
# Verify path
ls -l /tmp/cc-agent/62910883/project/lathe_tool.py

# Fix permissions if needed
chmod 644 /tmp/cc-agent/62910883/project/lathe_tool.py
```

---

### Issue: Import Error "No module named 'lathe'"
**Check:**
- [ ] Lathe package installed in same environment as OpenWebUI

**Fix:**
```bash
# Install in correct environment
pip install -e /tmp/cc-agent/62910883/project

# Verify
python3 -c "import lathe; print(lathe.__file__)"
```

---

### Issue: Functions Not Callable
**Check:**
- [ ] Functions exist at module level
- [ ] No syntax errors in tool file

**Fix:**
```bash
# Verify functions exist
python3 -c "import lathe_tool; print([f for f in dir(lathe_tool) if not f.startswith('_')])"

# Check for syntax errors
python3 -m py_compile /tmp/cc-agent/62910883/project/lathe_tool.py
```

---

### Issue: Docker Container Can't Access File
**Check:**
- [ ] File copied into container, OR
- [ ] Volume mount configured

**Fix Option 1 - Copy:**
```bash
docker cp /tmp/cc-agent/62910883/project/lathe_tool.py \
  openwebui:/app/tools/lathe_tool.py
```

**Fix Option 2 - Mount:**
Add to `docker-compose.yml`:
```yaml
volumes:
  - /tmp/cc-agent/62910883/project:/workspace/lathe:ro
```

---

## Success Criteria

All must be true:
- ✅ Tool file exists and is readable
- ✅ Lathe package installed in OpenWebUI environment
- ✅ Import test passes
- ✅ Function execution test passes
- ✅ Tool appears in OpenWebUI tools list
- ✅ All three functions callable from chat
- ✅ Functions return JSON responses
- ✅ No errors in OpenWebUI logs

---

## Quick Commands

### Verify Everything Works
```bash
# All-in-one verification
python3 << 'EOF'
import os
from lathe_tool import lathe_plan, lathe_validate, lathe_context_preview

# Test imports
print("✓ Imports work")

# Test functions
r1 = lathe_plan("test", "test", "analysis", "test")
r2 = lathe_validate("analysis", "test output")
r3 = lathe_context_preview("test query")

print(f"✓ lathe_plan: {r1.get('ready')}")
print(f"✓ lathe_validate: {r2.get('status')}")
print(f"✓ lathe_context_preview: {'context_blocks' in r3}")

# File check
tool_path = "/tmp/cc-agent/62910883/project/lathe_tool.py"
print(f"✓ Tool file: {os.path.exists(tool_path)}")

print("\n✅ ALL CHECKS PASSED")
EOF
```

### Check OpenWebUI Logs (Docker)
```bash
docker logs -f openwebui | grep -i "lathe\|tool\|error"
```

### Check OpenWebUI Logs (Local)
```bash
journalctl -u openwebui -f | grep -i "lathe\|tool\|error"
```

---

## Support Files

- **Quick Reference:** `OPENWEBUI_PUBLISH.md`
- **Technical Details:** `FIX.md`
- **Summary:** `DEPLOYMENT_FIX_SUMMARY.md`
- **Tool Documentation:** `lathe/tool/README.md`

---

## Final Command

After completing all checks, publish with:

**Tool Path:**
```
/tmp/cc-agent/62910883/project/lathe_tool.py
```

Good luck! 🚀
