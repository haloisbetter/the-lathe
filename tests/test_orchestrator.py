import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from lathe.core.task import TaskSpec
from lathe.core.orchestrator import Orchestrator
from lathe.bootstrap.openhands import OpenHandsExecutor
from lathe.storage.db import LatheDB


def test_orchestrator_runs_task(tmp_path):
    db_path = tmp_path / "lathe.db"

    executor = OpenHandsExecutor()
    db = LatheDB(db_path)
    orchestrator = Orchestrator(executor, db)

    task = TaskSpec(
        id="orch-001",
        goal="Orchestrator test",
        scope="test",
        constraints={},
        inputs={},
    )

    result = orchestrator.run_task(task)

    assert result.task_id == task.id