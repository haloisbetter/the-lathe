from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class TaskResult:
    """
    Outcome of a task execution.
    """
    task_id: str
    success: bool
    summary: str
    files_changed: List[str]
    commands_run: List[str]
    artifacts: Dict[str, Any]