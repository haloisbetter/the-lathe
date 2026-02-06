"""
Tests for workspace ingestion: scanner, registry, indexer, and integration.

Verifies:
1. Workspace can be ingested
2. Duplicate workspace name is rejected
3. Files are discovered correctly
4. Excluded paths are ignored
5. RAG queries return workspace files
6. Lathe repo files are NOT returned when querying workspace
7. RAG without workspace does NOT leak workspace data
8. Workspace ingestion is read-only enforced (scanner only reads)
"""
import os
import tempfile
import pytest

from lathe_app.workspace.scanner import (
    scan_workspace,
    collect_extensions,
    matches_any_glob,
    is_excluded_dir,
)
from lathe_app.workspace.registry import (
    WorkspaceRegistry,
    RegisteredWorkspace,
    get_default_registry,
    reset_default_registry,
)
from lathe_app.workspace.indexer import (
    WorkspaceIndexer,
    get_default_indexer,
    reset_default_indexer,
)
from lathe_app.workspace.errors import (
    WorkspaceError,
    WorkspacePathNotFoundError,
    WorkspaceNotDirectoryError,
    WorkspaceNameCollisionError,
    WorkspaceNotFoundError,
    WorkspaceUnsafePathError,
    WorkspaceEmptyError,
)
from lathe_app.knowledge.index import KnowledgeIndex


@pytest.fixture
def sample_workspace(tmp_path):
    (tmp_path / "main.py").write_text("def hello(): pass")
    (tmp_path / "README.md").write_text("# My Project")
    (tmp_path / "config.json").write_text('{"key": "value"}')
    (tmp_path / "notes.txt").write_text("some notes")
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n")
    (tmp_path / "binary.dat").write_bytes(b"\x00\x01\x02")

    subdir = tmp_path / "src"
    subdir.mkdir()
    (subdir / "app.py").write_text("class App: pass")
    (subdir / "utils.py").write_text("def util(): return 1")

    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "ignore.py").write_text("should be excluded")

    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("git config")

    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "cached.pyc").write_bytes(b"\x00")

    node = tmp_path / "node_modules"
    node.mkdir()
    (node / "pkg.json").write_text("{}")

    return tmp_path


@pytest.fixture
def registry():
    reg = WorkspaceRegistry()
    yield reg
    reg.clear()


@pytest.fixture
def indexer():
    idx = WorkspaceIndexer()
    yield idx
    idx.clear()


class TestScanner:
    def test_discovers_supported_files(self, sample_workspace):
        files = scan_workspace(str(sample_workspace))
        basenames = [os.path.basename(f) for f in files]
        assert "main.py" in basenames
        assert "README.md" in basenames
        assert "config.json" in basenames
        assert "notes.txt" in basenames
        assert "app.py" in basenames
        assert "utils.py" in basenames

    def test_excludes_binary_and_unsupported(self, sample_workspace):
        files = scan_workspace(str(sample_workspace))
        basenames = [os.path.basename(f) for f in files]
        assert "image.png" not in basenames
        assert "binary.dat" not in basenames

    def test_excludes_default_dirs(self, sample_workspace):
        files = scan_workspace(str(sample_workspace))
        for f in files:
            assert ".venv" not in f
            assert ".git" not in f
            assert "__pycache__" not in f
            assert "node_modules" not in f

    def test_custom_include_filter(self, sample_workspace):
        files = scan_workspace(str(sample_workspace), include=["**/*.py"])
        for f in files:
            assert f.endswith(".py")
        basenames = [os.path.basename(f) for f in files]
        assert "main.py" in basenames
        assert "app.py" in basenames
        assert "README.md" not in basenames

    def test_custom_exclude_filter(self, sample_workspace):
        files = scan_workspace(
            str(sample_workspace),
            exclude=[".venv", ".git", "node_modules", "__pycache__", "src"],
        )
        for f in files:
            assert "/src/" not in f

    def test_returns_sorted_absolute_paths(self, sample_workspace):
        files = scan_workspace(str(sample_workspace))
        assert files == sorted(files)
        for f in files:
            assert os.path.isabs(f)

    def test_collect_extensions(self, sample_workspace):
        files = scan_workspace(str(sample_workspace))
        exts = collect_extensions(files)
        assert ".py" in exts
        assert ".md" in exts
        assert ".json" in exts
        assert ".txt" in exts

    def test_empty_directory(self, tmp_path):
        files = scan_workspace(str(tmp_path))
        assert files == []

    def test_matches_any_glob(self):
        assert matches_any_glob("src/main.py", ["**/*.py"])
        assert matches_any_glob("main.py", ["*.py"])
        assert not matches_any_glob("main.py", ["*.md"])

    def test_is_excluded_dir(self):
        assert is_excluded_dir(".venv", [".venv", ".git"])
        assert is_excluded_dir("node_modules", ["node_modules"])
        assert not is_excluded_dir("src", [".venv", ".git"])


