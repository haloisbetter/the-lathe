"""
Execution Service

High-level API for enqueueing and querying execution jobs.
Called by HTTP route handlers in server.py.
"""
import logging
from typing import Any, Dict, List, Optional

from lathe_app.execution.models import ExecutionJob, ExecutionJobStatus, ExecutionTrace
from lathe_app.execution.queue import ExecutionQueue

logger = logging.getLogger(__name__)


class ExecutionService:
    """
    Facade over queue + review manager for run execution.

    Callers:
    - POST /runs/<run_id>/execute  → enqueue_run()
    - GET  /runs/<run_id>/execute  → get_latest_job_for_run()
    - GET  /jobs/<job_id>          → get_job()
    - GET  /runs/<run_id>/tool_traces → get_run_traces()
    """

    def __init__(self, queue: ExecutionQueue, storage, review_manager):
        self._queue = queue
        self._storage = storage
        self._review = review_manager

    def enqueue_run(self, run_id: str) -> Dict[str, Any]:
        """
        Enqueue execution for an approved run.

        Returns a response dict suitable for direct JSON serialisation.

        Error codes:
        - run_not_found    → 404
        - run_not_approved → 409
        - already_executing → 409
        """
        run = self._storage.load_run(run_id)
        if run is None:
            return {"ok": False, "error": "run_not_found", "status_code": 404}

        if not self._review.is_approved(run_id):
            state = self._review.get_state(run_id)
            state_str = state.value if state else "unknown"
            return {
                "ok": False,
                "error": "run_not_approved",
                "current_state": state_str,
                "status_code": 409,
            }

        if self._queue.has_active_job(run_id):
            return {
                "ok": False,
                "error": "already_executing",
                "status_code": 409,
            }

        job = ExecutionJob.create(run_id)
        self._queue.enqueue(job)

        return {
            "ok": True,
            "run_id": run_id,
            "job_id": job.id,
            "status": job.status.value,
            "results": [],
        }

    def get_latest_job_for_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Return the most recent job for a run, or None if no jobs exist."""
        jobs = self._queue.get_jobs_for_run(run_id)
        if not jobs:
            return None
        latest = sorted(jobs, key=lambda j: j.created_at, reverse=True)[0]
        return self._job_summary(latest)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Return full job detail including all traces, or None."""
        job = self._queue.get_job(job_id)
        if job is None:
            return None
        return job.to_dict()

    def get_run_traces(self, run_id: str) -> List[Dict[str, Any]]:
        """Return all execution traces across all jobs for a run (for TUI replay)."""
        jobs = self._queue.get_jobs_for_run(run_id)
        if not jobs:
            return []
        traces = []
        for job in sorted(jobs, key=lambda j: j.created_at):
            for t in job.tool_traces:
                d = t.to_dict()
                d["job_id"] = job.id
                traces.append(d)
        return traces

    def _job_summary(self, job: ExecutionJob) -> Dict[str, Any]:
        return {
            "id": job.id,
            "run_id": job.run_id,
            "status": job.status.value,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "error": job.error,
            "trace_count": len(job.tool_traces),
            "traces_summary": [
                {"tool_id": t.tool_id, "ok": t.ok, "started_at": t.started_at}
                for t in job.tool_traces
            ],
            "results": [],
        }
