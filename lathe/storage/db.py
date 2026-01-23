import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

from lathe.core.task import TaskSpec
from lathe.core.result import TaskResult


DB_PATH = Path("data/lathe.db")
SCHEMA_PATH = Path("lathe/storage/schema.sql")


class LatheDB:
    def __init__(self, db_path: Path = DB_PATH, schema_path: Path = SCHEMA_PATH):
        self.db_path = db_path
        self.schema_path = schema_path
        self._ensure_db()

    def _ensure_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            with open(self.schema_path, "r", encoding="utf-8") as f:
                conn.executescript(f.read())

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    # ---------- TASKS ----------

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

    def list_tasks(self) -> List[Dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT id, goal, created_at FROM tasks ORDER BY created_at DESC"
            )
            return [dict(row) for row in cur.fetchall()]

    def get_task(self, task_id: str) -> Optional[Dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def load_task_spec(self, task_id: str) -> Optional[TaskSpec]:
        row = self.get_task(task_id)
        if not row:
            return None

        return TaskSpec(
            id=row["id"],
            goal=row["goal"],
            scope=row["scope"],
            constraints=json.loads(row["constraints"]),
            inputs=json.loads(row["inputs"]),
        )

    # ---------- RUNS ----------

    def log_run(self, result: TaskResult) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO runs
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
            return cur.lastrowid

    def list_runs(self, task_id: str) -> List[Dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                """
                SELECT run_id, success, completed_at
                FROM runs
                WHERE task_id = ?
                ORDER BY run_id DESC
                """,
                (task_id,),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_run(self, run_id: int) -> Optional[Dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None