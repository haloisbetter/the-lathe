"""
Tests for workspace risk assessment.

Proves:
1) Risk assessment identifies large files
2) Extension distribution computed correctly
3) Directory depth stats computed
4) AST import graph computed for Python files
5) Gravity scores identify hotspots
6) Proposal risk assessment works
"""
import os
import tempfile
import pytest
from lathe_app.workspace.risk import (
    FileMetrics,
    RiskSummary,
    compute_file_metrics,
    compute_extension_distribution,
    compute_depth_stats,
    compute_largest_files,
    parse_python_imports,
    compute_import_graph,
    compute_risk_summary,
    assess_proposal_risk,
)


@pytest.fixture
def risk_workspace(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "deep").mkdir()
    (tmp_path / "tests").mkdir()

    main = tmp_path / "main.py"
    main.write_text("import os\nimport json\nfrom src import utils\nprint('hello')\n")

    utils = tmp_path / "src" / "utils.py"
    utils.write_text("import os\ndef helper(): pass\n")

    deep = tmp_path / "src" / "deep" / "nested.py"
    deep.write_text("from src import utils\ndef deep_func(): pass\n")

    readme = tmp_path / "README.md"
    readme.write_text("# Project\n" * 100)

    test_file = tmp_path / "tests" / "test_main.py"
    test_file.write_text("import main\ndef test_main(): pass\n")

    config = tmp_path / "config.json"
    config.write_text('{"key": "value"}')

    return tmp_path


class TestFileMetrics:
    def test_compute_file_metrics(self, risk_workspace):
        files = [
            str(risk_workspace / "main.py"),
            str(risk_workspace / "src" / "utils.py"),
            str(risk_workspace / "src" / "deep" / "nested.py"),
        ]
        metrics = compute_file_metrics(files, str(risk_workspace))
        assert len(metrics) == 3
        assert all(isinstance(m, FileMetrics) for m in metrics)
        assert any(m.depth == 0 for m in metrics)
        assert any(m.depth == 2 for m in metrics)

    def test_extension_distribution(self, risk_workspace):
        files = [
            str(risk_workspace / "main.py"),
            str(risk_workspace / "src" / "utils.py"),
            str(risk_workspace / "README.md"),
            str(risk_workspace / "config.json"),
        ]
        metrics = compute_file_metrics(files, str(risk_workspace))
        dist = compute_extension_distribution(metrics)
        assert dist[".py"] == 2
        assert dist[".md"] == 1
        assert dist[".json"] == 1

    def test_depth_stats(self, risk_workspace):
        files = [
            str(risk_workspace / "main.py"),
            str(risk_workspace / "src" / "utils.py"),
            str(risk_workspace / "src" / "deep" / "nested.py"),
        ]
        metrics = compute_file_metrics(files, str(risk_workspace))
        max_d, avg_d = compute_depth_stats(metrics)
        assert max_d == 2
        assert avg_d > 0

    def test_depth_stats_empty(self):
        max_d, avg_d = compute_depth_stats([])
        assert max_d == 0
        assert avg_d == 0.0


class TestLargestFiles:
    def test_identifies_largest(self, risk_workspace):
        files = [
            str(risk_workspace / "main.py"),
            str(risk_workspace / "README.md"),
            str(risk_workspace / "config.json"),
        ]
        metrics = compute_file_metrics(files, str(risk_workspace))
        largest = compute_largest_files(metrics, top_n=2)
        assert len(largest) == 2
        assert largest[0]["size_bytes"] >= largest[1]["size_bytes"]
        assert "size_kb" in largest[0]
        assert "path" in largest[0]


class TestImportGraph:
    def test_parse_imports(self, risk_workspace):
        imports = parse_python_imports(str(risk_workspace / "main.py"))
        assert "os" in imports
        assert "json" in imports
        assert "src" in imports

    def test_parse_invalid_python(self, tmp_path):
        bad = tmp_path / "bad.py"
        bad.write_text("def broken(\n")
        imports = parse_python_imports(str(bad))
        assert imports == []

    def test_compute_import_graph(self, risk_workspace):
        py_files = [
            str(risk_workspace / "main.py"),
            str(risk_workspace / "src" / "utils.py"),
            str(risk_workspace / "src" / "deep" / "nested.py"),
            str(risk_workspace / "tests" / "test_main.py"),
        ]
        edges, gravity = compute_import_graph(py_files, str(risk_workspace))
        assert len(edges) > 0
        assert "src" in gravity
        assert gravity["src"] > 0

    def test_gravity_normalized(self, risk_workspace):
        py_files = [
            str(risk_workspace / "main.py"),
            str(risk_workspace / "src" / "utils.py"),
            str(risk_workspace / "src" / "deep" / "nested.py"),
            str(risk_workspace / "tests" / "test_main.py"),
        ]
        _, gravity = compute_import_graph(py_files, str(risk_workspace))
        if gravity:
            assert max(gravity.values()) <= 1.0


class TestRiskSummary:
    def test_compute_full_summary(self, risk_workspace):
        files = [
            str(risk_workspace / "main.py"),
            str(risk_workspace / "src" / "utils.py"),
            str(risk_workspace / "src" / "deep" / "nested.py"),
            str(risk_workspace / "README.md"),
            str(risk_workspace / "config.json"),
            str(risk_workspace / "tests" / "test_main.py"),
        ]
        summary = compute_risk_summary(files, str(risk_workspace))
        assert isinstance(summary, RiskSummary)
        assert summary.total_files == 6
        assert ".py" in summary.extension_distribution
        assert summary.max_depth >= 2
        assert summary.avg_depth > 0
        assert len(summary.largest_files) > 0
        assert summary.import_graph_edges > 0

    def test_summary_to_dict(self, risk_workspace):
        files = [str(risk_workspace / "main.py")]
        summary = compute_risk_summary(files, str(risk_workspace))
        d = summary.to_dict()
        assert "total_files" in d
        assert "extension_distribution" in d
        assert "max_depth" in d
        assert "gravity_scores" in d
        assert "hotspot_files" in d


class TestProposalRisk:
    def test_assess_low_risk(self):
        summary = RiskSummary(
            total_files=10,
            gravity_scores={"utils": 0.3},
            hotspot_files=[],
            largest_files=[],
        )
        result = assess_proposal_risk(["utils.py"], summary)
        assert result["risk_level"] == "low"

    def test_assess_high_risk_hotspot(self):
        summary = RiskSummary(
            total_files=10,
            gravity_scores={"core": 1.0},
            hotspot_files=["core"],
            largest_files=[],
        )
        result = assess_proposal_risk(["core.py"], summary)
        assert result["risk_level"] == "high"
        assert result["touches_hotspot"] is True
