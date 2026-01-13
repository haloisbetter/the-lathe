"""
OpenHands bootstrap executor.

This module allows OpenHands to act as a temporary
task executor during The Lathe bootstrap phase.
"""

from lathe.core.executor import BootstrapExecutor
from lathe.core.task import TaskSpec
from lathe.core.result import TaskResult


class OpenHandsExecutor(BootstrapExecutor):
    def execute(self, task: TaskSpec) -> TaskResult:
        # Placeholder: actual OpenHands integration happens later
        return TaskResult(
            task_id=task.id,
            success=False,
            summary="OpenHands execution not yet implemented.",
            files_changed=[],
            commands_run=[],
            artifacts={},
        )