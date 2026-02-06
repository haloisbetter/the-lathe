"""
Tests for Git-backed Workspace support.

Covers:
- GitWorkspace operations (clone, pull, status, commit, push, init)
- Command whitelisting and credential redaction
- Trust policy gating for git operations
- Auto-commit/push flow after execution
- Kernel remains untouched
- Boundary checks and workspace isolation
"""
import json
import os
import tempfile
from unittest.mock import patch, MagicMock
import subprocess

import pytest

from lathe_app.workspace.git_workspace import (
    GitWorkspace,
    GitResult,
    _redact_credentials,
    _run_git,
    ALLOWED_GIT_COMMANDS,
)
from lathe_app.trust import (
    TrustPolicy,
    TrustEvaluation,
    evaluate_git_trust,
)


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def mock_git_repo(tmp_dir):
    os.makedirs(os.path.join(tmp_dir, ".git"))
    return tmp_dir


def _mock_completed_process(stdout="", stderr="", returncode=0):
    cp = subprocess.CompletedProcess(args=["git"], returncode=returncode)
    cp.stdout = stdout
    cp.stderr = stderr
    return cp


class TestGitWorkspaceInit:
    def test_create_with_valid_dir(self, tmp_dir):
        gw = GitWorkspace(tmp_dir, workspace_id="test-ws")
        assert gw.root == os.path.abspath(tmp_dir)
        assert gw.workspace_id == "test-ws"

    def test_create_with_invalid_dir(self):
        with pytest.raises(ValueError, match="does not exist"):
            GitWorkspace("/nonexistent/path/xyz")

    def test_default_workspace_id(self, tmp_dir):
        gw = GitWorkspace(tmp_dir)
        assert gw.workspace_id == os.path.basename(tmp_dir)

    def test_is_git_repo_false(self, tmp_dir):
        gw = GitWorkspace(tmp_dir)
        assert gw.is_git_repo() is False

    def test_is_git_repo_true(self, mock_git_repo):
        gw = GitWorkspace(mock_git_repo)
        assert gw.is_git_repo() is True


class TestGitWorkspaceStatus:
    @patch("lathe_app.workspace.git_workspace._run_git")
    def test_status_clean_repo(self, mock_run, mock_git_repo):
        mock_run.side_effect = [
            _mock_completed_process(stdout=""),
            _mock_completed_process(stdout="main"),
        ]
        gw = GitWorkspace(mock_git_repo, workspace_id="test")
        result = gw.status()
        assert result.success is True
        assert result.operation == "status"
        assert result.clean is True

    @patch("lathe_app.workspace.git_workspace._run_git")
    def test_status_dirty_repo(self, mock_run, mock_git_repo):
        mock_run.side_effect = [
            _mock_completed_process(stdout="M file.py\n"),
            _mock_completed_process(stdout="main"),
        ]
        gw = GitWorkspace(mock_git_repo, workspace_id="test")
        result = gw.status()
        assert result.success is True
        assert result.clean is False

    def test_status_on_non_repo(self, tmp_dir):
        gw = GitWorkspace(tmp_dir, workspace_id="test")
        result = gw.status()
        assert result.success is False
        assert "Not a git repository" in result.refusal_reason

    @patch("lathe_app.workspace.git_workspace._run_git")
    def test_status_timeout(self, mock_run, mock_git_repo):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=120)
        gw = GitWorkspace(mock_git_repo, workspace_id="test")
        result = gw.status()
        assert result.success is False
        assert "timed out" in result.refusal_reason


