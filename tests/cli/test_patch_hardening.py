import pytest
from pathlib import Path
from lathe.patch import validate_patch, apply_patch, dry_run_patch

def test_validate_patch_traversal():
    patch_content = """--- a/../../etc/passwd
+++ b/../../etc/passwd
@@ -1,1 +1,1 @@
-root
+hacker
"""
    with pytest.raises(ValueError, match="Path traversal detected"):
        validate_patch(patch_content)

def test_validate_patch_absolute():
    patch_content = """--- a/etc/passwd
+++ b/etc/passwd
@@ -1,1 +1,1 @@
-root
+hacker
"""
    # Note: validate_patch strips a/ b/. If it's just /etc/passwd, it's absolute.
    patch_content_abs = """--- /etc/passwd
+++ /etc/passwd
@@ -1,1 +1,1 @@
-root
+hacker
"""
    with pytest.raises(ValueError, match="Absolute path detected"):
        validate_patch(patch_content_abs)

def test_dry_run_stale_patch():
    patch_path = Path("tests/fixtures/patching/stale.patch")
    success, output = dry_run_patch(patch_path)
    assert not success
    assert "patching file" in output.lower()

def test_apply_clean_patch():
    # Setup: Ensure fixture file exists in its expected state
    target_file = Path("tests/fixtures/sample_repo/src/main.py")
    original_content = target_file.read_text()
    
    patch_path = Path("tests/fixtures/patching/clean.patch")
    why_data = {"goal": "Test clean apply"}
    
    success, output = apply_patch(patch_path, why_data)
    
    try:
        assert success
        assert "Hardened patching is active." in target_file.read_text()
    finally:
        # Restore original state
        target_file.write_text(original_content)
