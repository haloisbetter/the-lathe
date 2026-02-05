"""
Lathe App Filesystem Layer

Read-only filesystem inspection.

Rules:
- NEVER write to disk
- NEVER stage, commit, or modify files
- MUST refuse unsafe paths

All operations are read-only with no side effects.
"""
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


UNSAFE_PREFIXES = [
    "/etc",
    "/var",
    "/usr",
    "/bin",
    "/sbin",
    "/root",
    "/home",
    "..",
]


@dataclass
class TreeEntry:
    """A single entry in a directory tree."""
    path: str
    type: str
    size: Optional[int] = None


@dataclass 
class TreeResult:
    """Result of a tree operation."""
    root: str
    entries: List[TreeEntry]
    truncated: bool
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "root": self.root,
            "entries": [
                {"path": e.path, "type": e.type, "size": e.size}
                for e in self.entries
            ],
            "truncated": self.truncated,
            "error": self.error,
            "results": [],
        }


@dataclass
class GitResult:
    """Result of a git operation."""
    success: bool
    output: str
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "results": [],
        }


class FilesystemInspector:
    """
    Read-only filesystem inspection.
    
    SAFETY GUARANTEES:
    - Never writes to disk
    - Never modifies git state
    - Refuses unsafe paths
    - All operations are read-only
    """
    
    def __init__(self, base_path: str = "."):
        self._base = Path(base_path).resolve()
    
    def is_safe_path(self, path: str) -> bool:
        """Check if a path is safe to inspect."""
        for prefix in UNSAFE_PREFIXES:
            if path.startswith(prefix):
                return False
        
        try:
            resolved = (self._base / path).resolve()
            return str(resolved).startswith(str(self._base))
        except (ValueError, OSError):
            return False
    
    def tree(
        self,
        path: str = ".",
        max_depth: int = 3,
        max_entries: int = 500,
    ) -> TreeResult:
        """
        Get directory tree (depth-limited).
        
        Args:
            path: Starting path (relative to base)
            max_depth: Maximum depth to traverse
            max_entries: Maximum entries to return
            
        Returns:
            TreeResult with directory contents
        """
        if not self.is_safe_path(path):
            return TreeResult(
                root=path,
                entries=[],
                truncated=False,
                error=f"Unsafe path: {path}",
            )
        
        target = self._base / path
        if not target.exists():
            return TreeResult(
                root=path,
                entries=[],
                truncated=False,
                error=f"Path not found: {path}",
            )
        
        entries = []
        truncated = False
        
        try:
            for entry in self._walk(target, max_depth, 0):
                if len(entries) >= max_entries:
                    truncated = True
                    break
                entries.append(entry)
        except PermissionError as e:
            return TreeResult(
                root=path,
                entries=entries,
                truncated=truncated,
                error=f"Permission denied: {e}",
            )
        
        return TreeResult(
            root=path,
            entries=entries,
            truncated=truncated,
        )
    
    def _walk(self, path: Path, max_depth: int, current_depth: int) -> List[TreeEntry]:
        """Recursively walk directory tree."""
        entries = []
        
        if current_depth > max_depth:
            return entries
        
        if path.is_file():
            try:
                size = path.stat().st_size
            except OSError:
                size = None
            return [TreeEntry(
                path=str(path.relative_to(self._base)),
                type="file",
                size=size,
            )]
        
        if path.is_dir():
            entries.append(TreeEntry(
                path=str(path.relative_to(self._base)),
                type="directory",
            ))
            
            try:
                for child in sorted(path.iterdir()):
                    if child.name.startswith(".git"):
                        continue
                    entries.extend(self._walk(child, max_depth, current_depth + 1))
            except PermissionError:
                pass
        
        return entries
    
    def git_status(self) -> GitResult:
        """
        Get git status summary.
        
        Read-only: does not modify working tree or index.
        """
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self._base,
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode != 0:
                return GitResult(
                    success=False,
                    output="",
                    error=result.stderr or "git status failed",
                )
            
            return GitResult(
                success=True,
                output=result.stdout,
            )
        except subprocess.TimeoutExpired:
            return GitResult(success=False, output="", error="git status timed out")
        except FileNotFoundError:
            return GitResult(success=False, output="", error="git not found")
        except Exception as e:
            return GitResult(success=False, output="", error=str(e))
    
    def git_diff(self, staged: bool = False) -> GitResult:
        """
        Get git diff summary.
        
        Read-only: does not modify working tree or index.
        """
        try:
            cmd = ["git", "diff"]
            if staged:
                cmd.append("--staged")
            cmd.append("--stat")
            
            result = subprocess.run(
                cmd,
                cwd=self._base,
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode != 0:
                return GitResult(
                    success=False,
                    output="",
                    error=result.stderr or "git diff failed",
                )
            
            return GitResult(
                success=True,
                output=result.stdout,
            )
        except subprocess.TimeoutExpired:
            return GitResult(success=False, output="", error="git diff timed out")
        except FileNotFoundError:
            return GitResult(success=False, output="", error="git not found")
        except Exception as e:
            return GitResult(success=False, output="", error=str(e))
