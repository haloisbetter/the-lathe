from lathe.core.task import TaskSpec
from lathe.core.result import TaskResult
from lathe.core.executor import BootstrapExecutor


class Orchestrator:
    """
    Core execution coordinator for The Lathe.
    """

    def __init__(self, executor: BootstrapExecutor):
        self.executor = executor

    def run_task(self, task: TaskSpec) -> TaskResult:
        """
        Execute a task using the configured executor.
        """
        return self.executor.execute(task)