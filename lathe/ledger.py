import os
from pathlib import Path
from datetime import datetime

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

def _append_to_section(ledger_path: Path, section_name: str, entry: str):
    """Internal helper to append an entry to a specific markdown section."""
    if not ledger_path.exists():
        ensure_ledger(str(ledger_path.parent))
    
    content = ledger_path.read_text()
    lines = content.splitlines()
    
    target_header = f"# {section_name}"
    section_index = -1
    for i, line in enumerate(lines):
        if line.strip() == target_header:
            section_index = i
            break
    
    if section_index == -1:
        # Section missing, append it at the end
        lines.append(f"\n# {section_name}")
        lines.append(entry)
    else:
        # Find the end of the section (next header or end of file)
        insert_index = len(lines)
        for i in range(section_index + 1, len(lines)):
            if lines[i].startswith("# "):
                insert_index = i
                break
        
        # Backtrack to find last non-empty line before next section
        while insert_index > section_index + 1 and not lines[insert_index-1].strip():
            insert_index -= 1
            
        lines.insert(insert_index, entry)
        
    ledger_path.write_text("\n".join(lines) + "\n")

def append_recent_work(path: str, action_summary: str, why_goal: str, command: str, result: str):
    """Append a success entry to 'Recent Work'."""
    ledger_path = find_ledger(path)
    timestamp = datetime.now().isoformat(sep=' ', timespec='seconds')
    entry = f"- [{timestamp}] {action_summary}\n  - Goal: {why_goal}\n  - Command: `{command}`\n  - Result: {result}"
    _append_to_section(ledger_path, "Recent Work", entry)

def append_failed_attempt(path: str, action_summary: str, why_goal: str, command: str, result: str):
    """Append a failure entry to 'Failed Attempts'."""
    ledger_path = find_ledger(path)
    timestamp = datetime.now().isoformat(sep=' ', timespec='seconds')
    entry = f"- [{timestamp}] {action_summary}\n  - Goal: {why_goal}\n  - Command: `{command}`\n  - Result: {result}"
    _append_to_section(ledger_path, "Failed Attempts", entry)
