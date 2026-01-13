import sys

from lathe.core.task import TaskSpec
from lathe.core.orchestrator import Orchestrator
from lathe.bootstrap.openhands import OpenHandsExecutor
from lathe.storage.db import LatheDB
from lathe.cli.commands import list_tasks, show_task, replay_task


def main() -> None:
    db = LatheDB()
    executor = OpenHandsExecutor()
    orchestrator = Orchestrator(executor, db)

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "list":
            list_tasks(db)
            return

        if command == "show" and len(sys.argv) == 3:
            show_task(db, sys.argv[2])
            return

        if command == "replay" and len(sys.argv) == 3:
            replay_task(db, orchestrator, sys.argv[2])
            return

        print("Unknown command")
        print("Usage:")
        print("  python -m lathe.main")
        print("  python -m lathe.main list")
        print("  python -m lathe.main show <task_id>")
        print("  python -m lathe.main replay <task_id>")
        return

    print("The Lathe starting...")
    print("Executor: OpenHands (bootstrap)")
    print("Mode: execution")

    task = TaskSpec(
        id="lathe-smoke-004",
        goal="Verify replay engine is wired",
        scope="bootstrap",
        constraints={},
        inputs={},
    )

    result = orchestrator.run_task(task)

    print("Task complete")
    print("Success:", result.success)
    print("Summary:", result.summary)


if __name__ == "__main__":
    main()