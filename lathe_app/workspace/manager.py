"""
Workspace Manager

Manages workspace lifecycle and path resolution.
Enforces isolation guarantees.
"""
from typing import Dict, List, Optional
import os
import threading

from lathe_app.workspace.models import Workspace


UNSAFE_PATHS = {
    "/etc", "/var", "/usr", "/bin", "/sbin",
    "/root", "/proc", "/sys", "/dev", "/boot",
    "/lib", "/lib64", "/opt",
}


class WorkspaceManager:
    """
    Manages workspaces with isolation guarantees.
    
    Thread-safe in-memory workspace registry.
    
    SAFETY GUARANTEES:
    - No path traversal allowed
    - No cross-workspace access
    - System directories rejected
    """
    
    def __init__(self):
        self._workspaces: Dict[str, Workspace] = {}
        self._lock = threading.Lock()
        self._default_workspace: Optional[Workspace] = None
    
    def create_workspace(self, path: str, workspace_id: str = None) -> Workspace:
        """
        Create a new workspace.
        
        Args:
            path: Root path for the workspace
            workspace_id: Optional custom ID
            
        Returns:
            The created Workspace
            
        Raises:
            ValueError: If path is unsafe or already registered
        """
        abs_path = os.path.abspath(path)
        
        error = self._validate_path(abs_path)
        if error:
            raise ValueError(error)
        
        with self._lock:
            for ws in self._workspaces.values():
                if ws.root_path == abs_path:
                    raise ValueError(f"Workspace already exists for path: {abs_path}")
            
            workspace = Workspace.create(abs_path, workspace_id)
            self._workspaces[workspace.id] = workspace
            
            if self._default_workspace is None:
                self._default_workspace = workspace
            
            return workspace
    
    def list_workspaces(self) -> List[Workspace]:
        """Return all registered workspaces."""
        with self._lock:
            return list(self._workspaces.values())
    
    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """Get a workspace by ID."""
        with self._lock:
            return self._workspaces.get(workspace_id)
    
    def get_default_workspace(self) -> Optional[Workspace]:
        """Get the default workspace (first created or explicitly set)."""
        with self._lock:
            return self._default_workspace
    
    def set_default_workspace(self, workspace_id: str) -> bool:
        """
        Set the default workspace.
        
        Returns True if successful, False if workspace not found.
        """
        with self._lock:
            ws = self._workspaces.get(workspace_id)
            if ws is None:
                return False
            self._default_workspace = ws
            return True
    
    def resolve_path(
        self,
        workspace_id: str,
        relative_path: str,
    ) -> Optional[str]:
        """
        Resolve a path within a workspace.
        
        Args:
            workspace_id: The workspace ID
            relative_path: Path to resolve (relative to workspace root)
            
        Returns:
            Absolute path if valid, None if workspace not found or path escapes
        """
        workspace = self.get_workspace(workspace_id)
        if workspace is None:
            return None
        
        return workspace.resolve_path(relative_path)
    
    def is_path_in_workspace(
        self,
        workspace_id: str,
        path: str,
    ) -> bool:
        """
        Check if a path is within a workspace.
        
        Args:
            workspace_id: The workspace ID
            path: Path to check
            
        Returns:
            True if path is within workspace, False otherwise
        """
        workspace = self.get_workspace(workspace_id)
        if workspace is None:
            return False
        
        return workspace.contains_path(path)
    
    def remove_workspace(self, workspace_id: str) -> bool:
        """
        Remove a workspace from the registry.
        
        Does NOT delete files - only unregisters the workspace.
        
        Returns True if removed, False if not found.
        """
        with self._lock:
            if workspace_id not in self._workspaces:
                return False
            
            ws = self._workspaces.pop(workspace_id)
            
            if self._default_workspace and self._default_workspace.id == workspace_id:
                self._default_workspace = None
                if self._workspaces:
                    self._default_workspace = next(iter(self._workspaces.values()))
            
            return True
    
    def clear(self) -> None:
        """Clear all workspaces. Used for testing."""
        with self._lock:
            self._workspaces.clear()
            self._default_workspace = None
    
    def _validate_path(self, abs_path: str) -> Optional[str]:
        """
        Validate that a path is safe for workspace creation.
        
        Returns error message if invalid, None if valid.
        """
        for unsafe in UNSAFE_PATHS:
            if abs_path == unsafe or abs_path.startswith(unsafe + os.sep):
                return f"Cannot create workspace in system directory: {unsafe}"
        
        if ".." in abs_path:
            return f"Path traversal detected: {abs_path}"
        
        return None


_default_manager: Optional[WorkspaceManager] = None
_manager_lock = threading.Lock()


def get_default_manager() -> WorkspaceManager:
    """Get or create the default workspace manager."""
    global _default_manager
    
    with _manager_lock:
        if _default_manager is None:
            _default_manager = WorkspaceManager()
        return _default_manager


def reset_default_manager() -> None:
    """Reset the default manager. Used for testing."""
    global _default_manager
    
    with _manager_lock:
        if _default_manager is not None:
            _default_manager.clear()
        _default_manager = None
