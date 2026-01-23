"""
Core orchestration module for The Lathe.

Contains the task execution pipeline and orchestration logic.

Responsibilities:
- Task specification and validation
- Orchestration of task execution
- Result collection and storage
- Executor abstraction

Does NOT contain:
- Specific executor implementations (see bootstrap/)
- Storage implementation (see storage/)
- AI reasoning logic
"""

from .task import TaskSpec
from .result import TaskResult
from .orchestrator import Orchestrator
from .executor import BootstrapExecutor

__all__ = ["TaskSpec", "TaskResult", "Orchestrator", "BootstrapExecutor"]
