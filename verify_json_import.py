#!/usr/bin/env python3
"""
Verification script for OpenWebUI JSON import readiness.

This script verifies that:
1. The tool file can be imported cleanly
2. All functions are callable and return JSON-serializable results
3. The JSON definition is valid
4. The path in JSON matches the actual file location
"""

import sys
import os
import json
from pathlib import Path

def check_mark(passed: bool) -> str:
    return "✓" if passed else "✗"

def main():
    print("=" * 80)
    print("OPENWEBUI JSON IMPORT VERIFICATION")
    print("=" * 80)

    issues = []

    # Check 1: Tool file exists
    print("\n1. Tool File Existence")
    tool_file = Path("lathe_tool.py")
    if tool_file.exists():
        print(f"   ✓ lathe_tool.py exists")
        print(f"   ✓ Path: {tool_file.resolve()}")
    else:
        print(f"   ✗ lathe_tool.py not found")
        issues.append("Tool file missing")
        sys.exit(1)

    # Check 2: Clean import
    print("\n2. Python Import")
    try:
        from lathe_tool import lathe_plan, lathe_validate, lathe_context_preview
        print("   ✓ Tool module imports successfully")
        print("   ✓ All 3 functions available")
    except ImportError as e:
        print(f"   ✗ Import failed: {e}")
        issues.append(f"Import error: {e}")
        sys.exit(1)

    # Check 3: Module metadata
    print("\n3. Module Metadata")
    try:
        import lathe_tool
        for attr in ['__version__', '__title__', '__description__', '__author__']:
            if hasattr(lathe_tool, attr):
                val = getattr(lathe_tool, attr)
                print(f"   ✓ {attr} = {val}")
            else:
                print(f"   ⚠ Missing {attr} (optional)")
    except Exception as e:
        print(f"   ⚠ Metadata check failed: {e}")

    # Check 4: Function signatures
    print("\n4. Function Signatures")
    import inspect

    expected_funcs = {
        "lathe_plan": (lathe_plan, ["project", "scope", "phase", "goal"]),
        "lathe_validate": (lathe_validate, ["phase", "output"]),
        "lathe_context_preview": (lathe_context_preview, ["query"])
    }

    for func_name, (func, required_params) in expected_funcs.items():
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())

        # Check required params exist
        missing = [p for p in required_params if p not in params]
        if missing:
            print(f"   ✗ {func_name}: Missing params {missing}")
            issues.append(f"{func_name} missing params")
        else:
            print(f"   ✓ {func_name}{sig}")

    # Check 5: JSON serialization
    print("\n5. JSON Serialization")
    try:
        # Test lathe_plan
        result1 = lathe_plan(
            project="test",
            scope="demo",
            phase="analysis",
            goal="verify json import"
        )
        json.dumps(result1)
        print("   ✓ lathe_plan returns JSON-serializable result")

        # Test lathe_validate
        result2 = lathe_validate(
            phase="analysis",
            output="Test output"
        )
        json.dumps(result2)
        print("   ✓ lathe_validate returns JSON-serializable result")

        # Test lathe_context_preview
        result3 = lathe_context_preview(
            query="test query",
            sources=["knowledge"]
        )
        json.dumps(result3)
        print("   ✓ lathe_context_preview returns JSON-serializable result")

    except Exception as e:
        print(f"   ✗ JSON serialization failed: {e}")
        issues.append(f"JSON serialization: {e}")

    # Check 6: JSON definition file
    print("\n6. JSON Definition File")
    json_file = Path("lathe_tool.json")
    if json_file.exists():
        print(f"   ✓ lathe_tool.json exists")

        try:
            with open(json_file) as f:
                tool_def = json.load(f)
            print("   ✓ JSON is valid")

            # Check required fields
            required = ["name", "version", "type", "module", "path", "functions"]
            for field in required:
                if field in tool_def:
                    print(f"   ✓ Has '{field}': {tool_def[field] if field != 'functions' else f'{len(tool_def[field])} functions'}")
                else:
                    print(f"   ✗ Missing required field: {field}")
                    issues.append(f"JSON missing {field}")

            # Check path matches actual file
            json_path = tool_def.get("path", "")
            actual_path = str(tool_file.resolve())
            if json_path == actual_path:
                print(f"   ✓ Path in JSON matches actual file")
            else:
                print(f"   ⚠ Path mismatch:")
                print(f"      JSON:   {json_path}")
                print(f"      Actual: {actual_path}")
                print(f"   ⚠ Update JSON path before importing to OpenWebUI")

            # Check functions in JSON match Python
            json_funcs = {f["name"] for f in tool_def.get("functions", [])}
            py_funcs = {"lathe_plan", "lathe_validate", "lathe_context_preview"}

            if json_funcs == py_funcs:
                print(f"   ✓ Functions in JSON match Python module")
            else:
                missing = py_funcs - json_funcs
                extra = json_funcs - py_funcs
                if missing:
                    print(f"   ✗ Missing in JSON: {missing}")
                    issues.append(f"JSON missing functions: {missing}")
                if extra:
                    print(f"   ⚠ Extra in JSON: {extra}")

        except json.JSONDecodeError as e:
            print(f"   ✗ Invalid JSON: {e}")
            issues.append("Invalid JSON")
        except Exception as e:
            print(f"   ✗ JSON check failed: {e}")
            issues.append(f"JSON check: {e}")
    else:
        print(f"   ✗ lathe_tool.json not found")
        issues.append("JSON definition missing")

    # Check 7: No temporary paths in code
    print("\n7. Production-Ready Paths")
    try:
        with open(tool_file) as f:
            content = f.read()

        temp_patterns = ["/tmp/", "cc-agent", "bolt.new"]
        found_temp = [p for p in temp_patterns if p in content]

        if not found_temp:
            print("   ✓ No temporary paths in code")
        else:
            print(f"   ⚠ Found temporary paths: {found_temp}")
            print("   ⚠ Consider using only absolute imports")
    except Exception as e:
        print(f"   ⚠ Path check failed: {e}")

    # Summary
    print("\n" + "=" * 80)
    if not issues:
        print("✅ ALL CHECKS PASSED - READY FOR JSON IMPORT")
        print("=" * 80)
        print("\nNext Steps:")
        print("1. Update path in lathe_tool.json (if needed)")
        print("2. Import JSON into OpenWebUI:")
        print("   Admin Panel → Tools → Import Tool → Upload JSON")
        print("3. Test tool in conversation:")
        print("   @lathe lathe_plan project=test scope=demo phase=analysis goal=verify")
        return 0
    else:
        print("❌ ISSUES FOUND")
        print("=" * 80)
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}")
        print("\nFix these issues before importing to OpenWebUI.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
