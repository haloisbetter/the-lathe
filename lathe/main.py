from lathe.core.task import TaskSpec
from lathe.core.orchestrator import Orchestrator
from lathe.bootstrap.openhands import OpenHandsExecutor


def main() -> None:
    print("The Lathe starting...")
    print("Executor: OpenHands (bootstrap)")

    task = TaskSpec(
        id="lathe-smoke-001",
        goal="Verify orchestrator execution path",
        scope="bootstrap",
        constraints={},
        inputs={},
    )

    executor = OpenHandsExecutor()
    orchestrator = Orchestrator(executor)

    result = orchestrator.run_task(task)

    print("Task complete")
    print("Success:", result.success)
    print("Summary:", result.summary)


if __name__ == "__main__":
    main()