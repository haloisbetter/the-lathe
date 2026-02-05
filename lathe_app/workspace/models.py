"""
Workspace Models

Dataclasses for workspace isolation.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import os
import uuid


@dataclass
class Workspace:
    """
    Represents an isolated project workspace.
    
    Attributes:
        id: Unique workspace identifier
        root_path: Absolute path to workspace root
        created_at: When the workspace was created
        active: Whether the workspace is currently active
    """
    id: str
    root_path: str
    created_at: datetime
    active: bool = True
    
    @classmethod
    def create(cls, root_path: str, workspace_id: str = None) -> "Workspace":
        """
        Create a new workspace.
        
        Args:
            root_path: Path to workspace root (will be normalized to absolute)
            workspace_id: Optional ID (auto-generated if not provided)
            
        Returns:
            New Workspace instance
        """
        abs_path = os.path.abspath(root_path)
        ws_id = workspace_id or f"ws-{uuid.uuid4().hex[:12]}"
        
        return cls(
            id=ws_id,
            root_path=abs_path,
            created_at=datetime.utcnow(),
            active=True,
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "root_path": self.root_path,
            "created_at": self.created_at.isoformat(),
            "active": self.active,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Workspace":
        """Create from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.utcnow()
            
        return cls(
            id=data["id"],
            root_path=data["root_path"],
            created_at=created_at,
            active=data.get("active", True),
        )
    
    def contains_path(self, path: str) -> bool:
        """
        Check if a path is contained within this workspace.
        
        Args:
            path: Path to check (absolute or relative)
            
        Returns:
            True if path is inside workspace root
        """
        abs_path = os.path.abspath(path)
        return abs_path.startswith(self.root_path + os.sep) or abs_path == self.root_path
    
    def resolve_path(self, relative_path: str) -> Optional[str]:
        """
        Resolve a relative path within this workspace.
        
        Returns None if the resolved path escapes the workspace.
        
        Args:
            relative_path: Path relative to workspace root
            
        Returns:
            Absolute path if safe, None if path escapes workspace
        """
        if os.path.isabs(relative_path):
            if self.contains_path(relative_path):
                return relative_path
            return None
        
        resolved = os.path.normpath(os.path.join(self.root_path, relative_path))
        
        if not self.contains_path(resolved):
            return None
        
        return resolved