class TestGitWorkspaceCommit:
    @patch("lathe_app.workspace.git_workspace._run_git")
    def test_commit_with_changes(self, mock_run, mock_git_repo):
        mock_run.side_effect = [
            _mock_completed_process(),
            _mock_completed_process(stdout="[main abc123] test commit\n 1 file changed"),
            _mock_completed_process(stdout="main"),
        ]
        gw = GitWorkspace(mock_git_repo, workspace_id="test")
        result = gw.commit("test commit message")
        assert result.success is True
        assert result.operation == "commit"

    @patch("lathe_app.workspace.git_workspace._run_git")
    def test_commit_nothing_to_commit(self, mock_run, mock_git_repo):
        mock_run.side_effect = [
            _mock_completed_process(),
            _mock_completed_process(stdout="nothing to commit, working tree clean", returncode=1),
            _mock_completed_process(stdout="main"),
        ]
        gw = GitWorkspace(mock_git_repo, workspace_id="test")
        result = gw.commit("empty commit")
        assert result.success is True

    def test_commit_empty_message_refused(self, mock_git_repo):
        gw = GitWorkspace(mock_git_repo, workspace_id="test")
        result = gw.commit("")
        assert result.success is False
        assert "empty" in result.refusal_reason.lower()

    def test_commit_whitespace_message_refused(self, mock_git_repo):
        gw = GitWorkspace(mock_git_repo, workspace_id="test")
        result = gw.commit("   ")
        assert result.success is False

    def test_commit_on_non_repo(self, tmp_dir):
        gw = GitWorkspace(tmp_dir, workspace_id="test")
        result = gw.commit("test")
        assert result.success is False

    @patch("lathe_app.workspace.git_workspace._run_git")
    def test_commit_add_fails(self, mock_run, mock_git_repo):
        mock_run.return_value = _mock_completed_process(returncode=1, stderr="error")
        gw = GitWorkspace(mock_git_repo, workspace_id="test")
        result = gw.commit("test")
        assert result.success is False
        assert "git add failed" in result.refusal_reason


class TestGitWorkspaceInitRepo:
    @patch("lathe_app.workspace.git_workspace._run_git")
    def test_init_new_repo(self, mock_run, tmp_dir):
        mock_run.side_effect = [
            _mock_completed_process(stdout="Initialized empty Git repository"),
            _mock_completed_process(stdout="main"),
        ]
        gw = GitWorkspace(tmp_dir, workspace_id="test")
        result = gw.init()
        assert result.success is True
        assert result.operation == "init"

    def test_init_existing_repo_refused(self, mock_git_repo):
        gw = GitWorkspace(mock_git_repo, workspace_id="test")
        result = gw.init()
        assert result.success is False
        assert "already contains" in result.refusal_reason


class TestGitWorkspaceClone:
    def test_clone_into_existing_repo_refused(self, mock_git_repo):
        gw = GitWorkspace(mock_git_repo, workspace_id="test")
        result = gw.clone("https://example.com/repo.git")
        assert result.success is False
        assert "already contains" in result.refusal_reason

    @patch("lathe_app.workspace.git_workspace._run_git")
    def test_clone_success(self, mock_run, tmp_dir):
        mock_run.side_effect = [
            _mock_completed_process(stdout="Cloning into '.'..."),
            _mock_completed_process(stdout="main"),
        ]
        gw = GitWorkspace(tmp_dir, workspace_id="test")
        result = gw.clone("git@github.com:user/repo.git")
        assert result.success is True
        assert result.operation == "clone"

    @patch("lathe_app.workspace.git_workspace._run_git")
    def test_clone_with_branch(self, mock_run, tmp_dir):
        mock_run.side_effect = [
            _mock_completed_process(stdout="Cloning into '.'..."),
            _mock_completed_process(stdout="develop"),
        ]
        gw = GitWorkspace(tmp_dir, workspace_id="test")
        result = gw.clone("git@github.com:user/repo.git", branch="develop")
        assert result.success is True

        call_args = mock_run.call_args_list[0]
        args = call_args[0][0]
        assert "--branch" in args
        assert "develop" in args

    @patch("lathe_app.workspace.git_workspace._run_git")
    def test_clone_failure(self, mock_run, tmp_dir):
        mock_run.return_value = _mock_completed_process(
            returncode=128, stderr="fatal: repository not found"
        )
        gw = GitWorkspace(tmp_dir, workspace_id="test")
        result = gw.clone("bad-url")
        assert result.success is False
        assert "failed" in result.refusal_reason


