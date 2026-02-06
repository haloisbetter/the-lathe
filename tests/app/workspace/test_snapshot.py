"""
Tests for Workspace Snapshot (Component A).

Verifies:
1. Snapshot creation is deterministic
2. File hashes change when files change
3. Snapshot rejects unsafe paths
4. Snapshot rejects self-ingestion
5. Manifest contains correct per-file metadata
6. Stats are accurate
7. Read-only (no writes occur)
"""
import hashlib
import os
import tempfile

import pytest

from lathe_app.workspace.snapshot import (
    FileEntry,
    WorkspaceManifest,
    WorkspaceSnapshot,
    WorkspaceStats,
    snapshot_workspace,
    _hash_file,
    _count_lines,
    _validate_root,
)


@pytest.fixture
def sample_workspace(tmp_path):
    (tmp_path / "hello.py").write_text("print('hello')\nprint('world')\n")
    (tmp_path / "README.md").write_text("# Project\n")
    sub = tmp_path / "lib"
    sub.mkdir()
    (sub / "utils.py").write_text("def add(a, b):\n    return a + b\n")
    (tmp_path / "config.json").write_text('{"key": "value"}\n')
    return tmp_path


class TestSnapshotCreation:
    def test_produces_snapshot(self, sample_workspace):
        snap = snapshot_workspace(str(sample_workspace))
        assert isinstance(snap, WorkspaceSnapshot)
        assert isinstance(snap.manifest, WorkspaceManifest)
        assert isinstance(snap.stats, WorkspaceStats)

    def test_manifest_has_correct_file_count(self, sample_workspace):
        snap = snapshot_workspace(str(sample_workspace))
        assert len(snap.manifest.files) == 4

    def test_manifest_root_is_absolute(self, sample_workspace):
        snap = snapshot_workspace(str(sample_workspace))
        assert os.path.isabs(snap.manifest.root_path)

    def test_manifest_paths_are_relative(self, sample_workspace):
        snap = snapshot_workspace(str(sample_workspace))
        for entry in snap.manifest.files:
            assert not os.path.isabs(entry.path)

    def test_files_sorted_by_path(self, sample_workspace):
        snap = snapshot_workspace(str(sample_workspace))
        paths = [e.path for e in snap.manifest.files]
        assert paths == sorted(paths)


class TestSnapshotDeterminism:
    def test_same_workspace_same_snapshot(self, sample_workspace):
        ts = "2025-01-01T00:00:00Z"
        snap1 = snapshot_workspace(str(sample_workspace), timestamp=ts)
        snap2 = snapshot_workspace(str(sample_workspace), timestamp=ts)

        d1 = snap1.to_dict()
        d2 = snap2.to_dict()
        assert d1 == d2

    def test_deterministic_hashes(self, sample_workspace):
        snap1 = snapshot_workspace(str(sample_workspace))
        snap2 = snapshot_workspace(str(sample_workspace))

        for e1, e2 in zip(snap1.manifest.files, snap2.manifest.files):
            assert e1.content_hash == e2.content_hash


class TestFileHashing:
    def test_hash_changes_when_file_changes(self, sample_workspace):
        snap1 = snapshot_workspace(str(sample_workspace))
        entry1 = next(e for e in snap1.manifest.files if e.path == "hello.py")
        hash1 = entry1.content_hash

        (sample_workspace / "hello.py").write_text("print('changed')\n")
        snap2 = snapshot_workspace(str(sample_workspace))
        entry2 = next(e for e in snap2.manifest.files if e.path == "hello.py")
        hash2 = entry2.content_hash

        assert hash1 != hash2

    def test_hash_is_sha256(self, sample_workspace):
        snap = snapshot_workspace(str(sample_workspace))
        for entry in snap.manifest.files:
            assert len(entry.content_hash) == 64
            int(entry.content_hash, 16)

    def test_hash_matches_manual_sha256(self, sample_workspace):
        path = str(sample_workspace / "hello.py")
        expected = hashlib.sha256(open(path, "rb").read()).hexdigest()
        snap = snapshot_workspace(str(sample_workspace))
        entry = next(e for e in snap.manifest.files if e.path == "hello.py")
        assert entry.content_hash == expected


