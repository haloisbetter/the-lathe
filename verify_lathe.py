#!/usr/bin/env python3
"""
Verify Lathe is properly installed and ready for OpenWebUI.

Usage:
    python3 verify_lathe.py

This script checks:
1. Package imports work
2. Tool functions are available
3. Tool file is accessible
4. Basic functionality works
5. Validation rules enforce correctly
"""

import sys
import os
import json

def check_package_import():
    """Check if lathe package imports."""
    try:
        import lathe
        return True, "Package 'lathe' imports successfully"
    except ImportError as e:
        return False, f"Package import failed: {e}"

def check_tool_functions():
    """Check if tool functions are available."""
    try:
        from lathe_tool import lathe_plan, lathe_validate, lathe_context_preview
        return True, "All tool functions available (lathe_plan, lathe_validate, lathe_context_preview)"
    except ImportError as e:
        return False, f"Tool functions not available: {e}"

def check_tool_file():
    """Check if tool file exists."""
    try:
        tool_path = os.path.abspath("lathe_tool.py")
        if os.path.exists(tool_path):
            return True, f"Tool file exists: {tool_path}"
        else:
            return False, f"Tool file not found at {tool_path}"
    except Exception as e:
        return False, f"Tool file check failed: {e}"

def check_functionality():
    """Check if tool functions work."""
    try:
        from lathe_tool import lathe_plan
        result = lathe_plan(
            project="verify",
            scope="test",
            phase="analysis",
            goal="Verify installation"
        )
        if result.get("phase") == "analysis" and result.get("rules"):
            return True, f"Tool functions work correctly (loaded {len(result.get('rules', []))} rules)"
        else:
            return False, "Tool functions returned unexpected result"
    except Exception as e:
        return False, f"Tool function test failed: {e}"

def check_validation():
    """Check if validation works."""
    try:
        from lathe_tool import lathe_validate

        # Test 1: Good validation
        result = lathe_validate(
            phase="validation",
            output="VALIDATION\n- [ ] Test\nRollback: revert"
        )
        if not result.get("status"):
            return False, "Validation returned unexpected result"

        # Test 2: Code rejection
        result = lathe_validate(
            phase="validation",
            output="Here's code: export function() {}"
        )
        if result.get("status") != "fail":
            return False, "Validation did not reject code blocks"

        return True, "Validation working correctly (enforces phase rules)"
    except Exception as e:
        return False, f"Validation test failed: {e}"

def get_tool_path():
    """Get the absolute path to lathe_tool.py."""
    return os.path.abspath("lathe_tool.py")

def main():
    """Run all checks."""
    checks = [
        ("Package Import", check_package_import),
        ("Tool Functions", check_tool_functions),
        ("Tool File", check_tool_file),
        ("Functionality", check_functionality),
        ("Validation Rules", check_validation),
    ]

    print("\n" + "=" * 70)
    print("LATHE INSTALLATION VERIFICATION")
    print("=" * 70 + "\n")

    all_passed = True
    results = []

    for name, check in checks:
        passed, message = check()
        status = "✓" if passed else "✗"
        print(f"{status} {name}")
        print(f"  {message}\n")
        results.append((name, passed))
        if not passed:
            all_passed = False

    print("=" * 70)

    if all_passed:
        print("✅ ALL CHECKS PASSED - LATHE IS READY FOR OPENWEB UI")
        print("=" * 70)
        print("\nNext Step: Configure in OpenWebUI")
        print(f"Tool Path: {get_tool_path()}")
        print("\nInstructions:")
        print("1. Go to OpenWebUI Admin Panel → Tools")
        print("2. Click 'Add Tool' or 'Import Tool'")
        print("3. Select 'Custom Python Tool'")
        print("4. Enter Tool Path: " + get_tool_path())
        print("5. Click 'Save' or 'Import'")
        print("\nThe Lathe is now available in OpenWebUI as @lathe")
        return 0
    else:
        print("✗ SOME CHECKS FAILED")
        print("=" * 70)
        print("\nFailed checks:")
        for name, passed in results:
            if not passed:
                print(f"  - {name}")
        print("\nTroubleshooting:")
        print("1. Verify Python version: python3 --version (need 3.11+)")
        print("2. Check package installed: python3 -c 'import lathe'")
        print("3. Ensure lathe_tool.py exists: ls -l lathe_tool.py")
        print("4. Check file permissions: chmod 644 lathe_tool.py")
        return 1

if __name__ == "__main__":
    sys.exit(main())
