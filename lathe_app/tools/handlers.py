"""
Tool Handlers

Pure read-only tool implementations.
Each handler receives validated workspace + params, returns structured dict.

SAFETY GUARANTEES:
- No filesystem access outside workspace boundaries
- No model calls
- No mutation of any state
- No subprocess except whitelisted git commands via git_workspace
"""
import os
import subprocess
from collections import Counter
from typing import Any, Dict, List, Optional

from lathe_app.workspace.manager import get_default_manager
from lathe_app.workspace.scanner import scan_workspace, DEFAULT_EXCLUDE, is_excluded_dir
from lathe_app.trust import TrustPolicy


def _resolve_workspace(workspace_id: str):
    manager = get_default_manager()
    ws = manager.get_workspace(workspace_id)
    if ws is None:
        return None, {"error": "workspace_not_found", "message": f"Workspace '{workspace_id}' not found"}
    return ws, None


def _check_trust(workspace_root: str, trust_required: int):
    policy = TrustPolicy.load_from_workspace(workspace_root)
    if policy.trust_level < trust_required:
        return {
            "error": "trust_denied",
            "message": f"Tool requires trust level >= {trust_required}, workspace has {policy.trust_level}",
            "trust_level": policy.trust_level,
            "required": trust_required,
        }
    return None


def handle_fs_tree(workspace_id: str, ext: Optional[str] = None) -> Dict[str, Any]:
    ws, err = _resolve_workspace(workspace_id)
    if err:
        return err

    trust_err = _check_trust(ws.root_path, 0)
    if trust_err:
        return trust_err

    if ext and not ext.startswith("."):
        ext = f".{ext}"

    include = None
    if ext:
        include = [f"**/*{ext}"]

    abs_files = scan_workspace(ws.root_path, include=include)

    rel_files = []
    for f in abs_files:
        rel = os.path.relpath(f, ws.root_path)
        if not ws.contains_path(f):
            continue
        rel_files.append(rel)

    return {
        "files": sorted(rel_files),
        "count": len(rel_files),
        "workspace": workspace_id,
    }


def handle_fs_stats(workspace_id: str) -> Dict[str, Any]:
    ws, err = _resolve_workspace(workspace_id)
    if err:
        return err

    trust_err = _check_trust(ws.root_path, 0)
    if trust_err:
        return trust_err

    ext_counts: Counter = Counter()
    total = 0

    exclude = list(DEFAULT_EXCLUDE)

    for dirpath, dirnames, filenames in os.walk(ws.root_path):
        dirnames[:] = sorted([
            d for d in dirnames
            if not is_excluded_dir(d, exclude)
        ])

        for filename in filenames:
            abs_path = os.path.join(dirpath, filename)
            if not ws.contains_path(abs_path):
                continue
            if is_excluded_dir(filename, exclude):
                continue

            _, ext = os.path.splitext(filename)
            if ext:
                ext_counts[ext.lower()] += 1
            else:
                ext_counts["(no ext)"] += 1
            total += 1

    return {
        "extensions": dict(sorted(ext_counts.items(), key=lambda x: -x[1])),
        "total_files": total,
        "workspace": workspace_id,
    }


def handle_git_status(workspace_id: str) -> Dict[str, Any]:
    ws, err = _resolve_workspace(workspace_id)
    if err:
        return err

    trust_err = _check_trust(ws.root_path, 0)
    if trust_err:
        return trust_err

    git_dir = os.path.join(ws.root_path, ".git")
    if not os.path.isdir(git_dir):
        return {
            "error": "not_git_repo",
            "message": f"Workspace '{workspace_id}' is not a git repository",
            "workspace": workspace_id,
        }

    try:
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ws.root_path,
            capture_output=True,
            text=True,
            timeout=30,
        )

        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=ws.root_path,
            capture_output=True,
            text=True,
            timeout=10,
        )

        stdout = status_result.stdout.strip()
        clean = len(stdout) == 0
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None

        return {
            "clean": clean,
            "branch": branch,
            "stdout": stdout,
            "workspace": workspace_id,
        }
    except subprocess.TimeoutExpired:
        return {
            "error": "timeout",
            "message": "Git status timed out",
            "workspace": workspace_id,
        }
    except FileNotFoundError:
        return {
            "error": "git_not_found",
            "message": "git binary not found",
            "workspace": workspace_id,
        }


TOOL_HANDLERS = {
    "fs_tree": handle_fs_tree,
    "fs_stats": handle_fs_stats,
    "git_status": handle_git_status,
}