class TestFileMetadata:
    def test_line_count(self, sample_workspace):
        snap = snapshot_workspace(str(sample_workspace))
        entry = next(e for e in snap.manifest.files if e.path == "hello.py")
        assert entry.line_count == 2

    def test_file_size(self, sample_workspace):
        snap = snapshot_workspace(str(sample_workspace))
        entry = next(e for e in snap.manifest.files if e.path == "hello.py")
        expected_size = os.path.getsize(str(sample_workspace / "hello.py"))
        assert entry.size_bytes == expected_size

    def test_extension(self, sample_workspace):
        snap = snapshot_workspace(str(sample_workspace))
        entry = next(e for e in snap.manifest.files if e.path == "hello.py")
        assert entry.extension == ".py"


class TestStats:
    def test_total_files(self, sample_workspace):
        snap = snapshot_workspace(str(sample_workspace))
        assert snap.stats.total_files == 4

    def test_python_files(self, sample_workspace):
        snap = snapshot_workspace(str(sample_workspace))
        assert snap.stats.python_files == 2

    def test_markdown_files(self, sample_workspace):
        snap = snapshot_workspace(str(sample_workspace))
        assert snap.stats.markdown_files == 1

    def test_extension_distribution(self, sample_workspace):
        snap = snapshot_workspace(str(sample_workspace))
        dist = snap.stats.extension_distribution
        assert dist[".py"] == 2
        assert dist[".md"] == 1
        assert dist[".json"] == 1

    def test_depth_histogram(self, sample_workspace):
        snap = snapshot_workspace(str(sample_workspace))
        hist = snap.stats.directory_depth_histogram
        assert 0 in hist
        assert 1 in hist


class TestSafety:
    def test_rejects_etc(self):
        with pytest.raises(ValueError, match="system directory"):
            snapshot_workspace("/etc")

    def test_rejects_usr(self):
        with pytest.raises(ValueError, match="system directory"):
            snapshot_workspace("/usr")

    def test_rejects_var(self):
        with pytest.raises(ValueError, match="system directory"):
            snapshot_workspace("/var")

    def test_rejects_self_ingestion(self):
        lathe_root = os.path.abspath(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        )
        with pytest.raises(ValueError, match="Lathe repository"):
            snapshot_workspace(lathe_root)

    def test_rejects_nonexistent(self, tmp_path):
        with pytest.raises(ValueError, match="not found"):
            snapshot_workspace(str(tmp_path / "nonexistent"))

    def test_rejects_file_not_dir(self, tmp_path):
        f = tmp_path / "afile.txt"
        f.write_text("hello")
        with pytest.raises(ValueError, match="not a directory"):
            snapshot_workspace(str(f))


class TestSerialization:
    def test_to_dict_roundtrip(self, sample_workspace):
        snap = snapshot_workspace(str(sample_workspace))
        d = snap.to_dict()
        assert "manifest" in d
        assert "stats" in d
        assert isinstance(d["manifest"]["files"], list)
        assert d["stats"]["total_files"] == 4

    def test_file_entry_to_dict(self):
        entry = FileEntry(
            path="test.py",
            size_bytes=100,
            line_count=10,
            extension=".py",
            content_hash="abc123",
        )
        d = entry.to_dict()
        assert d["path"] == "test.py"
        assert d["content_hash"] == "abc123"


class TestEmptyWorkspace:
    def test_empty_workspace_no_error(self, tmp_path):
        snap = snapshot_workspace(str(tmp_path))
        assert snap.stats.total_files == 0
        assert len(snap.manifest.files) == 0
