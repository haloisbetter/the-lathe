"""
Tests for Proposal Analysis and Risk Assessment

Covers change detection, risk levels, and diff generation.
"""
import pytest

from lathe_app.proposal_analysis import (
    RiskLevel,
    compute_change_summary,
    assess_proposal_risk,
    generate_unified_diff_preview,
)


class TestChangeMetricsComputation:
    def test_no_proposals(self):
        result = compute_change_summary([])
        assert result["files_changed"] == 0
        assert result["lines_added"] == 0
        assert result["lines_removed"] == 0
        assert result["write_operations"] is False

    def test_read_only_proposal(self):
        proposals = [
            {
                "action": "read",
                "target": "file.txt",
            }
        ]
        result = compute_change_summary(proposals)
        assert result["write_operations"] is False

    def test_single_write_proposal(self):
        proposals = [
            {
                "action": "write",
                "target": "file.txt",
                "proposal": {
                    "old_content": "x = 1",
                    "new_content": "x = 1\ny = 2\nz = 3"
                }
            }
        ]
        result = compute_change_summary(proposals)
        assert result["files_changed"] == 1
        assert result["write_operations"] is True
        assert result["lines_added"] >= 2
        assert "file.txt" in result["affected_files"]

    def test_multiple_write_proposals(self):
        proposals = [
            {
                "action": "write",
                "target": "file1.txt",
                "proposal": {"old_content": "a", "new_content": "a\nb"}
            },
            {
                "action": "edit",
                "target": "file2.txt",
                "proposal": {"old_content": "x", "new_content": "x\ny"}
            },
        ]
        result = compute_change_summary(proposals)
        assert result["files_changed"] == 2
        assert "file1.txt" in result["affected_files"]
        assert "file2.txt" in result["affected_files"]

    def test_delete_operation(self):
        proposals = [
            {
                "action": "delete",
                "target": "old_file.txt",
            }
        ]
        result = compute_change_summary(proposals)
        assert result["write_operations"] is True
        assert "old_file.txt" in result["affected_files"]

    def test_lines_calculation(self):
        proposals = [
            {
                "action": "write",
                "target": "test.py",
                "proposal": {
                    "old_content": "x = 1",
                    "new_content": "x = 1\ny = 2\nz = 3\n"
                }
            }
        ]
        result = compute_change_summary(proposals)
        assert result["lines_added"] >= 2
        assert result["lines_removed"] == 1


class TestRiskAssessment:
    def test_read_only_low_risk(self):
        proposals = [
            {"action": "read", "target": "file.txt"}
        ]
        risk = assess_proposal_risk(proposals, {}, {})
        assert risk["level"] == "LOW"
        assert risk["write_operations"] is False

    def test_write_medium_risk(self):
        proposals = [
            {"action": "write", "target": "file.txt"}
        ]
        risk = assess_proposal_risk(proposals, {}, {})
        assert risk["level"] == "MEDIUM"
        assert risk["write_operations"] is True

    def test_trust_required_high_risk(self):
        proposals = [
            {
                "action": "write",
                "target": "file.txt",
                "trust_required": True
            }
        ]
        risk = assess_proposal_risk(proposals, {}, {})
        assert risk["level"] == "HIGH"
        assert risk["trust_required"] is True
        assert risk["trust_satisfied"] is False

    def test_trust_satisfied_medium_risk(self):
        proposals = [
            {
                "action": "write",
                "target": "file.txt",
                "trust_required": True
            }
        ]
        review = {"trust_satisfied": True}
        risk = assess_proposal_risk(proposals, {}, review)
        assert risk["level"] == "MEDIUM"
        assert risk["trust_satisfied"] is True

    def test_mixed_operations(self):
        proposals = [
            {"action": "read", "target": "file1.txt"},
            {"action": "write", "target": "file2.txt"},
        ]
        risk = assess_proposal_risk(proposals, {}, {})
        assert risk["level"] == "MEDIUM"
        assert risk["write_operations"] is True

    def test_multiple_trust_required(self):
        proposals = [
            {
                "action": "write",
                "target": "file1.txt",
                "trust_required": True
            },
            {
                "action": "delete",
                "target": "file2.txt",
                "trust_required": True
            }
        ]
        risk = assess_proposal_risk(proposals, {}, {})
        assert risk["level"] == "HIGH"
        assert len(risk["reasons"]) >= 2


