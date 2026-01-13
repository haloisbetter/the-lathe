from lathe.storage.db import LatheDB
from lathe.core.orchestrator import Orchestrator


def list_tasks(db: LatheDB) -> None:
    tasks = db.list_tasks()
    if not tasks:
        print("No tasks found.")
        return

    for task in tasks:
        print(f"- {task['id']} | {task['goal']} | {task['created_at']}")


def show_task(db: LatheDB, task_id: str) -> None:
    task = db.get_task(task_id)
    if not task:
        print(f"Task not found: {task_id}")
        return

    result = db.get_result(task_id)

    print("Task:")
    for k, v in task.items():
        print(f"  {k}: {v}")

    print("\nResult:")
    if not result:
        print("  (no result recorded)")
        return

    for k, v in result.items():
        print(f"  {k}: {v}")


def replay_task(db: LatheDB, orchestrator: Orchestrator, task_id: str) -> None:
    """
    Load a TaskSpec from DB and re-run it through the orchestrator.
    Note: With the current schema, replay overwrites the prior result for the same task_id.
    """
    task = db.load_task_spec(task_id)
    if not task:
        print(f"Task not found: {task_id}")
        return

    print(f"Replaying task: {task_id}")
    result = orchestrator.run_task(task)

    print("Replay complete")
    print("Success:", result.success)
    print("Summary:", result.summary)