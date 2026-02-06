"""
Git-backed Workspace

Safe subprocess wrapper for git operations within workspace boundaries.

SAFETY GUARANTEES:
- Whitelisted git commands only (clone, pull, status, commit, push, log, branch, rev-parse)
- No shell=True (subprocess.run with list args only)
- cwd ALWAYS locked to workspace directory
- No credentials logged or returned
- SSH auth preferred; HTTPS tokens allowed if stored outside the repo

All git operations live ONLY in the app layer.
The kernel (lathe/) MUST NEVER access git or subprocess.
"""
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ALLOWED_GIT_COMMANDS = frozenset({
    "clone", "pull", "status", "commit", "push",
    "log", "branch", "rev-parse", "diff", "remote",
    "init", "add",
})

CREDENTIAL_PATTERNS = [
    re.compile(r"https?://[^@]+@", re.IGNORECASE),
    re.compile(r"(password|token|secret|credential)[=:]\S+", re.IGNORECASE),
]

GIT_TIMEOUT_SECONDS = 120


@dataclass
class GitResult:
    success: bool
    operation: str
    workspace: str
    branch: Optional[str] = None
    clean: Optional[bool] = None
    stdout: str = ""
    stderr: str = ""
    refusal_reason: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "success": self.success,
            "operation": self.operation,
            "workspace": self.workspace,
            "branch": self.branch,
            "clean": self.clean,
            "timestamp": self.timestamp,
        }
        if self.refusal_reason:
            d["refusal_reason"] = self.refusal_reason
        if self.stdout:
            d["stdout"] = self.stdout
        if self.stderr:
            d["stderr"] = self.stderr
        return d


def _redact_credentials(text: str) -> str:
    result = text
    for pattern in CREDENTIAL_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result


