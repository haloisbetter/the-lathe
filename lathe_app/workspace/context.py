"""
Workspace Context

Provides workspace scoping for orchestrator operations.
"""
from dataclasses import dataclass
from typing import Optional
import os
import threading

from lathe_app.workspace.models import Workspace
from lathe_app.workspace.manager import get_default_manager


@dataclass
class WorkspaceContext:
    """
    Context object that scopes operations to a workspace.
    
    Injected into orchestrator to enforce isolation.
    
    Attributes:
        workspace_id: The workspace this context belongs to
        root_path: Absolute path to workspace root
    """
    workspace_id: str
    root_path: str
    
    @classmethod
    def from_workspace(cls, workspace: Workspace) -> "WorkspaceContext":
        """Create context from a Workspace."""
        return cls(
            workspace_id=workspace.id,
            root_path=workspace.root_path,
        )
    
    @classmethod
    def from_workspace_id(cls, workspace_id: str) -> Optional["WorkspaceContext"]:
        """
        Create context from a workspace ID.
        
        Returns None if workspace not found.
        """
        manager = get_default_manager()
        workspace = manager.get_workspace(workspace_id)
        
        if workspace is None:
            return None
        
        return cls.from_workspace(workspace)
    
    @classmethod
    def default(cls) -> "WorkspaceContext":
        """
        Get the default workspace context.
        
        Uses default workspace if available, otherwise current directory.
        """
        manager = get_default_manager()
        workspace = manager.get_default_workspace()
        
        if workspace is not None:
            return cls.from_workspace(workspace)
        
        return cls(
            workspace_id="default",
            root_path=os.getcwd(),
        )
    
    def resolve_path(self, relative_path: str) -> Optional[str]:
        """
        Resolve a path within this context's workspace.
        
        Returns None if path escapes workspace.
        """
        if os.path.isabs(relative_path):
            if self.contains_path(relative_path):
                return relative_path
            return None
        
        resolved = os.path.normpath(os.path.join(self.root_path, relative_path))
        
        if not self.contains_path(resolved):
            return None
        
        return resolved
    
    def contains_path(self, path: str) -> bool:
        """Check if a path is within this workspace."""
        abs_path = os.path.abspath(path)
        return abs_path.startswith(self.root_path + os.sep) or abs_path == self.root_path
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "workspace_id": self.workspace_id,
            "root_path": self.root_path,
        }


_current_context: Optional[WorkspaceContext] = None
_context_lock = threading.Lock()


def get_current_context() -> WorkspaceContext:
    """
    Get the current workspace context.
    
    Returns default context if none set.
    """
    global _current_context
    
    with _context_lock:
        if _current_context is None:
            return WorkspaceContext.default()
        return _current_context


def set_current_context(context: WorkspaceContext) -> None:
    """Set the current workspace context."""
    global _current_context
    
    with _context_lock:
        _current_context = context


def clear_current_context() -> None:
    """Clear the current context. Used for testing."""
    global _current_context
    
    with _context_lock:
        _current_context = None
