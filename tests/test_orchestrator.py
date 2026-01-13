import sys
from pathlib import Path

# Ensure repo root is on Python path (CI / WSL / Docker safe)
sys.path.append(str(Path(__file__).resolve().parents[1]))

from lathe.core.task import TaskSpec
from lathe.core.orchestrator import Orchestrator
from lathe.bootstrap.openhands import OpenHandsExecutor


def test_orchestrator_runs_task():
    task = TaskSpec(
        id="orch-001",
        goal="Orchestrator test",
        scope="test",
        constraints={},
        inputs={},
    )

    executor = OpenHandsExecutor()
    orchestrator = Orchestrator(executor)

    result = orchestrator.run_task(task)

    assert result.task_id == task.id