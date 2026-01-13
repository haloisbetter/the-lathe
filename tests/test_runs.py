import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from lathe.core.task import TaskSpec
from lathe.core.orchestrator import Orchestrator
from lathe.bootstrap.openhands import OpenHandsExecutor
from lathe.storage.db import LatheDB


def test_multiple_runs_are_recorded(tmp_path):
    db = LatheDB(tmp_path / "lathe.db")
    executor = OpenHandsExecutor()
    orchestrator = Orchestrator(executor, db)

    task = TaskSpec(
        id="multi-001",
        goal="Multi-run test",
        scope="test",
        constraints={},
        inputs={},
    )

    orchestrator.run_task(task)
    orchestrator.run_task(task)

    runs = db.list_runs("multi-001")
    assert len(runs) == 2