class TestGitWorkspacePull:
    @patch("lathe_app.workspace.git_workspace._run_git")
    def test_pull_success(self, mock_run, mock_git_repo):
        mock_run.side_effect = [
            _mock_completed_process(stdout="Already up to date."),
            _mock_completed_process(stdout="main"),
            _mock_completed_process(stdout=""),
        ]
        gw = GitWorkspace(mock_git_repo, workspace_id="test")
        result = gw.pull()
        assert result.success is True
        assert result.operation == "pull"

    def test_pull_non_repo(self, tmp_dir):
        gw = GitWorkspace(tmp_dir, workspace_id="test")
        result = gw.pull()
        assert result.success is False

    @patch("lathe_app.workspace.git_workspace._run_git")
    def test_pull_timeout(self, mock_run, mock_git_repo):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=120)
        gw = GitWorkspace(mock_git_repo, workspace_id="test")
        result = gw.pull()
        assert result.success is False
        assert "timed out" in result.refusal_reason


class TestGitWorkspacePush:
    @patch("lathe_app.workspace.git_workspace._run_git")
    def test_push_success(self, mock_run, mock_git_repo):
        mock_run.side_effect = [
            _mock_completed_process(stdout="Everything up-to-date"),
            _mock_completed_process(stdout="main"),
            _mock_completed_process(stdout=""),
        ]
        gw = GitWorkspace(mock_git_repo, workspace_id="test")
        result = gw.push()
        assert result.success is True
        assert result.operation == "push"

    def test_push_non_repo(self, tmp_dir):
        gw = GitWorkspace(tmp_dir, workspace_id="test")
        result = gw.push()
        assert result.success is False


class TestGitResultSerialization:
    def test_to_dict_success(self):
        r = GitResult(
            success=True,
            operation="status",
            workspace="test-ws",
            branch="main",
            clean=True,
            stdout="",
        )
        d = r.to_dict()
        assert d["success"] is True
        assert d["operation"] == "status"
        assert d["workspace"] == "test-ws"
        assert d["branch"] == "main"
        assert d["clean"] is True
        assert "timestamp" in d

    def test_to_dict_failure_with_refusal(self):
        r = GitResult(
            success=False,
            operation="push",
            workspace="test-ws",
            refusal_reason="trust denied",
        )
        d = r.to_dict()
        assert d["success"] is False
        assert d["refusal_reason"] == "trust denied"

    def test_to_dict_excludes_empty_fields(self):
        r = GitResult(
            success=True,
            operation="status",
            workspace="test-ws",
        )
        d = r.to_dict()
        assert "refusal_reason" not in d
        assert "stdout" not in d
        assert "stderr" not in d


class TestCredentialRedaction:
    def test_redacts_https_token(self):
        text = "https://user:ghp_secret123@github.com/repo.git"
        redacted = _redact_credentials(text)
        assert "ghp_secret123" not in redacted
        assert "[REDACTED]" in redacted

    def test_redacts_password_field(self):
        text = "password=mysecretpass"
        redacted = _redact_credentials(text)
        assert "mysecretpass" not in redacted

    def test_redacts_token_field(self):
        text = "token:abc123xyz"
        redacted = _redact_credentials(text)
        assert "abc123xyz" not in redacted

    def test_clean_text_unchanged(self):
        text = "Already up to date."
        assert _redact_credentials(text) == text


