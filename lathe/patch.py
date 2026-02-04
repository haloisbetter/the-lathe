import os
import subprocess
import re
from pathlib import Path
from typing import List, Tuple

MAX_FILES_PER_PATCH = 5

def validate_patch(patch_content: str) -> List[str]:
    """
    Validates a unified diff patch strictly against abuse vectors.
    """
    lines = patch_content.splitlines()
    target_files = set()
    
    # SECURITY: Disallow mode/permission changes in patch metadata
    if re.search(r"^(old|new) mode \d+", patch_content, re.MULTILINE):
        raise ValueError("Patch attempt to modify file permissions/modes is disallowed.")

    for line in lines:
        if line.startswith("--- ") or line.startswith("+++ "):
            parts = line.split()
            if len(parts) >= 2:
                file_path = parts[1]
                # Strip common prefixes like a/ b/
                if file_path.startswith("a/") or file_path.startswith("b/"):
                    file_path = file_path[2:]
                
                # SECURITY: No absolute paths
                if os.path.isabs(file_path):
                    raise ValueError(f"Absolute path detected: {file_path}")
                
                # SECURITY: No path traversal
                if ".." in Path(file_path).parts:
                    raise ValueError(f"Path traversal detected: {file_path}")
                
                if file_path != "/dev/null":
                    target_files.add(file_path)
    
    if not target_files:
        raise ValueError("No target files found in patch")
    
    if len(target_files) > MAX_FILES_PER_PATCH:
        raise ValueError(f"Too many files in patch ({len(target_files)} > {MAX_FILES_PER_PATCH})")
        
    repo_root = Path.cwd().resolve()
    for f in target_files:
        target_path = Path(f).resolve()
        
        # SECURITY: Symlink escape protection - ensure target is within repo root
        if not str(target_path).startswith(str(repo_root)):
            raise ValueError(f"Patch target outside repository root: {f}")
            
        # SECURITY: Disallow modification of symlinks themselves
        if Path(f).is_symlink():
            raise ValueError(f"Patching symlinks is disallowed: {f}")

        if not Path(f).exists():
            # SECURITY: Disallow file creation outside existing directories
            if not Path(f).parent.exists():
                raise ValueError(f"Cannot create file in non-existent directory: {f}")
            
    return list(target_files)

def dry_run_patch(patch_path: Path) -> Tuple[bool, str]:
    """Performs a dry-run apply to check if hunks match target context."""
    try:
        result = subprocess.run(
            ["patch", "-p1", "--dry-run", "-i", str(patch_path)],
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)

def apply_patch(patch_path: Path, why_data: dict, proposal_summary: str = "") -> Tuple[bool, str]:
    """Apply a patch with re-validation and race condition protection."""
    from lathe.ledger import append_recent_work, append_failed_attempt
    
    try:
        subprocess.run(["patch", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False, "System 'patch' command not found"

    # SECURITY: Re-validate patch content before final apply to prevent TOCTOU
    patch_content = patch_path.read_text()
    try:
        validate_patch(patch_content)
    except ValueError as e:
        return False, f"Re-validation failed: {str(e)}"

    success_dry, output_dry = dry_run_patch(patch_path)
    if not success_dry:
        error_msg = f"Patch dry-run failed. Context might be stale.\n{output_dry}"
        append_failed_attempt(".", f"Dry-run failed for {patch_path.name}", why_data.get("goal", "Unknown"), f"patch --dry-run -i {patch_path.name}", error_msg)
        return False, error_msg

    try:
        # Actual apply - SECURITY: Use --reject-file=/dev/null to prevent residue on failure
        result = subprocess.run(
            ["patch", "-p1", "--reject-file=/dev/null", "-i", str(patch_path)],
            capture_output=True,
            text=True
        )
        
        success = result.returncode == 0
        output = result.stdout + result.stderr
        
        action = f"Applied patch from {patch_path.name}"
        if proposal_summary:
            action += f" (Proposal: {proposal_summary})"
            
        goal = why_data.get("goal", "Unknown")
        command = f"patch -p1 -i {patch_path.name}"
        
        if success:
            append_recent_work(".", action, goal, command, "Success")
        else:
            append_failed_attempt(".", action, goal, command, f"Failed (exit {result.returncode})\n{output}")
            
        return success, output
        
    except Exception as e:
        return False, str(e)
