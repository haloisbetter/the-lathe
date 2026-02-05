"""
Lathe Observability Module

Passive instrumentation for pipeline tracing.
NEVER affects control flow or decision logic.
"""
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StageRecord:
    """A single pipeline stage record."""
    name: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelRecord:
    """Records model usage during a request."""
    requested: str
    used: str
    fallback_triggered: bool = False
    fallback_reason: Optional[str] = None


@dataclass
class OutcomeRecord:
    """Final outcome classification."""
    success: bool
    refusal: bool
    reason: Optional[str] = None


class ObservabilityRecorder:
    """
    Records pipeline execution for observability.
    
    Guarantees:
    - Stateless outside request lifecycle
    - Never raises exceptions
    - Never affects control flow
    - Optional (pipeline works if disabled)
    """
    
    def __init__(self, enabled: bool = True):
        self._enabled = enabled
        self._trace_id: str = ""
        self._start_time: float = 0.0
        self._stages: List[StageRecord] = []
        self._model: Optional[ModelRecord] = None
        self._outcome: Optional[OutcomeRecord] = None
    
    def start(self) -> str:
        """Initialize a new trace. Returns trace_id."""
        if not self._enabled:
            return ""
        try:
            self._trace_id = str(uuid.uuid4())
            self._start_time = time.time()
            self._stages = []
            self._model = None
            self._outcome = None
            return self._trace_id
        except Exception:
            return ""
    
    def record(self, stage_name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record a pipeline stage. Never raises."""
        if not self._enabled:
            return
        try:
            self._stages.append(StageRecord(
                name=stage_name,
                timestamp=time.time() - self._start_time,
                metadata=metadata or {},
            ))
        except Exception:
            pass
    
    def record_model(
        self,
        requested: str,
        used: str,
        fallback_triggered: bool = False,
        fallback_reason: Optional[str] = None,
    ) -> None:
        """Record model usage. Never raises."""
        if not self._enabled:
            return
        try:
            self._model = ModelRecord(
                requested=requested,
                used=used,
                fallback_triggered=fallback_triggered,
                fallback_reason=fallback_reason,
            )
        except Exception:
            pass
    
    def record_outcome(
        self,
        success: bool,
        refusal: bool,
        reason: Optional[str] = None,
    ) -> None:
        """Record final outcome. Never raises."""
        if not self._enabled:
            return
        try:
            self._outcome = OutcomeRecord(
                success=success,
                refusal=refusal,
                reason=reason,
            )
        except Exception:
            pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Export observability data. Never raises."""
        if not self._enabled:
            return {}
        try:
            result: Dict[str, Any] = {
                "trace_id": self._trace_id,
                "stages": [
                    {
                        "name": s.name,
                        "timestamp": round(s.timestamp, 6),
                        "metadata": s.metadata,
                    }
                    for s in self._stages
                ],
            }
            
            if self._model:
                result["models"] = {
                    "requested": self._model.requested,
                    "used": self._model.used,
                    "fallback_triggered": self._model.fallback_triggered,
                }
                if self._model.fallback_reason:
                    result["models"]["fallback_reason"] = self._model.fallback_reason
            
            if self._outcome:
                result["outcome"] = {
                    "success": self._outcome.success,
                    "refusal": self._outcome.refusal,
                }
                if self._outcome.reason:
                    result["outcome"]["reason"] = self._outcome.reason
            
            return result
        except Exception:
            return {"trace_id": self._trace_id, "error": "observability_export_failed"}
    
    @property
    def trace_id(self) -> str:
        """Get current trace ID."""
        return self._trace_id


def create_recorder(enabled: bool = True) -> ObservabilityRecorder:
    """Factory function to create a recorder."""
    return ObservabilityRecorder(enabled=enabled)
