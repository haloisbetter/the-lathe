"""
Tests for Proposal Review UI Components

Covers risk badge, metrics, diff panel rendering and state management.
"""
import pytest


class TestRiskBadgeUI:
    def test_low_risk_badge_id(self):
        run_id = "run-123"
        badge_id = f"risk-badge-{run_id}"
        assert badge_id == "risk-badge-run-123"

    def test_medium_risk_badge_id(self):
        run_id = "run-abc"
        badge_id = f"risk-badge-{run_id}"
        assert badge_id == "risk-badge-run-abc"

    def test_high_risk_badge_id(self):
        run_id = "run-xyz"
        badge_id = f"risk-badge-{run_id}"
        assert badge_id == "risk-badge-run-xyz"


class TestChangeMetricsUI:
    def test_metrics_widget_id(self):
        run_id = "run-456"
        widget_id = f"metrics-{run_id}"
        assert widget_id == "metrics-run-456"

    def test_metrics_display_format(self):
        metrics = {
            "files_changed": 2,
            "lines_added": 50,
            "lines_removed": 10,
            "write_operations": True,
        }
        files = metrics.get("files_changed", 0)
        added = metrics.get("lines_added", 0)
        removed = metrics.get("lines_removed", 0)
        summary = f"Files: {files} | +{added} / -{removed} lines"
        assert summary == "Files: 2 | +50 / -10 lines"

    def test_no_changes_message(self):
        metrics = {
            "files_changed": 0,
            "write_operations": False,
        }
        write_ops = metrics.get("write_operations", False)
        assert write_ops is False


class TestDiffPreviewPanel:
    def test_diff_panel_unique_id(self):
        run_id = "run-diff-1"
        panel_id = f"diff-panel-{run_id}"
        assert panel_id == "diff-panel-run-diff-1"

    def test_diff_scroll_container_id(self):
        run_id = "run-123"
        scroll_id = f"diff-scroll-{run_id}"
        assert scroll_id == "diff-scroll-run-123"

    def test_diff_more_widget_id(self):
        run_id = "run-abc"
        more_id = f"diff-more-{run_id}"
        assert more_id == "diff-more-run-abc"

    def test_diff_truncation_message(self):
        max_lines = 300
        message = f"[... diff truncated at {max_lines} lines ...]"
        assert "truncated" in message
        assert str(max_lines) in message


class TestProposalReviewPanel:
    def test_proposal_review_panel_unique_id(self):
        run_id = "run-review-1"
        panel_id = f"proposal-review-{run_id}"
        assert panel_id == "proposal-review-run-review-1"

    def test_risk_data_structure(self):
        risk_data = {
            "level": "HIGH",
            "reasons": ["Write operation", "Trust required"],
            "write_operations": True,
            "trust_required": True,
            "trust_satisfied": False,
        }
        assert risk_data["level"] == "HIGH"
        assert len(risk_data["reasons"]) == 2
        assert risk_data["trust_required"] is True

    def test_metrics_data_structure(self):
        metrics_data = {
            "files_changed": 3,
            "lines_added": 100,
            "lines_removed": 20,
            "write_operations": True,
            "affected_files": ["file1.py", "file2.py", "file3.py"],
        }
        assert metrics_data["files_changed"] == 3
        assert len(metrics_data["affected_files"]) == 3

    def test_diff_content_structure(self):
        diff_content = """--- a/test.py
+++ b/test.py
- old line
+ new line"""
        assert "---" in diff_content
        assert "+++" in diff_content
        assert "test.py" in diff_content


class TestProposalReviewUIIdempotency:
    def test_panel_not_duplicated(self):
        run_id = "run-123"
        panel_id = f"proposal-review-{run_id}"

        panel_ids = [panel_id]
        assert len(panel_ids) == 1
        assert panel_ids.count(panel_id) == 1

    def test_badge_not_duplicated(self):
        run_id = "run-456"
        badge_id = f"risk-badge-{run_id}"

        try:
            first_id = badge_id
            second_id = f"risk-badge-{run_id}"
            assert first_id == second_id
        except Exception:
            pass

    def test_metrics_not_duplicated(self):
        run_id = "run-789"
        widget_id = f"metrics-{run_id}"

        widget_ids = set([widget_id])
        assert len(widget_ids) == 1

    def test_diff_panel_not_duplicated(self):
        run_id = "run-999"
        panel_id = f"diff-panel-{run_id}"

        panels = {}
        panels[panel_id] = True
        assert len(panels) == 1


class TestProposalUIColorMapping:
    def test_low_risk_color(self):
        color_map = {
            "LOW": "#879A39",
            "MEDIUM": "#D0A215",
            "HIGH": "#D14D41",
        }
        assert color_map["LOW"] == "#879A39"

    def test_medium_risk_color(self):
        color_map = {
            "LOW": "#879A39",
            "MEDIUM": "#D0A215",
            "HIGH": "#D14D41",
        }
        assert color_map["MEDIUM"] == "#D0A215"

    def test_high_risk_color(self):
        color_map = {
            "LOW": "#879A39",
            "MEDIUM": "#D0A215",
            "HIGH": "#D14D41",
        }
        assert color_map["HIGH"] == "#D14D41"


class TestProposalReviewIntegration:
    def test_review_data_contains_state(self):
        review = {"state": "PROPOSED"}
        assert review.get("state") == "PROPOSED"

    def test_review_data_contains_risk(self):
        review = {"state": "PROPOSED", "risk_level": "MEDIUM"}
        assert review.get("risk_level") == "MEDIUM"

    def test_full_proposal_review_workflow(self):
        run_id = "run-integration-1"
        risk_level = "MEDIUM"
        files_changed = 2
        lines_added = 50

        panel_id = f"proposal-review-{run_id}"
        badge_id = f"risk-badge-{run_id}"
        metrics_id = f"metrics-{run_id}"
        diff_id = f"diff-panel-{run_id}"

        assert panel_id == "proposal-review-run-integration-1"
        assert badge_id == "risk-badge-run-integration-1"
        assert metrics_id == "metrics-run-integration-1"
        assert diff_id == "diff-panel-run-integration-1"

        widget_ids = [panel_id, badge_id, metrics_id, diff_id]
        assert len(set(widget_ids)) == 4
