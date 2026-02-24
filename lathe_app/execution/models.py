"""
Execution Service Data Models

ExecutionJob: represents one execution attempt for a run.
ExecutionTrace: append-only record of a single tool call execution.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


class ExecutionJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class ExecutionTrace:
    """Append-only record of a single tool call executed during a job."""
    tool_id: str
    inputs: Dict[str, Any]
    why: Optional[Dict[str, Any]]
    started_at: str
    finished_at: str
    ok: bool
    output: Optional[Dict[str, Any]]
    error: Optional[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "tool_id": self.tool_id,
            "inputs": self.inputs,
            "why": self.why,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "ok": self.ok,
        }
        if self.ok:
            d["output"] = self.output
        else:
            d["error"] = self.error
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionTrace":
        return cls(
            tool_id=data["tool_id"],
            inputs=data.get("inputs", {}),
            why=data.get("why"),
            started_at=data["started_at"],
            finished_at=data["finished_at"],
            ok=data["ok"],
            output=data.get("output"),
            error=data.get("error"),
        )


@dataclass
class ExecutionJob:
    """One execution attempt for an approved run."""
    id: str
    run_id: str
    status: ExecutionJobStatus
    created_at: str
    started_at: Optional[str]
    finished_at: Optional[str]
    error: Optional[str]
    tool_traces: List[ExecutionTrace] = field(default_factory=list)

    @classmethod
    def create(cls, run_id: str) -> "ExecutionJob":
        return cls(
            id=_gen_id("job"),
            run_id=run_id,
            status=ExecutionJobStatus.QUEUED,
            created_at=_now(),
            started_at=None,
            finished_at=None,
            error=None,
            tool_traces=[],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
            "tool_traces": [t.to_dict() for t in self.tool_traces],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionJob":
        return cls(
            id=data["id"],
            run_id=data["run_id"],
            status=ExecutionJobStatus(data["status"]),
            created_at=data["created_at"],
            started_at=data.get("started_at"),
            finished_at=data.get("finished_at"),
            error=data.get("error"),
            tool_traces=[
                ExecutionTrace.from_dict(t)
                for t in data.get("tool_traces", [])
            ],
        )
