"""
Lathe App Storage Layer

Pluggable persistence for runs and artifacts.
Default: in-memory (no disk I/O).

All state lives here. Lathe remains pure.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from lathe_app.artifacts import RunRecord
from lathe_app.goals import GoalRecord


class Storage(ABC):
    """
    Abstract storage interface.
    
    Implementations must be thread-safe if used concurrently.
    """
    
    @abstractmethod
    def save_run(self, run: RunRecord) -> None:
        """Persist a RunRecord."""
        pass
    
    @abstractmethod
    def load_run(self, run_id: str) -> Optional[RunRecord]:
        """Load a RunRecord by ID. Returns None if not found."""
        pass
    
    @abstractmethod
    def list_runs(self) -> List[str]:
        """List all stored run IDs."""
        pass
    
    @abstractmethod
    def delete_run(self, run_id: str) -> bool:
        """Delete a run. Returns True if deleted, False if not found."""
        pass


class InMemoryStorage(Storage):
    """
    In-memory storage implementation.
    
    No persistence to disk. Data is lost on process exit.
    Suitable for testing and ephemeral workflows.
    """
    
    def __init__(self):
        self._runs: Dict[str, RunRecord] = {}
    
    def save_run(self, run: RunRecord) -> None:
        """Store a run in memory."""
        self._runs[run.id] = run
    
    def load_run(self, run_id: str) -> Optional[RunRecord]:
        """Retrieve a run from memory."""
        return self._runs.get(run_id)
    
    def list_runs(self) -> List[str]:
        """List all run IDs in memory."""
        return list(self._runs.keys())
    
    def delete_run(self, run_id: str) -> bool:
        """Remove a run from memory."""
        if run_id in self._runs:
            del self._runs[run_id]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all stored runs. For testing only."""
        self._runs.clear()
    
    def get_all_runs(self) -> List[RunRecord]:
        """Get all runs. For query operations."""
        return list(self._runs.values())


class GoalStorage(ABC):
    """
    Abstract goal storage interface.

    Implementations must be thread-safe if used concurrently.
    """

    @abstractmethod
    def save_goal(self, goal: GoalRecord) -> None:
        pass

    @abstractmethod
    def load_goal(self, goal_id: str) -> Optional[GoalRecord]:
        pass

    @abstractmethod
    def list_goals(self) -> List[GoalRecord]:
        pass


class InMemoryGoalStorage(GoalStorage):
    """
    In-memory goal storage implementation.

    No persistence to disk. Data is lost on process exit.
    """

    def __init__(self):
        self._goals: Dict[str, GoalRecord] = {}

    def save_goal(self, goal: GoalRecord) -> None:
        self._goals[goal.goal_id] = goal

    def load_goal(self, goal_id: str) -> Optional[GoalRecord]:
        return self._goals.get(goal_id)

    def list_goals(self) -> List[GoalRecord]:
        return list(self._goals.values())


class NullStorage(Storage):
    """
    Null storage that discards everything.
    
    Useful when persistence is explicitly disabled.
    """
    
    def save_run(self, run: RunRecord) -> None:
        pass
    
    def load_run(self, run_id: str) -> Optional[RunRecord]:
        return None
    
    def list_runs(self) -> List[str]:
        return []
    
    def delete_run(self, run_id: str) -> bool:
        return False
