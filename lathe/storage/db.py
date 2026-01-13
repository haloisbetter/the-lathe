import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from lathe.core.task import TaskSpec
from lathe.core.result import TaskResult


DB_PATH = Path("data/lathe.db")


class LatheDB:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            with open("lathe/storage/schema.sql", "r", encoding="utf-8") as f:
                conn.executescript(f.read())

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def log_task(self, task: TaskSpec) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tasks
                (id, goal, scope, constraints, inputs, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id,
                    task.goal,
                    task.scope,
                    json.dumps(task.constraints),
                    json.dumps(task.inputs),
                    datetime.utcnow().isoformat(),
                ),
            )

    def log_result(self, result: TaskResult) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO results
                (task_id, success, summary, files_changed, commands_run, artifacts, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.task_id,
                    int(result.success),
                    result.summary,
                    json.dumps(result.files_changed),
                    json.dumps(result.commands_run),
                    json.dumps(result.artifacts),
                    datetime.utcnow().isoformat(),
                ),
            )

    def get_task(self, task_id: str) -> Optional[dict]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None