def _run_git(
    args: List[str],
    cwd: str,
    timeout: int = GIT_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess:
    if not args:
        raise ValueError("Empty git command")

    subcmd = args[0]
    if subcmd not in ALLOWED_GIT_COMMANDS:
        raise ValueError(f"Git command not allowed: {subcmd}")

    cmd = ["git"] + args

    logger.info("git %s in %s", subcmd, cwd)

    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class GitWorkspace:
    def __init__(self, workspace_root: str, workspace_id: str = ""):
        abs_root = os.path.abspath(workspace_root)
        if not os.path.isdir(abs_root):
            raise ValueError(f"Workspace root does not exist: {abs_root}")
        self._root = abs_root
        self._workspace_id = workspace_id or os.path.basename(abs_root)

    @property
    def root(self) -> str:
        return self._root

    @property
    def workspace_id(self) -> str:
        return self._workspace_id

    def is_git_repo(self) -> bool:
        git_dir = os.path.join(self._root, ".git")
        return os.path.isdir(git_dir)

    def _require_repo(self) -> Optional[str]:
        if not self.is_git_repo():
            return f"Not a git repository: {self._root}"
        return None

    def _get_branch(self) -> Optional[str]:
        try:
            result = _run_git(
                ["rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self._root,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def _is_clean(self) -> Optional[bool]:
        try:
            result = _run_git(
                ["status", "--porcelain"],
                cwd=self._root,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip() == ""
        except Exception:
            pass
        return None

    def clone(self, repo_url: str, branch: Optional[str] = None) -> GitResult:
        if self.is_git_repo():
            return GitResult(
                success=False,
                operation="clone",
                workspace=self._workspace_id,
                refusal_reason="Directory already contains a git repository",
            )

        args = ["clone", repo_url, "."]
        if branch:
            args = ["clone", "--branch", branch, repo_url, "."]

        try:
            result = _run_git(args, cwd=self._root)
            if result.returncode == 0:
                return GitResult(
                    success=True,
                    operation="clone",
                    workspace=self._workspace_id,
                    branch=self._get_branch(),
                    clean=True,
                    stdout=_redact_credentials(result.stdout),
                )
            else:
                return GitResult(
                    success=False,
                    operation="clone",
                    workspace=self._workspace_id,
                    stderr=_redact_credentials(result.stderr),
                    refusal_reason=f"git clone failed (exit {result.returncode})",
                )
        except subprocess.TimeoutExpired:
            return GitResult(
                success=False,
                operation="clone",
                workspace=self._workspace_id,
                refusal_reason="git clone timed out",
            )
        except Exception as e:
            return GitResult(
                success=False,
                operation="clone",
                workspace=self._workspace_id,
                refusal_reason=f"git clone error: {str(e)}",
            )

    def pull(self) -> GitResult:
        err = self._require_repo()
        if err:
            return GitResult(
                success=False,
                operation="pull",
                workspace=self._workspace_id,
                refusal_reason=err,
            )

        try:
            result = _run_git(["pull"], cwd=self._root)
            return GitResult(
                success=result.returncode == 0,
                operation="pull",
                workspace=self._workspace_id,
                branch=self._get_branch(),
                clean=self._is_clean(),
                stdout=_redact_credentials(result.stdout),
                stderr=_redact_credentials(result.stderr) if result.returncode != 0 else "",
                refusal_reason=f"git pull failed (exit {result.returncode})" if result.returncode != 0 else None,
            )
        except subprocess.TimeoutExpired:
            return GitResult(
                success=False,
                operation="pull",
                workspace=self._workspace_id,
                refusal_reason="git pull timed out",
            )

    def status(self) -> GitResult:
        err = self._require_repo()
        if err:
            return GitResult(
                success=False,
                operation="status",
                workspace=self._workspace_id,
                refusal_reason=err,
            )

        try:
            result = _run_git(["status", "--porcelain"], cwd=self._root)
            branch = self._get_branch()
            clean = result.stdout.strip() == "" if result.returncode == 0 else None

            return GitResult(
                success=result.returncode == 0,
                operation="status",
                workspace=self._workspace_id,
                branch=branch,
                clean=clean,
                stdout=result.stdout,
                stderr=result.stderr if result.returncode != 0 else "",
            )
        except subprocess.TimeoutExpired:
            return GitResult(
                success=False,
                operation="status",
                workspace=self._workspace_id,
                refusal_reason="git status timed out",
            )

    def commit(self, message: str) -> GitResult:
        err = self._require_repo()
        if err:
            return GitResult(
                success=False,
                operation="commit",
                workspace=self._workspace_id,
                refusal_reason=err,
            )

        if not message or not message.strip():
            return GitResult(
                success=False,
                operation="commit",
                workspace=self._workspace_id,
                refusal_reason="Commit message cannot be empty",
            )

        try:
            add_result = _run_git(["add", "-A"], cwd=self._root)
            if add_result.returncode != 0:
                return GitResult(
                    success=False,
                    operation="commit",
                    workspace=self._workspace_id,
                    stderr=add_result.stderr,
                    refusal_reason=f"git add failed (exit {add_result.returncode})",
                )

            result = _run_git(["commit", "-m", message], cwd=self._root)

            if result.returncode == 0:
                return GitResult(
                    success=True,
                    operation="commit",
                    workspace=self._workspace_id,
                    branch=self._get_branch(),
                    clean=True,
                    stdout=result.stdout,
                )
            elif "nothing to commit" in result.stdout.lower() or "nothing to commit" in result.stderr.lower():
                return GitResult(
                    success=True,
                    operation="commit",
                    workspace=self._workspace_id,
                    branch=self._get_branch(),
                    clean=True,
                    stdout="Nothing to commit, working tree clean",
                )
            else:
                return GitResult(
                    success=False,
                    operation="commit",
                    workspace=self._workspace_id,
                    stderr=result.stderr,
                    refusal_reason=f"git commit failed (exit {result.returncode})",
                )
        except subprocess.TimeoutExpired:
            return GitResult(
                success=False,
                operation="commit",
                workspace=self._workspace_id,
                refusal_reason="git commit timed out",
            )

    def push(self) -> GitResult:
        err = self._require_repo()
        if err:
            return GitResult(
                success=False,
                operation="push",
                workspace=self._workspace_id,
                refusal_reason=err,
            )

        try:
            result = _run_git(["push"], cwd=self._root)
            return GitResult(
                success=result.returncode == 0,
                operation="push",
                workspace=self._workspace_id,
                branch=self._get_branch(),
                clean=self._is_clean(),
                stdout=_redact_credentials(result.stdout),
                stderr=_redact_credentials(result.stderr) if result.returncode != 0 else "",
                refusal_reason=f"git push failed (exit {result.returncode})" if result.returncode != 0 else None,
            )
        except subprocess.TimeoutExpired:
            return GitResult(
                success=False,
                operation="push",
                workspace=self._workspace_id,
                refusal_reason="git push timed out",
            )

    def init(self) -> GitResult:
        if self.is_git_repo():
            return GitResult(
                success=False,
                operation="init",
                workspace=self._workspace_id,
                refusal_reason="Directory already contains a git repository",
            )

        try:
            result = _run_git(["init"], cwd=self._root)
            return GitResult(
                success=result.returncode == 0,
                operation="init",
                workspace=self._workspace_id,
                branch=self._get_branch() if result.returncode == 0 else None,
                clean=True if result.returncode == 0 else None,
                stdout=result.stdout,
                stderr=result.stderr if result.returncode != 0 else "",
            )
        except subprocess.TimeoutExpired:
            return GitResult(
                success=False,
                operation="init",
                workspace=self._workspace_id,
                refusal_reason="git init timed out",
            )
