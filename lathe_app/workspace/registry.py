"""
Workspace Registry

In-memory registry for named workspaces.
Stores workspace metadata and tracks which workspaces have been ingested.

Guarantees:
- In-memory only (v1)
- Thread-safe
- Lookup by name
- Rejects duplicate names
- Safe to extend to persistence later
"""
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class RegisteredWorkspace:
    name: str
    root_path: str
    manifest: str
    include: List[str]
    exclude: List[str]
    file_count: int
    indexed_extensions: List[str]
    registered_at: str
    indexed: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "root_path": self.root_path,
            "manifest": self.manifest,
            "include": self.include,
            "exclude": self.exclude,
            "file_count": self.file_count,
            "indexed_extensions": self.indexed_extensions,
            "registered_at": self.registered_at,
            "indexed": self.indexed,
        }


class WorkspaceRegistry:
    def __init__(self):
        self._workspaces: Dict[str, RegisteredWorkspace] = {}
        self._lock = threading.Lock()

    def register(self, workspace: RegisteredWorkspace) -> None:
        with self._lock:
            if workspace.name in self._workspaces:
                from lathe_app.workspace.errors import WorkspaceNameCollisionError
                raise WorkspaceNameCollisionError(workspace.name)
            self._workspaces[workspace.name] = workspace

    def get(self, name: str) -> Optional[RegisteredWorkspace]:
        with self._lock:
            return self._workspaces.get(name)

    def list_all(self) -> List[RegisteredWorkspace]:
        with self._lock:
            return list(self._workspaces.values())

    def contains(self, name: str) -> bool:
        with self._lock:
            return name in self._workspaces

    def remove(self, name: str) -> bool:
        with self._lock:
            if name in self._workspaces:
                del self._workspaces[name]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._workspaces.clear()


_default_registry: Optional[WorkspaceRegistry] = None
_registry_lock = threading.Lock()


def get_default_registry() -> WorkspaceRegistry:
    global _default_registry
    with _registry_lock:
        if _default_registry is None:
            _default_registry = WorkspaceRegistry()
        return _default_registry


def reset_default_registry() -> None:
    global _default_registry
    with _registry_lock:
        if _default_registry is not None:
            _default_registry.clear()
        _default_registry = None
