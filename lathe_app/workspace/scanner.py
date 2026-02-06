"""
Workspace Scanner

Stateless filesystem scanner with glob filtering.
Pure function: takes root + globs, returns file paths.

Guarantees:
- Read-only (only os.walk + glob matching)
- No subprocess calls
- No imports from workspace
- No execution of any kind
- Deterministic ordering (sorted output)
"""
import fnmatch
import os
from typing import List, Optional, Set


SUPPORTED_EXTENSIONS = frozenset({".py", ".md", ".txt", ".json"})

DEFAULT_EXCLUDE = frozenset({
    ".venv", ".git", "node_modules", "__pycache__",
    ".tox", ".mypy_cache", ".pytest_cache", "dist",
    "build", ".eggs", "*.egg-info",
})


def _expand_pattern(pattern: str) -> List[str]:
    """Expand a ** glob pattern into fnmatch-compatible variants."""
    if "**/" in pattern:
        suffix = pattern.split("**/", 1)[1]
        return [pattern, suffix, os.path.join("*", suffix)]
    return [pattern]


def matches_any_glob(path: str, patterns: List[str]) -> bool:
    basename = os.path.basename(path)
    for pattern in patterns:
        expanded = _expand_pattern(pattern)
        for p in expanded:
            if fnmatch.fnmatch(path, p) or fnmatch.fnmatch(basename, p):
                return True
    return False


def is_excluded_dir(dirname: str, exclude_patterns: List[str]) -> bool:
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(dirname, pattern):
            return True
    return False


def scan_workspace(
    root_path: str,
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
) -> List[str]:
    """
    Scan a directory tree and return matching file paths.

    Args:
        root_path: Absolute path to workspace root
        include: Glob patterns for files to include (default: supported extensions)
        exclude: Glob patterns for dirs/files to exclude (default: common excludes)

    Returns:
        Sorted list of absolute file paths that match filters.
    """
    if include is None:
        include = [f"**/*{ext}" for ext in SUPPORTED_EXTENSIONS]

    if exclude is None:
        exclude = list(DEFAULT_EXCLUDE)

    matched_files: List[str] = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = sorted([
            d for d in dirnames
            if not is_excluded_dir(d, exclude)
        ])

        for filename in filenames:
            abs_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(abs_path, root_path)

            if is_excluded_dir(filename, exclude):
                continue

            if matches_any_glob(rel_path, include):
                matched_files.append(abs_path)

    matched_files.sort()
    return matched_files


def collect_extensions(file_paths: List[str]) -> List[str]:
    exts: Set[str] = set()
    for path in file_paths:
        _, ext = os.path.splitext(path)
        if ext:
            exts.add(ext.lower())
    return sorted(exts)
