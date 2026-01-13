from lathe.core.task import TaskSpec
from lathe.core.orchestrator import Orchestrator
from lathe.bootstrap.openhands import OpenHandsExecutor
from lathe.storage.db import LatheDB


def main() -> None:
    print("The Lathe starting...")
    print("Executor: OpenHands (bootstrap)")
    print("Persistence: SQLite")

    task = TaskSpec(
        id="lathe-smoke-002",
        goal="Verify SQLite logging path",
        scope="bootstrap",
        constraints={},
        inputs={},
    )

    executor = OpenHandsExecutor()
    db = LatheDB()
    orchestrator = Orchestrator(executor, db)

    result = orchestrator.run_task(task)

    print("Task complete")
    print("Success:", result.success)
    print("Summary:", result.summary)


if __name__ == "__main__":
    main()