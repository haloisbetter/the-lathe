"""Tests for workspace manager."""
import os
import pytest
import tempfile
from lathe_app.workspace.manager import (
    WorkspaceManager,
    get_default_manager,
    reset_default_manager,
    UNSAFE_PATHS,
)


class TestWorkspaceManager:
    """Tests for WorkspaceManager."""
    
    def setup_method(self):
        """Reset manager before each test."""
        self.manager = WorkspaceManager()
    
    def test_create_workspace(self):
        """Test workspace creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = self.manager.create_workspace(tmpdir)
            
            assert ws.id.startswith("ws-")
            assert ws.root_path == tmpdir
            assert ws.active is True
    
    def test_create_workspace_custom_id(self):
        """Test workspace creation with custom ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = self.manager.create_workspace(tmpdir, workspace_id="my-ws")
            
            assert ws.id == "my-ws"
    
    def test_list_workspaces(self):
        """Test listing workspaces."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                self.manager.create_workspace(tmpdir1, workspace_id="ws1")
                self.manager.create_workspace(tmpdir2, workspace_id="ws2")
                
                workspaces = self.manager.list_workspaces()
                
                assert len(workspaces) == 2
                ids = [ws.id for ws in workspaces]
                assert "ws1" in ids
                assert "ws2" in ids
    
    def test_get_workspace(self):
        """Test getting workspace by ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            created = self.manager.create_workspace(tmpdir, workspace_id="test-ws")
            
            ws = self.manager.get_workspace("test-ws")
            
            assert ws is not None
            assert ws.id == "test-ws"
    
    def test_get_workspace_not_found(self):
        """Test getting non-existent workspace."""
        ws = self.manager.get_workspace("nonexistent")
        
        assert ws is None
    
    def test_resolve_path(self):
        """Test path resolution through manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.manager.create_workspace(tmpdir, workspace_id="test-ws")
            
            resolved = self.manager.resolve_path("test-ws", "src/main.py")
            
            assert resolved == os.path.join(tmpdir, "src/main.py")
    
    def test_resolve_path_traversal_rejected(self):
        """Test path traversal rejection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.manager.create_workspace(tmpdir, workspace_id="test-ws")
            
            resolved = self.manager.resolve_path("test-ws", "../escape.txt")
            
            assert resolved is None
    
    def test_is_path_in_workspace(self):
        """Test path containment check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.manager.create_workspace(tmpdir, workspace_id="test-ws")
            
            inside = os.path.join(tmpdir, "file.py")
            outside = "/etc/passwd"
            
            assert self.manager.is_path_in_workspace("test-ws", inside) is True
            assert self.manager.is_path_in_workspace("test-ws", outside) is False
    
    def test_remove_workspace(self):
        """Test workspace removal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.manager.create_workspace(tmpdir, workspace_id="test-ws")
            
            removed = self.manager.remove_workspace("test-ws")
            
            assert removed is True
            assert self.manager.get_workspace("test-ws") is None
    
    def test_remove_workspace_not_found(self):
        """Test removing non-existent workspace."""
        removed = self.manager.remove_workspace("nonexistent")
        
        assert removed is False
    
    def test_default_workspace(self):
        """Test default workspace is set to first created."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                ws1 = self.manager.create_workspace(tmpdir1, workspace_id="ws1")
                self.manager.create_workspace(tmpdir2, workspace_id="ws2")
                
                default = self.manager.get_default_workspace()
                
                assert default is not None
                assert default.id == "ws1"
    
    def test_set_default_workspace(self):
        """Test setting default workspace."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                self.manager.create_workspace(tmpdir1, workspace_id="ws1")
                self.manager.create_workspace(tmpdir2, workspace_id="ws2")
                
                result = self.manager.set_default_workspace("ws2")
                
                assert result is True
                assert self.manager.get_default_workspace().id == "ws2"


class TestUnsafePaths:
    """Tests for unsafe path rejection."""
    
    def setup_method(self):
        self.manager = WorkspaceManager()
    
    @pytest.mark.parametrize("unsafe_path", list(UNSAFE_PATHS))
    def test_system_directory_rejected(self, unsafe_path):
        """Test system directories are rejected."""
        with pytest.raises(ValueError) as exc:
            self.manager.create_workspace(unsafe_path)
        
        assert "system directory" in str(exc.value).lower()
    
    def test_subdirectory_of_system_rejected(self):
        """Test subdirectories of system paths are rejected."""
        with pytest.raises(ValueError):
            self.manager.create_workspace("/etc/lathe")
    
    def test_duplicate_path_rejected(self):
        """Test duplicate workspace path rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.manager.create_workspace(tmpdir, workspace_id="ws1")
            
            with pytest.raises(ValueError) as exc:
                self.manager.create_workspace(tmpdir, workspace_id="ws2")
            
            assert "already exists" in str(exc.value).lower()


class TestDefaultManager:
    """Tests for default manager singleton."""
    
    def setup_method(self):
        reset_default_manager()
    
    def teardown_method(self):
        reset_default_manager()
    
    def test_get_default_manager(self):
        """Test default manager creation."""
        manager = get_default_manager()
        
        assert manager is not None
        assert isinstance(manager, WorkspaceManager)
    
    def test_default_manager_is_singleton(self):
        """Test default manager is same instance."""
        manager1 = get_default_manager()
        manager2 = get_default_manager()
        
        assert manager1 is manager2
