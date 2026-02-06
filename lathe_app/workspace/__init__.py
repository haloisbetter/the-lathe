"""
Lathe App Workspace Package

Provides workspace isolation for multi-project safety,
workspace ingestion for external repository analysis,
and scoped RAG indexes per workspace.

ARCHITECTURAL INTENT:
"Lathe reasons globally.
 The app scopes locally.
 Executors act only inside workspaces."
"""
from lathe_app.workspace.models import Workspace
from lathe_app.workspace.manager import WorkspaceManager, get_default_manager
from lathe_app.workspace.context import WorkspaceContext, get_current_context
from lathe_app.workspace.registry import (
    WorkspaceRegistry,
    RegisteredWorkspace,
    get_default_registry,
)
from lathe_app.workspace.indexer import WorkspaceIndexer, get_default_indexer
from lathe_app.workspace.scanner import scan_workspace, collect_extensions
from lathe_app.workspace.snapshot import (
    WorkspaceSnapshot,
    WorkspaceManifest,
    FileEntry,
    WorkspaceStats,
    snapshot_workspace,
)
from lathe_app.workspace.memory import (
    FileReadArtifact,
    create_file_read,
    check_staleness,
    check_run_staleness,
    load_workspace_context,
    hash_file,
    hash_content,
)
from lathe_app.workspace.errors import (
    WorkspaceError,
    WorkspacePathNotFoundError,
    WorkspaceNotDirectoryError,
    WorkspaceNameCollisionError,
    WorkspaceNotFoundError,
    WorkspaceUnsafePathError,
    WorkspaceEmptyError,
)

__all__ = [
    "Workspace",
    "WorkspaceManager",
    "get_default_manager",
    "WorkspaceContext",
    "get_current_context",
    "WorkspaceRegistry",
    "RegisteredWorkspace",
    "get_default_registry",
    "WorkspaceIndexer",
    "get_default_indexer",
    "scan_workspace",
    "collect_extensions",
    "WorkspaceSnapshot",
    "WorkspaceManifest",
    "FileEntry",
    "WorkspaceStats",
    "snapshot_workspace",
    "FileReadArtifact",
    "create_file_read",
    "check_staleness",
    "check_run_staleness",
    "load_workspace_context",
    "hash_file",
    "hash_content",
    "WorkspaceError",
    "WorkspacePathNotFoundError",
    "WorkspaceNotDirectoryError",
    "WorkspaceNameCollisionError",
    "WorkspaceNotFoundError",
    "WorkspaceUnsafePathError",
    "WorkspaceEmptyError",
]