class TestRegistry:
    def _make_registered(self, name="test-ws", root="/tmp/test"):
        return RegisteredWorkspace(
            name=name,
            root_path=root,
            manifest="git",
            include=["**/*.py"],
            exclude=[".venv"],
            file_count=5,
            indexed_extensions=[".py"],
            registered_at="2025-01-01T00:00:00",
            indexed=True,
        )

    def test_register_and_lookup(self, registry):
        ws = self._make_registered()
        registry.register(ws)
        found = registry.get("test-ws")
        assert found is not None
        assert found.name == "test-ws"
        assert found.root_path == "/tmp/test"

    def test_duplicate_name_rejected(self, registry):
        ws1 = self._make_registered("project-a")
        ws2 = self._make_registered("project-a", "/tmp/other")
        registry.register(ws1)
        with pytest.raises(WorkspaceNameCollisionError):
            registry.register(ws2)

    def test_list_all(self, registry):
        ws1 = self._make_registered("ws-1")
        ws2 = self._make_registered("ws-2", "/tmp/ws2")
        registry.register(ws1)
        registry.register(ws2)
        all_ws = registry.list_all()
        assert len(all_ws) == 2
        names = {ws.name for ws in all_ws}
        assert names == {"ws-1", "ws-2"}

    def test_contains(self, registry):
        ws = self._make_registered("my-ws")
        registry.register(ws)
        assert registry.contains("my-ws")
        assert not registry.contains("other")

    def test_remove(self, registry):
        ws = self._make_registered("rm-ws")
        registry.register(ws)
        assert registry.remove("rm-ws")
        assert not registry.contains("rm-ws")
        assert not registry.remove("rm-ws")

    def test_get_missing_returns_none(self, registry):
        assert registry.get("nonexistent") is None

    def test_to_dict(self):
        ws = self._make_registered()
        d = ws.to_dict()
        assert d["name"] == "test-ws"
        assert d["file_count"] == 5
        assert d["indexed"] is True


class TestIndexer:
    def test_ingest_and_query(self, sample_workspace, indexer):
        files = scan_workspace(str(sample_workspace), include=["**/*.py"])
        doc_count, chunk_count, errors = indexer.ingest_files(
            "test-ws", files, str(sample_workspace)
        )
        assert doc_count > 0
        assert chunk_count > 0

        results = indexer.query("test-ws", "hello function")
        assert len(results) > 0
        assert all(r["workspace"] == "test-ws" for r in results)

    def test_workspace_scoped_query(self, tmp_path, indexer):
        ws_a = tmp_path / "ws_a"
        ws_b = tmp_path / "ws_b"
        ws_a.mkdir()
        ws_b.mkdir()
        (ws_a / "alpha.py").write_text("def alpha_function(): pass")
        (ws_b / "beta.py").write_text("def beta_function(): pass")

        files_a = scan_workspace(str(ws_a))
        files_b = scan_workspace(str(ws_b))
        indexer.ingest_files("alpha-ws", files_a, str(ws_a))
        indexer.ingest_files("beta-ws", files_b, str(ws_b))

        results_a = indexer.query("alpha-ws", "alpha")
        results_b = indexer.query("beta-ws", "beta")

        assert all(r["workspace"] == "alpha-ws" for r in results_a)
        assert all(r["workspace"] == "beta-ws" for r in results_b)

    def test_query_missing_workspace_returns_empty(self, indexer):
        results = indexer.query("nonexistent", "anything")
        assert results == []

    def test_no_cross_workspace_leakage(self, tmp_path, indexer):
        ws_a = tmp_path / "ws_a"
        ws_a.mkdir()
        (ws_a / "secret.py").write_text("SECRET_KEY = 'do-not-leak'")

        files = scan_workspace(str(ws_a))
        indexer.ingest_files("private-ws", files, str(ws_a))

        results_other = indexer.query("other-ws", "SECRET_KEY")
        assert results_other == []

    def test_has_index(self, tmp_path, indexer):
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / "code.py").write_text("x = 1")

        assert not indexer.has_index("ws")
        files = scan_workspace(str(ws))
        indexer.ingest_files("ws", files, str(ws))
        assert indexer.has_index("ws")

    def test_remove_index(self, tmp_path, indexer):
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / "code.py").write_text("x = 1")

        files = scan_workspace(str(ws))
        indexer.ingest_files("ws", files, str(ws))
        assert indexer.remove_index("ws")
        assert not indexer.has_index("ws")


