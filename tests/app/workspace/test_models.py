"""Tests for workspace models."""
import os
import pytest
import tempfile
from lathe_app.workspace.models import Workspace


class TestWorkspace:
    """Tests for Workspace dataclass."""
    
    def test_create_workspace(self):
        """Test workspace creation."""
        ws = Workspace.create("/tmp/test-project")
        
        assert ws.id.startswith("ws-")
        assert ws.root_path == "/tmp/test-project"
        assert ws.active is True
        assert ws.created_at is not None
    
    def test_create_with_custom_id(self):
        """Test workspace creation with custom ID."""
        ws = Workspace.create("/tmp/test-project", workspace_id="my-workspace")
        
        assert ws.id == "my-workspace"
    
    def test_to_dict(self):
        """Test serialization to dict."""
        ws = Workspace.create("/tmp/test-project", workspace_id="test-id")
        d = ws.to_dict()
        
        assert d["id"] == "test-id"
        assert d["root_path"] == "/tmp/test-project"
        assert d["active"] is True
        assert "created_at" in d
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        d = {
            "id": "test-id",
            "root_path": "/tmp/test-project",
            "created_at": "2025-01-01T00:00:00",
            "active": True,
        }
        ws = Workspace.from_dict(d)
        
        assert ws.id == "test-id"
        assert ws.root_path == "/tmp/test-project"
        assert ws.active is True
    
    def test_contains_path_inside(self):
        """Test path containment for paths inside workspace."""
        ws = Workspace.create("/tmp/test-project")
        
        assert ws.contains_path("/tmp/test-project/src/main.py") is True
        assert ws.contains_path("/tmp/test-project") is True
    
    def test_contains_path_outside(self):
        """Test path containment for paths outside workspace."""
        ws = Workspace.create("/tmp/test-project")
        
        assert ws.contains_path("/tmp/other-project/file.py") is False
        assert ws.contains_path("/etc/passwd") is False
    
    def test_resolve_path_valid(self):
        """Test path resolution for valid relative paths."""
        ws = Workspace.create("/tmp/test-project")
        
        resolved = ws.resolve_path("src/main.py")
        assert resolved == "/tmp/test-project/src/main.py"
    
    def test_resolve_path_traversal_rejected(self):
        """Test path resolution rejects traversals."""
        ws = Workspace.create("/tmp/test-project")
        
        resolved = ws.resolve_path("../other-project/file.py")
        assert resolved is None
    
    def test_resolve_path_absolute_inside(self):
        """Test absolute path resolution inside workspace."""
        ws = Workspace.create("/tmp/test-project")
        
        resolved = ws.resolve_path("/tmp/test-project/src/file.py")
        assert resolved == "/tmp/test-project/src/file.py"
    
    def test_resolve_path_absolute_outside(self):
        """Test absolute path resolution outside workspace."""
        ws = Workspace.create("/tmp/test-project")
        
        resolved = ws.resolve_path("/etc/passwd")
        assert resolved is None
