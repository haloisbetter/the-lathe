"""
Workspace Errors

Structured error types for workspace operations.
All errors carry enough context for structured refusal responses.
"""


class WorkspaceError(Exception):
    pass


class WorkspacePathNotFoundError(WorkspaceError):
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Path not found: {path}")


class WorkspaceNotDirectoryError(WorkspaceError):
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Path is not a directory: {path}")


class WorkspaceNameCollisionError(WorkspaceError):
    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Workspace already registered: {name}")


class WorkspaceNotFoundError(WorkspaceError):
    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Workspace not found: {name}")


class WorkspaceUnsafePathError(WorkspaceError):
    def __init__(self, path: str, reason: str = ""):
        self.path = path
        self.reason = reason
        super().__init__(f"Unsafe workspace path: {path}. {reason}")


class WorkspaceEmptyError(WorkspaceError):
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Zero files matched include/exclude filters in: {path}")
