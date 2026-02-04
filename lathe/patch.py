import os
import subprocess
import re
from pathlib import Path
from typing import List, Tuple
from lathe.ledger import append_recent_work, append_failed_attempt

MAX_FILES_PER_PATCH = 5

def validate_patch(patch_content: str) -> List[str]:
    """
    Validates a unified diff patch strictly.
    Checks for:
    - Path traversal (..)
    - Absolute paths
    - File existence
    - Max files limit
    """
    lines = patch_content.splitlines()
    target_files = set()
    
    for line in lines:
        if line.startswith("--- ") or line.startswith("+++ "):
            parts = line.split()
            if len(parts) >= 2:
                file_path = parts[1]
                # Strip common prefixes like a/ b/
                if file_path.startswith("a/") or file_path.startswith("b/"):
                    file_path = file_path[2:]
                
                # Check for absolute paths
                if os.path.isabs(file_path):
                    raise ValueError(f"Absolute path detected in patch: {file_path}")
                
                # Check for path traversal
                if ".." in Path(file_path).parts:
                    raise ValueError(f"Path traversal detected in patch: {file_path}")
                
                target_files.add(file_path)
    
    if not target_files:
        raise ValueError("No target files found in patch")
    
    if len(target_files) > MAX_FILES_PER_PATCH:
        raise ValueError(f"Too many files in patch ({len(target_files)} > {MAX_FILES_PER_PATCH})")
        
    for f in target_files:
        if f == "/dev/null": # Allow creation/deletion markers
            continue
        if not Path(f).exists():
            raise ValueError(f"Target file does not exist: {f}")
            
    return list(target_files)

def dry_run_patch(patch_path: Path) -> Tuple[bool, str]:
    """Performs a dry-run apply to check if hunks match target context."""
    try:
        # Some versions of patch don't support --dry-run or -C
        # Using -C (check) is often synonymous with --dry-run
        result = subprocess.run(
            ["patch", "-p1", "--dry-run", "-i", str(patch_path)],
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)

def apply_patch(patch_path: Path, why_data: dict, proposal_summary: str = "") -> Tuple[bool, str]:
    """Apply a patch with hardening and dry-run validation."""
    try:
        # Check if patch command exists
        subprocess.run(["patch", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False, "System 'patch' command not found"

    # Dry run first
    success_dry, output_dry = dry_run_patch(patch_path)
    if not success_dry:
        error_msg = f"Patch dry-run failed. Context might be stale or hunks might overlap.\n{output_dry}"
        append_failed_attempt(".", f"Dry-run failed for {patch_path.name}", why_data.get("goal", "Unknown"), f"patch --dry-run -i {patch_path.name}", error_msg)
        return False, error_msg

    try:
        # Actual apply
        result = subprocess.run(
            ["patch", "-p1", "-i", str(patch_path)],
            capture_output=True,
            text=True
        )
        
        success = result.returncode == 0
        output = result.stdout + result.stderr
        
        # Update ledger
        path = "." 
        action = f"Applied patch from {patch_path.name}"
        if proposal_summary:
            action += f" (Proposal: {proposal_summary})"
            
        goal = why_data.get("goal", "Unknown")
        command = f"patch -p1 -i {patch_path.name}"
        
        if success:
            append_recent_work(path, action, goal, command, "Success")
        else:
            append_failed_attempt(path, action, goal, command, f"Failed (exit {result.returncode})\n{output}")
            
        return success, output
        
    except Exception as e:
        return False, str(e)
