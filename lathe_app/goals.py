"""
Lathe App Goal Persistence

Immutable data structures and pure helpers for goal tracking.
Goals are DATA, not behavior. Verification is STRUCTURAL, not semantic.

NO execution logic. NO side effects. NO imports from lathe/.
"""
from dataclasses import dataclass
from typing import List, Optional, Literal
import time
import uuid


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    reason: str
    evidence: List[str]
    verified_at: float


@dataclass(frozen=True)
class GoalRecord:
    goal_id: str
    description: str
    success_criteria: List[str]

    max_runs: int
    max_executions: int
    max_time_seconds: int

    created_at: float
    status: Literal[
        "pending",
        "in_progress",
        "needs_rethink",
        "completed",
        "abandoned"
    ]

    runs: List[str]
    executions: int
    last_verification: Optional[VerificationResult]


def create_goal(
    description: str,
    success_criteria: List[str],
    *,
    max_runs: int = 5,
    max_executions: int = 3,
    max_time_seconds: int = 600
) -> GoalRecord:
    return GoalRecord(
        goal_id=str(uuid.uuid4()),
        description=description,
        success_criteria=list(success_criteria),
        max_runs=max_runs,
        max_executions=max_executions,
        max_time_seconds=max_time_seconds,
        created_at=time.time(),
        status="pending",
        runs=[],
        executions=0,
        last_verification=None,
    )


def record_verification(
    goal: GoalRecord,
    result: VerificationResult
) -> GoalRecord:
    new_status = "completed" if result.passed else goal.status
    return GoalRecord(
        goal_id=goal.goal_id,
        description=goal.description,
        success_criteria=list(goal.success_criteria),
        max_runs=goal.max_runs,
        max_executions=goal.max_executions,
        max_time_seconds=goal.max_time_seconds,
        created_at=goal.created_at,
        status=new_status,
        runs=list(goal.runs),
        executions=goal.executions,
        last_verification=result,
    )
