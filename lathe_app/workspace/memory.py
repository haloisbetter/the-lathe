"""
Workspace Memory

File Read Artifacts and Staleness Detection.

Every file read during reasoning produces a FileReadArtifact containing:
- path, content_hash, line_range, timestamp

If a file is modified after being read, the hash mismatch is detectable
and the run can be flagged as potentially stale.

This is OBSERVABILITY, not enforcement.

Also provides context.md loading for persistent workspace memory.

Guarantees:
- Read-only (hashing only, no writes)
- No code execution
- Deterministic hashing (sha256)
- stdlib only
"""
import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class FileReadArtifact:
    path: str
    content_hash: str
    line_start: Optional[int]
    line_end: Optional[int]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "content_hash": self.content_hash,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "timestamp": self.timestamp,
        }


def hash_file(path: str) -> str:
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


def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def create_file_read(
    path: str,
    line_start: Optional[int] = None,
    line_end: Optional[int] = None,
    timestamp: Optional[str] = None,
) -> FileReadArtifact:
    abs_path = os.path.abspath(path)
    content_hash = hash_file(abs_path)
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    return FileReadArtifact(
        path=abs_path,
        content_hash=content_hash,
        line_start=line_start,
        line_end=line_end,
        timestamp=ts,
    )


def check_staleness(read_artifact: FileReadArtifact) -> Dict[str, Any]:
    current_hash = hash_file(read_artifact.path)

    if current_hash == "error:unreadable":
        return {
            "path": read_artifact.path,
            "stale": True,
            "reason": "file_unreadable",
            "original_hash": read_artifact.content_hash,
            "current_hash": current_hash,
        }

    is_stale = current_hash != read_artifact.content_hash
    result = {
        "path": read_artifact.path,
        "stale": is_stale,
        "original_hash": read_artifact.content_hash,
        "current_hash": current_hash,
    }
    if is_stale:
        result["reason"] = "hash_mismatch"
    return result


def check_run_staleness(file_reads: List[FileReadArtifact]) -> Dict[str, Any]:
    stale_files = []
    fresh_files = []

    for read in file_reads:
        result = check_staleness(read)
        if result["stale"]:
            stale_files.append(result)
        else:
            fresh_files.append(result["path"])

    return {
        "potentially_stale": len(stale_files) > 0,
        "stale_count": len(stale_files),
        "fresh_count": len(fresh_files),
        "stale_files": stale_files,
    }


CONTEXT_FILE_NAMES = [".lathe/context.md", "lathe.md"]


def load_workspace_context(root_path: str) -> Optional[Dict[str, Any]]:
    abs_root = os.path.abspath(root_path)

    for name in CONTEXT_FILE_NAMES:
        context_path = os.path.join(abs_root, name)
        if os.path.isfile(context_path):
            try:
                with open(context_path, "r", encoding="utf-8") as f:
                    content = f.read()
                content_hash = hash_content(content)
                return {
                    "path": context_path,
                    "relative_path": name,
                    "content": content,
                    "content_hash": content_hash,
                    "loaded_at": datetime.now(timezone.utc).isoformat(),
                }
            except (OSError, IOError):
                continue

    return None
