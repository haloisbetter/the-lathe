from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class TaskSpec:
    """
    Immutable description of a unit of work.
    """
    id: str
    goal: str
    scope: str
    constraints: Dict[str, Any]
    inputs: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "scope": self.scope,
            "constraints": self.constraints,
            "inputs": self.inputs,
        }