class TestCommandWhitelist:
    def test_allowed_commands(self):
        for cmd in ["clone", "pull", "status", "commit", "push", "log", "init", "add"]:
            assert cmd in ALLOWED_GIT_COMMANDS

    def test_disallowed_command_raises(self, tmp_dir):
        with pytest.raises(ValueError, match="not allowed"):
            _run_git(["rm", "-rf", "."], cwd=tmp_dir)

    def test_empty_command_raises(self, tmp_dir):
        with pytest.raises(ValueError, match="Empty"):
            _run_git([], cwd=tmp_dir)

    def test_dangerous_commands_blocked(self, tmp_dir):
        for cmd in ["rm", "reset", "clean", "rebase", "filter-branch", "reflog"]:
            with pytest.raises(ValueError, match="not allowed"):
                _run_git([cmd], cwd=tmp_dir)


class TestGitTrustEvaluation:
    def test_read_ops_allowed_at_trust_0(self):
        policy = TrustPolicy(trust_level=0)
        for op in ["clone", "pull", "status"]:
            eval_result = evaluate_git_trust(policy, op)
            assert eval_result.allowed is True, f"{op} should be allowed at trust 0"

    def test_commit_denied_at_trust_0(self):
        policy = TrustPolicy(trust_level=0)
        eval_result = evaluate_git_trust(policy, "commit")
        assert eval_result.allowed is False
        assert "trust level >= 2" in eval_result.reason

    def test_commit_denied_at_trust_1(self):
        policy = TrustPolicy(trust_level=1)
        eval_result = evaluate_git_trust(policy, "commit")
        assert eval_result.allowed is False

    def test_commit_allowed_at_trust_2(self):
        policy = TrustPolicy(trust_level=2)
        eval_result = evaluate_git_trust(policy, "commit")
        assert eval_result.allowed is True

    def test_push_denied_at_trust_2(self):
        policy = TrustPolicy(trust_level=2)
        eval_result = evaluate_git_trust(policy, "push")
        assert eval_result.allowed is False
        assert "trust level >= 3" in eval_result.reason

    def test_push_allowed_at_trust_3(self):
        policy = TrustPolicy(trust_level=3)
        eval_result = evaluate_git_trust(policy, "push")
        assert eval_result.allowed is True

    def test_all_ops_allowed_at_trust_4(self):
        policy = TrustPolicy(trust_level=4)
        for op in ["clone", "pull", "status", "commit", "push"]:
            eval_result = evaluate_git_trust(policy, op)
            assert eval_result.allowed is True, f"{op} should be allowed at trust 4"

    def test_unknown_operation_denied_at_low_trust(self):
        policy = TrustPolicy(trust_level=1)
        eval_result = evaluate_git_trust(policy, "rebase")
        assert eval_result.allowed is False
        assert "Unknown" in eval_result.reason

    def test_unknown_operation_allowed_at_trust_4(self):
        policy = TrustPolicy(trust_level=4)
        eval_result = evaluate_git_trust(policy, "rebase")
        assert eval_result.allowed is True

    def test_trust_from_workspace_file(self, tmp_dir):
        lathe_dir = os.path.join(tmp_dir, ".lathe")
        os.makedirs(lathe_dir)
        with open(os.path.join(lathe_dir, "trust.json"), "w") as f:
            json.dump({"trust_level": 3}, f)

        policy = TrustPolicy.load_from_workspace(tmp_dir)
        assert policy.trust_level == 3

        commit_eval = evaluate_git_trust(policy, "commit", workspace_root=tmp_dir)
        assert commit_eval.allowed is True

        push_eval = evaluate_git_trust(policy, "push", workspace_root=tmp_dir)
        assert push_eval.allowed is True

    def test_default_trust_denies_commit_push(self, tmp_dir):
        policy = TrustPolicy.load_from_workspace(tmp_dir)
        assert policy.trust_level == 0

        commit_eval = evaluate_git_trust(policy, "commit")
        assert commit_eval.allowed is False

        push_eval = evaluate_git_trust(policy, "push")
        assert push_eval.allowed is False


