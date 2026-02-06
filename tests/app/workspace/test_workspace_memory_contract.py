"""
Integration tests for the Workspace Memory Contract.

Verifies the full contract end-to-end:
1. Snapshot + memory + staleness work together
2. Orchestrator loads context.md automatically
3. Kernel files remain unmodified
4. No filesystem writes during snapshots
5. Serialization works for new RunRecord fields
"""
import hashlib
import json
import os

import pytest

from lathe_app.workspace.snapshot import snapshot_workspace
from lathe_app.workspace.memory import (
    create_file_read,
    check_staleness,
    check_run_staleness,
    load_workspace_context,
    hash_file,
)


@pytest.fixture
def full_workspace(tmp_path):
    (tmp_path / "main.py").write_text("print('main')\n")
    (tmp_path / "lib.py").write_text("def helper():\n    pass\n")
    (tmp_path / "README.md").write_text("# My App\n")
    (tmp_path / "config.json").write_text("{}\n")

    lathe_dir = tmp_path / ".lathe"
    lathe_dir.mkdir()
    (lathe_dir / "context.md").write_text(
        "# Workspace Memory\n\n"
        "## Architecture\n"
        "- main.py is the entry point\n"
        "- lib.py contains helpers\n\n"
        "## Trust Level\n"
        "level: 2\n"
    )
    return tmp_path


class TestEndToEnd:
    def test_snapshot_then_reads_then_staleness(self, full_workspace):
        snap = snapshot_workspace(str(full_workspace))
        assert snap.stats.total_files >= 4

        reads = []
        for entry in snap.manifest.files:
            abs_path = os.path.join(snap.manifest.root_path, entry.path)
            reads.append(create_file_read(abs_path))

        result = check_run_staleness(reads)
        assert result["potentially_stale"] is False

        (full_workspace / "main.py").write_text("print('modified')\n")

        result2 = check_run_staleness(reads)
        assert result2["potentially_stale"] is True
        stale_paths = [s["path"] for s in result2["stale_files"]]
        assert any("main.py" in p for p in stale_paths)

    def test_snapshot_hash_matches_read_hash(self, full_workspace):
        snap = snapshot_workspace(str(full_workspace))
        for entry in snap.manifest.files:
            abs_path = os.path.join(snap.manifest.root_path, entry.path)
            read = create_file_read(abs_path)
            assert entry.content_hash == read.content_hash

    def test_context_md_loaded_during_snapshot(self, full_workspace):
        ctx = load_workspace_context(str(full_workspace))
        assert ctx is not None
        assert "Workspace Memory" in ctx["content"]
        assert "main.py is the entry point" in ctx["content"]

    def test_snapshot_serialization(self, full_workspace):
        snap = snapshot_workspace(str(full_workspace))
        d = snap.to_dict()
        j = json.dumps(d)
        parsed = json.loads(j)
        assert parsed["stats"]["total_files"] == snap.stats.total_files
        assert len(parsed["manifest"]["files"]) == len(snap.manifest.files)


class TestKernelUntouched:
    def test_kernel_files_not_modified(self):
        kernel_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "lathe"
        )
        if not os.path.isdir(kernel_dir):
            pytest.skip("kernel dir not found")

        import subprocess
        result = subprocess.run(
            ["git", "diff", "HEAD", "--", "lathe/"],
            capture_output=True, text=True, cwd=os.path.dirname(kernel_dir)
        )
        assert result.stdout.strip() == "", "Kernel files were modified!"


class TestNoImplicitMagic:
    def test_snapshot_does_not_auto_generate_context(self, tmp_path):
        (tmp_path / "test.py").write_text("x = 1\n")
        snapshot_workspace(str(tmp_path))
        assert not (tmp_path / ".lathe").exists()
        assert not (tmp_path / "lathe.md").exists()

    def test_context_is_operator_controlled(self, full_workspace):
        ctx = load_workspace_context(str(full_workspace))
        assert ctx is not None
        (full_workspace / ".lathe" / "context.md").unlink()
        ctx2 = load_workspace_context(str(full_workspace))
        assert ctx2 is None


class TestOrchestratorFileReads:
    def test_proposals_with_existing_files_create_reads(self, full_workspace):
        import json
        from lathe_app.orchestrator import Orchestrator
        from lathe_app.workspace.manager import get_default_manager, reset_default_manager
        from lathe_app.workspace.context import set_current_context, clear_current_context, WorkspaceContext

        reset_default_manager()
        manager = get_default_manager()
        ws = manager.create_workspace(str(full_workspace))
        ctx = WorkspaceContext.from_workspace(ws)
        set_current_context(ctx)

        try:
            def agent_fn(n, m):
                return json.dumps({
                    "proposals": [
                        {"action": "modify", "target": "main.py"},
                        {"action": "create", "target": "new_file.py"},
                    ],
                    "assumptions": [],
                    "risks": [],
                    "results": [],
                    "model_fingerprint": m,
                })

            orch = Orchestrator(agent_fn=agent_fn)
            run = orch.execute(
                intent="propose",
                task="modify main",
                why={"goal": "test"},
                workspace_id=ws.id,
                speculative=False,
            )

            assert len(run.file_reads) == 1
            assert "main.py" in run.file_reads[0]["path"]
            assert run.file_reads[0]["content_hash"]
        finally:
            clear_current_context()
            reset_default_manager()

    def test_context_md_loaded_in_orchestrator(self, full_workspace):
        import json
        from lathe_app.orchestrator import Orchestrator
        from lathe_app.workspace.manager import get_default_manager, reset_default_manager
        from lathe_app.workspace.context import set_current_context, clear_current_context, WorkspaceContext

        reset_default_manager()
        manager = get_default_manager()
        ws = manager.create_workspace(str(full_workspace))
        ctx = WorkspaceContext.from_workspace(ws)
        set_current_context(ctx)

        try:
            def agent_fn(n, m):
                return json.dumps({
                    "proposals": [],
                    "assumptions": [],
                    "risks": [],
                    "results": [],
                    "model_fingerprint": m,
                })

            orch = Orchestrator(agent_fn=agent_fn)
            run = orch.execute(
                intent="think",
                task="analyze",
                why={"goal": "test"},
                workspace_id=ws.id,
                speculative=False,
            )

            assert run.workspace_context_loaded is not None
            assert "Workspace Memory" in run.workspace_context_loaded["content"]
        finally:
            clear_current_context()
            reset_default_manager()


class TestRunRecordSerialization:
    def test_file_reads_serialize(self):
        from lathe_app.artifacts import RunRecord, ArtifactInput
        from lathe_app.http_serialization import to_jsonable_runrecord

        run = RunRecord.create(
            input_data=ArtifactInput(intent="propose", task="test", why={}),
            output=None,
            model_used="test",
            fallback_triggered=False,
            success=True,
            file_reads=[{"path": "/tmp/x.py", "content_hash": "abc", "line_start": 1, "line_end": 10, "timestamp": "t"}],
            workspace_context_loaded={"path": "/tmp/.lathe/context.md", "content": "# hi", "content_hash": "def", "loaded_at": "t"},
        )

        data = to_jsonable_runrecord(run)
        assert len(data["file_reads"]) == 1
        assert data["file_reads"][0]["path"] == "/tmp/x.py"
        assert data["workspace_context_loaded"]["content"] == "# hi"

        j = json.dumps(data)
        assert "file_reads" in j
        assert "workspace_context_loaded" in j
