import sys

from lathe.core.task import TaskSpec
from lathe.core.orchestrator import Orchestrator
from lathe.bootstrap.openhands import OpenHandsExecutor
from lathe.storage.db import LatheDB
from lathe.cli.commands import (
    list_tasks,
    show_task,
    show_run,
    replay_task,
)


def main() -> None:
    db = LatheDB()
    executor = OpenHandsExecutor()
    orchestrator = Orchestrator(executor, db)

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "list":
            list_tasks(db)
            return

        if cmd == "show" and len(sys.argv) == 3:
            show_task(db, sys.argv[2])
            return

        if cmd == "run" and len(sys.argv) == 3:
            show_run(db, int(sys.argv[2]))
            return

        if cmd == "replay" and len(sys.argv) == 3:
            replay_task(db, orchestrator, sys.argv[2])
            return

        print("Usage:")
        print("  python -m lathe.main")
        print("  python -m lathe.main list")
        print("  python -m lathe.main show <task_id>")
        print("  python -m lathe.main run <run_id>")
        print("  python -m lathe.main replay <task_id>")
        return

    task = TaskSpec(
        id="lathe-smoke-005",
        goal="Verify multi-run history",
        scope="bootstrap",
        constraints={},
        inputs={},
    )

    result = orchestrator.run_task(task)
    print("Task executed, run recorded")
    print("Success:", result.success)