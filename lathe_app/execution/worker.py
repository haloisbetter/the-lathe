"""
Execution Worker

Single-threaded daemon worker that drains the execution queue.
Picks up one job at a time, executes its tool calls in order,
and records an append-only ExecutionTrace for each call.

Rules:
- Worker ONLY executes tool calls declared in the run's proposal.
- No dynamic addition of tool calls at execution time.
- Trust and workspace boundary checks are re-applied at execution time.
- No retries on failure.
"""
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from lathe_app.execution.models import (
    ExecutionJob,
    ExecutionJobStatus,
    ExecutionTrace,
)
from lathe_app.execution.queue import ExecutionQueue

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 0.5


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_tool_calls(run) -> List[Dict[str, Any]]:
    """
    Extract tool calls from a RunRecord.

    Looks in run.tool_calls (ToolCallTrace list from the proposal phase).
    Only calls with status=="success" are included — refused/error traces
    were already recorded during agent phase and should not be re-executed.
    """
    calls = []
    for tc in getattr(run, "tool_calls", []):
        if tc.status == "success":
            calls.append({
                "tool_id": tc.tool_id,
                "inputs": tc.inputs,
                "why": tc.why,
            })
    return calls


def _execute_single_tool(
    tool_id: str,
    inputs: Dict[str, Any],
    why: Optional[Dict[str, Any]],
) -> ExecutionTrace:
    """Execute one tool call and return an ExecutionTrace."""
    from lathe_app.tools.registry import get_tool_spec
    from lathe_app.tools.requests import ToolRequest, ToolWhy, ToolRequestError
    from lathe_app.tools.execution import execute_tool

    started_at = _now()

    spec = get_tool_spec(tool_id)
    if spec is None:
        finished_at = _now()
        return ExecutionTrace(
            tool_id=tool_id,
            inputs=inputs,
            why=why,
            started_at=started_at,
            finished_at=finished_at,
            ok=False,
            output=None,
            error={"reason": "nonexistent_tool", "message": f"Tool '{tool_id}' not in registry"},
        )

    tool_why = ToolWhy.from_dict(why) if isinstance(why, dict) else ToolWhy()
    request = ToolRequest(tool_id=tool_id, why=tool_why, inputs=inputs, spec=spec)

    trace = execute_tool(request)
    finished_at = _now()

    ok = trace.status == "success"
    return ExecutionTrace(
        tool_id=tool_id,
        inputs=inputs,
        why=why,
        started_at=started_at,
        finished_at=finished_at,
        ok=ok,
        output=trace.raw_result if ok else None,
        error=(
            {"status": trace.status, "summary": trace.result_summary, "reason": trace.refusal_reason}
            if not ok else None
        ),
    )


def _run_job(job: ExecutionJob, storage, queue: ExecutionQueue) -> None:
    """Execute all tool calls for a job, updating job state as we go."""
    job.status = ExecutionJobStatus.RUNNING
    job.started_at = _now()
    queue.update(job)

    run = storage.load_run(job.run_id)
    if run is None:
        job.status = ExecutionJobStatus.FAILED
        job.finished_at = _now()
        job.error = f"Run {job.run_id} not found at execution time"
        queue.update(job)
        return

    tool_calls = _extract_tool_calls(run)

    any_failed = False
    for tc in tool_calls:
        exec_trace = _execute_single_tool(
            tool_id=tc["tool_id"],
            inputs=tc["inputs"],
            why=tc.get("why"),
        )
        job.tool_traces.append(exec_trace)
        queue.update(job)

        if not exec_trace.ok:
            any_failed = True

    job.finished_at = _now()
    job.status = ExecutionJobStatus.FAILED if any_failed else ExecutionJobStatus.SUCCEEDED
    queue.update(job)

    from lathe_app.review import ReviewAction
    try:
        from lathe_app import _default_review
        _default_review.mark_executed(job.run_id)
    except Exception as e:
        logger.warning("Could not mark run %s as executed: %s", job.run_id, e)


class Worker:
    """
    Single-threaded daemon worker.

    Polls the queue at a fixed interval and processes one job at a time.
    """

    def __init__(self, queue: ExecutionQueue, storage):
        self._queue = queue
        self._storage = storage
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="lathe-exec-worker")
        self._thread.start()
        logger.info("Execution worker started")

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        while self._running:
            try:
                job = self._queue.dequeue()
                if job is not None:
                    logger.info("Worker picked up job %s for run %s", job.id, job.run_id)
                    _run_job(job, self._storage, self._queue)
                    logger.info("Worker finished job %s status=%s", job.id, job.status.value)
                else:
                    time.sleep(_POLL_INTERVAL)
            except Exception as e:
                logger.exception("Worker error: %s", e)
                time.sleep(_POLL_INTERVAL)


_default_worker: Optional[Worker] = None
_worker_lock = threading.Lock()


def get_default_worker() -> Worker:
    global _default_worker
    if _default_worker is None:
        with _worker_lock:
            if _default_worker is None:
                from lathe_app.execution.queue import get_default_queue
                from lathe_app import _default_storage
                _default_worker = Worker(queue=get_default_queue(), storage=_default_storage)
    return _default_worker


def start_default_worker() -> Worker:
    worker = get_default_worker()
    worker.start()
    return worker
