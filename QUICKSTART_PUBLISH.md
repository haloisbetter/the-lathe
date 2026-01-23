# Quick Start: Publishing Lathe to OpenWebUI

**TL;DR:** 3 steps to publish

---

## Step 1: Verify

```bash
python3 verify_lathe.py
```

**Expected Output:**
```
✅ ALL CHECKS PASSED - LATHE IS READY FOR OPENWEB UI
Tool Path: /tmp/cc-agent/62910883/project/lathe_tool.py
```

---

## Step 2: Get Tool Path

```bash
python3 -c "import os; print(os.path.abspath('lathe_tool.py'))"
```

**Example Output:**
```
/tmp/cc-agent/62910883/project/lathe_tool.py
```

---

## Step 3: Add to OpenWebUI

1. Open OpenWebUI Admin Panel (http://localhost:8081/admin)
2. Go to: **Tools** → **Add Tool**
3. Select: **Python File** (or **Custom Python Tool**)
4. Enter **Path:** (paste output from Step 2)
5. Click **Save**

---

## Done!

Use in conversation:
```
@lathe plan: project=myapp scope=auth phase=analysis goal=discover_requirements
```

---

## Troubleshooting

**"File not found"** → Use absolute path (not relative)
**"ImportError"** → Run `pip install -e .` first
**"Tool returns empty"** → Check Python version is 3.11+

For detailed help, see: **PUBLISH_FIX.md**

---

## Files

- **lathe_tool.py** - The tool (single file)
- **verify_lathe.py** - Verification script
- **PUBLISH_FIX.md** - Detailed documentation
- **PUBLISH_FIX_SUMMARY.txt** - What was fixed

---

## That's It!

The Lathe is production-ready for publishing. ✅
