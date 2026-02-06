"""
Tests for failure taxonomy classification.

Proves:
1) Every response includes a classification object
2) Success classification includes warnings and confidence
3) Failure classification assigns correct failure types
4) Structural, semantic, unsafe classifications work
"""
import pytest
from lathe_app.classification import (
    FailureType,
    ResultClassification,
)


class TestFailureType:
    def test_all_types_exist(self):
        assert FailureType.SUCCESS.value == "success"
        assert FailureType.STRUCTURAL_FAILURE.value == "structural_failure"
        assert FailureType.SEMANTIC_FAILURE.value == "semantic_failure"
        assert FailureType.HALLUCINATED_REFERENCE.value == "hallucinated_reference"
        assert FailureType.INCOMPLETE_SCOPE.value == "incomplete_scope"
        assert FailureType.UNSAFE_PLAN.value == "unsafe_plan"


class TestResultClassification:
    def test_success_factory(self):
        c = ResultClassification.success(confidence=0.95)
        assert c.failure_type == FailureType.SUCCESS
        assert c.confidence == 0.95
        assert c.warnings == []
        assert c.reasons == []

    def test_success_with_warnings(self):
        c = ResultClassification.success(
            confidence=0.7,
            warnings=["high_assumption_count"],
        )
        assert c.failure_type == FailureType.SUCCESS
        assert len(c.warnings) == 1
        assert c.confidence == 0.7

    def test_structural_failure_factory(self):
        c = ResultClassification.structural_failure(
            reasons=["validation failed", "bad schema"],
        )
        assert c.failure_type == FailureType.STRUCTURAL_FAILURE
        assert c.confidence == 1.0
        assert len(c.reasons) == 2

    def test_to_dict(self):
        c = ResultClassification.success(confidence=0.9, warnings=["w1"])
        d = c.to_dict()
        assert d["failure_type"] == "success"
        assert d["confidence"] == 0.9
        assert d["warnings"] == ["w1"]
        assert d["reasons"] == []


class TestFromPipelineResult:
    def test_success_classification(self):
        response = {
            "proposals": [{"action": "create", "target": "foo.py"}],
            "assumptions": [],
            "risks": [],
            "results": [],
            "model_fingerprint": "test-123",
        }
        c = ResultClassification.from_pipeline_result(response, success=True)
        assert c.failure_type == FailureType.SUCCESS
        assert c.confidence > 0

    def test_empty_proposals_warning(self):
        response = {
            "proposals": [],
            "assumptions": [],
            "risks": [],
            "results": [],
            "model_fingerprint": "test-123",
        }
        c = ResultClassification.from_pipeline_result(response, success=True)
        assert "empty_proposals" in c.warnings
        assert c.confidence <= 0.5

    def test_high_assumptions_warning(self):
        response = {
            "proposals": [{"action": "create", "target": "foo.py"}],
            "assumptions": ["a1", "a2", "a3", "a4", "a5", "a6"],
            "risks": [],
            "results": [],
            "model_fingerprint": "test-123",
        }
        c = ResultClassification.from_pipeline_result(response, success=True)
        assert "high_assumption_count" in c.warnings

    def test_high_risk_warning(self):
        response = {
            "proposals": [{"action": "create", "target": "foo.py"}],
            "assumptions": [],
            "risks": ["This is a breaking change"],
            "results": [],
            "model_fingerprint": "test-123",
        }
        c = ResultClassification.from_pipeline_result(response, success=True)
        assert any("high_risk" in w for w in c.warnings)

    def test_missing_target_warning(self):
        response = {
            "proposals": [{"action": "create"}],
            "assumptions": [],
            "risks": [],
            "results": [],
            "model_fingerprint": "test-123",
        }
        c = ResultClassification.from_pipeline_result(response, success=True)
        assert "missing_target_in_proposal" in c.warnings

    def test_validation_failure(self):
        response = {
            "refusal": True,
            "reason": "Model output validation failed",
            "details": "Invalid JSON",
            "results": [],
        }
        c = ResultClassification.from_pipeline_result(response, success=False)
        assert c.failure_type == FailureType.STRUCTURAL_FAILURE

    def test_unsafe_failure(self):
        response = {
            "refusal": True,
            "reason": "Unsafe operation denied",
            "details": "Cannot modify system files",
            "results": [],
        }
        c = ResultClassification.from_pipeline_result(response, success=False)
        assert c.failure_type == FailureType.UNSAFE_PLAN

    def test_authorization_failure(self):
        response = {
            "refusal": True,
            "reason": "Model not authorized for intent",
            "details": "Tier B model",
            "results": [],
        }
        c = ResultClassification.from_pipeline_result(response, success=False)
        assert c.failure_type == FailureType.STRUCTURAL_FAILURE
