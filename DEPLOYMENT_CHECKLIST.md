# Lathe Deployment Checklist

## Pre-Deployment Verification

**Goal:** Ensure Lathe is production-ready for OpenWebUI publishing.

---

## Checklist

### 1. Installation & Accessibility

- [ ] **lathe_tool.py exists at project root**
  ```bash
  ls -l lathe_tool.py
  ```
  Expected: `-rw-r--r-- 1 appuser appuser 23K lathe_tool.py`

- [ ] **File is readable**
  ```bash
  python3 -c "exec(open('lathe_tool.py').read()); print('✓ File readable')"
  ```

- [ ] **pyproject.toml configured**
  ```bash
  grep "name = \"the-lathe\"" pyproject.toml
  ```
  Expected: Package named `the-lathe` with `version = "1.0.0"`

### 2. Python Environment

- [ ] **Python 3.11+ available**
  ```bash
  python3 --version
  ```
  Expected: `Python 3.11` or higher

- [ ] **No system/environment conflicts**
  ```bash
  python3 -m pip list | grep -i lathe
  ```
  Expected: No duplicate installations

### 3. Import Verification

- [ ] **Core module imports**
  ```bash
  python3 -c "import lathe; print('✓ lathe imported')"
  ```

- [ ] **Tool functions export**
  ```bash
  python3 -c "from lathe_tool import lathe_plan, lathe_validate, lathe_context_preview; print('✓ All functions')"
  ```

- [ ] **No import errors on first load**
  ```bash
  python3 lathe_tool.py 2>&1 | head -5
  ```
  Expected: No import errors

### 4. Functionality Tests

- [ ] **lathe_plan works**
  ```bash
  python3 << 'EOF'
  from lathe_tool import lathe_plan
  result = lathe_plan(project="test", scope="demo", phase="analysis", goal="Test")
  assert result.get("phase") == "analysis"
  print("✓ lathe_plan working")
  EOF
  ```

- [ ] **lathe_validate works**
  ```bash
  python3 << 'EOF'
  from lathe_tool import lathe_validate
  result = lathe_validate(phase="analysis", output="Test output")
  assert result.get("status") in ["pass", "warn", "fail"]
  print("✓ lathe_validate working")
  EOF
  ```

- [ ] **lathe_context_preview works**
  ```bash
  python3 << 'EOF'
  from lathe_tool import lathe_context_preview
  result = lathe_context_preview(project="test", scope="demo")
  assert "context_blocks" in result
  print("✓ lathe_context_preview working")
  EOF
  ```

### 5. Validation Phase Enforcement

- [ ] **Code blocks are rejected**
  ```bash
  python3 << 'EOF'
  from lathe_tool import lathe_validate
  result = lathe_validate(phase="validation", output="export function() {}")
  assert result["status"] == "fail", "Code blocks should be rejected"
  print("✓ Code blocks rejected")
  EOF
  ```

- [ ] **New implementation proposed is rejected**
  ```bash
  python3 << 'EOF'
  from lathe_tool import lathe_validate
  result = lathe_validate(phase="validation", output="We should add better logging")
  assert result["status"] == "fail", "Implementation proposals should be rejected"
  print("✓ New implementation rejected")
  EOF
  ```

- [ ] **Rollback steps are encouraged**
  ```bash
  python3 << 'EOF'
  from lathe_tool import lathe_validate
  result = lathe_validate(phase="validation", output="VALIDATION\nRollback: git revert")
  assert "violations" in result
  print("✓ Validation phase rules enforced")
  EOF
  ```

### 6. Documentation

- [ ] **PUBLISH.md exists**
  ```bash
  ls -l PUBLISH.md
  ```

- [ ] **PUBLISH.md is complete**
  ```bash
  grep -c "lathe_tool.py" PUBLISH.md
  ```
  Expected: ≥10 references

- [ ] **verify_lathe.py exists and runs**
  ```bash
  python3 verify_lathe.py
  ```
  Expected: All checks pass, shows tool path

### 7. File Path Verification

- [ ] **Absolute path can be obtained**
  ```bash
  python3 -c "import os; print(os.path.abspath('lathe_tool.py'))"
  ```
  Example: `/home/user/the-lathe/lathe_tool.py`

- [ ] **Path is reachable from OpenWebUI**
  ```bash
  test -r "$(python3 -c 'import os; print(os.path.abspath("lathe_tool.py"))')" && echo "✓ Readable"
  ```

### 8. No Temp Path Dependencies

- [ ] **No /tmp references in Python code**
  ```bash
  grep -r "/tmp" lathe/ lathe_tool.py --include="*.py" || echo "✓ No /tmp refs"
  ```

- [ ] **No cc-agent references**
  ```bash
  grep -r "cc-agent" lathe/ lathe_tool.py --include="*.py" || echo "✓ No cc-agent refs"
  ```

- [ ] **No bolt.new references**
  ```bash
  grep -r "bolt" lathe/ lathe_tool.py --include="*.py" || echo "✓ No bolt refs"
  ```

### 9. OpenWebUI Compatibility

- [ ] **lathe_tool.py is single file (not package)**
  ```bash
  test -f lathe_tool.py && test ! -d lathe_tool && echo "✓ Single file"
  ```

