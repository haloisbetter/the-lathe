import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from lathe.core.task import TaskSpec
from lathe.core.orchestrator import Orchestrator
from lathe.bootstrap.openhands import OpenHandsExecutor
from lathe.storage.db import LatheDB


def test_db_load_task_spec_and_replay(tmp_path):
    db_path = tmp_path / "lathe.db"
    db = LatheDB(db_path)

    # Log a task (simulates prior run)
    original = TaskSpec(
        id="replay-001",
        goal="Replay test",
        scope="test",
        constraints={"a": 1},
        inputs={"b": 2},
    )
    db.log_task(original)

    # Load it back
    loaded = db.load_task_spec("replay-001")
    assert loaded is not None
    assert loaded.id == original.id
    assert loaded.goal == original.goal
    assert loaded.constraints == original.constraints
    assert loaded.inputs == original.inputs

    # Replay through orchestrator (overwrites result for same task_id with current schema)
    executor = OpenHandsExecutor()
    orchestrator = Orchestrator(executor, db)
    result = orchestrator.run_task(loaded)

    assert result.task_id == "replay-001"