# OpenWebUI Publishing - Quick Reference

## TL;DR

**Tool File Path:**
```
/tmp/cc-agent/62910883/project/lathe_tool.py
```

**Installation Command:**
```bash
pip install -e /tmp/cc-agent/62910883/project
```

**Verification:**
```bash
python3 -c "from lathe_tool import lathe_plan; print('OK')"
```

---

## Publishing Steps

### 1. Prepare Environment

Run in the same environment where OpenWebUI executes (Docker container or local Python):

```bash
# Install lathe package
pip install -e /tmp/cc-agent/62910883/project

# Verify it works
python3 -c "from lathe_tool import lathe_plan, lathe_validate, lathe_context_preview; print('✓ Ready')"
```

### 2. Publish in OpenWebUI

#### Web UI Method:
1. Open OpenWebUI → **Settings** → **Tools**
2. Click **"Add Tool"** or **"Import Tool"**
3. Enter path: `/tmp/cc-agent/62910883/project/lathe_tool.py`
4. Click **"Import"** or **"Save"**

#### Config File Method:
Edit your OpenWebUI configuration:

```yaml
tools:
  - name: lathe
    type: python_function
    path: /tmp/cc-agent/62910883/project/lathe_tool.py
```

### 3. Test

In OpenWebUI chat, try:

```
Use lathe_plan to prepare a design phase for project "myapp",
scope "authentication", with goal "Design login system"
```

---

## Docker Users

If OpenWebUI runs in Docker:

### Step 1: Copy Tool into Container

```bash
# Copy tool file
docker cp /tmp/cc-agent/62910883/project/lathe_tool.py \
  openwebui:/app/tools/lathe_tool.py

# Install lathe package in container
docker exec openwebui bash -c "pip install -e /tmp/cc-agent/62910883/project"
```

### Step 2: Use Container Path

Use this path in OpenWebUI: `/app/tools/lathe_tool.py`

### Alternative: Volume Mount

Add to `docker-compose.yml`:

```yaml
services:
  openwebui:
    volumes:
      - /tmp/cc-agent/62910883/project:/workspace/lathe:ro
```

Then use path: `/workspace/lathe/lathe_tool.py`

---

## Available Functions

### `lathe_plan`
Prepare a phase-locked AI step

**Parameters:**
- `project` (str): Project name
- `scope` (str): Work scope
- `phase` (str): `analysis` | `design` | `implementation` | `validation` | `hardening`
- `goal` (str): Goal description
- `constraints` (list, optional): Constraints
- `sources` (list, optional): Context sources

**Returns:** System prompt, context, rules, risks

---

### `lathe_validate`
Validate AI output against rules

**Parameters:**
- `phase` (str): Current phase
- `output` (str): AI output to validate
- `ruleset` (list, optional): Rules to apply

**Returns:** Validation status, violations, summary

---

### `lathe_context_preview`
Preview context assembly

**Parameters:**
- `query` (str): Query for context
- `sources` (list, optional): Context sources
- `max_tokens` (int, optional): Max tokens (default: 2000)

**Returns:** Context blocks, token estimate

---

## Troubleshooting

### Error: "No such file or directory"
**Fix:** Use absolute path: `/tmp/cc-agent/62910883/project/lathe_tool.py`

### Error: "No module named 'lathe'"
**Fix:** Install package:
```bash
pip install -e /tmp/cc-agent/62910883/project
```

### Error: "Permission denied"
**Fix:** Check file permissions:
```bash
chmod 644 /tmp/cc-agent/62910883/project/lathe_tool.py
```

### Error: "Functions not found"
**Fix:** Verify import works:
```bash
python3 -c "from lathe_tool import lathe_plan; print('OK')"
```

---

## Complete Example

```bash
# 1. Install
pip install -e /tmp/cc-agent/62910883/project

# 2. Verify
python3 -c "from lathe_tool import lathe_plan; print('OK')"

# 3. Test function
python3 << 'EOF'
from lathe_tool import lathe_plan
result = lathe_plan(
    project="myapp",
    scope="auth",
    phase="design",
    goal="Design authentication system"
)
print(f"Phase: {result['phase']}")
print(f"Ready: {result['ready']}")
print(f"Rules: {len(result['rules'])} rules")
EOF

# 4. Publish in OpenWebUI
# Use path: /tmp/cc-agent/62910883/project/lathe_tool.py
```

---

## Support

- Full documentation: `lathe/tool/README.md`
- Examples: `lathe/tool/EXAMPLES.md`
- Integration guide: `lathe/tool/INTEGRATION.md`
- Fix details: `FIX.md`

---

**Status:** ✅ Fixed and ready to publish