- [ ] **Top-level functions are callable**
  ```bash
  python3 << 'EOF'
  import inspect
  from lathe_tool import lathe_plan, lathe_validate, lathe_context_preview
  assert callable(lathe_plan), "lathe_plan not callable"
  assert callable(lathe_validate), "lathe_validate not callable"
  assert callable(lathe_context_preview), "lathe_context_preview not callable"
  print("✓ All functions callable")
  EOF
  ```

- [ ] **Functions return JSON-serializable results**
  ```bash
  python3 << 'EOF'
  import json
  from lathe_tool import lathe_plan
  result = lathe_plan(project="test", scope="demo", phase="analysis", goal="Test")
  try:
      json.dumps(result)
      print("✓ Results JSON-serializable")
  except TypeError:
      print("✗ Results not JSON-serializable")
  EOF
  ```

### 10. Build & Tests

- [ ] **npm run build succeeds**
  ```bash
  npm run build
  ```
  Expected: No errors

- [ ] **Tests pass**
  ```bash
  npm run test 2>&1 | tail -10
  ```
  Expected: All tests pass or complete

---

## Pre-Publishing Verification Script

Save and run this to verify everything:

```bash
#!/bin/bash
# Comprehensive pre-publishing verification

echo "=== Lathe Pre-Publishing Verification ==="
echo ""

# Check 1: Files exist
echo "1. Checking files..."
[ -f lathe_tool.py ] && echo "   ✓ lathe_tool.py" || echo "   ✗ lathe_tool.py missing"
[ -f pyproject.toml ] && echo "   ✓ pyproject.toml" || echo "   ✗ pyproject.toml missing"
[ -f PUBLISH.md ] && echo "   ✓ PUBLISH.md" || echo "   ✗ PUBLISH.md missing"
[ -f verify_lathe.py ] && echo "   ✓ verify_lathe.py" || echo "   ✗ verify_lathe.py missing"
echo ""

# Check 2: Python version
echo "2. Checking Python..."
python3 --version
echo ""

# Check 3: Package imports
echo "3. Checking imports..."
python3 -c "import lathe; print('   ✓ lathe package')" 2>&1 || echo "   ✗ lathe import failed"
python3 -c "from lathe_tool import lathe_plan, lathe_validate, lathe_context_preview; print('   ✓ tool functions')" 2>&1 || echo "   ✗ tool functions import failed"
echo ""

# Check 4: Verification script
echo "4. Running verification..."
python3 verify_lathe.py 2>&1 | tail -5
echo ""

# Check 5: No temp paths
echo "5. Checking for temp paths..."
! grep -r "/tmp\|cc-agent\|bolt" lathe/ lathe_tool.py --include="*.py" 2>/dev/null && echo "   ✓ No temp paths" || echo "   ⚠ Found temp path references"
echo ""

echo "=== Verification Complete ==="
echo "If all checks pass, Lathe is ready for OpenWebUI publishing."
```

---

## Publishing Steps

Once all checks pass:

1. **Get absolute path:**
   ```bash
   python3 -c "import os; print(os.path.abspath('lathe_tool.py'))"
   ```

2. **Copy to stable location (optional):**
   ```bash
   mkdir -p /opt/lathe
   cp lathe_tool.py /opt/lathe/
   ```

3. **Note the path for OpenWebUI:**
   - Development: `/home/user/the-lathe/lathe_tool.py`
   - Production: `/opt/lathe/lathe_tool.py`

4. **Open OpenWebUI Admin:**
   - Go to http://localhost:8081 (or your OpenWebUI URL)
   - Admin Panel → Tools → Add Tool
   - Type: Python Tool
   - Path: (use path from step 1)

5. **Verify in OpenWebUI:**
   - Tool should appear in tool list
   - Should work with `@lathe` mention

---

## Post-Deployment Verification

After publishing to OpenWebUI:

- [ ] Tool appears in tool list
- [ ] Tool can be called with @lathe
- [ ] Tool returns proper results
- [ ] No errors in OpenWebUI logs
- [ ] All 3 functions work (@lathe plan, @lathe validate, @lathe context_preview)

---

## Rollback Plan

If issues occur:

1. **Disable tool in OpenWebUI:**
   - Admin Panel → Tools → Find "lathe" → Disable

2. **Check logs:**
   - OpenWebUI logs for error details

3. **Verify locally:**
   ```bash
   python3 verify_lathe.py
   ```

4. **Fix and redeploy:**
   - Fix any issues found
   - Update path in OpenWebUI
   - Re-enable tool

---

## Success Criteria

✅ **Deployment is successful when:**

- [ ] `verify_lathe.py` passes all checks
- [ ] `lathe_tool.py` is at project root and readable
- [ ] All three functions export from lathe_tool.py
- [ ] No temp path dependencies
- [ ] OpenWebUI can load the tool file
- [ ] Tool works when called with @lathe in OpenWebUI
- [ ] npm run build succeeds
- [ ] All tests pass

---

## Quick Start (Summary)

```bash
# 1. Verify
python3 verify_lathe.py

# 2. Get path
python3 -c "import os; print(os.path.abspath('lathe_tool.py'))"

# 3. Copy to OpenWebUI config
# (Use path from step 2)

# 4. Test in OpenWebUI
# @lathe plan: project=test scope=demo phase=analysis goal=verify
```

---

## Support

- **Verification fails?** See PUBLISH.md Troubleshooting section
- **OpenWebUI won't load?** Check file permissions and absolute path
- **Tool doesn't work?** Run `verify_lathe.py` to identify issue
