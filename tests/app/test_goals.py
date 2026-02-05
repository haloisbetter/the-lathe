"""
Tests for lathe_app/goals.py — Goal Persistence data structures and helpers.

Rules:
  - Do NOT mock time or uuid
  - Assert structure, not formatting
"""
import time

from lathe_app.goals import (
    GoalRecord,
    VerificationResult,
    create_goal,
    record_verification,
)
from lathe_app.storage import GoalStorage, InMemoryGoalStorage


class TestCreateGoal:
    def test_creates_with_correct_defaults(self):
        goal = create_goal("add auth", ["login endpoint exists", "tests pass"])
        assert goal.description == "add auth"
        assert goal.success_criteria == ["login endpoint exists", "tests pass"]
        assert goal.max_runs == 5
        assert goal.max_executions == 3
        assert goal.max_time_seconds == 600
        assert goal.status == "pending"
        assert goal.runs == []
        assert goal.executions == 0
        assert goal.last_verification is None

    def test_goal_id_is_unique_per_call(self):
        g1 = create_goal("task a", ["done"])
        g2 = create_goal("task b", ["done"])
        assert g1.goal_id != g2.goal_id

    def test_created_at_is_recent(self):
        before = time.time()
        goal = create_goal("task", ["done"])
        after = time.time()
        assert before <= goal.created_at <= after

    def test_custom_limits(self):
        goal = create_goal(
            "task",
            ["done"],
            max_runs=10,
            max_executions=7,
            max_time_seconds=1200,
        )
        assert goal.max_runs == 10
        assert goal.max_executions == 7
        assert goal.max_time_seconds == 1200

    def test_success_criteria_is_copied(self):
        criteria = ["a", "b"]
        goal = create_goal("task", criteria)
        criteria.append("c")
        assert goal.success_criteria == ["a", "b"]


class TestRecordVerification:
    def test_returns_new_object(self):
        goal = create_goal("task", ["done"])
        result = VerificationResult(
            passed=True, reason="all good", evidence=["test passed"], verified_at=time.time()
        )
        updated = record_verification(goal, result)
        assert updated is not goal

    def test_passed_verification_sets_completed(self):
        goal = create_goal("task", ["done"])
        result = VerificationResult(
            passed=True, reason="all good", evidence=["test passed"], verified_at=time.time()
        )
        updated = record_verification(goal, result)
        assert updated.status == "completed"
        assert updated.last_verification is result

    def test_failed_verification_does_not_complete(self):
        goal = create_goal("task", ["done"])
        result = VerificationResult(
            passed=False, reason="tests failing", evidence=["3 failures"], verified_at=time.time()
        )
        updated = record_verification(goal, result)
        assert updated.status == "pending"
        assert updated.last_verification is result

    def test_original_goal_not_mutated(self):
        goal = create_goal("task", ["done"])
        original_id = goal.goal_id
        original_status = goal.status
        original_verification = goal.last_verification
        result = VerificationResult(
            passed=True, reason="ok", evidence=[], verified_at=time.time()
        )
        record_verification(goal, result)
        assert goal.goal_id == original_id
        assert goal.status == original_status
        assert goal.last_verification is original_verification

    def test_preserves_all_fields(self):
        goal = create_goal("my task", ["criterion 1", "criterion 2"], max_runs=8)
        result = VerificationResult(
            passed=False, reason="nope", evidence=["fail"], verified_at=time.time()
        )
        updated = record_verification(goal, result)
        assert updated.goal_id == goal.goal_id
        assert updated.description == goal.description
        assert updated.success_criteria == goal.success_criteria
        assert updated.max_runs == goal.max_runs
        assert updated.max_executions == goal.max_executions
        assert updated.max_time_seconds == goal.max_time_seconds
        assert updated.created_at == goal.created_at
        assert updated.runs == goal.runs
        assert updated.executions == goal.executions


class TestGoalRecordFrozen:
    def test_goal_is_immutable(self):
        goal = create_goal("task", ["done"])
        try:
            goal.status = "completed"
            assert False, "Should have raised"
        except AttributeError:
            pass

    def test_verification_result_is_immutable(self):
        vr = VerificationResult(passed=True, reason="ok", evidence=[], verified_at=time.time())
        try:
            vr.passed = False
            assert False, "Should have raised"
        except AttributeError:
            pass


class TestGoalStorage:
    def test_save_and_load_roundtrip(self):
        store = InMemoryGoalStorage()
        goal = create_goal("add auth", ["login works"])
        store.save_goal(goal)
        loaded = store.load_goal(goal.goal_id)
        assert loaded is not None
        assert loaded.goal_id == goal.goal_id
        assert loaded.description == goal.description
        assert loaded.success_criteria == goal.success_criteria

    def test_load_missing_returns_none(self):
        store = InMemoryGoalStorage()
        assert store.load_goal("nonexistent") is None

    def test_list_goals_empty(self):
        store = InMemoryGoalStorage()
        assert store.list_goals() == []

    def test_list_goals_returns_all(self):
        store = InMemoryGoalStorage()
        g1 = create_goal("task a", ["done"])
        g2 = create_goal("task b", ["done"])
        store.save_goal(g1)
        store.save_goal(g2)
        goals = store.list_goals()
        assert len(goals) == 2
        ids = {g.goal_id for g in goals}
        assert g1.goal_id in ids
        assert g2.goal_id in ids

    def test_save_overwrites_existing(self):
        store = InMemoryGoalStorage()
        goal = create_goal("task", ["done"])
        store.save_goal(goal)
        result = VerificationResult(
            passed=True, reason="ok", evidence=[], verified_at=time.time()
        )
        updated = record_verification(goal, result)
        store.save_goal(updated)
        loaded = store.load_goal(goal.goal_id)
        assert loaded is not None
        assert loaded.status == "completed"

    def test_goal_storage_is_abstract(self):
        try:
            GoalStorage()
            assert False, "Should have raised"
        except TypeError:
            pass
