"""
Lathe App Workspace Package

Provides workspace isolation for multi-project safety.

ARCHITECTURAL INTENT:
"Lathe reasons globally.
 The app scopes locally.
 Executors act only inside workspaces."
"""
from lathe_app.workspace.models import Workspace
from lathe_app.workspace.manager import WorkspaceManager, get_default_manager
from lathe_app.workspace.context import WorkspaceContext, get_current_context

__all__ = [
    "Workspace",
    "WorkspaceManager",
    "get_default_manager",
    "WorkspaceContext",
    "get_current_context",
]
