"""
Tests for lathe_app.tools — Tool Registry and Handlers

Covers:
- Registry determinism and completeness
- Tool invocation with workspace boundary enforcement
- Trust level gating
- fs_tree, fs_stats, git_status handlers
"""
import json
import os
import subprocess
import tempfile

import pytest

from lathe_app.tools.registry import ToolSpec, TOOL_REGISTRY, get_tool_spec
from lathe_app.tools.handlers import (
    handle_fs_tree,
    handle_fs_stats,
    handle_git_status,
    TOOL_HANDLERS,
)
from lathe_app.workspace.manager import WorkspaceManager


@pytest.fixture
def manager():
    m = WorkspaceManager()
    yield m
    m.clear()


@pytest.fixture
def workspace_dir():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "src"))
        with open(os.path.join(d, "README.md"), "w") as f:
            f.write("# Test\n")
        with open(os.path.join(d, "main.py"), "w") as f:
            f.write("print('hello')\n")
        with open(os.path.join(d, "src", "lib.py"), "w") as f:
            f.write("x = 1\n")
        with open(os.path.join(d, "src", "data.json"), "w") as f:
            f.write("{}\n")
        with open(os.path.join(d, "notes.txt"), "w") as f:
            f.write("some notes\n")
        yield d


@pytest.fixture
def workspace(manager, workspace_dir, monkeypatch):
    monkeypatch.setattr(
        "lathe_app.tools.handlers.get_default_manager",
        lambda: manager,
    )
    ws = manager.create_workspace(workspace_dir, workspace_id="test-ws")
    return ws


class TestToolRegistry:
    def test_registry_is_list(self):
        assert isinstance(TOOL_REGISTRY, list)
        assert len(TOOL_REGISTRY) >= 3

    def test_all_specs_are_toolspec(self):
        for spec in TOOL_REGISTRY:
            assert isinstance(spec, ToolSpec)

    def test_all_ids_unique(self):
        ids = [s.id for s in TOOL_REGISTRY]
        assert len(ids) == len(set(ids))

    def test_all_read_only(self):
        for spec in TOOL_REGISTRY:
            assert spec.read_only is True

    def test_registry_deterministic(self):
        ids_a = [s.id for s in TOOL_REGISTRY]
        ids_b = [s.id for s in TOOL_REGISTRY]
        assert ids_a == ids_b

    def test_get_tool_spec_found(self):
        spec = get_tool_spec("fs_tree")
        assert spec is not None
        assert spec.id == "fs_tree"

    def test_get_tool_spec_not_found(self):
        assert get_tool_spec("nonexistent_tool") is None

    def test_required_tools_present(self):
        ids = {s.id for s in TOOL_REGISTRY}
        assert "fs_tree" in ids
        assert "fs_stats" in ids
        assert "git_status" in ids

    def test_toolspec_to_dict(self):
        spec = get_tool_spec("fs_tree")
        d = spec.to_dict()
        assert d["id"] == "fs_tree"
        assert d["category"] == "filesystem"
        assert d["read_only"] is True
        assert "inputs" in d
        assert "outputs" in d
        assert "trust_required" in d

    def test_toolspec_frozen(self):
        spec = get_tool_spec("fs_tree")
        with pytest.raises(AttributeError):
            spec.id = "changed"

    def test_all_handlers_registered(self):
        for spec in TOOL_REGISTRY:
            assert spec.id in TOOL_HANDLERS, f"No handler for tool: {spec.id}"


class TestFsTreeHandler:
    def test_list_all_files(self, workspace):
        result = handle_fs_tree("test-ws")
        assert "error" not in result
        assert result["count"] > 0
        assert isinstance(result["files"], list)
        assert result["workspace"] == "test-ws"

    def test_filter_by_extension(self, workspace):
        result = handle_fs_tree("test-ws", ext=".py")
        assert "error" not in result
        for f in result["files"]:
            assert f.endswith(".py")
        assert result["count"] >= 2

    def test_filter_by_ext_no_dot(self, workspace):
        result = handle_fs_tree("test-ws", ext="py")
        assert "error" not in result
        for f in result["files"]:
            assert f.endswith(".py")

    def test_workspace_not_found(self, workspace):
        result = handle_fs_tree("nonexistent-ws")
        assert result["error"] == "workspace_not_found"

    def test_files_are_relative(self, workspace, workspace_dir):
        result = handle_fs_tree("test-ws")
        for f in result["files"]:
            assert not os.path.isabs(f)