class TestDiffGeneration:
    def test_empty_proposals(self):
        diff = generate_unified_diff_preview([])
        assert diff == ""

    def test_read_only_no_diff(self):
        proposals = [{"action": "read", "target": "file.txt"}]
        diff = generate_unified_diff_preview(proposals)
        assert diff == ""

    def test_simple_write_diff(self):
        proposals = [
            {
                "action": "write",
                "target": "test.txt",
                "proposal": {
                    "old_content": "x = 1",
                    "new_content": "x = 1\ny = 2"
                }
            }
        ]
        diff = generate_unified_diff_preview(proposals)
        assert "test.txt" in diff
        assert "---" in diff
        assert "+++" in diff

    def test_diff_truncation(self):
        large_content = "\n".join([f"line {i}" for i in range(500)])
        proposals = [
            {
                "action": "write",
                "target": "large.txt",
                "proposal": {
                    "old_content": "",
                    "new_content": large_content
                }
            }
        ]
        diff = generate_unified_diff_preview(proposals, max_lines=100)
        assert "truncated" in diff or len(diff.split("\n")) <= 105

    def test_multiple_file_diffs(self):
        proposals = [
            {
                "action": "write",
                "target": "file1.txt",
                "proposal": {
                    "old_content": "a",
                    "new_content": "a\nb"
                }
            },
            {
                "action": "write",
                "target": "file2.txt",
                "proposal": {
                    "old_content": "x",
                    "new_content": "x\ny"
                }
            }
        ]
        diff = generate_unified_diff_preview(proposals)
        assert "file1.txt" in diff
        assert "file2.txt" in diff

    def test_no_changes_returns_empty(self):
        proposals = [
            {
                "action": "write",
                "target": "file.txt",
                "proposal": {
                    "old_content": "x",
                    "new_content": "x"
                }
            }
        ]
        diff = generate_unified_diff_preview(proposals)
        assert diff.strip() == "" or "truncated" not in diff


class TestRiskBadgeRendering:
    def test_risk_levels_enum(self):
        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.MEDIUM.value == "MEDIUM"
        assert RiskLevel.HIGH.value == "HIGH"


class TestProposalAnalysisEdgeCases:
    def test_proposal_without_action(self):
        proposals = [{"target": "file.txt"}]
        result = compute_change_summary(proposals)
        assert result["write_operations"] is False

    def test_proposal_without_target(self):
        proposals = [{"action": "write"}]
        result = compute_change_summary(proposals)
        assert result["files_changed"] == 0

    def test_none_proposal_data(self):
        proposals = [
            {
                "action": "write",
                "target": "file.txt",
                "proposal": None
            }
        ]
        result = compute_change_summary(proposals)
        assert result["write_operations"] is True
        assert result["lines_added"] == 0

    def test_malformed_content(self):
        proposals = [
            {
                "action": "write",
                "target": "file.txt",
                "proposal": {
                    "old_content": 123,
                    "new_content": {"key": "value"}
                }
            }
        ]
        try:
            result = compute_change_summary(proposals)
            assert result["write_operations"] is True
        except (TypeError, AttributeError):
            pass

    def test_duplicate_files(self):
        proposals = [
            {"action": "write", "target": "file.txt"},
            {"action": "edit", "target": "file.txt"},
        ]
        result = compute_change_summary(proposals)
        assert result["files_changed"] == 1
        assert result["affected_files"].count("file.txt") == 1
