"""
Workspace Snapshot

Produces an immutable, deterministic snapshot of a workspace's filesystem state.
Generates two artifacts:
  1. workspace_manifest.json - per-file metadata with content hashes
  2. workspace_stats.json - aggregate statistics

Guarantees:
- Read-only filesystem access (only os.walk + open for hashing)
- No code execution
- No imports from scanned files
- Deterministic ordering (sorted output)
- Rejects system paths (/etc, /usr, /bin, etc.)
- Rejects self-ingestion
"""
import hashlib
import os
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from lathe_app.workspace.scanner import (
    scan_workspace,
    SUPPORTED_EXTENSIONS,
    DEFAULT_EXCLUDE,
)
from lathe_app.workspace.manager import UNSAFE_PATHS


@dataclass
class FileEntry:
    path: str
    size_bytes: int
    line_count: int
    extension: str
    content_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "line_count": self.line_count,
            "extension": self.extension,
            "content_hash": self.content_hash,
        }


@dataclass
class WorkspaceManifest:
    root_path: str
    files: List[FileEntry]
    generated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_path": self.root_path,
            "files": [f.to_dict() for f in self.files],
            "generated_at": self.generated_at,
        }


@dataclass
class WorkspaceStats:
    total_files: int
    python_files: int
    markdown_files: int
    extension_distribution: Dict[str, int]
    directory_depth_histogram: Dict[int, int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_files": self.total_files,
            "python_files": self.python_files,
            "markdown_files": self.markdown_files,
            "extension_distribution": self.extension_distribution,
            "directory_depth_histogram": {
                str(k): v for k, v in sorted(self.directory_depth_histogram.items())
            },
        }


@dataclass
class WorkspaceSnapshot:
    manifest: WorkspaceManifest
    stats: WorkspaceStats

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest": self.manifest.to_dict(),
            "stats": self.stats.to_dict(),
        }


def _hash_file(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
    except (OSError, IOError):
        return "error:unreadable"
    return h.hexdigest()


def _count_lines(path: str) -> int:
    try:
        with open(path, "rb") as f:
            return sum(1 for _ in f)
    except (OSError, IOError):
        return 0


def _validate_root(root_path: str) -> Optional[str]:
    abs_path = os.path.abspath(root_path)

    for unsafe in UNSAFE_PATHS:
        if abs_path == unsafe or abs_path.startswith(unsafe + os.sep):
            return f"Cannot snapshot system directory: {unsafe}"

    lathe_root = os.path.abspath(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    )
    if abs_path == lathe_root or abs_path.startswith(lathe_root + os.sep):
        return "Cannot snapshot the Lathe repository itself"

    if not os.path.exists(abs_path):
        return f"Path not found: {abs_path}"

    if not os.path.isdir(abs_path):
        return f"Path is not a directory: {abs_path}"

    return None


def snapshot_workspace(
    root_path: str,
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
    timestamp: Optional[str] = None,
) -> WorkspaceSnapshot:
    abs_root = os.path.abspath(root_path)

    error = _validate_root(abs_root)
    if error:
        raise ValueError(error)

    files = scan_workspace(abs_root, include=include, exclude=exclude)

    entries: List[FileEntry] = []
    ext_counter: Counter = Counter()
    depth_counter: Counter = Counter()
    py_count = 0
    md_count = 0

    for abs_path in files:
        rel_path = os.path.relpath(abs_path, abs_root)
        _, ext = os.path.splitext(abs_path)
        ext = ext.lower()

        size = 0
        try:
            size = os.path.getsize(abs_path)
        except OSError:
            pass

        line_count = _count_lines(abs_path)
        content_hash = _hash_file(abs_path)

        entries.append(FileEntry(
            path=rel_path,
            size_bytes=size,
            line_count=line_count,
            extension=ext,
            content_hash=content_hash,
        ))

        ext_counter[ext] += 1
        depth = rel_path.count(os.sep)
        depth_counter[depth] += 1

        if ext == ".py":
            py_count += 1
        elif ext == ".md":
            md_count += 1

    entries.sort(key=lambda e: e.path)

    ts = timestamp or datetime.now(timezone.utc).isoformat()

    manifest = WorkspaceManifest(
        root_path=abs_root,
        files=entries,
        generated_at=ts,
    )

    stats = WorkspaceStats(
        total_files=len(entries),
        python_files=py_count,
        markdown_files=md_count,
        extension_distribution=dict(sorted(ext_counter.items())),
        directory_depth_histogram=dict(sorted(depth_counter.items())),
    )

    return WorkspaceSnapshot(manifest=manifest, stats=stats)
