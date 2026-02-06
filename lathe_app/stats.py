"""
Operational Dashboard Signals

Aggregation functions for run statistics, workspace stats,
and health summaries. All computed from in-memory state.
"""
from collections import Counter
from typing import Any, Dict, List, Optional

from lathe_app.artifacts import RunRecord


def compute_run_stats(runs: List[RunRecord]) -> Dict[str, Any]:
    if not runs:
        return {
            "total_runs": 0,
            "by_intent": {},
            "by_model": {},
            "success_rate": 0.0,
            "refusal_rate": 0.0,
            "fallback_rate": 0.0,
            "avg_warnings": 0.0,
            "escalation_count": 0,
        }

    total = len(runs)
    by_intent: Counter = Counter()
    by_model: Counter = Counter()
    successes = 0
    refusals = 0
    fallbacks = 0
    total_warnings = 0
    escalations = 0

    for run in runs:
        by_intent[run.input.intent] += 1
        by_model[run.model_used] += 1

        if run.success:
            successes += 1
        else:
            refusals += 1

        if run.fallback_triggered:
            fallbacks += 1

        classification = getattr(run, "classification", None)
        if classification:
            total_warnings += len(classification.warnings)

        escalation = getattr(run, "escalation", None)
        if escalation:
            escalations += 1

    return {
        "total_runs": total,
        "by_intent": dict(by_intent.most_common()),
        "by_model": dict(by_model.most_common()),
        "success_rate": round(successes / total, 4) if total else 0.0,
        "refusal_rate": round(refusals / total, 4) if total else 0.0,
        "fallback_rate": round(fallbacks / total, 4) if total else 0.0,
        "avg_warnings": round(total_warnings / total, 2) if total else 0.0,
        "escalation_count": escalations,
    }


def compute_health_summary(runs: List[RunRecord], last_n: int = 20) -> Dict[str, Any]:
    recent = sorted(runs, key=lambda r: r.timestamp, reverse=True)[:last_n]

    errors = []
    for run in recent:
        if not run.success:
            output = run.output
            reason = getattr(output, "reason", "unknown") if output else "unknown"
            errors.append({
                "run_id": run.id,
                "timestamp": run.timestamp,
                "intent": run.input.intent,
                "reason": reason,
            })

    recent_success_rate = 0.0
    if recent:
        recent_success_rate = round(
            sum(1 for r in recent if r.success) / len(recent), 4
        )

    return {
        "total_runs": len(runs),
        "recent_runs": len(recent),
        "recent_success_rate": recent_success_rate,
        "recent_errors": errors[:10],
        "healthy": recent_success_rate >= 0.5 if recent else True,
    }


def compute_workspace_stats(workspaces: List[Any]) -> Dict[str, Any]:
    if not workspaces:
        return {
            "total_workspaces": 0,
            "indexed_count": 0,
            "total_files": 0,
            "extensions": {},
            "workspaces": [],
        }

    indexed_count = 0
    total_files = 0
    all_extensions: Counter = Counter()
    ws_summaries = []

    for ws in workspaces:
        ws_dict = ws.to_dict() if hasattr(ws, "to_dict") else {}
        file_count = getattr(ws, "file_count", ws_dict.get("file_count", 0))
        indexed = getattr(ws, "indexed", ws_dict.get("indexed", False))
        name = getattr(ws, "name", ws_dict.get("name", "unknown"))
        exts = getattr(ws, "indexed_extensions", ws_dict.get("indexed_extensions", []))

        if indexed:
            indexed_count += 1
        total_files += file_count
        for ext in exts:
            all_extensions[ext] += 1

        ws_summaries.append({
            "name": name,
            "file_count": file_count,
            "indexed": indexed,
        })

    return {
        "total_workspaces": len(workspaces),
        "indexed_count": indexed_count,
        "total_files": total_files,
        "extensions": dict(all_extensions.most_common()),
        "workspaces": ws_summaries,
    }
