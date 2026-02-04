import os
from pathlib import Path

LEDGER_FILENAME = ".lathe.md"

DEFAULT_LEDGER_TEMPLATE = """# Purpose
(Describe the purpose of this folder)

# Known Invariants
- (List stable rules or facts about this directory)

# Recent Work
- (List recent changes or milestones)

# Failed Attempts
- (List what didn't work and why)

# Open Questions
- (List unresolved items)

# Agent Notes
- (Internal notes for agent context)
"""

def find_ledger(start_path: str) -> Path:
    """Find the nearest .lathe.md in the directory tree starting from start_path upwards."""
    current = Path(start_path).resolve()
    if current.is_file():
        current = current.parent
    
    while True:
        ledger_path = current / LEDGER_FILENAME
        if ledger_path.exists():
            return ledger_path
        if current.parent == current: # Root reached
            break
        current = current.parent
    
    return Path(start_path).resolve() / LEDGER_FILENAME if Path(start_path).resolve().is_dir() else Path(start_path).resolve().parent / LEDGER_FILENAME

def ensure_ledger(path: str) -> Path:
    """Find or create a .lathe.md file at the specified directory."""
    target_dir = Path(path).resolve()
    if target_dir.is_file():
        target_dir = target_dir.parent
        
    ledger_path = target_dir / LEDGER_FILENAME
    if not ledger_path.exists():
        ledger_path.write_text(DEFAULT_LEDGER_TEMPLATE)
    return ledger_path

def read_ledger(path: str) -> str:
    """Read the content of the nearest ledger."""
    ledger_path = find_ledger(path)
    if ledger_path.exists():
        return ledger_path.read_text()
    return "No ledger found."
