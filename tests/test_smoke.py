from lathe.core.task import TaskSpec
from lathe.bootstrap.openhands import OpenHandsExecutor


def test_bootstrap_executor_contract():
    task = TaskSpec(
        id="test-001",
        goal="Test task execution",
        scope="none",
        constraints={},
        inputs={},
    )

    executor = OpenHandsExecutor()
    result = executor.execute(task)

    assert result.task_id == task.id
    assert result.success is False