from abc import ABC, abstractmethod
from lathe.core.task import TaskSpec
from lathe.core.result import TaskResult


class BootstrapExecutor(ABC):
    """
    Temporary executor used during the bootstrap phase.
    """

    @abstractmethod
    def execute(self, task: TaskSpec) -> TaskResult:
        """
        Execute a task and return a structured result.
        """
        raise NotImplementedError