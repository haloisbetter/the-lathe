"""
Tests for Workspace Memory (Components B and C).

Component B: File Read Artifacts + Invalidation
Verifies:
1. FileReadArtifacts are created correctly
2. Hash changes are detectable
3. Stale reads are flagged
4. Run staleness aggregation works

Component C: Persistent Workspace Memory
Verifies:
5. .lathe/context.md is loaded when present
6. lathe.md fallback works
7. Missing context returns None
8. Content hash is correct
"""
import hashlib
import os
import tempfile
import time

import pytest

from lathe_app.workspace.memory import (
    FileReadArtifact,
    create_file_read,
    check_staleness,
    check_run_staleness,
    hash_file,
    hash_content,
    load_workspace_context,
    CONTEXT_FILE_NAMES,
)


@pytest.fixture
def sample_file(tmp_path):
    f = tmp_path / "example.py"
    f.write_text("x = 1\ny = 2\n")
    return f


@pytest.fixture
def workspace_with_context(tmp_path):
    lathe_dir = tmp_path / ".lathe"
    lathe_dir.mkdir()
    (lathe_dir / "context.md").write_text(
        "# My Project\n\n## Invariants\n- Never delete data\n"
    )
    return tmp_path


@pytest.fixture
def workspace_with_lathemd(tmp_path):
    (tmp_path / "lathe.md").write_text("# Alt Memory\n")
    return tmp_path


class TestHashFile:
    def test_hash_matches_manual(self, sample_file):
        expected = hashlib.sha256(sample_file.read_bytes()).hexdigest()
        assert hash_file(str(sample_file)) == expected

    def test_hash_changes_on_edit(self, sample_file):
        h1 = hash_file(str(sample_file))
        sample_file.write_text("z = 99\n")
        h2 = hash_file(str(sample_file))
        assert h1 != h2

    def test_nonexistent_returns_error(self, tmp_path):
        assert hash_file(str(tmp_path / "nope.txt")) == "error:unreadable"

    def test_hash_content(self):
        text = "hello world"
        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert hash_content(text) == expected


class TestCreateFileRead:
    def test_creates_artifact(self, sample_file):
        art = create_file_read(str(sample_file))
        assert isinstance(art, FileReadArtifact)
        assert art.path == str(sample_file)
        assert len(art.content_hash) == 64
        assert art.timestamp

    def test_line_range(self, sample_file):
        art = create_file_read(str(sample_file), line_start=1, line_end=5)
        assert art.line_start == 1
        assert art.line_end == 5

    def test_to_dict(self, sample_file):
        art = create_file_read(str(sample_file))
        d = art.to_dict()
        assert "path" in d
        assert "content_hash" in d
        assert "timestamp" in d


class TestStalenessDetection:
    def test_fresh_file_not_stale(self, sample_file):
        art = create_file_read(str(sample_file))
        result = check_staleness(art)
        assert result["stale"] is False
        assert result["original_hash"] == result["current_hash"]

    def test_modified_file_is_stale(self, sample_file):
        art = create_file_read(str(sample_file))
        sample_file.write_text("changed content\n")
        result = check_staleness(art)
        assert result["stale"] is True
        assert result["reason"] == "hash_mismatch"
        assert result["original_hash"] != result["current_hash"]

    def test_deleted_file_is_stale(self, sample_file):
        art = create_file_read(str(sample_file))
        sample_file.unlink()
        result = check_staleness(art)
        assert result["stale"] is True
        assert result["reason"] == "file_unreadable"

    def test_unchanged_file_stays_fresh(self, sample_file):
        art = create_file_read(str(sample_file))
        result = check_staleness(art)
        assert result["stale"] is False


class TestRunStaleness:
    def test_all_fresh(self, tmp_path):
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text("a = 1\n")
        f2.write_text("b = 2\n")

        reads = [create_file_read(str(f1)), create_file_read(str(f2))]
        result = check_run_staleness(reads)
        assert result["potentially_stale"] is False
        assert result["stale_count"] == 0
        assert result["fresh_count"] == 2

    def test_one_stale(self, tmp_path):
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text("a = 1\n")
        f2.write_text("b = 2\n")

        reads = [create_file_read(str(f1)), create_file_read(str(f2))]
        f1.write_text("a = 999\n")

        result = check_run_staleness(reads)
        assert result["potentially_stale"] is True
        assert result["stale_count"] == 1
        assert result["fresh_count"] == 1
        assert len(result["stale_files"]) == 1
        assert result["stale_files"][0]["path"] == str(f1)

    def test_empty_reads(self):
        result = check_run_staleness([])
        assert result["potentially_stale"] is False
        assert result["stale_count"] == 0


class TestWorkspaceContextLoading:
    def test_loads_lathe_context_md(self, workspace_with_context):
        ctx = load_workspace_context(str(workspace_with_context))
        assert ctx is not None
        assert "# My Project" in ctx["content"]
        assert ctx["relative_path"] == ".lathe/context.md"
        assert ctx["content_hash"]
        assert ctx["loaded_at"]

    def test_loads_lathe_md_fallback(self, workspace_with_lathemd):
        ctx = load_workspace_context(str(workspace_with_lathemd))
        assert ctx is not None
        assert "# Alt Memory" in ctx["content"]
        assert ctx["relative_path"] == "lathe.md"

    def test_prefers_lathe_context_md(self, tmp_path):
        lathe_dir = tmp_path / ".lathe"
        lathe_dir.mkdir()
        (lathe_dir / "context.md").write_text("# Primary\n")
        (tmp_path / "lathe.md").write_text("# Fallback\n")

        ctx = load_workspace_context(str(tmp_path))
        assert ctx["relative_path"] == ".lathe/context.md"
        assert "# Primary" in ctx["content"]

    def test_no_context_returns_none(self, tmp_path):
        ctx = load_workspace_context(str(tmp_path))
        assert ctx is None

    def test_content_hash_is_sha256(self, workspace_with_context):
        ctx = load_workspace_context(str(workspace_with_context))
        content = ctx["content"]
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert ctx["content_hash"] == expected

    def test_content_is_not_auto_generated(self, workspace_with_context):
        ctx = load_workspace_context(str(workspace_with_context))
        assert "auto-generated" not in ctx["content"].lower()


class TestFileReadArtifactOnRunRecord:
    def test_run_record_has_file_reads_field(self):
        from lathe_app.artifacts import RunRecord
        import dataclasses
        fields = {f.name for f in dataclasses.fields(RunRecord)}
        assert "file_reads" in fields
        assert "workspace_context_loaded" in fields

    def test_run_record_default_empty(self):
        from lathe_app.artifacts import RunRecord, ArtifactInput
        run = RunRecord.create(
            input_data=ArtifactInput(intent="propose", task="test", why={}),
            output=None,
            model_used="test",
            fallback_triggered=False,
            success=True,
        )
        assert run.file_reads == []
        assert run.workspace_context_loaded is None

    def test_run_record_with_file_reads(self, sample_file):
        from lathe_app.artifacts import RunRecord, ArtifactInput

        art = create_file_read(str(sample_file))
        run = RunRecord.create(
            input_data=ArtifactInput(intent="propose", task="test", why={}),
            output=None,
            model_used="test",
            fallback_triggered=False,
            success=True,
            file_reads=[art.to_dict()],
        )
        assert len(run.file_reads) == 1
        assert run.file_reads[0]["path"] == str(sample_file)