class TestFsStatsHandler:
    def test_extension_counts(self, workspace):
        result = handle_fs_stats("test-ws")
        assert "error" not in result
        assert result["total_files"] > 0
        assert ".py" in result["extensions"]
        assert ".md" in result["extensions"]
        assert result["workspace"] == "test-ws"

    def test_workspace_not_found(self, workspace):
        result = handle_fs_stats("nonexistent-ws")
        assert result["error"] == "workspace_not_found"


class TestGitStatusHandler:
    def test_not_a_git_repo(self, workspace):
        result = handle_git_status("test-ws")
        assert result["error"] == "not_git_repo"

    def test_git_status_in_repo(self, workspace, workspace_dir):
        subprocess.run(["git", "init"], cwd=workspace_dir, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=workspace_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init", "--author", "Test <test@test.com>"],
            cwd=workspace_dir,
            capture_output=True,
            env={**os.environ, "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@test.com"},
        )
        result = handle_git_status("test-ws")
        assert "error" not in result
        assert result["clean"] is True
        assert result["branch"] is not None
        assert result["workspace"] == "test-ws"

    def test_workspace_not_found(self, workspace):
        result = handle_git_status("nonexistent-ws")
        assert result["error"] == "workspace_not_found"


class TestWorkspaceBoundary:
    def test_fs_tree_no_escape(self, workspace, workspace_dir):
        symlink_path = os.path.join(workspace_dir, "escape")
        try:
            os.symlink("/etc", symlink_path)
        except OSError:
            pytest.skip("Cannot create symlink")

        result = handle_fs_tree("test-ws")
        for f in result["files"]:
            abs_path = os.path.join(workspace_dir, f)
            resolved = os.path.realpath(abs_path)
            assert resolved.startswith(workspace_dir) or not os.path.exists(abs_path)


class TestTrustEnforcement:
    def test_trust_denied_blocks_tool(self, manager, monkeypatch):
        with tempfile.TemporaryDirectory() as d:
            monkeypatch.setattr(
                "lathe_app.tools.handlers.get_default_manager",
                lambda: manager,
            )
            ws = manager.create_workspace(d, workspace_id="trust-test")

            lathe_dir = os.path.join(d, ".lathe")
            os.makedirs(lathe_dir)
            with open(os.path.join(lathe_dir, "trust.json"), "w") as f:
                json.dump({"trust_level": 0}, f)

            from lathe_app.tools.registry import TOOL_REGISTRY
            high_trust_spec = ToolSpec(
                id="test_high_trust",
                category="test",
                description="test tool",
                read_only=True,
                inputs={},
                outputs={},
                trust_required=3,
            )

            from lathe_app.tools import handlers
            original_check = handlers._check_trust

            def strict_check(workspace_root, trust_required):
                return original_check(workspace_root, trust_required)

            result = handlers._check_trust(d, 3)
            assert result is not None
            assert result["error"] == "trust_denied"
            assert result["required"] == 3

    def test_trust_allowed_passes(self, manager, monkeypatch):
        with tempfile.TemporaryDirectory() as d:
            monkeypatch.setattr(
                "lathe_app.tools.handlers.get_default_manager",
                lambda: manager,
            )
            ws = manager.create_workspace(d, workspace_id="trust-pass")

            lathe_dir = os.path.join(d, ".lathe")
            os.makedirs(lathe_dir)
            with open(os.path.join(lathe_dir, "trust.json"), "w") as f:
                json.dump({"trust_level": 2}, f)

            from lathe_app.tools import handlers
            result = handlers._check_trust(d, 1)
            assert result is None