class TestAutoCommitFlow:
    def test_auto_commit_not_applied_skips(self, mock_git_repo):
        from lathe_app.executor import ExecutionResult, auto_commit_after_execution
        result = ExecutionResult.dry_run([], workspace_id="test")
        auto = auto_commit_after_execution(
            result, mock_git_repo, "test", "run-1",
        )
        assert auto is None

    def test_auto_commit_trust_denied(self, mock_git_repo):
        from lathe_app.executor import ExecutionResult, ExecutionStatus, auto_commit_after_execution
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            diff=[{"operation": "modify", "target": "f.py", "status": "applied"}],
            applied=True,
            workspace_id="test",
        )
        auto = auto_commit_after_execution(
            result, mock_git_repo, "test", "run-1",
        )
        assert auto is not None
        assert auto["performed"] is False
        assert "trust" in auto["reason"].lower()

    @patch("lathe_app.workspace.git_workspace._run_git")
    def test_auto_commit_with_trust_2(self, mock_run, mock_git_repo):
        from lathe_app.executor import ExecutionResult, ExecutionStatus, auto_commit_after_execution
        lathe_dir = os.path.join(mock_git_repo, ".lathe")
        os.makedirs(lathe_dir)
        with open(os.path.join(lathe_dir, "trust.json"), "w") as f:
            json.dump({"trust_level": 2}, f)

        mock_run.side_effect = [
            _mock_completed_process(),
            _mock_completed_process(stdout="[main abc] Lathe: add file\n 1 file changed"),
            _mock_completed_process(stdout="main"),
        ]

        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            diff=[{"operation": "create", "target": "new_file.py", "status": "applied"}],
            applied=True,
            workspace_id="test",
        )
        auto = auto_commit_after_execution(
            result, mock_git_repo, "test", "run-1", task_summary="add new file",
        )
        assert auto is not None
        assert auto["performed"] is True
        assert auto["commit"]["success"] is True
        assert auto["auto_push"] is None

    @patch("lathe_app.workspace.git_workspace._run_git")
    def test_auto_commit_and_push_with_trust_3(self, mock_run, mock_git_repo):
        from lathe_app.executor import ExecutionResult, ExecutionStatus, auto_commit_after_execution
        lathe_dir = os.path.join(mock_git_repo, ".lathe")
        os.makedirs(lathe_dir)
        with open(os.path.join(lathe_dir, "trust.json"), "w") as f:
            json.dump({"trust_level": 3}, f)

        mock_run.side_effect = [
            _mock_completed_process(),
            _mock_completed_process(stdout="[main abc] Lathe: commit\n 1 file changed"),
            _mock_completed_process(stdout="main"),
            _mock_completed_process(stdout="Everything up-to-date"),
            _mock_completed_process(stdout="main"),
            _mock_completed_process(stdout=""),
        ]

        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            diff=[{"operation": "create", "target": "app.py", "status": "applied"}],
            applied=True,
            workspace_id="test",
        )
        auto = auto_commit_after_execution(
            result, mock_git_repo, "test", "run-1",
        )
        assert auto is not None
        assert auto["performed"] is True
        assert auto["auto_push"] is not None

    def test_auto_commit_non_git_workspace(self, tmp_dir):
        from lathe_app.executor import ExecutionResult, ExecutionStatus, auto_commit_after_execution
        lathe_dir = os.path.join(tmp_dir, ".lathe")
        os.makedirs(lathe_dir)
        with open(os.path.join(lathe_dir, "trust.json"), "w") as f:
            json.dump({"trust_level": 2}, f)

        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            diff=[],
            applied=True,
            workspace_id="test",
        )
        auto = auto_commit_after_execution(
            result, tmp_dir, "test", "run-1",
        )
        assert auto is not None
        assert auto["performed"] is False
        assert "not a git repository" in auto["reason"].lower()


