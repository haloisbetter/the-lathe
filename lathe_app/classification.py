"""
Failure Taxonomy Classification

Structured classification attached to every RunRecord.
Types: success, structural_failure, semantic_failure,
       hallucinated_reference, incomplete_scope, unsafe_plan

Classification is computed in the app layer only.
Kernel remains pure.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class FailureType(Enum):
    SUCCESS = "success"
    STRUCTURAL_FAILURE = "structural_failure"
    SEMANTIC_FAILURE = "semantic_failure"
    HALLUCINATED_REFERENCE = "hallucinated_reference"
    INCOMPLETE_SCOPE = "incomplete_scope"
    UNSAFE_PLAN = "unsafe_plan"


@dataclass
class ResultClassification:
    failure_type: FailureType
    confidence: float
    warnings: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_type": self.failure_type.value,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "reasons": self.reasons,
        }

    @classmethod
    def success(cls, confidence: float = 1.0, warnings: List[str] = None) -> "ResultClassification":
        return cls(
            failure_type=FailureType.SUCCESS,
            confidence=confidence,
            warnings=warnings or [],
            reasons=[],
        )

    @classmethod
    def structural_failure(cls, reasons: List[str], warnings: List[str] = None) -> "ResultClassification":
        return cls(
            failure_type=FailureType.STRUCTURAL_FAILURE,
            confidence=1.0,
            warnings=warnings or [],
            reasons=reasons,
        )

    @classmethod
    def from_pipeline_result(cls, response: Dict[str, Any], success: bool) -> "ResultClassification":
        if not success:
            return cls._classify_failure(response)
        return cls._classify_success(response)

    @classmethod
    def _classify_failure(cls, response: Dict[str, Any]) -> "ResultClassification":
        reason = response.get("reason", "")
        details = response.get("details", "")
        warnings = []

        if "validation failed" in reason.lower() or "does not match" in reason.lower():
            return cls(
                failure_type=FailureType.STRUCTURAL_FAILURE,
                confidence=1.0,
                warnings=warnings,
                reasons=[reason, details] if details else [reason],
            )

        if "not authorized" in reason.lower():
            return cls(
                failure_type=FailureType.STRUCTURAL_FAILURE,
                confidence=1.0,
                warnings=warnings,
                reasons=[reason, details] if details else [reason],
            )

        if "unsafe" in reason.lower() or "denied" in reason.lower():
            return cls(
                failure_type=FailureType.UNSAFE_PLAN,
                confidence=0.9,
                warnings=warnings,
                reasons=[reason, details] if details else [reason],
            )

        return cls(
            failure_type=FailureType.STRUCTURAL_FAILURE,
            confidence=0.8,
            warnings=warnings,
            reasons=[reason, details] if details else [reason],
        )

    @classmethod
    def _classify_success(cls, response: Dict[str, Any]) -> "ResultClassification":
        warnings = []
        confidence = 1.0

        proposals = response.get("proposals", [])
        assumptions = response.get("assumptions", [])
        risks = response.get("risks", [])

        if not proposals and not response.get("steps", []):
            warnings.append("empty_proposals")
            confidence = min(confidence, 0.5)

        if len(assumptions) > 5:
            warnings.append("high_assumption_count")
            confidence = min(confidence, 0.7)

        if risks:
            for risk in risks:
                risk_str = str(risk).lower()
                if any(w in risk_str for w in ("breaking", "destructive", "data loss", "irreversible")):
                    warnings.append(f"high_risk: {risk}")
                    confidence = min(confidence, 0.6)

        for proposal in proposals:
            target = str(proposal.get("target", proposal.get("file", "")))
            if not target or target == "unknown":
                warnings.append("missing_target_in_proposal")
                confidence = min(confidence, 0.7)

        return cls(
            failure_type=FailureType.SUCCESS,
            confidence=round(confidence, 2),
            warnings=warnings,
            reasons=[],
        )
