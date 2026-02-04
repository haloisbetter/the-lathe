import subprocess
import os
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
from lathe.why import validate_why_record

ALLOWED_COMMANDS = {
    "python", "python3", "pytest", "node", "npm", "pnpm", "yarn",
    "ruff", "black", "mypy", "eslint", "tsc", "go", "cargo", "make"
}

DENIED_SUBSTRINGS = {"sudo", "rm ", "del ", "format", "diskpart", "reg "}

@dataclass
class ExecResult:
    stdout: str
    stderr: str
    exit_code: int
    timeout_flag: bool

def run_safe_command(cwd: str, command: List[str], timeout: int = 60) -> ExecResult:
    """Execute a command safely within a directory."""
    cwd_path = Path(cwd).resolve()
    if not cwd_path.exists():
        raise ValueError(f"Working directory does not exist: {cwd}")

    if not command:
        raise ValueError("No command provided")

    base_cmd = command[0]
    if base_cmd not in ALLOWED_COMMANDS:
        raise ValueError(f"Command not in allowlist: {base_cmd}")

    full_cmd_str = " ".join(command)
    for forbidden in DENIED_SUBSTRINGS:
        if forbidden in full_cmd_str:
            raise ValueError(f"Command contains forbidden substring: {forbidden}")

    # Basic safety: ensure we are not trying to 'cd' out via the command itself if it were shell=True
    # But subprocess.run with list handles args safely.

    try:
        process = subprocess.run(
            command,
            cwd=cwd_path,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return ExecResult(
            stdout=process.stdout,
            stderr=process.stderr,
            exit_code=process.returncode,
            timeout_flag=False
        )
    except subprocess.TimeoutExpired as e:
        return ExecResult(
            stdout=e.stdout.decode() if e.stdout else "",
            stderr=e.stderr.decode() if e.stderr else "",
            exit_code=-1,
            timeout_flag=True
        )
    except Exception as e:
        return ExecResult(
            stdout="",
            stderr=str(e),
            exit_code=-1,
            timeout_flag=False
        )

def validate_why_input(why_input: str):
    """Validate WHY input which can be a file path or a JSON string."""
    if os.path.exists(why_input):
        with open(why_input, 'r') as f:
            data = json.load(f)
    else:
        data = json.loads(why_input)
    
    validate_why_record(data)
    return data
