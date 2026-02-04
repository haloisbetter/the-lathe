import os
import subprocess
from pathlib import Path
from typing import List, Tuple
from lathe.why import validate_why_record
from lathe.ledger import append_recent_work, append_failed_attempt

MAX_FILES_PER_PATCH = 5

def validate_patch(patch_content: str) -> List[str]:
    """Basic validation of a unified diff patch."""
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
                target_files.add(file_path)
    
    if not target_files:
        raise ValueError("No target files found in patch")
    
    if len(target_files) > MAX_FILES_PER_PATCH:
        raise ValueError(f"Too many files in patch ({len(target_files)} > {MAX_FILES_PER_PATCH})")
        
    for f in target_files:
        if not Path(f).exists():
            raise ValueError(f"Target file does not exist: {f}")
            
    return list(target_files)

def apply_patch(patch_path: Path, why_data: dict, proposal_summary: str = None) -> Tuple[bool, str]:
    """Apply a patch using the system 'patch' command."""
    try:
        # Check if patch command exists
        subprocess.run(["patch", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False, "System 'patch' command not found"

    try:
        # Apply patch
        # -p1 is common for git diffs
        result = subprocess.run(
            ["patch", "-p1", "-i", str(patch_path)],
            capture_output=True,
            text=True
        )
        
        success = result.returncode == 0
        output = result.stdout + result.stderr
        
        # Update ledger
        path = "." # Assume root for now
        action = f"Applied patch from {patch_path.name}"
        if proposal_summary:
            action += f" (Proposal: {proposal_summary})"
            
        goal = why_data.get("goal", "Unknown")
        command = f"patch -p1 -i {patch_path.name}"
        
        if success:
            append_recent_work(path, action, goal, command, "Success")
        else:
            append_failed_attempt(path, action, goal, command, f"Failed (exit {result.returncode})")
            
        return success, output
        
    except Exception as e:
        return False, str(e)
