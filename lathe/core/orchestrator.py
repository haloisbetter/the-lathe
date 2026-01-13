from lathe.core.task import TaskSpec
from lathe.core.result import TaskResult
from lathe.core.executor import BootstrapExecutor
from lathe.storage.db import LatheDB


class Orchestrator:
    """
    Core execution coordinator for The Lathe.
    """

    def __init__(self, executor: BootstrapExecutor, db: LatheDB):
        self.executor = executor
        self.db = db

    def run_task(self, task: TaskSpec) -> TaskResult:
        """
        Execute a task using the configured executor
        and persist execution details.
        """
        self.db.log_task(task)

        result = self.executor.execute(task)

        self.db.log_result(result)

        return result