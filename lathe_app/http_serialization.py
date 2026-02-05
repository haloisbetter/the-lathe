"""
HTTP Serialization utilities for lathe_app.

Converts dataclasses and Path objects to JSON-safe dictionaries.
"""
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict
from enum import Enum

from lathe_app.artifacts import RunRecord
from lathe_app.executor import ExecutionResult, ExecutionStatus


def _make_jsonable(obj: Any) -> Any:
    """Recursively convert an object to JSON-serializable form."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: _make_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_jsonable(v) for v in obj]
    if is_dataclass(obj) and not isinstance(obj, type):
        return _make_jsonable(asdict(obj))
    return str(obj)


def to_jsonable_runrecord(run: RunRecord) -> Dict[str, Any]:
    """
    Serialize a RunRecord to a JSON-safe dictionary.
    
    Always includes "results": [] for OpenWebUI compatibility.
    """
    data = _make_jsonable(run)
    if "results" not in data:
        data["results"] = []
    return data


def to_jsonable_execution_result(result: ExecutionResult) -> Dict[str, Any]:
    """
    Serialize an ExecutionResult to a JSON-safe dictionary.
    
    Always includes "results": [] for OpenWebUI compatibility.
    """
    data = {
        "status": result.status.value,
        "diff": _make_jsonable(result.diff),
        "error": result.error,
        "applied": result.applied,
        "results": [],
    }
    return data