class TestKernelUntouched:
    def test_no_git_workspace_in_kernel(self):
        import lathe
        kernel_dir = os.path.dirname(lathe.__file__)
        for root, dirs, files in os.walk(kernel_dir):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath) as f:
                    content = f.read()
                assert "git_workspace" not in content, (
                    f"Kernel file {fpath} references git_workspace"
                )
                assert "GitWorkspace" not in content, (
                    f"Kernel file {fpath} references GitWorkspace"
                )
                assert "evaluate_git_trust" not in content, (
                    f"Kernel file {fpath} references evaluate_git_trust"
                )

    def test_no_git_commit_push_in_kernel(self):
        import lathe
        kernel_dir = os.path.dirname(lathe.__file__)
        git_write_patterns = [
            "git commit", "git push", "git add -A",
            ".commit(", ".push(",
        ]
        for root, dirs, files in os.walk(kernel_dir):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath) as f:
                    content = f.read()
                for pattern in git_write_patterns:
                    assert pattern not in content, (
                        f"Kernel file {fpath} contains git write pattern: '{pattern}'"
                    )


class TestGitOpsOnlyInAppLayer:
    def test_git_workspace_in_app_layer(self):
        from lathe_app.workspace.git_workspace import GitWorkspace
        import inspect
        source_file = inspect.getfile(GitWorkspace)
        assert "lathe_app" in source_file
        assert "lathe/" not in source_file.replace("lathe_app", "")

    def test_evaluate_git_trust_in_app_layer(self):
        import inspect
        source_file = inspect.getfile(evaluate_git_trust)
        assert "lathe_app" in source_file


class TestWorkspaceBoundaryChecks:
    def test_git_workspace_cwd_locked(self, mock_git_repo):
        gw = GitWorkspace(mock_git_repo, workspace_id="test")
        assert gw.root == os.path.abspath(mock_git_repo)

    def test_workspace_id_propagated(self, tmp_dir):
        gw = GitWorkspace(tmp_dir, workspace_id="my-project")
        result = gw.clone("not-a-url")
        assert result.workspace == "my-project"


class TestEndToEndFlow:
    @patch("lathe_app.workspace.git_workspace._run_git")
    def test_propose_commit_flow(self, mock_run, mock_git_repo):
        """End-to-end: propose → execute → auto-commit."""
        from lathe_app.executor import ExecutionResult, ExecutionStatus, auto_commit_after_execution

        lathe_dir = os.path.join(mock_git_repo, ".lathe")
        os.makedirs(lathe_dir)
        with open(os.path.join(lathe_dir, "trust.json"), "w") as f:
            json.dump({"trust_level": 2}, f)

        mock_run.side_effect = [
            _mock_completed_process(),
            _mock_completed_process(stdout="[main abc123] Lathe: add feature.py\n 1 file changed"),
            _mock_completed_process(stdout="main"),
        ]

        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            diff=[{"operation": "create", "target": "feature.py", "status": "applied"}],
            applied=True,
            workspace_id="test-ws",
        )

        auto = auto_commit_after_execution(
            result, mock_git_repo, "test-ws", "run-42", task_summary="add feature.py",
        )

        assert auto is not None
        assert auto["performed"] is True
        assert auto["commit"]["success"] is True

    def test_full_trust_matrix(self):
        """Verify the complete trust matrix for git operations."""
        matrix = {
            0: {"clone": True, "pull": True, "status": True, "commit": False, "push": False},
            1: {"clone": True, "pull": True, "status": True, "commit": False, "push": False},
            2: {"clone": True, "pull": True, "status": True, "commit": True, "push": False},
            3: {"clone": True, "pull": True, "status": True, "commit": True, "push": True},
            4: {"clone": True, "pull": True, "status": True, "commit": True, "push": True},
        }

        for level, ops in matrix.items():
            policy = TrustPolicy(trust_level=level)
            for op, expected in ops.items():
                eval_result = evaluate_git_trust(policy, op)
                assert eval_result.allowed == expected, (
                    f"Trust {level}, op {op}: expected allowed={expected}, got {eval_result.allowed}"
                )
