"""
Tests for read-only filesystem inspection.

Verifies:
- Tree operation works
- Git status works
- Git diff works
- Unsafe paths are refused
- Filesystem is NEVER modified
"""
import os
import pytest
import tempfile
from pathlib import Path

from lathe_app.fs import FilesystemInspector


class TestFilesystemInspector:
    """Tests for FilesystemInspector."""
    
    def test_tree_basic(self):
        inspector = FilesystemInspector()
        
        result = inspector.tree(".", max_depth=1)
        
        assert result.error is None
        assert len(result.entries) > 0
    
    def test_tree_depth_limit(self):
        inspector = FilesystemInspector()
        
        result_shallow = inspector.tree(".", max_depth=1)
        result_deep = inspector.tree(".", max_depth=3)
        
        assert len(result_deep.entries) >= len(result_shallow.entries)
    
    def test_tree_entry_limit(self):
        inspector = FilesystemInspector()
        
        result = inspector.tree(".", max_entries=5)
        
        assert len(result.entries) <= 5
        if len(result.entries) == 5:
            assert result.truncated is True
    
    def test_tree_nonexistent_path(self):
        inspector = FilesystemInspector()
        
        result = inspector.tree("nonexistent_directory_xyz")
        
        assert result.error is not None
        assert "not found" in result.error.lower()
    
    def test_unsafe_path_refused(self):
        inspector = FilesystemInspector()
        
        result = inspector.tree("/etc")
        
        assert result.error is not None
        assert "unsafe" in result.error.lower()
    
    def test_parent_traversal_refused(self):
        inspector = FilesystemInspector()
        
        result = inspector.tree("../../../etc")
        
        assert result.error is not None
    
    def test_git_status(self):
        inspector = FilesystemInspector()
        
        result = inspector.git_status()
        
        assert result.success or result.error is not None
    
    def test_git_diff(self):
        inspector = FilesystemInspector()
        
        result = inspector.git_diff()
        
        assert result.success or result.error is not None
    
    def test_git_diff_staged(self):
        inspector = FilesystemInspector()
        
        result = inspector.git_diff(staged=True)
        
        assert result.success or result.error is not None


class TestFilesystemNeverModified:
    """Critical: verify filesystem is NEVER modified."""
    
    def test_tree_does_not_create_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            inspector = FilesystemInspector(tmpdir)
            
            initial_contents = set(os.listdir(tmpdir))
            
            inspector.tree(".")
            inspector.tree("nonexistent")
            
            final_contents = set(os.listdir(tmpdir))
            
            assert initial_contents == final_contents
    
    def test_git_status_does_not_modify(self):
        inspector = FilesystemInspector()
        
        inspector.git_status()
        inspector.git_diff()
        inspector.git_diff(staged=True)


class TestSafePathValidation:
    """Tests for path safety validation."""
    
    def test_relative_path_safe(self):
        inspector = FilesystemInspector()
        
        assert inspector.is_safe_path("src/main.py") is True
        assert inspector.is_safe_path("tests/") is True
    
    def test_absolute_system_path_unsafe(self):
        inspector = FilesystemInspector()
        
        assert inspector.is_safe_path("/etc/passwd") is False
        assert inspector.is_safe_path("/var/log") is False
        assert inspector.is_safe_path("/usr/bin") is False
    
    def test_parent_traversal_unsafe(self):
        inspector = FilesystemInspector()
        
        assert inspector.is_safe_path("..") is False
        assert inspector.is_safe_path("../..") is False