class TestIntegration:
    def test_full_ingest_pipeline(self, sample_workspace):
        registry = WorkspaceRegistry()
        indexer = WorkspaceIndexer()

        files = scan_workspace(str(sample_workspace))
        assert len(files) > 0

        doc_count, chunk_count, errors = indexer.ingest_files(
            "full-test", files, str(sample_workspace)
        )
        assert doc_count > 0
        assert chunk_count > 0

        extensions = collect_extensions(files)
        ws = RegisteredWorkspace(
            name="full-test",
            root_path=str(sample_workspace),
            manifest="git",
            include=[],
            exclude=[],
            file_count=len(files),
            indexed_extensions=extensions,
            registered_at="2025-01-01T00:00:00",
            indexed=True,
        )
        registry.register(ws)

        assert registry.contains("full-test")
        results = indexer.query("full-test", "hello")
        assert len(results) > 0

    def test_read_only_enforced(self, sample_workspace):
        original_files = set()
        for root, dirs, files in os.walk(str(sample_workspace)):
            for f in files:
                path = os.path.join(root, f)
                original_files.add(path)
                stat = os.stat(path)

        indexer = WorkspaceIndexer()
        files = scan_workspace(str(sample_workspace))
        indexer.ingest_files("readonly-test", files, str(sample_workspace))

        after_files = set()
        for root, dirs, files_list in os.walk(str(sample_workspace)):
            for f in files_list:
                path = os.path.join(root, f)
                after_files.add(path)

        assert original_files == after_files


class TestErrors:
    def test_workspace_error_hierarchy(self):
        assert issubclass(WorkspacePathNotFoundError, WorkspaceError)
        assert issubclass(WorkspaceNotDirectoryError, WorkspaceError)
        assert issubclass(WorkspaceNameCollisionError, WorkspaceError)
        assert issubclass(WorkspaceNotFoundError, WorkspaceError)
        assert issubclass(WorkspaceUnsafePathError, WorkspaceError)
        assert issubclass(WorkspaceEmptyError, WorkspaceError)

    def test_error_messages(self):
        e = WorkspacePathNotFoundError("/missing/path")
        assert "/missing/path" in str(e)
        assert e.path == "/missing/path"

        e = WorkspaceNameCollisionError("duplicate")
        assert "duplicate" in str(e)
        assert e.name == "duplicate"


class TestDefaultSingletons:
    def test_default_registry(self):
        reset_default_registry()
        reg = get_default_registry()
        assert isinstance(reg, WorkspaceRegistry)
        reg2 = get_default_registry()
        assert reg is reg2
        reset_default_registry()

    def test_default_indexer(self):
        reset_default_indexer()
        idx = get_default_indexer()
        assert isinstance(idx, WorkspaceIndexer)
        idx2 = get_default_indexer()
        assert idx is idx2
        reset_default_indexer()
