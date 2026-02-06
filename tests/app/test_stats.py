"""
Tests for operational dashboard signals.

Proves:
1) Stats endpoints return stable schema
2) Correct aggregation from seeded run records
3) Health summary works with empty and populated data
4) Workspace stats computed correctly
"""
import pytest
from lathe_app.artifacts import (
    ArtifactInput,
    RunRecord,
    ProposalArtifact,
    RefusalArtifact,
    ObservabilityTrace,
)
from lathe_app.classification import ResultClassification, FailureType
from lathe_app.stats import (
    compute_run_stats,
    compute_health_summary,
    compute_workspace_stats,
)


def make_run(intent="propose", model="deepseek-chat", success=True, classification=None):
    input_data = ArtifactInput(
        intent=intent,
        task="test task",
        why={"goal": "test"},
        model_requested=model,
    )
    obs = ObservabilityTrace.empty()
    if success:
        output = ProposalArtifact.create(
            input_data=input_data,
            proposals=[{"action": "create", "target": "test.py"}],
            assumptions=[],
            risks=[],
            results=[],
            model_fingerprint=model,
            observability=obs,
        )
    else:
        output = RefusalArtifact.create(
            input_data=input_data,
            reason="Test refusal",
            details="Test details",
            observability=obs,
        )
    return RunRecord.create(
        input_data=input_data,
        output=output,
        model_used=model,
        fallback_triggered=False,
        success=success,
        classification=classification or ResultClassification.success(),
    )


class TestRunStats:
    def test_empty_stats(self):
        stats = compute_run_stats([])
        assert stats["total_runs"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["by_intent"] == {}
        assert stats["by_model"] == {}

    def test_basic_stats(self):
        runs = [
            make_run(intent="propose", success=True),
            make_run(intent="propose", success=True),
            make_run(intent="think", success=False),
        ]
        stats = compute_run_stats(runs)
        assert stats["total_runs"] == 3
        assert stats["by_intent"]["propose"] == 2
        assert stats["by_intent"]["think"] == 1
        assert stats["success_rate"] == pytest.approx(2 / 3, abs=0.01)
        assert stats["refusal_rate"] == pytest.approx(1 / 3, abs=0.01)

    def test_model_distribution(self):
        runs = [
            make_run(model="gpt-4"),
            make_run(model="gpt-4"),
            make_run(model="deepseek-chat"),
        ]
        stats = compute_run_stats(runs)
        assert stats["by_model"]["gpt-4"] == 2
        assert stats["by_model"]["deepseek-chat"] == 1

    def test_warning_average(self):
        c1 = ResultClassification.success(warnings=["w1", "w2"])
        c2 = ResultClassification.success(warnings=[])
        runs = [
            make_run(classification=c1),
            make_run(classification=c2),
        ]
        stats = compute_run_stats(runs)
        assert stats["avg_warnings"] == 1.0

    def test_schema_stability(self):
        stats = compute_run_stats([make_run()])
        required_keys = {
            "total_runs", "by_intent", "by_model",
            "success_rate", "refusal_rate", "fallback_rate",
            "avg_warnings", "escalation_count",
        }
        assert required_keys.issubset(set(stats.keys()))


class TestHealthSummary:
    def test_empty_health(self):
        summary = compute_health_summary([])
        assert summary["total_runs"] == 0
        assert summary["healthy"] is True
        assert summary["recent_errors"] == []

    def test_healthy_system(self):
        runs = [make_run(success=True) for _ in range(10)]
        summary = compute_health_summary(runs)
        assert summary["healthy"] is True
        assert summary["recent_success_rate"] == 1.0
        assert summary["recent_errors"] == []

    def test_unhealthy_system(self):
        runs = [make_run(success=False) for _ in range(10)]
        summary = compute_health_summary(runs)
        assert summary["healthy"] is False
        assert len(summary["recent_errors"]) > 0

    def test_health_schema(self):
        summary = compute_health_summary([make_run()])
        required_keys = {
            "total_runs", "recent_runs", "recent_success_rate",
            "recent_errors", "healthy",
        }
        assert required_keys.issubset(set(summary.keys()))


class MockWorkspace:
    def __init__(self, name, file_count, indexed, extensions):
        self.name = name
        self.file_count = file_count
        self.indexed = indexed
        self.indexed_extensions = extensions

    def to_dict(self):
        return {
            "name": self.name,
            "file_count": self.file_count,
            "indexed": self.indexed,
            "indexed_extensions": self.indexed_extensions,
        }


class TestWorkspaceStats:
    def test_empty_stats(self):
        stats = compute_workspace_stats([])
        assert stats["total_workspaces"] == 0
        assert stats["total_files"] == 0

    def test_workspace_aggregation(self):
        workspaces = [
            MockWorkspace("ws1", 50, True, [".py", ".md"]),
            MockWorkspace("ws2", 30, False, [".py", ".json"]),
        ]
        stats = compute_workspace_stats(workspaces)
        assert stats["total_workspaces"] == 2
        assert stats["indexed_count"] == 1
        assert stats["total_files"] == 80
        assert ".py" in stats["extensions"]
        assert stats["extensions"][".py"] == 2

    def test_workspace_schema(self):
        stats = compute_workspace_stats([
            MockWorkspace("test", 10, True, [".py"]),
        ])
        required_keys = {
            "total_workspaces", "indexed_count",
            "total_files", "extensions", "workspaces",
        }
        assert required_keys.issubset(set(stats.keys()))
        assert len(stats["workspaces"]) == 1
        assert stats["workspaces"][0]["name"] == "test"
