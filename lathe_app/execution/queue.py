"""
Execution Queue

In-memory queue backed by SQLite for persistence.
Jobs survive server restarts; the worker re-picks queued jobs on startup.

Thread-safety: all mutations are protected by a single lock.
"""
import json
import logging
import os
import sqlite3
import threading
from typing import Dict, List, Optional

from lathe_app.execution.models import ExecutionJob, ExecutionJobStatus

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = os.environ.get(
    "LATHE_EXEC_DB",
    os.path.join(os.path.expanduser("~"), ".lathe", "execution.db"),
)


class ExecutionQueue:
    """
    Durable FIFO queue for ExecutionJobs.

    Storage: SQLite (one table, jobs serialised as JSON blobs).
    In-memory index for fast lookups.
    """

    def __init__(self, db_path: str = _DEFAULT_DB_PATH):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._memory: Dict[str, ExecutionJob] = {}
        self._queue: List[str] = []
        self._init_db()
        self._load_from_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_jobs (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    data TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_exec_jobs_run_id ON execution_jobs(run_id)"
            )
            conn.commit()

    def _load_from_db(self) -> None:
        """Load all jobs into memory on startup. Re-queue any that were interrupted."""
        with self._get_conn() as conn:
            rows = conn.execute("SELECT data FROM execution_jobs ORDER BY rowid").fetchall()
        for row in rows:
            try:
                job = ExecutionJob.from_dict(json.loads(row["data"]))
                self._memory[job.id] = job
                if job.status in (ExecutionJobStatus.QUEUED, ExecutionJobStatus.RUNNING):
                    job.status = ExecutionJobStatus.QUEUED
                    job.started_at = None
                    self._queue.append(job.id)
                    self._persist_job(job)
            except Exception as e:
                logger.warning("Failed to load job from DB: %s", e)

    def _persist_job(self, job: ExecutionJob) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO execution_jobs (id, run_id, status, data)
                VALUES (?, ?, ?, ?)
                """,
                (job.id, job.run_id, job.status.value, json.dumps(job.to_dict())),
            )
            conn.commit()

    def enqueue(self, job: ExecutionJob) -> None:
        with self._lock:
            self._memory[job.id] = job
            self._queue.append(job.id)
            self._persist_job(job)

    def dequeue(self) -> Optional[ExecutionJob]:
        with self._lock:
            while self._queue:
                job_id = self._queue.pop(0)
                job = self._memory.get(job_id)
                if job and job.status == ExecutionJobStatus.QUEUED:
                    return job
        return None

    def update(self, job: ExecutionJob) -> None:
        with self._lock:
            self._memory[job.id] = job
            self._persist_job(job)

    def get_job(self, job_id: str) -> Optional[ExecutionJob]:
        with self._lock:
            return self._memory.get(job_id)

    def get_jobs_for_run(self, run_id: str) -> List[ExecutionJob]:
        with self._lock:
            return [j for j in self._memory.values() if j.run_id == run_id]

    def has_active_job(self, run_id: str) -> bool:
        """True if the run already has a queued or running job."""
        with self._lock:
            return any(
                j.run_id == run_id
                and j.status in (ExecutionJobStatus.QUEUED, ExecutionJobStatus.RUNNING)
                for j in self._memory.values()
            )


_default_queue: Optional[ExecutionQueue] = None
_queue_lock = threading.Lock()


def get_default_queue() -> ExecutionQueue:
    global _default_queue
    if _default_queue is None:
        with _queue_lock:
            if _default_queue is None:
                _default_queue = ExecutionQueue()
    return _default_queue
