"""Tests for workspace context."""
import os
import pytest
import tempfile
from lathe_app.workspace.context import (
    WorkspaceContext,
    get_current_context,
    set_current_context,
    clear_current_context,
)
from lathe_app.workspace.manager import (
    get_default_manager,
    reset_default_manager,
)
from lathe_app.workspace.models import Workspace


class TestWorkspaceContext:
    """Tests for WorkspaceContext."""
    
    def setup_method(self):
        reset_default_manager()
        clear_current_context()
    
    def teardown_method(self):
        reset_default_manager()
        clear_current_context()
    
    def test_from_workspace(self):
        """Test context creation from workspace."""
        ws = Workspace.create("/tmp/test-project", workspace_id="test-ws")
        ctx = WorkspaceContext.from_workspace(ws)
        
        assert ctx.workspace_id == "test-ws"
        assert ctx.root_path == "/tmp/test-project"
    
    def test_from_workspace_id(self):
        """Test context creation from workspace ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = get_default_manager()
            manager.create_workspace(tmpdir, workspace_id="test-ws")
            
            ctx = WorkspaceContext.from_workspace_id("test-ws")
            
            assert ctx is not None
            assert ctx.workspace_id == "test-ws"
            assert ctx.root_path == tmpdir
    
    def test_from_workspace_id_not_found(self):
        """Test context creation from non-existent workspace ID."""
        ctx = WorkspaceContext.from_workspace_id("nonexistent")
        
        assert ctx is None
    
    def test_default_context(self):
        """Test default context uses cwd when no workspace."""
        ctx = WorkspaceContext.default()
        
        assert ctx.workspace_id == "default"
        assert ctx.root_path == os.getcwd()
    
    def test_default_context_uses_default_workspace(self):
        """Test default context uses default workspace when available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = get_default_manager()
            manager.create_workspace(tmpdir, workspace_id="test-ws")
            
            ctx = WorkspaceContext.default()
            
            assert ctx.workspace_id == "test-ws"
            assert ctx.root_path == tmpdir
    
    def test_resolve_path(self):
        """Test path resolution in context."""
        ctx = WorkspaceContext(workspace_id="test", root_path="/tmp/project")
        
        resolved = ctx.resolve_path("src/main.py")
        
        assert resolved == "/tmp/project/src/main.py"
    
    def test_resolve_path_traversal_rejected(self):
        """Test traversal rejection in context."""
        ctx = WorkspaceContext(workspace_id="test", root_path="/tmp/project")
        
        resolved = ctx.resolve_path("../escape.txt")
        
        assert resolved is None
    
    def test_contains_path(self):
        """Test path containment in context."""
        ctx = WorkspaceContext(workspace_id="test", root_path="/tmp/project")
        
        assert ctx.contains_path("/tmp/project/src/file.py") is True
        assert ctx.contains_path("/etc/passwd") is False
    
    def test_to_dict(self):
        """Test context serialization."""
        ctx = WorkspaceContext(workspace_id="test", root_path="/tmp/project")
        d = ctx.to_dict()
        
        assert d["workspace_id"] == "test"
        assert d["root_path"] == "/tmp/project"


class TestCurrentContext:
    """Tests for current context management."""
    
    def setup_method(self):
        reset_default_manager()
        clear_current_context()
    
    def teardown_method(self):
        reset_default_manager()
        clear_current_context()
    
    def test_get_current_context_default(self):
        """Test getting current context returns default."""
        ctx = get_current_context()
        
        assert ctx is not None
        assert ctx.workspace_id == "default"
    
    def test_set_current_context(self):
        """Test setting current context."""
        ctx = WorkspaceContext(workspace_id="custom", root_path="/tmp/custom")
        set_current_context(ctx)
        
        current = get_current_context()
        
        assert current.workspace_id == "custom"
    
    def test_clear_current_context(self):
        """Test clearing current context."""
        ctx = WorkspaceContext(workspace_id="custom", root_path="/tmp/custom")
        set_current_context(ctx)
        clear_current_context()
        
        current = get_current_context()
        
        assert current.workspace_id == "default"
